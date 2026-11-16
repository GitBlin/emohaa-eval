#!/usr/bin/env python3
"""Arena efficiency-only: full 25-turn sessions, no quality judge; original dialogues and memory audits."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'PsiArena'))
from evaluate_efficiency import measure,summary
from emobench_api import write_json


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--bot-id',type=int,default=1030)
 p.add_argument('--cards',type=int,default=10)
 p.add_argument('--start',type=int,default=0)
 p.add_argument('--workers',type=int,default=4)
 p.add_argument('--session-attempts',type=int,default=2,help='restart failed card from fresh user, preserving all failed attempts')
 p.add_argument('--execute',action='store_true')
 a=p.parse_args()
 if a.bot_id<1 or a.cards<1 or a.start<0 or a.start+a.cards>100 or min(a.workers,a.session_attempts)<1:p.error('invalid counts')
 if not a.execute:
  print(json.dumps({'cards':a.cards,'turns_per_card':25,'workers':a.workers,'bot_id':a.bot_id,'judge':False}));return
 os.environ['PSIARENA_AI_ROLE_BOT_ID']=str(a.bot_id)
 from psiarena import ai_role
 from psiarena.config import get_settings
 from psiarena.pipeline import generate_dialogue
 s=get_settings()
 if s.counselor_provider!='ai_role':raise ValueError('Requires ai_role provider')
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
 run=HERE/'efficiency_evaluations'/f'arena_{a.bot_id}_efficiency_{stamp}';run.mkdir(parents=True)
 hashes={}
 paths=[Path(__file__),HERE/'evaluate_efficiency.py',HERE/'emobench_api.py']
 paths += [f for folder in ['psiarena','data'] for f in (HERE/'PsiArena'/folder).rglob('*') if f.is_file() and f.suffix in ('.py','.json','.txt')]
 for source in paths:
  rel=source.relative_to(HERE);dest=run/'snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);hashes[str(rel)]=hashlib.sha256(source.read_bytes()).hexdigest()
 manifest={'at':datetime.now(timezone.utc).isoformat(),'bot_id':a.bot_id,'cards':list(range(a.start,a.start+a.cards)),
   'turns':25,'workers':a.workers,'history':'full','mode':'psycho','judge_enabled':False,'session_attempts':a.session_attempts,
   'roles':{r:{'model':v.model,'thinking':v.thinking,'reasoning_effort':v.reasoning_effort} for r,v in s.roles.items()},
   'temperature':s.temperature,'client_max_tokens':os.getenv('PSIARENA_CLIENT_MAX_TOKENS',str(s.max_tokens)),
   'timeout':s.timeout,'sha256':hashes,'measurement':'same measure() as single-turn; excludes audits, authentication and simulated client calls',
   'counselor_configuration':'platform-controlled, no inference that counselor uses client temperature or thinking'}
 write_json(run/'manifest.json',manifest)
 class TimedClient(ai_role.Client):
  def call(self,method,endpoint,directory,name,payload=None,params=None,chat=False):
   if not chat:return super().call(method,endpoint,directory,name,payload=payload,params=params,chat=chat)
   target=directory/'timings'/name;target.mkdir(parents=True)
   result=measure(self,payload,target)
   turn=int(re.search(r'turn_(\d+)',name)[1]); result.update(turn=turn,input_characters=len(payload['content']))
   write_json(target/'result.json',result)
   if not result['success']:raise ai_role.ProtocolError('Measured chat failed: '+str(result['error_type']))
   return result['reply'],{'finish_seen':True,'timing_directory':str(target)}
 ai_role.Client=TimedClient  # process-local adapter; original source and stored experiments untouched
 print('RUN_DIR='+str(run),flush=True)
 started=time.perf_counter()
 def execute(index):
  result={'card':index,'attempts':[],'complete':False}
  for attempt in range(1,a.session_attempts+1):
   d=run/'cards'/f'{index:03d}'/f'attempt_{attempt:02d}';d.mkdir(parents=True)
   entry={'attempt':attempt,'directory':str(d),'complete':False}
   try:
    dialogue=generate_dialogue(index,'psycho',output_dir=d,turns=25,history='full')
    (d/'dialogue.txt').write_text('\n'.join(dialogue)+'\n')
    entry['complete']=True;result['complete']=True
   except Exception as e:entry['error_type']=type(e).__name__
   result['attempts'].append(entry);write_json(run/'cards'/f'{index:03d}'/'status.json',result)
   print(f"card={index} attempt={attempt} complete={entry['complete']} error={entry.get('error_type')}",flush=True)
   if result['complete']:break
  return result
 statuses=[]
 with ThreadPoolExecutor(max_workers=a.workers) as pool:
  for fut in as_completed([pool.submit(execute,i) for i in manifest['cards']]):
   statuses.append(fut.result());write_json(run/'progress.json',{'finished_cards':len(statuses),'completed_cards':sum(x['complete'] for x in statuses),'planned_cards':a.cards})
 rows=[];final=[]
 for card in statuses:
  for attempt in card['attempts']:
   for f in sorted(Path(attempt['directory']).glob('memory/timings/*/result.json')):
    row=json.loads(f.read_text());row.update(card=card['card'],attempt=attempt['attempt']);rows.append(row)
    if attempt['complete']:final.append(row)
 def group(turn):return '01' if turn==1 else '02-05' if turn<=5 else '06-15' if turn<=15 else '16-25'
 stats={'wall_seconds':time.perf_counter()-started,'statuses':statuses,'all_attempts':summary(rows),'completed_session_turns':summary(final),
 'by_turn_group':{g:summary([r for r in final if group(r['turn'])==g]) for g in ['01','02-05','06-15','16-25']},
 'per_card':{str(i):summary([r for r in final if r['card']==i]) for i in manifest['cards']}}
 write_json(run/'summary.json',stats);write_json(run/'measurements.json',rows)
 print(json.dumps({'completed_cards':sum(x['complete'] for x in statuses),'all_attempts':stats['all_attempts'],'final_turns':len(final)},ensure_ascii=False,indent=2))
 return 0 if all(x['complete'] for x in statuses) else 2

if __name__=='__main__':sys.exit(main())
