"""Resumable, rebuildable records for expensive batch AI runs (#1323).

Idea adopted from HomerScribe: an interrupted batch run resumes where it
stopped, and a "rebuild" path regenerates final outputs from the stored model
results with **zero** model calls. Interruption safety matters most on the slow,
CPU-only machines that are QUILL's core audience -- a two-hour bulk
transcription that dies at unit 240 of 247 must not start over.

Design:

* Each unit of work has a stable string id. As a unit completes, its model
  result is written to a JSON record via :func:`core.storage.write_json_atomic`
  (the same crash-safe, atomic-replace discipline every QUILL store rides), so a
  kill at any moment leaves either the old record or the fully-written new one --
  never a half-file.
* A ``signature`` fingerprints the run's parameters (model, options, ...). If it
  changes, the old results are stale and are dropped rather than silently reused,
  so a resume never blends outputs from two different configurations.
* :func:`run_resumable` drives a run: it skips already-recorded units (resume)
  and computes only the rest. :func:`rebuild` returns the stored results with no
  ``compute`` at all -- the "regenerate outputs without re-querying" path.

Pure and unit-tested; ``compute`` is injected, so nothing here touches a real
model or the network.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.storage import read_json, write_json_atomic

_RECORD_VERSION = 1


class MissingResult(CodedError, KeyError):
    """A rebuild needed a unit's result that the record does not contain."""

    code = "QUILL-AI-RESUME-MISSING"


@dataclass
class ResumeStore:
    """A crash-safe map of ``unit_id -> model result`` for one batch run.

    Persisted to ``path`` on every :meth:`record`. Load an existing run with
    :meth:`load`; a record whose ``signature`` does not match the current run is
    treated as empty so stale results from a different configuration are never
    reused.
    """

    path: Path
    signature: str = ""
    results: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, *, signature: str = "") -> ResumeStore:
        raw = read_json(path, default={})
        if (
            not isinstance(raw, dict)
            or raw.get("version") != _RECORD_VERSION
            or raw.get("signature", "") != signature
        ):
            # Missing, corrupt, old-version, or a different run configuration:
            # start clean rather than resume against mismatched results.
            return cls(path=path, signature=signature, results={})
        stored = raw.get("results")
        results = dict(stored) if isinstance(stored, dict) else {}
        return cls(path=path, signature=signature, results=results)

    def _write(self) -> None:
        write_json_atomic(
            self.path,
            {"version": _RECORD_VERSION, "signature": self.signature, "results": self.results},
        )

    def is_done(self, unit_id: str) -> bool:
        return unit_id in self.results

    def result_for(self, unit_id: str) -> Any | None:
        return self.results.get(unit_id)

    def done_ids(self) -> set[str]:
        return set(self.results)

    def pending(self, all_ids: Iterable[str]) -> list[str]:
        """The ids not yet recorded, in the given order (duplicates dropped)."""
        seen: set[str] = set()
        out: list[str] = []
        for unit_id in all_ids:
            if unit_id not in self.results and unit_id not in seen:
                seen.add(unit_id)
                out.append(unit_id)
        return out

    def record(self, unit_id: str, result: Any) -> None:
        """Persist one unit's result atomically (safe to call after each unit)."""
        self.results[unit_id] = result
        self._write()

    def clear(self) -> None:
        """Forget all results and remove the record file (start a run over)."""
        self.results = {}
        self.path.unlink(missing_ok=True)


def run_resumable(
    all_ids: Iterable[str],
    compute: Callable[[str], Any],
    store: ResumeStore,
    *,
    on_result: Callable[[str, Any, bool], None] | None = None,
) -> dict[str, Any]:
    """Compute a result for every id, skipping ones already in ``store``.

    ``compute(unit_id)`` runs only for pending units; each result is recorded
    atomically as it lands, so an interruption resumes here next time.
    ``on_result(unit_id, result, from_cache)`` (optional) is called for every
    unit in order -- ``from_cache=True`` for a resumed one, so a caller can drive
    progress. Returns ``{unit_id: result}`` for all ids, in order.
    """
    ordered = list(dict.fromkeys(all_ids))  # de-dupe, keep order
    out: dict[str, Any] = {}
    for unit_id in ordered:
        if store.is_done(unit_id):
            result = store.result_for(unit_id)
            from_cache = True
        else:
            result = compute(unit_id)
            store.record(unit_id, result)
            from_cache = False
        out[unit_id] = result
        if on_result is not None:
            on_result(unit_id, result, from_cache)
    return out


def rebuild(store: ResumeStore, all_ids: Iterable[str]) -> dict[str, Any]:
    """Return stored results for ``all_ids`` with **no** compute (rebuild path).

    Raises :class:`MissingResult` if any id was never recorded -- a rebuild must
    be honest about an incomplete run rather than silently omitting outputs.
    """
    ordered = list(dict.fromkeys(all_ids))
    missing = [unit_id for unit_id in ordered if not store.is_done(unit_id)]
    if missing:
        raise MissingResult(
            f"cannot rebuild: {len(missing)} unit(s) have no stored result: {missing[:5]}"
        )
    return {unit_id: store.result_for(unit_id) for unit_id in ordered}
