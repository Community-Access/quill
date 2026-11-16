"""The outro skip fires only on a natural crossing (earshot.md E1). Pure, no wx."""

from __future__ import annotations

import pytest

from quill.core.podcasts.outro_skip import crossed_outro_boundary

LENGTH = 120_000
SKIP = 5_000  # boundary at 115 s


@pytest.mark.parametrize(
    ("previous", "current", "length", "skip", "expected"),
    [
        (114_000, 116_000, LENGTH, SKIP, True),  # listened across it
        (114_000, 115_000, LENGTH, SKIP, True),  # landed exactly on it
        (None, 116_000, LENGTH, SKIP, False),  # first poll after start, resume or seek
        (116_000, 117_000, LENGTH, SKIP, False),  # already inside: resumed or sought there
        (60_000, 116_000, LENGTH, SKIP, False),  # a jump, not listening
        (114_000, 113_000, LENGTH, SKIP, False),  # went backwards
        (114_000, 116_000, LENGTH, 0, False),  # off
        (0, 1_000, 4_000, SKIP, False),  # shorter than the skip
        (1_000, 2_000, 7_000, SKIP, False),  # not 2 s longer than the skip
        (114_000, 120_000, LENGTH, SKIP, False),  # reached the true end itself
    ],
)
def test_crossed_outro_boundary(
    previous: int | None, current: int, length: int, skip: int, expected: bool
) -> None:
    assert crossed_outro_boundary(previous, current, length, skip) is expected
