"""Every chord QUILL ships is one wx can actually bind, and nobody claims two.

The menu-accelerator gate walks Quill Radio's *menu bar*, which is the right
place to catch what a listener meets -- but it only ever walked Radio's. QUILL's
own menu bar shipped two faults that gate would have caught anywhere it looked:

* ``view.split_preview`` was ``"Ctrl+Shift+Backslash"``. ``wx`` has no name for
  that key, so it rejected the whole string ("Unrecognized accel key
  'Backslash', accel string ignored") and the View menu advertised a chord that
  could never fire. The only evidence was one line in the startup log.
* ``SIBLING_APP_ACCELERATORS`` moved onto F-keys in 2026-08 to get out of Quill
  Radio's quick-play favourites, and landed its third entry on
  ``power.count_occurrences``. In QUILL the Search menu's Count Occurrences and
  the QuillVille menu's Open Quill Inkwell claimed one key, so one of them never
  fired.

So this gate reads the *data* rather than a menu bar: every keymap, in every
app, whether or not anybody has built a window from it. It is the cheap half of
the pair -- `test_quill_menu_accelerators.py` walks QUILL's real menu bar for
what only a menu bar can show.
"""

from __future__ import annotations

import collections

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    del app


def _binds(chord: str) -> bool:
    """Whether ``wx`` can turn *chord* into a real accelerator."""
    entry = wx.AcceleratorEntry()
    with wx.LogNull():
        return bool(entry.FromString(chord))


def _single_chords(mapping: dict[str, str]) -> list[tuple[str, str]]:
    """``(command, chord)`` for the bindings wx is asked to parse.

    QUILL-key sequences ("Ctrl+Shift+Grave, V") are excluded: they are two
    keystrokes dispatched by QUILL's own chord handler, never handed to
    ``wxAcceleratorEntry``, which has no notion of a sequence.
    """
    return [
        (command, chord)
        for command, chord in sorted(mapping.items())
        if isinstance(chord, str) and chord and ", " not in chord
    ]


def _all_maps() -> list[tuple[str, dict[str, str]]]:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_KEYMAP

    return [("DEFAULT_KEYMAP", DEFAULT_KEYMAP), *sorted(APP_KEYMAPS.items())]


def test_every_default_chord_is_one_wx_can_bind(wx_app) -> None:
    broken = [
        f"{name}:{command} ({chord!r})"
        for name, mapping in _all_maps()
        for command, chord in _single_chords(mapping)
        if not _binds(chord)
    ]
    assert broken == [], (
        "wx drops these with a warning and leaves the menu advertising a key that "
        "does nothing: " + "; ".join(broken)
    )


def test_the_sibling_launcher_keys_are_bindable(wx_app) -> None:
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS

    broken = [chord for chord in SIBLING_APP_ACCELERATORS if not _binds(chord)]
    assert broken == [], f"wx cannot bind these QuillVille launcher keys: {broken}"


def test_no_two_commands_in_one_keymap_claim_the_same_key(wx_app) -> None:
    """Compared canonically -- wx ignores the order modifiers are written in."""
    from quill.core.keymap_query import canonical_binding

    for name, mapping in _all_maps():
        claimed = collections.defaultdict(list)
        for command, chord in sorted(mapping.items()):
            if isinstance(chord, str) and chord:
                claimed[canonical_binding(chord) or chord].append(command)
        duplicated = {key: who for key, who in claimed.items() if len(who) > 1}
        assert duplicated == {}, f"{name} claims a key twice: {duplicated}"


def test_the_sibling_launcher_keys_are_free_in_every_app(wx_app) -> None:
    """A QuillVille launcher must not sit on a command's key in any app.

    This is the check the 2026-08 move to F-keys did not have: it stepped off
    Quill Radio's quick-play favourites and onto QUILL's Count Occurrences,
    and nothing said so.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS
    from quill.core.keymap_query import canonical_binding

    launchers = {canonical_binding(chord) or chord for chord in SIBLING_APP_ACCELERATORS}
    collisions = []
    for name, mapping in _all_maps():
        for command, chord in sorted(mapping.items()):
            if not isinstance(chord, str) or not chord:
                continue
            if (canonical_binding(chord) or chord) in launchers:
                collisions.append(f"{name}:{command} ({chord})")
    assert collisions == [], (
        "a QuillVille launcher key is already a command's key, so one of the pair "
        "silently never fires: " + "; ".join(collisions)
    )


def test_there_is_a_launcher_key_for_every_row_the_menu_can_show(wx_app) -> None:
    """The QuillVille menu's own comment claims the house rule; make it true.

    An app never lists itself, so the longest possible menu is one row short of
    ``QUILLVILLE_APP_ORDER``. The tuple held three entries against seven apps,
    and the builder silently appended the rest with no accelerator at all.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS
    from quill.ui.quillville_menu import QUILLVILLE_APP_ORDER

    assert len(SIBLING_APP_ACCELERATORS) >= len(QUILLVILLE_APP_ORDER) - 1, (
        f"{len(QUILLVILLE_APP_ORDER) - 1} sibling rows are possible but only "
        f"{len(SIBLING_APP_ACCELERATORS)} launcher keys exist; the rows past the end "
        "ship with no keyboard route"
    )
