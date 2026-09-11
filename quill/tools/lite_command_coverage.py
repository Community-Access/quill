"""GATE-LITE-COVER: a QuillLite command may not ship without a behavioural test.

The gate that exists because of F8. ``cmd_start_extend_selection`` was on the
menu, had a key, had a handler, and was covered by a test that asserted the
handler existed and could be called -- and extend mode had never once worked
from the keyboard, because the *second* half of the interaction cancelled the
mode the first half started. Every check in the build was green the whole time.
Existence is not behaviour, and a suite that only proves a method is there
proves nothing a listener would notice.

So: every handler in :data:`quill.core.lite.commands.COMMANDS` is classified,
and the classification is a committed snapshot rather than a computed number.

``covered``
    A test in ``tests/unit/apps`` calls this handler. That is the artefact the
    scan can actually verify -- not a docstring, not a name, a call.
``shape_only``
    Existence and arity only. Every one of these is a debt with a date on it,
    and the list may only ever get shorter: a handler recorded as ``covered``
    that stops being called by any test fails the build, because a deleted test
    is exactly as invisible as a test that was never written.

**The ratchet runs in both directions.** A new command with no test fails
immediately (it is in the table and not in the snapshot). A handler whose test
went away fails immediately. And a handler that has *gained* a test also fails,
with a message saying to regenerate -- because leaving the snapshot behind is
how a ratchet quietly stops being one.

Regenerate with::

    python -m quill.tools.lite_command_coverage --write

and read the diff. A ``covered`` becoming ``shape_only`` in that diff is a
regression somebody has to explain, not a line to commit.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the committed classification lives, beside the other gate snapshots.
SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "lite_command_coverage.json"

#: The trees a behavioural test may live in. ``tests/unit/apps`` is where the
#: shared ``lite_window`` harness is; ``tests/unit/core/lite`` holds the pure
#: table checks, which are deliberately *not* counted -- they are the existence
#: tests this gate exists to distrust.
TEST_DIRS: tuple[str, ...] = ("tests/unit/apps",)

#: The two answers. ``shape_only`` is a debt; ``covered`` is the goal.
STATUSES = ("covered", "shape_only")


def command_handlers() -> list[str]:
    """Every handler name QuillLite's menu table names, sorted and de-duplicated."""
    from quill.core.lite.commands import COMMANDS

    return sorted({row[3] for row in COMMANDS if row[4] not in {"sep", "sub"} and row[3]})


def called_handlers(root: Path | None = None) -> set[str]:
    """Handler names some test in :data:`TEST_DIRS` actually calls.

    Parsed rather than grepped: ``win.cmd_copy()`` is a call and
    ``"cmd_copy"`` in a list of names is not, and a gate that could not tell
    them apart would be satisfied by the very inventory-style test that let F8
    through. Only ``<something>.cmd_x(...)`` counts -- an attribute access with
    no call is a reference, not an exercise.
    """
    base = root if root is not None else REPO_ROOT
    found: set[str] = set()
    for directory in TEST_DIRS:
        for path in sorted((base / directory).rglob("test_*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr.startswith("cmd_"):
                    found.add(func.attr)
    return found


def build_snapshot(root: Path | None = None) -> dict[str, str]:
    """The classification as the tree stands right now."""
    called = called_handlers(root)
    return {
        handler: ("covered" if handler in called else "shape_only")
        for handler in command_handlers()
    }


def load_snapshot(path: Path | None = None) -> dict[str, str]:
    target = path if path is not None else SNAPSHOT_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}


def write_snapshot(path: Path | None = None, root: Path | None = None) -> dict[str, str]:
    target = path if path is not None else SNAPSHOT_PATH
    snapshot = build_snapshot(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def violations(recorded: dict[str, str] | None = None, root: Path | None = None) -> list[str]:
    """Every way the tree and the snapshot disagree, in plain sentences.

    Four kinds, and three of them are failures the build should stop for. The
    fourth -- a handler that gained a test -- stops it too, because a snapshot
    left behind is a ratchet that has quietly stopped ratcheting.
    """
    committed = load_snapshot() if recorded is None else dict(recorded)
    current = build_snapshot(root)
    problems: list[str] = []

    for handler, status in sorted(current.items()):
        if handler not in committed:
            problems.append(
                f"{handler}: a new command with no entry. Write a behavioural test for it "
                f"in {TEST_DIRS[0]}, then run: python -m quill.tools.lite_command_coverage --write"
            )
            continue
        was = committed[handler]
        if was not in STATUSES:
            problems.append(f"{handler}: unknown status {was!r}; expected one of {STATUSES}")
        elif was == "covered" and status == "shape_only":
            problems.append(
                f"{handler}: was covered and no test calls it any more. A deleted test is "
                "as invisible as one that was never written -- restore it rather than "
                "recording the loss."
            )
        elif was == "shape_only" and status == "covered":
            problems.append(
                f"{handler}: has gained a behavioural test. Run: "
                "python -m quill.tools.lite_command_coverage --write"
            )

    for handler in sorted(set(committed) - set(current)):
        problems.append(
            f"{handler}: recorded here but no longer in the command table. Run: "
            "python -m quill.tools.lite_command_coverage --write"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate the snapshot from the tree instead of checking it",
    )
    args = parser.parse_args(argv)

    if args.write:
        snapshot = write_snapshot()
        covered = sum(1 for status in snapshot.values() if status == "covered")
        print(
            f"Wrote {len(snapshot)} handlers to {SNAPSHOT_PATH}: "
            f"{covered} covered, {len(snapshot) - covered} shape-only"
        )
        return 0

    problems = violations()
    if problems:
        print("GATE-LITE-COVER: the command-coverage ratchet has slipped.")
        for problem in problems:
            print(f"  {problem}")
        return 1
    snapshot = load_snapshot()
    covered = sum(1 for status in snapshot.values() if status == "covered")
    print(f"covered: {covered}, shape_only: {len(snapshot) - covered}")
    return 0


__all__ = [
    "SNAPSHOT_PATH",
    "STATUSES",
    "TEST_DIRS",
    "build_snapshot",
    "called_handlers",
    "command_handlers",
    "load_snapshot",
    "main",
    "violations",
    "write_snapshot",
]


if __name__ == "__main__":
    raise SystemExit(main())
