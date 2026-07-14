"""Phase 0 footprint report — read-only size + machine-context inventory.

Implements the AI footprint & optimization measurement phase (QUILL-PRD.md §5.25f;
open work tracked in docs/planning/roadmap.md §1.2). This script produces the diffable
baseline that every later phase is judged against: which installed components are large,
which on-disk models/assets exist, and the machine context for the run.

Design constraints (all honoured here):

- **Read-only.** Filesystem walks only. No file is created, moved, or deleted in
  any measured tree. No network. No ``wx`` import. Safe to run any time.
- **Degrades, never crashes.** A missing root, an unreadable file, or an absent
  ``psutil`` becomes a recorded note, not a traceback.
- **Machine-readable + speakable.** Emits JSON (diffable release-over-release) and
  a short Markdown summary (screen-reader friendly, plain ASCII).

Scope note: per-engine peak RSS and cold-start / first-output timings require loading
each engine and are measured by the companion ``scripts/footprint_live.py`` (isolated
subprocess per engine, real numbers or a note — never fabricated), which can merge them
into this baseline. This static script covers installed size by component, on-disk
model/asset sizes, and machine context, plus a best-effort current-process RSS snapshot.
Together they are the committed artifact for the later footprint/optimization phases.

Usage::

    python scripts/footprint_report.py                 # print summary + write baseline
    python scripts/footprint_report.py --out DIR       # choose output directory
    python scripts/footprint_report.py --root PATH      # measure an installed build tree
    python scripts/footprint_report.py --top 25         # rows in the Markdown table
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import site
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_BYTES_PER_MB = 1024 * 1024


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #
def human_bytes(n: int) -> str:
    """Speakable size, e.g. ``5.8 MB`` / ``1.2 GB`` — plain ASCII, no unicode."""
    mb = n / _BYTES_PER_MB
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    if mb >= 1:
        return f"{mb:.1f} MB"
    return f"{n / 1024:.1f} KB"


@dataclass
class Component:
    """One measured directory or file, attributed to a category."""

    name: str
    category: str
    bytes: int
    path: str


def sort_desc(components: list[Component]) -> list[Component]:
    """Biggest-first, stable on ties by name — the report's headline ordering."""
    return sorted(components, key=lambda c: (-c.bytes, c.name))


def total_bytes(components: list[Component]) -> int:
    return sum(c.bytes for c in components)


@dataclass
class Report:
    generated_at: str
    platform: str
    python: str
    machine: dict[str, object]
    process_rss_bytes: int | None
    components: list[Component] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        d = asdict(self)
        d["components"] = [asdict(c) for c in sort_desc(self.components)]
        return d


# --------------------------------------------------------------------------- #
# Measurement (read-only filesystem walks)
# --------------------------------------------------------------------------- #
def dir_size(path: Path) -> int:
    """Sum of regular-file sizes under ``path``; unreadable entries are skipped."""
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda _e: None):
        for name in files:
            fp = Path(root) / name
            try:
                if fp.is_symlink():
                    continue
                total += fp.stat().st_size
            except OSError:
                continue
    return total


def _site_package_roots(explicit_root: Path | None) -> list[Path]:
    """Locate the site-packages tree(s) to inventory.

    With ``--root`` (an installed build), prefer its ``Lib/site-packages``. In a
    dev checkout, use the current interpreter's site directories.
    """
    if explicit_root is not None:
        candidates = [
            explicit_root / "Lib" / "site-packages",
            explicit_root / "lib" / "site-packages",
            explicit_root,
        ]
        return [c for c in candidates if c.is_dir()][:1] or [explicit_root]
    roots: list[Path] = []
    try:
        roots.extend(Path(p) for p in site.getsitepackages())
    except AttributeError:  # virtualenv without getsitepackages
        pass
    try:
        user = site.getusersitepackages()
        if user:
            roots.append(Path(user))
    except AttributeError:
        pass
    # ``getsitepackages`` returns ``sys.prefix`` too on Windows; that root contains
    # ``Lib/`` (which already contains site-packages), so measuring it would
    # double-count every wheel and add stdlib/Scripts noise. Keep only the actual
    # ``site-packages`` directories.
    site_only = [r for r in roots if r.name == "site-packages"]
    chosen = site_only or roots
    seen: set[Path] = set()
    out: list[Path] = []
    for r in chosen:
        rp = r.resolve()
        if rp.is_dir() and rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def inventory_site_packages(explicit_root: Path | None, notes: list[str]) -> list[Component]:
    """Size every top-level entry under site-packages, biggest-first."""
    components: list[Component] = []
    roots = _site_package_roots(explicit_root)
    if not roots:
        notes.append("site-packages: no root found (measured nothing).")
        return components
    for root in roots:
        for entry in root.iterdir():
            if entry.name.endswith((".dist-info", ".egg-info", "__pycache__")):
                continue
            size = dir_size(entry)
            if size == 0:
                continue
            components.append(
                Component(name=entry.name, category="site-packages", bytes=size, path=str(entry))
            )
    return components


def _runtime_files(explicit_root: Path | None) -> list[Component]:
    """Embedded-runtime top-level files (python3NN.dll / .zip) when a build root is given."""
    if explicit_root is None:
        return []
    out: list[Component] = []
    for pattern in ("python*.dll", "python*.zip"):
        for fp in explicit_root.glob(pattern):
            out.append(
                Component(name=fp.name, category="runtime", bytes=dir_size(fp), path=str(fp))
            )
    return out


def inventory_data_dir(notes: list[str]) -> list[Component]:
    """On-disk models/assets under the user data dir (speech + GGUF + kokoro + ffmpeg)."""
    components: list[Component] = []
    try:
        from quill.core.paths import app_data_dir

        data = app_data_dir()
    except Exception as exc:  # noqa: BLE001 - report the reason, don't crash
        notes.append(f"data dir: unavailable ({exc.__class__.__name__}).")
        return components
    if not data.exists():
        notes.append(f"data dir: {data} does not exist yet (no on-disk models).")
        return components
    for sub in ("speech-models", "models", "kokoro-models", "speech-engine", "tools"):
        p = data / sub
        if p.exists():
            size = dir_size(p)
            if size:
                components.append(
                    Component(name=f"data/{sub}", category="data", bytes=size, path=str(p))
                )
    if not components:
        notes.append(f"data dir: {data} has no measured model/asset subdirs.")
    return components


def machine_context(notes: list[str]) -> dict[str, object]:
    """RAM / GPU / free disk via the existing wx-free detectors; tolerant of absence."""
    ctx: dict[str, object] = {}
    try:
        from quill.core.speech import service

        ctx["total_ram_gb"] = round(service.detect_total_ram_gb(), 1)
        ctx["has_gpu"] = bool(service.detect_has_gpu())
        free = service.models_dir_free_gb()
        ctx["models_dir_free_gb"] = round(free, 1) if free >= 0 else None
    except Exception as exc:  # noqa: BLE001
        notes.append(f"machine context: partial ({exc.__class__.__name__}).")
    return ctx


def process_rss(notes: list[str]) -> int | None:
    """Best-effort current-process RSS; None (with a note) if psutil is absent."""
    try:
        import psutil  # type: ignore
    except ImportError:
        notes.append("process RSS: psutil not installed (RSS unavailable).")
        return None
    try:
        return int(psutil.Process().memory_info().rss)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"process RSS: unavailable ({exc.__class__.__name__}).")
        return None


def build_report(explicit_root: Path | None) -> Report:
    notes: list[str] = []
    components: list[Component] = []
    components.extend(_runtime_files(explicit_root))
    components.extend(inventory_site_packages(explicit_root, notes))
    components.extend(inventory_data_dir(notes))
    return Report(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        platform=platform.platform(),
        python=platform.python_version(),
        machine=machine_context(notes),
        process_rss_bytes=process_rss(notes),
        components=components,
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_markdown(report: Report, top: int) -> str:
    rows = sort_desc(report.components)
    grand = total_bytes(rows)
    m = report.machine
    ram = m.get("total_ram_gb", "unknown")
    gpu = "yes" if m.get("has_gpu") else "no"
    free = m.get("models_dir_free_gb")
    free_txt = f"{free} GB" if free is not None else "unknown"
    rss = human_bytes(report.process_rss_bytes) if report.process_rss_bytes else "unavailable"

    lines: list[str] = []
    lines.append("# QUILL footprint baseline (Phase 0)")
    lines.append("")
    lines.append(f"- Generated: {report.generated_at}")
    lines.append(f"- Platform: {report.platform}")
    lines.append(f"- Python: {report.python}")
    lines.append(f"- Total RAM: {ram} GB; GPU present: {gpu}; models-dir free: {free_txt}")
    lines.append(f"- Report process RSS: {rss}")
    lines.append(f"- Measured components: {len(rows)}, total {human_bytes(grand)}")
    lines.append("")
    lines.append(f"## Largest components (top {top})")
    lines.append("")
    lines.append("| Size | Component | Category |")
    lines.append("| --- | --- | --- |")
    for c in rows[:top]:
        lines.append(f"| {human_bytes(c.bytes)} | {c.name} | {c.category} |")
    lines.append("")
    if report.notes:
        lines.append("## Notes")
        lines.append("")
        for n in report.notes:
            lines.append(f"- {n}")
        lines.append("")
    lines.append(
        "Read-only inventory. Sizes are uncompressed on-disk bytes; the installer "
        "compresses, so installer contribution is smaller. Per-engine peak RSS and "
        "cold-start timings are captured in-app, not by this static script."
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QUILL Phase 0 footprint report (read-only).")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Installed build tree to measure (default: current interpreter site-packages).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/planning/footprint"),
        help="Directory for footprint-baseline.json (default: docs/planning/footprint).",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help=(
            "Optional path to also write the Markdown summary. Omitted by default so a "
            "run never drops an un-rendered .md into the docs artifact-gated tree; the "
            "summary is always printed to stdout. Point it outside docs/ (e.g. build/)."
        ),
    )
    parser.add_argument("--top", type=int, default=25, help="Rows in the Markdown table.")
    parser.add_argument(
        "--print-only", action="store_true", help="Print the summary, do not write files."
    )
    args = parser.parse_args(argv)

    report = build_report(args.root)
    markdown = render_markdown(report, args.top)

    if not args.print_only:
        # Only the machine-readable JSON is committed under docs/ — it is the
        # diffable baseline and is not subject to the docs HTML/EPUB artifact gate
        # (that gate targets .md). The human summary is printed (and optionally
        # written via --md-out) so a routine run never creates a gated .md.
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "footprint-baseline.json").write_text(
            json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {args.out / 'footprint-baseline.json'}")
        if args.md_out is not None:
            args.md_out.parent.mkdir(parents=True, exist_ok=True)
            args.md_out.write_text(markdown, encoding="utf-8")
            print(f"Wrote {args.md_out}")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
