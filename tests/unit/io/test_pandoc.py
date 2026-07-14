from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quill.io.pandoc import (
    PandocConversionError,
    PandocUnavailableError,
    convert_document_with_pandoc,
)


def test_convert_document_with_pandoc_requires_installed_tool(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "quill.io.pandoc.get_external_tool_status",
        lambda _tool_id: type("Status", (), {"installed": False, "path": None})(),
    )

    with pytest.raises(PandocUnavailableError):
        convert_document_with_pandoc(tmp_path / "sample.docx", "markdown")


def test_convert_document_with_pandoc_returns_stdout(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    source.write_text("placeholder", encoding="utf-8")
    tool_status = type("Status", (), {"installed": True, "path": "C:/Tools/pandoc.exe"})()

    class Completed:
        returncode = 0
        stdout = "# Converted\n"

    # quill/io/pandoc.py delegates subprocess launching to
    # run_subprocess_safely (so the redact-args-in-logs contract applies);
    # monkeypatch the safety wrapper, not a module-level subprocess import
    # that no longer exists.
    monkeypatch.setattr(
        "quill.io.pandoc.run_subprocess_safely",
        lambda *args, **kwargs: Completed(),
    )

    result = convert_document_with_pandoc(source, "markdown", tool_status=tool_status)

    assert result.text == "# Converted\n"
    assert result.output_kind == "markdown"
    assert result.source_path == source


def test_convert_document_rejects_binary_output_kind(tmp_path: Path) -> None:
    # A binary writer (docx/odt/epub/pdf) cannot be captured as text. Reject it
    # up front with a clear message instead of letting Pandoc fail with the
    # cryptic "Cannot write docx output to terminal".
    source = tmp_path / "sample.docx"
    source.write_text("placeholder", encoding="utf-8")
    tool_status = type("Status", (), {"installed": True, "path": "C:/Tools/pandoc.exe"})()

    with pytest.raises(PandocConversionError, match="binary format"):
        convert_document_with_pandoc(source, "docx", tool_status=tool_status, from_format="docx")


def test_convert_document_with_pandoc_raises_on_error(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    source.write_text("placeholder", encoding="utf-8")
    tool_status = type("Status", (), {"installed": True, "path": "C:/Tools/pandoc.exe"})()

    def raise_error(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, ["pandoc"], stderr="bad input")

    monkeypatch.setattr(
        "quill.io.pandoc.run_subprocess_safely",
        raise_error,
    )

    # #262 rewrote the error path through _map_exception which formats the
    # message as "Pandoc invocation failed: <stderr from CalledProcessError>".
    with pytest.raises(PandocConversionError, match="Pandoc invocation failed"):
        convert_document_with_pandoc(source, "markdown", tool_status=tool_status)
