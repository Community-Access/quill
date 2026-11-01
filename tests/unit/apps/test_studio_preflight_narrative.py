"""QUILL Studio's agent tasks: Recording Pre-flight Check and Narrate a Recording
(codex.md 6.1, 6.3 and 6.8, Phase 4c).

The commands, called for real on a real Studio window with the agent window
patched where the shared opener imports it. Then every tool through a real
``FamilyToolRegistry``: reads answer without a question; a picture, the mixer
and the hand-off to QUILL ask with one exact sentence and do nothing when the
answer is no. The screen, FFmpeg, the mixer and QUILL are stand-ins, so nothing
is captured, played or sent, and no sound or video is ever read.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyToolRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity
from quill.core.demo_recording import DemoPlan
from quill.ui.audio_studio.studio_ai_narrative import NARRATE, studio_narrative_tools
from quill.ui.audio_studio.studio_ai_task import PREFLIGHT, studio_preflight_tools

wx = pytest.importorskip("wx")


def _png(width: int = 3000, height: int = 1500) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (10, 120, 200)).save(out, format="PNG")
    return out.getvalue()


# --------------------------------------------------------------------------- #
# The commands, on a real Studio window
# --------------------------------------------------------------------------- #


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

    def __init__(self, connection: str, *, tools: bool, sees: bool = True) -> None:
        self.connection_in_use = connection
        self.tools = tools
        self.sees = sees
        self.harnesses: list[str] = []

    def can_do(self, capability: str) -> bool:
        if capability == "agent_tools":
            return self.tools
        if capability == "pictures":
            return self.sees
        return True

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


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


@pytest.fixture
def studio(quill_data_dir: Path, wx_session_app, closed_machine_doors, monkeypatch):
    from quill.apps.studio import StudioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: True)
    frame = StudioAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    monkeypatch.setattr(type(frame), "_show_ai_window", lambda self, window: None)
    try:
        yield frame
    finally:
        remove = getattr(frame, "_remove_tray_icon", None)
        if callable(remove):
            remove()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


@pytest.mark.parametrize(
    ("command", "title", "starter", "spec"),
    [
        (
            lambda w: w.cmd_ai_task(),
            "Recording Pre-flight Check",
            "Check my set-up before I record",
            PREFLIGHT,
        ),
        (
            lambda w: w.cmd_studio_ai_narrative(),
            "Narrate a Recording",
            "Write an accessible narrative",
            NARRATE,
        ),
    ],
)
def test_on_copilot_each_task_opens_with_its_starter(
    studio, agent_window, monkeypatch, command, title, starter, spec
) -> None:
    service = _Service("copilot", tools=True, sees=False)
    monkeypatch.setattr(studio, "_ai_service", lambda: service)

    command(studio)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == title
    assert hooks.starter.startswith(starter)
    assert "never leave this computer" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is spec
    assert runner.context()
    names = [tool.name for tool in runner.tools()]
    # A connection that cannot see gets no picture tool at all.
    assert not {"studio.preview_still", "studio.contact_sheet"} & set(names)
    assert studio.said == []


@pytest.mark.parametrize(
    "command", [lambda w: w.cmd_ai_task(), lambda w: w.cmd_studio_ai_narrative()]
)
def test_on_a_connection_without_agent_tools_it_sends_nothing(
    studio, agent_window, monkeypatch, command
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(studio, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    command(studio)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


@pytest.mark.parametrize(
    "command", [lambda w: w.cmd_ai_task(), lambda w: w.cmd_studio_ai_narrative()]
)
def test_safe_mode_refuses_both_tasks(studio, agent_window, command) -> None:
    studio._safe_mode = True

    command(studio)

    assert agent_window.last is None
    assert studio.said == ["AI is off in Safe Mode."]


def test_both_rows_are_in_the_ai_menu_on_their_keys(studio) -> None:
    bar = studio.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    labels = [i.GetItemLabel() for i in menu.GetMenuItems() if not i.IsSeparator()]
    preflight = next(label for label in labels if label.startswith("&Recording Pre-flight"))
    narrate = next(label for label in labels if label.startswith("&Narrate a Recording"))
    assert preflight.endswith("\tCtrl+3")
    assert narrate.endswith("\tCtrl+Shift+3")
    assert studio.commands.get("tools.hosted_ai_task") is not None
    assert studio.commands.get("studio.ai_narrative") is not None


def test_the_narrative_row_says_what_it_needs_without_agent_tools(studio) -> None:
    studio._ai_host().settings.ai_connection = "free"
    studio._ai_connection_refresh()
    bar = studio.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    narrate = next(
        i.GetItemLabel() for i in menu.GetMenuItems() if i.GetItemLabel().startswith("&Narrate")
    )
    assert "(needs Copilot or Codex)" in narrate


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
    def __init__(self, apply: bool = True) -> None:
        self.apply = apply
        self.previews: list[tuple[str, str]] = []

    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        self.previews.append((title, text))
        return self.apply

    def note(self, text: str) -> None:
        pass


@pytest.fixture
def consent(monkeypatch):
    import quill.ui.hosted_ai_picture_consent as module

    answers = {"yes": True, "asked": []}

    def ask(host, connection):
        answers["asked"].append(connection)
        return answers["yes"]

    monkeypatch.setattr(module, "ask_picture_consent", ask)
    return answers


_PLAN = DemoPlan(
    target_kind="window",
    target_label="Notepad",
    bounds=(0, 0, 800, 600),
    folder="C:/Videos",
    target_identity="Notepad; process 42",
    window_handle=42,
    process_id=42,
)


def _studio_host(tmp_path: Path, *, sees: bool = True, **extra: Any) -> SimpleNamespace:
    host = SimpleNamespace(
        _studio_last_plan=_PLAN,
        mixers=[],
        opened=[],
        frame=None,
        _studio_last_verification=None,
    )
    host._ai_service = lambda: _Service("chatgpt", tools=True, sees=sees)
    host.open_mixer = lambda: host.mixers.append("mixer")
    host.open_in_quill = lambda *paths: host.opened.extend(paths)
    host._exclude_studio_windows = lambda exclude: None
    for key, value in extra.items():
        setattr(host, key, value)
    return host


def _registry(tools: list, approver: _Approver, agent: str) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity(agent, RiskLevel.LOW),
        app_scope="studio",
    )
    registry.register_app("studio", tools)
    registry.gate.begin_task(approver)
    return registry


def _preflight(host: Any, approver: _Approver, **kw: Any) -> FamilyToolRegistry:
    kw.setdefault("check", lambda: "Will record: Notepad.\nStop: the microphone is held.")
    kw.setdefault(
        "mixer", lambda: "Recording devices:\n- USB headset, the default, level 80 percent."
    )
    tools = studio_preflight_tools(host, _Ctx(), **kw)
    return _registry(tools, approver, "studio-preflight")


def test_read_preflight_is_a_read_with_the_check_and_the_mixer(tmp_path) -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _preflight(_studio_host(tmp_path), approver)

    result = registry.call("studio_read_preflight", {})

    assert result.ok
    assert result.text.splitlines() == [
        "Will record: Notepad.",
        "Stop: the microphone is held.",
        "",
        "The Studio Mixer now:",
        "Recording devices:",
        "- USB headset, the default, level 80 percent.",
    ]
    assert approver.asked == []


def test_the_check_is_record_a_demonstrations_own_on_the_plan_last_checked(
    tmp_path, monkeypatch
) -> None:
    import quill.platform.windows.screen_recorder_check as check
    from quill.core.demo_recording import PreflightFacts

    measured: list[Any] = []
    monkeypatch.setattr(
        check,
        "gather_facts",
        lambda plan, context, scratch: (
            measured.append((plan, context))
            or PreflightFacts(microphone_holder="QUILL Transcribe", display_count=2)
        ),
    )
    host = _studio_host(
        tmp_path,
        _demo_ffmpeg=lambda: "ffmpeg.exe",
        _demo_caps=lambda ffmpeg: "caps",
        _demo_check_context=lambda plan, ffmpeg, caps: ("context", ffmpeg, caps),
    )
    registry = _preflight(host, _Approver(ApprovalChoice.DENY), check=None, mixer=lambda: "")

    result = registry.call("studio_read_preflight", {})

    assert measured == [(_PLAN, ("context", "ffmpeg.exe", "caps"))]
    lines = result.text.splitlines()
    assert lines[0].startswith("Checked now, on the set-up you last checked")
    assert "Will record: Notepad, 800 by 600" in result.text
    assert "Microphone held by: QUILL Transcribe." in result.text
    assert "Displays: 2." in result.text


def test_without_ffmpeg_the_check_says_how_to_get_it(tmp_path) -> None:
    host = _studio_host(tmp_path, _demo_ffmpeg=lambda: None)
    registry = _preflight(host, _Approver(ApprovalChoice.DENY), check=None, mixer=lambda: "")

    result = registry.call("studio_read_preflight", {})

    assert result.ok and "Voices, Get FFmpeg" in result.text


def test_no_picture_tool_where_the_connection_cannot_see(tmp_path) -> None:
    tools = studio_preflight_tools(_studio_host(tmp_path, sees=False), _Ctx(), check=str, mixer=str)
    assert [t.name for t in tools] == ["studio.read_preflight", "studio.open_mixer"]


def test_preview_still_asks_naming_the_target_then_sends_one_fitted_picture(
    tmp_path, consent
) -> None:
    grabbed: list[Any] = []
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _preflight(
        _studio_host(tmp_path), approver, grab=lambda target: grabbed.append(target) or _png()
    )

    result = registry.call("studio_preview_still", {})

    assert approver.asked == ["Take one picture of Notepad and send it to My ChatGPT plan."]
    assert consent["asked"] == ["chatgpt"]
    assert result.ok and result.image is not None
    assert grabbed[0].window_handle == 42
    from PIL import Image

    with Image.open(io.BytesIO(result.image.data)) as picture:
        assert max(picture.size) <= 2048


def test_preview_still_refused_takes_no_picture(tmp_path, consent) -> None:
    grabbed: list[Any] = []
    registry = _preflight(
        _studio_host(tmp_path),
        _Approver(ApprovalChoice.DENY),
        grab=lambda target: grabbed.append(target) or _png(),
    )

    result = registry.call("studio_preview_still", {})

    assert not result.ok and grabbed == [] and consent["asked"] == []


def test_preview_still_without_the_picture_consent_takes_no_picture(tmp_path, consent) -> None:
    consent["yes"] = False
    grabbed: list[Any] = []
    registry = _preflight(
        _studio_host(tmp_path),
        _Approver(ApprovalChoice.ONCE),
        grab=lambda target: grabbed.append(target) or _png(),
    )

    result = registry.call("studio_preview_still", {})

    assert not result.ok and grabbed == []
    assert "not agreed to send pictures" in result.text


def test_open_mixer_asks_then_runs_studios_own_mixer(tmp_path) -> None:
    host = _studio_host(tmp_path)
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _preflight(host, approver)

    result = registry.call("studio_open_mixer", {})

    assert approver.asked == [
        "Open the Studio Mixer, where you can change sound devices and levels yourself."
    ]
    assert result.ok and host.mixers == ["mixer"]
    assert "The Studio Mixer now:" in result.text


def test_open_mixer_refused_opens_nothing(tmp_path) -> None:
    host = _studio_host(tmp_path)
    registry = _preflight(host, _Approver(ApprovalChoice.DENY))

    result = registry.call("studio_open_mixer", {})

    assert not result.ok and host.mixers == []
    assert not registry.mutated()


# -- the narrative -------------------------------------------------------------- #


_SRT = (
    "1\n00:00:05,000 --> 00:00:08,000\nWelcome to the demo.\n\n"
    "2\n00:01:10,000 --> 00:01:12,000\nNow the settings.\n"
)


def _recording(tmp_path: Path, *, captions: bool = True) -> Path:
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"not really a video")
    if captions:
        (tmp_path / "demo.srt").write_text(_SRT, encoding="utf-8")
    return video


def _narrative(host: Any, approver: _Approver, ctx: _Ctx | None = None, **kw: Any):
    kw.setdefault("duration", lambda path: 120.0)
    tools = studio_narrative_tools(host, ctx or _Ctx(), **kw)
    return _registry(tools, approver, "studio-narrative")


def test_transcript_excerpt_reads_the_captions_beside_the_last_recording(tmp_path) -> None:
    video = _recording(tmp_path)
    host = _studio_host(tmp_path, _studio_last_verification=SimpleNamespace(path=str(video)))
    approver = _Approver(ApprovalChoice.DENY)
    registry = _narrative(host, approver)

    result = registry.call("studio_transcript_excerpt", {"start": "0:00", "end": "0:30"})

    assert result.ok
    assert result.text.splitlines() == [
        "What is said from 0:00 to 0:30, from demo.srt:",
        "[0:05] Welcome to the demo.",
    ]
    assert approver.asked == []


def test_no_captions_says_so(tmp_path) -> None:
    video = _recording(tmp_path, captions=False)
    host = _studio_host(tmp_path, _studio_last_verification=SimpleNamespace(path=str(video)))

    result = _narrative(host, _Approver(ApprovalChoice.DENY)).call("studio_transcript_excerpt", {})

    assert not result.ok and "no captions beside demo.mp4" in result.text


def test_without_a_last_recording_studios_chooser_asks_once(tmp_path) -> None:
    video = _recording(tmp_path)
    chose: list[str] = []

    def choose(parent, what, wildcard):
        chose.append(what)
        return str(video)

    host = _studio_host(tmp_path, _choose_media_file=choose)
    registry = _narrative(host, _Approver(ApprovalChoice.DENY))

    registry.call("studio_transcript_excerpt", {})
    registry.call("studio_transcript_excerpt", {"start": "1:00"})

    assert chose == ["Video"]


def test_the_chooser_cancelled_narrates_nothing(tmp_path) -> None:
    host = _studio_host(tmp_path, _choose_media_file=lambda *_a: None)

    result = _narrative(host, _Approver(ApprovalChoice.DENY)).call("studio_transcript_excerpt", {})

    assert not result.ok and "No recording was chosen" in result.text


def test_contact_sheet_asks_naming_the_file_and_stretch_and_caps_the_frames(
    tmp_path, consent
) -> None:
    video = _recording(tmp_path)
    made: list[tuple] = []

    def sheet(ffmpeg, path, part, frames):
        made.append((ffmpeg, path, part.start, part.end, frames))
        return _png(), [12.0, 25.0]

    host = _studio_host(
        tmp_path,
        _studio_last_verification=SimpleNamespace(path=str(video)),
        _demo_ffmpeg=lambda: "ffmpeg.exe",
    )
    approver = _Approver(ApprovalChoice.ONCE)
    registry = _narrative(host, approver, sheet=sheet)

    result = registry.call("studio_contact_sheet", {"start": "0:10", "end": "0:50", "frames": 40})

    assert approver.asked == [
        "Take 16 frames from 0:10 to 0:50 of demo.mp4 as one picture and send it to "
        "My ChatGPT plan."
    ]
    assert made == [("ffmpeg.exe", video, 10.0, 50.0, 16)]
    assert result.ok and result.image is not None
    assert "labelled with its time: 0:12, 0:25." in result.image.description


def test_contact_sheet_refused_takes_no_frames(tmp_path, consent) -> None:
    video = _recording(tmp_path)
    made: list = []
    host = _studio_host(
        tmp_path,
        _studio_last_verification=SimpleNamespace(path=str(video)),
        _demo_ffmpeg=lambda: "ffmpeg.exe",
    )
    registry = _narrative(
        host,
        _Approver(ApprovalChoice.DENY),
        sheet=lambda *a: made.append(a) or (_png(), [1.0]),
    )

    result = registry.call("studio_contact_sheet", {})

    assert not result.ok and made == [] and consent["asked"] == []


def test_no_contact_sheet_where_the_connection_cannot_see(tmp_path) -> None:
    tools = studio_narrative_tools(_studio_host(tmp_path, sees=False), _Ctx())
    assert [t.name for t in tools] == ["studio.transcript_excerpt", "studio.open_in_quill"]


def test_open_in_quill_asks_previews_saves_beside_the_recording_and_opens_it(tmp_path) -> None:
    video = _recording(tmp_path)
    (tmp_path / "demo narrative.md").write_text("an older one", encoding="utf-8")
    host = _studio_host(tmp_path, _studio_last_verification=SimpleNamespace(path=str(video)))
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _narrative(host, approver, ctx)
    text = "# Demo\n\nOverview.\n\n## 0:05 Welcome\nThe presenter says hello."

    result = registry.call("studio_open_in_quill", {"text": text})

    assert approver.asked == [
        "Save the narrative as demo narrative (2).md beside demo.mp4 and open it in QUILL."
    ]
    assert ctx.previews == [("Narrative of demo.mp4, to save as demo narrative (2).md", text)]
    saved = tmp_path / "demo narrative (2).md"
    assert result.ok
    assert saved.read_text(encoding="utf-8") == text + "\n"
    assert host.opened == [str(saved)]
    assert (tmp_path / "demo narrative.md").read_text(encoding="utf-8") == "an older one"


def test_open_in_quill_not_applied_saves_and_opens_nothing(tmp_path) -> None:
    video = _recording(tmp_path)
    host = _studio_host(tmp_path, _studio_last_verification=SimpleNamespace(path=str(video)))
    registry = _narrative(host, _Approver(ApprovalChoice.ONCE), _Ctx(apply=False))

    result = registry.call("studio_open_in_quill", {"text": "# Demo"})

    assert not result.ok and result.text.endswith("The person did not apply it.")
    assert not (tmp_path / "demo narrative.md").exists()
    assert host.opened == []


def test_open_in_quill_refused_shows_nothing(tmp_path) -> None:
    video = _recording(tmp_path)
    host = _studio_host(tmp_path, _studio_last_verification=SimpleNamespace(path=str(video)))
    ctx = _Ctx(apply=True)
    registry = _narrative(host, _Approver(ApprovalChoice.DENY), ctx)

    result = registry.call("studio_open_in_quill", {"text": "# Demo"})

    assert not result.ok and ctx.previews == [] and host.opened == []
    assert not registry.mutated()
