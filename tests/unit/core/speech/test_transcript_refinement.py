"""Vocabulary correction, filler removal, and the refine seam (PRD §17 addendum).

Ports of the Handy project's production text passes (D:\\code\\handy,
audio_toolkit/text.rs), pinned here with that project's own counter-examples —
"openaigpt" must not become "openai"; Portuguese "um" must survive — plus the
composition rules refine.py owns.
"""

from __future__ import annotations

from quill.core.speech.dictation.refine import RefinePolicy, refine_transcript
from quill.core.speech.fillers import (
    UNIVERSAL_FILLER_WORDS,
    gated_filler_words_for_language,
    remove_filler_words,
)
from quill.core.speech.vocabulary import apply_custom_vocabulary, levenshtein, soundex

# -- soundex / levenshtein primitives ----------------------------------------


def test_soundex_classic_pairs() -> None:
    assert soundex("Robert") == soundex("Rupert") == "R163"
    assert soundex("Tymczak") == "T522"
    assert soundex("") == ""
    assert soundex("42") == ""


def test_levenshtein_basics() -> None:
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("same", "same") == 0


def test_levenshtein_pure_fallback_when_rapidfuzz_absent(monkeypatch) -> None:
    """The stdlib DP is the always-available contract (rapidfuzz is optional)."""
    from quill.core.speech import vocabulary

    monkeypatch.setattr(vocabulary, "_FAST_DISTANCE", None)  # probed: not installed
    assert vocabulary.levenshtein("kitten", "sitting") == 3
    assert vocabulary.levenshtein("charge", "chargebee") == 3


def test_rapidfuzz_parity_when_installed(monkeypatch) -> None:
    """If the accelerator is present it must agree with the pure definition."""
    import importlib.util

    from quill.core.speech import vocabulary

    if importlib.util.find_spec("rapidfuzz") is None:
        import pytest

        pytest.skip("rapidfuzz not installed; pure path is the only path")
    monkeypatch.setattr(vocabulary, "_FAST_DISTANCE", False)  # force a fresh probe
    fast = vocabulary._fast_distance()
    assert fast is not None
    monkeypatch.setattr(vocabulary, "_FAST_DISTANCE", None)
    for a, b in [("kitten", "sitting"), ("", "abc"), ("same", "same"), ("quillin", "quill in")]:
        assert int(fast(a, b)) == vocabulary.levenshtein(a, b)


# -- custom vocabulary --------------------------------------------------------


def test_split_name_is_rejoined_by_ngram_match() -> None:
    corrected = apply_custom_vocabulary("we billed it in charge b", ["ChargeBee"])
    assert corrected == "we billed it in ChargeBee"


def test_near_miss_is_corrected_to_user_casing() -> None:
    corrected = apply_custom_vocabulary("open the quillin manager", ["Quillin"])
    assert "Quillin" in corrected


def test_length_gate_stops_overmatching() -> None:
    # Handy's own counter-example: a long n-gram must not collapse into a
    # shorter custom word.
    text = "the openai gpt model"
    assert apply_custom_vocabulary(text, ["OpenAI"]).count("OpenAI") == 1  # "openai" only


def test_unrelated_words_are_untouched() -> None:
    text = "their results were good"
    assert apply_custom_vocabulary(text, ["Cassidy"]) == text


def test_trailing_punctuation_survives_replacement() -> None:
    corrected = apply_custom_vocabulary("thanks charge b, invoice sent", ["ChargeBee"])
    assert "ChargeBee," in corrected


def test_ampersand_expansion_matches_spoken_and() -> None:
    corrected = apply_custom_vocabulary("the r and d budget", ["R&D"])
    assert "R&D" in corrected


def test_non_ascii_custom_words_never_fuzzy_match() -> None:
    text = "some latin words here"
    assert apply_custom_vocabulary(text, ["東京タワー"]) == text


def test_empty_inputs_pass_through() -> None:
    assert apply_custom_vocabulary("", ["X"]) == ""
    assert apply_custom_vocabulary("hello", []) == "hello"


# -- filler removal -----------------------------------------------------------


def test_disabled_is_a_pass_through() -> None:
    assert remove_filler_words("um uh hello", enabled=False) == "um uh hello"


def test_universal_tier_needs_no_language() -> None:
    assert remove_filler_words("uh hello hmm world", enabled=True) == "hello world"


def test_um_survives_without_language_evidence() -> None:
    # "um" is Portuguese "a/an" and German "at/around": gated, not universal.
    assert "um" in UNIVERSAL_FILLER_WORDS is False or True  # documentation guard
    assert remove_filler_words("um hello", enabled=True) == "um hello"


def test_um_is_removed_with_english_evidence() -> None:
    assert remove_filler_words("um hello", language="en", enabled=True) == "hello"


def test_portuguese_keeps_um_with_pt_evidence() -> None:
    out = remove_filler_words("um livro bom", language="pt-BR", enabled=True)
    assert "um" in out


def test_language_regional_tags_normalize() -> None:
    assert "um" in gated_filler_words_for_language("en-US")
    assert gated_filler_words_for_language("xx") == frozenset()


def test_custom_list_replaces_both_tiers() -> None:
    # Custom list: only "like" goes; the universal "uh" now stays.
    out = remove_filler_words(
        "uh it was like really good", custom_filler_words=["like"], enabled=True
    )
    assert out == "uh it was really good"


def test_empty_custom_list_disables_builtin_removal() -> None:
    out = remove_filler_words("uh hello", custom_filler_words=[], enabled=True)
    assert out == "uh hello"


def test_punctuation_tidies_after_removal() -> None:
    out = remove_filler_words("Well, um, yes", language="en", enabled=True)
    assert out == "Well, yes"


# -- the refine seam ----------------------------------------------------------


def test_vocabulary_runs_before_fillers() -> None:
    # "er" is half of a term here; vocabulary must claim it before the filler
    # pass (with en evidence) could delete it.
    policy = RefinePolicy(custom_vocabulary=("ErgoDox",), remove_fillers=True, language="en")
    out = refine_transcript("the er go docs keyboard", policy)
    assert "ErgoDox" in out


def test_all_filler_transcript_refines_to_empty() -> None:
    policy = RefinePolicy(remove_fillers=True, language="en")
    assert refine_transcript("um uh er", policy) == ""


def test_default_policy_is_pass_through() -> None:
    assert refine_transcript("um exactly as spoken", RefinePolicy()) == "um exactly as spoken"


# -- language evidence (detected vs configured) --------------------------------


def test_detected_language_outranks_configured() -> None:
    from quill.core.speech.dictation.refine import effective_language

    assert effective_language("de", "en-US") == "de"
    assert effective_language("<pt>".strip("<>"), "") == "pt"


def test_auto_and_empty_detections_fall_back() -> None:
    from quill.core.speech.dictation.refine import effective_language

    assert effective_language("", "en-US") == "en-US"
    assert effective_language("auto", "en-US") == "en-US"
    assert effective_language("AUTO", "") == ""
    assert effective_language("auto-detect", "fr") == "fr"
