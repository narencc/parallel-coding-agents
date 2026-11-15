"""Exact parsing of written Indian rupee amounts."""

import re


_AMOUNT = re.compile(
    r"(?:(?ai:₹|rs\.?|inr)\s*)?"
    r"([0-9]+(?:,[0-9]+)*)(?:\.([0-9]+))?"
    r"(?:\s*((?ai:k|l|lakh|lakhs|cr|crore|crores)))?" 
)
_PLACES = {"k": 5, "l": 7, "lakh": 7, "lakhs": 7,
           "cr": 9, "crore": 9, "crores": 9}


def parse_inr(text: str) -> int:
    """Convert written rupees into exact whole paise; reject invalid syntax."""
    if not isinstance(text, str):
        raise ValueError("Expected a string")
    text = text.strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith("-"):
        negative = True
        text = text[1:].lstrip()

    match = _AMOUNT.fullmatch(text)
    if match is None:
        raise ValueError("Invalid rupee amount")
    integer, fraction, suffix = match.groups()
    fraction = fraction or ""
    places = _PLACES[suffix.lower()] if suffix else 2
    if suffix is None and len(fraction) > 2:
        raise ValueError("Too many decimal digits")
    if any(digit != "0" for digit in fraction[places:]):
        raise ValueError("Fractional paise are not allowed")

    digits = integer.replace(",", "") + fraction[:places].ljust(places, "0")
    # Small chunks avoid Python's string-to-int digit limit for large amounts.
    value = 0
    for offset in range(0, len(digits), 9):
        chunk = digits[offset:offset + 9]
        value = value * (10 ** len(chunk)) + int(chunk)
    return -value if negative else value
