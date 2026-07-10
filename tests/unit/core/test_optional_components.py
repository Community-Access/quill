from __future__ import annotations

import sys

import quill.core.optional_components as oc


def test_gather_includes_the_core_optional_components() -> None:
    ids = {c.component_id for c in oc.gather_optional_components()}
    assert {
        "whispercpp",
        "kokoro",
        "espeak",
        "audio_extras",
    }.issubset(ids)
    # DECtalk and MathCAT ship only Windows .dll's, so they are offered only on
    # Windows and hidden on macOS (offering them on macOS advertised a download
    # that could never work) -- see the win-only gate in gather_optional_components.
    if sys.platform.startswith("win"):
        assert {"dectalk", "mathcat"}.issubset(ids)
    else:
        assert "dectalk" not in ids
        assert "mathcat" not in ids
    # Vosk is a third engine choice inside the guided offline-speech picker
    # (the "whispercpp" row), not its own hub row -- no separate "vosk" entry.
    assert "vosk" not in ids
    assert "libmpv" not in ids
    assert "mp3" not in ids
    # FFmpeg is no longer its own row: it is folded into the single "audio_extras"
    # row (Audio: export, playback & chapters) and fetched on demand.
    assert "ffmpeg" not in ids


def test_dectalk_and_mathcat_are_hidden_on_macos(monkeypatch) -> None:
    """#46: MathCAT (like DECtalk) ships only a Windows .dll, so neither should
    be offered as a download on macOS -- offering them advertised a download
    that could never work there."""
    monkeypatch.setattr(oc.sys, "platform", "darwin")
    ids = {c.component_id for c in oc.gather_optional_components()}
    assert "mathcat" not in ids
    assert "dectalk" not in ids


def test_dectalk_and_mathcat_are_offered_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(oc.sys, "platform", "win32")
    ids = {c.component_id for c in oc.gather_optional_components()}
    assert "mathcat" in ids
    assert "dectalk" in ids


def test_status_reflects_detectors(monkeypatch) -> None:
    monkeypatch.setattr(oc, "_whisper_installed", lambda: True)
    monkeypatch.setattr(oc, "_kokoro_installed", lambda: False)
    monkeypatch.setattr(oc, "_espeak_installed", lambda: False)
    monkeypatch.setattr(oc, "_dectalk_installed", lambda: False)
    monkeypatch.setattr(oc, "_ffmpeg_installed", lambda: False)
    by_id = {c.component_id: c for c in oc.gather_optional_components()}
    assert by_id["whispercpp"].installed is True
    assert by_id["whispercpp"].status_label == "Installed"
    assert by_id["kokoro"].installed is False
    assert by_id["kokoro"].status_label == "Available to download"


def test_dictation_row_ready_requires_engine_and_model(monkeypatch) -> None:
    """The Dictation row's Download/Test state must reflect a real model, not
    just the whisper.cpp binary -- that was the whole point of #kokoro-focus's
    follow-up: the Test button used to look identical whether or not a model
    had ever been downloaded."""
    from quill.core.speech import guided_setup
    from quill.core.speech import transcribe as tr

    monkeypatch.setattr(oc, "_whisper_installed", lambda: True)

    def fake_options():
        return [
            guided_setup.OfflineSpeechEngineOption(
                engine_id="whispercpp",
                name="Whisper.cpp",
                tagline="",
                summary="",
                installed=True,
                install_supported=True,
                recommended=True,
            ),
        ]

    monkeypatch.setattr(guided_setup, "offline_speech_engine_options", fake_options)

    # Engine installed, no model yet: installed is True but not effective_ready.
    monkeypatch.setattr(tr, "provider_has_installed_model", lambda *a, **k: False)
    row = next(c for c in oc.gather_optional_components() if c.component_id == "whispercpp")
    assert row.installed is True
    assert row.effective_ready is False

    # Model downloaded too: now fully ready.
    monkeypatch.setattr(tr, "provider_has_installed_model", lambda *a, **k: True)
    row = next(c for c in oc.gather_optional_components() if c.component_id == "whispercpp")
    assert row.effective_ready is True


def test_effective_ready_defaults_to_installed_for_ordinary_components() -> None:
    installed = oc.OptionalComponent("x", "X", "d", oc.TOOL, True, "")
    missing = oc.OptionalComponent("y", "Y", "d", oc.TOOL, False, "")
    assert installed.effective_ready is True
    assert missing.effective_ready is False


def test_a_broken_detector_never_crashes_the_list(monkeypatch) -> None:
    def boom() -> bool:
        raise RuntimeError("detector exploded")

    monkeypatch.setattr(oc, "_whisper_installed", boom)
    comps = oc.gather_optional_components()  # must not raise
    whisper = next(c for c in comps if c.component_id == "whispercpp")
    assert whisper.installed is False


def test_dictionary_components_use_spellcheck_state(monkeypatch) -> None:
    from quill.core import spellcheck

    monkeypatch.setattr(spellcheck, "installed_languages", lambda: ["en_US", "fr_FR"])
    monkeypatch.setattr(spellcheck, "installable_languages", lambda: ["es_ES"])
    by_id = {c.component_id: c for c in oc.gather_optional_components()}
    # en_US is bundled in pyenchant, so it is never listed as a separate download.
    assert "spell-en_US" not in by_id
    assert by_id["spell-fr_FR"].installed is True
    assert by_id["spell-es_ES"].installed is False
    assert by_id["spell-fr_FR"].category == oc.DICTIONARY


def test_size_hints_present_for_large_components() -> None:
    by_id = {c.component_id: c for c in oc.gather_optional_components()}
    assert by_id["kokoro"].size_hint  # non-empty
    assert by_id["whispercpp"].size_hint


def test_libmpv_detector_checks_the_engine_pack(tmp_path, monkeypatch) -> None:
    import quill.core.speech.engine_install as ei

    monkeypatch.setattr(ei, "engine_packs_dir", lambda: tmp_path)
    assert oc._libmpv_installed() is False
    (tmp_path / "mpv").mkdir()
    (tmp_path / "mpv" / "libmpv-2.dll").write_bytes(b"MZ")
    assert oc._libmpv_installed() is True


def test_mathcat_detector_checks_the_engine_pack(tmp_path, monkeypatch) -> None:
    from quill.core.math import mathcat_engine

    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: tmp_path / "mathcat")
    assert oc._mathcat_installed() is False
    (tmp_path / "mathcat" / "Rules").mkdir(parents=True)
    (tmp_path / "mathcat" / "libmathcat_c.dll").write_bytes(b"MZ")
    assert oc._mathcat_installed() is True


def test_pdf_ocr_detector_reflects_module_availability(monkeypatch) -> None:
    import quill.core.pdf_ocr_install as pdf_ocr_install

    monkeypatch.setattr(pdf_ocr_install, "is_pdf_ocr_available", lambda: True)
    assert oc._pdf_ocr_installed() is True
    monkeypatch.setattr(pdf_ocr_install, "is_pdf_ocr_available", lambda: False)
    assert oc._pdf_ocr_installed() is False


def test_gather_includes_pdf_ocr() -> None:
    ids = {c.component_id for c in oc.gather_optional_components()}
    assert "pdf_ocr" in ids


def test_pdf_ocr_removable_path_is_its_engine_pack_dir(tmp_path, monkeypatch) -> None:
    import quill.core.pdf_ocr_install as pdf_ocr_install

    monkeypatch.setattr(pdf_ocr_install, "pdf_ocr_pack_dir", lambda: tmp_path / "pdf-ocr")
    assert oc._candidate_removable_path("pdf_ocr") == tmp_path / "pdf-ocr"


def test_gather_includes_piper_and_node() -> None:
    """Piper and Node.js are downloadable, so they must have a touch point in the
    dialog (they were missing before the catalog-completeness pass)."""
    ids = {c.component_id for c in oc.gather_optional_components()}
    assert "piper" in ids
    assert "node" in ids


def test_components_are_ordered_by_importance() -> None:
    comps = oc.gather_optional_components()
    ids = [c.component_id for c in comps]
    # Pandoc leads, PDF/Office extraction second, braille third (the
    # user-facing importance order).
    assert ids[0] == "pandoc"
    assert ids[1] == "pdf_ocr"
    assert ids[2] == "braille"
    # Spell-check dictionaries are grouped last.
    spell_positions = [i for i, cid in enumerate(ids) if cid.startswith("spell-")]
    non_spell_positions = [i for i, cid in enumerate(ids) if not cid.startswith("spell-")]
    if spell_positions and non_spell_positions:
        assert min(spell_positions) > max(non_spell_positions)


def test_every_component_row_states_a_size() -> None:
    # Every row (dictionaries included, which were blank before) shows a size.
    for c in oc.gather_optional_components():
        assert c.size_hint, f"{c.component_id} has no size_hint"


def test_describe_component_reports_state_and_size() -> None:
    installed = oc.OptionalComponent(
        "pandoc", "Pandoc", "Converts documents.", oc.TOOL, True, "~45 MB"
    )
    text = oc.describe_component(installed)
    assert "Pandoc" in text and "~45 MB" in text and "Installed" in text and "Remove" in text

    missing = oc.OptionalComponent(
        "kokoro", "Kokoro neural voices", "Neural voices.", oc.VOICES, False, "~120 MB"
    )
    text2 = oc.describe_component(missing)
    assert "Not installed" in text2 and "~120 MB" in text2 and "Download" in text2


def test_every_hosted_release_asset_is_catalogued() -> None:
    """A component QUILL can fetch from its own release must appear in the dialog,
    so a future downloadable component can't silently miss it. Spell-check assets
    map to the dynamic spell-<lang> rows and are checked separately. Vosk and
    libmpv are hosted assets but not their own hub rows: Vosk is a third engine
    choice inside the "whispercpp" row's guided picker, and libmpv is bundled
    into the "audio_extras" row with MP3 chapter markers."""
    from quill.core.release_assets import ASSETS

    ids = {c.component_id for c in oc.gather_optional_components()}
    folded_into = {"vosk": "whispercpp", "libmpv": "audio_extras"}
    for key in ASSETS:
        if key.startswith("spell-"):
            continue
        if key in folded_into:
            assert folded_into[key] in ids, f"{key!r}'s hub row {folded_into[key]!r} is missing"
            continue
        assert key in ids, f"release_assets component {key!r} is not in the download dialog"


def test_read_aloud_engine_for_component_maps_voice_engines() -> None:
    assert oc.read_aloud_engine_for_component("kokoro") == "kokoro"
    assert oc.read_aloud_engine_for_component("piper") == "piper"
    # Non-voice components have no engine to reset.
    assert oc.read_aloud_engine_for_component("pandoc") is None
    assert oc.read_aloud_engine_for_component("braille") is None


def test_removable_path_returns_none_for_uncatalogued_or_absent(tmp_path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    # Unknown component id -> never removable.
    assert oc.removable_path("nonsense") is None
    # Known components with nothing downloaded yet -> None (nothing to remove).
    assert oc.removable_path("dectalk") is None
    assert oc.removable_path("spell-fr_FR") is None
    assert oc.removable_path("kokoro") is None


def test_removable_path_and_remove_cover_dectalk(tmp_path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    dectalk = tmp_path / "speech" / "dectalk"
    dectalk.mkdir(parents=True)
    (dectalk / "say.exe").write_text("x", encoding="utf-8")

    assert oc.removable_path("dectalk") == dectalk
    assert oc.remove_component("dectalk") is True
    assert not dectalk.exists()


def test_remove_component_deletes_the_spell_dic_aff_pair(tmp_path, monkeypatch) -> None:
    hunspell = tmp_path / "spell" / "hunspell"
    hunspell.mkdir(parents=True)
    dic = hunspell / "fr_FR.dic"
    aff = hunspell / "fr_FR.aff"
    other = hunspell / "es_ES.dic"
    for f in (dic, aff, other):
        f.write_text("x", encoding="utf-8")
    # removable_path resolves the .dic; remove deletes the .dic/.aff pair only.
    monkeypatch.setattr(oc, "removable_path", lambda _cid: dic)

    assert oc.remove_component("spell-fr_FR") is True
    assert not dic.exists() and not aff.exists()
    assert other.exists()  # other languages untouched


def test_removable_path_and_remove_delete_the_app_data_copy(tmp_path, monkeypatch) -> None:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    models = tmp_path / "kokoro-models"
    models.mkdir()
    (models / "kokoro-v1.0.int8.onnx").write_text("model", encoding="utf-8")

    assert oc.removable_path("kokoro") == models
    assert oc.remove_component("kokoro") is True
    assert not models.exists()
    # Second remove is a no-op (nothing left).
    assert oc.remove_component("kokoro") is False


def test_removable_path_refuses_paths_outside_the_data_dir(tmp_path, monkeypatch) -> None:
    """Safety: never return a copy that lives outside the active data dir (a
    system tool or a bundled {app} copy)."""
    import quill.core.paths as paths

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside = tmp_path / "elsewhere" / "kokoro-models"
    outside.mkdir(parents=True)
    monkeypatch.setattr(paths, "app_data_dir", lambda: data_dir)
    monkeypatch.setattr(oc, "_candidate_removable_path", lambda _cid: outside)

    assert oc.removable_path("kokoro") is None  # outside data_dir -> refused


def test_fuzzy_match_tolerates_stt_variance() -> None:
    assert oc._fuzzy_match("the quick brown fox", "the quick brown fox") is True
    assert oc._fuzzy_match("the quick brown fox", "the quick fox jumped") is True  # >=40%
    assert oc._fuzzy_match("the quick brown fox", "") is False
    assert oc._fuzzy_match("the quick brown fox", "completely different words here") is False


def test_download_failure_report_text() -> None:
    text = oc.DownloadFailure(
        "kokoro", "pip exit 1", detail="No matching distribution", target=r"C:\data\kok"
    ).as_report_text()
    assert "Component: kokoro" in text
    assert "pip exit 1" in text
    assert "No matching distribution" in text
    assert r"C:\data\kok" in text


def test_verify_component_voice_defers_to_preview() -> None:
    result = oc.verify_component("kokoro")
    assert result.ok is True
    assert "Test" in result.summary  # UI plays the sample


def test_voice_pick_label_folds_in_accent_and_style() -> None:
    from quill.core.read_aloud import VoiceOption

    v = VoiceOption(
        id="en_GB-alan-medium", name="Alan", accent="British English", description="medium"
    )
    assert oc.voice_pick_label(v) == "Alan (British English, medium)"
    bare = VoiceOption(id="x", name="Solo")
    assert oc.voice_pick_label(bare) == "Solo"


def test_available_live_voices_filters_piper_to_downloaded(monkeypatch) -> None:
    from quill.core import read_aloud as ra
    from quill.core.read_aloud import VoiceOption

    monkeypatch.setattr(
        ra,
        "list_piper_catalog_voices",
        lambda: [
            VoiceOption(id="a", name="A", installed=True),
            VoiceOption(id="b", name="B", installed=False),
        ],
    )
    ids = [v.id for v in oc.available_live_voices("piper")]
    assert ids == ["a"]  # undownloaded "b" is filtered out


def test_available_live_voices_unknown_engine_is_empty() -> None:
    assert oc.available_live_voices("nope") == []


def test_verify_component_braille_reports_liblouis_version(monkeypatch) -> None:
    from quill.core import braille_pack

    monkeypatch.setattr(oc, "_braille_pack_installed", lambda: True)
    monkeypatch.setattr(braille_pack, "braille_pack_version", lambda: "3.30.0")
    result = oc.verify_component("braille")
    assert result.ok is True
    assert "LibLouis 3.30.0" in result.summary


def test_verify_component_braille_omits_version_when_unknown(monkeypatch) -> None:
    from quill.core import braille_pack

    monkeypatch.setattr(oc, "_braille_pack_installed", lambda: True)
    monkeypatch.setattr(braille_pack, "braille_pack_version", lambda: "unknown")
    result = oc.verify_component("braille")
    assert result.ok is True
    assert "LibLouis" not in result.summary
    assert "Installed and detected." in result.summary


def test_verify_component_stt_reports_what_it_heard(monkeypatch) -> None:
    import types

    from quill.core import read_aloud
    from quill.core.speech import transcribe as tr

    monkeypatch.setattr(tr, "provider_has_installed_model", lambda *a, **k: True)
    monkeypatch.setattr(read_aloud, "synthesize_to_file_with_sapi5", lambda *a, **k: None)
    captured: dict = {}

    def fake_transcribe(*_a, **k):
        captured.update(k)
        return types.SimpleNamespace(full_text="The quick brown fox jumps over the lazy dog.")

    monkeypatch.setattr(tr, "transcribe_audio_file", fake_transcribe)
    result = oc.verify_component("whispercpp")
    assert result.ok is True
    assert "heard" in result.summary.lower()
    # The self-test pins the engine under test, not "first available".
    assert captured.get("provider_id") == "whispercpp"


def test_verify_component_stt_closes_the_temp_file_descriptor(monkeypatch) -> None:
    """Regression: mkstemp's fd must be closed before SAPI can open the same path.

    ``_verify_stt`` used to discard mkstemp's returned fd
    (``Path(tempfile.mkstemp(...)[1])``), leaving the temp WAV open/locked from
    this process. SAPI's ``SpFileStream.Open()`` then failed on every real run
    with a generic COM error (E_INVALIDARG, "The parameter is incorrect")
    because the file was still exclusively held open -- reproduced directly
    against the real SAPI 5 backend on 2026-07-08.
    """
    import os
    import tempfile as tempfile_mod
    import types

    from quill.core import read_aloud
    from quill.core.speech import transcribe as tr

    monkeypatch.setattr(tr, "provider_has_installed_model", lambda *a, **k: True)
    monkeypatch.setattr(read_aloud, "synthesize_to_file_with_sapi5", lambda *a, **k: None)
    monkeypatch.setattr(
        tr,
        "transcribe_audio_file",
        lambda *a, **k: types.SimpleNamespace(
            full_text="The quick brown fox jumps over the lazy dog."
        ),
    )

    seen: dict = {}
    real_mkstemp = tempfile_mod.mkstemp

    def spying_mkstemp(*a, **k):
        fd, path = real_mkstemp(*a, **k)
        seen["fd"] = fd
        return fd, path

    monkeypatch.setattr(tempfile_mod, "mkstemp", spying_mkstemp)

    result = oc.verify_component("whispercpp")
    assert result.ok is True

    # Closing an already-closed fd raises OSError -- the only reliable, portable
    # way to prove _verify_stt itself closed it (not left it for GC to leak).
    try:
        os.close(seen["fd"])
    except OSError:
        pass
    else:
        raise AssertionError("_verify_stt left the mkstemp file descriptor open")


def test_verify_component_stt_targets_the_selected_engine(monkeypatch) -> None:
    """Faster Whisper is now a testable STT engine, and its own model presence
    (not any engine's) gates the test."""
    import types

    from quill.core import read_aloud
    from quill.core.speech import transcribe as tr

    seen: dict = {}

    def fake_gate(pid, *_a, **_k):
        seen["gate"] = pid
        return True

    monkeypatch.setattr(tr, "provider_has_installed_model", fake_gate)
    monkeypatch.setattr(read_aloud, "synthesize_to_file_with_sapi5", lambda *a, **k: None)
    monkeypatch.setattr(
        tr,
        "transcribe_audio_file",
        lambda *a, **k: types.SimpleNamespace(
            full_text="The quick brown fox jumps over the lazy dog."
        ),
    )
    result = oc.verify_component("fasterwhisper")
    assert result.ok is True
    assert seen.get("gate") == "fasterwhisper"


def test_verify_component_stt_flags_no_model(monkeypatch) -> None:
    from quill.core.speech import transcribe as tr

    monkeypatch.setattr(tr, "provider_has_installed_model", lambda *a, **k: False)
    result = oc.verify_component("vosk")
    assert result.ok is False
    assert "model" in result.summary.lower()
    # Expected "download a model" state, not a bug: the dialog routes to Manage
    # Speech Models via this remedy signal instead of offering a bug report.
    assert result.remedy == "models"
    assert not result.detail  # nothing to bug-report


def test_verify_component_tool_uses_availability(monkeypatch) -> None:
    from quill.core.speech import ffmpeg as ff

    monkeypatch.setattr(ff, "ffmpeg_available", lambda: True)
    assert oc.verify_component("ffmpeg").ok is True
    monkeypatch.setattr(ff, "ffmpeg_available", lambda: False)
    assert oc.verify_component("ffmpeg").ok is False


def test_voice_preview_phrase_prefers_app_root_file(tmp_path, monkeypatch) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "phrase.txt").write_text("Custom preview phrase.", encoding="utf-8")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    assert oc.voice_preview_phrase() == "Custom preview phrase."


def test_voice_preview_phrase_is_never_empty(monkeypatch) -> None:
    # With no app-root override, it reads the repo scripts/phrase.txt or the
    # built-in default -- either way a non-empty phrase.
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert oc.voice_preview_phrase().strip()


def test_piper_is_self_hosted_and_pinned() -> None:
    """Piper is published on QUILL's assets-v1 release, so its entry must be a
    real pinned asset (piper_install prefers it, falling back to rhasspy)."""
    from quill.core.release_assets import ASSETS, is_pinned

    assert "piper" in ASSETS
    assert is_pinned(ASSETS["piper"])
    assert ASSETS["piper"].sha256 == (
        "f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea"
    )


def test_manage_target_routes_stt_to_models_and_voices_to_voices() -> None:
    assert oc.manage_target("whispercpp") == "models"
    assert oc.manage_target("vosk") == "models"
    assert oc.manage_target("kokoro") == "voices"
    assert oc.manage_target("piper") == "voices"
    # Tools and dictionaries have no per-item manage dialog.
    assert oc.manage_target("pandoc") is None
    assert oc.manage_target("braille") is None
    assert oc.manage_target("spell-fr_FR") is None


def test_gather_includes_audio_extras() -> None:
    ids = {c.component_id for c in oc.gather_optional_components()}
    # mpv playback + MP3 chapter markers, bundled as one download from the hub.
    assert "audio_extras" in ids
    assert oc.manage_target("audio_extras") is None  # a tool, not a models/voices route


def test_audio_extras_installed_only_when_both_halves_present(monkeypatch) -> None:
    monkeypatch.setattr(oc, "_libmpv_installed", lambda: True)
    monkeypatch.setattr(oc, "_mp3_installed", lambda: False)
    assert oc._audio_extras_installed() is False
    monkeypatch.setattr(oc, "_mp3_installed", lambda: True)
    assert oc._audio_extras_installed() is True
