#!/usr/bin/env python3
"""Run matched pilot questions against candidate bot pairs, without assuming architecture."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
from uuid import uuid4

HERE = Path(__file__).resolve().parent
PAIRS = [("李言", 1, 242), ("怼怼大魔王", 231, 240), ("志航老师", 1028, 243)]


def main():
    parser = argparse.ArgumentParser(description="三组候选智能体的相同题目对比；不假设 -llm 等于纯模型")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit 必须大于0")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    output = HERE / "comparison_results" / run_id
    output.mkdir(parents=True)
    note = "仅按名称配对：-llm 是否关闭 harness、底层模型是否一致、会话隔离均未确认。不能将版本差异直接归因于 harness。"
    (output / "metadata.json").write_text(json.dumps({
        "pairs": PAIRS, "limit": args.limit, "seed": args.seed,
        "language": args.language, "dry_run": args.dry_run, "note": note,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"对比目录: {output}\n{note}", flush=True)
    summaries = []
    paired = []
    expected_samples = None
    for pair_name, llm_id, other_id in PAIRS:
        pair_records = {}
        for bot_id in (llm_id, other_id):
            child_dir = output / str(bot_id)
            command = [sys.executable, str(HERE / "test_tombench_bots.py"),
                       "--bot-id", str(bot_id), "--limit", str(args.limit),
                       "--seed", str(args.seed), "--language", args.language,
                       "--output-dir", str(child_dir)]
            if args.dry_run:
                command.append("--dry-run")
            subprocess.run(command, check=True)
            run = next(child_dir.iterdir())
            samples = [json.loads(s) for s in (run / "samples.jsonl").read_text(encoding="utf-8").splitlines()]
            signature = [(s["sample_id"], s["prompt"], s["map"], s["answer"]) for s in samples]
            if expected_samples is None:
                expected_samples = signature
            if signature != expected_samples:
                raise RuntimeError("不同智能体的题目或选项顺序不一致，停止比较")
            if args.dry_run:
                continue
            meta = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
            stats = json.loads((run / "summary.json").read_text(encoding="utf-8"))
            records = [json.loads(s) for s in (run / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
            pair_records[bot_id] = {r["sample_id"]: r for r in records}
            summaries.append({"pair": pair_name, "bot_id": bot_id, "name": meta["bot_name"],
                              "mean_seconds": statistics.mean(r["elapsed_seconds"] for r in records),
                              "run_dir": str(run), **stats})
            (output / "bots_summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.dry_run:
            left, right = pair_records[llm_id], pair_records[other_id]
            paired.append({"pair": pair_name, "llm_named_id": llm_id, "other_id": other_id,
                           "both_correct": sum(left[k]["correct"] and right[k]["correct"] for k in left),
                           "only_llm_named_correct": sum(left[k]["correct"] and not right[k]["correct"] for k in left),
                           "only_other_correct": sum(not left[k]["correct"] and right[k]["correct"] for k in left),
                           "both_wrong": sum(not left[k]["correct"] and not right[k]["correct"] for k in left)})
            (output / "paired_summary.json").write_text(json.dumps(paired, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.dry_run:
        print("六个版本的离线输入一致，未发送请求。")
        return
    lines = ["# 候选版本对比", "", note, "", "| ID | 名称 | 答对/总题数 | 无效回答 | 请求失败 | 严格格式率 | 平均耗时(秒) |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f"| {s['bot_id']} | {s['name']} | {s['correct']}/{s['total']} | {s['invalid_answers']} | {s['request_errors']} | {s['strict_format_rate']:.0%} | {s['mean_seconds']:.2f} |")
    lines.extend(["", "无效回答及请求失败计错；平均耗时包括失败请求。每题仅一次，样本很小，仅供诊断。"])
    report = "\n".join(lines) + "\n"
    (output / "report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
