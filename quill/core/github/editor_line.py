"""GitHub from the editor, where the code is (GitHub PRD 22.3, GH-R-084).

The editor commands in both QUILL and QUILL Lite that answer a question about
the line in front of you without opening the Workbench:

- **Copy GitHub Link to This Line** (or the selected lines), a permalink to
  the commit, so the link keeps pointing at the same text after the file
  changes: :func:`permalink`.
- **Who Changed This Line?**, the last commit, author and date
  (:func:`blame_sentence`, from :func:`quill.core.local_git.blame_line`), and
  **Open the Pull Request for This Line**, the pull request that brought that
  commit (:func:`commit_pulls_path` / :func:`first_pull`).
- **Open This Line on GitHub**: the permalink, in the browser.
- **New Issue from Selection...**: a title and a body quoting the selection
  with its permalink (:func:`issue_draft`).
- **Issues Mentioning This File**: the search the Workbench opens on
  (:func:`issues_mentioning_query`).
- **Comment on This Line in the Open Pull Request**: the pull request whose
  branch is checked out here (:func:`open_pulls_query`, :func:`line_anchor`).
- **References in any document** (``#42``, ``owner/name#42``, ``@person``, a
  commit hash) are recognised by :func:`references_in` and
  :func:`reference_at`, so Alt+Enter on one can open its Properties.

Everything that reads the working copy goes through an injected ``runner``
(``safe_subprocess`` in the app, a fake in tests), exactly as
:mod:`quill.core.local_git` does; nothing here talks to the network. The
caller sends the API paths this module builds. wx-free, strict-typed.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.diff_lines import LineCommentAnchor
from quill.core.github.local_repo import detect_github_repo
from quill.core.local_git import BlameInfo
from quill.core.vault.sync import Runner

__all__ = [
    "EditorLineError",
    "LineSite",
    "ShortReference",
    "blame_sentence",
    "caveat",
    "commit_pulls_path",
    "find_root",
    "first_pull",
    "issue_draft",
    "issues_mentioning_query",
    "line_anchor",
    "locate",
    "open_pulls_query",
    "permalink",
    "reference_at",
    "reference_url",
    "references_in",
]

_TIMEOUT = 15.0
#: The longest selection quoted into a new issue, in lines. Past it the body
#: says how many lines were left out; the permalink still covers them all.
QUOTE_LIMIT = 40
#: Fence languages for the quoted selection, by file extension.
_FENCE_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".json": "json",
    ".md": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".html": "html",
    ".css": "css",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "bash",
    ".ps1": "powershell",
    ".toml": "toml",
    ".xml": "xml",
    ".sql": "sql",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
}


class EditorLineError(CodedError):
    """The line cannot be tied to GitHub: no checkout, no GitHub remote, no commit."""

    code = "QUILL-GITHUB-EDITOR-LINE"


@dataclass(frozen=True, slots=True)
class LineSite:
    """Where a line of the open document is on GitHub.

    ``commit`` is the commit checked out (``HEAD``); ``pushed`` says whether a
    remote branch holds it, so a link to it will open; ``changed`` says the
    file has changes not in that commit, so the line numbers on GitHub may not
    match the editor's.
    """

    repository: str
    root: str
    path: str
    commit: str
    first: int
    last: int
    branch: str = ""
    pushed: bool = True
    changed: bool = False

    @property
    def lines(self) -> str:
        """``line 12`` or ``lines 12 to 15``, for a sentence."""
        if self.last > self.first:
            return f"lines {self.first} to {self.last}"
        return f"line {self.first}"


def _git(root: str, runner: Runner, *args: str) -> tuple[int, str]:
    raw = runner(["git", *args], cwd=root, timeout_seconds=_TIMEOUT)
    return int(getattr(raw, "returncode", 1)), str(getattr(raw, "stdout", "") or "")


def find_root(file_path: str | Path) -> Path | None:
    """The working tree that holds *file_path*: the nearest folder with ``.git``."""
    start = Path(file_path)
    folder = start if start.is_dir() else start.parent
    for candidate in (folder, *folder.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def locate(file_path: str | Path, first: int, last: int = 0, *, runner: Runner) -> LineSite:
    """Tie lines *first* to *last* (1-based) of *file_path* to GitHub.

    Raises :class:`EditorLineError` with the sentence to say when the file is
    unsaved, outside a git checkout, in a checkout with no GitHub remote, or in
    one with no commit yet.
    """
    if not str(file_path):
        raise EditorLineError("Save this document in a GitHub repository first.")
    root = find_root(file_path)
    if root is None:
        raise EditorLineError("This file is not in a git repository.")
    repository = detect_github_repo(root)
    if not repository:
        raise EditorLineError("This repository has no GitHub remote named origin.")
    try:
        relative = Path(file_path).resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise EditorLineError("This file is not inside its repository's folder.") from exc
    path = PurePosixPath(*relative.parts).as_posix()
    code, out = _git(str(root), runner, "rev-parse", "HEAD")
    commit = out.strip()
    if code != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise EditorLineError("This repository has no commits yet.")
    _code, out = _git(str(root), runner, "rev-parse", "--abbrev-ref", "HEAD")
    branch = out.strip()
    branch = "" if branch == "HEAD" else branch
    code, out = _git(str(root), runner, "branch", "-r", "--contains", commit)
    pushed = code == 0 and bool(out.strip())
    code, out = _git(str(root), runner, "status", "--porcelain", "--", path)
    changed = code == 0 and bool(out.strip())
    first = max(1, int(first))
    last = max(first, int(last or first))
    return LineSite(repository, str(root), path, commit, first, last, branch, pushed, changed)


def permalink(site: LineSite) -> str:
    """The link to *site*'s lines at its commit, which never drifts."""
    anchor = f"#L{site.first}" + (f"-L{site.last}" if site.last > site.first else "")
    return (
        f"https://github.com/{site.repository}/blob/{site.commit}/"
        f"{quote(site.path, safe='/')}{anchor}"
    )


def caveat(site: LineSite) -> str:
    """One sentence when the link may not show what the editor shows, else ``""``."""
    if not site.pushed:
        return "This commit is not on GitHub yet, so the link will not open until you push."
    if site.changed:
        return "This file has changes that are not committed, so the line on GitHub may differ."
    return ""


def blame_sentence(info: BlameInfo) -> str:
    """``Changed by Ada on 3 March 2026: Fix the parser (1a2b3c4).``"""
    if set(info.commit_sha) == {"0"}:
        return "Not committed yet: this line was changed on this computer."
    when = ""
    try:
        moment = dt.datetime.fromtimestamp(int(info.date), tz=dt.UTC)
        when = f" on {moment.day} {moment:%B %Y}"
    except (TypeError, ValueError, OverflowError, OSError):
        when = f" on {info.date}" if info.date else ""
    summary = f": {info.summary}" if info.summary else ""
    return f"Changed by {info.author or 'someone'}{when}{summary} ({info.commit_sha[:7]})."


def commit_pulls_path(repository: str, commit: str) -> str:
    """The REST path listing the pull requests that brought *commit*."""
    return f"/repos/{repository}/commits/{commit}/pulls"


def first_pull(answer: object) -> tuple[int, str] | None:
    """The pull request to open from a :func:`commit_pulls_path` answer.

    GitHub lists merged and open pull requests; a merged one is the one that
    brought the line, so it wins. ``None`` when there is none.
    """
    if not isinstance(answer, Sequence) or isinstance(answer, str):
        return None
    pulls = [item for item in answer if isinstance(item, Mapping)]
    pulls.sort(key=lambda item: 0 if item.get("merged_at") else 1)
    for item in pulls:
        number = item.get("number")
        url = item.get("html_url")
        if isinstance(number, int) and not isinstance(number, bool) and isinstance(url, str):
            return number, url
    return None


def issue_draft(site: LineSite, selection: str) -> tuple[str, str]:
    """A title and a Markdown body for an issue about the selected text."""
    text = selection.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    lines = text.split("\n") if text else []
    first_words = next((line.strip() for line in lines if line.strip()), "")
    name = PurePosixPath(site.path).name
    title = f"{name}, {site.lines}"
    if first_words:
        title = f"{title}: {first_words[:60]}"
    fence_language = _FENCE_LANGUAGES.get(PurePosixPath(site.path).suffix.casefold(), "")
    shown = lines[:QUOTE_LIMIT]
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=2)
    fence = "`" * max(3, longest + 1)
    body = [f"In [{site.path}, {site.lines}]({permalink(site)}):", ""]
    if shown:
        body += [f"{fence}{fence_language}", *shown, fence]
    if len(lines) > QUOTE_LIMIT:
        body += ["", f"({len(lines) - QUOTE_LIMIT} more lines at the link.)"]
    return title, "\n".join(body) + "\n"


def issues_mentioning_query(site: LineSite) -> str:
    """The issue search for *site*'s file: its path, in quotes, in this repository."""
    return f'repo:{site.repository} is:issue "{site.path}"'


def open_pulls_query(site: LineSite) -> tuple[str, dict[str, str]] | None:
    """The REST path and query for the open pull request from *site*'s branch.

    ``None`` when no branch is checked out (a detached head has no pull
    request to comment on).
    """
    if not site.branch:
        return None
    owner = site.repository.split("/", 1)[0]
    return (
        f"/repos/{site.repository}/pulls",
        {"state": "open", "head": f"{owner}:{site.branch}"},
    )


def line_anchor(site: LineSite) -> LineCommentAnchor:
    """Where a comment on *site*'s lines goes, on the pull request's new side."""
    if site.last > site.first:
        return LineCommentAnchor(site.path, site.last, "RIGHT", site.first, "RIGHT")
    return LineCommentAnchor(site.path, site.last)


# ---------------------------------------------------------------------------
# References in a document
# ---------------------------------------------------------------------------

_REFERENCE = re.compile(
    r"(?<![\w/#@.-])"
    r"(?:"
    r"(?P<repo>[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100})#(?P<rnum>[1-9][0-9]{0,9})"
    r"|(?:GH-|#)(?P<num>[1-9][0-9]{0,9})"
    r"|@(?P<login>[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})(?![\w/-])"
    r"|(?P<sha>(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40})"
    r")"
    r"(?![\w])"
)


@dataclass(frozen=True, slots=True)
class ShortReference:
    """A GitHub reference written in a document: ``#42``, ``@ada``, a commit."""

    kind: str  # "item" (an issue or pull request), "person" or "commit"
    text: str
    start: int
    end: int
    repository: str = ""
    number: int = 0
    login: str = ""
    sha: str = ""

    def describe(self) -> str:
        if self.kind == "item":
            return f"{self.repository}#{self.number}" if self.repository else f"#{self.number}"
        if self.kind == "person":
            return f"@{self.login}"
        return f"commit {self.sha[:7]}"


def references_in(text: str, repository: str = "") -> list[ShortReference]:
    """Every GitHub reference in *text*; bare ``#42`` belongs to *repository*.

    Commit hashes need a digit and a letter, so ordinary words such as
    "defaced" are not taken for one; an e-mail address is not a person.
    """
    found: list[ShortReference] = []
    for match in _REFERENCE.finditer(text):
        start, end = match.span()
        if match.group("repo"):
            found.append(
                ShortReference(
                    "item",
                    match.group(0),
                    start,
                    end,
                    repository=match.group("repo"),
                    number=int(match.group("rnum")),
                )
            )
        elif match.group("num"):
            found.append(
                ShortReference(
                    "item", match.group(0), start, end, repository, number=int(match.group("num"))
                )
            )
        elif match.group("login"):
            found.append(
                ShortReference("person", match.group(0), start, end, login=match.group("login"))
            )
        elif match.group("sha"):
            found.append(
                ShortReference("commit", match.group(0), start, end, repository, sha=match.group(0))
            )
    return found


def reference_at(text: str, offset: int, repository: str = "") -> ShortReference | None:
    """The reference that *offset* is on (or just after), or ``None``."""
    for reference in references_in(text, repository):
        if reference.start <= offset <= reference.end:
            return reference
    return None


def reference_url(reference: ShortReference) -> str:
    """The page a reference names on GitHub, or ``""`` when its repository is unknown."""
    if reference.kind == "person":
        return f"https://github.com/{reference.login}"
    if not reference.repository:
        return ""
    if reference.kind == "item":
        # GitHub sends /issues/N on to /pull/N when N is a pull request.
        return f"https://github.com/{reference.repository}/issues/{reference.number}"
    return f"https://github.com/{reference.repository}/commit/{reference.sha}"
