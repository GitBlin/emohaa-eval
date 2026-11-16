#!/usr/bin/env python
"""Two synthetic memory cases, 25 turns each; excluded from benchmark scores."""
import argparse,secrets,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from psiarena.ai_role import counselor_session
from psiarena.ai_role_transport import write_json,now
SYSTEM='这是会话记忆连通性验证。请简短回答。对于会话标记，若当前会话未提供，不要猜测，回答“不知道”；若已提供，请准确复述。'
PROBE='请准确复述当前会话之前告诉你的会话标记。若当前会话没有提供过，就回答“不知道”，不要猜测。'
TOPICS=['我想每天散步十分钟，你觉得可以从什么时间开始？','我准备把明天的待办写在纸上，请给一句鼓励。','我想晚上少看手机，请给一个简单建议。','今天我准备整理书桌，请给一句简短的建议。','我想每天读两页书，请给一句简短鼓励。']
def unknown(reply):
 return any(x in reply for x in ('不知道','不记得','不清楚','未提供','没有提供','没有记录','不确定','没有告诉','无法回忆','未告诉','没有提到','并未提供'))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');args=p.parse_args()
 if not args.execute:
  print('Two independent 25-turn sessions; recall at turns 5,15,25; second-session blind probe; same-user clear+probe. Add --execute.');return
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
 run=ROOT.parent/'PsiArena_李言老师-bench测试_1030'/('PsiArena_李言老师_记忆验证_'+stamp)
 run.mkdir(parents=True,exist_ok=False)
 markers=['MEM-'+secrets.token_hex(8).upper() for _ in range(2)]
 report={'started_at':now(),'kind':'synthetic memory verification; excluded from benchmark scores','cases':[],
         'api_calls_planned':52,'design':'seed only once; no history replay; 25 turns each; recall at 5/15/25; isolated users; clear+blind probe same user'}
 write_json(run/'report.json',report)
 for i,marker in enumerate(markers):
  case={'case':i+1,'turns':[],'checks':[]};report['cases'].append(case)
  try:
   with counselor_session(run/f'case_{i+1}'/'audit',f'memory_case_{i+1}') as session:
    case['user_id']=session.user_id
    for turn in range(1,26):
     if i==1 and turn==1:prompt,kind=PROBE,'cross_session_blind_probe'
     elif turn==(1 if i==0 else 2):prompt,kind=f'请记住本次会话的唯一会话标记：{marker}。后面我会再问。请确认收到。','seed'
     elif turn in (5,15,25):prompt,kind=PROBE,'recall'
     else:prompt,kind=TOPICS[(turn-1)%len(TOPICS)],'filler'
     reply=session.chat([{'role':'system','content':SYSTEM},{'role':'user','content':prompt}])
     case['turns'].append({'turn':turn,'kind':kind,'prompt':prompt,'reply':reply})
     if kind in ('recall','cross_session_blind_probe'):
      check={'kind':kind,'turn':turn,'reply':reply}
      if kind=='recall':check['passed']=marker in reply
      else:
       check.update(leaked=any(m in reply for m in markers),unknown_acknowledged=unknown(reply))
       check['passed']=not check['leaked'] and check['unknown_acknowledged']
      case['checks'].append(check)
      print(f'case={i+1} turn={turn} kind={kind} pass={check["passed"]}',flush=True)
     write_json(run/'report.json',report)
    response=session.client.call('POST','/open/chat/clearContext',session.directory,'clear_end_test',payload={'botId':session.bot_id,'courseProgressId':0})
    if not isinstance(response,dict) or response.get('role')!='flush_context':raise RuntimeError('clearContext failed')
    session.audit('context_after_explicit_clear',0);case['clear_empty_history_verified']=True
    session.turn=0
    session.directory=run/f'case_{i+1}'/'after_clear';session.directory.mkdir()
    reply=session.chat([{'role':'system','content':SYSTEM},{'role':'user','content':PROBE}])
    check={'kind':'same_user_after_clear_blind_probe','reply':reply,'leaked':any(m in reply for m in markers),'unknown_acknowledged':unknown(reply)}
    check['passed']=not check['leaked'] and check['unknown_acknowledged'];case['checks'].append(check)
    print(f'case={i+1} after_clear pass={check["passed"]}',flush=True)
   case['passed']=all(c['passed'] for c in case['checks'])
  except Exception as exc:
   case.update(passed=False,error_type=type(exc).__name__);print(f'case={i+1} error={type(exc).__name__}',flush=True)
  write_json(run/'report.json',report)
 report['independent_users']=len({c.get('user_id') for c in report['cases']})==2
 report['passed']=report['independent_users'] and all(c.get('passed',False) for c in report['cases'])
 report['finished_at']=now();write_json(run/'report.json',report)
 lines=['# 李言老师记忆行为验证','',f'结果：{"全部通过" if report["passed"] else "存在失败或未确认项"}','','两条人工合成数据，各25轮；不计入PsiArena成绩。','标记只在种子消息出现，追问不携带标记；不重发历史。','']
 for c in report['cases']:
  lines += [f'## 数据 {c["case"]}','',f'通过：{c.get("passed",False)}','']
  for check in c['checks']:lines += [f'- {check["kind"]}，轮次 {check.get("turn","清空后")}：{check["passed"]}；回复：{check["reply"]}']
  lines+=['']
 lines+=['结论仅覆盖本次两条合成数据，不证明平台所有隐藏记忆机制均被关闭。']
 (run/'report.md').write_text('\n'.join(lines)+'\n')
 print('SAVED',run,flush=True)
 if not report['passed']:raise SystemExit(2)
if __name__=='__main__':main()
