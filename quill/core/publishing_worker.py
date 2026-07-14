"""Dispatch glue between publishing actions and the background task manager.

This is the only publishing module allowed to import
:mod:`quill.stability.task_manager`; ``quill.core.publishing`` itself stays
decoupled from the stability layer and only knows about a plain
``is_cancelled`` callable.

Deliberate boundary: this wraps the existing trusted in-process WordPress
client on a background thread with cooperative cancellation. It does not
add a real subprocess/IPC worker boundary (the kind ``quill.core.quillins``
uses for Quillins) — there is no untrusted publishing provider yet to
validate one against, since third-party provider loading remains locked
off. That boundary is deferred to the live third-party provider loading
phase, when a real provider exists to justify and test it against.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.publishing import PublishingConnectionProfile, browse_publishing_content
from quill.core.publishing_clients import PublishingRemoteItemSummary
from quill.core.publishing_providers import PublishingOperationCancelled
from quill.stability.task_manager import CancellationToken, CancelledError


def browse_publishing_content_task(
    *,
    cancellation_token: CancellationToken,
    operation_id: str,
    progress_callback: Callable[[Any], None],
    profile: PublishingConnectionProfile,
    secret: str,
    content_kinds: tuple[str, ...] | None = None,
    statuses: tuple[str, ...] | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, list[PublishingRemoteItemSummary]]:
    del operation_id, progress_callback
    try:
        return browse_publishing_content(
            profile,
            secret,
            content_kinds=content_kinds,
            statuses=statuses,
            timeout_seconds=timeout_seconds,
            is_cancelled=cancellation_token.is_cancelled,
        )
    except PublishingOperationCancelled as exc:
        raise CancelledError(str(exc)) from exc
