"""Repository > Settings > Webhooks, Deploy Keys and Autolinks (GitHub PRD 14.3).

Three settings that are lists, each row a sentence:

* **Webhooks**, a repository's and (Organizations > org > Webhooks) an
  organization's: "https://ci.example.org/hook: on, JSON, push and
  pull_request, last delivery succeeded (200)." New Here adds one (address,
  content type, events, and a secret that is write-only: it can be set, never
  read back, and is never spoken or logged). On a webhook: **Ping**, **Recent
  Deliveries...** (each with its event, result and time; choosing one offers to
  redeliver it), **Change Address or Secret...** and **Delete Webhook...**.
* **Deploy Keys**: "Deploy key CI, read only, ED25519, SHA256:..., added
  2026-01-02, last used 2026-11-17." New Here adds one from a ``.pub`` file or
  a paste, read-only unless you choose otherwise; Delete removes it.
* **Autolinks**: "TICKET- links to https://jira.example.org/browse/TICKET-<num>,
  numbers only." New Here adds one; Delete removes it.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.account_keys import fingerprint, key_kind
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "hooks_path",
    "COMMON_EVENTS",
    "Delivery",
    "SettingsListError",
    "add_autolink",
    "add_deploy_key",
    "add_webhook",
    "change_webhook",
    "delete_autolink",
    "delete_deploy_key",
    "delete_webhook",
    "fetch_autolinks",
    "fetch_deliveries",
    "fetch_deploy_keys",
    "fetch_webhooks",
    "ping_webhook",
    "redeliver",
]

#: The events most webhooks want, offered first when choosing events.
COMMON_EVENTS = (
    "push",
    "pull_request",
    "issues",
    "issue_comment",
    "release",
    "workflow_run",
    "check_suite",
    "create",
    "delete",
    "discussion",
    "pull_request_review",
    "star",
)


class SettingsListError(CodedError):
    """A webhook, deploy key or autolink could not be read or changed; the message is said."""

    code = "QUILL-GITHUB-SETTINGS-LISTS"


@dataclass(frozen=True)
class Delivery:
    id: int
    event: str
    status: str
    code: int
    when: str
    redelivery: bool

    @property
    def label(self) -> str:
        result = "succeeded" if 200 <= self.code < 300 else "failed"
        again = ", a redelivery" if self.redelivery else ""
        return f"{self.event} at {self.when}: {result} ({self.code or self.status}){again}"


def hooks_path(owner: str) -> str:
    """Where *owner*'s webhooks live: ``owner/name`` is a repository, a name an organization."""
    return f"/repos/{owner}/hooks" if "/" in owner else f"/orgs/{owner}/hooks"


def _refused(exc: GitHubRestError, doing: str) -> SettingsListError:
    if exc.status in (403, 404):
        return SettingsListError(
            f"GitHub refused to {doing}: it needs administration of the repository or "
            "organization, and for an organization's webhooks the admin:org_hook permission."
        )
    if exc.status == 422:
        return SettingsListError(f"GitHub could not {doing}: {exc}")
    return SettingsListError(f"Could not {doing}: {exc}")


def _get(api: GitHubApi, path: str, doing: str) -> list[Mapping[str, Any]]:
    try:
        data = api.rest("GET", path, query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, doing) from exc
    return [raw for raw in data or () if isinstance(raw, Mapping)]


def _send(api: GitHubApi, method: str, path: str, doing: str, body: Any = None) -> Any:
    try:
        return api.rest(method, path, body=body).data
    except GitHubRestError as exc:
        raise _refused(exc, doing) from exc


def _events(events: list[str]) -> str:
    if "*" in events:
        return "every event"
    if len(events) <= 3:
        return " and ".join(events) if events else "no events"
    return f"{', '.join(events[:3])} and {len(events) - 3} more"


# -- webhooks ------------------------------------------------------------------------


def _hook_row(repository: str, raw: Mapping[str, Any]) -> ExploreRow:
    config = raw.get("config") if isinstance(raw.get("config"), Mapping) else {}
    url = str((config or {}).get("url") or "a webhook")
    kind = "JSON" if (config or {}).get("content_type") == "json" else "form"
    events = [str(e) for e in raw.get("events") or ()]
    last = raw.get("last_response") if isinstance(raw.get("last_response"), Mapping) else {}
    code = (last or {}).get("code")
    if code is None:
        delivered = "never delivered"
    elif isinstance(code, int) and 200 <= code < 300:
        delivered = f"last delivery succeeded ({code})"
    else:
        delivered = f"last delivery failed ({code}: {(last or {}).get('message') or ''})".replace(
            ": )", ")"
        )
    state = "on" if raw.get("active") else "off"
    label = f"{url}: {state}, {kind}, {_events(events)}, {delivered}."
    where = repository if "/" in repository else f"organizations/{repository}"
    page = f"https://github.com/{where}/settings/hooks/{raw.get('id')}"
    detail = f"{label}\nEvents: {', '.join(events) or 'none'}.\n{page}"
    return ExploreRow(label, detail, page, repository, "webhook", str(raw.get("id") or ""))


def fetch_webhooks(api: GitHubApi, repository: str) -> list[ExploreRow]:
    return [
        _hook_row(repository, raw)
        for raw in _get(api, hooks_path(repository), f"list {repository}'s webhooks")
    ]


def _check_address(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("https://", "http://")):
        raise SettingsListError("A webhook's address starts with https:// (or http://).")
    return cleaned


def add_webhook(
    api: GitHubApi,
    repository: str,
    url: str,
    *,
    events: list[str],
    json: bool = True,
    secret: str = "",
) -> str:
    """Add a webhook. *secret* is sent once and never kept, said or logged."""
    address = _check_address(url)
    if not events:
        raise SettingsListError("Choose at least one event for the webhook.")
    config: dict[str, str] = {
        "url": address,
        "content_type": "json" if json else "form",
        "insecure_ssl": "0",
    }
    if secret:
        config["secret"] = secret
    _send(
        api,
        "POST",
        hooks_path(repository),
        "add the webhook",
        {"name": "web", "active": True, "events": events, "config": config},
    )
    return f"Added a webhook to {address}, for {_events(events)}. GitHub sends it a ping now."


def change_webhook(
    api: GitHubApi, repository: str, hook: str, *, url: str = "", secret: str = ""
) -> str:
    body: dict[str, str] = {}
    if url:
        body["url"] = _check_address(url)
    if secret:
        body["secret"] = secret
    if not body:
        raise SettingsListError("Nothing to change.")
    _send(api, "PATCH", f"{hooks_path(repository)}/{hook}/config", "change the webhook", body)
    parts = (["address"] if url else []) + (["secret"] if secret else [])
    return f"Changed the webhook's {' and '.join(parts)}."


def ping_webhook(api: GitHubApi, repository: str, hook: str) -> str:
    _send(api, "POST", f"{hooks_path(repository)}/{hook}/pings", "ping the webhook")
    return "Sent a ping. Its result is the newest of the webhook's Recent Deliveries."


def fetch_deliveries(api: GitHubApi, repository: str, hook: str) -> list[Delivery]:
    found = []
    for raw in _get(
        api, f"{hooks_path(repository)}/{hook}/deliveries", "read the webhook's deliveries"
    ):
        event = str(raw.get("event") or "")
        if raw.get("action"):
            event += f" {raw['action']}"
        found.append(
            Delivery(
                int(raw.get("id") or 0),
                event,
                str(raw.get("status") or ""),
                int(raw.get("status_code") or 0),
                str(raw.get("delivered_at") or "").replace("T", " ")[:16],
                bool(raw.get("redelivery")),
            )
        )
    return found


def redeliver(api: GitHubApi, repository: str, hook: str, delivery: Delivery) -> str:
    _send(
        api,
        "POST",
        f"{hooks_path(repository)}/{hook}/deliveries/{delivery.id}/attempts",
        "redeliver it",
    )
    return f"Asked GitHub to deliver the {delivery.event} event again."


def delete_webhook(api: GitHubApi, repository: str, hook: str) -> str:
    _send(api, "DELETE", f"{hooks_path(repository)}/{hook}", "delete the webhook")
    return "Deleted the webhook. GitHub sends it nothing more."


# -- deploy keys ---------------------------------------------------------------------


def _deploy_row(repository: str, raw: Mapping[str, Any]) -> ExploreRow:
    key = str(raw.get("key") or "")
    parts = ["read only" if raw.get("read_only", True) else "read and write"]
    printed = fingerprint(key)
    if printed:
        parts.append(printed)
    if raw.get("created_at"):
        parts.append(f"added {str(raw['created_at'])[:10]}")
    parts.append(
        f"last used {str(raw['last_used'])[:10]}" if raw.get("last_used") else "never used"
    )
    label = f"Deploy key {raw.get('title') or 'untitled'}, {', '.join(parts)}."
    page = f"https://github.com/{repository}/settings/keys"
    return ExploreRow(
        label, f"{label}\n{key}\n{page}", page, repository, "deploy_key", str(raw.get("id") or "")
    )


def fetch_deploy_keys(api: GitHubApi, repository: str) -> list[ExploreRow]:
    return [
        _deploy_row(repository, raw)
        for raw in _get(api, f"/repos/{repository}/keys", f"list {repository}'s deploy keys")
    ]


def add_deploy_key(
    api: GitHubApi, repository: str, title: str, text: str, *, read_only: bool = True
) -> str:
    if key_kind(text) != "ssh" or "PRIVATE KEY" in text:
        raise SettingsListError(
            "That is not an SSH public key. Use the .pub file, never a private key."
        )
    _send(
        api,
        "POST",
        f"/repos/{repository}/keys",
        "add the deploy key",
        {"title": title.strip() or "QUILL", "key": text.strip(), "read_only": read_only},
    )
    access = "read only" if read_only else "read and write"
    return f"Added deploy key {title.strip() or 'QUILL'}, {access}, {fingerprint(text)}."


def delete_deploy_key(api: GitHubApi, repository: str, key_id: str) -> str:
    _send(api, "DELETE", f"/repos/{repository}/keys/{key_id}", "delete the deploy key")
    return "Deleted the deploy key."


# -- autolinks -----------------------------------------------------------------------


def _autolink_row(repository: str, raw: Mapping[str, Any]) -> ExploreRow:
    prefix = str(raw.get("key_prefix") or "")
    template = str(raw.get("url_template") or "")
    kind = "letters and numbers" if raw.get("is_alphanumeric", True) else "numbers only"
    label = f"{prefix} links to {template}, {kind}."
    page = f"https://github.com/{repository}/settings/key_links"
    return ExploreRow(
        label, f"{label}\n{page}", page, repository, "autolink", str(raw.get("id") or "")
    )


def fetch_autolinks(api: GitHubApi, repository: str) -> list[ExploreRow]:
    return [
        _autolink_row(repository, raw)
        for raw in _get(api, f"/repos/{repository}/autolinks", f"list {repository}'s autolinks")
    ]


def add_autolink(
    api: GitHubApi, repository: str, prefix: str, template: str, *, alphanumeric: bool
) -> str:
    if not prefix.strip():
        raise SettingsListError("An autolink needs a prefix, such as TICKET-.")
    if "<num>" not in template:
        raise SettingsListError("The address must contain <num> where the reference goes.")
    _check_address(template)
    _send(
        api,
        "POST",
        f"/repos/{repository}/autolinks",
        "add the autolink",
        {
            "key_prefix": prefix.strip(),
            "url_template": template.strip(),
            "is_alphanumeric": alphanumeric,
        },
    )
    return f"Added an autolink: {prefix.strip()} now links to {template.strip()}."


def delete_autolink(api: GitHubApi, repository: str, autolink: str) -> str:
    _send(api, "DELETE", f"/repos/{repository}/autolinks/{autolink}", "delete the autolink")
    return "Deleted the autolink. Text already written keeps its words, without the link."
