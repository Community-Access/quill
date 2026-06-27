"""Pandoc I/O layer tests (issue #262).

Tests the public surface of :mod:`quill.io.pandoc` without actually invoking
Pandoc. We use a fake ``ExternalToolStatus`` to control which binary path
the layer sees, and patch :func:`quill.stability.safe_subprocess.run_subprocess_safely`
to feed in canned results.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from unittest import mock

import pytest

from quill.core import pandoc_formats
from quill.core.external_tools import ExternalToolStatus
from quill.io import pandoc as pandoc_io


def _fake_status(installed: bool = True, path: str = "C:/pandoc/pandoc.exe") -> ExternalToolStatus:
    from quill.core.external_tools import ExternalToolDefinition

    return ExternalToolStatus(
        definition=ExternalToolDefinition(
            tool_id="pandoc",
            name="Pandoc",
            category="conversion",
            description="",
            capabilities=(),
            bundled_subpath=r"pandoc\pandoc.exe",
            executable_names=("pandoc.exe", "pandoc"),
            website_url="https://pandoc.org/",
            install_command="",
        ),
        installed=installed,
        path=path,
        source="fake",
        version="3.1.6",
    )


def test_convert_file_with_pandoc_happy_path(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.html"
    source.write_text("# Hello", encoding="utf-8")
    target.write_bytes(b"fake-html")  # simulate Pandoc producing the file
    fake_completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="<h1>Hello</h1>", stderr=""
    )
    with mock.patch(
        "quill.io.pandoc.run_subprocess_safely", return_value=fake_completed
    ) as patched:
        result = pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="markdown",
            to_format="html",
            tool_status=_fake_status(),
        )
    assert result == target
    assert patched.call_count == 1
    args = patched.call_args.args[0]
    # The runner puts the executable at the front, then --from/--to, -o target, source.
    assert args[0].endswith("pandoc.exe")
    assert "--from" in args
    assert "markdown" in args
    assert "--to" in args
    assert "html5" in args  # legacy html -> html5 mapping
    assert "-o" in args
    assert str(target) in args
    assert str(source) in args[-1] or str(source) in args


def test_convert_file_with_pandoc_writes_target_file(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.docx"
    source.write_text("# Hello", encoding="utf-8")
    target.write_bytes(b"fake-docx")  # simulate Pandoc creating the file
    fake_completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with mock.patch("quill.io.pandoc.run_subprocess_safely", return_value=fake_completed):
        result = pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="gfm",
            to_format="docx",
            tool_status=_fake_status(),
        )
    assert result == target
    assert target.exists()


def test_convert_file_with_pandoc_missing_input(tmp_path: Path) -> None:
    source = tmp_path / "missing.md"
    target = tmp_path / "out.html"
    with pytest.raises(pandoc_io.PandocConversionError):
        pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="markdown",
            to_format="html",
            tool_status=_fake_status(),
        )


def test_convert_file_with_pandoc_not_installed(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.html"
    source.write_text("# Hello", encoding="utf-8")
    with pytest.raises(pandoc_io.PandocUnavailableError):
        pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="markdown",
            to_format="html",
            tool_status=_fake_status(installed=False, path=None),
        )


def test_convert_file_with_pandoc_nonzero_exit(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.html"
    source.write_text("# Hello", encoding="utf-8")
    fake_completed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="pandoc: error parsing"
    )
    with mock.patch("quill.io.pandoc.run_subprocess_safely", return_value=fake_completed):
        with pytest.raises(pandoc_io.PandocConversionError) as exc_info:
            pandoc_io.convert_file_with_pandoc(
                source,
                target,
                from_format="markdown",
                to_format="html",
                tool_status=_fake_status(),
            )
    assert "error parsing" in str(exc_info.value)


def test_convert_file_with_pandoc_cancel(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.html"
    source.write_text("# Hello", encoding="utf-8")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(pandoc_io.PandocCancelledError):
        pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="markdown",
            to_format="html",
            tool_status=_fake_status(),
            cancel=cancel,
        )


def test_convert_file_with_pandoc_extra_args(tmp_path: Path) -> None:
    source = tmp_path / "in.md"
    target = tmp_path / "out.epub"
    source.write_text("# Hello", encoding="utf-8")
    target.write_bytes(b"fake-epub")
    fake_completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with mock.patch(
        "quill.io.pandoc.run_subprocess_safely", return_value=fake_completed
    ) as patched:
        pandoc_io.convert_file_with_pandoc(
            source,
            target,
            from_format="markdown",
            to_format="epub",
            tool_status=_fake_status(),
            extra_args=("--standalone", "--toc"),
        )
    args = patched.call_args.args[0]
    assert "--standalone" in args
    assert "--toc" in args


def test_convert_document_with_pandoc_text_result(tmp_path: Path) -> None:
    source = tmp_path / "in.html"
    source.write_text("<h1>Hello</h1>", encoding="utf-8")
    fake_completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="# Hello", stderr="")
    with mock.patch("quill.io.pandoc.run_subprocess_safely", return_value=fake_completed):
        result = pandoc_io.convert_document_with_pandoc(
            source, "markdown", tool_status=_fake_status()
        )
    assert result.text == "# Hello"
    assert result.output_kind == "markdown"
    assert result.source_path == source


def test_resolve_writer_legacy_values() -> None:
    assert pandoc_io._resolve_writer("markdown") == "gfm"
    assert pandoc_io._resolve_writer("html") == "html5"
    assert pandoc_io._resolve_writer("plain") == "plain"


def test_resolve_writer_passthrough() -> None:
    assert pandoc_io._resolve_writer("docx") == "docx"
    assert pandoc_io._resolve_writer("epub") == "epub"
    assert pandoc_io._resolve_writer("plain_text") == "plain"
    assert pandoc_io._resolve_writer("pdf") == "pdf"


def test_resolve_writer_passes_through_arbitrary_pandoc_tokens() -> None:
    # The Convert File catalogue reaches beyond Tier-1, so an unknown non-empty
    # writer name is passed straight to Pandoc (which validates it) rather than
    # rejected here. Only an empty token is a programming error.
    assert pandoc_io._resolve_writer("rst") == "rst"
    assert pandoc_io._resolve_writer("asciidoc") == "asciidoc"


def test_resolve_writer_rejects_empty() -> None:
    with pytest.raises(ValueError):
        pandoc_io._resolve_writer("   ")


def test_tier1_format_set_is_consistent_with_io() -> None:
    """Every Tier-1 output name resolves to a real Pandoc writer."""

    for name in pandoc_formats.TIER1_OUTPUTS:
        # Should not raise.
        pandoc_io._resolve_writer(name)
