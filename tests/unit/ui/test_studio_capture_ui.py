"""Screenshot chat, consent, artifact identity, and local OCR through native controls."""

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


class Host(StudioCaptureMixin):
    def __init__(self, frame, *, safe=False, consent=wx.NO):
        self.frame = frame
        self._safe_mode = safe
        self.consent = consent
        self.messages = []
        self._task_manager = Tasks()
        self._capture_lifetime = UiLifetimeToken()

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
    from quill.core import assistant_ai
    from quill.core.ai import model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)
    connection = SimpleNamespace(
        provider="openai", model="configured-model", host="https://example.org"
    )
    monkeypatch.setattr(assistant_ai, "load_assistant_connection_settings", lambda: connection)
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _provider: "provider-key")
    monkeypatch.setattr(assistant_ai, "load_assistant_api_key", lambda: "legacy-key")
    return connection


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
    assert not host._task_manager.jobs
    assert not any("Send this complete" in m for m in host.messages)


def test_declining_ai_sends_nothing(chat, connected):
    host, dialog = chat()
    dialog.send(local=False)
    assert not host._task_manager.jobs
    assert any("No automatic redaction" in m for m in host.messages)


def test_chat_keeps_same_artifact_custom_prompt_and_followup(chat, capture, connected, monkeypatch):
    from quill.core.ai import vision

    seen = []

    def describe(connection, key, path, **kwargs):
        seen.append((key, path.read_bytes(), kwargs["prompt"]))
        assert path != Path(capture.path)
        return "Possible overlay; uncertain.", None

    monkeypatch.setattr(vision, "describe_image", describe)
    host, dialog = chat(consent=wx.YES)
    dialog.prompt.ChangeValue("Focus on the error dialog.")
    dialog.question.ChangeValue("What is clipped?")
    dialog.send(local=False)
    _, work, callbacks = host._task_manager.jobs[0]
    callbacks["on_success"]("task", work(cancellation_token=CancellationToken()))
    assert seen[0][0] == "provider-key"
    assert seen[0][1] == Path(capture.path).read_bytes()
    assert "Focus on the error dialog" in seen[0][2]
    assert "What is clipped?" in seen[0][2]
    assert "Possible overlay" in dialog.transcript.GetValue()
    dialog.question.ChangeValue("Where is it?")
    dialog.send(local=False)
    host._task_manager.jobs[1][1](cancellation_token=CancellationToken())
    assert seen[1][1] == seen[0][1]
    assert "Possible overlay" in seen[1][2]
    assert "Where is it?" in seen[1][2]


def test_replaced_screenshot_cannot_be_sent(chat, capture, connected, monkeypatch):
    from quill.core.ai import vision

    monkeypatch.setattr(vision, "describe_image", lambda *a, **k: pytest.fail("network called"))
    host, dialog = chat(consent=wx.YES)
    dialog.send(local=False)
    Image.new("RGB", (20, 30), "red").save(capture.path)
    with pytest.raises(ValueError, match="changed"):
        host._task_manager.jobs[0][1](cancellation_token=CancellationToken())


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
    assert saved[-1]["approved_connection"]["host"] == "https://example.org"
    assert not host._task_manager.jobs


def test_revoking_automatic_permission_blocks_queued_upload(chat, connected, monkeypatch):
    from quill.core import studio_capture_ai as ai
    from quill.core.ai import vision

    host, dialog = chat(consent=wx.YES)
    preferences = {
        "auto_ai_enabled": True,
        "approved_connection": ai.connection_identity(connected),
    }
    monkeypatch.setattr(ai, "load_capture_ai_preferences", lambda: preferences)
    monkeypatch.setattr(
        vision, "describe_image", lambda *a, **k: pytest.fail("Upload after revocation")
    )
    host._maybe_auto_inspect(dialog.evidence)
    assert len(host._task_manager.jobs) == 1
    preferences["auto_ai_enabled"] = False
    with pytest.raises(RuntimeError, match="permission changed"):
        host._task_manager.jobs[0][1](cancellation_token=CancellationToken())


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
    preferences["approved_connection"] = ai.connection_identity(connected)
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
