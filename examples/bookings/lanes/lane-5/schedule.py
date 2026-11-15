"""Utilities for combining booking windows within one day."""


def merge_windows(windows):
    """Return sorted, merged copies of valid minute-based booking windows."""
    if not isinstance(windows, list):
        raise ValueError("windows must be a list")

    for window in windows:
        if (not isinstance(window, list) or len(window) != 2
                or any(type(value) is not int for value in window)):
            raise ValueError("each window must contain two integers")
        start, end = window
        if not 0 <= start < end <= 1440:
            raise ValueError("window endpoints are out of range or unordered")

    result = []
    for start, end in sorted(windows):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result
