exec(open('/tmp/check_arena_memory.py').read().split('try:\n for i')[0])
report={'bot_id':bot,'sessions':[]}
row={'turns':[]};report['sessions'].append(row)
try:
 with counselor_session(out/'natural_session','natural_memory') as s:
  row['user_id']=s.user_id
  ask(s,row,'我养了一只猫叫栗子，下周三要带它去打疫苗，我有点担心它紧张。请简短回答。','natural_seed')
  ask(s,row,'我刚才说我的猫叫什么名字？准备哪天带它去做什么？','natural_recall')
 report['finished']=True
except Exception as e:report.update(finished=False,error_type=type(e).__name__)
write_json(out/'natural_report.json',report)
