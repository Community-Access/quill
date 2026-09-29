"""The macOS view of a chord: Ctrl folded to Cmd, and the chords the Mac keeps.

Extracted from :mod:`quill.core.keymap` on 2026-09-28 (GATE-11) when two
Live Dictation bindings took that module over its ceiling. Nothing here
changed: it is the comparison-time view a keyboard pack's bindings are held
up against on macOS (#4), and the set of system chords no pack may steal.
"""

from __future__ import annotations

from quill.core.keymap_query import canonical_binding

__all__ = [
    "MACOS_RESERVED_RUNTIME_CHORDS",
    "darwin_runtime_chord",
    "is_macos_reserved_runtime_chord",
]

# macOS system-reserved chords a Quill binding must never steal on the Mac side
# of the Ctrl->Cmd accelerator mapping (#4). F9-F12 are the stock Mission
# Control / Spaces / Dashboard defaults; the Cmd+ chords are app-level ones
# (hide / minimize / quit / close / Spotlight / app switcher / window cycle).
MACOS_RESERVED_RUNTIME_CHORDS: frozenset[str] = frozenset({
    "Cmd+H",
    "Cmd+M",
    "Cmd+Q",
    "Cmd+W",
    "Cmd+Space",
    "Cmd+Tab",
    "Cmd+Grave",
    "F9",
    "F10",
    "F11",
    "F12",
})


def darwin_runtime_chord(chord: str, *, quill_key_prefix: str) -> str | None:
    """The chord as it fires on macOS, where wx maps ACCEL_CTRL to Cmd (#4).

    A pack stores ``"Ctrl+G"``; on macOS that fires as Cmd+G. To detect
    collisions against DEFAULT_KEYMAP's darwin ``"Cmd+G"`` entries, fold a
    leading Ctrl token to Cmd for comparison only. Storage is unchanged -- this
    is a comparison-time view, not a rewrite of the binding.
    """
    canonical = canonical_binding(chord, quill_key_prefix=quill_key_prefix)
    if canonical is None:
        return None
    if canonical.startswith("Ctrl+"):
        return "Cmd+" + canonical[len("Ctrl+") :]
    return canonical


def is_macos_reserved_runtime_chord(runtime_chord: str) -> bool:
    """True when *runtime_chord* (already Ctrl->Cmd folded) is macOS-reserved.

    Also flags ``Option+<single letter>`` (Alt with no other modifier): on macOS
    that is a dead-key / diacritical (Alt+A = å, Alt+E = acute accent, ...), so a
    pack binding there would steal a character the user types (support#67).
    """
    if runtime_chord in MACOS_RESERVED_RUNTIME_CHORDS:
        return True
    if runtime_chord.startswith("Alt+") and runtime_chord.count("+") == 1:
        key = runtime_chord[len("Alt+") :]
        if len(key) == 1 and key.isalpha():
            return True
    return False
