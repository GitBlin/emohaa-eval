"""Simulate a PsychEval case, then score the generated dialogue using upstream WAI."""
import asyncio
import json
import os
import sys

from bench_gateway import AiRoleSession, BENCH, configure, parser, write_json
import requests


def main():
    p = parser(__doc__)
    p.add_argument("--case", default="cbt/1.json")
    args = p.parse_args()
    base, key = configure(args)
    out = args.output.resolve()
    repo = BENCH / "PsychEval"
    case_path = (repo / "data" / args.case).resolve()
    if not case_path.is_relative_to((repo / "data").resolve()):
        p.error("--case must be relative to PsychEval/data")
    case = json.loads(case_path.read_text())
    out.mkdir(parents=True, exist_ok=False)
    os.chdir(repo / "eval")
    sys.path.insert(0, str(repo / "eval"))
    from methods.counselor.wai import WAI

    write_json(out / "manifest.json", {
        "protocol": "local interactive adaptation; upstream WAI only",
        "target": args.target, "bot_id": args.bot_id if args.target == "agent" else None,
        "target_model": args.target_model if args.target == "api" else None,
        "patient_model": args.patient_model, "judge_model": args.judge_model,
        "endpoint": base, "case": args.case, "turns": args.turns,
    })
    dialogue = []
    agent = None
    with requests.Session() as http:
        def complete(role, model, messages, response_format=None):
            body = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 8192}
            if response_format:
                body["response_format"] = response_format
            r = http.post(base + "/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {key}"}, timeout=(10, 100))
            if not r.ok:
                raise RuntimeError(f"{role}: gateway HTTP {r.status_code}")
            data = r.json()
            text = data["choices"][0]["message"].get("content")
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"{role}: no answer text")
            index = len(list(out.glob(f"{role}_*.json"))) + 1
            write_json(out / f"{role}_{index:03d}.json", {
                "request": body, "reply": text, "usage": data.get("usage"), "model": data.get("model"),
            })
            return text.strip()

        class Judge:
            async def chat_text(self, messages, response_format=None):
                # Supply the upstream schema in text as well, for gateways without strict schemas.
                schema = response_format["json_schema"]["schema"]
                messages = [*messages, {"role": "user", "content":
                            "仅返回JSON对象，符合此结构：" + json.dumps(schema, ensure_ascii=False)}]
                return complete("judge", args.judge_model, messages, {"type": "json_object"})

        patient_prompt = ("模拟以下来访者。根据咨询师的实际回复自然对话，逐步透露相关信息。"
                          "只输出来访者的一句发言，不泄露设定或代替咨询师说话。\n"
                          + json.dumps(case["client_info"], ensure_ascii=False))
        counselor_prompt = "请作为心理支持助手，用中文自然回应来访者当前发言。"
        try:
            if args.target == "agent":
                agent = AiRoleSession(out / "agent_requests", "PsychEval")
                agent.start()
            for turn in range(args.turns):
                patient_history = [
                    {"role": "assistant" if row["role"] == "Client" else "user", "content": row["text"]}
                    for row in dialogue
                ]
                patient = complete("patient", args.patient_model, [
                    {"role": "system", "content": patient_prompt},
                    *(patient_history or [{"role": "user", "content": "请自然开启第一次会谈。"}]),
                ])
                dialogue.append({"role": "Client", "text": patient})
                write_json(out / "dialogue.json", dialogue)
                history = [{"role": "user" if row["role"] == "Client" else "assistant",
                            "content": row["text"]} for row in dialogue]
                messages = [{"role": "system", "content": counselor_prompt}, *history]
                reply = agent.chat(messages) if agent else complete("target", args.target_model, messages)
                dialogue.append({"role": "Counselor", "text": reply})
                write_json(out / "dialogue.json", dialogue)
            scores = asyncio.run(WAI().evaluate(Judge(), dialogue, case["client_info"]))
            if not 0 <= scores["counselor"] <= 10:
                raise RuntimeError("Invalid WAI score")
            write_json(out / "summary.json", {"WAI": scores["counselor"], "turns": args.turns})
            print(f"Artifacts: {out}", flush=True)
        finally:
            if agent:
                agent.client.session.close()


if __name__ == "__main__":
    main()
