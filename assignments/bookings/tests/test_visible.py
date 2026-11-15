import pytest
from schedule import merge_windows


def test_empty():
    assert merge_windows([]) == []


def test_overlap():
    assert merge_windows([[60, 120], [90, 150]]) == [[60, 150]]


def test_sort_and_preserve_gap():
    assert merge_windows([[180, 240], [60, 120]]) == [[60, 120], [180, 240]]


def test_reject_backward_window():
    with pytest.raises(ValueError):
        merge_windows([[120, 60]])
