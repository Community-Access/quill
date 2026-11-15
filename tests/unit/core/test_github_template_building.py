"""GitHub templates: the catalogue, the builder model and its checks, saving and copying.

GitHub PRD section 21. Everything runs against a fake PyGithub repository; no
network.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.issue_forms import parse_issue_form, render_body
from quill.core.github.template_builder import (
    FormDraft,
    TemplateDraftError,
    check,
    dump_draft,
    field_summary,
    load_draft,
    make_id,
    markdown_to_form,
    new_field,
    starter,
    update_field,
)
from quill.core.github.template_catalog import list_templates
from quill.core.github.template_save import (
    TemplateSaveConflict,
    TemplateSaveError,
    copy_template,
    plan_copy,
    plan_save,
    save_template,
)


class _NotFound(Exception):
    status = 404


class _Item:
    def __init__(self, repo: _Repo, path: str, kind: str) -> None:
        self.path, self.type = path, kind
        self.name = path.rsplit("/", 1)[-1]
        self.html_url = f"https://github.com/{repo.full_name}/blob/main/{path}"
        text = repo.files.get(path, "")
        self.size = len(text.encode()) if kind == "file" else 0
        self.sha = repo.shas.get(path, "")
        self.decoded_content = text.encode() if kind == "file" else b""


class _Commit:
    def __init__(self, sha: str) -> None:
        self.sha = sha


class _Branch:
    def __init__(self, protected: bool) -> None:
        self.protected = protected
        self.commit = _Commit("head-sha")


class _Pull:
    number = 7
    html_url = "https://github.com/o/r/pull/7"


class _Perms:
    def __init__(self, push: bool) -> None:
        self.push = push


class _Repo:
    """Enough of PyGithub's Repository for the catalogue and the saves."""

    def __init__(
        self,
        full_name: str,
        files: dict[str, str],
        *,
        protected: bool = False,
        push: bool = True,
    ) -> None:
        self.full_name = full_name
        self.default_branch = "main"
        self.files = dict(files)
        self.shas = {path: f"sha-{index}" for index, path in enumerate(files)}
        self.branch_files: dict[str, dict[str, str]] = {}
        self.protected = protected
        self.permissions = _Perms(push)
        self.refs: list[tuple[str, str]] = []
        self.pulls: list[dict[str, Any]] = []
        self.writes: list[tuple[str, str, str]] = []

    def _tree(self, ref: str | None) -> dict[str, str]:
        if ref and ref != "main":
            return self.branch_files.setdefault(ref, dict(self.files))
        return self.files

    def get_contents(self, path: str, ref: str | None = None) -> Any:
        tree = self._tree(ref)
        if path in tree:
            return _Item(self, path, "file") if ref in (None, "main") else _BranchItem(tree, path)
        prefix = f"{path}/" if path else ""
        children = {p[len(prefix) :].split("/", 1)[0] for p in tree if p.startswith(prefix)}
        if not children:
            raise _NotFound(path)
        return [
            _Item(self, prefix + name, "file" if prefix + name in tree else "dir")
            for name in sorted(children)
        ]

    def get_branch(self, name: str) -> _Branch:
        if name != "main" and name not in self.branch_files:
            raise _NotFound(name)
        return _Branch(self.protected)

    def create_file(self, path: str, message: str, content: str, branch: str) -> dict[str, Any]:
        self._tree(branch)[path] = content
        self.writes.append(("create", path, branch))
        return {"commit": _Commit("new-commit")}

    def update_file(
        self, path: str, message: str, content: str, sha: str, branch: str
    ) -> dict[str, Any]:
        self._tree(branch)[path] = content
        self.writes.append(("update", path, branch))
        return {"commit": _Commit("new-commit")}

    def delete_file(self, path: str, message: str, sha: str, branch: str) -> None:
        del self._tree(branch)[path]
        self.writes.append(("delete", path, branch))

    def create_git_ref(self, ref: str, sha: str) -> None:
        self.refs.append((ref, sha))
        self.branch_files[ref.removeprefix("refs/heads/")] = dict(self.files)

    def create_pull(self, **kwargs: Any) -> _Pull:
        self.pulls.append(kwargs)
        return _Pull()


class _BranchItem:
    def __init__(self, tree: dict[str, str], path: str) -> None:
        self.decoded_content = tree[path].encode()
        self.sha = "branch-sha"


FORM = """name: Bug report
description: Something broke.
title: "[Bug]: "
labels: [bug, triage]
projects: ["o/1"]
body:
  - type: markdown
    attributes:
      value: Thanks.
  - type: textarea
    id: what
    attributes:
      label: What happened?
      x-future: kept
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version
"""

MARKDOWN = """---
name: Old bug
about: The old way.
labels: bug
---
Please fill this in.

### Steps to reproduce
<!-- One per line -->

### Expected
"""


# -- the catalogue -------------------------------------------------------------


def test_the_catalogue_lists_every_kind_and_marks_inherited_and_missing() -> None:
    own = _Repo(
        "o/r",
        {
            ".github/ISSUE_TEMPLATE/bug.yml": FORM,
            ".github/ISSUE_TEMPLATE/old.md": MARKDOWN,
            ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: false\n",
            ".github/pull_request_template.md": "## What\n",
            "CONTRIBUTING.md": "# Contributing\n",
        },
    )
    org = _Repo(
        "o/.github",
        {
            ".github/ISSUE_TEMPLATE/org.yml": FORM,
            ".github/DISCUSSION_TEMPLATE/ideas.yml": "body:\n  - type: input\n"
            "    attributes: {label: Idea}\n",
            "SECURITY.md": "# Security\n",
        },
    )
    repos = {"o/r": own, "o/.github": org}
    entries = list_templates(repos.__getitem__, "o/r")
    by_path = {(e.source, e.path): e for e in entries}
    bug = by_path["o/r", ".github/ISSUE_TEMPLATE/bug.yml"]
    assert bug.label() == "Bug report, issue form, adds bug and triage, 2 fields, 1 required"
    assert by_path["o/r", ".github/ISSUE_TEMPLATE/old.md"].name == "Old bug"
    chooser = by_path["o/r", ".github/ISSUE_TEMPLATE/config.yml"]
    assert "blank issues not allowed" in chooser.label()
    assert by_path["o/r", ".github/pull_request_template.md"].kind == "pull_request_template"
    # The repository has issue templates of its own, so the org's are not used.
    assert ("o/.github", ".github/ISSUE_TEMPLATE/org.yml") not in by_path
    ideas = by_path["o/.github", ".github/DISCUSSION_TEMPLATE/ideas.yml"]
    assert ideas.inherited and ideas.category == "ideas"
    assert "inherited from o/.github" in ideas.label()
    community = {e.name: e for e in entries if e.kind == "community_file"}
    assert not community["Contributing"].inherited
    assert community["Security"].inherited
    assert community["Code of Conduct"].missing
    assert community["Code of Conduct"].label() == "Code of Conduct, missing"


def test_an_oversized_template_is_listed_without_being_read() -> None:
    repo = _Repo("o/r", {".github/ISSUE_TEMPLATE/huge.yml": "x" * 60_000})
    (entry, *_rest) = list_templates({"o/r": repo}.__getitem__, "o/r")
    assert entry.text == ""
    assert "too large" in entry.problem


# -- the builder model ---------------------------------------------------------


def test_round_trip_keeps_keys_the_builder_does_not_know() -> None:
    draft = load_draft(FORM)
    draft.set("description", "Something broke badly.")
    draft.fields[1] = update_field(
        draft.fields[1],
        new_field("textarea", "What happened?", ident="what", required=False),
    )
    again = load_draft(dump_draft(draft))
    assert again.top["projects"] == ["o/1"]
    assert again.fields[1]["attributes"]["x-future"] == "kept"
    assert "validations" not in again.fields[1]
    assert again.get("description") == "Something broke badly."


def test_field_operations_and_summaries() -> None:
    draft = load_draft(FORM)
    assert field_summary(draft.fields[1]) == "What happened?, long text, required"
    assert draft.move(2, -1) == 1
    assert draft.fields[1]["id"] == "version"
    assert draft.move(0, -1) == 0
    draft.remove(0)
    assert [raw.get("id") for raw in draft.fields] == ["version", "what"]
    assert make_id("What happened?", {"what-happened"}) == "what-happened-2"
    drop = new_field("dropdown", "OS", options=["Windows", "macOS"], default=1)
    assert field_summary(drop) == "OS, drop-down, 2 options"


def test_check_catches_what_github_reports_after_commit() -> None:
    draft = FormDraft(top={"name": "Bug report"})
    draft.fields = [
        {"type": "input", "id": "a b", "attributes": {"label": "Name"}},
        {"type": "input", "id": "a b", "attributes": {"label": "name"}},
        {
            "type": "dropdown",
            "id": "os",
            "attributes": {"label": "OS", "options": ["None", "None"]},
        },
        {"type": "checkboxes", "id": "c", "attributes": {"label": "Agree", "options": []}},
        {"type": "slider", "attributes": {"label": "Mood"}},
        {"type": "textarea", "attributes": {"description": "no label"}},
    ]
    messages = [p.sentence() for p in check(draft, other_names=["bug report"])]
    text = "\n".join(messages)
    assert "Name: another template in this repository has this name" in text
    assert "Description: an issue form needs a description" in text
    assert "may use only letters, numbers, - and _" in text
    assert "is also field 1's" in text
    assert "the label is also field 1's" in text
    assert '"None" is reserved' in text
    assert "two options are the same" in text
    assert "Field 4 (Agree): needs at least one option" in text
    assert "GitHub has no field of kind slider" in text
    assert "every field but instructions needs a label" in text


def test_check_warns_about_unknown_labels_but_does_not_stop_a_save() -> None:
    draft = load_draft(FORM)
    found = check(draft, known_labels=["bug"])
    assert [p.severity for p in found] == ["warning"]
    assert any("'triage' does not exist" in p.message for p in found)


def test_unreadable_and_oversized_forms_say_why() -> None:
    with pytest.raises(TemplateDraftError, match="not valid YAML"):
        load_draft("name: [unclosed")
    with pytest.raises(TemplateDraftError, match="larger than"):
        load_draft("x" * 60_000)
    with pytest.raises(TemplateDraftError, match="body is not a list"):
        load_draft("body: 3")


def test_starters_pass_their_own_checks_and_fill() -> None:
    for name in ("bug", "feature", "accessibility", "blank"):
        draft = starter(name)
        assert [p for p in check(draft) if p.severity == "error"] == [], name
        form = parse_issue_form(dump_draft(draft), f"{name}.yml")
        assert not form.unsupported, name
    discussion = starter("bug", kind="discussion_form")
    assert "name" not in discussion.top
    assert check(discussion) == []


def test_markdown_template_converts_to_a_form() -> None:
    draft = markdown_to_form(MARKDOWN, filename="old.md")
    assert draft.top["name"] == "Old bug"
    assert draft.top["description"] == "The old way."
    assert draft.top["labels"] == ["bug"]
    assert [field_summary(raw) for raw in draft.fields] == [
        "Instructions: Please fill this in.",
        "Steps to reproduce, long text",
        "Expected, long text",
    ]
    assert draft.fields[1]["attributes"]["description"] == "One per line"
    form = parse_issue_form(dump_draft(draft))
    body = render_body(form, {"steps-to-reproduce": "1. Open it"})
    assert body == "### Steps to reproduce\n\n1. Open it\n\n### Expected\n\n_No response_"


# -- saving --------------------------------------------------------------------


def test_save_goes_to_the_default_branch_and_is_read_back() -> None:
    repo = _Repo("o/r", {".github/ISSUE_TEMPLATE/bug.yml": FORM})
    plan = plan_save(repo, "o/r", ".github/ISSUE_TEMPLATE/bug.yml")
    assert plan.current_sha == "sha-0" and not plan.needs_pull_request
    assert "replaces" in plan.sentence(use_pull_request=False)
    result = save_template(repo, plan, FORM + "# changed\n", expected_sha="sha-0")
    assert repo.writes == [("update", ".github/ISSUE_TEMPLATE/bug.yml", "main")]
    assert result.sentence().startswith("Saved .github/ISSUE_TEMPLATE/bug.yml to main")


def test_a_protected_branch_saves_through_a_new_branch_and_pull_request() -> None:
    repo = _Repo("o/r", {"README.md": "hi"}, protected=True)
    plan = plan_save(repo, "o/r", ".github/ISSUE_TEMPLATE/new.yml")
    assert plan.needs_pull_request and plan.current_sha == ""
    assert "protected" in plan.sentence(use_pull_request=True)
    result = save_template(repo, plan, FORM, expected_sha="")
    assert repo.refs and repo.refs[0][0].startswith("refs/heads/quill/template-new-yml-")
    assert repo.pulls[0]["base"] == "main"
    assert result.pull_request_number == 7
    assert "pull request #7" in result.sentence()
    assert ".github/ISSUE_TEMPLATE/new.yml" not in repo.files


def test_a_changed_file_is_a_conflict_and_nothing_is_written() -> None:
    repo = _Repo("o/r", {".github/ISSUE_TEMPLATE/bug.yml": FORM})
    plan = plan_save(repo, "o/r", ".github/ISSUE_TEMPLATE/bug.yml")
    with pytest.raises(TemplateSaveConflict, match="changed on GitHub"):
        save_template(repo, plan, FORM, expected_sha="an-older-sha")
    assert repo.writes == []


def test_no_write_access_saves_nothing() -> None:
    repo = _Repo("o/r", {}, push=False)
    plan = plan_save(repo, "o/r", ".github/pull_request_template.md")
    with pytest.raises(TemplateSaveError, match="write access"):
        save_template(repo, plan, "## What\n", expected_sha="")


# -- copying -------------------------------------------------------------------


def test_copy_previews_each_target_and_reports_each_result() -> None:
    path = ".github/ISSUE_TEMPLATE/bug.yml"
    repos = {
        "o/same": _Repo("o/same", {path: FORM}),
        "o/variant": _Repo("o/variant", {path: "name: old\n"}),
        "o/missing": _Repo("o/missing", {"README.md": "x"}),
    }

    def repo_for(name: str) -> _Repo:
        if name not in repos:
            raise RuntimeError("Repository not found")
        return repos[name]

    plan = plan_copy(repo_for, path, FORM, ["o/same", "o/variant", "o/missing", "o/gone"])
    assert [(t.repository, t.state) for t in plan] == [
        ("o/same", "same"),
        ("o/variant", "variant"),
        ("o/missing", "missing"),
        ("o/gone", "unreadable"),
    ]
    results = copy_template(repo_for, path, FORM, plan)
    assert [r.ok for r in results] == [True, True, True, False]
    assert repos["o/variant"].files[path] == FORM
    assert repos["o/missing"].files[path] == FORM
    assert repos["o/same"].writes == []


# -- the chooser, community files, conversions, Check This File -----------------


def test_the_chooser_round_trips_and_orders_by_renaming() -> None:
    from quill.core.github.template_files import (
        check_chooser,
        dump_chooser,
        order_renames,
        parse_chooser,
    )

    config = parse_chooser(
        "blank_issues_enabled: false\nx-keep: 1\ncontact_links:\n"
        "  - {name: Help, url: 'https://x.org', about: Ask}\n"
    )
    assert not config.blank_issues_enabled and config.contact_links[0]["name"] == "Help"
    config.contact_links.append({"name": "", "url": "ftp://y", "about": ""})
    messages = [p.message for p in check_chooser(config)]
    assert "needs name" in messages and "the address must start with https://" in messages
    config.contact_links.pop()
    assert "x-keep: 1" in dump_chooser(config)
    assert order_renames(["02-feature.yml", "01-bug.yml", "docs.md"]) == [
        ("02-feature.yml", "01-feature.yml"),
        ("01-bug.yml", "02-bug.yml"),
        ("docs.md", "03-docs.md"),
    ]


def test_rename_templates_adds_then_deletes_each_file() -> None:
    from quill.core.github.template_save import rename_templates

    repo = _Repo("o/r", {".github/ISSUE_TEMPLATE/bug.yml": FORM})
    plan = plan_save(repo, "o/r", ".github/ISSUE_TEMPLATE/config.yml")
    result = rename_templates(repo, plan, ".github/ISSUE_TEMPLATE", [("bug.yml", "01-bug.yml")])
    assert repo.files == {".github/ISSUE_TEMPLATE/01-bug.yml": FORM}
    assert [w[0] for w in repo.writes] == ["create", "delete"]
    assert result.branch == "main"


def test_funding_citation_and_codeowners() -> None:
    from quill.core.github.template_files import (
        dump_citation,
        dump_funding,
        owners_for,
        parse_citation,
        parse_funding,
    )

    funding = parse_funding("github: [a, b]\npatreon: me\n")
    assert funding == {"github": "a, b", "patreon": "me"}
    funding["ko_fi"] = "kofi"
    funding["patreon"] = ""
    assert dump_funding(funding) == "github:\n- a\n- b\nko_fi: kofi\n"
    fields, authors, extra = parse_citation(
        "cff-version: 1.2.0\ntitle: Q\nauthors:\n  - {family-names: Bishop, given-names: Jeff}\n"
        "keywords: [a]\n"
    )
    assert fields["title"] == "Q" and authors == ["Bishop, Jeff"]
    again = dump_citation(fields, [*authors, "Community Access"], extra)
    assert "- name: Community Access" in again and "keywords:" in again
    rules = "* @everyone\n/docs/ @writers\n*.py @coders  # code\n/docs/api/*.md @api\n"
    assert owners_for(rules, "src/app.py").owners == ("@coders",)
    assert owners_for(rules, "docs/guide.md").owners == ("@writers",)
    assert owners_for(rules, "docs/api/x.md").owners == ("@api",)
    assert owners_for(rules, "README").owners == ("@everyone",)
    assert owners_for("/docs/ @w\n", "src/a.c") is None


def test_a_form_converts_to_markdown_and_says_what_it_loses() -> None:
    from quill.core.github.template_convert import form_to_markdown, markdown_losses

    draft = load_draft(FORM)
    text = form_to_markdown(draft)
    assert text.startswith("---\nname: Bug report\nabout: Something broke.\n")
    assert "### What happened?" in text and "Thanks." in text
    assert markdown_losses(draft) == [
        "What happened? will no longer be required.",
        "Markdown templates cannot set projects.",
    ]
    back = markdown_to_form(text, filename="bug.md")
    assert [raw["attributes"].get("label") for raw in back.fields][1:] == [
        "What happened?",
        "Version",
    ]


def test_a_surveyjs_form_becomes_an_issue_form_with_a_report() -> None:
    from quill.core.forms.interop_surveyjs import import_surveyjs
    from quill.core.github.template_convert import qaf_to_draft

    survey = {
        "title": "Feedback",
        "elements": [
            {"type": "text", "name": "who", "title": "Your name", "isRequired": True},
            {"type": "comment", "name": "what", "title": "What happened"},
            {"type": "dropdown", "name": "os", "title": "OS", "choices": ["Windows", "Mac"]},
            {"type": "signaturepad", "name": "sig", "title": "Sign"},
        ],
    }
    draft, report = qaf_to_draft(import_surveyjs(survey).model)
    kinds = [(raw["type"], raw["attributes"].get("label")) for raw in draft.fields]
    assert ("input", "Your name") in kinds and ("dropdown", "OS") in kinds
    assert any("Sign" in line for line in report)
    assert [p for p in check(draft) if p.severity == "error"] == []


def test_check_this_file_puts_form_problems_on_their_lines(tmp_path) -> None:
    from pathlib import Path

    from quill.core.github.template_convert import form_template_kind
    from quill.core.problems.builtin import check_yaml

    text = "name: Bug\nbody:\n  - type: input\n    attributes: {label: A}\n  - type: slider\n"
    path = Path(".github/ISSUE_TEMPLATE/bug.yml")
    assert form_template_kind(str(path)) == "issue_form"
    assert form_template_kind(".github/ISSUE_TEMPLATE/config.yml") == ""
    found = check_yaml(text, path)
    lines = {(p.line, p.message.split(": ", 1)[0]) for p in found}
    assert (1, "Description") in lines
    assert (5, "Field 2") in lines
    assert check_yaml(text, Path("ci.yml")) == []


def test_assignees_that_cannot_be_assigned_are_warned_about() -> None:
    draft = load_draft(FORM)
    draft.set("assignees", "jeff, ghost")
    found = check(draft, known_assignees=["jeff"])
    assert [p.message for p in found if p.where == "Assignees"] == [
        "ghost cannot be assigned in this repository; GitHub skips them"
    ]


def test_a_whole_set_copies_with_one_result_per_repository() -> None:
    from quill.core.github.template_save import copy_set, plan_copy_set

    files = {".github/ISSUE_TEMPLATE/bug.yml": FORM, ".github/ISSUE_TEMPLATE/config.yml": "x: 1\n"}
    repos = {"o/a": _Repo("o/a", {".github/ISSUE_TEMPLATE/bug.yml": FORM})}
    plan = plan_copy_set(repos.__getitem__, files, ["o/a"])
    assert [t.state for _p, t in plan["o/a"]] == ["same", "missing"]
    (result,) = copy_set(repos.__getitem__, files, plan)
    assert result.ok and result.sentence == "o/a: 1 of 2 written."
    assert repos["o/a"].files[".github/ISSUE_TEMPLATE/config.yml"] == "x: 1\n"


def test_pull_request_templates_are_found() -> None:
    from quill.core.github.template_catalog import pull_request_templates

    repo = _Repo(
        "o/r",
        {
            ".github/PULL_REQUEST_TEMPLATE/feature.md": "## Feature\n",
            "docs/pull_request_template.md": "## Docs\n",
        },
    )
    assert sorted(pull_request_templates(repo, "o/r")) == [
        ("Feature", "## Feature\n"),
        ("Pull Request Template", "## Docs\n"),
    ]
