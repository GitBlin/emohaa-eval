#!/usr/bin/env python3
"""Measure client-observed latency using frozen ToMBench/EmoBench plans. No calls without --execute."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import uuid
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from emobench_api import Client, APIError, ProtocolError, sse_events, unpack, write_json, import_file


def measure(client, payload, directory):
    result = {'attempted': True, 'success': False, 'first_text_seconds': None,
              'complete_seconds': None, 'reply': '', 'error_type': None}
    events, pieces = [], []
    write_json(directory / 'request.json', {'url': client.base_url + '/open/chat/completions', 'payload': payload})
    start = time.perf_counter()
    try:
        with client.session.post(client.base_url + '/open/chat/completions', json=payload,
             headers={'Authorization': 'Bearer ' + client.token}, stream=True,
             timeout=(10, client.timeout), verify=client.verify) as response:
            result.update(headers_seconds=time.perf_counter()-start, http_status=response.status_code,
                          request_id=response.headers.get('X-Request-Id'), content_type=response.headers.get('Content-Type'))
            response.raise_for_status()
            if 'text/event-stream' not in response.headers.get('Content-Type', '').lower():
                raise ProtocolError('Non-streaming response: no valid streaming TTFT measurement')
            finished = False
            # One-byte reads avoid waiting for a large client buffer to fill. JSON/events are
            # persisted after timing completes; CPU overhead is included in client latency.
            for event_type, raw in sse_events(response.iter_lines(chunk_size=1)):
                elapsed = time.perf_counter()-start
                if elapsed > max(120, client.timeout*3):
                    raise TimeoutError('Total stream deadline exceeded')
                if raw.strip() == '[DONE]':
                    finished = True
                    result['end_event_seconds'] = elapsed
                    events.append({'elapsed_seconds': elapsed, 'event': event_type, 'data': '[DONE]'})
                    break
                obj = json.loads(raw)
                if isinstance(obj, str):
                    obj = json.loads(obj)
                elapsed = time.perf_counter()-start
                events.append({'elapsed_seconds': elapsed, 'event': event_type, 'data': obj})
                if not isinstance(obj, dict):
                    raise ProtocolError('SSE object expected')
                choice = (obj.get('choices') or [{}])[0]
                delta = choice.get('delta') or {}
                if event_type == 'error' or obj.get('model') == 'error' or obj.get('success') is False or obj.get('error'):
                    raise APIError('Server error event; see events.jsonl')
                typ = obj.get('type', '') or ''
                excluded = typ.startswith(('meta', 'tts', 'reasoning', 'thinking', 'heartbeat', 'progress'))
                content = delta.get('content')
                if not excluded and isinstance(content, str) and content:
                    if content.strip() in ('内容生成状态失败，请稍后重试', '发送内容长度不能超过5000'):
                        raise APIError('Known platform error text')
                    if content.strip() and result['first_text_seconds'] is None:
                        result['first_text_seconds'] = elapsed
                    pieces.append(content)
                if choice.get('finishReason', choice.get('finish_reason')) == 'stop':
                    finished = True
                    result['end_event_seconds'] = elapsed
                    break
            if not finished:
                raise ProtocolError('Missing normal stream end')
            if not ''.join(pieces).strip():
                raise ProtocolError('Empty answer')
            result.update(success=True, complete_seconds=result['end_event_seconds'])
    except Exception as exc:
        result['error_type'] = type(exc).__name__
    finally:
        result['terminated_seconds'] = time.perf_counter()-start
        result['reply'] = ''.join(pieces).strip()
        result['output_characters'] = len(result['reply'])
        (directory/'events.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in events))
        write_json(directory/'timing.json', result)
    return result


def quantile(values, p):
    if not values:
        return None
    a=sorted(values); h=(len(a)-1)*p; lo=int(h); hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(h-lo)


def summary(rows):
    attempts=[r for r in rows if r.get('attempted')]
    ok=[r for r in attempts if r['success']]
    first=[r['first_text_seconds'] for r in attempts if r['first_text_seconds'] is not None]
    complete=[r['complete_seconds'] for r in ok]
    n=len(attempts)
    return {'selected_cases':len(rows),'chat_attempts':n,'setup_failures':len(rows)-n,
            'successful_chats':len(ok),'failed_chats':n-len(ok),'success_rate':len(ok)/n if n else None,
            'first_text':{'n':len(first),'p50_seconds':quantile(first,.5),'p95_seconds':quantile(first,.95)},
            'complete':{'n':len(complete),'p50_seconds':quantile(complete,.5),'p95_seconds':quantile(complete,.95)},
            'successful_and_first_text_within':{str(t):sum(r['first_text_seconds'] is not None and r['first_text_seconds']<=t for r in ok)/n if n else None for t in (1,2,3,5)},
            'answer_format_valid':sum(r.get('score',{}).get('status')=='ok' for r in rows),
            'correct_answers':sum(bool(r.get('score',{}).get('correct')) for r in rows)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',choices=['tombench','emobench'],required=True)
    p.add_argument('--source-run',type=Path,help='existing run with plan.json and frozen scorer')
    p.add_argument('--bot-id',type=int,default=1030)
    p.add_argument('--samples-per-group',type=int,default=2,help='per language for ToM; per task/language for Emo; 0 selects all repeat=0 cases')
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--timeout',type=float,default=90)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.samples_per_group<0 or a.workers<1 or a.timeout<=0 or a.bot_id<1:p.error('invalid arguments')
    patterns={'tombench':'ToMBench*1030/*20261112T025335Z*/manifest.json','emobench':'EmoBench*1030/*20261112T111842Z*/manifest.json'}
    source=a.source_run.resolve() if a.source_run else next(HERE.glob(patterns[a.benchmark])).parent
    cases=json.loads((source/'plan.json').read_text());groups={}
    for c in cases:
        if c['repeat']!=0:continue
        k=c['language'] if a.benchmark=='tombench' else c['task']+'_'+c['language']
        groups.setdefault(k,[]).append(c)
    selected=[];rng=random.Random(a.seed)
    for k,items in sorted(groups.items()):
        items=sorted(items,key=lambda c:c['trial_id']);rng.shuffle(items)
        for c in (items[:a.samples_per_group] if a.samples_per_group else items):
            c=dict(c);c['group']=k;c['request']=dict(c['request'],botId=a.bot_id,isStream=True,returnTts=False);selected.append(c)
    print(json.dumps({'benchmark':a.benchmark,'bot_id':a.bot_id,'groups':list(groups),'selected':len(selected),'workers':a.workers,'execute':a.execute},ensure_ascii=False),flush=True)
    if not a.execute:return
    # Read only credential constants, do not execute the credential-bearing module.
    constants={}
    for node in ast.parse((HERE.parent/'bot_chat_client.py').read_text()).body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            for name in node.targets:
                if isinstance(name,ast.Name):constants[name.id]=node.value.value
    import os
    base=os.getenv('LINGX_BASE_URL',constants.get('DEFAULT_BASE_URL','https://www.ai-role.cn'))
    key=os.getenv('LINGX_API_KEY',constants.get('DEFAULT_API_KEY'));secret=os.getenv('LINGX_API_SECRET',constants.get('DEFAULT_API_SECRET'))
    if not key or not secret:raise ValueError('Missing API credentials')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    run=HERE/'efficiency_evaluations'/f'{a.benchmark}_{a.bot_id}_efficiency_{stamp}';run.mkdir(parents=True)
    scorer_name='evaluate_liyan.py' if a.benchmark=='tombench' else 'evaluate_emobench.py'
    scorer_path=source/'snapshot'/scorer_name
    scorer=import_file('efficiency_scorer',scorer_path)
    write_json(run/'plan.json',selected)
    for path in [Path(__file__),HERE/'emobench_api.py',scorer_path]:
        (run/path.name).write_bytes(path.read_bytes())
    write_json(run/'manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),'benchmark':a.benchmark,'bot_id':a.bot_id,
      'source_run':str(source),'workers':a.workers,'seed':a.seed,'timeout':a.timeout,'planned':len(selected),
      'retry':'none; each sample uses a fresh user and clear+verify','timing':'chat only; perf_counter; SSE iter_lines chunk_size=1; buffered event logging',
      'quantiles':'linear interpolation','known_limitations':'untyped platform placeholders cannot be distinguished from answer text; platform model version unreported',
      'source_plan_sha256':hashlib.sha256((source/'plan.json').read_bytes()).hexdigest(),
      'code_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),HERE/'emobench_api.py',scorer_path]}})
    print('RUN_DIR='+str(run),flush=True)
    def execute(case):
        d=run/'trials'/case['trial_id'];d.mkdir(parents=True)
        uid='eff_'+uuid.uuid4().hex
        client=Client(base,key,secret,uid,timeout=a.timeout)
        row={'attempted':False,'success':False,'trial_id':case['trial_id'],'group':case['group'],'user_id':uid}
        try:
            client.authenticate()
            clear=client.call('POST','/open/chat/clearContext',d,'clear',payload={'botId':a.bot_id,'courseProgressId':0})
            if clear.get('role')!='flush_context':raise ProtocolError('Clear failed')
            params={'botId':a.bot_id,'courseProgressId':0,'onlyLastSession':'true','pageNum':0,'pageSize':100}
            before=client.call('GET','/open/chat/context',d,'before',params=params)
            if not isinstance(before.get('content'),list) or any(m.get('role') in ('user','role') for m in before['content']):raise ProtocolError('History not empty')
            row.update(measure(client,case['request'],d))
            if row['success']:row['score']=scorer.score(row['reply'],case)
            try:
                after=client.call('GET','/open/chat/context',d,'after',params=params)
                row['history_one_pair']=all(sum(m.get('role')==r for m in after['content'])==1 for r in ('user','role'))
            except Exception as e:row['audit_error']=type(e).__name__
        except Exception as e:row['setup_or_scoring_error']=type(e).__name__
        finally:client.session.close()
        write_json(d/'result.json',row)
        print(f"{case['group']} {case['trial_id']} success={row['success']} ttft={row.get('first_text_seconds')} complete={row.get('complete_seconds')}",flush=True)
        return row
    with ThreadPoolExecutor(max_workers=a.workers) as pool:rows=list(pool.map(execute,selected))
    stats={'overall':summary(rows),'by_group':{k:summary([r for r in rows if r['group']==k]) for k in groups}}
    write_json(run/'summary.json',stats)
    (run/'report.md').write_text('# 效率小样本评测\n\n'+f'智能体：{a.bot_id}；bench：{a.benchmark}；并发：{a.workers}。无自动重试。\n\n仅代表本次样本，P95不能作为稳定生产结论。传输成功与答题正确分开。\n\n```json\n'+json.dumps(stats,ensure_ascii=False,indent=2)+'\n```\n')
    print(json.dumps(stats['overall'],ensure_ascii=False,indent=2))
    return 0 if all(r['success'] for r in rows) else 2

if __name__=='__main__':sys.exit(main())
