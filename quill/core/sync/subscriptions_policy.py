"""What another device may change here, and what stays here (ear.md 6.9, 6.10).

Split from :mod:`quill.core.sync.subscriptions_sync` (GATE-11), which applies it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["SubscriptionPolicy"]


@dataclass(frozen=True, slots=True)
class SubscriptionPolicy:
    """What the listener lets another device change here (ear.md 6.9).

    The defaults are the behaviour before these settings existed, so nobody's
    sync changes until they choose otherwise. Each "not here" choice is said
    once per podcast, never on every sync.
    """

    #: "follow": a podcast followed on another device is followed here too.
    #: "suggest": it is named once, and the listener decides.
    follow_new: str = "follow"
    #: "remove": unfollowing on another device unfollows here (the
    #: subscription only; episodes, downloads and history stay).
    #: "keep": it is named once, and stays followed here.
    unfollows: str = "remove"
    #: Whether folders, and which folder a podcast is filed in, travel.
    folders: bool = True
    #: Whether a podcast's own playback speed travels (sync.md 6.7 prefs).
    speed: bool = True
    #: Whether a podcast first followed here after sharing began is shared.
    new_podcasts_share: bool = True
    #: ``sub:`` ids of podcasts kept on this device only (ear.md 6.10).
    local_only: frozenset[str] = frozenset()

    def keeps_local(self, show: Any) -> bool:
        """Whether *show* stays on this device: chosen, or private by nature."""
        from quill.core.sync.subscriptions_sync import is_private, subscription_id

        url = str(getattr(show, "feed_url", "") or "")
        return is_private(show) or (bool(url) and subscription_id(url) in self.local_only)
