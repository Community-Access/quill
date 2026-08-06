"""Tests for resumable/rebuildable batch-AI records (#1323)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.resume_record import (
    MissingResult,
    ResumeStore,
    rebuild,
    run_resumable,
)


def test_record_persists_and_reloads(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    store = ResumeStore.load(path, signature="sig-1")
    store.record("a", {"text": "alpha"})
    store.record("b", {"text": "beta"})

    reloaded = ResumeStore.load(path, signature="sig-1")
    assert reloaded.result_for("a") == {"text": "alpha"}
    assert reloaded.done_ids() == {"a", "b"}


def test_signature_mismatch_starts_clean(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    ResumeStore.load(path, signature="model-v1").record("a", "old")

    # A different run configuration must not resume against stale results.
    fresh = ResumeStore.load(path, signature="model-v2")
    assert fresh.results == {}
    assert not fresh.is_done("a")


def test_pending_filters_done_keeps_order_dedupes(tmp_path: Path) -> None:
    store = ResumeStore.load(tmp_path / "r.json")
    store.record("b", 1)
    assert store.pending(["a", "b", "c", "a"]) == ["a", "c"]


def test_run_resumable_computes_only_pending_and_resumes_after_interruption(
    tmp_path: Path,
) -> None:
    path = tmp_path / "run.json"
    ids = ["u1", "u2", "u3"]
    calls: list[str] = []

    def compute(unit_id: str) -> str:
        calls.append(unit_id)
        if unit_id == "u3":
            raise RuntimeError("simulated crash before u3 completes")
        return f"result-{unit_id}"

    store = ResumeStore.load(path, signature="s")
    with pytest.raises(RuntimeError):
        run_resumable(ids, compute, store)
    # u1, u2 recorded before the crash; u3 attempted, not recorded.
    assert calls == ["u1", "u2", "u3"]
    assert ResumeStore.load(path, signature="s").done_ids() == {"u1", "u2"}

    # Resume: a fresh store reloads the record and computes only u3.
    calls.clear()
    resumed = ResumeStore.load(path, signature="s")
    out = run_resumable(ids, lambda u: f"result-{u}", resumed)
    assert calls == []  # compute passed above never raised; count via output
    assert out == {"u1": "result-u1", "u2": "result-u2", "u3": "result-u3"}
    assert resumed.done_ids() == {"u1", "u2", "u3"}


def test_run_resumable_reports_cache_vs_computed(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    store = ResumeStore.load(path)
    store.record("u1", "cached")

    seen: list[tuple[str, bool]] = []
    run_resumable(
        ["u1", "u2"],
        lambda u: "computed",
        store,
        on_result=lambda uid, _res, from_cache: seen.append((uid, from_cache)),
    )
    assert seen == [("u1", True), ("u2", False)]


def test_rebuild_returns_stored_without_recompute(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    store = ResumeStore.load(path)
    store.record("u1", "one")
    store.record("u2", "two")

    # A brand-new store (no compute available at all) rebuilds from disk.
    loaded = ResumeStore.load(path)
    assert rebuild(loaded, ["u1", "u2"]) == {"u1": "one", "u2": "two"}


def test_rebuild_raises_on_incomplete_run(tmp_path: Path) -> None:
    store = ResumeStore.load(tmp_path / "run.json")
    store.record("u1", "one")
    with pytest.raises(MissingResult):
        rebuild(store, ["u1", "u2"])


def test_clear_removes_the_record(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    store = ResumeStore.load(path)
    store.record("u1", "one")
    assert path.exists()
    store.clear()
    assert not path.exists()
    assert ResumeStore.load(path).results == {}


def test_corrupt_or_old_record_starts_clean(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text("{ not valid json", encoding="utf-8")
    assert ResumeStore.load(path).results == {}

    path.write_text('{"version": 0, "results": {"a": 1}}', encoding="utf-8")
    assert ResumeStore.load(path).results == {}
