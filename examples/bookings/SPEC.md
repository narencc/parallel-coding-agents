# Combine overlapping booking times

Implement `merge_windows(windows)` in `schedule.py` using Python's standard library.

Times are whole minutes after midnight in one day. For example, 60 means 1:00 am,
120 means 2:00 am, and 1440 is the end of the day. No dates, time zones, or daylight
saving rules are involved.

## Rules

1. Input must be a list of two-item lists. Every endpoint must be an integer,
   not a boolean. Tuples, strings, floats, and other input shapes are invalid.
2. Every pair must satisfy `0 <= start < end <= 1440`. Empty or backward windows
   are invalid. Reject invalid input with `ValueError`.
3. Combine windows that overlap OR touch at an endpoint. Combining can continue
   through a chain of windows. Keep actual gaps separate.
4. Return a new list of two-item lists sorted by start time. Endpoints are integers,
   not booleans. Duplicate or nested bookings are allowed and combine normally.
5. Never change the input list or any of its nested lists, on success or rejection.
6. The returned outer list and its inner lists must be independent of the input:
   changing the returned answer afterward must not change the original input.
7. An empty input list returns a new empty list.
8. Do not use a network, external files, third-party packages, or global mutable
   state. There is no permission to edit the specification or tests.

## Visible examples

| Input | Expected result |
| --- | --- |
| `[]` | `[]` |
| `[[60, 120], [90, 150]]` | `[[60, 150]]` |
| `[[180, 240], [60, 120]]` | `[[60, 120], [180, 240]]` |
| `[[120, 60]]` | `ValueError` |

Every assessment case must follow these rules. Hidden cases are withheld from
model prompts during the race and may be published afterward for reproduction.
