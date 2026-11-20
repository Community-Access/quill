"""You and the object, as context-menu rows (GitHub PRD 16.7).

Each relationship on a You page is also a row on the object's context menu,
and each says its outcome in one sentence:

* **Subscribe or Unsubscribe...** on an issue, a pull request, a discussion
  or a commit: all activity, or only when you take part or are mentioned
  (``updateSubscription``, the mutation the You page's Subscribed sends).
* **Block or Unblock...** on a person (``PUT`` or ``DELETE /user/blocks``,
  as the person's You page does).
* **Fork...** on a repository (``POST /repos/{owner}/{repo}/forks``).
* **Block from Organization...** on an organization, and on a member in its
  Members list (``PUT /orgs/{org}/blocks/{username}``); unblocking is the
  organization's Blocked Users list.
* **Leave Organization...** (``DELETE /orgs/{org}/memberships/{you}``) and
  **Your Invitation** on an organization. GitHub's API can accept an
  organization's invitation (Accept Membership) but not decline one, so
  Your Invitation says so and gives the page where GitHub declines it.
* **React to a Comment...** on an issue or a pull request (its conversation
  and its review comments) and on a discussion: choosing a reaction you
  gave takes it back, choosing another adds it. GitHub reacts to a commit's
  comments (React to a Commit Comment...), never to a commit itself.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.quick_actions import Ask, Quick, QuickError, call, gql

__all__ = ["YOU_QUICK"]

_ITEMS = ("issue", "pull_request", "discussion", "commit")
_STATES = ("SUBSCRIBED", "UNSUBSCRIBED")
_STATE_WORDS = ("All activity", "Only when you take part or are mentioned")
_REACTIONS = ("+1", "-1", "laugh", "confused", "heart", "hooray", "rocket", "eyes")
_ENUM = ("THUMBS_UP", "THUMBS_DOWN", "LAUGH", "CONFUSED", "HEART", "HOORAY", "ROCKET", "EYES")
_WORDS = ("thumbs up", "thumbs down", "laugh", "confused", "heart", "hooray", "rocket", "eyes")
_CHOICES = tuple(word.capitalize() for word in _WORDS)

_SUBSCRIBE = (
    "mutation($id:ID!,$state:SubscriptionState!){updateSubscription(input:"
    "{subscribableId:$id,state:$state}){subscribable{id viewerSubscription}}}"
)
_TARGET = (
    "query($o:String!,$n:String!,$x:Int!){repository(owner:$o,name:$n){"
    "issueOrPullRequest(number:$x){... on Issue{id} ... on PullRequest{id}}}}"
)
_DISCUSSION = (
    "query($o:String!,$n:String!,$x:Int!){repository(owner:$o,name:$n){discussion(number:$x){id}}}"
)
_COMMIT = (
    "query($o:String!,$n:String!,$x:String!){repository(owner:$o,name:$n){"
    "object(expression:$x){... on Commit{id}}}}"
)


def _subscribable(api: Any, ctx: Mapping[str, str]) -> str:
    """The node id of the issue, pull request, discussion or commit the row is."""
    owner, _sep, name = ctx.get("repo", "").partition("/")
    if ctx.get("sha"):
        data = gql(api, _COMMIT, {"o": owner, "n": name, "x": ctx["sha"]})
        found = (data.get("repository") or {}).get("object")
    elif ctx.get("number"):
        data = gql(api, _TARGET, {"o": owner, "n": name, "x": int(ctx["number"])})
        found = (data.get("repository") or {}).get("issueOrPullRequest")
    elif ctx.get("key", "").isdigit():
        data = gql(api, _DISCUSSION, {"o": owner, "n": name, "x": int(ctx["key"])})
        found = (data.get("repository") or {}).get("discussion")
    else:
        raise QuickError("Subscribe is for an issue, a pull request, a discussion or a commit.")
    if not isinstance(found, Mapping) or not found.get("id"):
        raise QuickError("GitHub could not find that to subscribe to.")
    return str(found["id"])


def _subscribe(api: Any, ctx: dict[str, str]) -> str:
    data = gql(api, _SUBSCRIBE, {"id": _subscribable(api, ctx), "state": ctx["state"]})
    found = ((data.get("updateSubscription") or {}).get("subscribable") or {}).get(
        "viewerSubscription"
    )
    return str(found or ctx["state"])


def _subscribed(state: Any, ctx: dict[str, str]) -> str:
    name = ctx.get("name") or "it"
    if state == "SUBSCRIBED":
        return f"Subscribed to {name}: you hear of all its activity."
    if state == "UNSUBSCRIBED":
        return f"Unsubscribed from {name}: you hear of it only when you take part or are mentioned."
    return f"GitHub says your subscription to {name} is {str(state).lower()}."


def _block(api: Any, ctx: dict[str, str]) -> str:
    method = "PUT" if ctx["block"] == "true" else "DELETE"
    call(api, method, "/user/blocks/{login}", ctx)
    return ctx["block"]


def _blocked(answer: Any, ctx: dict[str, str]) -> str:
    login = ctx["login"]
    if answer == "true":
        return (
            f"Blocked {login}: they cannot follow you, or open issues, comment or react in "
            "your repositories."
        )
    return f"Unblocked {login}."


def _fork(api: Any, ctx: dict[str, str]) -> Any:
    body: dict[str, object] = {}
    if ctx.get("organization", "").strip():
        body["organization"] = ctx["organization"].strip()
    return call(api, "POST", "/repos/{repo}/forks", ctx, body)


def _forked(data: Any, ctx: dict[str, str]) -> str:
    made = data.get("full_name") if isinstance(data, Mapping) else ""
    where = f" to {made}" if made else ""
    return f"Forked {ctx['repo']}{where}. GitHub copies its files in a moment."


def _org_block(api: Any, ctx: dict[str, str]) -> str:
    who = (ctx.get("who") or ctx.get("key") or "").strip().lstrip("@")
    if not who:
        raise QuickError("Type the login of the account to block.")
    call(api, "PUT", "/orgs/{org}/blocks/{who}", {**ctx, "who": who})
    return who


def _me(api: Any, ctx: Mapping[str, str]) -> str:
    me = call(api, "GET", "/user", ctx)
    login = me.get("login") if isinstance(me, Mapping) else ""
    if not login:
        raise QuickError("GitHub did not say who you are signed in as.")
    return str(login)


def _leave(api: Any, ctx: dict[str, str]) -> str:
    me = _me(api, ctx)
    call(api, "DELETE", "/orgs/{org}/memberships/{me}", {**ctx, "me": me})
    return me


def _invitation(data: Any, ctx: dict[str, str]) -> str:
    org = ctx["org"]
    data = data if isinstance(data, Mapping) else {}
    state, role = str(data.get("state") or ""), str(data.get("role") or "member")
    if state == "pending":
        return (
            f"{org} has invited you as {'an' if role == 'admin' else 'a'} {role}. Accept "
            "Membership joins it. GitHub's API cannot decline an invitation, so decline it on "
            f"GitHub: https://github.com/orgs/{org}/invitation"
        )
    if state == "active":
        return f"You are already a member of {org}, as {role}; there is no invitation to answer."
    return f"GitHub shows no invitation from {org} for you."


def _invitation_read(api: Any, ctx: dict[str, str]) -> Any:
    try:
        return call(api, "GET", "/user/memberships/orgs/{org}", ctx)
    except QuickError:
        return {}  # 404: no invitation and no membership


# -- reactions on comments ---------------------------------------------------------------


def _short(user: Any, body: Any) -> str:
    login = (user or {}).get("login") if isinstance(user, Mapping) else ""
    return f"{login or 'someone'}: {str(body or '').strip()[:60]}"


def _item_comments(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    """The conversation's comments, then (on a pull request) its review comments."""
    found: list[tuple[str, str]] = []
    rows = call(api, "GET", "/repos/{repo}/issues/{number}/comments?per_page=100", ctx)
    for c in rows if isinstance(rows, list) else ():
        if isinstance(c, Mapping) and c.get("id"):
            found.append((_short(c.get("user"), c.get("body")), f"issues/{c['id']}"))
    try:
        review = call(api, "GET", "/repos/{repo}/pulls/{number}/comments?per_page=100", ctx)
    except QuickError:
        review = []  # an issue has no review comments
    for c in review if isinstance(review, list) else ():
        if isinstance(c, Mapping) and c.get("id"):
            label = _short(c.get("user"), c.get("body"))
            found.append((f"{label} (on {c.get('path') or 'a line'})", f"pulls/{c['id']}"))
    return found


def _react_item(api: Any, ctx: dict[str, str]) -> str:
    kind, _sep, comment = ctx["comment"].partition("/")
    if kind not in ("issues", "pulls"):
        raise QuickError("That is not a comment GitHub can react to.")
    where = {**ctx, "c": comment}
    path = "/repos/{repo}/" + kind + "/comments/{c}/reactions"
    me = _me(api, ctx)
    rows = call(api, "GET", path + "?per_page=100", where)
    mine = next(
        (
            r
            for r in (rows if isinstance(rows, list) else ())
            if isinstance(r, Mapping)
            and r.get("content") == ctx["reaction"]
            and (r.get("user") or {}).get("login") == me
        ),
        None,
    )
    if mine is not None:
        call(api, "DELETE", path + "/{r}", {**where, "r": str(mine.get("id"))})
        return "removed"
    call(api, "POST", path, where, {"content": ctx["reaction"]})
    return "added"


def _reacted(done: Any, ctx: dict[str, str]) -> str:
    word = _WORDS[_REACTIONS.index(ctx["reaction"])] if ctx.get("reaction") in _REACTIONS else ""
    word = word or _WORDS[_ENUM.index(ctx["reaction"])]
    whose = ctx.get("comment_label", "the comment").split(":", 1)[0]
    if done == "removed":
        return f"Took back your {word} from {whose}'s comment."
    return f"Added a {word} to {whose}'s comment."


_DISCUSSION_COMMENTS = (
    "query($o:String!,$n:String!,$x:Int!){repository(owner:$o,name:$n){discussion(number:$x){"
    "comments(first:50){nodes{id body author{login} replies(first:20){nodes{id body "
    "author{login}}}}}}}}"
)
_GROUPS = "query($id:ID!){node(id:$id){... on Reactable{reactionGroups{content viewerHasReacted}}}}"
_ADD = (
    "mutation($id:ID!,$c:ReactionContent!){addReaction(input:{subjectId:$id,content:$c})"
    "{reaction{content}}}"
)
_REMOVE = (
    "mutation($id:ID!,$c:ReactionContent!){removeReaction(input:{subjectId:$id,content:$c})"
    "{reaction{content}}}"
)


def _discussion_comments(api: Any, ctx: dict[str, str]) -> list[tuple[str, str]]:
    owner, _sep, name = ctx["repo"].partition("/")
    data = gql(api, _DISCUSSION_COMMENTS, {"o": owner, "n": name, "x": int(ctx["key"])})
    nodes = (((data.get("repository") or {}).get("discussion") or {}).get("comments") or {}).get(
        "nodes"
    ) or []
    found: list[tuple[str, str]] = []
    for c in nodes:
        if not isinstance(c, Mapping) or not c.get("id"):
            continue
        found.append((_short(c.get("author"), c.get("body")), str(c["id"])))
        for r in (c.get("replies") or {}).get("nodes") or ():
            if isinstance(r, Mapping) and r.get("id"):
                found.append((_short(r.get("author"), r.get("body")) + " (a reply)", str(r["id"])))
    return found


def _react_discussion(api: Any, ctx: dict[str, str]) -> str:
    content = ctx["reaction"]
    data = gql(api, _GROUPS, {"id": ctx["comment"]})
    groups = (data.get("node") or {}).get("reactionGroups") or []
    mine = any(
        isinstance(g, Mapping) and g.get("content") == content and g.get("viewerHasReacted")
        for g in groups
    )
    gql(api, _REMOVE if mine else _ADD, {"id": ctx["comment"], "c": content})
    return "removed" if mine else "added"


_REACT_ASK = Ask(
    "reaction",
    "Which reaction? One you gave already is taken back.",
    "choice",
    _CHOICES,
    _REACTIONS,
)

YOU_QUICK: tuple[Quick, ...] = (
    Quick("subscribe", "Subscribe or Unsubscribe...", _ITEMS,
          frozenset({"item", "discussion", "commit"}),
          "Hear of all its activity, or only when you take part or are mentioned.",
          ("graphql:updateSubscription",), _subscribe, _subscribed, tier="O", need="sign_in",
          asks=(Ask("state", "Notify you of:", "choice", _STATE_WORDS, _STATES),),
          needs=("repo",), live="needs Jeff: a throwaway issue on the test repository"),
    Quick("block_person", "Block or Unblock...", ("person",), frozenset({"person"}),
          "Block them from following you and from your repositories, or lift the block.",
          ("PUT /user/blocks/{username}", "DELETE /user/blocks/{username}"), _block, _blocked,
          tier="V", need="sign_in",
          asks=(Ask("block", "Block them, or lift your block?", "choice", ("Block", "Unblock"),
                    ("true", "false")),),
          needs=("login",), live="needs Jeff: a second test account to block and unblock"),
    Quick("fork", "Fork...", ("repository",), frozenset({"repo"}),
          "Make your own copy of this repository, in your account or an organization's.",
          ("POST /repos/{owner}/{repo}/forks",), _fork, _forked, tier="V", need="sign_in",
          asks=(Ask("organization", "Fork into which organization? Leave it empty for your "
                    "own account:", optional=True),),
          needs=("repo",), live="needs Jeff: makes a fork he deletes afterwards"),
    Quick("block_from_org", "Block from Organization...", ("organization",), frozenset({"org"}),
          "Stop an account from taking part in this organization's repositories.",
          ("PUT /orgs/{org}/blocks/{username}",), _org_block,
          lambda who, ctx: f"Blocked {who} from {ctx['org']}. Its Blocked Users list unblocks.",
          tier="A", need="org:owner",
          asks=(Ask("who", "The login of the account to block from this organization:"),),
          confirm="Block that account from {org}? It cannot comment, open issues or pull "
          "requests, or react in any of {org}'s repositories until it is unblocked.",
          needs=("org",), live="needs Jeff: an organization he owns and a second test account"),
    Quick("block_member", "Block from Organization...", ("resource",),
          frozenset({"resource:org_members"}),
          "Stop this member's account from taking part in the organization's repositories.",
          ("PUT /orgs/{org}/blocks/{username}",), _org_block,
          lambda who, ctx: f"Blocked {who} from {ctx['org']}. Its Blocked Users list unblocks.",
          tier="A", need="org:owner",
          confirm="Block {key} from {org}? Blocking removes them from it, and they cannot take "
          "part in its repositories until they are unblocked.",
          needs=("org", "key"), live="needs Jeff: an organization he owns and a second account"),
    Quick("leave_org", "Leave Organization...", ("organization",), frozenset({"org"}),
          "Stop being a member of this organization.",
          ("DELETE /orgs/{org}/memberships/{username}",), _leave,
          lambda _me, ctx: f"You have left {ctx['org']}.", tier="D", need="org:member",
          confirm="Leave {org}? You lose its private repositories and your teams there, and "
          "only an owner can invite you back.",
          needs=("org",), reload=True, live="not here: needs an organization he can leave"),
    Quick("org_invitation", "Your Invitation", ("organization",), frozenset({"org"}),
          "Whether this organization has invited you, and how to answer.",
          ("GET /user/memberships/orgs/{org}",), _invitation_read, _invitation, needs=("org",)),
    Quick("react_comment", "React to a Comment...", ("issue", "pull_request"),
          frozenset({"item"}),
          "Add a reaction to one of its comments, or take back one you gave.",
          ("POST /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions",
           "DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions/{reaction_id}",
           "POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions",
           "DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions/{reaction_id}"),
          _react_item, _reacted, tier="O", need="sign_in", asks=(_REACT_ASK,),
          pick=_item_comments, pick_key="comment", pick_question="Which comment?",
          needs=("repo", "number"), live="needs Jeff: a comment on a test issue"),
    Quick("react_discussion_comment", "React to a Comment...", ("discussion",),
          frozenset({"discussion"}),
          "Add a reaction to one of its comments or replies, or take back one you gave.",
          ("graphql:addReaction", "graphql:removeReaction"), _react_discussion, _reacted,
          tier="O", need="sign_in",
          asks=(Ask("reaction", _REACT_ASK.question, "choice", _CHOICES, _ENUM),),
          pick=_discussion_comments, pick_key="comment", pick_question="Which comment?",
          needs=("repo", "key"), live="needs Jeff: a comment on a test discussion"),
)  # fmt: skip
