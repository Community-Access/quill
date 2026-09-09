"""The shared audio tag model: the table, the container, and the vendoring gate.

``quill/core/speech/audio_tags_core.py`` is vendored byte-identical into
podHarvest (``S:\\code\\pod``). These tests cover its pure parts and guard the
vendoring; the MP3/MP4 round trips live further down, behind ``mutagen``.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from quill.core.speech import audio_tags_core as core

MODULE = Path(core.__file__)
DIGEST_FILE = MODULE.with_suffix(".sha256")


class TestVendoring:
    """The shared module is copied, not imported. Something has to notice drift."""

    def test_the_shared_module_has_not_drifted(self) -> None:
        expected = DIGEST_FILE.read_text(encoding="utf-8").split()[0].strip()
        actual = hashlib.sha256(MODULE.read_bytes()).hexdigest()
        assert actual == expected, (
            "audio_tags_core.py has changed. Copy the new file to "
            "podharvest/audio_tags_core.py, update the digest in both repos, "
            "or QUILL and podHarvest have silently diverged."
        )

    def test_it_imports_nothing_from_either_host(self) -> None:
        """Byte-identity is only possible while it depends on neither package.

        Checks import statements, not mentions: the module's docstring names
        both repositories on purpose, and should.
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                root = name.split(".")[0]
                assert root not in {"quill", "podharvest"}, f"host import: {name}"

    def test_it_imports_mutagen_lazily(self) -> None:
        """podHarvest's CLI promise: importing this must not need mutagen."""
        for line in MODULE.read_text(encoding="utf-8").splitlines():
            if line.startswith(("import mutagen", "from mutagen")):
                pytest.fail(f"top-level mutagen import: {line!r}")


class TestFieldTable:
    def test_there_are_twenty_six_fields(self) -> None:
        assert len(core.TAG_FIELDS) == 26

    def test_keys_are_unique(self) -> None:
        keys = [f.key for f in core.TAG_FIELDS]
        assert len(keys) == len(set(keys))

    def test_id3_frames_are_unique(self) -> None:
        frames = [f.id3 for f in core.TAG_FIELDS]
        assert len(frames) == len(set(frames))

    def test_mp4_atoms_are_unique_where_they_exist(self) -> None:
        atoms = [f.mp4 for f in core.TAG_FIELDS if f.mp4]
        assert len(atoms) == len(set(atoms))

    def test_every_field_belongs_to_a_declared_group(self) -> None:
        declared = {key for key, _label in core.GROUPS}
        assert {f.group for f in core.TAG_FIELDS} <= declared

    def test_every_group_has_at_least_one_field(self) -> None:
        for group, _label in core.GROUPS:
            assert core.fields_in(group), f"{group} is an empty page"

    def test_every_field_declares_a_frame_and_explains_itself(self) -> None:
        for field in core.TAG_FIELDS:
            assert field.id3, f"{field.key} has no ID3 frame"
            assert field.help.endswith("."), f"{field.key} help is not a sentence"
            assert field.kind in {"text", "number", "pair", "multiline", "bool"}

    def test_mnemonics_are_unique_within_each_group(self) -> None:
        """Each group is its own notebook page, so each is its own namespace."""
        for group, _label in core.GROUPS:
            letters = [
                f.label[f.label.index("&") + 1].lower()
                for f in core.fields_in(group)
                if "&" in f.label
            ]
            assert len(letters) == len(set(letters)), f"duplicate mnemonic in {group}"

    def test_every_field_carries_a_mnemonic(self) -> None:
        for field in core.TAG_FIELDS:
            assert "&" in field.label, f"{field.key} has no mnemonic"

    def test_fields_in_returns_only_that_group(self) -> None:
        assert all(f.group == "sort" for f in core.fields_in("sort"))
        assert core.fields_in("nonexistent") == ()

    def test_field_for_finds_a_field_and_rejects_a_stranger(self) -> None:
        assert core.field_for("album").id3 == "TALB"
        with pytest.raises(KeyError):
            core.field_for("not_a_tag")


class TestAudioTags:
    def test_absent_tags_read_as_empty(self) -> None:
        assert core.AudioTags().get("album") == ""

    def test_values_are_stripped(self) -> None:
        tags = core.AudioTags()
        tags.set("album", "  My Book  ")
        assert tags.get("album") == "My Book"

    def test_setting_empty_clears_the_tag(self) -> None:
        tags = core.AudioTags()
        tags.set("album", "Something")
        tags.set("album", "   ")
        assert tags.get("album") == ""
        assert "album" not in tags.values

    def test_copy_is_independent(self) -> None:
        tags = core.AudioTags()
        tags.set("album", "First")
        tags.cover = core.CoverArt(data=b"abc", mime="image/png")
        clone = tags.copy()
        clone.set("album", "Second")
        assert clone.cover is not None
        clone.cover.description = "changed"
        assert tags.get("album") == "First"
        assert tags.cover is not None
        assert tags.cover.description == ""

    def test_an_unknown_key_is_rejected_both_ways(self) -> None:
        with pytest.raises(KeyError):
            core.AudioTags().set("not_a_tag", "x")
        with pytest.raises(KeyError):
            core.AudioTags().get("not_a_tag")


class TestTimeFormatting:
    """Editing needs milliseconds; a nudge of 100 ms must be visible."""

    def test_precise_format_always_shows_hours_and_milliseconds(self) -> None:
        assert core.format_time_precise(0) == "0:00:00.000"
        assert core.format_time_precise(9_500) == "0:00:09.500"
        assert core.format_time_precise(3_725_010) == "1:02:05.010"

    def test_negative_times_clamp_to_zero(self) -> None:
        assert core.format_time_precise(-5) == "0:00:00.000"

    def test_parse_accepts_the_shapes_a_person_types(self) -> None:
        assert core.parse_time("0:00:09.500") == 9_500
        assert core.parse_time("1:02:05.010") == 3_725_010
        assert core.parse_time("2:30") == 150_000
        assert core.parse_time("90") == 90_000
        assert core.parse_time("  9.5  ") == 9_500

    def test_parse_rejects_what_is_not_a_time(self) -> None:
        assert core.parse_time("") is None
        assert core.parse_time("banana") is None
        assert core.parse_time("1:2:3:4") is None

    def test_parse_round_trips_the_precise_format(self) -> None:
        for ms in (0, 1, 999, 9_500, 3_725_010):
            assert core.parse_time(core.format_time_precise(ms)) == ms


class TestExceptions:
    def test_every_error_is_an_audio_tag_error(self) -> None:
        """One base the hosts can catch, whatever went wrong underneath."""
        assert issubclass(core.TagReadError, core.AudioTagError)
        assert issubclass(core.TagWriteError, core.AudioTagError)
        assert issubclass(core.ChapterEditError, core.AudioTagError)

    def test_they_are_plain_exceptions(self) -> None:
        """QUILL retranslates these into CodedError at its adapter boundary."""
        assert core.AudioTagError.__mro__[1] is Exception


# --------------------------------------------------------------------- file round trips

mutagen = pytest.importorskip("mutagen")

_PNG_1X1 = bytes.fromhex(
    # A real 1x1 red PNG. The hex that used to sit here had a truncated
    # IDAT, so wx refused it and the cover-art tests popped an "Unknown
    # image data format" box -- which is how that modal was found.
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8cfc0f01f00050001ff89993d1d0000000049454e44ae426082"
)
_JPEG_HEAD = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture
def silent_mp3(tmp_path: Path) -> Path:
    """A minimal valid MP3 (silent frames) to tag in place."""
    path = tmp_path / "tagged.mp3"
    path.write_bytes((b"\xff\xfb\x90\x00" + b"\x00" * 413) * 4)
    return path


def _every_field_set() -> core.AudioTags:
    tags = core.AudioTags()
    for f in core.TAG_FIELDS:
        if f.kind in {"text", "multiline"}:
            tags.set(f.key, f"value for {f.key}")
    tags.set("year", "2026")
    tags.set("original_date", "1998")
    tags.set("bpm", "120")
    tags.set("track", "3/12")
    tags.set("disc", "1/2")
    tags.set("compilation", "1")
    return tags


class TestMp3RoundTrip:
    def test_every_field_survives_a_write(self, silent_mp3: Path) -> None:
        tags = _every_field_set()
        core.write_tags(silent_mp3, tags)
        back = core.read_tags(silent_mp3)
        for f in core.TAG_FIELDS:
            assert back.get(f.key) == tags.get(f.key), f"{f.key} did not round-trip"

    def test_an_untagged_file_reads_as_empty(self, silent_mp3: Path) -> None:
        assert core.read_tags(silent_mp3).values == {}

    def test_an_empty_value_deletes_the_frame(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "First")
        core.write_tags(silent_mp3, tags)
        assert core.read_tags(silent_mp3).get("album") == "First"
        tags.set("album", "")
        core.write_tags(silent_mp3, tags)
        assert core.read_tags(silent_mp3).get("album") == ""

    def test_lyrics_survive_whole_rather_than_by_first_character(self, silent_mp3: Path) -> None:
        """USLT stores a bare string; indexing it would hand back one letter."""
        tags = core.AudioTags()
        tags.set("lyrics", "The whole transcript, several words long.")
        core.write_tags(silent_mp3, tags)
        assert core.read_tags(silent_mp3).get("lyrics").startswith("The whole")

    def test_a_missing_file_is_refused_not_created(self, tmp_path: Path) -> None:
        with pytest.raises(core.TagReadError):
            core.read_tags(tmp_path / "nope.mp3")
        with pytest.raises(core.TagWriteError):
            core.write_tags(tmp_path / "nope.mp3", core.AudioTags())


class TestId3Version:
    def test_ordinary_tags_stay_at_2_3(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "Plain")
        assert core.preferred_id3_version(tags) == 3
        core.write_tags(silent_mp3, tags)
        assert silent_mp3.read_bytes()[3] == 3

    def test_a_sort_field_moves_the_file_to_2_4(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "Plain")
        tags.set("title_sort", "Plain, The")
        assert core.preferred_id3_version(tags) == 4
        core.write_tags(silent_mp3, tags)
        assert silent_mp3.read_bytes()[3] == 4


class TestCoverArt:
    def test_png_is_accepted(self, tmp_path: Path) -> None:
        path = tmp_path / "art.png"
        path.write_bytes(_PNG_1X1)
        cover = core.load_cover(path)
        assert cover.mime == "image/png"
        assert core.cover_extension(cover) == ".png"

    def test_the_bytes_are_sniffed_not_the_extension(self, tmp_path: Path) -> None:
        path = tmp_path / "actually_a_png.jpg"
        path.write_bytes(_PNG_1X1)
        assert core.load_cover(path).mime == "image/png"

    def test_jpeg_is_accepted(self, tmp_path: Path) -> None:
        path = tmp_path / "art.jpg"
        path.write_bytes(_JPEG_HEAD)
        assert core.load_cover(path).mime == "image/jpeg"

    def test_a_non_image_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_bytes(b"this is not a picture")
        with pytest.raises(core.TagReadError, match="JPEG or PNG"):
            core.load_cover(path)

    def test_an_oversized_image_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "huge.png"
        path.write_bytes(_PNG_1X1 + b"\x00" * core.MAX_COVER_BYTES)
        with pytest.raises(core.TagReadError, match="8 MB"):
            core.load_cover(path)

    def test_describe_names_the_format_and_size(self) -> None:
        assert core.describe_cover(None) == "No cover art."
        text = core.describe_cover(core.CoverArt(data=_PNG_1X1, mime="image/png"))
        assert "PNG" in text and "bytes" in text

    def test_art_round_trips_through_an_mp3(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.cover = core.CoverArt(data=_PNG_1X1, mime="image/png", description="Front")
        core.write_tags(silent_mp3, tags)
        back = core.read_tags(silent_mp3).cover
        assert back is not None
        assert back.data == _PNG_1X1
        assert back.mime == "image/png"
        assert back.description == "Front"

    def test_removing_art_clears_it(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.cover = core.CoverArt(data=_PNG_1X1, mime="image/png")
        core.write_tags(silent_mp3, tags)
        tags.cover = None
        core.write_tags(silent_mp3, tags)
        assert core.read_tags(silent_mp3).cover is None


class TestChapterFrames:
    def _two(self) -> list[core.Chapter]:
        return [
            core.Chapter(index=0, title="Opening", start_ms=0, end_ms=9_500),
            core.Chapter(index=1, title="The interview", start_ms=9_500, end_ms=30_000),
        ]

    def test_element_ids_follow_the_alignment_contract(self, silent_mp3: Path) -> None:
        """ch0, ch1, toc -- what ffmpeg writes, so files pass between the apps."""
        from mutagen.id3 import ID3

        core.write_mp3_chapters(silent_mp3, self._two())
        frames = ID3(str(silent_mp3))
        assert sorted(f.element_id for f in frames.getall("CHAP")) == ["ch0", "ch1"]
        assert [f.element_id for f in frames.getall("CTOC")] == ["toc"]

    def test_millisecond_precision_survives(self, silent_mp3: Path) -> None:
        core.write_mp3_chapters(silent_mp3, self._two())
        assert core.read_mp3_chapters(silent_mp3)[1].start_ms == 9_500

    def test_writing_twice_does_not_duplicate_them(self, silent_mp3: Path) -> None:
        core.write_mp3_chapters(silent_mp3, self._two())
        core.write_mp3_chapters(silent_mp3, self._two())
        assert len(core.read_mp3_chapters(silent_mp3)) == 2

    def test_tags_and_chapters_do_not_disturb_each_other(self, silent_mp3: Path) -> None:
        core.write_mp3_chapters(silent_mp3, self._two())
        tags = core.AudioTags()
        tags.set("album", "The Show")
        core.write_tags(silent_mp3, tags)
        assert [c.title for c in core.read_mp3_chapters(silent_mp3)] == [
            "Opening",
            "The interview",
        ]
        assert core.read_tags(silent_mp3).get("album") == "The Show"
        core.write_mp3_chapters(silent_mp3, self._two())
        assert core.read_tags(silent_mp3).get("album") == "The Show"


# ------------------------------------------------------------ chapter list operations


def _three() -> list[core.Chapter]:
    return [
        core.Chapter(index=0, title="One", start_ms=0, end_ms=10_000),
        core.Chapter(index=1, title="Two", start_ms=10_000, end_ms=20_000),
        core.Chapter(index=2, title="Three", start_ms=20_000, end_ms=30_000),
    ]


class TestAddChapter:
    def test_splits_the_chapter_holding_the_point(self) -> None:
        result = core.add_chapter(_three(), 15_000, title="Middle")
        assert [c.title for c in result] == ["One", "Two", "Middle", "Three"]
        assert result[2].start_ms == 15_000
        assert result[1].end_ms == 15_000
        assert [c.index for c in result] == [0, 1, 2, 3]

    def test_appends_at_or_past_the_end(self) -> None:
        """Nothing to split there, which is the case split_chapter refuses."""
        result = core.add_chapter(_three(), 30_000, title="Outro")
        assert [c.title for c in result] == ["One", "Two", "Three", "Outro"]
        assert result[-1].start_ms == 30_000 == result[-1].end_ms

    def test_refuses_a_sliver(self) -> None:
        with pytest.raises(core.ChapterEditError, match="too close"):
            core.add_chapter(_three(), 10_500, min_part_ms=1000)

    def test_refuses_a_negative_time(self) -> None:
        with pytest.raises(core.ChapterEditError, match="before the beginning"):
            core.add_chapter(_three(), -1)

    def test_refuses_an_empty_list(self) -> None:
        with pytest.raises(core.ChapterEditError, match="no chapters"):
            core.add_chapter([], 1_000)


class TestDeleteChapter:
    def test_first_pulls_the_next_start_to_zero(self) -> None:
        result = core.delete_chapter(_three(), 0)
        assert [c.title for c in result] == ["Two", "Three"]
        assert result[0].start_ms == 0
        assert result[0].end_ms == 20_000

    def test_middle_extends_the_previous(self) -> None:
        result = core.delete_chapter(_three(), 1)
        assert [c.title for c in result] == ["One", "Three"]
        assert result[0].end_ms == 20_000

    def test_last_extends_the_previous(self) -> None:
        result = core.delete_chapter(_three(), 2)
        assert [c.title for c in result] == ["One", "Two"]
        assert result[-1].end_ms == 30_000

    def test_the_only_chapter_cannot_go(self) -> None:
        one = [core.Chapter(index=0, title="All", start_ms=0, end_ms=10_000)]
        with pytest.raises(core.ChapterEditError, match="only chapter"):
            core.delete_chapter(one, 0)

    def test_out_of_range_is_refused(self) -> None:
        with pytest.raises(core.ChapterEditError, match="No chapter"):
            core.delete_chapter(_three(), 9)

    def test_the_timeline_stays_covered(self) -> None:
        for index in range(3):
            result = core.delete_chapter(_three(), index)
            assert result[0].start_ms == 0
            assert result[-1].end_ms == 30_000
            for a, b in zip(result, result[1:], strict=False):
                assert a.end_ms == b.start_ms


class TestSetChapterBounds:
    def test_moves_both_edges_and_the_neighbours(self) -> None:
        result = core.set_chapter_bounds(_three(), 1, 8_000, 22_000)
        assert result[0].end_ms == 8_000
        assert result[1].start_ms == 8_000
        assert result[1].end_ms == 22_000
        assert result[2].start_ms == 22_000

    def test_rejects_an_inverted_range(self) -> None:
        with pytest.raises(core.ChapterEditError, match="before its end"):
            core.set_chapter_bounds(_three(), 1, 20_000, 10_000)

    def test_rejects_swallowing_a_neighbour(self) -> None:
        with pytest.raises(core.ChapterEditError, match="between"):
            core.set_chapter_bounds(_three(), 1, 100, 29_900)

    def test_the_first_start_and_last_end_stay_pinned(self) -> None:
        result = core.set_chapter_bounds(_three(), 0, 5_000, 12_000)
        assert result[0].start_ms == 0
        assert result[-1].end_ms == 30_000


class TestNudge:
    def test_the_steps_are_the_ones_the_contract_names(self) -> None:
        assert core.NUDGE_STEPS_MS == (100, 250, 500, 1000, 2000, 5000, 10_000)

    def test_moves_the_start_and_the_previous_end_together(self) -> None:
        result, applied = core.nudge_chapter_start(_three(), 1, -500)
        assert applied == -500
        assert result[1].start_ms == 9_500
        assert result[0].end_ms == 9_500

    def test_forward_moves_the_boundary_later(self) -> None:
        result, applied = core.nudge_chapter_start(_three(), 1, 2_000)
        assert applied == 2_000
        assert result[1].start_ms == 12_000

    def test_clamps_at_the_previous_chapter_instead_of_raising(self) -> None:
        result, applied = core.nudge_chapter_start(_three(), 1, -60_000)
        assert applied == -9_500
        assert result[1].start_ms == 500

    def test_clamps_at_this_chapters_own_end(self) -> None:
        result, applied = core.nudge_chapter_start(_three(), 1, 60_000)
        assert applied == 9_500
        assert result[1].start_ms == 19_500

    def test_a_marker_at_the_wall_reports_zero(self) -> None:
        pinned = [
            core.Chapter(index=0, title="One", start_ms=0, end_ms=500),
            core.Chapter(index=1, title="Two", start_ms=500, end_ms=1_000),
        ]
        result, applied = core.nudge_chapter_start(pinned, 1, -1_000)
        assert applied == 0
        assert result[1].start_ms == 500

    def test_the_first_chapter_is_pinned_to_the_beginning(self) -> None:
        with pytest.raises(core.ChapterEditError, match="beginning"):
            core.nudge_chapter_start(_three(), 0, 500)

    def test_an_unselected_index_is_refused(self) -> None:
        with pytest.raises(core.ChapterEditError, match="No chapter"):
            core.nudge_chapter_start(_three(), 9, 500)


# ------------------------------------------------------------------- mp4 round trips


@pytest.fixture
def empty_m4a(tmp_path: Path) -> Path:
    """A real, minimal M4A built by ffmpeg; skipped when ffmpeg is absent."""
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")
    path = tmp_path / "book.m4a"
    args = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        "1",
        "-c:a",
        "aac",
        "-y",
        str(path),
    ]
    if run_subprocess_safely(args, timeout_seconds=180.0).returncode != 0:
        pytest.skip("ffmpeg could not build the fixture")
    return path


class TestMp4RoundTrip:
    def test_mapped_fields_survive_a_write(self, empty_m4a: Path) -> None:
        tags = core.AudioTags()
        for f in core.TAG_FIELDS:
            if f.mp4 and f.kind in {"text", "multiline"}:
                tags.set(f.key, f"value for {f.key}")
        tags.set("year", "2026")
        tags.set("track", "3/12")
        tags.set("disc", "1/2")
        tags.set("bpm", "120")
        tags.set("compilation", "1")
        core.write_tags(empty_m4a, tags)
        back = core.read_tags(empty_m4a)
        for f in core.TAG_FIELDS:
            if f.mp4:
                assert back.get(f.key) == tags.get(f.key), f"{f.key} did not round-trip"

    def test_cover_art_survives(self, empty_m4a: Path) -> None:
        tags = core.AudioTags()
        tags.cover = core.CoverArt(data=_PNG_1X1, mime="image/png")
        core.write_tags(empty_m4a, tags)
        back = core.read_tags(empty_m4a).cover
        assert back is not None
        assert back.mime == "image/png"
        assert back.data == _PNG_1X1

    def test_fields_with_no_atom_are_skipped_not_guessed(self, empty_m4a: Path) -> None:
        unmapped = [f.key for f in core.TAG_FIELDS if not f.mp4]
        tags = core.AudioTags()
        for key in unmapped:
            tags.set(key, "ignored")
        tags.set("album", "Still Written")
        core.write_tags(empty_m4a, tags)
        back = core.read_tags(empty_m4a)
        assert back.get("album") == "Still Written"
        for key in unmapped:
            assert back.get(key) == ""

    def test_an_empty_value_removes_the_atom(self, empty_m4a: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "First")
        core.write_tags(empty_m4a, tags)
        tags.set("album", "")
        core.write_tags(empty_m4a, tags)
        assert core.read_tags(empty_m4a).get("album") == ""


# ---------------------------------------------------------------- the QUILL adapter


class TestAdapter:
    """The thin layer that cannot be shared: coded errors and the bridge."""

    def test_the_errors_are_coded(self) -> None:
        from quill.core.error_codes import CodedError
        from quill.core.speech import audio_tags
        from quill.core.speech.chapters import ChapterEditError

        for cls, code in (
            (audio_tags.TagReadError, "QUILL-SPEECH-TAG-READ"),
            (audio_tags.TagWriteError, "QUILL-SPEECH-TAG-WRITE"),
            (ChapterEditError, "QUILL-SPEECH-CHAPTER-EDIT"),
        ):
            assert issubclass(cls, CodedError)
            assert cls.code == code

    def test_a_shared_error_arrives_coded(self, tmp_path: Path) -> None:
        """The shared module raises plain; callers must see the coded twin."""
        from quill.core.speech import audio_tags

        with pytest.raises(audio_tags.TagReadError) as caught:
            audio_tags.read_tags(tmp_path / "gone.mp3")
        assert "QUILL-SPEECH-TAG-READ" in str(caught.value)

    def test_a_chapter_error_arrives_coded(self) -> None:
        from quill.core.speech.chapters import ChapterEditError, delete_chapter

        one = [core.Chapter(index=0, title="All", start_ms=0, end_ms=10_000)]
        with pytest.raises(ChapterEditError) as caught:
            delete_chapter(one, 0)
        assert "QUILL-SPEECH-CHAPTER-EDIT" in str(caught.value)
        assert "only chapter" in str(caught.value)

    def test_a_bad_cover_arrives_coded(self, tmp_path: Path) -> None:
        from quill.core.speech import audio_tags

        path = tmp_path / "notes.txt"
        path.write_bytes(b"not a picture")
        with pytest.raises(audio_tags.TagReadError, match="JPEG or PNG"):
            audio_tags.load_cover(path)

    def test_to_audio_metadata_maps_the_seven_core_fields(self) -> None:
        from quill.core.speech.audio_tags import to_audio_metadata

        tags = core.AudioTags()
        tags.set("title", "A Title")
        tags.set("artist", "Jane Doe")
        tags.set("album", "The Book")
        tags.set("album_artist", "Sam Reader")
        tags.set("genre", "Audiobook")
        tags.set("year", "2026")
        tags.set("track", "3/12")
        tags.set("comment", "Hello")
        meta = to_audio_metadata(tags)
        assert meta.title == "A Title"
        assert meta.artist == "Jane Doe"
        assert meta.album == "The Book"
        assert meta.album_artist == "Sam Reader"
        assert meta.genre == "Audiobook"
        assert meta.year == "2026"
        assert meta.track == "3/12"
        assert meta.comment == "Hello"

    def test_merge_overlays_without_losing_the_other_fields(self) -> None:
        from quill.core.speech.audio_tags import merge_audio_metadata
        from quill.core.speech.ffmpeg import AudioMetadata

        tags = core.AudioTags()
        tags.set("publisher", "Example Press")
        tags.set("album", "Old Title")
        merged = merge_audio_metadata(tags, AudioMetadata(album="New Title"))
        assert merged.get("album") == "New Title"
        assert merged.get("publisher") == "Example Press"

    def test_merge_does_not_mutate_its_input(self) -> None:
        from quill.core.speech.audio_tags import merge_audio_metadata
        from quill.core.speech.ffmpeg import AudioMetadata

        tags = core.AudioTags()
        tags.set("album", "Old Title")
        merge_audio_metadata(tags, AudioMetadata(album="New Title"))
        assert tags.get("album") == "Old Title"

    def test_chapters_still_exports_what_eleven_modules_import(self) -> None:
        """The re-export is what keeps every existing caller working."""
        from quill.core.speech import chapters as chapters_mod

        for name in (
            "Chapter",
            "ChapterSection",
            "ChapterSettings",
            "ChapterEditError",
            "compute_chapters",
            "write_mp3_chapters",
            "read_mp3_chapters",
            "merge_chapter",
            "split_chapter",
            "set_chapter_start",
            "clamp_chapters",
        ):
            assert hasattr(chapters_mod, name), f"chapters lost {name}"


class TestChapterWriteFollowsTheFilesVersion:
    """Found by running the two apps against one file, not by reading the code.

    Saving an ID3 block is all-or-nothing. Writing chapters at a fixed 2.3
    after tags had been written at 2.4 quietly demoted the whole block, which
    is exactly the ordering bug a caller should not have to think about.
    """

    def _two(self) -> list[core.Chapter]:
        return [
            core.Chapter(index=0, title="Opening", start_ms=0, end_ms=9_500),
            core.Chapter(index=1, title="The interview", start_ms=9_500, end_ms=30_000),
        ]

    def test_chapters_after_sort_fields_keep_the_file_at_2_4(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "The Book")
        tags.set("title_sort", "Book, The")
        core.write_tags(silent_mp3, tags)
        core.write_mp3_chapters(silent_mp3, self._two())
        assert silent_mp3.read_bytes()[3] == 4
        assert core.read_tags(silent_mp3).get("title_sort") == "Book, The"

    def test_chapters_on_a_plain_file_stay_at_2_3(self, silent_mp3: Path) -> None:
        tags = core.AudioTags()
        tags.set("album", "The Book")
        core.write_tags(silent_mp3, tags)
        core.write_mp3_chapters(silent_mp3, self._two())
        assert silent_mp3.read_bytes()[3] == 3

    def test_an_explicit_version_still_wins(self, silent_mp3: Path) -> None:
        core.write_mp3_chapters(silent_mp3, self._two(), v2_version=4)
        assert silent_mp3.read_bytes()[3] == 4
