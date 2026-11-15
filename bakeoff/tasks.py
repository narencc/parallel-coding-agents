"""Explicit trusted task settings; models never choose filenames or test lists."""
from dataclasses import dataclass
from pathlib import Path
from .config import ROOT, SAMPLE


@dataclass(frozen=True)
class Task:
    name: str
    source: Path
    answer: str
    function: str
    practice_ids: frozenset

    @property
    def files(self):
        return ('SPEC.md', self.answer, 'tests/test_visible.py')


MONEY = Task('money', SAMPLE, 'money.py', 'parse_inr', frozenset(
    'tests/test_visible.py::' + name for name in (
        'test_rupee_sign', 'test_currency_marker_and_commas', 'test_decimal_amount', 'test_reject_unknown_word')))
BOOKINGS = Task('bookings', ROOT / 'assignments/bookings', 'schedule.py', 'merge_windows', frozenset(
    'tests/test_visible.py::' + name for name in (
        'test_empty', 'test_overlap', 'test_sort_and_preserve_gap', 'test_reject_backward_window')))
TASKS = {task.name: task for task in (MONEY, BOOKINGS)}


def get_task(name):
    return TASKS[name]
