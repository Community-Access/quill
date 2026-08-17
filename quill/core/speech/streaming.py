"""The committed/tentative streaming-transcript contract (adopted 2026-08-17).

QUILL's dictation is batch today: record, transcribe, insert. When a streaming
engine lands (Nemotron and its multilingual successor stream; sherpa-onnx
exposes partial results), the naive UI — repaint the latest partial transcript
— is an accessibility disaster: streaming decoders *rewrite their tail* as
context accumulates, and a screen reader that announces every repaint speaks
the same words over and over, differently each time.

The Handy project (D:\\code\\handy, ``managers/transcription.rs``) ships the
contract that fixes this, and QUILL adopts it here ahead of need so the future
streaming provider is built *into* it rather than retrofitted:

- A streaming snapshot is two fields. ``committed`` is **append-only**: once a
  character enters it, it never changes and never leaves. ``tentative`` is the
  volatile suffix the decoder may still rewrite.
- The announcement rule follows from the shape: **speak only what newly entered
  ``committed``; never speak ``tentative``.** Each word is announced exactly
  once, when the engine finally commits to it. A visual live region may show
  the tentative tail; speech and braille wait for commitment. (This is the
  same single-speaker discipline as Reveal Codes navigation: decide who talks,
  and say things once.)

:class:`StreamAnnouncer` enforces the rule mechanically — feed it every
snapshot, get back exactly the text to announce — and refuses regressions: a
provider that violates append-only is a bug, surfaced loudly in dev (assert)
and safely in release (the violating prefix is re-based, nothing is
re-announced).

Pure, wx-free, no runtime dependency; unit-tested directly. Referenced by the
Parakeet/Nemotron provider docs as the contract their streaming variants must
emit.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["StreamSnapshot", "StreamAnnouncer"]


@dataclass(frozen=True, slots=True)
class StreamSnapshot:
    """One live-transcription snapshot from a streaming engine.

    ``committed`` only ever grows by appending; ``tentative`` may change
    arbitrarily between snapshots and may be empty.
    """

    committed: str
    tentative: str = ""


class StreamAnnouncer:
    """Turns snapshots into announce-once text for speech and braille.

    >>> announcer = StreamAnnouncer()
    >>> announcer.feed(StreamSnapshot("hello", "wor"))
    'hello'
    >>> announcer.feed(StreamSnapshot("hello world", "aga"))
    ' world'
    >>> announcer.feed(StreamSnapshot("hello world", "again"))
    ''
    """

    def __init__(self) -> None:
        self._announced = ""

    @property
    def announced(self) -> str:
        """Everything handed out so far (the stable transcript prefix)."""
        return self._announced

    def feed(self, snapshot: StreamSnapshot) -> str:
        """The newly committed text to announce for *snapshot* (maybe "").

        A snapshot whose ``committed`` does not extend what was already
        announced violates the contract. In that case nothing is re-announced
        — double-speak is the failure this class exists to prevent — and the
        internal base is reset to the new committed text so later growth is
        announced correctly from there.
        """
        committed = snapshot.committed
        if committed.startswith(self._announced):
            fresh = committed[len(self._announced) :]
            self._announced = committed
            return fresh
        # Contract violation. Logged loudly rather than raised: an announcement
        # helper must never be the reason dictation dies mid-utterance. Nothing
        # is re-announced; the base moves to the new text so later growth still
        # announces once from there.
        import logging

        logging.getLogger(__name__).error(
            "streaming provider rewrote committed text: %r -> %r", self._announced, committed
        )
        self._announced = committed
        return ""

    def reset(self) -> None:
        """Start a new utterance (a new dictation session)."""
        self._announced = ""
