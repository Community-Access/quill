"""Safe parsing for pasted GitHub URLs and repository references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

from quill.core.error_codes import CodedError

_OWNER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_LINE_FRAGMENT = re.compile(r"^L(?P<first>[1-9][0-9]*)(?:-L(?P<last>[1-9][0-9]*))?$")
_SENSITIVE_QUERY_KEYS = frozenset({
    "access_token",
    "auth",
    "authorization",
    "client_secret",
    "code",
    "oauth_token",
    "token",
})


class GitHubReferenceError(CodedError):
    """A pasted GitHub reference is malformed or unsafe to forward."""

    code = "QUILL-GITHUB-REFERENCE-ERROR"


@dataclass(frozen=True, slots=True)
class GitHubReference:
    """A parsed repository or object URL, with a safe browser fallback."""

    host: str
    owner: str
    repo: str
    kind: str
    url: str
    number: int | None = None
    ref: str = ""
    path: str = ""
    line: int = 0
    line_end: int = 0
    section: str = ""

    @property
    def repository(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def supports_native_view(self) -> bool:
        supported = self.kind in {
            "repository",
            "issue",
            "pull_request",
            "discussion",
            "file",
            "commit",
            "release",
            "workflow",
            "workflow_run",
        } or (self.kind == "branch" and not self.path)
        return self.host in {"github.com", "www.github.com"} and supported


def _sensitive_query(query: str) -> bool:
    for key, _value in parse_qsl(query, keep_blank_values=True):
        normalized = key.casefold().replace("-", "_")
        if normalized in _SENSITIVE_QUERY_KEYS or normalized.endswith("_token"):
            return True
    return False


def _object_route(parts: list[str], fragment: str) -> dict[str, object]:
    result: dict[str, object] = {"kind": "repository"}
    if len(parts) < 3:
        return result

    route = parts[2].casefold()
    if route in {"issues", "pull", "discussions"} and len(parts) >= 4:
        number_text = unquote(parts[3])
        if not number_text.isdecimal() or int(number_text) <= 0:
            raise GitHubReferenceError(f"GitHub {route} links need a positive item number.")
        result.update(
            kind={"pull": "pull_request", "issues": "issue", "discussions": "discussion"}[route]
        )
        result["number"] = int(number_text)
        if len(parts) > 4:
            result["section"] = "/".join(unquote(item) for item in parts[4:])
    elif route == "commit" and len(parts) >= 4:
        result.update(kind="commit", ref=unquote(parts[3]))
    elif route == "tree" and len(parts) >= 4:
        result.update(
            kind="branch",
            ref=unquote(parts[3]),
            path="/".join(unquote(item) for item in parts[4:]),
        )
    elif route == "blob" and len(parts) >= 5:
        result.update(
            kind="file",
            ref=unquote(parts[3]),
            path="/".join(unquote(item) for item in parts[4:]),
        )
    elif route == "releases":
        result["kind"] = "release"
        if len(parts) >= 5 and parts[3].casefold() == "tag":
            result["ref"] = unquote(parts[4])
    elif route == "actions" and len(parts) >= 4:
        if parts[3].casefold() == "runs" and len(parts) >= 5:
            run_id = unquote(parts[4])
            if not run_id.isdecimal() or int(run_id) <= 0:
                raise GitHubReferenceError("GitHub workflow-run links need a positive run ID.")
            result.update(kind="workflow_run", number=int(run_id))
        elif parts[3].casefold() == "workflows" and len(parts) >= 5:
            result.update(kind="workflow", ref="/".join(unquote(item) for item in parts[4:]))
        else:
            result["kind"] = "unsupported"
    elif route == "compare" and len(parts) >= 4:
        result.update(kind="compare", ref="/".join(unquote(item) for item in parts[3:]))
    else:
        result["kind"] = "unsupported"

    line_match = _LINE_FRAGMENT.fullmatch(fragment)
    if line_match:
        result["line"] = int(line_match.group("first"))
        result["line_end"] = int(line_match.group("last") or line_match.group("first"))
        if result["line_end"] < result["line"]:
            raise GitHubReferenceError("The GitHub line range ends before it starts.")
    elif fragment.startswith("L") and any(char.isdecimal() for char in fragment[1:]):
        raise GitHubReferenceError("The GitHub line anchor is malformed.")
    return result


def parse_github_reference(text: str) -> GitHubReference:
    """Parse owner/repo, a GitHub web URL, or a GitHub SSH remote.

    Enterprise hosts are parsed but marked for an explicit browser fallback.
    Credentials in URL user-info or sensitive query parameters are rejected.
    """
    value = text.strip()
    if not value:
        raise GitHubReferenceError("Paste a GitHub URL or enter owner/repo.")

    if value.casefold().startswith("git@github.com:"):
        value = "https://github.com/" + value.split(":", 1)[1]
    elif "://" not in value:
        if value.casefold().startswith(("github.com/", "www.github.com/")):
            value = "https://" + value
        elif "/" in value and not any(char in value for char in "?#@"):
            value = "https://github.com/" + value
        else:
            raise GitHubReferenceError("Enter a GitHub URL or repository as owner/repo.")

    parsed = urlsplit(value)
    host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme.casefold() != "https" or not host:
        raise GitHubReferenceError("GitHub references must use a valid HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise GitHubReferenceError("URLs with embedded credentials cannot be opened.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise GitHubReferenceError("The GitHub URL has an invalid port.") from exc
    if host in {"github.com", "www.github.com"} and port not in (None, 443):
        raise GitHubReferenceError("GitHub.com references must use the standard HTTPS port.")
    if _sensitive_query(parsed.query):
        raise GitHubReferenceError("Remove credentials from the URL before opening it.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise GitHubReferenceError("The GitHub URL must include an owner and repository.")
    owner, repo = unquote(parts[0]), unquote(parts[1])
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]
    if not _OWNER.fullmatch(owner) or not _REPOSITORY.fullmatch(repo):
        raise GitHubReferenceError("The GitHub owner or repository name is invalid.")

    route_parts = [owner, repo, *parts[2:]]
    route = _object_route(route_parts, parsed.fragment)
    netloc = host if port is None else f"{host}:{port}"
    safe_path = "/" + "/".join(parts)
    safe_url = urlunsplit(("https", netloc, safe_path, parsed.query, parsed.fragment))
    return GitHubReference(
        host=host,
        owner=owner,
        repo=repo,
        kind=str(route["kind"]),
        url=safe_url,
        number=route.get("number") if isinstance(route.get("number"), int) else None,
        ref=str(route.get("ref", "")),
        path=str(route.get("path", "")),
        line=int(route.get("line", 0)),
        line_end=int(route.get("line_end", 0)),
        section=str(route.get("section", "")),
    )


__all__ = ["GitHubReference", "GitHubReferenceError", "parse_github_reference"]
