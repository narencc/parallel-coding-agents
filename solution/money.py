"""Parse Indian rupee amounts exactly, without floating-point arithmetic."""

import re


_AMOUNT = re.compile(
    r"(?:(?ai:₹|rs\.?|inr)\s*)?"
    r"([0-9]+(?:,[0-9]+)*)(?:\.([0-9]+))?"
    r"(?:\s*(?ai:(k|l|lakh|lakhs|cr|crore|crores)))?" 
)
_PLACES = {"k": 5, "l": 7, "lakh": 7, "lakhs": 7,
           "cr": 9, "crore": 9, "crores": 9}


def parse_inr(text: str) -> int:
    """Convert written rupees into an exact whole number of paise."""
    if not isinstance(text, str):
        raise ValueError("Amount must be a string")
    text = text.strip()
    negative = False
    if text.startswith("-"):
        negative = True
        text = text[1:].strip()
    elif text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    match = _AMOUNT.fullmatch(text)
    if match is None:
        raise ValueError("Invalid rupee amount")
    integer, fraction, suffix = match.groups()
    fraction = fraction or ""
    if suffix is None:
        places = 2
        if len(fraction) > places:
            raise ValueError("At most two decimal digits without a suffix")
    else:
        places = _PLACES[suffix.lower()]
        fraction = fraction.rstrip("0")
        if len(fraction) > places:
            raise ValueError("Amount contains fractional paise")

    digits = integer.replace(",", "") + fraction.ljust(places, "0")
    # Small chunks avoid Python's string-to-integer digit limit.
    amount = 0
    for start in range(0, len(digits), 9):
        chunk = digits[start:start + 9]
        amount = amount * 10 ** len(chunk) + int(chunk)
    return -amount if negative else amount
