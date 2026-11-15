"""Pre-run checks for the booking task, its sandbox boundary, and its judge."""
import ast
import json
from pathlib import Path
import shutil
from unittest.mock import Mock

import pytest

from bakeoff.agent import run_agent
from bakeoff.booking_judge import check_booking_case, freeze_assessment, load_booking_cases, read_frozen
from bakeoff.practice import check_practice
from bakeoff.repo import git, prepare_race, record_candidate
from bakeoff.sandbox import prepared_workspace
from bakeoff.tasks import BOOKINGS
from test_agent import write, reply

# Test fixture only; never included in the starting assignment or model prompt.
REFERENCE = '''def merge_windows(windows):
    if type(windows) is not list:
        raise ValueError()
    for row in windows:
        if type(row) is not list or len(row) != 2 or any(type(n) is not int for n in row):
            raise ValueError()
        if not 0 <= row[0] < row[1] <= 1440:
            raise ValueError()
    result = []
    for start, end in sorted(windows):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result
'''


@pytest.fixture
def source(tmp_path):
    folder = tmp_path.resolve() / 'source'
    shutil.copytree(BOOKINGS.source, folder)
    (folder / 'schedule.py').write_text(REFERENCE)
    return folder


def test_prewritten_answers_match_an_independent_minute_coverage_oracle():
    cases = load_booking_cases()
    assert sum(c['suite'] == 'hidden' for c in cases) == 44
    for case in cases:
        value = ast.literal_eval(case['input_literal'])
        valid = (type(value) is list and all(type(row) is list and len(row) == 2 and
                 all(type(n) is int for n in row) and 0 <= row[0] < row[1] <= 1440 for row in value))
        if not valid:
            assert case['expected'] == {'kind': 'ValueError'}
            continue
        minutes = {minute for start, end in value for minute in range(start, end)}
        expected = []
        for minute in sorted(minutes):
            if expected and expected[-1][1] == minute:
                expected[-1][1] = minute + 1
            else:
                expected.append([minute, minute + 1])
        assert case['expected'] == {'kind': 'windows', 'value': expected}


def test_reference_passes_all_frozen_cases_in_sandbox(source):
    assert all(check_booking_case(source, case)['passed'] for case in load_booking_cases())


@pytest.mark.parametrize('code,case_id', [
    ('def merge_windows(windows): return windows', 'singleton-no-alias'),
    ('def merge_windows(windows): return windows', 'practice-empty'),
    ('def merge_windows(windows):\n    windows.sort()\n    return [row[:] for row in windows]', 'unsorted-input-preserved'),
    ('def merge_windows(windows): return [(60, 120)]', 'singleton-no-alias'),
    ('def merge_windows(windows):\n    windows.sort()\n    raise ValueError()', 'late-invalid-no-mutation'),
    ('import os\nprint("48 passed", flush=True)\nos._exit(0)', 'practice-empty'),
])
def test_judge_rejects_mutation_aliasing_wrong_types_and_fake_passes(source, code, case_id):
    (source / 'schedule.py').write_text(code)
    case = next(c for c in load_booking_cases() if c['id'] == case_id)
    assert not check_booking_case(source, case)['passed']


def test_task_snapshot_excludes_assessment_and_rejects_arbitrary_copy_list(source):
    with prepared_workspace('', source, files=BOOKINGS.files) as snapshot:
        names = {str(p.relative_to(snapshot / 'source')) for p in (snapshot / 'source').rglob('*') if p.is_file()}
        assert names == set(BOOKINGS.files)
    with pytest.raises(ValueError, match='Unknown task copy list'):
        with prepared_workspace('', source, files=('assessment.json',)):
            pytest.fail('Must not accept assessment copy list')


def test_booking_agent_edits_only_schedule_and_preserves_frozen_protocol(tmp_path):
    race, baseline = prepare_race(tmp_path.resolve(), task=BOOKINGS)
    freeze_assessment(race, baseline)
    frozen = read_frozen(race)
    folder = race / 'lanes/lane-1'
    client = Mock()
    client.responses.create.side_effect = [write(REFERENCE), reply('submit', {'summary': 'Reviewed.'})]
    report = run_agent(client, folder, task=BOOKINGS)
    assert report['status'] == 'submitted_practice_passed'
    assert report['task'] == 'bookings'
    request = client.responses.create.call_args.kwargs
    assert 'merge_windows' in request['instructions']
    assert 'money.py' not in request['instructions']
    assert 'assessment.json' not in request['input'][0]['content']
    commit = record_candidate(folder, report, baseline, task=BOOKINGS)
    assert git(folder / 'candidate', 'show', commit + ':schedule.py') == REFERENCE
    assert not (folder / 'candidate/money.py').exists()
    assert frozen == read_frozen(race)
    from bakeoff.selection import keep_candidate
    from bakeoff.race import save_json
    save_json(race / 'race.json', {'task': 'bookings', 'baseline_commit': baseline, 'lanes': [dict(report, candidate_commit=commit, commit_verified=True)]})
    save_json(race / 'judge.json', {'baseline_commit': baseline, 'case_manifest_sha256': frozen['case_manifest_sha256'],
        'assessment_commit': git(race / 'assessment', 'rev-parse', 'HEAD').strip(),
        'lanes': [{'lane': report['lane'], 'commit': commit, 'qualified': True}]})
    kept = keep_candidate(race, race / 'judge.json', report['lane'], tmp_path.resolve() / 'kept')
    assert kept['task'] == 'bookings'
    assert (tmp_path.resolve() / 'kept/schedule.py').read_text() == REFERENCE
    (race / 'assessment/frozen.json').write_text('{}')
    with pytest.raises(ValueError, match='changed'):
        read_frozen(race)
