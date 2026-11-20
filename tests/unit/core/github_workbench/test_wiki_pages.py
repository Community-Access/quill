"""Wiki pages through the wiki's git repository: fetch, list, new page, publish (GX12)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import wiki_pages as wp

TOKEN = "ghp_" + "x" * 36


class FakeGit:
    """Answers git by its first argument; records argv, folder and whether a token was sent."""

    def __init__(self, answers: dict[str, list[tuple[int, str, str]]] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[tuple[list[str], str, bool]] = []

    def __call__(self, argv: list[str], *, cwd: str, timeout_seconds: float, env: Any = None):
        sent = bool(env) and any(TOKEN in str(v) or "basic" in str(v) for v in env.values())
        self.calls.append((list(argv[1:]), cwd, sent))
        step = argv[1]
        if step == "clone":
            target = Path(argv[-1])
            (target / ".git").mkdir(parents=True)
            (target / "Home.md").write_text("# Home\n", encoding="utf-8")
            (target / "Getting-Started.md").write_text("Start\n", encoding="utf-8")
            (target / "notes.txt").write_text("not a page\n", encoding="utf-8")
        queue = self.answers.get(step) or []
        code, out, err = queue.pop(0) if queue else (0, "", "")
        return SimpleNamespace(returncode=code, stdout=out, stderr=err)

    def steps(self) -> list[str]:
        return [argv[0] for argv, _cwd, _sent in self.calls]


def test_the_wiki_folder_is_per_repository_and_refuses_a_bad_name(tmp_path: Path) -> None:
    assert wp.wiki_folder(tmp_path, "o/r") == tmp_path / "o" / "r.wiki"
    assert wp.wiki_source("o/r").url == "https://github.com/o/r.wiki.git"
    for bad in ("o", "o/r/x", "../r"):
        with pytest.raises(wp.WikiPagesError):
            wp.wiki_folder(tmp_path, bad)


def test_first_fetch_clones_with_the_token_in_the_environment_only(tmp_path: Path) -> None:
    git, folder = FakeGit(), tmp_path / "o" / "r.wiki"
    said = wp.fetch_copy("git", "o/r", folder, token=TOKEN, runner=git)
    assert said == f"Copied o/r's wiki to {folder}."
    argv, _cwd, sent = git.calls[0]
    assert argv[0] == "clone" and sent and all(TOKEN not in a for a in argv)
    titles = [page.title for page in wp.list_pages(folder)]
    assert titles == ["Home", "Getting Started"]  # Home first; notes.txt is not a page


def test_a_later_fetch_pulls_fast_forward_only(tmp_path: Path) -> None:
    folder = tmp_path / "w"
    (folder / ".git").mkdir(parents=True)
    git = FakeGit()
    assert "up to date" in wp.fetch_copy("git", "o/r", folder, token=TOKEN, runner=git)
    assert git.calls[0][0] == ["pull", "--ff-only"] and git.calls[0][2]


def test_a_wiki_with_no_git_repository_yet_says_to_save_home_on_the_web(tmp_path: Path) -> None:
    git = FakeGit({"clone": [(128, "", "fatal: repository 'x' not found")]})

    def runner(argv: list[str], **kw: Any) -> Any:
        if argv[1] == "clone":
            return SimpleNamespace(returncode=128, stdout="", stderr="fatal: repository not found")
        return git(argv, **kw)

    with pytest.raises(wp.WikiPagesError, match="first page is saved on the web"):
        wp.fetch_copy("git", "o/r", tmp_path / "w", token=TOKEN, runner=runner)


def test_a_new_page_is_named_as_github_names_one_and_never_twice(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    path = wp.new_page(tmp_path, "How to: Build?")
    assert path.name == "How-to-Build.md"
    assert path.read_text(encoding="utf-8").startswith("# How to: Build?")
    with pytest.raises(wp.WikiPagesError, match="already has a page"):
        wp.new_page(tmp_path, "how to build")
    with pytest.raises(wp.WikiPagesError):
        wp.page_file_name("???")


def test_a_new_page_needs_the_copy_first(tmp_path: Path) -> None:
    with pytest.raises(wp.WikiPagesError, match="Fetch the wiki first"):
        wp.new_page(tmp_path, "Page")


def test_publish_commits_the_changed_pages_and_pushes(tmp_path: Path) -> None:
    git = FakeGit({"status": [(0, " M Home.md\n?? New-Page.md\n", "")]})
    said = wp.publish("git", "o/r", tmp_path, "Fix the home page", token=TOKEN, runner=git)
    assert said == "Published 2 pages to o/r's wiki: Home.md, New-Page.md."
    assert git.steps() == ["status", "rev-list", "add", "commit", "push"]
    assert ["commit", "-m", "Fix the home page"] in [c[0] for c in git.calls]
    push = git.calls[-1]
    assert push[0] == ["push", "origin", "HEAD"] and push[2]


def test_nothing_to_publish_says_so_and_sends_nothing(tmp_path: Path) -> None:
    git = FakeGit({"status": [(0, "", "")], "rev-list": [(0, "0\n", "")]})
    said = wp.publish("git", "o/r", tmp_path, "x", token=TOKEN, runner=git)
    assert said.startswith("Nothing to publish")
    assert "push" not in git.steps()


def test_a_refused_push_is_replayed_on_top_never_forced(tmp_path: Path) -> None:
    git = FakeGit({
        "status": [(0, " M Home.md\n", "")],
        "push": [(1, "", "rejected (fetch first)"), (0, "", "")],
    })
    wp.publish("git", "o/r", tmp_path, "x", token=TOKEN, runner=git)
    assert git.steps()[-3:] == ["push", "pull", "push"]
    assert all("--force" not in argv and "-f" not in argv for argv, _c, _s in git.calls)


def test_a_conflict_undoes_the_rebase_and_keeps_the_edits(tmp_path: Path) -> None:
    git = FakeGit({
        "status": [(0, " M Home.md\n", "")],
        "push": [(1, "", "rejected")],
        "pull": [(1, "", "CONFLICT (content): Merge conflict in Home.md")],
    })
    with pytest.raises(wp.WikiPagesError, match="same lines"):
        wp.publish("git", "o/r", tmp_path, "x", token=TOKEN, runner=git)
    assert git.calls[-1][0] == ["rebase", "--abort"]


def test_commits_left_from_a_refused_publish_are_pushed_next_time(tmp_path: Path) -> None:
    git = FakeGit({"status": [(0, "", "")], "rev-list": [(0, "1\n", "")]})
    said = wp.publish("git", "o/r", tmp_path, "x", token=TOKEN, runner=git)
    assert "committed earlier" in said and "commit" not in git.steps()
