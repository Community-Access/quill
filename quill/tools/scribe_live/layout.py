"""The run folder: the corpus layout, ``validation.json``, ``README.md``, ``run.json``.

The layout is Pneuma's, so the replay tests (``tests/unit/core/scribe/corpus.py``)
read a live run exactly as they read their corpus::

    html/<stem>.html            offline-html/<stem>-offline.html (or .zip)
    docx/ pdf/ epub/ mobi/ brf/ mp3/   <stem>.<ext>
    daisy/<stem>-daisy3.zip     sources/   README.md   validation.json

``<stem>`` is the source's stem, then the variant's label (``-large-print``,
``-math-on``, ``-brf-en-ueb-g2-32x20``...). ``validation.json`` is keyed
``<run id>/<folder>/<stem><ext>`` as Pneuma's is (``s1`` to ``s4`` and ``v1``,
``v2`` for the replayed ones). ``run.json`` is this tool's own record: the
plan, what happened to each upload, the credit used, and the Scribe document
IDs the clean-up deletes. Never a token and never the account's name.

Everything here is written outside the repository; wx-free, no network.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.scribe.model import FORMAT_IDS, format_label
from quill.core.storage import write_json_atomic
from quill.tools.scribe_live.facts import facts_for
from quill.tools.scribe_live.plan import BASE_SETTINGS, Plan, Upload
from quill.tools.scribe_live.sources import PNEUMA, Found

RUN_RECORD = "run.json"
RECORD_VERSION = 1

#: format -> the folder its files go in.
FOLDERS: dict[str, str] = {
    "html": "html",
    "offline_html": "offline-html",
    "docx": "docx",
    "pdf": "pdf",
    "epub": "epub",
    "mobi": "mobi",
    "brf": "brf",
    "mp3": "mp3",
    "daisy": "daisy",
}
#: validation.json's folder name for each format (Pneuma's).
VALIDATION_FOLDERS: dict[str, str] = {**FOLDERS, "offline_html": "offline_html"}
_BY_FOLDER = {folder: format_id for format_id, folder in FOLDERS.items()}


def final_name(format_id: str, file_stem: str, saved: Path) -> str:
    """The file's name in the layout, from where QUILL saved it."""
    if format_id == "offline_html":
        return f"{file_stem}-offline{saved.suffix.lower() or '.html'}"
    if format_id == "daisy":
        return f"{file_stem}-daisy3.zip"
    return f"{file_stem}{saved.suffix.lower()}"


def format_of(relative: str) -> str:
    """The format a layout path holds: ``"brf/x.brf"`` -> ``"brf"``."""
    return _BY_FOLDER.get(relative.split("/", 1)[0], "")


def layout_files(run_dir: Path) -> dict[str, Path]:
    """Every output in a run (or corpus) folder, by its path relative to it."""
    found: dict[str, Path] = {}
    for folder in FOLDERS.values():
        place = run_dir / folder
        if place.is_dir():
            for path in sorted(place.iterdir()):
                if path.is_file():
                    found[f"{folder}/{path.name}"] = path
    return found


def place_outputs(run_dir: Path, upload: Upload, outputs: dict[str, str]) -> dict[str, str]:
    """Move one upload's saved files into the layout; returns format -> relative path.

    The staging folder QUILL saved into (and the DAISY book it unpacked there)
    is removed afterwards: only the files Scribe returned stay.
    """
    placed: dict[str, str] = {}
    labels = {c.format: c for c in upload.conversions}
    for format_id, saved_text in outputs.items():
        saved = Path(saved_text)
        conversion = labels.get(format_id)
        if conversion is None or not saved.is_file():
            continue
        name = final_name(format_id, conversion.file_stem(upload.source.stem), saved)
        target = run_dir / FOLDERS[format_id] / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(saved), str(target))
        placed[format_id] = f"{FOLDERS[format_id]}/{name}"
    staging = staging_folder(run_dir, upload)
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    return placed


def staging_folder(run_dir: Path, upload: Upload) -> Path:
    return run_dir / ".staging" / upload.name


def copy_sources(run_dir: Path, plan: Plan) -> None:
    """The sources this run sent, beside its outputs (never into the repository)."""
    folder = run_dir / "sources"
    folder.mkdir(parents=True, exist_ok=True)
    for upload in plan.uploads:
        path = upload.source.path
        if path is not None and not (folder / path.name).exists():
            shutil.copyfile(path, folder / path.name)


def validation_key(run_id: str, relative: str) -> str:
    """``"s1/offline_html/<stem>.html"`` for ``"offline-html/<stem>-offline.html"``."""
    format_id = format_of(relative)
    name = Path(relative).name
    stem, suffix = Path(name).stem, Path(name).suffix
    if format_id == "offline_html":
        stem = stem.removesuffix("-offline")
    if format_id == "daisy":
        stem = stem.removesuffix("-daisy3")
    return f"{run_id}/{VALIDATION_FOLDERS[format_id]}/{stem}{suffix}"


def write_validation(run_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    """Facts for every placed file, keyed as Pneuma's ``validation.json``."""
    data: dict[str, Any] = {}
    for entry in record.get("uploads", []):
        for relative in (entry.get("files") or {}).values():
            path = run_dir / relative
            if path.is_file():
                key = validation_key(entry["run_id"], relative)
                data[key] = facts_for(format_of(relative), path)
    (run_dir / "validation.json").write_text(
        json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return data


def new_record(plan: Plan, found: Found, run_dir: Path) -> dict[str, Any]:
    """The run's record before anything is sent."""
    return {
        "version": RECORD_VERSION,
        "profile": plan.profile,
        "cap": plan.cap,
        "started": _now(),
        "finished": "",
        "run_dir": str(run_dir),
        "base_settings": dict(BASE_SETTINGS),
        "planned": {
            "uploads": plan.upload_count,
            "conversions": plan.conversion_count,
            "pages": plan.pages,
        },
        "uploads": [
            {
                "name": u.name,
                "run_id": u.run_id,
                "source": u.source.file,
                "stem": u.source.stem,
                "origin": u.source.origin,
                "expect": u.source.expect,
                "settings": dict(u.settings),
                "conversions": [{"format": c.format, "label": c.label} for c in u.conversions],
                "job_id": "",
                "document_id": "",
                "state": "planned",
                "error_code": "",
                "message": "",
                "files": {},
            }
            for u in plan.uploads
        ],
        "notes": list(found.notes),
    }


def save_record(run_dir: Path, record: dict[str, Any]) -> None:
    write_json_atomic(run_dir / RUN_RECORD, record)


def load_record(run_dir: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((run_dir / RUN_RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def finish_record(record: dict[str, Any]) -> None:
    record["finished"] = _now()


def _setting_line(name: str, value: Any) -> str:
    if value == "" and name == "language":
        return f'    {name}: "" (automatic)'
    if isinstance(value, bool):
        return f"    {name}: {'true' if value else 'false'}"
    if isinstance(value, str):
        return f'    {name}: "{value}"'
    return f"    {name}: {value}"


def write_readme(run_dir: Path, record: dict[str, Any], found: Found) -> None:
    """A README in the shape of Pneuma's, so the replay tests read its settings."""
    uploads = record.get("uploads", [])
    done = [u for u in uploads if u.get("state") == "done"]
    files = sum(len(u.get("files") or {}) for u in uploads)
    lines = [
        "# Scribe for Documents live regression run",
        "",
        f"Made by QUILL's live regression tool (`python -m quill.tools.scribe_live_run`, "
        f"profile {record.get('profile')}), through QUILL's own Scribe client: upload, "
        "per-format conversion over the document channel, download.",
        "",
        f"- Started {record.get('started')}, finished {record.get('finished') or 'not yet'}.",
        f"- {len(done)} of {len(uploads)} uploads finished; {files} files were collected.",
        "- Every file in the format folders is what Scribe returned; only the names are "
        "QUILL's (our stem, `-offline` for the offline page, `-daisy3` for the DAISY zip).",
        "- The test documents were deleted from the Scribe account afterwards, unless "
        "`run.json` says otherwise.",
        "- This run tests QUILL's handling of what comes back, not the quality of the conversion.",
        "",
        "## Folders",
        "",
    ]
    for format_id in FORMAT_IDS:
        lines.append(f"- `{FOLDERS[format_id]}/`: {format_label(format_id)} (`{format_id}`)")
    lines += [
        "- `sources/`: the documents sent",
        "- `validation.json`: the facts about each file, keyed by run id as in Pneuma's corpus",
        "- `run.json`: the plan, each upload's outcome and the credit used",
        "- `comparison.md`: this run against the one before it",
        "",
        "## Sources and licenses",
        "",
        "- Files starting `q`: made by the QUILL project with code "
        "(`tests/corpus/scribe_live/build_scribe_live_sources.py`); their text is our own, "
        "dedicated to the public domain (CC0 1.0).",
    ]
    if found.pneuma:
        lines.append(
            "- Files starting `01` to `04`: Pneuma Solutions' test corpus sources; see their "
            "README for each one's source and license. Kept on this computer only."
        )
    lines += [
        "",
        "## Settings",
        "",
        "Every upload sent the full set of settings with the document, never the "
        "account's own defaults, and a variant's changes on top. "
        "The defaults on the day were:",
        "",
    ]
    lines += [_setting_line(name, value) for name, value in BASE_SETTINGS.items()]
    lines += [
        "",
        "Variants are named by the settings that differ, after the source's stem: "
        "`-large-print` (Pneuma's: large print and 32 cells, for PDF, Word and BRF), "
        "`-math-on`, `-no-descriptions`, `-lang-es`, `-brf-<table>-<cells>x<lines>` or "
        "`-brf-<table>-<cells>-no-pages`, and the voice and speed for MP3 and DAISY "
        "(`-female-2x`). A setting is only varied for the formats it can change.",
        "",
    ]
    (run_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def pneuma_run_ids(record: dict[str, Any]) -> bool:
    """True when the run replays Pneuma's stems (its s1 to s4 are theirs)."""
    return any(u.get("origin") == PNEUMA and u.get("run_id") == "s1" for u in record["uploads"])


__all__ = [
    "FOLDERS",
    "RUN_RECORD",
    "VALIDATION_FOLDERS",
    "copy_sources",
    "final_name",
    "finish_record",
    "format_of",
    "layout_files",
    "load_record",
    "new_record",
    "place_outputs",
    "pneuma_run_ids",
    "save_record",
    "staging_folder",
    "validation_key",
    "write_readme",
    "write_validation",
]
