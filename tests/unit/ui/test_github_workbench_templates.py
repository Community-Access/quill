"""Repository > Templates and New Discussion in the GitHub Workbench (GitHub PRD 21).

The commands are called, not listed: Open Template saves after asking,
reopens with the draft when a save fails, Convert builds a form, Copy
previews then reports per repository, New Template starts from a starter,
and New Discussion fills a category's form natively.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.discussion_actions import DiscussionCategory  # noqa: E402
from quill.core.github.item_actions import GITHUB_ACTIONS, NEW_HERE  # noqa: E402
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS  # noqa: E402
from quill.ui.github_template_builder_dialog import (  # noqa: E402
    FieldDialog,
    TemplateBuilderDialog,
)
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_MIXIN = "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin"

FORM = """name: Bug report
description: Something broke.
labels: [bug]
body:
  - type: textarea
    id: what
    attributes:
      label: What happened?
    validations:
      required: true
"""


class _NotFound(Exception):
    status = 404


class _Commit:
    sha = "commit-sha"


class _Branch:
    protected = False
    commit = _Commit()


class _Item:
    def __init__(self, repo: _Repo, path: str, kind: str) -> None:
        self.path, self.type, self.name = path, kind, path.rsplit("/", 1)[-1]
        text = repo.files.get(path, "")
        self.size = len(text)
        self.sha = repo.shas.get(path, "")
        self.html_url = ""
        self.decoded_content = text.encode()


class _Repo:
    default_branch = "main"
    permissions = None

    def __init__(self, files: dict[str, str]) -> None:
        self.files = dict(files)
        self.shas = {path: f"sha-{path}" for path in files}
        self.writes: list[tuple[str, str]] = []
        self.fail_next = False

    def get_contents(self, path: str, ref: str | None = None) -> Any:
        if path in self.files:
            return _Item(self, path, "file")
        prefix = f"{path}/" if path else ""
        names = {p[len(prefix) :].split("/", 1)[0] for p in self.files if p.startswith(prefix)}
        if not names:
            raise _NotFound(path)
        return [
            _Item(self, prefix + n, "file" if prefix + n in self.files else "dir")
            for n in sorted(names)
        ]

    def get_branch(self, _name: str) -> _Branch:
        return _Branch()

    def _put(self, path: str, content: str) -> dict[str, Any]:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("GitHub is having a moment")
        self.files[path] = content
        self.shas[path] = f"new-{len(self.writes)}"
        self.writes.append((path, content))
        return {"commit": _Commit()}

    def create_file(self, path: str, _message: str, content: str, branch: str) -> Any:
        return self._put(path, content)

    def update_file(self, path: str, _m: str, content: str, _sha: str, branch: str) -> Any:
        return self._put(path, content)

    def delete_file(self, path: str, _m: str, _sha: str, branch: str) -> None:
        del self.files[path]
        self.writes.append((path, "(deleted)"))

    def get_labels(self) -> list[Any]:
        return [type("L", (), {"name": "bug"})(), type("L", (), {"name": "idea"})()]

    def get_assignees(self) -> list[Any]:
        return [type("P", (), {"login": "jeff"})()]


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.repos = {
            REPO: _Repo({
                ".github/ISSUE_TEMPLATE/bug.yml": FORM,
                ".github/ISSUE_TEMPLATE/old.md": "---\nname: Old\nabout: x\n---\n### Steps\n",
                ".github/DISCUSSION_TEMPLATE/ideas.yml": (
                    "labels: [idea]\nbody:\n  - type: input\n    id: idea\n"
                    "    attributes: {label: Idea}\n    validations: {required: true}\n"
                ),
            }),
            "owner/other": _Repo({"README.md": "x"}),
            "owner/.github": _Repo({
                ".github/ISSUE_TEMPLATE/org.yml": FORM,
                ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: true\n",
                "FUNDING.yml": "github: jeff\n",
            }),
        }
        self.discussions: list[tuple[str, str, str, str]] = []

    def template_repository(self, name: str) -> _Repo:
        if name not in self.repos:
            raise RuntimeError(f"Repository not found: {name}")
        return self.repos[name]

    def fetch_discussion_categories(self, _repo: str) -> tuple[str, list[DiscussionCategory]]:
        return "R_1", [
            DiscussionCategory("C_1", "General", slug="general"),
            DiscussionCategory("C_2", "Ideas", slug="ideas"),
        ]

    def create_discussion(self, repo_id: str, category: str, title: str, body: str) -> Any:
        self.discussions.append((repo_id, category, title, body))
        return 12, "https://github.com/owner/repo/discussions/12"

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    said: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    monkeypatch.setattr(f"{_MIXIN}._confirm", lambda _self, *_a: True)
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    if ref.template == "organization":
        frame.provider.add_instance("organization", ref.instance)
        frame.rebuild_tree()
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _select(frame: WorkbenchFrame, starts: str) -> None:
    index = next(i for i, row in enumerate(frame.rows) if row.label.startswith(starts))
    for other in range(frame.list.GetItemCount()):
        frame.list.Select(other, on=False)
    frame.list.Select(index)
    frame.list.Focus(index)


class _Builder:
    """Stands in for the builder window: returns what each test hands it."""

    answers: list[str | None] = []
    seen: list[dict[str, Any]] = []

    def __init__(self, _parent: Any, **kwargs: Any) -> None:
        _Builder.seen.append(kwargs)
        self.use_pull_request = False

    def show(self) -> str | None:
        return _Builder.answers.pop(0) if _Builder.answers else None


@pytest.fixture
def builder(monkeypatch):
    _Builder.answers, _Builder.seen = [], []
    monkeypatch.setattr("quill.ui.github_template_builder_dialog.TemplateBuilderDialog", _Builder)
    return _Builder


def test_the_templates_node_lists_rows_and_their_menu_declares_its_writes(bench) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    labels = [row.label for row in bench.rows]
    assert labels[0] == "Bug report, issue form, adds bug, 1 field, 1 required"
    assert "Code of Conduct, missing" in labels
    assert {row.kind for row in bench.rows} == {"template"}
    assert GITHUB_ACTIONS.default_for("template").command_id == "github.workbench.open_template"
    for verb in ("open_template", "convert_template", "copy_template"):
        assert f"github.workbench.{verb}" in COMMAND_REQUIREMENTS
    assert NEW_HERE["templates"] == "github.workbench.new_template"
    assert NEW_HERE["discussions"] == "github.workbench.new_discussion"


def test_open_template_saves_after_asking_and_says_the_checked_result(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Bug report")
    builder.answers = [FORM + "# edited\n"]
    bench.default_action()
    assert builder.seen[0]["kind"] == "issue_form"
    assert builder.seen[0]["text"] == FORM
    repo = bench.items.repos[REPO]
    assert repo.writes == [(".github/ISSUE_TEMPLATE/bug.yml", FORM + "# edited\n")]
    assert any("and checked it" in line for line in bench.said)


def test_a_failed_save_reopens_the_window_with_the_draft(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Bug report")
    bench.items.repos[REPO].fail_next = True
    builder.answers = ["name: Mine\n", None]
    bench.default_action()
    assert len(builder.seen) == 2
    assert builder.seen[1]["text"] == "name: Mine\n"
    assert any("Your draft is kept" in line for line in bench.said)


def test_a_missing_community_file_opens_a_starter_and_creates_it(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Contributing")
    builder.answers = ["# Contributing\n"]
    bench.run("github.workbench.open_template")
    assert builder.seen[0]["text"].startswith("# Contributing")
    assert bench.items.repos[REPO].files[".github/CONTRIBUTING.md"] == "# Contributing\n"


def test_convert_makes_a_form_beside_the_markdown_template(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Code of Conduct")
    assert not bench.provider.supports("github.workbench.convert_template")
    _select(bench, "Old")
    assert bench.provider.supports("github.workbench.convert_template")
    builder.answers = [None]
    bench.run("github.workbench.convert_template")
    assert builder.seen[0]["path"] == ".github/ISSUE_TEMPLATE/old.yml"
    assert "label: Steps" in builder.seen[0]["text"]


def test_copy_previews_then_reports_each_repository(bench, monkeypatch) -> None:
    monkeypatch.setattr(f"{_MIXIN}._ask_text", lambda _self, *_a, **_k: "owner/other, owner/gone")
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Bug report")
    bench.run("github.workbench.copy_template")
    assert bench.items.repos["owner/other"].files[".github/ISSUE_TEMPLATE/bug.yml"] == FORM
    assert any(line.startswith("Copied to 1 of 2 repositories.") for line in bench.said)


def test_new_template_starts_from_a_starter(bench, builder, monkeypatch) -> None:
    picks = iter([0, 0])
    monkeypatch.setattr(f"{_MIXIN}._choose", lambda _self, *_a: next(picks))
    monkeypatch.setattr(f"{_MIXIN}._ask_text", lambda _self, *_a, **_k: "crash")
    _go(bench, NodeRef("repository", "templates", REPO))
    builder.answers = [None]
    bench.run("github.workbench.new_template")
    assert builder.seen[0]["path"] == ".github/ISSUE_TEMPLATE/crash.yml"
    assert "name: Bug report" in builder.seen[0]["text"]


def test_new_discussion_fills_the_categorys_form(bench, monkeypatch) -> None:
    monkeypatch.setattr(f"{_MIXIN}._choose", lambda _self, *_a: 1)
    filled: list[Any] = []

    class _Form:
        def __init__(self, _parent: Any, form: Any, **kwargs: Any) -> None:
            filled.append((form, kwargs))
            self.result = ("A new idea", "### Idea\n\nDark mode")

        def show(self) -> bool:
            return True

    monkeypatch.setattr("quill.ui.github_issue_form_dialog.IssueFormDialog", _Form)
    _go(bench, NodeRef("repository", "discussions", REPO))
    bench.provider._do_new_discussion(NodeRef("repository", "discussions", REPO), None)
    form, kwargs = filled[0]
    assert [f.label for f in form.fields] == ["Idea"]
    assert kwargs["noun"] == "discussion"
    assert bench.items.discussions == [("R_1", "C_2", "A new idea", "### Idea\n\nDark mode")]
    assert any(line.startswith("Started discussion #12") for line in bench.said)


# -- the builder window --------------------------------------------------------


@pytest.fixture
def help_ready(wx_session_app):
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)


def test_the_builder_adds_moves_removes_and_checks(help_ready) -> None:
    said: list[str] = []
    window = TemplateBuilderDialog(
        None, text=FORM, kind="issue_form", path="x/bug.yml", repository=REPO, announce=said.append
    )
    try:
        assert window.fields.GetStrings() == ["What happened?, long text, required"]
        window.add_field({"type": "input", "id": "version", "attributes": {"label": "Version"}})
        window.move(-1)
        assert window.fields.GetStrings()[0] == "Version, short text"
        window.move(-1)
        assert said[-1] == "Already at the top."
        window.add_field({"type": "input", "id": "version", "attributes": {"label": "Again"}})
        assert "is also field 1's" in window.checks.GetValue()

        class _Event:
            skipped = False

            def Skip(self) -> None:  # noqa: N802 - wx's name
                self.skipped = True

        event = _Event()
        window._on_save(event)
        assert not event.skipped and window.result is None
        assert said[-1].startswith("1 problem to fix first")
        window.remove()
        assert window.apply_source("name: [broken").startswith("The form is not valid YAML")
        assert len(window.draft.fields) == 2  # the draft survives the bad source
        window._on_save(event)
        assert event.skipped and "id: version" in window.result
    finally:
        window.dialog.Destroy()


def test_a_broken_form_opens_as_source_without_losing_it(help_ready) -> None:
    broken = "name: Bug\nbody: [unclosed\n"
    window = TemplateBuilderDialog(
        None, text=broken, kind="issue_form", path="x/bug.yml", repository=REPO
    )
    try:
        assert window.draft is None and window.fallback.startswith("The form is not valid YAML")
        assert window.source.GetValue() == broken
        assert window.checks.GetValue().startswith("Warning: Form:")
    finally:
        window.dialog.Destroy()


def test_the_field_dialog_builds_a_dropdown(help_ready) -> None:
    window = FieldDialog(None, "dropdown", taken={"os"})
    try:
        assert not window.placeholder.IsEnabled() and window.options.IsEnabled()
        window.label.SetValue("Operating system")
        window.options.SetValue("Windows\nmacOS")
        window.default.SetValue("2")
        made, problem = window.build()
        assert problem == ""
        assert made == {
            "type": "dropdown",
            "id": "operating-system",
            "attributes": {
                "label": "Operating system",
                "options": ["Windows", "macOS"],
                "default": 1,
            },
        }
        window.default.SetValue("9")
        assert window.build()[1] == "The default option must be a number from 1 to 2."
    finally:
        window.dialog.Destroy()


# -- the rest of Phase 12 ------------------------------------------------------


def test_the_organizations_templates_node_lists_its_github_repository(bench) -> None:
    _go(bench, NodeRef("organization", "organization_templates", "owner"))
    labels = [row.label for row in bench.rows]
    assert any(label.startswith("Bug report, issue form") for label in labels)
    assert any(label.startswith("Funding, community file") for label in labels)


def test_the_chooser_saves_its_text_and_renames_for_the_order(bench, monkeypatch) -> None:
    opened: list[Any] = []

    class _Chooser:
        def __init__(self, _parent: Any, text: str, filenames: list[str], **_k: Any) -> None:
            opened.append((text, filenames))
            self.renames = [("org.yml", "01-org.yml")]

        def show(self) -> str:
            return "blank_issues_enabled: false\n"

    monkeypatch.setattr("quill.ui.github_template_sheets_dialog.ChooserDialog", _Chooser)
    _go(bench, NodeRef("organization", "organization_templates", "owner"))
    _select(bench, "Template chooser")
    bench.default_action()
    assert opened == [("blank_issues_enabled: true\n", ["org.yml"])]
    files = bench.items.repos["owner/.github"].files
    assert files[".github/ISSUE_TEMPLATE/config.yml"] == "blank_issues_enabled: false\n"
    assert ".github/ISSUE_TEMPLATE/01-org.yml" in files
    assert ".github/ISSUE_TEMPLATE/org.yml" not in files
    assert any("Renamed 1 templates" in line for line in bench.said)


def test_funding_opens_its_own_sheet(bench, monkeypatch) -> None:
    seen: list[str] = []

    class _Funding:
        def __init__(self, _parent: Any, text: str, **_k: Any) -> None:
            seen.append(text)

        def show(self) -> str:
            return "github: jeff\npatreon: jb\n"

    monkeypatch.setattr("quill.ui.github_template_sheets_dialog.FundingDialog", _Funding)
    _go(bench, NodeRef("organization", "organization_templates", "owner"))
    _select(bench, "Funding")
    bench.default_action()
    assert seen == ["github: jeff\n"]
    assert bench.items.repos["owner/.github"].files["FUNDING.yml"].endswith("patreon: jb\n")


def test_a_form_converts_to_markdown_after_saying_what_it_loses(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Bug report")
    assert bench.provider.supports("github.workbench.convert_template")
    builder.answers = [None]
    bench.run("github.workbench.convert_template")
    assert builder.seen[0]["path"] == ".github/ISSUE_TEMPLATE/bug.md"
    assert builder.seen[0]["kind"] == "issue_template"
    assert "### What happened?" in builder.seen[0]["text"]


def test_forms_open_with_the_repositorys_labels_and_assignees(bench, builder) -> None:
    _go(bench, NodeRef("repository", "templates", REPO))
    _select(bench, "Bug report")
    builder.answers = [None]
    bench.default_action()
    assert builder.seen[0]["known_labels"] == ["bug", "idea"]
    assert builder.seen[0]["known_assignees"] == ["jeff"]


def test_copy_a_whole_set_from_the_chooser(bench, monkeypatch) -> None:
    monkeypatch.setattr(f"{_MIXIN}._ask_text", lambda _self, *_a, **_k: "owner/other")
    _go(bench, NodeRef("organization", "organization_templates", "owner"))
    _select(bench, "Template chooser")
    bench.run("github.workbench.copy_template")
    files = bench.items.repos["owner/other"].files
    assert files[".github/ISSUE_TEMPLATE/org.yml"] == FORM
    assert ".github/ISSUE_TEMPLATE/config.yml" in files
    assert any(line.startswith("Copied the set to 1 of 1") for line in bench.said)


def test_new_pull_request_fills_the_chosen_template(bench, monkeypatch) -> None:
    from quill.core.github.pull_compose import PullDraft

    start = PullDraft(REPO, "main", "topic", "Topic", "- one commit")
    provider = bench.provider
    one = provider._with_pull_template(start, [("Default", "## What\n")])
    assert one.body == "## What\n\n- one commit"
    monkeypatch.setattr(f"{_MIXIN}._choose", lambda _self, *_a: 2)
    two = provider._with_pull_template(start, [("A", "## A\n"), ("B", "## B\n")])
    assert two.body.startswith("## B")
    monkeypatch.setattr(f"{_MIXIN}._choose", lambda _self, *_a: -1)
    assert provider._with_pull_template(start, [("A", "a"), ("B", "b")]) is None


def test_the_builder_pickers_set_labels_and_check_assignees(help_ready) -> None:
    window = TemplateBuilderDialog(
        None,
        text=FORM,
        kind="issue_form",
        path="x/bug.yml",
        repository=REPO,
        known_labels=["bug", "docs"],
        known_assignees=["jeff"],
    )
    try:
        window.pick("labels", ["bug", "docs"])
        assert window.draft.top["labels"] == ["bug", "docs"]
        window.pick("assignees", ["ghost"])
        assert "ghost cannot be assigned" in window.checks.GetValue()
    finally:
        window.dialog.Destroy()


def test_the_sheets_build_their_files(help_ready) -> None:
    from quill.ui.github_template_sheets_dialog import (
        ChooserDialog,
        CitationDialog,
        CodeownersDialog,
        FundingDialog,
    )

    chooser = ChooserDialog(None, "blank_issues_enabled: true\n", ["bug.yml", "feature.yml"])
    try:
        chooser.blank.SetValue(False)
        chooser.add_link("Help", "https://x.org", "Ask here")
        chooser.templates.SetSelection(1)
        chooser.move(-1)
        text, problem = chooser.build()
        assert problem == "" and "blank_issues_enabled: false" in text
        assert chooser.renames == [("feature.yml", "01-feature.yml"), ("bug.yml", "02-bug.yml")]
        chooser.add_link("", "ftp://y", "")
        assert chooser.build()[0] is None
    finally:
        chooser.dialog.Destroy()
    funding = FundingDialog(None, "github: jeff\n")
    try:
        funding.boxes["ko_fi"].SetValue("jb")
        assert funding.build()[0] == "github: jeff\nko_fi: jb\n"
    finally:
        funding.dialog.Destroy()
    citation = CitationDialog(None, "")
    try:
        assert citation.build()[0] is None
        citation.boxes["title"].SetValue("QUILL")
        citation.people.SetValue("Bishop, Jeff")
        assert "family-names: Bishop" in citation.build()[0]
    finally:
        citation.dialog.Destroy()
    owners = CodeownersDialog(None, "* @all\n/docs/ @writers\n")
    try:
        owners.path.SetValue("docs/a.md")
        assert owners.look_up() == "Line 2, /docs/: @writers own docs/a.md."
    finally:
        owners.dialog.Destroy()


def test_new_template_starts_an_issue_form_from_a_surveyjs_file(
    bench, builder, monkeypatch, tmp_path
) -> None:
    """PRD 21.4: the conversion's door is New Template's last "Start from" row."""
    import json

    from quill.core.github.template_builder import STARTERS

    survey = tmp_path / "feedback_form.json"
    survey.write_text(
        json.dumps({
            "title": "Feedback",
            "elements": [
                {"type": "text", "name": "who", "title": "Your name"},
                {"type": "signaturepad", "name": "sig", "title": "Sign"},
            ],
        }),
        encoding="utf-8",
    )
    picks = iter([0, len(STARTERS)])  # Issue form, then the file row
    monkeypatch.setattr(f"{_MIXIN}._choose", lambda _self, *_a: next(picks))
    monkeypatch.setattr(f"{_MIXIN}._ask_text", lambda _self, *_a, **_k: "feedback")
    monkeypatch.setattr(
        "quill.ui.github_workbench_form_file._pick_file", lambda _bench: str(survey)
    )
    _go(bench, NodeRef("repository", "templates", REPO))
    builder.answers = [None]
    bench.run("github.workbench.new_template")
    assert builder.seen[0]["path"] == ".github/ISSUE_TEMPLATE/feedback.yml"
    assert "Your name" in builder.seen[0]["text"]
    assert any("did not carry over" in line and "Sign" in line for line in bench.said)
