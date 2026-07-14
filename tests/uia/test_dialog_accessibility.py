"""Dialog accessibility regressions: every reachable control must have a name."""

from __future__ import annotations

import pytest

from tests.uia.a11y_scan import scan_window, summarize, unnamed_focusable

pytestmark = pytest.mark.uia


def _open_dialog_via_keys(quill_app, keys: str, title_fragment: str, attempts: int = 3):
    # A freshly-launched window can lose the first accelerator to a foreground
    # race (seen on CI runners), so the keystroke is retried, never assumed.
    last_error: Exception | None = None
    for _ in range(attempts):
        quill_app.main_window.set_focus()
        quill_app.main_window.type_keys(keys)
        dialog = quill_app.main_window.child_window(
            title_re=f".*{title_fragment}.*", control_type="Window"
        )
        try:
            dialog.wait("exists visible", timeout=6)
            return dialog
        except Exception as exc:  # noqa: BLE001 - retry the keystroke
            last_error = exc
    raise AssertionError(f"dialog {title_fragment!r} never opened via {keys!r}: {last_error}")


def test_go_to_line_dialog_is_fully_named(quill_app) -> None:
    # Ctrl+G: small, stable, and representative of the modal-dialog contract.
    dialog = _open_dialog_via_keys(quill_app, "^g", "Go")
    records = scan_window(dialog)
    offenders = unnamed_focusable(records)
    assert not offenders, "Keyboard-reachable controls without accessible names:\n" + "\n".join(
        summarize(offenders)
    )
    dialog.type_keys("{ESC}")


def test_escape_closes_the_dialog(quill_app) -> None:
    import time

    # The modal-id contract: Escape must always dismiss (apply_modal_ids).
    dialog = _open_dialog_via_keys(quill_app, "^g", "Go")
    dialog.type_keys("{ESC}")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if not dialog.exists(timeout=0.5):
                break
        except Exception:  # noqa: BLE001 - a destroyed window counts as closed
            break
        time.sleep(0.25)
    else:
        raise AssertionError("Escape did not close the Go To Line dialog")
    # The app is still responsive afterwards.
    quill_app.main_window.wait("visible", timeout=5)
