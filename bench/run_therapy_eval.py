"""Evaluate the first 50 Therapy-Eval cards with product-native counselors."""
import argparse
import fcntl
import hashlib
import json
import runpy
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

from bench_gateway import AiRoleSession, BENCH, configure_roles, save
from psiarena.config import chat

UPSTREAM = BENCH / "emnlp2026-graph2counsel/Therapy-Eval"
CRITERIA = ("specificity", "authenticity", "competence", "flow", "safety")


def score(prompt, turns):
    messages = [{"role": "user", "content": prompt.format(conversation="\n".join(turns))}]
    for _ in range(3):
        raw = chat("judge", messages, temperature=0).strip()
        try:
            result = json.loads(raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip())
            if (isinstance(result, dict) and type(result.get("score")) is int
                    and 0 <= result["score"] <= 4 and isinstance(result.get("justification"), str)
                    and result["justification"].strip()):
                return result
        except ValueError:
            pass
    raise ValueError("Judge returned invalid verdicts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["agent", "local"], required=True)
    parser.add_argument("--bot-id", type=int, default=1030)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1 or (args.target == "local" and not (args.model and args.base_url)):
        parser.error("Select positive workers and specify --model and --base-url for local inference")
    settings = configure_roles(args)
    generate = runpy.run_path(str(UPSTREAM / "generate-sessions.py"))["run_session"]
    profiles = json.loads((UPSTREAM / "data/eeyore.json").read_text())[:50]
    assert len(profiles) == 50
    prompts = {k: (UPSTREAM / "prompts" / (k + ".txt")).read_text() for k in CRITERIA}
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / ".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manifest = dict(target=args.target, bot_id=args.bot_id if args.target == "agent" else None,
                    cards=list(range(50)), counselor_prompt="product default", temperature=settings.temperature,
                    judge_temperature=0, local_temperature=0, max_turns=20,
                    input_sha256=hashlib.sha256(json.dumps([profiles, prompts]).encode()).hexdigest(),
                    roles={k: [r.model, r.base_url, r.thinking, r.reasoning_effort]
                           for k, r in settings.roles.items()})
    config = out / "config.json"
    if config.exists() and json.loads(config.read_text()) != manifest:
        parser.error("Output belongs to a different configuration")
    save(config, manifest)

    def evaluate(i):
        folder = out / f"card_{i:03d}"
        folder.mkdir(exist_ok=True)
        try:
            transcript = folder / "session.json"
            if not transcript.exists():
                session = None
                try:
                    if args.target == "agent":
                        session = AiRoleSession(folder / uuid.uuid4().hex, "Therapy-Eval", embed_system_prompt=False)
                        session.start()
                    def counselor(messages):
                        if session:
                            return session.chat(messages)
                        return chat("counselor", messages, temperature=0)
                    turns = generate(lambda msgs: chat("client", msgs), counselor, profiles[i]["profile"])
                    save(transcript, turns)
                finally:
                    if session:
                        session.client.session.close()
            turns = json.loads(transcript.read_text())
            verdicts = {}
            for k, prompt in prompts.items():
                path = folder / (k + ".json")
                if not path.exists():
                    save(path, score(prompt, turns))
                verdicts[k] = json.loads(path.read_text())["score"]
            print(f"card {i:03d} complete", flush=True)
            return verdicts
        except Exception as exc:
            print(f"card {i:03d} failed: {type(exc).__name__}", flush=True)
            return None

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(evaluate, range(50)))
    valid = [row for row in results if row is not None]
    means = {k: mean(row[k] for row in valid) for k in CRITERIA} if valid else {}
    summary = dict(completed=len(valid), expected=50, criterion_means=means,
                   overall=mean(means.values()) if means else None,
                   pending_cards=[i for i, row in enumerate(results) if row is None])
    save(out / "summary.json", summary)
    print(json.dumps(summary))
    return int(len(valid) != 50)


if __name__ == "__main__":
    raise SystemExit(main())
