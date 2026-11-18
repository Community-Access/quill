"""Repository > Security > Policy and Advisories, and the GitHub Advisory Database (PRD 14.1, GX11).

* **Policy** says where a repository's security policy is (``SECURITY.md``
  in the root, ``.github`` or ``docs``; Enter opens it in the editor) and
  whether private vulnerability reporting is on, so someone who found a hole
  knows how to report it before they write a public issue.
* **Advisories** lists the repository's security advisories, drafts too for
  maintainers: "GHSA-abcd-1234-wxyz: high severity, draft: Path traversal in
  the importer. CVE-2026-1234." The details pane has the affected packages,
  versions and credits (``GET .../security-advisories``).
* **New Here** there either reports a vulnerability privately to the
  maintainers (``POST .../security-advisories/reports``, open to anyone when
  private reporting is on) or drafts an advisory (``POST
  .../security-advisories``, maintainers).
* **Publish or Close Advisory...** changes its state (``PATCH``);
  publishing is public and cannot be undone, so it asks for the GHSA id typed.
  **Request CVE...** asks GitHub for a CVE number (``POST .../cve``).
* **Search > Security Advisories** searches GitHub's Advisory Database by a
  package name, a CVE or a GHSA id (``GET /advisories``).

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "SEVERITIES",
    "AdvisoryError",
    "advisory_row",
    "draft_advisory",
    "fetch_advisories",
    "fetch_policy",
    "report_vulnerability",
    "request_cve",
    "search_advisories",
    "set_state",
]

#: GitHub's severities, most serious first.
SEVERITIES = ("critical", "high", "medium", "low")
_POLICY_PATHS = ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md")
_GHSA = re.compile(r"^GHSA(-[a-z0-9]{4}){3}$", re.IGNORECASE)
_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)


class AdvisoryError(CodedError):
    """An advisory could not be read, reported or changed; the message is said."""

    code = "QUILL-GITHUB-ADVISORIES"


def _vulnerable(raw: Mapping[str, Any]) -> list[str]:
    lines = []
    for item in raw.get("vulnerabilities") or ():
        if not isinstance(item, Mapping):
            continue
        raw_package = item.get("package")
        package: Mapping[str, Any] = raw_package if isinstance(raw_package, Mapping) else {}
        name = f"{package.get('ecosystem') or ''} {package.get('name') or ''}".strip()
        versions = str(item.get("vulnerable_version_range") or "")
        patched = item.get("patched_versions") or item.get("first_patched_version")
        if isinstance(patched, Mapping):
            patched = patched.get("identifier")
        line = name or "a package"
        if versions:
            line += f", affected {versions}"
        if patched:
            line += f", fixed in {patched}"
        lines.append(line)
    return lines


def advisory_row(repository: str, raw: Mapping[str, Any]) -> ExploreRow:
    ghsa = str(raw.get("ghsa_id") or "")
    severity = str(raw.get("severity") or "unknown")
    state = str(raw.get("state") or "")
    summary = str(raw.get("summary") or "")
    cve = str(raw.get("cve_id") or "")
    label = f"{ghsa}: {severity} severity" + (f", {state}" if state else "") + f": {summary}."
    if cve:
        label += f" {cve}."
    detail = [label]
    affected = _vulnerable(raw)
    if affected:
        detail.append("Affects: " + "; ".join(affected) + ".")
    credits = [
        str((c.get("user") or {}).get("login") or c.get("login") or "")
        for c in raw.get("credits") or raw.get("credits_detailed") or ()
        if isinstance(c, Mapping)
    ]
    if any(credits):
        detail.append("Credited: " + ", ".join(c for c in credits if c) + ".")
    if raw.get("description"):
        detail.append(str(raw["description"]).strip())
    url = str(raw.get("html_url") or "")
    if url:
        detail.append(url)
    return ExploreRow(label, "\n".join(detail), url, repository, "advisory", ghsa)


def _refused(exc: GitHubRestError, doing: str) -> AdvisoryError:
    if exc.status in (403, 404):
        return AdvisoryError(
            f"GitHub refused to {doing}. Drafts are shown only to the repository's "
            "administrators and security managers."
        )
    if exc.status == 422:
        return AdvisoryError(f"GitHub could not {doing}: {exc}")
    return AdvisoryError(f"Could not {doing}: {exc}")


def fetch_advisories(api: GitHubApi, repository: str, *, limit: int = 100) -> list[ExploreRow]:
    try:
        data = api.rest(
            "GET",
            f"/repos/{repository}/security-advisories",
            query={"per_page": str(max(1, min(limit, 100))), "sort": "updated"},
        ).data
    except GitHubRestError as exc:
        raise _refused(exc, f"list {repository}'s security advisories") from exc
    return [advisory_row(repository, raw) for raw in data or () if isinstance(raw, Mapping)]


def fetch_policy(api: GitHubApi, repository: str, branch: str = "") -> list[ExploreRow]:
    """Where the security policy is, and whether private reporting is on."""
    rows: list[ExploreRow] = []
    for path in _POLICY_PATHS:
        try:
            found = api.rest("GET", f"/repos/{repository}/contents/{path}").data
        except GitHubRestError:
            continue
        if isinstance(found, Mapping) and found.get("html_url"):
            url = str(found["html_url"])
            label = f"Security policy: {path}. Enter opens it."
            rows.append(ExploreRow(label, f"{label}\n{url}", url, repository, "file", path))
            break
    if not rows:
        url = f"https://github.com/{repository}/security/policy"
        label = f"{repository} has no security policy file (SECURITY.md)."
        rows.append(ExploreRow(label, f"{label}\n{url}", url, repository, "policy", "none"))
    try:
        data = api.rest("GET", f"/repos/{repository}/private-vulnerability-reporting").data
        enabled = bool(data.get("enabled")) if isinstance(data, Mapping) else False
        reporting = (
            "Private vulnerability reporting is on: anyone can report a vulnerability "
            "privately, with New Here in Advisories."
            if enabled
            else "Private vulnerability reporting is off: report a vulnerability the way the "
            "policy says, not in a public issue."
        )
    except GitHubRestError:
        reporting = "GitHub did not say whether private vulnerability reporting is on."
    url = f"https://github.com/{repository}/security"
    rows.append(
        ExploreRow(reporting, f"{reporting}\n{url}", url, repository, "policy", "reporting")
    )
    return rows


def _severity(severity: str) -> str:
    word = severity.strip().lower()
    if word and word not in SEVERITIES:
        raise AdvisoryError(f"{severity} is not a severity GitHub knows.")
    return word


def report_vulnerability(
    api: GitHubApi, repository: str, summary: str, description: str, severity: str = ""
) -> str:
    if not summary.strip() or not description.strip():
        raise AdvisoryError("A report needs a summary and a description.")
    body: dict[str, object] = {"summary": summary.strip(), "description": description.strip()}
    if _severity(severity):
        body["severity"] = _severity(severity)
    try:
        data = api.rest("POST", f"/repos/{repository}/security-advisories/reports", body=body).data
    except GitHubRestError as exc:
        if exc.status in (403, 404, 422):
            raise AdvisoryError(
                f"{repository} does not take private vulnerability reports. Follow its "
                "security policy instead."
            ) from exc
        raise
    ghsa = str(data.get("ghsa_id") or "") if isinstance(data, Mapping) else ""
    return (
        f"Reported privately to {repository}'s maintainers" + (f" as {ghsa}" if ghsa else "") + "."
    )


def draft_advisory(
    api: GitHubApi,
    repository: str,
    summary: str,
    description: str,
    severity: str,
    *,
    ecosystem: str = "",
    package: str = "",
) -> str:
    if not summary.strip() or not description.strip():
        raise AdvisoryError("An advisory needs a summary and a description.")
    vulnerabilities: list[dict[str, object]] = []
    if package.strip():
        vulnerabilities.append({
            "package": {"ecosystem": ecosystem.strip() or "other", "name": package.strip()}
        })
    body: dict[str, object] = {
        "summary": summary.strip(),
        "description": description.strip(),
        "vulnerabilities": vulnerabilities,
    }
    if _severity(severity):
        body["severity"] = _severity(severity)
    try:
        data = api.rest("POST", f"/repos/{repository}/security-advisories", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, "draft the advisory") from exc
    ghsa = str(data.get("ghsa_id") or "") if isinstance(data, Mapping) else ""
    return f"Drafted advisory {ghsa}. Only maintainers can see it until it is published."


def set_state(api: GitHubApi, repository: str, ghsa: str, state: str) -> str:
    if state not in ("published", "closed", "draft"):
        raise AdvisoryError(f"{state} is not an advisory state.")
    try:
        api.rest(
            "PATCH",
            f"/repos/{repository}/security-advisories/{quote(ghsa, safe='')}",
            body={"state": state},
        )
    except GitHubRestError as exc:
        raise _refused(exc, f"change {ghsa}") from exc
    return {
        "published": f"Published {ghsa}. It is public now, and in the Advisory Database.",
        "closed": f"Closed {ghsa}.",
        "draft": f"{ghsa} is a draft again.",
    }[state]


def request_cve(api: GitHubApi, repository: str, ghsa: str) -> str:
    try:
        api.rest("POST", f"/repos/{repository}/security-advisories/{quote(ghsa, safe='')}/cve")
    except GitHubRestError as exc:
        raise _refused(exc, f"request a CVE for {ghsa}") from exc
    return f"Asked GitHub for a CVE number for {ghsa}. GitHub reviews the request first."


def search_advisories(api: GitHubApi, query: str, *, limit: int = 50) -> list[ExploreRow]:
    """GitHub's Advisory Database: by GHSA id, by CVE, or by the package affected."""
    words = query.strip()
    if not words:
        raise AdvisoryError("Type a package name, a CVE or a GHSA id to search for.")
    params = {"per_page": str(max(1, min(limit, 100)))}
    if _GHSA.match(words):
        params["ghsa_id"] = words
    elif _CVE.match(words):
        params["cve_id"] = words.upper()
    else:
        params["affects"] = words
    data = api.rest("GET", "/advisories", query=params).data
    rows = []
    for raw in data or ():
        if isinstance(raw, Mapping):
            repo = str(raw.get("source_code_location") or "").removeprefix("https://github.com/")
            rows.append(advisory_row(repo if repo.count("/") == 1 else "", raw))
    return rows
