"""Record a Demonstration: plan, file names, the spoken check and recovery (PRD 7A.6)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from quill.core.demo_recording import (
    CameraSetup,
    DemoPlan,
    DemoRecordingError,
    MarkerLog,
    PreflightFacts,
    SoundSource,
    can_start,
    demo_file_name,
    format_timestamp,
    output_size,
    preflight,
    screen_reader_sentence,
    short_target_name,
    spoken_duration,
    summary,
    unique_path,
    validate_plan,
)
from quill.core.demo_recording_session import (
    SegmentRecord,
    SessionRecord,
    find_unfinished,
    markers_from_session,
    plan_from_dict,
    plan_to_dict,
    preferences_from_plan,
    saved_level,
    work_folder,
)

STUDIO_PID = 4242


def _plan(tmp_path: Path, **changes) -> DemoPlan:
    base = DemoPlan(
        target_kind="display",
        target_label="Display 1: \\\\.\\DISPLAY1; 1920 by 1080; origin 0, 0; primary",
        bounds=(0, 0, 1920, 1080),
        folder=str(tmp_path),
        display_bounds=(0, 0, 1920, 1080),
        studio_process_id=STUDIO_PID,
        screen_reader="jfw.exe",
        sources=(
            SoundSource("application", "Edge sound", "app-msedge.exe", process_id=100),
            SoundSource("system", "System sound", "system"),
            SoundSource("microphone", "Microphone", "microphone", device="Headset"),
            SoundSource("screen_reader", "JAWS speech", "screen-reader", process_id=200),
        ),
    )
    return replace(base, **changes)


def _on(plan: DemoPlan, *ids: str, **extra) -> DemoPlan:
    return replace(
        plan,
        sources=tuple(
            replace(s, enabled=s.source_id in ids, **(extra if s.source_id in ids else {}))
            for s in plan.sources
        ),
    )


def _texts(findings, severity):
    return [f.text for f in findings if f.severity == severity]


# -- 1. File naming --------------------------------------------------------------


def test_short_name_strips_forbidden_characters_and_caps_length():
    assert short_target_name('Report: "Q3" <draft>|final?; process x') == "Report Q3 draftfinal"
    long = short_target_name("A" * 100)
    assert len(long) == 60


def test_demo_file_name_shape():
    name = demo_file_name("Microsoft Edge", datetime(2026, 10, 29, 21, 5, 9))
    assert name == "Demo - Microsoft Edge - 2026-10-29 210509.mp4"


def test_unique_path_never_overwrites(tmp_path):
    first = tmp_path / "Demo.mp4"
    assert unique_path(first) == first
    first.write_bytes(b"x")
    second = unique_path(first)
    assert second.name == "Demo (2).mp4"
    second.write_bytes(b"x")
    assert unique_path(first).name == "Demo (3).mp4"


def test_empty_label_still_names_a_file():
    assert short_target_name('<>:"') == "Recording"


# -- sizes -----------------------------------------------------------------------


def test_output_size_applies_ceiling_and_keeps_even(tmp_path):
    plan = _plan(tmp_path, bounds=(0, 0, 2561, 1441), size_ceiling=720)
    width, height = output_size(plan)
    assert height == 720 and width % 2 == 0
    odd = _plan(tmp_path, bounds=(0, 0, 801, 601))
    assert output_size(odd) == (802, 602)


# -- 3/4. The spoken check -------------------------------------------------------


def test_clean_plan_has_only_the_hotkey_warning_and_can_start(tmp_path):
    plan = _on(_plan(tmp_path), "app-msedge.exe")
    findings = preflight(plan, PreflightFacts(hotkeys_assigned=2, free_bytes=10**13))
    assert findings == []
    assert can_start(findings)
    assert "No problems found" in summary(plan, findings)


@pytest.mark.parametrize(
    ("facts", "fragment"),
    [
        (PreflightFacts(target_problem="The window closed."), "window closed"),
        (PreflightFacts(trial_grab_error="ddagrab failed"), "trial picture"),
        (PreflightFacts(ffmpeg_found=False), "FFmpeg was not found"),
        (PreflightFacts(h264_encoder=""), "no H.264"),
        (PreflightFacts(folder_error="Access denied"), "cannot be written"),
        (PreflightFacts(studio_process_in_capture=True), "Studio's own process"),
    ],
)
def test_each_stop_blocks_the_start(tmp_path, facts, fragment):
    findings = preflight(_plan(tmp_path), facts)
    assert any(fragment in text for text in _texts(findings, "Stop"))
    assert not can_start(findings)
    assert "cannot start" in summary(_plan(tmp_path), findings)


def test_source_that_cannot_open_is_a_stop(tmp_path):
    plan = _on(_plan(tmp_path), "app-msedge.exe")
    findings = preflight(plan, PreflightFacts(source_errors={"app-msedge.exe": "gone"}))
    assert any("Edge sound cannot be opened" in t for t in _texts(findings, "Stop"))


def test_microphone_lock_held_is_a_stop_naming_the_holder(tmp_path):
    plan = _on(_plan(tmp_path), "microphone")
    findings = preflight(plan, PreflightFacts(microphone_holder="Quill Inkwell is dictating"))
    assert any("Inkwell" in t for t in _texts(findings, "Stop"))


def test_microphone_lock_is_ignored_when_the_microphone_is_off(tmp_path):
    findings = preflight(
        _plan(tmp_path), PreflightFacts(microphone_holder="Inkwell", hotkeys_assigned=1)
    )
    assert can_start(findings)


def test_digital_silence_is_a_warn_and_quiet_is_not(tmp_path):
    plan = _on(_plan(tmp_path), "microphone", "app-msedge.exe")
    findings = preflight(
        plan,
        PreflightFacts(
            digital_silence=("microphone",), quiet=("app-msedge.exe",), hotkeys_assigned=1
        ),
    )
    warns = _texts(findings, "Warn")
    assert any("Microphone delivers exact digital silence" in t for t in warns)
    assert not any("Edge" in t for t in warns)


def test_system_sound_with_reader_left_out_warns(tmp_path):
    plan = _on(_plan(tmp_path), "system")
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("cannot subtract the screen reader" in t for t in warns)
    assert "may be heard" in screen_reader_sentence(plan)


def test_system_sound_excluding_the_reader_does_not_warn(tmp_path):
    plan = _on(_plan(tmp_path), "system", exclude_process_id=200, exclude_name="jfw.exe")
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert not any("subtract" in t for t in warns)
    assert "left out" in screen_reader_sentence(plan)


def test_doubled_sound_warns(tmp_path):
    plan = _on(_plan(tmp_path), "system", "app-msedge.exe")
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("heard twice" in t for t in warns)


def test_screen_reader_speech_on_is_a_reminder(tmp_path):
    plan = _on(_plan(tmp_path), "screen-reader")
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("everything your screen reader says" in t for t in warns)
    assert "IS in the recording" in summary(plan, [])


def test_no_hotkeys_warns(tmp_path):
    warns = _texts(preflight(_plan(tmp_path), PreflightFacts()), "Warn")
    assert any("No system-wide recording keys" in t for t in warns)


def test_uniform_trial_grab_and_studio_target_and_desktop_warn(tmp_path):
    plan = _plan(tmp_path, target_kind="desktop")
    warns = _texts(
        preflight(
            plan,
            PreflightFacts(trial_grab_uniform=True, target_is_studio=True, display_count=2),
        ),
        "Warn",
    )
    assert any("same colour" in t for t in warns)
    assert any("Studio's controls" in t for t in warns)
    assert any("2 displays" in t for t in warns)


def test_low_space_warns(tmp_path):
    warns = _texts(preflight(_plan(tmp_path), PreflightFacts(free_bytes=10)), "Warn")
    assert any("Free space is low" in t for t in warns)


def test_camera_problems(tmp_path):
    plan = _on(
        _plan(tmp_path, camera=CameraSetup(enabled=True, device="Surface Camera Front")),
        "microphone",
    )
    stops = _texts(preflight(plan, PreflightFacts(camera_error="busy")), "Stop")
    assert any("camera cannot be opened" in t for t in stops)
    warns = _texts(preflight(plan, PreflightFacts(camera_guidance="No face in view.")), "Warn")
    assert any("No face in view" in t for t in warns)
    fine = preflight(
        plan, PreflightFacts(camera_guidance="Face in view, centred.", hotkeys_assigned=1)
    )
    assert fine == []
    assert "Surface Camera Front" in summary(plan, fine)


def test_summary_order_names_target_sound_reader_folder(tmp_path):
    plan = _on(_plan(tmp_path), "microphone")
    text = summary(plan, [])
    order = [
        text.index(word)
        for word in ("Will record", "Sound in", "Left out", "Screen reader", "Saved in")
    ]
    assert order == sorted(order)


# -- validation ------------------------------------------------------------------


def test_studio_process_can_never_be_a_source(tmp_path):
    plan = _on(_plan(tmp_path), "app-msedge.exe")
    plan = replace(
        plan,
        sources=tuple(
            replace(s, process_id=STUDIO_PID) if s.kind == "application" else s
            for s in plan.sources
        ),
    )
    with pytest.raises(DemoRecordingError, match="Studio's own sounds"):
        validate_plan(plan)


@pytest.mark.parametrize(
    "changes",
    [
        {"fps": 25},
        {"size_ceiling": 480},
        {"countdown": 11},
        {"folder": "relative"},
        {"bounds": (0, 0, 0, 0)},
        {"camera": CameraSetup(enabled=True, device="")},
    ],
)
def test_validate_rejects_bad_shapes(tmp_path, changes):
    with pytest.raises(DemoRecordingError):
        validate_plan(_plan(tmp_path, **changes))


def test_validate_accepts_a_good_plan(tmp_path):
    validate_plan(_on(_plan(tmp_path), "microphone"))


# -- 4. The microphone's on state is never persisted ------------------------------


def test_preferences_never_store_the_microphone_on_state(tmp_path):
    plan = _on(_plan(tmp_path), "microphone", "screen-reader", "app-msedge.exe")
    prefs = preferences_from_plan(plan)
    text = json.dumps(prefs)
    mic = next(row for row in prefs["sources"] if row["kind"] == "microphone")
    reader = next(row for row in prefs["sources"] if row["kind"] == "screen_reader")
    assert "enabled" not in mic and "enabled" not in reader
    assert '"Headset"' in text


def test_session_file_never_stores_the_microphone_on_state(tmp_path):
    plan = _on(_plan(tmp_path), "microphone")
    session = SessionRecord(plan=plan_to_dict(plan), output=str(tmp_path / "x.mp4"), started="now")
    session.save(tmp_path)
    raw = json.loads((tmp_path / "session.json").read_text("utf-8"))
    mic = next(row for row in raw["plan"]["sources"] if row["kind"] == "microphone")
    assert "enabled" not in mic


def test_saved_level_is_clamped(tmp_path):
    prefs = {"sources": [{"source_id": "microphone", "level_db": 99}]}
    assert saved_level(prefs, "microphone") == 12.0
    assert saved_level(prefs, "missing", -3.0) == -3.0


# -- 6. Recovery ------------------------------------------------------------------


def test_recovery_finds_and_reloads_a_work_folder(tmp_path):
    plan = _on(_plan(tmp_path), "app-msedge.exe")
    output = tmp_path / "Demo.mp4"
    work = work_folder(output, "abc")
    work.mkdir()
    session = SessionRecord(plan=plan_to_dict(plan), output=str(output), started="2026")
    session.segments.append(SegmentRecord(1, str(work / "seg-001"), video_start=1.0, duration=4.0))
    session.markers.append({"seconds": 2.0, "label": "Edge closed", "failure": True})
    session.save(work)
    (tmp_path / "unrelated").mkdir()
    found = find_unfinished([tmp_path, tmp_path / "missing"])
    assert found == [work]
    loaded = SessionRecord.load(work)
    assert loaded.segments[0].duration == 4.0
    assert plan_from_dict(loaded.plan).source("application").label == "Edge sound"
    assert markers_from_session(loaded).failures[0].label == "Edge closed"


def test_load_rejects_a_folder_without_a_session(tmp_path):
    with pytest.raises(DemoRecordingError):
        SessionRecord.load(tmp_path)


# -- markers and spoken times ------------------------------------------------------


def test_markers_sort_and_format():
    log = MarkerLog()
    log.add(65.25, "second")
    log.add(1.0, "first")
    log.add(70, "", failure=True)
    text = log.text()
    assert text.splitlines()[0] == "00:00:01.0  first"
    assert "Problem: Marker" in text
    assert format_timestamp(3725.5) == "01:02:05.5"


def test_spoken_duration():
    assert spoken_duration(161) == "2 minutes 41 seconds"
    assert spoken_duration(3600) == "1 hour"
    assert spoken_duration(0) == "0 seconds"


# -- every combination of picture and sound -----------------------------------------


def test_nothing_chosen_is_a_stop(tmp_path):
    plan = _plan(tmp_path, screen=False)
    findings = preflight(plan, PreflightFacts(hotkeys_assigned=1))
    assert any("Nothing to record" in text for text in _texts(findings, "Stop"))


def test_sound_only_plan_names_format_and_skips_picture_checks(tmp_path):
    plan = _on(_plan(tmp_path, screen=False, sound_format="flac"), "microphone")
    assert not plan.has_picture and plan.extension == ".flac" and plan.name_label == "Sound"
    findings = preflight(
        plan, PreflightFacts(hotkeys_assigned=1, h264_encoder="", trial_grab_error="no screen")
    )
    assert can_start(findings)
    assert "sound only, saved as FLAC" in summary(plan, findings)
    assert output_size(plan) == (0, 0)
    assert demo_file_name(plan.name_label, datetime(2026, 1, 2, 3, 4, 5), plan.extension).endswith(
        "Sound - 2026-01-02 030405.flac"
    )


def test_camera_fills_when_screen_is_off(tmp_path):
    plan = _plan(
        tmp_path, screen=False, camera=CameraSetup(enabled=True, device="Surface Camera Front")
    )
    assert plan.camera_fills and plan.has_picture and plan.extension == ".mp4"
    assert plan.name_label == "Surface Camera Front"
    assert "camera picture only" in summary(plan, [])
    validate_plan(replace(plan, bounds=(0, 0, 0, 0)))  # no screen target needed


def test_picture_without_sound_warns_and_respects_silent_track(tmp_path):
    plan = _plan(tmp_path)
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("silent soundtrack" in t for t in warns)
    quiet = replace(plan, silent_track=False)
    warns = _texts(preflight(quiet, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("no soundtrack at all" in t for t in warns)
    assert not quiet.has_sound_track


def test_old_camera_only_setting_becomes_screen_off(tmp_path):
    data = plan_to_dict(_plan(tmp_path))
    data["camera"] = {"enabled": True, "device": "Cam", "position": "camera only"}
    plan = plan_from_dict(data)
    assert plan.camera_fills and plan.camera.position == "bottom right"


# -- keep awake and Do Not Disturb (P7) ----------------------------------------------


def test_quiet_options_are_named_and_checked(tmp_path):
    plan = _on(_plan(tmp_path), "microphone")
    assert "kept awake and Do Not Disturb is turned on" in summary(plan, [])
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1, dnd_available=False)), "Warn")
    assert any("did not let Studio control Do Not Disturb" in t for t in warns)
    off = replace(plan, do_not_disturb=False)
    warns = _texts(preflight(off, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("Do Not Disturb is off" in t for t in warns)
    assert "keep_awake" in preferences_from_plan(plan)


def test_whole_sound_card_source_warns_about_the_reader(tmp_path):
    plan = _plan(tmp_path)
    plan = replace(
        plan,
        sources=(
            *plan.sources,
            SoundSource("device", "Everything on Speakers", "card", enabled=True),
        ),
    )
    warns = _texts(preflight(plan, PreflightFacts(hotkeys_assigned=1)), "Warn")
    assert any("whole sound card" in t for t in warns)
    assert "may be heard if it speaks" in screen_reader_sentence(plan)


def test_readiness_warnings_for_long_recordings(tmp_path):
    facts = PreflightFacts(
        hotkeys_assigned=1,
        trial_dropped_share=0.12,
        on_battery=True,
        battery_percent=40,
        battery_minutes=55,
        restart_pending=True,
    )
    warns = _texts(preflight(_on(_plan(tmp_path), "microphone"), facts), "Warn")
    assert any("12 percent of frames were dropped" in t for t in warns)
    assert any("on battery at 40 percent, about 55 minutes left" in t for t in warns)
    assert any("Windows Update is waiting to restart" in t for t in warns)
    quiet = PreflightFacts(hotkeys_assigned=1, trial_dropped_share=0.01)
    assert not any(
        "dropped" in t for t in _texts(preflight(_on(_plan(tmp_path), "microphone"), quiet), "Warn")
    )
