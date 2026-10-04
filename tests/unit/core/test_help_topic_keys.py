"""F1 help names the key a command is actually on.

``topics.json`` carried its own copy of every command's key, and nothing
compared the copy with ``DEFAULT_KEYMAP``: by 2026-10-04, 87 command topics
named the wrong key or none, and several named a key that now does something
else (Ctrl+Period, taught as Next Misspelling, is Word Prediction; Ctrl+Shift+W,
taught as Word Count, is Select Word). At runtime the help window now renders
a command topic's key from the live keymap (``ContextHelpMixin``), so a rebind
is followed; these tests keep the stored default, which the generated
CONTROL_REFERENCE.md publishes, equal to the real one.
"""

from __future__ import annotations

import re

from quill.core.help.renderer import load_topics
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.keymap_format import format_binding_for_display


def test_every_command_topic_lists_its_default_key() -> None:
    wrong = []
    for topic in load_topics().values():
        if topic.id not in DEFAULT_KEYMAP:
            continue
        binding = DEFAULT_KEYMAP[topic.id]
        want = [format_binding_for_display(binding)] if binding else []
        if topic.keystrokes != want:
            wrong.append(f"{topic.id}: lists {topic.keystrokes}, bound to {want}")
    assert not wrong, "help topics name the wrong key:\n  " + "\n  ".join(wrong)


#: Chords a topic may name that the editor's keymap does not bind: keys inside
#: a dialog or list (access keys, Enter-style keys, native text-control keys),
#: and Quill Radio's Winamp keys, which live in the recordings window's own table.
_LOCAL = re.compile(
    r"^(Alt\+[A-Z]|Alt\+arrows|Ctrl\+[ACVX]|Ctrl\+Insert|Ctrl\+Enter|Ctrl\+Tab|"
    r"Ctrl\+Shift\+Tab|Shift\+(Left|Right|Tab|F10|V)|Ctrl\+(Up|Down|J|T))$"
)
_CHORD = re.compile(
    r"((?:QUILL Key \+ )?(?:(?:Ctrl|Alt|Shift)\+)+(?:F\d{1,2}|[A-Za-z0-9]+|[.,;'/\\\[\]=`-]))"
)


def test_every_chord_a_topic_names_is_bound() -> None:
    bound = {format_binding_for_display(v) for v in DEFAULT_KEYMAP.values() if v}
    unbound = []
    for topic in load_topics().values():
        for text in [topic.body, *topic.keystrokes]:
            for match in _CHORD.finditer(text):
                chord = match.group(1)
                if chord in bound or _LOCAL.match(chord):
                    continue
                # "Ctrl+Alt+1..6", "Ctrl+Alt+Shift+1..9": the first of a family.
                if text[match.end() : match.end() + 2] == "..":
                    continue
                unbound.append(f"{topic.id}: {chord}")
    assert not unbound, "help topics teach keys nothing binds:\n  " + "\n  ".join(unbound)
