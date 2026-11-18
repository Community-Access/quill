"""The GitHub live run covers every write command and every sheet, and says why it skips any.

``docs/qa/github-live-run.py`` is how the Workbench is regression tested
against a real repository. What it covers is derived from the code's own
tables, so this test fails when a command (``COMMAND_REQUIREMENTS``) or a sheet
(``SHEETS``) is added without a scenario or a reason in the run: the
classification is the review, as in the other gates. Nothing here reaches
GitHub.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType

import pytest

from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS

QA = Path(__file__).resolve().parents[3] / "docs" / "qa"


def _load(name: str, file: str) -> ModuleType:
    if str(QA) not in sys.path:
        sys.path.insert(0, str(QA))
    spec = importlib.util.spec_from_file_location(name, QA / file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verbs() -> ModuleType:
    return _load("github_live_verbs", "github_live_verbs.py")


@pytest.fixture(scope="module")
def harness(verbs: ModuleType) -> ModuleType:
    return _load("github_live_run", "github-live-run.py")


def test_every_write_command_has_a_scenario_or_a_reason(verbs: ModuleType) -> None:
    commands = {command.removeprefix("github.workbench.") for command in COMMAND_REQUIREMENTS}
    assert set(verbs.VERBS) == commands, (
        f"missing from the live run: {sorted(commands - set(verbs.VERBS))}; "
        f"no longer commands: {sorted(set(verbs.VERBS) - commands)}"
    )


def test_every_reason_says_which_kind_it_is(verbs: ModuleType) -> None:
    kinds = ("sheet:", "with ", "needs Jeff: ", "not here: ")
    for verb, how in verbs.VERBS.items():
        if not callable(how):
            assert how.startswith(kinds), (verb, how)


def test_a_sheet_reason_names_a_field_that_writes(verbs: ModuleType) -> None:
    for verb, how in verbs.VERBS.items():
        if isinstance(how, str) and how.startswith("sheet:") and "." in how:
            kind, key = how.removeprefix("sheet:").split(".", 1)
            assert kind in SHEETS and key in SHEETS[kind].writes, (verb, how)


def test_a_with_reason_names_a_verb_that_runs(verbs: ModuleType) -> None:
    for verb, how in verbs.VERBS.items():
        if isinstance(how, str) and how.startswith("with "):
            other = how.removeprefix("with ").split(":", 1)[0].strip()
            assert callable(verbs.VERBS.get(other)), (verb, other)


class _OfflineRun:
    repo, second, login, org = "me/test", "me/test-2", "me", "org"

    def __init__(self) -> None:
        self.ids: defaultdict[str, str] = defaultdict(lambda: "1")

    def rest(self, *_args: object, **_query: str) -> object:
        raise ConnectionError("offline")


def test_every_sheet_is_tried_or_says_why_not(harness: ModuleType) -> None:
    idents = harness.sheet_idents(_OfflineRun())
    assert set(idents) == set(SHEETS), sorted(set(SHEETS) ^ set(idents))
    for kind, ident in idents.items():
        if isinstance(ident, str):
            assert ident, kind


def test_fields_left_alone_are_real_writable_fields(harness: ModuleType) -> None:
    for kind, fields in harness.LEAVE_ALONE.items():
        for key in fields:
            assert key in SHEETS[kind].writes, (kind, key)


def test_every_editable_field_gets_a_different_value_or_says_there_is_none(
    harness: ModuleType,
) -> None:
    for sheet in SHEETS.values():
        for spec in sheet.sheet.fields():
            if spec.readonly or spec.key not in sheet.writes:
                continue
            for before in (None, "", "x", True, 3, ("a",)):
                after = harness.changed_value(spec, before, {"a": "a", "b": "b"})
                assert after is NotImplemented or after != before, (sheet.kind, spec.key, before)


def test_the_report_counts_and_escapes(harness: ModuleType) -> None:
    import datetime as dt

    run = harness.Run(
        api=None,
        items=None,
        login="me",
        repo="me/t",
        second="me/t-2",
        org="o",
        dry_run=False,
        keep=False,
    )
    run.record("list", "a | b", "pass", "2 rows")
    run.record("command", "c", "fail", "boom")
    text = harness.report(run, dt.datetime(2026, 11, 17, tzinfo=dt.UTC), "test")
    assert "**1 passed, 1 failed, 0 not here, 0 need Jeff.**" in text
    assert "a \\| b" in text and "### Command (1, 1 failed)" in text
