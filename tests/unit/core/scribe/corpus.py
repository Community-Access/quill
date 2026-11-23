"""Pneuma's Scribe for Documents test corpus, for the replay tests.

The corpus is Pneuma's, and it is kept outside the repository (Jeff,
2026-11-23). The tests that replay it run only when ``QUILL_SCRIBE_CORPUS``
names the extracted corpus folder (``scribe-test-corpus-2026-11``), and skip
with the reason otherwise; mark a test module with ``needs_corpus``.

The corpus is data. It is only ever read, never run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

ENV = "QUILL_SCRIBE_CORPUS"
SKIP_REASON = (
    f"needs Pneuma's Scribe corpus, which is kept out of the repository: "
    f"set {ENV} to the extracted scribe-test-corpus-2026-11 folder"
)

NIST = "01-born-digital-nist-csf2-excerpt"
SCAN = "02-scanned-usda-1919"
GARDEN = "03-word-garden-handbook"
MATH = "04-math-arxiv-1602.08328"
SOURCES = (NIST, SCAN, GARDEN, MATH)

#: format -> (corpus folder, file name pattern).
_PLACES: dict[str, tuple[str, str]] = {
    "html": ("html", "{stem}.html"),
    "offline_html": ("offline-html", "{stem}-offline.html"),
    "docx": ("docx", "{stem}.docx"),
    "pdf": ("pdf", "{stem}.pdf"),
    "epub": ("epub", "{stem}.epub"),
    "mobi": ("mobi", "{stem}.mobi"),
    "brf": ("brf", "{stem}.brf"),
    "mp3": ("mp3", "{stem}.mp3"),
    "daisy": ("daisy", "{stem}-daisy3.zip"),
}
#: validation.json's folder name for each format.
_VALIDATION_FOLDER = {"offline_html": "offline_html"}
_RUN = {NIST: "s1", SCAN: "s2", GARDEN: "s3", MATH: "s4"}


def full_corpus() -> Path | None:
    """The extracted corpus folder named by ``QUILL_SCRIBE_CORPUS``, if it is there."""
    value = os.environ.get(ENV, "").strip()
    folder = Path(value) if value else None
    return folder if folder is not None and (folder / "validation.json").is_file() else None


def require_full() -> Path:
    folder = full_corpus()
    if folder is None:
        pytest.skip(SKIP_REASON)
    return folder


#: Skips a whole test module when the corpus is not at hand.
needs_corpus = pytest.mark.skipif(full_corpus() is None, reason=SKIP_REASON)


def output(format_id: str, stem: str) -> Path | None:
    """The corpus file Scribe made in *format_id* from source *stem*, or ``None``."""
    folder, pattern = _PLACES[format_id]
    path = require_full() / folder / pattern.format(stem=stem)
    return path if path.is_file() else None


def outputs(stem: str, formats: tuple[str, ...] | list[str] | None = None) -> dict[str, Path]:
    """Every output of *stem* that is at hand, by format."""
    found: dict[str, Path] = {}
    for format_id in formats or tuple(_PLACES):
        path = output(format_id, stem)
        if path is not None:
            found[format_id] = path
    return found


def validation(format_id: str, stem: str) -> dict[str, Any]:
    """Pneuma's own check results for one output (``validation.json``)."""
    data = json.loads((require_full() / "validation.json").read_text(encoding="utf-8"))
    run = "v1" if stem.endswith("-large-print") else "v2" if stem.endswith("-math-on") else ""
    base = stem.removesuffix("-large-print").removesuffix("-math-on")
    run = run or _RUN[base]
    folder = _VALIDATION_FOLDER.get(format_id, _PLACES[format_id][0])
    for key, value in data.items():
        prefix = f"{run}/{folder}/"
        if key.startswith(prefix) and Path(key).stem == stem:
            return dict(value)
    raise KeyError(f"{run}/{folder}/{stem}")
