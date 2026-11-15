"""Offline tests: concurrency, separate worktrees, failures, and shared budgets."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bakeoff.agent import run_agent
from bakeoff.budget import BudgetExceeded, RaceBudget
from bakeoff.config import LANES
from bakeoff.race import execute_race
from bakeoff.repo import git, prepare_race, record_candidate
from test_agent import feedback, reply, write


def test_budget_reservations_are_atomic_and_unknown_usage_is_retained():
    budget = RaceBudget('0.03')
    def reserve(_):
        try:
            return budget.reserve('gpt-6-astra', 0, 0)
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=5) as pool:
        tickets = [t for t in pool.map(reserve, range(5)) if t]
    assert len(tickets) == 1
    budget.settle(tickets[0], None)
    state = budget.snapshot()
    assert state['unknown_requests'] == 1
    assert Decimal(state['accounted_estimated_usd']) == Decimal('0.02048')
    assert Decimal(state['reserved_estimated_usd']) == 0


def test_five_real_worktrees_run_overlapping_independent_conversations(tmp_path):
    race, baseline = prepare_race(tmp_path.resolve())
    barrier = threading.Barrier(5)
    seen = []
    lock = threading.Lock()
    class Client:
        def __init__(self, **kwargs):
            self.responses = self
            self.calls = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                with lock:
                    seen.append(kwargs['model'])
                barrier.wait(timeout=10)
                return write('# independent ' + kwargs['model'])
            return reply('submit', {'summary': 'Reviewed.'})
    def runner(client, folder, **kwargs):
        return run_agent(client, folder, checker=Mock(side_effect=[feedback(0), feedback(4)]), **kwargs)
    result = execute_race(race, baseline, 'fake-key', client_factory=Client, runner=runner)
    assert set(seen) == {lane.model for lane in LANES}
    assert result['peak_inflight_requests'] == 5
    assert result['main_unchanged'] and not result['hidden_tests_run']
    assert result['winner'] is None
    assert result['budget']['calls_started'] == 10
    commits = []
    for report in result['lanes']:
        assert report['status'] == 'submitted_practice_passed'
        assert report['commit_verified']
        candidate = race / 'lanes' / report['lane'] / 'candidate'
        assert git(candidate, 'branch', '--show-current').strip() == report['branch']
        assert git(candidate, 'rev-parse', 'HEAD^').strip() == baseline
        assert report['model'] in (candidate / 'money.py').read_text()
        commits.append(report['candidate_commit'])
    assert len(set(commits)) == 5
    assert 'NotImplementedError' in (race / 'repo/money.py').read_text()
    # A changed file cannot be committed using an earlier test record.
    lane_folder = race / 'lanes/lane-1'
    (lane_folder / 'candidate/money.py').write_text('# tampered')
    with pytest.raises(RuntimeError, match='changed'):
        record_candidate(lane_folder, result['lanes'][0], baseline)


def test_failed_lane_does_not_abort_other_lanes(tmp_path):
    race, baseline = prepare_race(tmp_path.resolve())
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def runner(client, folder, **kwargs):
        if kwargs['lane'].name == 'lane-3':
            raise RuntimeError('private provider detail')
        fake = Mock()
        fake.responses.create.side_effect = [write(), reply('submit', {'summary': 'done'})]
        return run_agent(fake, folder, checker=Mock(side_effect=[feedback(0), feedback(4)]), **kwargs)
    result = execute_race(race, baseline, 'fake', client_factory=Client, runner=runner)
    assert [r['status'] for r in result['lanes']].count('submitted_practice_passed') == 4
    assert result['lanes'][2]['status'] == 'lane_error'
    assert 'private provider detail' not in (race / 'race.json').read_text()
    assert result['main_unchanged']
