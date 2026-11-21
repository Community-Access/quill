"""Discussion to issue to pull request, and what links to what (complete.md 1.3, GX12).

Three pieces, each with the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`
so tests pass recorded answers:

* :func:`issue_from_discussion` opens an issue whose body links back to the
  discussion (``POST /repos/{owner}/{repo}/issues``), and, only when asked,
  comments on the discussion with the new issue's link
  (``addDiscussionComment``). GitHub has no API to convert an issue to a
  discussion or a discussion to an issue; its web page does that, and the
  Workbench says so.
* :func:`pull_for_issue` makes a branch linked to the issue (the
  ``createLinkedBranch`` GitHub's own "Create a branch" uses), and opens a
  draft pull request from it whose body says ``Closes #n``, so merging it
  closes the issue. GitHub refuses a pull request with no commits, so a new
  branch gets one empty commit first ("Start work on #n"), made with the git
  data API; nothing in the repository's files changes.
* :func:`related` lists the chain around an issue, pull request or
  discussion: the pull requests that close an issue (or the issues a pull
  request closes), what cross-referenced it (its timeline's
  ``CrossReferencedEvent`` and ``ConnectedEvent``), and the issues, pull
  requests and discussions its own text and comments link to. GitHub keeps no
  timeline for a discussion, so a discussion's list is only what it links to,
  and the list says so. Every row names its repository; a part GitHub would
  not give is said as unread, never as none.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "NO_CONVERT",
    "CollabError",
    "Related",
    "RelatedLink",
    "discussion_issue_body",
    "find_references",
    "issue_from_discussion",
    "pull_body",
    "pull_for_issue",
    "related",
]

#: Said where people look for it: there is no API for converting either way.
NO_CONVERT = (
    "GitHub has no API to turn an issue into a discussion or a discussion into an issue; "
    "its web page does that (Open on GitHub). Create Issue from Discussion... opens a new "
    "issue that links back instead."
)

_LIMIT = 30


class CollabError(CodedError):
    """A cross-link GitHub refused or that cannot be made; the message is safe to speak."""

    code = "QUILL-GITHUB-COLLAB"


def _split(repository: str) -> tuple[str, str]:
    owner, _slash, name = repository.partition("/")
    if not owner or not name:
        raise CollabError(f"{repository!r} is not owner/name.")
    return owner, name


def _quote(text: str, limit: int = 1200) -> str:
    body = text.strip()
    if len(body) > limit:
        body = body[:limit].rstrip() + "\n\n(The rest is in the discussion.)"
    return "\n".join(f"> {line}" if line else ">" for line in body.splitlines())


# -- discussion to issue -----------------------------------------------------------


def discussion_issue_body(url: str, author: str, body: str) -> str:
    """The new issue's body: where it came from, and the discussion's words quoted."""
    who = f" by @{author}" if author else ""
    head = f"From the discussion {url}{who}."
    quoted = _quote(body) if body.strip() else ""
    return f"{head}\n\n{quoted}".rstrip() + "\n"


_DISCUSSION_ID = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
    "discussion(number:$i){id url}}}"
)
_ADD_COMMENT = (
    "mutation($d:ID!,$b:String!){addDiscussionComment(input:{discussionId:$d,body:$b})"
    "{comment{url}}}"
)


def issue_from_discussion(
    api: GitHubApi,
    repository: str,
    discussion: int,
    title: str,
    body: str,
    *,
    comment_back: bool = False,
) -> tuple[int, str]:
    """Open the issue; with *comment_back*, link it from the discussion too.

    Returns the issue's number and the sentence to say. A refused comment
    never undoes the issue: the sentence says the issue was made and the
    comment was not.
    """
    if not title.strip():
        raise CollabError("An issue needs a title.")
    made = api.rest(
        "POST", f"/repos/{repository}/issues", body={"title": title.strip()[:256], "body": body}
    ).data
    number = int((made or {}).get("number") or 0) if isinstance(made, Mapping) else 0
    if not number:
        raise CollabError("GitHub did not say which issue it made.")
    url = str(made.get("html_url") or f"https://github.com/{repository}/issues/{number}")
    said = f"Opened issue #{number} from discussion #{discussion}."
    if not comment_back:
        return number, said
    owner, name = _split(repository)
    try:
        data = api.graphql(_DISCUSSION_ID, {"o": owner, "n": name, "i": int(discussion)})
        node = ((data.get("repository") or {}).get("discussion") or {}).get("id")
        if not node:
            raise CollabError("no discussion")
        api.graphql(_ADD_COMMENT, {"d": str(node), "b": f"Opened as issue {url}."})
    except Exception:  # noqa: BLE001 - the issue stands; say the comment did not
        return number, f"{said} The comment linking it from the discussion was not posted."
    return number, f"{said} The discussion links to it in a new comment."


# -- issue to pull request ---------------------------------------------------------


def pull_body(number: int, title: str) -> str:
    """A pull request body that closes the issue when the pull request merges."""
    return f"Closes #{int(number)}.\n\nWork on {title.strip() or 'the issue'}.\n"


def _sha(data: Any, *keys: str) -> str:
    for key in keys:
        data = data.get(key) if isinstance(data, Mapping) else None
    return str(data or "")


def pull_for_issue(
    api: GitHubApi,
    repository: str,
    number: int,
    title: str,
    branch: str,
    *,
    base: str = "",
) -> tuple[int, str]:
    """A linked branch and a draft pull request that closes #*number*; (its number, sentence)."""
    from quill.core.github.issue_development import (
        IssueDevelopmentError,
        create_linked_branch,
        valid_branch_name,
    )

    why = valid_branch_name(branch)
    if why:
        raise CollabError(why)
    if not base:
        base = str((api.rest("GET", f"/repos/{repository}").data or {}).get("default_branch"))
    made_branch = True
    try:
        create_linked_branch(api, repository, number, branch, base=base)
    except IssueDevelopmentError as exc:
        if "already has a branch" not in str(exc):
            raise CollabError(str(exc).split("] ", 1)[-1]) from exc
        made_branch = False  # an existing branch is used as it is
    compare = api.rest("GET", f"/repos/{repository}/compare/{base}...{branch}").data or {}
    if int(compare.get("ahead_by") or 0) == 0:
        _empty_commit(api, repository, branch, f"Start work on #{int(number)}")
    pull_title = title.strip() or f"Work on #{int(number)}"
    request: dict[str, object] = {
        "title": pull_title[:256],
        "head": branch,
        "base": base,
        "body": pull_body(number, title),
        "draft": True,
    }
    try:
        pull = api.rest("POST", f"/repos/{repository}/pulls", body=request).data
        draft = True
    except Exception as exc:  # noqa: BLE001 - only a refused draft is retried
        if "draft" not in str(exc).lower():
            raise
        request.pop("draft")
        pull = api.rest("POST", f"/repos/{repository}/pulls", body=request).data
        draft = False
    pr = int((pull or {}).get("number") or 0) if isinstance(pull, Mapping) else 0
    where = "Made branch" if made_branch else "Used the existing branch"
    kind = "draft pull request" if draft else "pull request (this repository has no drafts)"
    return pr, (
        f"{where} {branch}, linked to #{number}, and opened {kind} #{pr} into {base}. "
        f"Merging it closes #{number}."
    )


def _empty_commit(api: GitHubApi, repository: str, branch: str, message: str) -> None:
    head = api.rest("GET", f"/repos/{repository}/git/ref/heads/{branch}").data
    parent = _sha(head, "object", "sha")
    commit = api.rest("GET", f"/repos/{repository}/git/commits/{parent}").data
    tree = _sha(commit, "tree", "sha")
    if not parent or not tree:
        raise CollabError(f"Could not read the newest commit of {branch}.")
    made = api.rest(
        "POST",
        f"/repos/{repository}/git/commits",
        body={"message": message, "tree": tree, "parents": [parent]},
    ).data
    api.rest(
        "PATCH",
        f"/repos/{repository}/git/refs/heads/{branch}",
        body={"sha": _sha(made, "sha"), "force": False},
    )


# -- the related chain -------------------------------------------------------------

_URL = re.compile(
    r"https://github\.com/([A-Za-z0-9][\w.-]*)/([\w.-]+)/(issues|pull|discussions)/(\d+)"
)
_SHORT = re.compile(r"(?<![\w/#])(?:([A-Za-z0-9][\w.-]*/[\w.-]+))?#(\d+)\b")
_FENCE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
_KIND_WORDS = {"issues": "issue", "pull": "pull_request", "discussions": "discussion"}


def find_references(text: str, here: str) -> list[tuple[str, str, int]]:
    """``(kind, repository, number)`` for each link in *text*, in order, once each.

    *kind* is ``issue``, ``pull_request`` or ``discussion`` for a full link, and
    ``ref`` for ``#12`` or ``owner/name#12``, which may be either an issue or a
    pull request until GitHub says. Code spans and fences are skipped.
    """
    plain = _FENCE.sub(" ", text or "")
    found: dict[tuple[str, int], tuple[str, str, int]] = {}
    for owner, name, kind, number in _URL.findall(plain):
        key = (f"{owner}/{name}".casefold(), int(number))
        found.setdefault(key, (_KIND_WORDS[kind], f"{owner}/{name}", int(number)))
    for repo, number in _SHORT.findall(_URL.sub(" ", plain)):
        where = repo or here
        key = (where.casefold(), int(number))
        found.setdefault(key, ("ref", where, int(number)))
    return list(found.values())


@dataclass(frozen=True, slots=True)
class RelatedLink:
    """One linked issue, pull request or discussion, and how it is linked."""

    kind: str  # issue, pull_request, discussion
    repo: str
    number: int
    title: str
    state: str
    url: str
    how: str

    @property
    def line(self) -> str:
        noun = {"pull_request": "Pull request", "discussion": "Discussion"}.get(self.kind, "Issue")
        state = f" ({self.state.lower()})" if self.state else ""
        title = f", {self.title}" if self.title else ""
        return f"{noun} {self.repo}#{self.number}{title}{state}: {self.how}."


@dataclass(frozen=True)
class Related:
    """The chain around one item, and anything GitHub did not give."""

    subject: str
    links: tuple[RelatedLink, ...]
    notes: tuple[str, ...] = field(default=())

    @property
    def sentence(self) -> str:
        count = len(self.links)
        found = f"{count} linked item{'s' if count != 1 else ''}" if count else "nothing linked"
        extra = " " + " ".join(self.notes) if self.notes else ""
        return f"{self.subject}: {found}.{extra}"

    def lines(self) -> list[str]:
        return [link.line for link in self.links] or ["Nothing links to it, or from it."]


_SUBJECT = "number title state url repository{nameWithOwner}"
_DISCUSSION_SUBJECT = "number title closed url repository{nameWithOwner}"
_TIMELINE = (
    "timelineItems(first:100,itemTypes:[CROSS_REFERENCED_EVENT,CONNECTED_EVENT])"
    "{pageInfo{hasNextPage} nodes{__typename "
    f"... on CrossReferencedEvent{{willCloseTarget source{{__typename "
    f"... on Issue{{{_SUBJECT}}} ... on PullRequest{{{_SUBJECT}}}}}}} "
    f"... on ConnectedEvent{{subject{{__typename ... on Issue{{{_SUBJECT}}} "
    f"... on PullRequest{{{_SUBJECT}}}}}}}}}}}"
)
_COMMENTS = "comments(first:50){totalCount nodes{body}}"
_ITEM_QUERY = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
    "issueOrPullRequest(number:$i){__typename "
    f"... on Issue{{title body {_COMMENTS} "
    f"closedByPullRequestsReferences(first:20,includeClosedPrs:true){{nodes{{{_SUBJECT}}}}} "
    f"{_TIMELINE}}} "
    f"... on PullRequest{{title body {_COMMENTS} "
    f"closingIssuesReferences(first:20){{nodes{{{_SUBJECT}}}}} {_TIMELINE}}}"
    "}}}"
)
_DISCUSSION_QUERY = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
    "discussion(number:$i){title body comments(first:50){totalCount nodes{body "
    "replies(first:20){nodes{body}}}}}}}"
)


def _link(node: Any, how: str) -> RelatedLink | None:
    if not isinstance(node, Mapping) or not node.get("number"):
        return None
    typename = node.get("__typename")
    kind = {"PullRequest": "pull_request", "Discussion": "discussion"}.get(str(typename), "issue")
    state = str(node.get("state") or "")
    if typename == "Discussion":
        state = "closed" if node.get("closed") else "open"
    return RelatedLink(
        kind,
        str((node.get("repository") or {}).get("nameWithOwner") or ""),
        int(node["number"]),
        str(node.get("title") or ""),
        state,
        str(node.get("url") or ""),
        how,
    )


def _texts(subject: Mapping[str, Any]) -> list[str]:
    texts = [str(subject.get("body") or "")]
    for comment in (subject.get("comments") or {}).get("nodes") or ():
        if isinstance(comment, Mapping):
            texts.append(str(comment.get("body") or ""))
            replies = (comment.get("replies") or {}).get("nodes") or ()
            texts += [str(r.get("body") or "") for r in replies if isinstance(r, Mapping)]
    return texts


def _resolve(
    api: GitHubApi, refs: Sequence[tuple[str, str, int]]
) -> dict[tuple[str, int], Mapping[str, Any]]:
    """GitHub's title and state for each link, in one query; missing ones are left out."""
    parts, variables, keys = [], {}, []
    for index, (kind, repo, number) in enumerate(refs[:_LIMIT]):
        owner, _slash, name = repo.partition("/")
        if not owner or not name:
            continue
        if kind == "discussion":
            field_name, inner = "discussion", f"__typename {_DISCUSSION_SUBJECT}"
        else:
            field_name = "issueOrPullRequest"
            inner = f"__typename ... on Issue{{{_SUBJECT}}} ... on PullRequest{{{_SUBJECT}}}"
        parts.append(
            f"r{index}:repository(owner:$o{index},name:$n{index}){{"
            f"{field_name}(number:$i{index}){{{inner}}}}}"
        )
        variables.update({f"o{index}": owner, f"n{index}": name, f"i{index}": number})
        keys.append((index, field_name, repo, number))
    if not parts:
        return {}
    params = ",".join(
        f"$o{i}:String!,$n{i}:String!,$i{i}:Int!" for i, _field, _repo, _number in keys
    )
    data = api.graphql(f"query({params}){{{' '.join(parts)}}}", variables)
    out: dict[tuple[str, int], Mapping[str, Any]] = {}
    for index, field_name, repo, number in keys:
        node = (data.get(f"r{index}") or {}).get(field_name)
        if isinstance(node, Mapping) and node.get("number"):
            out[(repo.casefold(), number)] = node
    return out


def related(api: GitHubApi, repository: str, kind: str, number: int) -> Related:
    """The chain around issue, pull request or discussion #*number* of *repository*."""
    owner, name = _split(repository)
    variables = {"o": owner, "n": name, "i": int(number)}
    notes: list[str] = []
    links: list[RelatedLink] = []
    if kind == "discussion":
        subject = (api.graphql(_DISCUSSION_QUERY, variables).get("repository") or {}).get(
            "discussion"
        )
        noun = "Discussion"
        notes.append(
            "GitHub keeps no record of what links to a discussion, so this lists what "
            "the discussion and its replies link to."
        )
    else:
        subject = (api.graphql(_ITEM_QUERY, variables).get("repository") or {}).get(
            "issueOrPullRequest"
        )
        noun = "Pull request" if (subject or {}).get("__typename") == "PullRequest" else "Issue"
    if not isinstance(subject, Mapping):
        raise CollabError(f"{repository} has no {kind.replace('_', ' ')} #{number} you can see.")
    closing = "closedByPullRequestsReferences" if noun == "Issue" else "closingIssuesReferences"
    how = "merging it closes this issue" if noun == "Issue" else "this pull request closes it"
    for node in (subject.get(closing) or {}).get("nodes") or ():
        found = _link(node, how)
        if found is not None:
            links.append(found)
    timeline = subject.get("timelineItems") or {}
    for event in timeline.get("nodes") or ():
        if not isinstance(event, Mapping):
            continue
        if event.get("__typename") == "ConnectedEvent":
            found = _link(event.get("subject"), "linked to it by hand")
        else:
            closes = bool(event.get("willCloseTarget"))
            found = _link(event.get("source"), "will close it" if closes else "mentions it")
        if found is not None:
            links.append(found)
    if timeline.get("pageInfo", {}).get("hasNextPage"):
        notes.append("Only its first 100 cross-references were read.")
    comments = subject.get("comments") or {}
    if int(comments.get("totalCount") or 0) > 50:
        notes.append("Only its first 50 comments were read for links.")
    refs = [
        ref
        for text in _texts(subject)
        for ref in find_references(text, repository)
        if not (ref[1].casefold() == repository.casefold() and ref[2] == int(number))
    ]
    refs = list(dict.fromkeys(refs))
    if len(refs) > _LIMIT:
        notes.append(f"It links to {len(refs)} items; the first {_LIMIT} were read.")
    try:
        resolved = _resolve(api, refs)
    except Exception:  # noqa: BLE001 - the timeline still stands; say the rest is unread
        resolved = {}
        if refs:
            notes.append("GitHub did not answer for the items its text links to; they are unread.")
    for _kind, repo, ref_number in refs[:_LIMIT]:
        node = resolved.get((repo.casefold(), ref_number))
        if node is None:
            continue
        found = _link(node, "its text links to it")
        if found is not None:
            links.append(found)
    return Related(f"{noun} #{number}", tuple(_dedupe(links)), tuple(notes))


def _dedupe(links: Sequence[RelatedLink]) -> list[RelatedLink]:
    """One row per item, keeping the strongest link (closing before mentioning)."""
    kept: dict[tuple[str, int, str], RelatedLink] = {}
    for link in links:
        kept.setdefault((link.repo.casefold(), link.number, link.kind), link)
    return list(kept.values())
