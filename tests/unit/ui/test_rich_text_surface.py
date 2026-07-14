from quill.ui.rich_text_surface import RichTextSurface, build_render_plan


# --------------------------------------------------------------------------- #
# Pure render-plan tests (wx-free)
# --------------------------------------------------------------------------- #
def test_render_plan_heading() -> None:
    plan = build_render_plan("# Title")
    assert ("heading", 1) in plan
    assert ("text", "Title") in plan


def test_render_plan_bold_run_brackets_text() -> None:
    plan = build_render_plan("**bold**")
    idx = plan.index(("text", "bold"))
    assert plan[idx - 1] == ("bold_on",)
    assert plan[idx + 1] == ("bold_off",)


def test_render_plan_link_wraps_url() -> None:
    plan = build_render_plan("[QUILL](https://x)")
    assert ("url_on", "https://x") in plan
    assert ("url_off",) in plan


def test_render_plan_inserts_newline_between_paragraphs() -> None:
    plan = build_render_plan("one\ntwo")
    assert ("newline",) in plan


def test_render_plan_bullet() -> None:
    plan = build_render_plan("- item")
    assert ("bullet",) in plan


# --------------------------------------------------------------------------- #
# Behaviour tests over a fake wx (no live wx, Linux-safe)
# --------------------------------------------------------------------------- #
class _Recorder:
    def __init__(self) -> None:
        self.ops: list[tuple] = []

    def _record(self, name: str, *args: object) -> None:
        self.ops.append((name, *args))


class _FakeTextCtrl(_Recorder):
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        super().__init__()
        self._value = ""
        self._point = 0
        self._editable = True
        self._sel: tuple[int, int] = (0, 0)
        self._undo: list[str] = []
        self._redo: list[str] = []

    def ChangeValue(self, value: str) -> None:  # noqa: N802
        self._value = value

    def GetValue(self) -> str:  # noqa: N802
        return self._value

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self._point

    def SetInsertionPoint(self, point: int) -> None:  # noqa: N802
        self._point = point

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self._sel

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self._sel = (start, end)

    def GetStringSelection(self) -> str:  # noqa: N802
        start, end = self._sel
        return self._value[start:end]

    def GetRange(self, start: int, end: int) -> str:  # noqa: N802
        return self._value[start:end]

    def Replace(self, start: int, end: int, value: str) -> None:  # noqa: N802
        self._undo.append(self._value)
        self._value = self._value[:start] + value + self._value[end:]

    def CanUndo(self) -> bool:  # noqa: N802
        return bool(self._undo)

    def CanRedo(self) -> bool:  # noqa: N802
        return bool(self._redo)

    def Undo(self) -> None:  # noqa: N802
        if self._undo:
            self._redo.append(self._value)
            self._value = self._undo.pop()

    def Redo(self) -> None:  # noqa: N802
        if self._redo:
            self._undo.append(self._value)
            self._value = self._redo.pop()

    def SetEditable(self, editable: bool) -> None:  # noqa: N802
        self._editable = editable

    def IsEditable(self) -> bool:  # noqa: N802
        return self._editable

    def SetFocus(self) -> None:  # noqa: N802
        self._record("SetFocus")

    def Bind(self, *_args: object) -> None:  # noqa: N802
        pass


class _FakeRichCtrl(_Recorder):
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        super().__init__()
        self._editable = False

    def IsEditable(self) -> bool:  # noqa: N802
        return self._editable

    def SetEditable(self, editable: bool) -> None:  # noqa: N802
        self._editable = editable

    def Clear(self) -> None:  # noqa: N802
        self._record("Clear")

    def BeginFontSize(self, size: int) -> None:  # noqa: N802
        self._record("BeginFontSize", size)

    def BeginBold(self) -> None:  # noqa: N802
        self._record("BeginBold")

    def EndBold(self) -> None:  # noqa: N802
        self._record("EndBold")

    def BeginItalic(self) -> None:  # noqa: N802
        self._record("BeginItalic")

    def EndItalic(self) -> None:  # noqa: N802
        self._record("EndItalic")

    def BeginURL(self, url: str) -> None:  # noqa: N802
        self._record("BeginURL", url)

    def EndURL(self) -> None:  # noqa: N802
        self._record("EndURL")

    def BeginTextColour(self, colour: object) -> None:  # noqa: N802
        self._record("BeginTextColour")

    def EndTextColour(self) -> None:  # noqa: N802
        self._record("EndTextColour")

    def BeginSymbolBullet(self, *_args: object) -> None:  # noqa: N802
        self._record("BeginSymbolBullet")

    def WriteText(self, text: str) -> None:  # noqa: N802
        self._record("WriteText", text)

    def Newline(self) -> None:  # noqa: N802
        self._record("Newline")

    def EndAllStyles(self) -> None:  # noqa: N802
        self._record("EndAllStyles")

    def SetFocus(self) -> None:  # noqa: N802
        self._record("SetFocus")

    def Bind(self, *_args: object) -> None:  # noqa: N802
        pass


class _FakePanel:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def SetSizer(self, *_args: object) -> None:  # noqa: N802
        pass


class _FakeSizer:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def Add(self, *_args: object, **_kwargs: object) -> None:  # noqa: N802
        pass


class _FakeButton:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.label = _kwargs.get("label", "")

    def Bind(self, *_args: object) -> None:  # noqa: N802
        pass

    def SetLabel(self, label: str) -> None:  # noqa: N802
        self.label = label

    def SetName(self, name: str) -> None:  # noqa: N802
        self.name = name


class _FakeStatic(_FakeButton):
    pass


class _FakeNotebook:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._selection = 0

    def AddPage(self, *_args: object, **_kwargs: object) -> None:  # noqa: N802
        pass

    def SetName(self, name: str) -> None:  # noqa: N802
        self._name = name

    def Bind(self, *_args: object) -> None:  # noqa: N802
        pass

    def ChangeSelection(self, index: int) -> None:  # noqa: N802
        self._selection = index

    def GetSelection(self) -> int:  # noqa: N802
        return self._selection


class _FakeRichModule:
    RichTextCtrl = _FakeRichCtrl


class _FakeWx:
    Panel = _FakePanel
    BoxSizer = _FakeSizer
    Button = _FakeButton
    StaticText = _FakeStatic
    Notebook = _FakeNotebook
    TextCtrl = _FakeTextCtrl
    richtext = _FakeRichModule
    VERTICAL = HORIZONTAL = 0
    RIGHT = ALIGN_CENTER_VERTICAL = ALL = EXPAND = LEFT = BOTTOM = 0
    TE_MULTILINE = TE_READONLY = TE_RICH2 = TE_NOHIDESEL = 0
    EVT_BUTTON = EVT_TEXT = EVT_KEY_DOWN = EVT_KEY_UP = 0
    EVT_LEFT_UP = EVT_SET_FOCUS = EVT_CONTEXT_MENU = EVT_NOTEBOOK_PAGE_CHANGED = 0

    @staticmethod
    def Colour(*_args: object) -> object:  # noqa: N802
        return object()


class _Doc:
    text = "# Title\nbody with **bold**"


def _make_surface() -> RichTextSurface:
    changes: list[int] = []
    surface = RichTextSurface(_FakeWx(), _FakePanel(), _Doc(), lambda: changes.append(1))
    surface._changes = changes  # type: ignore[attr-defined]
    return surface


def test_surface_reports_rich_kind() -> None:
    assert _make_surface().surface_kind() == "rich"


def test_get_value_returns_canonical_markdown() -> None:
    surface = _make_surface()
    assert surface.GetValue() == "# Title\nbody with **bold**"


def test_change_value_renders_rich_view() -> None:
    surface = _make_surface()
    surface.ChangeValue("**hi**")
    ops = surface.rich.ops
    assert ("BeginBold",) in ops
    assert ("WriteText", "hi") in ops


def test_toggle_mode_announces_lens() -> None:
    surface = _make_surface()
    assert surface.toggle_mode() == "Markdown lens"
    assert surface.is_text_mode() is True
    assert surface.toggle_mode() == "Rich text lens"
    assert surface.is_text_mode() is False


def test_caret_format_description_heading() -> None:
    surface = _make_surface()
    surface.text_ctrl.SetInsertionPoint(0)
    assert surface.caret_format_description() == "heading level 1"


def test_caret_format_description_bold() -> None:
    surface = _make_surface()
    # Caret inside "**bold**" on the second line.
    markdown = surface.GetValue()
    surface.text_ctrl.SetInsertionPoint(markdown.index("bold") + 1)
    assert surface.caret_format_description() == "bold"


# --------------------------------------------------------------------------- #
# Offset-editing delegates to the canonical Markdown lens (all surfaces: rtf)
# --------------------------------------------------------------------------- #
def test_offset_api_delegates_to_markdown_lens_not_rich_view() -> None:
    # While the read-only rich pane is showing, offset queries must read the
    # canonical text_ctrl so join/move/transform commands stay exact on RTF.
    surface = _make_surface()
    assert surface.is_text_mode() is False  # default: rich pane visible
    surface.text_ctrl.SetSelection(2, 7)
    assert surface.GetSelection() == (2, 7)
    assert surface.GetInsertionPoint() == surface.text_ctrl.GetInsertionPoint()
    assert surface.GetStringSelection() == surface.GetValue()[2:7]


def test_replace_edits_markdown_and_rerenders_rich() -> None:
    surface = _make_surface()
    surface.Replace(0, len(surface.GetValue()), "**hi**")
    assert surface.GetValue() == "**hi**"
    # The rich pane re-rendered the new markup.
    assert ("WriteText", "hi") in surface.rich.ops


def test_undo_redo_route_through_markdown_lens() -> None:
    surface = _make_surface()
    original = surface.GetValue()
    surface.Replace(0, len(original), "changed")
    assert surface.CanUndo() is True
    surface.Undo()
    assert surface.GetValue() == original
