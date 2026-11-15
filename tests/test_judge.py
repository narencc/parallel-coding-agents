import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bakeoff.judge import check_case, judge_lane, load_cases
from bakeoff.repo import git, prepare_race
from bakeoff.sandbox import SandboxResult


@pytest.mark.parametrize('output,status,code,passed', [
    ('{"kind":"int","value":29}', 'finished', 0, True),
    ('{"kind":"int","value":true}', 'finished', 0, False),
    ('{"kind":"int","value":29.0}', 'finished', 0, False),
    ('{"kind":"int","value":30}', 'finished', 0, False),
    ('{"kind":"int","value":29}', 'failed', 1, False),
    ('{"kind":"int","value":29}', 'timeout', -9, False),
    ('44 passed', 'finished', 0, False),
    ('', 'finished', 0, False),
    ('{"kind":"int","value":29}\n{"kind":"int","value":29}', 'finished', 0, False),
])
def test_host_marks_answers_and_rejects_forged_success(output, status, code, passed):
    execute = Mock(return_value=SandboxResult(status, code, output, 0.1))
    case = dict(id='exact', suite='hidden', input='0.29', expected={'kind':'int', 'value':29})
    assert check_case(None, case, execute=execute)['passed'] is passed
    program = execute.call_args.args[0]
    assert 'expected' not in program and 'passed' not in program


def test_case_manifest_is_complete():
    cases = load_cases()
    assert len(cases) == 44
    assert sum(c['suite'] == 'hidden' for c in cases) == 40
    assert sum(c['expected']['kind'] == 'ValueError' for c in cases) == 22


def test_judge_uses_commit_not_worktree_and_rejects_bad_fingerprint(tmp_path, monkeypatch):
    race, baseline = prepare_race(tmp_path.resolve())
    source = race / 'lanes/lane-1/candidate'
    code = b'def parse_inr(text): return 29\n'
    (source / 'money.py').write_bytes(code)
    git(source, 'add', 'money.py')
    git(source, 'commit', '-q', '-m', 'test answer')
    commit = git(source, 'rev-parse', 'HEAD').strip()
    (source / 'money.py').write_text('raise RuntimeError("worktree must not execute")')
    lane = dict(lane='lane-1', model='test', candidate_commit=commit,
                candidate_sha256=hashlib.sha256(code).hexdigest(),
                status='submitted_practice_passed', commit_verified=True)
    def check(snapshot, case):
        assert (snapshot / 'money.py').read_bytes() == code
        return {**case, 'passed': True}
    monkeypatch.setattr('bakeoff.judge.check_case', check)
    assert judge_lane(race, lane, baseline, load_cases())['qualified']
    lane['candidate_sha256'] = '0' * 64
    assert judge_lane(race, lane, baseline, load_cases())['status'] == 'rejected'
    lane['candidate_sha256'] = hashlib.sha256(code).hexdigest()
    assert not judge_lane(race, lane, baseline, [])['qualified']


def test_actual_sandbox_rejects_early_exit_and_fake_test_claims(tmp_path):
    from bakeoff.config import SAMPLE
    import shutil
    folder = tmp_path.resolve() / 'source'
    shutil.copytree(SAMPLE, folder)
    case = dict(id='exact', suite='hidden', input='0.29', expected={'kind':'int', 'value':29})
    (folder / 'money.py').write_text('import os\nprint("44 passed", flush=True)\nos._exit(0)\n')
    assert not check_case(folder, case)['passed']
    (folder / 'money.py').write_text('def parse_inr(text): return 29\n')
    assert check_case(folder, case)['passed']
