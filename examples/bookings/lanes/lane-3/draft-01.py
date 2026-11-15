"""Combine booking windows within a single day."""


def merge_windows(windows):
    if not isinstance(windows, list):
        raise ValueError("windows must be a list of pairs")

    pairs = []
    for pair in windows:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("each window must be a two-item list")
        start, end = pair
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or not 0 <= start < end <= 1440):
            raise ValueError("invalid window endpoints")
        pairs.append((start, end))

    pairs.sort()
    merged = []
    for start, end in pairs:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
