"""Validate and combine booking windows within a single day."""


def merge_windows(windows):
    """Return independent, sorted windows, merging overlaps and touching ends."""
    if not isinstance(windows, list):
        raise ValueError("windows must be a list of two-item lists")

    ordered = []
    for window in windows:
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError("each window must be a two-item list")
        start, end = window
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)):
            raise ValueError("endpoints must be integers, not booleans")
        if not 0 <= start < end <= 1440:
            raise ValueError("windows must satisfy 0 <= start < end <= 1440")
        ordered.append([start, end])

    ordered.sort(key=lambda window: window[0])
    merged = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
