import json
from unittest.mock import Mock

import pytest

from bakeoff.judge import HIDDEN, digest, load_cases
from bakeoff.repo import git, prepare_race
from bakeoff.selection import keep_candidate


@pytest.fixture
def ready(tmp_path):
    race, baseline = prepare_race(tmp_path.resolve())
    candidate = race / 'lanes/lane-1/candidate'
    code = b'def parse_inr(text): return 100\n'
    (candidate / 'money.py').write_bytes(code)
    git(candidate, 'add', 'money.py')
    git(candidate, 'commit', '-q', '-m', 'fixture candidate')
    commit = git(candidate, 'rev-parse', 'HEAD').strip()
    lane = dict(lane='lane-1', model='test', candidate_commit=commit, candidate_sha256=digest(code))
    (race / 'race.json').write_text(json.dumps({'baseline_commit': baseline, 'lanes': [lane]}))
    assessment = dict(baseline_commit=baseline, hidden_suite_sha256=digest(HIDDEN.read_bytes()),
                      case_manifest_sha256=digest(json.dumps(load_cases(), sort_keys=True).encode()),
                      lanes=[dict(lane='lane-1', commit=commit, qualified=True)])
    evidence = race / 'judge.json'
    evidence.write_text(json.dumps(assessment))
    return race, baseline, commit, evidence, tmp_path.resolve() / 'solution', code


def test_keep_preserves_exact_code_and_fast_forwards_only_teaching_repo(ready):
    race, baseline, commit, evidence, target, code = ready
    result = keep_candidate(race, evidence, 'lane-1', target, verify=Mock(return_value={'qualified':True}))
    assert result['status'] == 'kept'
    assert (target / 'money.py').read_bytes() == code
    assert git(race / 'repo', 'rev-parse', 'main').strip() == commit
    assert git(race / 'repo', 'rev-parse', commit + '^').strip() == baseline
    assert len(git(race / 'repo', 'worktree', 'list').splitlines()) == 6
    with pytest.raises(ValueError, match='overwrite'):
        keep_candidate(race, evidence, 'lane-1', target)


@pytest.mark.parametrize('failure', ['fresh-tests', 'judge-commit', 'dirty-main'])
def test_rejection_does_not_merge_or_export(ready, failure):
    race, baseline, commit, evidence, target, code = ready
    verify = Mock(return_value={'qualified': failure != 'fresh-tests'})
    if failure == 'judge-commit':
        data = json.loads(evidence.read_text())
        data['lanes'][0]['commit'] = baseline
        evidence.write_text(json.dumps(data))
    if failure == 'dirty-main':
        (race / 'repo/money.py').chmod(0o600)
        (race / 'repo/money.py').write_text('# user edits')
    with pytest.raises(ValueError):
        keep_candidate(race, evidence, 'lane-1', target, verify=verify)
    assert not target.exists()
    assert git(race / 'repo', 'rev-parse', 'main').strip() == baseline
    if failure != 'fresh-tests':
        verify.assert_not_called()
