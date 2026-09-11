"""Where every app's window size is kept, and what it defaults to.

Two properties this file exists to hold:

* **Maximized is the default**, on a fresh machine and after any read that
  fails. That is the accessibility decision -- a small window is where clipped
  labels and four-row lists come from, and neither is visible to whoever picked
  the number.
* **A restored size is only ever a size the user chose.** Recording a maximized
  window's size as the restored size means un-maximizing gives back a
  full-screen "restored" window and the real preference is gone.

wx-free; whether a window *is* maximized is asked in ``quill/ui/window_state.py``
and tested beside it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.window_geometry import (
    MIN_HEIGHT,
    MIN_WIDTH,
    STORE_NAME,
    WindowGeometry,
    load_geometry,
    save_geometry,
)

# ---------------------------------------------------------------------------
# the default


def test_a_fresh_machine_opens_maximized(tmp_path: Path) -> None:
    assert load_geometry(tmp_path, "radio").maximized is True


def test_a_missing_store_is_the_default(tmp_path: Path) -> None:
    geometry = load_geometry(tmp_path, "radio")
    assert (geometry.maximized, geometry.width, geometry.height) == (True, 0, 0)


def test_a_corrupt_store_is_the_default(tmp_path: Path) -> None:
    """A geometry file that cannot be read must leave the app openable."""
    (tmp_path / STORE_NAME).write_text("{not json", encoding="utf-8")
    assert load_geometry(tmp_path, "radio").maximized is True


def test_a_foreign_store_is_the_default(tmp_path: Path) -> None:
    (tmp_path / STORE_NAME).write_text('["a list"]', encoding="utf-8")
    assert load_geometry(tmp_path, "radio").maximized is True


def test_an_app_with_no_entry_is_the_default(tmp_path: Path) -> None:
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=False, width=800, height=600))
    assert load_geometry(tmp_path, "weather").maximized is True


# ---------------------------------------------------------------------------
# the size


def test_an_unset_size_defers_to_the_apps_own_default() -> None:
    """Inventing a number would override an app's considered default."""
    assert WindowGeometry().restored_size((460, 360)) == (460, 360)


def test_a_chosen_size_wins_over_the_apps_default() -> None:
    assert WindowGeometry(width=1280, height=800).restored_size((460, 360)) == (1280, 800)


def test_a_size_below_the_floor_is_raised() -> None:
    """A window restored to 40x30 is one nobody can find the title bar of."""
    assert WindowGeometry(width=40, height=30).restored_size((460, 360)) == (
        MIN_WIDTH,
        MIN_HEIGHT,
    )


@pytest.mark.parametrize("junk", ["big", None, True, -5, 0, [800]])
def test_a_nonsense_stored_size_reads_as_unset(tmp_path: Path, junk: object) -> None:
    (tmp_path / STORE_NAME).write_text(
        json.dumps({"radio": {"maximized": False, "width": junk, "height": junk}}),
        encoding="utf-8",
    )
    geometry = load_geometry(tmp_path, "radio")
    assert (geometry.width, geometry.height) == (0, 0)
    assert geometry.restored_size((460, 360)) == (460, 360)


def test_a_nonsense_stored_maximized_reads_as_the_default(tmp_path: Path) -> None:
    (tmp_path / STORE_NAME).write_text(
        json.dumps({"radio": {"maximized": "yes"}}), encoding="utf-8"
    )
    assert load_geometry(tmp_path, "radio").maximized is True


# ---------------------------------------------------------------------------
# storing


def test_a_geometry_round_trips(tmp_path: Path) -> None:
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=False, width=1280, height=800))
    geometry = load_geometry(tmp_path, "radio")
    assert (geometry.maximized, geometry.width, geometry.height) == (False, 1280, 800)


def test_one_app_never_disturbs_another(tmp_path: Path) -> None:
    """One file, one entry per app, exactly as app_features does it."""
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=False, width=1280, height=800))
    save_geometry(tmp_path, "weather", WindowGeometry(maximized=True))

    assert load_geometry(tmp_path, "radio").width == 1280
    assert load_geometry(tmp_path, "weather").maximized is True
    assert load_geometry(tmp_path, "weather").width == 0


def test_an_unset_size_is_not_written(tmp_path: Path) -> None:
    """ "Maximized, and I never chose a size" is a real state and stays one."""
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=True))
    stored = json.loads((tmp_path / STORE_NAME).read_text(encoding="utf-8"))
    assert stored == {"radio": {"maximized": True}}


def test_a_stored_size_is_floored_on_the_way_in(tmp_path: Path) -> None:
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=False, width=10, height=10))
    stored = json.loads((tmp_path / STORE_NAME).read_text(encoding="utf-8"))
    assert stored["radio"]["width"] == MIN_WIDTH
    assert stored["radio"]["height"] == MIN_HEIGHT


def test_the_store_shares_the_shape_app_features_uses(tmp_path: Path) -> None:
    """One shared file, keyed per app -- so the two are read the same way."""
    save_geometry(tmp_path, "radio", WindowGeometry(maximized=False, width=800, height=600))
    stored = json.loads((tmp_path / STORE_NAME).read_text(encoding="utf-8"))
    assert set(stored) == {"radio"}
    assert isinstance(stored["radio"], dict)
