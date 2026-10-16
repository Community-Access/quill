"""Write QUILL Transcribe's tested-programs table from the harness's results.

``tests/integration/test_transcribe_targets.py`` types recorded phrases into
real programs and writes ``docs/qa/transcribe-targets.json``. This renders that
file into the table in QUILL Transcribe's user guide, between the
``compatibility:start`` and ``compatibility:end`` markers, so the guide says
only what a run measured (dict.md D-4). Every row cites the day it was checked
and a review-by date, because Office and browser versions drift.

A program counts as:

* **Supported** when at least 95 percent of the phrases arrived exactly (the
  D-4 bar);
* **Best effort** when at least half did;
* **Unsupported** when fewer than half did;
* **Untested** when it was not installed, was skipped for safety, or the run
  stopped early -- never "unsupported" for want of a test.

``tests/unit/scripts/test_transcribe_compatibility.py`` fails when the guide
falls behind the results file.

Usage::

    python scripts/build_transcribe_compatibility.py          # rewrite the table
    python scripts/build_transcribe_compatibility.py --check  # fail if stale
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
RESULTS = _REPO / "docs" / "qa" / "transcribe-targets.json"
GUIDE = _REPO / "standalone" / "transcribe" / "docs" / "userguide.md"
START = "<!-- compatibility:start -->"
END = "<!-- compatibility:end -->"

#: How long a row stands before somebody runs the harness again.
REVIEW_DAYS = 90
SUPPORTED_AT = 0.95
BEST_EFFORT_AT = 0.5


def classify(row: dict[str, Any]) -> str:
    """Supported, Best effort, Unsupported or Untested, for one results row."""
    if row.get("status") != "tested" or row.get("incomplete"):
        return "Untested"
    sent = int(row.get("phrases_sent") or 0)
    if not sent:
        return "Untested"
    share = int(row.get("phrases_exact") or 0) / sent
    if share >= SUPPORTED_AT:
        return "Supported"
    if share >= BEST_EFFORT_AT:
        return "Best effort"
    return "Unsupported"


def _review_by(date: str) -> str:
    try:
        return (_dt.date.fromisoformat(date) + _dt.timedelta(days=REVIEW_DAYS)).isoformat()
    except ValueError:
        return "-"


def _note(row: dict[str, Any], result: str) -> str:
    if row.get("incomplete"):
        # Why it stopped stays in the results file; the guide says only that
        # nothing was measured.
        return "The test run was interrupted before it finished, so nothing was measured yet."
    if result == "Untested":
        reason = str(row.get("reason") or "not installed").rstrip(".")
        return reason[:1].upper() + reason[1:] + "."
    misses = row.get("mismatches") or []
    if not misses:
        return "Every phrase arrived exactly."
    return f"{len(misses)} phrase{'s' if len(misses) != 1 else ''} arrived changed or incomplete."


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(results: dict[str, Any]) -> str:
    """The Markdown between the markers, newline-terminated."""
    lines = [
        "| Program | Version | Result | Phrases exact | Checked | Review by | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results.get("programs", []):
        result = classify(row)
        date = str(row.get("date") or "")
        exact = (
            f"{row.get('phrases_exact', 0)} of {row.get('phrases_sent', 0)}"
            if result != "Untested"
            else "-"
        )
        cells = [
            str(row.get("program") or row.get("key")),
            str(row.get("version") or "-"),
            result,
            exact,
            date or "-",
            _review_by(date) if date else "-",
            _note(row, result),
        ]
        lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " |")
    count = len(results.get("phrases", []))
    lines += [
        "",
        f"Each tested program was sent the same {count} phrases. A phrase counts as",
        "exact when the program's text, read back afterwards, grew by exactly that",
        "phrase. A program's own formatting, such as Word's curly quotes, and its",
        "own line ending are not counted as changes.",
    ]
    return "\n".join(lines) + "\n"


def load(path: Path = RESULTS) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply(guide: str, block: str) -> str:
    """*guide* with the text between the markers replaced by *block*."""
    head, start, rest = guide.partition(START)
    if not start:
        raise ValueError(f"{GUIDE.name} has no {START} marker")
    _, end, tail = rest.partition(END)
    if not end:
        raise ValueError(f"{GUIDE.name} has no {END} marker")
    return f"{head}{START}\n{block}{END}{tail}"


def stale() -> bool:
    guide = GUIDE.read_text(encoding="utf-8")
    return apply(guide, render(load())) != guide


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        if stale():
            print(f"{GUIDE} is out of date. Run: python scripts/build_transcribe_compatibility.py")
            return 1
        return 0
    guide = GUIDE.read_text(encoding="utf-8")
    GUIDE.write_text(apply(guide, render(load())), encoding="utf-8", newline="\n")
    print(f"Wrote {GUIDE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
