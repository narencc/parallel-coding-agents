# One recorded experiment, with the evidence

[Project introduction](../../README.md) · [Beginner guide](../../docs/BEGINNER_GUIDE.md)

This is a portable copy of the November 15, 2026 experiment. You can read it on
GitHub without an API key, installation, or payment. It is a recorded example,
not a live race. The original local worktrees are not required.

## Start here

1. Read the [assignment](SPEC.md). It defines valid input and the exact answer.
2. See the [four practice tests](test_visible.py) the models could inspect.
3. Read the [original hidden tests](test_hidden.py). They were withheld during
   writing and revision; they are now public so readers can inspect the assessment.
4. Compare the answers and case results below.
5. Read [why Astra was kept](../../solution/README.md).

| Lane and model | Final source | Saved drafts | Original case results | Extra review results |
| --- | --- | --- | --- | --- |
| 1 · Astra | [Code](lanes/lane-1/money.py) | [Draft 1](lanes/lane-1/draft-01.py) | [44/44](lanes/lane-1/original-results.json) | [22/22](lanes/lane-1/review-results.json) |
| 2 · Sol 6.1 | [Code](lanes/lane-2/money.py) | [Draft 1](lanes/lane-2/draft-01.py) | [44/44](lanes/lane-2/original-results.json) | [22/22](lanes/lane-2/review-results.json) |
| 3 · Terra 6.1 | [Code](lanes/lane-3/money.py) | [Draft 1](lanes/lane-3/draft-01.py), [draft 2](lanes/lane-3/draft-02.py) | [44/44](lanes/lane-3/original-results.json) | [22/22](lanes/lane-3/review-results.json) |
| 4 · Luna | [Code](lanes/lane-4/money.py) | [Draft 1](lanes/lane-4/draft-01.py), [draft 2](lanes/lane-4/draft-02.py), [draft 3](lanes/lane-4/draft-03.py) | [44/44](lanes/lane-4/original-results.json) | [17/22](lanes/lane-4/review-results.json) |
| 5 · Sol 6 | [Code](lanes/lane-5/money.py) | [Draft 1](lanes/lane-5/draft-01.py) | [44/44](lanes/lane-5/original-results.json) | [17/22](lanes/lane-5/review-results.json) |

The JSON files are structured records. Each case shows the input, expected
answer, observed answer, pass/fail decision, and execution status. `run.json`
includes each draft's explanation, practice score, token usage, recorded rates,
request timings, original commit IDs, and the selection reason.

## What the extra cases found

Both Luna and Sol 6 failed these same five checks:

- A valid number with 4,500 leading zeros.
- A valid suffixed amount with a very long all-zero fractional part.
- A nonbreaking space after the currency marker.
- A nonbreaking space before the suffix.
- An em space after the currency marker.

These represent related weaknesses in long-string conversion and whitespace
handling, not five independent bugs per model. The assignment had no digit-count
limit and permitted whitespace at those positions.

The extra checks were written after reading the code. They are useful bug-finding
evidence, not an independent prewritten benchmark. Every candidate received the
same additional checks. No model revised its answer after seeing the assessment.

## Costs and selection

[run.json](run.json) gives token counts and the recorded per-million-token rates
for each model. Estimated cost is input tokens times the input rate plus output
tokens times the output rate, divided by one million. It ignores cache discounts
and is not the provider's bill. The total is $0.1153683 for 13 model requests.

The top three tied on these cases. Readability decided the choice of Astra;
there is no evidence here that Astra is universally better or more economical.

## Verify without the original machine

From the repository root, `python3 -m bakeoff replay` checks file fingerprints
and displays the evidence without executing the answers. Fingerprints detect
accidental changes relative to the included manifest; they are not an external
signature or independent certification of the experiment.

For a new sandboxed execution of every case, follow the macOS setup in the
[project introduction](../../README.md), then run:

```sh
.venv/bin/python -m bakeoff recheck
```

This needs no OpenAI key. Expected failures count as a successful reproduction
when they match the recording. Different results should be investigated, not
silently replaced in the published example.

## Provenance and what was omitted

The original local race was `race-20261115T155112Z-rdly1111`. Its saved source and
draft bytes were checked against their original fingerprints during export.
[manifest.json](manifest.json) lists the fingerprints of this evidence package.
The original candidate commit IDs identify the nested teaching repository; they
are not commits in the outer public repository. Source bytes and tests are
included so the original nested Git history is not needed for verification.

The export keeps explicit fields only. It omits credentials, private settings,
absolute machine paths, raw provider conversations, and raw output tails that
can contain local paths. It includes observations and draft explanations, not
hidden model reasoning. Original private working records were left untouched.

Export helper: [scripts/export_example.py](../../scripts/export_example.py). It
requires the original local race. Reading and rechecking this package do not.
