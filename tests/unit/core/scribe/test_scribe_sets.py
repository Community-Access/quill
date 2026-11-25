"""Named sets of Scribe documents (2026-11-24): the family core and the queue.

The name check and its sentences, the folders, the log (one timestamped
line per event, appended), the row's percent sentence, a set recorded in
the queue file beside its jobs, and a set that carries on after the app was
closed writing to the same log and finishing once.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from quill.core import batch_sets as bs
from quill.core.scribe import queue as q
from quill.core.scribe import sets
from quill.core.scribe.runner import QueueService, default_channel_opener
from tests.unit.core.scribe.fake_scribe import BASE, FakeClock, FakeScribe, StaticTokens

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ")


# ------------------------------------------------------------- the name


def test_the_default_name_counts_the_files_and_says_the_day() -> None:
    assert bs.default_set_name(34, datetime(2026, 11, 24, 10, 0)) == "Set of 34, Nov 24"


@pytest.mark.parametrize(
    ("name", "words"),
    [
        ("", "Type a name"),
        ("   ", "Type a name"),
        ("Board packet.", "cannot end with a dot or a space"),
        ("Board packet ", "cannot end with a dot or a space"),
        ("Board: packet?", "cannot contain :, ?"),
        ("a/b", "cannot contain /"),
        ("CON", "Windows keeps for itself"),
        ("nul", "Windows keeps for itself"),
        ("LPT1.txt", "Windows keeps for itself"),
        ("x" * 101, "up to 100"),
    ],
)
def test_a_name_windows_refuses_gets_one_plain_sentence(
    tmp_path: Path, name: str, words: str
) -> None:
    problem = bs.name_problem(name, tmp_path)
    assert words in problem
    assert problem.endswith(".") and "Error" not in problem
    with pytest.raises(ValueError):
        bs.create_set_folder(name, tmp_path)
    assert not any(tmp_path.iterdir())  # nothing made


def test_a_name_a_folder_already_has_is_refused(tmp_path: Path) -> None:
    (tmp_path / "Board packet").mkdir()
    problem = bs.name_problem("Board packet", tmp_path)
    assert problem.startswith("A folder called Board packet is already in")
    assert bs.name_problem("Board packet 2", tmp_path) == ""
    made = bs.create_set_folder("Board packet 2", tmp_path)
    assert made.is_dir() and made.name == "Board packet 2"


def test_each_document_gets_its_own_folder_name() -> None:
    names = bs.member_folder_names(["Notes.pdf", "notes.docx", "CON.pdf", "a:b.pdf"])
    assert names == ["Notes", "notes (2)", "CON_", "a_b"]


# ---------------------------------------------------------------- the log


def test_each_log_line_starts_with_the_local_time(tmp_path: Path) -> None:
    when = datetime(2026, 11, 24, 10, 42, 7).timestamp()
    log = bs.SetLog(tmp_path, clock=lambda: when)
    log.append("Queued: Notes.pdf.")
    log.append("Uploaded:\nNotes.pdf.")  # one event is always one line
    text = (tmp_path / bs.LOG_NAME).read_bytes().decode("utf-8")
    assert text == (
        "2026-11-24 10:42:07 Queued: Notes.pdf.\n2026-11-24 10:42:07 Uploaded: Notes.pdf.\n"
    )
    bs.SetLog(tmp_path).append("Finished: Notes.pdf.")  # appended, never rewritten
    assert log.read().count("\n") == 3


def test_the_lines_say_what_happened_in_plain_words() -> None:
    assert bs.duration_words(125) == "2 minutes 5 seconds"
    assert bs.duration_words(3780) == "1 hour 3 minutes"
    assert bs.duration_words(0.2) == "under a second"
    assert bs.document_finished_line("A.pdf", 61) == "Finished: A.pdf in 1 minute 1 second."
    assert bs.document_failed_line("A.pdf", "You need more pages.") == (
        "Failed: A.pdf. Reason: You need more pages."
    )
    line = bs.set_finished_line(
        "Board", done=1, failed_names=["B.pdf"], seconds=90, retry_hint="Retry it."
    )
    assert line == (
        "Set Board finished in 1 minute 30 seconds: 1 done, 1 failed. Not made: B.pdf. Retry it."
    )


def test_the_percent_counts_finished_documents() -> None:
    assert (
        bs.progress_sentence("Board packet", done=12, failed=0, total=34)
        == "Board packet: 12 of 34 done, 35 percent"
    )
    assert (
        bs.progress_sentence("Board packet", done=12, failed=1, total=34)
        == "Board packet: 12 of 34 done, 38 percent, 1 failed"
    )


def test_a_set_record_keeps_fields_a_newer_app_added() -> None:
    made = bs.BatchSet.from_mapping({"id": "s", "name": "N", "colour": "blue"})
    assert made is not None and made.to_dict()["colour"] == "blue"


def test_the_core_knows_no_one_service() -> None:
    source = Path(bs.__file__).read_text(encoding="utf-8")
    assert "scribe" not in source.lower().split('"""', 2)[2]
    assert "import wx" not in source


# --------------------------------------------------------- the Scribe side


def _client(server: FakeScribe):  # noqa: ANN202
    from quill.core.scribe.client import ScribeClient

    return ScribeClient(
        StaticTokens(server), base_url=BASE, transport=server.transport, sleep=lambda _s: None
    )


def _service(server: FakeScribe, tmp_path: Path, events: list) -> QueueService:
    clock = FakeClock()
    server.clock = clock
    return QueueService(
        "QUILL",
        queue=q.FamilyQueue(tmp_path / "scribe", now=clock),
        client_factory=lambda: _client(server),
        channel_opener=default_channel_opener(server.connector),
        download_root=lambda: str(tmp_path / "out"),
        listener=lambda kind, job: events.append((kind, job)),
        sleep=clock.sleep,
        clock=clock,
    )


def _jobs(tmp_path: Path, *names: str) -> list[q.Job]:
    made = []
    for name in names:
        source = tmp_path / name
        source.write_bytes(b"%PDF fake")
        made.append(q.Job(file_name=name, source_path=str(source), formats=["docx"]))
    return made


def _queue_set(service: QueueService, tmp_path: Path, *names: str) -> bs.BatchSet:
    folder = bs.create_set_folder("Board packet", tmp_path / "out")
    jobs = _jobs(tmp_path, *names)
    made = sets.start_set("Board packet", folder, jobs, app="QUILL", now=service.queue.now())
    service.queue.add(jobs, batch_set=made)
    return made


def _log_lines(made: bs.BatchSet) -> list[str]:
    lines = made.log().read().splitlines()
    assert all(STAMP.match(line) for line in lines), lines
    return [STAMP.sub("", line) for line in lines]


def test_a_set_runs_logs_each_event_and_finishes_once(tmp_path: Path) -> None:
    server = FakeScribe()
    events: list = []
    service = _service(server, tmp_path, events)
    made = _queue_set(service, tmp_path, "A.pdf", "B.pdf")
    stored = json.loads((tmp_path / "scribe" / "queue.json").read_text(encoding="utf-8"))
    assert stored["sets"][0]["name"] == "Board packet"  # every app sees it
    assert stored["sets"][0]["members"] == [j["id"] for j in stored["jobs"]]
    while service.tick():
        pass
    service.tick()
    jobs = service.queue.batch_jobs(made.id)
    assert [Path(j.folder).name for j in jobs] == ["A", "B"]
    assert all(Path(j.folder).parent == Path(made.folder) for j in jobs)
    assert all(Path(p).exists() for j in jobs for p in j.outputs.values())
    lines = _log_lines(made)
    assert lines[0] == "Set Board packet started: 2 documents, formats Word."
    assert lines[1:3] == ["Queued: A.pdf.", "Queued: B.pdf."]
    assert "Uploaded: A.pdf." in lines and "Conversion started: B.pdf." in lines
    assert any(line.startswith("Finished: A.pdf in ") for line in lines)
    assert lines[-1].startswith("Set Board packet finished in ")
    assert lines[-1].endswith(": 2 done, 0 failed.")
    assert [k for k, _ in events].count("set_done") == 1
    service.tick()  # nothing more: a set finishes once
    assert [k for k, _ in events].count("set_done") == 1


def test_a_failed_document_is_logged_with_its_reason_and_how_to_retry(tmp_path: Path) -> None:
    server = FakeScribe()
    server.needs_purchase = True
    events: list = []
    service = _service(server, tmp_path, events)
    made = _queue_set(service, tmp_path, "A.pdf", "B.pdf")
    while service.tick():
        pass
    service.tick()
    lines = _log_lines(made)
    assert "Failed: A.pdf. Reason: You need more pages." in lines
    assert lines[-1].startswith("Set Board packet finished")
    assert "0 done, 2 failed. Not made: A.pdf and B.pdf." in lines[-1]
    assert "Retry Failed" in lines[-1]
    assert "Traceback" not in made.log().read()


def test_a_file_error_is_logged_without_the_exception_text(tmp_path: Path) -> None:
    job = q.Job(
        file_name="A.pdf", state=q.FAILED, message="A file could not be read or written: [Errno 13]"
    )
    assert sets.plain_reason(job) == "a file could not be read or written on this computer"


def test_a_set_carries_on_after_the_app_was_closed(tmp_path: Path) -> None:
    """The queue survives a restart: the next app's runner adds to the same
    log and writes the set's last line."""
    server = FakeScribe()
    first_events: list = []
    first = _service(server, tmp_path, first_events)
    made = _queue_set(first, tmp_path, "A.pdf", "B.pdf")
    first.tick()  # A done; then the app closes with B queued
    first.stop()
    before = _log_lines(made)
    assert any(line.startswith("Finished: A.pdf") for line in before)
    assert not any(line.startswith("Set Board packet finished") for line in before)
    events: list = []
    again = _service(server, tmp_path, events)
    again.note_resumed()
    while again.tick():
        pass
    again.tick()
    after = _log_lines(made)
    assert after[: len(before)] == before  # appended, never rewritten
    assert any(line.startswith("Finished: B.pdf") for line in after)
    assert after[-1].endswith(": 2 done, 0 failed.")
    assert [k for k, _ in events].count("set_done") == 1


def test_stopping_the_last_document_finishes_the_set(tmp_path: Path) -> None:
    server = FakeScribe()
    events: list = []
    service = _service(server, tmp_path, events)
    made = _queue_set(service, tmp_path, "A.pdf", "B.pdf")
    for job in service.queue.batch_jobs(made.id):
        service.queue.update(job.id, state=q.STOPPED, message="Stopped waiting")
    service.tick()
    assert [k for k, _ in events].count("set_done") == 1
    assert "Not made: A.pdf and B.pdf." in _log_lines(made)[-1]


def test_removing_a_set_takes_its_documents_but_leaves_its_folder(tmp_path: Path) -> None:
    queue = q.FamilyQueue(tmp_path / "scribe")
    folder = bs.create_set_folder("Board packet", tmp_path / "out")
    jobs = _jobs(tmp_path, "A.pdf", "B.pdf")
    made = sets.start_set("Board packet", folder, jobs, app="QUILL")
    queue.add(jobs, batch_set=made)
    queue.add(_jobs(tmp_path, "C.pdf"))
    assert queue.remove_set(made.id)
    assert [j.file_name for j in queue.jobs()] == ["C.pdf"] and queue.sets() == []
    assert (folder / bs.LOG_NAME).exists()
