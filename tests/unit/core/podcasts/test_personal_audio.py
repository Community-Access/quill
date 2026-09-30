"""Personal Audio as a collection (ear.md R8, R10, R12), against Earshot's PRD.

The most important test in this file is the round-trip one. Cast could import a
file and play it, and then lose it: ``PodcastEpisode.from_dict`` required a
non-empty ``audio_url``, imported files have none, so every Personal Audio episode
was silently dropped on load. The show survived -- ``PodcastShow.from_dict`` has no
such rule -- so it read as "my recording disappeared" rather than as a load
failure, and left an orphaned file on disk.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from quill.core.podcasts import personal_audio
from quill.core.podcasts.local_duplicates import content_hash, find_duplicate, prompt_for
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library


def _item(title: str, *, published: str, path: str = "", **kwargs) -> PodcastEpisode:
    return PodcastEpisode(
        guid=title.lower().replace(" ", "-"),
        title=title,
        audio_url="",
        downloaded_path=path or ("C:/managed/" + title + ".mp3"),
        published=published,
        **kwargs,
    )


def _library(*episodes: PodcastEpisode, subscribed: bool = True) -> PodcastLibrary:
    shows = [
        PodcastShow(
            id="local-1",
            title="Personal Audio",
            feed_url="",
            is_local=True,
            episodes=list(episodes),
        )
    ]
    if subscribed:
        shows.append(
            PodcastShow(
                id="sub-1",
                title="The Daily",
                feed_url="https://e/f.xml",
                episodes=[
                    PodcastEpisode(
                        guid="d1",
                        title="A subscribed episode",
                        audio_url="https://e/d1.mp3",
                        published="2026-09-30T00:00:00",
                    )
                ],
            )
        )
    return PodcastLibrary(shows=shows)


# -- the regression: imported items used to vanish on restart ---------------- #


def test_an_imported_item_survives_a_save_and_a_load() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        episode = _item(
            "My Lecture",
            published="2026-09-30T10:00:00",
            path=str(folder / "lecture.mp3"),
            position_ms=90_000,
            speed_override=1.5,
            content_hash="abc123",
            source_filename="Zoom recording.m4a",
        )
        save_library(folder, _library(episode))

        restored = load_library(folder)
        found = personal_audio.items(restored)

        assert len(found) == 1, "the imported item was dropped on load"
        kept = found[0].episode
        assert kept.position_ms == 90_000
        assert kept.speed_override == 1.5
        assert kept.content_hash == "abc123"
        assert kept.source_filename == "Zoom recording.m4a"


def test_an_episode_with_neither_a_url_nor_a_path_is_still_rejected() -> None:
    """The check was corrected, not removed: an episode needs audio somewhere."""
    assert (
        PodcastEpisode.from_dict({
            "guid": "g",
            "title": "t",
            "audio_url": "",
            "downloaded_path": "",
        })
        is None
    )


# -- the collection ---------------------------------------------------------- #


def test_only_imported_files_are_personal_audio() -> None:
    library = _library(_item("Mine", published="2026-09-30T10:00:00"))
    assert [item.title for item in personal_audio.items(library)] == ["Mine"]


def test_items_are_newest_added_first() -> None:
    """The reason somebody opens this place is usually what they just put in it."""
    library = _library(
        _item("First", published="2026-09-01T10:00:00"),
        _item("Third", published="2026-09-03T10:00:00"),
        _item("Second", published="2026-09-02T10:00:00"),
    )
    assert [item.title for item in personal_audio.items(library)] == ["Third", "Second", "First"]


def test_the_node_carries_its_count_and_drops_it_when_empty() -> None:
    assert personal_audio.node_label(_library()) == "Personal Audio"
    assert personal_audio.node_label(_library(_item("A", published="x"))) == "Personal Audio (1)"


def test_an_empty_collection_says_what_to_do_about_it() -> None:
    """An empty list that only says "empty" leaves a keyboard listener nowhere."""
    text = personal_audio.empty_state(_library())
    assert "Add Local Podcast" in text
    assert "original file stays where it is" in text
    assert personal_audio.empty_state(_library(_item("A", published="x"))) == ""


def test_a_namespaced_id_is_neither_a_filename_nor_a_feed() -> None:
    library = _library(_item("Mine", published="x"))
    item = personal_audio.items(library)[0]
    ident = personal_audio.content_id(item.show, item.episode)
    assert ident.startswith("personal-audio:")
    assert ".mp3" not in ident


# -- unavailable, not reset -------------------------------------------------- #


def test_a_missing_file_reads_as_unavailable_without_losing_the_position() -> None:
    """A drive that was unplugged will be plugged back in, and the position is the
    one thing the listener cannot recover."""
    library = _library(
        _item("Gone", published="x", path="C:/nowhere/absent.mp3", position_ms=60_000)
    )
    unavailable = personal_audio.unavailable_items(library)

    assert [item.title for item in unavailable] == ["Gone"]
    assert unavailable[0].row().endswith("Unavailable, the file is missing")
    assert unavailable[0].episode.position_ms == 60_000


def test_a_present_file_reads_as_played_or_unplayed(tmp_path: Path) -> None:
    audio = tmp_path / "there.mp3"
    audio.write_bytes(b"\x00")
    library = _library(_item("Here", published="x", path=str(audio)))
    item = personal_audio.items(library)[0]
    assert item.available
    assert item.row().endswith("Unplayed")
    item.episode.played = True
    assert personal_audio.items(library)[0].row().endswith("Played")


def test_an_orphaned_managed_file_is_reported_not_deleted(tmp_path: Path) -> None:
    """An import that failed between copying and saving leaves one of these."""
    kept = tmp_path / "kept.mp3"
    kept.write_bytes(b"\x00")
    orphan = tmp_path / "orphan.mp3"
    orphan.write_bytes(b"\x00")

    library = _library(_item("Kept", published="x", path=str(kept)))
    found = personal_audio.orphan_files(library, tmp_path)

    assert [p.name for p in found] == ["orphan.mp3"]
    assert orphan.is_file(), "orphan_files must report, never delete"


# -- duplicates by content (R10) -------------------------------------------- #


def test_identical_bytes_under_two_names_are_a_duplicate(tmp_path: Path) -> None:
    first = tmp_path / "recording.m4a"
    second = tmp_path / "lecture 3.m4a"
    for path in (first, second):
        path.write_bytes(b"the same audio bytes")

    library = _library(_item("Lecture Three", published="x", content_hash=content_hash(first)))
    match = find_duplicate(library, content_hash(second))

    assert match is not None
    assert match.title == "Lecture Three"


def test_the_same_filename_with_different_bytes_is_not_a_duplicate(tmp_path: Path) -> None:
    """A dozen devices call a dozen different recordings recording.m4a."""
    first = tmp_path / "a" / "recording.m4a"
    second = tmp_path / "b" / "recording.m4a"
    for path, body in ((first, b"one"), (second, b"two")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    library = _library(_item("First", published="x", content_hash=content_hash(first)))
    assert find_duplicate(library, content_hash(second)) is None


def test_a_file_that_cannot_be_hashed_matches_nothing() -> None:
    """It should be let through and rejected by validation, which can say why."""
    assert content_hash(Path("nowhere") / "absent.mp3") == ""
    library = _library(_item("A", published="x", content_hash="abc"))
    assert find_duplicate(library, "") is None


def test_the_prompt_names_both_sides_and_offers_both_answers(tmp_path: Path) -> None:
    """A bare "this looks like a duplicate" leaves the listener guessing of what."""
    audio = tmp_path / "recording.m4a"
    audio.write_bytes(b"x")
    library = _library(_item("Lecture Three", published="x", content_hash=content_hash(audio)))
    match = find_duplicate(library, content_hash(audio))
    assert match is not None

    text = prompt_for(match, "recording.m4a")
    assert "recording.m4a" in text
    assert "Lecture Three" in text
    assert "anyway" in text.lower()
    assert "cancel" in text.lower()


# -- per-file speed (R12) --------------------------------------------------- #


def test_a_stored_nonsense_speed_cannot_escape_the_scale() -> None:
    for value, expected in ((99, 5.0), ("fast", 0.0), (-3, 0.0), (None, 0.0), (1.37, 1.35)):
        episode = PodcastEpisode.from_dict({
            "guid": "g",
            "title": "t",
            "audio_url": "",
            "downloaded_path": "x",
            "speed_override": value,
        })
        assert episode is not None
        assert episode.speed_override == expected
