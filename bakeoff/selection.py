"""Keep one reviewed, rechecked commit without rewriting the competing answers."""
import json
from pathlib import Path
import shutil
import tempfile

from .judge import digest, HIDDEN, judge_lane, load_cases
from .race import save_json
from .repo import git
from .tasks import get_task


def keep_candidate(race, judge_file, lane_name, destination, *, verify=judge_lane):
    race, judge_file, destination = map(lambda p: Path(p).absolute(), (race, judge_file, destination))
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; refusing to overwrite it.')
    record = json.loads((race / 'race.json').read_text())
    assessment = json.loads(judge_file.read_text())
    task = get_task(record.get('task', 'money'))
    lane = next(r for r in record['lanes'] if r['lane'] == lane_name)
    verdict = next(r for r in assessment['lanes'] if r['lane'] == lane_name)
    baseline, commit = record['baseline_commit'], lane['candidate_commit']
    if task.name == 'bookings':
        from .booking_judge import read_frozen, judge_booking_lane
        frozen = read_frozen(race)
        cases = frozen['cases']
        suite_matches = assessment.get('assessment_commit') == git(race / 'assessment', 'rev-parse', 'HEAD').strip()
        if verify is judge_lane:
            verify = judge_booking_lane
    else:
        cases = load_cases()
        suite_matches = assessment.get('hidden_suite_sha256') == digest(HIDDEN.read_bytes())
    if (assessment['baseline_commit'] != baseline or verdict['commit'] != commit
            or not verdict['qualified'] or not suite_matches
            or assessment['case_manifest_sha256'] != digest(json.dumps(cases, sort_keys=True).encode())):
        raise ValueError('Judging evidence does not match this candidate and current suite.')
    repo = race / 'repo'
    if git(repo, 'branch', '--show-current').strip() != 'main':
        raise ValueError('The teaching repository must have main checked out.')
    if git(repo, 'status', '--porcelain').strip() or git(repo, 'rev-parse', 'HEAD').strip() != baseline:
        raise ValueError('Starting repository has changed; refusing to merge.')
    # A stored pass is useful evidence, but recheck the exact commit before keeping it.
    fresh = verify(race, lane, baseline, cases)
    if not fresh['qualified']:
        raise ValueError('Candidate failed its final verification; nothing was kept.')
    selection = {'task': task.name, 'stage': 7, 'lane': lane_name, 'model': lane['model'], 'commit': commit,
                 'baseline_commit': baseline, 'candidate_sha256': lane['candidate_sha256'],
                 'judge_record': str(judge_file), 'destination': str(destination),
                 'final_verification': fresh, 'status': 'prepared'}
    staging = Path(tempfile.mkdtemp(prefix='.keep-', dir=destination.parent))
    try:
        for name in task.files:
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git(repo, 'show', commit + ':' + name).encode())
        if digest((staging / task.answer).read_bytes()) != lane['candidate_sha256']:
            raise ValueError('Export differs from verified candidate.')
        save_json(staging / 'selection.json', selection)
        # Only the small race repository is merged; the outer user repository is not committed.
        git(repo, 'merge', '--ff-only', commit)
        staging.rename(destination)
        selection['status'] = 'kept'
        selection['main_commit'] = git(repo, 'rev-parse', 'main').strip()
        if selection['main_commit'] != commit:
            raise RuntimeError('Unexpected main commit after merge.')
        save_json(destination / 'selection.json', selection)
        save_json(race / 'selection.json', selection)
        return selection
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def keep_command(race, judge_file, lane, destination=None):
    from .config import ROOT
    from .sandbox_check import run_checks
    if not race or not judge_file or not lane:
        print('keep requires --race, --judge, and --lane. Review the candidates before choosing.')
        return 1
    try:
        if not all(run_checks().values()):
            print('Sandbox checks failed; nothing was kept.')
            return 1
        if destination is None:
            task_name = json.loads((Path(race) / 'race.json').read_text()).get('task', 'money')
            destination = ROOT / ('solution-bookings' if task_name == 'bookings' else 'solution')
        result = keep_candidate(race, judge_file, lane, destination)
    except (ValueError, RuntimeError, OSError, KeyError, StopIteration) as error:
        print(f'Could not keep the candidate ({type(error).__name__}). Inspect the paths and saved evidence.')
        return 1
    print(f"Kept {result['model']} from commit {result['commit']}.")
    print(f"Solution: {result['destination']}")
    print('The race repository main branch now points to this exact answer. Other lanes are retained.')
    return 0
