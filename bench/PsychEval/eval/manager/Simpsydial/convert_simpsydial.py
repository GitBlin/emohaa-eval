#!/usr/bin/env python
"""
Convert SimPsyDial data.json into EvaluationManager-ready JSON cases.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

SOURCE_PATH = Path("eval/data_sample/Simpsydial/data.json")
OUTPUT_DIR = Path("eval/manager/Simpsydial/prepared")
MAX_CASES: Optional[int] = None


def extract_dialogue(record: Dict) -> List[Dict[str, str]]:
    dialogue: List[Dict[str, str]] = []
    for msg in record.get("messages", []):
        role = (msg.get("role") or "").strip().lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            dialogue.append({"role": "Client", "text": content})
        elif role == "assistant":
            dialogue.append({"role": "Counselor", "text": content})
    return dialogue


def extract_metadata(record: Dict) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    system_prompts = [
        msg.get("content", "")
        for msg in record.get("messages", [])
        if (msg.get("role") or "").lower() == "system"
    ]
    if system_prompts:
        metadata["system_prompt"] = system_prompts[0]
    metadata["total_messages"] = str(len(record.get("messages", [])))
    return metadata


def convert() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE_PATH}")

    data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MAX_CASES = 10
    total = 0
    for idx, record in enumerate(data):
        if MAX_CASES is not None and total >= MAX_CASES:
            break

        dialogue = extract_dialogue(record)
        if not dialogue:
            continue

        client_turns = [turn["text"] for turn in dialogue if turn["role"] == "Client"]
        # main_problem = client_turns[0] if client_turns else dialogue[0]["text"]
        main_problem = ""
        case = {
            "client_id": f"simpsydial_{idx}",
            "client_info": {
                "topic": "",
                "main_problem": "",
                "core_demands": "",
                "responder_model": "SimPsyDial",
                "source_dataset": "SimPsyDial",
                "metadata": extract_metadata(record),
            },
            "sessions": [
                {
                    "session_number": 1,
                    "session_dialogue": dialogue,
                }
            ],
        }

        output_path = OUTPUT_DIR / f"simpsydial_{idx}.json"
        output_path.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
        total += 1

    print(f"Converted {total} cases into {OUTPUT_DIR}")


if __name__ == "__main__":
    convert()
