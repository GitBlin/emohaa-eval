import sys,json,uuid,re,os,hashlib
from pathlib import Path
from datetime import datetime,timezone
from zipfile import ZipFile
from xml.etree import ElementTree as E
root=Path('/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt')
sys.path.insert(0,str(root/'bench/PsiArena'))
from psiarena.ai_role import credentials
from psiarena.ai_role_transport import Client,write_json,sse_events
out=root/'bench/api_diagnostics'/('prompt_methods_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
out.mkdir(parents=True)
(out/'probe.py').write_text(Path(__file__).read_text())
pattern=re.compile(r'prompt|提示词|组装|编译层|注入|metainfo|meta.info|调试|trace|debug|接口地址',re.I)
docs=[]
for base,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in ('.git','.venv','node_modules','trials','snapshot','retry_history','code_migrations','api_diagnostics','__pycache__')]
 for name in files:
  p=Path(base)/name
  if p.suffix.lower() not in ('.md','.docx','.txt','.rst','.html','.pdf'):continue
  if p.suffix=='.docx':
   with ZipFile(p) as z:r=E.fromstring(z.read('word/document.xml'))
   n={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
   text='\n'.join(''.join(t.text or '' for t in x.findall('.//w:t',n)) for x in r.findall('.//w:p',n))
  elif p.suffix=='.pdf':
   docs.append({'path':str(p.relative_to(root)),'status':'PDF not extracted'});continue
  else:text=p.read_text(errors='replace')
  hits=[{'line':i,'text':line[:1800]} for i,line in enumerate(text.splitlines(),1) if pattern.search(line)]
  docs.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'hits':hits})
write_json(out/'document_search.json',docs)
print('OUTPUT',out,'DOCS',len(docs),flush=True)
results=[]
def inspect(obj):
 fields=[]
 def walk(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():
    q=path+'.'+k
    if re.search('prompt|system|messages|metainfo|inputs|reminder|customMessage|trace|debug',k,re.I):fields.append({'path':q,'value':v})
    walk(v,q)
  elif isinstance(x,list):
   for i,v in enumerate(x):walk(v,path+f'[{i}]')
 walk(obj)
 return fields
for bot in (1030,1032):
 c=Client(*credentials(),'probe_'+uuid.uuid4().hex,timeout=45)
 c.authenticate(); d=out/str(bot);d.mkdir()
 write_json(d/'identity.json',{'bot_id':bot,'user_id':c.user_id})
 def query(name,endpoint,params=None,method='GET',payload=None):
  try:
   value=c.call(method,endpoint,d,name,params=params,payload=payload)
   item={'bot':bot,'method':name,'ok':True,'fields':inspect(value)}
   if isinstance(value,dict):item.update(keys=list(value),roles=[m.get('role') for m in value.get('content',[]) if isinstance(m,dict)] if isinstance(value.get('content'),list) else [])
   results.append(item);print(bot,name,'OK',flush=True);return value
  except Exception as e:
   results.append({'bot':bot,'method':name,'ok':False,'error':str(e)});print(bot,name,type(e).__name__,flush=True)
 query('bot_list','/open/bot/list')
 query('bot_detail',f'/open/bot/{bot}')
 params={'botId':bot,'courseProgressId':0,'pageNum':0,'pageSize':100,'onlyLastSession':'true'}
 query('context_before','/open/chat/context',params)
 for mode in ('stream','nonstream','inputs'):
  body={'botId':bot,'content':'你好，这是一条接口字段核验消息，请简短回复你好即可。','courseProgressId':0,'isStream':mode!='nonstream','returnTts':False}
  if mode=='inputs':body['inputs']={'diagnostic_marker':'INPUT_PROBE_'+uuid.uuid4().hex}
  write_json(d/(mode+'.request.json'),body)
  try:
   with c.session.post(c.base_url+'/open/chat/completions',json=body,headers={'Authorization':'Bearer '+c.token},timeout=(10,45)) as r:
    (d/(mode+'.raw.txt')).write_bytes(r.content)
    ct=r.headers.get('content-type','');write_json(d/(mode+'.http.json'),{'status':r.status_code,'content_type':ct})
    r.raise_for_status()
    if 'event-stream' in ct:
     parsed=[]
     for typ,s in sse_events(r.content.decode().splitlines()):
      if s.strip()=='[DONE]':parsed.append({'event':typ,'data':s});continue
      obj=json.loads(s)
      if isinstance(obj,str):obj=json.loads(obj)
      parsed.append({'event':typ,'data':obj})
    else:parsed=r.json()
    write_json(d/(mode+'.parsed.json'),parsed)
    results.append({'bot':bot,'method':mode,'ok':True,'content_type':ct,'fields':inspect(parsed)})
    print(bot,mode,ct,flush=True)
  except Exception as e:results.append({'bot':bot,'method':mode,'ok':False,'error':str(e)});print(bot,mode,type(e).__name__,flush=True)
  query('context_'+mode,'/open/chat/context',params)
 query('clear_probe_only','/open/chat/clearContext',method='POST',payload={'botId':bot,'courseProgressId':0})
 query('context_after_clear_latest','/open/chat/context',params)
 query('context_after_clear_all','/open/chat/context',{**params,'onlyLastSession':'false'})
 c.session.close()
write_json(out/'results.json',results)
print('FINISHED',out,flush=True)
