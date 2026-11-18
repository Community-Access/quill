"""Hearing a diff: Changed Lines Only and a sound per added or removed line (PRD 22.12)."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.github.diff_lines import LINE_SOUNDS, changed_only, line_sound, parse_diff_lines
from quill.core.sound_events import SoundEvent

PACKS = Path(__file__).resolve().parents[4] / "quill" / "assets" / "sound_packs"


def test_changed_only_keeps_headings_and_changes() -> None:
    lines = parse_diff_lines("@@ -1,3 +1,3 @@\n keep\n-old\n+new\n same\n")
    kept = [lines[index].kind for index in changed_only(lines)]
    assert kept == ["hunk", "removed", "added"]


def test_each_change_has_its_sound_and_context_has_none() -> None:
    lines = parse_diff_lines("@@ -1 +1 @@\n-old\n+new\n keep\n")
    assert [line_sound(line) for line in lines] == [
        "",
        "diff_line_removed",
        "diff_line_added",
        "",
    ]


def test_the_sounds_are_real_events_with_clips_in_both_packs() -> None:
    events = {event.value for event in SoundEvent}
    for sound in LINE_SOUNDS.values():
        assert sound in events
        for pack in ("ink", "vscode_signals"):
            manifest = json.loads((PACKS / pack / "manifest.json").read_text(encoding="utf-8"))
            assert (PACKS / pack / manifest["events"][sound]).is_file()
