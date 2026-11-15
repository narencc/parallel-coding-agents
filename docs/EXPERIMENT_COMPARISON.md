# Two experiments, reported separately

[Project introduction](../README.md)

Each task was run once. The tasks exercise different skills and use different numbers
of cases. These observations do not establish a general model ranking.

| Model | Money: original | Money: later review | Bookings: original | Bookings: later review | Total estimated USD, both recorded runs |
| --- | --- | --- | --- | --- | ---: |
| gpt-6-astra | 44/44 | 22/22 | 48/48 | None added | $0.11482 |
| gpt-6.1-sol | 44/44 | 22/22 | 48/48 | None added | $0.02355 |
| gpt-6.1-terra | 44/44 | 22/22 | 48/48 | None added | $0.01759 |
| gpt-6-luna | 44/44 | 17/22 | 48/48 | None added | $0.00247 |
| gpt-6-sol | 44/44 | 17/22 | 48/48 | None added | $0.02251 |

## What we can say

- Every candidate passed the original assessment in both tasks.
- Extra cases written after reviewing the money answers exposed weaknesses in two answers.
- The booking assessment was frozen before model requests. All five passed it; no later cases were added.
- We kept Astra for money and Sol 6.1 for bookings using explicit readability judgments among tied candidates.
- Across both races there were 23 requests and an estimated $0.1809412 in model costs. These are recorded estimates, not a future-price guarantee.

## What we cannot conclude

We cannot conclude that one model is generally best, that a passing answer has no bugs,
or that this spending pattern will repeat. The money review cases were motivated by
reading the answers; they are not equivalent to a prewritten assessment.

No failed experiment was discarded to produce this comparison, and no model revised
an answer after seeing its final assessment results. This remains a small demonstration,
not a broad independent benchmark.

[Money evidence](../examples/money-converter/README.md) · [Booking evidence](../examples/bookings/README.md)
