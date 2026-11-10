#!/usr/bin/env python3
"""Auditable, resumable ToMBench evaluation of 李言老师 (bot 242).

Default: Chinese, all questions, five independently shuffled trials per question.
Credentials are imported at runtime or read from LINGX_* environment variables;
authentication bodies/headers/tokens are never saved in evaluation artifacts.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import shutil
import statistics
import sys
import time
from uuid import uuid4

import requests

HERE = Path(__file__).resolve().parent
VERSION = "1.0.0"
BOT_ID = 242


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_json(path, value):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class APIError(RuntimeError):
    pass


class ProtocolError(RuntimeError):
    pass


def unpack(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        message = payload.get("message") if isinstance(payload, dict) else "响应不是对象"
        code = payload.get("code") if isinstance(payload, dict) else None
        raise APIError(f"业务错误 code={code}: {message}")
    return payload.get("data")


def sse_events(lines):
    """Parse event boundaries, multiline data and a final event without blank line."""
    data, event_type = [], "message"
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line == "":
            if data:
                yield event_type, "\n".join(data)
            data, event_type = [], "message"
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
        elif line.startswith("event:"):
            event_type = line[6:].strip()
    if data:
        yield event_type, "\n".join(data)


def parse_sse(lines, event_sink):
    pieces, metadata = [], {"models": [], "conversation_ids": [], "finish_seen": False}
    for event_type, data in sse_events(lines):
        if data.strip() == "[DONE]":
            metadata["finish_seen"] = True
            event_sink({"event": event_type, "data": "[DONE]"})
            break
        obj = json.loads(data)
        if isinstance(obj, str):
            obj = json.loads(obj)
        event_sink({"event": event_type, "data": obj})
        if not isinstance(obj, dict):
            raise ProtocolError("SSE data 解码后不是对象")
        choices = obj.get("choices") or []
        choice = choices[0] if choices else {}
        delta = choice.get("delta") or {}
        if obj.get("model") == "error" or obj.get("success") is False or event_type == "error":
            raise APIError(str(delta.get("content") or obj.get("message") or obj.get("error") or "SSE error"))
        for source, key in (("model", "models"), ("conversationId", "conversation_ids")):
            if obj.get(source) is not None and obj[source] not in metadata[key]:
                metadata[key].append(obj[source])
        if obj.get("type") not in ("tts", "tts.error") and delta.get("content"):
            if not isinstance(delta["content"], str):
                raise ProtocolError("delta.content 不是字符串")
            pieces.append(delta["content"])
        if choice.get("finishReason") == "stop" or choice.get("finish_reason") == "stop":
            metadata["finish_seen"] = True
            break
    if not metadata["finish_seen"]:
        raise ProtocolError("流在结束标记前关闭，保留原始响应但不计为完整答案")
    return "".join(pieces).strip(), metadata


class Client:
    def __init__(self, base_url, key, secret, user_id, verify=True, timeout=60):
        self.base_url = base_url.rstrip("/") + "/psychology-api"
        self.key, self.secret, self.user_id = key, secret, user_id
        self.verify, self.timeout = verify, timeout
        self.session = requests.Session()
        self.session.trust_env = False
        self.token = None

    def authenticate(self):
        # Do not log authentication input/output; both contain credentials.
        with self.session.post(self.base_url + "/apis/auth", json={
            "apiKey": self.key, "apiSecret": self.secret, "userId": self.user_id,
        }, timeout=(10, self.timeout), verify=self.verify) as response:
            response.raise_for_status()
            data = unpack(response.json())
            if not isinstance(data, dict) or not data.get("access_token"):
                raise APIError("认证未返回 access_token")
            self.token = data["access_token"]

    def call(self, method, endpoint, directory, name, payload=None, params=None, chat=False):
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / f"{name}.request.json", {
            "timestamp": now(), "method": method, "url": self.base_url + endpoint,
            "json": payload, "params": params, "authentication": "Bearer [NOT SAVED]",
        })
        start = time.monotonic()
        with self.session.request(method, self.base_url + endpoint, json=payload, params=params,
                                  headers={"Authorization": f"Bearer {self.token}"},
                                  stream=True, timeout=(10, self.timeout), verify=self.verify) as response:
            write_json(directory / f"{name}.response.json", {
                "status_code": response.status_code, "content_type": response.headers.get("content-type"),
                "headers_seconds": time.monotonic() - start,
            })
            raw_path = directory / f"{name}.body.bin"
            if chat and response.ok and "text/event-stream" in response.headers.get("content-type", "").lower():
                # Save the body before parsing so malformed/failed events remain auditable.
                # Only received chunks are saved if the request times out.
                with raw_path.open("wb") as raw:
                    def lines():
                        buffer = b""
                        for chunk in response.iter_content(chunk_size=1024):
                            raw.write(chunk)
                            raw.flush()
                            if time.monotonic() - start > max(120, self.timeout * 3):
                                raise TimeoutError("SSE 总时长超限")
                            buffer += chunk
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                yield line.rstrip(b"\r").decode("utf-8")
                        if buffer:
                            yield buffer.rstrip(b"\r").decode("utf-8")
                    return parse_sse(lines(), lambda event: append_json(directory / f"{name}.events.jsonl", event))
            with raw_path.open("wb") as raw:
                for chunk in response.iter_content(chunk_size=8192):
                    raw.write(chunk)
            response.raise_for_status()
            body = json.loads(raw_path.read_bytes())
            data = unpack(body)
            if chat:
                if not isinstance(data, dict) or not isinstance(data.get("content"), str):
                    raise ProtocolError("聊天响应缺少字符串 data.content")
                return data["content"].strip(), {"response_source": data.get("responseSource"),
                                                "chat_id": data.get("chatId"), "finish_seen": True}
            return data


def prepare(args):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    run = args.output_dir.resolve() / run_id
    run.mkdir(parents=True)
    data_dir = run / "snapshot/data"
    data_dir.mkdir(parents=True)
    hashes = {}
    for path in sorted(args.data_dir.glob("*.jsonl")):
        target = data_dir / path.name
        shutil.copyfile(path, target)
        hashes[str(target.relative_to(run))] = digest(target)
    if not hashes:
        raise ValueError("数据目录中没有 JSONL 文件")
    prompts_path = HERE / "Tombench/prompts.py"
    shutil.copyfile(prompts_path, run / "snapshot/prompts.py")
    shutil.copyfile(__file__, run / "snapshot/evaluate_liyan.py")
    prompts = import_file("frozen_prompts", run / "snapshot/prompts.py")
    for name in ("prompts.py", "evaluate_liyan.py"):
        hashes[f"snapshot/{name}"] = digest(run / "snapshot" / name)
    references = {}
    for name in ("智能体聊天最佳实践.docx", "Emohaa _ agent 工程算法 todo list.docx"):
        path = HERE.parent / name
        if path.exists():
            references[name] = digest(path)
    pools, dataset_count = [], 0
    sampler = random.Random(args.seed)
    for path in sorted(data_dir.glob("*.jsonl")):
        rows = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                d = json.loads(line, parse_constant=lambda _: None)
                rows.append({"sample_id": f"{path.stem}:{line_no}", "task_file": path.stem,
                             "ability": d["能力\nABILITY"].strip(), "original_data": d})
        dataset_count += len(rows)
        sampler.shuffle(rows)
        pools.append(rows)
    sampler.shuffle(pools)
    selected = []
    while any(pools) and (args.limit == 0 or len(selected) < args.limit):
        for pool in pools:
            if pool and (args.limit == 0 or len(selected) < args.limit):
                selected.append(pool.pop())
    cases = []
    for s in selected:
        d = s["original_data"]
        answer_match = re.fullmatch(r"\s*([ABCD])\.?\s*", str(d["答案\nANSWER"]))
        if not answer_match:
            raise ValueError(f"异常标准答案: {s['sample_id']}")
        answer = answer_match[1]
        for lang in args.languages:
            values = {letter: d[("选项" if lang == "zh" else "OPTION-") + letter] for letter in "ABCD"}
            valid = [letter for letter, value in values.items() if isinstance(value, str) and value.strip()]
            if len(valid) not in (2, 4) or answer not in valid:
                raise ValueError(f"异常选项: {s['sample_id']}")
            instruction = getattr(prompts, f"SystemEvaluatePrompt_{lang}" + ("_cot" if args.cot else ""))
            # Keep the official template; remove nonexistent C/D choices for binary questions.
            if len(valid) == 2:
                instruction = instruction.replace("A、B、C、D", "A、B").replace("A, B, C, D", "A, B")
                instruction = instruction.replace('，“[[C]]”，“[[D]]”', '').replace(', "[[C]]", or "[[D]]"', '')
            template = getattr(prompts, f"UserEvaluatePrompt{len(valid)}Choices_{lang}")
            for repeat in range(args.repeats):
                order = valid.copy()
                # Independent deterministic shuffles: adding languages does not change ZH inputs.
                rng = random.Random(f"{args.seed}:{s['sample_id']}:{lang}:{repeat}")
                rng.shuffle(order)
                mapping = dict(zip("ABCD", order))
                formatted = {"story": d["故事" if lang == "zh" else "STORY"],
                             "question": d["问题" if lang == "zh" else "QUESTION"]}
                for shown, original in mapping.items():
                    formatted["choice_" + shown.lower()] = re.sub(r"^[ABCD]\.\s*", "", values[original].strip())
                content = instruction + "\n\n" + template.format(**formatted)
                trial_id = f"trial_{len(cases):06d}"
                cases.append({**s, "trial_id": trial_id, "language": lang, "repeat": repeat,
                              "answer": answer, "answer_raw": d["答案\nANSWER"], "map": mapping,
                              "request": {"botId": BOT_ID, "content": content,
                                          "isStream": True, "returnTts": False, "courseProgressId": 0}})
    write_json(run / "plan.json", cases)
    hashes["plan.json"] = digest(run / "plan.json")
    manifest = {
        "created_at": now(), "script_version": VERSION, "bot_id": BOT_ID, "bot_name": "李言老师",
        "base_url": args.base_url.rstrip("/"),
        "user_id": args.user_id or f"liyan_eval_{run_id}",
        "model_version": args.model_version, "harness_version": args.harness_version,
        "configuration_status": "operator_supplied_not_verified" if args.model_version != "unreported" else "backend_version_unreported",
        "languages": args.languages, "repeats": args.repeats, "cot": args.cot, "seed": args.seed,
        "dataset_questions": dataset_count, "selected_questions": len(selected), "planned_trials": len(cases),
        "interval": args.interval, "max_attempts": args.max_attempts, "timeout": args.timeout,
        "summary_every": args.summary_every, "max_consecutive_errors": args.max_consecutive_errors,
        "credential_defaults_module": str(HERE.parent / "bot_chat_client.py"),
        "verify_tls": not args.insecure, "generation_parameters": "backend defaults; not exposed by documented API",
        "context_policy": "clearContext + verify onlyLastSession before every attempt; shared account may still retain long-term memory",
        "scoring": "unique bracketed answer; invalid/error counted wrong; plurality of mapped valid answers; ties invalid; no default A",
        "protocol": "ToMBench local adapted agent evaluation; instructions in user content; not a certified official submission",
        "dataset_policy": "evaluation-only holdout; no training or prompt tuning on these items",
        "source_hashes": hashes, "reference_document_hashes": references,
        "environment": {"python": sys.version, "platform": platform.platform(), "requests": requests.__version__},
        "invocation": sys.argv, "other_benchmarks": "EmoBench / Psy-Arena / MentalHealthBench not evaluated by this script",
    }
    write_json(run / "manifest.json", manifest)
    return run, manifest, cases


def score(text, case):
    marks = set(re.findall(r"\[\[([ABCD])\]\]", text))
    shown = next(iter(marks)) if len(marks) == 1 else None
    if shown not in case["map"]:
        shown = None
    original = case["map"].get(shown)
    return {"status": "ok" if shown else "invalid_answer", "prediction": shown,
            "prediction_original": original, "correct": original == case["answer"],
            "strict_format": bool(shown and re.fullmatch(r"\s*\[\[[ABCD]\]\]\s*", text))}


def trial(client, case, run, manifest):
    trial_dir = run / "trials" / case["trial_id"]
    trial_dir.mkdir(parents=True, exist_ok=True)
    result = {k: case[k] for k in ("trial_id", "sample_id", "task_file", "ability", "language", "repeat", "answer", "map")}
    result.update(status="request_error", correct=False, strict_format=False,
                  prediction=None, prediction_original=None, reply="", attempts=[])
    started = time.monotonic()
    # A resumed interrupted attempt gets a new directory; no partial evidence is overwritten.
    previous = [int(p.name.split("_")[1]) for p in trial_dir.glob("attempt_*") if p.is_dir()]
    offset = max(previous, default=0)
    for n in range(1, manifest["max_attempts"] + 1):
        attempt_dir = trial_dir / f"attempt_{offset+n:03d}"
        attempt_dir.mkdir()
        info = {"number": offset+n, "started_at": now(), "stage": "clear_context"}
        try:
            cleared = client.call("POST", "/open/chat/clearContext", attempt_dir, "clear",
                                  payload={"botId": BOT_ID, "courseProgressId": 0})
            if not isinstance(cleared, dict) or cleared.get("role") != "flush_context":
                raise ProtocolError("清理响应未包含 flush_context 标记")
            info["stage"] = "verify_context"
            context = client.call("GET", "/open/chat/context", attempt_dir, "context_before", params={
                "botId": BOT_ID, "courseProgressId": 0, "onlyLastSession": "true", "pageNum": 0, "pageSize": 30})
            if not isinstance(context, dict) or not isinstance(context.get("content"), list):
                raise ProtocolError("上下文查询格式异常")
            if any(m.get("role") in ("user", "role") for m in context["content"]):
                raise ProtocolError("清理后仍存在 user/role 历史，停止本次发送")
            info["stage"] = "chat"
            reply, response_metadata = client.call("POST", "/open/chat/completions", attempt_dir, "chat",
                                                   payload=case["request"], chat=True)
            if reply == "内容生成状态失败，请稍后重试":
                raise APIError(reply)
            result.update(reply=reply, response_metadata=response_metadata, **score(reply, case))
            info["status"] = "received"
            # Retrieve server provenance after the answer; audit failure does not change its score.
            try:
                context = client.call("GET", "/open/chat/context", attempt_dir, "context_after", params={
                    "botId": BOT_ID, "courseProgressId": 0, "onlyLastSession": "true", "pageNum": 0, "pageSize": 10})
                messages = context.get("content") or []
                result["response_sources"] = sorted({str(m["responseSource"]) for m in messages if m.get("responseSource")})
                result["server_chat_ids"] = sorted({str(m["chatId"]) for m in messages if m.get("chatId")})
            except Exception as exc:
                info["audit_error"] = f"{type(exc).__name__}: {exc}"
            result["attempts"].append(info)
            write_json(attempt_dir / "outcome.json", info)
            break
        except (requests.RequestException, APIError, ProtocolError, ValueError, TimeoutError) as exc:
            info.update(status="error", error=f"{type(exc).__name__}: {exc}")
            result["attempts"].append(info)
            result["error"] = info["error"]
            write_json(attempt_dir / "outcome.json", info)
            if n < manifest["max_attempts"]:
                if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 401:
                    client.authenticate()
                time.sleep(min(2 ** n, 8))
    result["started_at"] = result["attempts"][0]["started_at"]
    result["finished_at"] = now()
    result["elapsed_seconds"] = time.monotonic() - started
    if result["status"] != "request_error":
        result.pop("error", None)
    write_json(trial_dir / "result.json", result)
    return result


def metrics(rows):
    count = len(rows)
    valid = sum(r["status"] == "ok" for r in rows)
    correct = sum(r["correct"] for r in rows)
    return {"count": count, "correct": correct, "valid": valid,
            "invalid": sum(r["status"] == "invalid_answer" for r in rows),
            "errors": sum(r["status"] == "request_error" for r in rows),
            "accuracy": correct / count if count else None,
            "accuracy_on_valid": correct / valid if valid else None,
            "strict_format_rate": sum(r["strict_format"] for r in rows) / count if count else None}


def summarize(run, manifest, cases, rows, status):
    groups = defaultdict(list)
    by_id = {c["trial_id"]: c for c in cases}
    for r in rows:
        groups[(r["language"], r["sample_id"])].append(r)
    votes = []
    for (language, sample_id), rs in groups.items():
        if len(rs) != manifest["repeats"]:
            continue
        counts = Counter(r["prediction_original"] for r in rs if r["status"] == "ok")
        winners = [k for k, v in counts.items() if v == max(counts.values())] if counts else []
        prediction = winners[0] if len(winners) == 1 else None
        votes.append({"sample_id": sample_id, "language": language, "answer": rs[0]["answer"],
                      "prediction": prediction, "correct": prediction == rs[0]["answer"],
                      "valid_votes": sum(counts.values()), "votes": dict(counts),
                      "all_trials_valid": all(r["status"] == "ok" for r in rs)})
    summary = {"updated_at": now(), "run_status": status, "trials": metrics(rows),
               "planned_trials": len(cases), "completed_trials": len(rows),
               "completed_question_languages": len(votes),
               "question_vote_accuracy": sum(v["correct"] for v in votes) / len(votes) if votes else None,
               "question_vote_ties_or_no_answer": sum(v["prediction"] is None for v in votes),
               "questions_with_all_valid_trials": sum(v["all_trials_valid"] for v in votes),
               "attempt_errors": sum(a["status"] == "error" for r in rows for a in r["attempts"]),
               "context_after_audit_errors": sum(bool(a.get("audit_error")) for r in rows for a in r["attempts"])}
    for field in ("language", "task_file", "ability"):
        buckets = defaultdict(list)
        for r in rows:
            buckets[r[field]].append(r)
        summary["by_" + field] = {k: metrics(v) for k, v in buckets.items()}
    durations = [r["elapsed_seconds"] + manifest["interval"] for r in rows]
    if durations:
        mean = statistics.mean(durations)
        summary["timing"] = {"measured_trials": len(durations), "mean_seconds_per_trial_including_interval": mean,
                             "median_seconds": statistics.median(durations),
                             "p95_seconds": sorted(durations)[math.ceil(len(durations) * .95)-1],
                             "remaining_hours_estimate": mean * (len(cases)-len(rows)) / 3600,
                             "full_dataset_1_repeat_1_language_hours": mean * manifest["dataset_questions"] / 3600,
                             "full_dataset_5_repeats_1_language_hours": mean * manifest["dataset_questions"] * 5 / 3600,
                             "caveat": "基于当前样本和服务速度线性外推，不含长期限流/中断；CoT与不同语言需另测"}
    write_json(run / "summary.json", summary)
    write_json(run / "question_votes.json", votes)
    # Atomic result files are the recovery authority; these are convenient exports.
    for filename, records in (("responses.jsonl", rows), ("badcases.jsonl", [
        {**r, "case": by_id[r["trial_id"]], "evidence_dir": "trials/"+r["trial_id"]}
        for r in rows if not r["correct"] or not r["strict_format"]])):
        temp = run / (filename + ".tmp")
        temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        temp.replace(run / filename)
    percent = lambda x: "N/A" if x is None else f"{x:.2%}"
    text = ["# 李言老师 ToMBench 本地评测", "", f"状态：{status}；更新时间：{summary['updated_at']}（UTC）。",
            f"botId=242；底座版本={manifest['model_version']}；harness版本={manifest['harness_version']}。",
            "", f"完成 {len(rows)}/{len(cases)} 次；按次准确率 {percent(summary['trials']['accuracy'])}；按题投票准确率 {percent(summary['question_vote_accuracy'])}。",
            f"无效答案 {summary['trials']['invalid']}；最终请求失败 {summary['trials']['errors']}；所有尝试中错误 {summary['attempt_errors']}。",
            "", "| 题目文件 | 次数 | 答对 | 无效 | 请求失败 | 准确率 |", "|---|---:|---:|---:|---:|---:|"]
    for key, m in summary["by_task_file"].items():
        text.append(f"| {key} | {m['count']} | {m['correct']} | {m['invalid']} | {m['errors']} | {percent(m['accuracy'])} |")
    text += ["", "## 口径与限制", "",
             "本报告是线上智能体的 ToMBench 适配评测，不是纯 Emohaa 分数或官方榜单提交。模型与 harness 标识由操作者填写，服务端版本锁定需负责人确认。",
             "答题要求放在用户消息；温度等生成参数由服务端控制。二选一提示词去掉不存在的选项；错误标准答案 A. 被规范化为 A。",
             "严格提取唯一 [[A]] 类标记；无效/失败计错。多次答案映射回原选项后按最高票选取，并列不猜测；缺失试次的题不计入投票分母。",
             "与原仓库默认A、并列取首个等行为存在差异，不能不加说明直接对比论文数值。20个题目文件不等于论文8类任务；能力标签保留原始字符串并去除首尾空格。",
             "每次尝试前清理并核查当前会话；这不保证跨会话长期记忆、其他业务状态完全清除。请勿用其他进程同时操作本次user_id。",
             "本次只评测ToMBench；EmoBench、Psy-Arena、MentalHealthBench，以及安全、记忆、抢话等业务指标不由此成绩替代。",
             "所有题目仅用于评估，原始数据、代码、提示词及哈希均留档；badcases只在本地保存，未公开或对外提交。",
             "", "## 交付物", "", "manifest.json、plan.json、snapshot/、trials/、responses.jsonl、question_votes.json、summary.json、badcases.jsonl、artifact_index.json。",
             "trials下保留每次清理、历史查询、聊天请求、原始响应体、解析事件和错误；不保存API密钥或认证Token。"]
    if "timing" in summary:
        text += ["", "## 耗时外推", "", json.dumps(summary["timing"], ensure_ascii=False, indent=2)]
    (run / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="抽样题数，0=全部2860题")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--languages", nargs="+", choices=["zh", "en"], default=["zh"])
    parser.add_argument("--cot", action="store_true", help="使用原仓库CoT提示词；默认直接答题")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--max-attempts", type=int, default=2, help="仅失败重试；每次重试先清理上下文")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--summary-every", type=int, default=20, help="每多少个试次刷新汇总，逐题结果始终立即保存")
    parser.add_argument("--max-consecutive-errors", type=int, default=5, help="连续最终失败达到此数即暂停运行")
    parser.add_argument("--insecure", action="store_true", help="显式关闭TLS校验，默认验证证书")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", type=Path, help="恢复已有运行，使用manifest中的参数；已完成的失败也不重复发送")
    parser.add_argument("--report-only", type=Path, help="从已有结果重建报告，不联网")
    parser.add_argument("--data-dir", type=Path, default=HERE / "Tombench/data")
    parser.add_argument("--output-dir", type=Path, default=HERE / "liyan_evaluations")
    parser.add_argument("--base-url", default=os.getenv("LINGX_BASE_URL", "https://www.ai-role.cn"))
    parser.add_argument("--user-id", help="默认每次运行新建专用测试用户；不要与其他程序共用")
    parser.add_argument("--model-version", default="unreported")
    parser.add_argument("--harness-version", default="unreported")
    args = parser.parse_args(argv)
    if args.limit < 0 or args.repeats < 1 or args.interval < 0 or args.max_attempts < 1 or args.timeout <= 0 or args.summary_every < 1 or args.max_consecutive_errors < 1:
        parser.error("limit/interval不得为负；repeats/max-attempts/timeout必须为正")
    if len(set(args.languages)) != len(args.languages):
        parser.error("languages不能重复")
    if args.user_id and len(args.user_id) > 64:
        parser.error("user-id不得超过64字符")
    if args.resume and args.report_only:
        parser.error("resume与report-only不能同时使用")
    run = args.resume or args.report_only
    if run:
        run = run.resolve()
        manifest, cases = read_json(run / "manifest.json"), read_json(run / "plan.json")
        for name, expected in manifest["source_hashes"].items():
            if digest(run / name) != expected:
                raise ValueError(f"运行快照发生变化: {name}")
        if digest(__file__) != manifest["source_hashes"]["snapshot/evaluate_liyan.py"]:
            raise ValueError("恢复/重建必须使用该运行snapshot中的脚本，避免代码版本混用")
    else:
        run, manifest, cases = prepare(args)
    print(f"RUN_DIR={run}\n计划 {len(cases)} 次答题；用户 {manifest['user_id']}", flush=True)
    rows = []
    for case in cases:
        path = run / "trials" / case["trial_id"] / "result.json"
        if path.exists():
            result = read_json(path)
            if result["trial_id"] != case["trial_id"]:
                raise ValueError("结果trial_id不匹配")
            rows.append(result)
    if args.dry_run or args.report_only:
        summarize(run, manifest, cases, rows, "prepared" if args.dry_run else "complete" if len(rows) == len(cases) else "partial")
        print("离线完成，未调用平台。")
        return
    # Import only defaults; never copy this credential-bearing module into the run archive.
    original_client = import_file("original_bot_client", manifest["credential_defaults_module"])
    client = Client(manifest["base_url"], os.getenv("LINGX_API_KEY", original_client.DEFAULT_API_KEY),
                    os.getenv("LINGX_API_SECRET", original_client.DEFAULT_API_SECRET), manifest["user_id"],
                    manifest["verify_tls"], manifest["timeout"])
    completed = {r["trial_id"] for r in rows}
    status = "running"
    exit_code = 0
    consecutive_errors = 0
    append_json(run / "execution_log.jsonl", {"event": "start", "at": now(), "already_completed": len(rows)})
    try:
        client.authenticate()
        session_dir = run / "sessions" / uuid4().hex
        bots = client.call("GET", "/open/bot/list", session_dir, "bots")
        if not any(str(b.get("id")) == str(BOT_ID) for b in bots):
            raise APIError("当前测试用户无权访问李言老师242")
        client.call("GET", f"/open/bot/{BOT_ID}", session_dir, "bot_detail")
        for case in cases:
            if case["trial_id"] in completed:
                continue
            result = trial(client, case, run, manifest)
            rows.append(result)
            if len(rows) % manifest["summary_every"] == 0 or len(rows) == 1:
                summarize(run, manifest, cases, rows, "running")
            eta = statistics.mean(r['elapsed_seconds'] + manifest['interval'] for r in rows) * (len(cases)-len(rows)) / 3600
            print(f"[{len(rows)}/{len(cases)}] {case['sample_id']} {case['language']} #{case['repeat']+1} "
                  f"{result['status']} correct={result['correct']} elapsed={result['elapsed_seconds']:.2f}s ETA={eta:.2f}h", flush=True)
            consecutive_errors = consecutive_errors + 1 if result['status'] == 'request_error' else 0
            if consecutive_errors >= manifest['max_consecutive_errors']:
                raise APIError("连续请求失败达到阈值；保留结果，排查后可resume后续题目")
            time.sleep(manifest["interval"])
        status = "complete"
    except KeyboardInterrupt:
        status, exit_code = "interrupted", 130
    except Exception as exc:
        status, exit_code = "failed", 1
        append_json(run / "execution_log.jsonl", {"event": "fatal", "at": now(), "error": f"{type(exc).__name__}: {exc}"})
        print(f"运行失败: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        client.session.close()
        summarize(run, manifest, cases, rows, status)
        append_json(run / "execution_log.jsonl", {"event": status, "at": now(), "completed_trials": len(rows)})
        write_json(run / "artifact_index.json", {str(p.relative_to(run)): digest(p)
                   for p in sorted(run.rglob("*")) if p.is_file() and p.name != "artifact_index.json"})
        print(f"结束状态={status}；报告={run / 'report.md'}", flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main() or 0)
