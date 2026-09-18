"""Copy Tray binding guard.

The twelve ``edit.paste_from_tray_N`` commands are a 0.6.0-shipped feature.
Their digits are also the natural chord for a screen-reader user to reach
for numeric "apply heading level" / "insert list" / "wrap link" shortcuts.
Without a guard, a future contributor can re-bind those digits to a
different command and silently break Copy Tray for every user on the
default keymap.

**The row moved on 2026-09-16, and this table moved with it.** Paste was on
``Ctrl+Shift+1``..``9`` / ``0`` / ``-`` / ``=`` and is now one modifier out,
on ``Ctrl+Alt+Shift+``.  The digits it gave up are Set Bookmark N -- which is
what QuillLite has meant by them since it shipped, and QUILL adopted the
shared numbered-bookmark core the same day (bad.md P0.1).  A bookmark is an
editing-loop verb and pasting slot seven by number is not, so the shorter
chord went to the bookmark.  The guard itself is unchanged in spirit: these
twelve chords belong to Copy Tray, and the gate is here so the next move is
also deliberate rather than accidental.

This gate runs as part of ``quill.tools.menu_lint`` (or directly via
``python -m quill.tools.check_copy_tray_binding``) and fails the build
if:

* any of the 12 expected ``edit.paste_from_tray_N`` bindings is missing,
* any of the 12 expected bindings is claimed by a *different* command
  in the resolved keymap (after the profile overlay is applied).

The check covers ``DEFAULT_KEYMAP`` plus every bundled ``profile_*.json``
under ``quill/core/keymap/``.  User-saved keymaps at
``%APPDATA%/quill/keymap.json`` are not in scope — users are explicitly
allowed to remap their own keys, but the shipped defaults must not change
without seeing this warning.

Run directly or via ``tests/unit/tools/test_check_copy_tray_binding.py``.
Exit code is non-zero when any violation is found.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KEYMAP_DIR = _REPO_ROOT / "quill" / "core" / "keymap"


def _discover_profiles() -> tuple[str, ...]:
    """Return the bundled ``profile_*.json`` filenames, sorted for stable output."""
    return tuple(sorted(p.name for p in _KEYMAP_DIR.glob("profile_*.json")))


# The 12 Copy Tray paste slots and the chord each one owns.  Order matches
# the slot number so error messages read naturally.
_PASTE_SLOTS: tuple[tuple[str, str], ...] = (
    ("edit.paste_from_tray_1", "Ctrl+Alt+Shift+1"),
    ("edit.paste_from_tray_2", "Ctrl+Alt+Shift+2"),
    ("edit.paste_from_tray_3", "Ctrl+Alt+Shift+3"),
    ("edit.paste_from_tray_4", "Ctrl+Alt+Shift+4"),
    ("edit.paste_from_tray_5", "Ctrl+Alt+Shift+5"),
    ("edit.paste_from_tray_6", "Ctrl+Alt+Shift+6"),
    ("edit.paste_from_tray_7", "Ctrl+Alt+Shift+7"),
    ("edit.paste_from_tray_8", "Ctrl+Alt+Shift+8"),
    ("edit.paste_from_tray_9", "Ctrl+Alt+Shift+9"),
    ("edit.paste_from_tray_10", "Ctrl+Alt+Shift+0"),
    ("edit.paste_from_tray_11", "Ctrl+Alt+Shift+-"),
    ("edit.paste_from_tray_12", "Ctrl+Alt+Shift+="),
)


def _resolved_keymap(profile_path: Path) -> dict[str, str]:
    """Return ``DEFAULT_KEYMAP`` overlaid with ``profile_path``'s bindings.

    Mirrors :func:`quill.core.keymap.load_keymap_profile` so the gate tests
    the same resolution the running app uses -- including the two profile
    shapes: an overlay on ``DEFAULT_KEYMAP``, or a subtractive profile
    (``_base: "none"``) where everything starts unbound and ``keep`` names
    what survives.  Falls back to the defaults copy if the profile file is
    missing or malformed so the gate does not hard-fail on a transient I/O
    error — the calling profile itself is linted separately by
    ``kqp_validator`` and the keymap import path.
    """
    from quill.core.keymap import DEFAULT_KEYMAP  # local import: avoid cycles

    merged = DEFAULT_KEYMAP.copy()
    if not profile_path.is_file():
        return merged
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not parse keymap profile %s: %s", profile_path.name, exc)
        return merged
    if not isinstance(data, dict):
        return merged
    bindings = data.get("bindings")
    if not isinstance(bindings, dict):
        return merged
    if data.get("_base") == "none":
        merged = dict.fromkeys(DEFAULT_KEYMAP, "")
        keep = data.get("keep")
        if isinstance(keep, list):
            for command_id in keep:
                if isinstance(command_id, str) and command_id in DEFAULT_KEYMAP:
                    merged[command_id] = DEFAULT_KEYMAP[command_id]
    for key, value in bindings.items():
        if isinstance(key, str) and isinstance(value, str):
            merged[key] = value
    return merged


def _is_subtractive(profile_path: Path) -> bool:
    """True when the profile unbinds by default (``_base: "none"``).

    A profile of that shape ships *fewer* commands on purpose -- "Minimal"
    exists to remove Copy Tray along with everything else it does not name --
    so the "all twelve slots present" half of this gate cannot apply to it.
    The half that still applies is the one that matters: nothing else may
    claim one of the twelve chords.
    """
    if not profile_path.is_file():
        return False
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("_base") == "none"


def _check_resolved(
    name: str, resolved: dict[str, str], *, require_slots: bool = True
) -> list[str]:
    errors: list[str] = []
    for command_id, expected_binding in _PASTE_SLOTS if require_slots else ():
        actual = resolved.get(command_id, "")
        if actual.strip().upper() != expected_binding.strip().upper():
            errors.append(
                f"  [{name}] {command_id!r} expected binding "
                f"{expected_binding!r}, got {actual!r}. "
                "Copy Tray paste slots are part of the shipped UX; "
                "do not re-bind them without an explicit release-note entry."
            )
    # Reverse check: nothing else should claim one of the 12 bindings.
    reserved: dict[str, str] = {
        binding.strip().upper(): command_id for command_id, binding in _PASTE_SLOTS
    }
    for command_id, binding in resolved.items():
        if command_id in {slot for slot, _ in _PASTE_SLOTS}:
            continue
        normalized = binding.strip().upper()
        if normalized in reserved:
            errors.append(
                f"  [{name}] {command_id!r} claims Copy Tray binding "
                f"{binding!r} (owned by {reserved[normalized]!r}). "
                "Pick a different chord."
            )
    return errors


def run_checks() -> list[str]:
    """Run the Copy Tray binding check across DEFAULT_KEYMAP and bundled profiles.

    Returns a flat list of error strings (empty list means clean).
    """
    errors: list[str] = []
    try:
        from quill.core.keymap import DEFAULT_KEYMAP
    except ImportError as exc:
        return [f"Cannot import DEFAULT_KEYMAP from quill.core.keymap: {exc}"]

    errors.extend(_check_resolved("DEFAULT_KEYMAP", DEFAULT_KEYMAP))
    for profile_name in _discover_profiles():
        profile_path = _KEYMAP_DIR / profile_name
        resolved = _resolved_keymap(profile_path)
        errors.extend(
            _check_resolved(profile_name, resolved, require_slots=not _is_subtractive(profile_path))
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    errors = run_checks()
    if errors:
        print("check_copy_tray_binding: FAIL", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    print("check_copy_tray_binding: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
