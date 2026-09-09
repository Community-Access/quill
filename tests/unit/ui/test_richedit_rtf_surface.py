"""QuillRichEdit — QUILL's one editor surface — with RTF via TOM.

Contract-level tests (no live wx/COM): QuillRichEdit is the default (and only)
surface every document tab is built on, the braille fix is applied from the
Braille-tab settings by default, the factory tags the surface + falls back
safely, RTF I/O uses the Text Object Model (not the crashing EM_STREAM
callback), and the wrapper degrades cleanly without a real HWND. The
end-to-end RTF round-trip is verified on-device (a real RICHEDIT50W +
comtypes), which CI has no handle for.
"""

from __future__ import annotations

import inspect

from quill.core.settings import Settings
from quill.core.settings_specs import SETTING_SPECS


class _FakeSurface:
    """A surface with no real native handle (hwnd 0), for boundary tests."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def GetHandle(self) -> int:  # noqa: N802 - wx API shape
        return 0

    def GetValue(self) -> str:  # noqa: N802
        return self._value


def test_quill_richedit_is_the_one_editor_surface() -> None:
    """Every document tab is built through create_richedit_rtf — no kind ladder.

    The default-surface pin: the surface experiment is decided, so the old
    editor_control_kind / experimental override dispatch must stay gone.
    """
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert "create_richedit_rtf" in source
    for retired in (
        "editor_control_kind",
        "experimental_editor_surface",
        "experimental_acknowledged",
        'kind == "richedit_rtf"',
        "create_stc_editor",
        "create_win32_edit_host",
        "create_rtf_editor",
    ):
        assert retired not in source, f"retired surface dispatch resurfaced: {retired}"


def test_braille_fix_settings_default_on_and_round_trip() -> None:
    # Both halves of the braille fix ship ON by default (#616/#813).
    settings = Settings()
    assert settings.braille_editor_system_edit_fix is True
    assert settings.braille_editor_hide_border is True
    loaded = Settings.from_dict({
        "braille_editor_system_edit_fix": False,
        "braille_editor_hide_border": False,
    })
    assert loaded.braille_editor_system_edit_fix is False
    assert loaded.braille_editor_hide_border is False


def test_braille_fix_specs_live_on_the_braille_tab() -> None:
    specs = {spec.key: spec for spec in SETTING_SPECS}
    fix = specs["braille_editor_system_edit_fix"]
    border = specs["braille_editor_hide_border"]
    assert fix.group == "braille" and border.group == "braille"
    assert "recommended" in fix.label.lower()
    assert "cell" in fix.label.lower() and "dots" in fix.label.lower()
    # The border explainer carries the honest warning about what unchecking does.
    assert "braille cell alignment" in border.label.lower()
    assert "breaks braille cell alignment" in border.description.lower()


def test_main_frame_applies_fix_and_borderless_by_default() -> None:
    """The fix-applied + borderless-by-default pins.

    _create_document_tab must honor both Braille-tab checkboxes, defaulting
    each to True so a missing attribute can never silently disable the fix.
    """
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert '"braille_editor_system_edit_fix", True' in source
    assert '"braille_editor_hide_border", True' in source
    assert "BORDER_NONE" in source
    assert "emulate_system_edit=" in source


def test_border_uncheck_warns_at_decision_time() -> None:
    # Unchecking Hide editor border must warn (it breaks cell alignment) and
    # re-check unless the user explicitly confirms.
    from pathlib import Path

    # MainFrame is composed from main_frame.py plus extracted mixin modules
    # (CQ-1); scan the composite so this pin survives extraction moves.
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(Path("quill/ui").glob("main_frame*.py"))
    )
    start = source.index("def _confirm_show_editor_border(self")
    body = source[start : source.index("\n    def ", start + 1)]
    assert "breaks braille cell alignment" in body
    assert "cell 1" in body
    wiring = source.index('spec.key == "braille_editor_hide_border"')
    window = source[wiring : wiring + 500]
    assert "_confirm_show_editor_border" in window
    assert "SetValue(True)" in window


def test_factory_falls_back_and_tags_surface_kind() -> None:
    import quill.ui.richedit_rtf_surface as mod

    assert callable(mod.create_richedit_rtf)
    source = inspect.getsource(mod)
    assert "TE_RICH2" in source and "TE_NOHIDESEL" in source
    assert "surface_kind = SURFACE_KIND" in source
    # The factory builds RichEditDocument, which *is* a QuillRichEdit plus the
    # paragraph and view capabilities (bullets, line spacing, the point-size
    # ladder, text mode, zoom). Building the subclass here is what stops QUILL
    # being behind its own small sibling QuillLite, which needed them first.
    assert "RichEditDocument(surface)" in source
    assert "return wx_module.TextCtrl(parent, style=style)" in source  # fallback


def test_every_tab_gets_the_paragraph_capabilities_not_just_quilllite() -> None:
    """The wrapper QUILL builds must answer the whole extended contract.

    The rule this pins: a capability the small product has and the editor
    cannot reach is a capability in the wrong place. RichEditDocument is a
    QuillRichEdit, so nothing below the line changes -- but everything above it
    is now available to a QUILL tab as well.
    """
    from quill.ui.richedit_editing import RichEditDocument
    from quill.ui.richedit_rtf_surface import QuillRichEdit

    assert issubclass(RichEditDocument, QuillRichEdit)
    wrapper = RichEditDocument(_FakeSurface())
    for capability in (
        "set_bullets",
        "bullets_at_caret",
        "set_line_spacing",
        "step_font_size",
        "set_alignment_justify",
        "all_headings",
        "heading_level_at_caret",
        "paragraph_text_at",
        "set_text_mode",
        "set_word_wrap",
        "set_zoom",
        "set_document_color",
    ):
        assert callable(getattr(wrapper, capability)), capability
    # And the base contract is untouched: no handle still means a clean error,
    # never a silent no-op.
    for probe in (wrapper.all_headings, wrapper.heading_level_at_caret):
        probe()  # best-effort readbacks: they answer, they do not raise


def test_rtf_uses_the_text_object_model_not_the_crashing_callback() -> None:
    # RTF I/O must go through the TOM (ITextDocument Open/Save), NOT the ctypes
    # EM_STREAM callback that hard-crashes msftedit (see the §8 post-mortem).
    import quill.ui.richedit_rtf_surface as mod

    source = inspect.getsource(mod)
    assert "EM_GETOLEINTERFACE" in source
    assert "ITextDocument" in source
    assert "_TOM_RTF" in source and ".Open(" in source and ".Save(" in source
    assert "comtypes" in source
    # The crashing callback machinery (the ctypes closure + stream pumps) must be
    # gone from the code -- only the docstring may reference EM_STREAM as history.
    assert "WINFUNCTYPE" not in source
    assert "_StreamInPump" not in source and "_stream_in(" not in source


def test_no_handle_raises_cleanly_and_plain_text_still_works() -> None:
    # Without a real HWND/comtypes, RTF I/O raises a clear RichEditRtfError (never
    # a silent no-op, never a crash), and plain-text extraction still works.
    import quill.ui.richedit_rtf_surface as mod

    wrapper = mod.QuillRichEdit(_FakeSurface("plain text here"))
    assert wrapper.rtf_available() is False  # hwnd 0
    caps = wrapper.capabilities()
    assert caps["phase"] == 1 and caps["native_control"] is True
    assert caps["rtf_load"] is False and caps["rtf_save"] is False

    calls = (lambda: wrapper.load_rtf("x.rtf"), lambda: wrapper.save_rtf("x.rtf"), wrapper.get_rtf)
    for call in calls:
        try:
            call()
        except mod.RichEditRtfError:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("RTF I/O with no handle must raise RichEditRtfError")

    ok, detail = wrapper.self_test_rtf_roundtrip()
    assert ok is False and isinstance(detail, str)  # reports, never raises
    assert wrapper.get_plain_text() == "plain text here"


def test_formatting_via_tom_and_boundary_safe() -> None:
    # Phase 2: formatting goes through the TOM ITextFont/ITextPara. Without a real
    # handle the methods raise a clear RichEditRtfError (never a silent no-op).
    import quill.ui.richedit_rtf_surface as mod

    source = inspect.getsource(mod)
    assert ".Font" in source and ".Para" in source and "_TOM_TOGGLE" in source
    assert "_TOM_ALIGNMENT" in source

    wrapper = mod.QuillRichEdit(_FakeSurface())
    for call in (
        wrapper.apply_bold,
        wrapper.apply_italic,
        wrapper.apply_underline,
        lambda: wrapper.set_font_name("Consolas"),
        lambda: wrapper.set_font_size(14),
        lambda: wrapper.set_alignment("center"),
    ):
        try:
            call()
        except mod.RichEditRtfError:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("formatting with no handle must raise RichEditRtfError")
    # An unknown alignment is a clear error, not a silent pass.
    try:
        wrapper.set_alignment("sideways")
    except mod.RichEditRtfError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown alignment must raise")

    # The now-removed 'not yet implemented' error type is gone.
    assert not hasattr(mod, "RichEditRtfUnavailableError")


def test_diagnostic_summary_carries_no_document_content() -> None:
    import quill.ui.richedit_rtf_surface as mod

    summary = mod.QuillRichEdit(_FakeSurface()).accessibility_diagnostic_summary()
    assert "Win32 class name" in summary
    assert "Document content included: no" in summary


def test_phase3_braille_instrument_and_lever_present() -> None:
    # Phase 3: the SES_EMULATESYSEDIT lever + the TOM selection instrument for the
    # cell-2 (#616) and dots-7-8 (#813) braille bugs.
    import quill.ui.richedit_rtf_surface as mod

    source = inspect.getsource(mod)
    assert "SES_EMULATESYSEDIT" in source and "EM_SETEDITSTYLE" in source
    assert "def set_emulate_system_edit" in source
    assert "def selection_diagnostic" in source and ".Selection" in source
    assert "emulate_system_edit" in inspect.getsource(mod.create_richedit_rtf)


def test_phase3_probes_are_safe_without_a_handle() -> None:
    import quill.ui.richedit_rtf_surface as mod

    wrapper = mod.QuillRichEdit(_FakeSurface("hi"))
    assert wrapper.edit_style() == 0
    wrapper.set_emulate_system_edit(True)  # must not raise with no handle
    wrapper.set_emulate_system_edit(False)
    assert "unavailable" in wrapper.selection_diagnostic()
    # The diagnostic surfaces the lever + the #813 localizer.
    summary = wrapper.accessibility_diagnostic_summary()
    assert "SES_EMULATESYSEDIT" in summary and "#813" in summary


def test_retired_surface_overrides_are_dropped_on_load() -> None:
    """The upgrade-force scenario: old overrides cannot hold the fix off.

    A user who had editor_control_kind = "plain" for braille, or the
    experimental combo set to any surface, or an experimental-era
    editor_hide_border False — all land on the promoted default with the fix
    on, and the retired keys are reported for the one-time migration notice.
    """
    from quill.core.settings_migration import (
        from_versioned,
        pop_retired_settings_keys,
    )

    pop_retired_settings_keys()  # clear anything a previous test left behind
    raw = {
        "schema_version": 2,
        "groups": {
            "accessibility": {"editor_control_kind": "plain"},
            "experimental": {
                "experimental_editor_surface": "stc",
                "experimental_editor_surfaces_enabled": True,
                "experimental_richedit_emulate_sysedit": False,
                "editor_hide_border": False,
            },
        },
    }
    loaded = from_versioned(raw)
    assert loaded.braille_editor_system_edit_fix is True
    assert loaded.braille_editor_hide_border is True
    for retired in ("editor_control_kind", "editor_hide_border"):
        assert not hasattr(loaded, retired)
    seen = pop_retired_settings_keys()
    assert "editor_control_kind" in seen and "editor_hide_border" in seen
    assert pop_retired_settings_keys() == []  # consume-once


def test_heading_level_for_font_reads_the_ladder() -> None:
    from quill.ui.richedit_rtf_surface import heading_level_for_font

    # Heading 1-4 have distinct point sizes and must be bold.
    assert heading_level_for_font(20.0, True) == 1
    assert heading_level_for_font(16.0, True) == 2
    assert heading_level_for_font(14.0, True) == 3
    assert heading_level_for_font(12.0, True) == 4
    # Levels 5/6 share the 11pt body size -> not distinguishable, not a heading.
    assert heading_level_for_font(11.0, True) is None
    # Not bold, or a non-ladder size -> body text.
    assert heading_level_for_font(20.0, False) is None
    assert heading_level_for_font(13.0, True) is None
    # Tolerant of tiny float drift from the control.
    assert heading_level_for_font(20.1, True) == 1


def test_next_heading_is_safe_without_a_handle() -> None:
    # Off-Windows / no native handle: heading navigation degrades to None,
    # never raising, so H / Shift+H just reports "no heading".
    from quill.ui.richedit_rtf_surface import QuillRichEdit

    surface = QuillRichEdit.__new__(QuillRichEdit)
    surface.rtf_available = lambda: False  # type: ignore[method-assign]
    assert surface.next_heading(0, reverse=False) is None
    assert surface.next_heading(50, reverse=True) is None


# -- the two fixes PR #1490 isolated ------------------------------------------


class _FakeFont:
    """An ITextFont that behaves the way RICHEDIT50W actually behaves.

    The whole point: assigning ``tomUndefined`` to ``Bold`` is *accepted* and
    changes nothing, which is why the bug was silent for as long as it was.
    """

    #: tom.h. tomTrue is -1; -9999999 is tomUndefined, "leave this alone".
    TRUE, UNDEFINED, TOGGLE = -1, -9999999, -9999998

    def __init__(self, name: str = "Arial", size: float = 11.0, bold: int = 0) -> None:
        self.Name = name
        self.Size = size
        self._bold = bold

    @property
    def Bold(self) -> int:  # noqa: N802 - COM API shape
        return self._bold

    @Bold.setter
    def Bold(self, value: int) -> None:  # noqa: N802
        if value == self.UNDEFINED:
            return  # the control accepts it and does nothing -- the bug
        if value == self.TOGGLE:
            self._bold = 0 if self._bold else self.TRUE
            return
        self._bold = self.TRUE if value == self.TRUE else 0

    @property
    def Weight(self) -> int:  # noqa: N802
        return 700 if self._bold else 400

    Italic = 0
    Underline = 0


class _FakePara:
    Alignment = 0


class _FakeRange:
    def __init__(self, start: int, end: int, font: _FakeFont) -> None:
        self.Start, self.End = start, end
        self.Font = font
        self.Para = _FakePara()

    @property
    def Duplicate(self) -> _FakeRange:  # noqa: N802
        return self

    def Expand(self, _unit: int) -> int:  # noqa: N802
        return 0


class _FakeDocument:
    """Two paragraphs: body text, then a bold 16-point Heading 2."""

    BODY_END = 20

    def __init__(self, caret: int) -> None:
        self._body = _FakeFont(size=11.0, bold=0)
        self._heading = _FakeFont(size=16.0, bold=_FakeFont.TRUE)
        self._caret = caret

    def _font_at(self, offset: int) -> _FakeFont:
        return self._body if offset < self.BODY_END else self._heading

    @property
    def Selection(self) -> _FakeRange:  # noqa: N802
        # A collapsed TOM range reports the formatting of the character BEFORE
        # it -- which is the whole second bug.
        return _FakeRange(self._caret, self._caret, self._font_at(max(0, self._caret - 1)))

    def Range(self, start: int, end: int) -> _FakeRange:  # noqa: N802
        return _FakeRange(start, end, self._font_at(start))


def test_tom_true_is_minus_one_not_tom_undefined() -> None:
    """The constant, and the reason it is not the other one.

    ``_TOM_TRUE`` was -9999999 until 2026-09-08. tom.h calls that
    ``tomUndefined``: "leave this property alone". Assigning it to
    ``ITextFont.Bold`` therefore asked the control to change nothing -- and
    succeeded, silently.
    """
    import quill.ui.richedit_rtf_surface as mod

    assert mod._TOM_TRUE == -1
    assert mod._TOM_UNDEFINED == -9999999
    assert mod._TOM_TRUE != mod._TOM_UNDEFINED


def test_set_heading_actually_applies_the_bold(monkeypatch) -> None:
    """Regression: the heading ladder is size AND bold, and both must land.

    Before the fix this passed the size and dropped the bold, so
    ``heading_level_for_font`` -- which requires bold before it will call a
    paragraph a heading -- could not see the heading QUILL had just made.
    Heading navigation and Describe Formatting both went blind in rich mode.
    """
    import quill.ui.richedit_rtf_surface as mod

    document = _FakeDocument(caret=0)
    monkeypatch.setattr(mod, "_get_text_document", lambda _hwnd: document)

    class _Handled(_FakeSurface):
        def GetHandle(self) -> int:  # noqa: N802
            return 4242

    wrapper = mod.QuillRichEdit(_Handled())
    wrapper.set_heading(1)
    font = document.Selection.Font
    assert font.Size == mod.HEADING_POINT_SIZES[1]
    assert font.Bold != 0, "set_heading applied the size but not the bold"
    assert font.Weight == 700
    assert mod.heading_level_for_font(float(font.Size), bool(font.Bold)) == 1


def test_caret_at_the_head_of_a_heading_describes_that_heading(monkeypatch) -> None:
    """Regression: a collapsed range reports the character BEFORE the caret.

    Standing at the start of a heading therefore described the paragraph above
    it. Screen readers describe the character *after* the caret; so does
    ``caret_format_description`` now.
    """
    import quill.ui.richedit_rtf_surface as mod

    document = _FakeDocument(caret=_FakeDocument.BODY_END)
    monkeypatch.setattr(mod, "_get_text_document", lambda _hwnd: document)

    class _Handled(_FakeSurface):
        def GetHandle(self) -> int:  # noqa: N802
            return 4242

    described = mod.QuillRichEdit(_Handled()).caret_format_description()
    assert "16 point" in described, described
    assert "heading 2" in described, described
    assert "11 point" not in described, "described the paragraph above the caret"
