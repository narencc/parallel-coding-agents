# Proposed second experiment: combine overlapping booking times

**Status: proposal, not implemented or run.** This is a different task chosen for
its practical use, not because we expect a particular model to fail. The current
race coordinator is still specific to the money converter.

A money parser checks written formats and exact arithmetic. A booking-window
combiner checks sorting, relationships between items, empty inputs, and preserving
the caller's data. It needs no external service or private information.

## Plain-English task

A room has several booked time windows during a day. Combine windows that overlap
or touch, and return them in time order. Times are whole minutes after midnight.

For example, 60 means 1:00 am and 120 means 2:00 am. `[[60, 120], [90, 150]]`
becomes `[[60, 150]]`: the room is continuously booked from 1:00 am to 2:30 am.

## Proposed contract

- Implement `merge_windows(windows)` in `schedule.py`.
- Input is a list of two-item lists. Both items must be integers, not booleans.
- Each pair is a start and end, with `0 <= start < end <= 1440`.
- Reject every other input with `ValueError`.
- Combine overlaps and touching endpoints; preserve gaps.
- Return a new list of two-item lists, ordered by start time.
- Do not change the input list or its nested lists.
- An empty list returns an empty list.
- Duplicate windows are allowed and combine normally.
- No third-party packages or network access are needed.

## Proposed visible examples

| Input | Expected output |
| --- | --- |
| `[]` | `[]` |
| `[[60, 120], [90, 150]]` | `[[60, 150]]` |
| `[[180, 240], [60, 120]]` | `[[60, 120], [180, 240]]` |
| `[[120, 60]]` | `ValueError` |

## Before any model request

1. Confirm these rules without reading candidate implementations.
2. Write practice cases and a separate original assessment, including touching
   endpoints, nesting, duplicates, full-day bounds, invalid types, and input mutation.
3. Save a version and fingerprint of the rules and assessment before the run.
4. Adapt the coordinator's hard-coded file names, entry function, and test counts
   with explicit task configuration. Keep the sandbox copy allowlist narrow.
5. Check the adapter offline before using paid requests.
6. Give every lane the same starting files and request/output limits. Record
   actual attempts and token use, even when the lengths differ.

## Reporting rules

Publish every lane's outcome, whether all succeed, all fail, or results differ.
Keep original-assessment results separate from any later review-inspired cases.
Do not revise candidates after the final assessment. Publish the tests after the
experiment so others can reproduce it.

Two tasks provide more examples, not a reliable general ranking. Repeated runs
would be needed to explore variability; those should be planned and costed
separately, not rerun selectively until a striking result appears.

## Why this is not yet run

The first release is for feedback on the existing evidence and instructions.
After someone tries that experience, implement this adapter and run the second
assignment. This document must not be counted as a completed experiment.
