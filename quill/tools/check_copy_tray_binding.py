"""Copy Tray binding guard.

The twelve ``edit.paste_from_tray_N`` commands are a 0.6.0-shipped feature.
Their bindings — ``Ctrl+Shift+1``..``9`` and ``Ctrl+Shift+0``/``-``/``=`` —
are also the natural chord for a screen-reader user to reach for numeric
"apply heading level" / "insert list" / "wrap link" shortcuts.  Without a
guard, a future contributor can re-bind those digits to a different
command and silently break Copy Tray for every user on the default
keymap.

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
    ("edit.paste_from_tray_1", "Ctrl+Shift+1"),
    ("edit.paste_from_tray_2", "Ctrl+Shift+2"),
    ("edit.paste_from_tray_3", "Ctrl+Shift+3"),
    ("edit.paste_from_tray_4", "Ctrl+Shift+4"),
    ("edit.paste_from_tray_5", "Ctrl+Shift+5"),
    ("edit.paste_from_tray_6", "Ctrl+Shift+6"),
    ("edit.paste_from_tray_7", "Ctrl+Shift+7"),
    ("edit.paste_from_tray_8", "Ctrl+Shift+8"),
    ("edit.paste_from_tray_9", "Ctrl+Shift+9"),
    ("edit.paste_from_tray_10", "Ctrl+Shift+0"),
    ("edit.paste_from_tray_11", "Ctrl+Shift+-"),
    ("edit.paste_from_tray_12", "Ctrl+Shift+="),
)


def _resolved_keymap(profile_path: Path) -> dict[str, str]:
    """Return ``DEFAULT_KEYMAP`` overlaid with ``profile_path``'s bindings.

    Mirrors :func:`quill.core.keymap.load_keymap_profile` so the gate tests
    the same resolution the running app uses.  Falls back to the defaults
    copy if the profile file is missing or malformed so the gate does not
    hard-fail on a transient I/O error — the calling profile itself is
    linted separately by ``kqp_validator`` and the keymap import path.
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
    for key, value in bindings.items():
        if isinstance(key, str) and isinstance(value, str):
            merged[key] = value
    return merged


def _check_resolved(name: str, resolved: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for command_id, expected_binding in _PASTE_SLOTS:
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
        resolved = _resolved_keymap(_KEYMAP_DIR / profile_name)
        errors.extend(_check_resolved(profile_name, resolved))
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
