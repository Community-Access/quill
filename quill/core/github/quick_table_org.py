"""Quick commands for organizations, teams, Projects views and your own account.

* An organization: **Dependabot Repository Access**, **Give Dependabot a
  Repository...**, **Take a Repository from Dependabot...**, **Dependabot's
  Default Access...**, **Make Someone an Outside Collaborator...**, **Define
  a Custom Property...**, **Set Repositories' Custom Property...**, **New
  Team...**, **Accept Membership**, **Members Without Two-Factor**, **My Activity
  Here**.
* A team: **Pending Invitations**, **Delete Team...**. An invitation to the
  organization: **Teams It Adds To**.
* A Project: **New View...** and **Items in a View...**.
* Your emails: **Email Visibility...**. Your profile: **Interaction Limits**,
  **Limit Interactions...**, **Lift Interaction Limits**.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.org_people import convert_problem
from quill.core.github.quick_actions import (
    Ask,
    Quick,
    QuickError,
    bulleted,
    call,
    gql,
    repository_id,
)

__all__ = ["ORG_QUICK"]

_ORG = frozenset({"org"})
_DEP = "/orgs/{org}/dependabot/repository-access"
_LIMITS = (
    ("existing_users", "Only people who already contributed"),
    ("contributors_only", "Only contributors to your repositories"),
    ("collaborators_only", "Only collaborators"),
)
_LASTS = ("one_day", "three_days", "one_week", "one_month", "six_months")
_LAST_WORDS = ("A day", "Three days", "A week", "A month", "Six months")


def _dependabot(data: Any, _ctx: dict[str, str]) -> str:
    data = data if isinstance(data, Mapping) else {}
    repos = [
        str(r.get("full_name") or r.get("name"))
        for r in data.get("accessible_repositories") or ()
        if isinstance(r, Mapping)
    ]
    level = data.get("default_level") or "not set"
    return (
        f"New repositories' default: {level}. Dependabot may also read: "
        + (", ".join(repos) if repos else "no other repositories")
        + "."
    )


def _repo_change(key: str) -> Any:
    def run(api: Any, ctx: dict[str, str]) -> Any:
        return call(api, "PATCH", _DEP, ctx, {key: [repository_id(api, ctx["repository"])]})

    return run


def _schema(api: Any, ctx: dict[str, str]) -> Any:
    prop: dict[str, Any] = {
        "property_name": ctx["prop"],
        "value_type": ctx["type"],
        "required": ctx["required"] == "true",
    }
    allowed = [v.strip() for v in ctx.get("allowed", "").split(",") if v.strip()]
    if allowed:
        prop["allowed_values"] = allowed
    if ctx.get("default"):
        prop["default_value"] = ctx["default"]
    if prop["required"] and "default_value" not in prop:
        raise QuickError("A required property needs a default, for repositories already here.")
    return call(api, "PATCH", "/orgs/{org}/properties/schema", ctx, {"properties": [prop]})


def _values(api: Any, ctx: dict[str, str]) -> Any:
    names = [n.strip().split("/")[-1] for n in ctx["repos"].split(",") if n.strip()]
    body = {
        "repository_names": names,
        "properties": [{"property_name": ctx["prop"], "value": ctx.get("value") or None}],
    }
    return call(api, "PATCH", "/orgs/{org}/properties/values", ctx, body)


def _team(api: Any, ctx: dict[str, str]) -> Any:
    body: dict[str, Any] = {"name": ctx["team"], "privacy": ctx["privacy"]}
    if ctx.get("about"):
        body["description"] = ctx["about"]
    if ctx.get("notify"):
        body["notification_setting"] = ctx["notify"]
    if ctx.get("parent"):
        if ctx["privacy"] == "secret":
            raise QuickError("A secret team cannot sit under another team; make it visible.")
        parent = call(api, "GET", "/orgs/{org}/teams/{parent}", ctx)
        body["parent_team_id"] = (parent or {}).get("id")
    return call(api, "POST", "/orgs/{org}/teams", ctx, body)


def _events(api: Any, ctx: dict[str, str]) -> Any:
    me = call(api, "GET", "/user", ctx)
    login = str(me.get("login") or "") if isinstance(me, Mapping) else ""
    return call(api, "GET", "/users/{me}/events/orgs/{org}?per_page=50", {**ctx, "me": login})


def _event_rows(data: Any, _ctx: dict[str, str]) -> str:
    rows = [
        f"{str(e.get('created_at') or '')[:16]}: {e.get('type')} in "
        f"{(e.get('repo') or {}).get('name')}"
        for e in data if isinstance(e, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip
    return bulleted(rows, "No recent activity of yours here.")


def _two_factor(data: Any, _ctx: dict[str, str]) -> str:
    rows = [str(r.get("login")) for r in data or () if isinstance(r, Mapping)]
    return bulleted(rows, "Every member has two-factor sign-in on.")


def _invitees(data: Any, _ctx: dict[str, str]) -> str:
    rows = [
        f"{i.get('login') or i.get('email')}, as {i.get('role')}, invited by "
        f"{(i.get('inviter') or {}).get('login')}"
        for i in data if isinstance(i, Mapping)
    ] if isinstance(data, list) else []  # fmt: skip
    return bulleted(rows, "Nobody is waiting to join this team.")


def _project_path(ctx: Mapping[str, str]) -> str:
    owner = "/orgs/{owner}" if ctx.get("owner_kind") == "orgs" else "/users/{owner_id}"
    return owner + "/projectsV2/{pnumber}"


def _user_id(api: Any, ctx: dict[str, str]) -> dict[str, str]:
    if ctx.get("owner_kind") == "orgs":
        return ctx
    data = call(api, "GET", "/users/{owner}", ctx)
    return {**ctx, "owner_id": str((data or {}).get("id") or "")}


def _new_view(api: Any, ctx: dict[str, str]) -> Any:
    ctx = _user_id(api, ctx)
    body = {"name": ctx["view_name"], "layout": ctx["layout"]}
    return call(api, "POST", _project_path(ctx) + "/views", ctx, body)


def _views(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    query = (
        "query($id: ID!) { node(id: $id) { ... on ProjectV2 { views(first: 50) "
        "{ nodes { number name layout } } } } }"
    )
    data = gql(api, query, {"id": ctx["key"]})
    nodes = (((data.get("node") or {}).get("views") or {}).get("nodes")) or []
    return [
        (f"{v.get('name')} ({str(v.get('layout') or '').lower().replace('_layout', '')})",
         str(v.get("number")))
        for v in nodes if isinstance(v, Mapping)
    ]  # fmt: skip


def _view_items(api: Any, ctx: dict[str, str]) -> Any:
    ctx = _user_id(api, ctx)
    owner = "/orgs/{owner}" if ctx.get("owner_kind") == "orgs" else "/users/{owner}"
    return call(api, "GET", owner + "/projectsV2/{pnumber}/views/{view}/items?per_page=100", ctx)


def _item_rows(data: Any, _ctx: dict[str, str]) -> str:
    rows = []
    for item in data if isinstance(data, list) else ():
        if isinstance(item, Mapping):
            found = item.get("content")
            content: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
            title = content.get("title") or item.get("title") or "A draft"
            number = f"#{content['number']} " if content.get("number") else ""
            rows.append(f"{number}{title} ({str(item.get('content_type') or 'item').lower()})")
    return bulleted(rows, "Nothing shows in this view.")


def _limits(data: Any, _ctx: dict[str, str]) -> str:
    if not isinstance(data, Mapping) or not data.get("limit"):
        return "No interaction limit is on your repositories."
    words = dict(_LIMITS).get(str(data["limit"]), str(data["limit"]))
    return f"{words} may comment and open issues and pull requests, until {data.get('expires_at')}."


_PROJECT = frozenset({"project"})
_TEAM = frozenset({"team"})

ORG_QUICK: tuple[Quick, ...] = (
    Quick("dependabot_access", "Dependabot Repository Access", ("organization",), _ORG,
          "Which private repositories Dependabot may read to update dependencies.",
          ("GET /orgs/{org}/dependabot/repository-access",),
          lambda api, ctx: call(api, "GET", _DEP, ctx), _dependabot, needs=("org",)),
    Quick("dependabot_add_repo", "Give Dependabot a Repository...", ("organization",), _ORG,
          "Let Dependabot read one more private repository.",
          ("PATCH /orgs/{org}/dependabot/repository-access",),
          _repo_change("repository_ids_to_add"),
          lambda _d, ctx: f"Dependabot may read {ctx['repository']} now.", tier="A",
          need="org:owner", asks=(Ask("repository", "The repository, as owner/name:"),),
          needs=("org",), live="needs Jeff: an organization he owns with a private repository"),
    Quick("dependabot_remove_repo", "Take a Repository from Dependabot...", ("organization",),
          _ORG, "Stop Dependabot reading a private repository.",
          ("PATCH /orgs/{org}/dependabot/repository-access",),
          _repo_change("repository_ids_to_remove"),
          lambda _d, ctx: f"Dependabot no longer reads {ctx['repository']}.", tier="A",
          need="org:owner", asks=(Ask("repository", "The repository, as owner/name:"),),
          needs=("org",), live="needs Jeff: an organization he owns with a private repository"),
    Quick("dependabot_default", "Dependabot's Default Access...", ("organization",), _ORG,
          "Which new repositories Dependabot may read without being given them.",
          ("PUT /orgs/{org}/dependabot/repository-access/default-level",),
          lambda api, ctx: call(api, "PUT", _DEP + "/default-level", ctx,
                                {"default_level": ctx["level"]}),
          lambda _d, ctx: f"New repositories' default is {ctx['level']} now.", tier="A",
          need="org:owner",
          asks=(Ask("level", "Dependabot may read, without being given them:", "choice",
                    ("Public repositories only", "Internal repositories too"),
                    ("public", "internal")),),
          needs=("org",), live="needs Jeff: an organization he owns"),
    Quick("make_outside_collaborator", "Make Someone an Outside Collaborator...",
          ("organization",), _ORG,
          "Take someone out of the organization's members but keep their repository access.",
          ("PUT /orgs/{org}/outside_collaborators/{username}",),
          lambda api, ctx: call(api, "PUT", "/orgs/{org}/outside_collaborators/{who}", ctx, {}),
          lambda _d, ctx: f"{ctx['who']} is an outside collaborator now.", tier="D",
          need="org:owner", asks=(Ask("who", "Their login:"),),
          confirm="Make {who} an outside collaborator? They stop being a member of the "
          "organization and its teams, and keep only their repositories.", typed="who",
          guard=lambda api, ctx: convert_problem(api, ctx["org"], ctx["who"]),
          needs=("org",), live="needs Jeff: a throwaway member of an organization he owns"),
    Quick("define_custom_property", "Define a Custom Property...", ("organization",), _ORG,
          "Add or change a property every repository here can be given.",
          ("PATCH /orgs/{org}/properties/schema",),
          _schema, lambda _d, ctx: f"Saved the property {ctx['prop']}.", tier="A",
          need="org:owner",
          asks=(Ask("prop", "The property's name:"),
                Ask("type", "What kind of value?", "choice",
                    ("Text", "One of a list", "Several of a list", "True or false"),
                    ("string", "single_select", "multi_select", "true_false")),
                Ask("required", "Must every repository have a value?", "yesno"),
                Ask("allowed", "For a list: its values, separated by commas:", optional=True),
                Ask("default", "Its default value (empty for none):", optional=True)),
          needs=("org",), live="needs Jeff: an organization he owns"),
    Quick("org_custom_property_values", "Set Repositories' Custom Property...",
          ("organization",), _ORG, "Give a custom property one value in several repositories.",
          ("PATCH /orgs/{org}/properties/values",),
          _values, lambda _d, ctx: f"Set {ctx['prop']} in {ctx['repos']}.", tier="V",
          need="org:owner",
          asks=(Ask("repos", "The repositories, separated by commas:"),
                Ask("prop", "The property's name:"),
                Ask("value", "Its value (empty clears it):", optional=True)),
          needs=("org",), live="needs Jeff: an organization with a custom property"),
    Quick("new_team", "New Team...", ("organization",), _ORG,
          "Make a team in this organization.",
          ("POST /orgs/{org}/teams",),
          _team, lambda data, _ctx: f"Made the team {(data or {}).get('name')}.", tier="A",
          need="org:member",
          asks=(Ask("team", "The team's name:"),
                Ask("privacy", "Who can see it?", "choice",
                    ("Every member of the organization", "Only its own members and owners"),
                    ("closed", "secret")),
                Ask("about", "What it is for (optional):", optional=True),
                Ask("parent", "The team it sits under, by its short name (empty for none):",
                    optional=True),
                Ask("notify", "Notify the team when it is mentioned?", "choice",
                    ("Yes", "No"), ("notifications_enabled", "notifications_disabled"))),
          needs=("org",), reload=True, live="needs Jeff: an organization he owns"),
    Quick("delete_team_now", "Delete Team...", ("team",), _TEAM,
          "Delete this team, and its child teams.",
          ("DELETE /orgs/{org}/teams/{team_slug}",),
          lambda api, ctx: call(api, "DELETE", "/orgs/{org}/teams/{key}", ctx),
          lambda _d, ctx: f"Deleted the team {ctx.get('name', '')}.", tier="D", need="org:owner",
          confirm="Delete the team {name}, and every team inside it? Its members keep their "
          "own access but lose what the team gave them.",
          needs=("org", "key"), reload=True, live="needs Jeff: a throwaway team"),
    Quick("team_invitations", "Pending Invitations", ("team",), _TEAM,
          "People invited to this team who have not joined yet.",
          ("GET /orgs/{org}/teams/{team_slug}/invitations",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/teams/{key}/invitations", ctx),
          _invitees, needs=("org", "key")),
    Quick("invitation_teams", "Teams It Adds To", ("resource",),
          frozenset({"resource", "resource:org_invitations"}),
          "The teams this invitation puts the person in when they accept.",
          ("GET /orgs/{org}/invitations/{invitation_id}/teams",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/invitations/{key}/teams", ctx),
          lambda data, _ctx: "Teams: " + (", ".join(
              str(t.get("name")) for t in data if isinstance(t, Mapping)
          ) if isinstance(data, list) and data else "none") + ".",
          needs=("org", "key")),
    Quick("accept_membership", "Accept Membership", ("organization",), _ORG,
          "Join this organization, when it has invited you.",
          ("PATCH /user/memberships/orgs/{org}",),
          lambda api, ctx: call(api, "PATCH", "/user/memberships/orgs/{org}", ctx,
                                {"state": "active"}),
          lambda _d, ctx: f"You are a member of {ctx['org']} now.", tier="A", need="sign_in",
          needs=("org",), live="not here: needs an invitation from another organization"),
    Quick("two_factor_off", "Members Without Two-Factor", ("organization",), _ORG,
          "Members who have not turned on two-factor sign-in. GitHub shows this to owners.",
          ("GET /orgs/{org}/members",),
          lambda api, ctx: call(api, "GET", "/orgs/{org}/members?filter=2fa_disabled"
                                "&per_page=100", ctx),
          _two_factor, report=True, needs=("org",)),
    Quick("my_org_activity", "My Activity Here", ("organization",), _ORG,
          "What you have done lately in this organization's repositories.",
          ("GET /users/{username}/events/orgs/{org}",),
          _events, _event_rows, report=True, needs=("org",)),
    Quick("project_new_view", "New View...", ("project",), _PROJECT,
          "Add a view to this Project: a table, a board or a roadmap.",
          ("POST /orgs/{org}/projectsV2/{project_number}/views",
           "POST /users/{user_id}/projectsV2/{project_number}/views"),
          _new_view, lambda _d, ctx: f"Added the view {ctx['view_name']}.", tier="V",
          need="sign_in",
          asks=(Ask("view_name", "The view's name:"),
                Ask("layout", "Its layout:", "choice", ("Table", "Board", "Roadmap"),
                    ("table", "board", "roadmap"))),
          needs=("owner", "pnumber"), live="needs Jeff: a throwaway Project"),
    Quick("project_view_items", "Items in a View...", ("project",), _PROJECT,
          "What one of this Project's views shows, in its order and with its filter.",
          ("GET /orgs/{org}/projectsV2/{project_number}/views/{view_number}/items",
           "GET /users/{username}/projectsV2/{project_number}/views/{view_number}/items"),
          _view_items, _item_rows, report=True, pick=_views, pick_key="view",
          pick_question="Which view?", needs=("owner", "pnumber", "key")),
    Quick("email_visibility", "Email Visibility...", ("node",), frozenset({"view"}),
          "Whether your primary email address shows on your profile and in your commits.",
          ("PATCH /user/email/visibility",),
          lambda api, ctx: call(api, "PATCH", "/user/email/visibility", ctx,
                                {"visibility": ctx["visibility"]}),
          lambda _d, ctx: f"Your primary email is {ctx['visibility']} now.", tier="V",
          need="sign_in", node="my_emails",
          asks=(Ask("visibility", "Your primary email address is:", "choice",
                    ("Public", "Private"), ("public", "private")),),
          live="needs Jeff: changes his own profile"),
    Quick("my_interaction_limits", "Interaction Limits", ("node",), frozenset({"view"}),
          "Whether you have limited who may comment in your repositories, and until when.",
          ("GET /user/interaction-limits",),
          lambda api, ctx: call(api, "GET", "/user/interaction-limits", ctx), _limits,
          node="my_profile"),
    Quick("limit_my_interactions", "Limit Interactions...", ("node",), frozenset({"view"}),
          "For a while, let only some people comment and open issues in all your repositories.",
          ("PUT /user/interaction-limits",),
          lambda api, ctx: call(api, "PUT", "/user/interaction-limits", ctx,
                                {"limit": ctx["limit"], "expiry": ctx["expiry"]}),
          lambda data, _ctx: _limits(data, _ctx), tier="V", need="sign_in", node="my_profile",
          asks=(Ask("limit", "Who may still take part?", "choice",
                    tuple(w for _k, w in _LIMITS), tuple(k for k, _w in _LIMITS)),
                Ask("expiry", "For how long?", "choice", _LAST_WORDS, _LASTS)),
          live="needs Jeff: changes every one of his repositories"),
    Quick("lift_my_interaction_limits", "Lift Interaction Limits", ("node",),
          frozenset({"view"}), "Let everyone take part in your repositories again.",
          ("DELETE /user/interaction-limits",),
          lambda api, ctx: call(api, "DELETE", "/user/interaction-limits", ctx),
          lambda _d, _ctx: "Lifted your interaction limits.", tier="V", need="sign_in",
          node="my_profile", live="needs Jeff: changes every one of his repositories"),
)  # fmt: skip
