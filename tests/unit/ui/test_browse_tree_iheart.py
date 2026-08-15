"""iHeart letter grouping -- the alphabetised sub-directory helper.

The helper moved from ``quill/ui/radio/browse_tree_helpers.py`` to
``quill/core/radio/browse_helpers.py`` when the browse registry (which is core)
needed it: core reaching up into the UI layer was the wrong fix. The tree shape
it feeds -- genre folders, then A-Z folders, then stations -- is asserted in
``tests/unit/core/radio/test_browse_sources.py``.
"""

from __future__ import annotations

from quill.core.radio.browse_helpers import iheart_letter_groups
from quill.core.radio.models import RadioStation


def _st(name: str) -> RadioStation:
    return RadioStation(name=name, stream_url=f"https://s/{name}", source="iHeart")


def test_iheart_letter_groups_buckets_and_orders() -> None:
    groups = iheart_letter_groups([
        _st("Alt 92.3"),
        _st("WABC"),
        _st("101.5 The Beat"),
        _st("!Weird"),
        _st("alpha FM"),
    ])
    assert [key for key, _rows in groups] == ["0-9", "A", "W", "#"]
    # Case-insensitive by first letter, and sorted case-insensitively inside.
    assert [s.name for _k, rows in groups for s in rows if _k == "A"] == ["alpha FM", "Alt 92.3"]


def test_iheart_letter_groups_is_empty_for_no_stations() -> None:
    assert iheart_letter_groups([]) == []
