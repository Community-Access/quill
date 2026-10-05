"""Asking Google for permission to act on YouTube, only when it is first needed.

Connect YouTube Account (:mod:`quill.core.radio.youtube_oauth`) asks for
``youtube.readonly`` and nothing else: listing what an account follows is all
it was for. Posting a comment, sending a chat message, subscribing, liking or
adding to a playlist each need one more permission, Google's
``youtube.force-ssl`` scope -- and most listeners will never use any of them.

So the extra permission is asked for **incrementally**: the first time somebody
uses one of those actions, Quill Radio explains in plain words what the
permission allows, and only then opens the browser on Google's consent page
for it. ``include_granted_scopes=true`` makes Google return a token carrying
both the old and the new permission, so reading keeps working exactly as
before. Nothing changes for anybody who never presses one of those buttons.

The token stays where every YouTube token stays -- the OS secret vault through
:func:`quill.core.radio.youtube_oauth.save_tokens` -- and which permissions it
carries is read from the bundle's own ``scope`` field, never stored anywhere
else.

wx-free, strict-typed. The only network calls are the ones
:mod:`quill.core.radio.youtube_oauth` already makes (the token exchange).
"""

from __future__ import annotations

import time
import urllib.parse
import webbrowser
from collections.abc import Callable

from quill.core.auth.token_bundle import TokenBundle
from quill.core.radio import youtube_oauth as oauth

#: Read *and* act: comment, chat, subscribe, rate, add to playlists.
WRITE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"

#: What the consent dialog says before the browser opens. Plain words, every
#: action named, and the verification caveat stated rather than hidden.
CONSENT_TITLE = "Allow Quill Radio to Act on YouTube"
CONSENT_TEXT = (
    "To do this, Quill Radio needs one more permission from Google: to act on "
    "YouTube for you.\n\n"
    "With it, Quill Radio can post and delete your comments and replies, send "
    "messages in a live chat, subscribe and unsubscribe, like or dislike "
    "videos, and add videos to your playlists or make new ones -- and only "
    "when you press the button for one of those. It never does any of them on "
    "its own, and it still cannot see your password.\n\n"
    'Google shows the permission as "See, edit, and permanently delete your '
    'YouTube videos, ratings, comments and captions", because that is how it '
    "names this one permission; Quill Radio uses only the actions above. "
    "Google may also warn that the app is not verified, or refuse, until "
    "Google has reviewed it.\n\n"
    "A browser window opens for you to approve. You can take the permission "
    "back any time by disconnecting your YouTube account. Continue?"
)


def has_write_scope(bundle: TokenBundle | None = None) -> bool:
    """Whether the stored session may act, not only read."""
    chosen = bundle if bundle is not None else oauth.load_tokens()
    return WRITE_SCOPE in chosen.scope.split()


def build_write_authorization(
    client_id: str, redirect_uri: str = oauth.DEFAULT_REDIRECT_URI
) -> oauth.AuthorizationRequest:
    """Google's consent URL for read *and* act, keeping what was granted.

    The same PKCE shape as :func:`quill.core.radio.youtube_oauth.build_authorization`,
    with both scopes and ``include_granted_scopes=true``.
    """
    import secrets as _secrets_module

    verifier, challenge = oauth._pkce_pair()
    state = _secrets_module.token_urlsafe(24)
    query = urllib.parse.urlencode({
        "client_id": client_id.strip(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": f"{oauth.SCOPE} {WRITE_SCOPE}",
        "include_granted_scopes": "true",
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    })
    return oauth.AuthorizationRequest(f"{oauth.AUTHORIZE_URL}?{query}", verifier, state)


def grant_write_access(
    *,
    safe_mode: bool = False,
    opener: oauth.Opener | None = None,
    browser_opener: Callable[[str], None] | None = None,
    callback_timeout: float = oauth._CALLBACK_TIMEOUT_SECONDS,
    wait_for_redirect: Callable[..., str] | None = None,
) -> None:
    """Run the browser consent for the extra permission and keep the result.

    Blocks until the listener answers in the browser, so callers run it off
    the UI thread. Raises :class:`~quill.core.radio.youtube_oauth.YouTubeOAuthError`
    when refused, timed out, or when Google's answer still lacks the scope
    (somebody unchecked it on the consent page).
    """
    oauth.refuse_in_safe_mode(safe_mode)
    client_id, client_secret = oauth.bundled_client()
    if not (client_id and client_secret):
        raise oauth.YouTubeOAuthError(
            "This build has no YouTube sign-in configured, so it cannot act on YouTube."
        )
    request = build_write_authorization(client_id)
    open_browser = browser_opener or webbrowser.open
    waiter = wait_for_redirect or oauth._wait_for_redirect

    def _on_ready() -> None:
        open_browser(request.url)

    code = waiter(
        request.state,
        oauth.DEFAULT_REDIRECT_URI,
        timeout=callback_timeout,
        on_ready=_on_ready,
    )
    response = oauth.exchange_code(
        code, request.code_verifier, client_id, client_secret, opener=opener
    )
    bundle = TokenBundle.from_token_response(response, now=time.time())
    if WRITE_SCOPE not in bundle.scope.split():
        oauth.save_tokens(bundle)  # reading still works with what was granted
        raise oauth.YouTubeOAuthError(
            "Google did not give Quill Radio permission to act on YouTube, so nothing was changed."
        )
    oauth.save_tokens(bundle)


def write_token(*, opener: oauth.Opener | None = None) -> str | None:
    """A current access token that may act, or ``None`` when it may not."""
    if not has_write_scope():
        return None
    return oauth.get_access_token(opener=opener)


__all__ = [
    "CONSENT_TEXT",
    "CONSENT_TITLE",
    "WRITE_SCOPE",
    "build_write_authorization",
    "grant_write_access",
    "has_write_scope",
    "write_token",
]
