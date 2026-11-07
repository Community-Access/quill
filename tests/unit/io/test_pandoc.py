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


def test_convert_document_with_pandoc_raises_on_none_stdout(monkeypatch, tmp_path: Path) -> None:
    # Regression for #954: a returncode-0 CompletedProcess with stdout=None
    # (the symptom of a locale-encoding decode failure in the subprocess
    # reader thread) must raise, not silently return an "empty document."
    source = tmp_path / "sample.docx"
    source.write_text("placeholder", encoding="utf-8")
    tool_status = type("Status", (), {"installed": True, "path": "C:/Tools/pandoc.exe"})()

    class Completed:
        returncode = 0
        stdout = None
        stderr = ""

    monkeypatch.setattr(
        "quill.io.pandoc.run_subprocess_safely",
        lambda *args, **kwargs: Completed(),
    )

    with pytest.raises(PandocConversionError, match="no output"):
        convert_document_with_pandoc(source, "markdown", tool_status=tool_status)


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


# -- an export never loses the file it was replacing ---------------------------


def _staging_run(monkeypatch, *, returncode: int = 0, write: bytes | None = b"new", raises=None):
    """Patch Pandoc with a fake that writes *write* to its ``-o`` path.

    Records every ``-o`` path so a test can check where Pandoc was pointed.
    A partial *write* with a non-zero exit is the realistic failure: Pandoc
    had begun the file before it gave up.
    """
    outputs: list[Path] = []

    class Completed:
        stdout = ""
        stderr = "pandoc: something went wrong"

    Completed.returncode = returncode

    def _run(command, **_kwargs):
        out = Path(command[command.index("-o") + 1])
        outputs.append(out)
        if write is not None:
            out.write_bytes(write)
        if raises is not None:
            raise raises
        return Completed()

    monkeypatch.setattr("quill.io.pandoc.run_subprocess_safely", _run)
    return outputs


def _status():
    return type("Status", (), {"installed": True, "path": "C:/Tools/pandoc.exe"})()


def _export(tmp_path: Path, **kwargs):
    from quill.io.pandoc import convert_file_with_pandoc

    source = tmp_path / "in.md"
    source.write_text("# New", encoding="utf-8")
    return convert_file_with_pandoc(
        source,
        tmp_path / "report.docx",
        from_format="gfm",
        to_format="docx",
        tool_status=_status(),
        **kwargs,
    )


def test_a_successful_export_replaces_the_earlier_file(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    target.write_bytes(b"old")
    outputs = _staging_run(monkeypatch, write=b"new")

    assert _export(tmp_path) == target

    assert target.read_bytes() == b"new"
    assert outputs[0] != target, "Pandoc writes beside the target, not over it"
    assert outputs[0].parent == target.parent
    assert outputs[0].suffix == ".docx", "the extension stays, Pandoc reads it"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.md", "report.docx"]


def test_a_failed_export_leaves_the_earlier_file_untouched(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    target.write_bytes(b"old")
    _staging_run(monkeypatch, returncode=1, write=b"half a fi")

    with pytest.raises(PandocConversionError):
        _export(tmp_path)

    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.md", "report.docx"]


def test_an_export_that_raises_leaves_the_earlier_file_untouched(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "report.docx"
    target.write_bytes(b"old")
    _staging_run(monkeypatch, write=b"half", raises=subprocess.TimeoutExpired("pandoc", 1))

    with pytest.raises(PandocConversionError, match="timed out"):
        _export(tmp_path)

    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.md", "report.docx"]


def test_an_export_cancelled_mid_run_leaves_the_earlier_file_untouched(
    monkeypatch, tmp_path: Path
) -> None:
    import threading

    from quill.io.pandoc import PandocCancelledError

    target = tmp_path / "report.docx"
    target.write_bytes(b"old")
    cancel = threading.Event()
    monkeypatch.setattr("quill.io.pandoc.run_subprocess_safely", _cancel_after(cancel))

    with pytest.raises(PandocCancelledError):
        _export(tmp_path, cancel=cancel)

    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.md", "report.docx"]


def _cancel_after(cancel):
    """A Pandoc run that finishes its file just as the user presses Cancel."""

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(command, **_kwargs):
        Path(command[command.index("-o") + 1]).write_bytes(b"new")
        cancel.set()
        return Completed()

    return _run


def test_an_export_with_no_earlier_file_still_arrives(monkeypatch, tmp_path: Path) -> None:
    _staging_run(monkeypatch, write=b"new")
    assert _export(tmp_path).read_bytes() == b"new"


def test_success_with_no_output_does_not_touch_the_earlier_file(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "report.docx"
    target.write_bytes(b"old")
    _staging_run(monkeypatch, write=None)

    with pytest.raises(PandocConversionError, match="did not produce"):
        _export(tmp_path)

    assert target.read_bytes() == b"old"
