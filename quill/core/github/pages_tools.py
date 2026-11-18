"""GitHub Pages: turn it on or off, rebuild, and check the site (GitHub PRD section 19).

Reading the site and its builds lives in Explore; this module does what a
person asks of the site: publish a repository's branch (or let a workflow
publish it), stop publishing, ask for a fresh build, and hear how the latest
build and the custom domain are doing. Deployments made through
``/pages/deployments`` need a workflow's identity token, so the workflow step
``actions/deploy-pages`` makes those, not QUILL. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["PagesError", "check", "rebuild", "turn_off", "turn_on"]


class PagesError(CodedError):
    code = "QUILL-GITHUB-PAGES-REFUSED"


def _refused(exc: GitHubRestError, doing: str) -> PagesError:
    if exc.status in (401, 403):
        return PagesError(f"GitHub refused to {doing}. It needs admin access to the repository.")
    if exc.status == 404:
        return PagesError(f"GitHub found no Pages site to {doing}. Turn Pages on first.")
    if exc.status == 409:
        return PagesError(f"GitHub could not {doing}: Pages is already set up that way.")
    if exc.status == 422:
        return PagesError(f"GitHub could not {doing}: {exc}")
    return PagesError(f"Could not {doing}: {exc}")


def turn_on(
    api: GitHubApi, repo: str, *, workflow: bool, branch: str = "", folder: str = "/"
) -> str:
    """Publish *branch* (from *folder*, ``/`` or ``/docs``), or let a workflow publish."""
    if workflow:
        body: dict[str, object] = {"build_type": "workflow"}
    else:
        if not branch.strip():
            raise PagesError("Name the branch to publish.")
        body = {"build_type": "legacy", "source": {"branch": branch.strip(), "path": folder}}
    try:
        data = api.rest("POST", f"/repos/{repo}/pages", body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, "turn Pages on") from exc
    url = str(data.get("html_url") or "") if isinstance(data, Mapping) else ""
    how = (
        "by your workflow"
        if workflow
        else f"from {branch.strip()}{'' if folder == '/' else folder}"
    )
    return f"Pages is on, published {how}" + (f", at {url}." if url else ".")


def turn_off(api: GitHubApi, repo: str) -> str:
    try:
        api.rest("DELETE", f"/repos/{repo}/pages")
    except GitHubRestError as exc:
        raise _refused(exc, "turn Pages off") from exc
    return "Pages is off. The site is no longer published; the repository is unchanged."


def rebuild(api: GitHubApi, repo: str) -> str:
    try:
        data = api.rest("POST", f"/repos/{repo}/pages/builds").data
    except GitHubRestError as exc:
        raise _refused(exc, "ask for a new build") from exc
    status = str(data.get("status") or "queued") if isinstance(data, Mapping) else "queued"
    return f"GitHub has {status} a new build of the site."


def _health(data: Any) -> str:
    if not isinstance(data, Mapping):
        return "GitHub is still checking the domain. Ask again in a minute."
    domain = data.get("domain")
    if not isinstance(domain, Mapping):
        return "The site has no custom domain to check."
    host = str(domain.get("host") or "The domain")
    problems = [
        words
        for key, words in (
            ("is_valid_domain", "the name is not a valid domain"),
            ("dns_resolves", "the domain's DNS does not resolve"),
            ("is_https_eligible", "it cannot have HTTPS yet"),
        )
        if domain.get(key) is False
    ]
    if domain.get("is_pointed_to_github_pages_ip") is False and not domain.get(
        "is_cname_to_github_user_domain"
    ):
        problems.append("it does not point at GitHub Pages")
    if not problems:
        return f"{host} points at GitHub Pages and is healthy."
    return f"{host}: " + "; ".join(problems) + "."


def check(api: GitHubApi, repo: str) -> str:
    """The latest build, then the custom domain's health, as two sentences."""
    try:
        build = api.rest("GET", f"/repos/{repo}/pages/builds/latest").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the latest build") from exc
    said = "No build yet."
    if isinstance(build, Mapping):
        status = str(build.get("status") or "unknown")
        when = str(build.get("created_at") or "")[:16].replace("T", " at ")
        error = build.get("error")
        message = str(error.get("message") or "") if isinstance(error, Mapping) else ""
        said = (
            f"The latest build {'is ' if status != 'built' else 'was '}{status}"
            + (f", {when}" if when else "")
            + (f": {message}" if message else "")
            + "."
        )
    try:
        health = api.rest("GET", f"/repos/{repo}/pages/health")
        domain = _health(health.data if health.status != 202 else None)
    except GitHubRestError as exc:
        domain = (
            "The site has no custom domain to check."
            if exc.status in (400, 404)
            else f"Could not check the domain: {exc}"
        )
    return f"{said} {domain}"
