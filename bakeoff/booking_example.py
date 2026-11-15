"""Portable booking evidence. Replay uses only the standard library."""
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from .evidence import example_file

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/bookings'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_booking_example(folder=EXAMPLE):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    for name, expected in manifest.items():
        if sha(example_file(folder, name).read_bytes()) != expected:
            raise ValueError('Booking example fingerprint mismatch: ' + name)
    record = json.loads(example_file(folder, 'run.json').read_text())
    frozen = json.loads(example_file(folder, 'frozen.json').read_text())
    if record.get('task') != 'bookings' or record.get('recorded') is not True:
        raise ValueError('Not a recorded booking experiment.')
    if sha(json.dumps(frozen['cases'], sort_keys=True).encode()) != frozen['case_manifest_sha256']:
        raise ValueError('Frozen assessment fingerprint mismatch.')
    if len(frozen['cases']) != 48 or len({c['id'] for c in frozen['cases']}) != 48:
        raise ValueError('Incomplete frozen assessment.')
    if [l['lane'] for l in record['lanes']] != [f'lane-{i}' for i in range(1, 6)]:
        raise ValueError('Expected five lanes.')
    required = {'run.json', 'frozen.json', 'SPEC.md', 'test_visible.py', 'judge-source.py'}
    for lane in record['lanes']:
        required.update((lane['source_path'], lane['results_path']))
        if sha(example_file(folder, lane['source_path']).read_bytes()) != lane['source_sha256']:
            raise ValueError('Answer differs from saved commit fingerprint.')
        for draft in lane['drafts']:
            required.add(draft['path'])
            if sha(example_file(folder, draft['path']).read_bytes()) != draft['sha256']:
                raise ValueError('Draft fingerprint mismatch.')
        observations = json.loads(example_file(folder, lane['results_path']).read_text())
        if len(observations) != 48:
            raise ValueError('Missing observations.')
        for case, observed in zip(frozen['cases'], observations):
            if {k: observed[k] for k in case} != case:
                raise ValueError('Observed case differs from frozen question.')
            original = json.loads(json.dumps(ast.literal_eval(case['input_literal'])))
            expected = {**case['expected'], 'input_after_call': original}
            if case['expected']['kind'] == 'windows':
                expected['input_after_output_edit'] = original
            matches = (observed['sandbox_status'] == 'finished' and observed['returncode'] == 0 and
                       json.dumps(observed['actual'], sort_keys=True) == json.dumps(expected, sort_keys=True))
            if observed['passed'] is not matches:
                raise ValueError('Observation disagrees with verdict.')
        if lane['passed'] != sum(c['passed'] for c in observations):
            raise ValueError('Summary disagrees with observations.')
        cost = (lane['input_tokens'] * Decimal(lane['input_usd_per_million']) +
                lane['output_tokens'] * Decimal(lane['output_usd_per_million'])) / 1_000_000
        if cost != Decimal(lane['estimated_usd']):
            raise ValueError('Cost accounting mismatch.')
    if not required.issubset(manifest):
        raise ValueError('Missing fingerprints.')
    if sum(Decimal(l['estimated_usd']) for l in record['lanes']) != Decimal(record['estimated_usd']):
        raise ValueError('Total cost mismatch.')
    return record, frozen


def replay_bookings(lane_name=None):
    try:
        record, frozen = read_booking_example()
        lanes = [l for l in record['lanes'] if not lane_name or l['lane'] == lane_name]
        if not lanes:
            raise ValueError('Choose lane-1 through lane-5.')
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('Cannot read booking example: ' + str(error))
        return 1
    print('RECORDED BOOKING EXPERIMENT — no model calls or candidate execution.\n')
    print('Task: combine overlapping or touching bookings; preserve original input.')
    print('Example: [[60,120],[90,150]] becomes [[60,150]].')
    print('48 original cases were frozen before the first request. No post-hoc review cases were added.\n')
    for lane in lanes:
        print(f"{lane['model']}: {lane['passed']}/48; {lane['rounds']} requests; estimated ${Decimal(lane['estimated_usd']):.5f}")
        if lane_name:
            for draft in lane['drafts']:
                print(f"  Draft {draft['number']}: {draft['explanation']}\n  File: {draft['path']}")
    print(f"\nRace: {record['seconds']:.2f}s; peak overlapping requests: {record['peak_inflight_requests']}.")
    print(f"Total estimated model cost: ${record['estimated_usd']} (not a provider bill).")
    print('Selection: ' + record['selection_reason'])
    print('Evidence: examples/bookings/README.md')
    return 0


def recheck_bookings():
    import tempfile
    from .booking_judge import check_booking_case
    from .config import ROOT
    from .race import save_json
    from .sandbox_check import run_checks
    record, frozen = read_booking_example()
    if sha(Path(__file__).with_name('booking_judge.py').read_bytes()) != frozen['judge_sha256']:
        raise ValueError('Judge differs from recorded version. Review changes before reproducing.')
    if not all(run_checks().values()):
        print('Sandbox checks failed.')
        return 1
    parent = ROOT / 'workdir'
    parent.mkdir(exist_ok=True)
    report = {'task': 'bookings', 'new_local_verification': True, 'lanes': []}
    for lane in record['lanes']:
        with tempfile.TemporaryDirectory(prefix='booking-recheck-', dir=parent) as temp:
            source = Path(temp)
            (source / 'tests').mkdir()
            for dest, origin in [('schedule.py', lane['source_path']), ('SPEC.md', 'SPEC.md'),
                                 ('tests/test_visible.py', 'test_visible.py')]:
                (source / dest).write_bytes(example_file(EXAMPLE, origin).read_bytes())
            checks = [check_booking_case(source, case) for case in frozen['cases']]
        original = json.loads(example_file(EXAMPLE, lane['results_path']).read_text())
        matched = [c['passed'] for c in checks] == [c['passed'] for c in original]
        report['lanes'].append({'lane': lane['lane'], 'matches_recording': matched, 'cases': checks})
        print(f"{lane['model']}: {sum(c['passed'] for c in checks)}/48; matches recording: {matched}", flush=True)
    folder = Path(tempfile.mkdtemp(prefix='booking-recheck-results-', dir=parent))
    save_json(folder / 'report.json', report)
    print('New local report: ' + str(folder / 'report.json'))
    return 0 if all(l['matches_recording'] for l in report['lanes']) else 1
