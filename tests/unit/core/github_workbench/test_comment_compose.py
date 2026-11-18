"""The comment composer's people, references, saved replies, spoken preview and check."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import comment_compose as cc
from quill.core.github.rest_transport import RestResponse


class FakeApi:
    def __init__(self, *, rest: Mapping[str, Any] | None = None, graphql: Any = None) -> None:
        self.answers = dict(rest or {})
        self.graphql_answer = graphql or {}
        self.asked: list[tuple[str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.asked.append((path, query))
        answer = self.answers.get(path)
        if isinstance(answer, Exception):
            raise answer
        return RestResponse(200, {}, answer)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        return self.graphql_answer


def test_mentions_put_the_conversation_first_without_repeats() -> None:
    api = FakeApi(rest={"/repos/o/r/assignees": [{"login": "ada"}, {"login": "jeff"}]})
    assert cc.mention_candidates(api, "o/r", already=["jeff", "lin"]) == ["jeff", "lin", "ada"]


def test_mentions_still_offer_the_conversation_when_assignees_fail() -> None:
    api = FakeApi(rest={"/repos/o/r/assignees": RuntimeError("403")})
    assert cc.mention_candidates(api, "o/r", already=["lin"]) == ["lin"]


def test_references_search_titles_or_take_a_number() -> None:
    api = FakeApi(
        rest={
            "/search/issues": {
                "items": [
                    {"number": 4, "title": "Parser", "state": "open"},
                    {"number": 9, "title": "Fix parser", "state": "closed", "pull_request": {}},
                ]
            },
            "/repos/o/r/issues/7": {"number": 7, "title": "Seven", "state": "open"},
        }
    )
    found = cc.reference_candidates(api, "o/r", "parser")
    assert [r.label for r in found] == [
        "#4, Parser (open issue)",
        "#9, Fix parser (closed pull request)",
    ]
    assert api.asked[0] == ("/search/issues", {"q": "repo:o/r parser in:title", "per_page": "30"})
    assert [r.number for r in cc.reference_candidates(api, "o/r", "#7")] == [7]


def test_saved_replies_come_from_the_account() -> None:
    api = FakeApi(
        graphql={"viewer": {"savedReplies": {"nodes": [{"title": "Thanks", "body": "Thank you!"}]}}}
    )
    assert cc.saved_replies(api) == [cc.SavedReply("Thanks", "Thank you!")]


def test_the_spoken_preview_says_what_each_line_is() -> None:
    text = (
        "## Steps\n\n- [ ] Run it\n- [x] Read it\n- plain\n2. second\n> quoted **bold**\n"
        "---\n![](shot.png) and ![a chart of sales](c.png)\nSee [the guide](u) @ada #12\n"
        "```py\nprint('@not')\n```\n"
    )
    assert cc.spoken_preview(text) == [
        "Heading 2: Steps",
        "Not done: Run it",
        "Done: Read it",
        "Bullet: plain",
        "2. second",
        "Quote: quoted bold",
        "Line across.",
        "[image with no description] and [image: a chart of sales]",
        "See the guide [link] @ada #12",
        "Code block, py:",
        "print('@not')",
        "End of code, 1 lines.",
        "Mentions, who GitHub will notify: @ada",
        "Refers to: #12",
    ]


def test_an_unclosed_code_block_is_said() -> None:
    assert cc.spoken_preview("```\nx")[-1].startswith("The code block is never closed")


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("![](https://x/shot.png)", "The image shot.png has no description"),
        ("![screenshot](a.png)", "needs words saying what it shows"),
        ("Read [click here](u).", "A link says 'click here'"),
        ("# One\n### Three", "jumps from level 1 to 3"),
        ("THIS IS NOT OK AT ALL", "A long run of capital letters"),
        ("🎉", "only an emoji"),
        (":tada:", "only an emoji"),
    ],
)
def test_the_check_finds_what_trips_a_reader(text: str, said: str) -> None:
    findings = cc.accessibility_findings(text)
    assert any(said in finding for finding in findings), findings


@pytest.mark.parametrize(
    "text",
    [
        "![a bar chart of sales by month](c.png)",
        "See [the install guide](u).",
        "# One\n## Two\n### Three",
        "Thanks 🎉 that worked",
        "```\n![](no-alt-in-code.png)\nSHOUTING IN CODE IS FINE HERE\n```",
        "OK, CI is green",
    ],
)
def test_the_check_leaves_good_comments_alone(text: str) -> None:
    assert cc.accessibility_findings(text) == []
