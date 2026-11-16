#!/usr/bin/env python
"""Strict score validation and JSON aggregation with coverage and explicit protocol."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from psiarena.scoring import aggregate, PROTOCOLS

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--score-dir', required=True)
    p.add_argument('-n', type=int, default=100, help='card count starting at zero')
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--end', type=int, help='exclusive; overrides -n')
    p.add_argument('--protocol', choices=PROTOCOLS, default='code')
    p.add_argument('--check', action='store_true', help='validate blocks, IDs, ranges and coverage')
    p.add_argument('--output', help='also save result as JSON')
    args = p.parse_args()
    end = args.end if args.end is not None else args.start + args.n
    if args.start < 0 or end <= args.start:
        p.error('invalid card range')
    result = aggregate(args.score_dir, protocol=args.protocol, indices=range(args.start, end))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if not result['complete']:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
