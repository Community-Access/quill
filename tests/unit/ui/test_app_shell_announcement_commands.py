"""Every companion app carries the two accessibility commands.

``AppShellFrame.register_announcement_commands`` shipped with **no caller**,
so for all six companion apps (Radio, Cast, Weather, Converter, Audio Studio,
Beacon) "Repeat Last Announcement" and the "Announcement Self-Test" existed
only as dead code -- while the changelog and PRD said they shipped "in every
shell". These pin the wiring so the claim stays true.
"""

from __future__ import annotations

import ast
from pathlib import Path

_APP_SHELL = Path(__file__).resolve().parents[3] / "quill" / "ui" / "app_shell.py"


def _shell_calls_registration() -> bool:
    """True when AppShellFrame.__init__ actually calls the registration helper."""
    tree = ast.parse(_APP_SHELL.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "register_announcement_commands":
            return True
    return False


def test_the_shell_registers_the_announcement_commands() -> None:
    assert _shell_calls_registration(), (
        "AppShellFrame no longer calls register_announcement_commands(), so "
        "Repeat Last Announcement and the Announcement Self-Test are "
        "unreachable in every companion app."
    )


def test_registration_uses_try_register_so_an_app_can_override() -> None:
    # try_register (not register) means an app that defines its own copy of
    # either command keeps it, instead of the shell raising on a duplicate.
    source = _APP_SHELL.read_text(encoding="utf-8")
    start = source.index("def register_announcement_commands")
    body = source[start : start + 900]
    assert "try_register" in body
    assert "app.repeat_last_announcement" in body
    assert "app.announcement_self_test" in body
