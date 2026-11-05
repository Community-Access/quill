"""The heavy engines behind captions, transcripts, listening versions and documents.

QUILL already has each of these, and this module only reaches them, so there is
no second implementation of any (wordpress.md 9.6):

* **transcription**: :func:`quill.core.speech.transcribe.transcribe_audio_file`,
  the offline whisper engines the Listening Companion uses. Nothing is uploaded
  to transcribe;
* **speech**: the Read Aloud engine and voice the person chose
  (:mod:`quill.core.speech.document_speech`), rendered to an MP3 with ffmpeg;
* **conversion**: Import / Convert Document (:func:`quill.io.docconvert.convert_document`),
  with on-device OCR only after a yes.

Every engine runs on a background task. :class:`ListenEngines` is a plain bundle
of callables so the commands' tests swap in fakes and never load a model.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from quill.core.wordpress.api import WordPressApi, WordPressApiError


@dataclass(frozen=True)
class Converted:
    """A converted document: its text as Markdown, and whether it looked scanned."""

    text: str
    needs_ocr: bool = False
    pages: int = 0


@dataclass
class ListenEngines:
    #: A file in, a :class:`~quill.core.speech.provider.TranscriptionResult` with timed segments.
    transcribe: Callable[[Path], Any]
    #: A title and HTML in, an MP3 written to the path; returns its length in milliseconds.
    speak: Callable[[str, str, Path], int]
    #: A PDF or Word file in, its text out.
    convert: Callable[[Path], Converted]
    #: The same, by on-device OCR, for a scanned PDF (asked first).
    convert_ocr: Callable[[Path], Converted]


def default_engines() -> ListenEngines:
    return ListenEngines(
        transcribe=_transcribe,
        speak=_speak,
        convert=_convert,
        convert_ocr=_convert_ocr,
    )


def _transcribe(path: Path) -> Any:
    from quill.core.speech.transcribe import transcribe_audio_file

    return transcribe_audio_file(path, output_timestamps=True)


def _speak(title: str, html_text: str, out_mp3: Path) -> int:
    from quill.core.settings import load_settings
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.document_speech import (
        engine_chunk_chars,
        synthesize_document_to_chaptered_file,
    )
    from quill.core.speech.ffmpeg import probe_duration_ms

    spec = synthesis_spec(load_settings())
    with tempfile.TemporaryDirectory(prefix="quill-wp-listen-") as work:
        source = Path(work) / "page.html"
        heading = f"<h1>{_escape(title)}</h1>\n" if title.strip() else ""
        source.write_text(heading + html_text, encoding="utf-8")
        options = ChapterAssembleOptions(
            output_format="mp3", max_chunk_chars=engine_chunk_chars(spec.engine)
        )
        synthesize_document_to_chaptered_file(source, out_mp3, spec, options)
    return probe_duration_ms(out_mp3)


def synthesis_spec(settings: Any) -> Any:
    """The Read Aloud engine and voice from settings, as a synthesis request."""
    from quill.core.speech.document_speech import SynthesisSpec

    engine = str(getattr(settings, "read_aloud_engine", "") or "sapi5").strip().lower()
    voice = {
        "kokoro": "read_aloud_kokoro_voice",
        "phonon": "read_aloud_phonon_voice",
        "piper": "read_aloud_piper_model",
        "dectalk": "read_aloud_dectalk_voice",
        "espeak": "read_aloud_espeak_voice",
    }.get(engine, "read_aloud_voice")
    speed_name = {"kokoro": "read_aloud_kokoro_speed", "phonon": "read_aloud_phonon_speed"}
    speed = float(getattr(settings, speed_name.get(engine, ""), 1.0) or 1.0)
    return SynthesisSpec(
        engine=engine,
        voice=str(getattr(settings, voice, "") or ""),
        rate=int(getattr(settings, "read_aloud_rate", 200) or 200),
        speed=speed,
    )


def _convert(path: Path) -> Converted:
    from quill.io.docconvert import convert_document

    outcome = convert_document(path)
    return Converted(outcome.text, bool(outcome.offer_local_ocr), int(outcome.page_count))


def _convert_ocr(path: Path) -> Converted:
    from quill.io.docconvert_windows import convert_with_on_device_ocr

    outcome = convert_with_on_device_ocr(path)
    return Converted(outcome.text, False, int(outcome.page_count))


def _escape(text: str) -> str:
    import html

    return html.escape(text, quote=False)


def download(api: WordPressApi, url: str, target: Path) -> Path:
    """A library file, fetched to *target* through the site's own connection."""
    request = Request(url, headers={"User-Agent": "QUILL"})
    opener = api._opener  # noqa: SLF001 - the one door to the site, unsigned for a public file
    try:
        with opener(request, timeout=api.timeout) as response:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.read())
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", "") or exc
        raise WordPressApiError(
            f"QUILL could not download {target.name} from {api.site_name} ({reason}). Check "
            "that it is still in the Media Library, then try again.",
            status=int(getattr(exc, "code", 0) or 0),
        ) from exc
    return target
