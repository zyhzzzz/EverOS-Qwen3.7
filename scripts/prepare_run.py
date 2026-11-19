"""Prepare an isolated run, but do not start chargeable API calls."""
from pathlib import Path
import argparse
import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
args = parser.parse_args()
assert re.fullmatch(r'[a-zA-Z0-9_-]+', args.name)
os.umask(0o077)
root = Path(os.environ['REPRO_ROOT']).resolve()
package = Path(__file__).resolve().parents[1]
source = root / 'runtime/EvoAgentBench-benchmark-6aa4990'
run = root / 'runs' / args.name
assert not run.exists(), 'Use a new run name; do not overwrite completed results.'
assert (root / '.env').is_file(), 'Create the private .env first.'
secrets = dict(line.split('=', 1) for line in (root / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
assert secrets.get('JUDGE_MODEL') == 'deepseek-v4-flash'
assert all(secrets.get(k) and secrets[k] != 'REPLACE_LOCALLY' for k in ('DASHSCOPE_API_KEY', 'JUDGE_API_KEY', 'QWEN_BASE_URL', 'JUDGE_API_BASE'))
for port in (19100, 19101, 19102):
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', port)) != 0, f'Port {port} occupied'
shutil.copytree(source, run / 'benchmark', ignore=shutil.ignore_patterns(
    '.benchmark-venv', '.env', 'data', 'jobs', '__pycache__', '*.pyc'))
shutil.copytree(source / 'data/splits', run / 'benchmark/data/splits')
shutil.copy2(package / 'scripts/flow_template.py', run / 'qwen_everos_flow.py')
shutil.copy2(package / 'scripts/apply_answer_patch.py', run / 'apply_answer_patch.py')
subprocess.run([sys.executable, str(run / 'apply_answer_patch.py')], check=True)
adapter = run / 'benchmark/src/agents/openclaw/openclaw.py'
assert hashlib.sha256(adapter.read_bytes()).hexdigest() == '1aa4d7537868fff345a8bf4a1fc061d8abf2acada86cdd414a39854ab01bbf42'
print('Prepared:', run)
print('Next: export EVEROS_MODELS_ROOT="$REPRO_ROOT/assets/models"')
print('Then execute the run qwen_everos_flow.py with the benchmark Python.')
