"""An AI answer as it should be *heard*: the speech-safe funnel for AI output.

AI models answer in Markdown whether or not anybody asked them to. On screen
that is harmless; spoken, it is noise -- "star star Note star star", "hash hash
Summary", a link read out as its whole address. QUILL has had the cure since
5a.10 in :func:`quill.core.speech_text.prepare_for_speech`, and until
2026-10-16 only the Mastodon reader used it. This module is the one place every
*spoken* AI path goes through instead of each one deciding for itself:

* the free AI's answers when they are delivered to the cursor or the
  clipboard (``quill/ui/hosted_ai_answers.py``), where the answer is spoken
  because focus does not move;
* each reply in an AI conversation (``quill/ui/hosted_ai_chat.py``), in both
  editors;
* Ask Quill's replies -- announced, read aloud by the local voice, or spoken by
  an AI voice (:mod:`quill.core.ai.voice_reply`) -- and its streamed progress
  (``quill/ui/assistant_panel.py``).

**Only what is spoken changes.** The text inserted into a document, put on the
clipboard, shown in the AI Result window or written to a conversation's
transcript is the answer exactly as it arrived, Markdown and all: a person who
asked for a Markdown table gets a Markdown table. What the screen reader is
handed is the words: emphasis markers, heading hashes, list bullets and link
addresses removed, a link's label kept, an image read as "image, <its
description>", and a fenced code block said as "code block" (the code itself is
in the document or the window, where it can be read character by character).

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.speech_text import prepare_for_speech

__all__ = ["speakable_answer", "speakable_line"]


def speakable_answer(text: str) -> str:
    """*text* with its Markdown reduced to words and speech hazards scrubbed.

    Line breaks are kept, because a reader pauses at them and a local voice
    reading a long answer is easier to follow with its paragraphs intact.
    """
    return prepare_for_speech(text or "", markdown=True)


def speakable_line(text: str) -> str:
    """:func:`speakable_answer` collapsed onto one line, for an announcement.

    The Markdown is stripped *before* the whitespace is collapsed: a heading or
    a bullet is only recognisable at the start of a line, so collapsing first
    would leave every "#" and "-" behind to be spoken.
    """
    return " ".join(speakable_answer(text).split())
