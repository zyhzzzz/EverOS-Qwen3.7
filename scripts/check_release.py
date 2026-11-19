"""Local release checks; does not upload anything or call any model API."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re

parser = argparse.ArgumentParser()
parser.add_argument('--write-manifest', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
problems = []
files = [p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts]
for p in files:
    rel = p.relative_to(root).as_posix()
    if any(x in p.relative_to(root).parts for x in ('workspace', 'jobs', 'agent-home', 'everos-state', '__pycache__')):
        problems.append((rel, 'private/generated directory'))
    if p.name == '.env' or p.suffix in ('.jsonl', '.parquet', '.pkl', '.safetensors', '.db', '.pyc', '.log'):
        problems.append((rel, 'private artifact type'))
    if p.stat().st_size > 5_000_000:
        problems.append((rel, 'unexpected large artifact'))
    text = p.read_text(encoding='utf-8')
    # This verified CUDA package version resembles a private IPv4 address.
    scan_text = re.sub(r'(nvidia-curand-cu12(?:==|":\s*"))10\.3\.7\.77', r'\1VERSION', text)
    patterns = {
        'credential-like token': r'\b(?:sk-|hf_)[A-Za-z0-9_-]{20,}',
        'private IPv4': r'\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b',
        'personal home path': r'/home/(?!REDACTED\b|USER\b)[A-Za-z0-9_.-]+/',
        'Windows user path': r'[A-Z]:[\\/]Users[\\/][^\s/\\]+',
        'private key': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
    }
    for label, pattern in patterns.items():
        if re.search(pattern, scan_text): problems.append((rel, label))
    if p.suffix == '.py':
        ast.parse(text, filename=rel)
    if p.suffix == '.md':
        for link in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in link and not link.startswith('#'):
                target = link.split('#')[0]
                if target and not (p.parent / target).exists(): problems.append((rel, 'missing local link: ' + target))
if problems:
    for rel, reason in problems: print(rel + ': ' + reason)
    raise SystemExit('Release checks failed; do not publish.')
manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if p.name != 'SHA256SUMS.json'}
path = root / 'SHA256SUMS.json'
if args.write_manifest:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
else:
    assert path.exists(), 'No manifest; generate it only after reviewing changes.'
    assert json.loads(path.read_text(encoding='utf-8')) == manifest, 'Release files changed since manifest generation'
print(f'PASS: {len(manifest)} files; syntax, pattern scan, local links and manifest. Manual review still required.')
