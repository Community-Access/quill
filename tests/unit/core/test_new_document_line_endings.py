"""A new document ends its lines the way Windows does (bad.md F11, P2.10).

`Document()` defaulted to LF while Notepad, WordPad, Word and QuillLite all
write CRLF, so a file QUILL created and a file anything else created differed
in a way nobody sees until a tool that cares complains. A file that is *opened*
keeps whatever endings it had -- every reader sets them explicitly -- so this
decides only what a brand-new document is born with.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.core.settings import Settings

CRLF = chr(13) + chr(10)
LF = chr(10)


def test_a_new_document_is_born_with_crlf() -> None:
    assert Document().line_ending == CRLF


def test_the_setting_exists_and_agrees() -> None:
    assert Settings().default_line_ending == "crlf"


def test_the_setting_takes_lf_and_refuses_nonsense() -> None:
    assert Settings.from_dict({"default_line_ending": "lf"}).default_line_ending == "lf"
    assert Settings.from_dict({"default_line_ending": "CRLF"}).default_line_ending == "crlf"
    assert Settings.from_dict({"default_line_ending": "old mac"}).default_line_ending == "crlf"


def test_an_opened_file_keeps_its_own_endings(tmp_path: Path) -> None:
    """The half that matters most: this must not rewrite anybody's file."""
    from quill.io.text import read_text_document

    target = tmp_path / "unix.txt"
    target.write_bytes(("one" + LF + "two" + LF).encode("utf-8"))
    assert read_text_document(target).line_ending == LF


def test_the_new_document_command_honours_the_setting() -> None:
    """The editor reads it; the dataclass default is only the fallback."""
    import inspect

    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame.new_file)
    assert 'getattr(self.settings, "default_line_ending", "crlf")' in source


def test_the_setting_is_documented() -> None:
    from quill.core.settings_specs import SETTING_SPECS

    spec = next(s for s in SETTING_SPECS if s.key == "default_line_ending")
    assert spec.choices == (("crlf", "Windows (CR LF)"), ("lf", "Unix (LF)"))
    assert "keeps the endings it already had" in spec.description
