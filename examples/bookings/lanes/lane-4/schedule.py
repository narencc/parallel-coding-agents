"""Combine overlapping or adjacent booking windows."""


def merge_windows(windows):
    """Return sorted, coalesced copies of valid minute windows.

    Raises ValueError if the input is not a list of two-item lists with
    integer (but not boolean) endpoints in the range [0, 1440].
    """
    if not isinstance(windows, list):
        raise ValueError("windows must be a list")

    validated = []
    for window in windows:
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError("each window must be a two-item list")
        start, end = window
        if (type(start) is not int or type(end) is not int
                or not (0 <= start < end <= 1440)):
            raise ValueError("window endpoints must be valid whole minutes")
        validated.append((start, end))

    validated.sort()
    merged = []
    for start, end in validated:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
