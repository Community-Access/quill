"""A repository's wiki pages, edited here and published with git (complete.md 1.3, GX12).

GitHub has no REST or GraphQL API for wiki pages. A wiki is its own git
repository, ``owner/name.wiki``, one file per page, so this module works on a
local copy of it with the same git QUILL clones with
(:mod:`quill.core.github.clone`):

* :func:`fetch_copy` clones the wiki into QUILL's own folder for it the first
  time, and brings it up to date (``git pull --ff-only``) after that. The
  token travels in git's environment, never in a URL or ``.git/config``.
* :func:`list_pages` lists the pages: each file's title is its name with
  hyphens read as spaces, as GitHub shows it; Home comes first.
* :func:`new_page` makes the file for a new page, named as GitHub names one.
* :func:`changed_pages` says which pages differ from what GitHub has.
* :func:`publish` commits every changed page with the message given and
  pushes. When someone else changed the wiki meanwhile, it replays the commit
  on top of theirs (``git pull --rebase``) and pushes again; a page both
  changed is refused plainly, the rebase undone, and the local edits kept.
  Nothing is ever forced.

The runner is injected (``run_subprocess_safely`` in the app, a fake in the
tests), as in :mod:`quill.core.local_git`. wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.clone import (
    CloneError,
    CloneSource,
    clone_environment,
    clone_repository,
    parse_clone_source,
)

__all__ = [
    "PAGE_SUFFIXES",
    "WikiPage",
    "WikiPagesError",
    "changed_pages",
    "fetch_copy",
    "list_pages",
    "new_page",
    "page_file_name",
    "publish",
    "wiki_folder",
    "wiki_source",
]

#: The markup GitHub renders a wiki page from; any other file is not a page.
PAGE_SUFFIXES = (
    ".md",
    ".markdown",
    ".mediawiki",
    ".wiki",
    ".textile",
    ".rdoc",
    ".org",
    ".creole",
    ".asciidoc",
    ".adoc",
    ".rst",
    ".pod",
)
_TIMEOUT = 120.0
#: Characters GitHub will not put in a page's file name.
_BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_NO_WIKI_REPO = (
    "GitHub makes a wiki's git repository only when its first page is saved on the web. "
    "Open the wiki on GitHub, save its Home page once, then try again."
)

Runner = Callable[..., Any]


class WikiPagesError(CodedError):
    """A wiki fetch, page or publish could not be done; the message is safe to speak."""

    code = "QUILL-GITHUB-WIKI-PAGES"


@dataclass(frozen=True, slots=True)
class WikiPage:
    """One page: its file and the title GitHub shows for it."""

    path: Path
    title: str

    @property
    def label(self) -> str:
        return f"{self.title} ({self.path.name})"


def wiki_source(repository: str) -> CloneSource:
    """The wiki's own git repository, ``owner/name.wiki``, on github.com."""
    try:
        return parse_clone_source(f"{repository.strip()}.wiki")
    except CloneError as exc:
        raise WikiPagesError(f"{repository} is not owner/name.") from exc


def wiki_folder(root: Path | str, repository: str) -> Path:
    """Where QUILL keeps *repository*'s wiki: ``root/owner/name.wiki``."""
    owner, _slash, name = repository.strip().partition("/")
    if not owner or not name or "/" in name or ".." in repository:
        raise WikiPagesError(f"{repository} is not owner/name.")
    return Path(root) / owner / f"{name}.wiki"


def _git(runner: Runner, git: Path | str, folder: Path, *args: str, env: Any = None) -> Any:
    kwargs: dict[str, Any] = {"cwd": str(folder), "timeout_seconds": _TIMEOUT}
    if env is not None:
        kwargs["env"] = env
    return runner([str(git), *args], **kwargs)


def _said(result: Any) -> str:
    from quill.core.github.clone import _git_said

    return _git_said(str(getattr(result, "stderr", "") or getattr(result, "stdout", "") or ""))


def _ok(result: Any) -> bool:
    return int(getattr(result, "returncode", 1)) == 0


def fetch_copy(
    git: Path | str, repository: str, folder: Path | str, *, token: str, runner: Runner
) -> str:
    """Clone the wiki into *folder*, or bring the copy there up to date; the sentence to say."""
    source, folder = wiki_source(repository), Path(folder)
    if (folder / ".git").is_dir():
        env = clone_environment(token, source)
        result = _git(runner, git, folder, "pull", "--ff-only", env=env)
        if not _ok(result):
            said = _said(result).rstrip(".")
            raise WikiPagesError(
                f"Could not bring {repository}'s wiki up to date. Git said: {said}. "
                "Your copy is unchanged; Publish Wiki Changes... sends your edits first."
            )
        return f"{repository}'s wiki is up to date in {folder}."
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        clone_repository(git, source, folder, token=token, runner=runner)
    except CloneError as exc:
        text = str(exc)
        if "not found" in text.lower():
            raise WikiPagesError(_NO_WIKI_REPO) from exc
        raise WikiPagesError(text.split("] ", 1)[-1]) from exc
    return f"Copied {repository}'s wiki to {folder}."


def _title(path: Path) -> str:
    return path.stem.replace("-", " ")


def list_pages(folder: Path | str) -> list[WikiPage]:
    """Every page in the copy, Home first, then by title; ``.git`` and sidebars' folders kept."""
    base = Path(folder)
    if not base.is_dir():
        return []
    found = [
        WikiPage(path, _title(path))
        for path in base.rglob("*")
        if path.is_file()
        and ".git" not in path.relative_to(base).parts
        and path.suffix.lower() in PAGE_SUFFIXES
    ]
    return sorted(found, key=lambda p: (p.title.casefold() != "home", p.title.casefold()))


def page_file_name(title: str, suffix: str = ".md") -> str:
    """The file GitHub keeps a page titled *title* in: spaces as hyphens."""
    cleaned = _BAD_NAME.sub("", title).strip()
    name = re.sub(r"\s+", "-", cleaned).strip(".-")
    if not name:
        raise WikiPagesError("A page needs a title with at least one letter or digit.")
    return name + suffix


def new_page(folder: Path | str, title: str, text: str = "") -> Path:
    """The new page's file, written with *text* (its title as a heading when empty)."""
    base = Path(folder)
    if not (base / ".git").is_dir():
        raise WikiPagesError("Fetch the wiki first: Edit Wiki Pages... copies it here.")
    path = base / page_file_name(title)
    existing = {p.path.stem.casefold() for p in list_pages(base)}
    if path.stem.casefold() in existing:
        raise WikiPagesError(f"The wiki already has a page called {title}.")
    path.write_text(text or f"# {title.strip()}\n\n", encoding="utf-8", newline="\n")
    return path


def changed_pages(git: Path | str, folder: Path | str, *, runner: Runner) -> list[str]:
    """The files that differ from the last fetch, as ``git status`` names them."""
    result = _git(runner, git, Path(folder), "status", "--porcelain", "--untracked-files=all")
    if not _ok(result):
        raise WikiPagesError(f"Could not read the wiki's changes. Git said: {_said(result)}")
    names = []
    for line in str(getattr(result, "stdout", "") or "").splitlines():
        name = line[3:].strip().strip('"')
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        if name:
            names.append(name)
    return names


def publish(
    git: Path | str,
    repository: str,
    folder: Path | str,
    message: str,
    *,
    token: str,
    runner: Runner,
) -> str:
    """Commit every changed page and push it to GitHub; the sentence to say.

    Never forces: when GitHub has changes this copy lacks, the commit is
    replayed on top of them first, and a page both sides changed is refused.
    """
    folder, source = Path(folder), wiki_source(repository)
    pages = changed_pages(git, folder, runner=runner)
    waiting = _unpublished(git, folder, runner)
    if not pages and not waiting:
        return f"Nothing to publish: no page of {repository}'s wiki has changed here."
    text = message.strip() or f"Update {', '.join(pages[:3])}"
    for step in (("add", "--all"), ("commit", "-m", text)) if pages else ():
        result = _git(runner, git, folder, *step)
        if not _ok(result):
            raise WikiPagesError(f"Could not commit the pages. Git said: {_said(result)}")
    env = clone_environment(token, source)
    pushed = _git(runner, git, folder, "push", "origin", "HEAD", env=env)
    if not _ok(pushed):
        rebased = _git(runner, git, folder, "pull", "--rebase", env=env)
        if not _ok(rebased):
            _git(runner, git, folder, "rebase", "--abort")
            raise WikiPagesError(
                "Someone else changed the same lines of the wiki since you fetched it. "
                "Your edits are committed here but not published; compare them with "
                "GitHub's page, then publish again."
            )
        pushed = _git(runner, git, folder, "push", "origin", "HEAD", env=env)
        if not _ok(pushed):
            raise WikiPagesError(
                f"GitHub refused the wiki change. Git said: {_said(pushed)}. "
                "Your edits are committed here and nothing was forced."
            )
    if not pages:
        return f"Published the wiki changes committed earlier to {repository}'s wiki."
    count = len(pages)
    noun = "page" if count == 1 else "pages"
    return f"Published {count} {noun} to {repository}'s wiki: {', '.join(pages[:5])}."


def _unpublished(git: Path | str, folder: Path, runner: Runner) -> int:
    """How many commits here GitHub does not have yet (0 when git cannot say)."""
    result = _git(runner, git, folder, "rev-list", "--count", "@{upstream}..HEAD")
    try:
        return int(str(getattr(result, "stdout", "") or "0").strip() or "0") if _ok(result) else 0
    except ValueError:
        return 0
