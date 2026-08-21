"""What an episode row in Quill Radio hands to QUILL Cast.

Three row actions and their labels, in their own module because
``core/radio/row_actions.py`` is at its GATE-11 ceiling and because these are
genuinely a set: they are the ones that do not act on Radio at all. Radio could
play a subscribed show's episode and nothing else, so an episode row was a dead
end -- the same episode offered different things depending on which of the two
apps you happened to be looking at it in.

They are a **handoff**, never a write into Cast's library. Both apps load and
save ``podcasts_library.json`` wholesale, so a Radio write while Cast is open
would be a last-writer-wins clobber waiting to happen. Radio appends an
instruction to a file of its own; Cast carries it out at its next launch, which
is why every confirmation is in the future tense. See
:mod:`quill.core.podcasts.radio_actions` for the file, and for why it is a
second file rather than a field on the existing one.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

__all__ = ["CAST_ADD_TO_QUEUE", "CAST_HANDOFFS", "CAST_PLAY_NEXT", "CAST_SEND_TO_INBOX"]

CAST_PLAY_NEXT = "podcast.cast_play_next"
CAST_ADD_TO_QUEUE = "podcast.cast_add_to_queue"
CAST_SEND_TO_INBOX = "podcast.cast_send_to_inbox"

#: ``(id, label)`` in the order an episode row offers them, soonest first.
#: Tuples rather than ``RowAction`` values so this module does not import the
#: one that imports it; ``row_actions`` builds the objects. The mnemonics are
#: chosen against the whole popup they join, where D is Download, R is Record,
#: C is Copy Link, P is Play, M is Rename and Y is Mark Played.
CAST_HANDOFFS: tuple[tuple[str, str], ...] = (
    (CAST_PLAY_NEXT, "Play &Next in QUILL Cast"),
    (CAST_ADD_TO_QUEUE, "Add to QUILL Cast &Queue"),
    (CAST_SEND_TO_INBOX, "Send to the QUILL Cast &Inbox"),
)
