from __future__ import annotations

import quill.core.speech.guided_setup as gs


def test_offline_speech_engine_options_lists_both_recommended_first() -> None:
    opts = gs.offline_speech_engine_options()
    ids = [o.engine_id for o in opts]
    # whisper.cpp leads (the friendly, zero-big-download default). The shared
    # speech models sit second: they hold Parakeet, the engine dictation itself
    # prefers once installed (dict.md D-26 replaced the separate Parakeet and
    # Nemotron engines with them). Vosk is not offered: it is the podcast
    # chapter engine only (2026-10-13).
    assert ids == ["whispercpp", "sherpa", "fasterwhisper"]
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
    monkeypatch.setattr(gs, "_shared_installed", boom)
    opts = gs.offline_speech_engine_options()  # must not raise
    assert all(o.installed is False for o in opts)


def test_recommended_engine_prefers_an_installed_one_else_whispercpp(monkeypatch) -> None:
    # Nothing installed -> the friendly default.
    monkeypatch.setattr(gs, "_whispercpp_installed", lambda: False)
    monkeypatch.setattr(gs, "_faster_whisper_installed", lambda: False)
    monkeypatch.setattr(gs, "_shared_installed", lambda: False)
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


def test_guided_models_carry_their_tier_and_the_reason(monkeypatch) -> None:
    """D-22: the guided picker names each model's tier and says why the
    recommended one suits this computer."""
    from quill.core.speech import service

    monkeypatch.setattr(service, "detect_total_ram_gb", lambda: 8.0)
    monkeypatch.setattr(service, "detect_has_gpu", lambda: False)
    models = gs.models_for_engine("whispercpp")
    assert all(m.tier in {"Lightweight", "Balanced", "High accuracy"} for m in models)
    best = [m for m in models if m.recommended]
    assert len(best) == 1 and "8.0 GB RAM" in best[0].reason
    assert all(not m.reason for m in models if not m.recommended)


def test_default_model_is_the_smallest_for_a_fast_start() -> None:
    # "default to tiny so they're going immediately" -- the first (smallest) model.
    assert gs.default_model_id("whispercpp") == "tiny"


def test_vosk_is_not_a_guided_engine() -> None:
    # Vosk left dictation on 2026-10-13; its catalog stays for the chapter engine,
    # but the guided picker neither lists it nor maps its models.
    assert "vosk" not in [o.engine_id for o in gs.offline_speech_engine_options()]
    cpp_ids = {m.model_id for m in gs.models_for_engine("whispercpp")}
    assert {m.model_id for m in gs.models_for_engine("vosk")} == cpp_ids


def test_there_is_no_separate_nemotron_or_parakeet_engine_any_more() -> None:
    """dict.md D-26: one shared engine for every sherpa-onnx model."""
    ids = [o.engine_id for o in gs.offline_speech_engine_options()]
    assert "nemotron" not in ids and "parakeet" not in ids


def test_models_for_the_shared_engine_are_the_family_catalogue(monkeypatch) -> None:
    from quill.core.windows_dictation import model_advice
    from quill.core.windows_dictation.model_catalog import catalogue_ids
    from quill.core.windows_dictation.speed_check import SpeedCheck

    advice = model_advice.recommend(SpeedCheck(tiny=0.05, cores=4, memory_gb=8.0))
    monkeypatch.setattr(model_advice, "for_this_computer", lambda *a, **k: advice)
    models = gs.models_for_engine("sherpa")
    assert [m.model_id for m in models] == list(catalogue_ids())
    best = [m for m in models if m.recommended]
    assert len(best) == 1 and best[0].reason == advice.sentence
    assert all(m.tier in {"Lightweight", "Balanced", "High accuracy"} for m in models)


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


def test_the_shared_engine_says_what_parakeet_does() -> None:
    """The shared engine's summary names Parakeet's silence-safety, the reason
    dictation prefers it."""
    opts = gs.offline_speech_engine_options()
    shared = next(o for o in opts if o.engine_id == "sherpa")
    assert "never invents text from silence" in shared.summary
    assert "never downloaded twice" in shared.summary
    assert shared.tagline
