"""A command the keymap binds is registered with that binding (#1703).

QUILL's menu shows a key, and wx builds the accelerator from it, only when the
command was registered with a binding. Eleven commands were registered with
``None`` although ``DEFAULT_KEYMAP`` gave them a key, so the keyboard reference
taught Ctrl+Alt+F2 for Get Help from Support and pressing it did nothing. The
CI keyboard run of core task 6 found it. QUILL-key chords ("Ctrl+Shift+Grave,
X") are exempt: the QUILL key dispatcher reads the keymap itself.
"""

from __future__ import annotations

import ast
from pathlib import Path

from quill.core.keymap import DEFAULT_KEYMAP

_COMMANDS = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_commands.py"

#: Registered without a key on purpose, with the reason.
_EXEMPT = {
    # Alt+I is also the Insert menu's access key in QUILL; giving the summary
    # an accelerator would take the menu away from the keyboard.
    "document.summary",
}


def _registered_without_binding() -> list[str]:
    tree = ast.parse(_COMMANDS.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "register"):
            continue
        if len(node.args) < 4:
            continue
        command, binding = node.args[0], node.args[3]
        if not (isinstance(command, ast.Constant) and isinstance(command.value, str)):
            continue
        if isinstance(binding, ast.Constant) and binding.value is None:
            found.append(command.value)
    return found


def test_keymap_bound_commands_are_registered_with_their_key() -> None:
    missing = [
        command
        for command in _registered_without_binding()
        if command not in _EXEMPT
        and DEFAULT_KEYMAP.get(command)
        and "," not in DEFAULT_KEYMAP[command]
    ]
    assert not missing, (
        "registered with no key although DEFAULT_KEYMAP binds one; pass "
        f"self._binding_for(...) instead: {sorted(missing)}"
    )
