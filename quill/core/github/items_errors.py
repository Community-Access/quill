"""Coded errors shared by the GitHub Items provider and small provider mixins."""

from __future__ import annotations

from quill.core.error_codes import CodedError


class GitHubItemsError(CodedError):
    """A GitHub item request failed or is unavailable in the current session."""

    code = "QUILL-GITHUB-ITEMS-ERROR"


__all__ = ["GitHubItemsError"]
