"""Compare a repository's configuration files with a source, and propose the update (PRD 22.11).

For one repository, against a source you choose -- another repository, or
the owner's ``.github`` repository -- :func:`compare_files` lists every file
GitHub reads for configuration:

* workflows (``.github/workflows/*.yml``; from an organization's ``.github``
  repository, its starter workflows in ``workflow-templates/`` count too,
  with ``$default-branch`` filled in as GitHub does when one is used);
* issue templates, the chooser, pull request templates and discussion forms;
* community health files (CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, SUPPORT,
  GOVERNANCE, FUNDING.yml), matched by name wherever each repository keeps
  it (``.github``, the root or ``docs``);
* ``.github/dependabot.yml`` and CODEOWNERS.

Each is **missing** here, **the same**, **different** (with lines added and
removed, and a unified diff to read), or **only here** (kept; a source
never removes a file). :func:`propose_update` writes the chosen files on a
new branch and opens **one pull request** whose description is a readable
summary of every file: it never pushes to the default branch, so every
change is reviewed before it takes effect.

Reads are directory listings and file contents (``GET .../contents``);
writes go through :func:`quill.core.github.template_save.files_pull_request`.
wx-free and strict-typed.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.github.template_save import SaveResult, files_pull_request

__all__ = [
    "FileDiff",
    "compare_files",
    "pull_request_body",
    "propose_update",
]

_FOLDERS: tuple[tuple[str, str], ...] = (
    (".github/workflows", "workflow"),
    (".github/ISSUE_TEMPLATE", "issue template"),
    (".github/PULL_REQUEST_TEMPLATE", "pull request template"),
    (".github/DISCUSSION_TEMPLATE", "discussion form"),
)
_COMMUNITY = (
    "CODE_OF_CONDUCT",
    "CONTRIBUTING",
    "SECURITY",
    "SUPPORT",
    "GOVERNANCE",
    "FUNDING",
    "PULL_REQUEST_TEMPLATE",
)
_MAX_BYTES = 200_000
_DIFF_LINES = 40


@dataclass(frozen=True, slots=True)
class FileDiff:
    """One file: where it goes here, where it came from, and how the two differ."""

    path: str
    source_path: str
    kind: str
    #: "missing", "same", "different" or "only_here"
    state: str
    source_text: str = ""
    target_text: str = ""
    target_sha: str = ""

    @property
    def can_update(self) -> bool:
        return self.state in ("missing", "different")

    def counts(self) -> tuple[int, int]:
        added = removed = 0
        for line in self.diff_lines():
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
        return added, removed

    def diff_lines(self) -> list[str]:
        return list(
            difflib.unified_diff(
                self.target_text.splitlines(),
                self.source_text.splitlines(),
                f"{self.path} (here)",
                f"{self.source_path} (source)",
                lineterm="",
            )
        )

    def sentence(self) -> str:
        """ "workflow .github/workflows/ci.yml: different, 4 lines added and 2 removed"."""
        head = f"{self.kind} {self.path}"
        if self.state == "missing":
            lines = len(self.source_text.splitlines())
            plural = "s" if lines != 1 else ""
            return f"{head}: missing here; it would be added ({lines} line{plural})."
        if self.state == "same":
            return f"{head}: the same as the source."
        if self.state == "only_here":
            return f"{head}: only here; the source has none, and it is kept."
        added, removed = self.counts()
        moved = "" if self.source_path == self.path else f" (from {self.source_path})"
        return (
            f"{head}: different{moved}, {added} line{'s' if added != 1 else ''} added and "
            f"{removed} removed."
        )


def _status(exc: BaseException) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def _listing(repo: Any, path: str) -> list[Any]:
    try:
        found = repo.get_contents(path)
    except Exception as exc:  # noqa: BLE001 - a folder that is not there is normal
        if _status(exc) == 404:
            return []
        raise
    return list(found) if isinstance(found, list) else [found]


def _text(repo: Any, entry: Any) -> tuple[str, str]:
    path = str(getattr(entry, "path", "") or "")
    if int(getattr(entry, "size", 0) or 0) > _MAX_BYTES:
        return "", str(getattr(entry, "sha", "") or "")
    raw = getattr(entry, "decoded_content", None)
    if raw is None:
        found = repo.get_contents(path)
        raw = getattr(found, "decoded_content", b"")
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return text, str(getattr(entry, "sha", "") or "")


def _files(repo: Any, *, organization_defaults: bool) -> dict[str, tuple[str, Any]]:
    """``key -> (kind, entry)``; the key is where the file belongs in a repository."""
    found: dict[str, tuple[str, Any]] = {}
    for folder, kind in _FOLDERS:
        for entry in _listing(repo, folder):
            if str(getattr(entry, "type", "")) == "file":
                found[str(getattr(entry, "path", ""))] = (kind, entry)
    if organization_defaults:
        for entry in _listing(repo, "workflow-templates"):
            name = str(getattr(entry, "name", ""))
            if str(getattr(entry, "type", "")) == "file" and name.endswith((".yml", ".yaml")):
                found.setdefault(f".github/workflows/{name}", ("workflow", entry))
    roots = {where: _listing(repo, where) for where in (".github", "", "docs")}
    for name in ("dependabot.yml", "dependabot.yaml"):
        for entry in roots[".github"]:
            if str(getattr(entry, "name", "")) == name:
                found[f".github/{name}"] = ("Dependabot configuration", entry)
    for where in (".github", "", "docs"):
        for entry in roots[where]:
            if str(getattr(entry, "type", "")) != "file":
                continue
            name = str(getattr(entry, "name", ""))
            stem = name.rsplit(".", 1)[0].upper()
            if name == "CODEOWNERS":
                found.setdefault("community:CODEOWNERS", ("CODEOWNERS", entry))
            elif stem in _COMMUNITY:
                kind = (
                    "pull request template"
                    if stem == "PULL_REQUEST_TEMPLATE"
                    else ("community file")
                )
                found.setdefault(f"community:{stem}", (kind, entry))
    return found


def _placed(key: str, source_entry: Any) -> str:
    """Where a source file goes in a repository that has none of it: ``.github``."""
    if not key.startswith("community:"):
        return key
    name = str(getattr(source_entry, "name", "")) or key.split(":", 1)[1]
    return f".github/{name}"


def compare_files(
    source_repo: Any,
    source_name: str,
    target_repo: Any,
    target_name: str,
    *,
    default_branch: str = "",
) -> list[FileDiff]:
    """Every configuration file of the two, compared; the target is the one to change."""
    organization = source_name.rsplit("/", 1)[-1].casefold() == ".github"
    theirs = _files(source_repo, organization_defaults=organization)
    mine = _files(target_repo, organization_defaults=False)
    branch = default_branch or str(getattr(target_repo, "default_branch", "") or "main")
    diffs: list[FileDiff] = []
    for key in sorted(set(theirs) | set(mine)):
        if key in theirs:
            kind, source_entry = theirs[key]
            source_path = str(getattr(source_entry, "path", ""))
            source_text, _sha = _text(source_repo, source_entry)
            if source_path.startswith("workflow-templates/"):
                source_text = source_text.replace("$default-branch", branch)
        if key not in theirs:
            kind, entry = mine[key]
            text, sha = _text(target_repo, entry)
            path = str(getattr(entry, "path", ""))
            diffs.append(FileDiff(path, "", kind, "only_here", "", text, sha))
            continue
        if key not in mine:
            diffs.append(
                FileDiff(_placed(key, source_entry), source_path, kind, "missing", source_text)
            )
            continue
        _kind, entry = mine[key]
        text, sha = _text(target_repo, entry)
        same = text.replace("\r\n", "\n") == source_text.replace("\r\n", "\n")
        diffs.append(
            FileDiff(
                str(getattr(entry, "path", "")),
                source_path,
                kind,
                "same" if same else "different",
                source_text,
                text,
                sha,
            )
        )
    order = {"different": 0, "missing": 1, "only_here": 2, "same": 3}
    return sorted(diffs, key=lambda d: (order[d.state], d.path))


def pull_request_body(source_name: str, chosen: Sequence[FileDiff]) -> str:
    """A description a reviewer can read: one line per file, then each change."""
    lines = [
        f"Brings these files in line with {source_name}, from QUILL's GitHub Workbench.",
        "Nothing takes effect until this pull request is merged.",
        "",
    ]
    lines += [f"- {diff.sentence()}" for diff in chosen]
    for diff in chosen:
        if diff.state != "different":
            continue
        shown = diff.diff_lines()
        lines += ["", f"### {diff.path}", "", "```diff", *shown[:_DIFF_LINES]]
        if len(shown) > _DIFF_LINES:
            lines.append(f"... {len(shown) - _DIFF_LINES} more lines in the Files tab.")
        lines.append("```")
    return "\n".join(lines) + "\n"


def propose_update(
    repo: Any,
    repository: str,
    source_name: str,
    chosen: Sequence[FileDiff],
) -> SaveResult:
    """One branch and one pull request with *chosen* files taken from the source."""
    writable = [diff for diff in chosen if diff.can_update]
    branch = str(getattr(repo, "default_branch", "") or "main")
    count = len(writable)
    title = f"Update {count} configuration file{'s' if count != 1 else ''} from {source_name}"
    return files_pull_request(
        repo,
        repository,
        branch,
        [(diff.path, diff.source_text, diff.target_sha) for diff in writable],
        title=title,
        body=pull_request_body(source_name, writable),
        branch_stem=f"update-from-{source_name.replace('/', '-')}",
    )
