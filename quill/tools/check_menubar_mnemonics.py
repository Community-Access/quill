"""GATE-15: a window's controls may not share an Alt letter with its menu bar.

Jeff, 2026-09-30, in QUILL Cast: "alt+s doesn't invoke the station menu either, it
invokes stop."

The main panel had a ``&Stop`` button and the menu bar had a ``&Subscriptions``
menu. Both claimed Alt+S, and on wxMSW an ambiguous Alt+letter goes to the
*control*, not the menu -- so the one key a listener uses to reach the first menu
in the bar pressed a button instead. ``Add to Fa&vorites`` did the same to the View
menu. GATE-14 could not see it, because GATE-14 scopes controls against controls
and menus against menus; the collision is *between* the two scopes.

The rule: **the menu bar wins.** Its top-level letters are how a keyboard listener
navigates the whole app, and a panel button is one Tab away regardless. So a
control whose mnemonic collides with a top-level menu is the one that moves.

What is checked, per app: the ``&`` letters of every top-level ``menu_bar.Append``
in the app's menu modules, against the ``&`` letters of every ``wx.Button``,
``wx.StaticText`` and ``wx.CheckBox`` label built in the app's main-panel module.
A label's mnemonic counts -- Alt+L on ``&Library:`` moves focus to the tree, and
would just as silently stop opening a menu.

Static, by AST, like the other gates: it reads the source rather than building a
window, so it runs in the pre-commit hook without a display.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["APPS", "DYNAMIC_LABELS", "Collision", "check_app", "main"]

_ROOT = Path(__file__).resolve().parents[2]

#: Per app: the modules whose top-level menu appends define the bar, and the
#: modules whose control labels share the window with it. An app absent here is
#: an app nobody has reviewed for this, which is worth a line in a report and is
#: not a pass.
APPS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "cast": (
        ("quill/apps/podcasts_menu.py", "quill/apps/podcasts_view_menu.py"),
        # Now Playing carries a copy of the main bar (qc.md section 5), so its
        # controls answer to the same rule as the main panel's.
        (
            "quill/ui/podcasts/main_panel.py",
            "quill/ui/podcasts/now_playing_layout.py",
            "quill/ui/notes_reader.py",
        ),
    ),
    "radio": (
        ("quill/apps/radio.py",),
        ("quill/apps/radio.py", "quill/ui/radio/main_transport_button.py"),
    ),
    "weather": (
        ("quill/apps/weather.py",),
        ("quill/apps/weather.py",),
    ),
}


def _cast_dynamic_labels() -> list[str]:
    from quill.core.podcasts import transport_intent

    return transport_intent.label_samples()


def _radio_dynamic_labels() -> list[str]:
    from quill.core import transport_button

    return transport_button.label_samples(transport_button.RADIO_MNEMONICS, active_verb="stop")


#: Labels a window builds at run time, which the source scan cannot see. The
#: survey of 2026-09-30 found ``&Pause`` reclaiming Alt+P from the Podcasts menu
#: the moment anything played: the gate had read only the static ``Pla&y``
#: literal, and the transport button's other two labels were computed. Each
#: provider returns every label shape its button can show, and they are checked
#: exactly like a literal.
DYNAMIC_LABELS: dict[str, tuple[tuple[str, Callable[[], list[str]]], ...]] = {
    "cast": (("quill/core/podcasts/transport_intent.py", _cast_dynamic_labels),),
    "radio": (("quill/core/transport_button.py", _radio_dynamic_labels),),
}

_MNEMONIC = re.compile(r"&([A-Za-z0-9])")
_CONTROLS = frozenset({"Button", "StaticText", "CheckBox", "RadioButton", "ToggleButton"})


@dataclass(frozen=True)
class Collision:
    app: str
    letter: str
    menu_label: str
    control_label: str
    control_file: str
    control_line: int

    def __str__(self) -> str:
        return (
            f"  {self.control_file}:{self.control_line}: {self.control_label!r} claims "
            f"Alt+{self.letter}, which is the {self.menu_label!r} menu"
        )


@dataclass
class _Found:
    menus: dict[str, str] = field(default_factory=dict)  # letter -> label
    controls: list[tuple[str, str, int]] = field(default_factory=list)  # label, file, line


def _letter(label: str) -> str | None:
    match = _MNEMONIC.search(label.replace("&&", ""))
    return match.group(1).upper() if match else None


def _string_of(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # f"{label}\t{accelerator}" -- the spine rows in the View menu build their
    # labels this way; the mnemonic is in the literal head of the f-string.
    if isinstance(node, ast.JoinedStr):
        head = node.values[0] if node.values else None
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    return None


def _scan(path: Path, found: _Found, *, menus: bool, controls: bool) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if menus and name == "Append" and isinstance(func, ast.Attribute):
            # menu_bar.Append(menu, "&Label") -- the receiver is a menu bar when
            # the second positional argument is the label. A wx.Menu.Append has
            # an id first and a label second, but its label carries an
            # accelerator tab and lives one level down, so it is excluded by the
            # receiver name.
            receiver = func.value
            receiver_name = getattr(receiver, "id", None) or getattr(receiver, "attr", "")
            if "menu_bar" in str(receiver_name) and len(node.args) >= 2:
                label = _string_of(node.args[1])
                letter = _letter(label) if label else None
                if letter:
                    found.menus.setdefault(letter, label or "")
        if controls and name in _CONTROLS:
            for keyword in node.keywords:
                if keyword.arg == "label":
                    label = _string_of(keyword.value)
                    if label and _letter(label):
                        found.controls.append((label, path.as_posix(), node.lineno))
            # wx.Button(parent, label=...) is the house style, but the positional
            # form exists: wx.Button(parent, id, "label").
            if len(node.args) >= 3:
                label = _string_of(node.args[2])
                if label and _letter(label):
                    found.controls.append((label, path.as_posix(), node.lineno))


def check_app(app: str) -> list[Collision]:
    menu_files, control_files = APPS[app]
    found = _Found()
    for rel in menu_files:
        _scan(_ROOT / rel, found, menus=True, controls=False)
    for rel in control_files:
        _scan(_ROOT / rel, found, menus=False, controls=True)
    for rel, provider in DYNAMIC_LABELS.get(app, ()):
        for label in provider():
            if _letter(label):
                found.controls.append((label, (_ROOT / rel).as_posix(), 0))
    collisions: list[Collision] = []
    for label, file, line in found.controls:
        letter = _letter(label)
        if letter and letter in found.menus:
            rel_file = Path(file).resolve().relative_to(_ROOT).as_posix()
            collisions.append(Collision(app, letter, found.menus[letter], label, rel_file, line))
    return collisions


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    apps = [a for a in args if a in APPS] or list(APPS)
    total = 0
    for app in apps:
        collisions = check_app(app)
        total += len(collisions)
        for collision in collisions:
            print(str(collision))
    if total:
        print(
            f"GATE-15: {total} control(s) share an Alt letter with a top-level menu. "
            "The menu bar wins -- move the control's mnemonic to a free letter."
        )
        return 1
    print("GATE-15: no window control shares an Alt letter with its menu bar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
