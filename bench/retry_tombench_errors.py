#!/usr/bin/env python3
"""Archive final request_error results and resume using the immutable run snapshot.

Only transport failures are retried; valid wrong answers and invalid answers remain.
Original attempts are retained and evaluate_one allocates new attempt numbers.
"""
import hashlib
import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', choices=['tombench','emobench'], default='tombench')
    parser.add_argument('--statuses', nargs='+', choices=['request_error','invalid_answer'], default=['request_error'])
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--until-success', action='store_true', help='retry request errors until cleared; Ctrl-C to stop')
    parser.add_argument('--execute', action='store_true', help='archive failed results and actually call APIs; default is read-only preview')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = json.loads((run/'manifest.json').read_text())
    cases = json.loads((run/'plan.json').read_text())
    script = run/('snapshot/evaluate_liyan.py' if args.benchmark == 'tombench' else 'snapshot/evaluate_emobench.py')
    if not script.is_file():
        parser.error('missing ToMBench snapshot script')
    for name, expected in manifest['source_hashes'].items():
        if hashlib.sha256((run/name).read_bytes()).hexdigest() != expected:
            parser.error(f'snapshot hash mismatch: {name}')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    with (run/'.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('run is active; stop its process before retrying')
        selected = []
        for case in cases:
            path = run/'trials'/case['trial_id']/'result.json'
            if path.exists() and json.loads(path.read_text()).get('status') in args.statuses:
                selected.append((case['trial_id'], path))
        missing = sum(not (run/'trials'/c['trial_id']/'result.json').exists() for c in cases)
        print(f'bot={manifest["bot_id"]}; workers={manifest["workers"]}; selected_failures={len(selected)}; missing={missing}', flush=True)
        if not args.execute:
            print('Preview only. Add --execute to archive failures and resume; --until-success repeats successful passes with remaining request errors.')
            return 0
        if not selected and not missing:
            print('No pending request failures or missing trials.')
            return 0
        backup = run/'retry_history'/stamp
        backup.mkdir(parents=True)
        # Save aggregate outputs before replacing them on resume.
        import shutil
        for name in ('manifest.json','summary.json','report.md','responses.jsonl','badcases.jsonl','artifact_index.json','question_votes.json','review_queue.json'):
            path = run/name
            if path.exists(): shutil.copyfile(path, backup/name)
        record = {'at': stamp, 'action': 'retry selected statuses; preserve prior attempts', 'statuses': args.statuses, 'benchmark': args.benchmark,
                  'trial_ids': [tid for tid,_ in selected], 'count': len(selected),
                  'workers': manifest['workers']}
        (backup/'retry_plan.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        for tid, path in selected:
            target = backup/'results'/tid/'result.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            path.rename(target)
        with (run/'execution_log.jsonl').open('a') as out:
            out.write(json.dumps(record, ensure_ascii=False)+'\n')
        print(f'Archived {len(selected)} selected failed results; original attempt files retained.', flush=True)
    # Snapshot verifies original source hashes and recreates summaries from current results.
    code = subprocess.call([sys.executable, str(script), '--resume', str(run)])
    if code:
        # The frozen ToMBench runner may stop at its consecutive-failure threshold.
        # Repeat only that known condition, never authentication/config errors.
        events = [json.loads(line) for line in (run/'execution_log.jsonl').read_text().splitlines() if line.strip()]
        last_fatal = next((e for e in reversed(events) if e.get('event') == 'fatal'), {})
        if args.until_success and code == 1 and '连续失败达到阈值' in last_fatal.get('error', ''):
            print('Consecutive request failures; retaining all records, retrying immediately.', flush=True)
            return 'retry'
        return code
    if args.until_success:
        outstanding = []
        for case in cases:
            path = run/'trials'/case['trial_id']/'result.json'
            if not path.exists() or json.loads(path.read_text()).get('status') in args.statuses:
                outstanding.append(case['trial_id'])
        if outstanding:
            print(f'{len(outstanding)} request errors remain; retrying immediately. Ctrl-C to stop.', flush=True)
            return 'retry'
    return code


if __name__ == '__main__':
    try:
        while True:
            result = main()
            if result != 'retry':
                raise SystemExit(result)
    except KeyboardInterrupt:
        print('Stopped by user; saved records retained.', flush=True)
        raise SystemExit(130)
