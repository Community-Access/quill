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
from pathlib import Path

import pytest

_APPS = Path(__file__).resolve().parents[3] / "quill" / "apps"

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
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS, SIBLING_APP_FIXED_ACCELERATORS

    every = [*SIBLING_APP_ACCELERATORS, *SIBLING_APP_FIXED_ACCELERATORS.values()]
    broken = [chord for chord in every if not _binds(chord)]
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
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS, SIBLING_APP_FIXED_ACCELERATORS
    from quill.core.keymap_query import canonical_binding

    every = [*SIBLING_APP_ACCELERATORS, *SIBLING_APP_FIXED_ACCELERATORS.values()]
    launchers = {canonical_binding(chord) or chord for chord in every}
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


def test_there_is_a_launcher_key_for_every_row_a_public_menu_can_show(wx_app) -> None:
    """The QuillVille menu's own comment claims the house rule; make it true.

    An app never lists itself, so the longest possible menu is one row short of
    ``QUILLVILLE_APP_ORDER``. The tuple held three entries against seven apps,
    and the builder silently appended the rest with no accelerator at all.

    A sibling with a key of its own (Quill Cast, on its show/hide key) takes no
    positional key, so the longest menu needs one positional key per *other*
    sibling.

    **Public builds only, since 2026-10-16.** QUILL Transcribe's release made
    the developer-build menus longer than ``SIBLING_APP_ACCELERATORS``, and
    Jeff decided against a sixth key (the comment beside the tuple says why):
    a public build lists only ``RELEASED_APPS``, and that list must fit the
    keys. The developer-build overflow is the next test's business.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS, SIBLING_APP_FIXED_ACCELERATORS
    from quill.core.app_launcher import RELEASED_APPS
    from quill.ui.quillville_menu import QUILLVILLE_APP_ORDER

    fixed = set(SIBLING_APP_FIXED_ACCELERATORS)
    # Quill Cast builds no QuillVille menu, which is the only menu that would
    # list six positional siblings; if it gains one, it needs a sixth key.
    assert "build_quillville_menu" not in "".join(
        path.read_text(encoding="utf-8") for path in _APPS.glob("podcasts*.py")
    )
    for app in sorted(RELEASED_APPS):
        counted = [
            key
            for key in QUILLVILLE_APP_ORDER
            if key != app and key not in fixed and key in RELEASED_APPS
        ]
        assert len(SIBLING_APP_ACCELERATORS) >= len(counted), (
            f"{app}'s public menu can show {len(counted)} positional rows but only "
            f"{len(SIBLING_APP_ACCELERATORS)} launcher keys exist; the rows past the end "
            "ship with no keyboard route"
        )


class _FakeMenu:
    def __init__(self) -> None:
        self.labels: list[str] = []

    def Append(self, _id: object, label: str) -> None:  # noqa: N802 - wx shape
        self.labels.append(label)


class _FakeWx:
    EVT_MENU = object()

    @staticmethod
    def Menu() -> _FakeMenu:  # noqa: N802 - wx shape
        return _FakeMenu()

    @staticmethod
    def NewIdRef() -> object:  # noqa: N802 - wx shape
        return object()


def _quillville_rows(exclude: str) -> list[tuple[str, str]]:
    """(name, key) for each row of *exclude*'s QuillVille menu, as built."""
    from types import SimpleNamespace

    from quill.ui.quillville_menu import build_quillville_menu

    frame = SimpleNamespace(Bind=lambda *_a, **_k: None)
    menu = build_quillville_menu(
        _FakeWx, frame, lambda _key: None, exclude=exclude, retain=lambda _id: None
    )
    rows = []
    for label in menu.labels:
        name, _, key = label.partition(chr(9))
        rows.append((name.replace("&", ""), key))
    return rows


def _apps_that_build_a_quillville_menu() -> list[str]:
    """Every app whose source builds a QuillVille menu, read from the call sites
    (``exclude="<app>"``), so a new menu cannot escape the check below."""
    import re

    sources = [*_APPS.glob("*.py"), _APPS.parent / "ui" / "main_frame_menu.py"]
    found: set[str] = set()
    for path in sources:
        text = path.read_text(encoding="utf-8")
        if "build_quillville_menu(" not in text:
            continue
        found.update(re.findall(r'(?<!also_)exclude="(\w+)"', text))
    assert {"quill", "radio", "player"} <= found  # the scan still sees the menus
    return sorted(found)


def test_only_a_developer_build_shows_a_quillville_row_with_no_key(monkeypatch) -> None:
    """Jeff, 2026-10-16: no sixth launcher key.

    Built from the real menu builder, not counted from the tuples. In a public
    build (only ``RELEASED_APPS`` listed) every row of every app's menu shows a
    key. In a developer build, which lists the unreleased apps too, the rows
    past the fifth positional one carry no key -- the one deliberate exemption
    from the house rule, limited to developer builds, where nobody but the
    people building the family meets them. They keep their access letter
    (Alt+Q, then the letter) and can be bound in Keyboard Shortcuts.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS
    from quill.core.app_launcher import APP_NAMES, RELEASED_APPS
    from quill.ui import quillville_menu

    monkeypatch.setattr(quillville_menu, "is_app_released", lambda key: key in RELEASED_APPS)
    for app in sorted(RELEASED_APPS):
        keyless = [name for name, key in _quillville_rows(app) if not key]
        assert keyless == [], f"{app}'s public QuillVille menu has rows with no key: {keyless}"

    monkeypatch.setattr(quillville_menu, "is_app_released", lambda _key: True)
    unreleased = {f"Open {APP_NAMES[key]}" for key in APP_NAMES if key not in RELEASED_APPS}
    for app in _apps_that_build_a_quillville_menu():
        rows = _quillville_rows(app)
        keyed = [name for name, key in rows if key]
        keyless = [name for name, key in rows if not key]
        # Keys are handed out in order, so a keyless row only ever follows the
        # last positional key -- never a gap in the middle of the menu.
        assert all(key for _name, key in rows[: len(keyed)]), (
            f"{app}'s developer menu skips a key mid-list: {rows}"
        )
        # The overflow exists only because unreleased apps are listed: there are
        # never more keyless rows than unreleased siblings on the menu.
        listed_unreleased = [name for name, _key in rows if name in unreleased]
        assert len(keyless) <= len(listed_unreleased), (
            f"{app}'s developer menu has {len(keyless)} rows with no key but lists only "
            f"{len(listed_unreleased)} unreleased apps; a released app lost its key"
        )
        assert len(keyed) <= len(SIBLING_APP_ACCELERATORS) + 1  # + Cast's own F12
