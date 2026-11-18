"""Your GitHub status: a short message, an emoji, and "busy" (GitHub PRD 14.2).

The status is what GitHub shows beside your name: "On holiday until Monday",
with an emoji and, when you choose, "Busy", which tells people asking for
your review that you may answer slowly. :func:`read_status` reads it
(``viewer.status``); :func:`set_status` changes it with ``changeUserStatus``,
optionally clearing itself after a while; :func:`clear_status` empties it.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from quill.core.github.workbench_api import GitHubApi

__all__ = ["CLEAR_AFTER", "UserStatus", "clear_status", "read_status", "set_status"]

_READ = "query { viewer { status { message emoji indicatesLimitedAvailability expiresAt } } }"
_CHANGE = """
mutation($message: String, $emoji: String, $busy: Boolean, $expires: DateTime) {
  changeUserStatus(input: {message: $message, emoji: $emoji,
                           limitedAvailability: $busy, expiresAt: $expires}) {
    status { message }
  }
}
"""

#: When a status clears itself: the words offered, and how long after now.
CLEAR_AFTER: tuple[tuple[str, timedelta | None], ...] = (
    ("Never", None),
    ("In 30 minutes", timedelta(minutes=30)),
    ("In 1 hour", timedelta(hours=1)),
    ("In 4 hours", timedelta(hours=4)),
    ("Tomorrow", timedelta(days=1)),
    ("In a week", timedelta(days=7)),
)


@dataclass(frozen=True)
class UserStatus:
    message: str = ""
    emoji: str = ""
    busy: bool = False
    expires: str = ""

    @property
    def sentence(self) -> str:
        if not (self.message or self.emoji or self.busy):
            return "You have no status set."
        from quill.core.github.emoji_names import name_shortcodes

        parts = [f"Your status: {name_shortcodes(self.message) or 'no message'}"]
        if self.emoji:
            parts.append(f"with {name_shortcodes(self.emoji)}")
        if self.busy:
            parts.append("and marked busy")
        said = " ".join(parts) + "."
        if self.expires:
            said += f" It clears at {self.expires[:16].replace('T', ' ')} UTC."
        return said


def read_status(api: GitHubApi) -> UserStatus:
    data = api.graphql(_READ, {})
    raw = ((data or {}).get("viewer") or {}).get("status")
    if not isinstance(raw, Mapping):
        return UserStatus()
    return UserStatus(
        message=str(raw.get("message") or ""),
        emoji=str(raw.get("emoji") or ""),
        busy=bool(raw.get("indicatesLimitedAvailability")),
        expires=str(raw.get("expiresAt") or ""),
    )


def set_status(
    api: GitHubApi,
    message: str,
    *,
    emoji: str = "",
    busy: bool = False,
    clear_after: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    """Set the status; returns the sentence to say."""
    expires = ""
    if clear_after is not None:
        moment = (now or datetime.now(UTC)) + clear_after
        expires = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    shortcode = emoji.strip()
    if shortcode and not shortcode.startswith(":"):
        shortcode = f":{shortcode.strip(':')}:"
    api.graphql(
        _CHANGE,
        {
            "message": message,
            "emoji": shortcode or None,
            "busy": bool(busy),
            "expires": expires or None,
        },
    )
    return UserStatus(message, shortcode, busy, expires).sentence.replace(
        "Your status:", "Your status is now:", 1
    )


def clear_status(api: GitHubApi) -> str:
    api.graphql(_CHANGE, {"message": None, "emoji": None, "busy": False, "expires": None})
    return "Your status is cleared."
