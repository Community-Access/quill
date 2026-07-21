"""The common network-adapter contract (PRD 6.3, 29.1).

Every network (mock, Mastodon, Bluesky, later RSS/GitHub) implements
``NetworkAdapter``. The domain and UI depend only on this interface plus the
capability registry, so adding a network never means editing a timeline widget
or a composer -- it means writing an adapter (PRD 34, extensibility).

Errors are normalized to :class:`AdapterError` with an ``error_kind`` the
scheduler uses to decide retry vs. review (PRD 18.12): ``transient`` errors
back off and retry; ``validation``, ``permission``, and ``privacy`` errors stop
and ask the user.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from quill_social.capabilities import Capabilities
from quill_social.model import Media, SocialItem

ERROR_KINDS = ("transient", "validation", "permission", "privacy", "unknown")


class AdapterError(Exception):
    """A normalized network failure.

    ``kind`` drives the scheduler's recovery policy; ``retry_after_ms`` carries a
    server-suggested backoff when the network provides one (rate limiting).
    """

    def __init__(
        self,
        message: str,
        *,
        kind: str = "unknown",
        retry_after_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind if kind in ERROR_KINDS else "unknown"
        self.retry_after_ms = retry_after_ms

    @property
    def is_transient(self) -> bool:
        return self.kind == "transient"


@dataclass
class PublishRequest:
    """Everything one adapter needs to publish one post (PRD 15, 16.2)."""

    text: str = ""
    visibility: str = "public"
    content_warning: str = ""
    lang: str = ""
    in_reply_to: str = ""  # remote id of the parent, for thread publishing
    quote_of: str = ""
    media: list[Media] = field(default_factory=list)
    idempotency_key: str = ""  # dedupe a retried publish (PRD 40, partial threads)


@dataclass
class PublishResult:
    """The outcome of a successful publish."""

    remote_id: str
    uri: str = ""
    item: SocialItem | None = None


class NetworkAdapter(ABC):
    """The interface every network implements."""

    #: stable network id, one of quill_social.model.NETWORKS
    name: str = "base"

    @abstractmethod
    def capabilities(self) -> Capabilities:
        """What this account can do, refined from server metadata when live."""

    @abstractmethod
    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        """The account's home feed, newest first."""

    @abstractmethod
    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        """Items that mention or involve the account."""

    @abstractmethod
    def thread(self, item: SocialItem) -> list[SocialItem]:
        """The full conversation containing ``item``, in reading order."""

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish one post and return its remote identifier."""

    # Optional interactions default to "not supported" so a minimal adapter is
    # valid; the capability registry is the source of truth for whether the UI
    # offers each action.

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError("favourite not supported", kind="validation")

    def set_bookmark(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError("bookmark not supported", kind="validation")

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        raise AdapterError("repost not supported", kind="validation")

    def delete(self, remote_id: str) -> None:
        raise AdapterError("delete not supported", kind="validation")

    @classmethod
    def available(cls) -> bool:
        """Whether this adapter's dependencies are installed and usable."""
        return True
