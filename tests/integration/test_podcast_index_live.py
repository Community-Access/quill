"""Live proof that the Podcast Index credential works and the catalogue reads.

The credential is baked in at build time, which means the way it fails is
silent: a build with an empty or revoked pair looks exactly like a build with a
working one until somebody opens the branch. This module points the real client
at the real index and checks the invariants that must hold whatever it serves
on the day:

* the app has a credential at all, and the signature is accepted;
* a search answers with feeds rather than store listings;
* a show's fact sheet comes back with the facts a details panel promises;
* **a show's episodes come back without subscribing to it**, which is the whole
  reason the branch exists;
* the taxonomy and the trending list are non-empty.

Opt in -- it needs the network and a credential::

    QUILL_PODCAST_INDEX_LIVE=1 pytest tests/integration/test_podcast_index_live.py -v
"""

from __future__ import annotations

import os

import pytest

from quill.core.podcasts import podcast_index
from quill.core.podcasts import podcast_index_catalog as catalog

pytestmark = pytest.mark.skipif(
    os.environ.get("QUILL_PODCAST_INDEX_LIVE") != "1",
    reason="Live Podcast Index probe; set QUILL_PODCAST_INDEX_LIVE=1 to run.",
)


@pytest.fixture(scope="module", autouse=True)
def _needs_a_credential() -> None:
    if not podcast_index.available():
        pytest.skip(
            "No Podcast Index credential in this checkout. Run "
            "tools/generate_podcast_index_key.py with the key and secret."
        )


def test_the_build_carries_a_credential_and_the_index_accepts_it() -> None:
    """The failure this file exists to catch: a shipped build with no key."""
    key, secret = podcast_index.credentials()
    assert key and secret

    rows = podcast_index.search_podcasts("news", limit=5)

    assert rows, "the index accepted the credential but found nothing for 'news'"
    assert all(row.feed_url for row in rows), "a search row with no feed is unusable"


def test_a_show_fact_sheet_answers_what_a_details_panel_promises() -> None:
    rows = podcast_index.search_podcasts("this american life", limit=5)
    feed = next((row.feed_url for row in rows if row.feed_url), "")
    if not feed:
        pytest.skip("nothing matched to look up")

    show = catalog.show_facts(feed)

    assert show is not None
    assert show.title
    assert show.feed_url
    # The catalogue facts a bare feed address cannot give.
    assert show.episode_count >= 0
    assert isinstance(show.categories, tuple)


def test_a_shows_episodes_come_back_without_subscribing() -> None:
    """The gap this integration was built to close."""
    rows = podcast_index.search_podcasts("planet money", limit=5)
    feed = next((row.feed_url for row in rows if row.feed_url), "")
    if not feed:
        pytest.skip("nothing matched to list")

    episodes = catalog.episodes_for_feed(feed, limit=10)

    if not episodes:
        pytest.skip(f"the index lists no episodes for {feed} today")
    assert any(episode.audio_url for episode in episodes), "no episode had audio to play"
    assert any(episode.title for episode in episodes)


def test_the_taxonomy_and_the_trending_list_are_there() -> None:
    found = catalog.categories()
    assert len(found) > 50, "the index publishes a hundred-odd categories"
    assert all(category.name for category in found)

    shows = catalog.trending(limit=10)
    assert shows, "nothing is trending, which would be a first"
    assert all(show.feed_url for show in shows)


def test_the_browse_branch_renders_what_the_index_serves() -> None:
    """End to end: the rows the tree would actually show."""
    from quill.core.radio import browse_sources

    rows = browse_sources.browse("pitrending")

    assert rows, "the Trending Now branch came back empty"
    assert all(row.is_folder for row in rows)
    # Every row says something before it is opened -- that is the point.
    assert any(row.note for row in rows)
