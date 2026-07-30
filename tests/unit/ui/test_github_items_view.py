"""Unit tests for the wx-free GitHub items view-model formatting (#924).

Covers the GHManage-parity list mode (Quick/Full cell spelling), the per-view
detail text, the Alt+N/Alt+P comment-position map, and the combined issues+PRs
sort -- all without a display, since the formatting lives in
:mod:`quill.ui.github_items_view` precisely to be testable this way.
"""

from __future__ import annotations

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubReleaseAsset,
    GitHubTag,
    GitHubWorkflow,
    GitHubWorkflowRun,
)
from quill.ui.github_items_view import (
    RELEASE_ASSET_COLUMNS,
    VIEW_BRANCHES,
    VIEW_COLUMNS,
    VIEW_ISSUES,
    VIEW_RELEASES,
    VIEW_RUNS,
    VIEWS,
    item_detail,
    model_detail,
    model_label,
    model_url,
    parse_repo_reference,
    release_drill_status,
    row_cells,
    sort_items,
    view_label,
)


def _asset(name: str, downloads: int, size: int = 1024) -> GitHubReleaseAsset:
    return GitHubReleaseAsset(
        name=name,
        download_count=downloads,
        size_bytes=size,
        browser_download_url=f"https://example.com/{name}",
        updated_at="2026-02-01T00:00:00Z",
    )


def _item(number: int, *, title: str = "T", state: str = "open", is_pr: bool = False) -> GitHubItem:
    return GitHubItem(
        number=number,
        title=title,
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        is_pr=is_pr,
        author="alice",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        body="body text",
        labels=("bug", "ui"),
        assignees=("bob",),
        comments=3,
    )


def _pr(number: int) -> GitHubItem:
    return GitHubItem(
        number=number,
        title="PR",
        state="open",
        url=f"https://github.com/owner/repo/pull/{number}",
        is_pr=True,
        author="alice",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        body="pr body",
        labels=("enh",),
        assignees=(),
        comments=1,
        additions=10,
        deletions=2,
        changed_files=4,
        base_branch="main",
        head_branch="feature-x",
    )


# ---------------------------------------------------------------------------
# List mode (GHManage parity)
# ---------------------------------------------------------------------------


def test_quick_mode_emits_bare_cells() -> None:
    item = _item(208)
    cells = row_cells(item, VIEW_COLUMNS[VIEW_ISSUES], full=False)
    # Bare values, no "col: " prefix.
    assert cells == ["208", "ISSUE", "OPEN", "T", "alice", "2026-01-02", "bug, ui", "3"]


def test_full_mode_spells_col_value_for_screen_readers() -> None:
    # GHManage parity: Full mode prefixes "col: " so a screen reader reads a
    # self-describing line. Empty cells are kept bare (no "col:" noise).
    item = _item(208)
    cells = row_cells(item, VIEW_COLUMNS[VIEW_ISSUES], full=True)
    assert cells[0] == "number: 208"
    assert cells[1] == "type: ISSUE"
    assert cells[2] == "state: OPEN"
    assert cells[3] == "title: T"


def test_pr_row_uses_kind_and_state_display() -> None:
    pr = _pr(300)
    cells = row_cells(pr, VIEW_COLUMNS[VIEW_ISSUES], full=False)
    assert cells[1] == "PR"  # kind
    assert cells[2] == "OPEN"  # state_display (not merged)


def test_merged_pr_state_display_is_merged() -> None:
    pr = GitHubItem(
        number=9,
        title="x",
        state="closed",
        url="u",
        is_pr=True,
        is_merged=True,
    )
    assert pr.state_display == "MERGED"


def test_branch_row_cells() -> None:
    branch = GitHubBranch(
        name="main",
        commit_sha="abc1234567",
        commit_message="Fix",
        commit_author="Alice",
        commit_date="2026-01-03T00:00:00Z",
        protected=True,
        url="https://github.com/owner/repo/tree/main",
    )
    cells = row_cells(branch, VIEW_COLUMNS[VIEW_BRANCHES], full=False)
    assert cells == ["main", "protected", "Alice", "2026-01-03", "abc1234"]


def test_workflow_row_cells() -> None:
    workflow = GitHubWorkflow(id=1, name="CI", path=".github/workflows/ci.yml", state="active")
    cells = row_cells(workflow, VIEW_COLUMNS["workflows"], full=False)
    assert cells == ["CI", "active", ".github/workflows/ci.yml"]


def test_views_cover_all_seven() -> None:
    keys = {key for key, _ in VIEWS}
    assert keys == {
        VIEW_ISSUES,
        VIEW_BRANCHES,
        "commits",
        "tags",
        "releases",
        "workflows",
        VIEW_RUNS,
    }


def test_view_label_falls_back_to_key() -> None:
    assert view_label(VIEW_ISSUES) == "Issues & PRs"
    assert view_label("bogus") == "bogus"


# ---------------------------------------------------------------------------
# Detail text + comment positions (Alt+N/Alt+P)
# ---------------------------------------------------------------------------


def test_item_detail_without_comments_has_no_positions() -> None:
    text, positions = item_detail(_item(208), [])
    assert positions == []
    assert "#208 [ISSUE] T" in text
    assert "State: OPEN" in text
    assert "Labels: bug, ui" in text
    assert "Assignees: bob" in text


def test_item_detail_pr_includes_diff_and_branches() -> None:
    text, _ = item_detail(_pr(300), [])
    assert "Branches: feature-x -> main" in text
    assert "Changes: +10 -2 (4 files)" in text
    assert "[PR]" in text


def test_item_detail_records_comment_positions_for_navigation() -> None:
    comments = [
        {"author": "reviewer", "created_at": "2026-01-05T00:00:00Z", "body": "looks good"},
        {"author": "alice", "created_at": "2026-01-06T00:00:00Z", "body": "line one\nline two"},
    ]
    text, positions = item_detail(_item(208), comments)
    assert len(positions) == 2
    # Each position is (start_line, line_count); the second comment's body has
    # two lines so it spans the header + two body lines = 3 lines.
    assert positions[1][1] == 3
    assert "Comment 1 of 2" in text
    assert "Comment 2 of 2" in text


def test_model_detail_branch() -> None:
    branch = GitHubBranch(name="main", commit_sha="abc", commit_message="m", url="u")
    detail = model_detail(branch)
    assert "Branch: main" in detail
    assert "Commit: abc" in detail


def test_model_detail_commit_short_sha_not_used_in_detail() -> None:
    # The commit detail shows the FULL sha (not the short form used in the list).
    commit = GitHubCommit(sha="0123456789abcdef", short_sha="0123456", message="msg", url="u")
    detail = model_detail(commit)
    assert "Commit: 0123456789abcdef" in detail


def test_model_detail_release_body() -> None:
    release = GitHubRelease(tag="v2.0", name="R2", body="release notes go here", url="u")
    detail = model_detail(release)
    assert "release notes go here" in detail  # the body
    assert "Release: R2 (v2.0)" in detail


def test_release_row_shows_downloads_and_asset_count() -> None:
    release = GitHubRelease(
        tag="v2.0",
        name="R2",
        assets=(_asset("big.exe", 900), _asset("small.zip", 100)),
    )
    cells = row_cells(release, VIEW_COLUMNS[VIEW_RELEASES], full=False)
    columns = VIEW_COLUMNS[VIEW_RELEASES]
    assert cells[columns.index("downloads")] == "1000"
    assert cells[columns.index("assets")] == "2"


def test_asset_row_cells_render_downloads_and_size() -> None:
    asset = _asset("setup.exe", 1234, size=2 * 1024 * 1024)
    cells = row_cells(asset, RELEASE_ASSET_COLUMNS, full=False)
    assert cells[RELEASE_ASSET_COLUMNS.index("name")] == "setup.exe"
    assert cells[RELEASE_ASSET_COLUMNS.index("downloads")] == "1234"
    assert cells[RELEASE_ASSET_COLUMNS.index("size")] == "2.0 MB"


def test_release_detail_breaks_down_by_file_and_states_caveat() -> None:
    release = GitHubRelease(
        tag="v2.0",
        name="R2",
        body="notes",
        assets=(_asset("big.exe", 900), _asset("small.zip", 100)),
    )
    detail = model_detail(release)
    assert "Total downloads: 1000 across 2 assets" in detail
    # Per-file breakdown, most-downloaded first.
    assert detail.index("big.exe") < detail.index("small.zip")
    assert "900 downloads" in detail
    # Correctness caveat surfaced in UI text.
    assert "not" in detail and "unique people" in detail
    assert "notes" in detail


def test_release_detail_notes_no_assets_and_excludes_source_archives() -> None:
    release = GitHubRelease(tag="v1.0", name="R1")
    detail = model_detail(release)
    assert "no downloadable assets" in detail
    assert "Source code" in detail  # explains source archives are not assets


def test_asset_detail_and_url_point_at_browser_download_url() -> None:
    asset = _asset("setup.exe", 5)
    detail = model_detail(asset)
    assert "Asset: setup.exe" in detail
    assert "Downloads: 5" in detail
    assert model_url(asset) == "https://example.com/setup.exe"
    assert model_label(asset) == "asset setup.exe"


def test_release_drill_status_repeats_download_caveat() -> None:
    release = GitHubRelease(tag="v2.0", name="R2", assets=(_asset("a", 3),))
    status = release_drill_status(release)
    assert "v2.0" in status
    assert "3 total downloads" in status
    assert "Backspace" in status


def test_model_detail_workflow_run() -> None:
    run = GitHubWorkflowRun(
        name="CI", status="completed", conclusion="success", url="u", run_number=42
    )
    detail = model_detail(run)
    assert "Run: CI #42" in detail
    assert "Conclusion: success" in detail


def test_model_detail_workflow_definition() -> None:
    workflow = GitHubWorkflow(id=1, name="CI", path=".github/workflows/ci.yml", state="active")
    detail = model_detail(workflow)
    assert "Workflow: CI" in detail
    assert "State: active" in detail
    assert "Path: .github/workflows/ci.yml" in detail


def test_model_url_returns_empty_for_plain_object() -> None:
    assert model_url(object()) == ""
    assert model_url(GitHubTag(name="v1", commit_sha="s", url="https://x")) == "https://x"


def test_model_label_describes_each_kind() -> None:
    assert model_label(_item(5)) == "#5"
    assert model_label(GitHubBranch(name="main", commit_sha="abc", url="u")) == "branch main"
    assert (
        model_label(GitHubCommit(sha="0123456789abcdef", short_sha="0123456", message="m", url="u"))
        == "commit 0123456"
    )
    assert model_label(GitHubTag(name="v1", commit_sha="s", url="u")) == "tag v1"
    assert model_label(GitHubRelease(tag="v2", name="R", url="u")) == "release v2"
    assert model_label(GitHubWorkflow(id=1, name="CI", path="p", state="active")) == "workflow CI"
    assert model_label(GitHubWorkflowRun(name="CI", status="completed", url="u")) == "run CI"


# ---------------------------------------------------------------------------
# Combined issues+PRs sort
# ---------------------------------------------------------------------------


def test_sort_items_number_desc_merges_issues_and_prs() -> None:
    # The inbox is the merge of two PyGithub calls; sort_items is the single
    # place they get combined and ordered.
    combined: list[GitHubItem] = [_item(100), _pr(300), _item(200)]
    ordered = sort_items(combined, "number_desc")
    assert [i.number for i in ordered] == [300, 200, 100]


def test_sort_items_comments_desc() -> None:
    items = [
        GitHubItem(number=1, title="a", state="open", url="u1", is_pr=False, comments=1),
        GitHubItem(number=2, title="b", state="open", url="u2", is_pr=False, comments=9),
        GitHubItem(number=3, title="c", state="open", url="u3", is_pr=False, comments=5),
    ]
    ordered = sort_items(items, "comments_desc")
    assert [i.number for i in ordered] == [2, 3, 1]


def test_sort_items_never_raises_on_mixed_state() -> None:
    # Defensive: a sort failure must fall back to the incoming order.
    items = [_item(1), _item(2)]
    assert sort_items(items, "unknown_order") == items


# ---------------------------------------------------------------------------
# parse_repo_reference (Ctrl+Shift+O: open a repo by pasted URL, GHManage parity)
# ---------------------------------------------------------------------------


def test_parse_repo_reference_plain_owner_repo() -> None:
    assert parse_repo_reference("Community-Access/quill") == "Community-Access/quill"


def test_parse_repo_reference_https_url() -> None:
    assert parse_repo_reference("https://github.com/owner/repo") == "owner/repo"


def test_parse_repo_reference_https_url_with_git_suffix_and_path() -> None:
    assert parse_repo_reference("https://github.com/owner/repo.git") == "owner/repo"
    assert parse_repo_reference("https://github.com/owner/repo/pull/42") == "owner/repo"
    assert parse_repo_reference("http://github.com/owner/repo/tree/main") == "owner/repo"


def test_parse_repo_reference_ssh_remote() -> None:
    assert parse_repo_reference("git@github.com:owner/repo.git") == "owner/repo"


def test_parse_repo_reference_bare_hostname() -> None:
    assert parse_repo_reference("github.com/owner/repo") == "owner/repo"


def test_parse_repo_reference_rejects_incomplete_input() -> None:
    assert parse_repo_reference("") is None
    assert parse_repo_reference("   ") is None
    assert parse_repo_reference("just-a-name") is None
    assert parse_repo_reference("https://github.com/owner") is None
