"""GATE-DOCMENU for QUILL Cast: what its changelog and guide promise is on the menus.

Jeff, 2026-10-16: changelogs and guides promised commands he could not find in
the menus of the running app. This builds Cast's real menu bar in memory -- the
real ``PodcastsAppFrame`` over an empty data folder, with the release gates of a
public build, so it is the menu bar a new install opens with -- and asks the
shared reader in ``menu_claims`` which menu paths and name-beside-key claims in
the user-facing changelog and the user guide that menu bar does not keep.

Two windows' menus count, because the guide teaches both: the main window's,
and the Lineups window's (``quill.ui.lineups.menus.MENUS``, its whole menu bar
apart from the Window menu every peer window shares).

**Simple and Advanced.** A new install opens with Simple menus
(``quill.core.podcasts.menu_mode``), which leave out the rows a listener goes
looking for once they know they exist; View > Advanced Features
(Ctrl+Alt+Shift+G) builds them. That is a product decision, so the guide may
teach an Advanced row -- but only on a line that says it is one, because the
row and its key are both absent until the switch is on. A claim that fails on
the Simple bar, holds on the Advanced bar, and does not say "Advanced" where it
is made is a finding. And since the guide promises that every Advanced command
still answers from the Command Palette in Simple mode, the last test holds the
app to that.

Not ``machine_global``: everything that would reach outside the process is
patched out before the frame is built -- the screen-reader bridge (the
announcement engine probes the live reader), app sounds, the tray icon, global
hotkeys and media keys, the launch-at-startup heal, the first-run window and
every network check. The frame is never shown.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.unit.docs.menu_claims import (
    ROOT,
    MenuItem,
    check_documents,
    items_from_wx_menu_bar,
    normalise,
)

wx = pytest.importorskip("wx")

DOCS = [
    ROOT / "standalone" / "cast" / "docs" / "CHANGELOG.md",
    ROOT / "standalone" / "cast" / "docs" / "userguide.md",
]

#: Finding key -> why it is allowed. Keep it short and honest; fix the document
#: first.
ALLOW: dict[str, str] = {}

#: Keys Cast binds on purpose without a menu row: chord -> command name.
EXTRA_KEYS: dict[str, str] = {
    # Settings for This Podcast is a window with its own Save on Ctrl+S
    # (quill/ui/podcasts/show_settings_dialog.py); the guide's steps press it.
    "Ctrl+S": "Save",
}

#: Advanced rows the Command Palette reaches under another name, or not at all,
#: with the reason. Everything else Simple mode hides must be a palette command.
PALETTE_EXCEPTIONS: dict[str, str] = {
    "clear all podcast data from this computer": (
        "the palette's name is Delete All Podcast Data... (podcasts.delete_all_data, "
        "shared with QUILL's Podcasts manager); same handler"
    ),
    "redeem unlock code": (
        "a tester-only command, registered in developer builds only "
        "(quill/ui/main_frame_unlock_codes.py)"
    ),
    "quillins": "a whole menu, not a command",
    "manage quillins": "inside the Quillins menu, which is itself the Advanced row",
}


class _SilentEngine:
    """Stands in for the announcement engine, which probes the live reader."""

    def __init__(self, *_a, **_k) -> None:
        pass

    def __getattr__(self, _name):
        return lambda *_a, **_k: None


def _lineups_window_items() -> list[MenuItem]:
    from quill.ui.lineups.menus import MENUS

    items: list[MenuItem] = []
    for title, rows in MENUS:
        items.append(MenuItem((title,)))
        items.extend(MenuItem((title, label), key) for verb, label, key, _help in rows if verb)
    return items


@pytest.fixture
def cast_menus(quill_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """The menu items a new public install shows, in each mode, and its commands."""
    from tests.unit.apps.conftest import _close_cast_frame

    app = wx.GetApp() or wx.App()  # held: an unreferenced App is collected
    from quill.apps.podcasts import PodcastsAppFrame

    for name in (
        "_check_at_launch",
        "_start_folder_watching",
        "_maybe_resume_last_episode",
        "_maybe_check_updates_on_startup",
        "_cast_launch_notices",
        "_reload_global_hotkeys",
        "_say_launch_digest",
        "_register_media_keys",
        "_ensure_tray_icon",
        "_announce",
    ):
        monkeypatch.setattr(PodcastsAppFrame, name, lambda self, *a, **kw: None)
    monkeypatch.setattr(PodcastsAppFrame, "_register_tray_hotkey", lambda self, _chord: True)
    monkeypatch.setattr("quill.ui.app_shell.AnnouncementEngine", _SilentEngine)
    monkeypatch.setattr("quill.ui.app_shell.init_app_sound", lambda *_a, **_k: None)
    monkeypatch.setattr("quill.ui.app_sounds.apply", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "quill.platform.windows.launch_heal.heal_in_background", lambda *_a, **_k: None
    )
    monkeypatch.setattr("quill.ui.podcasts.first_run_dialog.maybe_run_first_run", lambda h: False)
    monkeypatch.setattr("quill.ui.sync_places_command.sync_at_launch", lambda h: False)
    monkeypatch.setattr(
        "quill.ui.data_folder_dialog.surface_data_folder_startup", lambda *_a, **_k: None
    )
    monkeypatch.setattr("quill.ui.updates.started.confirm_for_shell", lambda *_a, **_k: None)
    # A public build's release gates, not the developer build the test session
    # runs as: an unreleased feature's rows are not on a new user's menus.
    monkeypatch.setattr("quill.core.feature_catalog.is_dev_build", lambda: False)
    monkeypatch.setattr("quill.core.app_launcher.is_dev_build", lambda: False)

    previous_loop = wx.EventLoop.GetActive()
    loop = wx.GUIEventLoop()
    wx.EventLoop.SetActive(loop)
    frame = PodcastsAppFrame()
    try:
        lineups = _lineups_window_items()
        simple = items_from_wx_menu_bar(frame.frame.GetMenuBar()) + lineups
        palette = {
            normalise(command.title.removeprefix("Podcasts: "))
            for command in frame.commands.list(frame.features)
        }
        frame._podcast_history.menu_mode = "advanced"
        frame._build_menu_bar()
        advanced = items_from_wx_menu_bar(frame.frame.GetMenuBar()) + lineups
        yield SimpleNamespace(simple=simple, advanced=advanced, palette=palette)
    finally:
        assert app is not None
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(None)
        try:
            _close_cast_frame(frame, loop=loop)
        finally:
            wx.EventLoop.SetActive(previous_loop)


_WHERE = re.compile(r"^(?P<doc>[^:]+):(?P<line>\d+): ")


def _says_advanced(finding: str) -> bool:
    """Whether the sentence a finding comes from says the row is an Advanced one."""
    where = _WHERE.match(finding)
    assert where is not None, finding
    path = ROOT / "standalone" / "cast" / "docs" / where["doc"]
    lines = path.read_text(encoding="utf-8").splitlines()
    number = int(where["line"])
    # The line and its neighbours: a wrapped sentence names its mode on
    # whichever line the wrap put it.
    window = lines[max(0, number - 2) : number + 1]
    return any("Advanced" in line for line in window)


def test_a_new_install_opens_on_the_simple_menus(cast_menus) -> None:
    names = {" > ".join(item.path) for item in cast_menus.simple}
    assert "&View > Advanced Feature&s" in names
    assert "&Podcasts > &Back Up My Podcasts..." not in names
    assert len(cast_menus.advanced) > len(cast_menus.simple)


def test_cast_documents_promise_only_what_a_new_install_menu_shows(cast_menus) -> None:
    on_simple, used = check_documents(DOCS, cast_menus.simple, ALLOW, extra_keys=EXTRA_KEYS)
    on_advanced, _ = check_documents(DOCS, cast_menus.advanced, ALLOW, extra_keys=EXTRA_KEYS)
    advanced_only = set(on_simple) - set(on_advanced)
    findings = [f for f in on_simple if f not in advanced_only or not _says_advanced(f)]
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"


def test_every_row_simple_mode_hides_is_a_palette_command(cast_menus) -> None:
    """The guide: "every Advanced command still works from the Command Palette"."""
    shown = {item.path for item in cast_menus.simple}
    hidden = {normalise(item.path[-1]) for item in cast_menus.advanced if item.path not in shown}
    unreachable = sorted(hidden - cast_menus.palette - set(PALETTE_EXCEPTIONS))
    assert unreachable == [], f"Advanced rows no command reaches in Simple mode: {unreachable}"
    stale = sorted(set(PALETTE_EXCEPTIONS) - hidden)
    assert stale == [], f"stale palette exceptions: {stale}"
