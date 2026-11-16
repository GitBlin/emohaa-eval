#!/usr/bin/env python
"""Two overlapping synthetic sessions; not part of benchmark scores."""
import argparse
import json
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if not args.execute:
        print('Two concurrent independent users, 3 turns each: seed, filler, blind recall. Add --execute.')
        return
    from psiarena.ai_role import counselor_session
    from psiarena.ai_role_transport import write_json
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + secrets.token_hex(4)
    out = ROOT.parent / 'api_diagnostics' / ('PsiArena_parallel_memory_' + stamp)
    out.mkdir(parents=True)
    markers = ['MEM-' + secrets.token_hex(8).upper() for _ in range(2)]
    barrier = Barrier(2)
    def test(index):
        row = {'case': index, 'turns': []}
        try:
            with counselor_session(out / str(index), f'parallel_memory_{index}') as session:
                row['user_id'] = session.user_id
                prompts = [f'这是接口记忆验证。请记住本次会话唯一标记：{markers[index]}。简短确认即可。',
                           '我准备今天散步十分钟，请给一句鼓励。',
                           '请准确复述本次会话之前告诉你的唯一标记，只返回标记。如果不知道，不要猜测。']
                for prompt in prompts:
                    reply = session.chat([{'role': 'user', 'content': prompt}])
                    row['turns'].append({'prompt': prompt, 'reply': reply})
                    barrier.wait(timeout=180)
                row['own_marker_recalled'] = markers[index] in reply
                row['other_marker_leaked'] = markers[1-index] in reply
                row['passed'] = row['own_marker_recalled'] and not row['other_marker_leaked']
        except Exception as exc:
            barrier.abort()
            row.update(passed=False, error_type=type(exc).__name__)
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(test, range(2)))
    report = {'cases': rows, 'passed': all(r['passed'] for r in rows),
              'scope': '3-turn behavioral probe; 25-turn persistence checked separately by benchmark history audits'}
    write_json(out / 'report.json', report)
    print(json.dumps({'output': str(out), **report}, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
