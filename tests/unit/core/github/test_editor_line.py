"""GitHub from the editor (GitHub PRD 22.3): tying a line to GitHub."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.github import editor_line as el
from quill.core.local_git import BlameInfo

SHA = "0123456789abcdef0123456789abcdef01234567"


def _checkout(tmp_path: Path, remote: str = "https://github.com/ada/engine.git") -> Path:
    git = tmp_path / ".git"
    git.mkdir()
    (git / "config").write_text(f'[remote "origin"]\n\turl = {remote}\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "my file.py"
    target.write_text("a\nb\nc\n", encoding="utf-8")
    return target


def _runner(
    *,
    head: str = SHA,
    branch: str = "feature",
    remote_branches: str = "  origin/feature\n",
    status: str = "",
) -> object:
    calls: list[list[str]] = []

    def run(argv: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(argv)
        args = argv[1:]
        if args == ["rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0 if head else 128, stdout=head + "\n")
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout=branch + "\n")
        if args[:3] == ["branch", "-r", "--contains"]:
            return SimpleNamespace(returncode=0, stdout=remote_branches)
        if args[:2] == ["status", "--porcelain"]:
            return SimpleNamespace(returncode=0, stdout=status)
        raise AssertionError(argv)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_locate_ties_the_lines_to_the_commit(tmp_path: Path) -> None:
    site = el.locate(_checkout(tmp_path), 3, 5, runner=_runner())
    assert (site.repository, site.path, site.commit) == ("ada/engine", "src/my file.py", SHA)
    assert (site.first, site.last, site.branch, site.pushed, site.changed) == (
        3,
        5,
        "feature",
        True,
        False,
    )
    assert site.lines == "lines 3 to 5"


def test_the_permalink_names_the_commit_and_encodes_the_path(tmp_path: Path) -> None:
    site = el.locate(_checkout(tmp_path), 7, 0, runner=_runner())
    assert el.permalink(site) == f"https://github.com/ada/engine/blob/{SHA}/src/my%20file.py#L7"
    ranged = el.LineSite("ada/engine", str(tmp_path), "src/my file.py", SHA, 2, 4)
    assert el.permalink(ranged).endswith("#L2-L4")


@pytest.mark.parametrize(
    ("kwargs", "words"),
    [
        ({"remote_branches": ""}, "not on GitHub yet"),
        ({"status": " M src/my file.py\n"}, "not committed"),
        ({}, ""),
    ],
)
def test_the_caveat_says_when_the_link_may_not_match(
    tmp_path: Path, kwargs: dict[str, str], words: str
) -> None:
    site = el.locate(_checkout(tmp_path), 1, runner=_runner(**kwargs))
    if words:
        assert words in el.caveat(site)
    else:
        assert el.caveat(site) == ""


def test_a_detached_head_has_no_branch(tmp_path: Path) -> None:
    site = el.locate(_checkout(tmp_path), 1, runner=_runner(branch="HEAD"))
    assert site.branch == ""
    assert el.open_pulls_query(site) is None


@pytest.mark.parametrize(
    ("setup", "words"),
    [
        ("unsaved", "Save this document"),
        ("no_git", "not in a git repository"),
        ("not_github", "no GitHub remote"),
        ("no_commit", "no commits yet"),
    ],
)
def test_locate_says_why_a_line_cannot_be_tied(tmp_path: Path, setup: str, words: str) -> None:
    runner = _runner()
    if setup == "unsaved":
        target: str | Path = ""
    elif setup == "no_git":
        target = tmp_path / "loose.txt"
        target.write_text("x", encoding="utf-8")
    elif setup == "not_github":
        target = _checkout(tmp_path, "https://gitlab.com/ada/engine.git")
    else:
        target = _checkout(tmp_path)
        runner = _runner(head="")
    with pytest.raises(el.EditorLineError, match=words):
        el.locate(target, 1, runner=runner)


def test_blame_sentence_reads_like_a_sentence() -> None:
    info = BlameInfo(SHA, "Ada Lovelace", "1772496000", "Fix the parser")
    assert el.blame_sentence(info) == (
        "Changed by Ada Lovelace on 3 March 2026: Fix the parser (0123456)."
    )
    uncommitted = BlameInfo("0" * 40, "Not Committed Yet", "0", "")
    assert "Not committed yet" in el.blame_sentence(uncommitted)


def test_the_merged_pull_request_is_the_one_that_brought_the_line() -> None:
    answer = [
        {"number": 9, "html_url": "https://github.com/a/b/pull/9", "merged_at": None},
        {"number": 4, "html_url": "https://github.com/a/b/pull/4", "merged_at": "2026-01-01"},
    ]
    assert el.first_pull(answer) == (4, "https://github.com/a/b/pull/4")
    assert el.first_pull([]) is None
    assert el.first_pull({"message": "Not Found"}) is None
    assert el.commit_pulls_path("a/b", SHA) == f"/repos/a/b/commits/{SHA}/pulls"


def test_issue_draft_quotes_the_selection_with_its_link(tmp_path: Path) -> None:
    site = el.locate(_checkout(tmp_path), 2, 3, runner=_runner())
    title, body = el.issue_draft(site, "  total = add(a, b)\r\nreturn total\r\n")
    assert title == "my file.py, lines 2 to 3: total = add(a, b)"
    assert body.startswith(
        f"In [src/my file.py, lines 2 to 3]({el.permalink(site)}):\n\n```python\n"
    )
    assert "  total = add(a, b)\nreturn total\n```" in body


def test_issue_draft_fences_around_a_fence_and_shortens_long_selections(tmp_path: Path) -> None:
    site = el.locate(_checkout(tmp_path), 1, 60, runner=_runner())
    selection = "```\ncode\n```\n" + "\n".join(f"line {n}" for n in range(60))
    _title, body = el.issue_draft(site, selection)
    assert "````python" in body
    assert "(23 more lines at the link.)" in body


def test_issues_mentioning_the_file_search_its_path() -> None:
    site = el.LineSite("a/b", "/r", "docs/guide.md", SHA, 1, 1)
    assert el.issues_mentioning_query(site) == 'repo:a/b is:issue "docs/guide.md"'


def test_the_open_pull_request_and_the_line_anchor() -> None:
    site = el.LineSite("ada/engine", "/r", "src/x.py", SHA, 4, 6, branch="fix/parser")
    assert el.open_pulls_query(site) == (
        "/repos/ada/engine/pulls",
        {"state": "open", "head": "ada:fix/parser"},
    )
    assert el.line_anchor(site).payload() == {
        "path": "src/x.py",
        "line": 6,
        "side": "RIGHT",
        "start_line": 4,
        "start_side": "RIGHT",
    }
    assert el.line_anchor(site).describe() == "lines 4 to 6 of src/x.py"
    one = el.LineSite("ada/engine", "/r", "src/x.py", SHA, 4, 4)
    assert el.line_anchor(one).payload() == {"path": "src/x.py", "line": 4, "side": "RIGHT"}


def test_references_are_found_and_ordinary_words_are_not() -> None:
    text = (
        "See #42 and ada/engine#7, thanks @grace-h. Fixed in 1a2b3c4d. "
        "Not refs: defaced, a@b.com, C#1x, path/to#3x, @-bad"
    )
    found = el.references_in(text, "ada/engine")
    assert [(r.kind, r.describe()) for r in found] == [
        ("item", "ada/engine#42"),
        ("item", "ada/engine#7"),
        ("person", "@grace-h"),
        ("commit", "commit 1a2b3c4"),
    ]


def test_reference_at_and_its_url() -> None:
    text = "Closes #12 for @ada"
    ref = el.reference_at(text, text.index("12"), "o/r")
    assert ref is not None and ref.number == 12
    assert el.reference_url(ref) == "https://github.com/o/r/issues/12"
    person = el.reference_at(text, len(text), "o/r")
    assert person is not None and el.reference_url(person) == "https://github.com/ada"
    assert el.reference_at(text, 2, "o/r") is None
    unknown = el.reference_at("#5", 1, "")
    assert unknown is not None and el.reference_url(unknown) == ""
