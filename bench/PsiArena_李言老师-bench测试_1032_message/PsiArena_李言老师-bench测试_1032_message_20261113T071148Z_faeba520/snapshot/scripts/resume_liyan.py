#!/usr/bin/env python
"""Resume frozen PsiArena artifacts; plan only unless --execute is passed."""
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--run-dir',type=Path,required=True)
 p.add_argument('--workers',type=int,default=4)
 p.add_argument('--execute',action='store_true')
 a=p.parse_args();run=a.run_dir.resolve();m=json.loads((run/'manifest.json').read_text());plan=m['plan']
 if a.workers<1:p.error('workers must be positive')
 for rel,h in m['sha256'].items():
  if hashlib.sha256((run/'snapshot'/rel).read_bytes()).hexdigest()!=h:p.error('Snapshot changed: '+rel)
 # Use frozen evaluation, prompts, scoring, generation and transport.
 sys.path.insert(0,str(ROOT));import psiarena.config as live_config
 live_config.get_settings() # load local credentials before importing frozen modules
 for name in list(sys.modules):
  if name=='psiarena' or name.startswith('psiarena.'):del sys.modules[name]
 sys.path.insert(0,str(run/'snapshot'))
 os.environ['PSIARENA_COUNSELOR_PROVIDER']=m['provider'];os.environ['PSIARENA_AI_ROLE_BOT_ID']=str(m['bot_id'])
 os.environ['PSIARENA_AI_ROLE_CREDENTIAL_FILE']=str(ROOT.parents[1]/'bot_chat_client.py')
 for role,rc in m['roles'].items():
  if role=='counselor':continue
  for field in ('model','base_url','thinking','reasoning_effort'):
   os.environ[f'PSIARENA_{role.upper()}_{field.upper()}']=rc.get(field) or ''
 for field,env in [('temperature','PSIARENA_TEMPERATURE'),('default_max_tokens','PSIARENA_MAX_TOKENS'),('client_max_tokens','PSIARENA_CLIENT_MAX_TOKENS'),('judge_max_tokens','PSIARENA_JUDGE_MAX_TOKENS'),('timeout','PSIARENA_TIMEOUT')]:
  if field in m:os.environ[env]=str(m[field])
 from psiarena.scoring import parse_score_text,parse_section,HEADERS,COUNTS,aggregate
 from psiarena.pipeline import generate_dialogue
 from psiarena.evaluate import evaluate_dialogue
 from psiarena.runtime import run_log
 from psiarena.ai_role_transport import write_json,append_json,now
 from psiarena.config import get_settings
 get_settings()
 def valid(i):
  try:parse_score_text((run/f'scores{i}.txt').read_text(),plan['protocol']);return True
  except (OSError,ValueError):return False
 def full(i):
  d=run/'cards'/f'{i:03d}'
  try:
   progress=json.loads((d/'dialogue_progress.json').read_text())
   text=(run/f'dialogue{i}.txt').read_text()
   return progress['completed_turns']==plan['turns'] and len(text.splitlines())==plan['turns']*2
  except (OSError,ValueError,KeyError):return False
 pending=[i for i in plan['cards'] if not valid(i)]
 print(json.dumps({'completed':len(plan['cards'])-len(pending),'judge_only':[i for i in pending if full(i)],'fresh_session':[i for i in pending if not full(i)],'workers':a.workers,'execute':a.execute},ensure_ascii=False,indent=2),flush=True)
 if not a.execute:return
 with (run/'.resume.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:p.error('Another resume process is active')
  # Detect the original runner, which predates the resume lock.
  import subprocess
  for line in subprocess.check_output(['ps','-eo','args'],text=True).splitlines():
   if line.startswith('python scripts/smoke_liyan.py ') and '--execute' in line:p.error('An original smoke runner is active; stop it before resuming')
  stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
  backup=run/'resume_history'/stamp;backup.mkdir(parents=True)
  shutil.copyfile(__file__,backup/'resume_liyan.py')
  write_json(backup/'plan.json',{'pending':pending,'workers':a.workers,'at':now(),'policy':'reuse valid scores; fresh user for incomplete dialogues; preserve prior records'})
  for name in ('summary.json','usage_summary.json'):
   if (run/name).exists():shutil.copyfile(run/name,backup/name)
  def task(i):
   directory=run/'cards'/f'{i:03d}'
   try:
    if not full(i):
     if directory.exists():
      target=backup/'cards'/directory.name;target.parent.mkdir(parents=True,exist_ok=True);directory.rename(target)
     for name in (f'dialogue{i}.txt',f'scores{i}.txt'):
      if (run/name).exists():(run/name).rename(backup/name)
     directory.mkdir(parents=True,exist_ok=True)
     with run_log(directory):
      dialogue=generate_dialogue(i,plan['mode'],output_dir=directory,turns=plan['turns'],history=plan['client_history'])
     (run/f'dialogue{i}.txt').write_text('\n'.join(dialogue)+'\n')
    text=(run/f'dialogue{i}.txt').read_text()
    # New request log path prevents overwriting old numbered calls.
    attempt=directory/'resume_requests'/stamp
    with run_log(attempt):
     # One perspective per call; reuse previously valid perspectives.
     import psiarena.evaluate as ev
     old=ev.COUNTS
     try:
      for perspective,count in COUNTS.items():
       f=directory/f'judge_{perspective}.txt'
       try:parse_section(f.read_text(),perspective,require_ids=True);continue
       except (OSError,ValueError):pass
       if f.exists():
        dest=backup/'judges'/f'{i:03d}';dest.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest/f.name)
       # evaluate_dialogue uses module global COUNTS; do not mutate across workers.
       from psiarena import data
       systems={'client':data.load_prompt('client_eval_prefix')+data.load_role_cards()[i], 'supervisor':data.load_prompt('supervisor_system'),'counselor':data.load_prompt('eval_counselor_system')}
       from psiarena.config import chat
       ids=', '.join(f'{perspective}_{n:02d}' for n in range(1,count+1))
       instruction=('\n<输出格式补充>严格按原量表顺序逐项评分。每项单独输出三行：\n[维度]固定ID 维度名称\n[分析]评分依据\n[得分]整数分数或N/A'+f'\n本视角恰好{count}项，固定ID依次为：{ids}。不要输出其他[得分]标记。\n</输出格式补充>')
       raw=chat('judge',[{'role':'system','content':systems[perspective]},{'role':'user','content':ev._with_dialogue(data.load_prompt('eval_'+perspective)+instruction,text)}])
       f.write_text(raw);parse_section(raw,perspective,require_ids=True)
     finally:pass
    scores=''.join(HEADERS[v]+' '+(directory/f'judge_{v}.txt').read_text()+'\n' for v in COUNTS)
    parsed=parse_score_text(scores,plan['protocol']);(run/f'scores{i}.txt').write_text(scores);write_json(directory/'parsed_scores.json',parsed)
    return {'at':now(),'card':i,'status':'complete','resume':stamp}
   except Exception as exc:return {'at':now(),'card':i,'status':'error','error_type':type(exc).__name__,'resume':stamp}
  errors=[]
  with ThreadPoolExecutor(max_workers=a.workers) as pool:
   for result in as_completed([pool.submit(task,i) for i in pending]):
    event=result.result();append_json(run/'execution_log.jsonl',event);print(event,flush=True)
    if event['status']=='error':errors.append(event)
  scores=aggregate(run,protocol=plan['protocol'],indices=plan['cards'])
  write_json(run/'summary.json',{'finished_at':now(),'plan':plan,'errors':errors,'scores':scores,'resume':stamp})
  print('SAVED',run,flush=True)
  if not scores['complete']:raise SystemExit(2)
if __name__=='__main__':main()
