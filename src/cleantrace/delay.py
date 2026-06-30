"""Configurable pause between outbound HTTP requests."""

import random
import time


def apply(seconds: float, randomize: bool) -> None:
    """Sleep for `seconds` before the next request.

    When `randomize` is True the actual sleep is between 0.5× and 1.5× the
    requested value, which breaks up predictable request timing patterns.
    """
    if seconds <= 0:
        return
    actual = seconds * random.uniform(0.5, 1.5) if randomize else seconds
    time.sleep(actual)
