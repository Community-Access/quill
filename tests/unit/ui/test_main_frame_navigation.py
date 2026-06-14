from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import quill.ui.main_frame as main_frame_module
from quill.core.a11y_regions import RegionTracker
from quill.core.document import Document
from quill.core.epub import EpubBook, EpubChapter, EpubHeading
from quill.core.features import FEATURE_DEFINITIONS, PROFILE_DEFINITIONS, feature_for_command
from quill.core.locations import LocationRing
from quill.core.search import SearchOptions
from quill.core.spellcheck import Misspelling
from quill.ui.main_frame import MainFrame


@pytest.fixture(autouse=True)
def _isolated_quill_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


class _Editor:
    def __init__(self, text: str, insertion_point: int = 0) -> None:
        self._text = text
        self._insertion_point = insertion_point
        self.selection: tuple[int, int] = (insertion_point, insertion_point)
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._insertion_point

    def SetInsertionPoint(self, value: int) -> None:
        self._insertion_point = value

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)

    def ChangeValue(self, value: str) -> None:
        self._text = value

    def Replace(self, start: int, end: int, value: str) -> None:
        self._text = f"{self._text[:start]}{value}{self._text[end:]}"
        self._insertion_point = start + len(value)

    def SetFocus(self) -> None:
        self.focused = True

    def GetSelection(self) -> tuple[int, int]:
        return self.selection


class _StatusBar:
    def __init__(self) -> None:
        self.focused = False
        self.status: dict[int, str] = {}

    def SetFocus(self) -> None:
        self.focused = True

    def SetStatusText(self, value: str, index: int = 0) -> None:
        self.status[index] = value

    def SetFieldsCount(self, count: int) -> None:
        self.fields_count = count

    def SetStatusWidths(self, widths: list[int]) -> None:
        self.widths = widths


class _Frame:
    def __init__(self) -> None:
        self.focused = False
        self.title = ""

    def SetFocus(self) -> None:
        self.focused = True

    def SetTitle(self, title: str) -> None:
        self.title = title


class _Notebook:
    def __init__(self) -> None:
        self.pages: list[object] = []
        self.selection = 0
        self.titles: list[str] = []
        self.visible = True

    def Bind(self, *_args: object, **_kwargs: object) -> None:
        return None

    def Show(self, value: bool = True) -> None:
        self.visible = value

    def Hide(self) -> None:
        self.visible = False

    def AddPage(self, page: object, title: str, select: bool = False) -> None:
        self.pages.append(page)
        self.titles.append(title)
        if select:
            self.selection = len(self.pages) - 1

    def DeletePage(self, index: int) -> None:
        del self.pages[index]
        del self.titles[index]
        if self.selection >= len(self.pages):
            self.selection = max(0, len(self.pages) - 1)

    def GetSelection(self) -> int:
        return self.selection

    def SetSelection(self, index: int) -> None:
        self.selection = index

    def ChangeSelection(self, index: int) -> None:
        self.selection = index

    def GetPageCount(self) -> int:
        return len(self.pages)

    def SetPageText(self, index: int, title: str) -> None:
        self.titles[index] = title

    def GetPageText(self, index: int) -> str:
        return self.titles[index]


class _MenuItem:
    def __init__(self, menu_id: int, label: str) -> None:
        self.menu_id = menu_id
        self.label = label

    def Enable(self, _enabled: bool) -> None:
        return None


class _Menu:
    def __init__(self) -> None:
        self.items: list[_MenuItem] = []

    def GetMenuItemCount(self) -> int:
        return len(self.items)

    def FindItemByPosition(self, position: int) -> _MenuItem | None:
        if position < 0 or position >= len(self.items):
            return None
        return self.items[position]

    def DestroyItem(self, item: _MenuItem) -> None:
        self.items.remove(item)

    def Append(self, menu_id: int, label: str) -> _MenuItem:
        item = _MenuItem(menu_id, label)
        self.items.append(item)
        return item

    def AppendSeparator(self) -> None:
        return None


def _build_frame(text: str, insertion_point: int = 0) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(path=Path("note.md"))
    frame.editor = _Editor(text=text, insertion_point=insertion_point)
    frame.statusbar = _StatusBar()
    frame.frame = _Frame()
    frame.notebook = _Notebook()
    frame._sessions_menu = _Menu()
    frame._session_menu_ids = {}
    frame._location_ring = LocationRing()
    frame._region_tracker = RegionTracker()
    frame._active_region = "Editor"
    frame._region_tracker.enter("Editor")
    frame._status_message = "Ready"
    frame._overwrite_mode = False
    frame._insert_key_down = False
    frame._extend_selection_mode = False
    frame._extend_selection_anchor = None
    frame._compare_session = None
    frame._compare_ignore_trailing_spaces = True
    frame._compare_ignore_line_endings = True
    frame._external_change_watcher = None
    frame._external_change_timer = None
    frame._document_tabs = [type("Tab", (), {"editor": frame.editor, "document": frame.document})()]
    frame._active_tab_index = 0
    frame.notebook.AddPage(object(), frame.document.name, select=True)
    frame.settings = type(
        "Settings",
        (),
        {
            "persistent_undo": False,
            "wrap_find": True,
            "show_tab_control": False,
            "title_bar_path_mode": "name",
            "dirty_title_style": "text",
            "status_bar_order": ["message", "line_column", "mode", "selection", "file_path"],
            "status_bar_hidden": ["selection"],
            # Keep the browse-mode prewarm a no-op in the shared harness: these
            # tests don't exercise it, and it otherwise needs wx/CallLater wiring.
            "browse_mode_preload_cache": False,
        },
    )()
    return frame


def test_navigate_next_region_focuses_status_bar() -> None:
    frame = _build_frame("hello")
    frame.navigate_next_region()
    assert frame._active_region == "Status Bar"
    assert frame.statusbar.focused is True


def _attach_split_preview(frame: MainFrame) -> object:
    """Give the active tab a visible side-preview pane (split open)."""

    class _PreviewControl:
        def __init__(self) -> None:
            self.focused = False

        def SetFocus(self) -> None:
            self.focused = True

    class _Splitter:
        def IsSplit(self) -> bool:
            return True

    preview = type("Preview", (), {"control": _PreviewControl()})()
    tab = frame._document_tabs[0]
    tab.preview = preview
    tab.splitter = _Splitter()
    return preview.control


def test_navigate_next_region_includes_preview_when_split() -> None:
    frame = _build_frame("# hi")
    preview_control = _attach_split_preview(frame)
    # Editor -> Preview -> Status Bar -> Editor
    frame.navigate_next_region()
    assert frame._active_region == "Preview"
    assert preview_control.focused is True
    frame.navigate_next_region()
    assert frame._active_region == "Status Bar"
    assert frame.statusbar.focused is True
    frame.navigate_next_region()
    assert frame._active_region == "Editor"
    assert frame.editor.focused is True


def test_navigate_previous_region_reaches_preview() -> None:
    frame = _build_frame("# hi")
    preview_control = _attach_split_preview(frame)
    # Shift+F6 from Editor wraps backwards to Status Bar, then Preview.
    frame.navigate_previous_region()
    assert frame._active_region == "Status Bar"
    frame.navigate_previous_region()
    assert frame._active_region == "Preview"
    assert preview_control.focused is True


def test_navigate_region_skips_preview_when_hidden() -> None:
    frame = _build_frame("hello")
    # No split preview attached: rotation stays Editor <-> Status Bar.
    frame.navigate_next_region()
    assert frame._active_region == "Status Bar"
    frame.navigate_next_region()
    assert frame._active_region == "Editor"


def test_match_bracket_moves_to_match() -> None:
    text = "alpha (one [two] three)"
    frame = _build_frame(text, insertion_point=text.index("["))
    frame.match_bracket()
    assert frame.editor.GetInsertionPoint() == text.index("]")


def test_navigate_next_structure_moves_to_heading() -> None:
    text = "intro\n## Heading\nbody"
    frame = _build_frame(text, insertion_point=0)
    frame.navigate_next_structure()
    assert frame.editor.GetInsertionPoint() == text.index("## Heading")


def test_navigate_next_heading_announces_level_and_ordinal() -> None:
    text = "# Top\nIntro\n## Child\nBody\n### Grandchild\nMore\n"
    frame = _build_frame(text, insertion_point=0)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.navigate_next_heading()

    assert statuses == ["Moved to next heading, H2, 2 of 3: Child"]


def test_navigate_previous_heading_announces_level_and_ordinal() -> None:
    text = "# Top\nIntro\n## Child\nBody\n### Grandchild\nMore\n"
    frame = _build_frame(text, insertion_point=len(text))
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.navigate_previous_heading()

    assert statuses == ["Moved to previous heading, H3, 3 of 3: Grandchild"]


def test_select_line_announces_scope_and_word_count() -> None:
    text = "one two three\nsecond line\n"
    frame = _build_frame(text, insertion_point=0)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.select_line()

    assert statuses == ["Selected line, 3 words."]


def test_select_paragraph_announces_scope_and_word_count() -> None:
    text = "alpha beta\ngamma\n\nnext paragraph\n"
    frame = _build_frame(text, insertion_point=0)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.select_paragraph()

    assert statuses == ["Selected paragraph, 3 words."]


def test_select_line_announces_singular_word() -> None:
    text = "solo\nmore\n"
    frame = _build_frame(text, insertion_point=0)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.select_line()

    assert statuses == ["Selected line, 1 word."]


def test_expand_selection_grows_and_announces_scope() -> None:
    text = "alpha beta gamma\n\nsecond paragraph\n"
    frame = _build_frame(text, insertion_point=2)
    frame.editor.SetSelection(2, 2)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.expand_selection()

    assert frame.editor.GetSelection() != (2, 2)
    assert statuses and statuses[-1].startswith("Selected ")


def test_shrink_selection_restores_previous_span() -> None:
    text = "alpha beta gamma\n\nsecond paragraph\n"
    frame = _build_frame(text, insertion_point=2)
    frame.editor.SetSelection(2, 2)
    frame.expand_selection()
    expanded = frame.editor.GetSelection()
    frame.expand_selection()
    assert frame.editor.GetSelection() != expanded

    frame.shrink_selection()

    assert frame.editor.GetSelection() == expanded


def test_shrink_selection_with_empty_stack_reports() -> None:
    text = "alpha beta\n"
    frame = _build_frame(text, insertion_point=0)
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    frame.shrink_selection()

    assert statuses == ["No selection to shrink"]


def test_persistent_undo_steps_across_history() -> None:
    frame = _build_frame("one", insertion_point=0)
    frame.settings = type(
        "Settings",
        (),
        {
            "persistent_undo": True,
            "wrap_find": True,
            "show_tab_control": False,
            "title_bar_path_mode": "name",
            "dirty_title_style": "text",
            "status_bar_order": ["message", "line_column", "mode", "selection", "file_path"],
            "status_bar_hidden": ["selection"],
        },
    )()
    frame._persistent_undo_history = ["one", "two", "three"]
    frame._persistent_undo_index = 2
    frame._suspend_persistent_undo = False
    frame._step_persistent_undo(-1)
    assert frame.editor.GetValue() == "two"


def test_statusbar_shows_line_and_column() -> None:
    frame = _build_frame("one\ntwo", insertion_point=5)
    frame._apply_statusbar_layout()
    assert frame.statusbar.fields_count == 6
    assert frame.statusbar.status[1] == "Ln 2, Col 2"
    assert frame.statusbar.status[2] == "INS"


def test_statusbar_respects_order_and_hidden_items() -> None:
    frame = _build_frame("hello", insertion_point=1)
    frame.settings.status_bar_order = ["line_column", "mode", "file_path", "message", "selection"]
    frame.settings.status_bar_hidden = ["file_path", "selection"]
    frame._apply_statusbar_layout()
    assert frame.statusbar.fields_count == 5
    assert frame.statusbar.status[0] == "Ln 1, Col 2"
    assert frame.statusbar.status[1] == "INS"


def test_refresh_title_uses_full_path_when_enabled() -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.document.modified = True
    frame.settings.title_bar_path_mode = "full_path"
    frame.settings.dirty_title_style = "asterisk"

    frame._refresh_title()

    assert frame.frame.title == f"{frame.document.path} * - Quill"


def test_statusbar_hides_file_path_when_title_uses_full_path() -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.settings.title_bar_path_mode = "full_path"

    items = frame._statusbar_items()

    assert "file_path" not in items


def test_statusbar_hides_cells_for_disabled_features() -> None:
    """A feature-gated status-bar cell must drop out when its feature is off.

    The original behaviour rendered the cell with the text "Unavailable in
    current profile" instead of hiding it, which contradicted the user-facing
    promise that toggling a feature flag removes its affordance from the UI.
    """
    frame = _build_frame("hello", insertion_point=0)
    frame.features = types.SimpleNamespace(
        is_enabled=lambda feature_id: feature_id not in {"core.read_aloud", "core.analysis"}
    )
    frame._status_message = "Ready"

    items = frame._statusbar_items()

    # Cells that map to enabled features stay; cells that map to disabled
    # features disappear entirely so the bar reflects the active profile.
    assert "word_count" not in items
    assert "read_aloud" not in items
    # Cells with no feature mapping (or always-on features) remain.
    assert "message" in items
    assert "line_column" in items


def test_statusbar_hides_modified_message_when_title_shows_dirty_state() -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.document.modified = True
    frame.settings.dirty_title_style = "text"
    frame._status_message = "Modified"

    message = frame._statusbar_text_for_item("message")

    assert message == "Ready"


def test_refresh_title_uses_asterisk_text_dirty_style() -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.document.modified = True
    frame.settings.title_bar_path_mode = "name"
    frame.settings.dirty_title_style = "asterisk_text"

    frame._refresh_title()

    assert frame.frame.title == "note.md * [modified] - Quill"


def test_feature_coverage_maps_new_surfaces_to_known_features() -> None:
    assert set(MainFrame._STATUS_BAR_FEATURES.values()) <= set(FEATURE_DEFINITIONS)

    command_ids = [
        "tools.profiles_and_features_settings",
        "help.switch_feature_profile",
        "help.undo_last_profile_change",
        "help.reset_feature_profile",
        "help.run_profile_onboarding",
        "help.why_dont_i_see_feature",
        "help.feature_profile_health_check",
        "tools.regex_helper",
        "tools.status_bar_settings",
        "tools.open_welcome_guide",
        "tools.open_keyboard_reference",
        "tools.read_aloud_start_pause",
        "tools.read_aloud_stop",
        "tools.announcement_backend",
        "tools.announcement_trace_toggle",
    ]
    assert all(feature_for_command(command_id) in FEATURE_DEFINITIONS for command_id in command_ids)


def test_increase_heading_level_for_markdown_line() -> None:
    frame = _build_frame("# Heading", insertion_point=2)
    frame.increase_heading_level()
    assert frame.editor.GetValue() == "## Heading"


def test_next_document_switches_active_tab() -> None:
    frame = _build_frame("one", insertion_point=0)
    second_editor = _Editor("two", insertion_point=0)
    second_doc = Document(path=Path("two.md"))
    frame._document_tabs.append(
        type("Tab", (), {"editor": second_editor, "document": second_doc})()
    )
    frame.notebook.AddPage(object(), "two.md", select=False)
    frame.notebook.selection = 0
    frame.next_document()
    assert frame.document.path == Path("two.md")
    assert frame.editor.GetValue() == "two"


def test_close_current_document_removes_tab() -> None:
    frame = _build_frame("one", insertion_point=0)
    second_editor = _Editor("two", insertion_point=0)
    second_doc = Document(path=Path("two.md"))
    frame._document_tabs.append(
        type("Tab", (), {"editor": second_editor, "document": second_doc})()
    )
    frame.notebook.AddPage(object(), "two.md", select=False)
    frame.notebook.selection = 1
    frame._prompt_to_save_active_document = lambda _label: True  # type: ignore[assignment]
    frame.close_current_document()
    assert len(frame._document_tabs) == 1
    assert frame.document.path == Path("note.md")


def test_prompt_to_save_active_document_saves_when_requested() -> None:
    frame = _build_frame("one", insertion_point=0)
    frame.document.modified = True
    frame._wx = type("WX", (), {"ID_YES": 1, "ID_CANCEL": 0})()
    actions: list[str] = []

    frame._prompt_unsaved_changes_action = lambda *_args: 1  # type: ignore[method-assign]

    def _save_file() -> None:
        actions.append("saved")
        frame.document.modified = False

    frame.save_file = _save_file  # type: ignore[method-assign]

    assert frame._prompt_to_save_active_document("closing") is True
    assert actions == ["saved"]


def test_prompt_to_save_active_document_cancels_when_requested() -> None:
    frame = _build_frame("one", insertion_point=0)
    frame.document.modified = True
    frame._wx = type("WX", (), {"ID_YES": 1, "ID_CANCEL": 0})()
    frame._prompt_unsaved_changes_action = lambda *_args: 0  # type: ignore[method-assign]

    assert frame._prompt_to_save_active_document("closing") is False


def test_prompt_to_save_active_document_discards_when_requested() -> None:
    frame = _build_frame("one", insertion_point=0)
    frame.document.modified = True
    frame._wx = type("WX", (), {"ID_YES": 1, "ID_CANCEL": 0, "ID_NO": 2})()
    frame._prompt_unsaved_changes_action = lambda *_args: 2  # type: ignore[method-assign]

    assert frame._prompt_to_save_active_document("closing") is True


def test_confirm_discard_changes_accepts_reload_only() -> None:
    frame = _build_frame("one", insertion_point=0)
    frame._wx = type("WX", (), {"ID_YES": 1, "ID_CANCEL": 0})()
    frame._prompt_unsaved_changes_action = lambda *_args: 1  # type: ignore[method-assign]

    assert frame._confirm_discard_changes() is True


def test_show_startup_wizard_page_uses_rendered_html_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.settings = type("Settings", (), {"bw_provider_id": "", "bw_speech_model_id": ""})()
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    captured: dict[str, object] = {}

    class _PreviewDialog:
        def __init__(self, parent: object, title: str, body_html: str) -> None:
            captured["parent"] = parent
            captured["title"] = title
            captured["body_html"] = body_html

        def show(self) -> None:
            captured["shown"] = True

    preview_module = types.ModuleType("quill.ui.preview_dialog")
    preview_module.MarkdownPreviewDialog = _PreviewDialog
    monkeypatch.setitem(sys.modules, "quill.ui.preview_dialog", preview_module)

    frame.show_startup_wizard_page()

    assert captured["parent"] is frame.frame
    assert captured["title"] == "Startup Wizard"
    assert "<!doctype html>" not in str(captured["body_html"])
    assert "<h1 id='startup-wizard'>Startup Wizard</h1>" in str(captured["body_html"])
    assert captured["shown"] is True
    assert statuses == ["Opened Startup Wizard overview"]


def test_compare_group_builder_classifies_case_only_changes() -> None:
    frame = _build_frame("Alpha")
    groups = frame._build_compare_groups([("left.txt", "Alpha\n"), ("right.txt", "alpha\n")])
    assert len(groups) == 1
    assert groups[0].kind == "case-only"


def test_compare_group_builder_ignores_trailing_space_when_enabled() -> None:
    frame = _build_frame("Alpha")
    frame._compare_ignore_trailing_spaces = True
    groups = frame._build_compare_groups([("left.txt", "Alpha\n"), ("right.txt", "Alpha   \n")])
    assert groups == []


class _KeyEvent:
    def __init__(self, key_code: int) -> None:
        self._key_code = key_code
        self.skipped = False
        self._control = False
        self._shift = False
        self._alt = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def ControlDown(self) -> bool:
        return self._control

    def ShiftDown(self) -> bool:
        return self._shift

    def AltDown(self) -> bool:
        return self._alt

    def Skip(self) -> None:
        self.skipped = True


def test_insert_key_toggles_overwrite_mode_status() -> None:
    frame = _build_frame("hello", insertion_point=5)
    event = _KeyEvent(45)
    frame._wx = type("WX", (), {"WXK_INSERT": 45})()
    frame._on_editor_key_down(event)
    assert frame.statusbar.status[2] == "OVR"


def test_ctrl_shift_o_opens_outline_navigator_from_editor() -> None:
    frame = _build_frame("# Title", insertion_point=0)
    called = {"outline": False}

    def fake_open_outline_navigator() -> None:
        called["outline"] = True

    frame.open_outline_navigator = fake_open_outline_navigator  # type: ignore[method-assign]
    event = _KeyEvent(ord("O"))
    event._control = True
    event._shift = True
    frame._wx = type("WX", (), {"WXK_INSERT": 45, "WXK_F8": 119})()

    frame._on_editor_key_down(event)

    assert called["outline"] is True


def test_enter_continues_markdown_list_item() -> None:
    frame = _build_frame("- item", insertion_point=6)
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_INSERT": 45,
            "WXK_F8": 119,
            "WXK_RETURN": 13,
            "WXK_NUMPAD_ENTER": 370,
            "WXK_TAB": 9,
        },
    )()
    event = _KeyEvent(13)

    frame._on_editor_key_down(event)

    assert frame.editor.GetValue() == "- item\n- "
    assert frame._status_message == "Continued list item"


def test_enter_on_empty_list_item_exits_list() -> None:
    frame = _build_frame("- ", insertion_point=2)
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_INSERT": 45,
            "WXK_F8": 119,
            "WXK_RETURN": 13,
            "WXK_NUMPAD_ENTER": 370,
            "WXK_TAB": 9,
        },
    )()
    event = _KeyEvent(13)

    frame._on_editor_key_down(event)

    assert frame.editor.GetValue() == ""
    assert frame._status_message == "Exited list"


def test_tab_and_shift_tab_adjust_list_nesting() -> None:
    frame = _build_frame("- one\n- two", insertion_point=8)
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_INSERT": 45,
            "WXK_F8": 119,
            "WXK_RETURN": 13,
            "WXK_NUMPAD_ENTER": 370,
            "WXK_TAB": 9,
        },
    )()
    event = _KeyEvent(9)
    frame._on_editor_key_down(event)
    assert frame.editor.GetValue() == "- one\n    - two"
    assert frame._status_message == "Nested list item"

    shift_event = _KeyEvent(9)
    shift_event._shift = True
    frame._on_editor_key_down(shift_event)
    assert frame.editor.GetValue() == "- one\n- two"
    assert frame._status_message == "Promoted list item"


def test_extract_list_manager_state_tracks_nested_items() -> None:
    frame = _build_frame("- Parent\n    - [x] Child\n1. Ordered", insertion_point=14)

    state = frame._extract_list_manager_state()

    assert state is not None
    assert [item.kind for item in state.items] == ["bullet", "task", "ordered"]
    assert [item.level for item in state.items] == [0, 1, 0]


def test_open_outline_navigator_routes_epub_to_epub_navigator() -> None:
    frame = _build_frame("# EPUB: Book", insertion_point=0)
    frame.document.path = Path("book.epub")
    called = {"epub": False}

    def fake_open_epub_navigator() -> None:
        called["epub"] = True

    frame.open_epub_navigator = fake_open_epub_navigator  # type: ignore[method-assign]

    frame.open_outline_navigator()

    assert called["epub"] is True


def test_open_outline_navigator_reports_plain_text_as_unsupported() -> None:
    frame = _build_frame("Plain text", insertion_point=0)
    frame.document.path = Path("notes.txt")
    frame._build_outline_navigator_nodes = lambda: (_ for _ in ()).throw(  # type: ignore[method-assign]
        AssertionError("outline nodes should not be built for plain text")
    )

    frame.open_outline_navigator()

    assert frame._status_message == "Outline is not available for plain text files"


# The live-execution Preferences tests that drove the old wx.SingleChoiceDialog
# "choose then OK then open" flow were removed when that picker was replaced by
# the multi-page Preferences hub (a wx.Listbook/wx.Toolbook book control). The
# hub is wx-heavy and cannot be exercised headlessly, so its wiring is pinned by
# the source-contract test in tests/unit/ui/test_preferences_hub_wiring.py.


def test_build_outline_navigator_nodes_tracks_heading_hierarchy() -> None:
    frame = _build_frame("# Title\nBody\n## Child\nText\n# Next\n", insertion_point=0)

    nodes = frame._build_outline_navigator_nodes()

    assert [node.label for node in nodes] == ["Title", "Next"]
    assert [node.label for node in nodes[0].children] == ["Child"]
    assert "## Child" in nodes[0].children[0].preview
    assert nodes[0].children[0].action_label == "Jump to Heading"


def test_build_epub_navigator_nodes_uses_chapter_titles_and_preview() -> None:
    frame = _build_frame("# EPUB", insertion_point=0)
    book = EpubBook(
        title="Sample Book",
        chapters=(
            EpubChapter(
                title="One",
                href="one.xhtml",
                text="Heading First chapter",
                headings=(EpubHeading(level=1, title="Heading"),),
            ),
            EpubChapter(title="Two", href="two.xhtml", text="Second chapter"),
        ),
    )

    nodes = frame._build_epub_navigator_nodes(book)

    assert [node.label for node in nodes] == ["One", "Two"]
    assert nodes[0].action_label == "Open Chapter"
    assert nodes[0].children[0].label == "Heading"
    assert nodes[0].children[0].action_label == "Jump to Heading"
    assert "First chapter" in nodes[0].preview


def test_refresh_contextual_menu_disables_insert_table_for_plain_documents() -> None:
    frame = _build_frame("Heading-like text\n- item\n", insertion_point=0)
    frame.document.path = Path("note.txt")

    class _TrackedMenuItem:
        def __init__(self) -> None:
            self.enabled: bool | None = None

        def Enable(self, enabled: bool) -> None:
            self.enabled = enabled

    class _MenuBar:
        def __init__(self, table_item: _TrackedMenuItem) -> None:
            self._table_item = table_item

        def FindItemById(self, item_id: int) -> object | None:
            if item_id == frame._id_insert_table:
                return self._table_item
            return None

    table_item = _TrackedMenuItem()
    frame.frame.GetMenuBar = lambda: _MenuBar(table_item)  # type: ignore[attr-defined]
    frame._id_insert_markdown_tag = 1001
    frame._id_heading_1 = 1002
    frame._id_heading_2 = 1003
    frame._id_heading_3 = 1004
    frame._id_heading_4 = 1005
    frame._id_heading_5 = 1006
    frame._id_heading_6 = 1007
    frame._id_insert_bullet_list = 1008
    frame._id_insert_numbered_list = 1009
    frame._id_insert_task_list = 1010
    frame._id_insert_code_block = 1011
    frame._id_insert_footnote = 1012
    frame._id_insert_table = 1013
    frame._id_insert_html_tag = 1014

    frame._refresh_contextual_menu_items()

    assert table_item.enabled is False


def test_find_heading_position_returns_matching_heading_offset() -> None:
    frame = _build_frame("# EPUB", insertion_point=0)
    chapter_text = "# Chapter\n\nIntro text Heading body\n"

    position = frame._find_heading_position(chapter_text, "Heading", 0)

    assert position == chapter_text.index("Heading")


def test_build_misspelling_navigator_nodes_uses_line_and_column() -> None:
    frame = _build_frame("hello\nwrng word\n", insertion_point=0)
    nodes = frame._build_misspelling_navigator_nodes([Misspelling(word="wrng", start=6, end=10)])

    assert nodes[0].label == "wrng (Ln 2, Col 1)"
    assert nodes[0].action_label == "Jump to Occurrence"
    assert "wrng word" in nodes[0].preview


def test_open_misspelling_list_jumps_to_selected_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _build_frame("hello\nwrng word\n", insertion_point=0)
    item = Misspelling(word="wrng", start=6, end=10)
    frame._spell_dictionary = lambda: {"hello", "word"}  # type: ignore[method-assign]
    frame._show_tree_navigator = lambda **_kwargs: item  # type: ignore[method-assign]
    monkeypatch.setattr(
        "quill.ui.main_frame.list_misspellings",
        lambda _text, _dictionary: [item],
    )

    frame.open_misspelling_list()

    assert frame.editor.GetInsertionPoint() == 6
    assert frame.editor.selection == (6, 10)


def test_list_bookmarks_jumps_to_selected_bookmark() -> None:
    frame = _build_frame("alpha\nbeta\n", insertion_point=0)
    frame._bookmarks = {"Middle": 6}
    frame._show_tree_navigator = lambda **_kwargs: "Middle"  # type: ignore[method-assign]

    frame.list_bookmarks()

    assert frame.editor.GetInsertionPoint() == 6
    assert frame._status_message == 'Jumped to bookmark "Middle"'


def test_go_to_bookmark_jumps_and_wires_modal_ids() -> None:
    # Regression for #85: Go To Bookmark must reliably show a dismissible
    # dialog with a guaranteed selection and move the caret to the bookmark.
    frame = _build_frame("alpha\nbeta\n", insertion_point=0)
    frame._bookmarks = {"Middle": 6}
    captured: dict[str, object] = {}

    class _ChoiceDialog:
        def __init__(
            self, _parent: object, _message: str, _caption: str, choices: list[str]
        ) -> None:
            self.choices = choices
            self.selection = -1
            self.affirmative_id: int | None = None
            self.escape_id: int | None = None
            captured["dialog"] = self

        def __enter__(self) -> _ChoiceDialog:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def SetSelection(self, selection: int) -> None:
            self.selection = selection

        def SetAffirmativeId(self, value: int) -> None:
            self.affirmative_id = value

        def SetEscapeId(self, value: int) -> None:
            self.escape_id = value

        def GetStringSelection(self) -> str:
            return self.choices[self.selection]

    frame._wx = type(
        "WX",
        (),
        {"SingleChoiceDialog": _ChoiceDialog, "ID_OK": 1, "ID_CANCEL": 0},
    )()
    frame._show_modal_dialog = lambda _dialog, _label: 1  # type: ignore[method-assign]

    frame.go_to_bookmark()

    dialog = captured["dialog"]
    assert dialog.selection == 0  # a default selection is guaranteed  # type: ignore[attr-defined]
    assert dialog.affirmative_id == 1  # type: ignore[attr-defined]
    assert dialog.escape_id == 0  # type: ignore[attr-defined]
    assert frame.editor.GetInsertionPoint() == 6
    assert frame._status_message == 'Jumped to bookmark "Middle"'


def test_go_to_bookmark_without_bookmarks_announces() -> None:
    frame = _build_frame("alpha\nbeta\n", insertion_point=0)
    frame._bookmarks = {}
    frame._wx = type("WX", (), {"ID_OK": 1, "ID_CANCEL": 0})()

    frame.go_to_bookmark()

    assert frame._status_message == "No bookmarks available. Bookmarks are named jump points."


def test_selection_action_specs_adapt_to_scope() -> None:
    frame = _build_frame("alpha beta gamma", insertion_point=0)

    word_labels = [label for label, _action in frame._selection_action_specs("word", None)]
    assert "Upper case" in word_labels
    assert "Sort lines ascending" not in word_labels
    assert "Bold" not in word_labels

    block_labels = [label for label, _action in frame._selection_action_specs("block", "markdown")]
    assert "Sort lines ascending" in block_labels
    assert "Toggle line comment" in block_labels
    assert "Bold" in block_labels


def test_quill_key_selection_actions_runs_chosen_action() -> None:
    frame = _build_frame("alpha beta gamma", insertion_point=0)
    frame.editor.SetSelection(0, 5)  # "alpha"
    frame._active_markup_surface = lambda: None  # type: ignore[method-assign]
    called: list[str] = []
    frame.format_upper_case = lambda: called.append("upper")  # type: ignore[method-assign]

    class _ChoiceDialog:
        def __init__(
            self, _parent: object, _message: str, _caption: str, choices: list[str]
        ) -> None:
            self.choices = choices
            self.selection = -1

        def __enter__(self) -> _ChoiceDialog:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def SetSelection(self, selection: int) -> None:
            self.selection = selection

        def SetAffirmativeId(self, _value: int) -> None:
            return None

        def SetEscapeId(self, _value: int) -> None:
            return None

        def GetStringSelection(self) -> str:
            return "Upper case"

    frame._wx = type(
        "WX",
        (),
        {"SingleChoiceDialog": _ChoiceDialog, "ID_OK": 1, "ID_CANCEL": 0},
    )()
    frame._show_modal_dialog = lambda _dialog, _label: 1  # type: ignore[method-assign]

    frame.quill_key_selection_actions()

    assert called == ["upper"]


def test_quill_key_selection_actions_without_selection_announces() -> None:
    frame = _build_frame("alpha beta gamma", insertion_point=3)
    frame.editor.SetSelection(3, 3)
    frame._wx = type("WX", (), {"ID_OK": 1, "ID_CANCEL": 0})()

    frame.quill_key_selection_actions()

    assert frame._status_message == "Select text first to use selection actions"


def test_previous_misspelling_jumps_to_prior_item() -> None:
    frame = _build_frame(
        "wrng\nhello\nlaterbad\n",
        insertion_point=len("wrng\nhello\nlaterbad"),
    )
    frame._spell_dictionary = lambda: {"hello"}  # type: ignore[method-assign]

    frame.previous_misspelling()

    assert frame.editor.GetInsertionPoint() == 11
    assert frame.editor.selection == (11, 19)
    assert frame._status_message == 'Previous misspelling: "laterbad"'


def test_misspelling_context_text_prefers_sentence() -> None:
    frame = _build_frame("This has wrng spelling. Another sentence here.", insertion_point=0)
    item = Misspelling(word="wrng", start=9, end=13)

    context = frame._misspelling_context_text(frame.editor.GetValue(), item)

    assert context == "This has wrng spelling."


def test_spell_word_for_speech_separates_letters_and_symbols() -> None:
    frame = _build_frame("placeholder", insertion_point=0)

    spoken = frame._spell_word_for_speech("can't-do_it")

    assert spoken == "C, A, N, apostrophe, T, dash, D, O, underscore, I, T"


def test_spellcheck_speech_message_includes_single_suggestion_spelling() -> None:
    frame = _build_frame("placeholder", insertion_point=0)

    message = frame._spellcheck_speech_message("wrng", "wrong")

    assert 'Misspelled word: "wrng".' in message
    assert "Spelling: W, R, N, G." in message
    assert 'Only suggestion: "wrong".' in message
    assert "Suggestion spelling: W, R, O, N, G." in message


def test_find_next_does_not_wrap_when_setting_disabled() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=len("alpha beta alpha"))
    frame._last_find_query = "alpha"
    frame._last_search_options = SearchOptions()
    frame.settings.wrap_find = False

    frame.find_next()

    assert frame._status_message == "No matches found from the current position"


def test_find_next_wraps_when_setting_enabled() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=len("alpha beta alpha"))
    frame._last_find_query = "alpha"
    frame._last_search_options = SearchOptions()
    frame.settings.wrap_find = True

    frame.find_next()

    assert frame.editor.selection == (0, 5)
    assert frame._status_message.endswith("(wrapped)")


def test_sort_lines_descending_uses_undo_preserving_replace_path() -> None:
    frame = _build_frame("a\nc\nb\n", insertion_point=0)
    frame.editor.SetSelection(0, len(frame.editor.GetValue()))
    frame.sort_lines_descending()

    assert frame.editor.GetValue() == "c\nb\na\n"


class _FindEvent:
    """Stand-in for wx FindDialogEvent (GetFindString/GetReplaceString/GetFlags)."""

    def __init__(self, find: str, replace: str = "", flags: int = 1) -> None:
        self._find = find
        self._replace = replace
        self._flags = flags

    def GetFindString(self) -> str:
        return self._find

    def GetReplaceString(self) -> str:
        return self._replace

    def GetFlags(self) -> int:
        return self._flags


_FIND_WX = type(
    "WX",
    (),
    {"FR_DOWN": 1, "FR_WHOLEWORD": 2, "FR_MATCHCASE": 4, "ICON_ERROR": 0, "OK": 0},
)


def test_replace_all_uses_undo_preserving_replace_path() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=0)
    frame._wx = _FIND_WX()
    frame._show_message_box = lambda *_args, **_kwargs: 1  # type: ignore[method-assign]

    # Native Replace dialog "Replace All" button fires EVT_FIND_REPLACE_ALL.
    frame._on_find_replace_all_event(_FindEvent("alpha", "omega"))

    assert frame.editor.GetValue() == "omega beta omega"


def test_replace_text_replaces_next_match() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=0)
    frame._wx = _FIND_WX()

    # Native Replace dialog "Replace" button fires EVT_FIND_REPLACE.
    frame._on_find_replace_event(_FindEvent("alpha", "omega"))

    assert frame.editor.GetValue() == "omega beta alpha"
    assert frame._status_message == "Replaced at position 1"


def test_replace_text_wraps_when_enabled() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=len("alpha beta alpha"))
    frame._wx = _FIND_WX()
    frame.settings.wrap_find = True

    frame._on_find_replace_event(_FindEvent("alpha", "omega"))

    assert frame.editor.GetValue() == "omega beta alpha"
    assert frame._status_message.endswith("(wrapped)")


def test_tab_key_indents_using_configured_mode() -> None:
    frame = _build_frame("alpha", insertion_point=0)
    frame.settings.indent_with_tabs = True
    frame.settings.indent_size = 2
    frame._wx = type("WX", (), {"WXK_INSERT": 45, "WXK_F8": 119, "WXK_TAB": 9})()
    event = _KeyEvent(9)

    frame._on_editor_key_down(event)

    assert frame.editor.GetValue() == "\talpha"


def test_shift_tab_outdents_using_configured_mode() -> None:
    frame = _build_frame("\talpha", insertion_point=1)
    frame.settings.indent_with_tabs = True
    frame.settings.indent_size = 2
    frame._wx = type("WX", (), {"WXK_INSERT": 45, "WXK_F8": 119, "WXK_TAB": 9})()
    event = _KeyEvent(9)
    event._shift = True

    frame._on_editor_key_down(event)

    assert frame.editor.GetValue() == "alpha"


def test_notebook_enter_focuses_active_document() -> None:
    frame = _build_frame("alpha", insertion_point=0)
    frame._activate_tab = lambda _index: None  # type: ignore[method-assign]
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_RETURN": 13,
            "WXK_NUMPAD_ENTER": 13,
            "WXK_SPACE": 32,
            "WXK_TAB": 9,
            "NOT_FOUND": -1,
        },
    )()
    event = _KeyEvent(13)

    frame._on_notebook_key_down(event)

    assert frame.editor.focused is True
    assert frame._status_message.startswith("Focused document ")


def test_profile_choice_label_includes_description() -> None:
    frame = _build_frame("alpha", insertion_point=0)
    profile = PROFILE_DEFINITIONS["essential"]
    label = frame._profile_choice_label(profile)

    assert label.startswith("Essential — ")
    assert profile.description in label


def test_print_document_cancel_reports_cancelled() -> None:
    frame = _build_frame("alpha", insertion_point=0)
    frame._print_data = object()
    frame._build_text_printout = lambda *_args: type(  # type: ignore[method-assign]
        "_Printout",
        (),
        {"Destroy": lambda self: None},
    )()
    frame._show_message_box = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    class _Printer:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return

        def Print(self, *_args: object, **_kwargs: object) -> bool:
            return False

        def GetLastError(self) -> int:
            return 2

    frame._wx = type(
        "WX",
        (),
        {
            "PrintDialogData": staticmethod(lambda data: data),
            "Printer": _Printer,
            "PRINTER_NO_ERROR": 0,
            "PRINTER_CANCELLED": 2,
            "ICON_ERROR": 0,
            "OK": 0,
        },
    )()

    frame.print_document()

    assert frame._status_message == "Printing cancelled"


def test_spellcheck_hint_bell_debounces_same_word(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _build_frame("alpha wrng", insertion_point=6)
    bells: list[str] = []
    frame._wx = type("WX", (), {"Bell": staticmethod(lambda: bells.append("bell"))})()
    frame._last_live_misspelling_feedback = None
    frame._last_live_misspelling_feedback_at = 0.0
    frame._spell_dictionary = lambda: {"alpha"}  # type: ignore[method-assign]
    monkeypatch.setattr(
        main_frame_module,
        "find_next_misspelling",
        lambda *_args, **_kwargs: Misspelling("wrng", 6, 10),
    )
    ticks = iter([10.0, 10.1, 11.2])
    monkeypatch.setattr(main_frame_module.time, "monotonic", lambda: next(ticks))

    frame._announce_spellcheck_hint()
    frame._announce_spellcheck_hint()
    frame._announce_spellcheck_hint()

    assert bells == ["bell", "bell"]


def test_extend_selection_mode_moves_down_with_arrow_key() -> None:
    frame = _build_frame("one\ntwo", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    event = _KeyEvent(317)
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_INSERT": 45,
            "WXK_F8": 119,
            "WXK_LEFT": 314,
            "WXK_RIGHT": 316,
            "WXK_UP": 315,
            "WXK_DOWN": 317,
            "WXK_HOME": 313,
            "WXK_END": 312,
            "WXK_PAGEUP": 366,
            "WXK_PAGEDOWN": 367,
            "WXK_ESCAPE": 27,
        },
    )()

    frame._on_editor_key_down(event)

    assert frame.editor.GetInsertionPoint() == 4
    assert frame.editor.selection == (4, 4)


def test_find_next_keeps_free_movement_when_mode_enabled() -> None:
    frame = _build_frame("alpha beta gamma alpha", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    frame.editor.SetInsertionPoint(1)
    frame._last_find_query = "alpha"
    frame._last_search_options = SearchOptions()

    frame.find_next()

    assert frame.editor.GetInsertionPoint() == 22
    assert frame.editor.selection == (22, 22)


def test_find_text_sets_anchor_and_keeps_free_movement_when_mode_is_on() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=6)
    frame._wx = _FIND_WX()
    frame.toggle_extend_selection_mode(True)
    frame._extend_selection_anchor = None

    # Native Find dialog Find / Find Next fires EVT_FIND / EVT_FIND_NEXT.
    frame._on_find_event(_FindEvent("alpha"))

    assert frame._extend_selection_anchor == 6
    assert frame.editor.selection == (16, 16)
    assert frame._status_message == "Found next at position 12"


def test_extend_selection_commits_on_non_movement_key_action() -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    frame.editor.SetInsertionPoint(5)
    frame.editor.SetSelection(5, 5)
    event = _KeyEvent(ord("X"))
    frame._wx = type(
        "WX",
        (),
        {
            "WXK_INSERT": 45,
            "WXK_F8": 119,
            "WXK_LEFT": 314,
            "WXK_RIGHT": 316,
            "WXK_UP": 315,
            "WXK_DOWN": 317,
            "WXK_HOME": 313,
            "WXK_END": 312,
            "WXK_PAGEUP": 366,
            "WXK_PAGEDOWN": 367,
            "WXK_ESCAPE": 27,
        },
    )()

    frame._on_editor_key_down(event)

    assert event.skipped is True
    assert frame.editor.selection == (0, 5)


def test_prompt_search_uses_web_form_and_maps_values(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame._last_find_query = "alpha"
    frame._wx = object()
    captured: dict[str, object] = {}

    import quill.ui.web_form as web_form_module

    def _fake_show_web_form(parent: object, wx: object, *, title: str, fields: list, **_kw: object):
        captured["title"] = title
        captured["fields"] = fields
        return {
            "query": "needle",
            "mode": "Regular expression",
            "case_sensitive": True,
        }

    monkeypatch.setattr(web_form_module, "show_web_form", _fake_show_web_form)

    result = frame._prompt_search("Find")

    assert result is not None
    query, replacement, options = result
    assert query == "needle"
    assert replacement is None
    assert options.use_regex is True
    assert options.case_sensitive is True
    # The default query is seeded from the last find term.
    query_field = next(f for f in captured["fields"] if f["name"] == "query")
    assert query_field["value"] == "alpha"


def test_prompt_search_returns_none_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame._last_find_query = ""
    frame._search_history = []
    frame._wx = object()
    import quill.ui.web_form as web_form_module

    monkeypatch.setattr(web_form_module, "show_web_form", lambda *a, **k: None)
    assert frame._prompt_search("Find") is None


def test_prompt_search_replacement_includes_replace_field(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame._last_find_query = ""
    frame._search_history = []
    frame._wx = object()
    import quill.ui.web_form as web_form_module

    def _fake(parent: object, wx: object, *, title: str, fields: list, **_kw: object):
        assert any(f["name"] == "replacement" for f in fields)
        return {"query": "a", "replacement": "b", "mode": "Plain text", "case_sensitive": False}

    monkeypatch.setattr(web_form_module, "show_web_form", _fake)
    result = frame._prompt_search("Replace", replacement=True)
    assert result is not None
    query, replacement, _options = result
    assert query == "a"
    assert replacement == "b"


def test_prompt_file_search_uses_modal_ids() -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    captured: dict[str, object] = {}

    class _Dialog:
        def __init__(self, _parent: object, title: str, size: tuple[int, int]) -> None:
            self.title = title
            self.size = size
            self.affirmative_id: int | None = None
            self.escape_id: int | None = None
            captured["dialog"] = self

        def CreateButtonSizer(self, _style: int) -> None:
            return None

        def SetAffirmativeId(self, value: int) -> None:
            self.affirmative_id = value

        def SetEscapeId(self, value: int) -> None:
            self.escape_id = value

        def SetSizerAndFit(self, _sizer: object) -> None:
            return None

        def Destroy(self) -> None:
            return None

    class _Panel:
        def __init__(self, _parent: object) -> None:
            return None

        def SetSizer(self, _sizer: object) -> None:
            return None

    class _BoxSizer:
        def __init__(self, _orientation: int) -> None:
            return None

        def Add(self, _item: object, *_args: object, **_kwargs: object) -> None:
            return None

        def AddSpacer(self, _size: int) -> None:
            return None

    class _FlexGridSizer(_BoxSizer):
        def __init__(self, *_args: object) -> None:
            return None

        def AddGrowableCol(self, _col: int, _proportion: int) -> None:
            return None

    class _StaticText:
        def __init__(self, _parent: object, label: str) -> None:
            self.label = label

    class _DirPickerCtrl:
        def __init__(self, _parent: object, path: str) -> None:
            self.path = path

        def GetPath(self) -> str:
            return self.path

    class _TextCtrl:
        def __init__(self, _parent: object, value: str = "", style: int = 0) -> None:
            self.value = value
            self.style = style

        def GetValue(self) -> str:
            return self.value

        def SetFocus(self) -> None:
            return None

        def Bind(self, _event: object, _handler: object) -> None:
            return None

    class _Choice:
        def __init__(self, _parent: object, choices: list[str]) -> None:
            self.choices = choices
            self.selection = 0

        def SetSelection(self, selection: int) -> None:
            self.selection = selection

        def GetSelection(self) -> int:
            return self.selection

        def GetStringSelection(self) -> str:
            return self.choices[self.selection]

    class _CheckBox:
        def __init__(self, _parent: object, label: str) -> None:
            self.label = label
            self.value = False

        def GetValue(self) -> bool:
            return self.value

        def SetValue(self, value: bool) -> None:
            self.value = value

    wx = type(
        "WX",
        (),
        {
            "Dialog": _Dialog,
            "Panel": _Panel,
            "BoxSizer": _BoxSizer,
            "FlexGridSizer": _FlexGridSizer,
            "StaticText": _StaticText,
            "DirPickerCtrl": _DirPickerCtrl,
            "TextCtrl": _TextCtrl,
            "Choice": _Choice,
            "CheckBox": _CheckBox,
            "VERTICAL": 1,
            "ALIGN_CENTER_VERTICAL": 2,
            "EXPAND": 4,
            "ALL": 8,
            "LEFT": 16,
            "RIGHT": 32,
            "TOP": 64,
            "BOTTOM": 128,
            "ALIGN_RIGHT": 256,
            "OK": 1,
            "CANCEL": 2,
            "ID_OK": 1,
            "ID_CANCEL": 0,
            "TE_PROCESS_ENTER": 512,
            "EVT_TEXT_ENTER": object(),
        },
    )()
    frame._wx = wx

    def _show_modal(dialog: object, label: str) -> int:
        assert label == "Search in Files"
        assert dialog.affirmative_id == wx.ID_OK  # type: ignore[attr-defined]
        assert dialog.escape_id == wx.ID_CANCEL  # type: ignore[attr-defined]
        return wx.ID_CANCEL

    frame._show_modal_dialog = _show_modal  # type: ignore[method-assign]

    result = frame._prompt_file_search(replace=False)

    assert result is None


def test_show_notifications_dialog_uses_close_for_affirmative_and_escape() -> None:
    frame = MainFrame.__new__(MainFrame)

    class _Dialog:
        def __init__(self, _parent: object, title: str, size: tuple[int, int]) -> None:
            self.title = title
            self.size = size
            self.affirmative_id: int | None = None
            self.escape_id: int | None = None

        def SetAffirmativeId(self, value: int) -> None:
            self.affirmative_id = value

        def SetEscapeId(self, value: int) -> None:
            self.escape_id = value

        def SetSizer(self, _sizer: object) -> None:
            return

        def Destroy(self) -> None:
            return

        def EndModal(self, _result: int) -> None:
            return

    class _BoxSizer:
        def __init__(self, _orientation: int) -> None:
            return

        def Add(self, *_args: object, **_kwargs: object) -> None:
            return

        def AddStretchSpacer(self, _proportion: int) -> None:
            return

    class _StaticText:
        def __init__(self, _parent: object, label: str) -> None:
            self.label = label

    class _ListBox:
        def __init__(self, _parent: object, choices: list[str]) -> None:
            self.choices = choices
            self.selection = -1
            self.enabled = True
            self.handlers: dict[int, object] = {}

        def SetSelection(self, selection: int) -> None:
            self.selection = selection

        def GetSelection(self) -> int:
            return self.selection

        def Enable(self, enabled: bool) -> None:
            self.enabled = enabled

        def Bind(self, event_type: int, handler: object) -> None:
            self.handlers[event_type] = handler

    class _Button:
        def __init__(self, _parent: object, id: int | None = None, label: str = "") -> None:
            self.id = id
            self.label = label
            self.enabled = True
            self.handlers: dict[int, object] = {}

        def Enable(self, enabled: bool) -> None:
            self.enabled = enabled

        def Bind(self, event_type: int, handler: object) -> None:
            self.handlers[event_type] = handler

    wx = type(
        "WX",
        (),
        {
            "Dialog": _Dialog,
            "BoxSizer": _BoxSizer,
            "StaticText": _StaticText,
            "ListBox": _ListBox,
            "Button": _Button,
            "VERTICAL": 1,
            "HORIZONTAL": 2,
            "ALL": 4,
            "EXPAND": 8,
            "RIGHT": 16,
            "ID_CLEAR": 1001,
            "ID_CLOSE": 1000,
            "NOT_FOUND": -1,
            "EVT_LISTBOX": 200,
            "EVT_BUTTON": 201,
        },
    )()
    frame._wx = wx
    frame.frame = object()
    frame._notifications = [
        types.SimpleNamespace(
            timestamp="2026-01-01T00:00:00Z",
            category="info",
            message="Done",
        )
    ]
    frame._copy_to_clipboard = lambda _text: True
    frame._set_status = lambda _text: None

    def _show_modal(dialog: object, label: str) -> int:
        assert label == "Notifications"
        assert dialog.affirmative_id == wx.ID_CLOSE  # type: ignore[attr-defined]
        assert dialog.escape_id == wx.ID_CLOSE  # type: ignore[attr-defined]
        return wx.ID_CLOSE

    frame._show_modal_dialog = _show_modal  # type: ignore[method-assign]

    result = frame._show_notifications_dialog()

    assert result == wx.ID_CLOSE


def test_find_previous_sets_anchor_and_keeps_free_movement_when_mode_is_on() -> None:
    frame = _build_frame("alpha beta alpha", insertion_point=len("alpha beta alpha"))
    frame._last_find_query = "alpha"
    frame._last_search_options = SearchOptions()
    frame.toggle_extend_selection_mode(True)
    frame._extend_selection_anchor = None

    frame.find_previous()

    assert frame._extend_selection_anchor == len("alpha beta alpha")
    assert frame.editor.selection == (11, 11)
    assert frame._status_message == "Found previous at position 12"


def test_command_run_commits_pending_extend_selection_for_text_commands() -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    frame.editor.SetInsertionPoint(5)
    frame.editor.SetSelection(5, 5)

    frame._on_command_run("format.bold")

    assert frame.editor.selection == (0, 5)


def test_command_run_does_not_commit_pending_extend_selection_for_search_navigation() -> None:
    frame = _build_frame("alpha beta", insertion_point=0)
    frame.toggle_extend_selection_mode(True)
    frame.editor.SetInsertionPoint(5)
    frame.editor.SetSelection(5, 5)

    frame._on_command_run("edit.find_next")

    assert frame.editor.selection == (5, 5)


def test_format_case_no_selection_targets_current_word() -> None:
    frame = _build_frame("hello world", insertion_point=1)

    frame.format_upper_case()

    assert frame.editor.GetValue() == "HELLO world"
    assert frame._status_message == "Upper case applied to current word"


def test_format_case_no_selection_on_whitespace_noops() -> None:
    frame = _build_frame("hello  world", insertion_point=6)

    frame.format_upper_case()

    assert frame.editor.GetValue() == "hello  world"
    assert frame._status_message == "No current word to transform"


def test_save_all_files_calls_save_file() -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.document.modified = True
    called = {"save": False}

    def fake_save_file() -> None:
        called["save"] = True

    frame.save_file = fake_save_file  # type: ignore[method-assign]
    frame.save_all_files()
    assert called["save"] is True


def test_restore_backup_loads_selected_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frame = _build_frame("hello", insertion_point=0)
    frame.document.path = tmp_path / "note.md"
    backup = tmp_path / "backup.bak"
    backup.write_text("restored text", encoding="utf-8")

    class _Dialog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.selected = 0

        def __enter__(self) -> _Dialog:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def ShowModal(self) -> int:
            return 1

        def GetSelection(self) -> int:
            return self.selected

    monkeypatch.setattr("quill.ui.main_frame.list_backups", lambda _path: [backup])
    frame._wx = type("WX", (), {"ID_OK": 1, "SingleChoiceDialog": _Dialog})()
    frame.restore_backup()
    assert frame.editor.GetValue() == "restored text"


def test_prompt_untrusted_location_uses_single_checkbox_dialog() -> None:
    frame = _build_frame("hello")
    captured: dict[str, object] = {}

    class _RichMessageDialog:
        def __init__(self, _parent: object, message: str, title: str, _style: int) -> None:
            captured["message"] = message
            captured["title"] = title

        def SetOKCancelLabels(self, ok: str, cancel: str) -> bool:
            captured["labels"] = (ok, cancel)
            return True

        def ShowCheckBox(self, label: str) -> None:
            captured["checkbox"] = label

        def IsCheckBoxChecked(self) -> bool:
            return True

        def Destroy(self) -> None:
            return None

    wx = type(
        "WX",
        (),
        {
            "RichMessageDialog": _RichMessageDialog,
            "OK": 1,
            "CANCEL": 2,
            "ICON_WARNING": 4,
            "ID_OK": 1,
            "ID_CANCEL": 0,
        },
    )()
    frame._wx = wx
    frame._show_modal_dialog = lambda _dialog, _label: wx.ID_OK  # type: ignore[method-assign]

    result = frame._prompt_untrusted_location(Path(r"C:\Users\Jeff\Notes"))

    assert result is True
    assert captured["checkbox"] == "Trust this folder for future opens"


def test_prompt_unsaved_changes_action_uses_native_message_dialog() -> None:
    frame = _build_frame("hello")
    captured: dict[str, object] = {}

    class _MessageDialog:
        def __init__(self, _parent: object, message: str, title: str, style: int) -> None:
            captured["message"] = message
            captured["title"] = title
            captured["style"] = style

        def SetYesNoCancelLabels(self, yes: str, no: str, cancel: str) -> bool:
            captured["labels"] = (yes, no, cancel)
            return True

        def Destroy(self) -> None:
            return None

    wx = type(
        "WX",
        (),
        {
            "MessageDialog": _MessageDialog,
            "YES_NO": 4,
            "CANCEL": 8,
            "ICON_WARNING": 16,
            "ID_YES": 1,
            "ID_NO": 2,
            "ID_CANCEL": 0,
        },
    )()
    frame._wx = wx
    # Native wx.MessageDialog handles keys itself; we only own the labels and
    # that ShowModal's result is returned unchanged.
    frame._show_modal_dialog = lambda _dialog, _label: wx.ID_NO  # type: ignore[method-assign]

    result = frame._prompt_unsaved_changes_action(
        "Unsaved changes",
        "You have unsaved changes. Save before closing?",
        "Save",
        "Don't Save",
    )

    assert result == wx.ID_NO
    assert captured["labels"] == ("Save", "Don't Save", "Cancel")


def test_prompt_table_shape_reprompts_invalid_values() -> None:
    frame = _build_frame("hello")
    messages: list[str] = []

    class _TextEntryDialog:
        values = iter(["abc", "3", "0", "4"])

        def __init__(self, _parent: object, _message: str, _title: str, value: str) -> None:
            self.value = next(self.values, value)

        def __enter__(self) -> _TextEntryDialog:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def ShowModal(self) -> int:
            return 1

        def GetValue(self) -> str:
            return self.value

    class _MessageDialog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def __enter__(self) -> _MessageDialog:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def ShowModal(self) -> int:
            return 1

    wx = type(
        "WX",
        (),
        {
            "TextEntryDialog": _TextEntryDialog,
            "MessageDialog": _MessageDialog,
            "VERTICAL": 1,
            "YES_NO": 2,
            "ICON_QUESTION": 4,
            "ICON_ERROR": 8,
            "OK": 16,
            "ID_OK": 1,
            "ID_YES": 2,
        },
    )()
    frame._wx = wx

    def _show_modal(dialog: object, _label: str) -> int:
        if isinstance(dialog, _MessageDialog):
            return wx.ID_YES
        return wx.ID_OK

    def _show_message_box(message: str, caption: str, _style: int) -> int:
        messages.append(f"{caption}: {message}")
        return wx.OK

    frame._show_modal_dialog = _show_modal  # type: ignore[method-assign]
    frame._show_message_box = _show_message_box  # type: ignore[method-assign]

    result = frame._prompt_table_shape()

    assert result == (4, 3, True)
    assert messages == [
        "Insert Table: Rows and columns must be whole numbers.",
        "Insert Table: Rows must be between 1 and 50.",
    ]


def _quick_nav_context() -> dict[str, object]:
    return {
        "headings_by_level": {1: [0], 2: [8]},
        "links": [20],
        "lists": [],
        "list_items": [],
        "tables": [],
        "block_quotes": [],
        "bookmarks": [],
        "code_blocks": [],
    }


def test_open_quick_nav_jumps_to_chosen_item() -> None:
    frame = _build_frame("# Title\n## Section\n[link](url)\n")
    frame._browse_navigation_context = lambda: _quick_nav_context()  # type: ignore[method-assign]
    frame._present_quick_nav = lambda items: items[0]  # type: ignore[method-assign]
    jumps: list[tuple[int, str]] = []
    frame._jump_to = lambda position, message: jumps.append((position, message))  # type: ignore[method-assign]
    frame.open_quick_nav()
    assert jumps
    assert jumps[0][0] == 0


def test_open_quick_nav_cancel_sets_status() -> None:
    frame = _build_frame("# Title\n")
    frame._browse_navigation_context = lambda: _quick_nav_context()  # type: ignore[method-assign]
    frame._present_quick_nav = lambda items: None  # type: ignore[method-assign]
    statuses: list[str] = []
    frame._set_status = lambda message: statuses.append(message)  # type: ignore[method-assign]
    frame.open_quick_nav()
    assert any("cancel" in status.lower() for status in statuses)


def test_open_quick_nav_reports_when_no_elements() -> None:
    frame = _build_frame("plain text without landmarks\n")
    frame._browse_navigation_context = lambda: {  # type: ignore[method-assign]
        "headings_by_level": {},
        "links": [],
        "lists": [],
        "list_items": [],
        "tables": [],
        "block_quotes": [],
        "bookmarks": [],
        "code_blocks": [],
    }
    statuses: list[str] = []
    frame._set_status = lambda message: statuses.append(message)  # type: ignore[method-assign]
    presented: list[object] = []
    frame._present_quick_nav = lambda items: presented.append(items)  # type: ignore[method-assign]
    frame.open_quick_nav()
    assert any("no navigable" in status.lower() for status in statuses)
    assert presented == []


def test_quick_nav_command_mapped_to_navigation_feature() -> None:
    assert feature_for_command("navigate.quick_nav") == "core.navigate"
