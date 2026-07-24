"""The read/interact half of QUILL's Mastodon support (Leasey Social parity).

Beyond composing a post, this adds: looking up an account and its relationship
(are you following them, do they follow you), following/unfollowing, seeing who
favourited or boosted a post, the accounts named in a post (author, booster,
favouriter, mentions), your lists and their members, adding an account to a
list, and reading your filters.

Pure model code (no ``wx``). Every network call funnels through the reviewed
egress site in :mod:`quill.core.mastodon.client`; the JSON->dataclass parsers
here are pure and unit-tested. Mastodon requires that you follow an account
before it can be added to a list, so :func:`add_to_list` surfaces that as a
clear, catchable error.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.mastodon import client
from quill.core.mastodon.client import MastodonError


@dataclass(frozen=True, slots=True)
class Account:
    """A fetched Mastodon account (profile), as opposed to a stored login."""

    id: str
    acct: str  # "user" or "user@remote.host"
    display_name: str

    @property
    def label(self) -> str:
        """A screen-reader-friendly name: display name and @handle."""
        name = self.display_name.strip()
        return f"{name} (@{self.acct})" if name else f"@{self.acct}"


@dataclass(frozen=True, slots=True)
class Relationship:
    """Your relationship with an account."""

    id: str
    following: bool
    followed_by: bool
    requested: bool = False

    def summary(self) -> str:
        """A spoken sentence describing the relationship both ways."""
        you = (
            "You have requested to follow them"
            if self.requested and not self.following
            else ("You follow them" if self.following else "You do not follow them")
        )
        them = "they follow you" if self.followed_by else "they do not follow you"
        mutual = " You follow each other." if self.following and self.followed_by else ""
        return f"{you}; {them}.{mutual}"


@dataclass(frozen=True, slots=True)
class MastodonList:
    """One of the user's lists."""

    id: str
    title: str


@dataclass(frozen=True, slots=True)
class MastodonFilter:
    """One of the user's content filters."""

    id: str
    title: str
    contexts: tuple[str, ...]


# -- pure JSON -> model parsers (unit-tested) ---------------------------------


def account_from_json(data: object) -> Account | None:
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return Account(
        id=str(data.get("id")),
        acct=str(data.get("acct") or data.get("username") or ""),
        display_name=str(data.get("display_name") or ""),
    )


def relationship_from_json(data: object) -> Relationship | None:
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return Relationship(
        id=str(data.get("id")),
        following=bool(data.get("following")),
        followed_by=bool(data.get("followed_by")),
        requested=bool(data.get("requested")),
    )


def list_from_json(data: object) -> MastodonList | None:
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return MastodonList(id=str(data.get("id")), title=str(data.get("title") or "Untitled list"))


def filter_from_json(data: object) -> MastodonFilter | None:
    if not isinstance(data, dict):
        return None
    fid = data.get("id")
    # v2 filters carry "title" + "context"; v1 filters carry "phrase" + "context".
    title = str(data.get("title") or data.get("phrase") or "").strip()
    if not fid or not title:
        return None
    contexts = data.get("context")
    ctx = tuple(str(c) for c in contexts) if isinstance(contexts, list) else ()
    return MastodonFilter(id=str(fid), title=title, contexts=ctx)


def users_in_post(status: object, *, notification_type: str = "") -> list[Account]:
    """Every account named in one post, de-duplicated and in a useful order: the
    author, whoever boosted it (a reblog wraps the original in ``reblog``), the
    person a favourite/boost notification is about, and the mentioned users.

    ``status`` is a Status dict (optionally the ``status`` inside a Notification);
    pass the notification's ``type`` and its ``account`` via ``notification_type``
    handling in the caller. Pure -- used by "Add User from Post to List".
    """
    found: list[Account] = []
    seen: set[str] = set()

    def add(candidate: object) -> None:
        account = account_from_json(candidate)
        if account is not None and account.id not in seen:
            seen.add(account.id)
            found.append(account)

    if not isinstance(status, dict):
        return found
    reblog = status.get("reblog")
    if isinstance(reblog, dict):
        add(reblog.get("account"))  # the original author
        add(status.get("account"))  # the booster
        base = reblog
    else:
        add(status.get("account"))
        base = status
    for mention in base.get("mentions") or []:
        if isinstance(mention, dict):
            add(mention)
    return found


# -- endpoints (funnel through the reviewed client egress site) ---------------


def lookup_account(instance_url: str, token: str, acct: str) -> Account:
    base = client.normalize_instance_url(instance_url)
    handle = acct.strip().lstrip("@")
    data = client._http_json("GET", f"{base}/api/v1/accounts/lookup?acct={handle}", token=token)
    account = account_from_json(data)
    if account is None:
        raise MastodonError(f"No account found for @{handle}.")
    return account


def relationship(instance_url: str, token: str, account_id: str) -> Relationship:
    base = client.normalize_instance_url(instance_url)
    rows = client.http_json_list(
        "GET", f"{base}/api/v1/accounts/relationships?id={account_id}", token=token
    )
    rel = relationship_from_json(rows[0]) if rows else None
    if rel is None:
        raise MastodonError("Could not read the relationship.")
    return rel


def set_following(instance_url: str, token: str, account_id: str, *, follow: bool) -> Relationship:
    base = client.normalize_instance_url(instance_url)
    verb = "follow" if follow else "unfollow"
    data = client._http_json("POST", f"{base}/api/v1/accounts/{account_id}/{verb}", token=token)
    rel = relationship_from_json(data)
    if rel is None:
        raise MastodonError(f"Could not {verb} the account.")
    return rel


def _accounts(base: str, path: str, token: str) -> list[Account]:
    rows = client.http_json_list("GET", f"{base}{path}", token=token)
    return [account for row in rows if (account := account_from_json(row)) is not None]


def favourited_by(instance_url: str, token: str, status_id: str) -> list[Account]:
    base = client.normalize_instance_url(instance_url)
    return _accounts(base, f"/api/v1/statuses/{status_id}/favourited_by", token)


def reblogged_by(instance_url: str, token: str, status_id: str) -> list[Account]:
    base = client.normalize_instance_url(instance_url)
    return _accounts(base, f"/api/v1/statuses/{status_id}/reblogged_by", token)


def get_lists(instance_url: str, token: str) -> list[MastodonList]:
    base = client.normalize_instance_url(instance_url)
    rows = client.http_json_list("GET", f"{base}/api/v1/lists", token=token)
    return [mlist for row in rows if (mlist := list_from_json(row)) is not None]


def list_accounts(instance_url: str, token: str, list_id: str) -> list[Account]:
    base = client.normalize_instance_url(instance_url)
    return _accounts(base, f"/api/v1/lists/{list_id}/accounts", token)


def add_to_list(instance_url: str, token: str, list_id: str, account_ids: list[str]) -> None:
    """Add one or more accounts to a list. Mastodon requires that you follow an
    account first; a 404/422 for that reason is surfaced as a clear message."""
    base = client.normalize_instance_url(instance_url)
    try:
        client._http_json(
            "POST",
            f"{base}/api/v1/lists/{list_id}/accounts",
            data={"account_ids": account_ids},
            token=token,
        )
    except MastodonError as exc:
        message = str(exc).lower()
        if "404" in message or "422" in message or "record not found" in message:
            raise MastodonError(
                "Mastodon could not add that account to the list. You usually have "
                "to be following an account before you can add it to a list."
            ) from exc
        raise


def get_filters(instance_url: str, token: str) -> list[MastodonFilter]:
    base = client.normalize_instance_url(instance_url)
    # Prefer v2 filters; fall back to v1 for older instances.
    try:
        rows = client.http_json_list("GET", f"{base}/api/v2/filters", token=token)
    except MastodonError:
        rows = client.http_json_list("GET", f"{base}/api/v1/filters", token=token)
    return [flt for row in rows if (flt := filter_from_json(row)) is not None]
