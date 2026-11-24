#!/usr/bin/env python
"""Plan or execute a small auditable PsiArena run. No network without --execute."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cards', type=int, default=2, help='number of consecutive cards (default 2)')
    p.add_argument('--workers', type=int, default=2, help='concurrent independent sessions; turns within a session stay sequential')
    p.add_argument('--history', choices=['full', 'sliding'], default='full', help='simulated client history; counselor always uses server session history')
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--turns', type=int, default=25, help='25 for a complete session; shorter runs are connectivity checks')
    p.add_argument('--mode', choices=['vanilla', 'psycho'], default='psycho')
    p.add_argument('--protocol', choices=['code', 'paper_v1'], default='code')
    p.add_argument('--archive-suffix', default='', help='archive label only, e.g. message; does not change bot or evaluation settings')
    p.add_argument('--output-dir', type=Path, help='parent output directory; each execution creates a unique run')
    p.add_argument('--execute', action='store_true', help='actually call counselor, client and judge APIs')
    p.add_argument('--skip-judge', action='store_true', help='only generate sessions and audit memory')
    args = p.parse_args()
    if not 1 <= args.cards <= 100 or not 0 <= args.start < 100 or args.start+args.cards > 100 or not 1 <= args.turns <= 25:
        p.error('cards must fit [0,100), turns must be in [1,25]')
    if args.archive_suffix and any(not (c.isalnum() or c in '_-') for c in args.archive_suffix):
        p.error('archive-suffix must contain only letters, numbers, underscores or hyphens')
    if args.workers < 1:
        p.error('workers must be positive')
    plan = {'workers': min(args.workers, args.cards), 'client_history': args.history, 'cards': list(range(args.start, args.start+args.cards)), 'turns': args.turns,
            'mode': args.mode, 'protocol': args.protocol,
            'partial_session': args.turns != 25, 'judge_enabled': not args.skip_judge,
            'planned_requests': {'counselor': args.cards*args.turns, 'client': args.cards*args.turns,
                                 'judge': 0 if args.skip_judge else args.cards*3},
            'memory_policy': 'independent user per card; clear once; preserve within-session history; audit every turn',
            'retry_policy': 'no automatic retries; rerun generation in a new run/user after failures'}
    if not args.execute:
        print(json.dumps({'execution': False, 'plan': plan, 'next_step': 'add --execute to make API calls'}, ensure_ascii=False, indent=2))
        return
    from psiarena.config import get_settings
    from psiarena.ai_role import credentials
    from psiarena.ai_role_transport import write_json, append_json, now
    from psiarena.runtime import run_log
    from psiarena.pipeline import generate_dialogue
    from psiarena.evaluate import evaluate_dialogue
    from psiarena.scoring import aggregate, parse_score_text
    s = get_settings()
    if s.counselor_provider != 'ai_role':
        p.error('this script requires PSIARENA_COUNSELOR_PROVIDER=ai_role')
    credentials()  # fail locally before starting a run if unavailable
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    import os
    bot_id = int(os.getenv('PSIARENA_AI_ROLE_BOT_ID', '1030'))
    prefix = f'PsiArena_李言老师-bench测试_{bot_id}'
    if args.archive_suffix:
        prefix += '_' + args.archive_suffix
    parent = args.output_dir or ROOT.parent / prefix
    run = parent / f'{prefix}_{stamp}'
    run.mkdir(parents=True, exist_ok=False)
    # Freeze nonsecret code/data. Never copy .env or bot_chat_client.py.
    files = [p for directory in ('psiarena', 'scripts', 'data') for p in (ROOT/directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py', '.txt', '.json')]
    hashes = {}
    for source in files:
        relative = source.relative_to(ROOT)
        target = run / 'snapshot' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = {'started_at': now(), 'plan': plan, 'sha256': hashes,
                'provider': s.counselor_provider, 'bot_id': bot_id, 'archive_suffix': args.archive_suffix,
                'roles': {role: {'model': rc.model, 'base_url': rc.base_url, 'thinking': rc.thinking, 'reasoning_effort': rc.reasoning_effort}
                          for role, rc in s.roles.items()},
                'temperature': s.temperature, 'default_max_tokens': s.max_tokens,
                'client_max_tokens': int(os.getenv('PSIARENA_CLIENT_MAX_TOKENS', str(s.max_tokens))),
                'judge_max_tokens': int(os.getenv('PSIARENA_JUDGE_MAX_TOKENS', str(s.max_tokens))),
                'timeout': s.timeout,
                'counselor_parameters': 'platform-controlled; temperature/model/token usage may be undisclosed',
                'comparability': 'ai-role product adaptation: full server history; system instructions embedded as user content'}
    write_json(run / 'manifest.json', manifest)
    errors = []
    def run_card(index):
        directory = run / 'cards' / f'{index:03d}'
        directory.mkdir(parents=True)
        try:
            with run_log(directory):
                dialogue = generate_dialogue(index, args.mode, output_dir=directory, turns=args.turns, history=args.history)
                text = '\n'.join(dialogue)+'\n'
                (run / f'dialogue{index}.txt').write_text(text, encoding='utf-8')
                if not args.skip_judge:
                    scores = evaluate_dialogue(index, text, output_dir=directory)
                    (run / f'scores{index}.txt').write_text(scores, encoding='utf-8')
                    write_json(directory / 'parsed_scores.json', parse_score_text(scores, args.protocol))
            return {'at': now(), 'card': index, 'status': 'complete'}
        except Exception as exc:
            # Detailed raw requests/responses remain in per-call files. Avoid secrets in exceptions.
            error = {'at': now(), 'card': index, 'status': 'error', 'error_type': type(exc).__name__}
            return error
    print(f'Running {len(plan["cards"])} cards, {plan["workers"]} workers: {run}', flush=True)
    with ThreadPoolExecutor(max_workers=plan['workers']) as pool:
        futures = [pool.submit(run_card, index) for index in plan['cards']]
        for future in as_completed(futures):
            event = future.result()
            append_json(run / 'execution_log.jsonl', event)
            if event['status'] == 'error':
                errors.append(event)
            print(f'card {event["card"]}: {event["status"]}', flush=True)
    result = aggregate(run, protocol=args.protocol, indices=plan['cards']) if not args.skip_judge else None
    write_json(run / 'summary.json', {'finished_at': now(), 'plan': plan, 'errors': errors, 'scores': result})
    usages = []
    for path in (run/'cards').glob('*/usage.jsonl'):
        usages.extend(json.loads(line) for line in path.read_text().splitlines())
    totals = {}
    for record in usages:
        role = record['role']
        total = totals.setdefault(role, {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0, 'usage_missing': 0})
        if record['usage'] is None:
            total['usage_missing'] += 1
        else:
            for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                total[key] += record['usage'].get(key, 0)
    write_json(run / 'usage_summary.json', {'openai_roles': totals, 'ai_role_usage': 'see raw platform events/context for provider-reported usage; not included in these totals'})
    print(f'Saved: {run}')
    if errors or (result is not None and not result['complete']):
        raise SystemExit(2)

if __name__ == '__main__':
    main()
