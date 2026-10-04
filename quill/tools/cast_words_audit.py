"""GATE-CAST-WORDS: QUILL Cast says podcast, follow, unheard, find -- never the other words.

qc.md section 12 (Phase 5, P7): follow, unfollow, following; podcast, never
show or feed or subscription (except "OPML subscription list"); unheard,
never unplayed; find, never search; downloaded, never cached. The list and
the exemptions are :mod:`quill.core.podcasts.words`; this walks every string
literal that could reach a listener in the Cast UI (``quill/ui/podcasts`` and
``quill/apps/podcasts*.py``) and fails on a forbidden word that is not in the
reviewed allowlist, with the reason beside it.

It also walks the settings catalogue's words (``settings_defs_*.py`` and
``settings_help.py`` in ``quill/core/podcasts``): Preferences and Settings for
This Podcast build their rows from those labels and help sentences, so they
reach a listener as surely as a literal in a window does. Until 2026-10-03 they
were outside the scan, and Preferences said "When I subscribe" in an app that
never otherwise does. QUILL shows the same labels, and Cast's words read
plainly there too.

A literal counts when it has at least two words and no underscore (an
identifier is not a sentence). Docstrings are skipped: they are read by
developers. The allowlist is a ratchet -- an entry with no reason is an
unreviewed offence and fails the build, so a new one cannot be waved through
by regenerating.

Regenerate with::

    python -m quill.tools.cast_words_audit --write

and then write a reason beside every new entry, or fix the words.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

from quill.core.podcasts import words

__all__ = ["ALLOWLIST_PATH", "Offence", "main", "scan"]

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "cast_words_allowlist.json"
#: (directory, glob) pairs: every file a Cast listener's words come from.
_SCAN: tuple[tuple[str, str], ...] = (
    ("quill/ui/podcasts", "*.py"),
    ("quill/apps", "podcasts*.py"),
    ("quill/core/podcasts", "settings_defs_*.py"),
    ("quill/core/podcasts", "settings_help.py"),
)


class Offence(tuple):
    """``(key, offending words)`` where key is ``<file>::<literal>``."""

    __slots__ = ()

    @property
    def key(self) -> str:
        return str(self[0])

    @property
    def words(self) -> list[str]:
        return list(self[1])


def _files() -> list[Path]:
    found: list[Path] = []
    for rel, pattern in _SCAN:
        base = REPO_ROOT / rel
        if base.is_dir():
            found.extend(sorted(base.glob(pattern)))
    return found


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _is_sentence(text: str) -> bool:
    stripped = text.strip()
    return " " in stripped and "_" not in stripped and any(ch.isalpha() for ch in stripped)


def scan() -> list[Offence]:
    """Every forbidden word in every listener-facing literal, by file and literal."""
    offences: list[Offence] = []
    seen: set[str] = set()
    for path in _files():
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        skip = _docstring_nodes(tree)
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in skip or not _is_sentence(node.value):
                continue
            found = words.offences(node.value)
            if not found:
                continue
            key = f"{rel}::{node.value.strip()[:80]}"
            if key in seen:
                continue
            seen.add(key)
            offences.append(Offence((key, tuple(found))))
    return offences


def load_allowlist(path: Path = ALLOWLIST_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in data.items()} if isinstance(data, dict) else {}


def write_allowlist(entries: dict[str, str], path: Path = ALLOWLIST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(entries.items())), indent=2) + "\n", encoding="utf-8")


def violations(found: list[Offence], allowlist: dict[str, str]) -> list[str]:
    """What fails: an offence not in the list, or listed with no reason."""
    bad: list[str] = []
    for offence in found:
        reason = allowlist.get(offence.key)
        if reason is None:
            bad.append(f"{offence.key}  <- {', '.join(offence.words)} (not reviewed)")
        elif not reason.strip():
            bad.append(f"{offence.key}  <- {', '.join(offence.words)} (no reason given)")
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GATE-CAST-WORDS: the words QUILL Cast uses")
    parser.add_argument("--write", action="store_true", help="add new offences to the allowlist")
    args = parser.parse_args(argv)
    found = scan()
    allowlist = load_allowlist()
    if args.write:
        merged = {offence.key: allowlist.get(offence.key, "") for offence in found}
        write_allowlist(merged)
        print(f"Wrote {len(merged)} entries to {ALLOWLIST_PATH}")
        unreviewed = sum(1 for reason in merged.values() if not reason.strip())
        print(f"{unreviewed} without a reason: fix the words or write one beside each.")
        return 0
    bad = violations(found, allowlist)
    stale = sorted(key for key in allowlist if key not in {o.key for o in found})
    for line in bad:
        print(f"OFFENCE {line}")
    for key in stale:
        print(f"STALE   {key} (no longer in the source; remove it)")
    if bad or stale:
        print(f"GATE-CAST-WORDS: {len(bad)} offence(s), {len(stale)} stale allowlist entries.")
        return 1
    print(f"GATE-CAST-WORDS: {len(found)} reviewed literal(s), no new offences.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
