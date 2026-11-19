"""Quick commands over GraphQL: discussions, closing references, environments and more.

* A discussion: **Close Discussion...**, **Reopen Discussion**, **Delete
  Discussion...**, **Upvote**, **Remove Upvote**, **Vote...** (in its poll),
  **Edit a Comment...**, **Delete a Comment...**.
* An issue: **Link a Pull Request That Closes It...** and **Unlink a Pull
  Request...**.
* An environment: **Pin Environment**, **Unpin Environment**, **Move
  Environment...**.
* A repository or an organization: **Require Sign-off on Web Commits...**. An
  organization: **Follow Organization** and **Unfollow Organization**. A
  repository: **Sponsor Links** and **Dependency Manifests**.

GitHub added the closing-reference mutations after the schema QUILL's
tests know, so those two read the input's field names from GitHub itself
first (:func:`input_fields`) and refuse plainly if they are not the ones
expected. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.discussion_actions import POLL_FIELDS
from quill.core.github.quick_actions import Ask, Quick, QuickError, bulleted, gql

__all__ = ["DISCUSS_QUICK", "input_fields", "node_id"]


def input_fields(api: Any, type_name: str) -> set[str]:
    """The field names of a GraphQL input type, as GitHub's schema has them now."""
    data = gql(api, "query($n: String!) { __type(name: $n) { inputFields { name } } }",
               {"n": type_name})  # fmt: skip
    found = (data.get("__type") or {}).get("inputFields") or []
    return {str(f.get("name")) for f in found if isinstance(f, Mapping)}


_IDS = {
    "repository": "query($o: String!, $n: String!) { repository(owner: $o, name: $n) { id } }",
    "discussion": "query($o: String!, $n: String!, $x: Int!) { repository(owner: $o, name: $n) "
    "{ discussion(number: $x) { id } } }",
    "issue": "query($o: String!, $n: String!, $x: Int!) { repository(owner: $o, name: $n) "
    "{ issue(number: $x) { id } } }",
    "pull": "query($o: String!, $n: String!, $x: Int!) { repository(owner: $o, name: $n) "
    "{ pullRequest(number: $x) { id } } }",
    "environment": "query($o: String!, $n: String!, $e: String!) { repository(owner: $o, "
    "name: $n) { environment(name: $e) { id } } }",
    "organization": "query($l: String!) { organization(login: $l) { id } }",
}


def node_id(api: Any, kind: str, ctx: Mapping[str, str], number: str = "") -> str:
    """The node id GraphQL needs, for a repository, its discussion, issue or more."""
    owner, _sep, name = ctx.get("repo", "").partition("/")
    variables: dict[str, Any] = {"o": owner, "n": name}
    if kind in ("discussion", "issue", "pull"):
        variables["x"] = int(number or ctx.get("key") or ctx.get("number") or 0)
    if kind == "environment":
        variables["e"] = ctx.get("key", "")
    if kind == "organization":
        variables = {"l": ctx.get("org", "")}
    data = gql(api, _IDS[kind], variables)
    found: Any = data.get("organization") if kind == "organization" else data.get("repository")
    if kind == "discussion":
        found = (found or {}).get("discussion")
    elif kind == "issue":
        found = (found or {}).get("issue")
    elif kind == "pull":
        found = (found or {}).get("pullRequest")
    elif kind == "environment":
        found = (found or {}).get("environment")
    if not isinstance(found, Mapping) or not found.get("id"):
        raise QuickError(f"GitHub could not find that {kind}.")
    return str(found["id"])


def _mutate(api: Any, name: str, fields: Mapping[str, Any]) -> Any:
    query = f"mutation($input: {name[0].upper()}{name[1:]}Input!) {{ {name}(input: $input) " + (
        "{ clientMutationId } }"
    )
    return gql(api, query, {"input": dict(fields)})


def _discussion(api: Any, ctx: dict[str, str]) -> str:
    return node_id(api, "discussion", ctx)


def _comments(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    owner, _s, name = ctx["repo"].partition("/")
    query = (
        "query($o: String!, $n: String!, $x: Int!) { repository(owner: $o, name: $n) { "
        "discussion(number: $x) { comments(first: 50) { nodes { id body viewerCanUpdate "
        "viewerCanDelete author { login } } } } } }"
    )
    data = gql(api, query, {"o": owner, "n": name, "x": int(ctx["key"])})
    nodes = (((data.get("repository") or {}).get("discussion") or {}).get("comments") or {}).get(
        "nodes"
    ) or []
    want = "viewerCanUpdate" if ctx.get("_want") != "delete" else "viewerCanDelete"
    return [
        (f"{(c.get('author') or {}).get('login')}: {str(c.get('body') or '')[:60]}", str(c["id"]))
        for c in nodes
        if isinstance(c, Mapping) and c.get(want)
    ]


def _deletable(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    return _comments(api, {**ctx, "_want": "delete"})


def _poll(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    """Vote...'s choices: each option with its votes, or why you cannot vote."""
    owner, _s, name = ctx["repo"].partition("/")
    query = (
        "query($o: String!, $n: String!, $x: Int!) { repository(owner: $o, name: $n) { "
        f"discussion(number: $x) {{ {POLL_FIELDS} }} }} }}"
    )
    data = gql(api, query, {"o": owner, "n": name, "x": int(ctx["key"])})
    poll = ((data.get("repository") or {}).get("discussion") or {}).get("poll")
    if not isinstance(poll, Mapping):
        raise QuickError("This discussion has no poll.")
    nodes = [o for o in (poll.get("options") or {}).get("nodes") or () if isinstance(o, Mapping)]
    mine = [str(o.get("option")) for o in nodes if o.get("viewerHasVoted")]
    if mine:
        raise QuickError(f"You have already voted in this poll, for {', '.join(mine)}.")
    if not poll.get("viewerCanVote"):
        raise QuickError("GitHub says you cannot vote in this poll.")
    return [
        (f"{o.get('option')} ({o.get('totalVoteCount', 0)} votes)", str(o["id"]))
        for o in nodes
        if o.get("id")
    ]


def _vote(api: Any, ctx: dict[str, str]) -> Any:
    query = (
        "mutation($input: AddDiscussionPollVoteInput!) { addDiscussionPollVote(input: $input) "
        "{ pollOption { option totalVoteCount viewerHasVoted poll { totalVoteCount } } } }"
    )
    return gql(api, query, {"input": {"pollOptionId": ctx["option"]}})


def _voted(data: Any, ctx: Mapping[str, str]) -> str:
    """The outcome, once, with the new count GitHub sends back."""
    option = ((data or {}).get("addDiscussionPollVote") or {}).get("pollOption") or {}
    if not option.get("viewerHasVoted", True):
        raise QuickError("GitHub did not record the vote.")
    name = str(option.get("option") or ctx.get("option_label") or "that answer")
    votes = int(option.get("totalVoteCount") or 0)
    total = int((option.get("poll") or {}).get("totalVoteCount") or votes)
    noun = "vote" if votes == 1 else "votes"
    return f"Voted for {name}. It has {votes} {noun} now, of {total} in all."


def _closing(add: bool) -> Any:
    name = "addCloseIssueReferences" if add else "removeCloseIssueReferences"

    def run(api: Any, ctx: dict[str, str]) -> str:
        fields = input_fields(api, name[0].upper() + name[1:] + "Input")
        issue_key = next((f for f in ("issueId", "subjectId", "id") if f in fields), "")
        pulls_key = next(
            (f for f in sorted(fields) if "pullrequest" in f.lower() and f.endswith("Ids")), ""
        )
        if not issue_key or not pulls_key:
            raise QuickError(
                "GitHub changed how this works, so QUILL did not send it. Use Open on GitHub, "
                "then Development in the issue's sidebar."
            )
        numbers = [n.strip().lstrip("#") for n in ctx["pulls"].split(",") if n.strip()]
        if not all(n.isdigit() for n in numbers):
            raise QuickError("Type pull request numbers, such as 12, 15.")
        ids = [node_id(api, "pull", ctx, n) for n in numbers]
        _mutate(api, name, {issue_key: node_id(api, "issue", ctx), pulls_key: ids})
        verb = "now close" if add else "no longer close"
        return f"Pull requests {', '.join('#' + n for n in numbers)} {verb} this issue."

    return run


def _environment(api: Any, ctx: dict[str, str]) -> str:
    return node_id(api, "environment", ctx)


def _signoff(api: Any, ctx: dict[str, str]) -> str:
    required = ctx["required"] == "true"
    if ctx.get("repo") and ctx.get("_scope") != "org":
        _mutate(api, "updateRepositoryWebCommitSignoffSetting", {
            "repositoryId": node_id(api, "repository", ctx), "webCommitSignoffRequired": required,
        })  # fmt: skip
    else:
        _mutate(api, "updateOrganizationWebCommitSignoffSetting", {
            "organizationId": node_id(api, "organization", ctx),
            "webCommitSignoffRequired": required,
        })  # fmt: skip
    return (
        "Commits made on GitHub's site now need a sign-off."
        if required
        else "Commits made on GitHub's site no longer need a sign-off."
    )


def _funding(api: Any, ctx: dict[str, str]) -> str:
    owner, _s, name = ctx["repo"].partition("/")
    data = gql(api, "query($o: String!, $n: String!) { repository(owner: $o, name: $n) { "
               "fundingLinks { platform url } } }", {"o": owner, "n": name})  # fmt: skip
    links = (data.get("repository") or {}).get("fundingLinks") or []
    rows = [
        f"{str(x.get('platform') or '').replace('_', ' ').title()}: {x.get('url')}"
        for x in links if isinstance(x, Mapping)
    ]  # fmt: skip
    return bulleted(rows, "This repository has no sponsor links (a FUNDING.yml file).")


def _manifests(api: Any, ctx: dict[str, str]) -> str:
    owner, _s, name = ctx["repo"].partition("/")
    query = (
        "query($o: String!, $n: String!) { repository(owner: $o, name: $n) { "
        "dependencyGraphManifests(first: 100) { nodes { filename dependenciesCount "
        "exceedsMaxSize parseable } } } }"
    )
    data = gql(api, query, {"o": owner, "n": name})
    nodes = ((data.get("repository") or {}).get("dependencyGraphManifests") or {}).get("nodes")
    rows = [
        f"{m.get('filename')}: {m.get('dependenciesCount')} dependencies"
        + ("" if m.get("parseable", True) else ", which GitHub could not read")
        + (", too large to read whole" if m.get("exceedsMaxSize") else "")
        for m in nodes or ()
        if isinstance(m, Mapping)
    ]
    return bulleted(rows, "GitHub found no manifest files here.")


_DISC = frozenset({"discussion"})
_ENV = frozenset({"environment"})
_LIVE_DISC = "needs Jeff: a throwaway discussion on the test repository"


def _say(text: str) -> Any:
    return lambda _d, _ctx: text


DISCUSS_QUICK: tuple[Quick, ...] = (
    Quick("close_discussion", "Close Discussion...", ("discussion",), _DISC,
          "Close it as resolved, outdated or a duplicate.",
          ("graphql:closeDiscussion",),
          lambda api, ctx: _mutate(api, "closeDiscussion", {
              "discussionId": _discussion(api, ctx), "reason": ctx["reason"]}),
          _say("Closed the discussion."), tier="V", need="repo:triage",
          asks=(Ask("reason", "Close it as:", "choice", ("Resolved", "Outdated", "A duplicate"),
                    ("RESOLVED", "OUTDATED", "DUPLICATE")),),
          needs=("repo", "key"), reload=True, live=_LIVE_DISC),
    Quick("reopen_discussion", "Reopen Discussion", ("discussion",), _DISC,
          "Open a closed discussion again.", ("graphql:reopenDiscussion",),
          lambda api, ctx: _mutate(
              api, "reopenDiscussion", {"discussionId": _discussion(api, ctx)}
          ),
          _say("Reopened the discussion."), tier="V", need="repo:triage", needs=("repo", "key"),
          reload=True, live=_LIVE_DISC),
    Quick("delete_discussion", "Delete Discussion...", ("discussion",), _DISC,
          "Delete it and every comment in it, for good.", ("graphql:deleteDiscussion",),
          lambda api, ctx: _mutate(api, "deleteDiscussion", {"id": _discussion(api, ctx)}),
          _say("Deleted the discussion."), tier="D", need="repo:admin",
          confirm="Delete the discussion {name}, with every comment in it? This cannot be "
          "undone.", needs=("repo", "key"), reload=True, live=_LIVE_DISC),
    Quick("upvote_discussion", "Upvote", ("discussion",), _DISC,
          "Add your upvote, which helps it rise in the list.", ("graphql:addUpvote",),
          lambda api, ctx: _mutate(api, "addUpvote", {"subjectId": _discussion(api, ctx)}),
          _say("Upvoted."), tier="O", need="sign_in", needs=("repo", "key"), live=_LIVE_DISC),
    Quick("remove_upvote", "Remove Upvote", ("discussion",), _DISC,
          "Take your upvote back.", ("graphql:removeUpvote",),
          lambda api, ctx: _mutate(api, "removeUpvote", {"subjectId": _discussion(api, ctx)}),
          _say("Removed your upvote."), tier="O", need="sign_in", needs=("repo", "key"),
          live=_LIVE_DISC),
    Quick("poll_vote", "Vote...", ("discussion",), _DISC,
          "Choose an answer in this discussion's poll and cast your vote; says the new count.",
          ("graphql:addDiscussionPollVote",), _vote, _voted, tier="O",
          need="sign_in", pick=_poll, pick_key="option", pick_question="Your answer:",
          needs=("repo", "key"), live="needs Jeff: a discussion with a poll"),
    Quick("edit_discussion_comment", "Edit a Comment...", ("discussion",), _DISC,
          "Change a comment you may edit.", ("graphql:updateDiscussionComment",),
          lambda api, ctx: _mutate(api, "updateDiscussionComment", {
              "commentId": ctx["comment"], "body": ctx["body"]}),
          _say("Saved the comment."), tier="V", need="sign_in", pick=_comments,
          pick_key="comment", pick_question="Which comment?",
          asks=(Ask("body", "Its new text:"),), needs=("repo", "key"), live=_LIVE_DISC),
    Quick("delete_discussion_comment", "Delete a Comment...", ("discussion",), _DISC,
          "Delete a comment you may delete.", ("graphql:deleteDiscussionComment",),
          lambda api, ctx: _mutate(api, "deleteDiscussionComment", {"id": ctx["comment"]}),
          _say("Deleted the comment."), tier="D", need="sign_in", pick=_deletable,
          pick_key="comment", pick_question="Which comment?",
          confirm="Delete the comment {comment_label}? This cannot be undone.",
          needs=("repo", "key"), live=_LIVE_DISC),
    Quick("link_closing_pull", "Link a Pull Request That Closes It...", ("issue",),
          frozenset({"item"}), "Say which pull requests close this issue when they merge.",
          ("graphql:addCloseIssueReferences",),
          _closing(True), lambda said, _ctx: str(said), tier="O", need="repo:triage",
          asks=(Ask("pulls", "Pull request numbers, separated by commas:"),),
          needs=("repo", "number"), live="needs Jeff: a throwaway issue and pull request"),
    Quick("unlink_closing_pull", "Unlink a Pull Request...", ("issue",), frozenset({"item"}),
          "Take a pull request off the ones that close this issue.",
          ("graphql:removeCloseIssueReferences",),
          _closing(False), lambda said, _ctx: str(said), tier="O", need="repo:triage",
          asks=(Ask("pulls", "Pull request numbers, separated by commas:"),),
          needs=("repo", "number"), live="needs Jeff: a throwaway issue and pull request"),
    Quick("pin_environment", "Pin Environment", ("environment",), _ENV,
          "Keep this environment at the top of the repository's Deployments.",
          ("graphql:pinEnvironment",),
          lambda api, ctx: _mutate(api, "pinEnvironment", {
              "environmentId": _environment(api, ctx), "pinned": True}),
          _say("Pinned it."), tier="O", need="repo:admin", needs=("repo", "key"), reload=True,
          live="needs Jeff: an environment on the test repository"),
    Quick("unpin_environment", "Unpin Environment", ("environment",), _ENV,
          "Let this environment take its usual place again.", ("graphql:pinEnvironment",),
          lambda api, ctx: _mutate(api, "pinEnvironment", {
              "environmentId": _environment(api, ctx), "pinned": False}),
          _say("Unpinned it."), tier="O", need="repo:admin", needs=("repo", "key"), reload=True,
          live="needs Jeff: a pinned environment on the test repository"),
    Quick("move_environment", "Move Environment...", ("environment",), _ENV,
          "Put this pinned environment at another place among the pinned ones.",
          ("graphql:reorderEnvironment",),
          lambda api, ctx: _mutate(api, "reorderEnvironment", {
              "environmentId": _environment(api, ctx), "position": int(ctx["position"]) - 1}),
          lambda _d, ctx: f"Moved it to place {ctx['position']}.", tier="O", need="repo:admin",
          asks=(Ask("position", "Its place among the pinned environments, 1 first:", "number"),),
          needs=("repo", "key"), reload=True, live="needs Jeff: two pinned environments"),
    Quick("repo_web_signoff", "Require Sign-off on Web Commits...", ("repository",),
          frozenset({"repo"}), "Whether commits made on GitHub's site must carry a sign-off.",
          ("graphql:updateRepositoryWebCommitSignoffSetting",),
          _signoff, lambda said, _ctx: str(said), tier="V", need="repo:admin",
          asks=(Ask("required", "Require a sign-off on commits made on GitHub's site?",
                    "yesno"),),
          needs=("repo",), live="needs Jeff: changes the test repository's settings"),
    Quick("org_web_signoff", "Require Sign-off on Web Commits...", ("organization",),
          frozenset({"org"}), "Whether commits made on GitHub's site, in every repository here, "
          "must carry a sign-off.", ("graphql:updateOrganizationWebCommitSignoffSetting",),
          lambda api, ctx: _signoff(api, {**ctx, "_scope": "org"}),
          lambda said, _ctx: str(said), tier="A", need="org:owner",
          asks=(Ask("required", "Require a sign-off on commits made on GitHub's site?",
                    "yesno"),),
          needs=("org",), live="needs Jeff: an organization he owns"),
    Quick("follow_org", "Follow Organization", ("organization",), frozenset({"org"}),
          "See this organization's public activity in your feed.",
          ("graphql:followOrganization",),
          lambda api, ctx: _mutate(api, "followOrganization", {
              "organizationId": node_id(api, "organization", ctx)}),
          lambda _d, ctx: f"You follow {ctx['org']} now.", tier="O", need="sign_in",
          needs=("org",), live="needs Jeff: changes whom he follows"),
    Quick("unfollow_org", "Unfollow Organization", ("organization",), frozenset({"org"}),
          "Stop seeing this organization in your feed.", ("graphql:unfollowOrganization",),
          lambda api, ctx: _mutate(api, "unfollowOrganization", {
              "organizationId": node_id(api, "organization", ctx)}),
          lambda _d, ctx: f"You no longer follow {ctx['org']}.", tier="O", need="sign_in",
          needs=("org",), live="needs Jeff: changes whom he follows"),
    Quick("funding_links", "Sponsor Links", ("repository",), frozenset({"repo"}),
          "Where people can sponsor this repository, from its FUNDING.yml.",
          ("graphql:fundingLinks",), _funding, lambda said, _ctx: str(said), needs=("repo",)),
    Quick("dependency_manifests", "Dependency Manifests", ("repository",), frozenset({"repo"}),
          "Each manifest file GitHub reads dependencies from, and how many it found.",
          ("graphql:dependencyGraphManifests",), _manifests, lambda said, _ctx: str(said),
          report=True, needs=("repo",)),
)  # fmt: skip
