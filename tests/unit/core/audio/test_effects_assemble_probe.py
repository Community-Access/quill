"""Effect recipes, Join/Split/Preview planning, ffprobe parsing, remembered choices."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core import converter_settings as cs
from quill.core.audio import assemble as asm
from quill.core.audio.convert import ConversionJob, ConversionSpec
from quill.core.audio.dsp import DspOptions, build_dsp_filters
from quill.core.audio.effect_recipes import (
    CUSTOM_RECIPE_ID,
    EFFECT_RECIPES,
    describe_custom,
    recipe_choices,
    recipe_filters,
)
from quill.core.audio.media_probe import Chapter, describe, format_duration, parse_probe_json


def test_every_recipe_but_none_does_something_and_ids_are_unique() -> None:
    ids = [recipe.id for recipe in EFFECT_RECIPES]
    assert len(ids) == len(set(ids)) and ids[0] == "none"
    for recipe in EFFECT_RECIPES[1:]:
        assert build_dsp_filters(recipe.dsp), recipe.id
    assert recipe_choices()[-1][0] == CUSTOM_RECIPE_ID


def test_new_effects_compose_in_a_stable_order() -> None:
    chain = build_dsp_filters(
        DspOptions(
            high_pass=True,
            remove_hum=True,
            noise_reduction=True,
            deesser=True,
            dialogue_boost=True,
            compressor=True,
            loudness="music",
            limiter=True,
        )
    )
    names = [link.split("=")[0] for link in chain]
    assert names == [
        "highpass",
        "bandreject",
        "afftdn",
        "deesser",
        "dialoguenhance",
        "acompressor",
        "loudnorm",
        "alimiter",
    ]
    assert "I=-14.0" in chain[-2]


def test_custom_recipe_reads_the_custom_options_and_describes_them() -> None:
    custom = DspOptions(bass_boost=True, gain_db=3.0)
    assert recipe_filters(CUSTOM_RECIPE_ID, custom) == build_dsp_filters(custom)
    assert describe_custom(custom) == "bass boost, gain +3 dB"
    assert describe_custom(DspOptions()) == "No effects"


def test_preview_starts_a_quarter_in_capped_at_thirty_seconds() -> None:
    assert asm.preview_start(10.0) == 0.0
    assert asm.preview_start(60.0) == 15.0
    assert asm.preview_start(3600.0) == 30.0
    assert asm.preview_start(60.0, clip_start=20.0) == 30.0


def test_preview_of_a_video_format_is_its_sound_as_that_format_encodes_it() -> None:
    spec = asm.preview_audio_spec(ConversionSpec(fmt="webm", filters=("volume=2",)), 12.0)
    assert spec.fmt == "opus" and spec.start_s == 12.0 and spec.end_s == 27.0
    assert spec.filters == ("volume=2",) and spec.extract_from_video


def test_render_preview_encodes_then_decodes(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class Done:
        returncode = 0
        stderr = ""

    def run(command: list[str]) -> object:
        calls.append(command)
        return Done()

    out = asm.render_preview(
        "ffmpeg",
        tmp_path / "a.flac",
        ConversionSpec(fmt="mp3"),
        tmp_path / "p.wav",
        original=False,
        run=run,
        duration_s=100.0,
    )
    assert out == tmp_path / "p.wav" and len(calls) == 2
    assert calls[0][calls[0].index("-ss") + 1] == "25"
    assert calls[1][-1] == str(tmp_path / "p.wav")


def test_join_command_splices_the_concat_demuxer_and_chapters(tmp_path: Path) -> None:
    argv = asm.build_join_command(
        "ffmpeg",
        tmp_path / "parts.txt",
        tmp_path / "ch.ffmeta",
        ConversionSpec(fmt="m4b", start_s=5.0),
        tmp_path / "book.m4b",
    )
    joined = " ".join(argv)
    assert "-f concat -safe 0 -i" in joined and "-map_chapters 1" in joined
    assert "-ss" not in argv  # keep-only-part never clips a Join
    assert argv[-1].endswith("book.m4b")


def test_concat_list_escapes_quotes_and_uses_forward_slashes() -> None:
    text = asm.build_concat_list([Path("C:/a b/it's.flac")])
    assert text == "file 'C:/a b/it'\\''s.flac'\n"


def test_chapter_titles_prefer_the_tag_then_tidy_the_file_name() -> None:
    assert asm.chapter_title_for(Path("01 - Intro.mp3"), {}) == "Intro"
    assert asm.chapter_title_for(Path("x.mp3"), {"title": "Real Title"}) == "Real Title"


def test_split_plans_one_named_clipped_job_per_chapter(tmp_path: Path) -> None:
    chapters = [Chapter("One: Start", 0.0, 10.0), Chapter("Two/Next?", 10.0, 25.5)]
    jobs = asm.plan_chapter_split(
        tmp_path / "book.m4b", chapters, tmp_path / "out", ConversionSpec(fmt="mp3")
    )
    assert [job.dest.name for job in jobs] == ["01 - One Start.mp3", "02 - Two Next.mp3"]
    assert (jobs[1].spec.start_s, jobs[1].spec.end_s) == (10.0, 25.5)
    assert jobs[1].spec.metadata is not None and jobs[1].spec.metadata.track == "2/2"
    assert isinstance(jobs[0], ConversionJob)


_PROBE = {
    "format": {
        "format_long_name": "Matroska",
        "duration": "3725.4",
        "size": "2048000",
        "bit_rate": "128000",
        "tags": {"TITLE": "Film"},
    },
    "streams": [
        {
            "codec_type": "video",
            "codec_long_name": "H.264",
            "width": 1280,
            "height": 720,
            "avg_frame_rate": "30000/1001",
        },
        {
            "codec_type": "audio",
            "codec_long_name": "AAC",
            "sample_rate": "48000",
            "channels": 6,
            "tags": {"language": "eng", "title": "Audio description"},
        },
        {"codec_type": "subtitle", "codec_name": "subrip", "tags": {"language": "fra"}},
        {"codec_type": "video", "codec_name": "png", "disposition": {"attached_pic": 1}},
    ],
    "chapters": [{"start_time": "0", "end_time": "60", "tags": {"title": "Opening"}}],
}


def test_probe_json_parses_streams_cover_and_chapters() -> None:
    info = parse_probe_json(Path("film.mkv"), json.dumps(_PROBE))
    assert info.duration_s == 3725.4 and len(info.video) == 1 and len(info.audio) == 1
    assert [s.kind for s in info.streams].count("cover") == 1
    assert info.chapters[0].title == "Opening" and info.tags["title"] == "Film"
    text = "\n".join(describe(info))
    assert "Length: 1 hour 2 minutes 5 seconds" in text
    assert "5.1 surround" in text and "Audio description" in text
    assert "Subtitle tracks: 1 (fra)" in text and "Cover art: yes" in text


def test_unreadable_file_is_described_in_words() -> None:
    lines = describe(parse_probe_json(Path("bad.mp3"), "not json"))
    assert "could not be read" in lines[-1]
    assert format_duration(0) == "0 seconds" and format_duration(61) == "1 minute 1 second"


def test_settings_round_trip_and_forgive_damage(tmp_path: Path) -> None:
    settings = cs.ConverterSettings(
        fmt="flac",
        effect="custom",
        start_s=2.5,
        custom_effects=DspOptions(noise_reduction=True, loudness="music"),
    )
    cs.save(settings, tmp_path)
    loaded = cs.load(tmp_path)
    assert loaded.fmt == "flac" and loaded.start_s == 2.5
    assert loaded.custom_effects == DspOptions(noise_reduction=True, loudness="music")
    (tmp_path / cs.FILE_NAME).write_text(
        '{"fmt": 3, "start_s": -1, "custom_effects": {"gain_db": "x"}}'
    )
    damaged = cs.load(tmp_path)
    assert (
        damaged.fmt == "mp3" and damaged.start_s == 0.0 and damaged.custom_effects == DspOptions()
    )
