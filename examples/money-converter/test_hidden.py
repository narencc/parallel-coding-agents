"""Assessment cases: omitted from future prompts, not a security boundary."""

import pytest

from money import parse_inr


@pytest.mark.parametrize("text, expected", [
    pytest.param("₹1,25,000.50", 12500050, id="indian-grouping"),
    pytest.param("0.29", 29, id="exact-paise"),
    pytest.param("1.2 lakh", 12000000, id="lakh"),
    pytest.param("3 crore", 3000000000, id="crore"),
    pytest.param("2.5Cr", 2500000000, id="suffix-without-space"),
    pytest.param("1.2345 lakh", 12345000, id="suffix-precision"),
    pytest.param("Rs 5 k", 500000, id="thousand"),
    pytest.param("1,2,3", 12300, id="irregular-grouping"),
    pytest.param("(₹200)", -20000, id="parentheses"),
    pytest.param("-Rs 15", -1500, id="minus"),
    pytest.param("  inr 7  ", 700, id="case-and-whitespace"),
    pytest.param("Rs.500", 50000, id="marker-without-space"),
    pytest.param("0.000001 lakh", 10, id="small-exact-suffix"),
    pytest.param("-0.00", 0, id="negative-zero"),
    pytest.param("2 LAKHS", 20000000, id="plural-lakhs"),
    pytest.param("1 crores", 1000000000, id="plural-crores"),
    pytest.param("( INR 1.50 )", -150, id="parentheses-whitespace"),
    pytest.param("1l", 10000000, id="short-lakh"),
    pytest.param("1000000000000000000000000000.29", 100000000000000000000000000029,
                 id="large-exact-amount"),
])
def test_valid_amount(text, expected):
    result = parse_inr(text)
    assert type(result) is int, "Return an integer number of paise, not a float or bool."
    assert result == expected


@pytest.mark.parametrize("text", [
    pytest.param("₹12.345", id="too-many-decimals"),
    pytest.param("", id="empty"),
    pytest.param("1.2.3", id="two-decimal-points"),
    pytest.param("₹ lakh", id="no-number"),
    pytest.param("₹1e5", id="scientific-notation"),
    pytest.param("(200", id="unbalanced-parentheses"),
    pytest.param("--200", id="double-minus"),
    pytest.param("500 INR", id="marker-after-number"),
    pytest.param("0.00000001 lakh", id="fractional-paisa"),
    pytest.param("(-200)", id="two-negative-forms"),
    pytest.param("+200", id="plus-sign"),
    pytest.param(".50", id="missing-integer-part"),
    pytest.param("1.", id="missing-fractional-part"),
    pytest.param(",100", id="leading-comma"),
    pytest.param("100,", id="trailing-comma"),
    pytest.param("1,,00", id="consecutive-commas"),
    pytest.param("1.2,5", id="fractional-comma"),
    pytest.param("1 000", id="space-inside-number"),
    pytest.param("1 million", id="unknown-suffix"),
    pytest.param("１２", id="non-ascii-digits"),
    pytest.param(None, id="non-string"),
])
def test_invalid_amount(text):
    with pytest.raises(ValueError):
        parse_inr(text)
