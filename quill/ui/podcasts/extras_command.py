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

#: Where the host keeps its About This Episode window.
_WINDOW_KEY = "_episode_extras_window"


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


def open_episode_extras(host: Any, show: Any, episode: Any) -> Any:
    """Say what there is, then show it -- in the one About This Episode window.

    A peer (qc.md Phase 4): made once per host, and asked for again -- for this
    episode or another -- it is raised with its tabs rebuilt for the episode
    asked about rather than opened a second time.
    """
    from quill.core.podcasts import extras as extras_module
    from quill.ui.podcasts.episode_extras_dialog import EpisodeExtrasWindow
    from quill.ui.podcasts.peer_window import open_peer

    extras = episode_extras(host, show, episode)
    marks = _bookmark_section(host, show, episode)
    if marks is not None:
        extras.sections.append(marks)
    host._announce(extras_module.summary(extras))

    content: dict[str, Any] = {
        "episode_title": str(getattr(episode, "title", "")),
        "open_url": lambda url: open_link(host, url),
        "play_url": lambda url, label: play_stream(host, show, url, label),
        "subscribe_feed": lambda url: subscribe_to(host, url),
        "jump_to": lambda target: _jump(host, show, episode, target),
    }
    existing = getattr(host, _WINDOW_KEY, None)
    if existing is not None and existing.frame:
        existing.load(extras, **content)

    def _make(owner: Any) -> EpisodeExtrasWindow:
        return EpisodeExtrasWindow(
            getattr(owner, "dialog", None) or getattr(owner, "frame", None),
            extras=extras,
            announce=owner._announce,
            **content,
        )

    return open_peer(host, _WINDOW_KEY, _make)


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
        host._announce("You already follow that podcast.")
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
            host._announce("You already follow that podcast.")
            return
        _save_and_refresh(host)
        host._announce(f"Now following {show.title}.")

    host._announce("Fetching that podcast...")
    task_manager.submit(
        "podcast-podroll-subscribe",
        _work,
        on_success=_done,
        on_failure=lambda _op, exc: _report(host, f"Could not follow it: {exc}"),
    )
    return True


def _save_and_refresh(host: Any) -> None:
    """Persist and redraw, whichever of the two hosts this is."""
    for name in ("_on_library_changed", "_save_podcast_library"):
        callback = getattr(host, name, None)
        if callable(callback):
            callback()
            return


def _bookmark_section(host: Any, show: Any, episode: Any) -> Any:
    """This episode's bookmarks as a tab, or None when it has none (qc.md 18.1)."""
    from quill.core import bookmark_anchors
    from quill.core.bookmark_ops import spoken_position
    from quill.core.podcasts.extras import ACTION_JUMP, Row, Section

    store_of = getattr(host, "_bookmark_store", None)
    if not callable(store_of):
        return None
    anchor = bookmark_anchors.for_episode(str(show.id), str(episode.guid))
    try:
        marks = store_of().list(anchor)
    except Exception:  # noqa: BLE001 - bookmarks are extra, never a reason to fail
        return None
    if not marks:
        return None
    rows = tuple(
        Row(
            label=" -- ".join(
                part for part in (spoken_position(mark.position_ms), mark.note.strip()) if part
            ),
            action=ACTION_JUMP,
            target=str(mark.position_ms),
        )
        for mark in sorted(marks, key=lambda m: m.position_ms)
    )
    return Section(
        key="bookmarks",
        title="Bookmarks",
        rows=rows,
        heading="The places you marked in this episode. Go There plays it from that moment.",
        noun=("bookmark", "bookmarks"),
    )


def _jump(host: Any, show: Any, episode: Any, target: str) -> bool:
    """Play *episode* from the bookmark at *target* milliseconds."""
    from quill.ui.podcasts.show_actions import start_episode_playback

    try:
        position = max(0, int(target))
    except ValueError:
        return False
    start_episode_playback(
        host._podcast_controller, host._podcast_library, show, episode, resume_ms=position
    )
    return True


def _report(host: Any, sentence: str) -> None:
    from quill.ui.podcasts.failure_report import report_failure

    report_failure(host, sentence)
