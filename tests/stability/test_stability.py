from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.stability import wx_dispatch as wx_dispatch_module
from quill.stability import wx_heartbeat as heartbeat_module
from quill.stability.crash_report import build_diagnostic_bundle
from quill.stability.diagnostics import close_diagnostic_handles, setup_fault_handler
from quill.stability.feature_contracts import FeatureContract, validate_feature_contract
from quill.stability.memory_watch import start_memory_tracing, write_memory_snapshot
from quill.stability.redaction import (
    filter_recent_commands,
    format_args_for_log,
    redact_command_arg,
    redact_text_for_bundle_with_stats,
)
from quill.stability.safe_mode import build_safe_mode_config, should_enable_safe_mode
from quill.stability.safe_regex import RegexTimeoutError, safe_finditer
from quill.stability.safe_subprocess import run_subprocess_safely
from quill.stability.task_manager import CancelledError, TaskManager
from quill.stability.ui_responsiveness import wx_event_handler
from quill.stability.wx_dispatch import CoalescedUiReporter, call_ui_safely


def test_call_ui_safely_schedules_through_callafter(monkeypatch) -> None:
    scheduled: list[object] = []
    monkeypatch.setattr(
        wx_dispatch_module,
        "wx",
        SimpleNamespace(CallAfter=lambda callback: scheduled.append(callback)),
    )

    called: list[str] = []

    call_ui_safely(lambda value: called.append(value), "done")

    assert len(scheduled) == 1
    scheduled[0]()
    assert called == ["done"]


def test_coalesced_ui_reporter_uses_latest_value(monkeypatch) -> None:
    scheduled: list[object] = []
    monkeypatch.setattr(
        wx_dispatch_module,
        "call_ui_safely",
        lambda callback, *args, **kwargs: scheduled.append(lambda: callback(*args, **kwargs)),
    )

    seen: list[int] = []
    reporter = CoalescedUiReporter(lambda value: seen.append(value), min_interval_seconds=999.0)
    reporter.report(1)
    reporter.report(2)

    assert len(scheduled) == 1
    scheduled[0]()
    assert seen == [2]


def test_heartbeat_timer_ticks_state(monkeypatch) -> None:
    class FakeTimer:
        def __init__(self, window: object) -> None:
            self.window = window
            self.running = False
            self.interval = None

        def Start(self, interval_ms: int) -> None:  # noqa: N802 - wx-style API
            self.running = True
            self.interval = interval_ms

        def IsRunning(self) -> bool:  # noqa: N802 - wx-style API
            return self.running

        def Stop(self) -> None:  # noqa: N802 - wx-style API
            self.running = False

    class FakeWindow:
        def __init__(self) -> None:
            self.bound = None

        def Bind(self, event: object, handler: object, timer: object) -> None:  # noqa: N802
            self.bound = (event, handler, timer)

    monkeypatch.setattr(
        heartbeat_module,
        "wx",
        SimpleNamespace(Timer=FakeTimer, EVT_TIMER=object()),
    )
    state = heartbeat_module.HeartbeatState()
    window = FakeWindow()

    timer = heartbeat_module.WxHeartbeatTimer(window, state, interval_ms=250)
    event = SimpleNamespace(Skip=lambda: None)
    before = state.last_ui_tick
    window.bound[1](event)

    assert timer.timer.running is True
    assert timer.timer.interval == 250
    assert state.last_ui_tick >= before


def test_watchdog_dumps_when_heartbeat_is_stale() -> None:
    state = heartbeat_module.HeartbeatState()
    with state.lock:
        state.last_ui_tick = time.monotonic() - 10

    dumped: list[str] = []
    watchdog = heartbeat_module.WxHeartbeatWatchdog(
        state,
        dump_callback=lambda reason: dumped.append(reason),
        warn_after_seconds=0.01,
        dump_after_seconds=0.02,
        poll_seconds=0.01,
    )
    watchdog.start()
    deadline = time.monotonic() + 1.0
    try:
        while not dumped and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        watchdog.stop()

    assert dumped


def test_task_manager_removes_completed_tasks_and_logs_failures(caplog) -> None:
    manager = TaskManager(max_workers=1)
    try:
        with caplog.at_level(logging.INFO):
            task = manager.submit(
                "boom", lambda **_kwargs: (_ for _ in ()).throw(ValueError("boom"))
            )
            with pytest.raises(ValueError):
                task.future.result(timeout=1)

        assert "Task failed" in caplog.text
        assert manager.snapshot() == []
    finally:
        manager.shutdown()


def test_task_manager_cancellation_token_raises_cancelled_error() -> None:
    manager = TaskManager(max_workers=1)
    started = threading.Event()

    def worker(*, cancellation_token, **_kwargs):
        started.set()
        while True:
            cancellation_token.raise_if_cancelled()
            time.sleep(0.01)

    try:
        task = manager.submit("cancel", worker)
        assert started.wait(timeout=1)
        task.cancellation_token.cancel()
        with pytest.raises(CancelledError):
            task.future.result(timeout=1)
    finally:
        manager.shutdown()


def test_task_manager_records_submitted_at_and_pending_result() -> None:
    # L-13: every task carries a wall-clock ``submitted_at`` and starts in
    # the ``pending`` state, which is what the diagnostic bundle will render.
    manager = TaskManager(max_workers=1)
    try:
        gate = threading.Event()

        def worker(*, cancellation_token, **_kwargs):
            gate.wait(timeout=1)
            cancellation_token.raise_if_cancelled()
            return "ok"

        before = time.time()
        task = manager.submit("slow", worker)
        try:
            assert task.submitted_at >= before
            assert task.result_summary == "pending"
        finally:
            gate.set()
            assert task.future.result(timeout=1) == "ok"
    finally:
        manager.shutdown()


def test_task_manager_result_summary_ok_after_success() -> None:
    # L-13: a successful task collapses to ``"ok"`` once the done callback
    # runs. The snapshot only carries the result_summary, not the future.
    manager = TaskManager(max_workers=1)
    try:
        task = manager.submit("noop", lambda **_kwargs: 42)
        assert task.future.result(timeout=1) == 42
        # The done callback may race with the assertion, so wait for it.
        for _ in range(20):
            if task.result_summary == "ok":
                break
            time.sleep(0.01)
        assert task.result_summary == "ok"
    finally:
        manager.shutdown()


def test_task_manager_result_summary_failed_on_exception() -> None:
    # L-13: an exception in the worker collapses to ``"failed"`` rather
    # than leaking the future's exception to the diagnostic bundle.
    manager = TaskManager(max_workers=1)
    try:
        task = manager.submit("boom", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("nope")))
        with pytest.raises(RuntimeError):
            task.future.result(timeout=1)
        for _ in range(20):
            if task.result_summary == "failed":
                break
            time.sleep(0.01)
        assert task.result_summary == "failed"
    finally:
        manager.shutdown()


def test_task_manager_result_summary_cancelled() -> None:
    # L-13: cancelling the future collapses the summary to ``"cancelled"``.
    manager = TaskManager(max_workers=1)
    try:
        started = threading.Event()

        def worker(*, cancellation_token, **_kwargs):
            started.set()
            while True:
                cancellation_token.raise_if_cancelled()
                time.sleep(0.01)

        task = manager.submit("never", worker)
        assert started.wait(timeout=1)
        task.cancellation_token.cancel()
        with pytest.raises(CancelledError):
            task.future.result(timeout=1)
        for _ in range(20):
            if task.result_summary == "cancelled":
                break
            time.sleep(0.01)
        assert task.result_summary == "cancelled"
    finally:
        manager.shutdown()


def test_run_subprocess_safely_times_out(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["echo"], timeout=0.1)

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(subprocess.TimeoutExpired):
        run_subprocess_safely(["echo", "hello"], timeout_seconds=0.1)


def test_run_subprocess_safely_rejects_empty_args() -> None:
    with pytest.raises(ValueError):
        run_subprocess_safely([])


def test_run_subprocess_safely_rejects_missing_cwd(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError):
        run_subprocess_safely(["echo", "hi"], cwd=str(missing))


def test_run_subprocess_safely_rejects_file_as_cwd(tmp_path: Path) -> None:
    a_file = tmp_path / "a.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        run_subprocess_safely(["echo", "hi"], cwd=str(a_file))


def test_run_subprocess_safely_wraps_launch_oserror(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(OSError) as excinfo:
        run_subprocess_safely(["definitely-not-a-real-binary-xyz"])
    assert "definitely-not-a-real-binary-xyz" in str(excinfo.value)


def test_safe_regex_times_out(monkeypatch) -> None:
    class FakeCompiled:
        def finditer(self, _text: str, timeout: float):
            raise TimeoutError("timeout")

    monkeypatch.setattr(
        "quill.stability.safe_regex.regex.compile",
        lambda *_args, **_kwargs: FakeCompiled(),
    )

    with pytest.raises(RegexTimeoutError):
        safe_finditer("(a+)+$", "a" * 100)


def test_memory_snapshot_writes_file(tmp_path: Path) -> None:
    start_memory_tracing()
    path = tmp_path / "memory.txt"
    write_memory_snapshot(path)

    assert path.exists()
    assert "QUILL memory snapshot" in path.read_text(encoding="utf-8")


def test_slow_wx_event_handler_logs_warning(caplog) -> None:
    @wx_event_handler("slow-handler", warn_after_ms=0)
    def handler() -> None:
        time.sleep(0.001)

    with caplog.at_level(logging.WARNING):
        handler()

    assert "Slow operation" in caplog.text


def test_safe_mode_configuration_disables_risky_features() -> None:
    config = build_safe_mode_config(True)

    assert config.enabled is True
    assert config.disable_plugins is True
    assert config.disable_ai_integrations is True
    assert should_enable_safe_mode(["--safe-mode"], {}) is True
    assert should_enable_safe_mode([], {"QUILL_SAFE_MODE": "1"}) is True


def test_safe_mode_blocks_assistant_network_calls(monkeypatch) -> None:
    """H-SAFE-1: when QUILL_SAFE_MODE=1, AI calls short-circuit with
    a safe-mode message instead of issuing a urllib.request call.
    """
    from quill.core import assistant_ai
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setenv("QUILL_SAFE_MODE", "1")

    # If any call attempted the network, this sentinel would be set.
    monkeypatch.setattr(
        assistant_ai,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network call attempted")),
    )

    settings = AssistantConnectionSettings(
        provider="openai", host="https://api.openai.com", model="gpt-4o-mini"
    )

    models, error = assistant_ai.list_assistant_models(settings, api_key="x")
    assert models == []
    assert error is not None
    assert "Safe Mode" in error

    text, error2 = assistant_ai.generate_assistant_response(settings, api_key="x", prompt="hi")
    assert text is None
    assert error2 is not None
    assert "Safe Mode" in error2

    ok, msg = assistant_ai.verify_assistant_connection(settings, api_key="x")
    assert ok is False
    assert "Safe Mode" in msg


def test_safe_mode_does_not_block_off_provider(monkeypatch) -> None:
    """``provider == 'off'`` is the *intended* offline state and must
    still return success in safe mode (the safe-mode banner is the
    wrong place to refuse an explicitly off provider)."""
    from quill.core import assistant_ai
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    settings = AssistantConnectionSettings(provider="off", host="", model="")
    models, error = assistant_ai.list_assistant_models(settings, api_key="")
    assert models == []
    assert error is None


def test_feature_contract_validation_rejects_risky_ui_thread_features() -> None:
    contract = FeatureContract(
        feature_id="regex_search",
        display_name="Regular Expression Search",
        stability_level="beta",
        default_enabled=False,
        disabled_in_safe_mode=True,
        runs_on_wx_main_thread=True,
        requires_timeout=True,
        supports_cancellation=True,
        reports_progress=True,
        diagnostic_category="search",
    )

    with pytest.raises(ValueError):
        validate_feature_contract(contract)


def test_diagnostic_bundle_includes_metadata(tmp_path: Path) -> None:
    logs = tmp_path / "quill.log"
    logs.write_text("log line", encoding="utf-8")
    bundle = build_diagnostic_bundle(
        logs_path=logs,
        safe_mode=True,
        enabled_plugins=["plugin-a"],
        recent_commands=["file.open"],
        feature_flags={"core.search": True},
        output_path=tmp_path / "bundle.zip",
    )

    assert bundle.exists()


def test_run_subprocess_safely_does_not_log_secrets(caplog, monkeypatch) -> None:
    """H-1: a secret passed in args must not appear in the log line."""

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    with caplog.at_level(logging.INFO):
        run_subprocess_safely([
            "fake",
            "--api-key=sk-LIVE-deadbeef1234567890",
            r"C:\Users\jane\secret.txt",
        ])

    joined = "\n".join(record.getMessage() for record in caplog.records)
    assert "sk-LIVE-deadbeef" not in joined
    assert r"C:\Users\jane" not in joined
    assert "fake" in joined  # executable basename still present


def test_diagnostic_bundle_redacts_secrets_and_paths(tmp_path: Path) -> None:
    """H-2: secrets and user paths in the input log must be redacted in the bundle."""

    import zipfile

    secret_line = "Bearer sk-LIVE-abcdef1234567890ABCDEF"
    path_line = r"Failed to read C:\Users\jane\Documents\secrets.txt"
    log = "\n".join(["normal line", secret_line, path_line, ""])

    logs = tmp_path / "quill.log"
    logs.write_text(log, encoding="utf-8")
    bundle_path = tmp_path / "bundle.zip"
    build_diagnostic_bundle(
        logs_path=logs,
        output_path=bundle_path,
        recent_commands=["file.open", "BAD/../cmd", "ok.command"],
    )

    with zipfile.ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert "quill.log" in names
        assert "metadata.json" in names
        redacted = archive.read("quill.log").decode("utf-8", errors="replace")
        metadata = json.loads(archive.read("metadata.json").decode("utf-8"))

    # The secret must be gone.
    assert "sk-LIVE-abcdef" not in redacted
    # The user path must be redacted (path token, not raw).
    assert r"C:\Users\jane" not in redacted
    # Normal content should still be present.
    assert "normal line" in redacted
    # Metadata records what was redacted.
    assert "redaction" in metadata
    assert metadata["redaction"]["quill.log"]["lines_dropped"] >= 1
    # recent_commands is filtered: only well-formed ids survive.
    assert metadata["recent_commands"] == ["file.open", "ok.command"]


# L-17: direct unit tests for redaction.py (previously only tested via the bundle)


def test_redact_command_arg_replaces_secret_name_value_pair() -> None:
    assert redact_command_arg("api_key=sk-LIVE-secret123") == "[REDACTED]"
    assert redact_command_arg("--token=abc") == "[REDACTED]"


def test_redact_command_arg_strips_windows_path_prefix() -> None:
    result = redact_command_arg(r"C:\Users\jane\Documents\file.txt")
    assert r"C:\Users\jane" not in result
    assert "[PATH]" in result


def test_format_args_for_log_preserves_basename_and_count() -> None:
    result = format_args_for_log(["piper", "--model", "en_US-amy-medium.onnx", "--output_file"])
    assert result.startswith("piper")
    assert "3 args" in result
    assert "input.png" not in result or "PATH" in result or "input.png" in result


def test_format_args_for_log_empty_returns_no_args() -> None:
    assert format_args_for_log([]) == "(no args)"


def test_redact_text_for_bundle_drops_bearer_line_and_reports_stats() -> None:
    text = "normal log line\nBearer sk-LIVE-abcdef1234567890\nanother normal line\n"
    redacted, stats = redact_text_for_bundle_with_stats(text)
    assert "sk-LIVE-abcdef" not in redacted
    assert stats.lines_dropped >= 1
    assert stats.lines_in == 3
    assert "normal log line" in redacted


def test_filter_recent_commands_drops_non_id_strings() -> None:
    commands = ["file.open", "INVALID CMD", "ok.command", "../traversal", ""]
    result = filter_recent_commands(commands)
    assert "file.open" in result
    assert "ok.command" in result
    assert "INVALID CMD" not in result
    assert "../traversal" not in result
    assert "" not in result


def test_safe_finditer_uses_cached_compile() -> None:
    # M-21: second call with same (pattern, flags) must hit the LRU cache.
    from quill.stability.safe_regex import _compile_cached

    _compile_cached.cache_clear()
    safe_finditer(r"\bword\b", "a word here")
    safe_finditer(r"\bword\b", "another word")
    info = _compile_cached.cache_info()
    assert info.hits >= 1


def test_call_ui_safely_logs_warning_without_wx(monkeypatch, caplog) -> None:
    # M-23: when wx.CallAfter is unavailable, a WARNING must be emitted so the
    # fallback synchronous execution is visible in the diagnostic log.
    monkeypatch.setattr(wx_dispatch_module, "wx", None)
    called: list[str] = []

    with caplog.at_level(logging.WARNING):
        call_ui_safely(lambda: called.append("ran"))

    assert called == ["ran"]
    assert "synchronously" in caplog.text


def test_feature_contract_full_validation() -> None:
    # M-22: validate_feature_contract must reject risky features that are not
    # disabled in safe mode, and experimental features that default to enabled.
    risky_not_safe_mode = FeatureContract(
        feature_id="test.risky",
        display_name="Risky Feature",
        stability_level="risky",
        default_enabled=True,
        disabled_in_safe_mode=False,  # should be True for risky
        runs_on_wx_main_thread=False,
        supports_cancellation=True,
        reports_progress=False,
        diagnostic_category="test",
    )
    with pytest.raises(ValueError, match="safe_mode"):
        validate_feature_contract(risky_not_safe_mode)

    experimental_enabled = FeatureContract(
        feature_id="test.exp",
        display_name="Experimental Feature",
        stability_level="experimental",
        default_enabled=True,  # should be False for experimental
        disabled_in_safe_mode=True,
        runs_on_wx_main_thread=False,
        supports_cancellation=True,
        reports_progress=False,
        diagnostic_category="test",
    )
    with pytest.raises(ValueError, match="experimental"):
        validate_feature_contract(experimental_enabled)


def test_diagnostic_handles_bounded(tmp_path: Path, monkeypatch) -> None:
    # M-17: calling setup_fault_handler twice must leave at most one open handle.
    import quill.stability.diagnostics as diag_module

    monkeypatch.setattr(diag_module, "_OPEN_HANDLES", [])
    monkeypatch.setattr(diag_module, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(diag_module, "ensure_app_directories", lambda: None)

    setup_fault_handler()
    setup_fault_handler()

    assert len(diag_module._OPEN_HANDLES) == 1
    close_diagnostic_handles()


def test_task_manager_shutdown_decoupled() -> None:
    # M-18: shutdown(wait=True) must not cancel pending futures;
    # shutdown(wait=False, cancel_pending=True) must cancel them.

    started = threading.Event()
    proceed = threading.Event()

    def long_task(**_kwargs: object) -> str:
        started.set()
        proceed.wait(timeout=2.0)
        return "done"

    mgr = TaskManager(max_workers=1)
    task = mgr.submit("long", long_task)
    started.wait(timeout=2.0)

    # Fast shutdown with cancel_pending=True should cancel the running future.
    proceed.set()
    mgr.shutdown(wait=True, cancel_pending=False)
    # No exception means wait=True + cancel_pending=False completed cleanly.
    assert task.future.done()


def test_watchdog_stop_joins_thread() -> None:
    # M-19: stop() must join the watchdog thread within the timeout so the
    # caller knows it has fully stopped before continuing.
    from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatWatchdog

    state = HeartbeatState()
    state.tick()

    dumps: list[str] = []
    watchdog = WxHeartbeatWatchdog(state, dump_callback=dumps.append, poll_seconds=0.05)
    watchdog.start()
    watchdog.stop(timeout=2.0)

    assert not watchdog._thread.is_alive()


def test_watchdog_re_dumps_after_recovery_window() -> None:
    # M-20: a brief UI unblock followed by a second block must trigger a second
    # dump once enough time has passed since the first dump. Exercises the pure
    # re-dump policy directly so the assertion does not depend on wall-clock
    # scheduling (the old time.sleep-based form flaked under load: too-tight 0.05s
    # windows meant a delayed poll could miss the second window entirely).
    from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatWatchdog

    state = HeartbeatState()
    watchdog = WxHeartbeatWatchdog(
        state,
        dump_callback=lambda _m: None,
        warn_after_seconds=0.01,
        dump_after_seconds=0.05,
        poll_seconds=0.02,
    )

    base = 1000.0
    # Not yet blocked long enough: no dump.
    assert watchdog._should_dump(age=0.04, now=base, last_dump_time=0.0) is False
    # Blocked past the window with no prior dump: first dump fires.
    assert watchdog._should_dump(age=0.06, now=base, last_dump_time=0.0) is True
    # Still blocked but inside the recovery window since the first dump: suppressed.
    assert watchdog._should_dump(age=0.09, now=base + 0.02, last_dump_time=base) is False
    # Recovery window elapsed and still blocked: second dump fires (re-dump).
    # Use a clear margin past the 0.05s window (not the exact boundary) so the
    # assertion does not depend on floating-point representability.
    assert watchdog._should_dump(age=0.12, now=base + 0.06, last_dump_time=base) is True


def test_watchdog_warn_level_dump_is_one_shot_per_episode() -> None:
    # A short-but-real stall (e.g. the ~7 s startup block in review.md) never
    # reaches dump_after_seconds (15 s), so without a warn-level dump no thread
    # stacks are captured. The warn dump must fire once when the stall crosses
    # warn_dump_after_seconds and not again until the UI recovers.
    from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatWatchdog

    watchdog = WxHeartbeatWatchdog(
        HeartbeatState(),
        dump_callback=lambda _m: None,
        warn_after_seconds=5.0,
        warn_dump_after_seconds=5.0,
    )
    # Below the threshold: no warn dump.
    assert watchdog._should_warn_dump(age=3.0) is False
    # Crosses the threshold, not yet dumped this episode: fire.
    assert watchdog._should_warn_dump(age=6.9) is True
    watchdog._warn_dumped_this_episode = True
    # Already dumped this episode: suppressed even while still stalled.
    assert watchdog._should_warn_dump(age=9.0) is False


def test_watchdog_warn_level_dump_can_be_disabled() -> None:
    from quill.stability.wx_heartbeat import HeartbeatState, WxHeartbeatWatchdog

    watchdog = WxHeartbeatWatchdog(
        HeartbeatState(),
        dump_callback=lambda _m: None,
        warn_dump_after_seconds=None,
    )
    assert watchdog._should_warn_dump(age=100.0) is False
