"""Tools > AI rows added 2026-10-15 -- Ask (the Chat Key), the Prompt Library and
Web Searches Left -- and 2026-10-31, Which AI Am I Using and Choose Your AI.

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

#: Do a Document Task (codex.md 6.2, 2026-11-01): the agent window, on My GitHub
#: Copilot or Codex. Ctrl+3 was the one plain chord left of the three 10A.9
#: found free in both editors and in every APP_KEYMAPS app (Ctrl+4 and Ctrl+8
#: went to Choose Your AI). Rule 6 keeps it off QUILL's leader, because QUILL
#: Lite reaches its AI on plain chords; rule 3 gives a command people will use
#: daily a short key rather than the long one rule 9 keeps for rare ones; and
#: rule 5 does not apply, since nothing moves. QUILL has it on the same chord
#: (tools.hosted_ai_task).
AI_TASK_ROW: tuple[str, str, str, str, str] = (
    "&Tools|&AI",
    "&Do a Document Task...",
    "Ctrl+3",
    "cmd_ai_task",
    "",
)

#: Propose Alt Text (codex.md 6.4, 10B.5): Do a Document Task with the
#: alt-text request filled in, for the document's own images. No key: no chord
#: is free in both editors, and Ctrl+3 is the front door (rule 8 reason in the
#: family gate). T is free in this submenu. QUILL has it (tools.hosted_ai_alt_text).
AI_ALT_TEXT_ROW: tuple[str, str, str, str, str] = (
    "&Tools|&AI",
    "Propose Alt &Text...",
    "",
    "cmd_ai_alt_text",
    "",
)

#: Spliced in after Ask About This Document: the ways to ask, then the task.
AI_ASK_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&AI", "Ask AI a &Question...", "Ctrl+6", "cmd_ai_chat_key", ""),
    ("&Tools|&AI", "Prompt &Library...", "Ctrl+7", "cmd_ai_prompt_library", ""),
    AI_TASK_ROW,
    AI_ALT_TEXT_ROW,
)

#: Choose Your AI (codex.md 10A.9, 2026-10-31). Which AI Am I Using is a quick
#: question, so a short key (rule 3) in the AI row beside Ctrl+6, 7 and 9; and
#: Ctrl+4 was one of the three plain chords free in both editors and in every
#: APP_KEYMAPS app. Rule 7 would keep editor chords for the editor, but rule 6
#: outranks it: QUILL Lite reaches its AI on plain chords, so QUILL cannot bury
#: this on the leader. Ctrl+8 pressed twice also opens the window. QUILL has
#: both on the same chords (tools.hosted_ai_which, tools.hosted_ai_choose).
AI_CHOOSE_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&AI", "W&hich AI Am I Using", "Ctrl+8", "cmd_ai_which", ""),
    ("&Tools|&AI", "Choose &Your AI...", "Ctrl+4", "cmd_ai_choose", ""),
)

#: Spliced in after Usage: the other number the free service keeps, then
#: Choose Your AI's two rows, which sit with the account rows below them.
AI_SEARCH_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&AI", "&Web Searches Left", "Ctrl+9", "cmd_ai_web_searches", ""),
    *AI_CHOOSE_ROWS,
)
