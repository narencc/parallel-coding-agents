# Experiment 2: combine overlapping booking times

[Project introduction](../../README.md) · [Step-by-step lesson](../../docs/BOOKING_EXPERIMENT.md) · [Compare both experiments](../../docs/EXPERIMENT_COMPARISON.md)

**All five models passed all 48 prewritten cases.** This recorded run is from
November 15, 2026. The assessment was saved before model requests. We did not
add post-hoc cases or revise any answer after final assessment.

## The task in one example

A room is booked from 1:00 to 2:00 and from 1:30 to 2:30. Combine those into one
continuous booking from 1:00 to 2:30. In minutes after midnight:

`[[60, 120], [90, 150]]` → `[[60, 150]]`

Touching endpoints combine too; gaps stay separate. The original list must stay
unchanged, even if someone later edits the returned answer.

## Inspect the evidence without an API key

- [Written rules](SPEC.md)
- [Four practice tests](test_visible.py)
- [Frozen protocol and all 48 original cases](frozen.json)
- [Exact judging source used](judge-source.py) — read-only evidence; use the sandbox command below to execute checks
- [Model requests, usage, costs, and selection](run.json)
- [File fingerprints](manifest.json)

| Model | Requests | Drafts | Original checks | Estimated USD | Final answer and evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| GPT-6 Astra | 2 | 1 | 48/48 | $0.04428 | [Code](lanes/lane-1/schedule.py), [draft](lanes/lane-1/draft-01.py), [cases](lanes/lane-1/results.json) |
| GPT-6.1 Sol | 2 | 1 | 48/48 | $0.00887 | [Code](lanes/lane-2/schedule.py), [draft](lanes/lane-2/draft-01.py), [cases](lanes/lane-2/results.json) |
| GPT-6.1 Terra | 2 | 1 | 48/48 | $0.00395 | [Code](lanes/lane-3/schedule.py), [draft](lanes/lane-3/draft-01.py), [cases](lanes/lane-3/results.json) |
| GPT-6 Luna | 2 | 1 | 48/48 | $0.00043 | [Code](lanes/lane-4/schedule.py), [draft](lanes/lane-4/draft-01.py), [cases](lanes/lane-4/results.json) |
| GPT-6 Sol | 2 | 1 | 48/48 | $0.00803 | [Code](lanes/lane-5/schedule.py), [draft](lanes/lane-5/draft-01.py), [cases](lanes/lane-5/results.json) |

The race took **12.84 seconds**, with five overlapping requests. Total reported
usage was **11,510 input tokens and 1,927 output tokens** over **10 requests**.
Estimated cost was **$0.0655729**, using recorded standard uncached rates. This is
not a provider bill or a promise about a future run. Per-model values above are
rounded; use `run.json` for exact accounting.

## What the assessment checked

There were 44 held-back cases and four practice cases. The held-back cases
included overlaps, touching chains, nesting, duplicates, sorting, day boundaries,
a chain of 1,440 minute-long bookings, and invalid types and ranges.

For each successful call, the judge compared the returned value and the input
left behind. It then edited the first returned inner list (if present) and
appended to the returned outer list, checking again that the original input was
unchanged. This catches common shared-list mistakes; it is not a proof covering
every possible mutation. Rejected inputs were also checked for unwanted changes.

Each case ran in a fresh restricted process. The expected answer stayed in the
host program. Model requests received only the rules, unfinished answer, and
practice tests—not the assessment. The assessment is now public for reproduction.

## Why we kept Sol 6.1

All five use a sound validate, sort, and merge approach, and all five passed.
Sol 6.1 was chosen because it separates endpoint type checks from range checks,
gives clear error messages, and uses a straightforward copy-sort-merge sequence.
This is a subjective readability tie-break, not a measured quality advantage.

The exact saved answer was rechecked against all 48 cases, then kept in
[solution-bookings](../../solution-bookings/README.md). The money-converter answer
and evidence were not replaced.

## Replay or reproduce

From the repository root, read the recording with Python alone:

```sh
python3 -m bakeoff replay --task bookings
python3 -m bakeoff replay --task bookings --lane lane-2
```

To execute the archived answers again, use the macOS sandbox setup in the
[project introduction](../../README.md), then:

```sh
.venv/bin/python -m bakeoff recheck --task bookings
```

Rechecking makes no GPT requests and writes a fresh local report. It does not
alter this archive. The judge source fingerprint must match the frozen version;
a changed judge requires an explicit review, not a silent reinterpretation.

## Provenance and limits

Original local race: `race-20261115T164405Z-o222yldv`.

Assessment commit, created before the model calls:
`f5b46975a97ddd405b2ff872bc3b552af8d06719`.

Selected candidate commit:
`3b400626a00cc57f61ad244f1f8f409e15f67888`.

These belong to separate local teaching repositories, not the outer public
repository. Exact source files and their fingerprints are included, so the
original local Git history is unnecessary for reproduction. Fingerprints detect
changes relative to these records; they are not independent third-party proof.
The archive excludes API keys, local absolute paths, and raw provider conversations.

One run of this task does not establish a general model ranking. All-pass results
are reported as all-pass; we did not seek extra failures to make the story more
interesting. The existing local sandbox limits still apply.
