"""The wx-free half of 9.6: captions, media blocks, embeds, episodes, engines."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.speech.provider import TranscriptionSegment
from quill.core.wordpress import blocks, fences
from quill.core.wordpress import episode as ep
from quill.core.wordpress import listen_engines as le
from quill.core.wordpress import listening as ls

SRC = "https://radio.example/v.mp4"
VIDEO = (
    '<!-- wp:video {"id":12} -->\n<figure class="wp-block-video"><video controls '
    f'src="{SRC}"></video></figure>\n<!-- /wp:video -->'
)


def test_review_lines_round_trip_to_webvtt() -> None:
    cues = ls.cues_from_segments((
        TranscriptionSegment(0, 2.5, " Hi  there "),
        TranscriptionSegment(2.5, 3, "Bye", "Ann"),
    ))
    text = ls.review_text(cues)
    assert (
        text == "00:00:00.000 --> 00:00:02.500 Hi there\n00:00:02.500 --> 00:00:03.000 Ann: Bye\n"
    )
    vtt = ls.to_webvtt(ls.cues_from_review(text))
    assert vtt.startswith("WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHi there\n")


def test_short_times_are_accepted_and_arrows_in_words_are_defused() -> None:
    cues = ls.cues_from_review("0:01 --> 0:02.5 a --> b\n\n")
    assert cues == [ls.Cue(1.0, 2.5, "a --> b")]
    assert "a -> b" in ls.to_webvtt(cues)


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("no time\n", "Line 1 does not start with a time"),
        ("00:00:02.000 --> 00:00:01.000 x\n", "Line 1 ends before it starts"),
        ("00:00:01.000 --> 00:00:02.000\n", "Line 1 has a time but no words"),
        ("\n\n", "no captions left"),
    ],
)
def test_review_problems_name_the_line(text: str, words: str) -> None:
    with pytest.raises(ls.CaptionsError) as raised:
        ls.cues_from_review(text)
    assert words in str(raised.value)
    assert raised.value.code == "QUILL-WP-CAPTIONS-INVALID"


def test_text_without_segments_is_one_cue() -> None:
    assert ls.cues_from_segments((), "Just words", 7.0) == [ls.Cue(0.0, 7.0, "Just words")]
    assert ls.cues_from_segments(None, "") == []


def test_language_labels() -> None:
    assert ls.language_label("en-GB") == "English"
    assert ls.language_label(None) == "English"
    assert ls.language_label("xx") == "xx"


def test_a_track_is_added_to_markup_and_attributes_once() -> None:
    once = ls.add_track(VIDEO, "https://r/v.vtt", "English", "en")
    block = blocks.parse(once)[0]
    assert block.attrs["tracks"] == [
        {"src": "https://r/v.vtt", "label": "English", "kind": "captions", "srcLang": "en"}
    ]
    assert (
        '<track src="https://r/v.vtt" label="English" kind="captions" srclang="en"/></video>'
        in (once)
    )
    assert ls.add_track(once, "https://r/v.vtt", "English", "en") == once
    assert ls.add_track("<p>no video</p>", "x", "y", "z") == "<p>no video</p>"


def test_media_blocks_are_found_by_id_or_address_even_nested() -> None:
    group = (
        f"<!-- wp:group --><div>{VIDEO.replace('{"id":12}', '{"id":99}')}</div><!-- /wp:group -->"
    )
    span = ls.find_media_block(group, "core/video", 12, SRC)
    assert span is not None and group[span.start : span.end].startswith("<!-- wp:video")
    assert ls.find_media_block(VIDEO, "core/video", 12, "") is not None
    assert ls.find_media_block(VIDEO, "core/video", 5, "https://other") is None
    assert ls.find_media_island({"island-1": VIDEO}, "core/video", 12, "") == "island-1"
    assert ls.find_media_island({"island-1": VIDEO}, "core/audio", 12, "") == ""


def test_island_lines_and_tokens() -> None:
    text = "a\n::: block core/video video island-3\nb"
    span = ls.island_line(text, "island-3")
    assert span is not None and text[span.start : span.end].endswith("island-3")
    assert ls.island_line(text, "island-4") is None
    assert ls.new_island_token({"video-1": ""}, "video") == "video-2"
    assert ls.island_fence("core/embed", "embed-1", "https://x") == (
        "::: block core/embed https://x embed-1"
    )
    assert ls.island_fence("core/embed", "embed-1", "two words") == "::: block core/embed embed-1"


def test_an_island_line_with_a_label_still_round_trips_through_fences() -> None:
    markup = ls.video_block(12, SRC)
    result = fences.convert_markdown(ls.island_fence("core/video", "v-1", "video"), {"v-1": markup})
    assert result.problems == []
    assert result.html.strip() == markup


def test_new_media_blocks_parse_as_the_block_editor_would() -> None:
    video = blocks.parse(ls.video_block(3, SRC, track=("t.vtt", "English", "en")))[0]
    assert video.name == "core/video" and video.attrs["id"] == 3
    audio = blocks.parse(ls.audio_block(4, "a.mp3", "Listen & learn"))[0]
    assert audio.attrs == {"id": 4}
    assert "Listen &amp; learn</figcaption>" in audio.inner_html


def test_details_in_both_formats() -> None:
    md = ls.details_markdown('Say "hi"', "One.\n\nTwo.")
    assert md == "::: details \"Say 'hi'\"\n\nOne.\n\nTwo.\n\n::: end details"
    assert fences.convert_markdown(md).problems == []
    html = ls.details_html("Read", "One <b>.\n\nTwo.")
    assert "<summary>Read</summary>" in html and "One &lt;b&gt;." in html
    assert [b.name for b in blocks.parse(html)] == ["core/details"]


def test_transcript_paragraphs_group_plain_cues_by_five() -> None:
    segments = [TranscriptionSegment(i, i + 1, f"S{i}.") for i in range(7)]
    assert ls.transcript_paragraphs(segments, "") == "S0. S1. S2. S3. S4.\n\nS5. S6.\n"
    assert ls.transcript_paragraphs((), "") == ""


EMBED_MD = "::: embed https://youtu.be/a type=video provider=youtube"


def test_embeds_are_found_in_every_form() -> None:
    embed_html = fences.markdown_to_blocks(EMBED_MD).strip()
    captioned = ls.caption_embed(embed_html, "Title")
    md = f"{EMBED_MD}\n\n::: block core/embed island-1\n"
    found = ls.find_embeds(md, "markdown", {"island-1": captioned})
    assert [(e.url, e.where, e.captioned) for e in found] == [
        ("https://youtu.be/a", "fence", False),
        ("https://youtu.be/a", "island", True),
    ]
    in_html = ls.find_embeds(embed_html, "html", {})
    assert [(e.where, e.captioned) for e in in_html] == [("html", False)]
    assert blocks.parse(captioned)[0].name == "core/embed"
    assert '<figcaption class="wp-element-caption">Title</figcaption></figure>' in captioned


def test_oembed_asks_the_sites_proxy() -> None:
    asked: list[tuple[str, dict]] = []

    class Api:
        def get(self, route: str, **params: object) -> object:
            asked.append((route, params))
            return {"title": " A  talk ", "author_name": "Ann", "provider_name": "Vimeo"}

    info = ls.oembed(Api(), "https://vimeo.com/1")  # type: ignore[arg-type]
    assert asked == [("oembed/1.0/proxy", {"url": "https://vimeo.com/1"})]
    assert info == ls.OEmbedInfo("A talk", "Ann", "Vimeo")
    assert info.caption() == "A talk"


def test_listening_labels_and_fingerprints() -> None:
    assert ls.listening_label("post", 6 * 60_000) == "Listen to this post (6 minutes)"
    assert ls.listening_label("page", 50_000) == "Listen to this page (1 minute)"
    assert ls.listening_label("post", 0) == "Listen to this post"
    assert ls.fingerprint("a  b") == ls.fingerprint("a b")


def test_a_listening_block_is_marked_and_stripped() -> None:
    block = ls.listening_audio_block(9, "l.mp3", "Listen")
    assert blocks.parse(block)[0].attrs == {"id": 9, "className": ls.LISTEN_MARK}
    assert ls.strip_listening_block(block + "\n\n<p>x</p>", "html", {}) == "<p>x</p>"
    md = "::: block core/audio listen listen-1\n\nBody\n"
    assert ls.strip_listening_block(md, "markdown", {"listen-1": block}) == "Body\n"
    assert ls.strip_listening_block("Body", "markdown", {"x": "other"}) == "Body"


def test_an_episode_post_has_player_notes_chapters_and_transcript() -> None:
    episode = ep.Episode(
        title="E1",
        show_notes="Plain notes.",
        chapters=(ep.Chapter(3725, "Late"), ep.Chapter(5, "")),
        transcript="Hello.",
    )
    text, islands = ep.episode_post(episode, media_id=7, src="e.mp3")
    assert text.startswith("::: block core/audio player episode-player-1\n\nPlain notes.")
    assert "- 1:02:05 Late\n- 0:05 Untitled" in text
    result = fences.convert_markdown(text, islands)
    assert result.problems == []
    assert 'wp:audio {"id":7}' in result.html and "wp:details" in result.html
    bare, _ = ep.episode_post(ep.Episode(title="E2"), media_id=1, src="x")
    assert bare == "::: block core/audio player episode-player-1\n"


def test_a_document_page_links_its_original() -> None:
    page = ep.document_page("Body", file_name="plan.docx", src="u", size=2048)
    assert page == "[Download the original Word document, 2 KB](u)\n\nBody\n"
    assert ep.document_page("", file_name="a.pdf", src="u", size=0) == (
        "[Download the original PDF document](u)\n"
    )
    assert ep.title_from_file("annual_report-2026.pdf") == "Annual report 2026"
    assert ep.title_from_file("_.pdf") == "Untitled"


def test_the_read_aloud_settings_become_a_synthesis_request() -> None:
    kokoro = le.synthesis_spec(
        SimpleNamespace(
            read_aloud_engine="Kokoro",
            read_aloud_kokoro_voice="am_liam",
            read_aloud_kokoro_speed=1.2,
            read_aloud_rate=180,
        )
    )
    assert (kokoro.engine, kokoro.voice, kokoro.speed, kokoro.rate) == (
        "kokoro",
        "am_liam",
        1.2,
        180,
    )
    sapi = le.synthesis_spec(SimpleNamespace(read_aloud_engine="", read_aloud_voice="Zira"))
    assert (sapi.engine, sapi.voice, sapi.speed) == ("sapi5", "Zira", 1.0)


def test_default_engines_reach_quills_own_engines(monkeypatch, tmp_path) -> None:
    from quill.core.speech import transcribe as tr
    from quill.io import docconvert

    seen: dict[str, object] = {}
    monkeypatch.setattr(
        tr, "transcribe_audio_file", lambda path, **kw: seen.setdefault("tr", (path, kw))
    )
    monkeypatch.setattr(
        docconvert,
        "convert_document",
        lambda path: SimpleNamespace(text="T", offer_local_ocr=True, page_count=3),
    )
    engines = le.default_engines()
    engines.transcribe(tmp_path / "a.mp3")
    assert seen["tr"] == (tmp_path / "a.mp3", {"output_timestamps": True})
    assert engines.convert(tmp_path / "a.pdf") == le.Converted("T", True, 3)


def test_download_failures_are_a_plain_sentence(tmp_path) -> None:
    from urllib.error import URLError

    from quill.core.wordpress.api import WordPressApiError

    def opener(_request, timeout=None):
        raise URLError("offline")

    api = SimpleNamespace(_opener=opener, timeout=5, site_name="Community Radio")
    with pytest.raises(WordPressApiError) as raised:
        le.download(api, "https://r/x.mp4", tmp_path / "x.mp4")  # type: ignore[arg-type]
    assert raised.value.plain.startswith("QUILL could not download x.mp4 from Community Radio")
