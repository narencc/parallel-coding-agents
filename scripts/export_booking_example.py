"""Export the completed second experiment without private logs or absolute paths."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bakeoff.booking_judge import read_frozen
from bakeoff.budget import RATES
from bakeoff.repo import git

RACE = ROOT / 'workdir/races/race-20261115T164405Z-o222yldv'
JUDGE = RACE / 'booking-judge-results-civ76_74/judge.json'
DEST = ROOT / 'examples/bookings'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def export():
    record = json.loads((RACE / 'race.json').read_text())
    judged = json.loads(JUDGE.read_text())
    kept = json.loads((RACE / 'selection.json').read_text())
    frozen = read_frozen(RACE)
    assert record['usage_complete'] and record['task'] == 'bookings'
    result = {'schema_version': 1, 'task': 'bookings', 'recorded': True, 'run_id': RACE.name,
              'date_utc': '2026-11-15', 'baseline_commit': record['baseline_commit'],
              'assessment_commit': judged['assessment_commit'], 'seconds': record['seconds'],
              'peak_inflight_requests': record['peak_inflight_requests'],
              'total_requests': record['budget']['calls_started'],
              'input_tokens': record['input_tokens'], 'output_tokens': record['output_tokens'],
              'estimated_usd': record['budget']['accounted_estimated_usd'],
              'cost_basis': 'Recorded standard uncached rates; not a provider bill or future-price guarantee',
              'selected_lane': kept['lane'], 'selected_commit': kept['commit'],
              'selection_reason': 'All five tied on the 48 prewritten cases. Sol 6.1 was chosen for explicit, separate validation and a clear copy-sort-merge sequence. This is a readability judgment.',
              'post_hoc_cases_added': 0, 'lanes': []}
    DEST.mkdir(parents=True, exist_ok=True)
    for name, source in [('SPEC.md', 'SPEC.md'), ('test_visible.py', 'tests/test_visible.py')]:
        data = git(RACE / 'repo', 'show', record['baseline_commit'] + ':' + source).encode()
        assert sha(data) == frozen['files'][source]
        (DEST / name).write_bytes(data)
    (DEST / 'frozen.json').write_bytes((RACE / 'assessment/frozen.json').read_bytes())
    judge_code = (ROOT / 'bakeoff/booking_judge.py').read_bytes()
    assert sha(judge_code) == frozen['judge_sha256']
    (DEST / 'judge-source.py').write_bytes(judge_code)
    for lane in record['lanes']:
        name = lane['lane']
        folder = DEST / 'lanes' / name
        folder.mkdir(parents=True, exist_ok=True)
        data = git(RACE / 'repo', 'show', lane['candidate_commit'] + ':schedule.py').encode()
        assert sha(data) == lane['candidate_sha256']
        (folder / 'schedule.py').write_bytes(data)
        observation = next(l for l in judged['lanes'] if l['lane'] == name)
        write(folder / 'results.json', observation['cases'])
        drafts=[]
        for draft in lane['drafts']:
            path = f"lanes/{name}/draft-{draft['number']:02d}.py"
            contents = (RACE / 'lanes' / name / 'drafts' / Path(path).name).read_bytes()
            assert sha(contents) == draft['sha256']
            (DEST / path).write_bytes(contents)
            drafts.append({k: draft[k] for k in ('number', 'round', 'explanation', 'sha256')} | {'path': path, 'practice_passed': draft['practice']['passed']})
        incoming,outgoing=RATES[lane['model']]
        cost=(lane['input_tokens']*incoming+lane['output_tokens']*outgoing)/1_000_000
        result['lanes'].append({'lane':name,'model':lane['model'],'commit':lane['candidate_commit'],
            'source_path':f'lanes/{name}/schedule.py','source_sha256':lane['candidate_sha256'],
            'results_path':f'lanes/{name}/results.json','drafts':drafts,'rounds':lane['rounds'],
            'input_tokens':lane['input_tokens'],'output_tokens':lane['output_tokens'],
            'input_usd_per_million':str(incoming),'output_usd_per_million':str(outgoing),
            'estimated_usd':str(cost),'requests':lane['requests'],
            'status':observation['status'],'passed':sum(c['passed'] for c in observation['cases']),'total':48})
    write(DEST/'run.json',result)
    paths=['run.json','frozen.json','SPEC.md','test_visible.py','judge-source.py']
    paths += [str(p.relative_to(DEST)) for p in sorted((DEST/'lanes').glob('*/*'))]
    write(DEST/'manifest.json',{name:sha((DEST/name).read_bytes()) for name in paths})
    print('Exported five booking candidates, all drafts, and the frozen assessment.')


if __name__=='__main__':
    export()
