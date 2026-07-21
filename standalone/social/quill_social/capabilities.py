"""Per-account capability registry (PRD 6.3, 11.4).

The interface adapts to what each account and server actually supports rather
than assuming every network behaves the same (PRD 6.2). A ``Capabilities``
record answers questions like "can this account quote?", "what visibilities are
allowed?", "what is the character limit?" -- and the UI hides or explains any
action the account cannot perform (PRD 6.3, "unsupported commands should be
hidden or clearly explained").

Defaults are seeded per network from public, well-known behavior. Live adapters
refine them from server metadata (Mastodon ``/api/v1/instance``, Bluesky
describeServer / app limits). This module is wx-free and has no network I/O.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True)
class Capabilities:
    """What an account can do. Immutable; refine with :meth:`merge`."""

    network: str = "mock"
    char_limit: int = 500
    visibilities: tuple[str, ...] = ("public", "unlisted", "followers", "direct")
    supports_quote: bool = True
    supports_edit: bool = False
    supports_delete: bool = True
    supports_polls: bool = True
    supports_native_scheduling: bool = False
    supports_content_warnings: bool = True
    supports_thread_gates: bool = False
    supports_bookmarks: bool = True
    supports_lists: bool = True
    supports_custom_feeds: bool = False
    supports_search: bool = True
    supports_filters: bool = True
    supports_video: bool = True
    supports_direct_messages: bool = True
    max_media_attachments: int = 4
    max_alt_text: int = 1500
    max_poll_options: int = 4
    server_version: str = ""

    def merge(self, **overrides: Any) -> Capabilities:
        """Return a refined copy; used when server metadata sharpens a default."""
        clean = {k: v for k, v in overrides.items() if k in _FIELD_NAMES}
        return replace(self, **clean)

    def allows_visibility(self, visibility: str) -> bool:
        return visibility in self.visibilities

    def to_dict(self) -> dict:
        d = asdict(self)
        d["visibilities"] = list(self.visibilities)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Capabilities:
        clean = {k: v for k, v in d.items() if k in _FIELD_NAMES}
        if "visibilities" in clean and clean["visibilities"] is not None:
            clean["visibilities"] = tuple(clean["visibilities"])
        return cls(**clean)


_FIELD_NAMES = set(Capabilities().__dataclass_fields__.keys())  # noqa: SLF001


# Seed defaults per network. These are conservative, well-known baselines; a
# live adapter's capability probe (PRD 11.4) is expected to overwrite the
# specific fields it can confirm from the server.
_DEFAULTS: dict[str, Capabilities] = {
    "mastodon": Capabilities(
        network="mastodon",
        char_limit=500,
        visibilities=("public", "unlisted", "followers", "direct"),
        supports_quote=False,  # not universal across Mastodon servers/versions
        supports_edit=True,
        supports_polls=True,
        supports_native_scheduling=True,  # Mastodon has server-side scheduling
        supports_content_warnings=True,
        supports_thread_gates=False,
        supports_bookmarks=True,
        supports_lists=True,
        supports_custom_feeds=False,
        supports_video=True,
        supports_direct_messages=True,
        max_media_attachments=4,
        max_alt_text=1500,
        max_poll_options=4,
    ),
    "bluesky": Capabilities(
        network="bluesky",
        char_limit=300,
        visibilities=("public",),  # Bluesky has no followers-only/DM-as-visibility
        supports_quote=True,
        supports_edit=False,
        supports_polls=False,  # no native polls
        supports_native_scheduling=False,  # needs the cloud/local scheduler
        supports_content_warnings=True,  # self-labels
        supports_thread_gates=True,
        supports_bookmarks=False,
        supports_lists=True,
        supports_custom_feeds=True,
        supports_video=True,
        supports_direct_messages=True,
        max_media_attachments=4,
        max_alt_text=2000,
        max_poll_options=0,
    ),
    "github": Capabilities(
        network="github",
        char_limit=65536,
        visibilities=("public",),
        supports_quote=False,
        supports_edit=True,
        supports_polls=False,
        supports_native_scheduling=False,
        supports_content_warnings=False,
        supports_thread_gates=False,
        supports_bookmarks=False,
        supports_lists=False,
        supports_custom_feeds=False,
        supports_video=False,
        supports_direct_messages=False,
        max_media_attachments=0,
        max_alt_text=0,
        max_poll_options=0,
    ),
    "mock": Capabilities(network="mock"),
}


def default_for(network: str) -> Capabilities:
    """Baseline capabilities for a network, before any live probe."""
    return _DEFAULTS.get(network, Capabilities(network=network))


class CapabilityRegistry:
    """Holds the effective capabilities for each connected account.

    Keyed by ``account_id``. The UI asks the registry, never the network name,
    so an old Mastodon server and a new one can differ even though both are
    "mastodon" (PRD 22, "must not assume every instance behaves like
    mastodon.social").
    """

    def __init__(self) -> None:
        self._by_account: dict[str, Capabilities] = {}

    def set(self, account_id: str, caps: Capabilities) -> None:
        self._by_account[account_id] = caps

    def seed_from_network(self, account_id: str, network: str) -> Capabilities:
        caps = default_for(network)
        self._by_account[account_id] = caps
        return caps

    def get(self, account_id: str, network: str = "mock") -> Capabilities:
        return self._by_account.get(account_id) or default_for(network)

    def refine(self, account_id: str, **overrides: Any) -> Capabilities:
        current = self._by_account.get(account_id) or Capabilities()
        refined = current.merge(**overrides)
        self._by_account[account_id] = refined
        return refined
