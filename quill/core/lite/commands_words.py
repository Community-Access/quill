"""The word rows of QUILL Lite's menu bar: the thesaurus and the dictionary.

Split out of :mod:`quill.core.lite.commands` under GATE-11, and spliced back
into ``COMMANDS`` at the positions the table marks. The shape of every row is
the table's (``menu, label, key, handler, kind``); see that module.

**The thesaurus** is QUILL's (``quill/ui/word_tools_commands.py``, shared), on
QUILL's and Word's key, Shift+F7 (rule 1 and rule 2). The data file ships in
every copy (``standalone/quilllite/portable-inventory.json`` lists it), so the
old note that QUILL Lite "needs an asset download" for this was wrong. Say
Word Summary speaks what the thesaurus knows without opening anything.

**The dictionary** is the AI word tools (``quill/core/ai/word_tools.py``):
twelve questions about the word you are on, on your own key or ChatGPT plan
only. Its own Tools submenu rather than twelve more rows in AI, switched with
the AI area (``command_areas.py``). The Word Explorer, everything at once,
takes Ctrl+F10 (free in both editors, nothing in Word); the other rows are
reached mostly from the Dictionary submenu on the word's context menu and from
the palette, and carry the Ctrl+Shift, Alt+Shift and Ctrl+Alt+Shift punctuation
chords that were free in both editors (rule 9: a key, not a short one; never a
bare Ctrl+Alt, which is AltGr and screen-reader-hostile) -- the same chords in
QUILL.

**Look Up** is the dictionary without AI (``quill/ui/lookup_window.py``,
QUILL's DICT-2 window, shared): the offline thesaurus, and, only after the
listener switches it on in the window, three free online services for
definitions, more words and an encyclopedia summary. Alt+F10, free in both
editors and nothing in Word; the most-pressed row gets the plainest chord.

**Dictionary Status** is QUILL's row (``tools.dictionary_status``): how many
words each dictionary holds, where each file is, and whether the thesaurus
data is present. A once-a-month reading on a long chord (rule 9), the same in
QUILL.
"""

from __future__ import annotations

WORD_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools", "&Look Up Word...", "Alt+F10", "cmd_look_up", ""),
    ("&Tools", "T&hesaurus...", "Shift+F7", "cmd_thesaurus", ""),
    ("&Tools", "Say &Word Summary", "Ctrl+Alt+Shift+[", "cmd_word_summary", ""),
)

DICTIONARY_STATUS_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&Spelling", "Dictionary Stat&us...", "Alt+Shift+;", "cmd_dictionary_status", ""),
)

DICTIONARY_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|Dictionar&y", "&Define in Context", "Ctrl+Alt+Shift+'", "cmd_word_define", ""),
    ("&Tools|Dictionar&y", "Word E&xplorer...", "Ctrl+F10", "cmd_word_explorer", ""),
    ("&Tools|Dictionar&y", "", "", "", "sep"),
    ("&Tools|Dictionar&y", "&Synonyms That Fit", "Ctrl+Shift+;", "cmd_word_synonyms", ""),
    ("&Tools|Dictionar&y", "S&impler Word", "Ctrl+Shift+-", "cmd_word_simpler", ""),
    ("&Tools|Dictionar&y", "More &Formal Word", "Ctrl+Shift+=", "cmd_word_formal", ""),
    ("&Tools|Dictionar&y", "More &Vivid Word", "Ctrl+Shift+'", "cmd_word_vivid", ""),
    ("&Tools|Dictionar&y", "&Opposites", "Alt+Shift+-", "cmd_word_opposites", ""),
    ("&Tools|Dictionar&y", "Is This the &Right Word?", "Ctrl+Alt+Shift+/", "cmd_word_right", ""),
    ("&Tools|Dictionar&y", "", "", "", "sep"),
    ("&Tools|Dictionar&y", "Use It in a S&entence", "Alt+Shift+=", "cmd_word_examples", ""),
    ("&Tools|Dictionar&y", "Where It Comes Fro&m", "Alt+Shift+,", "cmd_word_origin", ""),
    ("&Tools|Dictionar&y", "How to Sa&y It", "Alt+Shift+'", "cmd_word_pronounce", ""),
    ("&Tools|Dictionar&y", "R&hymes", "Ctrl+Alt+Shift+;", "cmd_word_rhymes", ""),
    ("&Tools|Dictionar&y", "", "", "", "sep"),
    ("&Tools|Dictionar&y", "Find the &Word For...", "Ctrl+Alt+Shift+]", "cmd_find_word", ""),
)

__all__ = ["DICTIONARY_ROWS", "DICTIONARY_STATUS_ROWS", "WORD_ROWS"]
