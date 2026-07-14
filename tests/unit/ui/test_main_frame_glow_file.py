"""Behavioral tests for the GLOW structured-file commands (GlowFileMixin).

The mixin is wx-free at module scope, so it is driven headless here with a
fake host: a stub ``_wx``, a synchronous task manager, and recording
implementations of the MainFrame surface it wires over. These pin the
contract that matters to a screen-reader user: reports open as named tabs,
outcomes are announced, and a fix never touches the original file.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.glow import GlowFileAuditResult, GlowFileFixResult, GlowFinding
from quill.ui.main_frame_glow import GlowFileMixin, glow_fixed_copy_path


class _FakeWx(SimpleNamespace):
    ID_OK = 1
    ID_CANCEL = 2
    YES = 5103
    NO = 5104
    ICON_ERROR = 512
    ICON_INFORMATION = 2048
    OK = 4
    YES_NO = 10
    FD_OPEN = 1
    FD_FILE_MUST_EXIST = 16


class _FakeDialog:
    def __init__(self, path: str) -> None:
        self._path = path

    def GetPath(self) -> str:
        return self._path

    def Destroy(self) -> None:
        pass


class _SyncTaskManager:
    """Runs the submitted func immediately and fires callbacks inline."""

    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, name, func, *, on_success=None, on_failure=None, **kwargs):
        self.submitted.append(name)
        try:
            result = func()
        except BaseException as exc:  # noqa: BLE001 - mirrors QuillTaskManager
            if on_failure is not None:
                on_failure("op", exc)
            return SimpleNamespace(operation_id="op")
        if on_success is not None:
            on_success("op", result)
        return SimpleNamespace(operation_id="op")


class _Host(GlowFileMixin):
    def __init__(self, picked: Path | None, answer: int | None = None) -> None:
        self._wx = _FakeWx()
        self.frame = object()
        self._task_manager = _SyncTaskManager()
        self._picked = picked
        self._answer = answer if answer is not None else self._wx.YES
        self.tabs: list[tuple[str, str]] = []
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.message_boxes: list[str] = []
        self.notifications: list[tuple[str, str]] = []

    # --- MainFrame surface -------------------------------------------------
    def _ensure_glow_enabled(self) -> bool:
        # The real MainFrame gates every GLOW command behind the Experimental
        # opt-in; the fake host defaults to enabled and tests override it.
        return getattr(self, "glow_enabled_gate", True)

    def _show_modal_dialog(self, dialog, _title):
        return self._wx.ID_OK if self._picked is not None else self._wx.ID_CANCEL

    def _show_message_box(self, message, _title, _style):
        self.message_boxes.append(message)
        return self._answer

    def _create_named_scratch_tab(self, title, text):
        self.tabs.append((title, text))

    def _set_status(self, message):
        self.statuses.append(message)

    def _announce(self, message):
        self.announcements.append(message)

    def _record_notification(self, message, category):
        self.notifications.append((message, category))

    # FileDialog is constructed on self._wx, so intercept it there.
    def _glow_pick_file(self, title):
        if self._picked is None:
            self._set_status(f"{title} cancelled")
            return None
        return self._picked


def _audit_result(path: str) -> GlowFileAuditResult:
    return GlowFileAuditResult(
        path=path,
        score=88,
        grade="B",
        findings=(
            GlowFinding(
                rule_id="GLOW-TEST",
                severity="warning",
                message="Example finding.",
                suggestion="Fix it.",
            ),
        ),
        backend="glow",
    )


def test_fixed_copy_path_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "report.docx"
    source.write_bytes(b"x")
    first = glow_fixed_copy_path(source)
    assert first.name == "report-accessible.docx"
    first.write_bytes(b"y")
    second = glow_fixed_copy_path(source)
    assert second.name == "report-accessible-2.docx"
    assert first != source and second != source


def test_audit_file_opens_report_tab_and_announces(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "deck.pptx"
    source.write_bytes(b"x")
    host = _Host(picked=source)
    import quill.core.glow as glow

    monkeypatch.setattr(glow, "audit_file", lambda p, **kw: _audit_result(str(p)))
    host.glow_audit_file()
    assert host._task_manager.submitted == ["glow-audit-file"]
    assert len(host.tabs) == 1
    title, body = host.tabs[0]
    assert "deck.pptx" in title
    assert "GLOW-TEST" in body
    assert any("score 88" in item and "grade B" in item for item in host.announcements)


def test_audit_file_cancelled_picker_is_quiet(tmp_path: Path) -> None:
    host = _Host(picked=None)
    host.glow_audit_file()
    assert host._task_manager.submitted == []
    assert host.tabs == []
    assert any("cancelled" in status for status in host.statuses)


def test_fix_file_confirms_and_reports_new_copy(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "letter.docx"
    source.write_bytes(b"original")
    host = _Host(picked=source)
    import quill.core.glow as glow

    def _fake_fix(path, output, **kwargs):
        return GlowFileFixResult(
            output_path=str(output),
            total_fixes=3,
            audit=_audit_result(str(path)),
            warnings=("One table was left for manual review.",),
            backend="glow",
        )

    monkeypatch.setattr(glow, "fix_file", _fake_fix)
    host.glow_fix_file()
    # The consent prompt named the non-destructive output path.
    assert any("letter-accessible.docx" in box for box in host.message_boxes)
    assert host._task_manager.submitted == ["glow-fix-file"]
    assert source.read_bytes() == b"original"
    title, body = host.tabs[0]
    assert "letter.docx" in title
    assert "Applied fixes: 3" in body
    assert "manual review" in body
    assert any("3 fixes" in item for item in host.announcements)


def test_fix_file_declined_consent_does_nothing(tmp_path: Path) -> None:
    source = tmp_path / "letter.docx"
    source.write_bytes(b"original")
    host = _Host(picked=source, answer=_FakeWx.NO)
    host.glow_fix_file()
    assert host._task_manager.submitted == []
    assert host.tabs == []


def test_gated_glow_commands_do_nothing_when_experimental_flag_off(tmp_path: Path) -> None:
    source = tmp_path / "report.docx"
    source.write_bytes(b"x")
    host = _Host(picked=source)
    host.glow_enabled_gate = False
    host.glow_audit_file()
    host.glow_fix_file()
    assert host._task_manager.submitted == []
    assert host.tabs == []
    assert source.read_bytes() == b"x"


def test_audit_failure_shows_error_not_crash(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"x")
    host = _Host(picked=source)
    import quill.core.glow as glow

    def _boom(path, **kwargs):
        raise ValueError("unreadable file")

    monkeypatch.setattr(glow, "audit_file", _boom)
    host.glow_audit_file()
    assert host.tabs == []
    assert any("unreadable file" in box for box in host.message_boxes)
    assert any("failed" in status for status in host.statuses)
