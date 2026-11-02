"""QUILL offers, mirrors, previews and bundles only the Piper voices it may share.

The 2026-11-01 licensing review read every MODEL_CARD of the 39 voices QUILL
used to mirror: 29 descend from research-only or non-commercial datasets (or
carry no licence at all), and one more could not be confirmed. Those 30 are
listed in ``scripts/data/restricted_piper_voices.txt`` so their release assets
can be removed; this pins that none of them creeps back into the catalogue,
the mirror table, the committed previews or the Offline Edition starter voice.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.speech import model_mirrors
from quill.core.voice_catalog import PIPER_VOICES

REPO = Path(__file__).resolve().parents[4]
RESTRICTED_LIST = REPO / "scripts" / "data" / "restricted_piper_voices.txt"
PREVIEWS = REPO / "quill" / "data" / "voice-previews" / "piper"

#: The voices trained from scratch, or from another clean voice, on
#: public-domain or permissive data.
CLEAN = {
    "en_GB-cori-high",
    "en_GB-cori-medium",
    "en_US-bryce-medium",
    "en_US-john-medium",
    "en_US-kristin-medium",
    "en_US-libritts-high",
    "en_US-ljspeech-high",
    "en_US-ljspeech-medium",
    "en_US-norman-medium",
}


def _restricted() -> set[str]:
    names = set()
    for line in RESTRICTED_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            assert line.startswith("piper-voice-") and line.endswith(".zip"), line
            names.add(line.removeprefix("piper-voice-").removesuffix(".zip"))
    return names


def test_the_restricted_list_names_thirty_voices_none_of_them_clean() -> None:
    restricted = _restricted()
    assert len(restricted) == 30
    assert not restricted & CLEAN
    assert "en_US-lessac-medium" in restricted


def test_the_catalogue_offers_only_clean_voices() -> None:
    assert {voice_id for voice_id, _label in PIPER_VOICES} == CLEAN


def test_no_restricted_voice_is_mirrored() -> None:
    mirrored = {
        key.removeprefix("piper:") for key in model_mirrors._MIRRORS if key.startswith("piper:")
    }
    assert mirrored == CLEAN
    assert not mirrored & _restricted()


def test_previews_exist_for_clean_voices_only() -> None:
    previews = {path.stem for path in PREVIEWS.glob("*.mp3")}
    assert previews == CLEAN


def test_the_offline_starter_voice_is_clean() -> None:
    from scripts.build_windows_distribution import DEFAULT_BUNDLED_PIPER_VOICES

    assert DEFAULT_BUNDLED_PIPER_VOICES == ("en_US-ljspeech-medium",)
    assert set(DEFAULT_BUNDLED_PIPER_VOICES) <= CLEAN
