"""The VS Code Signals sound pack: Visual Studio Code's accessibility signals.

An optional pack, never the default. Its sounds are Microsoft's, used under
the MIT licence and pinned to one commit of microsoft/vscode, so these tests
hold the pack to the record it ships with: every mapped file is there and is
the file that was recorded, every mapped event is one the apps can post, and
the notices name it.
"""

from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

from quill.core import third_party_notices as tpn
from quill.core.sound_events import SoundEvent
from quill.core.sound_pack import (
    BUNDLED_PREFIX,
    DEFAULT_SOUND_PACK_ID,
    available_sound_packs,
    load_sound_pack,
    resolve_sound_pack_path,
)

_PACK = Path(__file__).resolve().parents[3] / "quill" / "assets" / "sound_packs" / "vscode_signals"
_COMMIT = "891b2ac68d2e245f8f83d91c8a748801a81818fc"


def _manifest() -> dict:
    return json.loads((_PACK / "manifest.json").read_text(encoding="utf-8"))


def _sources() -> dict:
    return json.loads((_PACK / "SOURCES.json").read_text(encoding="utf-8"))


def test_the_pack_loads_with_every_mapped_event() -> None:
    pack = load_sound_pack(_PACK)
    assert pack.name == "VS Code Signals"
    assert pack.license == "MIT"
    assert "Sounds from Visual Studio Code, used under the MIT licence." in pack.description
    assert set(pack.events) == set(_manifest()["events"])


def test_the_pack_is_offered_but_is_not_the_default() -> None:
    packs = {pack.id: pack for pack in available_sound_packs()}
    assert "vscode_signals" in packs
    assert DEFAULT_SOUND_PACK_ID != "vscode_signals"
    assert packs["vscode_signals"].setting_value == f"{BUNDLED_PREFIX}vscode_signals"
    assert (
        resolve_sound_pack_path(f"{BUNDLED_PREFIX}vscode_signals") == packs["vscode_signals"].path
    )


def test_every_mapped_event_is_a_real_sound_event() -> None:
    known = {event.value for event in SoundEvent}
    unknown = sorted(set(_manifest()["events"]) - known)
    assert not unknown, f"VS Code Signals maps events no app posts: {unknown}"


def test_every_shipped_file_matches_its_recorded_hash() -> None:
    sources = _sources()
    assert sources["commit"] == _COMMIT
    recorded = {entry["file"]: entry for entry in sources["files"]}
    # All 32 upstream signals ship, mapped or not, each from the pinned commit.
    assert len(recorded) == 32
    for name, entry in recorded.items():
        assert entry["upstream"].startswith("src/vs/platform/accessibilitySignal/browser/media/")
        assert len(entry["upstream_sha256"]) == 64
        data = (_PACK / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], name
    for name in set(_manifest()["events"].values()):
        assert name in recorded, f"{name} is mapped but has no recorded source"


def test_every_shipped_file_is_a_wav_the_sound_scheme_window_can_read() -> None:
    for entry in _sources()["files"]:
        with wave.open(str(_PACK / entry["file"]), "rb") as handle:
            assert handle.getsampwidth() == 2
            assert handle.getnframes() / handle.getframerate() < 10.0


def test_the_mit_licence_ships_with_the_sounds() -> None:
    text = (_PACK / "LICENSE.txt").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    assert "Microsoft Corporation" in text
    digest = hashlib.sha256((_PACK / "LICENSE.txt").read_bytes()).hexdigest()
    assert digest == _sources()["license_sha256"]


def test_the_notices_name_the_pack() -> None:
    catalogue = tpn.load_catalogue()
    entry = next(item for item in catalogue.components if item.id == "vscode-signal-sounds")
    assert entry.licenses == ("MIT",)
    assert "Microsoft Corporation" in entry.copyright
    assert _COMMIT in entry.version
    assert "github.com/microsoft/vscode" in entry.homepage
    assert entry.ships_in("quill") and entry.ships_in("quilllite")
