"""AI recap orchestration for the media player (PRD Sections 9.5 / 18).

The pure, testable core behind "Summarize this chapter" and the Magical
"welcome-back" recap. An LLM can only summarize *text*, so this layer resolves the
text two ways and then summarizes it:

* **Path A (text-backed books).** DAISY 3 talking books and EPUB/text companions
  carry the chapter text; it is passed in on the :class:`ChapterContext` and
  summarized directly -- no transcription, fast and accurate.
* **Path B (pure audio).** With no text, an injected ``transcriber`` turns the
  relevant audio segment into text first (Whisper); if no transcriber is
  available, :class:`RecapUnavailable` is raised so the UI can explain why.

Everything the layer talks to is injected -- the ``summarizer`` (QUILL's AI), the
optional ``transcriber``, and the ``cache`` -- so the whole orchestration is unit
tested with fakes and no network, no model, and no audio device. The prompts live
here (``recap_prompt``) so they are consistent and testable; the UI only supplies
a callable that runs the prompt through the configured AI provider.

Guardrails enforced by the caller, not here: never on protected BARD content,
off in Safe Mode, opt-in, and requires a configured AI provider.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass

from quill.core.media.errors import MediaError

#: Runs a prepared prompt through the AI and returns the summary text.
Summarizer = Callable[[str], str]
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


class RecapService:
    """Produce chapter summaries and welcome-back recaps, with caching."""

    def __init__(
        self,
        summarizer: Summarizer,
        *,
        transcriber: Transcriber | None = None,
        cache: MutableMapping[str, str] | None = None,
    ) -> None:
        self._summarizer = summarizer
        self._transcriber = transcriber
        self._cache: MutableMapping[str, str] = cache if cache is not None else {}

    def chapter_summary(self, ctx: ChapterContext) -> str:
        """A one-to-two-sentence summary of the chapter (cached per book+chapter)."""
        return self._summarize(ctx, "chapter")

    def welcome_back(self, ctx: ChapterContext) -> str:
        """A warm "here's where you are" recap for resuming (cached)."""
        return self._summarize(ctx, "recap")

    def _summarize(self, ctx: ChapterContext, kind: str) -> str:
        key = f"{kind}:{ctx.book_key}:{ctx.chapter_index}"
        cached = self._cache.get(key)
        if cached:
            return cached
        text = self._text_for(ctx)
        if not text.strip():
            raise RecapUnavailable("No text was available to summarize.")
        summary = self._summarizer(recap_prompt(kind, text)).strip()
        if summary:
            self._cache[key] = summary
        return summary

    def _text_for(self, ctx: ChapterContext) -> str:
        if ctx.text and ctx.text.strip():
            return ctx.text
        if self._transcriber is not None and ctx.audio_path:
            return self._transcriber(ctx.audio_path, ctx.start_ms, ctx.duration_ms)
        raise RecapUnavailable(
            "This book has no text to summarize, and no transcription engine is available."
        )


__all__ = [
    "ChapterContext",
    "RecapService",
    "RecapUnavailable",
    "Summarizer",
    "Transcriber",
    "recap_prompt",
]
