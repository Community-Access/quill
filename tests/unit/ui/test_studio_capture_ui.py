"""Screenshot chat, consent, artifact identity, and local OCR through native controls.

A screenshot question goes to the connection in use in Choose Your AI (codex.md
Phase 3), through the shared service; here that service is a stand-in, so
nothing leaves the machine.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
import wx
from PIL import Image

from quill.apps.studio_capture import StudioCaptureMixin
from quill.core.studio_capture import CaptureTarget, verify_capture
from quill.stability.task_manager import CancellationToken, UiLifetimeToken
from quill.ui.studio_capture_chat import ScreenshotChatDialog
from quill.ui.studio_capture_dialog import CaptureSetupDialog


class Tasks:
    def __init__(self):
        self.jobs = []

    def submit(self, name, work, **kwargs):
        self.jobs.append((name, work, kwargs))
        return SimpleNamespace(cancellation_token=CancellationToken())

    def run(self, index=-1):
        """Finish a queued job the way the task manager would."""
        _name, work, callbacks = self.jobs[index]
        callbacks["on_success"]("task", work(cancellation_token=CancellationToken()))


class Service:
    """The connection in use, as the shared service answers for it."""

    def __init__(self, connection="chatgpt", model="vision-model"):
        self.connection_in_use = connection
        self.model = model
        self.own_key_provider = "openai"
        self.direct = True
        self.sent = []
        self.answer = "Possible overlay; uncertain."

    def can_do(self, capability):
        return self.capability_record(self.connection_in_use).claim(capability).supported

    def connection_model(self, connection=""):
        return self.model

    def capability_record(self, connection=""):
        from quill.core.ai.connection_caps import record_for

        return record_for(connection or self.connection_in_use)

    def describe_image(self, path, question, *, on_done, on_error, requires):
        self.sent.append((Path(path).read_bytes(), question, requires))
        on_done(self.answer)


class Host(StudioCaptureMixin):
    def __init__(self, frame, *, safe=False, consent=wx.NO):
        self.frame = frame
        self._safe_mode = safe
        self.consent = consent
        self.messages = []
        self._task_manager = Tasks()
        self._capture_lifetime = UiLifetimeToken()
        self.service = Service()

    def _ai_service(self):
        return self.service

    def _show_message_box(self, message, _title, _style):
        self.messages.append(message)
        return self.consent

    def _set_status(self, message):
        self.messages.append(message)

    _announce = _set_status


@pytest.fixture
def capture(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    path = tmp_path / "screen.png"
    Image.new("RGB", (20, 30), "white").save(path)
    return verify_capture(path, "screen")


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


@pytest.fixture
def connected(monkeypatch):
    from quill.core.ai import model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)


@pytest.fixture
def chat(parent, capture):
    created = []

    def make(**kwargs):
        host = Host(parent, **kwargs)
        dialog = ScreenshotChatDialog(host, capture)
        created.append(dialog)
        return host, dialog

    yield make
    for dialog in created:
        dialog.stop_delivery()
        dialog.Destroy()


def test_capture_setup_has_named_native_fields(parent):
    dialog = CaptureSetupDialog(
        parent,
        "C:/captures",
        [
            CaptureTarget("desktop", "Full desktop", (0, 0, 1920, 1080)),
            CaptureTarget("region", "Numeric rectangle"),
        ],
    )
    try:
        assert dialog.target.GetName() == "Target"
        assert dialog.delay.GetValue() == 5
        assert dialog.folder.GetName() == "Save folder"
        assert dialog.GetEscapeId() == wx.ID_CANCEL
    finally:
        dialog.Destroy()


def test_editing_starts_simple_and_keeps_exact_geometry_under_advanced(parent, capture):
    from quill.ui.studio_capture_editor import ScreenshotEditorDialog

    host = Host(parent)
    dialog = ScreenshotEditorDialog(host, capture)
    try:
        assert not dialog.position.GetParent().IsShown()
        assert dialog.action.GetStringSelection() == "Keep only this area"
        assert "SHA-256" not in dialog.plan.GetValue()
        dialog.action.SetSelection(1)
        dialog._add(None)
        assert len(host._task_manager.jobs) == 1
        _, work, callbacks = host._task_manager.jobs[0]
        result = work(cancellation_token=CancellationToken())
        callbacks["on_success"](None, result)
        assert dialog.project.operations[0]["kind"] == "redact"
        assert not dialog.busy
        assert "Hide private information" in dialog.plan.GetValue()
    finally:
        dialog.stop()
        dialog.Destroy()


def test_safe_mode_never_offers_network_send(chat, connected):
    host, dialog = chat(safe=True, consent=wx.YES)
    dialog.send(local=False)
    assert not host._task_manager.jobs and not host.service.sent
    assert not any("Send this complete" in m for m in host.messages)


def test_declining_the_picture_consent_sends_nothing(chat, connected):
    host, dialog = chat()
    dialog.send(local=False)
    assert not host._task_manager.jobs and not host.service.sent
    assert any(
        m.startswith("Pictures you ask about in QUILL Studio go to OpenAI on your ChatGPT plan")
        for m in host.messages
    )


def test_a_connection_that_cannot_see_is_offered_the_switch_and_sends_nothing(
    chat, connected, monkeypatch
):
    host, dialog = chat(consent=wx.YES)
    host.service.connection_in_use = "free"
    offered = []
    host.service.capability_offer = lambda capability: SimpleNamespace(
        sentence="Pictures need a connection that can see.", target="", open_row=""
    )
    host._announce = offered.append
    dialog.send(local=False)
    assert offered == ["Pictures need a connection that can see."]
    assert not host._task_manager.jobs and not host.service.sent


def test_chat_keeps_same_artifact_custom_prompt_and_followup(chat, capture, connected):
    host, dialog = chat(consent=wx.YES)
    dialog.prompt.ChangeValue("Focus on the error dialog.")
    dialog.question.ChangeValue("What is clipped?")
    dialog.send(local=False)
    assert any("Send this complete screenshot to My ChatGPT plan" in m for m in host.messages)
    host._task_manager.run(0)
    data, prompt, requires = host.service.sent[0]
    assert requires == ("text", "pictures")
    with Image.open(capture.path) as original:
        assert original.size == (20, 30)
    assert data  # the fitted copy of the very screenshot that was verified
    assert "Focus on the error dialog" in prompt and "What is clipped?" in prompt
    assert "Possible overlay" in dialog.transcript.GetValue()
    assert "AI (My ChatGPT plan, vision-model)" in dialog.transcript.GetValue()
    dialog.question.ChangeValue("Where is it?")
    dialog.send(local=False)
    host._task_manager.run(1)
    assert host.service.sent[1][0] == data
    assert "Possible overlay" in host.service.sent[1][1]
    assert "Where is it?" in host.service.sent[1][1]
    # The picture consent is asked once per connection, not with every screenshot.
    assert len([m for m in host.messages if m.startswith("Pictures you ask about")]) == 1


def test_replaced_screenshot_cannot_be_sent(chat, capture, connected):
    host, dialog = chat(consent=wx.YES)
    dialog.send(local=False)
    Image.new("RGB", (20, 30), "red").save(capture.path)
    _name, work, _callbacks = host._task_manager.jobs[0]
    with pytest.raises(ValueError, match="changed"):
        work(cancellation_token=CancellationToken())
    assert not host.service.sent


def test_local_ocr_works_in_safe_mode(chat, monkeypatch):
    from quill.io import ocr

    monkeypatch.setattr(
        ocr, "ocr_image", lambda path: SimpleNamespace(engine="windows", text="Hello")
    )
    host, dialog = chat(safe=True)
    dialog.send(local=True)
    text = host._task_manager.jobs[0][1](cancellation_token=CancellationToken())
    assert "Local OCR" in text and "Hello" in text
    assert "not reported" in text


def test_double_send_does_not_duplicate_network_requests(chat, connected):
    host, dialog = chat(consent=wx.YES)
    dialog.send(local=False)
    dialog.send(local=False)
    assert len(host._task_manager.jobs) == 1
    assert dialog.question.IsEnabled()


def test_auto_ai_requires_separate_explicit_consent(chat, connected, monkeypatch):
    import quill.ui.studio_capture_chat as ui

    saved = []
    monkeypatch.setattr(ui, "save_capture_ai_preferences", lambda prefs: saved.append(dict(prefs)))
    host, dialog = chat(consent=wx.NO)
    dialog.automatic.SetValue(True)
    dialog._set_automatic(None)
    assert not saved and not dialog.automatic.GetValue()
    host.consent = wx.YES
    dialog.automatic.SetValue(True)
    dialog._set_automatic(None)
    assert saved[-1]["auto_ai_enabled"] is True
    assert saved[-1]["approved_connection"] == {
        "provider": "chatgpt",
        "host": "OpenAI on your ChatGPT plan",
        "model": "vision-model",
    }
    assert any("Connection: My ChatGPT plan" in m for m in host.messages)
    assert not host._task_manager.jobs


def test_revoking_automatic_permission_blocks_queued_upload(chat, connected, monkeypatch):
    from quill.core import studio_capture_ai as ai

    host, dialog = chat(consent=wx.YES)
    preferences = {
        "auto_ai_enabled": True,
        "approved_connection": ai.connection_identity(host._studio_picture_route()),
    }
    monkeypatch.setattr(ai, "load_capture_ai_preferences", lambda: preferences)
    host._maybe_auto_inspect(dialog.evidence)
    assert len(host._task_manager.jobs) == 1
    preferences["auto_ai_enabled"] = False
    with pytest.raises(RuntimeError, match="permission changed"):
        host._task_manager.jobs[0][1](cancellation_token=CancellationToken())
    assert not host.service.sent


def test_a_changed_connection_pauses_automatic_analysis(chat, connected, monkeypatch):
    from quill.core import studio_capture_ai as ai

    host, dialog = chat(consent=wx.YES)
    preferences = {
        "auto_ai_enabled": True,
        "approved_connection": ai.connection_identity(host._studio_picture_route()),
    }
    monkeypatch.setattr(ai, "load_capture_ai_preferences", lambda: preferences)
    host.service.connection_in_use = "own_key"  # a different company now
    host.service.own_key_provider = "gemini"
    host._maybe_auto_inspect(dialog.evidence)
    assert not host._task_manager.jobs
    assert any("Automatic screenshot AI is paused" in m for m in host.messages)


def test_paused_automatic_ai_is_said_once_not_with_every_screenshot(chat, connected, monkeypatch):
    # Kelly Ford's Quick Describe: a lasting limitation is said once, not per result.
    from quill.core import studio_capture_ai as ai

    host, dialog = chat(consent=wx.YES)
    preferences = {"auto_ai_enabled": True, "approved_connection": {"host": "elsewhere"}}
    monkeypatch.setattr(ai, "load_capture_ai_preferences", lambda: preferences)
    host.messages.clear()
    host._maybe_auto_inspect(dialog.evidence)
    host._maybe_auto_inspect(dialog.evidence)
    paused = [m for m in host.messages if "Automatic screenshot AI is paused" in m]
    assert len(paused) == 1 and not host._task_manager.jobs
    preferences["approved_connection"] = ai.connection_identity(host._studio_picture_route())
    host._maybe_auto_inspect(dialog.evidence)
    assert host._auto_ai_pause_said is False


def test_refresh_does_not_replace_missing_window_with_desktop(parent, monkeypatch):
    from quill.platform.windows import studio_capture as platform

    desktop = CaptureTarget("desktop", "Full desktop", (0, 0, 1920, 1080))
    window = CaptureTarget("window", "Intended editor", (0, 0, 100, 100), 12, 34)
    dialog = CaptureSetupDialog(parent, "C:/captures", [desktop, window])
    try:
        dialog.target.SetSelection(1)
        monkeypatch.setattr(platform, "list_capture_targets", lambda **_kw: [desktop])
        dialog._refresh_targets(None)
        selected = dialog.selected_target()
        assert selected.kind == "window" and selected.window_handle == 12
        assert "Unavailable" in selected.label
    finally:
        dialog.Destroy()


def test_guided_region_needs_no_pixel_values_and_explains_clipping(parent):
    desktop = CaptureTarget("desktop", "Full desktop", (0, 0, 1920, 1080))
    window = CaptureTarget("window", "My document", (100, 100, 900, 700), 12, 34)
    dialog = CaptureSetupDialog(
        parent,
        "C:/captures",
        [
            desktop,
            window,
            CaptureTarget("region", "Guided region"),
        ],
    )
    try:
        dialog.target.SetSelection(2)
        dialog._update_region()
        assert not dialog.advanced.GetValue()
        assert not dialog.numeric_panel.IsShown()
        assert dialog.selected_target().bounds == window.bounds
        assert dialog.region_source.GetName() == "Region source"
        dialog.portion.SetSelection(1)
        dialog._update_guidance()
        assert dialog.selected_target().bounds == (100, 100, 900, 400)
        assert "may cut off words or controls" in dialog.guidance.GetValue()
        assert "overlapping windows" in dialog.guidance.GetValue()
    finally:
        dialog.Destroy()


def test_advanced_coordinates_are_optional_and_invalid_values_explained(parent):
    dialog = CaptureSetupDialog(
        parent,
        "C:/captures",
        [
            CaptureTarget("desktop", "Full desktop", (0, 0, 1920, 1080)),
            CaptureTarget("region", "Guided region"),
        ],
    )
    try:
        dialog.target.SetSelection(1)
        dialog.advanced.SetValue(True)
        dialog.coordinates[0].SetValue(5000)
        dialog._update_region()
        assert dialog.numeric_panel.IsShown()
        assert "Cannot capture this region" in dialog.guidance.GetValue()
        with pytest.raises(ValueError):
            dialog.selected_target()
    finally:
        dialog.Destroy()
