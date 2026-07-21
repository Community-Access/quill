"""Ordered thread publishing with pause-on-failure (PRD 16.2, 40).

Publishes a list of segments as a real reply chain: root first, then each
segment as a reply to the previous one. Every success is recorded. On the first
failure the run *pauses* -- it does not keep going and it does not republish
what already succeeded -- and returns a repair plan so the caller can retry,
edit and retry, skip, or stop (PRD 16.2). The user is always told exactly which
segments succeeded and which failed (PRD 16.2, "must be told exactly").

Idempotency: each segment carries a stable idempotency key derived from the run
id and the segment index, so a retried publish of the same segment does not
create a duplicate when a network confirmed the write but the response was lost
(PRD 40, partial-thread mitigation).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill_social.adapters.base import AdapterError, NetworkAdapter, PublishRequest

ProgressFn = Callable[[int, int, str], None]  # (index, total, published_remote_id)


@dataclass
class SegmentResult:
    index: int  # 1-based
    text: str
    ok: bool
    remote_id: str = ""
    error_kind: str = ""
    error_message: str = ""


@dataclass
class ThreadPublishResult:
    results: list[SegmentResult] = field(default_factory=list)
    total: int = 0
    parent_remote_id: str = ""  # remote id of the last successfully published segment
    failed_index: int | None = None  # 1-based index that failed, if any

    @property
    def ok(self) -> bool:
        return self.failed_index is None and len(self.results) == self.total

    @property
    def published_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    def summary(self) -> str:
        """A plain-language, screen-reader-friendly status line (PRD 16.2)."""
        if self.ok:
            return f"Published all {self.total} segments."
        done = self.published_count
        if done == 0:
            return f"Nothing published. Segment 1 of {self.total} failed."
        return (
            f"Published {done} of {self.total}. "
            f"Segment {self.failed_index} failed; the rest are paused and can be "
            f"retried without duplicating what already posted."
        )


def publish_thread(
    adapter: NetworkAdapter,
    segments: list[str],
    *,
    run_id: str,
    visibility: str = "public",
    content_warning: str = "",
    lang: str = "",
    reply_to: str = "",
    start_index: int = 1,
    parent_remote_id: str = "",
    on_progress: ProgressFn | None = None,
) -> ThreadPublishResult:
    """Publish ``segments`` in order as a reply chain.

    ``start_index`` and ``parent_remote_id`` let a repair run resume after a
    previous failure: pass the 1-based index to resume from and the remote id of
    the last good segment so the chain stays connected.
    """
    total = len(segments)
    result = ThreadPublishResult(total=total, parent_remote_id=parent_remote_id)
    parent = parent_remote_id or reply_to

    for i in range(start_index, total + 1):
        seg = segments[i - 1]
        # Only the very first segment carries the caller's CW/visibility as the
        # thread head; replies inherit the same visibility but no repeated CW.
        request = PublishRequest(
            text=seg,
            visibility=visibility,
            content_warning=content_warning if i == 1 else "",
            lang=lang,
            in_reply_to=parent,
            idempotency_key=f"{run_id}:{i}",
        )
        try:
            published = adapter.publish(request)
        except AdapterError as exc:
            result.results.append(
                SegmentResult(
                    index=i, text=seg, ok=False,
                    error_kind=exc.kind, error_message=str(exc),
                )
            )
            result.failed_index = i
            break
        parent = published.remote_id
        result.parent_remote_id = parent
        result.results.append(
            SegmentResult(index=i, text=seg, ok=True, remote_id=published.remote_id)
        )
        if on_progress:
            on_progress(i, total, published.remote_id)

    return result
