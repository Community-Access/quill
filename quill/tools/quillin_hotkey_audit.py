"""GATE-QHK: a Quillin may not claim a chord the core keymap already owns.

An extension declares ``hotkeys`` in its manifest, and nothing checked them
against ``DEFAULT_KEYMAP``. When two things claim one chord, **one of them
silently never fires** -- and which one it is depends on binding order, which
is not a thing anybody can reason about from the outside. The user presses the
key, gets the wrong verb or none, and has no way to find out why: neither the
menu nor the Keyboard Shortcuts sheet mentions the extension's claim.

The first run of this gate found all three bundled hotkeys colliding
(bad.md 7.4):

* ``markdown-helpers`` bound ``Ctrl+Shift+B``, which is Set Numbered Bookmark;
* ``math-equations`` bound ``Ctrl+Shift+E``, which is the core's own Insert
  Equation -- the extension was shadowing the command it duplicates;
* and ``Ctrl+Shift+Grave, F``, which is Speak Window Title on the leader.

**The Quillin moves, never the core.** An extension is the newcomer by
definition, and a core chord is one somebody's hands may already know; the
same rule the QuillVille launchers follow when they meet an editing verb.

Run::

    python -m quill.tools.quillin_hotkey_audit            # bundled Quillins
    python -m quill.tools.quillin_hotkey_audit <dir>      # one Quillin
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLED = REPO_ROOT / "quill" / "quillins_bundled"

#: Chords a Quillin may claim even though the core also binds them, each with
#: the reason. Empty, and meant to stay that way: the whole point of the gate is
#: that there is no such thing as a harmless double claim -- one of the pair
#: never fires and nothing says which.
ALLOWED: dict[str, str] = {}


@dataclass(frozen=True, slots=True)
class Collision:
    """One Quillin hotkey that a core command already answers to."""

    quillin: str
    command: str
    binding: str
    core_command: str

    def __str__(self) -> str:
        return (
            f"{self.quillin}: {self.command} claims {self.binding}, "
            f"which is {self.core_command}. The Quillin moves, not the core."
        )


def _identity(binding: str) -> str:
    """A chord, compared the way the keymap compares one.

    Modifier order and case must not make two spellings of one chord look like
    two chords -- ``Ctrl+Shift+B`` and ``Shift+Ctrl+B`` are the same key and a
    gate that missed that would be a gate somebody routes around by accident.
    """
    from quill.core.lite.keymap import chord_identity

    try:
        return str(chord_identity(binding))
    except Exception:  # noqa: BLE001 - an unparseable chord compares literally
        return (binding or "").strip().lower()


def _core_owners() -> dict[str, str]:
    """Every chord the core binds, to the command that owns it."""
    owners: dict[str, str] = {}
    for table in (DEFAULT_KEYMAP, DEFAULT_ALIASES):
        for command_id, binding in table.items():
            if binding:
                owners.setdefault(_identity(binding), command_id)
    return owners


def _hotkeys(manifest: dict[str, object]) -> list[dict[str, str]]:
    """The manifest's declared hotkeys, from either shape it may take."""
    contributes = manifest.get("contributes")
    source = contributes if isinstance(contributes, dict) else manifest
    raw = source.get("hotkeys") if isinstance(source, dict) else None
    return [entry for entry in raw or [] if isinstance(entry, dict)]


def audit(directories: list[Path]) -> list[Collision]:
    """Every collision across *directories*, each of which holds one Quillin."""
    owners = _core_owners()
    found: list[Collision] = []
    for directory in sorted(directories):
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # quillin_lint is the gate that reports a broken manifest
        for entry in _hotkeys(manifest):
            binding = str(entry.get("binding", "")).strip()
            if not binding or binding in ALLOWED:
                continue
            owner = owners.get(_identity(binding))
            if owner is None:
                continue
            found.append(
                Collision(
                    quillin=directory.name,
                    command=str(entry.get("command", "?")),
                    binding=binding,
                    core_command=owner,
                )
            )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "directory",
        nargs="?",
        help="One Quillin's folder. Omitted, every bundled Quillin is checked.",
    )
    args = parser.parse_args(argv)

    if args.directory:
        directories = [Path(args.directory)]
    else:
        directories = [child for child in BUNDLED.iterdir() if child.is_dir()]

    collisions = audit(directories)
    if not collisions:
        print("GATE-QHK Quillin hotkeys: no collisions with the core keymap.")
        return 0
    print("GATE-QHK Quillin hotkey collisions:", file=sys.stderr)
    for collision in collisions:
        print(f"  {collision}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
