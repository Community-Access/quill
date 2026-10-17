"""Build the LibriVox held-out set (dict.md section 8, B-1a): public-domain
audiobook recordings catalogued after each model's training cutoff, scored
against the Project Gutenberg text.

**Dev-only, and it downloads only when a person runs it and says yes.** The
tests exercise every step on tiny synthetic text; nothing here runs in CI
(``CI`` set refuses the downloads).

Steps, as dict.md lays them out::

    # 1. The catalogue: LibriVox projects catalogued since a date (librivox.org)
    python scripts/bench_librivox.py catalogue --since 2024-10-21 --out candidates.json
    # 2. A fixed, seeded selection, balanced across readers, Gutenberg texts only
    python scripts/bench_librivox.py select candidates.json --language en --out selection.json
    # 3. The chosen books' audio (archive.org / librivox.org) and text (gutenberg.org)
    python scripts/bench_librivox.py fetch selection.json --into D:/bench/librivox
    # 4. Each chapter: preamble stripped, aligned, cut into 5-20 s utterances,
    #    bad ones rejected, kept ones written as dictbench reads them
    python scripts/bench_librivox.py build --chapter ch01.mp3 --book pg1234.txt \\
        --reader "Reader Name" --project 9999 --ebook 1234 --out D:/bench/librivox-en

**Held out.** A recording counts as held out for a model only if it was
catalogued after that model's upper-bound date (``model_cutoffs`` in
``bench_datasets.json``). A model whose date is unknown has nothing held out
until one is filled in. ``speakers.tsv`` gets one column per model family
(``heldout_<family>``) so dictbench scores each model only on what is held
out for it, and on the shared subset held out for all of them
(``--group-by heldout``).

**Alignment.** No forced aligner is verified on Windows with Python 3.14
(dict.md lists the options), so this uses the fallback: an engine that is
*not* under evaluation transcribes each voice-detected stretch, and its words
are aligned to the book with ``difflib``. The reference written for a kept
utterance is always the *book's* words, with the author's punctuation. That
choice biases the set towards stretches the aligner heard well, so the
aligner's model is recorded (``aligner.txt``) and dictbench refuses to score
it on this set.

**Text.** The Gutenberg header, footer and licence, and every line that
mentions Project Gutenberg, are stripped (the licence requires it for
redistribution without the trademark); hyphenated line breaks are joined and
lines unwrapped.

**Hosts it contacts** (outside ``quill/``, so not in the egress audit):

* librivox.org -- the catalogue API, and some project zips
* archive.org -- the project zips LibriVox links to
* www.gutenberg.org -- the book texts

**The catalogue date.** The API has no catalogue-date field (checked
2026-10-17: ``date_catalog`` is absent). Every project's archive.org
identifier ends ``_YYMM_librivox``, the month it was catalogued, so that month's
first day is used (:func:`catalogue_date`): conservative, because a recording
from the cutoff's own month never counts as held out. ``date_catalog`` is still
read first, and the ``--since`` asked for is the last resort. Sections carry
their reader (``readers``), so the balance is per reader, not per project.

**Per chapter, not per book.** ``fetch`` downloads each chosen section's own
MP3 (its ``listen_url`` on archive.org), not the whole book's zip, and
``build-selection`` builds every chosen section in one run, trimmed to its
first ``--first-minutes``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import os
import random
import re
import sys
import urllib.parse
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from bench_scoring import basic_normalize, gutenberg_prepass  # noqa: E402

API = "https://librivox.org/api/feed/audiobooks/"
ALLOWED_HOSTS = frozenset({"librivox.org", "archive.org", "www.archive.org", "www.gutenberg.org"})
MIN_SECONDS = 5.0
MAX_SECONDS = 20.0
#: Start at 0.9 word match (dict.md B-1a step 5).
MATCH_THRESHOLD = 0.9

#: LibriVox's spoken boilerplate, found by matching words, never by timing.
PREAMBLE = (
    "this is a librivox recording",
    "all librivox recordings are in the public domain",
    "for more information or to volunteer please visit librivox org",
    "recording by",
    "read by",
)
CLOSING = (
    "end of chapter",
    "end of section",
    "end of book",
    "this recording is in the public domain",
)
_SPANISH_BOILERPLATE = (
    "esta es una grabacion de librivox",
    "todas las grabaciones de librivox estan en el dominio publico",
    "fin del capitulo",
)


# --------------------------------------------------------------------------- #
# Held out, per model
# --------------------------------------------------------------------------- #


def cutoffs(table: dict[str, Any]) -> dict[str, _dt.date | None]:
    """``{family: upper-bound date or None}`` from bench_datasets.json."""
    found: dict[str, _dt.date | None] = {}
    for family, entry in table.get("model_cutoffs", {}).items():
        if family.startswith("_"):
            continue
        date = entry.get("date")
        found[family] = _dt.date.fromisoformat(date) if date else None
    return found


def held_out_for(catalogued: _dt.date, limits: dict[str, _dt.date | None]) -> dict[str, bool]:
    """Per family: catalogued strictly after its date. Unknown date: not held out."""
    return {family: bool(date and catalogued > date) for family, date in limits.items()}


# --------------------------------------------------------------------------- #
# The catalogue and the selection
# --------------------------------------------------------------------------- #


def api_url(since: _dt.date, *, offset: int = 0, limit: int = 50) -> str:
    stamp = int(_dt.datetime.combine(since, _dt.time(), tzinfo=_dt.UTC).timestamp())
    query = urllib.parse.urlencode({
        "format": "json",
        "extended": 1,
        "since": stamp,
        "offset": offset,
        "limit": limit,
    })
    return f"{API}?{query}"


def gutenberg_number(url: str) -> int | None:
    """The ebook number in a Project Gutenberg link, or ``None``."""
    if "gutenberg.org" not in (url or ""):
        return None
    match = re.search(r"(?:ebooks|etext|files|epub)/(\d+)", url)
    return int(match.group(1)) if match else None


@dataclass
class Section:
    project: int
    section: int
    title: str
    language: str
    reader: str
    seconds: float
    ebook: int
    catalogued: str
    listen_url: str = ""
    zip_url: str = ""
    held_out: dict[str, bool] = field(default_factory=dict)


_ARCHIVE_MONTH = re.compile(r"_(\d{2})(\d{2})_librivox")


def catalogue_date(project: dict[str, Any], since: _dt.date) -> _dt.date:
    """When *project* was catalogued: ``date_catalog`` if the API gives it,
    else the first day of the ``_YYMM_librivox`` month in its archive.org
    identifier, else *since* (all the API's ``since=`` filter guarantees)."""
    raw_date = str(project.get("date_catalog") or "")[:10]
    try:
        return _dt.date.fromisoformat(raw_date)
    except ValueError:
        pass
    for key in ("url_iarchive", "url_zip_file"):
        match = _ARCHIVE_MONTH.search(str(project.get(key) or ""))
        if match and 1 <= int(match.group(2)) <= 12:
            return _dt.date(2000 + int(match.group(1)), int(match.group(2)), 1)
    return since


def sections_of(project: dict[str, Any], since: _dt.date) -> list[Section]:
    """A catalogue project's sections, when its text is from Gutenberg."""
    ebook = gutenberg_number(str(project.get("url_text_source") or ""))
    if ebook is None:
        return []
    catalogued = catalogue_date(project, since)
    project_readers = project.get("readers") or []
    found: list[Section] = []
    for section in project.get("sections") or []:
        readers = section.get("readers") or project_readers
        reader = str((readers[0] or {}).get("display_name", "")) if readers else ""
        found.append(
            Section(
                project=int(project.get("id") or 0),
                section=int(section.get("section_number") or 0),
                title=str(section.get("title") or ""),
                language=str(project.get("language") or ""),
                reader=reader or "unknown",
                seconds=float(section.get("playtime") or 0),
                ebook=ebook,
                catalogued=catalogued.isoformat(),
                listen_url=str(section.get("listen_url") or ""),
                zip_url=str(project.get("url_zip_file") or ""),
            )
        )
    return found


_LANGUAGES = {"en": "english", "es": "spanish"}


def select(
    projects: Iterable[dict[str, Any]],
    *,
    language: str,
    since: _dt.date,
    limits: dict[str, _dt.date | None],
    seed: int = 20261015,
    minutes_per_reader: float = 5.0,
    total_minutes: float = 40.0,
    max_section_minutes: float | None = None,
) -> list[Section]:
    """A fixed, seeded choice of sections, balanced across readers.

    No reader gives more than *minutes_per_reader*; the total stops at about
    *total_minutes* of audio (before rejection, which drops some). With
    *max_section_minutes*, a longer section counts as only that much, because
    ``build-selection --first-minutes`` uses no more of it -- so one long
    chapter cannot take a whole reader's share, or the whole set's.
    """
    wanted = _LANGUAGES.get(language, language).lower()
    pool = [
        section
        for project in projects
        if str(project.get("language") or "").lower() == wanted
        for section in sections_of(project, since)
        if section.seconds > 0
    ]
    pool.sort(key=lambda s: (s.project, s.section))
    random.Random(seed).shuffle(pool)
    per_reader: Counter[str] = Counter()
    chosen: list[Section] = []
    total = 0.0
    for section in pool:
        minutes = section.seconds / 60
        if max_section_minutes:
            minutes = min(minutes, max_section_minutes)
        if per_reader[section.reader] + minutes > minutes_per_reader and per_reader[section.reader]:
            continue
        if total + minutes > total_minutes and chosen:
            continue
        section.held_out = held_out_for(_dt.date.fromisoformat(section.catalogued), limits)
        chosen.append(section)
        per_reader[section.reader] += minutes
        total += minutes
    return sorted(chosen, key=lambda s: (s.project, s.section))


# --------------------------------------------------------------------------- #
# The text
# --------------------------------------------------------------------------- #

_START = re.compile(r"^\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*$", re.I | re.M)
_END = re.compile(r"^\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*$", re.I | re.M)


def clean_gutenberg(text: str) -> str:
    """The book alone: no header, footer, licence, or mention of Project Gutenberg."""
    text = text.replace("\r\n", "\n")
    start = _START.search(text)
    if start:
        text = text[start.end() :]
    end = _END.search(text)
    if end:
        text = text[: end.start()]
    kept = [
        line
        for line in text.split("\n")
        if "gutenberg" not in line.lower() and "pglaf" not in line.lower()
    ]
    return gutenberg_prepass("\n".join(kept))


# --------------------------------------------------------------------------- #
# The audio's boilerplate
# --------------------------------------------------------------------------- #


def _similar(words: Sequence[str], phrase: str) -> bool:
    target = phrase.split()
    if len(words) < len(target):
        return False
    for start in range(0, len(words) - len(target) + 1):
        window = words[start : start + len(target)]
        if difflib.SequenceMatcher(a=list(window), b=target).ratio() >= 0.8:
            return True
    return False


def is_boilerplate(text: str) -> bool:
    """A stretch that is LibriVox's own preamble or closing, by its words."""
    words = basic_normalize(text, accents=False)
    phrases = (*PREAMBLE, *CLOSING, *_SPANISH_BOILERPLATE)
    return any(_similar(words, phrase) for phrase in phrases)


# --------------------------------------------------------------------------- #
# Aligning and cutting
# --------------------------------------------------------------------------- #


@dataclass
class Stretch:
    """One voice-detected stretch of a chapter and what the aligner heard."""

    start: float
    end: float
    heard: str


@dataclass
class Utterance:
    start: float
    end: float
    reference: str  # the book's words, with the author's punctuation
    heard: str
    match: float
    kept: bool
    reason: str = ""


def _book_tokens(book: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Normalized book words, and each one's span in *book*."""
    words: list[str] = []
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"[\w][\w'’-]*", book):
        normal = basic_normalize(match.group(), accents=False)
        if normal:
            words.append(normal[0])
            spans.append((match.start(), match.end()))
    return words, spans


def locate(book_words: Sequence[str], heard_words: Sequence[str], n: int = 4) -> tuple[int, int]:
    """The stretch of the book a chapter's words come from, found by shared
    n-grams, so alignment does not run against a whole novel."""
    if not heard_words:
        return 0, 0
    index: dict[tuple[str, ...], list[int]] = {}
    for i in range(len(book_words) - n + 1):
        index.setdefault(tuple(book_words[i : i + n]), []).append(i)
    hits: list[int] = []
    for j in range(len(heard_words) - n + 1):
        for i in index.get(tuple(heard_words[j : j + n]), [])[:3]:
            hits.append(i - j)
    if not hits:
        return 0, len(book_words)
    hits.sort()
    centre = hits[len(hits) // 2]
    margin = len(heard_words) // 2 + 50
    return max(0, centre - margin), min(len(book_words), centre + len(heard_words) + margin)


def utterances(
    stretches: Sequence[Stretch],
    book: str,
    *,
    threshold: float = MATCH_THRESHOLD,
    min_seconds: float = MIN_SECONDS,
    max_seconds: float = MAX_SECONDS,
) -> list[Utterance]:
    """Cut a chapter into 5-20 s utterances whose reference is the book's text.

    Boilerplate stretches are dropped first. The aligner's words are matched
    to the book's; consecutive stretches are joined until an utterance is at
    least *min_seconds* and ends at a sentence boundary in the book, never past
    *max_seconds*. An utterance whose book words the aligner matched less than
    *threshold* of is kept=False, with the reason.
    """
    body = [s for s in stretches if not is_boilerplate(s.heard)]
    book_words, spans = _book_tokens(book)
    heard_words: list[str] = []
    owner: list[int] = []  # which stretch each heard word is from
    for index, stretch in enumerate(body):
        words = basic_normalize(stretch.heard, accents=False)
        heard_words.extend(words)
        owner.extend([index] * len(words))
    low, high = locate(book_words, heard_words)
    matcher = difflib.SequenceMatcher(a=heard_words, b=book_words[low:high], autojunk=False)
    # book position matched by each heard word, where one was
    book_at: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            book_at[block.a + k] = low + block.b + k
    # each stretch's matched book range
    ranges: list[tuple[int, int, int] | None] = []  # (first, last, matched)
    for index in range(len(body)):
        positions = [book_at[w] for w, o in enumerate(owner) if o == index and w in book_at]
        ranges.append((min(positions), max(positions), len(positions)) if positions else None)

    found: list[Utterance] = []
    group: list[int] = []

    def close(group: list[int]) -> None:
        start, end = body[group[0]].start, body[group[-1]].end
        heard = " ".join(body[i].heard for i in group)
        spans_here = [ranges[i] for i in group if ranges[i] is not None]
        if not spans_here:
            found.append(Utterance(start, end, "", heard, 0.0, False, "nothing matched the book"))
            return
        first = min(r[0] for r in spans_here)  # type: ignore[index]
        last = max(r[1] for r in spans_here)  # type: ignore[index]
        matched = sum(r[2] for r in spans_here)  # type: ignore[index]
        reference = book[spans[first][0] : _sentence_end(book, spans[last][1])].strip()
        # Against the longer of the two, so words the book does not have (a
        # reader's aside, a mishearing) count against it as much as skipped ones.
        expected = max(last - first + 1, len(basic_normalize(heard, accents=False)))
        match = round(matched / expected, 3) if expected else 0.0
        if end - start > max_seconds:
            found.append(Utterance(start, end, reference, heard, match, False, "too long"))
        elif match < threshold:
            found.append(
                Utterance(start, end, reference, heard, match, False, f"word match {match}")
            )
        else:
            found.append(Utterance(start, end, reference, heard, match, True))

    for index in range(len(body)):
        if group and body[index].end - body[group[0]].start > max_seconds:
            close(group)
            group = []
        group.append(index)
        length = body[index].end - body[group[0]].start
        span = ranges[index]
        at_sentence_end = span is not None and _ends_sentence(book, spans[span[1]][1])
        if length >= min_seconds and at_sentence_end:
            close(group)
            group = []
    if group and body[group[-1]].end - body[group[0]].start >= min_seconds:
        close(group)
    return found


def _ends_sentence(book: str, at: int) -> bool:
    return bool(re.match(r"[\"”’)\]]*[.?!]", book[at : at + 4]))


def _sentence_end(book: str, at: int) -> int:
    """Include the marks (and a closing quote) right after the last word."""
    match = re.match(r"[.,;:?!\"”’)\]]*", book[at:])
    return at + (match.end() if match else 0)


def keep_report(rows: Iterable[tuple[str, str, Utterance]]) -> dict[str, Any]:
    """How much was kept, per book and per reader (dict.md B-1a step 5)."""
    report: dict[str, dict[str, dict[str, float]]] = {"by_book": {}, "by_reader": {}}
    for book, reader, utterance in rows:
        for table, key in (("by_book", book), ("by_reader", reader)):
            entry = report[table].setdefault(key, {"kept": 0, "dropped": 0, "seconds_kept": 0.0})
            if utterance.kept:
                entry["kept"] += 1
                entry["seconds_kept"] = round(
                    entry["seconds_kept"] + utterance.end - utterance.start, 2
                )
            else:
                entry["dropped"] += 1
    return report


# --------------------------------------------------------------------------- #
# Driving it (a person, with the models and the downloads)
# --------------------------------------------------------------------------- #


def _refuse_ci() -> None:
    if os.environ.get("CI"):
        raise SystemExit("LibriVox audio and text are never downloaded in CI.")


def _get(url: str) -> bytes:  # pragma: no cover - network, by a person only
    import urllib.request

    host = urllib.parse.urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise SystemExit(f"{url} is not on an allowed host.")
    request = urllib.request.Request(url, headers={"User-Agent": "QUILL-bench/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _confirm(question: str, yes: bool) -> None:  # pragma: no cover - a person answers
    if not yes and input(f"{question} [y/N] ").strip().lower() not in {"y", "yes"}:
        raise SystemExit("Nothing was downloaded.")


def stretches_from_audio(samples: Any, aligner: Any) -> list[Stretch]:  # pragma: no cover
    """Voice-detected stretches of a chapter, each transcribed by *aligner*."""
    import numpy as np

    from quill.core.windows_dictation import local_recognizer as lr

    vad = lr._vad(0.5)
    found: list[Stretch] = []
    block = 512
    for begin in range(0, len(samples), block):
        vad.accept_waveform(np.asarray(samples[begin : begin + block], dtype=np.float32))
        while not vad.empty():
            # Copy out before pop(): the front segment's memory is freed by
            # pop(), and reading it afterwards crashed the first real run
            # (2026-10-17, a segmentation fault on the first chapter).
            segment = vad.front
            audio = np.array(segment.samples, dtype=np.float32)
            start = segment.start / 16_000
            vad.pop()
            stream = aligner.create_stream()
            stream.accept_waveform(16_000, audio)
            aligner.decode_stream(stream)
            found.append(Stretch(start, start + len(audio) / 16_000, stream.result.text))
    return found


def load_selection(path: Path, set_name: str | None = None) -> list[dict[str, Any]]:
    """A ``select`` output (a list), or one set of a ``bench_librivox_sets.json``
    file (the committed B-1a selections), by *set_name*."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    sets = data.get("sets", {})
    if set_name not in sets:
        raise SystemExit(f"Name one of these with --set: {', '.join(sorted(sets))}.")
    return list(sets[set_name])


def section_audio_name(section: dict[str, Any]) -> str:
    """The file ``fetch`` saves a chosen section's MP3 as."""
    return f"lv{section['project']}-{int(section['section']):03d}.mp3"


_ALIGNERS: dict[tuple[str, str], Any] = {}


def build(args: argparse.Namespace) -> int:  # pragma: no cover - needs models and audio
    import dictbench
    import soundfile as sf
    from fetch_bench_audio import resample

    samples, rate = sf.read(str(args.chapter), dtype="float32", always_2d=True)
    first = getattr(args, "first_minutes", None)
    if first:
        samples = samples[: int(first * 60 * rate)]
    mono = resample(samples.mean(axis=1), rate, 16_000)
    key = (args.aligner, args.language)
    if key not in _ALIGNERS:  # loaded once for a whole selection
        _ALIGNERS[key] = dictbench.load_engine(
            args.aligner, args.language, getattr(args, "threads", 2)
        )
    aligner = _ALIGNERS[key]
    found = utterances(
        stretches_from_audio(mono, aligner),
        clean_gutenberg(Path(args.book).read_text(encoding="utf-8", errors="replace")),
    )
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    stem = f"lv{args.project}-{Path(args.chapter).stem}"
    transcripts = out / "transcripts.txt"
    speakers = out / "speakers.tsv"
    limits = cutoffs(json.loads((_HERE / "bench_datasets.json").read_text(encoding="utf-8")))
    held = held_out_for(_dt.date.fromisoformat(args.catalogued), limits)
    if not speakers.is_file():
        columns = ["file", "speaker", "accent", "gender", "language", "group"]
        columns += [f"heldout_{family}" for family in sorted(held)]
        speakers.write_text("\t".join(columns) + "\n", encoding="utf-8")
    with (
        transcripts.open("a", encoding="utf-8") as t,
        speakers.open("a", encoding="utf-8") as s,
        (out / "ATTRIBUTION.txt").open("a", encoding="utf-8") as a,
    ):
        for number, utterance in enumerate(found, 1):
            if not utterance.kept:
                continue
            name = f"{stem}-{number:03d}.wav"
            cut = mono[int(utterance.start * 16_000) : int(utterance.end * 16_000)]
            sf.write(str(out / name), cut, 16_000, subtype="PCM_16")
            reference = " ".join(utterance.reference.split())
            t.write(f"{name}\t{reference}\n")
            flags = ["yes" if held[family] else "no" for family in sorted(held)]
            s.write("\t".join([name, args.reader, "", "", args.language, "", *flags]) + "\n")
            a.write(
                f"{name}: read by {args.reader} for LibriVox project {args.project}; "
                f"book text from ebook {args.ebook}\n"
            )
    (out / "aligner.txt").write_text(args.aligner + "\n", encoding="utf-8")
    report = keep_report((str(args.ebook), args.reader, u) for u in found)
    (out / f"{stem}-kept.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - a person runs it
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    cat = commands.add_parser("catalogue", help="LibriVox projects catalogued since a date")
    cat.add_argument("--since", required=True, type=_dt.date.fromisoformat)
    cat.add_argument("--out", type=Path, required=True)
    cat.add_argument("--pages", type=int, default=10)
    cat.add_argument("--yes", action="store_true")
    sel = commands.add_parser("select", help="a seeded, reader-balanced selection")
    sel.add_argument("candidates", type=Path)
    sel.add_argument("--language", default="en")
    sel.add_argument("--since", type=_dt.date.fromisoformat, default=_dt.date(2024, 10, 21))
    sel.add_argument("--minutes-per-reader", type=float, default=5.0)
    sel.add_argument("--minutes", type=float, default=40.0)
    sel.add_argument("--seed", type=int, default=20261015)
    sel.add_argument("--max-section-minutes", type=float, help="count a section as at most this")
    sel.add_argument("--out", type=Path, required=True)
    fet = commands.add_parser("fetch", help="the selection's zips and Gutenberg texts")
    fet.add_argument("selection", type=Path)
    fet.add_argument("--set", help="one set of a bench_librivox_sets.json file")
    fet.add_argument("--into", type=Path, required=True)
    fet.add_argument("--yes", action="store_true")
    bld = commands.add_parser("build", help="one chapter into kept utterances")
    bld.add_argument("--chapter", type=Path, required=True)
    bld.add_argument("--book", type=Path, required=True)
    bld.add_argument("--reader", required=True)
    bld.add_argument("--project", required=True)
    bld.add_argument("--ebook", required=True)
    bld.add_argument("--catalogued", required=True, help="YYYY-MM-DD")
    bld.add_argument("--language", default="en")
    bld.add_argument("--aligner", default="whisper", help="an engine NOT being evaluated")
    bld.add_argument("--first-minutes", type=float, help="use only the chapter's start")
    bld.add_argument("--threads", type=int, default=2)
    bld.add_argument("--out", type=Path, required=True)
    many = commands.add_parser("build-selection", help="every fetched section of a selection")
    many.add_argument("selection", type=Path)
    many.add_argument("--set", help="one set of a bench_librivox_sets.json file")
    many.add_argument("--audio", type=Path, required=True, help="the folder fetch saved into")
    many.add_argument("--language", default="en")
    many.add_argument("--aligner", default="whisper", help="an engine NOT being evaluated")
    many.add_argument("--first-minutes", type=float, default=6.0)
    many.add_argument("--threads", type=int, default=2)
    many.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "catalogue":
        _refuse_ci()
        _confirm(f"Read the LibriVox catalogue since {args.since} from librivox.org?", args.yes)
        projects: list[Any] = []
        for page in range(args.pages):
            data = json.loads(_get(api_url(args.since, offset=page * 50)))
            batch = data.get("books") or []
            projects.extend(batch)
            if len(batch) < 50:
                break
        args.out.write_text(json.dumps(projects, indent=2), encoding="utf-8")
        print(f"{len(projects)} projects written to {args.out}.")
        return 0
    if args.command == "select":
        table = json.loads((_HERE / "bench_datasets.json").read_text(encoding="utf-8"))
        chosen = select(
            json.loads(args.candidates.read_text(encoding="utf-8")),
            language=args.language,
            since=args.since,
            limits=cutoffs(table),
            seed=args.seed,
            minutes_per_reader=args.minutes_per_reader,
            total_minutes=args.minutes,
            max_section_minutes=args.max_section_minutes,
        )
        args.out.write_text(json.dumps([asdict(c) for c in chosen], indent=2), encoding="utf-8")
        print(f"{len(chosen)} sections from {len({c.reader for c in chosen})} readers.")
        return 0
    if args.command == "fetch":
        _refuse_ci()
        chosen = load_selection(args.selection, args.set)
        books = sorted({c["ebook"] for c in chosen})
        singles = [c for c in chosen if c.get("listen_url")]
        zips = sorted({c["zip_url"] for c in chosen if c["zip_url"] and not c.get("listen_url")})
        _confirm(
            f"Download {len(books)} book texts, {len(singles)} chapter MP3s "
            f"and {len(zips)} audio zips?",
            args.yes,
        )
        args.into.mkdir(parents=True, exist_ok=True)
        for ebook in books:
            target = args.into / f"pg{ebook}.txt"
            if not target.is_file():
                url = f"https://www.gutenberg.org/cache/epub/{ebook}/pg{ebook}.txt"
                target.write_bytes(_get(url))
        for section in singles:
            target = args.into / section_audio_name(section)
            if not target.is_file():
                try:
                    target.write_bytes(_get(section["listen_url"]))
                except OSError as error:  # archive.org has the odd bad file: skip it
                    print(f"Skipped {target.name}: {error}")
        for url in zips:
            (args.into / Path(urllib.parse.urlparse(url).path).name).write_bytes(_get(url))
        print(f"Saved to {args.into}. Then: build-selection, or build per chapter.")
        return 0
    if args.command == "build-selection":
        return build_selection(args)
    return build(args)


def build_selection(args: argparse.Namespace) -> int:  # pragma: no cover - needs models and audio
    """``build`` for every section of a selection whose MP3 ``fetch`` saved."""
    chosen = load_selection(args.selection, args.set)
    built = 0
    for section in chosen:
        chapter = args.audio / section_audio_name(section)
        book = args.audio / f"pg{section['ebook']}.txt"
        if not (chapter.is_file() and book.is_file()):
            print(f"Skipped {chapter.name}: not fetched.")
            continue
        print(f"Building {chapter.name} ({section['reader']})...", flush=True)
        one = argparse.Namespace(
            chapter=chapter,
            book=book,
            reader=section["reader"],
            project=section["project"],
            ebook=section["ebook"],
            catalogued=section["catalogued"],
            language=args.language,
            aligner=args.aligner,
            first_minutes=args.first_minutes,
            threads=args.threads,
            out=args.out,
        )
        try:
            build(one)
            built += 1
        except Exception as error:  # noqa: BLE001 - one bad chapter never stops the set
            print(f"  {chapter.name} failed: {error}")
    print(f"{built} of {len(chosen)} sections built into {args.out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
