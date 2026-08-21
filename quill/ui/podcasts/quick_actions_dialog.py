"""Subscriptions > Quick Actions... -- Cast's call into the shared dialog.

The dialog itself is :mod:`quill.ui.media.quick_actions_dialog`, shared with
Quill Radio. What stays here is the one thing that is Cast's: which catalogue
and which labels it opens on. Kept as a module of its own rather than folded
into the caller so the existing import path and the dialog inventory entry are
unchanged.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.quick_actions import CONTEXT_LABELS, QuickActionOrders
from quill.ui.media.quick_actions_dialog import QuickActionsDialog as _SharedDialog


class QuickActionsDialog(_SharedDialog):
    """Returns the edited :class:`QuickActionOrders`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        orders: QuickActionOrders,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            orders=orders,
            context_labels=CONTEXT_LABELS,
            announce_cb=announce_cb,
        )
