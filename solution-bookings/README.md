# The booking answer we kept

We kept **GPT-6.1 Sol, lane-2**, from commit
`3b400626a00cc57f61ad244f1f8f409e15f67888`.

The code in [schedule.py](schedule.py) is the exact saved model answer. It passed
all 48 prewritten cases during judging and again before being kept. The original
money-converter solution remains in `solution/`.

## How the function works, in plain English

1. **Check the outside container.** The bookings must arrive as a list.
2. **Check each booking.** Each booking needs exactly two whole-number times.
   True/false values are not accepted as times.
3. **Check the limits.** Start must be earlier than end, and both must fit inside
   one day, from minute 0 to minute 1440.
4. **Make separate pairs.** Copy the endpoint values into new lists. This avoids
   changing the caller's original bookings while sorting or merging.
5. **Sort by start time.** Read the earliest booking first.
6. **Compare with the last combined booking.** If the next booking starts before
   or exactly when that combined booking ends, extend the end when needed.
7. **Start a new combined booking when there is a gap.** Never fill a genuine gap.
8. **Return the new list.** Editing it later does not alter the original list.

For example, `[[60, 120], [90, 150]]` becomes `[[60, 150]]`. The second booking
starts before the first ends, so together they occupy minutes 60 through 150.

## Review of all five answers

| Candidate | Review |
| --- | --- |
| Astra | Clear validation and fresh copies; uses a short generator to check both endpoint types. Passed all cases. |
| Sol 6.1 | Explicit type checks, separate range checks, descriptive errors, and a clear copy-sort-merge sequence. Selected on readability. |
| Terra 6.1 | Compact, uses temporary tuples, and combines type/range rejection into one condition. Passed all cases. |
| Luna | Clear documentation, exact integer type checks, temporary tuples, and an explicit conditional to extend an end. Passed all cases. |
| Sol 6 | Concise; validates all input before sorting a new outer list and creates new output pairs. Passed all cases. |

All five tied on observed behavior. Another reviewer could reasonably prefer a
different implementation. The choice is not a claim that Sol 6.1 is generally the
best or cheapest model.

## Try it safely

From the project root, run the full saved assessment inside restricted processes:

```sh
.venv/bin/python -m bakeoff recheck --task bookings
```

This checks all five archived answers, including the exact code kept here. It
makes no model calls. [Full experiment and evidence](../examples/bookings/README.md).
