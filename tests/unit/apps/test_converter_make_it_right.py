"""Make This Right for My Player, Quill Converter's agent task (codex.md 6.7, Phase 4c).

Two halves. The command, called for real on a real Quill Converter window, with
the agent window patched where the shared opener imports it
(``quill.ui.agent_window``). Then every tool through a real
``FamilyToolRegistry`` on that window: the reads answer as text without a
question, and the job asks with the files, format, bit rate and chapters, sets
the window's own choices and starts through Converter's own commands -- or
does nothing when refused. ffprobe and FFmpeg are stand-ins, so nothing runs.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.converter_ai_task import APP, MAKE_IT_RIGHT, converter_task_tools  # noqa: E402
from quill.core.ai.activity_log import ActivityLog  # noqa: E402
from quill.core.ai.approvals import ApprovalChoice  # noqa: E402
from quill.core.ai.family_tools import FamilyToolRegistry  # noqa: E402
from quill.core.ai.permissions import PermissionBroker, RiskLevel  # noqa: E402
from quill.core.ai.tool_gateway import AgentIdentity  # noqa: E402

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Window:
    last: dict | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).last = {"args": args, "kwargs": kwargs}

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args: Any, **_kwargs: Any):  # noqa: N802 - wx API shape
        pass


class _Service:
    signed_in = True
    direct = True

    def __init__(self, connection: str, *, tools: bool) -> None:
        self.connection_in_use = connection
        self.tools = tools
        self.harnesses: list[str] = []

    def can_do(self, capability: str) -> bool:
        return capability != "agent_tools" or self.tools

    def needs_label(self, capability: str) -> str:
        return "" if self.can_do(capability) else "(needs Copilot or Codex)"

    def agent_harness(self, connection: str) -> object:
        self.harnesses.append(connection)
        return object()

    def capability_offer(self, capability: str) -> Any:
        from quill.core.ai.connection_caps import SwitchOffer

        return SwitchOffer(
            "Agent tasks need a connection that runs tasks. My GitHub Copilot can. "
            "Switch to it and ask?",
            target="copilot",
        )


def _info(path: Path):
    from quill.core.audio.media_probe import MediaInfo, StreamInfo

    return MediaInfo(
        path=path,
        container="mp3",
        duration_s=600.0,
        size_bytes=9_000_000,
        streams=(StreamInfo("audio", "mp3", sample_rate=44100, channels=2),),
    )


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


@pytest.fixture
def converter(quill_data_dir: Path, wx_session_app, tmp_path: Path, monkeypatch):
    from quill.apps import converter as app
    from quill.core import converter_settings
    from quill.core.audio import media_probe

    monkeypatch.setattr(
        converter_settings, "settings_path", lambda _d=None: tmp_path / "converter.json"
    )
    monkeypatch.setattr(app, "_find_ffmpeg", lambda: None)
    monkeypatch.setattr(app, "available_output_formats", lambda _f: ["mp3", "m4b", "wav", "mp4"])
    monkeypatch.setattr(media_probe, "probe", lambda path, **_kw: _info(path))
    frame = app.QuillConverterFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    frame.boxes = []
    frame._show_message_box = lambda message, *_a, **_kw: frame.boxes.append(message)
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: None)
    try:
        yield frame
    finally:
        frame._busy = False
        frame._ipc_timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def _queue(frame, tmp_path: Path, *names: str) -> list[Path]:
    folder = tmp_path / "Book"
    folder.mkdir(exist_ok=True)
    paths = []
    for name in names:
        path = folder / name
        path.write_bytes(b"x")
        paths.append(path)
    frame.add_paths(paths, announce=False)
    return paths


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


def test_on_copilot_it_opens_on_converters_tools(converter, agent_window, monkeypatch) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(converter, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(converter)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Make This Right for My Player"
    assert hooks.starter == ""
    assert "never their sound" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is MAKE_IT_RIGHT
    assert runner.context().startswith("Queue: 0 items.")
    assert [tool.name for tool in runner.tools()] == [
        "converter.list_queue",
        "converter.probe",
        "converter.list_formats",
        "converter.queue_job",
    ]
    assert converter.said == []


def test_on_a_connection_without_agent_tools_it_sends_nothing(
    converter, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(converter, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(converter)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_safe_mode_refuses_it(converter, agent_window, monkeypatch) -> None:
    monkeypatch.setattr(converter, "_ai_service", lambda: _Service("copilot", tools=True))
    converter._safe_mode = True

    (lambda w: w.cmd_ai_task())(converter)

    assert agent_window.last is None
    assert any("Safe Mode" in said for said in converter.said)


def test_the_row_is_in_the_ai_menu_on_ctrl_f3(converter) -> None:
    bar = converter.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    labels = [item.GetItemLabel() for item in menu.GetMenuItems()]
    # No agent connection yet, so the row says what it needs (codex.md 10A.8).
    assert "&Make This Right for My Player (needs Copilot or Codex)...\tCtrl+F3" in labels
    assert converter.commands.get("tools.hosted_ai_task") is not None


# --------------------------------------------------------------------------- #
# The tools, through a real registry
# --------------------------------------------------------------------------- #


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


class _Ctx:
    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        raise AssertionError("a job asks; it has no text to preview")

    def note(self, text: str) -> None:
        pass


def _registry(host: Any, approver: _Approver) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("converter-make-it-right", RiskLevel.LOW),
        app_scope=APP,
    )
    registry.register_app(APP, converter_task_tools(host, _Ctx()))
    registry.gate.begin_task(approver)
    return registry


def test_the_reads_answer_as_text_without_asking(converter, tmp_path) -> None:
    _queue(converter, tmp_path, "01 Intro.mp3", "02 Chapter.mp3")
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(converter, approver)

    queue = registry.call("converter_list_queue", {})
    probed = registry.call("converter_probe", {"file": "F2"})
    formats = registry.call("converter_list_formats", {})

    assert queue.text.splitlines()[:3] == [
        "2 files queued:",
        "F1. 01 Intro.mp3",
        "F2. 02 Chapter.mp3",
    ]
    assert "Convert would make now:" in queue.text
    assert str(tmp_path) not in queue.text  # file names, never folders
    assert probed.text.splitlines()[0] == "File: 02 Chapter.mp3"
    assert "- m4b:" in formats.text and "chapters written into the file" in formats.text
    assert "- audiobook:" in formats.text
    assert "Bit rates in kbps: 96, 128, 192, 256, 320" in formats.text
    assert approver.asked == []
    assert not registry.mutated()


def test_an_unknown_file_is_explained(converter, tmp_path) -> None:
    _queue(converter, tmp_path, "a.mp3")
    registry = _registry(converter, _Approver(ApprovalChoice.DENY))

    result = registry.call("converter_probe", {"file": "F9"})

    assert not result.ok and "converter_list_queue" in result.text


def test_join_asks_with_the_files_format_bitrate_and_chapters_then_starts(
    converter, tmp_path, monkeypatch
) -> None:
    import quill.apps.converter_chapters as chapters

    _queue(converter, tmp_path, "01 Intro.mp3", "02 Chapter.mp3", "03 End.mp3")
    started: list[Any] = []
    monkeypatch.setattr(converter, "_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        chapters,
        "threading",
        SimpleNamespace(Thread=lambda **kw: SimpleNamespace(start=lambda: started.append(kw))),
    )
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(converter, approver)

    result = registry.call(
        "converter_queue_job",
        {
            "action": "join",
            "format": "m4b",
            "preset": "audiobook",
            "bitrate_kbps": 96,
            "file_name": "My Book",
        },
    )

    (question,) = approver.asked
    assert question.startswith("Join 3 files (01 Intro.mp3, 02 Chapter.mp3, 03 End.mp3) into one")
    assert "Audiobook (M4B) preset, at 96 kbps" in question
    assert question.endswith("with a chapter for each file.")
    assert result.ok and result.text.startswith("Started: Join 3 files")
    assert len(started) == 1 and converter._busy
    # The window shows what ran: its own choices were set.
    assert converter._chosen_format() == "m4b"
    assert converter._chosen_preset_id() == "audiobook"
    assert (tmp_path / "Book" / "Converted").is_dir()
    assert registry.mutated()


def test_convert_runs_through_convert_now(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3", "b.mp3")
    ran: list[Any] = []
    monkeypatch.setattr(converter, "_ffmpeg", lambda: "ffmpeg")

    def run_jobs(ffmpeg, jobs, label, dest, *, notes=""):
        ran.append((len(jobs), jobs[0].spec.fmt, jobs[0].spec.bitrate_kbps))
        converter._busy = True

    monkeypatch.setattr(converter, "_run_jobs", run_jobs)
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(converter, approver)

    result = registry.call(
        "converter_queue_job",
        {"action": "convert", "format": "mp3", "preset": "mp3_128", "chapters": "keep"},
    )

    assert approver.asked == [
        "Convert 2 files (a.mp3, b.mp3) to MP3 audio, MP3 128 kbps (small) preset, at the "
        "preset's bit rate. Chapter marks: keep each file's own chapters."
    ]
    assert result.ok
    assert ran == [(2, "mp3", 128)]


def test_refused_starts_nothing_and_changes_no_choice(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3", "b.mp3")
    monkeypatch.setattr(converter, "_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(converter, "_run_jobs", lambda *a, **k: pytest.fail("ran"))
    before = converter._chosen_format()
    registry = _registry(converter, _Approver(ApprovalChoice.DENY))

    result = registry.call("converter_queue_job", {"action": "convert", "format": "m4b"})

    assert not result.ok
    assert converter._chosen_format() == before
    assert not converter._busy


def test_a_job_that_does_not_start_is_reported(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3", "b.mp3")
    monkeypatch.setattr(converter, "_ffmpeg", lambda: "ffmpeg")
    registry = _registry(converter, _Approver(ApprovalChoice.TASK))

    split = registry.call("converter_queue_job", {"action": "split", "format": "mp3"})
    joined_video = registry.call("converter_queue_job", {"action": "join", "format": "mp4"})
    alone = registry.call("converter_queue_job", {"action": "convert", "format": "flac"})

    assert not split.ok and "did not start" in split.text
    assert converter.boxes and "chapters" in converter.boxes[0]  # Split said why itself
    assert not joined_video.ok and joined_video.text.startswith("Join makes one sound file")
    assert not alone.ok and "converter_list_formats" in alone.text
