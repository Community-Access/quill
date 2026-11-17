"""GitHub from the editor (PRD 22.3): the shared commands, against a fake window.

Git, the network, the browser and the comment prompt are replaced; everything
else is the real module, so each command's sentence, refusal and hand-off is
the one both editors give.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import editor_line as el
from quill.core.local_git import BlameInfo
from quill.ui import github_editor_line as gel

SHA = "0123456789abcdef0123456789abcdef01234567"


class Window:
    """A LineHost's worth of window: records what it was asked to do."""

    def __init__(self, path: str = "/repo/src/app.py", selection: str = "") -> None:
        self.said: list[str] = []
        self.copied: list[str] = []
        self.workbench: list[tuple[str, str]] = []
        self.references: list[tuple[Any, str]] = []
        self.path = path
        self.selection = selection
        self.text = "Fixes #12 for @ada"
        self.offset = 7
        self.provider_object: Any = SimpleNamespace(token="t", comments=[])
        self.provider_object.post_line_comment = lambda *args: self.provider_object.comments.append(
            args
        )

    def host(self, **overrides: Any) -> gel.LineHost:
        values: dict[str, Any] = {
            "parent": None,
            "announce": self.said.append,
            "run_background": lambda _name, work, done, failed: _run(work, done, failed),
            "copy_text": lambda text: self.copied.append(text) or True,
            "file_path": lambda: self.path,
            "span": lambda: (4, 6 if self.selection else 4, self.selection),
            "text_and_offset": lambda: (self.text, self.offset),
            "provider": lambda _retry: self.provider_object,
            "open_workbench": lambda repo, then: self.workbench.append((repo, then)),
            "open_reference": lambda ref, then: self.references.append((ref, then)),
            "show_modal": lambda _dialog, _label: 0,
        }
        values.update(overrides)
        return gel.LineHost(**values)


def _run(work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001 - the host reports it, as the editors do
        failed(exc)
        return
    done(result)


SITE = el.LineSite("ada/engine", "/repo", "src/app.py", SHA, 4, 4, branch="feature")


@pytest.fixture(autouse=True)
def _git(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """git is installed, and every line is SITE (or the span asked for)."""
    state: dict[str, Any] = {"site": SITE}
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: True)
    monkeypatch.setattr(gel, "_runner", lambda: None)
    gel._LAST_BLAME.clear()

    def locate(_path: str, first: int, last: int = 0, *, runner: object) -> el.LineSite:
        site: el.LineSite = state["site"]
        return el.LineSite(
            site.repository,
            site.root,
            site.path,
            site.commit,
            first,
            max(first, last),
            site.branch,
            site.pushed,
            site.changed,
        )

    monkeypatch.setattr(el, "locate", locate)
    return state


def test_copy_line_link_copies_the_permalink_and_says_so() -> None:
    window = Window()
    gel.copy_line_link(window.host())
    assert window.copied == [f"https://github.com/ada/engine/blob/{SHA}/src/app.py#L4"]
    assert window.said == ["Copied the link to line 4."]


def test_a_link_to_an_unpushed_commit_says_it_will_not_open_yet(_git) -> None:
    _git["site"] = el.LineSite("ada/engine", "/repo", "src/app.py", SHA, 4, 4, pushed=False)
    window = Window()
    gel.copy_line_link(window.host())
    assert "not on GitHub yet" in window.said[0]


def test_every_line_command_is_refused_in_safe_mode() -> None:
    for command in (
        gel.copy_line_link,
        gel.open_line,
        gel.who_changed_line,
        gel.issue_from_selection,
        gel.issues_mentioning_file,
        gel.open_reference_at_cursor,
    ):
        window = Window(selection="x")
        command(window.host(safe_mode=True))
        assert window.said == [gel.SAFE_MODE], command.__name__


def test_without_git_the_command_says_where_to_get_it(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.git_available", lambda: False)
    window = Window()
    gel.copy_line_link(window.host())
    assert window.said == [gel.NO_GIT]


def test_a_file_outside_a_repository_is_said_plainly(monkeypatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> el.LineSite:
        raise el.EditorLineError("This file is not in a git repository.")

    monkeypatch.setattr(el, "locate", refuse)
    window = Window()
    gel.copy_line_link(window.host())
    # Said with its support code, as every coded error is.
    assert window.said == ["[QUILL-GITHUB-EDITOR-LINE] This file is not in a git repository."]


def test_open_line_opens_the_permalink_in_the_browser(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(gel.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    window = Window()
    gel.open_line(window.host())
    assert opened == [el.permalink(SITE)]
    assert window.said == ["Opened line 4 on GitHub in your browser."]


def test_who_changed_says_the_commit_and_a_second_press_opens_its_pull(monkeypatch) -> None:
    info = BlameInfo(SHA, "Ada", "1772496000", "Fix the parser")
    monkeypatch.setattr("quill.core.local_git.blame_line", lambda *_a, **_k: info)
    answers = SimpleNamespace(
        data=[{"number": 7, "html_url": "https://github.com/ada/engine/pull/7", "merged_at": "x"}]
    )
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.rest_transport.request_json",
        lambda _token, _method, path, **_k: asked.append(path) or answers,
    )
    window = Window()
    gel.who_changed_line(window.host())
    assert window.said == ["Changed by Ada on 3 March 2026: Fix the parser (0123456)."]
    gel.who_changed_line(window.host())
    assert asked == [f"/repos/ada/engine/commits/{SHA}/pulls"]
    reference, then = window.references[0]
    assert (reference.repository, reference.kind, then) == (
        "ada/engine",
        "pull_request",
        "filter:#7",
    )


def test_a_line_no_pull_request_brought_says_so(monkeypatch) -> None:
    info = BlameInfo(SHA, "Ada", "1772496000", "Direct push")
    monkeypatch.setattr("quill.core.local_git.blame_line", lambda *_a, **_k: info)
    monkeypatch.setattr(
        "quill.core.github.rest_transport.request_json",
        lambda *_a, **_k: SimpleNamespace(data=[]),
    )
    window = Window()
    gel.open_line_pull(window.host())
    assert window.said == [
        "No pull request brought this line: commit 0123456 went straight to its branch."
    ]


def test_new_issue_from_selection_needs_a_selection_then_drafts_it() -> None:
    window = Window()
    gel.issue_from_selection(window.host())
    assert window.said == ["Select the text the issue is about first."]
    window = Window(selection="total = add(a, b)\nreturn total")
    gel.issue_from_selection(window.host())
    repository, then = window.workbench[0]
    assert repository == "ada/engine" and then.startswith("issue:")
    title, body = json.loads(then.partition(":")[2])
    assert title == "app.py, lines 4 to 6: total = add(a, b)"
    assert "```python\ntotal = add(a, b)\nreturn total\n```" in body


def test_issues_mentioning_the_file_open_the_workbench_search() -> None:
    window = Window()
    gel.issues_mentioning_file(window.host())
    assert window.workbench == [("ada/engine", 'search:repo:ada/engine is:issue "src/app.py"')]


def _pulls(monkeypatch: pytest.MonkeyPatch, pulls: list[dict[str, Any]]) -> list[Any]:
    asked: list[Any] = []
    monkeypatch.setattr(
        "quill.core.github.rest_transport.request_json",
        lambda _t, _m, path, query=None, **_k: (
            asked.append((path, query)) or SimpleNamespace(data=pulls)
        ),
    )
    return asked


def test_comment_on_line_posts_on_the_open_pull_request(monkeypatch) -> None:
    asked = _pulls(monkeypatch, [{"number": 3, "head": {"sha": SHA}}])
    monkeypatch.setattr(gel, "_ask_comment", lambda _host, _title: "Rename this")
    window = Window(selection="x")
    gel.comment_on_line(window.host())
    assert asked == [("/repos/ada/engine/pulls", {"state": "open", "head": "ada:feature"})]
    full_name, number, anchor, text, commit = window.provider_object.comments[0]
    assert (full_name, number, text, commit) == ("ada/engine", 3, "Rename this", SHA)
    assert anchor.describe() == "lines 4 to 6 of src/app.py"
    assert window.said == ["Commented on lines 4 to 6 of src/app.py in pull request 3."]


@pytest.mark.parametrize(
    ("pulls", "site_changes", "words"),
    [
        ([], {}, "No open pull request comes from the branch feature."),
        ([{"number": 3, "head": {"sha": "f" * 40}}], {}, "Push or pull first"),
        ([{"number": 3, "head": {"sha": SHA}}], {"changed": True}, "not committed"),
        ([{"number": 3, "head": {"sha": SHA}}], {"branch": ""}, "No branch is checked out"),
    ],
)
def test_comment_on_line_says_why_it_cannot(
    monkeypatch, _git, pulls: list[dict[str, Any]], site_changes: dict[str, Any], words: str
) -> None:
    from dataclasses import replace

    _git["site"] = replace(SITE, **site_changes)
    _pulls(monkeypatch, pulls)
    monkeypatch.setattr(gel, "_ask_comment", lambda *_a: pytest.fail("asked for a comment"))
    window = Window()
    gel.comment_on_line(window.host())
    assert words in window.said[0]
    assert window.provider_object.comments == []


def test_comment_on_line_waits_for_sign_in() -> None:
    window = Window()
    gel.comment_on_line(window.host(provider=lambda _retry: None))
    assert window.said == [] and window.provider_object.comments == []


def test_the_reference_at_the_cursor_opens_in_the_workbench(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "o/r")
    window = Window()
    gel.open_reference_at_cursor(window.host())
    reference, then = window.references[0]
    assert (reference.repository, reference.number, then) == ("o/r", 12, "filter:#12")


def test_a_person_opens_in_the_browser_and_no_reference_is_said(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "o/r")
    opened: list[str] = []
    monkeypatch.setattr(gel.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    window = Window()
    window.offset = len(window.text)
    gel.open_reference_at_cursor(window.host())
    assert opened == ["https://github.com/ada"]
    window = Window()
    window.text, window.offset = "nothing here", 3
    gel.open_reference_at_cursor(window.host())
    assert window.said == ["No GitHub reference at the cursor."]


def test_a_bare_number_outside_a_repository_says_how_to_write_it(monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "")
    window = Window(path="")
    gel.open_reference_at_cursor(window.host())
    assert "owner/name#number" in window.said[0]
