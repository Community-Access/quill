"""One scorecard over every gate QUILL already runs (polish.md P5.4).

The repo's quality culture is a dozen ratchet gates — module budgets, banned
patterns, egress audit, error codes, dialog inventory, docs artifacts, the
runtime inventory — each excellent alone and each invisible until it fails.
This tool runs them all and emits a single accessible Markdown scorecard, so
"the platform's footing" is an instrument you can read (and trend in CI)
rather than folklore. It exists because 2026-08-17's review found a gate that
was written, tested, and never wired in: a visible roster makes a silent gate
conspicuous.

Usage::

    python -m quill.tools.platform_report            # scorecard to stdout
    python -m quill.tools.platform_report --out platform-report.md

Exit code is non-zero when any gate fails, so CI can consume it directly.
Heavy externally-dependent steps (pip-audit, pandoc rendering) belong to
release_readiness and are deliberately not duplicated here — this is the
fast, offline, every-commit view.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Gate:
    """One gate: a name, what it protects, and how to run it."""

    name: str
    protects: str
    argv: tuple[str, ...]


#: The roster. Adding a gate to the codebase and not listing it here is the
#: "written but never wired" failure this tool exists to make conspicuous —
#: test_platform_report cross-checks this list against quill/tools.
GATES: tuple[Gate, ...] = (
    Gate(
        "banned-patterns",
        "UI-thread and dialog-contract invariants (incl. GATE-40 threads)",
        (sys.executable, "-m", "quill.tools.check_banned_patterns"),
    ),
    Gate(
        "module-size-budget",
        "GATE-11: module line-count ratchet",
        (sys.executable, "-m", "quill.tools.module_size_budget"),
    ),
    Gate(
        "network-egress",
        "every outbound call site is inventoried and reviewed",
        (sys.executable, "-m", "quill.tools.network_egress_audit"),
    ),
    Gate(
        "error-codes",
        "GATE-EC: every custom exception is coded",
        (sys.executable, "-m", "quill.tools.error_code_audit"),
    ),
    Gate(
        "dialog-inventory",
        "every modal goes through the hardened path",
        (sys.executable, "-m", "quill.tools.dialog_inventory"),
    ),
    Gate(
        "dialog-buttons",
        "Close/Cancel buttons are bound (modeless-safe)",
        (sys.executable, "-m", "quill.tools.dialog_button_contract"),
    ),
    Gate(
        "docs-artifacts",
        "changed Markdown ships regenerated HTML/EPUB",
        (sys.executable, "scripts/check_docs_artifacts.py"),
    ),
    Gate(
        "runtime-inventory",
        "the shared runtime contains exactly what is declared",
        (
            sys.executable,
            "scripts/check_runtime_inventory.py",
            "standalone/runtime/dist/QuillVilleRuntime",
        ),
    ),
    Gate(
        "quillin-lint",
        "bundled Quillins meet the extension standards",
        (sys.executable, "-m", "quill.tools.quillin_lint", "quill/quillins_bundled", "--strict"),
    ),
    Gate(
        "agent-standards",
        "bundled agents meet the agent standards",
        (sys.executable, "-m", "quill.tools.agent_lint", "quill/core/ai/agents", "--strict"),
    ),
    # The eleven below were surfaced by this tool's own roster cross-check on
    # its first run — each ran green standalone but none had a shared surface.
    Gate(
        "accessible-names",
        "controls carry accessible names",
        (sys.executable, "-m", "quill.tools.accessible_name_audit"),
    ),
    Gate(
        "radio-help",
        "GATE-RADIO-HELP: every radio surface and control answers F1",
        (sys.executable, "-m", "quill.tools.radio_help_audit"),
    ),
    Gate(
        "announce-gap",
        "user-visible outcomes are announced",
        (sys.executable, "-m", "quill.tools.check_announce_gap"),
    ),
    Gate(
        "copy-tray-binding",
        "tray copy bindings stay consistent",
        (sys.executable, "-m", "quill.tools.check_copy_tray_binding"),
    ),
    Gate(
        "dialog-zorder",
        "labels precede fields in tab order",
        (sys.executable, "-m", "quill.tools.check_dialog_zorder"),
    ),
    Gate(
        "feature-tags",
        "feature flags are declared and tagged",
        (sys.executable, "-m", "quill.tools.check_feature_tags"),
    ),
    Gate(
        "help-coverage",
        "shipped features have help coverage",
        (sys.executable, "-m", "quill.tools.check_help_coverage"),
    ),
    Gate(
        "listbox-activation",
        "list rows activate from the keyboard",
        (sys.executable, "-m", "quill.tools.check_listbox_activation"),
    ),
    Gate(
        "publishing-providers",
        "publishing providers meet their contract",
        (sys.executable, "-m", "quill.tools.check_publishing_providers"),
    ),
    Gate(
        "translation",
        "i18n catalogs parse and stay in sync",
        (sys.executable, "-m", "quill.tools.check_translation"),
    ),
    Gate(
        "method-contracts",
        "mixin host-method contracts hold",
        (sys.executable, "-m", "quill.tools.method_contract_audit"),
    ),
    Gate(
        "binding-labels",
        "menu labels match their bindings",
        (sys.executable, "-m", "quill.tools._check_binding_label_consistency"),
    ),
)


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: Gate
    passed: bool
    seconds: float
    detail: str  # last output line on failure, "" on success
    skipped: bool = False


def run_gate(gate: Gate) -> GateResult:
    """Run one gate; a gate whose subject is absent (e.g. no runtime dist on a
    fresh clone) reports as skipped rather than failed."""
    if gate.name == "runtime-inventory":
        dist = _REPO_ROOT / "standalone" / "runtime" / "dist" / "QuillVilleRuntime"
        if not dist.is_dir():
            return GateResult(gate, True, 0.0, "no runtime dist built here", skipped=True)
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(gate.argv),
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except Exception as exc:  # noqa: BLE001 - a gate that cannot run is a failure
        return GateResult(gate, False, time.perf_counter() - started, str(exc))
    elapsed = time.perf_counter() - started
    if proc.returncode == 0:
        return GateResult(gate, True, elapsed, "")
    tail = (proc.stdout.strip() or proc.stderr.strip()).splitlines()
    return GateResult(gate, False, elapsed, tail[-1] if tail else f"exit {proc.returncode}")


def render_markdown(results: list[GateResult]) -> str:
    """The scorecard, accessible-first: a real table, states as words."""
    failed = [r for r in results if not r.passed]
    lines = [
        "# QUILL platform scorecard",
        "",
        f"**{len(results) - len(failed)} of {len(results)} gates passing.**"
        + (" All green." if not failed else f" **{len(failed)} FAILING.**"),
        "",
        "| Gate | Protects | State | Time |",
        "|---|---|---|---|",
    ]
    for r in results:
        state = "skipped" if r.skipped else ("pass" if r.passed else "**FAIL**")
        lines.append(f"| {r.gate.name} | {r.gate.protects} | {state} | {r.seconds:.1f}s |")
    if failed:
        lines += ["", "## Failures", ""]
        lines += [f"- **{r.gate.name}**: {r.detail}" for r in failed]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--out", type=Path, default=None, help="also write the scorecard here")
    args = parser.parse_args()
    results = [run_gate(gate) for gate in GATES]
    report = render_markdown(results)
    print(report)
    if args.out is not None:
        args.out.write_text(report, encoding="utf-8")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
