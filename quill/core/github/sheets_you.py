"""The You page: every relationship you can have with an object (GitHub PRD 16.7, GH-R-046).

Every sheet whose object you can have a relationship with has a **You** page
right after General. The relationships GitHub lets you change are fields
with the same writes the menu rows send (star is ``PUT /user/starred``,
Follow Organization is ``followOrganization``, Upvote is ``addUpvote``), so
saving the page sends only what changed, through the one checked save path,
and says the outcome in one sentence; several rows selected change each of
them (16.4). The ones GitHub's API cannot change are read-only fields whose
help says why in one sentence.

This module holds the pieces several sheets share: the read-only reasons, the
reads that answer "is it pinned to your profile", "do you sponsor them" and
"do you follow this organization", and :data:`YOU_PAGES`, the relationships
each kind's You page holds, which the tests and the guide are checked
against. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef
from quill.core.github.sheet_fields import dig, gql_input_toggle, ro
from quill.core.workbench.properties import FieldKind, FieldSpec, Value

__all__ = [
    "DISCUSSION_PIN_READ",
    "FOLLOW_ORGANIZATION",
    "ORG_YOU_READ",
    "PERSON_SPONSOR_READ",
    "PROFILE_PIN_WHY",
    "SPONSOR_WHY",
    "YOU_PAGES",
    "discussion_pin_field",
    "profile_pin_field",
    "profile_pin_read",
    "pull_request_pin_field",
    "sponsoring_field",
    "you_page_keys",
]

#: Each kind's You page, in order: (editable relationships, read-only ones).
YOU_PAGES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "repository": (("starred", "watch"), ("custom_watch", "profile_pinned", "your_access")),
    "gist": (("starred",), ("profile_pinned",)),
    "person": (("following", "blocked"), ("follows_you", "sponsoring", "sponsor", "report")),
    "organization": (("following", "public_member"), ("your_org_role", "sponsoring")),
    "issue": (("subscribed", "reactions", "pinned"), ()),
    "pull_request": (("subscribed", "reactions"), ("pinned",)),
    "discussion": (("subscribed", "reactions", "upvoted"), ("upvotes", "pinned")),
    "release": (("reactions",), ()),
    "notification": (("subscribed",), ()),
}

PROFILE_PIN_WHY = (
    "GitHub's API cannot pin anything to your profile, so this only reads; "
    "Customize your pins on your profile page on GitHub."
)
SPONSOR_WHY = (
    "Sponsoring spends money at a tier you choose, so it is never a check box: "
    "a person's Sponsor node in the tree lists their tiers and pays, as GitHub's "
    "Sponsors page does."
)
_PULL_PIN_WHY = "GitHub pins issues only; a pull request cannot be pinned to its repository."
_DISCUSSION_PIN_WHY = (
    "GitHub's API cannot pin or unpin a discussion, so this only reads; "
    "Open on GitHub, Shift+Enter, and pin it from the discussion's page."
)


def you_page_keys(sheet: SheetDef) -> tuple[str, ...]:
    """The field keys on *sheet*'s You page, or none when it has no such page."""
    for spec in sheet.sheet.pages:
        if spec.key == "you":
            return tuple(field.key for field in spec.fields)
    return ()


# -- pinned to your profile (repositories and gists) ------------------------------

_PROFILE_PINS = (
    "query{viewer{pinnedItems(first:6){nodes{__typename "
    "... on Repository{nameWithOwner} ... on Gist{name}}}}}"
)


def profile_pin_field() -> FieldSpec:
    return ro("profile_pinned", "Pinned to your profile", FieldKind.CHECK, PROFILE_PIN_WHY)


def profile_pin_read(ident_key: str) -> Read:
    """Whether the object named by *ident_key* is among your profile's pins."""

    def pick(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
        wanted = ident.get(ident_key, "").casefold()
        nodes = dig(data, "viewer", "pinnedItems", "nodes") or ()
        pinned = {
            str(node.get("nameWithOwner") or node.get("name") or "").casefold()
            for node in nodes
            if isinstance(node, Mapping)
        }
        return {"profile_pinned": bool(wanted) and wanted in pinned}

    return Read(graphql=_PROFILE_PINS, variables=lambda _ident: {}, pick=pick, optional=True)


# -- sponsoring (people and organizations) -----------------------------------------

_SPONSORABLE = (
    "query($login:String!){repositoryOwner(login:$login){... on Sponsorable{viewerIsSponsoring}}}"
)


def sponsoring_field() -> FieldSpec:
    return ro("sponsoring", "Sponsoring", FieldKind.CHECK, SPONSOR_WHY)


def _sponsoring(data: Mapping[str, Any]) -> dict[str, Value]:
    owner = dig(data, "repositoryOwner") or dig(data, "organization") or {}
    return {"sponsoring": bool(owner.get("viewerIsSponsoring"))}


PERSON_SPONSOR_READ = Read(
    graphql=_SPONSORABLE,
    variables=lambda ident: {"login": ident.get("login", "")},
    extract=_sponsoring,
    optional=True,
)


# -- following an organization -----------------------------------------------------

_ORG_YOU = "query($org:String!){organization(login:$org){id viewerIsFollowing viewerIsSponsoring}}"


def _org_you(data: Mapping[str, Any]) -> dict[str, Value]:
    org = dig(data, "organization") or {}
    return {
        "node_id": str(org.get("id") or ""),
        "following": bool(org.get("viewerIsFollowing")),
        **_sponsoring(data),
    }


ORG_YOU_READ = Read(
    graphql=_ORG_YOU,
    variables=lambda ident: {"org": ident.get("org", "")},
    extract=_org_you,
    optional=True,
)

#: Follow Organization and Unfollow Organization, the same two mutations the menu rows send.
FOLLOW_ORGANIZATION = gql_input_toggle(
    "followOrganization", "unfollowOrganization", "organizationId", "sign_in", WriteTier.ORGANIZING
)


# -- pins GitHub keeps to itself ---------------------------------------------------


def pull_request_pin_field() -> FieldSpec:
    return ro("pinned", "Pinned to the repository", FieldKind.CHECK, _PULL_PIN_WHY)


def discussion_pin_field() -> FieldSpec:
    return ro("pinned", "Pinned to the repository", FieldKind.CHECK, _DISCUSSION_PIN_WHY)


_DISCUSSION_PINS = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
    "pinnedDiscussions(first:10){nodes{discussion{number}}}}}"
)


def _discussion_pinned(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    nodes = dig(data, "repository", "pinnedDiscussions", "nodes") or ()
    numbers = {
        str(dig(node, "discussion", "number")) for node in nodes if isinstance(node, Mapping)
    }
    return {"pinned": ident.get("number", "") in numbers}


DISCUSSION_PIN_READ = Read(
    graphql=_DISCUSSION_PINS,
    variables=lambda ident: {
        "owner": ident["repo"].partition("/")[0],
        "name": ident["repo"].partition("/")[2],
    },
    pick=_discussion_pinned,
    optional=True,
)
