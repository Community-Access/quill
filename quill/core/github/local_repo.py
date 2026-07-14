"""Local Git sync: derive ``owner/repo`` from the document's own git checkout.

The Unified GitHub Management review's "Local Git Sync" item: when the current
document lives inside a git working tree whose ``origin`` remote points at
GitHub, the GitHub Items viewer can prefill that repository — no retyping —
even when the file was opened from disk rather than through QUILL's
Open-from-GitHub flow (which already tracks its own origins).

Pure file reading: walks up from the document to the nearest ``.git`` (a
directory, or a worktree's ``gitdir:`` pointer file), parses ``config`` for
the ``origin`` URL, and normalizes the three GitHub URL shapes
(``https://github.com/o/r[.git]``, ``git@github.com:o/r[.git]``,
``ssh://git@github.com/o/r``). No subprocess, no network. wx-free; strict-typed.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["detect_github_repo", "parse_github_remote_url"]

_URL_PATTERNS = (
    re.compile(
        r"^https?://(?:www\.)?github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$"
    ),
    re.compile(r"^git@github\.com:(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?$"),
    re.compile(r"^ssh://git@github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$"),
)


def parse_github_remote_url(url: str) -> str:
    """Return ``owner/repo`` for a GitHub remote URL, or ``""`` for anything else."""
    candidate = url.strip()
    for pattern in _URL_PATTERNS:
        match = pattern.match(candidate)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return ""


def _git_config_for(start: Path) -> Path | None:
    """The nearest enclosing repo's ``config`` file, following worktree pointers."""
    current = start if start.is_dir() else start.parent
    for folder in (current, *current.parents):
        git_entry = folder / ".git"
        try:
            if git_entry.is_dir():
                config = git_entry / "config"
                return config if config.is_file() else None
            if git_entry.is_file():
                # Worktree/submodule: ".git" is a one-line "gitdir: <path>" file.
                text = git_entry.read_text(encoding="utf-8", errors="replace").strip()
                if text.startswith("gitdir:"):
                    gitdir = Path(text.removeprefix("gitdir:").strip())
                    if not gitdir.is_absolute():
                        gitdir = (folder / gitdir).resolve()
                    # A linked worktree's config lives in the common dir.
                    for candidate in (gitdir / "config", gitdir.parent.parent / "config"):
                        if candidate.is_file():
                            return candidate
                return None
        except OSError:
            return None
    return None


def detect_github_repo(path: Path | str | None) -> str:
    """``owner/repo`` for the GitHub ``origin`` of *path*'s checkout, or ``""``.

    Best-effort by contract — any parse or I/O problem returns ``""`` so the
    caller simply leaves the repository field for the user to fill.
    """
    if not path:
        return ""
    try:
        config = _git_config_for(Path(path))
        if config is None:
            return ""
        in_origin = False
        for raw_line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if line.startswith("["):
                in_origin = line.replace(" ", "") in ('[remote"origin"]',)
                continue
            if in_origin and line.startswith("url"):
                _key, _sep, value = line.partition("=")
                return parse_github_remote_url(value)
    except OSError:
        return ""
    return ""
