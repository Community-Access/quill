"""QuillLite's keys: the table is the defaults, the user file is the overrides.

Until now a QuillLite key was a string literal in the fourth column of
:data:`~quill.core.lite.commands.COMMANDS`, read three times -- once for the menu
label, once for the accelerator, once for the Ctrl+F1 list. That is exactly what
made the keys impossible to drift and impossible to *change*: there was no keymap
object to rebind, only a table nobody outside the source tree can edit.

This module is the layer that makes them changeable without giving up either
property. The table stays the defaults -- it is still what the uniqueness gates
in ``tests/unit/core/lite/test_lite_commands.py`` assert against -- and a user's
choices live beside it in their own small file. Everything that used to read the
literal now reads :func:`binding_for`, so the three readers still cannot
disagree: there is one resolved answer and they all ask for it.

Three decisions worth stating, because each has a cheaper wrong version:

**Overrides are stored as deltas, never as a snapshot.** A file holding all 214
bindings would freeze today's defaults into a profile forever, so a key we
improve in a later version would never reach anybody who had launched the app
once. Only what a user actually changed is written, which is the same rule
``quill.core.lite.settings`` follows for the same reason.

**A chord's identity ignores how its modifiers were spelled.** ``Ctrl+Alt+Shift+H``
and ``Ctrl+Shift+Alt+H`` are one key to wx and to the keyboard, and two strings to
a set -- a distinction that let a collision through review once. Comparison goes
through :func:`chord_identity`; string equality is not a check.

**The Insert key can never be bound.** It is NVDA's and JAWS's modifier. Watching
it go past is fine and is what the Typing Mode cell does; claiming it would take
the screen reader's own key away from a user who cannot then turn it back.

wx-free, so the resolution rule and the conflict rule are testable without a
display. Whether wx can actually *fire* a binding is a different question and is
asked where wx lives (``quill/apps/lite_keymap_editor.py``), because a binding
that normalises cleanly and that ``wx.AcceleratorEntry`` refuses is assigned and
inert -- the one failure that looks like success from in here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.lite.commands import (
    COMMANDS,
    CommandRow,
    plain_label,
    split_menu,
    visible_commands,
)
from quill.core.storage import write_json_atomic

__all__ = [
    "KEYMAP_FILE",
    "RESERVED_KEYS",
    "KeymapAudit",
    "binding_for",
    "chord_identity",
    "command_titles",
    "conflicting_handlers",
    "default_keymap",
    "describe_binding_problem",
    "keymap_path",
    "load_keymap",
    "normalise_chord",
    "resolved_commands",
    "save_keymap",
]

#: The overrides file, beside the settings file in QuillLite's own data folder.
KEYMAP_FILE = "lite_keymap.json"

#: Bumped only if the stored shape changes. Present so a future reader can tell
#: a file it understands from one it does not, rather than guessing.
SCHEMA = 1

#: Modifier spellings a person might type, and what each one is.
_MODIFIER_ALIASES: dict[str, str] = {
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "ctl": "Ctrl",
    "alt": "Alt",
    "option": "Alt",
    "shift": "Shift",
    "win": "Win",
    "windows": "Win",
    "cmd": "Win",
    "command": "Win",
}

#: The order wx renders modifiers in, so a normalised chord and what
#: ``wx.AcceleratorEntry.ToString`` gives back are the same string.
_MODIFIER_ORDER: tuple[str, ...] = ("Ctrl", "Shift", "Alt", "Win")

#: Named keys, in the spelling wx accepts. Lower-cased alias to canonical.
_NAMED_KEYS: dict[str, str] = {
    name.lower(): name
    for name in (
        "Up",
        "Down",
        "Left",
        "Right",
        "Home",
        "End",
        "PageUp",
        "PageDown",
        "Insert",
        "Delete",
        "Back",
        "Tab",
        "Return",
        "Escape",
        "Space",
    )
}
_NAMED_KEYS.update({
    "enter": "Return",
    "esc": "Escape",
    "backspace": "Back",
    "del": "Delete",
    "ins": "Insert",
    "pgup": "PageUp",
    "pgdn": "PageDown",
    "pagedn": "PageDown",
})
_NAMED_KEYS.update({f"f{index}": f"F{index}" for index in range(1, 25)})

#: Keys QuillLite refuses to bind, with the reason a user is given. Insert is
#: the screen reader's own modifier; taking it would take away the key somebody
#: needs to get it back.
RESERVED_KEYS: dict[str, str] = {
    "Insert": (
        "Insert is the key NVDA and JAWS use as their own modifier, so QuillLite "
        "never binds it. Watching it go past is what the Typing Mode cell does."
    ),
}


# --------------------------------------------------------------------------- #
# Chords
# --------------------------------------------------------------------------- #


def normalise_chord(key: str) -> str:
    """*key* rewritten the way wx renders it, or "" if it is not a chord.

    Modifier aliases and order are forgiven; the key itself is canonicalised to
    the spelling ``wx.AcceleratorEntry`` accepts, so a punctuation key stays
    punctuation (``Ctrl+,``, which is the only spelling wx will parse) and a
    named key gets its wx name.
    """
    parts = [part.strip() for part in str(key).split("+") if part.strip()]
    if not parts:
        return ""
    modifiers: set[str] = set()
    main: str | None = None
    for part in parts:
        lowered = part.lower()
        if lowered in _MODIFIER_ALIASES:
            modifiers.add(_MODIFIER_ALIASES[lowered])
            continue
        if main is not None:
            return ""  # two non-modifier keys is not a chord
        if lowered in _NAMED_KEYS:
            main = _NAMED_KEYS[lowered]
        elif len(part) == 1:
            main = part.upper()
        else:
            return ""
    if main is None:
        return ""
    ordered = [mod for mod in _MODIFIER_ORDER if mod in modifiers]
    return "+".join([*ordered, main])


def chord_identity(key: str) -> str:
    """A chord's identity for comparison, independent of how it was spelled.

    Falls back to the lower-cased raw string for anything :func:`normalise_chord`
    refuses, so two equally unparseable strings still compare equal rather than
    quietly counting as two free keys.
    """
    return normalise_chord(key).lower() or str(key).strip().lower()


def describe_binding_problem(key: str) -> str:
    """Why *key* cannot be assigned, or "" when it can.

    A sentence rather than a boolean, because a refusal a user cannot act on is
    the same as no refusal at all.
    """
    text = str(key).strip()
    if not text:
        return "Press the key combination you want to use."
    chord = normalise_chord(text)
    if not chord:
        return f"{text} is not a key combination QuillLite can use."
    main = chord.split("+")[-1]
    if main in RESERVED_KEYS:
        return RESERVED_KEYS[main]
    if chord == main and len(main) == 1:
        return f"{main} on its own would type the letter instead. Add Ctrl, Alt or Shift."
    return ""


# --------------------------------------------------------------------------- #
# Defaults, read out of the command table
# --------------------------------------------------------------------------- #


def default_keymap() -> dict[str, str]:
    """Every handler's shipped key, taken from the command table.

    The table *is* the defaults. Nothing is copied into a second list that could
    fall out of step with it, which is what kept the keys drift-proof before
    there was a keymap at all.
    """
    return {
        handler: key
        for _menu, _label, key, handler, kind in COMMANDS
        if kind not in {"sep", "sub"} and handler and key
    }


def command_titles() -> dict[str, str]:
    """Handler to the name a person would recognise, with its menu path.

    "Sort Lines" alone is ambiguous in a list of two hundred; "Edit > Lines >
    Sort Lines" is where somebody would look for it, and is what the editor's
    search matches against.
    """
    titles: dict[str, str] = {}
    for menu, label, _key, handler, kind in COMMANDS:
        if kind in {"sep", "sub"} or not handler:
            continue
        parent, child = split_menu(menu)
        path = [plain_label(parent)]
        if child:
            path.append(plain_label(child))
        path.append(plain_label(label))
        titles[handler] = " > ".join(path)
    return titles


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #


def binding_for(keymap: dict[str, str], handler: str) -> str:
    """The key *handler* answers to now: the user's if they set one, else the default."""
    return keymap.get(handler, "")


def resolved_commands(
    is_enabled: Callable[[str], bool], keymap: dict[str, str] | None = None
) -> list[CommandRow]:
    """:func:`~quill.core.lite.commands.visible_commands` with the live keys in it.

    The one function the menu builder, the accelerator table and the Ctrl+F1
    list all go through, so a rebound key reaches all three or none of them.
    ``keymap`` of None means "the shipped keys", which is what every test that
    predates rebinding is asking for.
    """
    rows = visible_commands(is_enabled)
    if not keymap:
        return rows
    return [
        (menu, label, keymap.get(handler, key) if handler else key, handler, kind)
        for menu, label, key, handler, kind in rows
    ]


# --------------------------------------------------------------------------- #
# Conflicts and diagnosis
# --------------------------------------------------------------------------- #


def conflicting_handlers(keymap: dict[str, str], handler: str, key: str) -> list[str]:
    """Which other handlers already answer to *key*.

    Compared by identity, not by string: a user typing ``shift+ctrl+s`` is
    claiming the key ``Ctrl+Shift+S`` already has.
    """
    wanted = chord_identity(key)
    if not wanted:
        return []
    return sorted(
        other
        for other, bound in keymap.items()
        if other != handler and chord_identity(bound) == wanted
    )


@dataclass(frozen=True, slots=True)
class KeymapAudit:
    """What is wrong with a keymap, in the four ways it can be wrong."""

    duplicates: dict[str, list[str]] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)
    unparseable: list[str] = field(default_factory=list)
    reserved: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not (self.duplicates or self.unknown or self.unparseable or self.reserved)

    def summary(self) -> str:
        """One spoken sentence, because a listener should not have to read a table."""
        if self.is_clean:
            return "No problems found. Every key is unique, valid and reachable."
        counts = []
        if self.duplicates:
            counts.append(f"{len(self.duplicates)} keys claimed more than once")
        if self.unknown:
            counts.append(f"{len(self.unknown)} bindings for commands that no longer exist")
        if self.unparseable:
            counts.append(f"{len(self.unparseable)} bindings QuillLite cannot read")
        if self.reserved:
            counts.append(f"{len(self.reserved)} bindings on a reserved key")
        return "Found " + ", ".join(counts) + "."


def audit_keymap(keymap: dict[str, str], known: Iterable[str] | None = None) -> KeymapAudit:
    """Everything wrong with *keymap*, gathered in one pass.

    A duplicate means one of the pair silently never fires; an unknown handler
    means a binding a user set that now does nothing; an unparseable or reserved
    binding means a key that is assigned and inert. All four are invisible until
    somebody presses the key and hears nothing.
    """
    known_set = set(known) if known is not None else set(default_keymap())
    seen: dict[str, list[str]] = {}
    unparseable: list[str] = []
    reserved: list[str] = []
    for handler, key in sorted(keymap.items()):
        chord = normalise_chord(key)
        if not chord:
            unparseable.append(handler)
            continue
        if chord.split("+")[-1] in RESERVED_KEYS:
            reserved.append(handler)
        seen.setdefault(chord, []).append(handler)
    return KeymapAudit(
        duplicates={chord: owners for chord, owners in seen.items() if len(owners) > 1},
        unknown=sorted(set(keymap) - known_set),
        unparseable=unparseable,
        reserved=reserved,
    )


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #


def keymap_path(data_dir: Path) -> Path:
    return data_dir / KEYMAP_FILE


def load_keymap(data_dir: Path) -> dict[str, str]:
    """The shipped keys with the user's overrides on top.

    A missing, corrupt or foreign file reads as "no overrides", because a broken
    keymap file must leave the editor usable rather than keyless. An override
    for a handler that no longer exists is dropped on read: it can never fire,
    and keeping it would only let it collide with a key somebody can reach.
    """
    resolved = default_keymap()
    try:
        raw = json.loads(keymap_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return resolved
    overrides = raw.get("bindings") if isinstance(raw, dict) else None
    if not isinstance(overrides, dict):
        return resolved
    for handler, key in overrides.items():
        if handler in resolved and isinstance(key, str) and normalise_chord(key):
            resolved[handler] = normalise_chord(key)
    return resolved


def save_keymap(data_dir: Path, keymap: dict[str, str]) -> None:
    """Write only what differs from the shipped keys.

    Deltas, not a snapshot: a file holding all of today's bindings would freeze
    them into a profile forever, so a key improved in a later version would
    never reach anybody who had launched the app once.

    Raises ``OSError`` if the disk says no; that is the caller's to swallow,
    because a read-only profile must not make the editor unusable.
    """
    defaults = default_keymap()
    deltas = {
        handler: key
        for handler, key in sorted(keymap.items())
        if handler in defaults and chord_identity(key) != chord_identity(defaults[handler])
    }
    write_json_atomic(keymap_path(data_dir), {"schema": SCHEMA, "bindings": deltas})
