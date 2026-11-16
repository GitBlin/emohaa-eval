#!/usr/bin/env python3
"""Archive final request_error results and resume using the immutable run snapshot.

Only transport failures are retried; valid wrong answers and invalid answers remain.
Original attempts are retained and evaluate_one allocates new attempt numbers.
"""
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
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--until-success', action='store_true', help='retry request errors until cleared; Ctrl-C to stop')
    args = parser.parse_args()
    run = args.run_dir.resolve()
    manifest = json.loads((run/'manifest.json').read_text())
    cases = json.loads((run/'plan.json').read_text())
    script = run/'snapshot/evaluate_emobench.py'
    if not script.is_file():
        parser.error('missing EmoBench snapshot script')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    with (run/'.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('run is active; stop its process before retrying')
        selected = []
        for case in cases:
            path = run/'trials'/case['trial_id']/'result.json'
            if path.exists() and json.loads(path.read_text()).get('status') == 'request_error':
                selected.append((case['trial_id'], path))
        backup = run/'retry_history'/stamp
        backup.mkdir(parents=True)
        # Save aggregate outputs before replacing them on resume.
        import shutil
        for name in ('summary.json','report.md','responses.jsonl','badcases.jsonl','artifact_index.json'):
            path = run/name
            if path.exists(): shutil.copyfile(path, backup/name)
        record = {'at': stamp, 'action': 'retry request_error only; preserve prior attempts',
                  'trial_ids': [tid for tid,_ in selected], 'count': len(selected),
                  'workers': manifest['workers']}
        (backup/'retry_plan.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        for tid, path in selected:
            target = backup/'results'/tid/'result.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            path.rename(target)
        with (run/'execution_log.jsonl').open('a') as out:
            out.write(json.dumps(record, ensure_ascii=False)+'\n')
        print(f'Archived {len(selected)} request_error results; original attempt files retained.', flush=True)
    # Snapshot verifies original source hashes and recreates summaries from current results.
    code = subprocess.call([sys.executable, str(script), '--resume', str(run)])
    if code:
        return code  # explicit interruption/auth/config errors must remain visible
    if args.until_success:
        outstanding = []
        for case in cases:
            path = run/'trials'/case['trial_id']/'result.json'
            if not path.exists() or json.loads(path.read_text()).get('status') == 'request_error':
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
