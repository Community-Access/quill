"""Scribe for Documents, the rest of QUILL and QUILL Lite: the wx-free parts.

The streamed blocks (only whole blocks, plain text), the runner telling the
streaming tab the preview has ended, the watch-folder action (consent per
profile, the 23 types only, through the family queue one at a time, sign-in
said once per profile, the result as a watch outcome), a watch file taking the
account defaults, the entry point's own format winning, and QUILL Lite's
feature area and rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core import scribe
from quill.core.scribe import queue as q
from quill.core.scribe.stream import BlockAssembler, block_at, block_lines, offset_of_block
from quill.core.watch_actions import WatchItem, default_registry
from quill.core.watch_scribe import WATCH_OPEN_AS, ScribeConvertAction
from tests.unit.core.scribe.fake_scribe import FakeScribe
from tests.unit.core.scribe.test_scribe_core import _job, _service

# ------------------------------------------------------------ the stream


def test_only_complete_blocks_come_out_however_the_chunks_are_cut() -> None:
    blocks = BlockAssembler()
    assert blocks.push("<h1>Chap") == []
    assert blocks.push("ter one</h1><p>First para") == ["Chapter one"]
    assert blocks.push("graph.</p><ul><li>One</l") == ["First paragraph."]
    assert blocks.push("i><li>Two</li></ul>") == ["One", "Two"]
    assert blocks.finish() == []


def test_blocks_are_plain_text_with_cells_on_one_line_and_alt_text_kept() -> None:
    blocks = BlockAssembler()
    out = blocks.push(
        "<style>p{}</style><table><tr><th>Name</th><td>Age</td></tr></table>"
        '<p>A <b>bold</b>   word <img alt="a red bird"> here</p>'
    )
    assert out == ["Name, Age", "A bold word a red bird here"]
    assert not any("#" in b or "*" in b for b in out)


def test_what_is_left_when_the_stream_ends_is_the_last_block() -> None:
    blocks = BlockAssembler()
    assert blocks.push("<p>Half a para") == []
    assert blocks.finish() == ["Half a para"]


def test_blocks_go_after_existing_text_with_a_blank_line() -> None:
    assert block_lines(["One", "Two"], after_text=False) == "One\n\nTwo"
    assert block_lines(["Three"], after_text=True) == "\n\nThree"
    assert block_lines([], after_text=True) == ""


def test_the_reading_place_is_matched_by_words_not_by_index() -> None:
    stream = "Intro\n\nThe second paragraph is here.\n\nEnd"
    caret = stream.index("second") + 3
    anchor = block_at(stream, caret)
    assert anchor == "The second paragraph is here."
    finished = "A title Scribe added\n\nIntro\n\nThe second   paragraph\nis here.\n\nEnd"
    assert finished[offset_of_block(finished, anchor) :].startswith("The second")
    assert offset_of_block(finished, "not there at all") == 0


def test_the_runner_says_when_the_free_preview_has_ended(
    tmp_path: Path,
) -> None:
    server = FakeScribe()
    server.in_progress_once = True  # the html_stream preview runs first
    server.chunks = ["<h1>Notes</h1>", "<p>Body</p>"]
    events: list = []
    service = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    service.tick()
    kinds = [kind for kind, _ in events]
    assert kinds.count("chunk") == 2
    assert "stream_done" in kinds and kinds.index("stream_done") > kinds.index("chunk")
    assert service.queue.jobs()[0].state == q.DONE


# ---------------------------------------------------------- watch folder


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(scribe, "CLIENT_ID", "test-client")
    return tmp_path


class _Runner:
    """Stands in for the app's queue runner: finishes each job as it is woken."""

    def __init__(self, queue: q.FamilyQueue, end_state: str = q.DONE, **fields: Any) -> None:
        self.queue = queue
        self.end_state = end_state
        self.fields = fields
        self.woken = 0

    def wake(self) -> None:
        self.woken += 1
        for job in self.queue.jobs():
            if job.state == q.QUEUED:
                self.queue.update(job.id, state=self.end_state, **self.fields)


def _action(queue: q.FamilyQueue, runner: _Runner, signed_in: bool = True) -> ScribeConvertAction:
    return ScribeConvertAction(
        on_wake=runner.wake,
        signed_in=lambda: signed_in,
        queue_factory=lambda: queue,
        sleep=lambda _s: None,
    )


def _arriving(folder: Path, name: str = "Scan.pdf") -> WatchItem:
    path = folder / name
    path.write_bytes(b"%PDF-1.4 scan")
    return WatchItem(source_path=path, profile_id="inbox")


def test_the_action_is_registered_and_needs_per_profile_consent(isolated: Path) -> None:
    registry = default_registry()
    action = registry.get("scribe_convert")
    assert action is not None and action.requires_consent
    assert action.label == "Convert with Scribe for Documents"
    outcome = registry.run("scribe_convert", _arriving(isolated), {"formats": ["docx"]})
    assert outcome.status == "skipped" and "consent" in outcome.message


def test_a_file_goes_through_the_family_queue_and_the_result_is_the_outcome(
    isolated: Path,
) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    out = isolated / "Scan.docx"
    out.write_bytes(b"docx")
    runner = _Runner(queue, outputs={"docx": str(out)}, folder=str(isolated))
    outcome = _action(queue, runner).run(_arriving(isolated), {"formats": ["docx", "brf"]})
    assert runner.woken == 1
    job = queue.jobs()[0]
    assert job.open_as == WATCH_OPEN_AS and job.formats == ["docx", "brf"]
    assert outcome.status == "done" and "Scan.docx" in outcome.message
    assert outcome.result_path == out


def test_only_the_23_types_are_sent(isolated: Path) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    runner = _Runner(queue)
    page = isolated / "page.html"
    page.write_text("<p>web</p>")
    outcome = _action(queue, runner).run(WatchItem(source_path=page, profile_id="p"), {})
    assert outcome.status == "skipped" and queue.jobs() == [] and runner.woken == 0


def test_sign_in_is_said_once_per_profile_not_once_a_file(isolated: Path) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    action = _action(queue, _Runner(queue), signed_in=False)
    first = action.run(_arriving(isolated, "a.pdf"), {})
    second = action.run(_arriving(isolated, "b.pdf"), {})
    assert first.status == "failed" and "sign in" in first.message
    assert second.status == "skipped"  # recorded, not said again
    assert queue.jobs() == []


def test_a_file_that_needs_its_password_waits_without_a_dialog(isolated: Path) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    outcome = _action(queue, _Runner(queue, q.NEEDS_PASSWORD)).run(_arriving(isolated), {})
    assert outcome.status == "failed" and "Open Scribe Conversions" in outcome.message
    assert queue.jobs()[0].state == q.NEEDS_PASSWORD  # still waiting there


def test_a_failure_names_scribe_and_the_file(isolated: Path) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    runner = _Runner(queue, q.FAILED, message="Server trouble")
    outcome = _action(queue, runner).run(_arriving(isolated), {})
    assert outcome.status == "failed"
    assert outcome.message == "Scribe for Documents could not convert Scan.pdf: Server trouble"


def test_a_slow_file_lets_the_folder_move_on(isolated: Path) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    ticks = iter(range(0, 10_000, 1000))
    action = ScribeConvertAction(
        on_wake=lambda: None,
        signed_in=lambda: True,
        queue_factory=lambda: queue,
        sleep=lambda _s: None,
        clock=lambda: float(next(ticks)),
        wait_limit_s=2500.0,
    )
    outcome = action.run(_arriving(isolated), {})
    assert outcome.status == "skipped" and "Scribe Conversions" in outcome.message


def test_safe_mode_and_empty_formats_are_refused(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    action = ScribeConvertAction()
    assert action.validate({"formats": []})
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert "Safe Mode" in action.validate({})[0]


def test_the_dry_run_says_what_would_be_sent_and_that_it_costs_pages(isolated: Path) -> None:
    preview = ScribeConvertAction().preview(_arriving(isolated), {"formats": ["brf"]})
    assert "Scan.pdf" in preview and "Braille" in preview and "pages" in preview


def test_a_watch_file_starts_from_the_account_defaults(tmp_path: Path) -> None:
    server = FakeScribe()
    server.account_defaults.update({"language": "fr", "tts_rate": 2.0})
    service = _service(server, tmp_path)
    job = _job(tmp_path, open_as=WATCH_OPEN_AS, settings={"tts_rate": 1.5})
    client = service._client_factory()
    merged = service._watch_settings(client, job)
    assert merged is not None and merged.language == "fr" and merged.tts_rate == 1.5


def test_the_command_s_own_format_wins_over_the_last_choice() -> None:
    from quill.core.scribe.options import ScribeOptions

    options = ScribeOptions(last_formats=["docx"], default_formats=["html"])
    assert options.formats_for(["brf"]) == ["brf"]  # Translate with Scribe is braille
    assert options.formats_for(None) == ["docx"]
    assert ScribeOptions().formats_for(None) == ["docx"]


# ----------------------------------------------------------- QUILL Lite


def test_the_scribe_area_is_off_by_default_and_on_only_in_everything() -> None:
    from quill.core.lite.features import AREAS, DEFAULT_OFF, PROFILES

    ids = {area.id for area in AREAS}
    assert "scribe" in ids and "scribe" in DEFAULT_OFF and len(ids) == 26
    on = {p.id: "scribe" not in p.disabled for p in PROFILES}
    assert on == {
        "recommended": False,
        "everything": True,
        "developer": False,
        "wordpad": False,
        "notepad": False,
    }
    counts = {p.id: len(ids - set(p.disabled)) for p in PROFILES}
    assert counts == {
        "recommended": 19,
        "everything": 25,
        "developer": 20,
        "wordpad": 6,
        "notepad": 3,
    }
    for profile in PROFILES:  # each profile's own sentence carries its count
        assert "of the 26 areas" in profile.description, profile.id


def test_an_existing_store_gets_scribe_off_once(tmp_path: Path) -> None:
    from quill.core.app_features import load_app_features, save_app_features
    from quill.core.lite.features import APP_ID, load_features

    seeded = load_app_features(tmp_path, APP_ID)
    seeded.disabled |= {"_seeded", "_seeded_coding", "_seeded_forms_payments"}
    save_app_features(tmp_path, seeded)
    assert "scribe" in load_features(tmp_path).disabled
    again = load_features(tmp_path)
    again.disabled.discard("scribe")
    save_app_features(tmp_path, again)
    assert "scribe" not in load_features(tmp_path).disabled  # a later "on" sticks


def test_lite_rows_sit_in_one_file_submenu_and_leave_with_the_area() -> None:
    from quill.core.lite.command_areas import visible_commands
    from quill.core.lite.commands_scribe import SCRIBE_EQUIVALENTS, SCRIBE_ROWS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    handlers = {row[3] for row in SCRIBE_ROWS if row[3]}
    assert handlers | {"cmd_scribe_window"} == set(SCRIBE_EQUIVALENTS)
    for handler, quill_id in SCRIBE_EQUIVALENTS.items():
        assert COMMAND_EQUIVALENTS[handler] == quill_id
    shown = {row[3] for row in visible_commands(lambda area: True)}
    hidden = {row[3] for row in visible_commands(lambda area: area != "scribe")}
    assert set(SCRIBE_EQUIVALENTS) <= shown
    assert not set(SCRIBE_EQUIVALENTS) & hidden


def test_quill_has_every_command_lite_has() -> None:
    """Rule 10: every Lite Scribe row is a QUILL command too."""
    from quill.core.lite.commands_scribe import SCRIBE_EQUIVALENTS
    from quill.ui.main_frame_scribe import ROWS

    quill_ids = {row[0] for row in ROWS}
    assert set(SCRIBE_EQUIVALENTS.values()) <= quill_ids


def test_a_watch_retry_reports_the_job_scribe_has_rather_than_uploading_again(
    isolated: Path,
) -> None:
    queue = q.FamilyQueue(isolated / "scribe")
    runner = _Runner(queue, q.FAILED, message="Server trouble")
    action = _action(queue, runner)
    item = _arriving(isolated)
    first = action.run(item, {})
    again = action.run(item, {})  # the watch queue retries a failed item
    assert first.status == again.status == "failed"
    assert len(queue.jobs()) == 1  # sent once, never paid for twice


def test_every_quill_scribe_row_is_in_the_keymap_with_no_chord() -> None:
    """Assignable in the Keymap Editor, and what Lite's parity table maps onto."""
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.scribe.keys import COMMAND_IDS
    from quill.ui.main_frame_scribe import ROWS

    assert {row[0] for row in ROWS} == set(COMMAND_IDS)
    assert all(DEFAULT_KEYMAP[command_id] == "" for command_id in COMMAND_IDS)


def test_replace_with_finished_document_sits_in_the_scribe_submenu() -> None:
    from quill.ui.main_frame_scribe import ROWS

    place = {row[0]: row[3] for row in ROWS}
    assert place["scribe.replace_finished"] == "tools"  # File has no letter left
