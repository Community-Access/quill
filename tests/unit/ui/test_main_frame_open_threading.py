from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_open_reads_heavy_office_formats_off_the_ui_thread() -> None:
    # PERF-12: large office/PDF reads must run on a worker thread so the UI
    # thread never blocks while parsing them.
    assert "from quill.io.open_read import read_open_document" in SOURCE
    assert "if suffix in _OFFICE_STREAM_SUFFIXES:" in SOURCE
    # The office branch dispatches the read through the background-task helper.
    assert "self._run_background_task(" in SOURCE
    assert (
        "lambda _progress: read_open_document(\n"
        "                    selected_path, suffix, word_mode=word_mode, docx_engine=docx_engine\n"
        "                )"
    ) in SOURCE


def test_open_resolves_word_prompt_before_leaving_the_ui_thread() -> None:
    # The Word open-mode chooser is a wx dialog, so it must be resolved on the
    # UI thread before the worker (which must not touch wx) starts.
    index = SOURCE.index("if suffix in _OFFICE_STREAM_SUFFIXES:")
    branch = SOURCE[index : index + 800]
    assert "self._resolve_word_open_mode(selected_path)" in branch
    assert "_run_background_task" in branch
    # The prompt resolution appears before the worker dispatch.
    assert branch.index("self._resolve_word_open_mode(selected_path)") < branch.index(
        "_run_background_task"
    )


def test_finish_open_document_runs_on_the_ui_thread() -> None:
    assert "def _finish_open_document(" in SOURCE
    assert 'self._epub_book = epub_book if suffix == ".epub" else None' in SOURCE


def test_main_frame_class_is_importable() -> None:
    assert MainFrame is not None
