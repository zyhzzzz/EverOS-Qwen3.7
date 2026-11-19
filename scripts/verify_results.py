"""Independently recount the published score-only evidence."""
from pathlib import Path
import csv
import json

r = Path(__file__).resolve().parents[1]
expected = {'run1': {'train': (154, 77), 'baseline': (65, 23), 'with-everos': (65, 29)},
            'run2': {'train': (154, 78), 'baseline': (65, 22), 'with-everos': (65, 29)}}
for name, jobs in expected.items():
    with (r / f'evidence/{name}_tasks.csv').open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for job, target in jobs.items():
        subset = [x for x in rows if x['job'] == job]
        n, correct = len(subset), sum(float(x['reward']) > 0 for x in subset)
        assert (n, correct) == target
        assert len({x['task_id'] for x in subset}) == n
        assert all(x['method'] == 'llm_judge' for x in subset)
        assert all(x['final_selection_matches'] == 'True' for x in subset)
        print(f'{name} {job}: {correct}/{n} = {correct/n:.2%}')
    a = {x['task_id'] for x in rows if x['job'] == 'train'}
    b = {x['task_id'] for x in rows if x['job'] == 'baseline'}
    assert not a & b
    assert b == {x['task_id'] for x in rows if x['job'] == 'with-everos'}
print('PASS. This verifies exported bookkeeping, not independent semantic rejudging.')
