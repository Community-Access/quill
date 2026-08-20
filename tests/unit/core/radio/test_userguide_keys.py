"""The Quill Radio user guide advertises the keys the app actually binds.

The guide is where a listener goes to *learn* a key, so a stale one there costs
more than a stale comment: somebody presses it, nothing happens, and the honest
conclusion is that the feature is broken.

That is not hypothetical. When this was written (2026-08-19) the guide still
documented the pre-3.0 transport keys -- Next/Previous Chapter on
Ctrl+Alt+Right/Left and speed on Ctrl+Alt+Up/Down/0 -- which had moved off the
Ctrl+Alt+arrow block precisely because JAWS and NVDA claim it for table
navigation. Worse, its keyboard reference listed **Where Am I** and **Command
Palette** on the same Ctrl+Shift+P, and Go to Position on Ctrl+Shift+J, which
is the download queue. Four wrong keys and two collisions, in the one document
whose whole job is to be right about keys.

``transport_commands.COMMANDS`` is the authority: the menus, the accelerators,
the palette and the player panel are all built from it. This checks the guide
against it in both directions -- every current key is documented, and no
retired one lingers.
"""

from __future__ import annotations

import pathlib

from quill.core.radio import transport_commands as tc

_GUIDE = (
    pathlib.Path(__file__).resolve().parents[4] / "standalone" / "radio" / "docs" / "userguide.md"
)

#: Keys the transport verbs used before 3.0 moved them. Ctrl+Alt+arrow is
#: JAWS's and NVDA's table navigation, so a transport verb there works
#: everywhere except while somebody is reading a table -- the reason for the
#: move, and the reason a document must not still teach them.
RETIRED = ("Ctrl+Alt+Right", "Ctrl+Alt+Left", "Ctrl+Alt+Up", "Ctrl+Alt+Down", "Ctrl+Alt+0")


def _guide_text() -> str:
    return _GUIDE.read_text(encoding="utf-8")


def test_the_guide_exists_where_the_gate_looks() -> None:
    """A check that reads nothing passes forever."""
    assert _GUIDE.is_file(), _GUIDE
    assert len(_guide_text()) > 10_000


def test_every_transport_key_is_documented() -> None:
    text = _guide_text()

    missing = [f"{c.label.replace('&', '')} ({c.key})" for c in tc.COMMANDS if c.key not in text]

    assert not missing, "Keys the app binds but the user guide never names: " + ", ".join(missing)


def test_no_retired_transport_key_is_still_taught() -> None:
    text = _guide_text()

    lingering = [key for key in RETIRED if key in text]

    assert not lingering, (
        "The user guide still teaches keys that moved off Ctrl+Alt+arrow in 3.0: "
        + ", ".join(lingering)
    )


def test_where_am_i_and_the_palette_are_not_the_same_key() -> None:
    """The specific collision this file was written after.

    Both rows of the keyboard reference read Ctrl+Shift+P, so the guide told a
    reader that one key did two different things.
    """
    where = tc.command(tc.ANNOUNCE_POSITION)
    palette = tc.command(tc.COMMAND_PALETTE)

    assert where is not None and palette is not None
    assert where.key != palette.key
    assert f"| Where am I? (position, length, chapter) | {where.key} |" in _guide_text()
