"""Batch conversion tests (issue #262).

Covers :mod:`quill.core.batch_convert` end-to-end without spawning real
Pandoc. We patch :func:`quill.io.pandoc.convert_file_with_pandoc` to a
fake that produces a small target file.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest import mock

import pytest

from quill.core import batch_convert


def _fake_pandoc(
    source: Path,
    target: Path,
    **kwargs: object,
) -> Path:
    """Stand-in for ``convert_file_with_pandoc`` that just copies text."""

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _fake_failing_pandoc(
    source: Path,
    target: Path,
    **kwargs: object,
) -> Path:
    from quill.io.pandoc import PandocConversionError

    raise PandocConversionError(f"simulated failure for {source.name}")


def _make_files(folder: Path, names: tuple[str, ...]) -> list[Path]:
    created = []
    for name in names:
        p = folder / name
        p.write_text("# hi", encoding="utf-8")
        created.append(p)
    return created


def test_iter_target_files_non_recursive(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.markdown", "c.txt"))
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "d.md").write_text("# nested", encoding="utf-8")
    result = list(
        batch_convert.iter_target_files(tmp_path, recursive=False, source_format="markdown")
    )
    names = sorted(p.name for p in result)
    assert names == ["a.md", "b.markdown"]


def test_iter_target_files_recursive(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    _make_files(tmp_path, ("a.md",))
    _make_files(nested, ("b.md", "c.md"))
    result = list(
        batch_convert.iter_target_files(tmp_path, recursive=True, source_format="markdown")
    )
    names = sorted(p.name for p in result)
    assert names == ["a.md", "b.md", "c.md"]


def test_iter_target_files_extension_filter(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.html", "c.txt"))
    md = list(batch_convert.iter_target_files(tmp_path, recursive=False, source_format="markdown"))
    html = list(batch_convert.iter_target_files(tmp_path, recursive=False, source_format="html"))
    assert [p.name for p in md] == ["a.md"]
    assert [p.name for p in html] == ["b.html"]


def test_iter_target_files_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = list(
        batch_convert.iter_target_files(missing, recursive=False, source_format="markdown")
    )
    assert result == []


def test_output_path_for_subfolder(tmp_path: Path) -> None:
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    src = tmp_path / "report.md"
    dest = batch_convert.output_path_for(src, plan)
    assert dest == tmp_path / "Output" / "report.html"


def test_output_path_for_same_folder(tmp_path: Path) -> None:
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="same_folder",
        overwrite="always",
    )
    src = tmp_path / "report.md"
    dest = batch_convert.output_path_for(src, plan)
    assert dest == tmp_path / "report.html"


def test_run_batch_happy_path(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.md"))
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_pandoc,
    ):
        report = batch_convert.run_batch(plan)
    assert report.total == 2
    assert report.converted == 2
    assert report.failed == 0
    assert report.skipped == 0
    assert all(e.success for e in report.entries)
    # The Output/ folder is created and contains the targets.
    output_dir = tmp_path / "Output"
    assert output_dir.is_dir()
    assert (output_dir / "a.html").exists()
    assert (output_dir / "b.html").exists()


def test_run_batch_failed_entries(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.md"))
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_failing_pandoc,
    ):
        report = batch_convert.run_batch(plan)
    assert report.total == 2
    assert report.converted == 0
    assert report.failed == 2
    for entry in report.entries:
        assert entry.success is False
        assert entry.error and "simulated failure" in entry.error


def test_run_batch_overwrite_never_skips_existing(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md",))
    # Pre-create the target so the "never" policy kicks in.
    (tmp_path / "Output").mkdir()
    (tmp_path / "Output" / "a.html").write_text("existing", encoding="utf-8")
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="never",
    )
    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_pandoc,
    ) as patched:
        report = batch_convert.run_batch(plan)
    assert patched.call_count == 0
    assert report.skipped == 1
    assert report.failed == 0
    # The pre-existing target is untouched.
    assert (tmp_path / "Output" / "a.html").read_text(encoding="utf-8") == "existing"


def test_run_batch_overwrite_ask_without_callback_raises(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md",))
    (tmp_path / "Output").mkdir()
    (tmp_path / "Output" / "a.html").write_text("existing", encoding="utf-8")
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="ask",
    )
    with pytest.raises(batch_convert.OverwriteRequired) as exc_info:
        batch_convert.run_batch(plan)
    assert len(exc_info.value.outputs) == 1


def test_run_batch_overwrite_ask_with_callback(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md",))
    (tmp_path / "Output").mkdir()
    (tmp_path / "Output" / "a.html").write_text("existing", encoding="utf-8")
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="ask",
    )
    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_pandoc,
    ):
        report = batch_convert.run_batch(plan, ask_overwrite=lambda _p: False)
    assert report.skipped == 1
    assert report.converted == 0
    # The pre-existing target was not overwritten.
    assert (tmp_path / "Output" / "a.html").read_text(encoding="utf-8") == "existing"


def test_run_batch_empty_folder(tmp_path: Path) -> None:
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    progress_calls: list[tuple[str, int, int]] = []

    def progress(msg: str, current: int, total: int) -> None:
        progress_calls.append((msg, current, total))

    report = batch_convert.run_batch(plan, progress=progress)
    assert report.total == 0
    assert report.converted == 0
    assert progress_calls  # at least one progress event so the SR user hears it


def test_run_batch_cancel_event(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.md", "c.md"))
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    cancel = threading.Event()
    cancel.set()  # already cancelled before the loop starts

    progress_calls: list[tuple[str, int, int]] = []

    def progress(msg: str, current: int, total: int) -> None:
        progress_calls.append((msg, current, total))

    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_pandoc,
    ):
        report = batch_convert.run_batch(plan, cancel=cancel, progress=progress)
    assert report.cancelled is True
    assert report.total == 3
    assert report.converted == 0
    # When pre-cancelled, run_batch returns without touching the folder or files.
    assert not (tmp_path / "Output").exists()


def test_run_batch_progress_callback(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md", "b.md"))
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
    )
    events: list[tuple[str, int, int]] = []

    def progress(msg: str, current: int, total: int) -> None:
        events.append((msg, current, total))

    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=_fake_pandoc,
    ):
        batch_convert.run_batch(plan, progress=progress)
    # The last progress call should announce completion.
    assert events[-1][0].startswith("Done:")
    assert events[-1][1] == events[-1][2]  # current == total


def test_run_batch_uses_profile_flags(tmp_path: Path) -> None:
    _make_files(tmp_path, ("a.md",))
    plan = batch_convert.BatchPlan(
        root=tmp_path,
        recursive=False,
        source_format="markdown",
        target_format="html",
        output_layout="subfolder",
        overwrite="always",
        profile="accessible_html_page",
    )
    captured: dict[str, object] = {}

    def spy(source: Path, target: Path, **kwargs: object) -> Path:
        captured["extra_args"] = kwargs.get("extra_args")
        return _fake_pandoc(source, target, **kwargs)

    with mock.patch(
        "quill.core.batch_convert.convert_file_with_pandoc",
        side_effect=spy,
    ):
        batch_convert.run_batch(plan)
    extra = captured.get("extra_args")
    assert isinstance(extra, tuple)
    # The accessible-html profile adds --standalone and metadata flags.
    assert "--standalone" in extra
