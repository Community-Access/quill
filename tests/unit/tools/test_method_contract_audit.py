"""Gate: no calls to never-defined private methods (CALL-1)."""

from __future__ import annotations

from pathlib import Path

from quill.tools.method_contract_audit import find_undefined_private_calls


def test_no_undefined_private_method_calls() -> None:
    findings = find_undefined_private_calls()
    detail = "; ".join(
        f"self.{name}() at {', '.join(sites)}" for name, sites in sorted(findings.items())
    )
    assert not findings, (
        "Call(s) to never-defined self._private() method(s) found. Fix the typo or "
        "define the method (this class previously crashed Settings apply/reset): " + detail
    )


def test_audit_flags_a_synthetic_undefined_call(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        "class A:\n"
        "    def run(self):\n"
        "        self._defined()\n"
        "        self._missing()\n"
        "    def _defined(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    findings = find_undefined_private_calls(tmp_path)
    assert "_missing" in findings
    assert "_defined" not in findings


def test_audit_accepts_attribute_and_dataclass_callbacks(tmp_path: Path) -> None:
    # A private name provided as an instance/class attribute (e.g. an injected
    # callback) is defined for our purposes and must not be flagged.
    (tmp_path / "mod.py").write_text(
        "class A:\n"
        "    _hook = None\n"
        "    def __init__(self, cb):\n"
        "        self._cb = cb\n"
        "    def run(self):\n"
        "        self._cb()\n"
        "        self._hook()\n",
        encoding="utf-8",
    )
    assert find_undefined_private_calls(tmp_path) == {}
