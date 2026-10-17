"""GATE-DOCMENU for QUILL: what the user guide promises is on the menus.

The report that started it (Jeff, 2026-10-16) was about both editors. QUILL's
half was worse than QUILL Lite's: Search in Files and Replace Across Files were
gated by ``core.search.regex``, which Essential -- the profile every new install
starts in -- leaves off, and because the feature gated the *commands* as well as
the rows, ``Ctrl+Alt+Shift+F`` did nothing for a new user while QUILL Lite showed
it. Every chord gate stayed green: the key was bound, just not reachable.

This builds QUILL's real menu bar twice, in memory, on fresh data folders: once
as a new install gets it, and once with every profile area on and **Show
advanced AI features** checked. A path or a command named beside its key in the
user guide must be on the first; one that is only on the second passes where
the same chapter tells the reader how to switch it on.

**Not the root CHANGELOG.md.** That file is developer-facing and covers every
app in the family -- "View > Station Details" is Radio's, "View > Places" is
Cast's -- so checking it against QUILL's bar would be checking the wrong menu.
Each app's own user-facing changelog is gated by its own file here, and the
October 2026 sections of the root changelog were read by hand when this landed.

Safe on a desktop somebody is using: ``RegisterHotKey`` and the announcement
engine are replaced for the build, so no system-wide key is taken and nothing
is spoken; timers are stopped before the frame goes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from tests.unit.docs.menu_claims import (  # noqa: E402
    ROOT,
    MenuItem,
    OptIn,
    check_documents,
    items_from_wx_menu_bar,
)

GUIDE = ROOT / "docs" / "user guide" / "userguide.md"

#: Claims that are right although a new install's menu does not keep them.
ALLOW: dict[str, str] = {
    "path:tools > add-ons and themes": (
        "Thunderbird's own menu, in the steps for using QUILL as its external editor"
    ),
    "path:insert > explore equation structure": (
        "a row the bundled math-equations Quillin adds; the in-memory bar loads no Quillins"
    ),
}

#: The words a chapter uses to tell the reader how to reach a switched-off
#: command: the AI menu's own checkbox, and the profile switch.
_SWITCH_PHRASES = (
    "Show advanced AI features",
    "Profiles and Features",
    "feature profile",
    "Experimental tab",
)


def _stop_started_timers() -> None:
    """Stop the frame's clocks before it goes, as the app's own close path does.

    The harness records every owner-bound ``wx.Timer`` as it starts (its
    ``_WATCHED_WX_TIMERS``); the module pytest loaded is found by that name
    rather than imported, because importing ``tests.conftest`` again would give
    a second, empty copy.
    """
    for module in list(sys.modules.values()):
        watched = getattr(module, "_WATCHED_WX_TIMERS", None)
        if watched is None:
            continue
        for timer in list(watched):
            try:
                if timer.IsRunning():
                    timer.Stop()
            except RuntimeError:
                continue


def _build(data_dir: Path, monkeypatch: pytest.MonkeyPatch, *, everything: bool) -> list[MenuItem]:
    from unittest.mock import patch

    from quill.platform.windows import prism_bridge
    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.main_frame import MainFrame

    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.setattr(wx.Frame, "RegisterHotKey", lambda _self, *_a: False, raising=False)
    monkeypatch.setattr(wx.Frame, "UnregisterHotKey", lambda _self, *_a: True, raising=False)
    monkeypatch.setattr(prism_bridge.AnnouncementEngine, "announce", lambda _self, _m, **_k: None)
    if everything:
        (data_dir / "features.json").write_text(
            json.dumps({"active_profile_id": "full_quill"}), encoding="utf-8"
        )
        # The Experimental tab's master switch and its two menu-bearing
        # checkboxes: GLOW and Table Studio are rows of Tools > Writing and
        # Language only when these are on.
        (data_dir / "settings.json").write_text(
            json.dumps({
                "experimental_acknowledged": True,
                "glow_experimental_enabled": True,
                "table_studio_experimental_enabled": True,
            }),
            encoding="utf-8",
        )
        from quill.core.ai.onboarding import EXPERIENCE_ADVANCED, save_experience_mode

        save_experience_mode(EXPERIENCE_ADVANCED)
    app = wx.App()
    try:
        with patch.object(MainFrame, "check_for_updates", lambda self, **_kwargs: None):
            frame = MainFrame()
        items = items_from_wx_menu_bar(frame.frame.GetMenuBar())
        _stop_started_timers()
        frame.frame.Destroy()
    finally:
        set_transition_announcement_policy(None)
        del app
    return items


def test_every_guide_path_and_command_is_on_a_new_install_menu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    new_install = _build(tmp_path / "new", monkeypatch, everything=False)
    everything = _build(tmp_path / "all", monkeypatch, everything=True)
    edit = [item.path[-1].split("\t")[0] for item in new_install if item.path[:1] == ("&Edit",)]
    for title in ("Find in Open Documents", "Search in Files", "Replace Across Files"):
        assert any(title in row.replace("&", "") for row in edit), (
            f"{title} is not a row of Edit for a new install"
        )
    findings, used = check_documents(
        [GUIDE], new_install, ALLOW, opt_in=[OptIn(everything, _SWITCH_PHRASES)]
    )
    assert not findings, (
        "QUILL's user guide promises menu paths or commands a new install does "
        "not show (fix the guide, the menu, or say in the same chapter how to "
        "switch it on):\n  " + "\n  ".join(findings)
    )
    stale = sorted(set(ALLOW) - used)
    assert not stale, f"allowlist entries that no longer match anything: {stale}"
