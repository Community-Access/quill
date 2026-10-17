"""GATE-DOCMENU for Quill Converter: what its changelog and guide promise is on its menus.

Builds the real Quill Converter menu bar in memory (``converter_menu.build_menu_bar``
through the real frame), with the empty data folder a new install starts from
and a released build's release gate, and reads
``standalone/converter/docs/CHANGELOG.md`` and ``userguide.md`` against it with
the shared reader in ``menu_claims``.

Not ``machine_global``: a new install has no show/hide key (it is chosen in
File > Show and Hide Key...), so building the frame registers nothing
system-wide; it is built in Safe Mode, as Weather's and Inkwell's gates are.
"""

from __future__ import annotations

import pytest

from tests.unit.docs.menu_claims import ROOT, check_documents, items_from_wx_menu_bar
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

DOCS = ROOT / "standalone" / "converter" / "docs"

#: Finding key -> why it is allowed.
ALLOW: dict[str, str] = {
    "path:file > preferences > app sounds play on": (
        "The released 1.0.0 changelog entry writes the App Sounds Play On... "
        "button inside the File > Preferences... window as one path. The button "
        "is real (converter_preferences.py, app_sounds.preference_action); it is "
        "a window's button, not a menu row, and the shipped entry is left as "
        "released. The user guide now says 'the App Sounds Play On... button in "
        "File > Preferences...'."
    ),
}

#: Keys Quill Converter binds with no menu row of its own, on purpose.
EXTRA_KEYS: dict[str, str] = {}


def test_converter_documents_promise_only_what_the_menus_show(
    quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A released build's menus: QUILL_DEV_BUILD=1 would add the gated apps to
    # the QuillVille menu, which a new user never sees.
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    from quill.apps import converter as converter_app

    monkeypatch.setattr(converter_app, "_find_ffmpeg", lambda: None)
    app = shared_wx_app()
    frame = converter_app.QuillConverterFrame(safe_mode=True)
    try:
        items = items_from_wx_menu_bar(frame.frame.GetMenuBar())
    finally:
        frame._ipc_timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()
        app.Destroy()
    findings, used = check_documents(
        [DOCS / "CHANGELOG.md", DOCS / "userguide.md"], items, ALLOW, extra_keys=EXTRA_KEYS
    )
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
