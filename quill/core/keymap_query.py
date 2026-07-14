"""Tolerant parsing, canonicalisation, and diagnostics for key bindings.

The stored keymap grammar is deliberately strict: ``"Ctrl+Shift+K"``,
``"Alt+Shift+Up"``, or the QUILL-key chord ``"Ctrl+Shift+Grave, S"``. Humans are
not. Someone hunting for a free shortcut will type ``control+shift+k``,
``SHIFT+CTRL+K``, ``ctl+k``, or even ``k+ctrl`` — all of which *mean* the same
chord. This module is the wx-free brain that makes the Keyboard Manager forgiving
and self-aware:

* :func:`parse_binding` accepts any of those spellings (alias-tolerant,
  order-independent, case-insensitive, chord-aware) and rejects genuine garbage.
* :func:`canonical_binding` collapses an accepted binding to one deterministic
  string, so two spellings of the same chord compare equal.
* :func:`find_keymap_conflicts` / :func:`commands_for_keystroke` answer "what
  else uses this key?" and "what does this key do?" using that canonical form —
  not a brittle ``.upper()`` string match.
* :func:`duplicate_bindings` / :func:`diagnose_keymap` power the diagnostics and
  self-heal surface.

Nothing here imports wx or touches disk; the UI layer owns capture and display.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "Binding",
    "KeymapDiagnostics",
    "bindings_equivalent",
    "canonical_binding",
    "commands_for_keystroke",
    "diagnose_keymap",
    "duplicate_bindings",
    "find_keymap_conflicts",
    "parse_binding",
]

#: Modifier spellings we accept, mapped to their canonical label. Windows-first
#: (QUILL's primary platform) but the mac spellings are accepted so a binding
#: typed from muscle memory still resolves. Canonical order is Ctrl, Alt, Shift —
#: the order every entry in ``DEFAULT_KEYMAP`` already uses.
_MODIFIER_ALIASES: dict[str, str] = {
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "ctl": "Ctrl",
    "alt": "Alt",
    "option": "Alt",
    "opt": "Alt",
    "shift": "Shift",
    "shft": "Shift",
    # Cmd is a *distinct* physical key from Ctrl on macOS (wx stores macOS
    # bindings as "Cmd+[" alongside Windows "Ctrl+["). It must never collapse to
    # Ctrl or the two would falsely conflict, so it keeps its own canonical token.
    "cmd": "Cmd",
    "command": "Cmd",
}

#: Canonical sort order for modifiers in the rendered binding. Cmd sorts first to
#: match the conventional macOS display ("Cmd+Shift+X").
_MODIFIER_ORDER: dict[str, int] = {"Cmd": 0, "Ctrl": 1, "Alt": 2, "Shift": 3}

#: Named (multi-character) keys we accept, mapped to their canonical label. The
#: canonical labels match the spellings already used in ``DEFAULT_KEYMAP`` so a
#: round-trip through this module leaves existing bindings untouched.
_NAMED_KEY_ALIASES: dict[str, str] = {
    "enter": "Enter",
    "return": "Enter",
    "ret": "Enter",
    "tab": "Tab",
    "space": "Space",
    "spacebar": "Space",
    "esc": "Escape",
    "escape": "Escape",
    "del": "Delete",
    "delete": "Delete",
    "backspace": "Backspace",
    "bksp": "Backspace",
    "bs": "Backspace",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pgup": "PageUp",
    "pagedown": "PageDown",
    "pgdn": "PageDown",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "ins": "Insert",
    "insert": "Insert",
    "grave": "Grave",
    "backtick": "Grave",
    "`": "Grave",
    "plus": "+",
    "minus": "-",
    "hyphen": "-",
    "equals": "=",
    "equal": "=",
}

#: QUILL-key prefix aliases. When a user types one of these as a leading segment
#: (``"quill+s"``, ``"quill key, s"``) it expands to the active prefix so the
#: branded chord can be searched and assigned by its friendly name.
_QUILL_KEY_ALIASES: frozenset[str] = frozenset({"quill", "quillkey", "quill key", "qk"})

#: Function keys F1-F24.
_FUNCTION_KEYS: dict[str, str] = {f"f{i}": f"F{i}" for i in range(1, 25)}


@dataclass(frozen=True)
class _Segment:
    """One chord segment: a set of modifiers plus exactly one key."""

    modifiers: frozenset[str]
    key: str

    def render(self) -> str:
        ordered = sorted(self.modifiers, key=lambda mod: _MODIFIER_ORDER.get(mod, 99))
        return "+".join([*ordered, self.key])


@dataclass(frozen=True)
class Binding:
    """A parsed, validated binding — one segment, or two for a QUILL-key chord."""

    segments: tuple[_Segment, ...]

    @property
    def is_chord(self) -> bool:
        return len(self.segments) > 1

    @property
    def canonical(self) -> str:
        return ", ".join(segment.render() for segment in self.segments)


def _canonical_key(token: str) -> str | None:
    """Return the canonical label for a single key token, or None if invalid."""
    lowered = token.lower()
    if lowered in _NAMED_KEY_ALIASES:
        return _NAMED_KEY_ALIASES[lowered]
    if lowered in _FUNCTION_KEYS:
        return _FUNCTION_KEYS[lowered]
    if len(token) == 1:
        # Single printable character (letter, digit, punctuation). Uppercased so
        # "k" and "K" collapse together; punctuation is unaffected by upper().
        return token.upper()
    return None


def _parse_segment(text: str, *, quill_key_prefix: str | None) -> _Segment | None:
    raw = text.strip()
    if not raw:
        return None
    # A QUILL-key alias used as the whole segment expands to the configured
    # prefix (itself a normal binding segment).
    if raw.lower() in _QUILL_KEY_ALIASES:
        if not quill_key_prefix:
            return None
        return _parse_segment(quill_key_prefix, quill_key_prefix=None)
    tokens = [part.strip() for part in raw.split("+") if part.strip()]
    if not tokens:
        return None
    modifiers: set[str] = set()
    key: str | None = None
    for token in tokens:
        lowered = token.lower()
        if lowered in _MODIFIER_ALIASES:
            modifiers.add(_MODIFIER_ALIASES[lowered])
            continue
        # Position-independent: the single non-modifier token is the key,
        # wherever the user happened to type it.
        if key is not None:
            return None  # two non-modifier keys in one segment is not a chord
        resolved = _canonical_key(token)
        if resolved is None:
            return None
        key = resolved
    if key is None:
        return None
    return _Segment(modifiers=frozenset(modifiers), key=key)


def parse_binding(text: str | None, *, quill_key_prefix: str | None = None) -> Binding | None:
    """Parse a human-typed binding into a validated :class:`Binding`, or None.

    Accepts modifier aliases (``control``/``ctl``/``ctrl``), any modifier order,
    any case, named keys (``return``/``enter``), and the QUILL-key chord grammar
    (``"<prefix>, <key>"`` or the ``"quill"`` alias). Returns None for anything
    that is not a real, assignable binding.
    """
    if text is None:
        return None
    raw = text.strip()
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts or len(parts) > 2:
        return None
    segments: list[_Segment] = []
    for part in parts:
        segment = _parse_segment(part, quill_key_prefix=quill_key_prefix)
        if segment is None:
            return None
        segments.append(segment)
    return Binding(segments=tuple(segments))


def canonical_binding(text: str | None, *, quill_key_prefix: str | None = None) -> str | None:
    """Return the deterministic canonical string for ``text``, or None if invalid."""
    parsed = parse_binding(text, quill_key_prefix=quill_key_prefix)
    return parsed.canonical if parsed is not None else None


def bindings_equivalent(
    first: str | None, second: str | None, *, quill_key_prefix: str | None = None
) -> bool:
    """True when two binding spellings denote the same chord."""
    left = canonical_binding(first, quill_key_prefix=quill_key_prefix)
    right = canonical_binding(second, quill_key_prefix=quill_key_prefix)
    return left is not None and left == right


def find_keymap_conflicts(
    keymap: Mapping[str, str],
    command_id: str,
    binding: str,
    *,
    quill_key_prefix: str | None = None,
) -> list[str]:
    """Return every *other* command whose binding equals ``binding``.

    Comparison is canonical, so ``"Shift+Ctrl+K"`` conflicts with a stored
    ``"Ctrl+Shift+K"``. The command being edited (``command_id``) is excluded.
    Order is stable (keymap iteration order) for predictable messaging.
    """
    candidate = canonical_binding(binding, quill_key_prefix=quill_key_prefix)
    if candidate is None:
        return []
    conflicts: list[str] = []
    for existing_command, existing_binding in keymap.items():
        if existing_command == command_id:
            continue
        existing = canonical_binding(existing_binding, quill_key_prefix=quill_key_prefix)
        if existing is not None and existing == candidate:
            conflicts.append(existing_command)
    return conflicts


def commands_for_keystroke(
    keymap: Mapping[str, str],
    binding: str,
    *,
    quill_key_prefix: str | None = None,
) -> list[str]:
    """Return every command bound to ``binding`` (reverse lookup for search)."""
    candidate = canonical_binding(binding, quill_key_prefix=quill_key_prefix)
    if candidate is None:
        return []
    matches: list[str] = []
    for command_id, existing_binding in keymap.items():
        existing = canonical_binding(existing_binding, quill_key_prefix=quill_key_prefix)
        if existing is not None and existing == candidate:
            matches.append(command_id)
    return matches


def duplicate_bindings(
    keymap: Mapping[str, str], *, quill_key_prefix: str | None = None
) -> dict[str, list[str]]:
    """Map each canonical binding used by more than one command to those commands.

    Empty/unassigned bindings are ignored. The returned command lists preserve
    keymap iteration order so the report is deterministic.
    """
    grouped: dict[str, list[str]] = defaultdict(list)
    for command_id, binding in keymap.items():
        canonical = canonical_binding(binding, quill_key_prefix=quill_key_prefix)
        if canonical is None:
            continue
        grouped[canonical].append(command_id)
    return {canonical: ids for canonical, ids in grouped.items() if len(ids) > 1}


@dataclass(frozen=True)
class KeymapDiagnostics:
    """A structured health report for a keymap.

    ``duplicates``: canonical binding -> the commands sharing it.
    ``invalid``: command -> its unparseable (non-empty) binding string.
    ``unknown_commands``: bound command ids not present in ``known_commands``.
    ``missing_dispatch``: bound, known command ids with no dispatch hook (no
    accelerator/menu integration) — the "assigned but inert" case the Heal
    action repairs.
    """

    duplicates: dict[str, list[str]]
    invalid: dict[str, str]
    unknown_commands: list[str]
    missing_dispatch: list[str]

    @property
    def ok(self) -> bool:
        return not (
            self.duplicates or self.invalid or self.unknown_commands or self.missing_dispatch
        )

    @property
    def issue_count(self) -> int:
        return (
            len(self.duplicates)
            + len(self.invalid)
            + len(self.unknown_commands)
            + len(self.missing_dispatch)
        )


def diagnose_keymap(
    keymap: Mapping[str, str],
    *,
    known_commands: set[str] | None = None,
    dispatchable_commands: set[str] | None = None,
    quill_key_prefix: str | None = None,
) -> KeymapDiagnostics:
    """Audit ``keymap`` for duplicates, invalid bindings, and dispatch gaps.

    ``known_commands`` (if given) is the set of command ids the app actually
    defines; bound ids outside it are reported as ``unknown_commands``.
    ``dispatchable_commands`` (if given) is the set that has a live dispatch hook
    (menu accelerator or command-registry binding); a known, bound command not in
    it is reported under ``missing_dispatch`` — a key the user assigned that would
    do nothing until re-applied. Both default to "do not check" so the pure
    duplicate/invalid audit works without UI context.
    """
    duplicates = duplicate_bindings(keymap, quill_key_prefix=quill_key_prefix)
    invalid: dict[str, str] = {}
    unknown: list[str] = []
    missing_dispatch: list[str] = []
    for command_id, binding in keymap.items():
        text = (binding or "").strip()
        if text and canonical_binding(text, quill_key_prefix=quill_key_prefix) is None:
            invalid[command_id] = text
        if known_commands is not None and command_id not in known_commands:
            unknown.append(command_id)
            continue
        if text and dispatchable_commands is not None and command_id not in dispatchable_commands:
            missing_dispatch.append(command_id)
    return KeymapDiagnostics(
        duplicates=duplicates,
        invalid=invalid,
        unknown_commands=unknown,
        missing_dispatch=missing_dispatch,
    )
