"""Tests for quill.tools.menu_lint (GATE-12)."""

from __future__ import annotations

from quill.tools.menu_lint import (
    _check_ctrl_alt,
    _check_depth,
    _check_required_clusters,
    run_checks,
)

# ---------------------------------------------------------------------------
# Ctrl+Alt policy
# ---------------------------------------------------------------------------


def test_ctrl_alt_clean_source_passes() -> None:
    src = 'DEFAULT_KEYMAP: dict[str, str] = {\n    "edit.find": "Ctrl+F",\n}\n'
    assert _check_ctrl_alt(src) == []


def test_ctrl_alt_detects_violation() -> None:
    src = 'DEFAULT_KEYMAP: dict[str, str] = {\n    "edit.bad": "Ctrl+Alt+X",\n}\n'
    errors = _check_ctrl_alt(src)
    assert any("Ctrl+Alt+" in e for e in errors)
    assert any("edit.bad" in e for e in errors)


def test_ctrl_alt_exempted_commands_pass() -> None:
    src = (
        "DEFAULT_KEYMAP: dict[str, str] = {\n"
        '    "view.send_to_tray": "Ctrl+Alt+T",\n'
        '    "view.toggle_tab_control": "Ctrl+Alt+Shift+T",\n'
        "}\n"
    )
    assert _check_ctrl_alt(src) == []


def test_ctrl_alt_case_insensitive() -> None:
    src = 'DEFAULT_KEYMAP: dict[str, str] = {\n    "edit.bad": "ctrl+alt+v",\n}\n'
    errors = _check_ctrl_alt(src)
    assert errors


def test_ctrl_alt_edsharp_heading_permitted() -> None:
    """EdSharp PR2: format.heading_1..6 are allowlisted because each
    binding carries a per-line # §edsharp-ok justification comment
    naming the screen-reader binding it overrides (NVDA switch-to-synth-N).
    """
    src = (
        "DEFAULT_KEYMAP: dict[str, str] = {\n"
        '    "format.heading_1": "Ctrl+Alt+1",  # §edsharp-ok — overrides NVDA switch-to-synth-1\n'
        '    "format.heading_6": "Ctrl+Alt+6",  # §edsharp-ok — overrides NVDA switch-to-synth-6\n'
        "}\n"
    )
    assert _check_ctrl_alt(src) == []


def test_ctrl_alt_uncommented_still_fails() -> None:
    """Regression: the gate still fires for an unlisted Ctrl+Alt+ binding
    even after the escape-hatch is introduced.  Ensures the per-binding
    justification comment is required."""
    src = 'DEFAULT_KEYMAP: dict[str, str] = {\n    "edit.something": "Ctrl+Alt+Q",\n}\n'
    errors = _check_ctrl_alt(src)
    assert errors
    assert any("edit.something" in e for e in errors)


def test_ctrl_alt_edsharp_comment_without_allowlist_entry_still_passes() -> None:
    """The escape hatch is per-binding: a Ctrl+Alt+ binding outside the
    global allowlist passes if its line carries # §edsharp-ok.  This is
    the path that lets future EdSharp-style bindings enter the keymap
    without needing a menu_lint.py edit each time."""
    src = (
        "DEFAULT_KEYMAP: dict[str, str] = {\n"
        '    "format.new_one_off_command": "Ctrl+Alt+Q",  # §edsharp-ok — justifies why\n'
        "}\n"
    )
    assert _check_ctrl_alt(src) == []


def test_ctrl_alt_shift_plus_does_not_match_ctrl_alt_gate() -> None:
    """Regression for #347: the regex `ctrl+alt+` was a prefix match, so it
    fired on every Ctrl+Alt+Shift+... binding. The gate's intent is the
    plain Ctrl+Alt+ chord; Ctrl+Alt+Shift+ is governed by §10.4 and is not
    this gate's concern. An unlisted Ctrl+Alt+Shift+ binding must pass."""
    src = (
        "DEFAULT_KEYMAP: dict[str, str] = {\n"
        '    "view.toggle_dark_mode": "Ctrl+Alt+Shift+D",\n'
        '    "tools.run_macro": "Ctrl+Alt+Shift+M",\n'
        "}\n"
    )
    assert _check_ctrl_alt(src) == []


def test_ctrl_alt_lower_case_shift_plus_does_not_match() -> None:
    src = 'DEFAULT_KEYMAP: dict[str, str] = {\n    "x": "ctrl+alt+shift+q",\n}\n'
    assert _check_ctrl_alt(src) == []


# ---------------------------------------------------------------------------
# Required clusters
# ---------------------------------------------------------------------------


def _fake_menu_source(*labels: str) -> str:
    """Build a fake main_frame_menu.py body with one AppendSubMenu(...) call
    per label, matching the real file's `_("...")`-wrapped label argument."""
    lines = ["from quill.core.i18n import _", ""]
    for index, label in enumerate(labels):
        lines.append(f"sub_{index} = wx.Menu()")
        lines.append(f'parent_menu.AppendSubMenu(sub_{index}, _("{label}"))')
    return "\n".join(lines)


def test_required_clusters_present() -> None:
    # All nine required cluster labels, each passed to a real AppendSubMenu call.
    fake = _fake_menu_source(
        "R&eading && Dictation",
        "C&omparison",
        "&Watch Folder",
        "AI &Assistant",
        "&Advanced",
        "&Quillins",
        "A&ccessibility",
        "&Customize && Support",
        "&Writing && Language",
    )
    assert _check_required_clusters(fake) == []


def test_required_clusters_missing_reports_error() -> None:
    fake = _fake_menu_source("C&omparison")  # most clusters absent
    errors = _check_required_clusters(fake)
    assert errors


def test_required_clusters_missing_writing_language() -> None:
    fake = _fake_menu_source(
        "R&eading && Dictation",
        "C&omparison",
        "&Watch Folder",
        "AI &Assistant",
        "&Advanced",
        "&Quillins",
        "A&ccessibility",
        "&Customize && Support",
    )
    errors = _check_required_clusters(fake)
    assert any("Writing" in e for e in errors)


def test_required_clusters_comment_mention_does_not_satisfy_gate() -> None:
    """Regression for #286: the old substring check would pass if a cluster's
    label text merely appeared in a comment. The AST check must not."""
    fake = '# TODO: rename the "AI &Assistant" cluster someday\nimport wx\n'
    errors = _check_required_clusters(fake)
    assert any("AI Assistant" in e for e in errors)


# ---------------------------------------------------------------------------
# Depth check
# ---------------------------------------------------------------------------


def test_depth_two_level_allowed() -> None:
    # tools_menu > power_tools_menu > macro_menu  (depth 2, no further children)
    src = (
        "def build():\n"
        "    tools_menu = wx.Menu()\n"
        "    power_tools_menu = wx.Menu()\n"
        "    macro_menu = wx.Menu()\n"
        "    macro_menu.Append(1, 'item')\n"
        "    power_tools_menu.AppendSubMenu(macro_menu, 'Macros')\n"
        "    tools_menu.AppendSubMenu(power_tools_menu, 'Power Tools')\n"
    )
    assert _check_depth(src) == []


def test_depth_three_level_flagged() -> None:
    # tools_menu > sub1 > sub2 > sub3 — sub2 is depth 2 with children
    src = (
        "def build():\n"
        "    tools_menu = wx.Menu()\n"
        "    sub1 = wx.Menu()\n"
        "    sub2 = wx.Menu()\n"
        "    sub3 = wx.Menu()\n"
        "    sub3.Append(1, 'item')\n"
        "    sub2.AppendSubMenu(sub3, 'Sub3')\n"
        "    sub1.AppendSubMenu(sub2, 'Sub2')\n"
        "    tools_menu.AppendSubMenu(sub1, 'Sub1')\n"
    )
    errors = _check_depth(src)
    assert errors
    assert any("sub2" in e for e in errors)


def test_depth_root_menus_ignored() -> None:
    # file_menu is depth 0 (root); it can have submenus without violation.
    src = (
        "def build():\n"
        "    file_menu = wx.Menu()\n"
        "    recent_menu = wx.Menu()\n"
        "    recent_menu.Append(1, 'item')\n"
        "    file_menu.AppendSubMenu(recent_menu, 'Recent')\n"
    )
    assert _check_depth(src) == []


# ---------------------------------------------------------------------------
# Integration: full run_checks on live source
# ---------------------------------------------------------------------------


def test_run_checks_passes_on_current_codebase() -> None:
    errors = run_checks()
    assert errors == [], "\n".join(errors)
