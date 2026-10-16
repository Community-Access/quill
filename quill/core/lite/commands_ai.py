"""Three Tools > AI rows added 2026-10-15: the Chat Key, the Prompt Library and
Web Searches Left.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced into
``COMMANDS`` where the table marks; the row shape is that table's (``menu,
label, key, handler, kind``). The handlers are the shared hosted-AI mixin's
(:mod:`quill.ui.hosted_ai_answers`), so QUILL has the same three commands on
the same three chords (``tools.hosted_ai_chat_key``,
``tools.hosted_ai_prompt_library``, ``tools.hosted_ai_web_searches``; rule 2).

**The chords.** Measured on 2026-10-15, the chords free in both editors that are
neither AltGr (a bare Ctrl+Alt), nor a menu's Alt+letter, nor an Alt+F4
neighbour (rule 4), nor a key Word gives a function both editors have (rule 1),
nor a family show-and-hide key, were Ctrl+3, Ctrl+4 and Ctrl+6 to Ctrl+9 --
Ctrl+1, Ctrl+2 and Ctrl+5 being line spacing in both. The Chat Key is the one
pressed most (rule 3), so it gets the first of the run, Ctrl+6; the Prompt
Library the next, Ctrl+7. Web Searches Left is a once-a-month reading that rule
9 would give a long key, but no long key was free in both editors, so it takes
Ctrl+9 and leaves Ctrl+8 beside the other two for whatever comes next.
"""

from __future__ import annotations

#: Spliced in after Ask About This Document: the two ways to ask.
AI_ASK_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&AI", "Ask AI a &Question...", "Ctrl+6", "cmd_ai_chat_key", ""),
    ("&Tools|&AI", "Prompt &Library...", "Ctrl+7", "cmd_ai_prompt_library", ""),
)

#: Spliced in after Usage: the other number the free service keeps.
AI_SEARCH_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&AI", "&Web Searches Left", "Ctrl+9", "cmd_ai_web_searches", ""),
)
