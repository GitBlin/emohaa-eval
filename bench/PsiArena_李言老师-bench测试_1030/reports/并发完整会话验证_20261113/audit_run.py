import json,sys
from pathlib import Path
from datetime import datetime
r=Path(sys.argv[1]); read=lambda p:json.loads(p.read_text())
manifest=read(r/'manifest.json');summary=read(r/'summary.json'); checks=[]; users=[]; chatids=[]
for d in sorted((r/'cards').iterdir()):
 m=d/'memory'; identity=read(m/'session.json');users.append(identity['user_id'])
 history=read(m/'turn_25_after.body.bin')['data']['content'];ordered=sorted(history,key=lambda x:x['seqNum'])
 expected=[]
 for turn in range(1,26):
  request=read(m/f'turn_{turn:02d}_chat.request.json')['json'];reply=read(m/f'turn_{turn:02d}.json')['reply']
  expected.extend([('user',request['content']),('role',reply)])
 actual=[(x['role'],x['content'].strip()) for x in ordered]
 chatids.extend(set(x['chatId'] for x in history))
 reqs=[read(p) for p in sorted((d/'requests').glob('*/request.json'))]
 clients=[x for x in reqs if len(x['messages'])>1 and x['messages'][0]['content'].startswith('NOT_A_REAL_PREFIX')]
 # Directory suffix explicitly records the role, not model-generated text.
 clients=[read(p) for p in sorted((d/'requests').glob('*_client/request.json'))]
 judges=[read(p) for p in sorted((d/'requests').glob('*_judge/request.json'))]
 errors=list(d.rglob('error.json'))
 checks.append({'card':d.name,'turns':read(d/'dialogue_progress.json')['completed_turns'],
 'history_exact_match':actual==[(role,text.strip()) for role,text in expected],
 'final_history_messages':len(actual),'clear_calls':len(list(m.glob('clear_start.request.json'))),
 'audit_queries':len(list(m.glob('*before.request.json')))+len(list(m.glob('*after.request.json')))+len(list(m.glob('context_start.request.json'))),
 'client_calls':len(clients),'judge_calls':len(judges),'full_client_message_counts':[len(x['messages']) for x in clients],
 'models_correct':all(x['model']=='deepseek-v4.1-flash-1017' for x in clients+judges),
 'thinking_disabled':all(x.get('extra_body',{}).get('thinking',{}).get('type')=='disabled' for x in clients+judges),
 'call_errors':len(errors)})
result={'run':str(r),'workers':manifest['plan']['workers'],'unique_users':len(users)==len(set(users)),
 'unique_chat_ids':len(chatids)==len(set(chatids))==len(users),'cards':checks,
 'elapsed_seconds':(datetime.fromisoformat(summary['finished_at'])-datetime.fromisoformat(manifest['started_at'])).total_seconds(),
 'scores':summary['scores'],'errors':summary['errors']}
result['passed']=not result['errors'] and result['scores']['complete'] and result['unique_users'] and result['unique_chat_ids'] and all(x['turns']==25 and x['history_exact_match'] and x['final_history_messages']==50 and x['clear_calls']==1 and x['client_calls']==25 and x['judge_calls']==3 and x['full_client_message_counts']==list(range(2,51,2)) and x['models_correct'] and x['thinking_disabled'] and x['call_errors']==0 for x in checks)
(r/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
