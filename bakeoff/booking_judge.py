"""Prewritten booking assessment. Expected answers stay in the trusted host."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile

from .config import LANES
from .race import save_json
from .repo import git
from .sandbox import run_python
from .sandbox_check import run_checks
from .tasks import BOOKINGS

ASSESSMENT = BOOKINGS.source / 'assessment.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_booking_cases():
    cases = json.loads(ASSESSMENT.read_text())
    if len(cases) != 48 or len({c['id'] for c in cases}) != 48:
        raise ValueError('Expected all 48 distinct prewritten booking cases.')
    for case in cases:
        ast.literal_eval(case['input_literal'])
    return cases


def freeze_assessment(race, baseline):
    """Write and commit the full protocol before any model request; never prompt it."""
    cases = load_booking_cases()
    files = {name: sha(git(race / 'repo', 'show', baseline + ':' + name).encode()) for name in BOOKINGS.files}
    frozen = {'task': 'bookings', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
              'baseline_commit': baseline, 'files': files, 'cases': cases,
              'case_manifest_sha256': sha(json.dumps(cases, sort_keys=True).encode()),
              'judge_sha256': sha(Path(__file__).read_bytes()),
              'rules': 'All 48 cases required. Original assessment fixed before requests; no post-assessment revisions.',
              'selection_policy': 'Only full passes qualify. Review correctness and clarity; report subjective tie-breaks explicitly.'}
    protocol = race / 'assessment'
    protocol.mkdir()
    save_json(protocol / 'frozen.json', frozen)
    git(protocol, 'init', '-q', '-b', 'main')
    git(protocol, 'config', 'user.name', 'bakeoff learning project')
    git(protocol, 'config', 'user.email', 'bakeoff@localhost')
    git(protocol, 'add', 'frozen.json')
    git(protocol, 'commit', '-q', '-m', 'Freeze booking assessment before model requests')
    print('Assessment frozen before requests: ' + git(protocol, 'rev-parse', 'HEAD').strip(), flush=True)
    return frozen


def read_frozen(race):
    protocol = race / 'assessment'
    data = (protocol / 'frozen.json').read_bytes()
    if git(protocol, 'show', 'HEAD:frozen.json').encode() != data or git(protocol, 'status', '--porcelain').strip():
        raise ValueError('Frozen assessment changed.')
    frozen = json.loads(data)
    if frozen['case_manifest_sha256'] != sha(json.dumps(frozen['cases'], sort_keys=True).encode()):
        raise ValueError('Frozen case fingerprint mismatch.')
    if frozen['judge_sha256'] != sha(Path(__file__).read_bytes()):
        raise ValueError('Judge changed since assessment freeze; do not silently reinterpret results.')
    return frozen


def check_booking_case(source, case, *, execute=run_python):
    value = ast.literal_eval(case['input_literal'])
    program = '''import json
from schedule import merge_windows
windows = INPUT
try:
    result = merge_windows(windows)
    valid_shape = type(result) is list and all(type(row) is list and len(row) == 2 and all(type(n) is int for n in row) for row in result)
    saved = json.loads(json.dumps(result)) if valid_shape else None
    after_call = json.loads(json.dumps(windows))
    if valid_shape:
        if result:
            result[0][0] = -999
        result.append([0, 1])
    record = {"kind": "windows" if valid_shape else "wrong_type", "value": saved,
              "input_after_call": after_call, "input_after_output_edit": windows}
except ValueError:
    record = {"kind": "ValueError", "input_after_call": windows}
except BaseException:
    record = {"kind": "exception"}
print(json.dumps(record), flush=True)
'''.replace('INPUT', repr(value))
    result = execute(program, source=source, timeout=2, files=BOOKINGS.files)
    actual = None
    reason = result.status
    if result.status == 'finished' and result.returncode == 0:
        try:
            actual = json.loads(result.output)
            unchanged = json.loads(json.dumps(value))
            if case['expected']['kind'] == 'ValueError':
                expected = {'kind': 'ValueError', 'input_after_call': unchanged}
            else:
                expected = {**case['expected'], 'input_after_call': unchanged, 'input_after_output_edit': unchanged}
            # Canonical JSON comparison distinguishes booleans/floats from integers.
            matched = json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
            reason = 'match' if matched else 'wrong_answer_or_mutation'
        except (ValueError, TypeError):
            reason = 'invalid_response'
    return {**case, 'actual': actual, 'passed': reason == 'match', 'reason': reason,
            'sandbox_status': result.status, 'returncode': result.returncode, 'seconds': result.seconds}


def judge_booking_lane(race, lane, baseline, cases):
    result = {'lane': lane['lane'], 'model': lane['model'], 'commit': lane.get('candidate_commit'),
              'qualified': False, 'cases': []}
    try:
        commit = result['commit']
        if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
            raise ValueError('Missing exact commit.')
        if lane['status'] != 'submitted_practice_passed' or not lane['commit_verified']:
            raise ValueError('No verified submitted candidate.')
        repo = race / 'repo'
        if git(repo, 'rev-parse', commit + '^').strip() != baseline:
            raise ValueError('Candidate does not have the common baseline as its parent.')
        if set(git(repo, 'diff', '--name-only', baseline, commit).splitlines()) != {BOOKINGS.answer}:
            raise ValueError('Unexpected files changed.')
        code = git(repo, 'show', commit + ':schedule.py').encode()
        if sha(code) != lane['candidate_sha256']:
            raise ValueError('Candidate fingerprint mismatch.')
        with tempfile.TemporaryDirectory(prefix='booking-judge-', dir=race) as temp:
            source = Path(temp)
            for name in BOOKINGS.files:
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(code if name == BOOKINGS.answer else git(repo, 'show', baseline + ':' + name).encode())
            result['cases'] = [check_booking_case(source, c) for c in cases]
        result['qualified'] = len(result['cases']) == 48 and all(c['passed'] for c in result['cases'])
        result['status'] = 'qualified' if result['qualified'] else 'failed_tests'
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        result['status'] = 'rejected'
        result['error'] = str(error)
    result['hidden_passed'] = sum(c['passed'] for c in result['cases'] if c['suite'] == 'hidden')
    result['practice_passed'] = sum(c['passed'] for c in result['cases'] if c['suite'] == 'practice')
    return result


def judge_bookings(race_path):
    race = Path(race_path).resolve()
    record = json.loads((race / 'race.json').read_text())
    frozen = read_frozen(race)
    baseline = record['baseline_commit']
    if record.get('task') != 'bookings' or baseline != frozen['baseline_commit']:
        raise ValueError('Wrong task or baseline.')
    if [(l['lane'], l['model']) for l in record['lanes']] != [(l.name, l.model) for l in LANES]:
        raise ValueError('Expected all five configured lanes.')
    if not all(run_checks().values()):
        print('Sandbox checks failed; assessment stopped.')
        return 1
    for name, expected in frozen['files'].items():
        if sha(git(race / 'repo', 'show', baseline + ':' + name).encode()) != expected:
            raise ValueError('Baseline differs from frozen assignment.')
    main_before = git(race / 'repo', 'rev-parse', 'main').strip()
    folder = Path(tempfile.mkdtemp(prefix='booking-judge-results-', dir=race))
    result = {'task': 'bookings', 'stage': 6, 'baseline_commit': baseline,
              'assessment_commit': git(race / 'assessment', 'rev-parse', 'HEAD').strip(),
              'case_manifest_sha256': frozen['case_manifest_sha256'], 'expected_hidden': 44,
              'expected_practice': 4, 'lanes': [], 'winner': None}
    for lane in record['lanes']:
        print(f"Judging {lane['model']} against the prewritten cases...", flush=True)
        verdict = judge_booking_lane(race, lane, baseline, frozen['cases'])
        result['lanes'].append(verdict)
        save_json(folder / 'judge.json', result)
        print(f"  {verdict['hidden_passed']}/44 hidden, {verdict['practice_passed']}/4 practice: {verdict['status']}", flush=True)
    result['main_preserved_during_judging'] = git(race / 'repo', 'rev-parse', 'main').strip() == main_before
    result['qualified_lanes'] = [l['lane'] for l in result['lanes'] if l['qualified']]
    save_json(folder / 'judge.json', result)
    print(f'Results: {folder / "judge.json"}', flush=True)
    return 0 if result['main_preserved_during_judging'] and result['qualified_lanes'] else 1
