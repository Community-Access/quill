"""DLG-3 Phase 7: characterization of dialog/tab-launch command paths.

These tests pin the *return value and observable side effects* of the public
command methods that open a help/guide surface or a preview dialog, so the
CQ-1 decomposition of ``main_frame.py`` stays behaviour-preserving. They drive
a stub ``MainFrame`` skeleton (no live wx event loop) and assert the exact
sequence of side effects each command performs: the document/preview surface it
opens, the location-ring reset, the title refresh, and the final status line.

If a refactor changes any of these contracts, these tests fail first -- long
before a manual screen-reader pass -- which is the regression protection Phase 7
exists to provide.
"""

from __future__ import annotations

import quill.ui.main_frame as main_frame_module
from quill.ui.main_frame import MainFrame


class _Frame:
    def GetMenuBar(self):  # noqa: N802 - mimics wx API
        return None


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.features = None
    frame.settings = type("Settings", (), {})()
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)
    # Record the documents opened into tabs instead of building real wx widgets.
    frame._tabs: list[object] = []
    frame._create_document_tab = lambda document, select=True: (
        frame._tabs.append(document) or len(frame._tabs) - 1
    )
    frame._title_refreshes: list[int] = []
    frame._refresh_title = lambda: frame._title_refreshes.append(1)
    return frame


def test_open_welcome_guide_opens_markdown_tab_and_resets_navigation() -> None:
    frame = _build_frame()

    frame.open_welcome_guide()

    # One tab opened, carrying the Markdown welcome guide (never HTML).
    assert len(frame._tabs) == 1
    document = frame._tabs[0]
    assert document.text.startswith("# Welcome to Quill")
    assert document.path is None
    assert document.modified is False
    # Navigation was reset to the top of the new document.
    assert frame._location_ring._entries == [0]
    # Title refreshed and the canonical status line announced.
    assert frame._title_refreshes == [1]
    assert frame._status[-1] == "Opened welcome guide"


def test_open_third_party_notices_opens_tab_and_announces(monkeypatch, tmp_path) -> None:
    frame = _build_frame()
    fake_pyproject = tmp_path / "pyproject.toml"
    fake_pyproject.write_text("")
    frame._project_root_path = lambda: tmp_path
    frame._pyproject_path = lambda: fake_pyproject
    monkeypatch.setattr(
        main_frame_module,
        "render_full_third_party_notices",
        lambda pyproject, root: "NOTICES BODY",
    )

    frame.open_third_party_notices()

    assert len(frame._tabs) == 1
    assert frame._tabs[0].text == "NOTICES BODY"
    assert frame._location_ring._entries == [0]
    assert frame._title_refreshes == [1]
    assert frame._status[-1] == "Opened third-party notices"


def test_open_user_guide_falls_back_to_welcome_when_file_missing(monkeypatch) -> None:
    frame = _build_frame()

    # Force every candidate path to be reported missing so the documented
    # fallback path (open welcome guide + explanatory status) runs.
    monkeypatch.setattr(main_frame_module.Path, "is_file", lambda self: False)

    frame.open_user_guide()

    # Exactly one tab (the welcome-guide fallback) and the explanatory status.
    assert len(frame._tabs) == 1
    assert frame._tabs[0].text.startswith("# Welcome to Quill")
    assert frame._status[-1] == "User guide file not found; opened welcome guide instead."


def test_show_startup_wizard_page_opens_native_dialog_and_announces(monkeypatch) -> None:
    frame = _build_frame()
    frame.settings = type("Settings", (), {"bw_provider_id": "", "bw_speech_model_id": ""})()
    frame._wx = None  # not used when show_startup_wizard_page_native is monkeypatched
    frame._show_modal_dialog = lambda *_a, **_kw: None  # type: ignore[method-assign]

    calls: list[tuple] = []

    import quill.ui.info_pages as info_pages_module

    monkeypatch.setattr(
        info_pages_module,
        "show_startup_wizard_page_native",
        lambda parent, wx, steps, show_modal_dialog: calls.append((parent, steps)),
    )

    frame.show_startup_wizard_page()

    # Native dialog called once; no document tab opened; status announced.
    assert len(calls) == 1
    assert calls[0][0] is frame.frame
    assert frame._tabs == []
    assert frame._status[-1] == "Opened Startup Wizard overview"
