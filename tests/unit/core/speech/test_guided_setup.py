from __future__ import annotations

import quill.core.speech.guided_setup as gs


def test_offline_speech_engine_options_lists_both_recommended_first() -> None:
    opts = gs.offline_speech_engine_options()
    ids = [o.engine_id for o in opts]
    assert ids == ["whispercpp", "fasterwhisper", "vosk"]
    # whisper.cpp is the friendly default and always installable (release asset).
    whispercpp = opts[0]
    assert whispercpp.recommended is True
    assert whispercpp.install_supported is True
    # Every option carries a plain-language explanation for the picker.
    for opt in opts:
        assert opt.name
        assert opt.tagline  # short trade-off spoken in the radio label
        assert len(opt.summary) > 20


def test_engine_options_never_crash_on_detector_failure(monkeypatch) -> None:
    def boom() -> bool:
        raise RuntimeError("detector exploded")

    monkeypatch.setattr(gs, "_whispercpp_installed", boom)
    monkeypatch.setattr(gs, "_faster_whisper_installed", boom)
    monkeypatch.setattr(gs, "_vosk_installed", boom)
    opts = gs.offline_speech_engine_options()  # must not raise
    assert all(o.installed is False for o in opts)


def test_recommended_engine_prefers_an_installed_one_else_whispercpp(monkeypatch) -> None:
    # Nothing installed -> the friendly default.
    monkeypatch.setattr(gs, "_whispercpp_installed", lambda: False)
    monkeypatch.setattr(gs, "_faster_whisper_installed", lambda: False)
    monkeypatch.setattr(gs, "_vosk_installed", lambda: False)
    assert gs.recommended_engine_id() == "whispercpp"

    # Faster Whisper already installed -> keep the user on what they have.
    monkeypatch.setattr(gs, "_faster_whisper_installed", lambda: True)
    assert gs.recommended_engine_id() == "fasterwhisper"


def test_models_for_engine_lists_catalog_with_a_recommendation() -> None:
    cpp = gs.models_for_engine("whispercpp")
    fw = gs.models_for_engine("fasterwhisper")
    assert cpp and fw
    # Smallest first, and exactly one best-fit recommendation each.
    assert cpp[0].model_id == gs.default_model_id("whispercpp")
    assert sum(1 for m in cpp if m.recommended) == 1
    for m in cpp:
        assert m.display_name and m.size_text and m.summary
    # The two engines have distinct catalogs.
    assert {m.model_id for m in cpp} != {m.model_id for m in fw}


def test_default_model_is_the_smallest_for_a_fast_start() -> None:
    # "default to tiny so they're going immediately" -- the first (smallest) model.
    assert gs.default_model_id("whispercpp") == "tiny"


def test_vosk_is_a_third_engine_with_its_own_model_catalog() -> None:
    # Vosk is reached through this same guided flow, not a separate hub row.
    vosk = gs.models_for_engine("vosk")
    assert vosk
    assert vosk[0].model_id == gs.default_model_id("vosk")
    assert sum(1 for m in vosk if m.recommended) == 1
    cpp_ids = {m.model_id for m in gs.models_for_engine("whispercpp")}
    assert {m.model_id for m in vosk} != cpp_ids


def test_models_for_engine_never_crashes_on_detection_failure(monkeypatch) -> None:
    from quill.core.speech import service

    monkeypatch.setattr(
        service, "detect_total_ram_gb", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    models = gs.models_for_engine("whispercpp")  # must not raise
    assert models and sum(1 for m in models if m.recommended) == 1


def test_setup_status_step1_when_engine_not_installed() -> None:
    st = gs.dictation_setup_status(
        engine_name="Faster Whisper",
        engine_installed=False,
        has_installed_model=False,
        is_default=False,
    )
    assert st.stage == gs.STAGE_ENGINE
    assert st.step_number == 1
    assert "Faster Whisper" in st.headline and "1 of 3" in st.headline
    assert not st.can_test and not st.can_set_default


def test_setup_status_step1_flags_unsupported_install() -> None:
    st = gs.dictation_setup_status(
        engine_name="Faster Whisper",
        engine_installed=False,
        has_installed_model=False,
        is_default=False,
        engine_install_supported=False,
    )
    assert st.stage == gs.STAGE_ENGINE
    assert "another engine" in st.next_step.lower()


def test_setup_status_step2_when_engine_but_no_model() -> None:
    st = gs.dictation_setup_status(
        engine_name="Whisper",
        engine_installed=True,
        has_installed_model=False,
        is_default=False,
    )
    assert st.stage == gs.STAGE_MODEL
    assert st.step_number == 2
    assert not st.can_test  # no model yet
    assert not st.can_set_default


def test_setup_status_step3_ready_but_not_default_can_test_and_set() -> None:
    st = gs.dictation_setup_status(
        engine_name="Whisper",
        engine_installed=True,
        has_installed_model=True,
        is_default=False,
    )
    assert st.stage == gs.STAGE_READY
    assert st.can_test and st.can_set_default
    assert "Set as Default" in st.next_step


def test_setup_status_ready_and_default_can_test_but_not_reset_default() -> None:
    st = gs.dictation_setup_status(
        engine_name="Whisper",
        engine_installed=True,
        has_installed_model=True,
        is_default=True,
    )
    assert st.stage == gs.STAGE_READY
    assert st.is_default
    assert st.can_test and not st.can_set_default
    assert "default" in st.headline.lower()
