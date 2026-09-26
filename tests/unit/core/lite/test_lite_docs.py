"""QUILL Lite's user guide cannot fall behind QUILL Lite.

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


def test_every_profile_has_its_own_section_in_the_guide(guide: str) -> None:
    """A profile is a decision, and a decision needs more than a table row.

    The dialog shows a paragraph and F1 reads it, but somebody choosing between
    four of them is reading the guide -- so each one gets a heading of its own
    saying what it keeps, what it removes and what Ctrl+N will make.
    """
    from quill.core.lite.features import PROFILES

    missing = sorted(p.name for p in PROFILES if f"#### {p.name}" not in guide)
    assert missing == [], "profiles with no section of their own: " + ", ".join(missing)


#: Words the guide is allowed to use for an area instead of its checkbox label,
#: where the label is a phrase and the prose is a sentence. Keyed by area id, and
#: each entry is a phrase that must appear in the profile's section.
_AREA_IN_PROSE: dict[str, str] = {
    "rich_text": "Format menu",
    "headings": "headings",
    "markup": "Markdown",
    "bookmarks": "bookmarks",
    "tools": "line tools",
    "clipboard": "clipboard",
    "abbreviations": "abbreviations",
    "selection": "Selection submenu",
    "spelling": "spell check",
    "autoformat": "autocorrect",
    "backups": "backups",
    "go_to_anything": "Go To Anything",
    "matches": "Matches",
    "history": "Back and Forward",
    "command_palette": "Command Palette",
    "character_info": "Describe Character",
    "zoom": "text size",
    "printing": "printing",
    "hosted_ai": "AI help",
    "dictation": "dictation",
}


def test_every_profile_section_names_what_that_profile_removes(guide: str) -> None:
    """The half of a profile's promise that is easiest to get wrong.

    What a profile *keeps* is visible the moment you use it. What it *removes*
    is a menu that is not there, which is exactly the thing somebody does not
    notice and cannot look up -- so the guide lists the removals by name, and
    this asserts the list is complete rather than nearly complete.

    It was not. WordPad and Notepad each switch off **AI help** and **Markdown
    and HTML**, and neither was in either section; Notepad's list had fifteen of
    its seventeen. Somebody choosing Notepad to get a small editor and then
    finding Ctrl+B in a `.md` no longer writes asterisks has no way to connect
    the two, because the paragraph that would have told them was the one that
    was short.

    Matched on a phrase rather than the checkbox label, because the labels are
    written for a checkbox ("Rich text and the Format menu") and the prose is
    written for a reader ("the Format menu and everything under it").
    """
    from quill.core.lite.features import AREAS, PROFILES

    known = {area.id for area in AREAS}
    unknown = sorted(set(_AREA_IN_PROSE) - known)
    assert unknown == [], f"_AREA_IN_PROSE names areas that no longer exist: {unknown}"
    unmapped = sorted(known - set(_AREA_IN_PROSE))
    assert unmapped == [], (
        f"a new area needs a phrase in _AREA_IN_PROSE before this can check it: {unmapped}"
    )

    problems: list[str] = []
    for profile in PROFILES:
        if not profile.disabled:
            continue
        start = guide.index(f"#### {profile.name}")
        section = guide[start:]
        end = section.find("\n#### ", 1)
        if end != -1:
            section = section[:end]
        # Whitespace-normalised, because the guide is hard-wrapped and a phrase
        # like "line tools" can arrive with a newline in the middle of it.
        lowered = " ".join(section.lower().split())
        for area_id in sorted(profile.disabled):
            phrase = _AREA_IN_PROSE[area_id]
            if phrase.lower() not in lowered:
                problems.append(f"{profile.name} removes {area_id} and never says so")
    assert problems == [], "\n".join(problems)


def test_the_guide_says_how_many_areas_each_profile_keeps(guide: str) -> None:
    """The number somebody comparing four profiles actually wants."""
    from quill.core.lite.features import AREAS, PROFILES

    for profile in PROFILES:
        on = len(AREAS) - len(profile.disabled)
        assert f"{on} of {len(AREAS)}" in guide, (
            f"{profile.name} keeps {on} and the guide never says"
        )


def test_the_guide_says_what_a_profile_that_claims_a_format_creates(guide: str) -> None:
    from quill.core.lite.features import PROFILES

    for profile in PROFILES:
        mode = dict(profile.settings).get("default_mode")
        if mode is None:
            continue
        assert f"Ctrl+N makes a {mode} text document" in guide, profile.name


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


def test_the_guide_does_not_describe_a_cell_that_is_not_there(guide: str) -> None:
    """The other direction, and the one that went wrong.

    The check above asks whether every real cell is documented and says nothing
    about rows the guide invents. The guide's status-bar table carried a
    **Language** row for months: the Format cell had been split into two in an
    earlier draft and the halves were never rejoined, so the table described
    fourteen cells where the bar has thirteen, and a reader arrowing along it
    counted wrong and went looking for a cell that has never existed. A wrong
    count is recoverable; hunting a bar for a control that is not in it is the
    same dead end as a key that does nothing.

    Scoped to the one table rather than the whole guide, because the prose
    around it reasonably names things that are not cells.
    """
    start = guide.index("| Part | What it tells you | Enter does |")
    table = guide[start:]
    table = table[: table.index("\n\n")]
    labels = {cell.label for cell in CELLS}
    rows = [
        line.split("|")[1].strip().strip("*")
        for line in table.splitlines()
        if line.startswith("| **")
    ]
    invented = sorted(row for row in rows if row not in labels)
    assert invented == [], "the guide's table has rows the status bar does not: " + ", ".join(
        invented
    )
    assert len(rows) == len(CELLS), (
        f"the table has {len(rows)} rows and the bar has {len(CELLS)} cells"
    )


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


def test_the_guide_says_rich_text_prints_as_rich_text(guide: str) -> None:
    """The limitation this used to assert is gone, so the assertion inverted.

    Until 2026-09-17 a rich document printed as flat text in one size, and the
    guide had to say so up front rather than let somebody find it on paper. It
    prints through the control's own renderer now (bad.md PR3,
    ``quill/ui/richedit_printing.py``), so the sentence a reader needs is the
    opposite one -- and a guide still carrying the old warning would send
    somebody looking for a workaround they no longer need.
    """
    assert "rich text prints as rich text" in guide.lower()
    assert "rich formatting does not print" not in guide.lower()
