"""Tests for the audio-converter presets (#1255 §7)."""

from __future__ import annotations

from quill.core.audio import presets
from quill.core.audio.convert import ALL_OUTPUT_FORMATS, Channels


def test_every_preset_targets_a_known_format() -> None:
    for preset in presets.BUILTIN_PRESETS:
        assert preset.spec.fmt in ALL_OUTPUT_FORMATS, preset.id


def test_preset_ids_are_unique_and_have_labels() -> None:
    ids = [p.id for p in presets.BUILTIN_PRESETS]
    assert len(ids) == len(set(ids))
    for preset in presets.BUILTIN_PRESETS:
        assert preset.name and len(preset.description) > 10


def test_preset_spec_resolves_known_and_defaults_unknown() -> None:
    assert presets.preset_spec("mp3_320").bitrate_kbps == 320
    # Unknown -> the default preset's spec (never raises).
    assert presets.preset_spec("nope") is presets.preset_by_id(presets.DEFAULT_PRESET_ID).spec


def test_default_preset_exists_and_is_plain() -> None:
    default = presets.preset_by_id(presets.DEFAULT_PRESET_ID)
    assert default is not None
    assert default.spec.channels is Channels.KEEP
    assert default.spec.bitrate_kbps is None  # "just convert" changes nothing but format


def test_voice_and_podcast_presets_are_mono() -> None:
    assert presets.preset_by_id("podcast").spec.channels is Channels.MONO
    assert presets.preset_by_id("voice_memo").spec.channels is Channels.MONO
    assert presets.preset_by_id("voice_memo").spec.sample_rate == 22050


def test_archival_is_lossless_flac_untouched() -> None:
    spec = presets.preset_by_id("archival_flac").spec
    assert spec.fmt == "flac"
    assert spec.channels is Channels.KEEP and spec.sample_rate is None


def test_preset_choices_pairs_id_and_spoken_label() -> None:
    choices = presets.preset_choices()
    assert len(choices) == len(presets.BUILTIN_PRESETS)
    ids = {pid for pid, _label in choices}
    assert "just_convert" in ids and "mp3_320" in ids
    for _pid, label in choices:
        assert "—" in label  # name — description, spoken on focus
