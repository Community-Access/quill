"""Wave 2 pull-request review: line comments, since-review, timeline, reactions, summary."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import items_provider_review, reactions, timeline
from quill.core.github import pr_summary as summary_mod
from quill.core.github.diff_lines import (
    LINE_MARKS_SYMBOLS,
    LineCommentAnchor,
    anchor_for,
    lines_for_range,
    parse_diff_lines,
    parse_range,
    render_line,
    strip_suggestion_block,
    suggestion_block,
    unified_diff_text,
)
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider_review import GitHubPullReviewExtrasMixin
from quill.core.github.line_comment_drafts import LineCommentDraftStore
from quill.core.github.pr_summary import PullRef, PullSummary, build_summary_query
from quill.core.github.reactions import reaction_choices, reaction_counts_in_words
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_preferences import load_line_marks, save_line_marks
from quill.core.github.review_thread_models import GitHubCheckRun
from quill.core.github.timeline import build_timeline, timeline_entry

PATCH = "@@ -10,3 +10,4 @@ def run():\n keep = 1\n-old = 2\n+new = 2\n+extra = 3\n tail = 4\n"
SHA = "a" * 40


# -- diff lines --------------------------------------------------------------


def test_patch_lines_carry_both_line_numbers_and_render_in_both_styles() -> None:
    lines = parse_diff_lines(PATCH)
    kinds = [line.kind for line in lines]
    assert kinds == ["hunk", "context", "removed", "added", "added", "context"]
    removed, added = lines[2], lines[3]
    assert (removed.side, removed.line) == ("LEFT", 11)
    assert (added.side, added.line) == ("RIGHT", 11)
    assert render_line(added) == "Added line 11: new = 2"
    assert render_line(removed) == "Removed line 11: old = 2"
    assert render_line(added, LINE_MARKS_SYMBOLS) == "+ 11: new = 2"
    assert render_line(removed, LINE_MARKS_SYMBOLS) == "- 11: old = 2"
    assert render_line(lines[0]).startswith("Changes at old line 10, new line 10")


def test_anchor_for_one_line_and_a_range_matches_the_rest_payload() -> None:
    lines = parse_diff_lines(PATCH)
    single = anchor_for("app.py", [lines[3]])
    assert single.payload() == {"path": "app.py", "line": 11, "side": "RIGHT"}
    assert single.describe() == "line 11 of app.py"
    ranged = anchor_for("app.py", lines[3:5])
    assert ranged.payload() == {
        "path": "app.py",
        "line": 12,
        "side": "RIGHT",
        "start_line": 11,
        "start_side": "RIGHT",
    }
    assert ranged.describe() == "lines 11 to 12 of app.py"
    mixed = anchor_for("app.py", lines[2:4])
    assert mixed.describe() == "old line 11 to line 11 of app.py"


def test_anchor_refuses_headings_and_ranges_across_hunks() -> None:
    lines = parse_diff_lines(PATCH + "@@ -40 +41 @@\n+later\n")
    with pytest.raises(GitHubReviewError, match="Move to one"):
        anchor_for("app.py", [lines[0]])
    with pytest.raises(GitHubReviewError, match="same hunk"):
        anchor_for("app.py", [lines[3], lines[-1]])


def test_typed_range_must_be_in_the_patch() -> None:
    lines = parse_diff_lines(PATCH)
    assert parse_range("11-12") == (11, 12)
    assert parse_range("12 to 11") == (12, 11)
    found = lines_for_range(lines, 12, 11)
    assert [line.new_line for line in found] == [11, 12]
    with pytest.raises(GitHubReviewError, match="Line 14 is not"):
        lines_for_range(lines, 12, 99)


def test_suggestion_block_holds_new_file_text_and_can_be_removed() -> None:
    lines = parse_diff_lines(PATCH)
    block = suggestion_block(lines[2:5])
    assert block == "```suggestion\nnew = 2\nextra = 3\n```"
    with pytest.raises(GitHubReviewError, match="new file"):
        suggestion_block([lines[2]])
    assert strip_suggestion_block(f"Try this:\n\n{block}") == "Try this:"


def test_unified_diff_text_writes_git_headers() -> None:
    class _File:
        filename = "app.py"
        previous_filename = ""
        status = "modified"
        patch = PATCH

    class _Binary:
        filename = "logo.png"
        previous_filename = ""
        status = "added"
        patch = ""

    text = unified_diff_text([_File(), _Binary()])
    assert "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -10,3" in text
    assert "Binary files /dev/null and b/logo.png differ" in text


def test_line_mark_preference_round_trips(tmp_path) -> None:
    path = tmp_path / "prefs.json"
    assert load_line_marks(path) == "words"
    assert save_line_marks("symbols", path)
    assert load_line_marks(path) == "symbols"
    assert not save_line_marks("emoji", path)


# -- pending line comment drafts --------------------------------------------


def test_pending_line_comments_are_kept_per_pull_and_account(tmp_path) -> None:
    path = tmp_path / "drafts.json"
    store = LineCommentDraftStore.load("token-a", path)
    anchor = LineCommentAnchor("app.py", 12, "RIGHT", 11, "RIGHT")
    added = store.add("owner/repo", 7, anchor, "Rename this.", SHA)
    assert added is not None
    again = LineCommentDraftStore.load("token-a", path)
    pending = again.pending("owner/repo", 7)
    assert [comment.body for comment in pending] == ["Rename this."]
    assert pending[0].review_payload() == {**anchor.payload(), "body": "Rename this."}
    assert LineCommentDraftStore.load("token-b", path).pending("owner/repo", 7) == ()
    assert again.update("owner/repo", 7, pending[0].id, "Rename this, please.")
    assert again.pending("owner/repo", 7)[0].body == "Rename this, please."
    assert again.remove("owner/repo", 7, pending[0].id)
    assert again.pending("owner/repo", 7) == ()
    assert store.add("owner/repo", 7, anchor, "   ", SHA) is None


# -- reactions ---------------------------------------------------------------


def test_reaction_counts_read_in_words() -> None:
    assert reaction_counts_in_words({"+1": 3, "heart": 1, "laugh": 0, "total_count": 4}) == (
        "3 thumbs up, 1 heart"
    )
    assert reaction_counts_in_words({"rocket": 2}) == "2 rockets"
    assert reaction_counts_in_words(None) == ""
    labels = dict(reaction_choices({"heart"}))
    assert labels["+1"] == "thumbs up"
    assert labels["heart"].startswith("heart, yours")
    assert len(labels) == 8


class _Provider(GitHubPullReviewExtrasMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"sign in to {action}")


class _Rest:
    """Replays queued responses and records each request."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, token, method, path, **kwargs) -> RestResponse:
        self.calls.append((method, path, kwargs))
        reply = self.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply  # type: ignore[return-value]


def test_add_and_remove_reaction_say_only_what_github_confirmed(monkeypatch) -> None:
    rest = _Rest(
        RestResponse(201, data={"content": "heart"}),
        RestResponse(200, data={"login": "me"}),
        RestResponse(200, data=[{"id": 5, "content": "heart", "user": {"login": "other"}}]),
    )
    monkeypatch.setattr(reactions, "request_json", rest)
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    provider = _Provider()
    assert provider.add_reaction("owner/repo", "issue", 7, "heart") == "Added heart."
    assert rest.calls[0][:2] == ("POST", "/repos/owner/repo/issues/7/reactions")
    message = provider.remove_reaction("owner/repo", "review_comment", 9, "heart")
    assert "nothing to remove" in message  # someone else's heart is never deleted
    assert all(method != "DELETE" for method, _path, _kw in rest.calls)
    with pytest.raises(GitHubItemsError, match="eight"):
        provider.add_reaction("owner/repo", "issue", 7, "party")


def test_remove_reaction_deletes_only_the_accounts_own(monkeypatch) -> None:
    rest = _Rest(
        RestResponse(200, data={"login": "Me"}),
        RestResponse(200, data=[{"id": 42, "content": "+1", "user": {"login": "me"}}]),
        RestResponse(204),
    )
    monkeypatch.setattr(reactions, "request_json", rest)
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    assert (
        _Provider().remove_reaction("owner/repo", "issue_comment", 3, "+1") == "Removed thumbs up."
    )
    assert rest.calls[-1][:2] == ("DELETE", "/repos/owner/repo/issues/comments/3/reactions/42")


# -- line comments and reviews ----------------------------------------------


def test_post_line_comment_sends_the_anchor_and_needs_github_confirmation(monkeypatch) -> None:
    rest = _Rest(RestResponse(201, data={"id": 77, "html_url": "https://x"}))
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    anchor = LineCommentAnchor("app.py", 12, "RIGHT", 11, "RIGHT")
    posted = _Provider().post_line_comment("owner/repo", 7, anchor, "Nice.", SHA)
    assert posted.id == 77
    method, path, kwargs = rest.calls[0]
    assert (method, path) == ("POST", "/repos/owner/repo/pulls/7/comments")
    assert kwargs["body"]["commit_id"] == SHA
    assert kwargs["body"]["start_line"] == 11
    rest.responses.append(RestResponse(202, data={}))
    with pytest.raises(GitHubItemsError, match="without confirming"):
        _Provider().post_line_comment("owner/repo", 7, anchor, "Nice.", SHA)
    with pytest.raises(GitHubItemsError, match="sign in"):
        _Provider(token=None).post_line_comment("owner/repo", 7, anchor, "Nice.", SHA)


def test_review_with_pending_comments_is_one_request(tmp_path, monkeypatch) -> None:
    store = LineCommentDraftStore.load("tok", tmp_path / "d.json")
    store.add("owner/repo", 7, LineCommentAnchor("app.py", 11), "Why?", SHA)
    rest = _Rest(RestResponse(200, data={"id": 1, "state": "COMMENTED"}))
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    sent = _Provider().submit_review_with_comments(
        "owner/repo", 7, "comment", "", store.pending("owner/repo", 7), SHA
    )
    assert sent == " with 1 line comment"
    body = rest.calls[0][2]["body"]
    assert body["event"] == "COMMENT"
    assert body["comments"] == [{"path": "app.py", "line": 11, "side": "RIGHT", "body": "Why?"}]
    rest.responses.append(RestResponse(200, data={"id": 1, "state": "PENDING"}))
    with pytest.raises(GitHubItemsError, match="pending"):
        _Provider().submit_review_with_comments(
            "owner/repo", 7, "comment", "", store.pending("owner/repo", 7), SHA
        )


# -- changed since my last review --------------------------------------------


def _reviews(*rows: dict[str, Any]) -> RestResponse:
    return RestResponse(200, data=list(rows))


def test_changes_since_my_review_counts_files(monkeypatch) -> None:
    rest = _Rest(
        RestResponse(200, data={"login": "me"}),
        _reviews(
            {
                "user": {"login": "me"},
                "commit_id": "b" * 40,
                "submitted_at": "2026-11-01T10:00:00Z",
            },
            {
                "user": {"login": "me"},
                "commit_id": "c" * 40,
                "submitted_at": "2026-11-03T09:00:00Z",
            },
            {
                "user": {"login": "you"},
                "commit_id": "d" * 40,
                "submitted_at": "2026-11-05T09:00:00Z",
            },
        ),
        RestResponse(
            200, data={"behind_by": 0, "files": [{"filename": f"f{i}"} for i in range(4)]}
        ),
    )
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    result = _Provider().fetch_changes_since_my_review("owner/repo", 7, SHA)
    assert result.sentence() == "4 files changed since your review on 2026-11-03."
    assert rest.calls[-1][1] == f"/repos/owner/repo/compare/{'c' * 40}...{SHA}"


def test_force_pushed_review_commit_is_said_plainly(monkeypatch) -> None:
    rest = _Rest(
        RestResponse(200, data={"login": "me"}),
        _reviews({"user": {"login": "me"}, "commit_id": "c" * 40, "submitted_at": "2026-11-03"}),
        GitHubRestError("Not Found", status=404),
    )
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    result = _Provider().fetch_changes_since_my_review("owner/repo", 7, SHA)
    assert result.commit_missing
    assert "force-pushed" in result.sentence()


def test_no_earlier_review_says_so(monkeypatch) -> None:
    rest = _Rest(RestResponse(200, data={"login": "me"}), _reviews())
    monkeypatch.setattr(items_provider_review, "request_json", rest)
    result = _Provider().fetch_changes_since_my_review("owner/repo", 7, SHA)
    assert not result.reviewed
    assert "not reviewed" in result.sentence()


# -- timeline ----------------------------------------------------------------


def test_timeline_events_read_as_one_line_each_newest_last() -> None:
    rows = [
        {
            "event": "merged",
            "actor": {"login": "a"},
            "created_at": "2026-11-05T12:00:00Z",
            "commit_id": "f" * 40,
        },
        {
            "event": "labeled",
            "actor": {"login": "b"},
            "created_at": "2026-11-01T08:30:00Z",
            "label": {"name": "bug"},
        },
        {
            "event": "reviewed",
            "user": {"login": "c"},
            "submitted_at": "2026-11-02T09:00:00Z",
            "state": "approved",
        },
        {
            "event": "committed",
            "sha": "1234567890",
            "message": "Fix it\n\nbody",
            "author": {"name": "Dev", "date": "2026-11-01T09:00:00Z"},
        },
        {
            "event": "head_ref_force_pushed",
            "actor": {"login": "d"},
            "created_at": "2026-11-03T00:00:00Z",
        },
        {
            "event": "cross-referenced",
            "actor": {"login": "e"},
            "created_at": "2026-11-04T00:00:00Z",
            "source": {
                "issue": {"number": 9, "title": "Related", "repository": {"full_name": "o/r"}}
            },
        },
        {"event": "subscribed", "actor": {"login": "x"}, "created_at": "2026-11-01T00:00:00Z"},
    ]
    result = build_timeline(rows)
    lines = [entry.line for entry in result.entries]
    assert lines == [
        "2026-11-01 08:30, b: added the label bug",
        "2026-11-01 09:00, Dev: committed 1234567: Fix it",
        "2026-11-02 09:00, c: approved",
        "2026-11-03 00:00, d: force-pushed the branch",
        "2026-11-04 00:00, e: mentioned this in o/r#9: Related",
        "2026-11-05 12:00, a: merged this as fffffff",
    ]
    assert (
        timeline_entry({
            "event": "assigned",
            "actor": {"login": "a"},
            "assignee": {"login": "b"},
        }).text
        == "assigned b"
    )


def test_timeline_pages_and_says_when_it_stopped_early(monkeypatch) -> None:
    page = [{"event": "closed", "actor": {"login": "a"}, "created_at": "2026-11-01"}] * 100
    rest = _Rest(*[RestResponse(200, {"link": '<x>; rel="next"'}, page)] * 5)
    monkeypatch.setattr(timeline, "request_json", rest)
    result = _Provider().fetch_timeline("owner/repo", 7)
    assert not result.complete
    assert "first 500 events" in result.note
    assert len(rest.calls) == 5
    rest = _Rest(RestResponse(200, {}, page[:3]))
    monkeypatch.setattr(timeline, "request_json", rest)
    done = _Provider().fetch_timeline("owner/repo", 7)
    assert done.complete and done.note == "Complete history: 3 events."


# -- one-sentence summary ----------------------------------------------------


def _pull(**overrides: Any) -> dict[str, Any]:
    pull: dict[str, Any] = {
        "title": "Add feature",
        "state": "OPEN",
        "isDraft": False,
        "merged": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "BEHIND",
        "reviewDecision": "APPROVED",
        "baseRefName": "main",
        "headRefName": "feature",
        "headRefOid": SHA,
        "isCrossRepository": False,
        "autoMergeRequest": None,
        "reviewThreads": {
            "totalCount": 2,
            "pageInfo": {"hasNextPage": False},
            "nodes": [{"isResolved": False}, {"isResolved": True}],
        },
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "state": "FAILURE",
                            "contexts": {
                                "pageInfo": {"hasNextPage": False},
                                "nodes": [
                                    {
                                        "__typename": "CheckRun",
                                        "name": "a",
                                        "status": "COMPLETED",
                                        "conclusion": "FAILURE",
                                    },
                                    {
                                        "__typename": "CheckRun",
                                        "name": "b",
                                        "status": "COMPLETED",
                                        "conclusion": "TIMED_OUT",
                                    },
                                    {
                                        "__typename": "StatusContext",
                                        "context": "c",
                                        "state": "SUCCESS",
                                    },
                                ],
                            },
                        }
                    }
                }
            ]
        },
        "baseRef": {"compare": {"aheadBy": 2, "behindBy": 3}},
    }
    pull.update(overrides)
    return pull


def test_summary_sentence_matches_the_example() -> None:
    summary = summary_mod.parse_pull_summary(
        PullRef("owner/repo", 7, "feature"), _pull(), compare_requested=True
    )
    assert summary.sentence() == (
        "Approved, 2 checks failing, 1 open thread, 3 commits behind main."
    )


def test_summary_never_claims_ready_on_partial_data() -> None:
    clean = _pull(mergeStateStatus="CLEAN", baseRef={"compare": {"behindBy": 0}})
    clean["commits"]["nodes"][0]["commit"]["statusCheckRollup"]["contexts"]["nodes"] = [
        {"__typename": "CheckRun", "name": "a", "status": "COMPLETED", "conclusion": "SUCCESS"}
    ]
    clean["reviewThreads"]["nodes"] = []
    ready = summary_mod.parse_pull_summary(
        PullRef("o/r", 1, "feature"), clean, compare_requested=True
    )
    assert ready.sentence().endswith("GitHub reports it can merge.")
    clean["reviewThreads"]["pageInfo"] = {"hasNextPage": True}
    partial = summary_mod.parse_pull_summary(PullRef("o/r", 1), clean)
    assert "can merge" not in partial.sentence()
    assert "merge readiness unknown" in partial.sentence()


def test_fork_branch_names_are_not_compared() -> None:
    summary = summary_mod.parse_pull_summary(
        PullRef("o/r", 1, "main"), _pull(isCrossRepository=True), compare_requested=True
    )
    assert summary.behind_by is None
    assert "behind main" in summary.sentence()  # from mergeStateStatus, without a count


def test_summary_query_batches_with_aliases(monkeypatch) -> None:
    query, variables = build_summary_query([PullRef("o/r", 1, "x"), PullRef("o/s", 2)])
    assert "p0: repository(owner:$o0" in query and "p1: repository(owner:$o1" in query
    assert variables["c0"] is True and variables["c1"] is False
    seen: list[list[str] | None] = []

    def fake_request(token, query, variables, *, errors_out=None):
        seen.append(errors_out)
        return {"p0": {"pullRequest": _pull()}, "p1": None}

    monkeypatch.setattr(summary_mod, "_request", fake_request)
    first, second = summary_mod.fetch_pull_summaries("tok", [PullRef("o/r", 1), PullRef("o/s", 2)])
    assert first.review_decision == "APPROVED" and not first.error
    assert second.sentence().startswith("Summary unavailable")
    assert seen == [[]]


def test_summary_text_for_closed_and_unknown_checks() -> None:
    assert PullSummary("o/r", 1, merged=True).sentence() == "Merged."
    open_pull = PullSummary(
        "o/r",
        1,
        state="OPEN",
        review_decision="REVIEW_REQUIRED",
        checks=(GitHubCheckRun("ci", "in_progress", ""),),
        auto_merge=True,
    )
    assert open_pull.sentence() == (
        "Review required, 1 check running, no open threads, auto-merge on, merge readiness unknown."
    )
