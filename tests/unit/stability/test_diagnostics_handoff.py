"""The support handoff checked at its final form, not at its preview.

Regression tests for the shared-diagnostics review (plan.md, "Shared
diagnostics and background-runtime review", 2026-11):

* a credential in an exception's text reached the crash email's *subject*,
  although the preview and the body were clean;
* a long active-task name made the diagnostic bundle's ``metadata.json``
  invalid, because the serialized JSON was redacted line by line and every
  line cut at 200 characters;
* a long subject produced a 4,735-character ``mailto:`` URL against the
  1,800-character limit, because only the body was ever shortened;
* :class:`~quill.stability.wx_dispatch.CoalescedUiReporter` deadlocked when
  its synchronous fallback took the lock ``report`` already held, and
  stranded a final value reported inside the throttle interval;
* :meth:`~quill.stability.task_manager.TaskManager.cancel` returned False for
  a running ``safe_to_cancel=False`` task after it had already signalled it.

Every credential here is synthetic. Nothing is sent: the mail program launch
and the clipboard are replaced with recorders.
"""

from __future__ import annotations

import json
import threading
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.support_message import (
    MAILTO_URL_LIMIT,
    SupportMessage,
    build_mailto_url,
    build_subject,
)
from quill.stability import wx_dispatch as wx_dispatch_module
from quill.stability.crash_email import build_crash_support_message
from quill.stability.crash_report import build_diagnostic_bundle
from quill.stability.crash_submit import build_crash_report_payload
from quill.stability.task_manager import TaskManager
from quill.stability.wx_dispatch import CoalescedUiReporter

NEWLINE = chr(10)

#: A made-up credential. Never a real one.
SYNTHETIC_SECRET = "hunter2-synthetic-7Q"


def _crash_payload(message: str):
    try:
        raise RuntimeError(message)
    except RuntimeError as exc:
        return build_crash_report_payload(
            exc_type=type(exc),
            exc_value=exc,
            exc_tb=exc.__traceback__,
            local_crash_file=None,
            app_version="9.8.7",
            portable=False,
            screen_reader_name="NVDA",
            recent_commands=["file.save"],
            active_document=None,
        )


def _decoded(url: str) -> dict[str, str]:
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    return {key: values[0] for key, values in query.items()}


# ---------------------------------------------------------------------------
# 1. The crash email subject, and every other outbound field
# ---------------------------------------------------------------------------


def test_a_credential_in_the_exception_never_reaches_the_crash_subject() -> None:
    payload = _crash_payload(f"login failed: password={SYNTHETIC_SECRET}")

    assert SYNTHETIC_SECRET not in payload.summary
    assert payload.summary.startswith("RuntimeError")
    message = build_crash_support_message(
        summary=payload.summary, body=payload.body, app_version="9.8.7"
    )
    url, _shortened = build_mailto_url(message)
    fields = _decoded(url)
    assert SYNTHETIC_SECRET not in fields["subject"]
    assert SYNTHETIC_SECRET not in fields["body"]


def test_the_support_message_redacts_every_field_a_caller_hands_it() -> None:
    # A caller that forgot to redact its summary, or a support fact that
    # carries a path, is caught at the last step before the mail program.
    message = build_crash_support_message(
        summary=f"token={SYNTHETIC_SECRET}",
        body="ok\n",
        app_version="1.0",
        platform_name=r"Windows C:\Users\someone\AppData",
        screen_reader_name=f"NVDA api_key={SYNTHETIC_SECRET}",
        extra={"Note": f"secret={SYNTHETIC_SECRET}", "Log": r"C:\Users\someone\quill.log"},
    )
    every_field = " ".join([
        message.product,
        message.summary,
        message.message,
        message.platform,
        message.screen_reader,
        *message.extra.keys(),
        *message.extra.values(),
    ])
    assert SYNTHETIC_SECRET not in every_field
    assert r"C:\Users\someone" not in every_field


class _Host:
    frame = None

    def __init__(self) -> None:
        self.copied: list[str] = []
        self.spoken: list[str] = []

    def _announce(self, text: str) -> None:
        self.spoken.append(text)

    def _copy_to_clipboard(self, text: str) -> bool:
        self.copied.append(text)
        return True

    def ai_support_facts(self) -> dict[str, str]:
        return {"Detail": f"password={SYNTHETIC_SECRET}"}


@pytest.mark.parametrize("mail_program_answers", [True, False])
def test_the_final_crash_handoff_carries_no_credential(monkeypatch, mail_program_answers) -> None:
    import quill.ui.support_dialog as support_dialog
    from quill.ui.crash_report_dialog import CrashReportDialogResult
    from quill.ui.crash_report_mail import act_on_crash_choice

    launched: list[str] = []
    monkeypatch.setattr(
        support_dialog, "_launch", lambda url: launched.append(url) or mail_program_answers
    )
    monkeypatch.setattr(support_dialog, "_message_box", lambda *_a, **_k: None)
    # Long enough that the URL is shortened and the full text goes to the
    # clipboard too, so both outbound routes are checked.
    payload = _crash_payload(f"bad password={SYNTHETIC_SECRET} " + "x" * 3000)
    host = _Host()

    act_on_crash_choice(
        payload,
        CrashReportDialogResult(
            act="send", what_doing_text=NEWLINE.join(["Saving the chapter again"] * 80)
        ),
        host,
        copy=host._copy_to_clipboard,
        notify=lambda _text: None,
        find_window=lambda: None,
    )

    assert launched
    for url in launched:
        assert len(url) <= MAILTO_URL_LIMIT
        assert SYNTHETIC_SECRET not in url
        assert SYNTHETIC_SECRET not in " ".join(_decoded(url).values())
    assert host.copied
    for text in host.copied:
        assert SYNTHETIC_SECRET not in text


def test_the_crash_copy_route_is_redacted_too() -> None:
    from quill.ui.crash_report_dialog import CrashReportDialogResult
    from quill.ui.crash_report_mail import act_on_crash_choice

    copied: list[str] = []
    payload = _crash_payload("plain failure")
    # A dialog that handed over an unredacted field must not reach the
    # clipboard with it.
    act_on_crash_choice(
        payload,
        CrashReportDialogResult(act="copy", what_doing_text=f"token={SYNTHETIC_SECRET}"),
        None,
        copy=lambda text: copied.append(text) or True,
        notify=lambda _text: None,
        find_window=lambda: None,
    )
    assert copied
    assert SYNTHETIC_SECRET not in copied[0]


# ---------------------------------------------------------------------------
# 2. metadata.json stays valid JSON, whatever the task names are
# ---------------------------------------------------------------------------


def _task(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        operation_id="op-1",
        name=name,
        started_at=1.0,
        timeout_seconds=None,
        safe_to_cancel=True,
        safe_to_kill=False,
        submitted_at=2.0,
        result_summary="pending",
    )


def test_a_long_task_name_leaves_metadata_json_valid(tmp_path: Path) -> None:
    long_name = "Open " + "The Long Winter, chapter twelve. " * 20 + "end"
    bundle = build_diagnostic_bundle(
        task_snapshot=[_task(long_name)],
        output_path=tmp_path / "bundle.zip",
    )
    with zipfile.ZipFile(bundle) as archive:
        metadata = json.loads(archive.read("metadata.json").decode("utf-8"))
    name = metadata["active_tasks"][0]["name"]
    assert name.startswith("Open The Long Winter")
    assert len(name) < len(long_name)


def test_a_secret_or_path_in_a_task_name_is_redacted_and_json_still_parses(
    tmp_path: Path,
) -> None:
    bundle = build_diagnostic_bundle(
        task_snapshot=[
            _task(f"Sync password={SYNTHETIC_SECRET}"),
            _task(r"Open C:\Users\someone\Documents\diary.txt"),
            _task("Bearer " + SYNTHETIC_SECRET),
        ],
        enabled_plugins=[r"C:\Users\someone\plugins\x"],
        feature_flags={"core.search": True},
        output_path=tmp_path / "bundle.zip",
    )
    with zipfile.ZipFile(bundle) as archive:
        raw = archive.read("metadata.json").decode("utf-8")
    metadata = json.loads(raw)
    assert SYNTHETIC_SECRET not in raw
    assert r"C:\Users\someone" not in raw
    assert len(metadata["active_tasks"]) == 3
    assert metadata["feature_flags"] == {"core.search": True}


# ---------------------------------------------------------------------------
# 3. Every field of the mailto URL is bounded, Unicode included
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "summary",
    [
        "x" * 4000,
        "é" * 1500,  # six encoded characters each
        "名前" * 600,  # nine each
        "\U0001f600" * 500,  # an emoji is twelve
    ],
    ids=["ascii", "accented", "cjk", "emoji"],
)
def test_a_long_subject_still_fits_the_mailto_limit(summary: str) -> None:
    message = SupportMessage(product="QUILL", summary=summary, message="short body")
    url, shortened = build_mailto_url(message)
    assert shortened
    assert len(url) <= MAILTO_URL_LIMIT
    fields = _decoded(url)  # still decodes: no character was split
    assert fields["subject"].startswith("[QUILL] ")
    assert "complete text is on your clipboard" in fields["body"]


def test_a_long_reply_address_and_facts_still_fit_the_limit() -> None:
    message = SupportMessage(
        product="Quill Radio " + "ü" * 400,
        summary="ok",
        message="m" * 2000,
        extra={"Fact " + str(i): "ß" * 200 for i in range(10)},
    )
    url, shortened = build_mailto_url(message)
    assert shortened
    assert len(url) <= MAILTO_URL_LIMIT
    _decoded(url)


def test_a_short_message_is_not_touched() -> None:
    message = SupportMessage(product="QUILL", summary="Crash", message="Body")
    url, shortened = build_mailto_url(message)
    assert not shortened
    assert _decoded(url)["subject"] == "[QUILL] Crash"


def test_the_clipboard_fallback_keeps_the_whole_subject(monkeypatch) -> None:
    import quill.ui.support_dialog as support_dialog

    monkeypatch.setattr(support_dialog, "_launch", lambda _url: True)
    host = _Host()
    message = SupportMessage(product="QUILL", summary="long " * 500, message="body")
    assert support_dialog.send_by_mail(host, message)
    assert host.copied
    assert build_subject(message) in host.copied[0]


# ---------------------------------------------------------------------------
# 4. The coalescing reporter, and TaskManager.cancel
# ---------------------------------------------------------------------------


def test_the_coalescer_does_not_deadlock_when_wx_is_absent(monkeypatch) -> None:
    # No wx.CallAfter: call_ui_safely runs the flush synchronously on the
    # reporting thread, which used to take the lock report() still held.
    monkeypatch.setattr(wx_dispatch_module, "wx", None)
    seen: list[int] = []
    reporter = CoalescedUiReporter(seen.append, min_interval_seconds=0.0)

    worker = threading.Thread(target=reporter.report, args=(1,), daemon=True)
    worker.start()
    worker.join(2.0)

    assert not worker.is_alive(), "report() deadlocked on its own lock"
    assert seen == [1]


def test_the_coalescer_delivers_a_final_value_reported_inside_the_interval(monkeypatch) -> None:
    # A stand-in for wx.CallAfter that runs the callback later, on another
    # thread, so this test sees the stranded value and not the deadlock above.
    def call_after(callback, *args, **kwargs):
        threading.Thread(target=callback, args=args, kwargs=kwargs, daemon=True).start()

    monkeypatch.setattr(wx_dispatch_module, "call_ui_safely", call_after)
    seen: list[int] = []
    reporter = CoalescedUiReporter(seen.append, min_interval_seconds=0.05)

    reporter.report(1)
    reporter.report(2)  # inside the interval: must not be stranded
    reporter.report(3)

    deadline = time.monotonic() + 2.0
    while seen[-1:] != [3] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert seen[0] == 1
    assert seen[-1] == 3
    assert 2 not in seen  # coalesced away, as designed


def test_the_coalescer_still_delivers_latest_only_through_callafter(monkeypatch) -> None:
    scheduled: list[object] = []
    monkeypatch.setattr(
        wx_dispatch_module,
        "call_ui_safely",
        lambda callback, *args, **kwargs: scheduled.append(lambda: callback(*args, **kwargs)),
    )
    seen: list[int] = []
    reporter = CoalescedUiReporter(seen.append, min_interval_seconds=0.0)
    reporter.report(1)
    reporter.report(2)
    assert len(scheduled) == 1
    scheduled[0]()
    assert seen == [2]


def _blocking_worker(entered: threading.Event, release: threading.Event):
    def worker(*, cancellation_token, **_kwargs):
        entered.set()
        assert release.wait(5)
        cancellation_token.raise_if_cancelled()
        return "written"

    return worker


def test_cancel_does_not_signal_a_running_task_that_is_unsafe_to_cancel() -> None:
    manager = TaskManager(max_workers=1)
    entered, release = threading.Event(), threading.Event()
    try:
        task = manager.submit("write", _blocking_worker(entered, release), safe_to_cancel=False)
        assert entered.wait(5)

        assert manager.cancel(task.operation_id) is False
        assert not task.cancellation_token.is_cancelled()
        release.set()
        assert task.future.result(5) == "written"
    finally:
        release.set()
        manager.shutdown()


def test_cancel_signals_a_running_task_that_is_safe_to_cancel() -> None:
    from quill.stability.task_manager import CancelledError

    manager = TaskManager(max_workers=1)
    entered, release = threading.Event(), threading.Event()
    try:
        task = manager.submit("read", _blocking_worker(entered, release))
        assert entered.wait(5)

        assert manager.cancel(task.operation_id) is True
        assert task.cancellation_token.is_cancelled()
        release.set()
        with pytest.raises(CancelledError):
            task.future.result(5)
    finally:
        release.set()
        manager.shutdown()


def test_cancel_stops_an_unsafe_task_that_has_not_started_yet() -> None:
    manager = TaskManager(max_workers=1)
    entered, release = threading.Event(), threading.Event()
    try:
        manager.submit("first", _blocking_worker(entered, release))
        assert entered.wait(5)
        queued = manager.submit("queued write", lambda **_k: "ran", safe_to_cancel=False)

        assert manager.cancel(queued.operation_id) is True
        assert queued.future.cancelled()
    finally:
        release.set()
        manager.shutdown()
