# Lesson 2: combining booking times

[Back to the project](../README.md) · [Actual results](../examples/bookings/README.md)

This experiment is complete. All five GPT models passed the 48 cases written
before the race. We kept Sol 6.1's answer after a readability review.

## 1. Understand the problem before asking AI

Imagine a meeting room with two reservations:

- 1:00 am to 2:00 am.
- 1:30 am to 2:30 am.

The room is continuously booked from 1:00 am to 2:30 am. We want one combined
window describing that time, rather than two overlapping windows.

To avoid date and time-zone complications, we describe time as minutes after
midnight: 1:00 am is 60, 2:00 am is 120, and 2:30 am is 150.

| Situation | Input | Expected answer |
| --- | --- | --- |
| Overlap | `[[60, 120], [90, 150]]` | `[[60, 150]]` |
| Touching endpoints | `[[60, 120], [120, 180]]` | `[[60, 180]]` |
| Real gap | `[[60, 120], [180, 240]]` | Two separate windows |
| No bookings | `[]` | `[]` |
| Backward time | `[[120, 60]]` | Reject with `ValueError` |

`ValueError` is Python's way of reporting that the supplied value is invalid.

## 2. Decide the rules and questions first

We wrote [the specification](../assignments/bookings/SPEC.md) and 48 assessment
cases before making any model request. Four cases were practice examples the
models could see. The other 44 were held back until final marking.

We independently checked the expected valid answers using a different approach:
mark every booked minute, then group consecutive booked minutes. This helped
check that the marking sheet itself was correct.

A copy of the rules, case list, file fingerprints, and judge fingerprint was saved
in a separate Git repository before the first request. Git is a tool for recording
versions. A fingerprint is a calculated identifier for file contents.

## 3. Teach the coordinator about a second assignment

The first version knew only `money.py` and `parse_inr`. It now has explicit task
settings for either the money converter or bookings.

For bookings, the allowed answer is `schedule.py`, and the function to implement
is `merge_windows`. The model cannot choose a different destination file. The
sandbox copies only that file, the specification, and the practice tests.

The held-back assessment is not copied into the sandbox or sent to models. We
kept the restricted execution rules in place while adding the new assignment.

## 4. Start five separate attempts

Each model received the same unfinished file and written rules in its own Git
worktree—a separate working folder attached to its own branch of saved changes.
Each had its own conversation and up to four requests to write, check, and revise.

In this run, every model wrote one draft and used a second request to submit it.
All five requests overlapped. The race took 12.84 seconds and used 10 requests.
The estimated model cost was $0.0655729, about 6.6 US cents. Actual billing can
differ from this standard-rate estimate.

## 5. Check more than the returned times

A function can return the right times but still damage its original input. For
example, sorting the caller's list directly changes the caller's ordering.
Another mistake is returning the original inner lists: editing the answer could
then unexpectedly change the original bookings.

For each case, our judge runs a fresh restricted process and observes the answer
and the input left behind. On a valid output it edits the first returned pair and
appends another pair, then checks whether the original input changed. It also
checks the output shape and rejects booleans where integer times are required.

The expected result stays outside the restricted process. Empty output, crashes,
timeouts, or printing a claim such as “48 passed” do not count as success.

## 6. Report the result honestly

All five answers passed 44 held-back cases and four practice cases: 240 successful
case executions across five candidates.

Unlike the money-converter experiment, we did not add extra review cases after
seeing the implementations. We found no reason in this review to manufacture a
new challenge just to create a winner. This is a five-way tie on the chosen tests,
not proof that every possible input works.

## 7. Review and keep a separate answer

All five implementations validate first, sort bookings, and merge in time order.
We chose Sol 6.1 for its explicit checks and clear sequence. We reran all 48 cases
against its exact saved commit before keeping it in
[solution-bookings](../solution-bookings/README.md).

The booking race's main branch now points to that exact answer. All five candidate
branches remain. The original unfinished booking assignment remains available for
new races. The first experiment's solution and evidence were not replaced.

## Commands you can try

Read saved results for free, with no credentials or candidate execution:

```sh
python3 -m bakeoff replay --task bookings
```

After the macOS setup in the project README, reproduce the assessment locally:

```sh
.venv/bin/python -m bakeoff recheck --task bookings
```

Run the unfinished booking sample's practice checks (four failures are expected):

```sh
.venv/bin/python -m bakeoff practice --task bookings
```

Start a new paid race:

```sh
.venv/bin/python -m bakeoff race --task bookings
```

The new race prints its folder. Judge that specific folder with:

```sh
.venv/bin/python -m bakeoff judge --race PATH_TO_NEW_RACE
```

After reviewing the qualifying candidates, keep one in a new destination:

```sh
.venv/bin/python -m bakeoff keep --race PATH_TO_NEW_RACE --judge PATH_TO_JUDGE_JSON --lane lane-N --destination NEW_SOLUTION_FOLDER
```

Replace the placeholders with real paths and the reviewed lane. Existing
solutions will not be overwritten. New paid runs may produce different answers.

## Implementation checks

All 75 project tests passed after adding the second task. These include the
independent marking-sheet check, common input-mutation mistakes, excluded hidden
files, frozen-assessment protection, task-specific saving, and replay from a fresh
copy without an API key or installed OpenAI package.

The portable booking archive was also executed again: all 240 case outcomes
matched the recorded run. The kept answer was verified byte-for-byte against its
saved commit. The outer project has not been committed or published by this work.
