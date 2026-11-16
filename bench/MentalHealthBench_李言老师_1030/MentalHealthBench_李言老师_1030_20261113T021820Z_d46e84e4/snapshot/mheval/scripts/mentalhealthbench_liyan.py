#!/usr/bin/env python3
"""Audited ai-role adaptation of the local MentalHealthBench harness; default is plan-only."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import statistics
import sys
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH/'PsiArena'))
spec = importlib.util.spec_from_file_location('mh_original', ROOT/'tasks/quality/mentalhealthbench/harness.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def serialize_prefix(messages):
    if not messages or messages[-1]['role'] != 'user':
        raise ValueError('Expected a conversation ending in user')
    if any(m['role'] not in ('system','user','assistant') or not isinstance(m['content'],str) for m in messages):
        raise ValueError('Unsupported message schema')
    return ('Continue the supplied conversation by writing ONLY the next assistant reply. '
            'The JSON array preserves the original message order and roles, including system instructions. '
            'Do not regenerate prior replies, describe this evaluation, or score yourself. '
            'Respond in the language appropriate to the conversation.\n<conversation_json>\n'
            +json.dumps(messages,ensure_ascii=False)+'\n</conversation_json>')


def parse_grade(text):
    match = re.search(r'\{.*\}',text,re.S)
    value = json.loads(match.group(0) if match else text)
    if set(value) != {'explanation','satisfaction'} or type(value['satisfaction']) is not int or value['satisfaction'] not in (0,1) or not isinstance(value['explanation'],str):
        raise ValueError('Expected explanation and integer satisfaction 0/1')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--indices',type=int,nargs='+',default=[4,6])
    p.add_argument('--all',action='store_true')
    p.add_argument('--n-samples',type=int,default=4)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    data=BENCH/'MentalHealthBench/mentalhealthbench_eval.jsonl'
    tasks=[json.loads(line) for line in data.read_text().splitlines()]
    indices=list(range(len(tasks))) if a.all else a.indices
    if a.n_samples<1 or a.workers<1 or len(set(indices))!=len(indices) or any(i<0 or i>=len(tasks) for i in indices):p.error('Invalid indices, samples or workers')
    selected=[tasks[i] for i in indices]
    def input_size(task):
        # AiRoleSession adds this exact first-turn wrapper even with no system entry.
        content='<咨询行为要求>\n\n</咨询行为要求>\n'+serialize_prefix(task['conversation']['messages'])
        return len(content.encode('utf-16-le'))//2
    too_long=[i for i in indices if input_size(tasks[i])>5000]
    if too_long:
        p.error(f'{len(too_long)} selected cases exceed the observed 5000-character platform limit; no truncation is permitted. Example indices: {too_long[:10]}')
    plan={'indices':indices,'cases':len(selected),'samples_per_case':a.n_samples,'workers':a.workers,
          'target_calls':len(selected)*a.n_samples,'judge_calls':sum(len(t['rubric_items']) for t in selected)*a.n_samples,
          'adaptation':'fixed history serialized in a single user content; hidden platform system remains; no simulated user',
          'dataset_cases_exceeding_limit':sum(input_size(t)>5000 for t in tasks),
          'canary_policy':'only conversation.messages and criterion_text sent; canary_string never sent'}
    if not a.execute:print(json.dumps(plan,ensure_ascii=False,indent=2));return
    from psiarena.config import get_settings,chat
    from psiarena.ai_role import counselor_session, credentials
    from psiarena.ai_role_transport import write_json, append_json, now
    from psiarena.runtime import run_log
    settings=get_settings();rc=settings.roles['judge']
    if settings.counselor_provider!='ai_role' or settings.roles['counselor'].model!='ai-role-bot-1030':p.error('Expected ai-role bot 1030')
    if rc.model!='deepseek-v4.1-flash-1017' or rc.thinking!='enabled' or rc.reasoning_effort!='medium':p.error('Expected DeepSeek Flash, thinking enabled, reasoning_effort medium')
    credentials()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    run=BENCH/'MentalHealthBench_李言老师_1030'/('MentalHealthBench_李言老师_1030_'+stamp)
    run.mkdir(parents=True)
    source_paths=[Path(__file__),ROOT/'tasks/quality/mentalhealthbench/harness.py',ROOT/'tasks/quality/mentalhealthbench/grader_prompt.txt',ROOT/'tasks/quality/mentalhealthbench/mentalhealthbench.yaml',ROOT/'mheval/native.py']
    source_paths+=list((BENCH/'PsiArena/psiarena').glob('*.py'))
    hashes={}
    for src in source_paths:
        relative=src.relative_to(BENCH);dest=run/'snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
        hashes[str(relative)]=hashlib.sha256(src.read_bytes()).hexdigest()
    write_json(run/'manifest.json',{'started_at':now(),'plan':plan,'bot_id':1030,'judge':{'model':rc.model,'base_url':rc.base_url,'thinking':rc.thinking,'reasoning_effort':rc.reasoning_effort},'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'source_hashes':hashes,'judge_max_tokens':__import__('os').getenv('PSIARENA_JUDGE_MAX_TOKENS'),'judge_temperature':settings.temperature,'timeout':settings.timeout,
          'scope':'local adaptation; changed judge and serialized roles; not an official comparable score','platform_model_version':'unreported','retry_policy':'no target retry; at most 3 judge format attempts; failed records retained'})
    print('RUN_DIR='+str(run),flush=True)
    def job(index,task,sample):
        directory=run/'cases'/f'{index:04d}'/f'sample_{sample:02d}'
        directory.mkdir(parents=True)
        try:
            with run_log(directory):
                with counselor_session(directory/'memory',f'mhb_{index}_{sample}') as session:
                    completion=session.chat([{'role':'user','content':serialize_prefix(task['conversation']['messages'])}])
                    uid=session.user_id
                write_json(directory/'completion.json',{'case_index':index,'id':task['id'],'sample':sample,'user_id':uid,'completion':completion})
                grades=[]
                for n,item in enumerate(task['rubric_items']):
                    prompt=(original.PROMPT.replace('{TASK_DEFINITION}',original.render(task['conversation']['messages'])).replace('{SAMPLED_TASK_COMPLETION}',completion).replace('{RUBRIC_ITEM_RULE}',item['criterion_text']))
                    for attempt in range(3):
                        text=chat('judge',[{'role':'user','content':prompt}])
                        try:g=parse_grade(text);break
                        except (ValueError,TypeError):
                            if attempt==2:raise
                    grades.append(g)
                    write_json(directory/f'criterion_{n:02d}.json',{'criterion_index':n,'points':item['points'],'behavior_axis':item['behavior_axis'],'grade':g})
                result={'case_index':index,'id':task['id'],'sample':sample,'status':'ok','user_id':uid,'completion':completion,'grades':grades,'score':original.score(task['rubric_items'],[g['satisfaction'] for g in grades])}
        except Exception as exc:
            result={'case_index':index,'id':task['id'],'sample':sample,'status':'error','error_type':type(exc).__name__}
        write_json(directory/'result.json',result)
        return result
    results=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        pending=[pool.submit(job,index,task,k) for index,task in zip(indices,selected) for k in range(a.n_samples)]
        for future in as_completed(pending):
            result=future.result();results.append(result);append_json(run/'samples.jsonl',result)
            print(f'case={result["case_index"]} sample={result["sample"]} status={result["status"]} completed={len(results)}/{len(pending)}',flush=True)
    good=[r for r in results if r['status']=='ok'];complete=len(good)==len(results)
    per_task=defaultdict(list)
    for r in good:per_task[r['id']].append(r['score'])
    task_scores={t['id']:{k:statistics.mean(x[k] for x in per_task[t['id']]) for k in ('clipped','signed','earned','burden')} for t in selected if len(per_task[t['id']])==a.n_samples}
    metrics={k:statistics.mean(v[field] for v in task_scores.values()) if task_scores else None for k,field in [('task_clipped_score','clipped'),('signed_score','signed'),('positive_points_earned','earned'),('normalized_penalty_burden','burden')]}
    breakdown={}
    for field in ('acuity','user_profile','language','has_prior_context'):
        groups=defaultdict(list)
        for t in selected:
            if t['id'] in task_scores:groups[str(t[field])].append(task_scores[t['id']]['clipped'])
        breakdown[field]={k:{'task_clipped_score':statistics.mean(v),'n':len(v)} for k,v in groups.items()}
    axes=defaultdict(list)
    for r in good:
        for axis,value in r['score']['axes'].items():axes[axis].append(value)
    breakdown['behavior_axis']={axis:{**{k:statistics.mean(v[k] for v in vals) for k in vals[0]},'n':len(vals)} for axis,vals in axes.items()}
    usage=defaultdict(int);reasoning_calls=0;judge_calls=0
    for path in (run/'cases').glob('*/*/requests/*/response.json'):
        response=json.loads(path.read_text());u=response.get('usage') or {};judge_calls+=1
        for k in ('prompt_tokens','completion_tokens','total_tokens'):usage[k]+=u.get(k,0)
        rt=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0
        usage['reasoning_tokens']+=rt
        reasoning_calls+=bool(rt or response['choices'][0]['message'].get('reasoning_content'))
    summary={'finished_at':now(),'complete':complete,'n':len(task_scores),'planned_cases':len(selected),'planned_samples':len(results),'successful_samples':len(good),'metrics':metrics if complete else None,'partial_metrics':metrics if not complete else None,'breakdown':breakdown,'errors':[r for r in results if r['status']!='ok'],'judge_calls':judge_calls,'judge_calls_with_reasoning':reasoning_calls,'judge_usage':dict(usage)}
    write_json(run/'results.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('breakdown','errors')},ensure_ascii=False,indent=2))
    if not complete:raise SystemExit(2)

if __name__=='__main__':main()
