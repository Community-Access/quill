"""QUILL against QAF's form model conformance suite: the one contract both keep.

Two runs of the same checks:

- the vendored subset in ``fixtures/conformance`` (always; CI has no QAF);
- every case in QAF's own ``tests/conformance/manifest.json``, when QAF is on
  this machine: from its working tree, or with ``git archive`` from the
  ``chore/rename-qaf`` branch, falling back to ``feat/json-form-model``'s older
  layout, into a temporary folder (nothing in QAF is touched). Skipped, with
  the reason, when none is possible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from forms_baf_sources import qaf_root  # noqa: E402
from forms_conformance import OLD_KINDS, SUITE_KINDS, Suite, materialize  # noqa: E402

VENDORED = Path(__file__).parent / "fixtures" / "conformance" / "manifest.json"


@pytest.mark.parametrize("kind", SUITE_KINDS)
def test_vendored_suite(kind: str) -> None:
    assert Suite(VENDORED).check(kind) == []


def test_vendored_suite_has_every_kind_we_run() -> None:
    kinds = {s["kind"] for s in Suite(VENDORED).manifest["suites"]}
    assert set(SUITE_KINDS) <= kinds


_LIVE: dict[str, Suite | None] = {}


def _live() -> Suite | None:
    if "suite" not in _LIVE:
        root = qaf_root()
        found = materialize(root) if root else None
        _LIVE["suite"] = Suite(found / "tests" / "conformance" / "manifest.json") if found else None
    return _LIVE["suite"]


@pytest.mark.parametrize("kind", SUITE_KINDS)
def test_every_case_in_qafs_manifest(kind: str) -> None:
    suite = _live()
    if suite is None:
        pytest.skip(
            "QAF's conformance suite is not on this machine (needs S:\\code\\baf or QUILL_BAF_ROOT, "  # noqa: E501
            "with the chore/rename-qaf or feat/json-form-model branch); the vendored subset still ran."  # noqa: E501
        )
    assert suite.check(kind) == []


def test_the_live_suite_is_the_whole_suite() -> None:
    suite = _live()
    if suite is None:
        pytest.skip("QAF's conformance suite is not on this machine.")
    assert suite.case_count() >= 15
    renamed = {v: k for k, v in OLD_KINDS.items()}
    kinds = {renamed.get(s["kind"], s["kind"]) for s in suite.manifest["suites"]}
    assert kinds >= set(SUITE_KINDS)
