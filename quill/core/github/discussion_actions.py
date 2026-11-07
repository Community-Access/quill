"""Discussion threads and Discussion writes for the shared workbench (Wave 3).

Explore's Discussions view lists discussions read-only
(:mod:`quill.core.github.discussions`). This adds the rest: one discussion as a
thread (its comments, their replies, the answer and any poll), replying to the
discussion or to a comment, marking a comment as the answer and unmarking it,
and starting a discussion in a category. Every call is GraphQL through
:func:`~quill.core.github.github_graphql.graphql_data`, and each write is
reported only when GitHub's reply shows it.

A poll reads as text, one option to a line: "Option A: 12 votes, 40 percent".
No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.github.github_graphql import as_dict, graphql_data, split_repo
from quill.core.github.items_errors import GitHubItemsError

__all__ = [
    "DiscussionCategory",
    "DiscussionComment",
    "DiscussionPoll",
    "DiscussionThread",
    "GitHubDiscussionActionsMixin",
    "parse_discussion_thread",
    "poll_lines",
]

_MAX_BODY = 20_000

_THREAD_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      id number title bodyText url closed isAnswered
      author { login }
      category { name isAnswerable }
      answer { id author { login } }
      poll { question totalVoteCount options(first:20) { nodes { option totalVoteCount } } }
      comments(first:50) {
        totalCount
        nodes {
          id bodyText url createdAt isAnswer viewerCanMarkAsAnswer viewerCanUnmarkAsAnswer
          author { login }
          replies(first:50) {
            totalCount
            nodes { id bodyText url createdAt author { login } }
          }
        }
      }
    }
  }
}
"""

_CATEGORIES_QUERY = """
query($owner:String!, $repo:String!) {
  repository(owner:$owner, name:$repo) {
    id
    discussionCategories(first:50) { nodes { id name description isAnswerable } }
  }
}
"""

_ADD_COMMENT = """
mutation($discussion:ID!, $body:String!, $replyTo:ID) {
  addDiscussionComment(input:{discussionId:$discussion, body:$body, replyToId:$replyTo}) {
    comment { id url }
  }
}
"""

_MARK_ANSWER = """
mutation($id:ID!) {
  markDiscussionCommentAsAnswer(input:{id:$id}) { discussion { isAnswered answer { id } } }
}
"""

_UNMARK_ANSWER = """
mutation($id:ID!) {
  unmarkDiscussionCommentAsAnswer(input:{id:$id}) { discussion { isAnswered answer { id } } }
}
"""

_CREATE_DISCUSSION = """
mutation($repository:ID!, $category:ID!, $title:String!, $body:String!) {
  createDiscussion(input:{repositoryId:$repository, categoryId:$category,
                          title:$title, body:$body}) {
    discussion { number url }
  }
}
"""


def _login(node: object) -> str:
    author = node.get("author") if isinstance(node, dict) else None
    return str(author.get("login") or "") if isinstance(author, dict) else ""


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


@dataclass(frozen=True, slots=True)
class DiscussionCategory:
    id: str
    name: str
    answerable: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class DiscussionPoll:
    question: str
    total_votes: int
    options: tuple[tuple[str, int], ...] = ()


def poll_lines(poll: DiscussionPoll) -> list[str]:
    """The poll as text: the question, then "Option A: 12 votes, 40 percent" per option."""
    lines = [f"Poll: {poll.question or 'untitled'}, {poll.total_votes} votes in all"]
    for option, votes in poll.options:
        percent = votes * 100 // poll.total_votes if poll.total_votes else 0
        noun = "vote" if votes == 1 else "votes"
        lines.append(f"{option}: {votes} {noun}, {percent} percent")
    return lines


@dataclass(frozen=True, slots=True)
class DiscussionComment:
    id: str
    author: str
    body: str
    created_at: str = ""
    url: str = ""
    is_answer: bool = False
    can_mark: bool = False
    can_unmark: bool = False
    parent_id: str = ""  # set on a reply: the top-level comment it belongs to
    replies: tuple[DiscussionComment, ...] = ()

    @property
    def is_reply(self) -> bool:
        return bool(self.parent_id)

    @property
    def label(self) -> str:
        first = next((line.strip() for line in self.body.splitlines() if line.strip()), "")
        who = self.author or "unknown"
        kind = "Reply" if self.is_reply else "Comment"
        answer = ", the answer" if self.is_answer else ""
        count = len(self.replies)
        replies = f", {count} {'reply' if count == 1 else 'replies'}" if count else ""
        return f"{kind} by {who}{answer}{replies}: {first[:120]}"


@dataclass(frozen=True, slots=True)
class DiscussionThread:
    id: str
    number: int
    title: str
    body: str
    url: str
    author: str
    category: str
    answerable: bool
    answered_by: str = ""
    closed: bool = False
    poll: DiscussionPoll | None = None
    comments: tuple[DiscussionComment, ...] = ()
    warnings: tuple[str, ...] = field(default=())

    @property
    def answer_line(self) -> str:
        if self.answered_by:
            return f"Answered by {self.answered_by}."
        return "Not answered yet." if self.answerable else "This category does not take answers."

    def text(self) -> str:
        lines = [
            f"Discussion #{self.number}: {self.title}",
            f"Category: {self.category or 'uncategorized'}. Started by {self.author or 'unknown'}.",
            self.answer_line,
        ]
        if self.closed:
            lines.append("This discussion is closed.")
        if self.poll is not None:
            lines.extend(["", *poll_lines(self.poll)])
        if self.body:
            lines.extend(["", self.body])
        lines.extend(self.warnings)
        return "\n".join(lines)

    def entries(self) -> list[DiscussionComment]:
        """Every comment, each followed by its replies, in reading order."""
        out: list[DiscussionComment] = []
        for comment in self.comments:
            out.append(comment)
            out.extend(comment.replies)
        return out


def _comment(node: dict[str, Any], parent_id: str = "") -> DiscussionComment:
    replies: tuple[DiscussionComment, ...] = ()
    if not parent_id:
        connection = as_dict(node.get("replies"))
        reply_nodes = connection.get("nodes") if isinstance(connection, dict) else None
        replies = tuple(
            _comment(reply, str(node.get("id") or ""))
            for reply in reply_nodes or ()
            if isinstance(reply, dict) and reply.get("id")
        )
    return DiscussionComment(
        id=str(node.get("id") or ""),
        author=_login(node),
        body=str(node.get("bodyText") or "")[:_MAX_BODY],
        created_at=str(node.get("createdAt") or ""),
        url=str(node.get("url") or ""),
        is_answer=bool(node.get("isAnswer")),
        can_mark=bool(node.get("viewerCanMarkAsAnswer")),
        can_unmark=bool(node.get("viewerCanUnmarkAsAnswer")),
        parent_id=parent_id,
        replies=replies,
    )


def _poll(node: object) -> DiscussionPoll | None:
    if not isinstance(node, dict):
        return None
    options_node = as_dict(node.get("options"))
    rows = options_node.get("nodes") if isinstance(options_node, dict) else None
    options = tuple(
        (str(row.get("option") or ""), _count(row.get("totalVoteCount")))
        for row in rows or ()
        if isinstance(row, dict)
    )
    return DiscussionPoll(
        str(node.get("question") or ""), _count(node.get("totalVoteCount")), options
    )


def parse_discussion_thread(data: object, number: int) -> DiscussionThread:
    repository = data.get("repository") if isinstance(data, dict) else None
    node = repository.get("discussion") if isinstance(repository, dict) else None
    if not isinstance(node, dict) or not node.get("id"):
        raise GitHubItemsError(f"Discussion #{number} was not found in this repository.")
    category = as_dict(node.get("category"))
    answer = node.get("answer") if isinstance(node.get("answer"), dict) else None
    connection = as_dict(node.get("comments"))
    nodes = connection.get("nodes") if isinstance(connection, dict) else None
    comments = tuple(
        _comment(row) for row in nodes or () if isinstance(row, dict) and row.get("id")
    )
    warnings: list[str] = []
    total = _count(connection.get("totalCount")) if isinstance(connection, dict) else 0
    if total > len(comments):
        warnings.append(
            f"Showing the first {len(comments)} of {total} comments; "
            "open it on GitHub for the rest."
        )
    if any(len(comment.replies) >= 50 for comment in comments):
        warnings.append("Some comments have more replies than QUILL shows; see GitHub for them.")
    return DiscussionThread(
        id=str(node["id"]),
        number=_count(node.get("number")) or number,
        title=str(node.get("title") or ""),
        body=str(node.get("bodyText") or "")[:_MAX_BODY],
        url=str(node.get("url") or ""),
        author=_login(node),
        category=str(category.get("name") or "") if isinstance(category, dict) else "",
        answerable=bool(category.get("isAnswerable")) if isinstance(category, dict) else False,
        answered_by=_login(answer) or ("someone" if answer else ""),
        closed=bool(node.get("closed")),
        poll=_poll(node.get("poll")),
        comments=comments,
        warnings=tuple(warnings),
    )


class _DiscussionAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


def _answer_state(data: dict[str, Any], key: str) -> tuple[bool, str]:
    payload = as_dict(data.get(key))
    discussion = payload.get("discussion") if isinstance(payload, dict) else None
    if not isinstance(discussion, dict):
        return False, ""
    answer = discussion.get("answer")
    return bool(discussion.get("isAnswered")), (
        str(answer.get("id") or "") if isinstance(answer, dict) else ""
    )


class GitHubDiscussionActionsMixin:
    """Discussion thread reads and writes for ``GitHubItemsProvider``."""

    def fetch_discussion_thread(
        self: _DiscussionAccess, full_name: str, number: int
    ) -> DiscussionThread:
        owner, name = split_repo(full_name)
        if number <= 0:
            raise GitHubItemsError("Discussion numbers are positive.")
        data = graphql_data(
            self._token,
            _THREAD_QUERY,
            {"owner": owner, "repo": name, "number": int(number)},
            action=f"load discussion #{number}",
        )
        return parse_discussion_thread(data, number)

    def fetch_discussion_categories(
        self: _DiscussionAccess, full_name: str
    ) -> tuple[str, list[DiscussionCategory]]:
        """``(repository node ID, categories)`` for starting a discussion."""
        owner, name = split_repo(full_name)
        data = graphql_data(
            self._token,
            _CATEGORIES_QUERY,
            {"owner": owner, "repo": name},
            action="list the discussion categories",
        )
        repository = as_dict(data.get("repository"))
        repo_id = str(repository.get("id") or "") if isinstance(repository, dict) else ""
        connection = (
            repository.get("discussionCategories") if isinstance(repository, dict) else None
        )
        nodes = connection.get("nodes") if isinstance(connection, dict) else None
        categories = [
            DiscussionCategory(
                id=str(row["id"]),
                name=str(row.get("name") or ""),
                answerable=bool(row.get("isAnswerable")),
                description=str(row.get("description") or ""),
            )
            for row in nodes or ()
            if isinstance(row, dict) and row.get("id")
        ]
        if not repo_id:
            raise GitHubItemsError(f"Could not find {full_name} on GitHub.")
        if not categories:
            raise GitHubItemsError(
                f"{full_name} has no discussion categories; Discussions may be turned off."
            )
        return repo_id, categories

    def reply_to_discussion(
        self: _DiscussionAccess, discussion_id: str, body: str, *, reply_to: str = ""
    ) -> str:
        """Comment on the discussion, or reply under the top-level comment *reply_to*.

        Returns the new comment's address.
        """
        if not discussion_id:
            raise GitHubItemsError("This discussion cannot be replied to from here.")
        if not body.strip():
            raise GitHubItemsError("Write a reply first.")
        what = "reply to the comment" if reply_to else "reply to the discussion"
        self._require_write_access(what)
        variables: dict[str, object] = {"discussion": discussion_id, "body": body}
        variables["replyTo"] = reply_to or None
        data = graphql_data(self._token, _ADD_COMMENT, variables, action=what)
        added = data.get("addDiscussionComment")
        comment = added.get("comment") if isinstance(added, dict) else None
        if not isinstance(comment, dict) or not comment.get("id"):
            raise GitHubItemsError(f"Could not {what}. GitHub did not confirm the comment.")
        return str(comment.get("url") or "")

    def set_discussion_answer(self: _DiscussionAccess, comment_id: str, *, answer: bool) -> None:
        """Mark a comment as the answer, or unmark it, and check GitHub agrees."""
        if not comment_id:
            raise GitHubItemsError("Choose a comment first.")
        what = "mark the comment as the answer" if answer else "unmark the answer"
        self._require_write_access(what)
        key = "markDiscussionCommentAsAnswer" if answer else "unmarkDiscussionCommentAsAnswer"
        data = graphql_data(
            self._token,
            _MARK_ANSWER if answer else _UNMARK_ANSWER,
            {"id": comment_id},
            action=what,
        )
        answered, answer_id = _answer_state(data, key)
        if answer and (not answered or answer_id != comment_id):
            raise GitHubItemsError(f"Could not {what}. GitHub did not confirm it.")
        if not answer and answer_id == comment_id:
            raise GitHubItemsError(f"Could not {what}. GitHub still shows it as the answer.")

    def create_discussion(
        self: _DiscussionAccess,
        repository_id: str,
        category_id: str,
        title: str,
        body: str,
    ) -> tuple[int, str]:
        """Start a discussion; returns its ``(number, address)``."""
        if not title.strip():
            raise GitHubItemsError("A discussion needs a title.")
        if not body.strip():
            raise GitHubItemsError("A discussion needs a body.")
        if not repository_id or not category_id:
            raise GitHubItemsError("Choose a category first.")
        self._require_write_access("start a discussion")
        data = graphql_data(
            self._token,
            _CREATE_DISCUSSION,
            {
                "repository": repository_id,
                "category": category_id,
                "title": title.strip(),
                "body": body,
            },
            action="start the discussion",
        )
        created = data.get("createDiscussion")
        discussion = created.get("discussion") if isinstance(created, dict) else None
        number = _count(discussion.get("number")) if isinstance(discussion, dict) else 0
        if not number or not isinstance(discussion, dict):
            raise GitHubItemsError("Could not start the discussion. GitHub did not confirm it.")
        return number, str(discussion.get("url") or "")
