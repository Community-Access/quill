"""Tools > AI, the whole submenu, in the family's one AI menu shape.

Split out of :mod:`quill.core.lite.commands` under GATE-11 and spliced into
``COMMANDS`` where the table marks; the row shape is that table's (``menu,
label, key, handler, kind``). The handlers are the shared hosted-AI mixins'
(:mod:`quill.ui.hosted_ai_commands` and its siblings), so QUILL has the same
commands on the same chords (rule 2).

**The shape** (2026-11-03, :mod:`quill.core.ai.ai_menu_layout`): the ways to
ask; then what the AI does to the document; then Which AI Am I Using and Choose
Your AI; then **Accounts and Usage**, a submenu holding the six account windows
a person opens a few times a year. Until then this was sixteen rows with one
separator, Ask About an Image and Tidy Dictated Text among the account rows and
Choose Your AI tenth. No chord moved: a row's key works wherever the row sits.

**The chords.** Measured on 2026-10-15, the chords free in both editors that
are neither AltGr (a bare Ctrl+Alt), nor a menu's Alt+letter, nor an Alt+F4
neighbour (rule 4), nor a key Word gives a function both editors have (rule 1),
nor a family show-and-hide key, were Ctrl+3, Ctrl+4 and Ctrl+6 to Ctrl+9 --
Ctrl+1, Ctrl+2 and Ctrl+5 being line spacing in both. The Chat Key is the one
pressed most (rule 3), so it gets Ctrl+6; the Prompt Library Ctrl+7; Web
Searches Left, a once-a-month reading, Ctrl+9. Which AI Am I Using is a quick
question (rule 3) on Ctrl+8, and Choose Your AI took Ctrl+4 (codex.md 10A.9);
rule 6 outranks rule 7 here, because QUILL Lite reaches its AI on plain chords
and QUILL cannot bury them on the leader. Do a Document Task (codex.md 6.2) took
Ctrl+3, the last of the three. Propose Alt Text has no key: no chord is free in
both editors, and Ctrl+3 is the front door (rule 8 reason in the family gate).
Use My ChatGPT Subscription sits on Alt+F5 beside the own-key window's Alt+F2,
both once-a-year windows (rule 9); Ask About an Image took Ctrl+F5 and Tidy
Dictated Text Ctrl+F3, both free in both editors and nothing in Word.
"""

from __future__ import annotations

from quill.core.ai.ai_menu_layout import ACCOUNTS_TITLE

_AI = "&Tools|&AI"
_ACCOUNTS = f"{_AI}|{ACCOUNTS_TITLE}"
_SEP = (_AI, "", "", "", "sep")

#: Project tasks (code.md 6.4): the Developer profile's Coding area, every row
#: where people already look for that kind of command (Jeff, 2026-11-04), not in
#: one submenu. The handlers are the shared mixin's
#: (quill/ui/project_task_commands.py); QUILL has the same ten in the same menus
#: (quill/ui/main_frame_project_rows.py). command_areas.py maps each handler to
#: Coding, so a row exists only in the Developer profile. No chords: none is free
#: in both editors (keymap.py says what was measured); Ctrl+3 is the front door
#: and opens a project task whenever a project is open; each row's letter is a
#: free one in its menu.
PROJECT_FILE_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&File", "Open Pro&ject Folder...", "", "cmd_open_project_folder", ""),
    ("&File", "Close Projec&t", "", "cmd_close_project", ""),
)

#: Edit > Agent Work: undoing and stopping are Edit's verbs. A submenu because
#: Edit has five letters left (J, K, Q, W, Z) and a row with no key needs one.
PROJECT_EDIT_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Edit", "Agent &Work", "", "", "sub"),
    ("&Edit|Agent &Work", "&Undo Last Agent Turn", "", "cmd_undo_agent_turn", ""),
    ("&Edit|Agent &Work", "&Stop Agent", "", "cmd_stop_agent", ""),
)

#: View: the two records a task leaves, opened as documents.
PROJECT_VIEW_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&View", "Agent Task Transcri&pt", "", "cmd_project_transcript", ""),
    ("&View", "Agent Command O&utput", "", "cmd_open_command_output", ""),
)

#: Tools: the project's own settings list.
PROJECT_TOOLS_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools", "Commands Allowed in This Pro&ject...", "", "cmd_project_allowed_commands", ""),
)

#: The AI menu's second group, what the AI does (ai_menu_layout.py): the task,
#: its explanation, and the engine's own tools.
PROJECT_AI_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    (_AI, "Do a &Project Task...", "", "cmd_project_task", ""),
    (_AI, "Explain Last Tu&rn", "", "cmd_explain_agent_turn", ""),
    (_AI, "&Engine Tools for This Project...", "", "cmd_project_engine_tools", ""),
)


#: The whole of Tools > AI, spliced into ``COMMANDS``.
AI_MENU_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    # -- Ask ---------------------------------------------------------------------
    (_AI, "Ask AI a &Question...", "Ctrl+6", "cmd_ai_chat_key", ""),
    (_AI, "As&k About This Document...", "Ctrl+Alt+Z", "cmd_ai_ask_document", ""),
    (_AI, "Ask About an &Image...", "Ctrl+F5", "cmd_ai_image", ""),
    (_AI, "AI &Assistant...", "Ctrl+Alt+G", "cmd_ai_assistant", ""),
    (_AI, "Prompt &Library...", "Ctrl+7", "cmd_ai_prompt_library", ""),
    _SEP,
    # -- What the AI does to the document --------------------------------------
    (_AI, "&Do a Document Task...", "Ctrl+3", "cmd_ai_task", ""),
    (_AI, "Propose Alt &Text...", "", "cmd_ai_alt_text", ""),
    (_AI, "Tidy Dictated Te&xt...", "Ctrl+F3", "cmd_dictation_tidy", ""),
    *PROJECT_AI_ROWS,  # Developer profile only (Coding area)
    _SEP,
    # -- Which AI ----------------------------------------------------------------
    (_AI, "W&hich AI Am I Using", "Ctrl+8", "cmd_ai_which", ""),
    (_AI, "Choose &Your AI...", "Ctrl+4", "cmd_ai_choose", ""),
    _SEP,
    # -- Accounts and Usage: the once-a-year windows, every one on its own key --
    (_AI, ACCOUNTS_TITLE, "", "", "sub"),
    (_ACCOUNTS, "Use My &Own AI Key...", "Alt+F2", "cmd_ai_own_key", ""),
    (_ACCOUNTS, "Use My Chat&GPT Subscription...", "Alt+F5", "cmd_ai_chatgpt", ""),
    # "Connect or Sign Out" rather than "Sign In or Out": the window talks about
    # connecting *this computer*, and both editors speak the one sentence that
    # names this row, composed once in the shared module.
    (_ACCOUNTS, "&Connect or Sign Out...", "Ctrl+Alt+Shift+F10", "cmd_ai_sign_in", ""),
    (_ACCOUNTS, "&Usage...", "Ctrl+Alt+Shift+F9", "cmd_ai_usage", ""),
    (_ACCOUNTS, "&Web Searches Left", "Ctrl+9", "cmd_ai_web_searches", ""),
    # Reachable with the feature switched off, deliberately: the agreement is
    # how somebody turns it on. Its chord is the one held back when this family
    # was laid out.
    (_ACCOUNTS, "&Privacy Agreement...", "Ctrl+Alt+Shift+K", "cmd_ai_privacy", ""),
)
