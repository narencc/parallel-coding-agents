"""Practice checks: shown to every coding agent."""

import pytest

from money import parse_inr


def test_rupee_sign():
    assert parse_inr("₹500") == 50000


def test_currency_marker_and_commas():
    assert parse_inr("Rs. 1,250") == 125000


def test_decimal_amount():
    assert parse_inr("INR 99.50") == 9950


def test_reject_unknown_word():
    with pytest.raises(ValueError):
        parse_inr("abc")
