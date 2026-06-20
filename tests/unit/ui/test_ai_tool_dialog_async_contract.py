"""DLG-3.6 / DLG-2 guard: safe async + modal contract for AI tool dialogs.

Phase 6 of the dialog estate work (DLG-3.6, which folds in DLG-2) requires the
assistant/AI tool dialogs in ``assistant_tools.py``, ``ai_model_panel.py``,
``train_style_dialog.py``, and ``assistant_panel.py`` to share one modal/focus/error
contract *with safe async/"busy" semantics*: a long-running action disables its
trigger before work starts, runs off the UI thread, marshals every result
(including failures) back with ``CallAfter``, and re-enables the trigger when the
work finishes — so focus never lands on a dead control and a background failure
never leaves the dialog wedged.

This guard pins that structure as source contract so it cannot silently regress.
The manual NVDA/JAWS/Narrator sign-off for these dialogs is tracked separately in
DLG-3.8; this test covers only the machine-verifiable half.
"""

from __future__ import annotations

from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def _read(name: str) -> str:
    return (_UI / name).read_text(encoding="utf-8")


def test_every_modal_open_routes_through_the_shared_contract() -> None:
    """Each module that arms a modal with ``apply_modal_ids`` must also drive it
    through the announcing ``show_modal_dialog`` helper (never a raw ShowModal)."""
    for module in (
        "assistant_tools.py",
        "ai_model_panel.py",
    ):
        source = _read(module)
        assert "apply_modal_ids(" in source, module
        assert "show_modal_dialog(" in source, module
        # The raw modal call must not be used directly to bypass the helper.
        assert ".ShowModal()" not in source, (
            f"{module} calls ShowModal() directly instead of show_modal_dialog()."
        )


def _assert_async_busy_cycle(
    source: str,
    *,
    trigger: str,
    disable: str,
    completion: str,
    reenable: str,
) -> None:
    """Assert one async action disables before the thread and re-enables after."""
    assert trigger in source
    trigger_at = source.index(trigger)
    disable_at = source.index(disable, trigger_at)
    thread_at = source.index("threading.Thread(", disable_at)
    # The trigger control is disabled *before* the worker thread is started.
    assert disable_at < thread_at, "control must be disabled before the thread starts"
    # The worker body guards against failure and marshals the result to the UI thread.
    worker_segment = source[disable_at:thread_at]
    assert "except Exception" in worker_segment
    assert f"CallAfter(self.{completion}" in worker_segment
    # The completion handler (UI thread) re-enables the trigger control.
    completion_at = source.index(f"def {completion}(")
    assert reenable in source[completion_at:], "completion handler must re-enable the control"


def test_ai_model_download_disables_and_reenables_around_the_worker() -> None:
    _assert_async_busy_cycle(
        _read("ai_model_panel.py"),
        trigger="def _on_download(",
        disable="self.download_button.Enable(False)",
        completion="_after_download",
        reenable="self.download_button.Enable(True)",
    )


def test_style_guide_build_disables_and_reenables_around_the_worker() -> None:
    _assert_async_busy_cycle(
        _read("train_style_dialog.py"),
        trigger="def _start_build(",
        disable="self.build_button.Enable(False)",
        completion="_deliver_guide",
        reenable="self.build_button.Enable(True)",
    )


def test_assistant_panel_submit_brackets_the_worker_with_busy_state() -> None:
    source = _read("assistant_panel.py")
    # Submit enters the busy state before spawning the worker thread.
    busy_on = source.index("self._set_busy(True)")
    thread_at = source.index("threading.Thread(", busy_on)
    worker_segment = source[busy_on:thread_at]
    assert "except Exception" in worker_segment
    assert "CallAfter(self._apply" in worker_segment
    # The _apply completion handler clears the busy state on the UI thread.
    apply_at = source.index("def _apply(")
    assert "self._set_busy(False)" in source[apply_at:]
    # _set_busy toggles the composer controls so focus never lands on a live
    # control mid-request.
    assert "def _set_busy(" in source
