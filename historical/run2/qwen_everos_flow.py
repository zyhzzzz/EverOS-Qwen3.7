"""Isolated Qwen/EverOS experiment supervisor. Logs remain private on server."""
import json, os, signal, socket, subprocess, sys, time
from pathlib import Path
import httpx, yaml

r=Path(__file__).resolve().parent
h=Path.home()
old=h/'openclaw/evoagentbench-official-everos-20261110'
b=r/'benchmark'
orig=old/'EvoAgentBench-benchmark-6aa4990'
py=orig/'.benchmark-venv/bin/python'
ever=old/'EverOS-v1.2.3/.venv/bin/everos'
model='qwen3.7-flash'
os.umask(0o077)
def envfile(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))
q=envfile(h/'openclaw/qwen37-flash-config/qwen.env')
j=envfile(orig/'.env')
assert j['JUDGE_MODEL']=='deepseek-v4-flash'
env=dict(os.environ)
services=[]
def status(stage,**kw):
    (r/'status.tmp').write_text(json.dumps(dict(stage=stage,**kw)))
    (r/'status.tmp').replace(r/'status.json')
    print(stage,flush=True)
def run(cmd,label,environment=None):
    status(label)
    with (r/(label+'.log')).open('ab') as log:
        subprocess.run(list(map(str,cmd)),cwd=b,env=environment or env,stdout=log,stderr=subprocess.STDOUT,check=True)
def service(cmd,label,environment):
    with (r/(label+'.log')).open('ab') as log:
        p=subprocess.Popen(list(map(str,cmd)),env=environment,stdout=log,stderr=subprocess.STDOUT,cwd=r)
    services.append(p)
def wait(port):
    for _ in range(600):
        if any(x.poll() is not None for x in services):raise RuntimeError('service exited during startup')
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1',port))==0:return
        time.sleep(2)
    raise TimeoutError(port)
def audit(job,ids):
    paths=list((b/'jobs'/job).glob('*/result.json'))
    assert {p.parent.name.split('__')[0] for p in paths}==set(map(str,ids))
    for p in paths:
        res=json.loads(p.read_text())
        if res['verifier_result']['method']!='llm_judge':raise RuntimeError('judge review needed: '+str(p.parent.name))
        events=list(map(json.loads,(p.parent/'session.jsonl').read_text().splitlines()))
        assert model in {e.get('modelId') for e in events}
        if job.startswith('smoke'):
            msgs=[e['message'] for e in events if e.get('message',{}).get('role')=='assistant']
            final='\n'.join(v['text'] for v in msgs[-1]['content'] if v.get('type')=='text').strip()
            assert msgs[-1].get('stopReason')=='stop' and final and final==res['agent_result']['response'].strip(), 'smoke final-answer gate'
            assert any(v.get('name')=='search' for m in msgs for v in m['content'] if v.get('type')=='toolCall')
    return sum(json.loads(p.read_text())['verifier_result']['reward']>0 for p in paths)
try:
    status('preflight')
    for port in (19100,19101,19102):
        with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',port))!=0
    isolated=r/'agent-home';(isolated/'.openclaw').mkdir(parents=True,exist_ok=True)
    (isolated/'.openclaw/openclaw.json').write_text(json.dumps({'skills':{'allowBundled':[]}}))
    env.update(HOME=str(isolated),**q)
    settings={k:j[k] for k in ('JUDGE_MODEL','JUDGE_API_KEY','JUDGE_API_BASE')}
    env.update(settings)
    (b/'.env').write_text('\n'.join(k+'='+v for k,v in {**settings,**q}.items())+'\n')
    cfg=yaml.safe_load((b/'config.yaml.example').read_text());cfg['agent']='openclaw'
    (b/'config.yaml').write_text(yaml.safe_dump(cfg))
    ap=b/'src/agents/openclaw/openclaw.yaml'
    a=yaml.safe_load(ap.with_suffix('.yaml.example').read_text())
    m=a['providers']['openrouter']['models'][0];m.update(id=model,name=model,compat={'thinkingFormat':'qwen'})
    a.update(command=str(old/'openclaw-runtime/node_modules/.bin/openclaw'),model='modelstudio/'+model,
             tools={'profile':'full','deny':['group:openclaw']},
             providers={'modelstudio':{'baseUrl':q['QWEN_BASE_URL'],'apiKey':'${DASHSCOPE_API_KEY}','api':'openai-completions','models':[m]}})
    ap.write_text(yaml.safe_dump(a))
    dp=b/'src/domains/information_retrieval/information_retrieval.yaml'
    d=yaml.safe_load(dp.read_text());d['dataset_file']=str(h/'openclaw/EvoAgentBench/benchmark/data/BrowseComp-Plus/browsecomp_plus_decrypted.jsonl')
    d['mcp_server'].update(auto_start=False,port=19101,url='http://127.0.0.1:19101/mcp')
    dp.write_text(yaml.safe_dump(d))
    split=json.loads((b/'data/splits/information_retrieval.json').read_text())
    assert len(split['train'])==154 and len(split['test'])==65 and not set(split['train'])&set(split['test'])
    (r/'manifest.json').write_text(json.dumps(dict(agent=model,extract=model,judge=settings['JUDGE_MODEL'],model_config=m,commit='6aa49908adef7d430b3a172d6d7c06d5224ef6d2',trials=1,parallel=4,top_k=2,case_injection=True,agent_timeout=d['agent_timeout'])))
    status('starting_document_search')
    service([py,'-u',old/'start_official_local_search.py'],'search',dict(os.environ,CUDA_VISIBLE_DEVICES='0',HF_ENDPOINT='https://hf-mirror.com'))
    wait(19101)
    domain=['--domain','information_retrieval']
    single=['--task','106','--split','train']
    def solve(label,selection):
        run([py,'-u','src/run.py','--agent','openclaw',*domain,*selection,'--parallel','4','--job',label],label)
    status('prior_smoke_agent_verified')
    status('starting_memory_services')
    service([py,'-u',old/'everos_local_models.py'],'memory-models',dict(os.environ,CUDA_VISIBLE_DEVICES='0,1',EMBED_DEVICE='cuda:0',RERANK_DEVICE='cuda:1'))
    wait(19102)
    ee=dict(os.environ,EVEROS_API__HOST='127.0.0.1',EVEROS_API__PORT='19100',EVEROS_LLM__MODEL=model,EVEROS_LLM__API_KEY=q['DASHSCOPE_API_KEY'],EVEROS_LLM__BASE_URL=q['QWEN_BASE_URL'],EVEROS_EMBEDDING__BASE_URL='http://127.0.0.1:19102/v1',EVEROS_EMBEDDING__API_KEY='local-only',EVEROS_RERANK__PROVIDER='vllm',EVEROS_RERANK__BASE_URL='http://127.0.0.1:19102',EVEROS_RERANK__API_KEY='local-only')
    state=r/'everos-state'
    run([ever,'init','--root',state],'initialize-memory',ee)
    service([ever,'server','start','--root',state],'everos',ee);wait(19100)
    def extract(train,scope):
        args=['--agent-id',scope,'--project-id',scope,'--app-id','qwen37-ir','--api-url','http://127.0.0.1:19100']
        run([py,'-u','src/skill_evolution/evermemos/extract_skills.py',*domain,'--job-dir','jobs/'+train,'--output-dir',r/(scope+'-skills'),*args],scope+'-extract')
        log=(r/(scope+'-extract.log')).read_text()
        expected=1 if scope=='smoke' else 154
        assert f'Sent {expected}/{expected}' in log and '[FAIL]' not in log,'incomplete extraction submissions'
        return args
    def enhanced(label,sel,args):
        run([py,'-u','src/skill_evolution/evermemos/eval_with_skills.py',*domain,*sel,'--parallel','4','--top-k','2','--job',label,*args],label)
        assert any(json.loads((b/'jobs'/label/'skill_cache.json').read_text()).values())
    status('formal_training_authorized')
    solve('train',['--split','train']);train=audit('train',split['train'])
    formal=extract('train','formal')
    solve('baseline',['--split','test']);base=audit('baseline',split['test'])
    resp=httpx.post('http://127.0.0.1:19100/api/v2/memory/get',json=dict(agent_id='formal',app_id='qwen37-ir',project_id='formal',memory_type='agent_skill',page=1,page_size=100),timeout=60)
    resp.raise_for_status()
    data=resp.json()['data']
    n=int(data['total_count']) if 'total_count' in data else len(data['agent_skills'])
    (r/'formal-skill-count.txt').write_text(str(n))
    if not n:
        status('complete_without_skills',skills=0,train=train,baseline=base)
    else:
        enhanced('with-everos',['--split','test'],formal);score=audit('with-everos',split['test'])
        status('complete_raw',skills=n,train=train,baseline=base,everos=score)
except BaseException as exc:
    status('stopped_for_review',error=type(exc).__name__)
    raise
finally:
    for proc in reversed(services):
        if proc.poll() is None:proc.terminate()
    for proc in services:
        try:proc.wait(timeout=30)
        except subprocess.TimeoutExpired:proc.kill()
