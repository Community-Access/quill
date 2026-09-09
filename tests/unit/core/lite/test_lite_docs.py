"""QuillLite's user guide cannot fall behind QuillLite.

Documentation drift is not a tidiness problem, it is a correctness one, and it
is invisible: a guide that names a key the app does not bind sends somebody to
press nothing, and an app that binds a key the guide never names has a feature
nobody finds. Neither shows up in any other test.

So the three lists that a user reads and the three lists the app is built from
are checked against each other here:

* **every bound key** appears in the guide, which a generated table between
  the ``<!-- keys:start -->`` markers guarantees;
* **every switchable feature area** is named by the exact label its checkbox
  carries, so somebody reading the guide can find the box;
* **every status-bar cell** is named by the exact label it announces, so
  somebody hearing "Line Endings" can look it up.

The guide is prose and stays prose; what is asserted is coverage, never wording.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.apps.lite_window_status import CELLS
from quill.core.lite.commands import COMMANDS, plain_label
from quill.core.lite.features import AREAS

DOCS = Path(__file__).resolve().parents[4] / "standalone" / "quilllite" / "docs"
GUIDE = DOCS / "userguide.md"

_KEYS_START = "<!-- keys:start -->"
_KEYS_END = "<!-- keys:end -->"


@pytest.fixture(scope="module")
def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def test_the_guide_exists_and_carries_the_generated_key_table(guide: str) -> None:
    """A check that cannot find the table would pass everything below it."""
    assert _KEYS_START in guide and _KEYS_END in guide
    table = guide.split(_KEYS_START, 1)[1].split(_KEYS_END, 1)[0]
    assert table.count("|") > 200, "the generated key table looks empty"


def test_every_bound_key_is_in_the_guide(guide: str) -> None:
    missing = sorted(
        f"{plain_label(menu)} > {plain_label(label)} ({key})"
        for menu, label, key, _handler, kind in COMMANDS
        if kind != "sep" and key not in guide
    )
    assert missing == [], (
        "These keys are bound and the user guide never names them, so nobody "
        "reading it will find them:\n  " + "\n  ".join(missing)
    )


def test_every_command_name_is_in_the_guide(guide: str) -> None:
    """A key with no name beside it is a key nobody can look up."""
    missing = sorted(
        plain_label(label)
        for _menu, label, _key, _handler, kind in COMMANDS
        if kind != "sep" and plain_label(label) not in guide
    )
    assert missing == [], "commands the guide never names: " + ", ".join(missing)


def test_every_switchable_area_is_named_by_its_checkbox_label(guide: str) -> None:
    """Somebody reading the guide has to be able to find the box to untick."""
    missing = sorted(area.label for area in AREAS if area.label not in guide)
    assert missing == [], (
        "Customize Features offers these and the guide does not name them: " + ", ".join(missing)
    )


def test_the_three_default_off_areas_are_marked_as_off(guide: str) -> None:
    """Off by default is only honest if the guide says which three, and why."""
    from quill.core.lite.features import DEFAULT_OFF

    labels = {area.id: area.label for area in AREAS}
    for area_id in DEFAULT_OFF:
        assert labels[area_id] in guide, area_id
    assert "off** | " in guide or "**off**" in guide, "the guide never marks anything off"


def test_every_status_bar_cell_is_named_by_the_label_it_announces(guide: str) -> None:
    missing = sorted(cell.label for cell in CELLS if cell.label not in guide)
    assert missing == [], "status-bar cells the guide never names: " + ", ".join(missing)


@pytest.mark.parametrize(
    "doc",
    ["prd.md", "userguide.md", "release-notes-1.0.md", "CHANGELOG.md"],
)
def test_every_shipped_document_has_its_rendered_pair(doc: str) -> None:
    """The docs-artifacts gate checks *changed* files; this checks they exist.

    A markdown file with no HTML beside it is a Help menu item that opens
    nothing, because the installer stages the rendered pages.
    """
    source = DOCS / doc
    assert source.is_file(), source
    for suffix in (".html", ".epub"):
        assert source.with_suffix(suffix).is_file(), source.with_suffix(suffix)


def test_the_guide_states_the_cost_of_the_mdi_window_model(guide: str) -> None:
    """The one thing a user will otherwise discover by being confused.

    Documents live inside one window, so they are not in Alt+Tab. That is a
    deliberate trade for the numbering, and a guide that omits it is a guide
    that lets somebody conclude the app is broken.
    """
    assert "Alt+Tab" in guide
    assert "not** appear in Alt+Tab" in guide or "do not appear in Alt+Tab" in guide


def test_the_guide_states_the_printing_limit(guide: str) -> None:
    """Rich formatting does not print in 1.0, and that has to be said up front."""
    assert "rich formatting does not print" in guide.lower()
