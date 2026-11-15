"""Host-owned verdicts over exact saved commits; candidate execution stays sandboxed."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile

from .config import ROOT, LANES
from .race import save_json
from .repo import git
from .sandbox import run_python
from .sandbox_check import run_checks

HIDDEN = ROOT / 'hidden_tests/test_hidden.py'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_cases():
    # Read literal test data without importing the test module (or candidate).
    tree = ast.parse(HIDDEN.read_text())
    cases = []
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        if fn.name not in ('test_valid_amount', 'test_invalid_amount'):
            raise ValueError('Unrecognized hidden test function.')
        valid = fn.name == 'test_valid_amount'
        decorator = fn.decorator_list[0]
        for item in decorator.args[1].elts:
            if ast.unparse(item.func) != 'pytest.param':
                raise ValueError('Expected literal pytest parameters.')
            values = [ast.literal_eval(arg) for arg in item.args]
            case_id = next(ast.literal_eval(k.value) for k in item.keywords if k.arg == 'id')
            cases.append(dict(id=case_id, suite='hidden', input=values[0],
                              expected={'kind': 'int', 'value': values[1]} if valid else {'kind': 'ValueError'}))
    if len(cases) != 40 or len({c['id'] for c in cases}) != 40:
        raise ValueError('Expected exactly 40 unique hidden cases; review the judge adapter.')
    for name, value, expected in [('rupee-sign', '₹500', 50000), ('commas', 'Rs. 1,250', 125000),
                                   ('decimal', 'INR 99.50', 9950), ('unknown-word', 'abc', None)]:
        cases.append(dict(id=name, suite='practice', input=value,
                          expected={'kind': 'ValueError'} if expected is None else {'kind': 'int', 'value': expected}))
    return cases


def check_case(source, case, *, execute=run_python):
    # No expected answers or pass/fail logic enter the child process.
    program = '''import json
from money import parse_inr
try:
    value = parse_inr(INPUT)
    answer = {"kind": "int", "value": value} if type(value) is int else {"kind": "wrong_type"}
except ValueError:
    answer = {"kind": "ValueError"}
except BaseException:
    answer = {"kind": "exception"}
print(json.dumps(answer), flush=True)
'''.replace('INPUT', repr(case['input']))
    result = execute(program, source=source, timeout=2)
    actual = None
    reason = result.status
    if result.status == 'finished' and result.returncode == 0:
        try:
            actual = json.loads(result.output)
            # bool equals int in Python: explicitly require exact types and schema.
            well_formed = (type(actual) is dict and (
                actual == {'kind': 'ValueError'} or
                (set(actual) == {'kind', 'value'} and actual['kind'] == 'int' and type(actual['value']) is int)))
            reason = 'match' if well_formed and actual == case['expected'] else 'wrong_answer'
        except (ValueError, TypeError):
            reason = 'invalid_response'
    return {**case, 'passed': reason == 'match', 'reason': reason, 'actual': actual,
            'sandbox_status': result.status, 'returncode': result.returncode, 'seconds': result.seconds,
            'output_tail': result.output[-2000:] if reason != 'match' else ''}


def judge_lane(race, lane, baseline, cases):
    result = {'lane': lane['lane'], 'model': lane['model'], 'commit': lane.get('candidate_commit'),
              'qualified': False, 'cases': []}
    try:
        commit = result['commit']
        if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('Missing exact commit ID.')
        repo = race / 'repo'
        if lane.get('status') != 'submitted_practice_passed' or not lane.get('commit_verified'):
            raise ValueError('Lane did not submit a verified candidate.')
        if git(repo, 'rev-parse', commit + '^').strip() != baseline:
            raise ValueError('Candidate is not based directly on the shared starting commit.')
        changed = set(git(repo, 'diff', '--name-only', baseline, commit).splitlines())
        if changed != {'money.py'}:
            raise ValueError('Candidate changed files outside the allowed answer.')
        code = git(repo, 'show', commit + ':money.py').encode()
        if digest(code) != lane.get('candidate_sha256'):
            raise ValueError('Saved candidate fingerprint does not match the race record.')
        with tempfile.TemporaryDirectory(prefix='judge-source-', dir=race) as temp:
            source = Path(temp).resolve()
            for name in ('money.py', 'SPEC.md', 'tests/test_visible.py'):
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(code if name == 'money.py' else git(repo, 'show', baseline + ':' + name).encode())
            result['cases'] = [check_case(source, case) for case in cases]
        result['qualified'] = len(result['cases']) == 44 and all(c['passed'] for c in result['cases'])
        result['status'] = 'qualified' if result['qualified'] else 'failed_tests'
    except (ValueError, RuntimeError, OSError) as error:
        result['status'] = 'rejected'
        result['error'] = str(error)
    result['hidden_passed'] = sum(c['passed'] for c in result['cases'] if c['suite'] == 'hidden')
    result['practice_passed'] = sum(c['passed'] for c in result['cases'] if c['suite'] == 'practice')
    return result


def judge_command(race_path=None):
    if race_path is None:
        print('Specify the saved race folder with --race. No latest-folder guessing.')
        return 1
    race = Path(race_path).expanduser().resolve()
    record = json.loads((race / 'race.json').read_text())
    baseline = record['baseline_commit']
    if not re.fullmatch(r'[0-9a-f]{40}', baseline):
        raise ValueError('Invalid baseline commit.')
    lanes = record['lanes']
    if [(r['lane'], r['model']) for r in lanes] != [(l.name, l.model) for l in LANES]:
        raise ValueError('Expected the five configured lanes exactly once.')
    main_before = git(race / 'repo', 'rev-parse', 'main').strip()
    cases = load_cases()
    print('STEP 6: Marking exact saved answers. No API calls or model revisions.', flush=True)
    if not all(run_checks().values()):
        print('Sandbox checks failed. Judging stopped.')
        return 1
    folder = Path(tempfile.mkdtemp(prefix='judge-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=race))
    result = {'stage': 6, 'baseline_commit': baseline, 'hidden_suite_sha256': digest(HIDDEN.read_bytes()),
              'case_manifest_sha256': digest(json.dumps(cases, sort_keys=True).encode()),
              'expected_hidden': 40, 'expected_practice': 4, 'lanes': [], 'winner': None}
    for lane in lanes:
        print(f"Marking {lane['lane']} ({lane['model']})...", flush=True)
        verdict = judge_lane(race, lane, baseline, cases)
        result['lanes'].append(verdict)
        save_json(folder / 'judge.json', result)
        print(f"  {verdict['hidden_passed']}/40 hidden; {verdict['practice_passed']}/4 practice; {verdict['status']}", flush=True)
    result['main_unchanged'] = git(race / 'repo', 'rev-parse', 'main').strip() == baseline
    result['main_preserved_during_judging'] = git(race / 'repo', 'rev-parse', 'main').strip() == main_before
    result['qualified_lanes'] = [r['lane'] for r in result['lanes'] if r['qualified']]
    save_json(folder / 'judge.json', result)
    lines = ['# Hidden-test judging results', '', '| Lane | Model | Hidden | Practice | Verdict |',
             '| --- | --- | --- | --- | --- |']
    for r in result['lanes']:
        lines.append(f"| {r['lane']} | {r['model']} | {r['hidden_passed']}/40 | {r['practice_passed']}/4 | {r['status']} |")
    lines += ['', 'A qualifier passed this fixed suite; it is not proof of correctness for every possible input.',
              'No model received feedback, no winner was selected, and no candidate was merged.', '']
    (folder / 'RESULTS.md').write_text('\n'.join(lines))
    print(f'Results: {folder / "RESULTS.md"}', flush=True)
    return 0 if result['main_preserved_during_judging'] and result['qualified_lanes'] else 1
