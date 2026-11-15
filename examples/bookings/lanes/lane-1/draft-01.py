"""Combine overlapping or touching booking windows within one day."""


def merge_windows(windows):
    """Return independent, sorted merged windows; reject invalid input."""
    if not isinstance(windows, list):
        raise ValueError("windows must be a list")

    copied = []
    for window in windows:
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError("each window must be a two-item list")
        start, end = window
        if any(not isinstance(value, int) or isinstance(value, bool)
               for value in (start, end)):
            raise ValueError("endpoints must be integers, not booleans")
        if not 0 <= start < end <= 1440:
            raise ValueError("windows must satisfy 0 <= start < end <= 1440")
        copied.append([start, end])

    copied.sort(key=lambda window: window[0])
    merged = []
    for start, end in copied:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
