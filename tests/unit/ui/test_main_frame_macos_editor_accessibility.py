"""#616: source-pin tests for the macOS editor accessibility changes.

These tests read ``quill/ui/main_frame.py`` directly and assert the
structural shape of the macOS branch. We do not drive a real wx
editor from a unit test (no wxWidgets runtime in CI), so the pin
is the only regression fence. If anyone removes the macOS branch,
these tests fail immediately and point at the issue.

The three things that must stay true for VoiceOver to read the
editor as a native text area:

1. ``_apply_silent_accessible`` is a no-op on macOS so the MSAA
   shim does not replace the native NSView role.
2. ``_create_document_tab`` drops ``TE_RICH2`` and ``TE_NOHIDESEL``
   on macOS so wx uses the standard NSTextView mapping for
   ``TE_MULTILINE``.
3. A helper reaches the editor's NSView and sets the AX role to
   ``NSTextView`` (Apple's ``NSAccessibilityRoleTextAreaRole``).
"""

from __future__ import annotations

import re
from pathlib import Path

MAIN_FRAME = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)

# Module-level patterns (extracted so the long regexes do not push
# individual test bodies past the 100-char line limit). Each pattern
# matches one full method body in main_frame.py.
_APPLY_SILENT_PATTERN = (
    r"def _apply_silent_accessible\(self, widget: object\) -> None:.*?(?=^    def |\Z)"
)
_CREATE_DOCUMENT_TAB_PATTERN = (
    r"def _create_document_tab\(self, document: Document, select: bool = True\) "
    r"-> int:.*?(?=^    def |\Z)"
)
_PIN_MACOS_ROLE_PATTERN = (
    r"def _pin_macos_editor_accessibility_role\(self, editor: object\) -> None:"
    r".*?(?=^    def |\Z)"
)
_MACOS_EDITOR_BRANCH_PATTERN = (
    r'if\s+sys\.platform\s*==\s*"darwin":\s*\n\s*editor\s*=\s*wx\.TextCtrl\('
    r"[^)]*style\s*=\s*wx\.TE_MULTILINE\s*\)"
)
# The non-macOS branch now selects the RichEdit version via ``rich_flag``
# (TE_RICH2 default, TE_RICH opt-in for the braille A/B), keeping TE_NOHIDESEL.
_WIN_EDITOR_BRANCH_PATTERN = (
    r"style\s*=\s*wx\.TE_MULTILINE\s*\|\s*rich_flag\s*\|\s*wx\.TE_NOHIDESEL"
)


def test_apply_silent_accessible_is_noop_on_macos() -> None:
    """#616: the MSAA shim is Windows-only; on darwin it would replace
    the native NSView role with a generic one and VoiceOver would stop
    seeing the nested NSTextView as a real text area.
    """
    body = re.search(_APPLY_SILENT_PATTERN, MAIN_FRAME, re.MULTILINE | re.DOTALL)
    assert body is not None, "_apply_silent_accessible not found"
    src = body.group(0)
    assert 'sys.platform == "darwin"' in src, "_apply_silent_accessible must early-return on macOS"
    # The early-return must come BEFORE the SetAccessible() call so
    # the wx.Accessible subclass is never installed on darwin.
    darwin_idx = src.find('sys.platform == "darwin"')
    set_accessible_idx = src.find("widget.SetAccessible(")
    assert 0 <= darwin_idx < set_accessible_idx, "macOS early-return must precede SetAccessible()"
    assert "return" in src.split('sys.platform == "darwin"', 1)[1].splitlines()[0:6].__str__(), (
        "macOS branch must include a return statement"
    )


def test_create_document_tab_drops_rich2_and_nohidesel_on_macos() -> None:
    """#616: TE_RICH2 and TE_NOHIDESEL are Windows-only. The macOS
    branch must build the editor with wx.TE_MULTILINE alone so wx
    maps the control to the native NSTextView.
    """
    body = re.search(_CREATE_DOCUMENT_TAB_PATTERN, MAIN_FRAME, re.MULTILINE | re.DOTALL)
    assert body is not None, "_create_document_tab not found"
    src = body.group(0)
    # The macOS branch exists and uses wx.TE_MULTILINE alone.
    assert re.search(_MACOS_EDITOR_BRANCH_PATTERN, src), (
        "macOS branch must build the editor with wx.TE_MULTILINE alone"
    )

    # The other branch (Windows / Linux) keeps TE_RICH2 + TE_NOHIDESEL
    # so the Windows screen-reader behaviour from #170 / #5890 is
    # untouched.
    assert re.search(_WIN_EDITOR_BRANCH_PATTERN, src), (
        "non-macOS branch must keep the rich_flag | TE_NOHIDESEL style for rich kinds"
    )
    # All three control kinds remain available: RichEdit 3.0 (default), RichEdit
    # 2.0, and a plain Notepad-style EDIT control for braille.
    assert "wx.TE_RICH2" in src, "RichEdit 3.0 (default) must remain"
    assert "wx.TE_RICH if" in src, "RichEdit 2.0 (legacy) option must remain"
    assert 'kind == "plain"' in src, "plain Notepad-style control option must exist"

    # After construction the macOS branch must call the role pinner.
    assert "_pin_macos_editor_accessibility_role(editor)" in src, (
        "macOS branch must invoke _pin_macos_editor_accessibility_role"
    )


def test_pin_macos_editor_accessibility_role_helper_exists() -> None:
    """#616: the helper reaches the editor's NSView via GetHandle()
    and sets NSAccessibilityRoleTextAreaRole so VoiceOver treats the
    editor as a native text area. The helper must be a no-op on
    non-darwin and must tolerate AppKit being unavailable.
    """
    body = re.search(_PIN_MACOS_ROLE_PATTERN, MAIN_FRAME, re.MULTILINE | re.DOTALL)
    assert body is not None, "_pin_macos_editor_accessibility_role not found"
    src = body.group(0)
    # Helper early-returns on non-darwin.
    assert 'sys.platform != "darwin"' in src, "helper must guard on sys.platform"
    # Imports AppKit and uses the text-area role constant.
    assert "AppKit" in src, "helper must import AppKit"
    assert "NSAccessibilityRoleTextAreaRole" in src, "helper must set the NSTextView role"
    # Uses GetHandle() to reach the NSView.
    assert "GetHandle" in src, "helper must use GetHandle() to reach NSView"
    # Calls setAccessibilityRole_ on the NSView.
    assert "setAccessibilityRole_" in src, "helper must call setAccessibilityRole_"
    # Defensive: tolerates missing AppKit via try/except import.
    assert re.search(r"except\s+Exception:\s*\n\s*return", src), (
        "AppKit import failure must be a silent no-op"
    )


def test_create_document_tab_documents_te_rich2_windows_only() -> None:
    """#616: the comment in _create_document_tab must explicitly call
    out that TE_RICH2 and TE_NOHIDESEL are Windows-only so the next
    reader of this code knows why the macOS branch exists.
    """
    body = re.search(_CREATE_DOCUMENT_TAB_PATTERN, MAIN_FRAME, re.MULTILINE | re.DOTALL)
    assert body is not None
    src = body.group(0)
    assert "#616" in src, "_create_document_tab must carry the #616 marker"
    assert "TE_RICH2" in src and "TE_NOHIDESEL" in src
    assert "Windows" in src, "comment must name Windows"
