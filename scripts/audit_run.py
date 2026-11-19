"""Read-only structural audit of a private run; emit no answer or question text."""
from pathlib import Path
import argparse
import hashlib
import json

parser = argparse.ArgumentParser()
parser.add_argument('run_dir', type=Path)
args = parser.parse_args()
r = args.run_dir.resolve()
report = {}
for job, expected in [('train', 154), ('baseline', 65), ('with-everos', 65)]:
    rows = []
    for p in sorted((r / 'benchmark/jobs' / job).glob('*/result.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        events = [json.loads(line) for line in (p.parent / 'session.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        assistants = [e['message'] for e in events if e.get('message', {}).get('role') == 'assistant']
        last = assistants[-1] if assistants else {}
        selected = '\n'.join(x.get('text', '') for x in last.get('content', [])
                             if isinstance(x, dict) and x.get('type') == 'text' and x.get('text', '').strip()).strip() if last.get('stopReason') == 'stop' else ''
        response = d.get('agent_result', {}).get('response', '')
        v = d.get('verifier_result', {})
        rows.append({'task_id': p.parent.name.split('__')[0], 'reward': v.get('reward'),
                     'method': v.get('method'), 'final_selection_matches': response.strip() == selected,
                     'final_stop_reason': last.get('stopReason'),
                     'content_filter_error': 'DataInspectionFailed' in json.dumps(last),
                     'response_chars': len(response),
                     'session_sha256': hashlib.sha256((p.parent / 'session.jsonl').read_bytes()).hexdigest()})
    report[job] = {'expected': expected, 'completed': len(rows),
                   'correct': sum((x['reward'] or 0) > 0 for x in rows),
                   'all_llm_judge': all(x['method'] == 'llm_judge' for x in rows),
                   'all_final_selection_matches': all(x['final_selection_matches'] for x in rows),
                   'tasks': rows}
print(json.dumps(report, ensure_ascii=False, indent=2))
