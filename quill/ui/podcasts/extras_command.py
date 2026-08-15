"""**About This Episode** -- opening the window, and doing what its rows say.

Plain functions taking the Podcast Manager (or the standalone app frame) as
``host``, the house pattern for extracted UI helpers. Kept out of the manager
itself because the three actions a row can take -- open a link, play a stream,
subscribe to a feed -- each touch a different part of the app, and none of them
is about managing a podcast library.

The rules that shape this:

* **The summary is spoken before the window opens.** Most of the time the answer
  to "did this podcast publish anything extra?" is the whole question, and
  hearing it costs one keystroke instead of a window and a Close.
* **Subscribing from a podroll is a real subscribe**, through the same code path
  Add by Feed URL uses -- so the show arrives with its real name, its artwork and
  its episodes rather than as a bare address in a list.
* **Nothing here spends money and nothing here reports anything.** A funding link
  opens in the browser and QUILL takes no further part; a podroll entry is
  fetched only when somebody chooses to subscribe.
"""

from __future__ import annotations

from typing import Any


def episode_extras(host: Any, show: Any, episode: Any) -> Any:
    """Build the extras for one episode of one show."""
    from quill.core.podcasts import extras as extras_module

    return extras_module.build(
        show_tags=getattr(show, "tags", None),
        episode_tags=getattr(episode, "tags", None),
        show_title=str(getattr(show, "title", "")),
    )


def has_extras(show: Any, episode: Any) -> bool:
    """Whether the menu item is worth appending for this episode."""
    from quill.core.podcasts.extras import has_extras as _has

    return _has(getattr(show, "tags", None), getattr(episode, "tags", None))


def open_episode_extras(host: Any, show: Any, episode: Any) -> None:
    """Say what there is, then show it."""
    from quill.core.podcasts import extras as extras_module
    from quill.ui.podcasts.episode_extras_dialog import EpisodeExtrasDialog

    extras = episode_extras(host, show, episode)
    host._announce(extras_module.summary(extras))

    dialog = EpisodeExtrasDialog(
        getattr(host, "dialog", None) or getattr(host, "frame", None) or host,
        extras=extras,
        episode_title=str(getattr(episode, "title", "")),
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        announce=host._announce,
        open_url=lambda url: open_link(host, url),
        play_url=lambda url, label: play_stream(host, show, url, label),
        subscribe_feed=lambda url: subscribe_to(host, url),
    )
    dialog.show()


def open_for_playing_episode(host: Any) -> None:
    """About This Episode..., for whatever is playing.

    Nothing playing means there is no episode to be about, which is said rather
    than left as a command that appears to do nothing.
    """
    state = host._podcast_controller.state
    if not state.show_id or not state.episode_guid:
        host._announce("Nothing is playing, so there are no episode details to show.")
        return
    show = host._podcast_library.find_show(state.show_id)
    episode = show.find_episode(state.episode_guid) if show is not None else None
    if show is None or episode is None:
        host._announce("That episode is no longer in your library.")
        return
    open_episode_extras(host, show, episode)


def open_link(host: Any, url: str) -> bool:
    """Open a publisher's link in the browser. HTTPS or nothing.

    The scheme check is not ceremony: these addresses come from a feed, which is
    somebody else's input, and a ``file:`` or a custom scheme handed to the
    system opener is a way for a feed to run something.
    """
    import webbrowser

    address = str(url or "").strip()
    if not address.lower().startswith(("https://", "http://")):
        host._announce("That link could not be opened.")
        return False
    try:
        return bool(webbrowser.open(address))
    except Exception:  # noqa: BLE001 - a browser that will not start is not a crash
        return False


def play_stream(host: Any, show: Any, url: str, label: str) -> bool:
    """Play a live stream or an alternate version of the episode's audio.

    Through the ordinary podcast player, deliberately: a live item carried in a
    feed is still something to listen to, and giving it a second, separate
    transport would mean a different set of keys for pause and volume depending
    on where the audio came from.
    """
    controller = (
        getattr(host, "_controller", None)
        or getattr(host, "_podcast_controller", None)
        or getattr(host, "_player", None)
    )
    address = str(url or "").strip()
    if controller is None or not address:
        return False
    try:
        controller.play_episode(
            show_id=str(getattr(show, "id", "")),
            # A live stream has no episode of its own, and marking a resume
            # position in something with no end would be meaningless.
            episode_guid=f"live:{address}",
            title=label or "Live",
            source=address,
        )
    except Exception:  # noqa: BLE001 - reported by the caller, never raised at a listener
        return False
    return True


def subscribe_to(host: Any, feed_url: str) -> bool:
    """Subscribe to a feed a podcast recommended.

    Fetched on the task manager, never on the UI thread, and refused in Safe
    Mode the same way every other feed fetch is.
    """
    from quill.core.podcasts import feed_reader
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import new_id

    library = getattr(host, "_library", None) or getattr(host, "_podcast_library", None)
    task_manager = getattr(host, "_task_manager", None)
    address = str(feed_url or "").strip()
    if library is None or task_manager is None or not address:
        return False
    if any(getattr(existing, "feed_url", "") == address for existing in library.shows):
        host._announce("You are already subscribed to that podcast.")
        return False

    safe_mode = bool(getattr(host, "_safe_mode", False))

    def _work(**_kwargs: object) -> feed_reader.FeedInfo:
        return feed_reader.fetch_and_parse_feed(address, safe_mode=safe_mode)

    def _done(_op: str, info: feed_reader.FeedInfo) -> None:
        show = PodcastShow(
            id=new_id(),
            title=info.title or address,
            feed_url=address,
            homepage=info.homepage,
            artwork_url=info.artwork_url,
            tags=info.tags,
            episodes=info.episodes,
        )
        if not library.add_show(show):
            host._announce("You are already subscribed to that podcast.")
            return
        _save_and_refresh(host)
        host._announce(f"Subscribed to {show.title}.")

    host._announce("Fetching that podcast...")
    task_manager.submit(
        "podcast-podroll-subscribe",
        _work,
        on_success=_done,
        on_failure=lambda _op, exc: host._announce(f"Could not subscribe: {exc}"),
    )
    return True


def _save_and_refresh(host: Any) -> None:
    """Persist and redraw, whichever of the two hosts this is."""
    for name in ("_on_library_changed", "_save_podcast_library"):
        callback = getattr(host, name, None)
        if callable(callback):
            callback()
            return
