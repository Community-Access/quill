"""Tests for QSP manifest validation and pack loading.

Covers :mod:`quill.core.sound_pack` and :mod:`quill.core.sound_events`.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from quill.core.sound_events import SoundEvent
from quill.core.sound_pack import SoundPack, SoundPackError, load_sound_pack, validate_manifest

# Minimal WAV header (PCM, mono, 44100 Hz, 16-bit, 0 samples).
_EMPTY_WAV = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    b"\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00"
    b"data\x00\x00\x00\x00"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "format": "qsp",
        "version": "1",
        "name": "Test Pack",
        "events": {"abbreviation_expanded": "expand.wav"},
    }
    base.update(overrides)
    return base


def _make_zip(manifest: dict[str, object], wavs: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in (wavs or {}).items():
            zf.writestr(name, data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# SoundEvent enum
# ---------------------------------------------------------------------------


def test_sound_event_values_are_strings() -> None:
    assert SoundEvent.ABBREVIATION_EXPANDED == "abbreviation_expanded"
    assert isinstance(SoundEvent.DOCUMENT_SAVED, str)


def test_sound_event_str_roundtrip() -> None:
    for event in SoundEvent:
        assert SoundEvent(str(event)) is event


# ---------------------------------------------------------------------------
# validate_manifest - valid cases
# ---------------------------------------------------------------------------


def test_valid_minimal_manifest() -> None:
    assert validate_manifest(_valid_manifest()) == []


def test_valid_full_manifest() -> None:
    raw = _valid_manifest(
        author="A",
        description="D",
        license="CC0",
        events={
            "abbreviation_expanded": "expand.wav",
            "document_saved": "save.wav",
        },
    )
    assert validate_manifest(raw) == []


def test_valid_empty_events() -> None:
    assert validate_manifest(_valid_manifest(events={})) == []


# ---------------------------------------------------------------------------
# validate_manifest - required field errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["format", "version", "name", "events"])
def test_missing_required_field(field: str) -> None:
    raw = _valid_manifest()
    del raw[field]  # type: ignore[misc]
    errors = validate_manifest(raw)
    assert any(field in e for e in errors)


def test_wrong_format_value() -> None:
    errors = validate_manifest(_valid_manifest(format="other"))
    assert any("format" in e for e in errors)


def test_wrong_version_value() -> None:
    errors = validate_manifest(_valid_manifest(version="2"))
    assert any("version" in e for e in errors)


def test_name_too_long() -> None:
    errors = validate_manifest(_valid_manifest(name="x" * 81))
    assert any("name" in e for e in errors)


def test_unknown_top_level_key() -> None:
    raw = _valid_manifest()
    raw["extra"] = "oops"
    errors = validate_manifest(raw)
    assert any("extra" in e for e in errors)


def test_events_not_object() -> None:
    errors = validate_manifest(_valid_manifest(events=["not", "a", "dict"]))
    assert any("events" in e for e in errors)


def test_event_value_not_string() -> None:
    errors = validate_manifest(_valid_manifest(events={"abbreviation_expanded": 42}))
    assert errors


def test_path_traversal_rejected() -> None:
    errors = validate_manifest(_valid_manifest(events={"abbreviation_expanded": "../escape.wav"}))
    assert any(".." in e for e in errors)


def test_absolute_path_rejected() -> None:
    errors = validate_manifest(_valid_manifest(events={"abbreviation_expanded": "/etc/passwd"}))
    assert errors


def test_non_dict_manifest() -> None:
    errors = validate_manifest(["not", "a", "dict"])
    assert errors


# ---------------------------------------------------------------------------
# load_sound_pack - directory
# ---------------------------------------------------------------------------


def test_load_from_directory(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(_valid_manifest(events={"abbreviation_expanded": "expand.wav"}))
    )
    (tmp_path / "expand.wav").write_bytes(_EMPTY_WAV)

    pack = load_sound_pack(tmp_path)

    assert pack.name == "Test Pack"
    assert "abbreviation_expanded" in pack.events
    assert pack.events["abbreviation_expanded"] == _EMPTY_WAV


def test_load_from_directory_missing_wav_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(
        json.dumps(_valid_manifest(events={"abbreviation_expanded": "missing.wav"}))
    )

    pack = load_sound_pack(tmp_path)
    assert "abbreviation_expanded" not in pack.events


def test_load_from_directory_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(SoundPackError, match="missing"):
        load_sound_pack(tmp_path)


# ---------------------------------------------------------------------------
# load_sound_pack - ZIP
# ---------------------------------------------------------------------------


def test_load_from_zip(tmp_path: Path) -> None:
    manifest = _valid_manifest(
        author="Jeff",
        description="Test",
        license="CC0",
        events={"document_saved": "save.wav"},
    )
    zip_bytes = _make_zip(manifest, {"save.wav": _EMPTY_WAV})
    qsp = tmp_path / "test.qsp"
    qsp.write_bytes(zip_bytes)

    pack = load_sound_pack(qsp)

    assert pack.name == "Test Pack"
    assert pack.author == "Jeff"
    assert pack.license == "CC0"
    assert pack.events["document_saved"] == _EMPTY_WAV


def test_load_from_zip_missing_wav_is_skipped(tmp_path: Path) -> None:
    manifest = _valid_manifest(events={"document_saved": "save.wav"})
    zip_bytes = _make_zip(manifest, wavs={})
    qsp = tmp_path / "test.qsp"
    qsp.write_bytes(zip_bytes)

    pack = load_sound_pack(qsp)
    assert "document_saved" not in pack.events


def test_load_from_zip_multiple_events(tmp_path: Path) -> None:
    manifest = _valid_manifest(
        events={
            "abbreviation_expanded": "expand.wav",
            "document_saved": "save.wav",
            "error": "error.wav",
        }
    )
    wavs = {
        "expand.wav": _EMPTY_WAV,
        "save.wav": _EMPTY_WAV,
        "error.wav": _EMPTY_WAV,
    }
    qsp = tmp_path / "test.qsp"
    qsp.write_bytes(_make_zip(manifest, wavs))

    pack = load_sound_pack(qsp)
    assert len(pack.events) == 3


def test_load_bad_json_raises(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", "not json {{{")
    qsp = tmp_path / "bad.qsp"
    qsp.write_bytes(buf.getvalue())

    with pytest.raises(SoundPackError, match="not valid JSON"):
        load_sound_pack(qsp)


def test_load_invalid_manifest_raises(tmp_path: Path) -> None:
    bad = {"format": "wrong", "version": "1", "name": "X", "events": {}}
    qsp = tmp_path / "bad.qsp"
    qsp.write_bytes(_make_zip(bad))

    with pytest.raises(SoundPackError, match="invalid manifest"):
        load_sound_pack(qsp)


def test_load_not_a_zip_raises(tmp_path: Path) -> None:
    f = tmp_path / "garbage.qsp"
    f.write_bytes(b"this is not a zip")

    with pytest.raises(SoundPackError):
        load_sound_pack(f)


def test_load_nonexistent_path_raises(tmp_path: Path) -> None:
    with pytest.raises(SoundPackError, match="does not exist"):
        load_sound_pack(tmp_path / "nope.qsp")


# ---------------------------------------------------------------------------
# SoundPack dataclass
# ---------------------------------------------------------------------------


def test_sound_pack_defaults() -> None:
    pack = SoundPack(name="X", author="", description="", license="")
    assert pack.events == {}
