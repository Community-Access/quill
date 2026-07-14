"""QuillRichEdit surface (native Rich Edit wrapper, "richedit_rtf") with RTF via TOM.

Contract-level tests (no live wx/COM): the setting round-trips, the combo offers
the surface, the Experimental-tab explainer covers it, MainFrame dispatches it,
the factory tags the surface + falls back safely, RTF I/O uses the Text Object
Model (not the crashing EM_STREAM callback), and the wrapper degrades cleanly
without a real HWND. The end-to-end RTF round-trip is verified on-device (a real
RICHEDIT50W + comtypes), which CI has no handle for. See
docs/planning/editor-surface-experiments.md §8.
"""

from __future__ import annotations

import inspect

from quill.core.settings import Settings
from quill.core.settings_specs import SETTING_SPECS


def _surface_spec():
    return next(spec for spec in SETTING_SPECS if spec.key == "experimental_editor_surface")


class _FakeSurface:
    """A surface with no real native handle (hwnd 0), for boundary tests."""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def GetHandle(self) -> int:  # noqa: N802 - wx API shape
        return 0

    def GetValue(self) -> str:  # noqa: N802
        return self._value


def test_settings_accept_richedit_rtf_surface() -> None:
    loaded = Settings.from_dict({"experimental_editor_surface": "richedit_rtf"})
    assert loaded.experimental_editor_surface == "richedit_rtf"


def test_settings_still_reject_unknown_surfaces() -> None:
    loaded = Settings.from_dict({"experimental_editor_surface": "bogus"})
    assert loaded.experimental_editor_surface == "default"


def test_combo_offers_quill_richedit_surface() -> None:
    choices = dict(_surface_spec().choices)
    assert "richedit_rtf" in choices
    assert "QuillRichEdit" in choices["richedit_rtf"]


def test_explainer_covers_every_surface_choice() -> None:
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._build_experimental_explainer)
    for value, _label in _surface_spec().choices:
        assert f'"{value}": (' in source, f"no explainer text for surface {value!r}"


def test_main_frame_dispatches_richedit_rtf_surface() -> None:
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert 'kind == "richedit_rtf"' in source
    assert "create_richedit_rtf" in source


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


def test_emulate_sysedit_setting_round_trips() -> None:
    loaded = Settings.from_dict({"experimental_richedit_emulate_sysedit": True})
    assert loaded.experimental_richedit_emulate_sysedit is True
    assert Settings().experimental_richedit_emulate_sysedit is False  # off by default


def test_main_frame_gates_and_passes_the_emulate_lever() -> None:
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert "experimental_richedit_emulate_sysedit" in source
    assert "emulate_system_edit=" in source
    assert "acknowledged and" in source  # only when the experimental gates are on


def test_everything_is_gated_behind_both_experimental_flags() -> None:
    # The whole QuillRichEdit surface (and therefore all of its RTF/formatting/
    # braille capabilities, which only exist once it is instantiated) is only
    # activated when BOTH experimental gates are acknowledged -- so nothing here
    # can reach a user who has not opted into experimental editor surfaces.
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert "experimental_acknowledged" in source
    assert "experimental_editor_surfaces_enabled" in source
    # The surface override (incl. richedit_rtf) is applied only under `acknowledged`.
    assert "if acknowledged and override" in source
