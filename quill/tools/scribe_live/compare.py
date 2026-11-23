"""This run against the previous one: what changed in what comes back.

The comparison exists to catch Scribe changing **the shape** of what it
returns -- the change that once made the offline page arrive as one HTML
file instead of a zip (F1) -- before a person meets it. It flags, as things
that could **break** collecting or using a file:

* a planned file that did not arrive, or a format missing since last time;
* a different kind of file (zip, HTML, PDF, MP3...), such as a zip that
  became a single file;
* a file QUILL's reader opened last time and cannot open now;
* structure QUILL relies on gone: headings in Word and HTML, DAISY's
  navigation file and chapters, BRF form feeds, a changed BRF cell width.

and, **for information** only: sizes beyond the threshold, language tags,
pictures embedded or referenced, page, chapter and table counts, and new
files. It never grades conversion quality (OCR, braille translation, voices,
image descriptions, epubcheck): that is Pneuma's, not ours
(scribe-test-plan.md).

Both sides' facts are computed now with :func:`.facts.facts_for`, so a run
compares with Pneuma's corpus, which has no ``run.json``, the same way it
compares with an earlier run. wx-free, no network.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from quill.tools.scribe_live.facts import facts_for
from quill.tools.scribe_live.layout import (
    FOLDERS,
    RUN_RECORD,
    format_of,
    layout_files,
    load_record,
)

BREAK = "break"
INFO = "info"
SIZE_THRESHOLD = 0.25

#: Facts compared for information only, by format.
_INFO_FACTS: dict[str, tuple[str, ...]] = {
    "html": ("lang", "imgs", "data_uri_imgs", "external_img_refs", "tables", "lists", "mathml"),
    "offline_html": ("lang", "imgs", "data_uri_imgs", "external_img_refs", "tables", "files"),
    "docx": ("language", "tables", "images", "math_omml", "headings"),
    "pdf": ("pages", "tagged", "lang", "encrypted"),
    "epub": ("language", "epub_version", "spine_items", "chapters", "mathml_items"),
    "mobi": ("mobi_version", "compression"),
    "brf": ("form_feeds", "max_lines_per_page", "tabs", "non_ascii_bytes", "crlf"),
    "mp3": ("seconds", "sample_rate", "channels", "id3"),
    "daisy": ("chapters", "mp3s", "smils", "dc_format", "dtbook_images_missing_from_zip"),
}


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    kind: str
    path: str
    sentence: str


@dataclass(slots=True)
class Comparison:
    baseline: str
    findings: list[Finding] = field(default_factory=list)
    compared: int = 0

    @property
    def breaks(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == BREAK]

    @property
    def infos(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == INFO]

    def add(self, severity: str, kind: str, path: str, sentence: str) -> None:
        self.findings.append(Finding(severity, kind, path, sentence))

    def summary(self) -> str:
        breaks, infos = len(self.breaks), len(self.infos)
        verdict = (
            f"{breaks} change{'' if breaks == 1 else 's'} could break collecting or using "
            f"the files, and {infos} {'is' if infos == 1 else 'are'} for information"
        )
        if not self.baseline:
            return f"There was no earlier run or corpus to compare with: {verdict}."
        name = Path(self.baseline).name
        if (Path(self.baseline) / RUN_RECORD).is_file():
            who = f"the run of {name}"
        else:
            who = "Pneuma's corpus" if "scribe-test-corpus" in name else name
        return f"Comparison with {who}: {verdict}, out of {self.compared} files compared."


def _match_key(relative: str) -> str:
    """The file without the extension the offline page may change (F1)."""
    folder, name = relative.split("/", 1)
    if folder == FOLDERS["offline_html"]:
        name = name.rsplit(".", 1)[0]
    return f"{folder}/{name}"


def _planned(record: dict[str, Any] | None) -> dict[str, str]:
    """match key -> upload name, for every conversion the run planned."""
    planned: dict[str, str] = {}
    for entry in (record or {}).get("uploads", []):
        if entry.get("expect", "converts") != "converts":
            continue
        for conversion in entry.get("conversions", []):
            format_id, label = conversion["format"], conversion.get("label", "")
            stem = f"{entry['stem']}-{label}" if label else entry["stem"]
            folder = FOLDERS[format_id]
            name = {
                "offline_html": f"{stem}-offline",
                "daisy": f"{stem}-daisy3.zip",
                "html": f"{stem}.html",
            }.get(format_id, f"{stem}.{_ext(format_id)}")
            planned[f"{folder}/{name}"] = entry["name"]
    return planned


def _ext(format_id: str) -> str:
    return {"docx": "docx", "pdf": "pdf", "epub": "epub", "mobi": "mobi", "brf": "brf"}.get(
        format_id, "mp3"
    )


def compare_runs(
    current: Path, baseline: Path | None, *, size_threshold: float = SIZE_THRESHOLD
) -> Comparison:
    """Every difference in shape between *current* and *baseline*."""
    result = Comparison(str(baseline) if baseline else "")
    record = load_record(current)
    now = {_match_key(k): (k, v) for k, v in layout_files(current).items()}
    planned = _planned(record)
    for key, upload in sorted(planned.items()):
        if key not in now and _attempted(record, upload):
            result.add(BREAK, "not collected", key, f"Planned and not collected: {key}.")
    if baseline is None:
        return result
    then = {_match_key(k): (k, v) for k, v in layout_files(baseline).items()}
    for key in sorted(then.keys() - now.keys()):
        if key in planned:
            continue  # said above, when it was attempted
        if record is None or _stem_in_run(key, record):
            result.add(BREAK, "missing", key, f"In the baseline, missing from this run: {key}.")
    new = sorted(now.keys() - then.keys())
    if new:
        noun = "file is" if len(new) == 1 else "files are"
        result.add(INFO, "new", "", f"{len(new)} {noun} new since the baseline.")
    for key in sorted(now.keys() & then.keys()):
        result.compared += 1
        _compare_file(result, now[key], then[key], size_threshold)
    return result


def _attempted(record: dict[str, Any] | None, upload: str) -> bool:
    for entry in (record or {}).get("uploads", []):
        if entry["name"] == upload:
            return entry.get("state") in ("done", "failed")
    return False


def _stem_in_run(key: str, record: dict[str, Any]) -> bool:
    """True when the baseline file's source was sent in this run at all."""
    name = key.split("/", 1)[1]
    return any(name.startswith(entry["stem"]) for entry in record.get("uploads", []))


def _compare_file(
    result: Comparison, now: tuple[str, Path], then: tuple[str, Path], threshold: float
) -> None:
    relative, path = now
    format_id = format_of(relative)
    a = facts_for(format_id, then[1])
    b = facts_for(format_id, path)
    if a.get("type") != b.get("type"):
        result.add(
            BREAK,
            "file type",
            relative,
            f"Different kind of file: {relative} was {_kind(a)}, now {_kind(b)}"
            + (f", named {Path(then[0]).name} before." if then[0] != relative else "."),
        )
    if a.get("opens") and b.get("opens") is False:
        result.add(
            BREAK,
            "does not open",
            relative,
            f"No longer opens: {relative}. QUILL opened it before and cannot open it now. "
            + _capital(str(b.get("open_error") or "").rstrip("."))
            + ("." if b.get("open_error") else ""),
        )
    _structure(result, format_id, relative, a, b)
    for name in _INFO_FACTS.get(format_id, ()):
        if name in a and name in b and a[name] != b[name]:
            words = _FACT_WORDS.get(name, name.replace("_", " "))
            result.add(
                INFO,
                name,
                relative,
                f"{relative}: {words} was {_said(a[name])}, now {_said(b[name])}.",
            )
    old, new = a.get("bytes", 0), b.get("bytes", 0)
    if old and abs(new - old) / old > threshold:
        change = round(abs(new - old) / old * 100)
        bigger = "larger" if new > old else "smaller"
        result.add(
            INFO,
            "size",
            relative,
            f"{relative}: {_kb(old)} before, {_kb(new)} now, {change} percent {bigger}.",
        )


_FACT_WORDS = {
    "lang": "the language",
    "language": "the language",
    "imgs": "pictures",
    "data_uri_imgs": "embedded pictures",
    "external_img_refs": "pictures referenced by name",
    "files": "files in the zip",
    "math_omml": "Word equations",
    "spine_items": "reading-order items",
    "mathml_items": "files with MathML",
    "max_lines_per_page": "lines per page",
    "non_ascii_bytes": "non-ASCII bytes",
    "form_feeds": "form feeds",
    "dtbook_images_missing_from_zip": "pictures missing from the DAISY zip",
    "dc_format": "the DAISY format label",
    "mp3s": "MP3 files",
    "smils": "SMIL files",
    "seconds": "seconds",
}


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def _said(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if value == "":
        return "empty"
    return str(value)


def _kb(size: int) -> str:
    return f"{size:,} bytes" if size < 1024 else f"{round(size / 1024):,} KB"


def _lost(a: dict[str, Any], b: dict[str, Any], name: str) -> bool:
    return bool(a.get(name)) and not b.get(name)


def _structure(
    result: Comparison, format_id: str, relative: str, a: dict[str, Any], b: dict[str, Any]
) -> None:
    """Structure QUILL relies on to use the file."""
    checks: list[tuple[str, str]] = []
    if format_id in ("html", "offline_html", "docx"):
        checks.append(("headings", "its headings are gone"))
    if format_id == "docx":
        checks.append(("word_document", "it is no longer a Word document"))
    if format_id == "daisy":
        checks += [("ncx", "its dtb.ncx is gone"), ("chapters", "its chapters are gone")]
    if format_id == "brf":
        checks.append(("form_feeds", "its form feeds (page breaks) are gone"))
    if format_id == "epub":
        checks.append(("chapters", "its chapters are gone"))
    for name, words in checks:
        if _lost(a, b, name):
            result.add(BREAK, name, relative, f"{words[0].upper()}{words[1:]}: {relative}.")
    width_a, width_b = a.get("max_cells"), b.get("max_cells")
    if format_id == "brf" and width_a and width_b and width_a != width_b:
        result.add(
            BREAK,
            "cell width",
            relative,
            f"Braille width changed: {relative} was {width_a} cells wide, now {width_b}.",
        )


def _kind(facts: dict[str, Any]) -> str:
    words = {
        "zip": "a zip",
        "html": "a web page",
        "pdf": "a PDF",
        "mp3": "an MP3",
        "mobi": "a MOBI book",
        "text": "plain text",
        "missing": "missing",
    }
    return words.get(str(facts.get("type")), "another kind of file")


def find_baseline(runs_root: Path, current: Path, pneuma_corpus: Path | None) -> Path | None:
    """The newest finished earlier run in *runs_root*, else Pneuma's corpus."""
    if runs_root.is_dir():
        for folder in sorted(runs_root.iterdir(), reverse=True):
            if folder.resolve() == current.resolve() or not (folder / RUN_RECORD).is_file():
                continue
            record = load_record(folder)
            if record and record.get("finished"):
                return folder
    if pneuma_corpus is not None and (pneuma_corpus / "validation.json").is_file():
        return pneuma_corpus
    return None


def write_comparison(run_dir: Path, comparison: Comparison) -> None:
    lines = ["# Comparison", "", comparison.summary(), ""]
    for title, items in (
        ("Could break collecting or using the files", comparison.breaks),
        ("For information", comparison.infos),
    ):
        lines += [f"## {title}", ""]
        lines += [f"- {f.sentence}" for f in items] or ["- None."]
        lines.append("")
    (run_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    data = {
        "baseline": comparison.baseline,
        "compared": comparison.compared,
        "findings": [asdict(f) for f in comparison.findings],
    }
    (run_dir / "comparison.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


def comparison_sentences(comparison: Comparison, limit: int = 15) -> list[str]:
    """For the console: the summary, then each break, then a few notes."""
    lines = [comparison.summary()]
    for heading, items in (
        ("Could break:", comparison.breaks),
        ("For information:", comparison.infos),
    ):
        if not items:
            continue
        lines.append(heading)
        lines += [f.sentence for f in items[:limit]]
        if len(items) > limit:
            lines.append(f"And {len(items) - limit} more, listed in comparison.md.")
    return lines


__all__ = [
    "BREAK",
    "INFO",
    "Comparison",
    "Finding",
    "compare_runs",
    "comparison_sentences",
    "find_baseline",
    "write_comparison",
]
