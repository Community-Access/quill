"""CI gate for QUILL context-sensitive help coverage.

Two jobs, so context help stays current as features are added or changed:

1. **Integrity** (always fatal): ``topics.json`` must parse, ids must be
   unique and non-empty, every topic needs a non-empty title and body, and
   every ``see_also`` reference must resolve to a real topic id. A broken
   topics file silently disables F1 help, so these are hard errors.

2. **Coverage** (warning by default, fatal with ``--strict``): every command
   id in :data:`COMMAND_FEATURE_MAP` should have a matching help topic so F1
   on a menu item or command says something useful. Missing topics are
   reported grouped by feature namespace. This generalises the #294 braille
   regression guard to the whole command surface.

To add the missing topics quickly, scaffold stubs straight into
``topics.json``::

    python -m quill.tools.check_help_coverage --scaffold file.print
    python -m quill.tools.check_help_coverage --scaffold-missing braille

Run the gate::

    python -m quill.tools.check_help_coverage [--strict]

Exit code 0 = pass.  Exit code 1 = integrity failure, or (with ``--strict``)
any missing coverage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quill.core.feature_command_map import COMMAND_FEATURE_MAP
from quill.core.help import renderer as _renderer

_TOPICS_PATH = Path(_renderer.__file__).resolve().with_name("topics.json")


def _load_raw() -> list[dict]:
    if not _TOPICS_PATH.is_file():
        return []
    raw = json.loads(_TOPICS_PATH.read_text(encoding="utf-8"))
    return [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []


def _namespace(command_id: str) -> str:
    return command_id.split(".", 1)[0] if "." in command_id else command_id


def check_integrity(entries: list[dict]) -> list[str]:
    """Return a list of integrity error messages (empty == clean)."""
    errors: list[str] = []
    seen: set[str] = set()
    ids: set[str] = set()
    for entry in entries:
        topic_id = str(entry.get("id", "")).strip()
        if not topic_id:
            errors.append(f"topic with empty id: {entry!r}")
            continue
        if topic_id in seen:
            errors.append(f"duplicate topic id: {topic_id!r}")
        seen.add(topic_id)
        ids.add(topic_id)
        if not str(entry.get("title", "")).strip():
            errors.append(f"{topic_id!r}: empty title")
        if not str(entry.get("body", "")).strip():
            errors.append(f"{topic_id!r}: empty body")
    for entry in entries:
        topic_id = str(entry.get("id", "")).strip()
        for ref in entry.get("see_also", []) or []:
            if str(ref) not in ids:
                errors.append(f"{topic_id!r}: see_also references unknown topic {ref!r}")
    return errors


def missing_command_topics(topic_ids: set[str]) -> list[str]:
    """Command ids that have no matching help topic, sorted."""
    return sorted(cmd for cmd in COMMAND_FEATURE_MAP if cmd not in topic_ids)


def _scaffold(new_ids: list[str]) -> int:
    """Append stub topics for *new_ids* to topics.json (sorted, deduped)."""
    entries = _load_raw()
    existing = {str(e.get("id", "")) for e in entries}
    added: list[str] = []
    for topic_id in new_ids:
        if topic_id in existing:
            continue
        title = topic_id.rsplit(".", 1)[-1].replace("_", " ").title()
        entries.append({
            "id": topic_id,
            "title": title,
            "body": "TODO: describe what this control or command does.",
        })
        existing.add(topic_id)
        added.append(topic_id)
    if not added:
        print("scaffold: nothing to add (all ids already have topics)")
        return 0
    entries.sort(key=lambda e: str(e.get("id", "")))
    _TOPICS_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"scaffold: added {len(added)} stub topic(s): {', '.join(added)}")
    print("Now fill in the 'body' (and optional 'keystrokes') in topics.json.")
    return 0


def run(strict: bool = False) -> int:
    entries = _load_raw()
    if not entries:
        print(f"check_help_coverage: no topics loaded from {_TOPICS_PATH}")
        return 1

    errors = check_integrity(entries)
    if errors:
        print(f"check_help_coverage: {len(errors)} integrity error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    topic_ids = {str(e.get("id", "")) for e in entries}
    missing = missing_command_topics(topic_ids)
    print(f"check_help_coverage: {len(topic_ids)} topics, integrity OK")

    if missing:
        by_ns: dict[str, int] = {}
        for cmd in missing:
            by_ns[_namespace(cmd)] = by_ns.get(_namespace(cmd), 0) + 1
        summary = ", ".join(f"{ns}:{n}" for ns, n in sorted(by_ns.items()))
        label = "ERROR" if strict else "WARNING"
        print(f"{label}: {len(missing)} command(s) without a help topic ({summary})")
        print(
            "  Scaffold them with: "
            "python -m quill.tools.check_help_coverage --scaffold-missing <namespace>"
        )
        if strict:
            return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check QUILL context-sensitive help coverage.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail (exit 1) on any command missing a help topic.",
    )
    parser.add_argument(
        "--scaffold",
        metavar="ID",
        action="append",
        default=[],
        help="Append a stub topic for this command/control id and exit.",
    )
    parser.add_argument(
        "--scaffold-missing",
        metavar="NAMESPACE",
        help="Append stub topics for every command in NAMESPACE that lacks one.",
    )
    args = parser.parse_args()

    if args.scaffold:
        sys.exit(_scaffold(list(args.scaffold)))
    if args.scaffold_missing:
        topic_ids = {str(e.get("id", "")) for e in _load_raw()}
        ns = args.scaffold_missing.rstrip(".")
        wanted = [cmd for cmd in missing_command_topics(topic_ids) if _namespace(cmd) == ns]
        if not wanted:
            print(f"scaffold-missing: no missing commands in namespace {ns!r}")
            sys.exit(0)
        sys.exit(_scaffold(wanted))

    sys.exit(run(strict=args.strict))


if __name__ == "__main__":
    main()
