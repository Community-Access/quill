"""The Podcast Index as a branch of the browse tree.

Quill Radio could already *search* for a podcast and subscribe to it. What it
could not do was **look at one** -- a show was a name, and the only way to find
out what it published was to subscribe and then go and read the list. That is a
commitment made in order to ask a question, and it is the gap the
podcast-directory review named.

This branch answers it. Every show here opens straight into its episodes,
subscribed or not, and every episode is a row you can play, favourite,
download, or read the transcript of exactly like any other row in the tree --
because it *is* one. Nothing about this branch is a special case downstream: a
show becomes a folder, an episode becomes a ``RadioStation`` with
``is_recording=True``, and the rest of the app has never heard of the Podcast
Index.

Three ways in, in the order somebody actually uses them:

* **Trending Now** -- what is being talked about today, which no other branch
  in the tree can answer for podcasts.
* **By Category** -- the index's own hundred-and-twelve-category taxonomy,
  each one a trending list narrowed to it.
* **Search the Podcast Index...** -- the in-tree search, so finding a show does
  not take the tree away from you.

**What each row says before you open it.** A show row speaks its author, how
many episodes it has, its categories, and -- when it matters -- that the index
can no longer read the feed. An episode row speaks its length and when it was
published. That is the whole point of asking a catalogue rather than a feed:
the facts arrive before the commitment does.

Nothing here is required for anything. Switch the branch off in Choose Browse
Sources and podcasts work exactly as they did; the credential is the app's, so
nobody configures anything to switch it on. See
:mod:`quill.core.podcasts.podcast_index` for what that credential is and is not.

wx-free, strict-typed. Every request goes through the catalogue client's own
reviewed egress site and its Safe Mode refusal.
"""

from __future__ import annotations

from datetime import UTC

from quill.core.radio.browse_nodes import BrowseNode, action, folder, leaf, make_id
from quill.core.radio.models import RadioStation

#: How many shows a list shows. The index will serve more; a browse level
#: nobody can arrow through is not a better answer.
SHOW_LIMIT = 50

#: How many episodes a show opens with, newest first. A show with two thousand
#: episodes must not try to be one level of a tree -- the same rule the YouTube
#: channel branch follows.
EPISODE_LIMIT = 100

SOURCE_LABEL = "Podcast Index"


def _spoken_length(seconds: int) -> str:
    """ "42 minutes", the way a row should read it aloud. "" when unknown."""
    if seconds <= 0:
        return ""
    from quill.core.speech_text import speak_duration

    return speak_duration(float(seconds))


def _spoken_date(published: int) -> str:
    """ "3 March 2026" from unix seconds, or "" -- never a bare timestamp."""
    if published <= 0:
        return ""
    from datetime import datetime

    try:
        return datetime.fromtimestamp(published, tz=UTC).strftime("%d %B %Y").lstrip("0")
    except (OverflowError, OSError, ValueError):
        return ""


def show_note(show: object) -> str:
    """What a show row says after its name."""
    summary = str(getattr(show, "summary", "") or "")
    return summary


def episode_note(episode: object) -> str:
    """What an episode row says after its title: how long, and when."""
    parts = [
        _spoken_length(int(getattr(episode, "duration_seconds", 0) or 0)),
        _spoken_date(int(getattr(episode, "published", 0) or 0)),
    ]
    return ", ".join(part for part in parts if part)


def show_details(show: object) -> str:
    """The details-panel text for a show: the catalogue's whole fact sheet.

    Written to be read down, in the order somebody deciding whether to
    subscribe wants it, and it stops rather than padding: a field the index has
    nothing for is a line that is not there.
    """
    lines: list[str] = []
    author = str(getattr(show, "author", "") or "")
    if author:
        lines.append(f"By: {author}")
    categories = tuple(getattr(show, "categories", ()) or ())
    if categories:
        lines.append(f"Categories: {', '.join(categories)}")
    language = str(getattr(show, "language", "") or "")
    if language:
        lines.append(f"Language: {language}")
    count = int(getattr(show, "episode_count", 0) or 0)
    if count:
        lines.append(f"Episodes: {count}")
    last = _spoken_date(int(getattr(show, "last_published", 0) or 0))
    if last:
        lines.append(f"Latest episode: {last}")
    if getattr(show, "explicit", False):
        lines.append("Marked explicit by the publisher.")
    if getattr(show, "dead", False):
        # Said plainly rather than left to be discovered by subscribing to a
        # show that will never publish again.
        lines.append("The Podcast Index can no longer read this feed.")
    funding_url = str(getattr(show, "funding_url", "") or "")
    if funding_url:
        label = str(getattr(show, "funding_label", "") or "") or "Support this show"
        lines.append(f"{label}: {funding_url}")
    description = str(getattr(show, "description", "") or "").strip()
    if description:
        lines.extend(["", description])
    return "\n".join(lines)


def show_folder(show: object) -> BrowseNode:
    """One show as a folder that opens into its episodes."""
    feed_url = str(getattr(show, "feed_url", "") or "")
    count = int(getattr(show, "episode_count", 0) or 0)
    return folder(
        make_id("pishow", feed_url),
        str(getattr(show, "display_name", "") or feed_url),
        note=show_note(show),
        child_count=count or None,
    )


def episode_leaf(episode: object, show_title: str, feed_url: str) -> BrowseNode:
    """One episode as a playable row -- an ordinary station, like every other.

    When the index knows the episode's transcript, the node id carries its
    address and type, exactly as a subscribed episode's row does
    (``browse_libraries._episode_leaves``) -- so **View Transcript works on a
    show nobody is subscribed to**. That is the one transcript source neither
    Earshot nor Cast has: Earshot can only read the tag out of a feed it has
    followed and refreshed, and the index is holding the same tag for every
    feed in the catalogue.
    """
    audio = str(getattr(episode, "audio_url", "") or "")
    transcript_url = str(getattr(episode, "transcript_url", "") or "")
    node_id = (
        make_id(
            "piepisode", audio, transcript_url, str(getattr(episode, "transcript_type", "") or "")
        )
        if transcript_url
        else make_id("piepisode", audio)
    )
    return leaf(
        RadioStation(
            name=str(getattr(episode, "display_name", "") or ""),
            stream_url=audio,
            # The feed, not the episode page: this is what every podcast row in
            # the tree carries, and what Subscribe reads to find the show.
            homepage=feed_url,
            source=SOURCE_LABEL,
            # A published episode is a finished recording: it seeks, reports a
            # position, remembers where you stopped.
            is_recording=True,
            notes=str(getattr(episode, "description", "") or ""),
            tags=(show_title,) if show_title else (),
        ),
        node_id=node_id,
        note=episode_note(episode),
    )


def browse_root(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The branch itself: trending, the taxonomy, and a way to search it."""
    if args and args[0]:
        return []
    return [
        folder(make_id("pitrending"), "Trending Now", note="what is being talked about today"),
        folder(make_id("picategories"), "By Category", note="the index's own taxonomy"),
        action(
            "searchpodcastindex",
            "Search the Podcast Index...",
            note="finds shows iTunes does not",
        ),
    ]


def browse_trending(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """Trending shows, optionally narrowed to one category."""
    from quill.core.podcasts import podcast_index_catalog as catalog

    category = args[0] if args and args[0] else ""
    shows = catalog.trending(limit=SHOW_LIMIT, category=category, safe_mode=safe_mode)
    return [show_folder(show) for show in shows if getattr(show, "feed_url", "")]


def browse_categories(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """The index's taxonomy, each category a trending list narrowed to it."""
    from quill.core.podcasts import podcast_index_catalog as catalog

    return [
        folder(make_id("pitrending", found.name), found.name)
        for found in catalog.categories(safe_mode=safe_mode)
        if found.name
    ]


def browse_show(args: list[str], *, safe_mode: bool) -> list[BrowseNode]:
    """A show's episodes -- **without subscribing to it**.

    The node id is the feed address, which is also what a Subscribe on this row
    needs, so following the show costs no second lookup.
    """
    from quill.core.podcasts import podcast_index_catalog as catalog

    if not args or not args[0]:
        return []
    feed_url = args[0]
    show = catalog.show_facts(feed_url, safe_mode=safe_mode)
    title = str(getattr(show, "title", "") or "") if show is not None else ""
    episodes = catalog.episodes_for_feed(feed_url, limit=EPISODE_LIMIT, safe_mode=safe_mode)
    return [
        episode_leaf(episode, title, feed_url)
        for episode in episodes
        if getattr(episode, "audio_url", "")
    ]


def search(term: str, *, safe_mode: bool = False) -> list[BrowseNode]:
    """Shows matching *term*, as browse rows -- the in-tree search's answer."""
    from quill.core.podcasts import podcast_index

    rows = podcast_index.search_podcasts(term, limit=SHOW_LIMIT, safe_mode=safe_mode)
    nodes: list[BrowseNode] = []
    for row in rows:
        feed_url = str(getattr(row, "feed_url", "") or "")
        if not feed_url:
            continue
        # The search result carries a title and a feed; the fact sheet comes
        # from the cache when the listener opens the row, not now -- fifty
        # lookups to render one list is exactly the cost this tree avoids.
        nodes.append(
            folder(
                make_id("pishow", feed_url),
                str(getattr(row, "title", "") or feed_url),
                note=str(getattr(row, "artist", "") or ""),
            )
        )
    return nodes
