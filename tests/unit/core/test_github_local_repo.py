"""Local git sync: owner/repo detection from the document's own checkout."""

from __future__ import annotations

from pathlib import Path

from quill.core.github.local_repo import detect_github_repo, parse_github_remote_url


def test_parse_github_remote_url_covers_the_three_shapes() -> None:
    assert parse_github_remote_url("https://github.com/o/r.git") == "o/r"
    assert parse_github_remote_url("https://github.com/o/r") == "o/r"
    assert parse_github_remote_url("git@github.com:o/r.git") == "o/r"
    assert parse_github_remote_url("ssh://git@github.com/o/r") == "o/r"
    assert parse_github_remote_url("https://gitlab.com/o/r.git") == ""
    assert parse_github_remote_url("not a url") == ""


def _write_repo(root: Path, url: str) -> Path:
    git = root / ".git"
    git.mkdir(parents=True)
    (git / "config").write_text(
        "[core]\n\trepositoryformatversion = 0\n"
        '[remote "origin"]\n'
        f"\turl = {url}\n"
        "\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
        '[remote "upstream"]\n'
        "\turl = https://github.com/someone/else.git\n",
        encoding="utf-8",
    )
    return root


def test_detects_origin_from_a_nested_document_path(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path / "clone", "git@github.com:Community-Access/QUILL.git")
    nested = repo / "docs" / "guide"
    nested.mkdir(parents=True)
    document = nested / "notes.md"
    document.write_text("hi", encoding="utf-8")
    # origin (not upstream) wins, from any depth.
    assert detect_github_repo(document) == "Community-Access/QUILL"


def test_non_repo_and_non_github_return_empty(tmp_path: Path) -> None:
    plain = tmp_path / "plain" / "doc.md"
    plain.parent.mkdir(parents=True)
    plain.write_text("hi", encoding="utf-8")
    assert detect_github_repo(plain) == ""
    assert detect_github_repo(None) == ""

    gitlab = _write_repo(tmp_path / "gl", "https://gitlab.com/o/r.git")
    assert detect_github_repo(gitlab / "x.md") == ""


def test_worktree_gitdir_pointer_is_followed(tmp_path: Path) -> None:
    main = _write_repo(tmp_path / "main", "https://github.com/o/r.git")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    linked = main / ".git" / "worktrees" / "wt"
    linked.mkdir(parents=True)
    (worktree / ".git").write_text(f"gitdir: {linked}\n", encoding="utf-8")
    assert detect_github_repo(worktree / "file.md") == "o/r"
