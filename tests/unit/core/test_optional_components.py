from __future__ import annotations

import quill.core.optional_components as oc
from quill.core.optional_components import gather_optional_components


def test_gather_includes_the_core_optional_components() -> None:
    ids = {c.component_id for c in gather_optional_components()}
    assert {"whispercpp", "kokoro", "espeak", "dectalk", "ffmpeg"}.issubset(ids)


def test_status_reflects_detectors(monkeypatch) -> None:
    monkeypatch.setattr(oc, "_whisper_installed", lambda: True)
    monkeypatch.setattr(oc, "_kokoro_installed", lambda: False)
    monkeypatch.setattr(oc, "_espeak_installed", lambda: False)
    monkeypatch.setattr(oc, "_dectalk_installed", lambda: False)
    monkeypatch.setattr(oc, "_ffmpeg_installed", lambda: False)
    by_id = {c.component_id: c for c in gather_optional_components()}
    assert by_id["whispercpp"].installed is True
    assert by_id["whispercpp"].status_label == "Installed"
    assert by_id["kokoro"].installed is False
    assert by_id["kokoro"].status_label == "Available to download"


def test_a_broken_detector_never_crashes_the_list(monkeypatch) -> None:
    def boom() -> bool:
        raise RuntimeError("detector exploded")

    monkeypatch.setattr(oc, "_whisper_installed", boom)
    comps = gather_optional_components()  # must not raise
    whisper = next(c for c in comps if c.component_id == "whispercpp")
    assert whisper.installed is False


def test_dictionary_components_use_spellcheck_state(monkeypatch) -> None:
    from quill.core import spellcheck

    monkeypatch.setattr(spellcheck, "installed_languages", lambda: ["en_US", "fr_FR"])
    monkeypatch.setattr(spellcheck, "installable_languages", lambda: ["es_ES"])
    by_id = {c.component_id: c for c in gather_optional_components()}
    # en_US is bundled in pyenchant, so it is never listed as a separate download.
    assert "spell-en_US" not in by_id
    assert by_id["spell-fr_FR"].installed is True
    assert by_id["spell-es_ES"].installed is False
    assert by_id["spell-fr_FR"].category == oc.DICTIONARY


def test_size_hints_present_for_large_components() -> None:
    by_id = {c.component_id: c for c in gather_optional_components()}
    assert by_id["kokoro"].size_hint  # non-empty
    assert by_id["whispercpp"].size_hint
