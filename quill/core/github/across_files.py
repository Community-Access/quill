"""Workflows, templates, Dependabot and CODEOWNERS by name across repositories (PRD 22.11).

These four kinds are files, so a row is a file name and a variant is a
version of the file: "ci.yml: in 12 of 12 repositories, 3 versions of the
file". :func:`read_file_copies` reads one repository's files of a kind from
directory listings (``GET .../contents``), where GitHub gives each file's
blob sha, so two copies are the same version exactly when their shas are:

- **Workflows**: ``.github/workflows/*.yml`` and ``*.yaml``.
- **Templates and community files**: issue templates and the chooser, pull
  request templates, discussion forms, and CONTRIBUTING, CODE_OF_CONDUCT,
  SECURITY, SUPPORT, GOVERNANCE and FUNDING wherever each repository keeps
  them (``.github``, the root or ``docs``), as Compare Configuration finds them.
- **Dependabot**: ``.github/dependabot.yml``, with its update entries.
- **CODEOWNERS**: the file GitHub uses (``.github``, then the root, then
  ``docs``), with how many rules and which owners.

A file is never pushed. :func:`file_diff` makes the Compare Configuration
difference of two copies (:class:`~quill.core.github.config_compare.FileDiff`,
from #1959), and :func:`plan_files` / :func:`apply_files` propose the
winner's version in every other repository as **one pull request each**,
through :func:`~quill.core.github.config_compare.propose_update`, which checks
each file's sha first and never writes to the default branch.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.github.across import why_failed
from quill.core.github.across_by_name import ByNameRow, Copy, Survey, seg
from quill.core.github.across_changes import LogEntry, Outcome, Plan, Result, Step, blocked_for
from quill.core.github.config_compare import FileDiff

__all__ = [
    "FILE_KINDS",
    "apply_files",
    "file_diff",
    "files_summary",
    "plan_files",
    "read_file_copies",
    "source_copy",
]

#: The by-name kinds that are files.
FILE_KINDS = frozenset({"workflows", "templates", "dependabot", "codeowners"})

#: Compare Configuration's word for each kind, said in its pull request.
_KIND_WORDS = {
    "workflows": "workflow",
    "templates": "template",
    "dependabot": "Dependabot configuration",
    "codeowners": "CODEOWNERS",
}
_TEMPLATE_FOLDERS = (
    ".github/ISSUE_TEMPLATE",
    ".github/PULL_REQUEST_TEMPLATE",
    ".github/DISCUSSION_TEMPLATE",
)
_TEMPLATE_WORDS = {
    ".github/ISSUE_TEMPLATE": "issue template",
    ".github/PULL_REQUEST_TEMPLATE": "pull request template",
    ".github/DISCUSSION_TEMPLATE": "discussion form",
}
_COMMUNITY = (
    "CODE_OF_CONDUCT",
    "CONTRIBUTING",
    "SECURITY",
    "SUPPORT",
    "GOVERNANCE",
    "FUNDING",
    "PULL_REQUEST_TEMPLATE",
)
_PLACES = (".github", "", "docs")


def _contents(repo: str, path: str) -> str:
    """``/repos/{repo}/contents/{path}``, each segment quoted; the root has no path."""
    tail = "/".join(seg(part) for part in path.split("/")) if path else ""
    return f"/repos/{repo}/contents" + (f"/{tail}" if tail else "")


def _listing(api: Any, repo: str, folder: str) -> list[Mapping[str, Any]]:
    """The files of *folder*; a folder that is not there is empty, not a failure."""
    try:
        data = api.rest("GET", _contents(repo, folder)).data
    except Exception as exc:  # noqa: BLE001 - a missing folder is the normal case
        if "not found" in why_failed(exc):
            return []
        raise
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, Mapping) and e.get("type") == "file"]


def file_text(api: Any, repo: str, path: str, *, expected_sha: str = "") -> str:
    """One file's text, from ``GET .../contents/{path}``."""
    data = api.rest("GET", _contents(repo, path)).data
    if not isinstance(data, Mapping):
        raise ValueError(f"GitHub did not return the contents of {path} in {repo}.")
    if expected_sha and data.get("sha") != expected_sha:
        raise ValueError(f"{path} changed in {repo} since it was compared; look again.")
    raw = data.get("content")
    if data.get("encoding") != "base64" or not isinstance(raw, str):
        raise ValueError(f"GitHub did not return readable contents for {path} in {repo}.")
    try:
        return base64.b64decode("".join(raw.split()), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not read {path} in {repo} as UTF-8 text.") from exc


def _folder(where: str) -> str:
    """A folder in words: "the root folder", "the .github folder"."""
    where = where.strip("/")
    return f"the {where} folder" if where else "the root folder"


def _copy(repo: str, name: str, entry: Mapping[str, Any], *extra: tuple[str, str]) -> Copy:
    sha = str(entry.get("sha") or "")
    path = str(entry.get("path") or "")
    if not sha or not path:
        raise ValueError(f"GitHub did not identify {name} in {repo}.")
    return Copy(repo, name, (("version", sha),), path, (*extra, ("sha", sha)))


def _workflows(api: Any, repo: str) -> list[Copy]:
    return [
        _copy(repo, str(e.get("name")), e)
        for e in _listing(api, repo, ".github/workflows")
        if str(e.get("name") or "").endswith((".yml", ".yaml"))
    ]


def _templates(api: Any, repo: str, places: Mapping[str, list[Mapping[str, Any]]]) -> list[Copy]:
    found: dict[str, Copy] = {}
    for folder in _TEMPLATE_FOLDERS:
        for entry in _listing(api, repo, folder):
            name = f"{entry.get('name')}, {_TEMPLATE_WORDS[folder]}"
            found[name.casefold()] = _copy(repo, name, entry)
    for where in _PLACES:
        for entry in places[where]:
            name = str(entry.get("name") or "")
            if name.rsplit(".", 1)[0].upper() in _COMMUNITY:
                found.setdefault(name.casefold(), _copy(repo, name, entry, ("at", _folder(where))))
    return list(found.values())


def _dependabot(api: Any, repo: str, places: Mapping[str, list[Mapping[str, Any]]]) -> list[Copy]:
    from quill.core.github.dependabot_config import load_config

    for entry in places[".github"]:
        if str(entry.get("name") or "") in ("dependabot.yml", "dependabot.yaml"):
            text = file_text(api, repo, str(entry.get("path")))
            try:
                entries = load_config(text).entries
                said = ", ".join(
                    f"{e.get('package-ecosystem')} in {_folder(str(e.get('directory') or ''))}"
                    for e in entries
                )
            except Exception:  # noqa: BLE001 - a file GitHub would refuse is still a version
                said = "could not be read as YAML"
            if not said:
                return [_copy(repo, "dependabot.yml", entry, ("has", "no update entries"))]
            return [_copy(repo, "dependabot.yml", entry, ("updates", said))]
    return []


def _codeowners(api: Any, repo: str, places: Mapping[str, list[Mapping[str, Any]]]) -> list[Copy]:
    from quill.core.github.codeowners_table import CodeownersLines

    for where in _PLACES:  # the first GitHub finds is the one it uses
        for entry in places[where]:
            if str(entry.get("name") or "") == "CODEOWNERS":
                rules = CodeownersLines(file_text(api, repo, str(entry.get("path")))).rows()
                owners = sorted({o for r in rules for o in r.owners}, key=str.casefold)
                said = f"{len(rules)} rule{'' if len(rules) == 1 else 's'}"
                return [
                    _copy(
                        repo,
                        "CODEOWNERS",
                        entry,
                        ("at", _folder(where)),
                        ("has", said + (f", owned by {', '.join(owners)}" if owners else "")),
                    )
                ]
    return []


def read_file_copies(api: Any, kind: str, repo: str) -> list[Copy]:
    """*kind*'s files in *repo*. Raises on a refusal, which the survey says per repository."""
    if kind == "workflows":
        return _workflows(api, repo)
    if kind not in FILE_KINDS:
        raise ValueError(f"Unknown file kind {kind!r}.")
    wanted = (".github",) if kind == "dependabot" else _PLACES
    places = {where: _listing(api, repo, where) if where in wanted else [] for where in _PLACES}
    if kind == "templates":
        return _templates(api, repo, places)
    if kind == "dependabot":
        return _dependabot(api, repo, places)
    return _codeowners(api, repo, places)


# -- comparing and proposing ------------------------------------------------------------


def source_copy(row: ByNameRow, winner: Sequence[tuple[str, str]]) -> Copy:
    """The copy whose version won (the first repository that has it)."""
    return next(c for c in row.copies if c.props == tuple(winner))


def _sha(copy: Copy | None) -> str:
    return dict(copy.extra).get("sha", "") if copy is not None else ""


def file_diff(api: Any, kind: str, source: Copy, target: str, here: Copy | None) -> FileDiff:
    """Compare Configuration's difference of *source* and *target*'s copy (or its absence)."""
    text = file_text(api, source.repository, source.ident, expected_sha=_sha(source))
    word = _KIND_WORDS[kind]
    if here is None:
        return FileDiff(source.ident, source.ident, word, "missing", text)
    mine = file_text(api, target, here.ident, expected_sha=_sha(here))
    same = mine.replace("\r\n", "\n") == text.replace("\r\n", "\n")
    state = "same" if same else "different"
    return FileDiff(here.ident, source.ident, word, state, text, mine, _sha(here))


def plan_files(
    survey: Survey,
    row: ByNameRow,
    winner: Sequence[tuple[str, str]],
    targets: Sequence[str] = (),
    *,
    missing: bool = False,
) -> Plan:
    """A pull request with the winner's version for each copy that differs, or each target.

    The plan's ``into`` is the repository whose version won.
    """
    source = source_copy(row, winner)
    number = {props: n for n, (props, _r) in enumerate(row.variants(), start=1)}
    origin = f"version {number[tuple(winner)]} from {source.repository}"
    steps = []
    if missing:
        for repo in targets or row.missing:
            have = survey.has(repo, row.name)
            if have is not None:
                steps.append(Step(repo, "skip", after="it already has the file", copy=have))
            else:
                blocked = blocked_for(survey, repo)
                steps.append(Step(repo, "pull request", "", f"adds {origin}", blocked))
        return Plan(survey.kind, row.name, "Propose", tuple(steps), into=source.repository)
    for copy in row.copies:
        if copy.props == tuple(winner):
            steps.append(Step(copy.repository, "skip", after="already this version", copy=copy))
            continue
        after = f"replaces version {number[copy.props]} with {origin}"
        blocked = blocked_for(survey, copy.repository)
        steps.append(Step(copy.repository, "pull request", "", after, blocked, copy))
    return Plan(survey.kind, row.name, "Propose", tuple(steps), into=source.repository)


def apply_files(
    api: Any,
    plan: Plan,
    source: Copy,
    repo_for: Callable[[str], Any],
    *,
    on_step: Callable[[Result], None] | None = None,
) -> list[Result]:
    """Open one pull request per runnable step; never a push. Runs off the UI thread."""
    from quill.core.github.across_changes import apply
    from quill.core.github.config_compare import propose_update

    def run(_api: Any, _plan: Plan, step: Step) -> Outcome:
        diff = file_diff(api, plan.kind, source, step.repository, step.copy)
        if diff.state == "same":
            return "no change, already this version", None
        made = propose_update(repo_for(step.repository), step.repository, source.repository, [diff])
        said = f"opened pull request #{made.pull_request_number}"
        target = f"{step.repository} {diff.path}"
        return said, LogEntry("repository", (("repo", step.repository),), target, said)

    return apply(api, plan, on_step=on_step, runner=run, check=lambda *_a: "")


def files_summary(results: Sequence[Result]) -> str:
    """The outcome in pull requests, because nothing changes until each is merged."""
    opened = sum(1 for r in results if r.ok and r.said.startswith("opened pull request"))
    same = sum(1 for r in results if r.ok) - opened
    head = f"Opened {_count(opened, 'pull request')} to review"
    if same:
        had = "repository already had" if same == 1 else "repositories already had"
        head += f"; {same} {had} this version"
    head += "."
    failed = [f"{r.repository}: {r.said}" for r in results if not r.ok]
    if failed:
        head += " Not proposed: " + "; ".join(failed) + "."
    return head + (" Nothing changes until each is merged." if opened else "")


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"
