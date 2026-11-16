#!/usr/bin/env python3
"""Independent EmoBench EU/EA agent evaluation; bilingual, auditable and resumable."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import shutil
import signal
import statistics
import sys
import time
from uuid import uuid4

from emobench_api import Client, APIError, ProtocolError, now, digest, write_json, import_file

HERE = Path(__file__).resolve().parent
VERSION = '1.0.2'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def append(path, value):
    with Path(path).open('a', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=False) + '\n')


def parse_answer(text):
    # Official utility accepts JSON or ```json ... ```; no guessing letters from prose.
    value = text.strip()
    if '```json' in value:
        matches = re.findall(r'```json\s*([\s\S]*?)```', value)
        if len(matches) != 1:
            return None
        value = matches[0]
    try:
        def unique(pairs):
            obj = {}
            for k, v in pairs:
                if k in obj:
                    raise ValueError('duplicate JSON key')
                obj[k] = v
            return obj
        obj = json.loads(value, object_pairs_hook=unique)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def score(text, case):
    obj = parse_answer(text) or {}
    keys = ['answer'] if case['task'] == 'EA' else ['answer_q1', 'answer_q2']
    mapped, shown, component = {}, {}, {}
    for key in keys:
        answer = obj.get(key)
        mapping = case['maps'][key]
        # Case-sensitive, no suffix stripping, no guessing; matches official equality semantics.
        valid = isinstance(answer, str) and answer in mapping
        shown[key] = answer if valid else None
        mapped[key] = mapping.get(answer) if valid else None
        component[key] = mapped[key] == case['labels'][key]
    valid = all(shown[k] is not None for k in keys)
    return {'status': 'ok' if valid else 'invalid_answer',
            'prediction_shown': shown, 'prediction_original': mapped,
            'component_correct': component, 'correct': valid and all(component.values()),
            'strict_format': valid and set(obj) == set(keys + (['reasoning'] if case['cot'] else []))}


def prompt(sample, task, config, order, cot):
    lang = sample['language']
    response = config['response']
    conditions = response[task][lang]
    if cot:
        conditions = response['reasoning'][lang] + ',\n' + conditions
    # Reproduce the official output-format template exactly; move system instruction into user content.
    output = '\n{statement}\n```json\n    {{\n    {conditions}\n    }}\n``` \n    '.format(
        statement=response['cot' if cot else 'base'][lang], conditions=conditions)
    instructions = config['prompts']['sys'][lang] + output
    rank = lambda values: '\n'.join(f'{LETTERS[i]}) {value}' for i, value in enumerate(values))
    args = {'scenario': sample['scenario'], 'subject': sample['subject']}
    if task == 'EA':
        args.update(choices=rank(order['answer']), q_type=sample['question type'])
    else:
        args.update(emo_choices=rank(order['answer_q1']), cause_choices=rank(order['answer_q2']))
    return instructions + '\n\n' + config['prompts'][task][lang].format(**args)


def prepare(args):
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    bot_slug = re.sub(r"[^\w.-]+", "_", args.bot_name).strip("._-")[:64] or "bot"
    prefix = f"EmoBench_{bot_slug}_{args.bot_id}"
    output_root = (args.output_dir or HERE / prefix).resolve()
    run = output_root / f"{prefix}_{run_id}"
    snapshot = run / 'snapshot'
    (snapshot / 'data').mkdir(parents=True)
    for name in ['evaluate_emobench.py', 'emobench_api.py']:
        shutil.copyfile(HERE / name, snapshot / name)
    shutil.copytree(HERE / 'emobench_official', snapshot / 'emobench_official')
    config = read(snapshot / 'emobench_official/config.json')
    data, audit = {}, {'counts': {}, 'categories': {}, 'validation': 'passed'}
    for task in args.tasks:
        src = args.data_dir / (task + '.jsonl')
        shutil.copyfile(src, snapshot / 'data' / src.name)
        rows = [json.loads(l) for l in src.read_text(encoding='utf-8').splitlines() if l.strip()]
        seen = set()
        for sample in rows:
            key = (sample['language'], str(sample['qid']))
            if key in seen or sample['language'] not in ('zh', 'en'):
                raise ValueError(f'duplicate or invalid sample {task}: {key}')
            seen.add(key)
            fields = [('choices', 'label')] if task == 'EA' else [('emotion_choices', 'emotion_label'), ('cause_choices', 'cause_label')]
            for choices, label in fields:
                values = sample[choices]
                if not 2 <= len(values) <= 26 or len(set(values)) != len(values) or values.count(sample[label]) != 1:
                    raise ValueError(f'invalid choices/label {task}: {key}')
        qsets = {lang: {str(r['qid']) for r in rows if r['language'] == lang} for lang in args.languages}
        if len({tuple(sorted(ids)) for ids in qsets.values()}) != 1 or any(not ids for ids in qsets.values()):
            raise ValueError(f'missing paired bilingual qids: {task}')
        qids = sorted(next(iter(qsets.values())), key=lambda x: int(x) if x.isdigit() else x)
        rng = random.Random(f'{args.seed}:{task}')
        rng.shuffle(qids)
        selected = set(qids[:args.limit] if args.limit else qids)
        data[task] = [r for r in rows if r['language'] in args.languages and str(r['qid']) in selected]
        audit['counts'][task] = dict(Counter(r['language'] for r in rows))
        audit['categories'][task] = dict(Counter(r.get('category', r.get('coarse_category')) for r in rows if r['language'] == 'en'))
    cases = []
    for task in args.tasks:
        for sample in data[task]:
            fields = {'answer': ('choices', 'label')} if task == 'EA' else {'answer_q1': ('emotion_choices', 'emotion_label'), 'answer_q2': ('cause_choices', 'cause_label')}
            for repeat in range(args.repeats):
                maps, labels, options = {}, {}, {}
                for key, (choices, label) in fields.items():
                    indices = list(range(len(sample[choices])))
                    if args.shuffle_options:
                        random.Random(f'{args.seed}:{task}:{sample["language"]}:{sample["qid"]}:{repeat}:{key}').shuffle(indices)
                    maps[key] = {LETTERS[i]: LETTERS[original] for i, original in enumerate(indices)}
                    labels[key] = LETTERS[sample[choices].index(sample[label])]
                    options[key] = [sample[choices][i] for i in indices]
                cases.append({'trial_id': f'trial_{len(cases):06d}', 'sample_id': f'{task}:{sample["qid"]}',
                              'task': task, 'language': sample['language'], 'repeat': repeat,
                              'category': sample.get('category', sample.get('coarse_category')),
                              'fine_category': sample.get('finegrained_category'), 'question_type': sample.get('question type'),
                              'labels': labels, 'maps': maps, 'original_data': sample, 'cot': args.cot,
                              'request': {'botId': args.bot_id, 'content': prompt(sample, task, config, options, args.cot),
                                          'isStream': True, 'returnTts': False, 'courseProgressId': 0}})
    # Interleave tasks/languages to avoid a long single-language phase.
    random.Random(args.seed).shuffle(cases)
    write_json(run / 'plan.json', cases)
    write_json(run / 'data_audit.json', audit)
    hashes = {str(p.relative_to(run)): digest(p) for p in snapshot.rglob('*') if p.is_file()}
    hashes.update({name: digest(run / name) for name in ['plan.json', 'data_audit.json']})
    manifest = {'created_at': now(), 'benchmark': 'EmoBench', 'script_version': VERSION,
                'bot_id': args.bot_id, 'bot_name': args.bot_name, 'base_url': args.base_url.rstrip('/'),
                'tasks': args.tasks, 'languages': args.languages, 'repeats': args.repeats,
                'seed': args.seed, 'cot': args.cot, 'shuffle_options': args.shuffle_options,
                'planned_trials': len(cases), 'selected_question_languages': sum(len(x) for x in data.values()),
                'workers': args.workers, 'interval': args.interval, 'timeout': args.timeout,
                'max_attempts': args.max_attempts, 'max_consecutive_errors': args.max_consecutive_errors,
                'summary_every': args.summary_every, 'verify_tls': not args.insecure,
                'user_namespace': 'emo_eval_' + run_id,
                'credentials_module': str(args.credentials_module.resolve()),
                'model_version': args.model_version, 'harness_version': args.harness_version,
                'generation_parameters': 'backend defaults, not exposed by agent API; official API example uses temperature=0.6',
                'context_policy': 'unique user per trial; clear and verify before every attempt',
                'scoring': 'EA: exact answer; EU: emotion AND cause correct; invalid/error counted wrong',
                'protocol_differences': ['official system instruction carried in user content',
                                         'platform model/generation parameters are not fixed by this client',
                                         'three repeats are saved/scored separately; plurality is auxiliary',
                                         'duplicate JSON keys rejected; invalid format is not retried for a better answer'],
                'source_hashes': hashes, 'official_provenance': read(snapshot / 'emobench_official/provenance.json'),
                'environment': {'python': sys.version, 'platform': platform.platform(), 'requests': importlib.metadata.version('requests')},
                'invocation': sys.argv, 'holdout_status': 'evaluation data; do not train or tune prompts on these samples'}
    write_json(run / 'manifest.json', manifest)
    return run, manifest, cases


def evaluate_one(client, case, run, manifest, user_id):
    directory = run / 'trials' / case['trial_id']
    directory.mkdir(parents=True, exist_ok=True)
    result = {k: case[k] for k in ['trial_id', 'sample_id', 'task', 'language', 'repeat', 'category', 'fine_category', 'question_type', 'labels', 'maps']}
    result.update(user_id=user_id, status='request_error', correct=False, strict_format=False,
                  reply='', prediction_original={}, component_correct={}, attempts=[])
    existing = [int(p.name.split('_')[1]) for p in directory.glob('attempt_*') if p.is_dir()]
    offset = max(existing, default=0)
    started = time.monotonic()
    for i in range(1, manifest['max_attempts'] + 1):
        target = directory / f'attempt_{offset+i:03d}'
        target.mkdir()
        info = {'number': offset+i, 'started_at': now(), 'stage': 'authenticate', 'status': 'error'}
        try:
            if not client.token:
                client.authenticate()
            info['stage'] = 'clear_context'
            clear = client.call('POST', '/open/chat/clearContext', target, 'clear', payload={'botId': manifest['bot_id'], 'courseProgressId': 0})
            if not isinstance(clear, dict) or clear.get('role') != 'flush_context':
                raise ProtocolError('clearContext missing flush_context')
            params = {'botId': manifest['bot_id'], 'courseProgressId': 0, 'onlyLastSession': 'true', 'pageNum': 0, 'pageSize': 100}
            info['stage'] = 'verify_context'
            before = client.call('GET', '/open/chat/context', target, 'context_before', params=params)
            if not isinstance(before, dict) or not isinstance(before.get('content'), list) or any(x.get('role') in ('user', 'role') for x in before['content']):
                raise ProtocolError('context not empty after clear; question blocked')
            info['stage'] = 'chat'
            reply, metadata = client.call('POST', '/open/chat/completions', target, 'chat', payload=case['request'], chat=True)
            if reply == '内容生成状态失败，请稍后重试':
                raise APIError(reply)
            result.update(reply=reply, response_metadata=metadata, **score(reply, case))
            info['status'] = 'received'
            try:
                after = client.call('GET', '/open/chat/context', target, 'context_after', params=params)
                messages = after['content']
                if any(sum(x.get('role') == role for x in messages) != 1 for role in ['user', 'role']):
                    raise ProtocolError('post-chat history is not exactly one user and one reply')
                result['response_sources'] = sorted({str(x['responseSource']) for x in messages if x.get('responseSource')})
            except Exception as exc:
                info['audit_error'] = f'{type(exc).__name__}: {exc}'
        except Exception as exc:
            # Auth exceptions can include raw HTTP URLs but never credential payloads/tokens.
            info['error'] = f'{type(exc).__name__}: {exc}'
            result['error'] = info['error']
            if getattr(getattr(exc, 'response', None), 'status_code', None) == 401:
                client.token = None
        result['attempts'].append(info)
        write_json(target / 'outcome.json', info)
        if info['status'] == 'received':
            result.pop('error', None)
            break
        if i < manifest['max_attempts']:
            time.sleep(min(2 ** i, 8))
    result.update(elapsed_seconds=time.monotonic() - started, finished_at=now())
    write_json(directory / 'result.json', result)
    return result


def metrics(rows):
    n = len(rows)
    eu = [r for r in rows if r['task'] == 'EU']
    return {'count': n, 'correct': sum(r['correct'] for r in rows),
            'accuracy': sum(r['correct'] for r in rows) / n if n else None,
            'request_errors': sum(r['status'] == 'request_error' for r in rows),
            'invalid_answers': sum(r['status'] == 'invalid_answer' for r in rows),
            'strict_format_rate': sum(r['strict_format'] for r in rows) / n if n else None,
            'emotion_accuracy': sum(r['component_correct'].get('answer_q1', False) for r in eu) / len(eu) if eu else None,
            'cause_accuracy': sum(r['component_correct'].get('answer_q2', False) for r in eu) / len(eu) if eu else None}


def summarize(run, manifest, cases, rows, status):
    rows = sorted(rows, key=lambda r: r['trial_id'])
    summary = {'updated_at': now(), 'run_status': status, 'planned_trials': len(cases),
               'completed_trials': len(rows), 'trials': metrics(rows),
               'attempt_errors': sum(a['status'] == 'error' for r in rows for a in r['attempts']),
               'context_after_audit_errors': sum(bool(a.get('audit_error')) for r in rows for a in r['attempts']),
               'task_language': {}}
    groups = defaultdict(list)
    for r in rows:
        groups[(r['task'], r['language'], r['sample_id'])].append(r)
    votes = []
    for (task, lang, sid), rs in groups.items():
        if len(rs) != manifest['repeats']:
            continue
        counts = Counter(tuple(sorted(r['prediction_original'].items())) for r in rs if r['status'] == 'ok')
        winners = [p for p, count in counts.items() if count == max(counts.values())] if counts else []
        prediction = dict(winners[0]) if len(winners) == 1 else None
        votes.append({'task': task, 'language': lang, 'sample_id': sid, 'labels': rs[0]['labels'],
                      'prediction': prediction, 'correct': prediction == rs[0]['labels'],
                      'valid_votes': sum(counts.values()), 'votes': [{'answer': dict(k), 'count': v} for k, v in counts.items()]})
    for task in manifest['tasks']:
        summary['task_language'][task] = {}
        for lang in manifest['languages']:
            rs = [r for r in rows if r['task'] == task and r['language'] == lang]
            expected = sum(c['task'] == task and c['language'] == lang for c in cases) // manifest['repeats']
            rounds = {str(i+1): metrics([r for r in rs if r['repeat'] == i]) for i in range(manifest['repeats'])}
            completed = [v['accuracy'] for v in rounds.values() if v['count'] == expected and expected]
            categories = {cat: metrics([r for r in rs if r['category'] == cat]) for cat in sorted({r['category'] for r in rs})}
            fine = {cat: metrics([r for r in rs if r['fine_category'] == cat]) for cat in sorted({r['fine_category'] for r in rs if r['fine_category']})}
            types = {cat: metrics([r for r in rs if r['question_type'] == cat]) for cat in sorted({r['question_type'] for r in rs if r['question_type']})}
            vs = [v for v in votes if v['task'] == task and v['language'] == lang]
            summary['task_language'][task][lang] = {'overall': metrics(rs), 'rounds': rounds,
                'complete_rounds': len(completed), 'mean_accuracy': statistics.mean(completed) if completed else None,
                'sample_std_accuracy': statistics.stdev(completed) if len(completed) > 1 else None,
                'categories': categories, 'fine_categories': fine, 'question_types': types,
                'auxiliary_vote': {'questions': len(vs), 'correct': sum(v['correct'] for v in vs),
                                   'accuracy': sum(v['correct'] for v in vs) / len(vs) if vs else None,
                                   'ties_or_no_answer': sum(v['prediction'] is None for v in vs)}}
    write_json(run / 'summary.json', summary)
    write_json(run / 'question_votes.json', votes)
    # Official-shaped rows use original option letters even in shuffle experiments.
    for task in manifest['tasks']:
        for repeat in range(manifest['repeats']):
            official = []
            for row in rows:
                if row['task'] != task or row['repeat'] != repeat:
                    continue
                base = {'qid': row['sample_id'].split(':', 1)[1], 'lang': row['language']}
                pred = row['prediction_original']
                if task == 'EA':
                    base.update(category=row['category'], label=row['labels']['answer'], answer=pred.get('answer') or '')
                else:
                    base.update(coarse_category=row['category'], finegrained_category=row['fine_category'],
                                emo_label=row['labels']['answer_q1'], emo_answer=pred.get('answer_q1') or '',
                                cause_label=row['labels']['answer_q2'], cause_answer=pred.get('answer_q2') or '')
                official.append(base)
            target = run / 'official_format' / task / f'round_{repeat+1}.jsonl'
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_suffix('.tmp')
            temp.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in official), encoding='utf-8')
            temp.replace(target)

    by_id = {c['trial_id']: c for c in cases}
    bad = [{**r, 'case': by_id[r['trial_id']], 'evidence_dir': 'trials/' + r['trial_id']}
           for r in rows if not r['correct'] or not r['strict_format'] or any(a.get('audit_error') for a in r['attempts'])]
    for name, values in [('responses.jsonl', rows), ('badcases.jsonl', bad)]:
        target = run / name
        tmp = target.with_suffix('.tmp')
        tmp.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values), encoding='utf-8')
        tmp.replace(target)
    write_json(run / 'review_queue.json', [{'trial_id': r['trial_id'], 'task': r['task'], 'language': r['language'],
        'category': r['category'], 'root_cause': 'pending_review', 'owner': None, 'due_date': None,
        'evidence_dir': r['evidence_dir']} for r in bad])
    fmt = lambda value: 'N/A' if value is None else f'{value*100:.2f}%'
    lines = ['# EmoBench 独立评测报告', '', f"状态：{status}；完成{len(rows)}/{len(cases)}；botId={manifest['bot_id']}。", '',
             '| 任务 | 语言 | 答对/次数 | 三轮/多轮均值 | 样本标准差（百分点） | EU情绪准确率 | EU原因准确率 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for task, langs in summary['task_language'].items():
        for lang, value in langs.items():
            metric = value['overall']
            std = value['sample_std_accuracy']
            lines.append(f"| {task} | {lang} | {metric['correct']}/{metric['count']} | {fmt(value['mean_accuracy'])} | {std*100 if std is not None else 'N/A'} | {fmt(metric['emotion_accuracy'])} | {fmt(metric['cause_accuracy'])} |")
    lines += ['', '| 任务 | 语言 | 轮次 | 答对/次数 | 准确率 |', '|---|---|---:|---:|---:|']
    for task, langs in summary['task_language'].items():
        for lang, value in langs.items():
            for repeat, metric in value['rounds'].items():
                lines.append(f"| {task} | {lang} | {repeat} | {metric['correct']}/{metric['count']} | {fmt(metric['accuracy'])} |")
    lines += ['', 'EU主成绩要求情绪和原因同时正确；情绪/原因分数只是辅助诊断。EA主成绩要求所选动作/回应正确。全局合并准确率不是官方EU/EA分数的替代。',
              '', '默认不打乱选项，使用官方提示词和JSON字段；本客户端将系统指令合并进用户消息，后台生成参数无法锁定，不宣称完全复现论文设置。',
              '', '多轮按次平均为主成绩；投票为辅助成绩，EU按完整答案对投票而非分别拼接情绪/原因。并列计错。',
              '', '## 完整分类、轮次和投票', '', '```json', json.dumps(summary['task_language'], ensure_ascii=False, indent=2), '```',
              '', '## 运行配置与限制', '', '```json', json.dumps({k: manifest[k] for k in ['script_version', 'model_version', 'harness_version', 'seed', 'cot', 'shuffle_options', 'context_policy', 'protocol_differences']}, ensure_ascii=False, indent=2), '```',
              '', '所有样本/错误和请求证据保存在plan.json、responses.jsonl、badcases.jsonl、trials/；输入/提示词/代码及官方来源在snapshot/和manifest.json。未自动公开样本或提交榜单。']
    (run / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', nargs='+', choices=['EU', 'EA'], default=['EU', 'EA'])
    parser.add_argument('--languages', nargs='+', choices=['zh', 'en'], default=['zh', 'en'])
    parser.add_argument('--limit', type=int, default=0, help='每任务每语言的场景数；0=全部200个，双语抽取相同qid')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--cot', action='store_true')
    parser.add_argument('--shuffle-options', action='store_true', help='默认保持官方选项顺序；启用后属于额外实验')
    parser.add_argument('--interval', type=float, default=0)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--max-attempts', type=int, default=2)
    parser.add_argument('--max-consecutive-errors', type=int, default=5)
    parser.add_argument('--summary-every', type=int, default=200)
    parser.add_argument('--bot-id', type=int, default=1030)
    parser.add_argument('--bot-name', default='李言老师-bench测试')
    parser.add_argument('--model-version', default='unreported')
    parser.add_argument('--harness-version', default='unreported')
    parser.add_argument('--base-url', default=os.getenv('LINGX_BASE_URL', 'https://www.ai-role.cn'))
    parser.add_argument('--credentials-module', type=Path, default=HERE.parent / 'bot_chat_client.py')
    parser.add_argument('--data-dir', type=Path, default=HERE / 'Emobench')
    parser.add_argument('--output-dir', type=Path, default=None, help='输出根目录；默认按EmoBench、智能体名称和ID命名')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--report-only', type=Path)
    parser.add_argument('--insecure', action='store_true')
    args = parser.parse_args(argv)
    if args.limit < 0 or args.interval < 0 or min(args.repeats, args.workers, args.timeout, args.max_attempts, args.summary_every, args.max_consecutive_errors, args.bot_id) <= 0:
        parser.error('counts/timeouts must be positive; limit/interval may be zero')
    if len(set(args.tasks)) != len(args.tasks) or len(set(args.languages)) != len(args.languages):
        parser.error('tasks/languages must not repeat')
    if args.resume and args.report_only or args.dry_run and (args.resume or args.report_only):
        parser.error('dry-run/resume/report-only are mutually exclusive')
    if args.resume or args.report_only:
        run = (args.resume or args.report_only).resolve()
        manifest, cases = read(run / 'manifest.json'), read(run / 'plan.json')
        if digest(__file__) != manifest['source_hashes']['snapshot/evaluate_emobench.py']:
            raise ValueError('use this run\'s snapshot/evaluate_emobench.py to resume/rebuild')
        for name, expected in manifest['source_hashes'].items():
            if digest(run / name) != expected:
                raise ValueError(f'changed snapshot/input: {name}')
    else:
        run, manifest, cases = prepare(args)
    with (run / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('another process is using this run directory')
        rows = [read(run / 'trials' / c['trial_id'] / 'result.json') for c in cases if (run / 'trials' / c['trial_id'] / 'result.json').exists()]
        if any(r['trial_id'] not in {c['trial_id'] for c in cases} for r in rows):
            raise ValueError('unexpected trial ID')
        print(f"RUN_DIR={run}\n计划{len(cases)}次；目标{manifest['bot_id']}；并发{manifest['workers']}", flush=True)
        if args.dry_run or args.report_only:
            summarize(run, manifest, cases, rows, 'prepared' if args.dry_run else 'complete' if len(rows) == len(cases) else 'partial')
            write_json(run / 'artifact_index.json', {str(p.relative_to(run)): digest(p) for p in run.rglob('*') if p.is_file() and p.name != 'artifact_index.json'})
            return 0
        defaults = import_file('emobench_credentials', manifest['credentials_module'])
        key = os.getenv('LINGX_API_KEY', defaults.DEFAULT_API_KEY)
        secret = os.getenv('LINGX_API_SECRET', defaults.DEFAULT_API_SECRET)
        def new_client(uid):
            return Client(manifest['base_url'], key, secret, uid, manifest['verify_tls'], manifest['timeout'])
        def execute(case):
            uid = 'emo_' + hashlib.sha256((manifest['user_namespace'] + ':' + case['trial_id']).encode()).hexdigest()[:40]
            c = new_client(uid)
            try:
                result = evaluate_one(c, case, run, manifest, uid)
                time.sleep(manifest['interval'])
                return result
            finally:
                c.session.close()
        status, exit_code, failures = 'running', 0, 0
        append(run / 'execution_log.jsonl', {'event': 'start', 'at': now(), 'already_completed': len(rows)})
        try:
            check = new_client(manifest['user_namespace'])
            try:
                check.authenticate()
                bots = check.call('GET', '/open/bot/list', run / 'sessions' / uuid4().hex, 'bots')
                if not any(str(b.get('id')) == str(manifest['bot_id']) for b in bots):
                    raise APIError('target bot not accessible with these credentials')
            finally:
                check.session.close()
            completed = {r['trial_id'] for r in rows}
            todo = iter(c for c in cases if c['trial_id'] not in completed)
            state_path = run / 'adaptive_concurrency.json'
            state = read(state_path) if state_path.exists() else {}
            active_workers = max(1, min(manifest['workers'], state.get('workers', manifest['workers'])))
            pool = ThreadPoolExecutor(max_workers=manifest['workers'])
            pending = {}
            def submit():
                case = next(todo, None)
                if case is not None:
                    pending[pool.submit(execute, case)] = case
            try:
                for _ in range(active_workers):
                    submit()
                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        case = pending.pop(future)
                        result = future.result()
                        rows.append(result)
                        print(f"[{len(rows)}/{len(cases)}] {case['task']} {case['language']} {case['sample_id']} #{case['repeat']+1} {result['status']} correct={result['correct']}", flush=True)
                        if len(rows) == 1 or len(rows) % manifest['summary_every'] == 0:
                            summarize(run, manifest, cases, rows, 'running')
                        failures = failures + 1 if result['status'] == 'request_error' else 0
                        if failures >= manifest['max_consecutive_errors']:
                            previous_workers = active_workers
                            active_workers = max(1, active_workers // 2)
                            event = {'event': 'reduce_concurrency', 'at': now(),
                                     'previous_workers': previous_workers, 'workers': active_workers,
                                     'reason': 'consecutive final request failures', 'backoff_seconds': 30}
                            write_json(state_path, event)
                            append(run / 'execution_log.jsonl', event)
                            print(f'连续请求失败：并发 {previous_workers} -> {active_workers}；立即继续', flush=True)
                            failures = 0
                    # Drain outstanding work naturally; refill only up to the reduced limit.
                    while len(pending) < active_workers:
                        before = len(pending)
                        submit()
                        if len(pending) == before:
                            break
            finally:
                for future in pending:
                    future.cancel()
                pool.shutdown(wait=True)
            status = 'complete'
        except KeyboardInterrupt:
            status, exit_code = 'interrupted', 130
        except Exception as exc:
            status, exit_code = 'failed', 1
            append(run / 'execution_log.jsonl', {'event': 'fatal', 'at': now(), 'error': f'{type(exc).__name__}: {exc}'})
            print(f'运行失败：{type(exc).__name__}: {exc}', file=sys.stderr)
        finally:
            rows = [read(run / 'trials' / c['trial_id'] / 'result.json') for c in cases if (run / 'trials' / c['trial_id'] / 'result.json').exists()]
            summarize(run, manifest, cases, rows, status)
            append(run / 'execution_log.jsonl', {'event': status, 'at': now(), 'completed_trials': len(rows)})
            write_json(run / 'artifact_index.json', {str(p.relative_to(run)): digest(p) for p in run.rglob('*') if p.is_file() and p.name != 'artifact_index.json'})
            print(f"结束状态={status}；报告={run / 'report.md'}", flush=True)
        return exit_code


if __name__ == '__main__':
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    sys.exit(main() or 0)
