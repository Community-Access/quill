"""The last four GitHub features, against fake GitHub: Copilot review and the coding
agent, commit comments, gist editing, and the attention queue's batched summaries."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import commit_comments, copilot, gists, github_graphql
from quill.core.github.attention_queue_summaries import SUMMARY_LIMIT, summarize_queue_rows
from quill.core.github.commit_comments import GitHubCommitCommentsMixin, parse_commit_comment
from quill.core.github.copilot import (
    COPILOT_GRAPHQL_FEATURES,
    COPILOT_REVIEWER_LOGIN,
    CopilotAssignment,
    GitHubCopilotMixin,
    parse_assignment,
)
from quill.core.github.explore_models import ExploreRow
from quill.core.github.gists import Gist, GistDraft, GistFile, GitHubGistsMixin, parse_gist
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.pr_summary import PullRef, PullSummary
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class _Api:
    """Answers ``request_json`` calls from a table; records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []
        self.replies: dict[tuple[str, str], Any] = {}

    def __call__(self, token, method, path, *, body=None, query=None, extra_headers=None, **_kw):
        self.calls.append((method, path, body, extra_headers))
        reply = self.replies.get((method, path), RestResponse(200, {}, None))
        if isinstance(reply, list):
            reply = reply.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    for module in (copilot, commit_comments, gists, github_graphql):
        monkeypatch.setattr(module, "request_json", fake)
    return fake


class _Provider(GitHubCopilotMixin, GitHubCommitCommentsMixin):
    def __init__(self, token: str | None = "t") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


class _Gists(GitHubGistsMixin):
    def __init__(self, token: str | None = "t") -> None:
        self._provider = SimpleNamespace(token=token)


# -- Copilot code review -------------------------------------------------------------


def test_copilot_review_asks_for_the_documented_reviewer_and_reads_it_back(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/pulls/7/requested_reviewers")] = RestResponse(
        201, {}, {"requested_reviewers": [{"login": "Copilot", "type": "Bot"}]}
    )
    sentence = _Provider().request_copilot_review("o/r", 7)
    method, path, body, _headers = api.calls[0]
    assert (method, path) == ("POST", "/repos/o/r/pulls/7/requested_reviewers")
    assert body == {"reviewers": [COPILOT_REVIEWER_LOGIN]}
    assert COPILOT_REVIEWER_LOGIN == "copilot-pull-request-reviewer[bot]"
    assert sentence.startswith("Copilot review requested on pull request #7")


def test_copilot_review_left_off_the_list_is_said_not_claimed(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/pulls/7/requested_reviewers")] = RestResponse(
        201, {}, {"requested_reviewers": [{"login": "alice"}]}
    )
    with pytest.raises(GitHubItemsError, match="did not list Copilot"):
        _Provider().request_copilot_review("o/r", 7)


def test_copilot_review_refused_names_the_likely_reason(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/pulls/7/requested_reviewers")] = GitHubRestError(
        "Unprocessable",
        status=422,
        data={"message": "Reviews may only be requested from collaborators."},
    )
    with pytest.raises(GitHubItemsError, match="Copilot code review may not be available"):
        _Provider().request_copilot_review("o/r", 7)


def test_copilot_review_needs_an_account(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).request_copilot_review("o/r", 7)
    assert api.calls == []


# -- Copilot coding agent ------------------------------------------------------------


def _assignment_data(*, bot: bool = True, state: str = "OPEN", assignees=()) -> dict[str, Any]:
    actors = [{"login": "alice", "__typename": "User", "id": "U_alice"}]
    if bot:
        actors.insert(0, {"login": "copilot-swe-agent", "__typename": "Bot", "id": "BOT_1"})
    return {
        "data": {
            "repository": {
                "id": "R_1",
                "suggestedActors": {"nodes": actors},
                "issue": {
                    "id": "I_9",
                    "state": state,
                    "assignees": {"nodes": [{"id": f"U_{a}", "login": a} for a in assignees]},
                },
            }
        }
    }


def test_assignment_check_sends_the_feature_header_and_finds_the_agent(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = RestResponse(200, {}, _assignment_data(assignees=["bob"]))
    found = _Provider().check_copilot_assignment("o/r", 9)
    _method, _path, body, headers = api.calls[0]
    assert "suggestedActors(capabilities: [CAN_BE_ASSIGNED]" in body["query"]
    assert body["variables"] == {"owner": "o", "name": "r", "number": 9}
    assert headers == COPILOT_GRAPHQL_FEATURES
    assert found.available and found.bot_id == "BOT_1" and found.issue_id == "I_9"
    assert found.refusal() == ""
    assert "bob stay assigned too" in found.confirmation()


def test_assignment_unavailable_says_why_plainly() -> None:
    found = parse_assignment("o/r", 9, _assignment_data(bot=False)["data"])
    assert not found.available
    assert "not available for o/r" in found.refusal()
    assert "Nothing was changed" in found.refusal()


@pytest.mark.parametrize(
    ("data", "words"),
    [
        (_assignment_data(state="CLOSED")["data"], "is closed"),
        (_assignment_data(assignees=["copilot-swe-agent"])["data"], "already assigned"),
        ({"repository": {"suggestedActors": {"nodes": []}}}, "not available"),
    ],
)
def test_assignment_refusals(data: dict[str, Any], words: str) -> None:
    assert words in parse_assignment("o/r", 9, data).refusal()


def test_assign_keeps_existing_assignees_and_confirms_from_the_reply(api: _Api) -> None:
    assignment = parse_assignment("o/r", 9, _assignment_data(assignees=["bob"])["data"])
    api.replies[("POST", "/graphql")] = RestResponse(
        200,
        {},
        {
            "data": {
                "replaceActorsForAssignable": {
                    "assignable": {
                        "number": 9,
                        "assignees": {"nodes": [{"id": "U_bob", "login": "bob"}]},
                    }
                }
            }
        },
    )
    # The reply is the proof: without the agent in it, nothing is claimed.
    with pytest.raises(GitHubItemsError, match="did not confirm Copilot"):
        _Provider().assign_issue_to_copilot(assignment)
    _method, _path, body, headers = api.calls[0]
    assert "replaceActorsForAssignable" in body["query"]
    assert body["variables"] == {"assignable": "I_9", "actors": ["U_bob", "BOT_1"]}
    assert headers == COPILOT_GRAPHQL_FEATURES

    api.replies[("POST", "/graphql")] = RestResponse(
        200,
        {},
        {
            "data": {
                "replaceActorsForAssignable": {
                    "assignable": {"assignees": {"nodes": [{"id": "BOT_1", "login": "Copilot"}]}}
                }
            }
        },
    )
    assert "assigned to Copilot" in _Provider().assign_issue_to_copilot(assignment)


def test_assign_refuses_before_sending_when_unavailable(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="not available"):
        _Provider().assign_issue_to_copilot(CopilotAssignment("o/r", 9, available=False))
    assert api.calls == []


def test_graphql_errors_become_one_sentence(api: _Api) -> None:
    api.replies[("POST", "/graphql")] = RestResponse(
        200, {}, {"errors": [{"message": "Resource not accessible"}]}
    )
    with pytest.raises(GitHubItemsError, match="GitHub said: Resource not accessible"):
        _Provider().check_copilot_assignment("o/r", 9)


# -- Commit comments -----------------------------------------------------------------

_SHA = "abcdef1234567890abcdef1234567890abcdef12"


def _comment(identifier: int, **extra: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "user": {"login": "octocat"},
        "created_at": "2026-11-07T10:00:00Z",
        "body": "Looks good\nSecond line",
        **extra,
    }


def test_commit_comments_read_as_author_date_and_text(api: _Api) -> None:
    path = f"/repos/o/r/commits/{_SHA}/comments"
    api.replies[("GET", path)] = RestResponse(
        200, {}, [_comment(1), _comment(2, path="docs/a.md", line=12), {"id": "bad"}]
    )
    result = _Provider().fetch_commit_comments("o/r", _SHA)
    assert result.complete
    first, second = result.items
    assert first.label() == "octocat, 2026-11-07: Looks good"
    assert second.label() == "octocat, 2026-11-07 on docs/a.md line 12: Looks good"
    assert "On: the whole commit" in first.detail()


def test_commit_comments_stop_at_the_page_cap_and_say_so(api: _Api) -> None:
    path = f"/repos/o/r/commits/{_SHA}/comments"
    api.replies[("GET", path)] = RestResponse(200, {}, [_comment(n + 1) for n in range(100)])
    result = _Provider().fetch_commit_comments("o/r", _SHA)
    assert not result.complete and "has more" in result.warning
    assert len(api.calls) == 10


def test_add_commit_comment_on_a_line_sends_path_and_line(api: _Api) -> None:
    path = f"/repos/o/r/commits/{_SHA}/comments"
    api.replies[("POST", path)] = RestResponse(201, {}, _comment(5, path="a.py", line=3))
    posted = _Provider().add_commit_comment("o/r", _SHA, "Why?", path="/a.py", line=3)
    assert api.calls[0][2] == {"body": "Why?", "path": "a.py", "line": 3}
    assert posted.where == "a.py line 3"


def test_add_commit_comment_on_the_whole_commit_sends_only_the_body(api: _Api) -> None:
    path = f"/repos/o/r/commits/{_SHA}/comments"
    api.replies[("POST", path)] = RestResponse(201, {}, _comment(6))
    _Provider().add_commit_comment("o/r", _SHA, "Thanks")
    assert api.calls[0][2] == {"body": "Thanks"}


@pytest.mark.parametrize(
    ("kwargs", "words"),
    [
        ({"body": " "}, "needs some text"),
        ({"body": "x", "line": 3}, "Name the file"),
        ({"body": "x", "path": "a", "line": 0}, "from 1 up"),
    ],
)
def test_add_commit_comment_refuses_bad_input_before_sending(
    api: _Api, kwargs: dict[str, Any], words: str
) -> None:
    body = kwargs.pop("body")
    with pytest.raises(GitHubItemsError, match=words):
        _Provider().add_commit_comment("o/r", _SHA, body, **kwargs)
    assert api.calls == []


def test_add_commit_comment_unconfirmed_is_not_success(api: _Api) -> None:
    api.replies[("POST", f"/repos/o/r/commits/{_SHA}/comments")] = RestResponse(200, {}, {})
    with pytest.raises(GitHubItemsError, match="did not confirm"):
        _Provider().add_commit_comment("o/r", _SHA, "x")


def test_commit_comment_failure_is_actionable(api: _Api) -> None:
    api.replies[("GET", f"/repos/o/r/commits/{_SHA}/comments")] = GitHubRestError(
        "Not Found", status=404
    )
    with pytest.raises(GitHubItemsError, match="Could not read the commit's comments"):
        _Provider().fetch_commit_comments("o/r", _SHA)


def test_parse_commit_comment_rejects_non_comments() -> None:
    assert parse_commit_comment([]) is None
    assert parse_commit_comment({"id": True}) is None


# -- Gists ---------------------------------------------------------------------------


def _gist(**files: str) -> Gist:
    return Gist(
        "g1",
        "Notes",
        False,
        "https://gist.github.com/g1",
        tuple(GistFile(name, text) for name, text in files.items()),
    )


def _gist_json(description: str, files: dict[str, str], *, public: bool = False) -> dict:
    return {
        "id": "g1",
        "description": description,
        "public": public,
        "html_url": "https://gist.github.com/g1",
        "files": {name: {"filename": name, "content": text} for name, text in files.items()},
    }


def test_new_gist_payload_and_create_confirmed(api: _Api) -> None:
    draft = GistDraft.new("doc.md", "# Hello", "Greeting")
    assert draft.create_payload(public=False) == {
        "description": "Greeting",
        "public": False,
        "files": {"doc.md": {"content": "# Hello"}},
    }
    api.replies[("POST", "/gists")] = RestResponse(
        201, {}, _gist_json("Greeting", {"doc.md": "# Hello"})
    )
    created = _Gists().create_gist(draft, public=False)
    assert created.visibility == "secret"


def test_create_gist_unconfirmed_visibility_is_refused(api: _Api) -> None:
    draft = GistDraft.new("doc.md", "x")
    api.replies[("POST", "/gists")] = RestResponse(
        201, {}, _gist_json("", {"doc.md": "x"}, public=True)
    )
    with pytest.raises(GitHubItemsError, match="did not confirm"):
        _Gists().create_gist(draft, public=False)


def test_empty_file_is_refused_before_sending() -> None:
    with pytest.raises(GitHubItemsError, match="is empty"):
        GistDraft.new("doc.md", "  ").create_payload(public=True)


def test_edit_draft_builds_one_patch_for_rename_delete_add_and_text() -> None:
    draft = GistDraft.from_gist(_gist(**{"a.md": "A", "b.md": "B", "c.md": "C"}))
    draft.description = "Better notes"
    draft.rename_file("a.md", "intro.md")
    draft.set_content("b.md", "B2")
    draft.delete_file("c.md")
    draft.add_file("new.txt", "N")
    assert draft.names() == ["intro.md", "b.md", "new.txt"]
    assert draft.changes() == {
        "description": "Better notes",
        "files": {
            "c.md": None,
            "a.md": {"filename": "intro.md"},
            "b.md": {"content": "B2"},
            "new.txt": {"content": "N"},
        },
    }
    summary = draft.summary()
    for words in (
        "change the description",
        "delete c.md",
        "rename a.md to intro.md",
        "add new.txt",
    ):
        assert words in summary


def test_unchanged_draft_sends_nothing(api: _Api) -> None:
    draft = GistDraft.from_gist(_gist(**{"a.md": "A"}))
    assert draft.changes() == {} and draft.summary() == "No changes."
    assert _Gists().update_gist("g1", draft) is None
    assert api.calls == []


def test_update_gist_confirms_the_files_github_kept(api: _Api) -> None:
    draft = GistDraft.from_gist(_gist(**{"a.md": "A", "b.md": "B"}))
    draft.delete_file("b.md")
    api.replies[("PATCH", "/gists/g1")] = RestResponse(
        200, {}, _gist_json("Notes", {"a.md": "A", "b.md": "B"})
    )
    with pytest.raises(GitHubItemsError, match="not the ones QUILL sent"):
        _Gists().update_gist("g1", draft)
    assert api.calls[0][2] == {"files": {"b.md": None}}
    api.replies[("PATCH", "/gists/g1")] = RestResponse(200, {}, _gist_json("Notes", {"a.md": "A"}))
    assert _Gists().update_gist("g1", draft) is not None


@pytest.mark.parametrize(
    ("act", "words"),
    [
        (lambda d: d.delete_file("a.md"), "at least one file"),
        (lambda d: d.add_file("a.md"), "already has"),
        (lambda d: d.add_file("x/y.md"), "slash"),
        (lambda d: d.add_file("gistfile1"), "reserves"),
        (lambda d: d.rename_file("a.md", ""), "needs a name"),
    ],
)
def test_draft_refusals(act: Any, words: str) -> None:
    draft = GistDraft.from_gist(_gist(**{"a.md": "A"}))
    with pytest.raises(GitHubItemsError, match=words):
        act(draft)


def test_reusing_a_renamed_name_waits_for_a_save() -> None:
    draft = GistDraft.from_gist(_gist(**{"a.md": "A", "b.md": "B"}))
    draft.rename_file("a.md", "z.md")
    with pytest.raises(GitHubItemsError, match="Save first"):
        draft.add_file("a.md", "new")
    # Renaming back to its own old name is fine.
    draft.rename_file("z.md", "a.md")
    assert draft.changes() == {}


def test_truncated_file_is_never_sent_back() -> None:
    gist = Gist(
        "g1", "", False, "", (GistFile("big.log", "partial", truncated=True), GistFile("s", "x"))
    )
    draft = GistDraft.from_gist(gist)
    assert draft.is_truncated("big.log")
    with pytest.raises(GitHubItemsError, match="too large"):
        draft.set_content("big.log", "changed")
    draft.rename_file("big.log", "huge.log")
    assert draft.changes() == {"files": {"big.log": {"filename": "huge.log"}}}


def test_star_unstar_delete_and_star_state(api: _Api) -> None:
    api.replies[("PUT", "/gists/g1/star")] = RestResponse(204, {}, None)
    api.replies[("DELETE", "/gists/g1/star")] = RestResponse(204, {}, None)
    api.replies[("DELETE", "/gists/g1")] = RestResponse(204, {}, None)
    api.replies[("GET", "/gists/g1/star")] = GitHubRestError("Not Found", status=404)
    client = _Gists()
    client.set_gist_starred("g1", True)
    client.set_gist_starred("g1", False)
    client.delete_gist("g1")
    assert client.is_gist_starred("g1") is False
    assert [call[:2] for call in api.calls[:3]] == [
        ("PUT", "/gists/g1/star"),
        ("DELETE", "/gists/g1/star"),
        ("DELETE", "/gists/g1"),
    ]


def test_gist_write_unconfirmed_status_is_not_success(api: _Api) -> None:
    api.replies[("DELETE", "/gists/g1")] = RestResponse(200, {}, None)
    with pytest.raises(GitHubItemsError, match="without confirming"):
        _Gists().delete_gist("g1")


def test_gists_need_an_account(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Gists(token=None).delete_gist("g1")
    assert api.calls == []


def test_parse_gist_reads_files_and_rejects_nothing() -> None:
    gist = parse_gist(_gist_json("D", {"a.md": "A"}, public=True))
    assert gist.public and gist.file("a.md") == GistFile("a.md", "A")
    with pytest.raises(GitHubItemsError):
        parse_gist({})


# -- Attention queue summaries -------------------------------------------------------


def _row(number: int, *, kind: str = "pr", reason: str = "Review requested") -> ExploreRow:
    label = f"o/r #{number}: Title {number} (PR)"
    return ExploreRow(label, f"{reason}\n{label}\nState: open", "", "o/r", kind, str(number))


def test_queue_summaries_are_one_request_and_keep_the_reason() -> None:
    calls: list[list[PullRef]] = []

    def fetch(refs):
        calls.append(list(refs))
        return [
            PullSummary("o/r", 1, state="OPEN", review_decision="APPROVED", open_threads=1),
            PullSummary("o/r", 3, error="GitHub returned no pull request."),
        ]

    rows = [_row(1), _row(2, kind="issue", reason="Assigned"), _row(3)]
    out, warning = summarize_queue_rows(rows, fetch)
    assert len(calls) == 1 and [ref.number for ref in calls[0]] == [1, 3]
    assert out[0].label.startswith("o/r #1: Title 1 (PR). Approved, no checks, 1 open thread")
    assert out[0].detail.splitlines()[0] == "Review requested"
    assert out[0].detail.splitlines()[1].startswith("Summary: Approved")
    assert out[1] == rows[1]
    assert out[2].label.endswith("Summary unavailable")
    assert "did not summarise 1 pull request" in warning


def test_queue_summaries_never_claim_ready_on_partial_data() -> None:
    def fetch(refs):
        return [
            PullSummary(
                "o/r",
                1,
                state="OPEN",
                merge_state="CLEAN",
                mergeable="MERGEABLE",
                review_decision="APPROVED",
                checks_complete=False,
            )
        ]

    out, _warning = summarize_queue_rows([_row(1)], fetch)
    assert "can merge" not in out[0].label


def test_queue_summaries_cover_the_newest_batch_and_say_so() -> None:
    sizes: list[int] = []

    def fetch(refs):
        sizes.append(len(refs))
        return [PullSummary(ref.full_name, ref.number, state="OPEN") for ref in refs]

    rows = [_row(n + 1) for n in range(SUMMARY_LIMIT + 5)]
    out, warning = summarize_queue_rows(rows, fetch)
    assert sizes == [SUMMARY_LIMIT]
    assert "newest 20 of 25" in warning
    assert out[-1] == rows[-1]


def test_queue_summaries_failure_keeps_rows_and_says_why() -> None:
    def fetch(refs):
        raise GitHubItemsError("Sign in to GitHub to read pull request summaries.")

    rows = [_row(1)]
    out, warning = summarize_queue_rows(rows, fetch)
    assert out == tuple(rows) and warning.startswith("Pull request summaries unavailable")


def test_queue_without_pulls_or_provider_support_makes_no_request() -> None:
    def fetch(refs):  # pragma: no cover - must not be called
        raise AssertionError("no request expected")

    rows = [_row(2, kind="issue")]
    assert summarize_queue_rows(rows, fetch) == (tuple(rows), "")
    assert summarize_queue_rows([_row(1)], None) == ((_row(1),), "")


def test_attention_fetch_attaches_summaries_in_one_call() -> None:
    from quill.core.github.attention_queue_fetch import fetch_attention_queue

    issue = SimpleNamespace(
        repository=SimpleNamespace(full_name="o/r"),
        number=4,
        title="Fix it",
        html_url="https://github.com/o/r/pull/4",
        pull_request=SimpleNamespace(),
        state="open",
        updated_at="2026-11-07T00:00:00",
    )
    batches: list[int] = []

    class _P:
        is_authenticated = True
        _gh = SimpleNamespace(
            get_user=lambda: SimpleNamespace(login="me"), search_issues=lambda _q: [issue]
        )

        def fetch_pull_summaries(self, refs):
            batches.append(len(refs))
            return [PullSummary("o/r", 4, state="OPEN", review_decision="CHANGES_REQUESTED")]

    result = fetch_attention_queue(_P(), categories=["review_requested"])  # type: ignore[arg-type]
    assert batches == [1]
    assert result.complete
    assert result.items[0].label.endswith(
        "Changes requested, no checks, no open threads, merge readiness unknown"
    )
