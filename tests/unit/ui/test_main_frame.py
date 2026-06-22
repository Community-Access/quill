"""Tests for MainFrame dialog contract helpers (M-28: crash recovery focus)."""

from __future__ import annotations

import re
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_show_modal_dialog_has_restore_editor_focus_param() -> None:
    # M-28: _show_modal_dialog must accept restore_editor_focus to prevent
    # focus-racing in loops that re-show the same dialog.
    assert "restore_editor_focus: bool = True" in SOURCE


def test_crash_recovery_loop_does_not_steal_focus() -> None:
    # M-28: The crash-recovery re-show loop must pass restore_editor_focus=False
    # so editor.SetFocus is not called between loop iterations, which would race
    # with the dialog's own focus management.
    assert "restore_editor_focus=False" in SOURCE
    # The _show_modal_dialog call for Crash Recovery must carry the flag.
    crash_call = (
        "_show_modal_dialog(\n"
        '                    dialog, "Crash Recovery", restore_editor_focus=False\n'
        "                )"
    )
    assert crash_call in SOURCE


def test_document_tab_declares_language_profile_slots() -> None:
    # #263: _DocumentTab is @dataclass(slots=True) — every attribute assigned
    # elsewhere must be declared as a slot, or the assignment raises
    # AttributeError. _on_notebook_page_changed and the language picker
    # both write _language_profile and _language_profile_pinned; the slots
    # are what keeps those writes from crashing.
    tab_block_match = re.search(
        r"^class _DocumentTab:.*?(?=^class |\Z)", SOURCE, re.MULTILINE | re.DOTALL
    )
    assert tab_block_match is not None, "_DocumentTab block not found"
    block = tab_block_match.group(0)
    assert "_language_profile: object = None" in block
    assert "_language_profile_pinned: bool = False" in block


def test_open_startup_logs_handler_is_defined() -> None:
    # #263: Help > View Startup Logs... handler. Uses _reveal_in_explorer so
    # the OS opens the file in the default app.
    assert "def open_startup_logs(self) -> None" in SOURCE
    assert "startup-errors.log" in SOURCE


def test_help_view_startup_logs_menu_id_is_defined() -> None:
    # The Help > View Startup Logs... wiring requires the new id to appear in
    # both the menu build and the EVT_MENU binding.
    menu_src = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_menu.py"
    ).read_text(encoding="utf-8")
    assert "_id_view_startup_logs" in menu_src
    assert "help.view_startup_logs" in menu_src


def test_startup_speech_gate_uses_quiet_status() -> None:
    # #263: The "Ready. Tip..." and "Theme applied..." announcements must
    # keep showing in the status bar but stay silent on the screen reader
    # when announcement_startup_tips_enabled is off.
    assert "announcement_startup_tips_enabled" in SOURCE
    assert "_set_status_quiet" in SOURCE


def test_screen_reader_detected_announcement_is_gated() -> None:
    # The "Detected screen reader: ..." line at the screen-reader probe must
    # honor the new announce_screen_reader_detected AND verbosity_speech_enabled
    # gates. The status bar still receives the text in the off branch.
    assert "announce_screen_reader_detected" in SOURCE
    assert "verbosity_speech_enabled" in SOURCE


def test_show_about_quill_passes_real_about_info_instance() -> None:
    # #266: the traceback at line 11615 (`statuses = get_external_tool_statuses()`)
    # was from pre-#260 code. The current show_about_quill is a thin shim that
    # calls gather_about_info() and forwards the AboutInfo to
    # show_about_quill_native. This test pins the type-correct wire so the
    # native dialog's `isinstance(about_info, AboutInfo)` assert can never
    # silently go back to receiving a different shape.
    show_fn = re.search(
        r"def show_about_quill\(self\).*?(?=^    def |\Z)", SOURCE, re.DOTALL | re.MULTILINE
    )
    assert show_fn is not None, "show_about_quill not found"
    body = show_fn.group(0)
    assert "from quill.core.about_info import gather_about_info" in body
    assert "about_info = gather_about_info()" in body
    assert "show_about_quill_native(" in body


def test_close_tab_does_not_hit_undeclared_slot() -> None:
    # #266 traceback also includes the _DocumentTab slot crash at line 3923
    # (`tab._language_profile = ...`). That crash was closed by #263 (slots
    # added), but the close-document path is the user-visible surface that
    # triggered the dialog. This test asserts the close path lands in
    # _activate_tab, which is where the slot field is written — guards against
    # future refactors that re-introduce the regression by skipping the field.
    assert "def close_current_document(self)" in SOURCE
    assert "def _close_tab(self" in SOURCE
    assert "def _select_tab(self" in SOURCE
    assert "def _activate_tab(self" in SOURCE
    # The slot write site itself must remain in _activate_tab.
    activate_block = re.search(
        r"def _activate_tab\(self.*?(?=^    def |\Z)", SOURCE, re.DOTALL | re.MULTILINE
    )
    assert activate_block is not None, "_activate_tab not found"
    body = activate_block.group(0)
    assert "_language_profile_pinned" in body
    assert "_language_profile = get_profile_for_path" in body


def test_about_dialog_open_handler_calls_show_about_quill() -> None:
    # #264: the AssertionError dialog the user saw was from
    # show_about_quill_native asserting isinstance(about_info, AboutInfo).
    # The handler wired to the Help ▸ About Quill menu must be show_about_quill
    # — the shim that gathers AboutInfo correctly — not a stale pre-#260 path.
    menu_src = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_menu.py"
    ).read_text(encoding="utf-8")
    assert "_id_about_quill" in menu_src
    assert "show_about_quill" in menu_src
    # The About menu wiring must route through show_about_quill.
    assert (
        re.search(
            r"self\.frame\.Bind\(\s*wx\.EVT_MENU,\s*lambda _e:\s*self\.show_about_quill\(\),\s*id=self\._id_about_quill",  # noqa: E501
            menu_src,
        )
        is not None
    ), "About menu not bound to show_about_quill"
