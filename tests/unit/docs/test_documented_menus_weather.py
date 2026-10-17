"""GATE-DOCMENU for Quill Weather: what its changelog and guide promise is on its menus.

Builds the real Quill Weather menu bar in memory, with the empty data folder a
new install starts from, and reads ``standalone/weather/docs/CHANGELOG.md`` and
``userguide.md`` against it with the shared reader in ``menu_claims``. The first
run (2026-10-16) found the guide sending people to Help > Product Requirements
and the changelog promising a Command Palette, neither of which the menus had,
and the guide teaching Ctrl+Shift+M for a command on Ctrl+Alt+Shift+M.

Not ``machine_global``: the frame is built in Safe Mode with no show/hide key
(the default), the same way ``tests/unit/apps/test_weather_app.py`` builds it.
"""

from __future__ import annotations

import pytest

from tests.unit.docs.menu_claims import ROOT, check_documents, items_from_wx_menu_bar

wx = pytest.importorskip("wx")

DOCS = ROOT / "standalone" / "weather" / "docs"

#: Finding key -> why it is allowed. Empty: every finding so far was a document
#: to correct or a menu row to add.
ALLOW: dict[str, str] = {}

#: Keys Quill Weather binds with no menu row of its own, on purpose.
EXTRA_KEYS: dict[str, str] = {}


def test_weather_documents_promise_only_what_the_menus_show(
    quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A released build's menus: QUILL_DEV_BUILD=1 would add the gated apps to
    # the QuillVille menu, which a new user never sees.
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    from quill.apps.weather import WeatherAppFrame

    app = wx.App(False)
    frame = WeatherAppFrame(safe_mode=True)
    try:
        items = items_from_wx_menu_bar(frame.frame.GetMenuBar())
    finally:
        # The app's own shutdown stops its IPC poll timer; Destroy alone would
        # leave it firing into a freed window (see test_weather_app._dispose).
        WeatherAppFrame._weather_app_shutdown(frame)
        frame.frame.Destroy()
        app.Destroy()
    findings, used = check_documents(
        [DOCS / "CHANGELOG.md", DOCS / "userguide.md"], items, ALLOW, extra_keys=EXTRA_KEYS
    )
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
