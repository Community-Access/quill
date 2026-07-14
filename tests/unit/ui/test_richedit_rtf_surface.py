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

    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
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
    assert "QuillRichEdit(surface)" in source
    assert "return wx_module.TextCtrl(parent, style=style)" in source  # fallback


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
