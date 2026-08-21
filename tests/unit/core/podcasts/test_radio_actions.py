"""The Radio-to-Cast instruction handoff.

The case that decides whether this file exists at all is the last one: a new
Radio's instruction must survive an **older** Cast, because Radio ships first
and every Cast in the field is the old one.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from quill.core.podcasts import radio_actions
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

_FEED = "https://feeds.example.com/ba"
_AUDIO = "https://cdn.example.com/ep214.mp3"


def _library() -> PodcastLibrary:
    show = PodcastShow(id="show-1", title="Blind Abilities", feed_url=_FEED)
    show.episodes = [
        PodcastEpisode(guid="guid-214", title="Episode 214", audio_url=_AUDIO),
        PodcastEpisode(
            guid="guid-215", title="Episode 215", audio_url="https://cdn.example.com/ep215.mp3"
        ),
    ]
    library = PodcastLibrary()
    library.shows = [show]
    return library


def _record(tmp_path: Path, action: str) -> bool:
    return radio_actions.record_action(
        tmp_path, feed_url=_FEED, audio_url=_AUDIO, action=action, title="Episode 214"
    )


# -- writing -----------------------------------------------------------------


def test_an_instruction_is_written_and_waits(tmp_path: Path) -> None:
    assert _record(tmp_path, radio_actions.ACTION_QUEUE_TOP)
    pending = radio_actions.pending(tmp_path)
    assert len(pending) == 1
    assert pending[0]["action"] == "queue_top"
    assert pending[0]["audio"] == _AUDIO


def test_asking_twice_is_one_instruction(tmp_path: Path) -> None:
    _record(tmp_path, radio_actions.ACTION_QUEUE_TOP)
    _record(tmp_path, radio_actions.ACTION_QUEUE_BOTTOM)
    pending = radio_actions.pending(tmp_path)
    assert [row["action"] for row in pending] == ["queue_bottom"]


def test_played_and_queue_are_not_alternatives(tmp_path: Path) -> None:
    """ "Mark it played" and "put it in the queue" can both be true."""
    _record(tmp_path, radio_actions.ACTION_PLAYED)
    _record(tmp_path, radio_actions.ACTION_QUEUE_TOP)
    assert {row["action"] for row in radio_actions.pending(tmp_path)} == {
        "played",
        "queue_top",
    }


def test_played_and_unplayed_replace_each_other(tmp_path: Path) -> None:
    _record(tmp_path, radio_actions.ACTION_PLAYED)
    _record(tmp_path, radio_actions.ACTION_UNPLAYED)
    assert [row["action"] for row in radio_actions.pending(tmp_path)] == ["unplayed"]


def test_junk_is_refused_rather_than_written(tmp_path: Path) -> None:
    assert not radio_actions.record_action(
        tmp_path, feed_url=_FEED, audio_url=_AUDIO, action="delete_everything"
    )
    assert not radio_actions.record_action(
        tmp_path, feed_url="", audio_url=_AUDIO, action=radio_actions.ACTION_INBOX
    )
    assert radio_actions.pending(tmp_path) == []


def test_a_damaged_file_reads_as_nothing_waiting(tmp_path: Path) -> None:
    (tmp_path / "radio-actions.json").write_text("{ not json", encoding="utf-8")
    assert radio_actions.pending(tmp_path) == []


# -- merging -----------------------------------------------------------------


def test_queue_top_puts_it_next(tmp_path: Path) -> None:
    _record(tmp_path, radio_actions.ACTION_QUEUE_TOP)
    library = _library()
    applied, said = radio_actions.merge_radio_actions(tmp_path, library)
    assert applied == 1
    assert [item.episode_guid for item in library.queue] == ["guid-214"]
    assert said == ["1 episode added to your queue."]
    # Consumed: a second launch must not queue it again.
    assert radio_actions.pending(tmp_path) == []


def test_queue_bottom_appends(tmp_path: Path) -> None:
    library = _library()
    from quill.core.podcasts import queue as queue_module

    queue_module.add_to_queue(library, "show-1", "guid-215")
    _record(tmp_path, radio_actions.ACTION_QUEUE_BOTTOM)
    radio_actions.merge_radio_actions(tmp_path, library)
    assert [item.episode_guid for item in library.queue] == ["guid-215", "guid-214"]


def test_played_is_applied_and_stamped(tmp_path: Path) -> None:
    _record(tmp_path, radio_actions.ACTION_PLAYED)
    library = _library()
    applied, said = radio_actions.merge_radio_actions(tmp_path, library)
    episode = library.shows[0].episodes[0]
    assert applied == 1
    assert episode.played is True
    assert episode.position_ms == 0
    # The timestamp is what lets the place travel; an unstamped write is a
    # place that silently stops syncing.
    assert episode.position_updated_at.endswith("Z")
    assert said == ["1 episode marked played in Quill Radio."]


def test_the_inbox_instruction_files_it_at_the_top_level(tmp_path: Path) -> None:
    from quill.core.podcasts.inbox import inbox_key

    _record(tmp_path, radio_actions.ACTION_INBOX)
    library = _library()
    applied, said = radio_actions.merge_radio_actions(tmp_path, library)
    assert applied == 1
    assert inbox_key("show-1", "guid-214") in library.inbox_assignments
    assert said == ["1 episode sent to your Inbox."]


def test_an_episode_cast_has_never_fetched_is_kept_for_later(tmp_path: Path) -> None:
    """The phone listened to an episode from a feed this machine has not refreshed."""
    radio_actions.record_action(
        tmp_path,
        feed_url="https://feeds.example.com/other",
        audio_url="https://cdn.example.com/unknown.mp3",
        action=radio_actions.ACTION_QUEUE_TOP,
    )
    applied, _said = radio_actions.merge_radio_actions(tmp_path, _library())
    assert applied == 0
    assert len(radio_actions.pending(tmp_path)) == 1


def test_a_stale_unmatched_instruction_is_dropped(tmp_path: Path) -> None:
    stale = [
        {
            "feed": "https://feeds.example.com/other",
            "audio": "https://cdn.example.com/unknown.mp3",
            "action": "queue_top",
            "at": time.time() - (60 * 24 * 3600),
        }
    ]
    (tmp_path / "radio-actions.json").write_text(json.dumps(stale), encoding="utf-8")
    radio_actions.merge_radio_actions(tmp_path, _library())
    assert radio_actions.pending(tmp_path) == []


def test_an_instruction_already_true_changes_nothing(tmp_path: Path) -> None:
    _record(tmp_path, radio_actions.ACTION_PLAYED)
    library = _library()
    library.shows[0].episodes[0].played = True
    applied, said = radio_actions.merge_radio_actions(tmp_path, library)
    assert applied == 0
    assert said == []


# -- the reason this is a second file ----------------------------------------


def test_an_older_cast_leaves_the_backlog_intact(tmp_path: Path) -> None:
    """The forward-compatibility hazard this whole module exists to avoid.

    An older Cast reads ``radio-listens.json`` and knows nothing about
    ``radio-actions.json``. Had the instruction been a field on the listens
    record, that Cast would have matched it, done nothing, and deleted it --
    losing the queue intent silently, in what is the *common* case, because
    Radio ships first.
    """
    from quill.core.podcasts.radio_listens import merge_radio_listens

    _record(tmp_path, radio_actions.ACTION_QUEUE_TOP)
    library = _library()
    # This is everything an older Cast does at launch.
    merge_radio_listens(tmp_path, library)
    assert len(radio_actions.pending(tmp_path)) == 1
    assert library.queue == []
