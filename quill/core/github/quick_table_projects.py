"""Quick commands for a Project's insides, and for GitHub Sponsors, over GraphQL.

* A Project: **Rename a View...**, **Delete a View...**, **Rename a Field...**,
  **Add an Issue Field...**, **Edit a Draft...**, **Make a Draft an
  Issue...**, **Move an Item...**, **Edit a Status Update...**, **Delete a
  Status Update...**, **Delete a Workflow...**, **Share the Project...**,
  **Link a Team...**, **Unlink a Team...**.
* Your sponsorships: **Set Up a Sponsors Profile...**, **New Sponsor Tier...**,
  **Patreon Sponsorships...**. A sponsorship: **Sponsorship Preferences...**.
  A tier of yours: **Publish Tier** and **Retire Tier...**.

The view and issue-field mutations are newer than the schema QUILL's tests
know, so those read their input's field names from GitHub first and refuse
plainly when they are not the expected ones. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, gql
from quill.core.github.quick_table_discuss import input_fields, node_id

__all__ = ["PROJECT_QUICK"]

_PROJECT = frozenset({"project"})
_LIVE_PROJECT = "needs Jeff: a throwaway Project"


def _mutate(api: Any, name: str, fields: Mapping[str, Any]) -> Any:
    query = f"mutation($input: {name[0].upper()}{name[1:]}Input!) {{ {name}(input: $input) " + (
        "{ clientMutationId } }"
    )
    return gql(api, query, {"input": dict(fields)})


def _shaped(api: Any, name: str, wanted: Mapping[str, Any]) -> Any:
    """Send a newer mutation only when GitHub's input has every field QUILL fills in."""
    fields = input_fields(api, name[0].upper() + name[1:] + "Input")
    missing = [key for key in wanted if key not in fields]
    if missing:
        raise QuickError(
            "GitHub changed how this works, so QUILL did not send it. Use Open on GitHub "
            "and make the change in the Project there."
        )
    return _mutate(api, name, wanted)


def _part(api: Any, ctx: dict[str, str], part: str) -> list[Mapping[str, Any]]:
    queries = {
        "views": "views(first: 50) { nodes { id name number layout } }",
        "fields": "fields(first: 50) { nodes { ... on ProjectV2FieldCommon "
        "{ id name dataType } } }",
        "drafts": "items(first: 100) { nodes { id content { __typename ... on DraftIssue "
        "{ id title } } } }",
        "items": "items(first: 100) { nodes { id content { __typename ... on DraftIssue { title }"
        " ... on Issue { title number } ... on PullRequest { title number } } } }",
        "updates": "statusUpdates(first: 20) { nodes { id status body createdAt } }",
        "workflows": "workflows(first: 50) { nodes { id name enabled } }",
    }
    data = gql(api, "query($id: ID!) { node(id: $id) { ... on ProjectV2 { " + queries[part]
               + " } } }", {"id": ctx["key"]})  # fmt: skip
    found = (data.get("node") or {}).get("views" if part == "views" else
             "fields" if part == "fields" else "statusUpdates" if part == "updates" else
             "workflows" if part == "workflows" else "items") or {}  # fmt: skip
    return [n for n in found.get("nodes") or () if isinstance(n, Mapping)]


def _views(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [(str(v.get("name")), str(v["id"])) for v in _part(api, ctx, "views") if v.get("id")]


def _fields(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [
        (f"{f.get('name')} ({str(f.get('dataType') or '').lower()})", str(f["id"]))
        for f in _part(api, ctx, "fields")
        if f.get("id")
    ]


def _drafts(api: Any, ctx: dict[str, str], *, item: bool) -> list[tuple[str, str]]:
    out = []
    for n in _part(api, ctx, "drafts"):
        content = _content(n)
        if content.get("__typename") == "DraftIssue":
            out.append((str(content.get("title")), str(n["id"] if item else content.get("id"))))
    if not out:
        raise QuickError("This Project has no drafts.")
    return out


def _content(n: Mapping[str, Any]) -> Mapping[str, Any]:
    found = n.get("content")
    return found if isinstance(found, Mapping) else {}


def _title(n: Mapping[str, Any]) -> str:
    content = _content(n)
    number = f"#{content['number']} " if content.get("number") else ""
    return f"{number}{content.get('title') or 'An item'}"


def _items(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [(_title(n), str(n["id"])) for n in _part(api, ctx, "items") if n.get("id")]


def _move(api: Any, ctx: dict[str, str]) -> str:
    after = ctx.get("after", "").strip().lower()
    fields: dict[str, Any] = {"projectId": ctx["key"], "itemId": ctx["item"]}
    if after:
        found = [
            str(n["id"]) for n in _part(api, ctx, "items") if _title(n).lower().startswith(after)
        ]
        if not found:
            raise QuickError(f"No item here starts with {ctx['after']}.")
        fields["afterId"] = found[0]
    _mutate(api, "updateProjectV2ItemPosition", fields)
    return "Moved it." if after else "Moved it to the top."


def _updates(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [
        (f"{str(u.get('createdAt') or '')[:10]}, {str(u.get('status') or 'no status').lower()}: "
         f"{str(u.get('body') or '')[:50]}", str(u["id"]))
        for u in _part(api, ctx, "updates") if u.get("id")
    ]  # fmt: skip


def _workflows(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return [
        (f"{w.get('name')}{'' if w.get('enabled') else ', off'}", str(w["id"]))
        for w in _part(api, ctx, "workflows") if w.get("id")
    ]  # fmt: skip


def _user(api: Any, login: str) -> str:
    data = gql(api, "query($l: String!) { user(login: $l) { id } }", {"l": login.lstrip("@")})
    found = data.get("user")
    if not isinstance(found, Mapping) or not found.get("id"):
        raise QuickError(f"GitHub has nobody called {login}.")
    return str(found["id"])


def _team(api: Any, ctx: dict[str, str]) -> str:
    if ctx.get("owner_kind") != "orgs":
        raise QuickError("Only an organization's Project can be linked to a team.")
    data = gql(api, "query($o: String!, $s: String!) { organization(login: $o) { team(slug: $s)"
               " { id } } }", {"o": ctx["owner"], "s": ctx["team"]})  # fmt: skip
    found = (data.get("organization") or {}).get("team")
    if not isinstance(found, Mapping) or not found.get("id"):
        raise QuickError(f"{ctx['owner']} has no team called {ctx['team']}.")
    return str(found["id"])


def _say(text: str) -> Any:
    return lambda _d, _ctx: text


_SPONSOR_VIEW = frozenset({"view"})
_LIVE_SPONSOR = "not here: needs an account that takes sponsorships"

PROJECT_QUICK: tuple[Quick, ...] = (
    Quick("project_rename_view", "Rename a View...", ("project",), _PROJECT,
          "Give one of this Project's views another name.", ("graphql:updateProjectV2View",),
          lambda api, ctx: _shaped(api, "updateProjectV2View",
                                   {"viewId": ctx["view"], "name": ctx["view_name"]}),
          _say("Renamed the view."), tier="V", need="sign_in", pick=_views, pick_key="view",
          pick_question="Which view?", asks=(Ask("view_name", "Its new name:"),),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_delete_view", "Delete a View...", ("project",), _PROJECT,
          "Delete one of this Project's views; its items stay.",
          ("graphql:deleteProjectV2View",),
          lambda api, ctx: _shaped(api, "deleteProjectV2View", {"viewId": ctx["view"]}),
          _say("Deleted the view."), tier="D", need="sign_in", pick=_views, pick_key="view",
          pick_question="Which view?", confirm="Delete the view {view_label}? Its items stay.",
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_rename_field", "Rename a Field...", ("project",), _PROJECT,
          "Give one of this Project's fields another name.", ("graphql:updateProjectV2Field",),
          lambda api, ctx: _mutate(api, "updateProjectV2Field",
                                   {"fieldId": ctx["field"], "name": ctx["field_name"]}),
          _say("Renamed the field."), tier="V", need="sign_in", pick=_fields, pick_key="field",
          pick_question="Which field?", asks=(Ask("field_name", "Its new name:"),),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_issue_field", "Add an Issue Field...", ("project",), _PROJECT,
          "Add one of the organization's issue fields to this Project.",
          ("graphql:createProjectV2IssueField",),
          lambda api, ctx: _shaped(api, "createProjectV2IssueField",
                                   {"projectId": ctx["key"], "name": ctx["field_name"]}),
          lambda _d, ctx: f"Added the issue field {ctx['field_name']}.", tier="V",
          need="sign_in", asks=(Ask("field_name", "The issue field's name:"),),
          needs=("key",), live="needs Jeff: an organization with issue fields and a Project"),
    Quick("project_edit_draft", "Edit a Draft...", ("project",), _PROJECT,
          "Change a draft's title and text.", ("graphql:updateProjectV2DraftIssue",),
          lambda api, ctx: _mutate(api, "updateProjectV2DraftIssue", {
              "draftIssueId": ctx["draft"], "title": ctx["title"],
              **({"body": ctx["body"]} if ctx.get("body") else {})}),
          _say("Saved the draft."), tier="V", need="sign_in",
          pick=lambda api, ctx: _drafts(api, ctx, item=False), pick_key="draft",
          pick_question="Which draft?",
          asks=(Ask("title", "Its title:"),
                Ask("body", "Its text (empty keeps it):", "text", optional=True)),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_draft_to_issue", "Make a Draft an Issue...", ("project",), _PROJECT,
          "Turn a draft into a real issue in a repository; it stays in the Project.",
          ("graphql:convertProjectV2DraftIssueItemToIssue",),
          lambda api, ctx: _mutate(api, "convertProjectV2DraftIssueItemToIssue", {
              "itemId": ctx["draft"],
              "repositoryId": node_id(api, "repository", {"repo": ctx["repository"]})}),
          lambda _d, ctx: f"Made it an issue in {ctx['repository']}.", tier="V", need="sign_in",
          pick=lambda api, ctx: _drafts(api, ctx, item=True), pick_key="draft",
          pick_question="Which draft?",
          asks=(Ask("repository", "Into which repository, as owner/name?"),),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_move_item", "Move an Item...", ("project",), _PROJECT,
          "Put an item in another place in the Project's own order.",
          ("graphql:updateProjectV2ItemPosition",),
          _move, lambda said, _ctx: str(said), tier="O", need="sign_in", pick=_items,
          pick_key="item", pick_question="Which item?",
          asks=(Ask("after", "After which item? Type the start of its title, or nothing for "
                    "the top:", optional=True),),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_edit_status", "Edit a Status Update...", ("project",), _PROJECT,
          "Change a status update's status or text.", ("graphql:updateProjectV2StatusUpdate",),
          lambda api, ctx: _mutate(api, "updateProjectV2StatusUpdate", {
              "statusUpdateId": ctx["update"], "status": ctx["status"],
              **({"body": ctx["body"]} if ctx.get("body") else {})}),
          _say("Saved the status update."), tier="V", need="sign_in", pick=_updates,
          pick_key="update", pick_question="Which update?",
          asks=(Ask("status", "Its status:", "choice",
                    ("On track", "At risk", "Off track", "Complete", "Inactive"),
                    ("ON_TRACK", "AT_RISK", "OFF_TRACK", "COMPLETE", "INACTIVE")),
                Ask("body", "Its text (empty keeps it):", optional=True)),
          needs=("key",), live=_LIVE_PROJECT),
    Quick("project_delete_status", "Delete a Status Update...", ("project",), _PROJECT,
          "Delete one of this Project's status updates.",
          ("graphql:deleteProjectV2StatusUpdate",),
          lambda api, ctx: _mutate(api, "deleteProjectV2StatusUpdate",
                                   {"statusUpdateId": ctx["update"]}),
          _say("Deleted the status update."), tier="D", need="sign_in", pick=_updates,
          pick_key="update", pick_question="Which update?",
          confirm="Delete the status update {update_label}?", needs=("key",),
          live=_LIVE_PROJECT),
    Quick("project_delete_workflow", "Delete a Workflow...", ("project",), _PROJECT,
          "Delete one of this Project's automatic workflows.",
          ("graphql:deleteProjectV2Workflow",),
          lambda api, ctx: _mutate(api, "deleteProjectV2Workflow", {"workflowId": ctx["flow"]}),
          _say("Deleted the workflow."), tier="D", need="sign_in", pick=_workflows,
          pick_key="flow", pick_question="Which workflow?",
          confirm="Delete the workflow {flow_label}? Items it would have moved stay where "
          "they are.", needs=("key",), live=_LIVE_PROJECT),
    Quick("project_share", "Share the Project...", ("project",), _PROJECT,
          "Give a person a role in this Project, or take it away.",
          ("graphql:updateProjectV2Collaborators",),
          lambda api, ctx: _mutate(api, "updateProjectV2Collaborators", {
              "projectId": ctx["key"],
              "collaborators": [{"userId": _user(api, ctx["who"]), "role": ctx["role"]}]}),
          lambda _d, ctx: f"{ctx['who']} is set.", tier="A", need="sign_in",
          asks=(Ask("who", "Their login:"),
                Ask("role", "Their role:", "choice",
                    ("Read", "Write", "Admin", "No access"),
                    ("READER", "WRITER", "ADMIN", "NONE"))),
          needs=("key",), live="needs Jeff: a throwaway Project and a second account"),
    Quick("project_link_team", "Link a Team...", ("project",), _PROJECT,
          "Show this Project on a team's Projects.", ("graphql:linkProjectV2ToTeam",),
          lambda api, ctx: _mutate(api, "linkProjectV2ToTeam",
                                   {"projectId": ctx["key"], "teamId": _team(api, ctx)}),
          lambda _d, ctx: f"Linked the team {ctx['team']}.", tier="O", need="sign_in",
          asks=(Ask("team", "The team's short name (its slug):"),),
          needs=("key", "owner"), live="needs Jeff: an organization Project and a team"),
    Quick("project_unlink_team", "Unlink a Team...", ("project",), _PROJECT,
          "Take this Project off a team's Projects.", ("graphql:unlinkProjectV2FromTeam",),
          lambda api, ctx: _mutate(api, "unlinkProjectV2FromTeam",
                                   {"projectId": ctx["key"], "teamId": _team(api, ctx)}),
          lambda _d, ctx: f"Unlinked the team {ctx['team']}.", tier="O", need="sign_in",
          asks=(Ask("team", "The team's short name (its slug):"),),
          needs=("key", "owner"), live="needs Jeff: an organization Project linked to a team"),
    Quick("sponsors_profile", "Set Up a Sponsors Profile...", ("node",), _SPONSOR_VIEW,
          "Start taking sponsorships: GitHub reviews the profile before it shows.",
          ("graphql:createSponsorsListing",),
          lambda api, ctx: _mutate(api, "createSponsorsListing", {
              "fullDescription": ctx["about"],
              "residenceCountryOrRegionCode": ctx["country"].upper(),
              **({"contactEmail": ctx["email"]} if ctx.get("email") else {})}),
          _say("Sent your Sponsors profile. GitHub reviews it, then it shows."), tier="V",
          need="sign_in", node="sponsorships",
          asks=(Ask("about", "Your profile, as sponsors will read it:"),
                Ask("country", "The country you live in, as two letters (US, GB, CA):"),
                Ask("email", "An email address GitHub may write to (optional):",
                    optional=True)),
          live=_LIVE_SPONSOR),
    Quick("new_sponsor_tier", "New Sponsor Tier...", ("node",), _SPONSOR_VIEW,
          "Add a tier to your Sponsors profile, as a draft or published.",
          ("graphql:createSponsorsTier",),
          lambda api, ctx: _mutate(api, "createSponsorsTier", {
              "sponsorableLogin": ctx["me"] if ctx.get("me") else _viewer(api),
              "amount": int(ctx["amount"]), "description": ctx["about"],
              "isRecurring": ctx["monthly"] == "true", "publish": ctx["publish"] == "true"}),
          lambda _d, ctx: f"Added a ${ctx['amount']} tier.", tier="V", need="sign_in",
          node="sponsorships",
          asks=(Ask("amount", "Its price, in whole US dollars:", "number"),
                Ask("about", "What sponsors get:"),
                Ask("monthly", "Every month (No: once)?", "yesno"),
                Ask("publish", "Publish it now (No: keep it as a draft)?", "yesno")),
          live=_LIVE_SPONSOR),
    Quick("patreon_sponsorships", "Patreon Sponsorships...", ("node",), _SPONSOR_VIEW,
          "Let sponsors pay through Patreon as well as GitHub.",
          ("graphql:updatePatreonSponsorability",),
          lambda api, ctx: _mutate(api, "updatePatreonSponsorability", {
              "sponsorableLogin": _viewer(api),
              "enablePatreonSponsorships": ctx["on"] == "true"}),
          lambda _d, ctx: "Patreon sponsorships are " + ("on." if ctx["on"] == "true" else "off."),
          tier="V", need="sign_in", node="sponsorships",
          asks=(Ask("on", "Take sponsorships through Patreon?", "yesno"),),
          live=_LIVE_SPONSOR),
    Quick("sponsorship_preferences", "Sponsorship Preferences...", ("sponsorship",),
          frozenset({"sponsorship"}), "Whether people see this sponsorship, and whether "
          "you get the maintainer's emails.", ("graphql:updateSponsorshipPreferences",),
          lambda api, ctx: _mutate(api, "updateSponsorshipPreferences", {
              "sponsorableLogin": ctx["key"], "privacyLevel": ctx["privacy"],
              "receiveEmails": ctx["emails"] == "true"}),
          _say("Saved your preferences for this sponsorship."), tier="O", need="sign_in",
          asks=(Ask("privacy", "Who may see that you sponsor them?", "choice",
                    ("Everyone", "Only you and them"), ("PUBLIC", "PRIVATE")),
                Ask("emails", "Get the emails they send their sponsors?", "yesno")),
          needs=("key",), live="needs Jeff: changes one of his sponsorships"),
    Quick("publish_sponsor_tier", "Publish Tier", ("sponsor_tier",),
          frozenset({"sponsor_tier"}), "Publish one of your draft tiers.",
          ("graphql:publishSponsorsTier",),
          lambda api, ctx: _mutate(api, "publishSponsorsTier", {"tierId": ctx["key"]}),
          _say("Published the tier."), tier="V", need="sign_in", needs=("key",),
          live=_LIVE_SPONSOR),
    Quick("retire_sponsor_tier", "Retire Tier...", ("sponsor_tier",),
          frozenset({"sponsor_tier"}), "Stop offering one of your tiers; sponsors on it stay.",
          ("graphql:retireSponsorsTier",),
          lambda api, ctx: _mutate(api, "retireSponsorsTier", {"tierId": ctx["key"]}),
          _say("Retired the tier. Its sponsors keep it."), tier="D", need="sign_in",
          confirm="Retire the tier {name}? New sponsors cannot choose it; its sponsors keep it.",
          needs=("key",), live=_LIVE_SPONSOR),
)  # fmt: skip


def _viewer(api: Any) -> str:
    data = gql(api, "query { viewer { login } }", {})
    return str((data.get("viewer") or {}).get("login") or "")
