"""Tests for the Audio Studio post-PR follow-up plumbing.

Three slices:

- **Keymap/palette/cross-link** — ``tools.speech_batch_export`` shows up
  in the keymap machinery (display-name registry, feature command map,
  default keymap, and all three keymap pack profiles).
- **MRU + remembered journey** — the new MRU lists (audio source
  folders, finished audiobooks) behave the same as the existing
  recent-files list: prepend, dedupe, honor the limit, and persist
  across reads.
- **Project profile v2** — ``SpeechProjectProfile`` round-trips
  ``book_credits`` and ``library_mode`` and tolerates v1 documents that
  lack the new fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.feature_command_map import COMMAND_FEATURE_MAP
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.keymap_packs import _PACK_LABELS
from quill.core.recent import (
    add_recent_audio_source_folder,
    add_recent_audiobook_file,
    clear_recent_audio_source_folders,
    clear_recent_audiobook_files,
    recent_audio_source_folders,
    recent_audiobook_files,
)
from quill.core.speech.project_profile import (
    PROFILE_VERSION,
    SpeechProjectProfile,
)

# ---------------------------------------------------------------- Item 4 -----


def test_speech_batch_export_has_display_name() -> None:
    assert _PACK_LABELS.get("tools.speech_batch_export") == "Audio Studio..."


def test_speech_export_audio_has_display_name() -> None:
    assert _PACK_LABELS.get("tools.speech_export_audio") == "Export to Speech Audio..."


def test_speech_export_translated_has_display_name() -> None:
    assert (
        _PACK_LABELS.get("tools.speech_export_translated") == "Export to Translated Speech Audio..."
    )


def test_speech_commands_feature_gated() -> None:
    # ``tools.speech_batch_export`` is the only one that needed a new feature
    # entry; the other two are pre-existing command ids that just gained a
    # display name. The feature gate must point at a real feature so the
    # command-palette filtering still works.
    feature = COMMAND_FEATURE_MAP.get("tools.speech_batch_export")
    assert feature is not None
    assert feature.startswith("core.")  # the new gate is core.read_aloud


def test_default_keymap_binds_speech_batch_export() -> None:
    binding = DEFAULT_KEYMAP.get("tools.speech_batch_export", "")
    assert binding, "speech_batch_export must have a default binding"


def test_keymap_pack_profiles_parse_and_include_batch_export() -> None:
    """Every keymap pack ships a (possibly empty) binding for the new command.

    The merger never produces a delta for a command that is missing from
    a profile. Empty string in profile_minimal is correct — the minimal
    pack has no Audio Studio entry by design.
    """
    pack_dir = Path("quill/core/keymap")
    profiles = ("profile_default.json", "profile_minimal.json", "profile_sr_friendly.json")
    seen: dict[str, str] = {}
    for name in profiles:
        path = pack_dir / name
        data = json.loads(path.read_text(encoding="utf-8"))
        bindings = data.get("bindings", {})
        assert "tools.speech_batch_export" in bindings, (
            f"{name} must declare tools.speech_batch_export (even if empty)"
        )
        seen[name] = bindings["tools.speech_batch_export"]
    # The default and sr_friendly profiles both bind it.
    assert seen["profile_default.json"]
    assert seen["profile_sr_friendly.json"]


# ---------------------------------------------------------------- Item 5 -----


def test_add_recent_audio_source_folder_prepends_and_dedupes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()

    add_recent_audio_source_folder(one, limit=10)
    add_recent_audio_source_folder(two, limit=10)
    items = add_recent_audio_source_folder(one, limit=10)

    assert items[0] == one.resolve()
    assert items[1] == two.resolve()
    assert len(items) == 2


def test_add_recent_audio_source_folder_honors_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    for index in range(5):
        d = tmp_path / f"d{index}"
        d.mkdir()
        add_recent_audio_source_folder(d, limit=3)
    assert len(recent_audio_source_folders()) == 3


def test_add_recent_audiobook_file_prepends_and_dedupes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.m4b"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")

    add_recent_audiobook_file(a, limit=10)
    add_recent_audiobook_file(b, limit=10)
    items = add_recent_audiobook_file(a, limit=10)

    assert items[0] == a.resolve()
    assert items[1] == b.resolve()
    assert len(items) == 2


def test_add_recent_audiobook_file_honors_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    for index in range(7):
        f = tmp_path / f"book{index}.mp3"
        f.write_text("x", encoding="utf-8")
        add_recent_audiobook_file(f, limit=4)
    assert len(recent_audiobook_files()) == 4


def test_clear_recent_audio_lists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    f = tmp_path / "a.mp3"
    f.write_text("x", encoding="utf-8")
    d = tmp_path / "src"
    d.mkdir()

    add_recent_audiobook_file(f)
    add_recent_audio_source_folder(d)
    clear_recent_audiobook_files()
    clear_recent_audio_source_folders()
    assert recent_audiobook_files() == []
    assert recent_audio_source_folders() == []


def test_mru_lists_use_separate_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The two new MRUs must not collide on disk or in the in-memory cache.

    The folders and audiobooks lists are different stores, so a write to
    one must not appear in the other and the JSON files must land under
    separate names.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    d = tmp_path / "src"
    d.mkdir()
    f = tmp_path / "book.mp3"
    f.write_text("x", encoding="utf-8")
    add_recent_audio_source_folder(d)
    add_recent_audiobook_file(f)
    files = sorted(p.name for p in tmp_path.iterdir() if p.suffix == ".json")
    assert "audio-studio-recent-source-folders.json" in files
    assert "audio-studio-recent-audiobooks.json" in files
    # Reading one list must not return entries from the other.
    assert recent_audio_source_folders() == [d.resolve()]
    assert recent_audiobook_files() == [f.resolve()]


# ---------------------------------------------------------------- Item 6 -----


def test_profile_version_bumped_to_two() -> None:
    # The new fields land under v2. from_dict accepts older files; a future
    # bump would land here too.
    assert PROFILE_VERSION == 2
    # The default ctor carries the new fields at the new version.
    assert SpeechProjectProfile().version == 2


def test_profile_round_trips_new_fields() -> None:
    profile = SpeechProjectProfile(book_credits=True, library_mode=True)
    raw = profile.to_dict()
    assert raw["book_credits"] is True
    assert raw["library_mode"] is True
    restored = SpeechProjectProfile.from_dict(raw)
    assert restored.book_credits is True
    assert restored.library_mode is True


def test_profile_from_dict_tolerates_v1_data() -> None:
    """An old v1 document (no top-level booleans) loads with both fields False.

    Pre-existing project folders must not break when the v2 schema is rolled
    out. The booleans default to False so the second run lands on the
    "skip credits / skip library mode" defaults — the same as a fresh project.
    The on-disk ``version`` stamp is preserved (round-trip fidelity); the
    dataclass defaults use PROFILE_VERSION.
    """
    v1 = {
        "version": 1,
        "synthesizer": {},
        "discovery": {},
        "output": {},
        "chapters": {},
        "normalization": {},
        "pronunciation": {},
        "metadata": {},
        "execution": {},
        "translation": {},
    }
    restored = SpeechProjectProfile.from_dict(v1)
    assert restored.version == 1  # on-disk version is preserved
    assert restored.book_credits is False
    assert restored.library_mode is False
    # Re-serialising preserves the data; the missing booleans round-trip
    # as False now (the writer always emits them under v2).
    out = restored.to_dict()
    assert out["version"] == 1
    assert out["book_credits"] is False
    assert out["library_mode"] is False
    again = SpeechProjectProfile.from_dict(out)
    assert again.book_credits is False
    assert again.library_mode is False


def test_profile_from_dict_handles_non_dict() -> None:
    """A corrupt or non-dict load returns the defaults, never raises."""
    assert SpeechProjectProfile.from_dict({}).book_credits is False  # type: ignore[arg-type]
    # from_dict is typed for dict but defensive at runtime; non-dict in
    # production means a bad file was written and we silently fall back.
    assert (
        SpeechProjectProfile.from_dict("not a dict").book_credits is False  # type: ignore[arg-type]
    )
