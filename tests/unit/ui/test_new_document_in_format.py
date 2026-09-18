"""New Rich Text Document and New Plain Text Document (bad.md P1.13, 3.7).

QuillLite has had both since it shipped: `Ctrl+Shift+N` starts a rich document,
`Ctrl+Alt+N` a plain one. QUILL could only make a new document in whatever
`default_new_document_format` said and then *convert* it -- two commands and a
popup menu to do what the small product does with one key, which is the kind of
gap CLAUDE.md calls backwards.

There was also no seam for it: nothing in QUILL started a document *in* a kind.
`new_document_in_format` is that seam, and `--rich` / `--plain` (P2.16) is
waiting on the same one.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.main_frame_rich_mode import DOCUMENT_FORMATS, RichModeMixin


class _Host(RichModeMixin):
    def __init__(self, arriving_as: str = "markdown") -> None:
        self._arriving_as = arriving_as
        self.created = 0
        self.formats: list[str] = []
        self.status: list[str] = []

    # -- what the seam leans on --
    def new_file(self) -> None:
        self.created += 1

    def current_document_format(self) -> str:
        return self._arriving_as

    def set_document_format(self, target: str, *, announce: bool = True) -> None:
        self.formats.append(target)
        self.announced_by_the_switcher = announce
        self._arriving_as = target

    def _set_status(self, message: str) -> None:
        self.status.append(message)


def test_a_new_rich_document_is_created_and_converted_once() -> None:
    host = _Host(arriving_as="markdown")
    host.new_document_in_format("rtf")
    assert host.created == 1
    assert host.formats == ["rtf"]


def test_a_document_that_already_arrives_in_the_kind_is_not_converted() -> None:
    # Converting markdown to markdown is a no-op that still runs the bridge and
    # says "Already editing as Markdown" -- noise on a command that was meant
    # to be silent about how it got there.
    host = _Host(arriving_as="markdown")
    host.new_document_in_format("markdown")
    assert host.created == 1
    assert host.formats == []


def test_the_kind_is_said_because_nothing_else_says_it() -> None:
    host = _Host(arriving_as="markdown")
    host.new_document_in_format("plain")
    assert host.status[-1] == "New Plain text document"


def test_the_switcher_is_told_to_keep_quiet_about_the_conversion() -> None:
    # "Now editing as plain text" describes a change that did not happen to
    # somebody who just pressed New: the document has never been anything else.
    host = _Host(arriving_as="markdown")
    host.new_document_in_format("plain")
    assert host.announced_by_the_switcher is False


def test_an_unknown_kind_is_refused_rather_than_guessed() -> None:
    host = _Host()
    host.new_document_in_format("perl")
    assert host.created == 0
    assert host.formats == []


def test_every_kind_the_switcher_knows_can_start_a_document() -> None:
    for kind in DOCUMENT_FORMATS:
        host = _Host(arriving_as="markdown" if kind != "markdown" else "plain")
        host.new_document_in_format(kind)
        assert host.created == 1, kind


def test_new_rich_uses_quilllites_chord() -> None:
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["file.new_rich_document"] == lite["cmd_new_rich"]


def test_both_commands_exist_as_handlers_the_registry_can_resolve() -> None:
    assert hasattr(RichModeMixin, "new_rich_document")
    assert hasattr(RichModeMixin, "new_plain_text_document")


def test_the_two_commands_are_registered_in_the_command_table() -> None:
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_commands.py"
    ).read_text(encoding="utf-8")
    assert '"file.new_rich_document"' in source
    assert '"file.new_plain_text_document"' in source
