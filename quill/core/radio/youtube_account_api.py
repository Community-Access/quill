"""Acting on YouTube for the listener: comments, chat, subscriptions, ratings, playlists.

Everything here goes through the official YouTube Data API v3 with the
listener's own token, and only after they granted the extra permission in
:mod:`quill.core.radio.youtube_write_scope`. One request helper,
:func:`call`, is the reviewed egress site; every action is a small function
over it that builds the documented request body, so each body is unit-tested
against a fake opener and nothing in the test suite reaches the network.

**The daily limit.** Every Google Cloud project gets a fixed number of API
"units" a day, shared by everybody using that app; a write costs 50. When it
runs out Google answers ``403 quotaExceeded``, and :class:`QuotaExceeded`
carries exactly one plain sentence for it. Nothing here ever retries -- a
retry loop against a spent quota only spends the listener's patience.

**What YouTube does not allow.** Watch Later cannot be read or added to
through the API (Google closed that in 2016: ``playlistItems.insert`` on
``WL`` fails), so Add to Watch Later is not offered as an API action. A
dislike is accepted and counted, though YouTube no longer shows the number.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from quill.core import http_client
from quill.core.radio.youtube_oauth import (
    _TIMEOUT_SECONDS,
    Opener,
    YouTubeOAuthError,
    _context_for,
)

API_ROOT = "https://www.googleapis.com/youtube/v3"

#: The one sentence for a spent daily quota.
QUOTA_SENTENCE = "YouTube's daily limit for QUILL has been reached; try again tomorrow."

LIKE = "like"
DISLIKE = "dislike"
NO_RATING = "none"

#: The longest comment or chat message YouTube accepts.
MAX_COMMENT_CHARS = 10_000
MAX_CHAT_CHARS = 200


class QuotaExceeded(YouTubeOAuthError):
    """Google's daily request allowance for this app is spent."""

    code = "QUILL-RADIO-YTOAUTH-QUOTA"


@dataclass(frozen=True, slots=True)
class PostedComment:
    comment_id: str
    text: str


def plain(error: BaseException) -> str:
    """The sentence an error carries, without its ``[QUILL-...]`` code."""
    if isinstance(error, YouTubeOAuthError) and error.args:
        return str(error.args[0])
    return str(error)


def _reason(payload: object) -> tuple[str, str]:
    """``(first error reason, message)`` from a Google error body."""
    if not isinstance(payload, dict):
        return "", ""
    error = payload.get("error")
    if not isinstance(error, dict):
        return "", ""
    message = str(error.get("message", ""))
    errors = error.get("errors")
    if isinstance(errors, list) and errors and isinstance(errors[0], dict):
        return str(errors[0].get("reason", "")), message
    return "", message


def _explain(status: int, reason: str, message: str) -> str:
    if reason in ("quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"):
        return QUOTA_SENTENCE
    if status == 401:
        return "Your YouTube sign-in has expired. Connect your YouTube account again."
    if reason in ("insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"):
        return "Quill Radio does not have permission to do that on YouTube yet."
    if reason == "commentsDisabled":
        return "Comments are turned off for this video."
    if reason in ("liveChatEnded", "liveChatNotFound", "liveChatDisabled"):
        return "This video's live chat is closed."
    if reason == "forbidden" and "chat" in message.lower():
        return "YouTube will not let this account post in that chat."
    if reason == "subscriptionDuplicate":
        return "You are already subscribed to that channel."
    if reason == "subscriptionForbidden":
        return "YouTube will not let you subscribe to that channel."
    if reason in ("videoNotFound", "commentNotFound", "playlistNotFound", "channelNotFound"):
        return "YouTube says that is not there any more."
    if reason == "playlistContainsMaximumNumberOfVideos":
        return "That playlist is full."
    plain_message = re.sub(r"<[^>]+>", "", message).strip()
    return plain_message or f"YouTube refused the request (error {status})."


def call(
    method: str,
    path: str,
    access_token: str,
    params: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
    *,
    opener: Opener | None = None,
) -> dict[str, object]:
    """One authenticated YouTube Data API request -- the reviewed egress site.

    ``GET``/``POST``/``PUT``/``DELETE``; a JSON *body* when given. A 204 (what
    rate and delete answer) comes back as ``{}``. Raises :class:`QuotaExceeded`
    for a spent quota and :class:`YouTubeOAuthError` with a speakable sentence
    for anything else. Never retries.
    """
    query = urllib.parse.urlencode(params or {})
    url = f"{API_ROOT}/{path}" + (f"?{query}" if query else "")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": http_client.user_agent(),
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    elif method in ("POST", "PUT"):
        headers["Content-Length"] = "0"
        data = b""
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        if opener is not None:
            status, raw = opener(request)
        else:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS, context=_context_for(url)
            ) as resp:
                status, raw = int(resp.status or 200), resp.read()
    except urllib.error.HTTPError as error:
        status, raw = int(error.code), error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise YouTubeOAuthError(
            "YouTube could not be reached. Check your connection and try again."
        ) from error
    text = raw.decode("utf-8", errors="replace").strip() if raw else ""
    try:
        payload: object = json.loads(text) if text else {}
    except json.JSONDecodeError:
        payload = {}
    if status >= 400:
        reason, message = _reason(payload)
        sentence = _explain(status, reason, message)
        if sentence == QUOTA_SENTENCE:
            raise QuotaExceeded(sentence)
        raise YouTubeOAuthError(sentence)
    return payload if isinstance(payload, dict) else {}


def _items(payload: dict[str, object]) -> list[dict[str, object]]:
    items = payload.get("items")
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def _clean(text: str, limit: int) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise YouTubeOAuthError("There is nothing to send. Type something first.")
    if len(cleaned) > limit:
        raise YouTubeOAuthError(f"That is too long for YouTube, which allows {limit:,} characters.")
    return cleaned


# -- comments -------------------------------------------------------------------


def thread_of(comment_id: str) -> str:
    """The top-level comment a reply belongs to (pure).

    A reply's id is ``<thread id>.<reply id>``; YouTube threads one level
    deep, so answering a reply means answering its thread.
    """
    return comment_id.split(".", 1)[0]


def add_comment(
    access_token: str, video_id: str, text: str, *, opener: Opener | None = None
) -> PostedComment:
    """commentThreads.insert: a new top-level comment on *video_id*."""
    body: dict[str, object] = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": _clean(text, MAX_COMMENT_CHARS)}},
        }
    }
    payload = call("POST", "commentThreads", access_token, {"part": "snippet"}, body, opener=opener)
    snippet = payload.get("snippet")
    top = snippet.get("topLevelComment") if isinstance(snippet, dict) else None
    new_id = str(top.get("id", "")) if isinstance(top, dict) else ""
    return PostedComment(new_id or str(payload.get("id", "")), text.strip())


def reply(
    access_token: str, comment_id: str, text: str, *, opener: Opener | None = None
) -> PostedComment:
    """comments.insert: a reply in *comment_id*'s thread."""
    body: dict[str, object] = {
        "snippet": {
            "parentId": thread_of(comment_id),
            "textOriginal": _clean(text, MAX_COMMENT_CHARS),
        }
    }
    payload = call("POST", "comments", access_token, {"part": "snippet"}, body, opener=opener)
    return PostedComment(str(payload.get("id", "")), text.strip())


def delete_comment(access_token: str, comment_id: str, *, opener: Opener | None = None) -> None:
    """comments.delete. YouTube itself refuses anybody else's comment."""
    call("DELETE", "comments", access_token, {"id": comment_id}, opener=opener)


def my_channel_id(access_token: str, *, opener: Opener | None = None) -> str:
    """The signed-in account's own channel id, or ``""``."""
    payload = call("GET", "channels", access_token, {"part": "id", "mine": "true"}, opener=opener)
    items = _items(payload)
    return str(items[0].get("id", "")) if items else ""


def comment_author_channel(
    access_token: str, comment_id: str, *, opener: Opener | None = None
) -> str:
    """Who wrote *comment_id* (their channel id), or ``""`` if YouTube will not say."""
    payload = call(
        "GET",
        "comments",
        access_token,
        {"part": "snippet", "id": comment_id, "textFormat": "plainText"},
        opener=opener,
    )
    items = _items(payload)
    snippet = items[0].get("snippet") if items else None
    author = snippet.get("authorChannelId") if isinstance(snippet, dict) else None
    return str(author.get("value", "")) if isinstance(author, dict) else ""


def is_mine(access_token: str, comment_id: str, *, opener: Opener | None = None) -> bool:
    """Whether the signed-in account wrote *comment_id*."""
    mine = my_channel_id(access_token, opener=opener)
    return bool(mine) and comment_author_channel(access_token, comment_id, opener=opener) == mine


# -- live chat ------------------------------------------------------------------


def live_chat_id(access_token: str, video_id: str, *, opener: Opener | None = None) -> str:
    """videos.list liveStreamingDetails.activeLiveChatId, or ``""`` when closed."""
    payload = call(
        "GET",
        "videos",
        access_token,
        {"part": "liveStreamingDetails", "id": video_id},
        opener=opener,
    )
    items = _items(payload)
    details = items[0].get("liveStreamingDetails") if items else None
    return str(details.get("activeLiveChatId", "")) if isinstance(details, dict) else ""


def send_chat_message(
    access_token: str, chat_id: str, text: str, *, opener: Opener | None = None
) -> str:
    """liveChatMessages.insert: a plain text message; returns its id."""
    body: dict[str, object] = {
        "snippet": {
            "liveChatId": chat_id,
            "type": "textMessageEvent",
            "textMessageDetails": {"messageText": _clean(text, MAX_CHAT_CHARS)},
        }
    }
    payload = call(
        "POST", "liveChat/messages", access_token, {"part": "snippet"}, body, opener=opener
    )
    return str(payload.get("id", ""))


# -- subscriptions --------------------------------------------------------------

_CHANNEL_ID = re.compile(r"/channel/(UC[\w-]{22})")
_HANDLE = re.compile(r"/(@[\w.\-]+)")


def channel_id_for(access_token: str, url: str, *, opener: Opener | None = None) -> str:
    """The ``UC...`` id behind a channel address, asking YouTube for a handle."""
    match = _CHANNEL_ID.search(url)
    if match:
        return match.group(1)
    handle = _HANDLE.search(url)
    if not handle:
        return ""
    payload = call(
        "GET", "channels", access_token, {"part": "id", "forHandle": handle.group(1)}, opener=opener
    )
    items = _items(payload)
    return str(items[0].get("id", "")) if items else ""


def find_subscription(access_token: str, channel_id: str, *, opener: Opener | None = None) -> str:
    """The subscription id if the account subscribes to *channel_id*, else ``""``."""
    payload = call(
        "GET",
        "subscriptions",
        access_token,
        {"part": "id", "mine": "true", "forChannelId": channel_id},
        opener=opener,
    )
    items = _items(payload)
    return str(items[0].get("id", "")) if items else ""


def subscribe(access_token: str, channel_id: str, *, opener: Opener | None = None) -> str:
    """subscriptions.insert; returns the new subscription's id."""
    body: dict[str, object] = {
        "snippet": {"resourceId": {"kind": "youtube#channel", "channelId": channel_id}}
    }
    payload = call("POST", "subscriptions", access_token, {"part": "snippet"}, body, opener=opener)
    return str(payload.get("id", ""))


def unsubscribe(access_token: str, subscription_id: str, *, opener: Opener | None = None) -> None:
    """subscriptions.delete."""
    call("DELETE", "subscriptions", access_token, {"id": subscription_id}, opener=opener)


# -- ratings and playlists ------------------------------------------------------


def get_rating(access_token: str, video_id: str, *, opener: Opener | None = None) -> str:
    """videos.getRating: ``like``, ``dislike`` or ``none``."""
    payload = call("GET", "videos/getRating", access_token, {"id": video_id}, opener=opener)
    items = _items(payload)
    return str(items[0].get("rating", NO_RATING)) if items else NO_RATING


def rate(access_token: str, video_id: str, rating: str, *, opener: Opener | None = None) -> None:
    """videos.rate with ``like``, ``dislike`` or ``none`` (remove the rating)."""
    if rating not in (LIKE, DISLIKE, NO_RATING):
        raise ValueError(rating)
    call("POST", "videos/rate", access_token, {"id": video_id, "rating": rating}, opener=opener)


def add_to_playlist(
    access_token: str, playlist_id: str, video_id: str, *, opener: Opener | None = None
) -> str:
    """playlistItems.insert at the end of *playlist_id*; returns the item id."""
    body: dict[str, object] = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    payload = call("POST", "playlistItems", access_token, {"part": "snippet"}, body, opener=opener)
    return str(payload.get("id", ""))


#: The privacy a new playlist may have, as the chooser reads them.
PRIVACY_CHOICES: tuple[tuple[str, str], ...] = (
    ("private", "Private: only you"),
    ("unlisted", "Unlisted: anyone with the link"),
    ("public", "Public: anyone"),
)


def create_playlist(
    access_token: str,
    title: str,
    *,
    privacy: str = "private",
    opener: Opener | None = None,
) -> str:
    """playlists.insert; returns the new playlist's id."""
    if privacy not in dict(PRIVACY_CHOICES):
        privacy = "private"
    body: dict[str, object] = {
        "snippet": {"title": _clean(title, 150)},
        "status": {"privacyStatus": privacy},
    }
    payload = call(
        "POST", "playlists", access_token, {"part": "snippet,status"}, body, opener=opener
    )
    return str(payload.get("id", ""))


def my_playlists(access_token: str, *, opener: Opener | None = None) -> list[tuple[str, str]]:
    """``(playlist id, title)`` for every playlist the account owns, A to Z."""
    found: list[tuple[str, str]] = []
    page = ""
    for _ in range(20):  # 1000 playlists is more than anybody has
        params = {"part": "snippet", "mine": "true", "maxResults": "50"}
        if page:
            params["pageToken"] = page
        payload = call("GET", "playlists", access_token, params, opener=opener)
        for item in _items(payload):
            snippet = item.get("snippet")
            title = str(snippet.get("title", "")) if isinstance(snippet, dict) else ""
            if item.get("id"):
                found.append((str(item["id"]), title or "Untitled playlist"))
        page = str(payload.get("nextPageToken", "") or "")
        if not page:
            break
    return sorted(found, key=lambda pair: pair[1].casefold())


__all__ = [
    "DISLIKE",
    "LIKE",
    "NO_RATING",
    "PRIVACY_CHOICES",
    "QUOTA_SENTENCE",
    "PostedComment",
    "QuotaExceeded",
    "add_comment",
    "add_to_playlist",
    "call",
    "channel_id_for",
    "comment_author_channel",
    "create_playlist",
    "delete_comment",
    "find_subscription",
    "get_rating",
    "is_mine",
    "live_chat_id",
    "my_channel_id",
    "my_playlists",
    "plain",
    "rate",
    "reply",
    "send_chat_message",
    "subscribe",
    "thread_of",
    "unsubscribe",
]
