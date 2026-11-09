"""GATE-CATALOGUE: every command is a catalogue row, or classified (command-key.md 15).

A command reachable from a sentence is a command somebody decided about. This
audit lists every command each catalogued app registers and fails on any that
is neither a row in :mod:`quill.core.command_catalogue` nor classified in
``tests/unit/core/fixtures/command_catalogue.json``:

- ``unreviewed`` -- nobody has written its row yet, so it is NEVER: no sentence
  can reach it. This list may only shrink. ``--write`` drops ids that have
  gained a row or gone away, and refuses to add one unless ``--allow-growth``
  is passed, because a new command should arrive with its row.
- ``internal`` -- not a command a person runs (a submenu anchor, a key layer).

It also checks the rules a row must keep: dangerous verbs are never SAFE, no
CONFIRM or NEVER row is offered to agents, every offered row has a
description and an example, aliases are unique where they could be confused,
no alias is a dictation phrase, and every opposite is a real row.

    python -m quill.tools.command_catalogue_audit            # check
    python -m quill.tools.command_catalogue_audit --write    # re-snapshot
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

from quill.core.command_catalogue import CommandSpec, Risk, all_rows, row, rows_for_app

_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = _ROOT / "tests" / "unit" / "core" / "fixtures" / "command_catalogue.json"

#: The apps whose every command must be decided about. QUILL Lite is a view of
#: QUILL's rows, so it is checked by construction rather than listed.
CHECKED_APPS: tuple[str, ...] = ("quill", "radio")

#: Words in a command id that mean it sends, deletes, overwrites, exits, signs
#: in or changes what is installed. Such a command is never SAFE.
DANGER_WORDS = frozenset({
    "account",
    "accounts",
    "clear",
    "close",
    "delete",
    "discard",
    "download",
    "erase",
    "exit",
    "install",
    "key",
    "keys",
    "merge",
    "overwrite",
    "password",
    "publish",
    "push",
    "quit",
    "remove",
    "send",
    "signin",
    "signout",
    "token",
    "update",
    "updates",
    "upload",
})

_RADIO_SOURCE = _ROOT / "quill" / "ui" / "radio" / "palette_commands.py"
_RADIO_ID = re.compile(r'"(radio\.[a-z0-9_.]+)"')


def universe(app: str) -> tuple[str, ...]:
    """Every command id *app* registers, as far as can be known without wx."""
    if app == "quill":
        from quill.core.keymap import DEFAULT_KEYMAP

        return tuple(sorted(DEFAULT_KEYMAP))
    if app == "radio":
        from quill.core.app_keymaps import APP_KEYMAPS

        ids = set(APP_KEYMAPS["radio"])
        ids.update(_RADIO_ID.findall(_RADIO_SOURCE.read_text(encoding="utf-8")))
        return tuple(sorted(ids))
    raise KeyError(app)


def load_snapshot(path: Path = SNAPSHOT) -> dict[str, dict[str, list[str]]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        app: {kind: list(ids) for kind, ids in table.items()}
        for app, table in raw.get("apps", {}).items()
    }


def _row_ids(app: str) -> set[str]:
    return {spec.id for spec in rows_for_app(app)}


def classification_problems(snapshot: dict[str, dict[str, list[str]]]) -> list[str]:
    """Commands nobody decided about, and snapshot entries that are stale."""
    problems: list[str] = []
    for app in CHECKED_APPS:
        table = snapshot.get(app, {})
        unreviewed = set(table.get("unreviewed", []))
        internal = set(table.get("internal", []))
        rows = _row_ids(app)
        ids = set(universe(app))
        for command_id in sorted(ids - rows - unreviewed - internal):
            problems.append(f"{app}: {command_id} has no catalogue row and no classification")
        for command_id in sorted((unreviewed | internal) & rows):
            problems.append(f"{app}: {command_id} has a row now; re-snapshot with --write")
        for command_id in sorted((unreviewed | internal) - ids):
            problems.append(f"{app}: {command_id} is classified but no longer registered")
    return problems


def _id_words(command_id: str) -> set[str]:
    return set(re.split(r"[._]", command_id.lower()))


#: Rows whose command is registered with no default chord, so it is not in
#: the keymap: each with the file that registers it, which is checked instead.
#: Reading every UI module to find two ids took over a minute on a busy disk.
REGISTERED_ELSEWHERE: dict[str, str] = {
    "file.save_all": "quill/ui/main_frame_commands.py",
    "edit.select_all": "quill/ui/main_frame_menu_editor.py",
    "format.insert_bullet_list": "quill/ui/main_frame_commands.py",
    "format.insert_numbered_list": "quill/ui/main_frame_commands.py",
    "file.restore_backup": "quill/ui/main_frame_commands.py",
    "app.report_editor_surface": "quill/ui/main_frame_commands.py",
    "app.braille_ab": "quill/ui/main_frame_commands.py",
    "tools.copy_diagnostic_summary": "quill/ui/main_frame_commands.py",
}


def _registered_in_source(command_id: str) -> bool:
    where = REGISTERED_ELSEWHERE.get(command_id)
    needle = f'"{command_id}"'
    if where is not None:
        return needle in (_ROOT / where).read_text(encoding="utf-8")
    # Not in the table: look through the UI and app modules (slow, so only on a miss).
    for folder in ("ui", "apps"):
        for path in (_ROOT / "quill" / folder).rglob("*.py"):
            if needle in path.read_text(encoding="utf-8", errors="replace"):
                return True
    return False


def _dictation_phrases() -> set[str]:
    from quill.core.windows_dictation import vocabulary

    return {" ".join(phrase) for phrase in (*vocabulary.COMMANDS, *vocabulary.PREFIXES)}


def _normal(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def row_problems(rows: Iterable[CommandSpec] | None = None) -> list[str]:
    """Rows that break a rule of the catalogue."""
    specs = tuple(all_rows() if rows is None else rows)
    problems: list[str] = []
    dictation = _dictation_phrases()
    seen: dict[tuple[str, str], str] = {}
    universes = {app: set(universe(app)) for app in CHECKED_APPS}
    for spec in specs:
        where = f"{','.join(spec.apps)}: {spec.id}"
        if not spec.title.strip():
            problems.append(f"{where} has no title")
        if spec.risk is Risk.SAFE and _id_words(spec.id) & DANGER_WORDS:
            problems.append(f"{where} sends, deletes, closes or exits, so it cannot be SAFE")
        if spec.agent_ok and spec.risk is not Risk.SAFE:
            problems.append(f"{where} is offered to agents but is {spec.risk.value}")
        if spec.offered:
            if not spec.description.strip():
                problems.append(f"{where} is offered to sentences but has no description")
            if not spec.examples:
                problems.append(f"{where} is offered to sentences but has no example")
        elif not spec.where:
            problems.append(f"{where} is NEVER but does not say where it is found")
        for alias in spec.aliases:
            normal = _normal(alias)
            if normal in dictation:
                problems.append(f"{where} alias {alias!r} is a dictation phrase")
            if not spec.offered:
                continue
            for app in spec.apps:
                for surface in spec.surfaces or ("",):
                    key = (f"{app}/{surface}", normal)
                    other = seen.get(key)
                    if other is not None and other != spec.id:
                        problems.append(f"{where} alias {alias!r} is also {other}'s")
                    seen[key] = spec.id
        for app in spec.apps:
            if spec.opposite and row(spec.opposite, app) is None:
                problems.append(f"{where} opposite {spec.opposite} is not a row")
            known = universes.get(app)
            if known is not None and spec.id not in known and not _registered_in_source(spec.id):
                problems.append(f"{where} is not a command {app} registers")
    return problems


def snapshot_for(previous: dict[str, dict[str, list[str]]]) -> dict[str, object]:
    apps: dict[str, dict[str, list[str]]] = {}
    for app in CHECKED_APPS:
        table = previous.get(app, {})
        rows = _row_ids(app)
        ids = set(universe(app))
        internal = sorted(set(table.get("internal", [])) & ids - rows)
        unreviewed = sorted(ids - rows - set(internal))
        apps[app] = {"internal": internal, "unreviewed": unreviewed}
    return {
        "_doc": (
            "GATE-CATALOGUE (docs/design/command-key.md 15). 'unreviewed' means NEVER "
            "and may only shrink; regenerate with "
            "python -m quill.tools.command_catalogue_audit --write."
        ),
        "apps": apps,
    }


def growth(previous: dict[str, dict[str, list[str]]], new: dict[str, object]) -> list[str]:
    grown: list[str] = []
    apps = new["apps"]
    assert isinstance(apps, dict)
    for app, table in apps.items():
        before = set(previous.get(app, {}).get("unreviewed", []))
        if not before and app not in previous:
            continue
        grown.extend(
            f"{app}: {command_id}" for command_id in sorted(set(table["unreviewed"]) - before)
        )
    return grown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="re-snapshot the classification")
    parser.add_argument(
        "--allow-growth",
        action="store_true",
        help="let --write add unreviewed commands (a new command should bring its row)",
    )
    args = parser.parse_args(argv)
    previous = load_snapshot()
    if args.write:
        new = snapshot_for(previous)
        grown = growth(previous, new)
        if grown and not args.allow_growth:
            print("Error: these would become unreviewed; give each a catalogue row instead:")
            for item in grown:
                print(f"- {item}")
            return 1
        SNAPSHOT.write_bytes((json.dumps(new, indent=2) + "\n").encode("utf-8"))
        print(f"OK: wrote {SNAPSHOT.relative_to(_ROOT).as_posix()}")
        return 0
    problems = classification_problems(previous) + row_problems()
    if problems:
        print(f"Error: {len(problems)} catalogue problem(s):")
        for item in problems:
            print(f"- {item}")
        return 1
    counts = ", ".join(f"{app} {len(rows_for_app(app))} rows" for app in ("quill", "lite", "radio"))
    print(f"OK: every command is catalogued or classified ({counts}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
