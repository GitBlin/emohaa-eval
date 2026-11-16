import os,sys,json,secrets
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/PsiArena')
sys.path.insert(0,str(ROOT))
from psiarena.ai_role import counselor_session
from psiarena.ai_role_transport import write_json
bot=int(sys.argv[1]);os.environ['PSIARENA_AI_ROLE_BOT_ID']=str(bot)
out=Path(sys.argv[2])/str(bot);out.mkdir(parents=True)
markers=['MEM-'+secrets.token_hex(6).upper() for _ in range(2)]
report={'bot_id':bot,'markers':markers,'sessions':[]}
probe='请复述我在当前会话告诉你的记忆标记，以及我准备周几做什么。如果本会话没有提供这些信息，请回答不知道，不要猜。'
def ask(s,row,p,kind):
 r=s.chat([{'role':'user','content':p}]);row['turns'].append({'kind':kind,'prompt':p,'reply':r});write_json(out/'report.json',report);print(bot,kind,r,flush=True);return r
try:
 for i in range(2):
  row={'turns':[]};report['sessions'].append(row)
  with counselor_session(out/f'session_{i}',f'memory_comparison_{bot}_{i}') as s:
   row['user_id']=s.user_id
   if i:
    r=ask(s,row,probe,'new_session_blind');row['old_marker_leaked']=markers[0] in r
   seed=f'这是记忆验证。我的记忆标记是{markers[i]}。我准备'+('周六去植物园散步。' if i==0 else '周二去图书馆读书。')+'请记住，简短确认即可。'
   ask(s,row,seed,'seed')
   ask(s,row,'今天我想早点睡觉，请给一句简短建议。','filler')
   r=ask(s,row,probe,'recall');row['marker_recalled']=markers[i] in r
   row['facts_recalled']=all(w in r for w in (['周六','植物园'] if i==0 else ['周二','图书馆']))
   if i:
    cleared=s.client.call('POST','/open/chat/clearContext',s.directory,'clear_end',payload={'botId':bot,'courseProgressId':0})
    assert cleared.get('role')=='flush_context'
    s.audit('after_clear',0);row['clear_empty_verified']=True
    s.turn=0;s.directory=out/'after_clear';s.directory.mkdir()
    r=ask(s,row,probe,'cleared_session_blind');row['cleared_marker_leaked']=any(m in r for m in markers)
 report['independent_users']=len({r['user_id'] for r in report['sessions']})==2
 report['finished']=True
except Exception as e:
 report['error_type']=type(e).__name__;report['finished']=False
write_json(out/'report.json',report)
print('SAVED',out,flush=True)
