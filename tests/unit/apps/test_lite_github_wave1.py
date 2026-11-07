"""QUILL Lite reaches every Wave 1 GitHub feature through the shared surfaces.

Lite opens the same ``GitHubItemsDialog`` QUILL does (test_lite_github_workbench.py
pins that), so a Wave 1 feature is in Lite exactly when it lives on a shared
surface. This pins that the features stayed there rather than drifting into a
QUILL-only module.
"""

from __future__ import annotations

from quill.core.github.items_provider import GitHubItemsProvider
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog
from quill.ui.github_workflow_jobs_dialog import WorkflowJobsDialog


def test_wave1_actions_live_on_the_shared_dialogs() -> None:
    for name in (
        "_triage_notification",
        "_mark_all_read",
        "_activate_notification",
    ):
        assert callable(getattr(GitHubExploreDialog, name))
    for name in (
        "_show_failure_digest",
        "_rerun_failed_jobs",
        "_cancel_selected_run",
        "_delete_selected_run",
        "_approve_fork_run",
        "_review_pending_deployments",
        "_show_combined_status",
    ):
        assert callable(getattr(GitHubItemsDialog, name))
    for name in ("_show_digest", "_rerequest_check"):
        assert callable(getattr(WorkflowJobsDialog, name))
    for name in ("_enable_auto_merge", "_enqueue", "_combined_status"):
        assert callable(getattr(GitHubPullReviewDialog, name))


def test_wave1_provider_operations_are_on_the_shared_provider() -> None:
    for name in (
        "fetch_notification_inbox",
        "mark_notification_done",
        "unsubscribe_notification",
        "mark_all_notifications_read",
        "rerun_failed_jobs",
        "cancel_workflow_run",
        "delete_workflow_run",
        "rerequest_check_run",
        "fetch_pending_deployments",
        "review_pending_deployments",
        "approve_fork_run",
        "fetch_combined_check_status",
    ):
        assert callable(getattr(GitHubItemsProvider, name))
