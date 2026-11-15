"""Parse written Indian rupee amounts into exact whole paise."""
import re


_AMOUNT = re.compile(
    r"(?:₹|Rs\.?|INR)?\s*"
    r"(?P<integer>[0-9]+(?:,[0-9]+)*)(?:\.(?P<fraction>[0-9]+))?"
    r"\s*(?P<suffix>k|l|lakhs?|cr|crores?)?",
    re.IGNORECASE | re.ASCII,
 )
_MULTIPLIERS = {
    "k": 1000, "l": 100000, "lakh": 100000, "lakhs": 100000,
    "cr": 10000000, "crore": 10000000, "crores": 10000000,
}


def parse_inr(text: str) -> int:
    """Convert written rupees into an exact whole number of paise."""
    if not isinstance(text, str):
        raise ValueError("amount must be text")
    amount = text.strip()
    negative = False
    if amount.startswith("("):
        if not amount.endswith(")"):
            raise ValueError("unclosed parentheses")
        negative = True
        amount = amount[1:-1].strip()
    elif amount.startswith("-"):
        negative = True
        amount = amount[1:].strip()
    match = _AMOUNT.fullmatch(amount)
    if match is None:
        raise ValueError("invalid rupee amount")
    fraction = match.group("fraction") or ""
    suffix = match.group("suffix")
    if suffix is None and len(fraction) > 2:
        raise ValueError("too many decimal places")
    digits = match.group("integer").replace(",", "") + fraction
    multiplier = _MULTIPLIERS[suffix.lower()] if suffix else 1
    numerator = int(digits) * multiplier * 100
    denominator = 10 ** len(fraction)
    paise, remainder = divmod(numerator, denominator)
    if remainder:
        raise ValueError("fractional paise")
    return -paise if negative else paise
