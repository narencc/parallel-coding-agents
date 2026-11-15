"""Export this completed experiment using explicit fields, never whole private logs.

Run from the repository root: .venv/bin/python scripts/export_example.py
No candidate is imported or executed. The original local run remains unchanged.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bakeoff.budget import RATES
from bakeoff.repo import git

RACE = ROOT / 'workdir/races/race-20261115T155112Z-rdly1111'
DEST = ROOT / 'examples/money-converter'
JUDGE = RACE / 'judge-20261115T155616Z-ca5yn801/judge.json'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def clean_case(case):
    # Exclude raw output tails, which can contain host paths. Preserve observations.
    return {k: case[k] for k in ('id', 'suite', 'input', 'expected', 'actual', 'passed',
                                 'reason', 'sandbox_status', 'returncode', 'seconds')}


def export():
    record = json.loads((RACE / 'race.json').read_text())
    judge = json.loads(JUDGE.read_text())
    review = json.loads((RACE / 'review-cases.json').read_text())
    selection = json.loads((RACE / 'selection.json').read_text())
    assert record['usage_complete'] and all(l['commit_verified'] for l in record['lanes'])
    assert hashlib.sha256((ROOT / 'hidden_tests/test_hidden.py').read_bytes()).hexdigest() == judge['hidden_suite_sha256']
    for name in ('SPEC.md', 'tests/test_visible.py'):
        assert (ROOT / 'sample' / name).read_bytes() == git(RACE / 'repo', 'show', record['baseline_commit'] + ':' + name).encode()
    public = {'schema_version': 1, 'recorded': True, 'run_id': RACE.name,
              'date_utc': '2026-11-15', 'task': 'money-converter',
              'baseline_commit': record['baseline_commit'], 'seconds': record['seconds'],
              'peak_inflight_requests': record['peak_inflight_requests'],
              'total_requests': record['budget']['calls_started'],
              'input_tokens': record['input_tokens'], 'output_tokens': record['output_tokens'],
              'estimated_usd': record['budget']['accounted_estimated_usd'],
              'rates_checked': record['budget']['rates_checked'],
              'cost_basis': 'Recorded standard uncached input/output rates; not a provider bill or future-price quote',
              'original_cases_sha256': judge['case_manifest_sha256'],
              'review_cases_sha256': review['case_manifest_sha256'],
              'selected_lane': selection['lane'],
              'selection_reason': 'The top three tied on observed checks; Astra was chosen for a clear single-function flow. This is a review judgment, not a model ranking.',
              'lanes': []}
    for lane in record['lanes']:
        name = lane['lane']
        original = next(r for r in judge['lanes'] if r['lane'] == name)
        extra = next(r for r in review['lanes'] if r['lane'] == name)
        folder = DEST / 'lanes' / name
        folder.mkdir(parents=True, exist_ok=True)
        code = git(RACE / 'repo', 'show', lane['candidate_commit'] + ':money.py').encode()
        assert hashlib.sha256(code).hexdigest() == lane['candidate_sha256']
        (folder / 'money.py').write_bytes(code)
        drafts = []
        for draft in lane['drafts']:
            filename = f"draft-{draft['number']:02d}.py"
            data = (RACE / 'lanes' / name / 'drafts' / filename).read_bytes()
            assert hashlib.sha256(data).hexdigest() == draft['sha256']
            (folder / filename).write_bytes(data)
            drafts.append({'number': draft['number'], 'round': draft['round'],
                           'path': f'lanes/{name}/{filename}', 'sha256': draft['sha256'],
                           'explanation': draft['explanation'],
                           'practice_passed': (draft.get('practice') or {}).get('passed'),
                           'practice_total': (draft.get('practice') or {}).get('total')})
        original_cases = [clean_case(c) for c in original['cases']]
        review_cases = [clean_case(c) for c in extra['cases']]
        write_json(folder / 'original-results.json', original_cases)
        write_json(folder / 'review-results.json', review_cases)
        incoming, outgoing = RATES[lane['model']]
        cost = (lane['input_tokens'] * incoming + lane['output_tokens'] * outgoing) / 1_000_000
        public['lanes'].append({
            'lane': name, 'model': lane['model'], 'commit': lane['candidate_commit'],
            'source_path': f'lanes/{name}/money.py', 'source_sha256': lane['candidate_sha256'],
            'status': lane['status'], 'rounds': lane['rounds'], 'drafts': drafts,
            'input_tokens': lane['input_tokens'], 'output_tokens': lane['output_tokens'],
            'input_usd_per_million': str(incoming), 'output_usd_per_million': str(outgoing),
            'estimated_usd': str(cost), 'requests': lane['requests'],
            'original_results': f'lanes/{name}/original-results.json',
            'review_results': f'lanes/{name}/review-results.json',
            'original_passed': sum(c['passed'] for c in original_cases), 'original_total': len(original_cases),
            'review_passed': sum(c['passed'] for c in review_cases), 'review_total': len(review_cases)})
    for name, origin in [('SPEC.md', ROOT / 'sample/SPEC.md'),
                         ('test_visible.py', ROOT / 'sample/tests/test_visible.py'),
                         ('test_hidden.py', ROOT / 'hidden_tests/test_hidden.py')]:
        (DEST / name).write_bytes(origin.read_bytes())
    write_json(DEST / 'run.json', public)
    paths = ['run.json', 'SPEC.md', 'test_visible.py', 'test_hidden.py']
    paths += [str(p.relative_to(DEST)) for p in sorted((DEST / 'lanes').glob('*/*'))]
    manifest = {name: hashlib.sha256((DEST / name).read_bytes()).hexdigest() for name in paths}
    write_json(DEST / 'manifest.json', manifest)
    print(f'Exported {len(public["lanes"])} lanes and {len(manifest)} fingerprinted files to examples/money-converter.')


if __name__ == '__main__':
    export()
