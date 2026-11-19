"""Members of a Paid Memberships Pro level, as a list (complete.md 2.3, Memberships).

For the owner who wants to email or count one tier's members. Paid
Memberships Pro has **no REST route that lists a level's members**:

- ``pmpro/v1`` reads one person's levels at a time
  (``get_membership_levels_for_user``);
- ``pmpro/v1/recent_memberships`` (in PMPro's own REST class, for Zapier) gives
  the latest membership changes across every level, a few at a time, not
  everyone who holds a level; it is not among the routes recorded from the
  test site either, so nothing here relies on it;
- the PMPro abilities QUILL reads (``pmpro/levels-query`` and the rest) have
  none that lists members.

So the list is built from the site's people (``wp/v2/users``, a page of a
hundred at a time) and each person's current levels: the
``pmpro/member-memberships-get`` ability where the site offers it, otherwise
``pmpro/v1/get_membership_levels_for_user``. That is one request a person, so
it is slow on a big site: :func:`ask_words` says how many people it will ask
about before anything starts, the read runs in the background, and a
``threading.Event`` stops it, keeping what it found (:func:`find_members`).

Wx-free; the reads take an injected API. Nothing here reads payment details.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.counted import plural
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import plain_text

__all__ = [
    "MEMBER_ABILITY",
    "SLOW_FROM",
    "Member",
    "MembersFound",
    "ask_words",
    "count_people",
    "find_members",
    "levels_reader",
]

MEMBER_ABILITY = "pmpro/member-memberships-get"
USERS_ROUTE = "wp/v2/users"
#: From this many people the question says plainly that the list is slow.
SLOW_FROM = 200


@dataclass(frozen=True)
class Member:
    """One person who holds the level now."""

    user_id: int
    name: str
    email: str = ""
    since: str = ""

    def line(self) -> str:
        parts = [self.name, self.email or "no email address shown"]
        if self.since:
            parts.append(f"since {self.since[:10]}")
        return ", ".join(parts)


@dataclass(frozen=True)
class MembersFound:
    """What a read found: the members, how many people it asked about, and whether it stopped."""

    level: str
    site: str
    members: tuple[Member, ...]
    checked: int
    people: int | None = None
    stopped: bool = False
    unread: int = 0

    def sentence(self) -> str:
        """The outcome, said once."""
        found = plural(len(self.members), "member")
        if self.stopped:
            of = f" of {self.people}" if self.people else ""
            said = (
                f"Stopped after {self.checked}{of} people on {self.site}: {found} of "
                f"{self.level} so far."
            )
        else:
            said = f"{self.level} on {self.site} has {found}."
        if self.unread:
            said += f" {plural(self.unread, 'person', 'people')} could not be read."
        return said

    def emails(self) -> str:
        """Every member's email address once, a semicolon between, for an email's To box."""
        seen: list[str] = []
        for member in self.members:
            address = member.email.strip()
            if address and address.casefold() not in {s.casefold() for s in seen}:
                seen.append(address)
        return "; ".join(seen)


def count_people(api: Any) -> int | None:
    """How many people the site has (``X-WP-Total``), or None when it does not say."""
    try:
        response = api.request("GET", USERS_ROUTE, params={"per_page": 1, "_fields": "id"})
    except WordPressApiError:
        return None
    total = getattr(response, "total", None)
    return int(total) if isinstance(total, int) else None


def ask_words(level: str, site: str, people: int | None) -> str:
    """The question before the read: what it does, how long, and how to stop it."""
    who = f"each of its {plural(people, 'person', 'people')}" if people else "each person on it"
    said = (
        f"Find every member of {level} on {site}? Paid Memberships Pro has no route that "
        f"lists a level's members, so QUILL asks {site} about {who}, one at a time."
    )
    if people is None or people >= SLOW_FROM:
        said += (
            " On a site this size that is slow: it can take some minutes, and each question "
            "is a request to the site."
        )
    return said + (
        " It runs in the background; choosing Members of This Level again stops it, keeping "
        "the members found so far."
    )


def levels_reader(api: Any) -> Callable[[int], list[dict[str, Any]]]:
    """How to read one person's current levels: the ability first, then ``pmpro/v1``."""
    from quill.core.wordpress.abilities import list_abilities, run_ability
    from quill.core.wordpress.workbench_pmpro_rest import member_levels

    try:
        ability = next((a for a in list_abilities(api) if a.name == MEMBER_ABILITY), None)
    except WordPressApiError:
        ability = None
    if ability is None or not ability.readonly:
        return lambda user_id: member_levels(api, user_id)
    found = ability

    def read(user_id: int) -> list[dict[str, Any]]:
        answer = run_ability(api, found, {"user_id": user_id, "include_inactive": False})
        items = answer.get("memberships", []) if isinstance(answer, Mapping) else []
        return [dict(i) for i in items if isinstance(i, Mapping)]

    return read


def _holds(levels: list[dict[str, Any]], level_id: int) -> tuple[bool, str]:
    """Whether *levels* hold *level_id* now, and since when."""
    for level in levels:
        found = level.get("id") or level.get("membership_id") or level.get("level_id")
        status = str(level.get("status") or "active").lower()
        if str(found) == str(level_id) and status == "active":
            return True, str(level.get("startdate") or level.get("start_date") or "")
    return False, ""


def find_members(
    api: Any,
    level_id: int,
    level: str,
    site: str,
    *,
    people: int | None = None,
    stop: threading.Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> MembersFound:
    """Every person who holds *level_id* now, asking about each person in turn.

    *stop* ends the read between two people and keeps what was found;
    *progress* hears ``(people asked about, members found)`` after each one.
    A site that answers the first person with neither the ability nor the
    ``pmpro/v1`` route is refused in a sentence, rather than asked about
    everyone else.
    """
    read = levels_reader(api)
    members: list[Member] = []
    checked = unread = 0
    stopped = False
    params = {"context": "edit", "_fields": "id,name,email", "orderby": "name"}
    for person in api.iter_collection(USERS_ROUTE, params):
        if stop is not None and stop.is_set():
            stopped = True
            break
        user_id = int(person.get("id") or 0)
        if not user_id:
            continue
        try:
            levels = read(user_id)
        except WordPressApiError as exc:
            if not checked and exc.status in (401, 403, 404):
                raise WordPressApiError(
                    f"{site} exposes neither the Paid Memberships Pro member-memberships "
                    "ability nor its pmpro/v1 routes to you, so the members of a level cannot "
                    "be listed here.",
                    status=exc.status,
                ) from exc
            unread += 1
            levels = []
        checked += 1
        holds, since = _holds(levels, level_id)
        if holds:
            name = plain_text(str(person.get("name") or f"Person {user_id}"))
            members.append(Member(user_id, name, str(person.get("email") or ""), since))
        if progress is not None:
            progress(checked, len(members))
    return MembersFound(level, site, tuple(members), checked, people, stopped, unread)
