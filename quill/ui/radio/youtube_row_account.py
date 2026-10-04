"""The account-aware YouTube row verbs: subscribe for real, About, Live Chat, the video window.

Wired from :mod:`quill.ui.radio.browse_youtube_menu`'s handler table.

**Subscribe on YouTube...** subscribes for real when Quill Radio may sign in
to YouTube and an account is connected: it asks YouTube whether the account
already subscribes, then subscribes -- or, if it already does, asks whether to
unsubscribe (No is the default). The first time, the plain-language
permission request comes first. Everywhere else -- no sign-in in this copy, or
no account connected -- it keeps opening YouTube's own subscribe-confirm page
in the browser, exactly as before.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _row_name(dialog: Any, node: Any) -> str:
    try:
        return str(dialog._tree.GetItemText(node)).split("  (")[0].strip()
    except Exception:  # noqa: BLE001 - a vanished row still has a channel
        return "that channel"


def subscribe(dialog: Any, node: Any, args: list[str], fallback: Callable[[], None]) -> None:
    """Subscribe or unsubscribe through the API; *fallback* is the confirm page."""
    from quill.core.radio import youtube_oauth
    from quill.ui.radio.youtube_account_ui import can_sign_in

    if not (can_sign_in(dialog) and youtube_oauth.is_signed_in()):
        fallback()
        return
    from quill.core.radio import youtube_account_api as api
    from quill.core.radio.youtube_oauth import YouTubeOAuthError
    from quill.ui.radio.youtube_account_ui import confirm, run_write

    urls = [url for url in args if url]
    name = _row_name(dialog, node)

    def _look(token: str) -> object:
        channel_id = ""
        for url in urls:
            channel_id = api.channel_id_for(token, url)
            if channel_id:
                break
        if not channel_id:
            raise YouTubeOAuthError("YouTube could not find that channel.")
        return channel_id, api.find_subscription(token, channel_id)

    def _found(result: object) -> None:
        channel_id, subscription = result if isinstance(result, tuple) else ("", "")
        if subscription:
            if confirm(
                dialog,
                "Unsubscribe on YouTube",
                f"You subscribe to {name} on YouTube. Unsubscribe?",
            ):
                run_write(
                    dialog,
                    "Unsubscribe on YouTube",
                    lambda token: api.unsubscribe(token, str(subscription)),
                    lambda _r: dialog._announce(f"Unsubscribed from {name}."),
                )
            return
        run_write(
            dialog,
            "Subscribe on YouTube",
            lambda token: api.subscribe(token, str(channel_id)),
            lambda _r: dialog._announce(f"Subscribed to {name}."),
        )

    run_write(dialog, "Subscribe on YouTube", _look, _found)


def about_channel(dialog: Any, node: Any, args: list[str]) -> None:
    """About This Channel...: its name, subscribers and description, in a reader."""
    from quill.core.radio.youtube_video_info import fetch_about

    url = next((u for u in args if u), "")
    if not url:
        dialog._announce("That channel's address could not be read.")
        return
    name = _row_name(dialog, node)
    dialog._announce(f"Fetching About for {name}...")

    def _work(**_kwargs: object) -> object:
        return fetch_about(url)

    def _ok(_op: str, text: object) -> None:
        from quill.ui.radio.youtube_video_window import show_text

        show_text(dialog, f"About {name}", str(text))

    def _bad(_op: str, error: BaseException) -> None:
        from quill.core.radio.youtube_requests import plain
        from quill.ui.radio.youtube_account_ui import record_problem

        reason = plain(error)
        # announce-punctuation: exempt -- each part is a whole sentence
        dialog._announce(f"About could not be fetched. {reason}")
        record_problem(f"About {name}", reason)

    dialog._task_manager.submit("radio-youtube-about", _work, on_success=_ok, on_failure=_bad)


def live_chat(dialog: Any, station: Any) -> None:
    from quill.ui.radio import youtube_live_chat_ui

    youtube_live_chat_ui.open_for_station(dialog, station)


def video_window(dialog: Any, station: Any) -> None:
    from quill.ui.radio import youtube_video_window

    youtube_video_window.open_for_station(dialog, station)


__all__ = ["about_channel", "live_chat", "subscribe", "video_window"]
