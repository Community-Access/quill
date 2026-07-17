"""Regression test for #1067: background-thread -> ``wx.CallAfter`` callbacks in
the AI dialogs must no-op when the dialog has been closed before the background
work finished, instead of touching a destroyed ``wx.StaticText`` / ``wx.Button``
and raising ``RuntimeError: wrapped C/C++ object of type StaticText has been
deleted``.

These callbacks post back from a ``threading.Thread`` via ``wx.CallAfter``. The
guard is a ``dialog_alive(self.dialog)`` check at the top of each callback. We
exercise the callbacks directly with a stub ``self`` whose ``dialog`` reports
"being deleted" and assert no widget method is touched -- and, for one callback,
that an alive dialog still drives the widget (so the guard is conditional, not a
blanket no-op). No wx is required.
"""

from __future__ import annotations

from quill.ui.ai_document_qa_dialog import AIDocumentQADialog
from quill.ui.ai_hub_dialog import AIHubDialog
from quill.ui.ai_model_panel import AIModelDialog
from quill.ui.ai_thesaurus_dialog import AIThesaurusDialog
from quill.ui.dialog_contract import dialog_alive


class _RecordingWidget:
    """Records every method call made on it (SetLabel, Enable, Set, ...)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def _method(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return _method


class _DeletedDialog:
    """Stands in for a wx.Dialog that is mid-teardown."""

    def IsBeingDeleted(self) -> bool:  # noqa: D401 - stub
        return True


class _AliveDialog:
    """Stands in for a live wx.Dialog."""

    def IsBeingDeleted(self) -> bool:
        return False


class _RaisingDialog:
    """A dialog whose liveness probe itself raises (torn-down C++ object)."""

    def IsBeingDeleted(self) -> bool:
        raise RuntimeError("wrapped C/C++ object of type Dialog has been deleted")


class _Stub:
    """A minimal stand-in for an AI dialog instance.

    Any attribute access except ``dialog`` returns a shared recording widget, so
    a callback that reaches ``self._test_label.SetLabel(...)`` (or any other
    widget) is observable. ``dialog`` is the liveness probe target.
    """

    def __init__(self, dialog: object) -> None:
        object.__setattr__(self, "_dialog", dialog)
        object.__setattr__(self, "_widgets", {})

    @property
    def dialog(self) -> object:
        return self._dialog

    def __getattr__(self, name: str):
        widgets = object.__getattribute__(self, "_widgets")
        if name not in widgets:
            widgets[name] = _RecordingWidget()
        return widgets[name]

    def widget_call_count(self) -> int:
        widgets = object.__getattribute__(self, "_widgets")
        return sum(len(w.calls) for w in widgets.values())

    def widget_calls(self, name: str) -> list[tuple[str, tuple, dict]]:
        widgets = object.__getattribute__(self, "_widgets")
        return list(widgets.get(name, _RecordingWidget()).calls)


# --- dialog_alive itself ----------------------------------------------------


def test_dialog_alive_truth_table() -> None:
    assert dialog_alive(_AliveDialog()) is True
    assert dialog_alive(_DeletedDialog()) is False
    assert dialog_alive(None) is False
    # A torn-down dialog whose probe raises must read as "not alive", not crash.
    assert dialog_alive(_RaisingDialog()) is False


# --- AI Hub: auto-probe / list-models / test-connection ----------------------


def test_hub_auto_probe_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIHubDialog._on_auto_probe_done(stub, "Ollama running.")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


def test_hub_auto_probe_updates_label_when_alive() -> None:
    stub = _Stub(_AliveDialog())
    AIHubDialog._on_auto_probe_done(stub, "Ollama running. 3 models available.")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 1
    assert stub.widget_calls("_test_label") == [
        ("SetLabel", ("Ollama running. 3 models available.",), {})
    ]


def test_hub_models_listed_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIHubDialog._on_hub_models_listed(stub, ["m1"], "", None)  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


def test_hub_test_done_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIHubDialog._on_test_done(stub, "Connection OK.")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


# --- AI Thesaurus: lookup result / error ------------------------------------


def test_thesaurus_results_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIThesaurusDialog._on_results(stub, [])  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


def test_thesaurus_error_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIThesaurusDialog._on_error(stub, "boom")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


# --- AI Model Panel: download -----------------------------------------------


def test_model_download_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIModelDialog._after_download(stub, "Downloaded.")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


# --- AI Document Q&A: answer / error ----------------------------------------


def test_document_qa_answer_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIDocumentQADialog._on_answer_done(stub, "q?", object())  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0


def test_document_qa_error_noops_when_dialog_deleted() -> None:
    stub = _Stub(_DeletedDialog())
    AIDocumentQADialog._on_answer_error(stub, "boom")  # type: ignore[attr-defined]
    assert stub.widget_call_count() == 0
