#!/usr/bin/env python
"""Aggregate three-party scores into per-perspective means and pass-rates.

Examples
--------
    python scripts/aggregate_scores.py --score-dir runs/glm_psycho
    python scripts/aggregate_scores.py --score-dir runs/glm_psycho --check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psiarena.scoring import N_TOTAL, aggregate, check_dir


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--score-dir", required=True, help="dir containing scores{i}.txt")
    p.add_argument("-n", type=int, default=100, help="number of cards (default 100)")
    p.add_argument("--check", action="store_true",
                   help="only verify each file has the expected number of scored dimensions")
    return p.parse_args()


def main():
    args = parse_args()
    if args.check:
        bad = check_dir(args.score_dir, n=args.n)
        if not bad:
            print(f"OK: all {args.n} files have {N_TOTAL} scored dimensions.")
        else:
            print(f"{len(bad)} file(s) off (expected {N_TOTAL} marks; -1 = missing):")
            for card, marks in bad:
                print(f"  scores{card}.txt -> {marks}")
        return

    result = aggregate(args.score_dir, n=args.n)
    means, passes = result["means"], result["passes"]
    print(f"scored {result['n_scored']}/{args.n} dialogues"
          + (f" (skipped {result['skipped']})" if result["skipped"] else ""))
    if not means:
        return
    print("\nmean scores (1-5):")
    print(f"  client     = {means['client']}")
    print(f"  supervisor = {means['supervisor']}")
    print(f"  counselor  = {means['counselor']}")
    print(f"  overall    = {means['overall']}")
    print("\npass counts (>= threshold):")
    print(f"  client>=2.6={passes['client']}  supervisor>=3={passes['supervisor']}  "
          f"counselor>=3.8={passes['counselor']}  overall>=3={passes['overall']}")


if __name__ == "__main__":
    main()
