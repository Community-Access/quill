"""After a run: the whole replay suite against its folder, summed up per app and format.

The suite is every test marked ``scribe_corpus`` (``tests/unit/core/scribe/corpus.py``
``needs_corpus``), run with ``QUILL_SCRIBE_CORPUS`` naming the run's folder:
Pneuma-corpus replays, the opens-and-reads table, the live-run checks, and
any module marked later -- a new module is picked up by its marker, never by
a list here.

Each test's app and format come from the junit properties ``scribe_app`` and
``scribe_format`` when the test records them (``record_property``), as the
opens-and-reads table does; otherwise from words in its name. Results are
read from the junit XML pytest writes into the run folder, through
:mod:`quill.core.safe_xml`. The child process gets this process's
environment plus the corpus folder, and runs without a network.

wx-free (the child imports wx; this process does not).
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.scribe.model import FORMAT_IDS, format_label
from quill.tools.scribe_live.sources import REPO_ROOT

MARKER = "scribe_corpus"
JUNIT = "replay.xml"
_TIMEOUT_S = 3 * 3600.0

#: (word in a test's name, app) -- the fallback when a test records no app.
_APP_WORDS: tuple[tuple[str, str], ...] = (
    ("lite", "QUILL Lite"),
    ("media_player", "Media Player"),
    ("player", "Media Player"),
    ("converter", "Converter"),
    ("studio", "Studio"),
    ("cast", "Cast"),
    ("social", "Social"),
    ("beacon", "Beacon"),
    ("send_to", "Send To"),
    ("braille_view", "QUILL"),
    ("quill", "QUILL"),
)
_FORMAT_WORDS: tuple[tuple[str, str], ...] = (
    ("offline", "offline_html"),
    ("daisy", "daisy"),
    ("mp3", "mp3"),
    ("brf", "brf"),
    ("braille", "brf"),
    ("epub", "epub"),
    ("mobi", "mobi"),
    ("word", "docx"),
    ("docx", "docx"),
    ("pdf", "pdf"),
    ("ocr", "pdf"),
    ("html", "html"),
)


@dataclass(slots=True)
class Case:
    name: str
    outcome: str  # passed, failed, skipped
    app: str
    format: str
    message: str = ""


@dataclass(slots=True)
class Replay:
    ran: bool
    cases: list[Case] = field(default_factory=list)
    note: str = ""

    def count(self, outcome: str) -> int:
        return sum(1 for c in self.cases if c.outcome == outcome)

    def summary(self) -> str:
        if not self.ran:
            return f"The replay suite did not run: {self.note}"
        passed, failed = self.count("passed"), self.count("failed")
        skipped = self.count("skipped")
        text = f"The replay suite passed {passed} of {passed + failed} tests"
        if skipped:
            text += f", and skipped {skipped}"
        return text + "."

    def by(self, attribute: str) -> dict[str, tuple[int, int, list[str]]]:
        """name -> (passed, run, failed test names), skipped tests left out."""
        table: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        failures: dict[str, list[str]] = defaultdict(list)
        for case in self.cases:
            if case.outcome == "skipped":
                continue
            key = getattr(case, attribute)
            table[key][1] += 1
            if case.outcome == "passed":
                table[key][0] += 1
            else:
                failures[key].append(case.name)
        order = {name: index for index, name in enumerate(FORMAT_IDS)}
        keys = sorted(table, key=lambda k: (order.get(k, len(order)), k))
        return {k: (table[k][0], table[k][1], failures[k]) for k in keys}

    def sentences(self) -> list[str]:
        lines = [self.summary()]
        if not self.ran:
            return lines
        for attribute, heading in (("app", "By app"), ("format", "By format")):
            parts = []
            for key, (passed, run, _failed) in self.by(attribute).items():
                name = format_label(key) if attribute == "format" else key
                if key == "general":
                    name = "not tied to one format"
                score = f"all {run} passed" if passed == run > 1 else f"{passed} of {run} passed"
                parts.append(f"{name}, {score}")
            if parts:
                lines.append(f"{heading}: " + "; ".join(parts) + ".")
        failed_cases = [c for c in self.cases if c.outcome == "failed"]
        for case in failed_cases[:20]:
            module, _sep, test = case.name.rpartition("::")
            where = module.replace(".", "/") + ".py" if module else ""
            lines.append(f"Failed: {test}, in {where}. {_trim(case.message)}".rstrip())
        if len(failed_cases) > 20:
            lines.append(f"And {len(failed_cases) - 20} more failures, in replay.xml.")
        return lines


def _trim(message: str, limit: int = 200) -> str:
    text = " ".join(message.split())
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + " ..."
    return text


def _guess(name: str, words: tuple[tuple[str, str], ...], default: str) -> str:
    lowered = name.lower()
    for word, value in words:
        if word in lowered:
            return value
    return default


def read_junit(path: Path) -> list[Case]:
    from quill.core import safe_xml

    root = safe_xml.fromstring(path.read_bytes())
    cases: list[Case] = []
    for case in root.iter("testcase"):
        name = f"{case.get('classname', '')}::{case.get('name', '')}"
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        outcome, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                outcome, message = "failed", (child.get("message") or "")[:200]
            elif child.tag == "skipped":
                outcome, message = "skipped", (child.get("message") or "")[:200]
        cases.append(
            Case(
                name=name,
                outcome=outcome,
                app=props.get("scribe_app") or _guess(name, _APP_WORDS, "Every app (shared code)"),
                format=props.get("scribe_format") or _guess(name, _FORMAT_WORDS, "general"),
                message=message,
            )
        )
    return cases


#: The suite: everything in the Scribe core tests (our own fixtures, the fake
#: server, the corpus replays), then every module elsewhere marked
#: ``scribe_corpus`` -- the app replays, and whatever is marked later.
SUITE: tuple[tuple[str, ...], ...] = (
    ("tests/unit/core/scribe",),
    ("-m", MARKER, "--ignore=tests/unit/core/scribe", "tests/unit"),
)


_PARTS = ("the Scribe core tests", "the app replays marked scribe_corpus")


def run_suite(
    corpus: Path | None, out_dir: Path, say: Callable[[str], None] | None = None
) -> Replay:
    """Run the suite with ``QUILL_SCRIBE_CORPUS`` set to *corpus* (or unset),
    writing junit results into *out_dir*. No network: the tests use the fake
    server and the files in *corpus*."""
    from quill.stability.safe_subprocess import run_subprocess_safely

    env = dict(os.environ)
    env.pop("QUILL_TEST_SHARD", None)  # a shard would deselect what the marker selects
    env.pop("QUILL_SCRIBE_CORPUS", None)
    if corpus is not None:
        env["QUILL_SCRIBE_CORPUS"] = str(corpus)
    out_dir.mkdir(parents=True, exist_ok=True)
    cases: list[Case] = []
    for index, selection in enumerate(SUITE):
        if say is not None:
            say(f"Part {index + 1} of {len(SUITE)}: {_PARTS[index]}.")
        junit = out_dir / (JUNIT if index == 0 else JUNIT.replace(".xml", f"-{index}.xml"))
        junit.unlink(missing_ok=True)
        args = [
            sys.executable, "-m", "pytest", "-o", "timeout=0", "-q", "-p", "no:cacheprovider",
            f"--junitxml={junit}", "-o", "junit_family=xunit1", *selection,
        ]  # fmt: skip
        try:
            run_subprocess_safely(args, timeout_seconds=_TIMEOUT_S, cwd=str(REPO_ROOT), env=env)
        except (OSError, ValueError) as error:
            return Replay(False, note=str(error))
        except Exception as error:  # noqa: BLE001 - a timeout: say so, keep the run
            return Replay(False, note=f"{type(error).__name__}: {error}")
        if not junit.is_file():
            return Replay(False, note="pytest wrote no results.")
        cases += read_junit(junit)
    return Replay(True, cases)


def run_replay(run_dir: Path, say: Callable[[str], None] | None = None) -> Replay:
    """The suite against a run's (or the corpus's) folder, results kept in it."""
    if not (run_dir / "validation.json").is_file():
        return Replay(False, note=f"{run_dir} has no validation.json, so it is not a run folder.")
    return run_suite(run_dir, run_dir, say)


__all__ = ["JUNIT", "MARKER", "SUITE", "Case", "Replay", "read_junit", "run_replay", "run_suite"]
