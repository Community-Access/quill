"""QUILL's multi-file results say what is now true, and where (FUX-04)."""

from __future__ import annotations

from pathlib import PureWindowsPath

from quill.core.batch_convert import BatchEntry, BatchPlan, BatchReport
from quill.core.document_results import (
    batch_conversion_details,
    batch_conversion_folder,
    batch_conversion_result,
    distinct_names,
    joined,
    save_all_result,
)

DOCS = PureWindowsPath(r"C:\Users\pat\Documents")
WORK = PureWindowsPath(r"C:\Users\pat\Work")


def test_names_are_told_apart_by_folder_only_when_they_clash() -> None:
    paths = [DOCS / "notes.md", WORK / "notes.md", DOCS / "plan.md"]
    assert distinct_names(paths) == ["notes.md in Documents", "notes.md in Work", "plan.md"]


def test_joined_lists_three_then_counts_the_rest() -> None:
    assert joined(["a"]) == "a"
    assert joined(["a", "b"]) == "a and b"
    assert joined(["a", "b", "c", "d", "e"]) == "a, b, c and 2 more"


def test_save_all_with_nothing_changed_does_not_claim_a_save() -> None:
    assert save_all_result([]) == "Nothing needed saving."


def test_save_all_of_one_names_the_file_and_folder() -> None:
    assert save_all_result([DOCS / "plan.md"]) == "Saved plan.md in Documents."


def test_save_all_of_several_tells_duplicate_names_apart() -> None:
    said = save_all_result([DOCS / "notes.md", WORK / "notes.md"])
    assert said == "Saved 2 documents: notes.md in Documents and notes.md in Work."


def test_save_all_that_stopped_says_what_is_still_unsaved() -> None:
    said = save_all_result([DOCS / "plan.md"], stopped_at="Untitled 2", left=2)
    assert said == (
        "Saved plan.md in Documents. Stopped at Untitled 2, which is not saved. "
        "2 more are not saved."
    )
    assert save_all_result([], stopped_at="Untitled", left=1) == (
        "Stopped at Untitled, which is not saved. 1 more is not saved."
    )


def _report(entries: list[BatchEntry], *, cancelled: bool = False, total: int = 0) -> BatchReport:
    plan = BatchPlan(
        root=DOCS,  # type: ignore[arg-type]
        recursive=False,
        source_format="markdown",
        target_format="docx",
        output_layout="subfolder",
        overwrite="never",
    )
    converted = sum(1 for e in entries if e.success)
    skipped = sum(1 for e in entries if e.error and "overwrite" in e.error.lower())
    failed = len(entries) - converted - skipped - (1 if cancelled else 0)
    return BatchReport(
        plan=plan,
        total=total or len(entries),
        converted=converted,
        skipped=skipped,
        failed=failed,
        entries=tuple(entries),
        duration_seconds=1.0,
        cancelled=cancelled,
    )


def _ok(name: str) -> BatchEntry:
    return BatchEntry(DOCS / name, DOCS / "Output" / (name[:-3] + ".docx"), True, 0, None, 0.1)  # type: ignore[arg-type]


def _bad(folder: PureWindowsPath, name: str, error: str = "pandoc exited 1") -> BatchEntry:
    return BatchEntry(folder / name, None, False, 0, error, 0.1)  # type: ignore[arg-type]


def test_batch_says_where_the_files_are() -> None:
    report = _report([_ok("a.md"), _ok("b.md")])
    assert batch_conversion_result(report) == (
        "Converted 2 files. They are in Output in Documents."
    )
    assert batch_conversion_folder(report) == DOCS / "Output"


def test_batch_names_failures_and_skips_separately() -> None:
    skipped = _bad(DOCS, "c.md", "Output already exists; overwrite policy is 'never'.")
    report = _report([_ok("a.md"), _bad(DOCS, "notes.md"), _bad(WORK, "notes.md"), skipped])
    assert batch_conversion_result(report) == (
        "Converted 1 of 4 files. It is in Output in Documents. "
        "2 failed: notes.md in Documents and notes.md in Work. "
        "1 skipped, because the converted file was already there."
    )
    details = batch_conversion_details(report)
    assert r"Not converted: C:\Users\pat\Work\notes.md: pandoc exited 1" in details
    assert r"Converted: C:\Users\pat\Documents\a.md to " in details


def test_a_stopped_batch_says_what_was_not_reached() -> None:
    report = _report([_ok("a.md"), _bad(DOCS, "b.md", "Cancelled")], cancelled=True, total=5)
    said = batch_conversion_result(report)
    assert said.startswith("Converted 1 of 5 files")
    assert "failed" not in said
    assert said.endswith("Stopped before the last 4 files; they were not converted.")


def test_a_batch_that_found_nothing_says_so() -> None:
    assert batch_conversion_result(_report([], total=0)) == (
        "Batch conversion found no files to convert in Documents."
    )
