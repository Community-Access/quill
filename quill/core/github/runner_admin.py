"""Adding, labelling and removing a repository's self-hosted runners (GitHub PRD 14.2).

A self-hosted runner is a program on your own machine that GitHub hands jobs
to. Setting one up is a few commands on that machine, with a token GitHub
issues for an hour; the Workbench gets the token and the right download for
the machine's system and puts the whole set of commands on the clipboard,
ready to paste into a terminal there. The token is never said, shown in a
list, or logged.

* **New Runner...** (``Ctrl+N`` in Runners) asks which system the machine
  runs (``GET .../runners/downloads`` lists them) and copies its commands,
  which download the runner, check its SHA-256 checksum, and register it
  (``POST .../runners/registration-token``).
* **Runner Labels...** adds a label or takes one away (``POST`` and ``DELETE
  .../labels``); the labels GitHub gives every runner cannot be taken away.
* **Remove Runner...** forgets a runner (``DELETE .../runners/{id}``); the
  program on the machine stops getting jobs.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "Download",
    "RunnerAdminError",
    "add_label",
    "custom_labels",
    "fetch_downloads",
    "remove_label",
    "remove_runner",
    "setup_commands",
]


class RunnerAdminError(CodedError):
    """A runner could not be added, labelled or removed; the message is said."""

    code = "QUILL-GITHUB-RUNNER-ADMIN"


@dataclass(frozen=True)
class Download:
    os: str
    architecture: str
    url: str
    filename: str
    sha256: str

    @property
    def label(self) -> str:
        names = {"linux": "Linux", "osx": "macOS", "win": "Windows"}
        return f"{names.get(self.os, self.os)} {self.architecture}"


def _refused(exc: GitHubRestError, doing: str) -> RunnerAdminError:
    if exc.status in (403, 404):
        return RunnerAdminError(
            f"GitHub refused to {doing}: runners need administration of the repository."
        )
    return RunnerAdminError(f"Could not {doing}: {exc}")


def fetch_downloads(api: GitHubApi, repository: str) -> list[Download]:
    try:
        data = api.rest("GET", f"/repos/{repository}/actions/runners/downloads").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the runner downloads") from exc
    found = []
    for raw in data or ():
        if isinstance(raw, Mapping) and raw.get("download_url"):
            found.append(
                Download(
                    str(raw.get("os") or ""),
                    str(raw.get("architecture") or ""),
                    str(raw["download_url"]),
                    str(raw.get("filename") or ""),
                    str(raw.get("sha256_checksum") or ""),
                )
            )
    return found


def setup_commands(api: GitHubApi, repository: str, download: Download) -> str:
    """The commands to paste on the machine; they hold a token that works for an hour."""
    from quill.stability.redaction import remember_secret

    try:
        data = api.rest("POST", f"/repos/{repository}/actions/runners/registration-token").data
    except GitHubRestError as exc:
        raise _refused(exc, "get a runner token") from exc
    token = str(data.get("token") or "") if isinstance(data, Mapping) else ""
    if not token:
        raise RunnerAdminError("GitHub sent no runner token.")
    remember_secret(token)
    url = f"https://github.com/{repository}"
    name, sha = download.filename, download.sha256
    if download.os == "win":
        check = (
            f"if ((Get-FileHash -Path {name} -Algorithm SHA256).Hash.ToUpper() -ne "
            f"'{sha}'.ToUpper()) {{ throw 'The download does not match its checksum.' }}"
        )
        lines = [
            "mkdir actions-runner; cd actions-runner",
            f"Invoke-WebRequest -Uri {download.url} -OutFile {name}",
            check,
            "Add-Type -AssemblyName System.IO.Compression.FileSystem",
            f'[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD/{name}", "$PWD")',
            f"./config.cmd --url {url} --token {token}",
            "./run.cmd",
        ]
    else:
        lines = [
            "mkdir actions-runner && cd actions-runner",
            f"curl -o {name} -L {download.url}",
            f'echo "{sha}  {name}" | shasum -a 256 -c',
            f"tar xzf ./{name}",
            f"./config.sh --url {url} --token {token}",
            "./run.sh",
        ]
    return "\n".join(lines) + "\n"


def _labels_path(repository: str, runner: str) -> str:
    return f"/repos/{repository}/actions/runners/{runner}/labels"


def custom_labels(api: GitHubApi, repository: str, runner: str) -> list[str]:
    """The labels that can be removed: the ones someone added, not GitHub's own."""
    try:
        data = api.rest("GET", _labels_path(repository, runner)).data
    except GitHubRestError as exc:
        raise _refused(exc, "read the runner's labels") from exc
    labels = data.get("labels") if isinstance(data, Mapping) else None
    return [
        str(label.get("name"))
        for label in labels or ()
        if isinstance(label, Mapping) and label.get("type") == "custom" and label.get("name")
    ]


def add_label(api: GitHubApi, repository: str, runner: str, label: str) -> str:
    cleaned = label.strip()
    if not cleaned:
        raise RunnerAdminError("Type the label to add, such as gpu.")
    try:
        api.rest("POST", _labels_path(repository, runner), body={"labels": [cleaned]})
    except GitHubRestError as exc:
        raise _refused(exc, "add the label") from exc
    return f"Added the label {cleaned}."


def remove_label(api: GitHubApi, repository: str, runner: str, label: str) -> str:
    try:
        api.rest("DELETE", f"{_labels_path(repository, runner)}/{quote(label, safe='')}")
    except GitHubRestError as exc:
        if exc.status == 422:
            raise RunnerAdminError(
                f"{label} is one of the labels GitHub gives every runner; it cannot be removed."
            ) from exc
        raise _refused(exc, "remove the label") from exc
    return f"Removed the label {label}."


def remove_runner(api: GitHubApi, repository: str, runner: str, name: str) -> str:
    try:
        api.rest("DELETE", f"/repos/{repository}/actions/runners/{runner}")
    except GitHubRestError as exc:
        raise _refused(exc, f"remove {name}") from exc
    return f"Removed the runner {name}. The program on that machine gets no more jobs."
