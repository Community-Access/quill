"""A workflow file as linear pieces, and what GitHub would reject it for (GitHub PRD 22.1)."""

from __future__ import annotations

import pytest

from quill.core.github.actions_yaml import ActionsYamlError, dump_mapping, load_mapping
from quill.core.github.workflow_authoring import (
    dispatch_inputs,
    dump_workflow,
    input_summary,
    job_summary,
    load_workflow,
    make_job_id,
    move_job,
    needs_sentence,
    new_workflow,
    order_sentence,
    pairs_text,
    parse_pairs,
    permissions_summary,
    remove_job,
    remove_trigger,
    replace_job,
    set_trigger,
    step_summary,
    trigger_summary,
    triggers,
)
from quill.core.github.workflow_checks import check_workflow

CI = """# Build and test on every push.
# Owned by the release team.

name: CI
on:
  push:
    branches: [main]
    paths-ignore: ['docs/**']
  workflow_dispatch:
    inputs:
      target:
        type: choice
        options: [staging, production]
        default: staging
        required: true
permissions:
  contents: read
jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pip install .
          pytest -q
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .
  build:
    name: Build
    needs: [test, lint]
    runs-on: ubuntu-latest
    concurrency: build
    steps:
      - run: make
"""


def _texts(draft: object) -> list[str]:
    return [p.text() for p in check_workflow(draft)]  # type: ignore[arg-type]


def test_on_stays_a_key_and_yes_stays_a_word() -> None:
    data = load_mapping("on:\n  push:\nenv:\n  FLAG: yes\n", "workflow")
    assert "on" in data and True not in data
    assert data["env"]["FLAG"] == "yes"
    assert dump_mapping(data).startswith("on:\n  push:\n")


def test_an_unchanged_workflow_is_saved_as_it_was_read() -> None:
    draft = load_workflow(CI)
    assert not draft.changed()
    assert dump_workflow(draft) == CI


def test_a_changed_workflow_keeps_its_top_comments_and_unknown_keys() -> None:
    draft = load_workflow(CI)
    set_trigger(draft, "schedule", [{"cron": "30 5 * * 1"}])
    text = dump_workflow(draft)
    assert text.startswith("# Build and test on every push.\n# Owned by the release team.\n\n")
    assert "concurrency: build" in text
    assert "on:\n  push:" in text
    assert "run: |\n          pip install .\n          pytest -q\n" in text
    assert (
        load_workflow(text).data["jobs"]["test"]["steps"][1]["run"] == "pip install .\npytest -q\n"
    )


def test_a_file_that_is_not_yaml_says_where() -> None:
    with pytest.raises(ActionsYamlError, match="at line 3: expected ',' or ']'"):
        load_workflow("on: push\njobs: [a, b\n  c: d\n")
    with pytest.raises(ActionsYamlError, match="not a set of keys"):
        load_workflow("- a\n- b\n")


def test_triggers_read_as_rows_whichever_way_on_is_written() -> None:
    draft = load_workflow(CI)
    rows = [trigger_summary(e, s) for e, s in triggers(draft).items()]
    assert rows == ["On a push, branches main, paths ignore docs/**", "Run by hand, 1 input"]
    assert list(triggers(load_workflow("on: push\njobs: {}\n"))) == ["push"]
    assert list(triggers(load_workflow("on: [push, pull_request]\njobs: {}\n"))) == [
        "push",
        "pull_request",
    ]
    inputs = dispatch_inputs(triggers(draft)["workflow_dispatch"])
    assert input_summary("target", inputs["target"]) == (
        "target, a choice of staging and production, required, default staging"
    )
    remove_trigger(draft, "push")
    assert list(triggers(draft)) == ["workflow_dispatch"]


def test_the_dependency_graph_is_said_in_words() -> None:
    draft = load_workflow(CI)
    assert needs_sentence(draft, "build") == "Build runs after Test and Lint."
    assert needs_sentence(draft, "test") == "Test starts first; it needs no other job."
    assert order_sentence(draft) == "First Test and Lint, together. Then Build."
    assert job_summary(draft, "build") == (
        "Build (build), runs on ubuntu-latest, runs after Test and Lint, 1 step"
    )
    assert permissions_summary(draft.data["permissions"]) == "contents read"
    assert permissions_summary(None).startswith("not set")


def test_renaming_a_job_carries_the_needs_and_removing_one_frees_them() -> None:
    draft = load_workflow(CI)
    spec = dict(draft.data["jobs"]["test"])
    replace_job(draft, "test", "unit", spec)
    assert list(draft.data["jobs"]) == ["unit", "lint", "build"]
    assert draft.data["jobs"]["build"]["needs"] == ["unit", "lint"]
    assert remove_job(draft, "lint") == ["build"]
    assert draft.data["jobs"]["build"]["needs"] == ["unit"]
    assert move_job(draft, "build", -1) and list(draft.data["jobs"]) == ["build", "unit"]
    assert not move_job(draft, "build", -1)
    assert make_job_id("Build & Test", ["build-test"]) == "build-test-2"
    assert make_job_id("2nd") == "job-2nd"


def test_steps_and_pairs_read_and_write_typed_values() -> None:
    assert step_summary({"name": "Check out", "uses": "actions/checkout@v4"}, 1) == (
        "1. Check out: uses actions/checkout@v4"
    )
    assert step_summary({"run": "a\nb\nc", "if": "success()"}, 2) == (
        "2. runs a and 2 more lines, only if success()"
    )
    pairs = parse_pairs("fetch-depth: 0\nlfs: true\nname: hello world\n\n")
    assert pairs == {"fetch-depth": 0, "lfs": True, "name": "hello world"}
    assert pairs_text(pairs) == "fetch-depth: 0\nlfs: true\nname: hello world"


def test_the_starter_is_a_workflow_github_would_take() -> None:
    draft = new_workflow("Docs")
    assert check_workflow(draft) == []
    assert "workflow_dispatch:\n" in dump_workflow(draft)


def test_github_s_rejections_are_found_before_saving() -> None:
    draft = load_workflow(
        """on:
  push:
    branches: [main]
    branches-ignore: [old]
    folders: [x]
  schedule:
    - cron: '0 5 * *'
  workflow_dispatch:
    inputs:
      env: {type: choice, options: []}
      size: {type: huge}
  bogus_event:
permissions: {contents: maybe, id-token: read, secrets: write}
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout
      - {run: pytest, uses: x/y@1}
      - {}
      - {id: a, run: x}
      - {id: a, run: y, colour: red}
  build:
    needs: [test, deploy]
    steps: [{run: make}]
  "2fast":
    runs-on: ubuntu-latest
    needs: 2fast
    steps: [{run: x}]
foo: 1
"""
    )
    texts = _texts(draft)
    for expected in (
        "The file: foo is not something a workflow has.",
        "Trigger push: folders is not a filter it takes.",
        "Trigger push: branches and branches-ignore cannot both be used; use ! in branches.",
        "Trigger schedule: '0 5 * *' is not five fields (minute hour day month weekday).",
        "Trigger workflow_dispatch, input env: a choice needs at least one option.",
        "Trigger bogus_event: bogus_event is not an event GitHub has.",
        "Workflow permissions: contents cannot be maybe; it can be read or write or none.",
        "Workflow permissions: id-token cannot be read; it can be write or none.",
        "Workflow permissions: secrets is not a permission GitHub has; remove it.",
        "Job test, step 1: actions/checkout has no version; add one, such as "
        "actions/checkout@v4 or a commit.",
        "Job test, step 2: a step either uses an action or runs commands, not both.",
        "Job test, step 3: it neither uses an action nor runs anything.",
        "Job test, step 5: the id a is used twice.",
        "Job test, step 5: colour is not something a step has.",
        "Job build: it has no runs-on, so no runner would take it.",
        "Job build: it needs deploy, and there is no job deploy. Fix or remove it.",
        "Job 2fast: it needs itself, so it could never start.",
    ):
        assert expected in texts, expected
    assert any(t.startswith("Job 2fast: a job id starts with a letter") for t in texts)
    assert any("size: huge" in t or "huge is not an input type" in t for t in texts)


def test_a_loop_of_needs_is_found_and_said_as_never() -> None:
    draft = load_workflow(
        "on: push\njobs:\n  a: {runs-on: x, needs: b, steps: [{run: x}]}\n"
        "  b: {runs-on: x, needs: a, steps: [{run: x}]}\n  c: {runs-on: x, steps: [{run: x}]}\n"
    )
    assert "Jobs: a, b wait for each other in a loop, so none of them could ever start." in _texts(
        draft
    )
    assert order_sentence(draft) == (
        "First c. Never: a and b, which wait for a job that never finishes."
    )


def test_a_reusable_workflow_job_and_missing_parts() -> None:
    draft = load_workflow(
        "on: push\njobs:\n  call:\n    uses: o/r/.github/workflows/x.yml@main\n    steps: []\n"
    )
    assert "Job call: a job that calls a reusable workflow cannot have steps." in _texts(draft)
    empty = load_workflow("name: x\n")
    assert _texts(empty) == [
        "Triggers: there are none, so nothing would ever start it.",
        "Jobs: there are none; a workflow needs at least one.",
    ]
