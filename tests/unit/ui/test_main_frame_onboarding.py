from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame


def _main_frame_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )


class _Frame:
    def GetMenuBar(self):  # noqa: N802 - mimics wx API
        return None


class _Wx:
    ICON_QUESTION = 0x0001
    ICON_INFORMATION = 0x0002
    ICON_WARNING = 0x0004
    YES_NO = 0x0008
    OK = 0x0010
    ID_OK = 5100
    ID_CANCEL = 5101
    YES = 5103
    NO = 5104
    NOT_FOUND = -1


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.settings = type("Settings", (), {})()
    frame._wx = _Wx()
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)
    frame._boxes: list[tuple[str, str, int]] = []
    return frame


def test_show_bw_onboarding_declined_stages_nothing(monkeypatch) -> None:
    frame = _build_frame()
    applied: list[str] = []
    frame._show_message_box = lambda message, caption, style: (
        frame._boxes.append((message, caption, style)) or _Wx.NO
    )
    monkeypatch.setattr(frame, "apply_bw_recommended_provider", lambda: applied.append("provider"))
    monkeypatch.setattr(frame, "apply_bw_recommended_model", lambda: applied.append("model"))

    frame._show_bw_onboarding(force=True)

    assert applied == []
    assert frame._status[-1] == "BITS Whisperer setup skipped"


def test_show_bw_onboarding_accepted_applies_recommended_defaults(monkeypatch) -> None:
    frame = _build_frame()
    frame.settings.bw_auto_open_status_page_on_download_start = True
    applied: list[str] = []
    frame._show_message_box = lambda message, caption, style: _Wx.YES
    monkeypatch.setattr(frame, "apply_bw_recommended_provider", lambda: applied.append("provider"))
    monkeypatch.setattr(frame, "apply_bw_recommended_model", lambda: applied.append("model"))

    frame._show_bw_onboarding(force=True)

    assert applied == ["provider", "model"]
    assert frame._status[-1] == "BITS Whisperer rollout defaults configured"


def test_show_profile_onboarding_uses_real_method_not_corrupted_link_dialog() -> None:
    # Regression for BUG-1: the remaining onboarding methods must exist and
    # reference only defined names (no leftover Insert Link copy-paste). The
    # legacy per-feature first-run prompts (profile/AI/etc.) were removed (#700).
    assert callable(getattr(MainFrame, "_show_bw_onboarding", None))
    assert callable(getattr(MainFrame, "_sync_ai_enabled_menu", None))


def test_startup_wizard_does_not_offer_bw_setup() -> None:
    # BITS Whisperer is deferred to QUILL 2.0; the setup wizard pages must not
    # include any BITS Whisperer / transcription onboarding for a 1.0 first run.
    wizard_source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "setup_wizard_pages.py"
    ).read_text(encoding="utf-8")
    assert "_show_bw_onboarding" not in wizard_source, (
        "setup_wizard_pages.py must not call _show_bw_onboarding "
        "(BW is deferred to QUILL 2.0 and the master flag is locked off)"
    )
    assert "bw_whisperer" not in wizard_source, (
        "setup_wizard_pages.py must not reference bw_whisperer; "
        "the wizard must not offer transcription setup in 1.0"
    )
