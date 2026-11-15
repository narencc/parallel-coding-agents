import re


_PATTERN = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*)?"
    r"([0-9][0-9,]*(?:\.[0-9]+)?)"
    r"(k|l|lakh|lakhs|cr|crore|crores)?",
    re.IGNORECASE,
 )

_MULTIPLIERS = {
    "k": 1_000,
    "l": 100_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "cr": 10_000_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}


def parse_inr(text: str) -> int:
    """Convert written rupees into an exact whole number of paise."""
    if not isinstance(text, str):
        raise ValueError("amount must be text")
    value = text.strip()
    negative = False
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
        negative = True
    elif value.startswith("-"):
        value = value[1:].strip()
        negative = True
    match = _PATTERN.fullmatch(value)
    if not match:
        raise ValueError("invalid rupee amount")
    number, suffix = match.groups()
    if number.count(".") > 1:
        raise ValueError("invalid decimal")
    integer, dot, fraction = number.partition(".")
    if not integer or integer.startswith(",") or integer.endswith(",") or ",," in integer:
        raise ValueError("invalid comma grouping")
    digits = integer.replace(",", "")
    if not digits.isascii() or not digits.isdigit():
        raise ValueError("invalid digits")
    if suffix is None and len(fraction) > 2:
        raise ValueError("too many decimal places")
    multiplier = _MULTIPLIERS.get(suffix.lower(), 1) if suffix else 1
    # Scale rupees to paise using integers only, then require exact divisibility.
    numerator = int(digits) * (10 ** len(fraction) if dot else 1) + (int(fraction) if fraction else 0)
    denominator = 10 ** len(fraction) if dot else 1
    paise_numerator = numerator * multiplier * 100
    if paise_numerator % denominator:
        raise ValueError("fractional paise")
    result = paise_numerator // denominator
    return -result if negative else result
