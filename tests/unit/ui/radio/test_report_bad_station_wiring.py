"""Report Bad Station (#1218) is wired from the discovery surfaces to the shell.

The report *content* is unit-tested in tests/unit/core/radio/test_bad_station_report.py;
these guard the thin UI plumbing (callback param -> context-menu entry ->
mixin -> app shell) so it can't silently drop out. Source-level assertions,
matching the repo's other wiring guards (e.g. test_speech_hub_dialog)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]


def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_browse_tree_offers_report_bad_station_when_callback_present() -> None:
    # The row menu moved to browse_tree_menu.py under GATE-11 when Download...
    # arrived; the dialog still owns the injected callback, the menu builds the
    # entry from it, and both halves are asserted so neither can drift away.
    dialog = _src("quill/ui/radio/browse_tree_dialog.py")
    menu = _src("quill/ui/radio/browse_tree_menu.py")
    # What a row offers moved again, into wx-free core (row_actions.py), so the
    # label lives there and the wiring here; both halves are still asserted.
    actions = _src("quill/core/radio/row_actions.py")
    assert "on_report_bad_station" in dialog
    assert "Report &Bad Station..." in actions
    assert "REPORT_BAD" in menu
    # Only offered when a callback was injected (embedded QUILL passes none).
    assert "if dialog._on_report_bad_station is not None:" in menu


def test_station_browser_offers_report_bad_station_when_callback_present() -> None:
    src = _src("quill/ui/radio/station_browser_dialog.py")
    assert "on_report_bad_station" in src
    assert "Report &Bad Station..." in src
    assert "if self._on_report_bad_station is not None:" in src


def test_mixin_passes_the_shell_reporter_to_both_dialogs() -> None:
    src = _src("quill/ui/main_frame_radio.py")
    # Bound only when the host actually has it (standalone apps do; embedded
    # QUILL MainFrame does not, so it stays None -> no menu item there).
    assert src.count('on_report_bad_station=getattr(self, "report_bad_station", None)') == 2


def test_app_shell_reporter_prefills_and_self_identifies() -> None:
    src = _src("quill/ui/app_shell.py")
    assert "def report_bad_station(" in src
    assert "build_bad_station_report" in src
    # Pre-fill flows through to the report and defaults the app name from title.
    assert "prefill_summary=summary" in src
    assert "prefill_body=body" in src
    assert "frame.GetTitle()" in src
