#!/usr/bin/env python3
"""Small ToMBench pilot for the Lingx bot API. Run --help for usage."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import sys
import time
from uuid import uuid4

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "Tombench"))
from bot_chat_client import (  # noqa: E402
    BotChatClient, DEFAULT_API_KEY, DEFAULT_API_SECRET,
    DEFAULT_BASE_URL, DEFAULT_USER_ID,
)
from prompts import SystemEvaluatePrompt_zh, SystemEvaluatePrompt_en  # noqa: E402


def load_samples(data_dir, tasks, limit, seed):
    """Round-robin over shuffled files so large files do not dominate a pilot."""
    files = sorted(data_dir.glob("*.jsonl"))
    if tasks:
        unknown = set(tasks) - {p.stem for p in files}
        if unknown:
            raise ValueError(f"未知题目文件: {sorted(unknown)}")
        files = [p for p in files if p.stem in tasks]
    rng = random.Random(seed)
    pools = []
    for path in files:
        rows = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                rows.append({"sample_id": f"{path.stem}:{line_no}",
                             "task": path.stem,
                             "data": json.loads(line, parse_constant=lambda _: None)})
        rng.shuffle(rows)
        pools.append(rows)
    rng.shuffle(pools)
    selected = []
    while len(selected) < limit and any(pools):
        for pool in pools:
            if pool and len(selected) < limit:
                selected.append(pool.pop())
    if not selected:
        raise ValueError(f"没有找到题目: {data_dir}")
    return selected


def prepare_sample(sample, language, rng):
    d = sample["data"]
    letters = "ABCD"
    # Track original indices, including when multiple choices have equal text.
    raw_answer = str(d["答案\nANSWER"])
    match = re.fullmatch(r"\s*([ABCD])(?:\.)?\s*", raw_answer)
    if not match:
        raise ValueError(f"无法识别标准答案: {sample['sample_id']} {raw_answer!r}")
    if language == "zh":
        instruction = SystemEvaluatePrompt_zh
        body = f"[故事]\n{d['故事']}\n\n[问题]\n{d['问题']}\n\n[答案选项]"
        choices = {a: d[f"选项{a}"] for a in letters}
    else:
        instruction = SystemEvaluatePrompt_en
        body = f"[Story]\n{d['STORY']}\n\n[Question]\n{d['QUESTION']}\n\n[Candidate Answers]"
        choices = {a: d[f"OPTION-{a}"] for a in letters}
    order = [a for a in letters if isinstance(choices[a], str) and choices[a].strip()]
    if len(order) not in (2, 4) or match[1] not in order:
        raise ValueError(f"选项或标准答案异常: {sample['sample_id']}")
    rng.shuffle(order)
    mapping = dict(zip(letters, order))
    if len(order) == 2:
        instruction = (
            "请根据故事和问题，按常理从 A、B 中选择最可能的答案。"
            "只输出 [[A]] 或 [[B]]，不要输出其他内容。即使信息不足，也必须选择一个答案。"
            if language == "zh" else
            "Choose the most likely answer to the question based on the story. "
            "Output only [[A]] or [[B]], with no other text. Choose one even if information is insufficient."
        )
    for displayed, original in mapping.items():
        text = re.sub(r"^[ABCD]\.\s*", "", choices[original].strip())
        body += f"\n{displayed}. {text}"
    return {**sample, "ability": d["能力\nABILITY"].strip(),
            "answer_raw": raw_answer, "answer": match[1], "map": mapping,
            "prompt": instruction + "\n\n" + body}


def score_reply(reply, mapping, answer):
    # The existing client can return a JSON business-error message as reply text.
    if reply.strip() == "内容生成状态失败，请稍后重试":
        return {"prediction": None, "prediction_original": None,
                "status": "request_error", "strict_format": False,
                "correct": False, "error": "平台返回内容生成失败"}
    # Never guess an answer from ordinary prose or silently default to A.
    candidates = set(re.findall(r"\[\[([ABCD])\]\]", reply))
    prediction = next(iter(candidates)) if len(candidates) == 1 else None
    if prediction not in mapping:
        prediction = None
    original = mapping[prediction] if prediction else None
    return {"prediction": prediction, "prediction_original": original,
            "status": "ok" if prediction else "invalid_answer",
            "strict_format": prediction is not None and bool(re.fullmatch(r"\s*\[\[[ABCD]\]\]\s*", reply)),
            "correct": original == answer}


def summarize(records):
    def metrics(rows):
        n = len(rows)
        valid = sum(r["status"] == "ok" for r in rows)
        correct = sum(r["correct"] for r in rows)
        return {"total": n, "valid_answers": valid, "correct": correct,
                "invalid_answers": sum(r["status"] == "invalid_answer" for r in rows),
                "request_errors": sum(r["status"] == "request_error" for r in rows),
                "accuracy": correct / n if n else None,
                "accuracy_on_valid": correct / valid if valid else None,
                "strict_format_rate": sum(r["strict_format"] for r in rows) / n if n else None}
    result = metrics(records)
    for field in ("task", "ability"):
        groups = defaultdict(list)
        for row in records:
            groups[row[field]].append(row)
        result[f"by_{field}"] = {key: metrics(rows) for key, rows in groups.items()}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lingx 智能体 ToMBench 小规模测试（每题一次）")
    parser.add_argument("--list", action="store_true", help="仅查询智能体列表，不发送题目")
    parser.add_argument("--bot-id", type=int, help="测试的智能体 ID")
    parser.add_argument("--limit", type=int, default=20, help="题数，默认20")
    parser.add_argument("--task", action="append", help="题目文件名（不含.jsonl），可重复指定")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--interval", type=float, default=1, help="请求之间的间隔秒数")
    parser.add_argument("--dry-run", action="store_true", help="只生成题目，不认证、不请求平台")
    parser.add_argument("--data-dir", type=Path, default=HERE / "Tombench/data")
    parser.add_argument("--output-dir", type=Path, default=HERE / "pilot_results")
    parser.add_argument("--user-id", default=os.getenv("LINGX_USER_ID", DEFAULT_USER_ID))
    parser.add_argument("--key", default=os.getenv("LINGX_API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--secret", default=os.getenv("LINGX_API_SECRET", DEFAULT_API_SECRET))
    parser.add_argument("--base-url", default=os.getenv("LINGX_BASE_URL", DEFAULT_BASE_URL))
    args = parser.parse_args(argv)
    if args.limit < 1 or args.interval < 0:
        parser.error("--limit 必须大于0，--interval 不得小于0")
    if not args.list and not args.dry_run and args.bot_id is None:
        parser.error("请指定 --bot-id，或使用 --list / --dry-run")

    client = BotChatClient(args.key, args.secret, args.base_url)
    try:
        bots = []
        if not args.dry_run or args.list:
            client.auth_user(args.user_id)
            bots = client.get_bot_list()
        if args.list:
            for bot in bots:
                print(f"{bot['id']}\t{bot.get('name', '')}\t{bot.get('position') or ''}")
            print(f"共 {len(bots)} 个可访问智能体")
            return
        bot = next((b for b in bots if str(b.get("id")) == str(args.bot_id)), None)
        if not args.dry_run and bot is None:
            parser.error(f"当前用户无权访问智能体 {args.bot_id}，请先运行 --list")
        samples = load_samples(args.data_dir, args.task, args.limit, args.seed)
        rng = random.Random(args.seed)
        prepared = [prepare_sample(s, args.language, rng) for s in samples]
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
        output = args.output_dir / f"bot_{args.bot_id or 'preview'}_{run_id}"
        output.mkdir(parents=True, exist_ok=False)
        metadata = {"created_at": datetime.now(timezone.utc).isoformat(),
                    "bot_id": args.bot_id, "bot_name": bot.get("name") if bot else None,
                    "user_id": args.user_id, "base_url": args.base_url,
                    "language": args.language, "seed": args.seed,
                    "requested_limit": args.limit, "actual_samples": len(prepared),
                    "sampling": "round_robin_by_file", "repeats": 1, "dry_run": args.dry_run,
                    "conversation_isolation": "unverified_shared_user",
                    "instruction_placement": "user_content",
                    "note": "同一用户连续请求，未确认服务端是否保留历史；仅供试跑，不是正式基准结果。"}
        (output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"输出目录: {output}")
        print(metadata["note"], flush=True)
        records = []
        with (output / "samples.jsonl").open("w", encoding="utf-8") as sample_file:
            for sample in prepared:
                sample_file.write(json.dumps(sample, ensure_ascii=False) + "\n")
        if args.dry_run:
            print(f"预览完成，生成 {len(prepared)} 道题，未调用平台。")
            return
        with (output / "responses.jsonl").open("w", encoding="utf-8") as response_file:
            for i, sample in enumerate(prepared, 1):
                start = time.monotonic()
                row = {k: sample[k] for k in ("sample_id", "task", "ability", "map", "answer")}
                row.update(bot_id=args.bot_id, reply="", correct=False, strict_format=False,
                           prediction=None, prediction_original=None)
                try:
                    row["reply"] = client.send_message(args.bot_id, sample["prompt"])
                    row.update(score_reply(row["reply"], sample["map"], sample["answer"]))
                except Exception as exc:
                    row.update(status="request_error", error=f"{type(exc).__name__}: {exc}")
                row["elapsed_seconds"] = round(time.monotonic() - start, 3)
                records.append(row)
                response_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                response_file.flush()
                (output / "summary.json").write_text(json.dumps(summarize(records), ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[{i}/{len(prepared)}] {sample['sample_id']} {row['status']} correct={row['correct']}", flush=True)
                if i < len(prepared):
                    time.sleep(args.interval)
        summary = summarize(records)
        print(f"准确率 {summary['accuracy']:.1%}；有效答案 {summary['valid_answers']}/{summary['total']}；请求失败 {summary['request_errors']}")
    finally:
        client.session.close()


if __name__ == "__main__":
    main()
