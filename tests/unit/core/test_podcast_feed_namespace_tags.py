"""Reading the Podcasting 2.0 namespace out of a real feed, and keeping it.

The bytes were already being fetched and parsed; everything below them was
being thrown away. These pin the three seams that make it stick: the channel
half and the item half stay apart, the tags survive a refresh, and a feed that
stops publishing them does not erase what it already said.
"""

from __future__ import annotations

from quill.core.podcasts.feed_reader import parse_feed
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import merge_episodes

_FEED = b"""<?xml version="1.0"?>
<rss version="2.0" xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>The Show</title>
    <link>https://show.example</link>
    <podcast:person role="Host">Alice Adams</podcast:person>
    <podcast:funding url="https://support.example">Buy us a coffee</podcast:funding>
    <podcast:podroll><podcast:remoteItem feedUrl="https://one.example/feed"/></podcast:podroll>
    <item>
      <title>Ep 1</title>
      <guid>ep-1</guid>
      <enclosure url="https://audio.example/ep1.mp3" type="audio/mpeg" length="1"/>
      <podcast:person role="Guest">Bob Brown</podcast:person>
      <podcast:soundbite startTime="600" duration="60">The good bit</podcast:soundbite>
      <podcast:location>Kansas City, Missouri</podcast:location>
    </item>
    <podcast:liveItem status="live">
      <title>Live tonight</title>
      <enclosure url="https://live.example/stream" type="audio/mpeg"/>
    </podcast:liveItem>
  </channel>
</rss>
"""

_FEED_WITHOUT_TAGS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>The Show</title>
<item><title>Ep 1</title><guid>ep-1</guid>
<enclosure url="https://audio.example/ep1.mp3" type="audio/mpeg" length="1"/></item>
</channel></rss>
"""


def test_a_host_stays_with_the_show_and_a_guest_with_the_episode() -> None:
    # Reading the whole feed text for the channel would credit every episode's
    # guests to the podcast itself.
    info = parse_feed(_FEED)
    assert [p.display for p in info.tags.people] == ["Alice Adams, host"]
    assert [p.display for p in info.episodes[0].tags.people] == ["Bob Brown, guest"]


def test_the_show_keeps_its_podroll_and_its_funding_link() -> None:
    info = parse_feed(_FEED)
    assert info.tags.podroll == ["https://one.example/feed"]
    assert info.tags.funding[0].url == "https://support.example"


def test_a_live_item_is_found_wherever_the_feed_wrote_it() -> None:
    # Channel-level, but publishers put them among the episodes.
    info = parse_feed(_FEED)
    assert [item.title for item in info.tags.live_items] == ["Live tonight"]


def test_an_episode_keeps_its_marked_moments_and_its_place() -> None:
    episode = parse_feed(_FEED).episodes[0]
    assert [b.title for b in episode.tags.soundbites] == ["The good bit"]
    assert episode.tags.location == "Kansas City, Missouri"


def test_a_feed_that_publishes_none_of_it_costs_nothing() -> None:
    info = parse_feed(_FEED_WITHOUT_TAGS)
    assert info.tags.is_empty
    assert info.episodes[0].tags.is_empty
    assert "tags" not in info.episodes[0].to_dict()


def test_a_refresh_brings_a_credit_added_after_publication() -> None:
    show = PodcastShow(id="s", title="The Show", feed_url="https://show.example/feed")
    merge_episodes(show, parse_feed(_FEED_WITHOUT_TAGS).episodes)
    assert show.episodes[0].tags.is_empty
    merge_episodes(show, parse_feed(_FEED).episodes)
    assert [p.display for p in show.episodes[0].tags.people] == ["Bob Brown, guest"]


def test_a_feed_that_stops_carrying_them_does_not_erase_what_it_said() -> None:
    # An empty replacement is far more often a partial feed than a retraction.
    show = PodcastShow(id="s", title="The Show", feed_url="https://show.example/feed")
    merge_episodes(show, parse_feed(_FEED).episodes)
    merge_episodes(show, parse_feed(_FEED_WITHOUT_TAGS).episodes)
    assert [b.title for b in show.episodes[0].tags.soundbites] == ["The good bit"]
