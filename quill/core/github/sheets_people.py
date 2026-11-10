"""Sheets for people, collaborators and invitations (GitHub PRD Appendix C, 16.7, 18.3).

A person's sheet has the **You** page of section 16.7: Follow, Block, and
whether they follow you; Sponsor and Report are links, because GitHub has no
API for either. Your own sheet's Profile page is editable (name, bio,
company, location, website, social handle, hireable); anyone else's reads.
A collaborator's role and an invitation's role are editable, each a tier 2
change previewed in words.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import REPO_ROLES, WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, page, patch, ro, toggle, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["COLLABORATOR", "INVITATION", "PERSON"]

_O, _A = WriteTier.ORGANIZING, WriteTier.ACCESS
_K = FieldKind


def _person(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "login": str(data.get("login") or ""),
        "name": str(data.get("name") or ""),
        "kind": str(data.get("type") or "User"),
        "bio": str(data.get("bio") or ""),
        "company": str(data.get("company") or ""),
        "location": str(data.get("location") or ""),
        "blog": str(data.get("blog") or ""),
        "twitter": str(data.get("twitter_username") or ""),
        "hireable": bool(data.get("hireable")),
        "followers": int(data.get("followers") or 0),
        "following_count": int(data.get("following") or 0),
        "repositories": int(data.get("public_repos") or 0),
        "created": when(data.get("created_at")),
        "url": str(data.get("html_url") or ""),
        "sponsor": f"https://github.com/sponsors/{data.get('login', '')}",
    }


def _yes(key: str) -> Any:
    return lambda _data: {key: True}


_PROFILE = "/user"

PERSON = SheetDef(
    "person",
    SheetSpec(
        "person",
        "Person",
        (
            page(
                "general",
                "General",
                ro("login", "Login"),
                ro("kind", "Kind", help="A user or an organization."),
                ro("created", "Joined", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "you",
                "You",
                ed("following", "Following", _K.CHECK, "Follow to see their activity in yours."),
                ed(
                    "blocked",
                    "Blocked",
                    _K.CHECK,
                    "A blocked person cannot follow you, "
                    "comment on your issues or open pull requests on your repositories.",
                ),
                ro("follows_you", "Follows you", _K.CHECK),
                ro(
                    "sponsor",
                    "Sponsor",
                    _K.LINK,
                    "GitHub Sponsors has no API for sponsoring; Open on GitHub goes to the page.",
                ),
                ro(
                    "report",
                    "Report",
                    help="Reporting someone is done on GitHub's own page; "
                    "it has no API. Open on GitHub, then Report or block.",
                ),
            ),
            page(
                "profile",
                "Profile",
                ed("name", "Name", help="Your own profile only."),
                ed("bio", "Bio", _K.MULTILINE),
                ed("company", "Company"),
                ed("location", "Location"),
                ed("blog", "Website"),
                ed("twitter", "Social handle", help="Your X (Twitter) handle, without the @."),
                ed("hireable", "Available for hire", _K.CHECK),
            ),
            page(
                "repositories",
                "Repositories",
                ro("repositories", "Public repositories", _K.NUMBER),
            ),
            page("followers", "Followers", ro("followers", "Followers", _K.NUMBER)),
            page("following_page", "Following", ro("following_count", "Following", _K.NUMBER)),
            page(
                "organizations",
                "Organizations",
                ro("organizations", "Public organizations", _K.TABLE),
            ),
        ),
    ),
    (
        Read("/users/{login}", _person),
        Read(
            "/user/following/{login}",
            _yes("following"),
            optional=True,
            fallback={"following": False},
        ),
        Read("/user/blocks/{login}", _yes("blocked"), optional=True, fallback={"blocked": False}),
        Read(
            "/users/{login}/following/{me}",
            _yes("follows_you"),
            optional=True,
            fallback={"follows_you": False},
        ),
        Read(
            "/users/{login}/orgs",
            lambda d: {
                "organizations": tuple(
                    str(row.get("login", "")) for row in lst(d, "items") if isinstance(row, Mapping)
                )
            },
            optional=True,
        ),
    ),
    {
        "following": toggle("/user/following/{login}", "sign_in+scope:user:follow", _O),
        "blocked": toggle("/user/blocks/{login}", "sign_in+scope:user", _O),
        "name": patch(_PROFILE, "self+scope:user", _O),
        "bio": patch(_PROFILE, "self+scope:user", _O),
        "company": patch(_PROFILE, "self+scope:user", _O),
        "location": patch(_PROFILE, "self+scope:user", _O),
        "blog": patch(_PROFILE, "self+scope:user", _O),
        "twitter": patch(_PROFILE, "self+scope:user", _O, "twitter_username"),
        "hireable": patch(_PROFILE, "self+scope:user", _O),
    },
    title=lambda ident: ident["login"],
    url=lambda ident: f"https://github.com/{ident['login']}",
)


def _collaborator(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "login": str(dig(data, "user", "login") or ""),
        "role": str(data.get("role_name") or data.get("permission") or ""),
        "source": "direct",
    }


COLLABORATOR = SheetDef(
    "collaborator",
    SheetSpec(
        "collaborator",
        "Collaborator",
        (
            page(
                "general",
                "General",
                ro("login", "Person"),
                ed(
                    "role",
                    "Role",
                    _K.CHOICE,
                    "Read, triage, write, maintain or admin, or "
                    "one of the organization's custom roles.",
                    choices=REPO_ROLES,
                ),
                ro("source", "Where it comes from"),
            ),
        ),
    ),
    (Read("/repos/{repo}/collaborators/{login}/permission", _collaborator),),
    {
        "role": Write(
            "/repos/{repo}/collaborators/{login}",
            "repo:admin",
            _A,
            "PUT",
            "put",
            "permission",
            encode=lambda v, _c, _i: {"permission": _api_role(v)},
        ),
    },
    title=lambda ident: f"{ident['login']} on {ident['repo']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/settings/access",
)


def _api_role(value: Value) -> str:
    """GitHub's REST words for a role: read is pull, write is push."""
    word = str(value or "read")
    return {"read": "pull", "write": "push"}.get(word, word)


def _invitation(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    for row in lst(data, "items"):
        if isinstance(row, Mapping) and str(row.get("id")) == ident.get("id"):
            return {
                "invitee": str(dig(row, "invitee", "login") or row.get("email") or ""),
                "inviter": str(dig(row, "inviter", "login") or ""),
                "role": str(row.get("permissions") or ""),
                "created": when(row.get("created_at")),
                "expired": bool(row.get("expired")),
            }
    return {}


INVITATION = SheetDef(
    "invitation",
    SheetSpec(
        "invitation",
        "Invitation",
        (
            page(
                "general",
                "General",
                ro("invitee", "Invited"),
                ro("inviter", "Invited by"),
                ed(
                    "role",
                    "Role",
                    _K.CHOICE,
                    choices=("read", "triage", "write", "maintain", "admin"),
                ),
                ro("created", "Sent", _K.DATE),
                ro("expired", "Expired", _K.CHECK),
            ),
        ),
    ),
    (Read("/repos/{repo}/invitations", pick=_invitation),),
    {"role": patch("/repos/{repo}/invitations/{id}", "repo:admin", _A, "permissions")},
    title=lambda ident: f"Invitation {ident['id']}",
)
