"""Repair one malformed judge response, then resume without regenerating answers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

r = Path.home() / 'openclaw/qwen37-everos-repeat-20261118'
b = r / 'benchmark'
os.umask(0o077)
os.chdir(b)
sys.path.insert(0, str(b / 'src'))
from dotenv import load_dotenv
load_dotenv(b / '.env', override=True)
from config import get_domain_config
from domains.information_retrieval.browsecomp_plus import BrowseCompPlusAdapter

p = b / 'jobs/train/495__trial_1'
backup = r / 'judge-repair-495'
backup.mkdir(exist_ok=False)
for name in ('result.json', 'session.jsonl'):
    shutil.copy2(p / name, backup / name)
shutil.copy2(p / 'verifier/details.json', backup / 'original-details.json')
result = json.loads((p / 'result.json').read_text())
assert result['verifier_result']['method'] == 'exact_match'
cfg = get_domain_config('information_retrieval')
record = next(json.loads(line) for line in Path(cfg['dataset_file']).read_text().splitlines()
              if str(json.loads(line).get('query_id')) == '495')
task = {'name': '495', 'problem': record.get('problem', record.get('query')),
        'answer': record['answer']}
judge = BrowseCompPlusAdapter().verify(task, {}, backup, result['agent_result'])
assert judge['method'] == 'llm_judge', 'Repeat judge failed; original result untouched'
result['verifier_result'] = judge
(p / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
shutil.copy2(backup / 'verifier/details.json', p / 'verifier/details.json')
assert (p / 'session.jsonl').read_bytes() == (backup / 'session.jsonl').read_bytes()
(backup / 'repair-record.json').write_text(json.dumps({
    'reason': 'Missing correct field in original judge response',
    'same_official_verifier': True, 'answer_regenerated': False,
    'repaired_verifier_result': judge,
    'session_sha256': hashlib.sha256((p / 'session.jsonl').read_bytes()).hexdigest(),
}, indent=2))
print('Judge repaired:', judge, flush=True)
source = (r / 'qwen_everos_flow.py').read_text()
before = "solve('train',['--split','train']);train=audit('train',split['train'])"
assert source.count(before) == 1
source = source.replace(before, "status('resume_frozen_train');train=audit('train',split['train'])")
before = "run([ever,'init','--root',state],'initialize-memory',ee)"
assert source.count(before) == 1
assert (r / 'everos-state').is_dir() and not (r / 'formal-extract.log').exists()
source = source.replace(before, "status('reuse_unpopulated_memory_state')")
(r / 'resume-effective-flow.py').write_text(source)
exec(compile(source, str(r / 'resume-effective-flow.py'), 'exec'),
     {'__name__': '__main__', '__file__': str(r / 'resume-effective-flow.py')})
