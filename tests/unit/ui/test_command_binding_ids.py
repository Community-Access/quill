"""Every command registers with its *own* key, not the one above it in the file.

Four commands in ``main_frame_commands.py`` were registered as
``self.commands.register("a.b", label, handler, self._binding_for("c.d"))`` --
the id of a neighbouring command, a copy-paste the eye slides straight over
because the shape is right and the strings are plausible. The cost is paid
twice: the command binds a chord that belongs to something else, so the menu
advertises a key that fires the other thing and its own key reaches nothing.

Three of the four shipped that way in 2026-09 and were found by the duplicate-
accelerator gate, which only sees the pair when *both* rows are in one menu bar.
Select Block advertised Ctrl+Shift+Y (Say Selected's), Title Case advertised
Ctrl+Shift+U (Upper Case's), Sentence Case advertised Ctrl+Shift+T (Title
Case's), and Set Bookmark advertised Ctrl+Alt+F6 (Set Document Language's).
This gate sees all four directly, before a menu is ever built.
"""

from __future__ import annotations

import ast
from pathlib import Path

UI = Path("quill/ui")


def _mismatches() -> list[str]:
    found: list[str] = []
    for path in sorted(UI.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Attribute) and node.func.attr == "register"):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            command_id = node.args[0].value
            if not isinstance(command_id, str):
                continue
            for arg in node.args[1:]:
                if (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and arg.func.attr == "_binding_for"
                    and arg.args
                    and isinstance(arg.args[0], ast.Constant)
                    and arg.args[0].value != command_id
                ):
                    found.append(
                        f"{path.as_posix()}:{node.lineno}: {command_id} "
                        f"registers _binding_for({arg.args[0].value!r})"
                    )
    return found


def test_no_command_borrows_another_commands_binding() -> None:
    assert _mismatches() == []
