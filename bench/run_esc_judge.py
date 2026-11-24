"""Generate ESC-Judge conversations and compare two targets on the first 50 roles."""
import argparse
import fcntl
import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench_gateway import AiRoleSession, BENCH, configure_roles, save
from psiarena.config import chat

DATA = BENCH / "ESC-Judge/data"
ROLE_FILE = DATA / "roles-v1.json"
RUBRIC = DATA / "exploration_rubric3.jsonl"
JUDGE_PROMPT = DATA / "ESEval-multidim-cot.txt"
OPENING = "Hey! how's it going?"
ROUNDS = 7
LIMIT = 50


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roles():
    rows = [json.loads(line) for line in ROLE_FILE.read_text().splitlines() if line.strip()]
    if len(rows) != 100 or len({row["pid"] for row in rows}) != len(rows):
        raise ValueError("Expected 100 unique roles in roles-v1.json")
    return rows[:LIMIT]


def simulate(row, args, folder):
    turns = [{"role": "supporter", "content": OPENING}]
    seeker = [{"role": "system", "content": (
        f"Here is a description of your role:\n\n{row['role']}\n\n"
        "You are talking to an emotional support expert about your ongoing challenge. "
        "Focus on your problem and engage in the conversation. Make sure you are "
        "consistent with your designated behavioral traits and role description."
    )}, {"role": "user", "content": OPENING}]
    supporter = [{"role": "assistant", "content": OPENING}]
    session = None
    try:
        if args.target == "agent":
            session = AiRoleSession(folder / uuid.uuid4().hex, "ESC-Judge", embed_system_prompt=False)
            session.start()
        for _ in range(ROUNDS):
            request = chat("client", seeker.copy())
            seeker.append({"role": "assistant", "content": request})
            supporter.append({"role": "user", "content": request})
            turns.append({"role": "seeker", "content": request})
            if session:
                reply = session.chat(supporter)
            else:
                reply = chat("counselor", supporter.copy(), temperature=0)
            supporter.append({"role": "assistant", "content": reply})
            seeker.append({"role": "user", "content": reply})
            turns.append({"role": "supporter", "content": reply})
    finally:
        if session:
            session.client.session.close()
    return {"pid": row["pid"], "turns": turns}


def transcript(record):
    return "\n".join(f"{message['role']}: {message['content']}" for message in record["turns"])


def judge(prompt):
    for _ in range(3):
        raw = chat("judge", [{"role": "user", "content": prompt}], temperature=1.0)
        match = re.search(r"(?im)^[ \t]*##[ 	]+Verdict[ 	]*:?[ 	]*", raw)
        if match:
            verdict = raw[match.end():].strip().strip("*`<>. \n").strip().lower()
            if verdict in ("model a", "model b", "tie"):
                return {"verdict": verdict, "raw": raw}
    raise ValueError("Judge did not return a valid verdict")


def role_config(role):
    return [role.model, role.base_url, role.thinking, role.reasoning_effort]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--target", choices=("agent", "local"), required=True)
    generate.add_argument("--bot-id", type=int, default=1030)
    generate.add_argument("--model")
    generate.add_argument("--base-url")
    compare = commands.add_parser("compare")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    compare.set_defaults(target="agent", bot_id=1030)
    for command in (generate, compare):
        command.add_argument("--workers", type=int, default=4)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1 or (args.target == "local" and not (args.model and args.base_url)):
        parser.error("Require positive workers and --model / --base-url for a local target")
    settings = configure_roles(args)
    selected = roles()
    protocol = dict(role_file_sha256=digest(ROLE_FILE), pids=[r["pid"] for r in selected],
                    rounds=ROUNDS, client=role_config(settings.roles["client"]),
                    client_temperature=settings.temperature, supporter_prompt="product default")
    if args.mode == "generate":
        manifest = dict(mode=args.mode, protocol=protocol, target=args.target,
                        counselor=role_config(settings.roles["counselor"]))
    else:
        left, right = (p.resolve() for p in (args.left, args.right))
        if left == right or args.output.resolve() in (left, right):
            parser.error("Use two different generation directories and a separate comparison output")
        configs = [json.loads((p / "config.json").read_text()) for p in (left, right)]
        if any(c.get("mode") != "generate" or c.get("protocol") != protocol for c in configs):
            parser.error("Conversation inputs must use the same ESC-Judge generation protocol")
        rubric = json.loads(RUBRIC.read_text())
        criteria = [(stage, name, desc) for stage, dims in rubric.items() for name, desc in dims.items()]
        template = JUDGE_PROMPT.read_text()
        manifest = dict(mode=args.mode, protocol=protocol, left=str(left), right=str(right),
                        judge=role_config(settings.roles["judge"]), judge_temperature=1.0,
                        rubric_sha256=digest(RUBRIC), prompt_sha256=digest(JUDGE_PROMPT))

    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    with (out / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = out / "config.json"
        if config.exists() and json.loads(config.read_text()) != manifest:
            parser.error("Output belongs to a different configuration")
        save(config, manifest)

        def evaluate(index):
            row = selected[index]
            card = f"card_{index:03d}"
            folder = out / card
            folder.mkdir(exist_ok=True)
            try:
                if args.mode == "generate":
                    path = folder / "session.json"
                    if not path.exists():
                        save(path, simulate(row, args, folder))
                    return True
                records = [json.loads((p / card / "session.json").read_text()) for p in (left, right)]
                if any(r["pid"] != row["pid"] or len(r["turns"]) != 1 + ROUNDS * 2 for r in records):
                    raise ValueError("Input session does not match the role or expected length")
                # Balance position over the 50 roles and report wins in the original left/right order.
                order = ("left", "right") if index % 2 == 0 else ("right", "left")
                if index % 2:
                    records.reverse()
                results = {}
                for number, (stage, name, description) in enumerate(criteria):
                    path = folder / f"criterion_{number:02d}.json"
                    if not path.exists():
                        prompt = template.format(conversation_a=transcript(records[0]),
                                                 conversation_b=transcript(records[1]),
                                                 criteria=name, criteria_description=description)
                        result = judge(prompt)
                        winner = {"model a": order[0], "model b": order[1], "tie": "tie"}[result["verdict"]]
                        save(path, dict(result, winner=winner, stage=stage, criterion=name, a=order[0], b=order[1]))
                    results[name] = json.loads(path.read_text())["winner"]
                return results
            except Exception as exc:
                print(f"{card} pid={row['pid']} failed: {type(exc).__name__}", flush=True)
                return None

        with ThreadPoolExecutor(args.workers) as pool:
            results = list(pool.map(evaluate, range(LIMIT)))
        completed = [r for r in results if r is not None]
        summary = dict(completed=len(completed), expected=LIMIT,
                       pending_cards=[i for i, r in enumerate(results) if r is None])
        if args.mode == "compare":
            summary["expected_verdicts"] = LIMIT * len(criteria)
            summary["saved_verdicts"] = len(list(out.glob("card_*/criterion_*.json")))
            summary["by_criterion"] = {name: {winner: sum(r[name] == winner for r in completed)
                                              for winner in ("left", "right", "tie")}
                                       for _, name, _ in criteria}
        save(out / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return int(len(completed) != LIMIT)


if __name__ == "__main__":
    raise SystemExit(main())
