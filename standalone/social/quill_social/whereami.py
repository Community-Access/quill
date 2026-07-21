"""Where Am I context builder (PRD 10.3).

Where Am I answers, in one utterance, every question the PRD lists: workspace,
account, network, folder or timeline, item position, unread count, current
field, filter and sort state, post type, visibility, media state, moderation
state, scheduling state, and any pending operation or error.

This module is wx-free. The UI assembles a :class:`WhereAmI` from live state and
calls :meth:`WhereAmI.announce`; the string it returns is exactly what is
spoken and shown, so the logic is fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WhereAmI:
    workspace: str = ""
    account: str = ""
    network: str = ""
    feed: str = ""
    position: int = 0
    total: int = 0
    unread: int = 0
    current_field: str = ""
    field_value: str = ""
    filter_state: str = ""
    sort_state: str = ""
    post_type: str = ""
    visibility: str = ""
    media_state: str = ""
    moderation_state: str = ""
    scheduling_state: str = ""
    pending: str = ""
    error: str = ""
    extra: list[str] = field(default_factory=list)

    def announce(self) -> str:
        """Compose the full Where Am I utterance, omitting empty parts."""
        parts: list[str] = []
        if self.workspace:
            parts.append(f"Workspace {self.workspace}")
        if self.account:
            net = f" on {self.network.capitalize()}" if self.network else ""
            parts.append(f"Account {self.account}{net}")
        elif self.network:
            parts.append(self.network.capitalize())
        if self.feed:
            parts.append(self.feed)
        if self.total:
            parts.append(f"item {self.position} of {self.total}")
        elif self.position:
            parts.append(f"item {self.position}")
        if self.unread:
            parts.append(f"{self.unread} unread")
        if self.filter_state:
            parts.append(f"filter {self.filter_state}")
        if self.sort_state:
            parts.append(f"sorted by {self.sort_state}")
        if self.post_type:
            parts.append(self.post_type)
        if self.visibility:
            parts.append(f"visibility {self.visibility}")
        if self.media_state:
            parts.append(self.media_state)
        if self.moderation_state:
            parts.append(self.moderation_state)
        if self.scheduling_state:
            parts.append(self.scheduling_state)
        if self.current_field:
            fv = f": {self.field_value}" if self.field_value else ""
            parts.append(f"field {self.current_field}{fv}")
        parts.extend(self.extra)
        if self.pending:
            parts.append(f"pending {self.pending}")
        if self.error:
            parts.append(f"error: {self.error}")
        if not parts:
            return "No context available"
        return ". ".join(parts) + "."
