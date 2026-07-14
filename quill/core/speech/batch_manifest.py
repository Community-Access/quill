"""Run manifest for batch document-to-speech (the optional report sidecar).

wx-free, strict-typed. Writes ``manifest.json`` + ``manifest.csv`` summarizing a
batch export — one row per file with its status, output path, duration, and any
error — into the output folder. Kept out of ``batch_export`` so the pipeline
module stays focused on synthesis; :func:`quill.core.speech.batch_export.run_batch_export`
calls this when ``BatchExportOptions.write_manifest`` is set.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.storage import write_json_atomic

if TYPE_CHECKING:
    from quill.core.speech.batch_export import BatchFileResult

_FIELDS = ["source", "output", "status", "error", "duration_s", "pronunciation_applied"]


def write_manifest(output_folder: Path, results: list[BatchFileResult]) -> tuple[Path, Path]:
    """Write ``manifest.json`` and ``manifest.csv`` for *results*; return their paths."""
    output_folder.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for res in results:
        rows.append({
            "source": str(res.source_path),
            "output": str(res.output_path) if res.output_path else "",
            "status": res.status,
            "error": res.error or "",
            "duration_s": round(res.duration_s, 3) if res.duration_s is not None else "",
            "pronunciation_applied": res.pronunciation_applied,
        })

    json_path = output_folder / "manifest.json"
    write_json_atomic(json_path, {"files": rows})

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    csv_path = output_folder / "manifest.csv"
    csv_path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    return json_path, csv_path
