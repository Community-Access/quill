"""Rich document mode + the Document Format switcher (One Editor, Every Format).

Unit tests over the ``RichModeMixin`` with a fake QuillRichEdit wrapper (no wx,
no COM): mode derivation, the native save intercept, the RTF autosave sidecar,
mode-polymorphic command routing, format retargeting, and the switcher's
status bar cell wiring (source pins, since headless CI cannot build wx).
The on-device RTF round trip is verified on real hardware.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.document import Document
from quill.ui.main_frame import MainFrame
from quill.ui.main_frame_rich_mode import DOCUMENT_FORMATS
from quill.ui.richedit_rtf_surface import RichEditRtfError


class _FakeWrapper:
    """Records QuillRichEdit calls; behaves like a live TOM by default."""

    def __init__(self, available: bool = True, fail: bool = False) -> None:
        self.available = available
        self.fail = fail
        self.calls: list[tuple[str, tuple]] = []

    def rtf_available(self) -> bool:
        return self.available

    def _record(self, name: str, *args: object) -> None:
        if self.fail:
            raise RichEditRtfError("no handle")
        self.calls.append((name, args))

    def apply_bold(self) -> None:
        self._record("apply_bold")

    def apply_italic(self) -> None:
        self._record("apply_italic")

    def apply_underline(self) -> None:
        self._record("apply_underline")

    def set_heading(self, level: int) -> None:
        self._record("set_heading", level)

    def set_alignment(self, how: str) -> None:
        self._record("set_alignment", how)

    def set_font_name(self, name: str) -> None:
        self._record("set_font_name", name)

    def set_font_size(self, points: float) -> None:
        self._record("set_font_size", points)

    def set_color(self, color: str) -> None:
        self._record("set_color", color)

    def set_highlight(self, color: str) -> None:
        self._record("set_highlight", color)

    def save_rtf(self, path: str) -> None:
        self._record("save_rtf", path)

    def get_rtf(self) -> bytes:
        self._record("get_rtf")
        return b"{\\rtf1 fake}"

    def set_rtf(self, data: bytes) -> None:
        self._record("set_rtf", data)

    def get_plain_text(self) -> str:
        return "plain text"


class _FakeEditor:
    def __init__(self, wrapper: _FakeWrapper | None) -> None:
        if wrapper is not None:
            self.quill_richedit = wrapper
        self._value = "hello"

    def GetValue(self) -> str:  # noqa: N802 - wx shape
        return self._value


def _frame(mode: str = "markup", wrapper: _FakeWrapper | None = None) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    tab = SimpleNamespace(
        editor_mode=mode,
        pending_format_suffix="",
        plain_format_choice="",
        document=None,
        docx_rich=False,
        docx_flagged=False,
        rich_backup_done=False,
    )
    frame.editor = _FakeEditor(wrapper)
    frame.document = Document(text="hello", path=None)
    tab.document = frame.document
    frame._active_tab = lambda: tab
    frame._statuses: list[str] = []
    frame._announced: list[str] = []
    frame._set_status = frame._statuses.append
    frame._set_status_quiet = frame._statuses.append
    frame._announce = frame._announced.append
    frame._refresh_title = lambda: None
    frame._refresh_statusbar = lambda: None
    return frame


# --------------------------------------------------------------------------- #
# Mode state (Phase 2)
# --------------------------------------------------------------------------- #


def test_editor_mode_defaults_to_markup() -> None:
    assert _frame()._current_editor_mode() == "markup"
    assert _frame("rich")._current_editor_mode() == "rich"
    assert _frame("rich_converted")._current_editor_mode() == "rich_converted"


def test_rich_capable_requires_wrapper_and_tom() -> None:
    assert _frame()._rich_capable() is False
    assert _frame(wrapper=_FakeWrapper(available=False))._rich_capable() is False
    assert _frame(wrapper=_FakeWrapper())._rich_capable() is True


# --------------------------------------------------------------------------- #
# Native save intercept (Phase 2)
# --------------------------------------------------------------------------- #


def test_rich_save_intercepts_only_the_native_rich_rtf_case(tmp_path: Path) -> None:
    wrapper = _FakeWrapper()
    frame = _frame("rich", wrapper)
    target = tmp_path / "doc.rtf"
    frame.document.path = target
    assert frame._save_rich_document_natively(frame.document, None) is True
    assert ("save_rtf", (str(target),)) in wrapper.calls
    assert frame.document.modified is False  # mark_saved ran

    # Markup mode: the classic conversion writer must run instead.
    frame2 = _frame("markup", _FakeWrapper())
    frame2.document.path = target
    assert frame2._save_rich_document_natively(frame2.document, None) is False

    # Save As to a non-RTF format leaves the conversion writer in charge.
    frame3 = _frame("rich", _FakeWrapper())
    frame3.document.path = target
    assert frame3._save_rich_document_natively(frame3.document, tmp_path / "doc.md") is False

    # rich_converted saves through the RTF writer (today's behavior).
    frame4 = _frame("rich_converted", _FakeWrapper())
    frame4.document.path = target
    assert frame4._save_rich_document_natively(frame4.document, None) is False


def test_rich_save_failure_surfaces_as_oserror(tmp_path: Path) -> None:
    frame = _frame("rich", _FakeWrapper(fail=True))
    frame.document.path = tmp_path / "doc.rtf"
    try:
        frame._save_rich_document_natively(frame.document, None)
    except OSError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("a failed rich save must raise OSError for the save handler")


# --------------------------------------------------------------------------- #
# Autosave sidecar (Phase 2)
# --------------------------------------------------------------------------- #


def test_rich_autosave_payload_only_in_rich_mode() -> None:
    assert _frame()._rich_autosave_payload() is None
    assert _frame("rich_converted", _FakeWrapper())._rich_autosave_payload() is None
    payload = _frame("rich", _FakeWrapper())._rich_autosave_payload()
    assert payload == b"{\\rtf1 fake}"


def test_rich_autosave_snapshots_round_trip(tmp_path, monkeypatch) -> None:
    from uuid import uuid4

    from quill.core.autosave import autosave_rich_document, latest_rich_autosave

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session = str(uuid4())
    document = Document(text="hi", path=None)
    target = autosave_rich_document(document, session, b"{\\rtf1 formatted}")
    assert target.suffix == ".rtfsnap"
    assert target.read_bytes() == b"{\\rtf1 formatted}"
    assert latest_rich_autosave(document, session) == target
    # Retention: never more than max_snapshots sidecars per document.
    for index in range(12):
        autosave_rich_document(document, session, b"%d" % index, max_snapshots=3)
    remaining = list(target.parent.glob("*.rtfsnap"))
    assert len(remaining) == 3


# --------------------------------------------------------------------------- #
# Mode-polymorphic formatting (Phase 3)
# --------------------------------------------------------------------------- #


def test_rich_format_command_routes_to_the_wrapper() -> None:
    wrapper = _FakeWrapper()
    frame = _frame("rich", wrapper)
    assert frame._rich_format_command("apply_bold", "Bold") is True
    assert ("apply_bold", ()) in wrapper.calls
    assert frame._announced == ["Bold"]
    assert frame.document.modified is True  # explicit dirty marking


def test_rich_format_command_declines_in_markup_mode() -> None:
    frame = _frame("markup", _FakeWrapper())
    assert frame._rich_format_command("apply_bold", "Bold") is False
    assert frame._announced == []


def test_rich_format_command_reports_tom_errors() -> None:
    frame = _frame("rich", _FakeWrapper(fail=True))
    assert frame._rich_format_command("apply_bold", "Bold") is True  # handled
    assert any("Could not apply bold" in status for status in frame._statuses)
    assert frame.document.modified is False


def test_rich_run_attrs_map_onto_the_tom() -> None:
    wrapper = _FakeWrapper()
    frame = _frame("rich", wrapper)
    assert frame._rich_apply_run_attrs({"font-family": "Consolas"}, "ok", "Font") is True
    assert frame._rich_apply_run_attrs({"font-size": "14"}, "ok", "Font size") is True
    assert frame._rich_apply_run_attrs({"color": "#ff0000"}, "ok", "Color") is True
    assert frame._rich_apply_run_attrs({"highlight": "yellow"}, "ok", "Highlight") is True
    names = [name for name, _args in wrapper.calls]
    assert names == ["set_font_name", "set_font_size", "set_color", "set_highlight"]
    # Unmapped attributes are refused honestly, not silently dropped.
    assert frame._rich_apply_run_attrs({"strike": "1"}, "ok", "Strikethrough") is False


def test_heading_command_passes_level() -> None:
    wrapper = _FakeWrapper()
    frame = _frame("rich", wrapper)
    assert frame._rich_format_command("set_heading", "Heading 2", 2) is True
    assert ("set_heading", (2,)) in wrapper.calls


# --------------------------------------------------------------------------- #
# The Document Format switcher (Phase 4)
# --------------------------------------------------------------------------- #


def test_document_formats_offer_the_five_targets() -> None:
    assert list(DOCUMENT_FORMATS) == ["plain", "markdown", "html", "rtf", "docx"]
    assert DOCUMENT_FORMATS["rtf"] == ("Rich Text (RTF)", ".rtf")


def test_current_document_format_follows_the_mode() -> None:
    frame = _frame("rich")
    assert frame.current_document_format() == "rtf"
    converted = _frame("rich_converted")
    assert converted.current_document_format() == "rtf"
    assert converted._document_format_status_text() == "Rich Text (RTF) (converted)"

    markup = _frame("markup")
    markup._current_markup_context = lambda: "markdown"
    assert markup.current_document_format() == "markdown"
    assert markup._document_format_status_text() == "Markdown"


def test_retarget_records_pending_suffix_and_save_redirect(tmp_path: Path) -> None:
    frame = _frame("markup")
    tab = frame._active_tab()
    frame.document.path = tmp_path / "notes.md"
    frame._retarget_format_suffix(tab, ".rtf")
    assert tab.pending_format_suffix == ".rtf"
    redirect = frame._pending_format_redirect()
    assert redirect is not None and redirect.name == "notes.rtf"
    # A path already matching the target clears the retarget.
    frame.document.path = tmp_path / "notes.rtf"
    frame._retarget_format_suffix(tab, ".rtf")
    assert tab.pending_format_suffix == ""
    assert frame._pending_format_redirect() is None


def test_plain_text_prompt_answer_is_remembered() -> None:
    frame = _frame("markup")
    frame._active_tab().plain_format_choice = "plain"
    # A remembered "stay plain" answer keeps the command quiet with no dialog.
    assert frame._offer_plain_text_formatting_choice("Bold") == "plain"


# --------------------------------------------------------------------------- #
# Editable rich Word (Phase 7)
# --------------------------------------------------------------------------- #


def test_switcher_offers_word_as_the_fifth_target() -> None:
    assert DOCUMENT_FORMATS["docx"] == ("Word (.docx)", ".docx")


def test_docx_rich_tab_reports_word_format() -> None:
    frame = _frame("rich", _FakeWrapper())
    frame._active_tab().docx_rich = True
    assert frame.current_document_format() == "docx"
    assert frame._document_format_status_text() == "Word (.docx)"


def test_docx_rich_save_runs_the_bridge_and_backs_up_flagged_originals(
    tmp_path: Path,
) -> None:
    import pytest

    from quill.io.docx_writer import python_docx_available

    if not python_docx_available():  # pragma: no cover - CI without python-docx
        pytest.skip("python-docx not installed")
    wrapper = _FakeWrapper()
    wrapper.get_rtf = lambda: b"{\\rtf1\\ansi\\deff0 hello\\par}"  # type: ignore[method-assign]
    frame = _frame("rich", wrapper)
    tab = frame._active_tab()
    tab.docx_rich = True
    tab.docx_flagged = True
    target = tmp_path / "report.docx"
    target.write_bytes(b"original word bytes")
    frame.document.path = target

    assert frame._save_rich_document_natively(frame.document, None) is True
    # The original was backed up exactly once, before the first overwrite.
    backups = list(tmp_path.glob("report.backup-*.docx"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"original word bytes"
    assert tab.rich_backup_done is True
    # The target is now a real docx (ZIP signature), not the original bytes.
    assert target.read_bytes()[:2] == b"PK"
    assert frame.document.modified is False

    # A second save must not write a second backup.
    frame.document.modified = True
    assert frame._save_rich_document_natively(frame.document, None) is True
    assert len(list(tmp_path.glob("report.backup-*.docx"))) == 1


def test_docx_save_without_the_flag_never_backs_up(tmp_path: Path) -> None:
    import pytest

    from quill.io.docx_writer import python_docx_available

    if not python_docx_available():  # pragma: no cover
        pytest.skip("python-docx not installed")
    wrapper = _FakeWrapper()
    wrapper.get_rtf = lambda: b"{\\rtf1\\ansi\\deff0 clean\\par}"  # type: ignore[method-assign]
    frame = _frame("rich", wrapper)
    tab = frame._active_tab()
    tab.docx_rich = True
    tab.docx_flagged = False
    target = tmp_path / "clean.docx"
    target.write_bytes(b"clean original")
    frame.document.path = target
    assert frame._save_rich_document_natively(frame.document, None) is True
    assert list(tmp_path.glob("clean.backup-*.docx")) == []


def test_rich_tab_saving_docx_without_docx_rich_uses_the_classic_writer(
    tmp_path: Path,
) -> None:
    # An RTF-native rich tab Save-As'd to .docx is the conversion writer's job.
    frame = _frame("rich", _FakeWrapper())
    frame.document.path = tmp_path / "doc.rtf"
    assert frame._save_rich_document_natively(frame.document, tmp_path / "doc.docx") is False


def test_docx_open_declines_gracefully_without_rich_capability() -> None:
    # No wrapper (or no python-docx): the read-extract floor stays untouched.
    frame = _frame("markup")
    frame._enter_docx_rich_mode_for_open(Path("missing.docx"), frame.document)
    assert frame._active_tab().editor_mode == "markup"
    assert frame.document.text == "hello"


# --------------------------------------------------------------------------- #
# Source pins: every entry point dispatches the one handler
# --------------------------------------------------------------------------- #

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def test_switcher_entry_points_share_one_handler() -> None:
    main_frame = (_UI / "main_frame.py").read_text(encoding="utf-8")
    menu = (_UI / "main_frame_menu.py").read_text(encoding="utf-8")
    statusbar = (_UI / "main_frame_statusbar.py").read_text(encoding="utf-8")
    # Command palette / keyboard chord registration.
    assert '"format.switch_document_format"' in main_frame
    assert "self.switch_document_format" in main_frame
    # Format menu item.
    assert "_id_switch_document_format" in menu
    assert "self.switch_document_format()" in menu
    # Status bar cell activation.
    assert '"document_format": self.switch_document_format' in statusbar


def test_status_bar_offers_the_format_cell() -> None:
    from quill.core.settings import STATUS_BAR_ITEMS

    assert "document_format" in STATUS_BAR_ITEMS
    main_frame = (_UI / "main_frame.py").read_text(encoding="utf-8")
    assert '"document_format": "Format"' in main_frame
    assert '"document_format": "core.format"' in main_frame


def test_default_chord_moved_to_the_switcher() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP.get("format.switch_document_format") == "Ctrl+Shift+Grave, K"
    assert "view.switch_editing_lens" not in DEFAULT_KEYMAP


def test_rtf_open_dispatch_goes_through_rich_mode() -> None:
    main_frame = (_UI / "main_frame.py").read_text(encoding="utf-8")
    assert "_enter_rich_mode_for_open" in main_frame
    # The retired lens dispatch must stay gone.
    assert "_create_rich_document_tab" not in main_frame
    assert "_rich_editor_enabled" not in main_frame


def test_native_ctrl_biu_interception_is_wired() -> None:
    main_frame = (_UI / "main_frame.py").read_text(encoding="utf-8")
    start = main_frame.index("def _on_editor_char_hook(")
    body = main_frame[start : main_frame.index("\n    def ", start + 1)]
    assert '== "rich"' in body
    assert "format_bold" in body and "format_italic" in body and "format_underline" in body
