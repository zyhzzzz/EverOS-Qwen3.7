"""Download public assets locally; never publish decrypted benchmark data."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
from huggingface_hub import snapshot_download, HfApi

r = Path(os.environ['REPRO_ROOT']).resolve()
b = r / 'runtime/EvoAgentBench-benchmark-6aa4990'
subprocess.run([sys.executable, 'src/utils/browsecomp-plus-tools/setup_data.py',
                '--index', 'qwen3-embedding-8b'], cwd=b, check=True)
assets = r / 'assets'
records = []
api = HfApi()
items = [('Tevatron/browsecomp-plus-corpus', 'dataset', assets / 'data/browsecomp-plus-corpus'),
         ('Qwen/Qwen3-Embedding-8B', 'model', assets / 'models/Qwen3-Embedding-8B'),
         ('Qwen/Qwen3-Embedding-4B', 'model', assets / 'models/Qwen3-Embedding-4B'),
         ('Qwen/Qwen3-Reranker-4B', 'model', assets / 'models/Qwen3-Reranker-4B')]
for repo, kind, target in items:
    info = api.repo_info(repo, repo_type=kind)
    snapshot_download(repo, repo_type=kind, revision=info.sha, local_dir=target)
    records.append({'repo': repo, 'revision': info.sha})
# The upstream snippet code resolves this tokenizer itself. Warm its cache.
from transformers import AutoTokenizer
AutoTokenizer.from_pretrained('Qwen/Qwen3-0.6B')
raw = json.loads((b / 'data/splits/information_retrieval.json').read_text())
if 'clusters' in raw:
    train = [str(v) for c in raw['clusters'].values() for v in c['train']]
    test = [str(v) for c in raw['clusters'].values() for v in c['test']]
else:
    train, test = list(map(str, raw['train'])), list(map(str, raw['test']))
assert len(train) == len(set(train)) == 154
assert len(test) == len(set(test)) == 65 and not set(train) & set(test)
data = b / 'data/BrowseComp-Plus/browsecomp_plus_decrypted.jsonl'
ids = {str(json.loads(line)['query_id']) for line in data.read_text().splitlines()}
assert set(train + test) <= ids
assert len(list((b / 'data/BrowseComp-Plus/indexes/qwen3-embedding-8b').glob('corpus.*.pkl'))) == 4
(assets / 'download_manifest.json').write_text(json.dumps({
    'downloads': records, 'train': 154, 'test': 65,
    'task_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
    'note': 'Historical HF revision IDs were not fully recorded. These are new download revisions.'
}, indent=2))
print('Validated 154 train / 65 test, no overlap; assets stored locally.')
