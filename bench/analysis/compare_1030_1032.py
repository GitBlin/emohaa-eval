"""Offline paired comparison of explicitly designated new/baseline archives."""
import json,math,statistics,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/1030新智能体_1032基线_回复与能力比较_20261113';OUT.mkdir(parents=True,exist_ok=True)
def locate(suffix):return next(p.parent for p in ROOT.glob('*/*/manifest.json') if p.parent.name.endswith(suffix))
def readrows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
paths={k:locate(v) for k,v in {'tom_new':'bb42bf7a','tom_base':'f03b16ff','emo_new':'d38e5524','emo_base1':'8eefca75','emo_base2':'3fca89e2'}.items()}
# Prefer a complete record set for the headline; retain current partially resumed state separately.
files={k:v/'responses.jsonl' for k,v in paths.items()}
for k in ['tom_base']:
 m=json.loads((paths[k]/'manifest.json').read_text())
 if len(readrows(files[k]))!=m['planned_trials']:
  files[k]=next(p for p in sorted((paths[k]/'retry_history').glob('*/responses.jsonl'),reverse=True) if len(readrows(p))==m['planned_trials'])
rows={k:readrows(p) for k,p in files.items()}
def key(x):return (x['sample_id'],x['language'],x['repeat'])
def pred(x):return json.dumps(x.get('prediction_original'),sort_keys=True,ensure_ascii=False)
def style(rs):
 good=[x for x in rs if x['status']=='ok'];replies=[x['reply'] for x in good];lengths=[len(x) for x in replies]
 return {'count':len(rs),'correct':sum(x['correct'] for x in rs),'accuracy':sum(x['correct'] for x in rs)/len(rs),'statuses':dict(collections.Counter(x['status'] for x in rs)),'median_reply_chars':statistics.median(lengths),'mean_reply_chars':statistics.mean(lengths),'top_replies':collections.Counter(replies).most_common(8),'code_fence_rate':sum('```' in x for x in replies)/len(replies),'noncanonical':sum(not __import__('re').fullmatch(r'\[\[[A-Z]\]\]',x) for x in replies) if rs[0].get('task_file') else None}
def compare(a,b):
 A={key(x):x for x in a};B={key(x):x for x in b};pairs=[(A[k],B[k]) for k in A.keys()&B.keys() if A[k]['status']=='ok' and B[k]['status']=='ok'];n=len(pairs)
 wins=sum(x['correct'] and not y['correct'] for x,y in pairs);losses=sum(y['correct'] and not x['correct'] for x,y in pairs);d=wins+losses
 logterms=[math.lgamma(d+1)-math.lgamma(i+1)-math.lgamma(d-i+1)-d*math.log(2) for i in range(min(wins,losses)+1)]
 p=min(1,2*sum(math.exp(v) for v in logterms)) if d else 1
 groups=collections.defaultdict(list)
 for x,y in pairs:groups[x.get('task_file',x.get('task',''))+' / '+x['language']].append((x,y))
 breakdown=[]
 for group,ps in groups.items():
  w=sum(x['correct'] and not y['correct'] for x,y in ps);l=sum(y['correct'] and not x['correct'] for x,y in ps)
  breakdown.append({'group':group,'n':len(ps),'new_correct':sum(x['correct'] for x,y in ps),'base_correct':sum(y['correct'] for x,y in ps),'new_only_correct':w,'base_only_correct':l,'delta_pp':100*(w-l)/len(ps)})
 examples=[]
 for kind in ['new_only_correct','base_only_correct']:
  chosen=[(x,y) for x,y in sorted(pairs,key=lambda p:key(p[0])) if (x['correct'] and not y['correct'] if kind=='new_only_correct' else y['correct'] and not x['correct'])][:8]
  for x,y in chosen:examples.append({'kind':kind,'key':key(x),'new_trial':x['trial_id'],'base_trial':y['trial_id'],'new_reply':x['reply'],'base_reply':y['reply'],'gold_original':x.get('labels',x.get('answer')), 'gold_shown':next((shown for shown,original in x.get('map',{}).items() if original==x.get('answer')),None), 'note':'ToMBench options shuffled; reply uses shown labels, prediction_original uses original labels'})
 return {'paired_valid_n':n,'prediction_agreement':sum(pred(x)==pred(y) for x,y in pairs)/n,'exact_reply_agreement':sum(x['reply']==y['reply'] for x,y in pairs)/n,'new_correct':sum(x['correct'] for x,y in pairs),'base_correct':sum(y['correct'] for x,y in pairs),'new_only_correct':wins,'base_only_correct':losses,'delta_pp':100*(wins-losses)/n,'mcnemar_exact_p':p,'breakdown':sorted(breakdown,key=lambda x:x['delta_pp']),'examples':examples}
comparisons={label:compare(rows[a],rows[b]) for label,a,b in [('ToMBench','tom_new','tom_base'),('EmoBench_基线第一次','emo_new','emo_base1'),('EmoBench_基线第二次','emo_new','emo_base2'),('EmoBench_基线自身重复','emo_base2','emo_base1')]}
# Verify prompt, options, answer and data comparability across aligned plans.
def plans(a,b):
 A={key(x):x for x in json.loads((paths[a]/'plan.json').read_text())};B={key(x):x for x in json.loads((paths[b]/'plan.json').read_text())};common=A.keys()&B.keys()
 diffs=[]
 for k in common:
  x,y=A[k],B[k]
  if {a:b for a,b in x.get('request',{}).items() if a!='botId'}!={a:b for a,b in y.get('request',{}).items() if a!='botId'}:diffs.append(k)
 return {'common':len(common),'request_mismatches':len(diffs),'examples':diffs[:3]}
result={'sources':{k:str(p) for k,p in files.items()},'stats':{k:style(v) for k,v in rows.items()},'comparisons':comparisons,'prompt_checks':{a+'_'+b:plans(a,b) for a,b in [('tom_new','tom_base'),('emo_new','emo_base1'),('emo_new','emo_base2')]}}
# Pull provider-reported usage from audit artifacts, no network and no credentials.
usage={}
for k in paths:
 vals=[]
 for row in rows[k]:
  if row['status']!='ok':continue
  d=paths[k]/'trials'/row['trial_id']
  attempts=sorted(d.glob('attempt_*'),reverse=True)
  for attempt in attempts:
   f=attempt/'context_after.body.bin'
   if not f.exists():continue
   try:
    body=json.loads(f.read_bytes())
    for msg in (body.get('data') or {}).get('content',[]):
     if msg.get('role')=='role':
      for c in msg.get('contents') or []:
       if c.get('promptTokens') is not None:vals.append({'prompt':c['promptTokens'],'completion':c.get('completionTokens',0)})
    break
   except (ValueError,AttributeError):pass
 if vals:usage[k]={'observations':len(vals),'median_prompt_tokens':statistics.median(x['prompt'] for x in vals),'median_completion_tokens':statistics.median(x['completion'] for x in vals)}
result['provider_usage']=usage
(OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
for k,v in result['stats'].items():print(k,json.dumps(v,ensure_ascii=False))
for k,v in comparisons.items():print(k,json.dumps({a:b for a,b in v.items() if a not in ['breakdown','examples']},ensure_ascii=False));print('TOPDIFF',v['breakdown'][:4],v['breakdown'][-4:])
print('PROMPTS',result['prompt_checks']);print('USAGE',usage);print('OUT',OUT)
