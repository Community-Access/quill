"""D-22: one model recommended for this computer, with reasons, and tier labels.

The recommendation is pure: a speed check (Moonshine tiny's time here, cores,
memory, graphics card), a language and a priority in; one model and its
reasons out. These tests pin it over a table of machine profiles, so a change
to the rule shows up as a changed row here rather than as a surprise on
somebody's computer.
"""

from __future__ import annotations

import pytest

from quill.core.speech.service import recommendation_reason
from quill.core.windows_dictation import model_advice, speed_check
from quill.core.windows_dictation.model_advice import (
    ESTIMATE_NOTE,
    PRIORITIES,
    engine_tier,
    recommend,
)
from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable
from quill.core.windows_dictation.model_types import (
    BALANCED,
    HIGH_ACCURACY,
    LIGHTWEIGHT,
    MEASURED,
    TIER_MEANINGS,
    TIERS,
    legacy_tier,
    tier_for,
)
from quill.core.windows_dictation.speed_check import SpeedCheck

#: The baseline machine (dictation design, section 1) and its betters.
BASELINE = SpeedCheck(tiny=0.12, cores=2, memory_gb=3.8)
BASELINE_UNTIMED = SpeedCheck(tiny=None, cores=2, memory_gb=3.8)
EIGHT_GB = SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8)
EIGHT_GB_DUAL = SpeedCheck(tiny=0.07, cores=2, memory_gb=7.8)
SIXTEEN_GB = SpeedCheck(tiny=0.04, cores=8, memory_gb=15.8)
SIXTEEN_GB_GPU = SpeedCheck(tiny=0.04, cores=8, memory_gb=31.8, has_gpu=True)
VERY_SLOW = SpeedCheck(tiny=0.3, cores=2, memory_gb=3.8)
NO_MEMORY_READING = SpeedCheck(tiny=0.05, cores=4, memory_gb=None)


@pytest.mark.parametrize(
    ("check", "language", "priority", "expected"),
    [
        # The 4 GB baseline keeps the built-in model: a download that measured
        # no better is not worth having there.
        (BASELINE, "en", "balanced", "moonshine"),
        (BASELINE_UNTIMED, "en", "balanced", "moonshine"),
        (BASELINE, "en", "speed", "moonshine"),
        (BASELINE, "en", "accuracy", "moonshine_base"),
        # Spanish has only Whisper built in.
        (BASELINE, "es", "balanced", "whisper"),
        (BASELINE, "es", "accuracy", "whisper"),
        # 8 GB, four cores: Moonshine base; Nemotron only when accuracy is asked.
        (EIGHT_GB, "en", "balanced", "moonshine_base"),
        (EIGHT_GB, "en", "speed", "moonshine"),
        (EIGHT_GB, "en", "accuracy", "nemotron"),
        (EIGHT_GB, "es", "balanced", "whisper"),
        # Spanish is ranked by real Spanish speech (2026-10-22): Parakeet
        # TDT v3 got 5.9 percent wrong, Nemotron 7.2, Whisper tiny 28.8.
        (EIGHT_GB, "es", "accuracy", "parakeet"),
        # Two cores are a modest computer, whatever the memory.
        (EIGHT_GB_DUAL, "en", "balanced", "moonshine"),
        # 16 GB and up: Nemotron by default (dict.md D-26's tier table).
        (SIXTEEN_GB, "en", "balanced", "nemotron"),
        (SIXTEEN_GB, "en", "speed", "moonshine"),
        (SIXTEEN_GB, "es", "balanced", "parakeet"),
        (SIXTEEN_GB_GPU, "en", "balanced", "nemotron"),
        # Nothing keeps up: the lightest built-in model, with a warning.
        (VERY_SLOW, "en", "balanced", "moonshine"),
        (VERY_SLOW, "es", "balanced", "whisper"),
        (NO_MEMORY_READING, "en", "balanced", "moonshine_base"),
    ],
)
def test_recommendation_over_machine_profiles(check, language, priority, expected) -> None:
    advice = recommend(check, language, priority=priority)
    assert advice.model_id == expected
    assert advice.sentence.startswith(advice.name)
    assert advice.tier in TIERS
    assert advice.line == f"Recommended for this computer: {advice.sentence}"


def test_the_sentence_names_the_machine_the_wait_and_privacy() -> None:
    advice = recommend(EIGHT_GB, "en")
    assert advice.sentence == (
        "Moonshine base, Lightweight: keeps up on this computer's 8 GB and 4 cores, "
        "about 0.3 seconds after you pause; stays on this computer; a 141 MB download."
    )
    assert not advice.built_in
    assert advice.download_bytes == downloadable("moonshine_base").download_bytes


def test_a_built_in_model_says_nothing_to_download() -> None:
    advice = recommend(BASELINE, "en")
    assert "already installed" in advice.sentence
    assert "Nothing to download: it is already on this computer." in advice.reasons


def test_two_threads_are_said_with_their_cost() -> None:
    advice = recommend(SIXTEEN_GB, "en")
    assert "using two processor threads" in advice.sentence
    assert any("screen reader may answer a little more slowly" in r for r in advice.reasons)


def test_a_better_model_left_out_is_named_with_why() -> None:
    advice = recommend(EIGHT_GB, "en")
    assert any(
        r.startswith("NVIDIA Nemotron") and "second processor thread" in r for r in advice.reasons
    )
    memory = recommend(BASELINE, "en", priority="accuracy")
    assert any("more memory than this computer can spare" in r for r in memory.reasons)


def test_nothing_keeps_up_is_said_plainly() -> None:
    advice = recommend(VERY_SLOW, "es")
    assert advice.may_lag
    assert "the lightest model for Spanish; it may lag behind your speech" in advice.sentence


def test_every_answer_is_marked_an_estimate_and_never_switches() -> None:
    advice = recommend(EIGHT_GB, "en")
    assert ESTIMATE_NOTE in advice.reasons
    assert advice.reasons[-1].startswith("QUILL never changes your model by itself")
    assert advice.details.splitlines()[0] == advice.line


def test_spanish_cites_real_spanish_speech() -> None:
    advice = recommend(EIGHT_GB, "es")
    assert any("real Spanish speakers" in r for r in advice.reasons)
    assert not any("measured in English only" in r for r in advice.reasons)


def test_spanish_offers_only_models_measured_in_spanish() -> None:
    from quill.core.windows_dictation.model_types import MEASURED

    for check in (BASELINE, EIGHT_GB, SIXTEEN_GB):
        for priority in ("balanced", "speed", "accuracy"):
            chosen = recommend(check, "es", priority=priority).model_id
            assert MEASURED[chosen].word_errors_es is not None, (check, priority, chosen)


def test_free_memory_caps_the_choice_and_says_why() -> None:
    from dataclasses import replace

    roomy = recommend(SIXTEEN_GB, "es")
    assert roomy.model_id == "parakeet"
    # The same 16 GB computer with 1.2 GB free: Parakeet's 1.1 GB peak plus
    # the half-gigabyte reserve does not fit, so a lighter model is named.
    busy = recommend(replace(SIXTEEN_GB, available_gb=1.2), "es")
    assert busy.model_id != "parakeet"
    assert any("free on this computer right now" in r for r in busy.reasons)


def test_unreadable_free_memory_falls_back_to_the_total() -> None:
    from dataclasses import replace

    assert recommend(replace(SIXTEEN_GB, available_gb=None), "es").model_id == "parakeet"


def test_an_untimed_check_says_so() -> None:
    advice = recommend(BASELINE_UNTIMED, "en")
    assert any("estimated from the processor and memory, not timed" in r for r in advice.reasons)


def test_a_graphics_card_is_mentioned_only_to_say_it_changes_nothing() -> None:
    with_gpu = recommend(SIXTEEN_GB_GPU, "en")
    assert any("graphics card is not used" in r for r in with_gpu.reasons)
    without = recommend(SIXTEEN_GB, "en")
    assert not any("graphics card" in r for r in without.reasons)
    assert recommend(SIXTEEN_GB, "en", has_gpu=True).model_id == without.model_id


def test_priority_labels_and_unknown_priority() -> None:
    assert [value for value, _label in PRIORITIES] == ["balanced", "speed", "accuracy"]
    assert recommend(EIGHT_GB, "en", priority="nonsense").model_id == "moonshine_base"


def test_privacy_other_than_local_still_recommends_a_local_model() -> None:
    advice = recommend(EIGHT_GB, "en", privacy="any")
    assert advice.model_id == "moonshine_base"
    assert "stays on this computer" in advice.sentence
    assert any("keep your speech on this computer" in r for r in advice.reasons)


def test_unmeasured_models_are_never_recommended() -> None:
    measured = set(MEASURED)
    for check in (BASELINE, EIGHT_GB, SIXTEEN_GB, SIXTEEN_GB_GPU):
        for language in ("en", "es"):
            for priority, _label in PRIORITIES:
                assert recommend(check, language, priority=priority).model_id in measured


def test_speed_check_recommend_is_the_spec_entry_point() -> None:
    assert speed_check.recommend(EIGHT_GB, "en") == recommend(EIGHT_GB, "en")


def test_latest_is_instant_and_remembers_a_timed_check(monkeypatch) -> None:
    monkeypatch.setattr(speed_check, "_LAST", None)
    assert speed_check.latest().tiny is None
    timed = speed_check.run(lambda: 0.05, gpu=lambda: False)
    assert speed_check.latest() == timed
    monkeypatch.setattr(model_advice, "recommend", lambda *a, **k: a[0])
    assert model_advice.for_this_computer("en") == timed


# -- tiers ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    ("cost", "errors", "tier"),
    [
        (1.0, 3.4, LIGHTWEIGHT),
        (5.0, None, LIGHTWEIGHT),
        (6.1, 3.4, BALANCED),
        (10.0, None, BALANCED),
        (8.0, 2.5, HIGH_ACCURACY),
        (24.0, 5.1, HIGH_ACCURACY),
    ],
)
def test_tier_from_cost_and_word_errors(cost, errors, tier) -> None:
    assert tier_for(cost, errors) == tier


def test_every_model_has_a_tier_and_the_known_ones_are_pinned() -> None:
    tiers = {model.id: model.tier for model in CATALOGUE}
    assert set(tiers.values()) <= set(TIERS)
    assert tiers["moonshine_base"] == LIGHTWEIGHT
    assert tiers["parakeet"] == tiers["parakeet_unified"] == tiers["whisper_base"] == BALANCED
    assert tiers["nemotron"] == tiers["whisper_small"] == tiers["whisper_large_v3"] == HIGH_ACCURACY
    assert engine_tier("moonshine") == engine_tier("whisper") == LIGHTWEIGHT
    assert engine_tier("windows") == engine_tier("voice_typing") == engine_tier("openai") == ""
    assert set(TIER_MEANINGS) == set(TIERS)


def test_quills_own_catalogue_uses_the_same_tiers() -> None:
    assert legacy_tier("tiny", 75, "low") == LIGHTWEIGHT
    assert legacy_tier("small", 465, "medium") == BALANCED
    assert legacy_tier("large-v3", 3100, "highest") == HIGH_ACCURACY
    # One model, one tier, whichever catalogue lists it.
    assert legacy_tier("nemotron-streaming-en-0.6b", 632, "high") == downloadable("nemotron").tier
    assert legacy_tier("parakeet-tdt-0.6b-v3", 650, "high") == downloadable("parakeet").tier


@pytest.mark.parametrize(
    ("ram", "gpu", "words"),
    [
        (0.0, False, "could not be measured"),
        (2.0, False, "lightest model"),
        (4.0, False, "light model fits"),
        (8.0, False, "mid-sized model"),
        (14.0, False, "larger, more accurate"),
        (32.0, True, "practical with a graphics card"),
        (32.0, False, "one size down"),
    ],
)
def test_quills_own_recommendation_says_why(ram, gpu, words) -> None:
    assert words in recommendation_reason(ram, gpu)
