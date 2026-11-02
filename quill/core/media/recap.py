"""AI recap orchestration for the media player (PRD Sections 9.5 / 18).

The pure, testable core behind "Summarize this chapter" and the Magical
"welcome-back" recap. A model can only summarize *text*, so this layer finds the
text two ways:

* **Path A (text-backed books).** DAISY 3 talking books and EPUB/text companions
  carry the chapter text; it is passed in on the :class:`ChapterContext` and
  used directly -- no transcription, fast and accurate.
* **Path B (pure audio).** With no text, an injected ``transcriber`` turns the
  relevant audio segment into text first, on this computer; if no transcriber
  is available, :class:`RecapUnavailable` is raised so the UI can explain why.
  The audio itself never leaves the machine.

Sending the prompt is not this layer's job (codex.md 10E.8): the app sends
``recap_prompt(kind, text)`` to whichever AI the person chose, then hands the
answer back to :meth:`RecapService.remember`, so the same chapter is not asked
about twice. Everything is injected -- the ``transcriber`` and the ``cache`` --
so the whole layer is unit tested with fakes: no network, no model, no audio.

Guardrails enforced by the caller, not here: never on protected BARD content,
off in Safe Mode, and an AI chosen in Choose Your AI.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass

from quill.core.media.errors import MediaError

#: Transcribes an audio segment ``(path, start_ms, duration_ms)`` to text.
Transcriber = Callable[[str, int, int], str]

#: Cap the text handed to the model so a long chapter stays within a sane token
#: budget; the tail is kept (most relevant to "where you are now").
_MAX_CHARS = 6000


class RecapUnavailable(MediaError):
    """Raised when there is no text to summarize and no way to obtain it."""

    code = "QUILL-MEDIA-RECAP-UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ChapterContext:
    """What the recap needs about the current chapter."""

    book_key: str
    chapter_index: int
    title: str = ""
    #: Path A: the chapter's text when the book has a text layer.
    text: str | None = None
    #: Path B: where to transcribe from when there is no text.
    audio_path: str | None = None
    start_ms: int = 0
    duration_ms: int = 0


def recap_prompt(kind: str, text: str) -> str:
    """Build the AI prompt for a ``chapter`` summary or a ``recap`` (welcome-back)."""
    if kind == "recap":
        instruction = (
            "You are helping a listener resume an audiobook. In ONE or TWO sentences, "
            "warmly remind them what was happening. Do not reveal anything beyond this "
            "point in the book."
        )
    else:
        instruction = (
            "Summarize this audiobook chapter for a listener in ONE or TWO sentences. "
            "Be concise and do not reveal anything beyond this chapter."
        )
    return f"{instruction}\n\n{_trim(text)}"


def _trim(text: str) -> str:
    stripped = text.strip()
    return stripped[-_MAX_CHARS:] if len(stripped) > _MAX_CHARS else stripped


def recap_key(kind: str, ctx: ChapterContext) -> str:
    """The cache key for one ``chapter`` summary or ``recap`` of one place in one book."""
    return f"{kind}:{ctx.book_key}:{ctx.chapter_index}"


class RecapService:
    """Find the text a recap is made from, and remember the answers (per book+chapter)."""

    def __init__(
        self,
        *,
        transcriber: Transcriber | None = None,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        self._transcriber = transcriber
        self._cache: MutableMapping[str, str] = cache if cache is not None else {}

    def cached(self, kind: str, ctx: ChapterContext) -> str:
        """The answer already given for this kind and place, or ""."""
        return self._cache.get(recap_key(kind, ctx), "")

    def remember(self, kind: str, ctx: ChapterContext, summary: str) -> None:
        """Keep *summary* so the same chapter is not asked about again."""
        summary = summary.strip()
        if summary:
            self._cache[recap_key(kind, ctx)] = summary

    def text_for(self, ctx: ChapterContext) -> str:
        """The text to summarize: the book's own, else a local transcript.

        Slow on Path B (it transcribes), so callers run it off the UI thread.
        Raises :class:`RecapUnavailable` when there is none.
        """
        if ctx.text and ctx.text.strip():
            return ctx.text
        if self._transcriber is not None and ctx.audio_path:
            text = self._transcriber(ctx.audio_path, ctx.start_ms, ctx.duration_ms)
            if text.strip():
                return text
            raise RecapUnavailable("No text was available to summarize.")
        raise RecapUnavailable(
            "This book has no text to summarize, and no transcription engine is available."
        )


__all__ = [
    "ChapterContext",
    "RecapService",
    "RecapUnavailable",
    "Transcriber",
    "recap_key",
    "recap_prompt",
]
