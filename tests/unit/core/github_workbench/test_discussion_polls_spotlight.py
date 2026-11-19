"""Discussion polls as a table and Vote..., Pinned (spotlight), and Categories by section.

complete.md 1.3. Every GitHub answer here is a recorded GraphQL reply; nothing
reaches GitHub.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import discussions, github_graphql
from quill.core.github.discussion_actions import (
    DiscussionCategory,
    GitHubDiscussionActionsMixin,
    parse_poll,
    poll_heading,
    poll_lines,
    poll_table,
)
from quill.core.github.discussion_categories import (
    ALL_SECTIONS,
    SECTIONS_NOT_IN_API,
    category_rows,
)
from quill.core.github.explore_models import ExploreRow
from quill.core.github.permissions import AccessLevel
from quill.core.github.quick_tables import QUICK, QUICK_LIVE, QUICK_REQUIREMENTS
from quill.core.github.rest_transport import RestResponse
from quill.core.github.sheets_talk import DISCUSSION
from quill.core.github.workbench_tree import GITHUB_TREE
from quill.core.workbench.properties import FieldKind
from quill.ui.github_workbench_discussions import NO_UNVOTE, GitHubWorkbenchDiscussionsMixin
from quill.ui.github_workbench_loaders import load_local, place_key
from quill.ui.github_workbench_quick import GitHubWorkbenchQuickMixin

POLL = {
    "question": "Which sound pack?",
    "totalVoteCount": 25,
    "viewerCanVote": True,
    "viewerHasVoted": False,
    "options": {
        "nodes": [
            {"id": "PO_1", "option": "Classic", "totalVoteCount": 15, "viewerHasVoted": False},
            {"id": "PO_2", "option": "Soft", "totalVoteCount": 10, "viewerHasVoted": False},
        ]
    },
}
VOTED = {
    **POLL,
    "viewerCanVote": False,
    "viewerHasVoted": True,
    "options": {
        "nodes": [
            {"id": "PO_1", "option": "Classic", "totalVoteCount": 15, "viewerHasVoted": True},
            {"id": "PO_2", "option": "Soft", "totalVoteCount": 10, "viewerHasVoted": False},
        ]
    },
}


def _discussion(number: int, title: str, poll: Any = None) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "bodyText": "Body",
        "url": f"https://github.com/o/r/discussions/{number}",
        "createdAt": "2026-10-01T00:00:00Z",
        "updatedAt": "2026-11-01T00:00:00Z",
        "closed": False,
        "author": {"login": "alice"},
        "category": {"name": "Q&A", "emoji": "", "isAnswerable": True},
        "answer": None,
        "poll": poll,
    }


# -- polls -------------------------------------------------------------------------


def test_a_poll_reads_as_a_table_of_option_votes_percent_and_your_vote() -> None:
    poll = parse_poll(VOTED)
    assert poll is not None
    assert poll_table(poll) == (
        "Classic, 15 votes, 60 percent, your vote: yes",
        "Soft, 10 votes, 40 percent, your vote: no",
    )
    assert poll_heading(poll) == "Poll: Which sound pack?, 25 votes in all. You have voted."
    assert poll_lines(poll)[1] == "Classic: 15 votes, 60 percent, your vote"
    fresh = parse_poll(POLL)
    assert fresh is not None and fresh.can_vote and not fresh.voted
    assert poll_heading(fresh).endswith("You may vote: Vote...")
    assert parse_poll(None) is None


def test_the_discussions_list_details_carry_the_poll_table(monkeypatch) -> None:
    sent: list[str] = []

    def reply(_token: str, query: str, _variables: dict[str, object]) -> dict[str, Any]:
        sent.append(query)
        return {
            "repository": {
                "discussions": {
                    "totalCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [_discussion(4, "Sounds", POLL)],
                }
            }
        }

    monkeypatch.setattr(discussions, "_request", reply)
    rows, _complete, _warning = discussions.list_discussions("tok", "o/r")
    assert "viewerHasVoted" in sent[0] and "viewerCanVote" in sent[0]
    detail = rows[0].detail
    assert "Option, votes, percent, your vote:" in detail
    assert "Classic, 15 votes, 60 percent, your vote: no" in detail


def test_the_properties_sheet_has_the_poll_as_a_table() -> None:
    field = DISCUSSION.sheet.field("poll")
    assert field.kind is FieldKind.TABLE and field.readonly
    assert "viewerCanVote" in DISCUSSION.reads[0].graphql
    extract = DISCUSSION.reads[0].extract
    assert extract is not None
    values = extract({"repository": {"discussion": {"id": "D_1", "title": "T", "poll": VOTED}}})
    assert values["poll"] == poll_table(parse_poll(VOTED))  # type: ignore[arg-type]
    assert "You have voted." in str(values["poll_question"])
    none = extract({"repository": {"discussion": {"id": "D_1"}}})
    assert none["poll"] == () and none["poll_question"] == "This discussion has no poll."


class _Api:
    def __init__(self, *replies: dict[str, Any]) -> None:
        self.replies, self.sent = list(replies), []

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        self.sent.append((query, variables))
        return self.replies.pop(0)


class _Frame:
    def __init__(self) -> None:
        self.current = type("Ref", (), {"key": "discussions", "instance": "o/r"})()
        self.reloads = 0
        self.frame = None

    def reload(self) -> None:
        self.reloads += 1


class _Host(GitHubWorkbenchQuickMixin, GitHubWorkbenchDiscussionsMixin):
    def __init__(self, api: _Api, answers: list[Any], level: AccessLevel = AccessLevel.FULL):
        self.api, self.answers, self.said, self.signed_in = api, answers, [], True
        self.level, self.frame, self._folders, self.went = level, _Frame(), {}, []
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]

    def github_api(self) -> Any:
        return self.api

    def access_level(self) -> AccessLevel:
        return self.level

    def _go_filtered(self, template: str, key: str, instance: str, text: str) -> None:
        self.went.append((template, key, instance, text))


_ROW = ExploreRow("#4 Sounds", "", "", "o/r", "discussion", "4", title="Sounds")
_VOTE_REPLY = {
    "addDiscussionPollVote": {
        "pollOption": {
            "option": "Soft",
            "totalVoteCount": 11,
            "viewerHasVoted": True,
            "poll": {"totalVoteCount": 26},
        }
    }
}


def test_vote_chooses_an_option_casts_it_and_says_the_new_count_once() -> None:
    vote = next(q for q in QUICK if q.verb == "poll_vote")
    assert vote.label == "Vote..."
    api = _Api({"repository": {"discussion": {"poll": POLL}}}, _VOTE_REPLY)
    host = _Host(api, [1])
    host._do_poll_vote(None, _ROW)
    assert api.sent[1][1] == {"input": {"pollOptionId": "PO_2"}}
    assert "addDiscussionPollVote" in api.sent[1][0]
    assert host.said == ["Voted for Soft. It has 11 votes now, of 26 in all."]


def test_vote_says_why_when_you_have_voted_or_may_not() -> None:
    host = _Host(_Api({"repository": {"discussion": {"poll": VOTED}}}), [])
    host._do_poll_vote(None, _ROW)
    assert host.said[0].endswith("You have already voted in this poll, for Classic.")
    closed = {**POLL, "viewerCanVote": False}
    host = _Host(_Api({"repository": {"discussion": {"poll": closed}}}), [])
    host._do_poll_vote(None, _ROW)
    assert host.said[0].endswith("GitHub says you cannot vote in this poll.")
    host = _Host(_Api({"repository": {"discussion": {"poll": None}}}), [])
    host._do_poll_vote(None, _ROW)
    assert host.said[0].endswith("This discussion has no poll.")


def test_a_read_only_account_cannot_vote_and_nothing_is_sent() -> None:
    api = _Api()
    host = _Host(api, [], level=AccessLevel.READ_ONLY)
    host._do_poll_vote(None, _ROW)
    assert api.sent == []
    assert host.said == [
        "This account is read only in the Workbench. Workbench Options, Accounts changes it."
    ]
    assert QUICK_REQUIREMENTS["github.workbench.poll_vote"][0] == "sign_in"
    assert QUICK_LIVE["poll_vote"].startswith("needs Jeff")


def test_the_sheets_poll_table_votes_and_cannot_take_a_vote_back() -> None:
    api = _Api({"repository": {"discussion": {"poll": POLL}}}, _VOTE_REPLY)
    host = _Host(api, [1])
    host.vote_from_sheet({"repo": "o/r", "number": "4"}, "change")
    assert api.sent[0][1] == {"o": "o", "n": "r", "x": 4}
    assert host.said == ["Voted for Soft. It has 11 votes now, of 26 in all."]
    host.vote_from_sheet({"repo": "o/r", "number": "4"}, "remove")
    assert host.said[-1] == NO_UNVOTE


# -- the spotlight -------------------------------------------------------------------


def test_pinned_lists_the_spotlight_in_githubs_order_and_says_it_is_read_only(
    monkeypatch,
) -> None:
    def reply(_token: str, query: str, _variables: dict[str, object]) -> dict[str, Any]:
        assert "pinnedDiscussions" in query
        return {
            "repository": {
                "pinnedDiscussions": {
                    "totalCount": 2,
                    "nodes": [
                        {"pinnedBy": {"login": "jeff"}, "discussion": _discussion(9, "Welcome")},
                        {"pinnedBy": None, "discussion": _discussion(3, "Rules", POLL)},
                    ],
                }
            }
        }

    monkeypatch.setattr(discussions, "_request", reply)
    rows = discussions.list_pinned_discussions("tok", "o/r")
    assert [row.key for row in rows] == ["9", "3"]
    assert rows[0].label.startswith("1. #9 Welcome")
    assert rows[0].detail.startswith("Pinned 1 of 2, by jeff.")
    assert discussions.PIN_NOT_IN_API in rows[0].detail
    assert "your vote: no" in rows[1].detail and rows[1].kind == "discussion"


def test_the_spotlight_needs_a_sign_in_and_says_when_nothing_is_pinned(monkeypatch) -> None:
    from quill.core.github.explore_models import GitHubExploreError

    with pytest.raises(GitHubExploreError, match="Sign in"):
        discussions.list_pinned_discussions(None, "o/r")
    monkeypatch.setattr(
        discussions,
        "_request",
        lambda *_a: {"repository": {"pinnedDiscussions": {"totalCount": 0, "nodes": []}}},
    )
    node = GITHUB_TREE.template_node("repository", "discussions_pinned")
    host = type("Host", (), {"local_note": ""})()
    items = type("Items", (), {"token": "tok"})()
    assert load_local(items, node, instance="o/r", host=host) == []
    assert host.local_note == "Nothing is pinned in this repository's Discussions."


# -- categories and sections ------------------------------------------------------------


def _categories(*sections: str) -> list[DiscussionCategory]:
    names = ("Q&A", "Help", "Ideas")
    return [
        DiscussionCategory(
            f"C{i}",
            name,
            answerable=name != "Ideas",
            slug=name.lower(),
            section=sections[i] if i < len(sections) else "",
        )  # fmt: skip
        for i, name in enumerate(names)
    ]


def test_without_sections_in_the_api_categories_are_listed_and_the_note_says_why() -> None:
    rows, note = category_rows(_categories(), "o/r")
    assert note == SECTIONS_NOT_IN_API
    assert [row.label for row in rows] == [
        "Q&A, question and answer",
        "Help, question and answer",
        "Ideas",
    ]
    assert rows[0].kind == "discussion_category" and rows[0].key == "Q&A"


def test_sections_are_places_you_can_go_and_come_back_from() -> None:
    categories = _categories("Q&A", "Q&A", "Other")
    rows, note = category_rows(categories, "o/r")
    assert note == ""
    assert [row.label for row in rows] == [
        "Section: Q&A (2 categories)",
        "Section: Other (1 category)",
    ]
    assert rows[0].kind == "discussion_section" and rows[0].key == "Q&A"
    inside, _note = category_rows(categories, "o/r", "Q&A")
    assert [row.label for row in inside][0] == ALL_SECTIONS
    assert inside[0].key == "" and len(inside) == 3


def test_categories_read_a_section_when_githubs_reply_names_one(monkeypatch) -> None:
    class _Provider(GitHubDiscussionActionsMixin):
        _token = "tok"

    reply = {
        "data": {
            "repository": {
                "id": "R_1",
                "discussionCategories": {
                    "nodes": [
                        {"id": "C1", "name": "Q&A", "section": {"name": "Support"}},
                        {"id": "C2", "name": "Ideas"},
                    ]
                },
            }
        }
    }
    monkeypatch.setattr(
        github_graphql, "request_json", lambda *_a, **_k: RestResponse(200, {}, reply)
    )
    _repo, categories = _Provider().fetch_discussion_categories("o/r")
    assert [c.section for c in categories] == ["Support", ""]


def test_the_categories_node_opens_a_section_and_enter_finds_its_discussions() -> None:
    node = GITHUB_TREE.template_node("repository", "discussion_categories")
    assert node.parent == "discussions" and node.loader == "discussions:categories"
    pinned = GITHUB_TREE.template_node("repository", "discussions_pinned")
    assert pinned.label == "Pinned (spotlight)"

    class _Items:
        token = "tok"

        def fetch_discussion_categories(self, _repo: str) -> tuple[str, list[Any]]:
            return "R_1", _categories("Q&A", "Q&A", "Other")

    host = _Host(_Api(), [])
    section = category_rows(_categories("Q&A", "Q&A", "Other"), "o/r")[0][0]
    ref = type("Ref", (), {"key": "discussion_categories", "instance": "o/r"})()
    assert host._fits_open_section(section)
    host._do_open_section(ref, section)
    assert host.frame.reloads == 1
    folder = host._folders[place_key("discussion_categories", "o/r")]
    assert place_key("files", "o/r") == "o/r" and "o/r" not in host._folders
    rows = load_local(_Items(), node, instance="o/r", folder=folder, host=host)
    assert rows[0].label == ALL_SECTIONS and rows[1].label == "Q&A, question and answer"
    host._do_category_discussions(ref, rows[1])
    assert host.went == [("repository", "discussions", "o/r", "Q&A")]
    spaced = ExploreRow("Show and tell", "", "", "o/r", "discussion_category", "Show and tell")
    host._do_category_discussions(ref, spaced)
    assert host.went[-1][3] == '"Show and tell"'


def test_a_quick_write_is_refused_by_the_level_before_anything_is_read() -> None:
    close = next(q for q in QUICK if q.verb == "delete_discussion")
    api = _Api()
    host = _Host(api, [], level=AccessLevel.ORGANIZE)
    host._do_delete_discussion(None, _ROW)
    assert api.sent == [] and "Organize" in host.said[0]
    assert close.tier == "D"
