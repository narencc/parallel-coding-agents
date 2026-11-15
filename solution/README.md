# The answer we kept

We chose **GPT-6 Astra, lane-1**, from saved commit
`46288e9267df9b6ab71df202384a48393c2e6423` on November 15, 2026.
The code in `money.py` is byte-for-byte the model's saved answer. We did not mix
answers together or repair the winning code after judging.

## What this little program does

It reads an amount written in rupees and returns an exact whole number of paise.
For example, `₹500` becomes `50000`, and `1.2 lakh` becomes `12000000`.
It does not transfer money or call an API. Invalid input raises `ValueError`.

## How we reviewed the five answers

First, all five passed the original 40 hidden tests and four practice tests.
Then we read each saved implementation against the written assignment. We looked
for correctness first, followed by readability and unnecessary complexity.

Reading the code suggested additional questions: does a very long but valid
number work, and do different kinds of whitespace work where whitespace is
allowed? We wrote 22 extra cases and ran the same cases against every saved
candidate in the sandbox. We did not feed the results back to any GPT model.

| Candidate | Original cases | Extra review cases | Code review |
| --- | --- | --- | --- |
| Astra, lane-1 | 44/44 | 22/22 | Clear single-function flow, exact digit arithmetic, handles long inputs in chunks. Selected. |
| Sol 6.1, lane-2 | 44/44 | 22/22 | Equally strong tested behavior; checks excess fractional digits using a slice and `any`. Close alternative. |
| Terra, lane-3 | 44/44 | 22/22 | Equally strong tested behavior; extracts chunk parsing into a helper, but its amount pattern is one long line and calculation is split into whole and fractional parts. |
| Luna, lane-4 | 44/44 | 17/22 | Exact integer arithmetic for ordinary inputs, but direct integer conversion rejects long valid inputs. Global ASCII matching rejects allowed Unicode whitespace. Also repeats some digit validation. |
| Sol 6, lane-5 | 44/44 | 17/22 | Compact code with named pattern groups and quotient/remainder arithmetic. Same demonstrated long-input and Unicode-whitespace failures as Luna. |

The top three tie on the observed results. Choosing Astra over Sol 6.1 and Terra
is a readability judgment, not a claim that the tests prove Astra uniquely best.
Its ordinary-amount and suffixed-amount rules are easy to follow separately.
We did not use model reputation, price, or response speed as a substitute for
correctness. This selects one answer for this assignment, not the best model
for every task.

## What the extra tests found

Two valid examples use more than 4,300 digits: leading zeros followed by `1`, and
`1.` followed by many zeros and `l`. Their answers are small exact integers.
Luna and Sol 6 use direct conversions that encounter Python's decimal-string
conversion limit. Astra, Sol 6.1, and Terra convert long whole numbers in small
chunks and avoid converting an enormous fractional string.

Three other cases put a nonbreaking space or em space between the currency marker
and number, or before the suffix. The assignment allows whitespace there.
Luna and Sol 6 apply ASCII mode to their entire regular expression, narrowing
what counts as whitespace. The top three apply ASCII restrictions to the marker
and suffix letters while allowing the broader whitespace matches.

The extra cases also cover negative signs, invalid mixed signs, split markers,
invalid suffixes, suffix precision, and boolean input. The full input/expected/
actual records are in `review-cases.json`. The original hidden-test result has
not been rewritten: the lower two really did pass that original suite.

## Reading the winning code in plain English

1. **Check the input type.** An amount must be text.
2. **Remove surrounding spaces.** These do not change its value.
3. **Remember whether it is negative.** Remove the one permitted minus sign or
   pair of parentheses. The rest must still match the amount rules.
4. **Check the shape.** A regular expression is a pattern describing permitted
   text. It separates the whole number, fractional digits, and optional suffix.
5. **Choose the number of decimal places.** Plain rupees need two places to
   become paise. Thousands need five; lakhs need seven; crores need nine.
6. **Reject fractional paise.** Without a suffix, more than two fractional digits
   are forbidden. With a suffix, trailing zeros can be removed, but any remaining
   digits beyond the allowed places mean the result is smaller than a whole paisa.
7. **Build the exact integer.** Remove commas and pad the fractional part with
   zeros. For `1.2 lakh`, seven places turn the fractional `2` into `2000000`;
   placing it after `1` produces `12000000` paise. No floating-point rounding occurs.
8. **Read digits in chunks.** Nine digits at a time avoid Python's limit on one
   very long decimal-string conversion. Accumulating the chunks preserves the value.
9. **Apply the remembered sign.** Return the exact positive or negative integer.

## What “keep it” changed

We reran all 44 original cases against Astra's exact commit immediately before
keeping it. They all passed. We then fast-forwarded the small race repository's
`main` branch to that commit. A fast-forward means moving the main bookmark to
an already-saved answer; it does not rewrite that answer or create a mixed version.

This `solution/` folder contains a convenient copy of the same code, assignment,
and practice test file. `selection.json` identifies its origin and contains the
final 44-case verification. The outer project repository was not committed.
All five competing branches, drafts, and historical judging records remain.
The unfinished `sample/` remains the starting assignment for future races.

## Try it inside the sandbox

Run this from the project folder to test the kept answer's four practice cases:

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
from bakeoff.practice import check_practice
result = check_practice(Path('solution').resolve())
print(f'{result.passed}/{result.total} passed; all_passed={result.all_passed}')
PY
```

This makes no API calls. The code still runs through our restricted workspace.

## Limits of our conclusion

Passing the original 44 cases plus 22 review cases gives evidence, not a proof
for every possible input. The retained implementation uses a regular expression
and has not been exhaustively assessed for performance on adversarial inputs.
The existing sandbox limits still apply; this is a local learning project.
