"""Each app's first single-request feature, built from local data."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai import app_ai_prompts as ap
from quill.core.audio.media_probe import MediaInfo, StreamInfo
from quill.core.demo_recording import Finding
from quill.core.weather.models import (
    CurrentConditions,
    HourlyPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)


def test_should_i_go_out_uses_text_and_never_rewords_alerts() -> None:
    report = WeatherReport(
        location=WeatherLocation("40.71,-74.00", 40.71, -74.0),
        current=CurrentConditions(text_description="Cloudy", temperature_f=48.0),
        hourly=[HourlyPeriod("5 PM", 45, "F", "Rain", precipitation_percent=70)],
        alerts=[WeatherAlert("a", "Wind Advisory")],
    )
    prompt = ap.should_i_go_out_prompt(report, when="at 5", plans="walk the dog")
    assert prompt.startswith("Should I go out at 5 to walk the dog?")
    assert "do not restate" in prompt
    assert "Wind Advisory" in prompt
    assert "40.71" not in prompt and "the saved place" in prompt


def test_will_it_play_from_probe_text() -> None:
    info = MediaInfo(
        Path(r"C:\Users\jeff\book.flac"),
        container="flac",
        duration_s=3600,
        streams=(StreamInfo("audio", "flac", sample_rate=96000, channels=2),),
    )
    prompt = ap.will_it_play_prompt([info], device="my car")
    assert prompt.startswith("Will these files play on my car?")
    assert "Audio 1: flac" in prompt and "jeff" not in prompt


def test_suggest_abbreviations_counts_locally() -> None:
    text = ("Thank you for your patience. " * 4) + ("Community Access newsletter. " * 3)
    ideas = ap.suggest_abbreviations(text, existing=[("tyfp", "something else")])
    phrases = [i.phrase for i in ideas]
    assert "thank you for your patience" in phrases
    assert "community access newsletter" in phrases
    first = next(i for i in ideas if i.phrase == "thank you for your patience")
    assert first.abbreviation == "tyfyp" and first.count == 4
    assert "you for your" not in phrases  # a piece of a chosen phrase


def test_suggest_abbreviations_skips_what_the_library_has_and_avoids_clashes() -> None:
    text = "Community Access newsletter. " * 3
    known = ap.suggest_abbreviations(text, existing=[("x", "Community  Access newsletter")])
    assert "community access newsletter" not in [i.phrase for i in known]
    clash = ap.suggest_abbreviations(text, existing=[("can", "can")])
    assert clash[0].abbreviation == "can2"


def test_abbreviation_prompt_sends_phrases_only() -> None:
    ideas = [ap.AbbreviationIdea("thank you for your patience", 4, "tyfyp")]
    prompt = ap.abbreviation_prompt(ideas)
    assert "thank you for your patience (typed 4 times; proposed tyfyp)" in prompt


def test_player_recap_uses_the_media_wording() -> None:
    prompt = ap.player_recap_prompt("chapter", book="Dune", chapter_title="One", transcript="text")
    assert prompt.startswith("Summarize this audiobook chapter")
    assert "Book: Dune\nChapter: One" in prompt


def test_beacon_prompts() -> None:
    summary = ap.beacon_summarise_prompt("Taxes", "Filed on April 1.", tags=["money"])
    assert "Note: Taxes" in summary and "Tags: money" in summary
    describe = ap.beacon_describe_prompt(r"C:\shots\error.png", ocr_text="Access denied")
    assert "Saved as: error.png" in describe and "Access denied" in describe


def test_setup_ready_local_verdict_first() -> None:
    assert ap.setup_ready_local([]) == "Ready to record."
    assert ap.setup_ready_local([Finding("Warn", "x")]) == "Ready, with 1 thing worth a look."
    assert ap.setup_ready_local([Finding("Stop", "a"), Finding("Stop", "b")]) == (
        "Not ready: 2 things stop the recording."
    )
    prompt = ap.setup_ready_prompt(
        plan_summary="Will record: screen.", findings=[Finding("Stop", "No microphone.")]
    )
    assert prompt.startswith("Not ready: 1 thing stops the recording.")
    assert "Stop: No microphone." in prompt


def test_cast_missed_prompt() -> None:
    prompt = ap.cast_missed_prompt(
        "Show", "Ep", chapters=[("Intro", 0), ("Main", 60)], position_s=90, transcript="so far"
    )
    assert "Current chapter: Main" in prompt and "Transcript so far:\nso far" in prompt


def test_transcript_prompts_reuse_the_builtin_actions() -> None:
    from quill.core.ai.transcript_actions import find_action

    summary = ap.transcript_summary_prompt("A: hi", extra="short")
    action = find_action("executive-summary")
    assert action is not None
    assert summary == action.build_prompt("A: hi", extra_instruction="short")
    assert "TRANSCRIPT:\nA: hi" in ap.transcript_action_items_prompt("A: hi")
