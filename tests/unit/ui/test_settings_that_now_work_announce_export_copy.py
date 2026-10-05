"""Four settings that were drawn in Settings and read by nothing (questions.md 38).

Each test flips the setting and proves the feature behaves differently:

* announcement_echo_history -- the Spoken Echo records, or keeps nothing.
* announcement_severity_interrupt -- which severities cut across the reader.
* default_export_preset -- what Export > Other Pandoc Format opens on.
* markdown_clipboard_format -- what Copy With Source puts beside the text.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.announce import Announcement, AnnouncementService, Severity
from quill.core.announce.adapters import SpeechSink
from quill.core.export_preset import preset_format_name, preset_index
from quill.core.markdown_clipboard import clipboard_mode, formatted_copy
from quill.core.settings import Settings
from quill.core.spoken_echo import HISTORY_OFF_MESSAGE, spoken_echo_text
from quill.ui.announce_wiring import policy_from_settings
from quill.ui.main_frame import MainFrame

# -- Keep an announcement history ------------------------------------------------


class _EchoStub:
    _record_spoken = MainFrame._record_spoken

    def __init__(self, keep: bool) -> None:
        self.settings = Settings(announcement_echo_history=keep)


def test_echo_history_on_records_what_was_said() -> None:
    stub = _EchoStub(keep=True)
    stub._record_spoken("Saved")
    assert list(stub._spoken_echo_history) == ["Saved"]
    assert "Saved" in spoken_echo_text(list(stub._spoken_echo_history), stub.settings)


def test_echo_history_off_keeps_nothing_and_drops_what_was_kept() -> None:
    stub = _EchoStub(keep=True)
    stub._record_spoken("Private thing")
    stub.settings = Settings(announcement_echo_history=False)
    stub._record_spoken("Saved")
    assert stub._spoken_echo_history is None
    assert spoken_echo_text([], stub.settings) == HISTORY_OFF_MESSAGE


# -- Interrupt speech for --------------------------------------------------------


def _spoken_interrupts(choice: str) -> dict[Severity, bool]:
    heard: list[bool] = []
    service = AnnouncementService(
        [SpeechSink(lambda _text, force: heard.append(force))],
        policy=policy_from_settings(Settings(announcement_severity_interrupt=choice)),
    )
    result: dict[Severity, bool] = {}
    for severity in Severity:
        service.announce(Announcement(text=f"msg {severity.value}", severity=severity))
        result[severity] = heard[-1]
    return result


def test_interrupt_default_keeps_warnings_and_errors_interrupting() -> None:
    assert Settings().announcement_severity_interrupt == "warnings"
    got = _spoken_interrupts("warnings")
    assert got[Severity.WARNING] and got[Severity.ERROR]
    assert not got[Severity.INFO] and not got[Severity.ROUTINE]


def test_interrupt_errors_only_lets_warnings_wait() -> None:
    got = _spoken_interrupts("errors")
    assert got[Severity.ERROR]
    assert not got[Severity.WARNING]


def test_interrupt_never_interrupts_nothing() -> None:
    assert not any(_spoken_interrupts("never").values())


def test_unknown_interrupt_value_loads_as_the_default() -> None:
    loaded = Settings.from_dict({"announcement_severity_interrupt": "bogus"})
    assert loaded.announcement_severity_interrupt == "warnings"


# -- Default export format -------------------------------------------------------

_EXPORT_NAMES = ["markdown", "commonmark", "gfm", "html", "docx", "plain_text", "epub", "pdf"]


@pytest.mark.parametrize(
    ("preset", "expected"),
    [("html", "html"), ("docx", "docx"), ("text", "plain_text"), ("pdf", "pdf")],
)
def test_export_preset_selects_its_format(preset: str, expected: str) -> None:
    settings = Settings(default_export_preset=preset)
    assert preset_format_name(settings) == expected
    assert _EXPORT_NAMES[preset_index(_EXPORT_NAMES, settings)] == expected


def test_export_other_dialog_opens_on_the_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import pandoc_formats

    selected: list[int] = []
    exported: list[str] = []

    class _Dialog:
        def __init__(self, *_a: object) -> None:
            self._sel = 0

        def __enter__(self) -> _Dialog:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def SetSelection(self, index: int) -> None:  # noqa: N802 - wx API
            self._sel = index
            selected.append(index)

        def GetSelection(self) -> int:  # noqa: N802 - wx API
            return self._sel

    host = SimpleNamespace(
        _wx=SimpleNamespace(SingleChoiceDialog=_Dialog, ID_OK=5100),
        frame=None,
        settings=Settings(default_export_preset="docx"),
        _show_modal_dialog=lambda _d, _t: 5100,
        export_document=exported.append,
    )
    MainFrame.export_document_other(host)  # type: ignore[arg-type]
    names = [fmt.name for fmt in pandoc_formats.formats_for_direction("export")]
    assert exported == ["docx"]
    assert names[selected[0]] == "docx"
    host.settings = Settings(default_export_preset="epub")
    MainFrame.export_document_other(host)  # type: ignore[arg-type]
    assert exported[-1] == "epub"


# -- Markdown clipboard format ---------------------------------------------------


def test_markdown_clipboard_default_is_plain_text_only() -> None:
    assert clipboard_mode(Settings()) == "text"
    assert formatted_copy("# Title", document_kind="markdown", mode="text") is None


def test_markdown_clipboard_html_adds_rendered_html() -> None:
    extra = formatted_copy("# Title\n\n**bold**", document_kind="markdown", mode="html")
    assert extra is not None and extra.kind == "html"
    assert "<h1" in extra.data and "<strong>bold</strong>" in extra.data


def test_markdown_clipboard_rtf_adds_rich_text() -> None:
    extra = formatted_copy("**bold**", document_kind="markdown", mode="rtf")
    assert extra is not None and extra.kind == "rtf"
    assert extra.data.startswith("{\\rtf1")


def test_markdown_clipboard_leaves_non_markdown_documents_plain() -> None:
    assert formatted_copy("plain words", document_kind="plain", mode="html") is None


def test_copy_with_source_puts_the_chosen_flavour_on_the_clipboard() -> None:
    from quill.ui.markdown_clipboard_copy import copy_with_source_payload

    placed: list[object] = []

    class _Composite:
        def __init__(self) -> None:
            self.parts: list[object] = []

        def Add(self, part: object, _preferred: bool = False) -> None:  # noqa: N802
            self.parts.append(part)

    class _Clipboard:
        def Open(self) -> bool:  # noqa: N802
            return True

        def Close(self) -> None:  # noqa: N802
            return None

        def SetData(self, data: object) -> bool:  # noqa: N802
            placed.append(data)
            return True

    fake_wx = SimpleNamespace(
        TheClipboard=_Clipboard(),
        DataObjectComposite=_Composite,
        TextDataObject=lambda text: ("text", text),
        HTMLDataObject=lambda html: ("html", html),
        LogNull=lambda: None,
    )
    plain_copies: list[str] = []
    host = SimpleNamespace(
        _wx=fake_wx,
        document=SimpleNamespace(path=None),
        editor=SimpleNamespace(GetValue=lambda: "# Notes\n\nSome **bold** text"),
        settings=Settings(markdown_clipboard_format="text"),
        _copy_to_clipboard=lambda text: plain_copies.append(text) or True,
    )
    assert copy_with_source_payload(host, "Some **bold** text\n\nSource: notes")
    assert plain_copies and not placed

    host.settings = Settings(markdown_clipboard_format="html")
    assert copy_with_source_payload(host, "Some **bold** text\n\nSource: notes")
    kinds = [part[0] for part in placed[-1].parts]  # type: ignore[attr-defined]
    assert kinds == ["text", "html"]
