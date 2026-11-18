"""Copilot Autofix, every place an alert was found, and uploading SARIF (GitHub PRD section 19).

Three things a person does with code scanning beyond dismissing an alert:

- :func:`autofix` asks for Copilot Autofix's suggested fix, or reads the one
  already made; :func:`commit_autofix` puts it on a branch as one commit.
- :func:`instances` lists every place an alert's problem was found, one
  sentence each.
- :func:`upload_sarif` sends a SARIF file (the results another scanning tool
  wrote) gzipped and base64-encoded, as GitHub asks, and :func:`sarif_status`
  reads back whether GitHub has processed it.

Each returns sentences to say, never raw JSON. wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import gzip
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Autofix",
    "CodeScanningError",
    "autofix",
    "commit_autofix",
    "instances",
    "sarif_status",
    "upload_sarif",
]

#: GitHub refuses a SARIF upload larger than this once gzipped.
SARIF_LIMIT = 10 * 1024 * 1024


class CodeScanningError(CodedError):
    code = "QUILL-GITHUB-CODESCAN-REFUSED"


@dataclass(frozen=True)
class Autofix:
    status: str  # pending, success, error, outdated, or "none" when none was asked for
    description: str = ""

    @property
    def ready(self) -> bool:
        return self.status == "success"

    def sentence(self) -> str:
        if self.status == "none":
            return "No fix has been asked for yet."
        if self.status == "pending":
            return "Copilot Autofix is still making the fix. Ask again in a minute."
        if self.status == "success":
            return "Copilot Autofix has a fix ready." + (
                f" {self.description}" if self.description else ""
            )
        if self.status == "outdated":
            return "The fix was made for older code. Ask again for a new one."
        return "Copilot Autofix could not make a fix for this alert."


def _alert(repo: str, number: int) -> str:
    return f"/repos/{repo}/code-scanning/alerts/{number}"


def _refused(exc: GitHubRestError, doing: str) -> CodeScanningError:
    if exc.status in (401, 403):
        return CodeScanningError(
            f"GitHub refused to {doing}. It needs write access to the repository, and "
            "Copilot Autofix needs code scanning with CodeQL."
        )
    if exc.status == 404:
        return CodeScanningError(f"GitHub found nothing to {doing}.")
    if exc.status == 422:
        return CodeScanningError(f"GitHub could not {doing}: {exc}")
    return CodeScanningError(f"Could not {doing}: {exc}")


def _autofix_of(data: Any) -> Autofix:
    if not isinstance(data, Mapping):
        return Autofix("error")
    return Autofix(str(data.get("status") or "pending"), str(data.get("description") or ""))


def autofix(api: GitHubApi, repo: str, number: int, *, ask: bool = False) -> Autofix:
    """The alert's fix as it stands; with *ask*, ask Copilot Autofix to make one first."""
    path = f"{_alert(repo, number)}/autofix"
    if ask:
        try:
            return _autofix_of(api.rest("POST", path).data)
        except GitHubRestError as exc:
            raise _refused(exc, "ask Copilot Autofix for a fix") from exc
    try:
        return _autofix_of(api.rest("GET", path).data)
    except GitHubRestError as exc:
        if exc.status == 404:
            return Autofix("none")
        raise _refused(exc, "read the suggested fix") from exc


def commit_autofix(api: GitHubApi, repo: str, number: int, branch: str, message: str) -> str:
    """Put the ready fix on *branch* as one commit, and say where it went."""
    body: dict[str, object] = {"target_ref": f"refs/heads/{branch}"}
    if message.strip():
        body["message"] = message.strip()
    try:
        data = api.rest("POST", f"{_alert(repo, number)}/autofix/commits", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, f"commit the fix to {branch}") from exc
    sha = str(data.get("sha") or "")[:7] if isinstance(data, Mapping) else ""
    return f"Committed the fix to {branch}" + (f" as {sha}." if sha else ".")


def _place(raw: Mapping[str, Any]) -> str:
    location = raw.get("location") if isinstance(raw.get("location"), Mapping) else {}
    assert isinstance(location, Mapping)
    path = str(location.get("path") or "a file")
    line = location.get("start_line")
    where = f"{path}, line {line}" if line else path
    ref = str(raw.get("ref") or "").removeprefix("refs/heads/")
    state = str(raw.get("state") or "open")
    message = raw.get("message") if isinstance(raw.get("message"), Mapping) else {}
    assert isinstance(message, Mapping)
    text = str(message.get("text") or "").strip().rstrip(".")
    return (
        f"{where}"
        + (f" on {ref}" if ref else "")
        + f", {state}"
        + (f": {text}" if text else "")
        + "."
    )


def instances(api: GitHubApi, repo: str, number: int) -> list[str]:
    """Every place the alert's problem was found, newest analysis first."""
    try:
        data = api.rest("GET", f"{_alert(repo, number)}/instances", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, "list where the alert was found") from exc
    return [_place(raw) for raw in data or () if isinstance(raw, Mapping)]


def _encoded(path: Path) -> str:
    packed = gzip.compress(path.read_bytes())
    if len(packed) > SARIF_LIMIT:
        raise CodeScanningError(
            f"{path.name} is {len(packed) // (1024 * 1024)} MB once compressed; GitHub takes "
            "at most 10 MB. Split the results into smaller files."
        )
    return base64.b64encode(packed).decode("ascii")


def _head(api: GitHubApi, repo: str, branch: str) -> str:
    try:
        data = api.rest("GET", f"/repos/{repo}/branches/{branch}").data
    except GitHubRestError as exc:
        raise _refused(exc, f"find the newest commit on {branch}") from exc
    sha = data.get("commit", {}).get("sha") if isinstance(data, Mapping) else None
    if not sha:
        raise CodeScanningError(f"GitHub sent no commit for {branch}.")
    return str(sha)


def upload_sarif(api: GitHubApi, repo: str, path: Path, branch: str) -> tuple[str, str]:
    """Upload *path*'s results against *branch*'s newest commit: (sentence, upload id)."""
    if not path.is_file():
        raise CodeScanningError(f"{path.name} is not a file QUILL can read.")
    body = {
        "commit_sha": _head(api, repo, branch),
        "ref": f"refs/heads/{branch}",
        "sarif": _encoded(path),
        "tool_name": path.stem,
    }
    try:
        data = api.rest("POST", f"/repos/{repo}/code-scanning/sarifs", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, f"upload {path.name}") from exc
    upload = str(data.get("id") or "") if isinstance(data, Mapping) else ""
    return f"Uploaded {path.name} for {branch}. GitHub is processing it.", upload


def sarif_status(api: GitHubApi, repo: str, upload: str) -> str:
    """Whether GitHub has finished with an upload, and any errors it found."""
    try:
        data = api.rest("GET", f"/repos/{repo}/code-scanning/sarifs/{upload}").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the upload's progress") from exc
    if not isinstance(data, Mapping):
        return "GitHub sent nothing about the upload."
    status = str(data.get("processing_status") or "pending")
    errors = [str(one) for one in data.get("errors") or []]
    if status == "complete":
        return "GitHub has processed the upload. Its results are in the repository's alerts."
    if status == "failed":
        return "GitHub could not process the upload" + (
            ": " + "; ".join(errors) + "." if errors else "."
        )
    return "GitHub is still processing the upload."
