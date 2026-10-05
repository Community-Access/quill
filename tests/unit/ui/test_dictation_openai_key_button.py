"""Dictation Settings can take you to Use My Own AI Key (the owner asked for a
way to add an OpenAI key from where OpenAI dictation is chosen)."""

from __future__ import annotations

from quill.ui import dictation_more_dialog, windows_dictation_dialog
from quill.ui.windows_dictation_commands import WindowsDictationMixin


def test_the_two_windows_pass_the_same_answer_on() -> None:
    assert dictation_more_dialog.EDIT_OPENAI_KEY == windows_dictation_dialog.EDIT_OPENAI_KEY


class _Host(WindowsDictationMixin):
    def __init__(self, with_own_key: bool) -> None:
        self.opened = 0
        self.said: list[str] = []
        if with_own_key:
            self.cmd_ai_own_key = self._own_key  # type: ignore[method-assign]

    def _own_key(self) -> None:
        self.opened += 1

    def _dictation_say(self, text: str) -> None:
        self.said.append(text)


def test_it_opens_the_shared_own_key_window() -> None:
    host = _Host(with_own_key=True)
    host._dictation_add_openai_key()
    assert host.opened == 1
    assert host.said == []


def test_it_says_so_where_there_is_no_own_key_window() -> None:
    host = _Host(with_own_key=False)
    host._dictation_add_openai_key()
    assert host.said == ["Use My Own AI Key is not available here."]
