"""Save a template to GitHub, and copy one to many repositories (GitHub PRD 21.6).

**Save** commits one file. Templates only take effect from the default
branch, so that is where a save goes -- unless the branch is protected, or
the person asks, in which case the file goes to a new branch and a pull
request opens against the default branch (decision 18). Before writing, the
file's current ``sha`` is compared with the one the draft was opened from:
if somebody changed it since, the save stops with a conflict rather than
overwriting their work. After writing, the file is read back and compared,
so "saved" is only said when GitHub holds exactly what was written.

**Copy to Repositories** previews each target first -- the file is missing
there, already the same, a different variant, or the repository cannot be
read -- and then saves to each in turn, one result per repository; one
failure never stops the rest.

Calls: ``GET``/``PUT /repos/{owner}/{repo}/contents/{path}``, ``GET`` the
default branch, ``POST /repos/{owner}/{repo}/git/refs`` for the new branch
and ``POST /repos/{owner}/{repo}/pulls``, through a PyGithub-shaped
repository from ``repo_for``. No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "CopyResult",
    "CopyTarget",
    "SavePlan",
    "SaveResult",
    "TemplateSaveConflict",
    "TemplateSaveError",
    "copy_set",
    "copy_template",
    "plan_copy",
    "plan_copy_set",
    "plan_save",
    "rename_templates",
    "save_template",
]


class TemplateSaveError(CodedError):
    """A template could not be saved; the message says why and nothing half-done."""

    code = "QUILL-GITHUB-TEMPLATE-SAVE-FAILED"


class TemplateSaveConflict(TemplateSaveError):
    """The file changed on GitHub since the draft was opened."""

    code = "QUILL-GITHUB-TEMPLATE-SAVE-CONFLICT"


@dataclass(frozen=True, slots=True)
class SavePlan:
    """Where a save will go, decided before anything is written."""

    repository: str
    path: str
    default_branch: str
    protected: bool
    can_push: bool
    current_sha: str

    @property
    def needs_pull_request(self) -> bool:
        return self.protected

    def sentence(self, *, use_pull_request: bool) -> str:
        where = (
            f"a new branch with a pull request into {self.default_branch}"
            if use_pull_request
            else f"{self.default_branch}, the default branch"
        )
        change = "replaces" if self.current_sha else "creates"
        why = (
            f" {self.default_branch} is protected, so it cannot be written directly."
            if self.protected
            else ""
        )
        return (
            f"Saving {change} {self.path} in {self.repository} on {where}.{why} "
            "Templates take effect only from the default branch."
        )


@dataclass(frozen=True, slots=True)
class SaveResult:
    repository: str
    path: str
    branch: str
    commit_sha: str
    pull_request_url: str = ""
    pull_request_number: int = 0

    def sentence(self) -> str:
        if self.pull_request_number:
            return (
                f"Saved {self.path} to the branch {self.branch} and opened pull request "
                f"#{self.pull_request_number}; it takes effect when that is merged."
            )
        return f"Saved {self.path} to {self.branch} in {self.repository}, and checked it."


def _status(exc: BaseException) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def _current_sha(repo: Any, path: str, ref: str) -> str:
    try:
        found = repo.get_contents(path, ref=ref)
    except Exception as exc:  # noqa: BLE001 - not there yet is the normal "create" case
        if _status(exc) == 404:
            return ""
        raise TemplateSaveError(f"Could not read {path}: {exc}") from exc
    if isinstance(found, list):
        raise TemplateSaveError(f"{path} is a folder on GitHub, not a file.")
    return str(getattr(found, "sha", "") or "")


def plan_save(repo: Any, repository: str, path: str) -> SavePlan:
    """Read the default branch, its protection, push access and the file's sha."""
    try:
        branch_name = str(repo.default_branch or "main")
        branch = repo.get_branch(branch_name)
        protected = bool(getattr(branch, "protected", False))
        permissions = getattr(repo, "permissions", None)
        can_push = bool(getattr(permissions, "push", True)) if permissions is not None else True
    except Exception as exc:  # noqa: BLE001
        raise TemplateSaveError(f"Could not read {repository}'s default branch: {exc}") from exc
    return SavePlan(
        repository,
        path,
        branch_name,
        protected,
        can_push,
        _current_sha(repo, path, branch_name),
    )


def _branch_name(path: str, taken: Callable[[str], bool]) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", path.rsplit("/", 1)[-1].casefold()).strip("-") or "template"
    base = f"quill/template-{stem}-{datetime.now(UTC):%Y%m%d}"
    candidate, number = base, 2
    while taken(candidate):
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def _branch_exists(repo: Any, name: str) -> bool:
    try:
        repo.get_branch(name)
    except Exception as exc:  # noqa: BLE001
        if _status(exc) == 404:
            return False
        raise TemplateSaveError(f"Could not check the branch {name}: {exc}") from exc
    return True


def _write(repo: Any, path: str, text: str, message: str, branch: str, sha: str) -> str:
    try:
        if sha:
            result = repo.update_file(path, message, text, sha, branch=branch)
        else:
            result = repo.create_file(path, message, text, branch=branch)
    except Exception as exc:  # noqa: BLE001
        if _status(exc) in (409, 422) and sha:
            raise TemplateSaveConflict(
                f"{path} changed on GitHub while saving; nothing was overwritten."
            ) from exc
        if _status(exc) == 403:
            raise TemplateSaveError(
                f"GitHub refused the write to {path}: you need write access."
            ) from exc
        raise TemplateSaveError(f"Could not save {path}: {exc}") from exc
    commit = result.get("commit") if isinstance(result, dict) else None
    return str(getattr(commit, "sha", "") or "")


def _verify(repo: Any, path: str, branch: str, text: str) -> None:
    try:
        found = repo.get_contents(path, ref=branch)
        raw = getattr(found, "decoded_content", b"")
    except Exception as exc:  # noqa: BLE001
        raise TemplateSaveError(
            f"Saved {path}, but could not read it back to check it: {exc}"
        ) from exc
    held = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    if held.replace("\r\n", "\n") != text.replace("\r\n", "\n"):
        raise TemplateSaveError(
            f"Saved {path}, but GitHub now holds different text; open it and check."
        )


def save_template(
    repo: Any,
    plan: SavePlan,
    text: str,
    *,
    expected_sha: str,
    message: str = "",
    use_pull_request: bool | None = None,
) -> SaveResult:
    """Commit *text* to ``plan.path`` as *plan* decided, then read it back.

    *expected_sha* is the sha the draft was opened from ("" for a new file);
    a different sha on GitHub now is a :class:`TemplateSaveConflict`.
    """
    if not plan.can_push:
        raise TemplateSaveError(
            f"You do not have write access to {plan.repository}; nothing was saved."
        )
    path = plan.path
    current = _current_sha(repo, path, plan.default_branch)
    if current != expected_sha:
        what = "was created" if not expected_sha else "changed"
        raise TemplateSaveConflict(
            f"{path} {what} on GitHub since you opened it. Nothing was saved; "
            "reopen it to see the other change, then save again."
        )
    message = message or f"{'Update' if current else 'Add'} {path}"
    pull = plan.needs_pull_request if use_pull_request is None else use_pull_request
    if not pull:
        commit = _write(repo, path, text, message, plan.default_branch, current)
        _verify(repo, path, plan.default_branch, text)
        return SaveResult(plan.repository, path, plan.default_branch, commit)
    branch = _branch_name(path, lambda name: _branch_exists(repo, name))
    try:
        head = repo.get_branch(plan.default_branch).commit.sha
        repo.create_git_ref(f"refs/heads/{branch}", head)
    except Exception as exc:  # noqa: BLE001
        raise TemplateSaveError(f"Could not make the branch {branch}: {exc}") from exc
    commit = _write(repo, path, text, message, branch, current)
    _verify(repo, path, branch, text)
    try:
        pull_request = repo.create_pull(
            title=message,
            body=(
                f"Changes the template `{path}`, from QUILL's GitHub Workbench. "
                "It takes effect once merged into the default branch."
            ),
            head=branch,
            base=plan.default_branch,
        )
    except Exception as exc:  # noqa: BLE001
        raise TemplateSaveError(
            f"Saved {path} to the branch {branch}, but could not open the pull request: {exc}"
        ) from exc
    return SaveResult(
        plan.repository,
        path,
        branch,
        commit,
        str(getattr(pull_request, "html_url", "") or ""),
        int(getattr(pull_request, "number", 0) or 0),
    )


@dataclass(frozen=True, slots=True)
class CopyTarget:
    """One repository's preview: ``missing``, ``same``, ``variant`` or ``unreadable``."""

    repository: str
    state: str
    sha: str = ""
    problem: str = ""

    def sentence(self) -> str:
        return {
            "missing": f"{self.repository}: does not have it; it will be added.",
            "same": f"{self.repository}: already the same; skipped.",
            "variant": f"{self.repository}: has a different version; it will be replaced.",
        }.get(self.state, f"{self.repository}: cannot be read ({self.problem}); skipped.")


@dataclass(frozen=True, slots=True)
class CopyResult:
    repository: str
    ok: bool
    sentence: str


def plan_copy(
    repo_for: Callable[[str], Any], path: str, text: str, repositories: Iterable[str]
) -> list[CopyTarget]:
    """Each target's state, read before anything is written."""
    targets: list[CopyTarget] = []
    for name in dict.fromkeys(r.strip() for r in repositories if r.strip()):
        try:
            repo = repo_for(name)
            branch = str(repo.default_branch or "main")
        except Exception as exc:  # noqa: BLE001 - a repository that cannot be read stays per-target
            targets.append(CopyTarget(name, "unreadable", problem=str(exc)))
            continue
        try:
            found = repo.get_contents(path, ref=branch)
        except Exception as exc:  # noqa: BLE001
            if _status(exc) == 404:
                targets.append(CopyTarget(name, "missing"))
            else:
                targets.append(CopyTarget(name, "unreadable", problem=str(exc)))
            continue
        raw = getattr(found, "decoded_content", b"")
        held = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        same = held.replace("\r\n", "\n") == text.replace("\r\n", "\n")
        sha = str(getattr(found, "sha", "") or "")
        targets.append(CopyTarget(name, "same" if same else "variant", sha))
    return targets


def copy_template(
    repo_for: Callable[[str], Any],
    path: str,
    text: str,
    targets: Iterable[CopyTarget],
    *,
    message: str = "",
) -> list[CopyResult]:
    """Save *text* to every target that is ``missing`` or a ``variant``; one result each."""
    results: list[CopyResult] = []
    for target in targets:
        if target.state not in ("missing", "variant"):
            results.append(CopyResult(target.repository, target.state == "same", target.sentence()))
            continue
        try:
            repo = repo_for(target.repository)
            plan = plan_save(repo, target.repository, path)
            done = save_template(repo, plan, text, expected_sha=target.sha, message=message)
            results.append(CopyResult(target.repository, True, done.sentence()))
        except Exception as exc:  # noqa: BLE001 - one failure never stops the rest
            results.append(CopyResult(target.repository, False, f"{target.repository}: {exc}"))
    return results


def rename_templates(
    repo: Any,
    plan: SavePlan,
    folder: str,
    renames: Sequence[tuple[str, str]],
    *,
    use_pull_request: bool | None = None,
) -> SaveResult:
    """Rename files in *folder* (the chooser's order), each as add-then-delete.

    GitHub orders the template chooser by file name, so a new order is a set
    of renames. Each new file is read back before its old one is deleted.
    """
    if not plan.can_push:
        raise TemplateSaveError(
            f"You do not have write access to {plan.repository}; nothing was renamed."
        )
    if not renames:
        raise TemplateSaveError("The order is unchanged; nothing to rename.")
    pull = plan.needs_pull_request if use_pull_request is None else use_pull_request
    branch = plan.default_branch
    if pull:
        branch = _branch_name(f"{folder}/order", lambda name: _branch_exists(repo, name))
        try:
            head = repo.get_branch(plan.default_branch).commit.sha
            repo.create_git_ref(f"refs/heads/{branch}", head)
        except Exception as exc:  # noqa: BLE001
            raise TemplateSaveError(f"Could not make the branch {branch}: {exc}") from exc
    message = f"Reorder the templates in {folder}"
    commit = ""
    for old, new in renames:
        old_path, new_path = f"{folder}/{old}", f"{folder}/{new}"
        try:
            found = repo.get_contents(old_path, ref=branch)
            raw = getattr(found, "decoded_content", b"")
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception as exc:  # noqa: BLE001
            raise TemplateSaveError(f"Could not read {old_path}: {exc}") from exc
        commit = _write(repo, new_path, text, message, branch, "")
        _verify(repo, new_path, branch, text)
        try:
            repo.delete_file(old_path, message, str(getattr(found, "sha", "")), branch=branch)
        except Exception as exc:  # noqa: BLE001
            raise TemplateSaveError(
                f"Added {new_path} but could not remove {old_path}: {exc}"
            ) from exc
    if not pull:
        return SaveResult(plan.repository, folder, branch, commit)
    try:
        pull_request = repo.create_pull(
            title=message,
            body="Renames the templates so GitHub's chooser lists them in this order.",
            head=branch,
            base=plan.default_branch,
        )
    except Exception as exc:  # noqa: BLE001
        raise TemplateSaveError(
            f"Renamed on the branch {branch}, but could not open the pull request: {exc}"
        ) from exc
    return SaveResult(
        plan.repository,
        folder,
        branch,
        commit,
        str(getattr(pull_request, "html_url", "") or ""),
        int(getattr(pull_request, "number", 0) or 0),
    )


def plan_copy_set(
    repo_for: Callable[[str], Any], files: Mapping[str, str], repositories: Iterable[str]
) -> dict[str, list[tuple[str, CopyTarget]]]:
    """For a whole template set: each repository's ``(path, state)`` per file."""
    names = list(dict.fromkeys(r.strip() for r in repositories if r.strip()))
    plan: dict[str, list[tuple[str, CopyTarget]]] = {name: [] for name in names}
    for path, text in files.items():
        for target in plan_copy(repo_for, path, text, names):
            plan[target.repository].append((path, target))
    return plan


def copy_set(
    repo_for: Callable[[str], Any],
    files: Mapping[str, str],
    plan: Mapping[str, Sequence[tuple[str, CopyTarget]]],
) -> list[CopyResult]:
    """Copy every file of a set; one result per repository, naming any file that failed."""
    results: list[CopyResult] = []
    for repository, rows in plan.items():
        failed: list[str] = []
        written = 0
        for path, target in rows:
            if target.state == "unreadable":
                failed.append(f"{path} ({target.problem})")
                continue
            if target.state == "same":
                continue
            done = copy_template(repo_for, path, files[path], [target])[0]
            if done.ok:
                written += 1
            else:
                failed.append(done.sentence)
        if failed:
            results.append(
                CopyResult(
                    repository,
                    False,
                    f"{repository}: {written} written; failed: {'; '.join(failed)}",
                )
            )
        else:
            results.append(
                CopyResult(repository, True, f"{repository}: {written} of {len(rows)} written.")
            )
    return results
