"""Wave 2 review UI: summary line, since-review filter, pending comments, diff lines."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.github import line_comment_drafts, local_drafts, review_preferences
from quill.core.github.diff_lines import LineCommentAnchor
from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile
from quill.core.github.items_provider_review import ChangesSinceReview
from quill.core.github.pr_review import (
    GitHubCheckRun,
    GitHubPullReviewState,
    GitHubReviewComment,
    GitHubReviewThread,
)
from quill.core.github.pr_summary import PullSummary
from quill.core.github.timeline import TimelineEntry, TimelineResult
from quill.ui.github_line_comment_dialog import ADD_TO_REVIEW, LineCommentChoice
from quill.ui.github_pr_diff_dialog import GitHubPullDiffDialog
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog
from quill.ui.github_timeline_dialog import GitHubTimelineDialog
from tests.wx_session import patch_call_after, shared_wx_app

SHA = "a" * 40
PATCH = "@@ -1,2 +1,3 @@\n keep\n-old\n+new\n+more\n"


class _SyncThread:
    def __init__(self, *, target, daemon):
        self._target = target

    def start(self):
        self._target()


class _Provider:
    is_authenticated = True
    token = "tok"

    def __init__(self) -> None:
        self.posted: list[tuple[Any, ...]] = []

    def fetch_file_text(self, _repo: str, _path: str, _ref: str) -> str:
        return "keep\nnew\nmore\n"

    def post_line_comment(self, *args: Any) -> None:
        self.posted.append(args)

    def fetch_changes_since_my_review(self, _repo, _number, _head) -> ChangesSinceReview:
        return ChangesSinceReview(True, "b" * 40, "2026-11-03T10:00:00Z", files=("src/b.py",))


@pytest.fixture(scope="module")
def wx_app():
    return shared_wx_app()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    for module in (local_drafts, line_comment_drafts, review_preferences):
        monkeypatch.setattr(module, "app_data_dir", lambda: tmp_path)
    return tmp_path


def _state() -> GitHubPullReviewState:
    return GitHubPullReviewState(
        number=7,
        title="Add feature",
        state="open",
        draft=False,
        merged=False,
        mergeable=True,
        mergeable_state="clean",
        base_ref="main",
        head_ref="feature",
        head_sha=SHA,
        checks=(GitHubCheckRun("CI", "completed", "success"),),
    )


def _thread(path: str, comment_id: int) -> GitHubReviewThread:
    return GitHubReviewThread(
        comments=(
            GitHubReviewComment(
                id=comment_id,
                author="reviewer",
                body="Why?",
                path=path,
                line=3,
                reactions="2 thumbs up, 1 heart",
            ),
        )
    )


def _diff() -> GitHubPullDiff:
    return GitHubPullDiff(
        number=7,
        title="Add feature",
        base_ref="main",
        base_sha="b" * 40,
        head_ref="feature",
        head_sha=SHA,
        files=(
            GitHubPullFile("src/a.py", "modified", 2, 1, patch=PATCH),
            GitHubPullFile("src/b.py", "modified", 1, 0, patch=PATCH),
        ),
    )


@pytest.fixture
def review(wx_app, data_dir):
    frame = wx.Frame(None)
    spoken: list[str] = []
    dialog = GitHubPullReviewDialog(frame, _Provider(), "owner/repo", 7, announce_cb=spoken.append)
    dialog.spoken = spoken
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def _children(tree, item):
    out = []
    child, cookie = tree.GetFirstChild(item)
    while child.IsOk():
        out.append(child)
        child, cookie = tree.GetNextChild(item, cookie)
    return out


def test_summary_sentence_is_shown_and_said_once(review) -> None:
    summary = PullSummary(
        "owner/repo", 7, state="OPEN", review_decision="APPROVED", base_ref="main", behind_by=3
    )
    review._refresh_ready(_state(), (), _diff(), summary)
    assert review._one_line.GetLabel().startswith("Approved, no checks")
    assert "3 commits behind main" in review.spoken[-1]
    review._refresh_ready(_state(), (), _diff(), summary)
    assert "3 commits behind main" not in review.spoken[-1]


def test_reaction_counts_read_in_thread_detail(review) -> None:
    review._refresh_ready(_state(), (_thread("src/a.py", 11),), _diff())
    review._outline.SelectItem(review._thread_items[0])
    review._select_node(None)
    assert "Reactions: 2 thumbs up, 1 heart" in review._thread_detail.GetValue()


def test_changed_since_my_review_narrows_the_outline(review, monkeypatch) -> None:
    patch_call_after(monkeypatch)
    monkeypatch.setattr("quill.ui.github_pr_review_extras.threading.Thread", _SyncThread)
    threads = (_thread("src/a.py", 11), _thread("src/b.py", 12))
    review._refresh_ready(_state(), threads, _diff())
    review._since_check.SetValue(True)
    review._toggle_since_filter(None)
    root = review._outline.GetRootItem()
    files = _children(review._outline, root)[0]
    assert review._outline.GetItemText(files) == "Files changed since your last review"
    assert [review._outline.GetItemText(item) for item in _children(review._outline, files)] == [
        "src/b.py"
    ]
    assert review.spoken[-1] == "1 file changed since your review on 2026-11-03."
    review._next_thread(unresolved_only=False)  # the hidden file's thread is skipped
    review._since_check.SetValue(False)
    review._toggle_since_filter(None)
    files = _children(review._outline, review._outline.GetRootItem())[0]
    assert len(_children(review._outline, files)) == 2


def test_stale_since_result_is_dropped(review) -> None:
    review._refresh_ready(_state(), (), _diff())
    review._since_check.SetValue(True)
    review._since_loaded(review._since_generation - 1, SHA, ChangesSinceReview(True))
    assert review._since_files is None


def test_pending_comments_are_listed_and_deleted_after_confirming(review, monkeypatch) -> None:
    review._line_comment_store.add("owner/repo", 7, LineCommentAnchor("src/a.py", 2), "Hm.", SHA)
    review._refresh_ready(_state(), (), _diff())
    root = review._outline.GetRootItem()
    pending_root = next(
        item
        for item in _children(review._outline, root)
        if review._outline.GetItemText(item).startswith("Pending line comments")
    )
    node = _children(review._outline, pending_root)[0]
    assert review._outline.GetItemText(node) == "line 2 of src/a.py: Hm."
    review._outline.SelectItem(node)
    review._select_node(None)
    assert "Pending, not sent yet" in review._thread_detail.GetValue()
    menu, _ids = review._build_node_menu()
    labels = [menu.GetLabelText(int(item_id)) for item_id in _ids]
    menu.Destroy()
    assert "Delete Pending Comment..." in labels
    monkeypatch.setattr(review, "_confirm", lambda *_args: True)
    review._delete_pending(None)
    assert review._pending_comments() == ()


def test_pull_request_menu_offers_timeline_and_reaction(review) -> None:
    review._refresh_ready(_state(), (), _diff())
    review._outline.SelectItem(review._outline.GetRootItem())
    menu, _ids = review._build_node_menu()
    labels = [menu.GetLabelText(int(item_id)) for item_id in _ids]
    menu.Destroy()
    assert "View Timeline..." in labels
    assert "React to Pull Request..." in labels


@pytest.fixture
def diff_dialog(wx_app, data_dir, monkeypatch):
    monkeypatch.setattr("quill.ui.github_pr_diff_dialog.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch)
    frame = wx.Frame(None)
    spoken: list[str] = []
    provider = _Provider()
    dialog = GitHubPullDiffDialog(frame, provider, "owner/repo", _diff(), announce_cb=spoken.append)
    dialog.spoken = spoken
    dialog.provider = provider
    dialog._files.SetSelection(0)
    dialog._on_select(None)
    yield dialog
    dialog.dialog.Destroy()
    frame.Destroy()


def test_patch_lines_follow_the_line_mark_style(diff_dialog) -> None:
    assert diff_dialog._patch_list.GetString(3) == "Added line 2: new"
    diff_dialog._marks_choice.SetSelection(1)
    diff_dialog._on_marks_changed(None)
    assert diff_dialog._patch_list.GetString(3) == "+ 2: new"
    assert "punctuation" in diff_dialog.spoken[-1]
    assert review_preferences.load_line_marks() == "symbols"


def test_comment_on_lines_adds_to_the_pending_review(diff_dialog, monkeypatch) -> None:
    diff_dialog._patch_list.SetSelection(3)
    diff_dialog._patch_list.SetSelection(4)
    seen: dict[str, Any] = {}

    class _Composer:
        def __init__(self, _parent, **kwargs):
            seen.update(kwargs)

        def show(self):
            return LineCommentChoice(ADD_TO_REVIEW, "Use a constant.")

    monkeypatch.setattr("quill.ui.github_line_comment_dialog.GitHubLineCommentDialog", _Composer)
    diff_dialog._comment_on_lines(None)
    assert seen["anchor"].describe() == "lines 2 to 3 of src/a.py"
    pending = diff_dialog._pending_store.pending("owner/repo", 7)
    assert [comment.body for comment in pending] == ["Use a constant."]
    assert pending[0].head_sha == SHA
    assert "1 line comment waiting" in diff_dialog._pending_label.GetLabel()


def test_post_now_sends_one_comment_off_the_ui_thread(diff_dialog, monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.github_pr_diff_comments.threading.Thread", _SyncThread)
    diff_dialog._post_line_comment(LineCommentAnchor("src/a.py", 2), "Nice.")
    assert diff_dialog.provider.posted[0][:2] == ("owner/repo", 7)
    assert diff_dialog.spoken[-1] == "GitHub posted your comment on line 2 of src/a.py."


def test_timeline_dialog_shows_the_history(wx_app) -> None:
    frame = wx.Frame(None)
    spoken: list[str] = []
    dialog = GitHubTimelineDialog(frame, object(), "owner/repo", 7, announce_cb=spoken.append)
    try:
        result = TimelineResult(
            (TimelineEntry("2026-11-01T10:00:00Z", "a", "closed this"),),
            note="Complete history: 1 events.",
        )
        dialog._ready(result)
        assert dialog._text.GetValue().startswith("2026-11-01 10:00, a: closed this")
        assert spoken[-1] == "Timeline loaded, 1 event."
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


# -- hearing a diff (GitHub PRD 22.12) --------------------------------------------


def test_changed_lines_only_leaves_out_the_unchanged_and_keeps_the_mapping(diff_dialog) -> None:
    every = [
        diff_dialog._patch_list.GetString(i) for i in range(diff_dialog._patch_list.GetCount())
    ]
    diff_dialog._changed_only.SetValue(True)
    diff_dialog._on_changed_only(None)
    shown = [
        diff_dialog._patch_list.GetString(i) for i in range(diff_dialog._patch_list.GetCount())
    ]
    assert len(shown) < len(every)
    assert not any(row.startswith("Unchanged") for row in shown)
    assert shown[0] == every[0]  # the hunk heading stays
    assert "changed line" in diff_dialog.spoken[-1] and "unchanged" in diff_dialog.spoken[-1]
    added = next(i for i, row in enumerate(shown) if row.startswith("Added"))
    diff_dialog._patch_list.SetSelection(added)
    assert [line.kind for line in diff_dialog._selected_patch_lines()] == ["added"]
    diff_dialog._changed_only.SetValue(False)
    diff_dialog._on_changed_only(None)
    assert diff_dialog._patch_list.GetCount() == len(every)
    assert [line.kind for line in diff_dialog._selected_patch_lines()] == ["added"]


def test_arriving_on_an_added_or_removed_line_plays_its_sound(diff_dialog, monkeypatch) -> None:
    played: list[str] = []
    monkeypatch.setattr("quill.ui.sound_manager.post_sound", played.append)
    kinds = [line.kind for line in diff_dialog._patch_lines]
    for kind, sound in (("added", "diff_line_added"), ("removed", "diff_line_removed")):
        if kind not in kinds:
            continue
        diff_dialog._patch_list.SetSelection(wx.NOT_FOUND)
        diff_dialog._patch_list.SetSelection(kinds.index(kind))
        diff_dialog._on_patch_line(None)
        assert played[-1] == sound
    before = len(played)
    diff_dialog._patch_list.SetSelection(wx.NOT_FOUND)
    diff_dialog._patch_list.SetSelection(0)
    diff_dialog._on_patch_line(None)
    assert len(played) == before


# -- hiding whitespace and one commit at a time ---------------------------------


def test_hide_whitespace_changes_leaves_out_only_whitespace(diff_dialog) -> None:
    from quill.core.github.diff_lines import parse_diff_lines

    diff_dialog._patch_lines = parse_diff_lines("@@ -1,2 +1,2 @@\n-  a\n-b\n+    a\n+c\n")
    diff_dialog._render_patch_lines()
    assert diff_dialog._patch_list.GetCount() == 5
    diff_dialog._hide_ws.SetValue(True)
    diff_dialog._on_hide_whitespace(None)
    shown = [
        diff_dialog._patch_list.GetString(i) for i in range(diff_dialog._patch_list.GetCount())
    ]
    assert shown[1:] == ["Removed line 2: b", "Added line 2: c"]
    assert diff_dialog.spoken[-1] == "2 changed lines that only change whitespace left out."


def test_choose_commit_shows_one_commit_and_back(diff_dialog, monkeypatch) -> None:
    from quill.core.github import commit_review
    from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile

    monkeypatch.setattr("quill.ui.github_pr_diff_comments.threading.Thread", _SyncThread)
    commits = [commit_review.PullCommit("c" * 40, "One step", "ann")]
    monkeypatch.setattr(commit_review, "pull_commits", lambda *_a: commits)
    only = (GitHubPullFile("only.py", "modified", 1, 0, patch=PATCH),)
    one = GitHubPullDiff(7, "x", "commit ppp", "p" * 40, "commit ccccccc", "c" * 40, only)
    monkeypatch.setattr(commit_review, "commit_diff", lambda *_a: one)
    answers = [1, 0]

    class _Choice:
        def __init__(self, *_a, **_k) -> None:
            self.labels = _a[3]

        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None:
            pass

        def SetName(self, _n) -> None:  # noqa: N802
            pass

        def GetSelection(self) -> int:  # noqa: N802
            return answers.pop(0)

    monkeypatch.setattr(wx, "SingleChoiceDialog", _Choice)
    monkeypatch.setattr(
        "quill.ui.github_pr_diff_comments.show_modal_dialog", lambda *_a, **_k: wx.ID_OK
    )
    diff_dialog._choose_commit()
    assert "only.py" in diff_dialog._files.GetString(0)
    assert "Commit ccccccc. 1 changed file." in diff_dialog.spoken
    assert "commit ccccccc into commit ppp" in diff_dialog._header.GetLabel()
    diff_dialog._choose_commit()
    assert diff_dialog._diff is diff_dialog._whole_diff
    assert diff_dialog._files.GetCount() == 2


def test_the_timeline_hides_the_comment_on_the_cursors_line(wx_app, monkeypatch) -> None:
    from quill.core.github.timeline import TimelineEntry, TimelineResult

    monkeypatch.setattr("quill.ui.github_timeline_dialog.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.core.github.comment_moderation.hide_comment",
        lambda _api, node, why: (sent.append((node, why)), "Hid it.")[1],
    )
    frame = wx.Frame(None)
    spoken: list[str] = []
    dialog = GitHubTimelineDialog(frame, object(), "owner/repo", 7, announce_cb=spoken.append)
    try:
        entries = (
            TimelineEntry("2026-11-01", "ann", "added the label bug"),
            TimelineEntry("2026-11-02", "bo", "commented: buy now", "IC_2"),
        )
        dialog._ready(TimelineResult(entries))
        assert dialog._hide_btn.IsEnabled()
        dialog._text.SetInsertionPoint(0)
        dialog._hide_or_show()
        assert spoken[-1].startswith("Put the cursor on a line that says commented")

        class _Choice:
            def __init__(self, *_a, **_k) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_a) -> None:
                pass

            def SetName(self, _n) -> None:  # noqa: N802
                pass

            def GetSelection(self) -> int:  # noqa: N802
                return 0

        monkeypatch.setattr(wx, "SingleChoiceDialog", _Choice)
        monkeypatch.setattr(
            "quill.ui.github_timeline_dialog.show_modal_dialog", lambda *_a, **_k: wx.ID_OK
        )
        dialog._text.SetInsertionPoint(dialog._text.XYToPosition(0, 1))
        dialog._hide_or_show()
        assert sent == [("IC_2", "SPAM")] and spoken[-1] == "Hid it."
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()
