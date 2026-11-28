"""Real chapter names from every place a publisher puts them (2026-11-27).

Jeff heard "Chapter 1, Chapter 2" instead of real names. The episode he heard
it on was not available, so every candidate on the plan's list is covered here:
ID3 titles in TIT3 behind a placeholder TIT2, the CTOC's own list, MP4 chapter
atoms with no title, Podlove Simple Chapters in the feed, a single-quoted
``podcast:chapters`` address, file chapters for a still-streaming episode, and
Radio reading Cast's playback cache.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.podcasts import chapter_sources as cs
from quill.core.podcasts.feed_reader import _episode_extra_tags
from quill.core.podcasts.namespace_tags import NamespaceTags, parse, parse_psc_chapters

CORPUS = Path(__file__).parents[3] / "corpus" / "audio" / "chaptered-sample.mp3"


def _tagged_copy(tmp_path: Path, frames) -> Path:
    id3 = pytest.importorskip("mutagen.id3")
    path = tmp_path / "episode.mp3"
    shutil.copyfile(CORPUS, path)
    tags = id3.ID3(str(path))
    tags.delall("CHAP")
    tags.delall("CTOC")
    ids = []
    for element_id, start, end, sub in frames:
        tags.add(id3.CHAP(element_id=element_id, start_time=start, end_time=end, sub_frames=sub))
        ids.append(element_id)
    tags.add(
        id3.CTOC(
            element_id="toc",
            flags=id3.CTOCFlags.TOP_LEVEL | id3.CTOCFlags.ORDERED,
            child_element_ids=ids[:2],
            sub_frames=[],
        )
    )
    tags.save(str(path))
    return path


def test_the_corpus_file_reads_its_real_names() -> None:
    titles = [c.title for c in cs.read_file_chapters(CORPUS)]
    assert titles == ["Opening", "Address", "Closing"]


def test_a_placeholder_tit2_gives_way_to_tit3_and_the_toc_is_obeyed(tmp_path: Path) -> None:
    id3 = pytest.importorskip("mutagen.id3")
    path = _tagged_copy(
        tmp_path,
        [
            ("a", 0, 60_000, [id3.TIT2(text=["Chapter 1"]), id3.TIT3(text=["Welcome"])]),
            ("b", 60_000, 120_000, [id3.TIT3(text=["Listener mail"])]),
            ("stray", 120_000, 180_000, [id3.TIT2(text=["Not in the table"])]),
        ],
    )
    chapters = cs.read_file_chapters(path)
    assert [c.title for c in chapters] == ["Welcome", "Listener mail"]
    assert chapters[1].end_ms == 120_000


def test_untitled_file_marks_are_kept_but_show_notes_name_them_first(tmp_path: Path) -> None:
    path = _tagged_copy(tmp_path, [("a", 0, 60_000, []), ("b", 60_000, 120_000, [])])
    assert [c.title for c in cs.read_file_chapters(path)] == ["", ""]
    notes = "0:00 Welcome\n10:00 Listener mail\n20:00 Goodbye"
    found = cs.chapter_cascade(audio_path=path, show_notes=notes, total_ms=1_800_000)
    assert found.source == "show_notes"
    assert cs.chapter_cascade(audio_path=path, total_ms=1_800_000).source == "file"


def test_an_mp4_is_sniffed_and_its_untitled_atoms_are_not_invented(tmp_path, monkeypatch) -> None:
    from quill.core.speech.chapters import Chapter

    path = tmp_path / "cache-entry.audio"  # the playback cache's name for an unknown kind
    path.write_bytes(b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 32)
    monkeypatch.setattr(
        "quill.core.speech.audiobook.read_m4b_chapters",
        lambda p: [
            Chapter(index=0, title="Chapter 1", start_ms=0, end_ms=60_000),
            Chapter(index=1, title="Listener mail", start_ms=60_000, end_ms=120_000),
        ],
    )
    assert [c.title for c in cs.read_file_chapters(path)] == ["", "Listener mail"]


def test_podlove_simple_chapters_are_read_from_the_item() -> None:
    item = (
        "<item><psc:chapters version='1.2'>"
        '<psc:chapter start="00:00:00.000" title="Welcome" />'
        "<psc:chapter start='12:34' title='Listener mail' href='https://x.example/m'/>"
        '<psc:chapter start="bad" title="Dropped"/>'
        "</psc:chapters></item>"
    )
    marks = parse_psc_chapters(item)
    assert [(m.start_ms, m.title) for m in marks] == [(0, "Welcome"), (754_000, "Listener mail")]
    assert marks[1].link_url == "https://x.example/m"
    tags = parse(item)
    assert NamespaceTags.from_dict(tags.to_dict()).psc_chapters == marks


def test_podlove_chapters_feed_the_published_tier_even_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(cs, "_streaming_head", lambda show, episode: None)
    monkeypatch.setattr(
        "quill.core.podcasts.playback_cache.local_audio_path", lambda show, episode: None
    )
    tags = parse(
        '<item><psc:chapter start="0" title="Welcome"/>'
        '<psc:chapter start="600" title="Listener mail"/></item>'
    )
    episode = SimpleNamespace(
        guid="g",
        chapters_url="",
        description="",
        downloaded_path="",
        tags=tags,
        duration_seconds=1800,
        audio_url="",
    )
    found = cs.build_episode_chapters(episode, None, safe_mode=True)
    assert found.source == "published"
    assert [c.title for c in found.chapters] == ["Welcome", "Listener mail"]


def test_a_single_quoted_chapters_address_is_read() -> None:
    url, _transcript, _kind = _episode_extra_tags(
        "<item><podcast:chapters url='https://x.example/c.json' "
        "type='application/json+chapters'/></item>"
    )
    assert url == "https://x.example/c.json"


def test_a_streaming_mp3s_head_is_enough_for_its_chapters(tmp_path, monkeypatch) -> None:
    part = tmp_path / "abc.mp3.part"
    shutil.copyfile(CORPUS, part)
    monkeypatch.setattr("quill.core.podcasts.playback_cache.partial_path", lambda *a: part)
    head = cs._streaming_head(SimpleNamespace(id="s"), SimpleNamespace(guid="g", audio_url=""))
    assert head == part
    assert [c.title for c in cs.read_file_chapters(head)] == ["Opening", "Address", "Closing"]


def test_a_streaming_file_whose_tag_has_not_arrived_is_not_read(tmp_path, monkeypatch) -> None:
    part = tmp_path / "abc.mp3.part"
    part.write_bytes(CORPUS.read_bytes()[:64])
    monkeypatch.setattr("quill.core.podcasts.playback_cache.partial_path", lambda *a: part)
    assert cs._streaming_head(SimpleNamespace(id="s"), SimpleNamespace(guid="g")) is None


def test_radio_reads_casts_playback_cache_for_a_streamed_episode(monkeypatch) -> None:
    from quill.core.radio import chapter_lookup

    seen: list[tuple] = []
    monkeypatch.setattr(
        "quill.core.podcasts.playback_cache.cached_audio",
        lambda show, guid, url="": seen.append((show, guid, url)) or CORPUS,
    )
    chapters, source = chapter_lookup.chapters_for_media(
        None, show_id="s", episode_guid="g", media_url="https://x.example/e.mp3"
    )
    assert seen == [("s", "g", "https://x.example/e.mp3")]
    assert source == chapter_lookup.SOURCE_FILE
    assert [c.title for c in chapters] == ["Opening", "Address", "Closing"]


def test_a_streamed_episode_gets_one_second_look() -> None:
    from quill.ui.podcasts.chapter_retry import should_retry

    host = SimpleNamespace()
    streamed = SimpleNamespace(downloaded_path="")
    assert should_retry(host, ("s", "g"), streamed, SimpleNamespace(source="show_notes"))
    assert not should_retry(host, ("s", "g"), streamed, SimpleNamespace(source="published"))
    downloaded = SimpleNamespace(downloaded_path="C:/x.mp3")
    assert not should_retry(host, ("s", "g"), downloaded, SimpleNamespace(source=""))
    host._podcast_chapters_retried = ("s", "g")
    assert not should_retry(host, ("s", "g"), streamed, SimpleNamespace(source=""))
