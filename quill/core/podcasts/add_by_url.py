"""Add a podcast by pasting its feed address. One validator, two apps.

The flow is the whole feature: somebody found a feed URL on a show's
website and wants it in the library. Everything that can go wrong at that
moment has a *different* fix -- a typo, a page instead of a feed, a feed
behind a sign-in, a site that is down -- so the result of every failure is
a sentence naming the fix, never a stack trace and never a bare "invalid".

Used by Quill Radio's Add a Podcast by URL... rows and available to Quill
Cast; the success path lands in the shared library (follow + first episode
sync), so the show is simply there in both apps.

wx-free, strict-typed. The one network call is the reviewed feed_reader
egress site; nothing new reaches the network from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddByUrlOutcome:
    """What happened, and the sentence to say about it."""

    ok: bool
    spoken: str
    #: On success (and on "already followed"): the canonical feed URL, so the
    #: caller can walk the tree to the show.
    feed_url: str = ""
    title: str = ""


def _invalid(spoken: str) -> AddByUrlOutcome:
    return AddByUrlOutcome(False, spoken)


def add_podcast_by_url(data_dir: Path, url: str, *, safe_mode: bool = False) -> AddByUrlOutcome:
    """Validate *url* as a podcast feed and subscribe to it. Never raises.

    Blocking (one bounded HTTPS GET): callers run it off the UI thread.
    """
    address = (url or "").strip()
    if not address:
        return _invalid("Paste or type the feed's web address first.")
    if address.lower().startswith("http://"):
        # Plain-http feeds are refused downstream; nearly every one answers
        # on https today, so try that rather than bouncing the listener.
        address = "https://" + address[7:]
    if not address.lower().startswith("https://"):
        return _invalid(
            "That does not look like a web address. A podcast feed address starts "
            "with https:// -- it is usually behind a link named RSS or Subscribe "
            "on the show's website."
        )
    if safe_mode:
        return _invalid(
            "Adding a podcast needs the network, which Safe Mode disables. "
            "Restart normally to add it."
        )

    from quill.core.podcasts.feed_reader import (
        FeedAuthError,
        FeedReaderError,
        fetch_and_parse_feed,
    )

    try:
        info = fetch_and_parse_feed(address, safe_mode=safe_mode)
    except FeedAuthError:
        return _invalid(
            "That feed asks for a sign-in before it will answer. Add it in Quill "
            "Cast's Add Podcast dialog, which can save the feed's username and "
            "password; it will then work in both apps."
        )
    except FeedReaderError as error:
        return _invalid(
            f"That address could not be read as a feed. {error} "
            "Check the address for typos, and that you are online."
        )

    playable = [episode for episode in info.episodes if episode.audio_url]
    if not playable:
        if info.title:
            return _invalid(
                f"{info.title} reads as a feed, but it lists no playable episodes -- "
                "it may be a news feed rather than a podcast. Nothing was added."
            )
        return _invalid(
            "That address answers with a web page, not a podcast feed. On the "
            "show's website, look for a link named RSS or Subscribe and paste "
            "that address instead."
        )

    from quill.core.podcasts.subscriptions import load_library, merge_episodes, save_library
    from quill.core.radio.podcast_follow import follow_feed

    result = follow_feed(
        data_dir,
        feed_url=address,
        title=info.title or address,
        homepage=info.homepage,
        artwork_url=info.artwork_url,
    )
    title = info.title or address
    if not result.added:
        return AddByUrlOutcome(True, f"You already follow {title}.", feed_url=address, title=title)
    # Sync the just-fetched episodes in, so the show opens full rather than
    # empty-until-someone-refreshes (same manners as browsing a show).
    library = load_library(data_dir)
    show = library.find_show_by_feed_url(address)
    if show is not None and merge_episodes(show, playable) > 0:
        save_library(data_dir, library)
    count = len(playable)
    return AddByUrlOutcome(
        True,
        f"Subscribed to {title}. {count} episode{'s are' if count != 1 else ' is'} "
        "listed, and the show is shared with Quill Cast.",
        feed_url=address,
        title=title,
    )
