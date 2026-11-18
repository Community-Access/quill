"""Hiding a comment, and showing it again (GitHub PRD 14.2: "Hide a comment").

GitHub lets anyone who can triage hide a comment for a reason -- spam, abuse,
off topic, outdated, a duplicate, or resolved -- so it folds away behind that
reason for everyone, without being deleted (``minimizeComment``), and show it
again (``unminimizeComment``).

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.workbench_api import GitHubApi

__all__ = ["REASONS", "hide_comment", "show_comment"]

#: The reason as offered, and GitHub's classifier for it.
REASONS: tuple[tuple[str, str], ...] = (
    ("Spam", "SPAM"),
    ("Abuse", "ABUSE"),
    ("Off topic", "OFF_TOPIC"),
    ("Outdated", "OUTDATED"),
    ("Duplicate", "DUPLICATE"),
    ("Resolved", "RESOLVED"),
)

_HIDE = """
mutation($id: ID!, $why: ReportedContentClassifiers!) {
  minimizeComment(input: {subjectId: $id, classifier: $why}) {
    minimizedComment { isMinimized minimizedReason }
  }
}
"""
_SHOW = """
mutation($id: ID!) {
  unminimizeComment(input: {subjectId: $id}) { unminimizedComment { isMinimized } }
}
"""


def hide_comment(api: GitHubApi, node_id: str, classifier: str) -> str:
    label = next((said for said, code in REASONS if code == classifier), classifier)
    api.graphql(_HIDE, {"id": node_id, "why": classifier})
    return f"Hid the comment as {label.casefold()}. It is folded away for everyone, not deleted."


def show_comment(api: GitHubApi, node_id: str) -> str:
    api.graphql(_SHOW, {"id": node_id})
    return "The comment shows again."
