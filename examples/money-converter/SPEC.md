# The money converter assignment

Implement `parse_inr(text: str) -> int` in `money.py`.

Input is text describing Indian rupees. Output is an exact whole number of paise.
One rupee equals 100 paise. This interprets text; it does not transfer money.

## Rules

1. Ignore whitespace at the start and end of the input.
2. An optional currency marker comes before the number: `₹`, `Rs`, `Rs.`, or
   `INR`. Letter case does not matter. Whitespace may separate marker and number.
3. Use ASCII digits 0 through 9. Require at least one digit before a decimal
   point and, if a point appears, at least one digit after it.
4. Commas may appear between digits in the integer part. Ignore grouping sizes:
   `1,25,000`, `125,000`, and `1,2,3` are valid. Leading, trailing, consecutive,
   and fractional-part commas are invalid.
5. Without a suffix, allow at most two digits after the decimal point.
6. An optional suffix follows the number, with or without whitespace, in any
   letter case. `k` multiplies by 1000; `l`, `lakh`, and `lakhs` by 100000;
   `cr`, `crore`, and `crores` by 10000000.
7. With a suffix, allow additional decimal digits only if the final amount is
   an exact whole number of paise. Reject fractional paise; never round.
8. A negative amount uses either one leading `-` before the marker or number,
   or one pair of parentheses around the complete amount. Ignore surrounding
   whitespace inside those parentheses and after a leading minus. Do not combine
   minus and parentheses. Do not accept a plus sign.
9. No internal whitespace is allowed inside the number, marker, or suffix.
10. Return an integer with no loss of precision. Do not use binary floating-point
    arithmetic for monetary calculations. Negative zero returns integer zero.
11. Anything outside these rules, including non-string input, raises `ValueError`.

## Examples everyone can see

| Input | Expected result |
| --- | --- |
| `₹500` | `50000` |
| `Rs. 1,250` | `125000` |
| `INR 99.50` | `9950` |
| `abc` | `ValueError` |

These rules clarify ambiguities in the original tutorial about comma placement,
decimal syntax, and fractional paise. Every assessment case must follow this agreement.
