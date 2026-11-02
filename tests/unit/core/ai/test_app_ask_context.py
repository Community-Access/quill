"""Each app's Ask facts, the never-without-a-yes filter and the change marker."""

from __future__ import annotations

from pathlib import Path

from quill.core.abbreviations import Abbreviation
from quill.core.ai import app_ask_context as ac
from quill.core.ai.connection_caps import CHATGPT
from quill.core.audio.media_probe import MediaInfo, StreamInfo
from quill.core.demo_recording import Finding
from quill.core.demo_recording_verify import Check, Verification
from quill.core.weather.models import (
    CurrentConditions,
    ForecastPeriod,
    HourlyPeriod,
    WeatherAlert,
    WeatherLocation,
    WeatherReport,
)

# -- the filter --------------------------------------------------------------- #


def test_scrub_removes_paths_emails_and_coordinates() -> None:
    text = r"Saved C:\Users\jeff\Music\song.mp3 for jeff@example.com at 32.22, -110.97"
    assert ac.scrub(text) == "Saved song.mp3 for an email address at a place"
    assert ac.scrub("see /home/jeff/notes/todo.txt") == "see todo.txt"


def test_filter_holds_back_every_kind_that_needs_a_yes() -> None:
    facts = ac.AppFacts(
        "x",
        (
            ac.Fact("Plain", r"in D:\secret\file.txt"),
            ac.Fact("History", "songs", ac.HISTORY),
            ac.Fact("Where", "1.23,4.56", ac.COORDINATES),
            ac.Fact("Empty", "  "),
        ),
    )
    held = ac.filter_facts(facts)
    assert [f.name for f in held.facts] == ["Plain"]
    assert held.facts[0].value == "in file.txt"
    assert held.held_back == ("History", "Where")
    allowed = ac.filter_facts(facts, consented=[ac.HISTORY])
    assert [f.name for f in allowed.facts] == ["Plain", "History"]
    assert ac.NEVER_WITHOUT_YES >= {ac.PICTURE, ac.AUDIO, ac.PATH, ac.ACCOUNT, ac.WHOLE_TEXT}


def test_facts_text_and_change_note() -> None:
    first = ac.radio_context("KUAZ", "Song A")
    second = ac.radio_context("KUAZ", "Song B")
    assert ac.facts_text(first) == "Station: KUAZ\nNow playing: Song A"
    assert ac.change_note(None, first) == ""
    assert ac.change_note(first, first) == ""
    assert ac.change_note(first, second) == "Now playing changed since your last question."
    third = ac.radio_context("WQXR", "Song C")
    assert ac.change_note(first, third) == (
        "Station and Now playing changed since your last question."
    )


def test_asking_line() -> None:
    assert ac.asking_line(CHATGPT, "this station") == "Asking My ChatGPT plan about this station."


# -- Radio -------------------------------------------------------------------- #


def test_radio_sends_favourites_and_songs_only_when_the_question_needs_them() -> None:
    favs = [("KUAZ", "Public"), ("WQXR", "")]
    plain = ac.radio_context("KUAZ", "Song", question="Who is this?", favorites=favs)
    assert plain.get("Favourite stations") == ""
    asked = ac.radio_context(
        "KUAZ", "Song", question="Recommend more like my favourites", favorites=favs
    )
    assert "KUAZ (in Public)" in asked.get("Favourite stations")
    songs = ac.radio_context(
        "KUAZ", "", question="What has it played lately?", recent_songs=["a", "b"]
    )
    assert "a; b" in songs.get("Songs heard on this station")


def test_radio_listening_history_never_leaves_without_a_yes() -> None:
    listening = [("KUAZ", ["a"])]
    facts = ac.radio_context("KUAZ", "", needs="listening", listening=listening)
    assert ac.filter_facts(facts).held_back == ("Listening history",)
    assert "KUAZ: a" in ac.filter_facts(facts, [ac.HISTORY]).get("Listening history")


# -- the other apps ----------------------------------------------------------- #


def test_cast_context_names_the_current_chapter_and_position() -> None:
    facts = ac.cast_context(
        "Show",
        "Ep 1",
        notes="Notes",
        chapters=[("Intro", 0), ("Interview", 300)],
        position_s=400,
        duration_s=3600,
    )
    assert facts.get("Current chapter") == "Interview"
    assert facts.get("Position") == "6:40 of 1:00:00"
    assert "5:00 Interview" in facts.get("Chapters")


def test_studio_context_from_findings_and_the_last_check() -> None:
    verification = Verification(
        "Needs review",
        "One thing needs a look.",
        [Check("Sound", False, "Silent from 0:10"), Check("Picture", True, "ok")],
    )
    facts = ac.studio_context(
        plan_summary="Will record: the Studio window.",
        findings=[Finding("Warn", "The microphone is quiet.")],
        capture={"Displays": "2", "Encoder": ""},
        verification=verification,
    )
    assert facts.get("Pre-flight check") == "Warn: The microphone is quiet."
    assert facts.get("Capture facts") == "Displays: 2"
    assert "Sound: Silent from 0:10" in facts.get("Last recording check")
    assert ac.studio_context(plan_summary="x").get("Pre-flight check") == "No problems found."


def test_transcribe_context_finds_speakers_and_holds_back_the_rest() -> None:
    transcript = "Alex: hello\nSam: hi\n" + ("word " * 4000)
    facts = ac.transcribe_context(transcript, title="Meeting")
    assert facts.get("Speakers") == "Alex, Sam"
    filtered = ac.filter_facts(facts)
    assert filtered.held_back == ("Rest of the transcript",)
    assert len(filtered.get("Transcript")) <= 12000


def test_converter_context_uses_probe_text_without_paths() -> None:
    info = MediaInfo(
        Path(r"C:\Users\jeff\Music\a.mp3"),
        container="mp3",
        duration_s=61,
        size_bytes=1000,
        streams=(StreamInfo("audio", "mp3", sample_rate=44100, channels=2),),
    )
    facts = ac.filter_facts(ac.converter_context([info]))
    details = facts.get("File details")
    assert "File: a.mp3" in details and "Users" not in details
    assert facts.get("Files queued") == "1"


def test_player_context() -> None:
    facts = ac.player_context(
        "Dune", chapter_title="Arrakis", chapter_number=3, chapter_count=40, position_s=75
    )
    assert facts.get("Chapter") == "Arrakis (chapter 3 of 40)"
    assert facts.get("Position") == "1:15"


def _report(name: str) -> WeatherReport:
    return WeatherReport(
        location=WeatherLocation(display_name=name, latitude=32.2, longitude=-110.9),
        current=CurrentConditions(
            text_description="Sunny", temperature_f=72.0, wind_speed_mph=5, wind_direction="NW"
        ),
        periods=[ForecastPeriod("Tonight", 50, "F", "Clear", "Clear, low 50.")],
        hourly=[HourlyPeriod("5 PM", 61, "F", "Rain", precipitation_percent=80)],
        alerts=[WeatherAlert("a1", "Heat Advisory", headline="Until 8 PM")],
    )


def test_weather_sends_the_place_name_never_coordinates() -> None:
    facts = ac.weather_context(_report("32.2,-110.9"))
    assert facts.get("Place") == "the saved place"
    assert "32.2" not in ac.facts_text(facts)
    named = ac.weather_context(_report("Tucson, AZ"))
    assert named.get("Place") == "Tucson, AZ"
    assert named.get("Current conditions") == "Sunny, 72 F, wind NW 5 mph"
    assert "80 percent chance of rain" in named.get("Next hours")
    assert named.get("Active alerts, as the Weather Service wrote them") == (
        "Heat Advisory -- Until 8 PM"
    )


def test_inkwell_context_most_used_first_and_scrubbed() -> None:
    abbreviations = [
        Abbreviation("1", "sig", "Jeff, jeff@example.com", usage_count=2),
        Abbreviation("2", "brb", "be right back", usage_count=9),
        Abbreviation("3", "off", "never sent", enabled=False),
    ]
    facts = ac.filter_facts(ac.inkwell_context(abbreviations))
    rows = facts.get("Abbreviation list").splitlines()
    assert rows[0].startswith("brb -> be right back")
    assert "an email address" in rows[1]
    assert len(rows) == 2


def test_beacon_context() -> None:
    facts = ac.beacon_context(search="tax", results=[("2025 return", "filed in April")])
    assert facts.get("Search results") == "- 2025 return: filed in April"


def test_studio_context_names_the_recording_and_the_book_but_never_a_path() -> None:
    from quill.core.ai.app_ask_context import facts_text, filter_facts, studio_context

    facts = filter_facts(
        studio_context(recording="Recording, 2 minutes 10 seconds.", book="Sea Stories")
    )
    text = facts_text(facts)
    assert "Recording now: Recording, 2 minutes 10 seconds." in text
    assert "Book open: Sea Stories" in text
    leaked = studio_context(book=r"C:\Users\me\Books\Sea Stories.m4b")
    assert "Users" not in facts_text(filter_facts(leaked))
