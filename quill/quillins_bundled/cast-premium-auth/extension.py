"""Cast Premium Auth -- a bundled sample ``podcast.feed.auth`` provider.

Demonstrates the podcast feed-auth capability for Quill Cast: it returns a
Bearer ``Authorization`` header for feeds on ``premium.example.com`` (declared in
``match_hosts``), read from this Quillin's own storage. It makes **no** network
call -- it returns a header string the host attaches to the feed request, which
is why it needs no ``net`` capability (least privilege).

The out-of-process worker discards a handler's return value, so the header is
handed back by writing it to storage under ``_RESULT_KEY`` (kept in lock-step
with ``quill.core.quillins.app_host.FEED_AUTH_RESULT_KEY``); the host reads it
from the shared storage dict after the call.
"""

from __future__ import annotations

# Must match quill.core.quillins.app_host.FEED_AUTH_RESULT_KEY.
_RESULT_KEY = "__quill_feed_auth_header__"


def feed_auth_header(api, event: dict) -> None:
    """Return a Bearer header for a matching premium feed request.

    ``event`` carries ``{"feed_url": ..., "url": ...}``. The token is read from
    this Quillin's storage (``api_token``); a real provider would let the user
    set it, and the sample falls back to a demo token so it works out of the box.
    """

    token = api.get_storage("api_token") or "demo-premium-token"
    api.set_storage(_RESULT_KEY, f"Bearer {token}")


def register(api) -> None:
    api.register_command("feed_auth_header", feed_auth_header)
    api.log("Cast Premium Auth loaded")
