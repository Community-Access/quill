"""qc.md F-12, safe absence: a damaged store reads as defaults, never a crash.

Every store a Quill app reads at launch is fed the shapes a real disk produces
-- a truncated write, the wrong top-level type, a field of the wrong type,
binary noise, an empty file -- and must come back as something usable. One
that raises here is an app that does not start, and that the person cannot
fix without being told which file to delete.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_DAMAGE = [
    "",
    '{"shows": [{"id": "s", "title": "cut off',
    "[1, 2, 3]",
    '"just a string"',
    '{"shows": "not a list", "queue": 7, "apps": [], "values": "x", "active": 3}',
    '{"shows": [null, 5, {"id": 9, "episodes": "x"}], "queue": [null, {"show_id": 1}]}',
    "\x00\xff\xfe garbage",
]


def _stores() -> list[tuple[str, Callable[[Path], Path], Callable[[Path], Any]]]:
    from quill.core import family_preferences, settings_recipes
    from quill.core.podcasts import history as podcast_history
    from quill.core.podcasts import subscriptions

    # The model before its store: history_store imported first is a circular
    # import, which is how Radio itself always loads them.
    radio_history = importlib.import_module("quill.core.radio.history")
    history_store = importlib.import_module("quill.core.radio.history_store")
    radio_history_file = radio_history._FILE_NAME

    return [
        ("Cast library", subscriptions._store_path, subscriptions.load_library),
        ("Cast preferences", podcast_history._store_path, podcast_history.load_history),
        ("Radio preferences", lambda d: d / radio_history_file, history_store.load_history),
        ("working modes", lambda d: d / settings_recipes._STATE_FILE, settings_recipes.load_state),
        (
            "shared choices",
            lambda d: d / family_preferences._FILE,
            lambda d: family_preferences.is_sharing(d, "cast"),
        ),
    ]


@pytest.mark.parametrize("damage", _DAMAGE)
def test_every_store_survives_a_damaged_file(tmp_path: Path, damage: str) -> None:
    for name, path_of, load in _stores():
        path = path_of(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(damage.encode("utf-8", "surrogateescape"))
        try:
            load(tmp_path)
        except Exception as exc:  # noqa: BLE001 - the assertion names the store
            pytest.fail(f"{name} raised {type(exc).__name__} on {damage[:30]!r}")


def test_every_store_survives_being_absent(tmp_path: Path) -> None:
    for _name, _path_of, load in _stores():
        load(tmp_path / "never-created")
