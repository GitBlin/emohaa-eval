#!/usr/bin/env python
"""Run three-party evaluation over a folder of generated dialogues.

Reads ``dialogue{i}.txt`` from --input-dir and writes ``scores{i}.txt`` to --output-dir
(which defaults to --input-dir, matching the layout used for the rewrite feedback step).

Example
-------
    python scripts/evaluate_dialogues.py --input-dir runs/glm_psycho
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psiarena.config import get_settings
from psiarena.evaluate import evaluate_dialogue
from psiarena.scoring import parse_score_file
from psiarena.runtime import run_log


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-dir", required=True, help="dir containing dialogue{i}.txt")
    p.add_argument("--output-dir", help="dir for scores{i}.txt (default: --input-dir)")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=100)
    p.add_argument("--resume", action="store_true", help="skip cards whose scores file already exists")
    return p.parse_args()


def main():
    args = parse_args()
    if args.start < 0 or args.end <= args.start or args.end > 100:
        sys.exit("Invalid card range; require 0 <= start < end <= 100")
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir) if args.output_dir else in_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"judge={get_settings().judge_model} | cards [{args.start}, {args.end})")

    for card in range(args.start, args.end):
        dialogue_path = in_dir / f"dialogue{card}.txt"
        if not dialogue_path.exists():
            print(f"[{card}] SKIP: no dialogue {dialogue_path}")
            continue
        out_path = out_dir / f"scores{card}.txt"
        if args.resume and out_path.exists() and parse_score_file(out_path) is not None:
            print(f"[{card}] skip (valid scores)")
            continue

        dialogue_text = dialogue_path.read_text(encoding="utf-8")
        # Separate directory per scoring execution prevents overwriting raw calls.
        import uuid
        audit_dir = out_dir / 'judge_calls' / f'{card:03d}_{uuid.uuid4().hex[:8]}'
        with run_log(audit_dir):
            scores = evaluate_dialogue(card, dialogue_text, output_dir=audit_dir)
        out_path.write_text(scores, encoding="utf-8")
        print(f"[{card}] saved scores")

    print("done.")


if __name__ == "__main__":
    main()
