"""Convert written Indian rupee amounts to whole paise."""

import re


_AMOUNT = re.compile(
    r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*)(?:\.([0-9]+))?\s*(k|lakhs|lakh|l|crores|crore|cr)?',
    re.IGNORECASE | re.ASCII,
 )
_SCALE = {None: 2, 'k': 5, 'l': 7, 'lakh': 7, 'lakhs': 7,
          'cr': 9, 'crore': 9, 'crores': 9}


def _integer(digits: str) -> int:
    # Parse in small chunks to avoid Python's decimal string conversion limit.
    value = 0
    for pos in range 0, len(digits), 9:
        chunk = digits[pos:pos + 9]
        value = value * (10 ** len(chunk)) + int(chunk)
    return value


def parse_inr(text: str) -> int:
    """Convert written rupees into an exact whole number of paise."""
    if not isinstance(text, str):
        raise ValueError('amount must be text')
    text = text.strip()
    negative = False
    if text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1].strip()
    elif text.startswith('-'):
        negative = True
        text = text[1:].lstrip()
    match = _AMOUNT.fullmatch(text)
    if not match:
        raise ValueError('invalid amount')
    whole, fraction, suffix = match.groups()
    suffix = suffix.lower() if suffix else None
    fraction = fraction or ''
    if suffix is None and len(fraction) > 2:
        raise ValueError('too many decimal places')
    scale = _SCALE[suffix]
    fraction = fraction.rstrip('0')
    if len(fraction) > scale:
        raise ValueError('fractional paise')
    result = _integer(whole.replace(',', '')) * 10 ** scale
    if fraction:
        result += int(fraction) * 10 ** (scale - len(fraction))
    return -result if negative else result
