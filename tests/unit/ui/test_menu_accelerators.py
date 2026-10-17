"""Every menu item shows a way to reach it from the keyboard.

The house rule (CLAUDE.md; the radio PRD): a screen-reader user should never
have to walk a menu to discover there is no faster way in, and a menu item
that advertises a key must actually be reachable by it. Before this gate,
Quill Radio shipped 115 menu items of which 49 had no accelerator at all,
seven keys were claimed by two items each (so one of the pair silently never
fired), and two labels advertised "Ctrl+Shift+Plus"/"Minus" -- which wx
rejects outright with "Unrecognized accel key, accel string ignored".

Built from the real menu bar rather than by reading source, because that is
the thing the listener actually meets: submenus, dynamic rows and all.

Three apps are walked: Quill Radio, Quill Beacon and QUILL Social (todo.md
D.9, 2026-10-17). Beacon and Social build their bars in ways the source-level
gate (``test_app_menu_accelerators``) cannot read -- Beacon through an
``_add`` helper, Social from a table whose keys come from its own keymap --
and between them they had 47 enabled rows with no key at all (16 in Beacon,
31 in Social) while every gate stayed green.

Exempt, deliberately: a *disabled* item (Quill Radio's "Radio: stopped" is a
status readout, not a command -- there is nothing to invoke).
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

import pytest

from tests.wx_session import patch_call_after, shared_wx_app

wx = pytest.importorskip("wx")

_ROOT = Path(__file__).resolve().parents[3]

#: The apps whose real menu bars this gate walks. Each has a fixture below
#: named ``<app>_menu_bar``.
_APPS = ("radio", "beacon", "social")


@pytest.fixture
def _isolated_profile(quill_data_dir):
    """A data directory of this test's own.

    Building a real ``RadioAppFrame`` reads and *writes* the profile: it sweeps
    the undo-holding directory (deleting stale media as it goes), and the
    fixture below seeds twelve favorites into it. Against the developer's own
    profile that is exactly the incident ``tests/conftest.py`` was written
    about -- and on 2026-09-21 the guard there learned to watch deletions and
    caught this doing it.

    Function-scoped, and so is the frame it serves. The frame was module-scoped
    to build once; it cannot be, because ``QUILL_DATA_DIR`` set for a whole
    module outlives the first test and the environment-leak guard rightly fails
    it. One frame per test costs a fraction of a second and buys an isolation
    that is actually honest.
    """
    return quill_data_dir


@pytest.fixture
def radio_menu_bar(_isolated_profile):
    app = shared_wx_app()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    # The gate must walk a menu bar with DATA in it, not the empty-profile
    # default: the Favorites submenu is only appended when favorites exist, so
    # an empty fixture shipped rows with no keyboard route while this gate
    # stayed green (found 2026-08-17 — the blind spot polish.md called P0.2).
    # Twelve favorites (one foldered) exercise the ten quick-play slots AND the
    # disabled overflow readout; the menu bar is then rebuilt so the walk sees
    # what a real user's menu shows.
    from quill.core.radio.models import RadioStation

    favorites = frame._radio_favorites
    for index in range(1, 13):
        station = RadioStation(
            name=f"Gate Station {index}",
            stream_url=f"http://example.invalid/{index}",
        )
        favorites.add(station, folder="Morning" if index == 12 else "")
    frame._build_menu_bar()
    yield frame.frame.GetMenuBar()
    # Close the way the app closes: only its shutdown stops its timers, and a
    # timer whose owner window is deleted fires into freed memory later.
    frame._radio_shutdown()
    # Building the app installs a process-global dialog-transition policy;
    # leaving it set leaks this app's preference into every later test.
    set_transition_announcement_policy(None)
    del app


@pytest.fixture
def beacon_menu_bar(_isolated_profile, monkeypatch: pytest.MonkeyPatch):
    """Quill Beacon's real menu bar, over an empty data folder of its own.

    Beacon is a plain ``wx.Frame``; the machine doors are closed by hand, as
    ``tests/unit/docs/test_documented_menus_beacon.py`` does: no localhost
    capture bridge, no tray icon, no auto-sync timer, nothing deferred, and an
    announcer that keeps its status-bar half and never reaches the screen
    reader. None of that changes which rows ``_build_menu`` appends.
    """
    import quill.apps.beacon.app as beacon_app
    from quill.apps.beacon.announce import Announcer

    class _StatusBarOnly(Announcer):
        def _speak(self, *_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            return None

    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    monkeypatch.setenv("QUILLBEACON_DATA", str(_isolated_profile / "beacon"))
    monkeypatch.setattr(beacon_app, "Announcer", _StatusBarOnly)
    monkeypatch.setattr(beacon_app, "init_app_sound", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.app_sounds, "apply", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_setup_auto_sync", lambda self: None)
    patch_call_after(monkeypatch, lambda *_a, **_k: None)
    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
    app = shared_wx_app()
    frame = beacon_app.BeaconFrame()
    yield frame.GetMenuBar()
    frame.store.close()
    frame.Destroy()
    del app


@pytest.fixture
def social_menu_bar(_isolated_profile, monkeypatch: pytest.MonkeyPatch):
    """QUILL Social's real menu bar, imported from this tree's own source.

    The shared venv may carry an installed ``quill_social``; the worktree's
    copy is imported instead and any earlier one is put back afterwards. The
    doors are closed as ``test_documented_menus_social`` closes them: no
    speech engine, nothing deferred, credentials in memory rather than the
    Windows vault, and the scheduler timer stopped before the frame goes.
    """
    social = _ROOT / "standalone" / "social"
    saved = {n: m for n, m in sys.modules.items() if n.split(".")[0] == "quill_social"}
    for name in saved:
        del sys.modules[name]
    monkeypatch.syspath_prepend(str(social))
    frame = None
    try:
        import quill_social.ui.app as social_app
        from quill_social.security.credentials import InMemoryCredentialStore
        from quill_social.ui.announce import Announcer

        assert social in Path(social_app.__file__).resolve().parents
        monkeypatch.setenv("QUILLSOCIAL_DATA", str(_isolated_profile / "social"))
        monkeypatch.setattr(Announcer, "_make_speaker", lambda self: None)
        monkeypatch.setattr(social_app, "_make_credential_store", InMemoryCredentialStore)
        patch_call_after(monkeypatch, lambda *_a, **_k: None)
        monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
        app = shared_wx_app()
        frame = social_app.SocialFrame()
        yield frame.GetMenuBar()
        del app
    finally:
        if frame is not None:
            frame._closing = True
            frame._sched_timer.Stop()
            frame.store.close()
            frame.Destroy()
        for name in [n for n in sys.modules if n.split(".")[0] == "quill_social"]:
            del sys.modules[name]
        sys.modules.update(saved)


@pytest.fixture(params=_APPS)
def app_menu_bar(request):
    """``(app, menu bar)`` for each app this gate walks."""
    return request.param, request.getfixturevalue(f"{request.param}_menu_bar")


def _walk(menu, path, out):
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        label = item.GetItemLabel()
        submenu = item.GetSubMenu()
        if submenu is not None:
            _walk(submenu, f"{path} > {label.split(chr(9))[0]}", out)
            continue
        out.append((f"{path} > {label.split(chr(9))[0]}", label, item.IsEnabled()))


def _items(menu_bar):
    out: list[tuple[str, str, bool]] = []
    for index in range(menu_bar.GetMenuCount()):
        _walk(menu_bar.GetMenu(index), menu_bar.GetMenuLabel(index), out)
    return out


#: A route written in the label rather than as a native accelerator, the form
#: QUILL's menu_routes gives a keyless row: "Release Cha&nnel... (Alt+H, N)".
#: Help > Release Channel... is the one such row here; it has no chord on
#: purpose (keymap.py's help.release_channel: rules 4 and 9).
_ALT_PATH_ROUTE = re.compile(r"\(Alt\+[^()]*\)\s*$")


def test_every_enabled_menu_item_advertises_a_keyboard_route(app_menu_bar) -> None:
    app, menu_bar = app_menu_bar
    missing = [
        where
        for where, label, enabled in _items(menu_bar)
        if enabled and chr(9) not in label and not _ALT_PATH_ROUTE.search(label)
    ]
    assert missing == [], f"{app}: menu items with no accelerator: " + "; ".join(missing)


def test_no_two_menu_items_claim_the_same_key(app_menu_bar) -> None:
    """Two items on one key means one of them never fires -- worse than none,
    because the menu promises something it cannot deliver.

    Compared *canonically*, not as text. wx ignores the order the modifiers are
    written in, so "Ctrl+Shift+Alt+C" and "Ctrl+Alt+Shift+C" are one chord --
    and this gate, comparing raw strings, read them as two and stayed green
    while Choose Columns and Continue Listening shared a key. The Keyboard
    Manager already had the right answer (``keymap_query.canonical_binding``);
    it is used here so the two cannot disagree about what "the same key" means.
    """
    from quill.core.keymap_query import canonical_binding

    app, menu_bar = app_menu_bar
    claimed = collections.defaultdict(list)
    for where, label, _enabled in _items(menu_bar):
        if chr(9) in label:
            accel = label.split(chr(9), 1)[1].strip()
            claimed[canonical_binding(accel) or accel].append(where)
    duplicated = {key: where for key, where in claimed.items() if len(where) > 1}
    assert duplicated == {}, f"{app}: accelerators claimed twice: {duplicated}"


def test_every_advertised_key_is_one_wx_can_actually_bind(app_menu_bar) -> None:
    """wx parses the text after the tab; anything it cannot parse is dropped
    with a warning and the menu is left advertising a key that does nothing."""
    app, menu_bar = app_menu_bar
    unparsable = []
    for where, label, _enabled in _items(menu_bar):
        if chr(9) not in label:
            continue
        entry = wx.AcceleratorEntry()
        if not entry.FromString(label):
            unparsable.append(f"{where} ({label.split(chr(9), 1)[1]})")
    assert unparsable == [], f"{app}: wx cannot bind these: " + "; ".join(unparsable)


def test_no_menu_item_claims_a_table_navigation_key(app_menu_bar) -> None:
    """Ctrl+Alt+arrow belongs to table navigation and never reaches the app.

    Two claimants, not one: QUILL's own table navigation binds that block
    (keymap.table.next_cell and kin), and JAWS and NVDA bind it for *their*
    table navigation too -- so a menu item advertising one of these keys is
    advertising a key the screen reader eats before the app ever sees it
    (reported 2026-08-18: "ctralt and arrow keys will not work either, more
    table navigation keys for JAWS and NVDA").

    Quill Radio shipped six transport verbs there -- speed, chapters, position
    -- and they now read their keys from quill.core.radio.transport_commands.
    This is the gate that keeps them out.
    """
    app, menu_bar = app_menu_bar
    forbidden = {"ctrl+alt+up", "ctrl+alt+down", "ctrl+alt+left", "ctrl+alt+right"}
    offenders = []
    for where, label, _enabled in _items(menu_bar):
        _text, _, key = label.partition(chr(9))
        if key and key.replace(" ", "").lower() in forbidden:
            offenders.append(f"{where} -> {key}")

    assert not offenders, f"{app}: menu items on a table-navigation key: " + "; ".join(offenders)


def test_every_enabled_menu_item_has_an_access_letter(app_menu_bar) -> None:
    """Alt, the menu's letter, then the item's: every command reachable one key
    at a time, with nothing held down (BITS, 2026-09-28 -- a BrailleNote Evolve,
    or anyone for whom a four-key chord is hard). A menu of more than 26 items
    must share some letters, and pressing a shared letter again moves on to the
    next item that has it, so sharing is allowed; having none is not."""
    app, menu_bar = app_menu_bar
    exempt = _OUT_OF_LETTERS.get(app, frozenset())
    missing = [
        where
        for where, label, enabled in _items(menu_bar)
        if enabled and "&" not in label.split(chr(9))[0] and where.split(" > ")[-1] not in exempt
    ]
    assert missing == [], f"{app}: menu items with no access letter: " + "; ".join(missing)


#: The Station menu has more items than the alphabet has letters, and a letter
#: may not be claimed twice (test_menu_item_access_keys). Every letter in these
#: five labels is already another item's, so they keep only their keys --
#: Ctrl+comma, Ctrl+Q, Ctrl+Alt+P, Ctrl+Alt+O and Ctrl+O -- and Alt+S then the
#: arrows. Shrink this, never grow it: a new Station item takes a free letter.
#: Local Media joined on 2026-10-04 by the owner's decision: it had taken D,
#: which Download Preferences already had.
_STATION_MENU_OUT_OF_LETTERS = frozenset({
    "Preferences...",
    "Exit",
    "Connect to Spotify...",
    "Browse Spotify...",
    "Local Media...",
})

#: Per app, the rows that have run out of letters. Beacon and Social have none.
_OUT_OF_LETTERS = {"radio": _STATION_MENU_OUT_OF_LETTERS}


#: Apps whose every menu fits the alphabet, so no letter needs sharing. Pressing
#: a shared letter only moves to the item rather than choosing it, which means
#: the one-key-at-a-time path (Alt, the menu's letter, the item's letter) stops
#: one key short. Quill Radio's Station menu is longer than the alphabet and is
#: not held to this.
_UNIQUE_LETTER_APPS = ("beacon", "social")


@pytest.mark.parametrize("app", _UNIQUE_LETTER_APPS)
def test_no_access_letter_is_shared_within_one_menu(app, request) -> None:
    menu_bar = request.getfixturevalue(f"{app}_menu_bar")
    shared = []
    for index in range(menu_bar.GetMenuCount()):
        letters = collections.defaultdict(list)
        _letters(menu_bar.GetMenu(index), letters)
        title = menu_bar.GetMenuLabel(index).replace("&", "")
        shared += [f"{title}: {key!r} on {rows}" for key, rows in letters.items() if len(rows) > 1]
    assert shared == [], f"{app}: one letter, two rows: " + "; ".join(shared)


def _letters(menu, out) -> None:
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        key = _access_key(item.GetItemLabel())
        if key:
            out[key].append(item.GetItemLabel().split(chr(9))[0].replace("&", ""))


# -- the Alt paths the guide teaches ------------------------------------------

#: The guides a listener is handed for each app. Help > User Guide and Help >
#: Keyboard Reference open Social's two; Beacon's installer names the QuillSync
#: guide its User Guide.
_GUIDES = {
    "radio": (_ROOT / "standalone" / "radio" / "docs" / "userguide.md",),
    "beacon": (_ROOT / "standalone" / "beacon" / "docs" / "USER-GUIDE-QuillSync.md",),
    "social": (
        _ROOT / "standalone" / "social" / "docs" / "USER_GUIDE.md",
        _ROOT / "standalone" / "social" / "docs" / "KEYMAP_SPEC.md",
    ),
}
_DOC_ALT_PATH = re.compile(r"\bAlt\+([A-Z]),? then ([A-Z0-9])\b")


def _access_key(label: str) -> str:
    """The letter after a single ``&`` in *label*, lower case, or ``""``."""
    match = re.search(r"(?<!&)&([^&\s])", label.split(chr(9))[0])
    return match.group(1).lower() if match else ""


def test_every_alt_path_the_guide_teaches_reaches_a_menu_item(app_menu_bar) -> None:
    """ "Alt+Q, then W opens Quill Weather" must be true of the real menu bar.

    The chord gates check that a key the guide writes is bound; nothing checked
    the *menu path* a guide writes -- the letters a person presses to walk the
    menus -- so a renamed menu or a moved access key left the guide teaching a
    path that went somewhere else, or nowhere (P3, 2026-10-15).
    """
    app, menu_bar = app_menu_bar
    menus = {}
    for index in range(menu_bar.GetMenuCount()):
        key = _access_key(menu_bar.GetMenuLabel(index))
        if key:
            menus[key] = menu_bar.GetMenu(index)
    text = "\n".join(path.read_text(encoding="utf-8") for path in _GUIDES[app])
    paths = sorted(set(_DOC_ALT_PATH.findall(text)))
    assert paths, (
        f"{app}: the guide teaches no Alt paths; the pattern changed and this checks nothing"
    )
    wrong = []
    for menu_key, item_key in paths:
        menu = menus.get(menu_key.lower())
        if menu is None:
            wrong.append(f"Alt+{menu_key}: no top-level menu has that access key")
            continue
        items = [i for i in menu.GetMenuItems() if not i.IsSeparator()]
        if not any(_access_key(i.GetItemLabel()) == item_key.lower() for i in items):
            wrong.append(
                f"Alt+{menu_key}, then {item_key}: no item in that menu has that access key"
            )
    assert not wrong, f"the {app} guide teaches menu paths that do not exist:\n  " + "\n  ".join(
        wrong
    )
