"""AI-proposed chapter titles: hear the opening, name the chapter.

Turns a Workbench full of ``track07`` chapters into a navigable book: each
chapter's opening minute is sliced with ffmpeg (16 kHz mono, the shape the
local whisper stack likes), transcribed **on this machine** by the installed
offline speech model, and the transcript — text only, never audio — goes to
the caller-provided ``ask`` callable (QUILL's AI gateway; a local model keeps
even the text on-device). Proposals are returned for review; nothing is
applied blind, and a chapter whose slice, transcription, or summary fails
keeps its current title. wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.speech.chapters import Chapter
from quill.core.speech.ffmpeg import INSTALL_HINT, TranscodeError, find_ffmpeg

#: How much of each chapter is transcribed for naming.
OPENING_SECONDS = 60
_MAX_TITLE_WORDS = 8
_MAX_TRANSCRIPT_CHARS = 4000

_PROMPT = (
    "Here is the transcript of the opening minute of one audiobook chapter. "
    "Reply with only a short, descriptive chapter title of at most eight "
    "words. No quotes, no numbering, no trailing period.\n\n"
    "Transcript:\n{transcript}"
)


def build_opening_slice_command(
    ffmpeg: str, book: Path, start_ms: int, duration_ms: int, out_wav: Path
) -> list[str]:
    """The ffmpeg argv slicing one chapter opening to 16 kHz mono WAV (pure)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{max(0, start_ms) / 1000.0:.3f}",
        "-t",
        f"{max(1, duration_ms) / 1000.0:.3f}",
        "-i",
        str(book),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out_wav),
    ]


def slice_chapter_opening(
    book: Path, chapter: Chapter, out_wav: Path, *, seconds: int = OPENING_SECONDS
) -> Path:
    """Write chapter's first *seconds* (or its whole length if shorter)."""
    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is required to slice chapters. {INSTALL_HINT}")
    duration_ms = min(chapter.duration_ms, seconds * 1000)
    args = build_opening_slice_command(ffmpeg, book, chapter.start_ms, duration_ms, out_wav)
    from quill.stability.safe_subprocess import run_subprocess_safely

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = run_subprocess_safely(args, timeout_seconds=300.0)
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0 or not out_wav.is_file():
        detail = (completed.stderr or "").strip()[:300]
        raise TranscodeError(f"ffmpeg could not slice the chapter. {detail}".strip())
    return out_wav


def clean_title(raw: str, fallback: str) -> str:
    """One reviewable title from a model reply (or *fallback* when unusable)."""
    line = raw.strip().splitlines()[0].strip() if raw.strip() else ""
    line = line.strip("\"'`“”‘’").strip()
    for prefix in ("Title:", "Chapter title:", "chapter:"):
        if line.lower().startswith(prefix.lower()):
            line = line[len(prefix) :].strip()
    line = line.rstrip(".").strip()
    words = line.split()
    if not words:
        return fallback
    return " ".join(words[:_MAX_TITLE_WORDS])


def propose_chapter_titles(
    book: Path,
    chapters: list[Chapter],
    ask: Callable[[str], str],
    work_dir: Path,
    *,
    seconds: int = OPENING_SECONDS,
    transcribe: Callable[[Path], str] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[str]:
    """A proposed title per chapter (existing titles kept on any failure).

    *transcribe* maps a WAV to text; the default uses the installed offline
    whisper model (:func:`quill.core.speech.transcribe.transcribe_audio_file`).
    Cancellation between chapters keeps the titles proposed so far and the
    originals for the rest.
    """

    def _default_transcribe(wav: Path) -> str:
        from quill.core.speech.transcribe import transcribe_audio_file

        return transcribe_audio_file(wav).full_text

    transcriber = transcribe or _default_transcribe
    proposals: list[str] = []
    total = len(chapters)
    for i, chapter in enumerate(chapters):
        if is_cancelled is not None and is_cancelled():
            proposals.extend(c.title for c in chapters[i:])
            break
        if on_progress is not None:
            on_progress(i, total)
        try:
            wav = work_dir / f"opening_{i:04d}.wav"
            slice_chapter_opening(book, chapter, wav, seconds=seconds)
            transcript = transcriber(wav).strip()[:_MAX_TRANSCRIPT_CHARS]
            if not transcript:
                proposals.append(chapter.title)
                continue
            reply = ask(_PROMPT.format(transcript=transcript))
            proposals.append(clean_title(reply, chapter.title))
        except Exception:  # noqa: BLE001 - one bad chapter keeps its old title
            proposals.append(chapter.title)
    if on_progress is not None:
        on_progress(total, total)
    return proposals
