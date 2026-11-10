#!/usr/bin/env python
"""Generate multi-turn counseling dialogues for a set of role cards.

Examples
--------
    # Vanilla Prompt (generic assistant)
    python scripts/generate_dialogues.py --mode vanilla --output-dir runs/glm_vanilla

    # Psycho Prompt (psychology-grounded)
    python scripts/generate_dialogues.py --mode psycho --output-dir runs/glm_psycho

    # feedback-guided rewrite (needs an evaluated prior run to learn from)
    python scripts/generate_dialogues.py --mode rewrite \
        --output-dir runs/glm_rewrite --feedback-dir runs/glm_psycho
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psiarena.config import get_settings
from psiarena.pipeline import Feedback, generate_dialogue, summarize_feedback


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", required=True, choices=["vanilla", "psycho", "rewrite"])
    p.add_argument("--output-dir", required=True, help="where dialogue{i}.txt files are written")
    p.add_argument("--feedback-dir", help="rewrite mode: dir of prior scores{i}.txt to learn from")
    p.add_argument("--start", type=int, default=0, help="first card index (inclusive)")
    p.add_argument("--end", type=int, default=100, help="last card index (exclusive)")
    p.add_argument("--resume", action="store_true", help="skip cards whose dialogue file already exists")
    return p.parse_args()


def main():
    args = parse_args()
    if args.mode == "rewrite" and not args.feedback_dir:
        sys.exit("rewrite mode requires --feedback-dir (a prior evaluated run).")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    s = get_settings()
    print(f"mode={args.mode} | counselor={s.counselor_model} | client={s.client_model} "
          f"| cards [{args.start}, {args.end})")

    for card in range(args.start, args.end):
        out_path = out_dir / f"dialogue{card}.txt"
        if args.resume and out_path.exists():
            print(f"[{card}] skip (exists)")
            continue

        feedback = None
        if args.mode == "rewrite":
            scores_path = Path(args.feedback_dir) / f"scores{card}.txt"
            if not scores_path.exists():
                print(f"[{card}] SKIP: no feedback file {scores_path}")
                continue
            feedback = Feedback(*summarize_feedback(scores_path.read_text(encoding="utf-8")))

        dialogue = generate_dialogue(card, args.mode, feedback=feedback)
        out_path.write_text("\n".join(dialogue) + "\n", encoding="utf-8")
        print(f"[{card}] saved dialogue ({len(dialogue)} lines)")

    print("done.")


if __name__ == "__main__":
    main()
