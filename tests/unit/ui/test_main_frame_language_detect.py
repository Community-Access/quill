"""The language-detection suggestion names the key Set Language is really on.

It said "Ctrl+Shift+L" as a literal, which is the bullet-list key; the picker is
navigate.set_language (Ctrl+Alt+F6 by default) and can be rebound.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.main_frame_language_detect import LanguageDetectMixin


class _Host(LanguageDetectMixin):
    def __init__(self, keymap: dict[str, str]) -> None:
        self.keymap = keymap
        self.settings = SimpleNamespace(quill_key_binding="Ctrl+Shift+Grave")
        self.statuses: list[str] = []

    def _binding_for(self, command_id: str) -> str | None:
        return (self.keymap.get(command_id) or "").strip() or None

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)


def test_prompt_names_the_bound_set_language_key() -> None:
    host = _Host(dict(DEFAULT_KEYMAP))
    host._act_on_language_detection("prompt", "Python", 0.9)
    assert host.statuses == [
        f"This looks like Python. Press {DEFAULT_KEYMAP['navigate.set_language']}, "
        "then Enter, to set the document language."
    ]
    assert "Ctrl+Shift+L" not in host.statuses[0]


def test_hint_follows_a_rebinding_and_a_leader_chord_reads_as_the_quill_key() -> None:
    host = _Host({"navigate.set_language": "Ctrl+Shift+Grave, Shift+L"})
    host._act_on_language_detection("hint", "Python", 0.9)
    assert host.statuses == [
        "Looks like Python (90%) — press QUILL Key + Shift+L to set the language."
    ]


def test_an_unbound_picker_is_named_rather_than_given_a_dead_key() -> None:
    host = _Host({"navigate.set_language": ""})
    host._act_on_language_detection("prompt", "Python", 0.9)
    assert host.statuses[0].startswith("This looks like Python. Use Set Language, then Enter")
