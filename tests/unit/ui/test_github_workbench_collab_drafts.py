"""Wiki, discussion to issue to pull request, Related, github.dev and AI drafts (GX12-15)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import collab_links as cl
from quill.core.github import wiki_pages as wp
from quill.core.github.explore_models import ExploreRow
from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.items_provider import GitHubItem
from quill.core.github.write_gate import gated_tier
from quill.ui import github_workbench_collab as collab
from quill.ui import github_workbench_drafts as drafts
from quill.ui.github_workbench_development import DEVELOPMENT_REASONS, DEVELOPMENT_VERBS

ISSUE = GitHubItem(
    number=7, title="Fix it", state="open", url="https://github.com/o/r/issues/7", is_pr=False
)
PULL = GitHubItem(
    number=8, title="Pull", state="open", url="https://github.com/o/r/pull/8", is_pr=True
)
WIKI = ExploreRow("o/r has a wiki.", "", "https://github.com/o/r/wiki", "o/r", "wiki", "on")
WIKI_OFF = ExploreRow("off", "", "", "o/r", "wiki", "off")
DISCUSSION = ExploreRow(
    "Idea", "", "https://github.com/o/r/discussions/5", "o/r", "discussion", "5", title="Idea"
)


class _Window(collab.GitHubWorkbenchCollabMixin, drafts.GitHubWorkbenchDraftsMixin):
    signed_in = True

    def __init__(self, *, answers: list[str] | None = None, confirm: bool = True) -> None:
        self.said: list[str] = []
        self.asked: list[str] = []
        self.opened: list[Path] = []
        self.shown: list[tuple[str, str]] = []
        self.answers, self.confirm, self.choice = list(answers or []), confirm, 0
        self.items = SimpleNamespace(token="t")
        self.frame = SimpleNamespace(
            current=SimpleNamespace(template="repository", instance="o/r"),
            reload=lambda: self.said.append("(reloaded)"),
            rows=[ISSUE, PULL],
            selected_indices=lambda: [0, 1],
        )
        self._open_document = self.opened.append
        self._open_file_url = None

    def account_name(self) -> str:
        return "jeff"

    def github_api(self) -> Any:
        return "API"

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _ask_text(self, title: str, prompt: str, **_kw: Any) -> str:
        self.asked.append(prompt)
        return self.answers.pop(0) if self.answers else ""

    def _confirm(self, title: str, question: str) -> bool:
        self.asked.append(question)
        return self.confirm

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append(prompt + " | " + " / ".join(labels))
        return self.choice

    def _show_text(self, title: str, text: str) -> None:
        self.shown.append((title, text))

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


REF = SimpleNamespace(instance="o/r")


def test_every_verb_is_registered_with_a_reason_a_row_and_its_gate() -> None:
    for verb in (*collab.COLLAB_VERBS, *drafts.DRAFT_VERBS):
        assert verb in DEVELOPMENT_VERBS and verb in DEVELOPMENT_REASONS
    kinds = ("wiki", "issue", "pull_request", "discussion", "file", "repository")
    rows = {kind: {r.command_id for r in GITHUB_ACTIONS.rows_for(kind)} for kind in kinds}
    p = "github.workbench."
    assert {f"{p}wiki_pages", f"{p}new_wiki_page", f"{p}publish_wiki"} <= rows["wiki"]
    assert {f"{p}related", f"{p}pull_for_issue", f"{p}ai_task_breakdown"} <= rows["issue"]
    assert {f"{p}ai_pr_description", f"{p}ai_reviewer_brief", f"{p}open_github_dev"} <= rows[
        "pull_request"
    ]
    assert {f"{p}issue_from_discussion", f"{p}related"} <= rows["discussion"]
    assert f"{p}open_github_dev" in rows["file"] and f"{p}prompt_files" in rows["repository"]
    # The writes that reach GitHub are held to the account's level; local ones are not.
    for verb in ("publish_wiki", "issue_from_discussion", "pull_for_issue"):
        assert gated_tier(p + verb) is not None
    for verb in ("wiki_pages", "new_wiki_page", "related", "prompt_files"):
        assert gated_tier(p + verb) is None


def test_wiki_commands_fit_a_wiki_that_is_on(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(collab, "wiki_root", lambda: tmp_path)
    window = _Window()
    window.frame.current = SimpleNamespace(template="organization", instance="acme")
    assert window._fits_wiki_pages(WIKI) and not window._fits_wiki_pages(WIKI_OFF)
    assert not window._fits_publish_wiki(WIKI)  # no copy here yet
    (tmp_path / "o" / "r.wiki" / ".git").mkdir(parents=True)
    assert window._fits_publish_wiki(WIKI)


def test_new_wiki_page_makes_the_file_and_opens_it(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(collab, "wiki_root", lambda: tmp_path)
    (tmp_path / "o" / "r.wiki" / ".git").mkdir(parents=True)
    window = _Window(answers=["Release Steps"])
    window._do_new_wiki_page(REF, WIKI)
    assert window.opened == [tmp_path / "o" / "r.wiki" / "Release-Steps.md"]
    assert window.said[-1].startswith("Made the page Release Steps here.")


def test_publish_names_the_pages_the_wiki_and_the_account_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(collab, "wiki_root", lambda: tmp_path)
    monkeypatch.setattr(collab.GitHubWorkbenchCollabMixin, "_git", staticmethod(lambda: "git"))
    monkeypatch.setattr(wp, "changed_pages", lambda *_a, **_k: ["Home.md"])
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        wp, "publish", lambda git, repo, folder, msg, **kw: sent.append((repo, msg)) or "Done."
    )
    window = _Window(answers=["Fix typo"])
    window._do_publish_wiki(REF, WIKI)
    assert "Publish 1 changed pages (Home.md) to o/r's wiki on GitHub, as jeff?" in window.asked[0]
    assert sent == [("o/r", "Fix typo")] and window.said[-1] == "Done."

    refused = _Window(confirm=False)
    sent.clear()
    refused._do_publish_wiki(REF, WIKI)
    assert sent == []


def test_create_issue_from_discussion_asks_then_opens_without_the_comment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made: list[dict[str, Any]] = []

    def issue(api: Any, repo: str, number: int, title: str, body: str, **kw: Any) -> Any:
        made.append({"repo": repo, "number": number, "title": title, "body": body, **kw})
        return 11, "Opened issue #11 from discussion #5."

    monkeypatch.setattr(cl, "issue_from_discussion", issue)
    window = _Window(answers=["New title", "Edited body"])
    window.choice = 1
    api = SimpleNamespace(
        graphql=lambda _q, _v: {
            "repository": {"discussion": {"body": "Hi", "author": {"login": "ann"}}}
        }
    )
    window.github_api = lambda: api  # type: ignore[method-assign]
    window._do_issue_from_discussion(REF, DISCUSSION)
    assert made == [
        {"repo": "o/r", "number": 5, "title": "New title", "body": "Edited body",
         "comment_back": False},
    ]  # fmt: skip
    assert "Open the issue in o/r, as jeff:" in window.asked[-1]
    assert window.said == ["Opened issue #11 from discussion #5."]


def test_start_pull_request_states_the_effect_and_stops_on_no(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(cl, "pull_for_issue", lambda *a: calls.append(a[1:]) or (21, "Opened #21."))
    assert _Window()._fits_pull_for_issue(ISSUE) and not _Window()._fits_pull_for_issue(PULL)
    window = _Window(answers=["7-fix-it"])
    window._do_pull_for_issue(REF, ISSUE)
    assert "make branch 7-fix-it linked to #7" in window.asked[-1]
    assert "draft pull request that closes #7" in window.asked[-1]
    assert calls == [("o/r", 7, "Fix it", "7-fix-it")]
    assert window.said == ["Opened #21.", "(reloaded)"]
    calls.clear()
    _Window(answers=["7-fix-it"], confirm=False)._do_pull_for_issue(REF, ISSUE)
    assert calls == []


def test_related_with_nothing_linked_says_one_sentence() -> None:
    window = _Window()
    window._show_related(cl.Related("Issue #7", ()))
    assert window.said == ["Issue #7: nothing linked."]
    assert window._fits_related(ISSUE) and window._fits_related(DISCUSSION)


def test_github_dev_opens_the_exact_file_or_pull_request() -> None:
    window = _Window()
    file_row = ExploreRow("a.py", "", "https://github.com/o/r/blob/main/src/a.py", "o/r", "file")
    assert window._github_dev_url(file_row) == "https://github.dev/o/r/blob/main/src/a.py"
    assert window._github_dev_url(PULL) == "https://github.dev/o/r/pull/8"
    assert not window._fits_open_github_dev(ISSUE)


def test_prompt_files_fit_a_repository() -> None:
    window = _Window()
    assert window._fits_prompt_files(None)
    window.frame.current = SimpleNamespace(template="person", instance="ann")
    assert not window._fits_prompt_files(None)
    repo_row = ExploreRow("o/x", "", "", "o/x", "repo", "o/x")
    assert window._prompt_repo(repo_row) == "o/x"


def test_drafts_are_greyed_without_ai_and_say_why() -> None:
    window = _Window()
    assert not window._fits_ai_task_breakdown(ISSUE)
    assert "Choose Your AI" in DEVELOPMENT_REASONS["ai_task_breakdown"]


def test_a_draft_is_grounded_opened_as_a_file_and_never_posted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drafts, "_draft_path", lambda name, task: tmp_path / f"{task}.md")
    prompts: list[str] = []
    window = _Window()
    window.ai_drafter = lambda: lambda prompt: prompts.append(prompt) or "1. Do the thing."
    assert window._fits_ai_task_breakdown(ISSUE) and not window._fits_ai_task_breakdown(PULL)
    window._do_ai_task_breakdown(REF, ISSUE)
    assert "untrusted source material" in prompts[0] and "#7 Fix it" in prompts[0]
    text = (tmp_path / "issue_decomposition.md").read_text(encoding="utf-8")
    assert text.startswith("Draft task breakdown, written by AI")
    assert "QUILL has posted nothing" in text and "https://github.com/o/r/issues/7" in text
    assert window.opened == [tmp_path / "issue_decomposition.md"]


def test_release_notes_use_only_the_selected_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drafts, "_draft_path", lambda name, task: tmp_path / f"{task}.md")
    prompts: list[str] = []
    window = _Window()
    window.frame.selected_indices = lambda: [1]
    window.ai_drafter = lambda: lambda prompt: prompts.append(prompt) or "Notes."
    window._do_ai_release_notes(REF, PULL)
    assert "#8 Pull" in prompts[0] and "#7 Fix it" not in prompts[0]


def test_declining_the_ai_connection_sends_nothing() -> None:
    window = _Window()
    window.ai_drafter = lambda: None
    window._do_ai_task_breakdown(REF, ISSUE)
    assert window.said == ["AI is not set up, so there is no draft."]
