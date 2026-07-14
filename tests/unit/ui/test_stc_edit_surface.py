"""The "Notepad++ experiment" surface (wx.stc.StyledTextCtrl / Scintilla).

Contract-level tests (no live wx): the setting round-trips, the combo offers
the surface under the agreed label, the Experimental-tab explainer covers it,
MainFrame dispatches it, and the wrapper shims the four contract gaps the
probe found (see docs/planning/editor-surface-experiments.md, "stc"
section): EVT_TEXT never fires natively,
ChangeValue leaves the buffer modified, SetInsertionPoint drags the anchor,
and CRLF passes through unconverted.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from quill.core.settings import Settings
from quill.core.settings_specs import SETTING_SPECS


def _surface_spec():
    return next(spec for spec in SETTING_SPECS if spec.key == "experimental_editor_surface")


def test_settings_accept_stc_surface() -> None:
    loaded = Settings.from_dict({"experimental_editor_surface": "stc"})
    assert loaded.experimental_editor_surface == "stc"


def test_settings_still_reject_unknown_surfaces() -> None:
    loaded = Settings.from_dict({"experimental_editor_surface": "bogus"})
    assert loaded.experimental_editor_surface == "default"


def test_combo_offers_notepad_plus_plus_experiment() -> None:
    choices = dict(_surface_spec().choices)
    assert "stc" in choices
    assert "Notepad++ experiment" in choices["stc"]


def test_explainer_covers_every_surface_choice() -> None:
    # Every value offered in the combo must have an Experimental-tab
    # explanation; a missing key silently falls back to the "default" text
    # and the user reads the wrong description for the selected surface.
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._build_experimental_explainer)
    for value, _label in _surface_spec().choices:
        assert f'"{value}": (' in source, f"no explainer text for surface {value!r}"


def test_main_frame_dispatches_stc_surface() -> None:
    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._create_document_tab)
    assert 'kind == "stc"' in source


def test_wrapper_shims_the_probed_contract_gaps() -> None:
    import quill.ui.stc_edit_surface as mod

    assert callable(mod.create_stc_editor)
    source = inspect.getsource(mod)
    # EVT_TEXT forwarding (STC never fires wx.EVT_TEXT natively).
    assert "EVT_STC_CHANGE" in source and "wxEVT_TEXT" in source
    # ChangeValue must not report the buffer as modified after a load.
    assert "def ChangeValue" in source and "SetSavePoint" in source
    # SetInsertionPoint must collapse the selection (GotoPos moves the anchor).
    assert "def SetInsertionPoint" in source and "GotoPos" in source
    # LF-only buffer and paste conversion so offsets match GetValue().
    assert "STC_EOL_LF" in source and "SetPasteConvertEndings" in source


def test_stc_surface_exposes_classic_text_diagnostics_without_document_content() -> None:
    import quill.ui.stc_edit_surface as mod

    source = inspect.getsource(mod)
    assert "def accessibility_diagnostic_summary" in source
    assert "WM_GETTEXTLENGTH" in source
    assert "EM_GETSEL" in source
    assert "EM_EXGETSEL" in source
    assert "Document content included: no" in source
    assert "GetValue" not in source[source.index("def accessibility_diagnostic_summary") :]


def test_jaws_bridge_stays_removed_and_the_surface_is_labeled_nvda_only() -> None:
    # 2026-07-03 post-mortem (docs/planning/editor-surface-experiments.md):
    # three JAWS bridging attempts on this
    # surface failed live testing (caret mirror; classic WM_GETTEXT/EM_*
    # answers; those plus the EM_POSFROMCHAR/EM_CHARFROMPOS geometry set) and
    # were rolled back. The negative result is pinned here so the bridge is
    # not casually reintroduced and users are warned off JAWS + stc.
    assert not hasattr(Settings(), "experimental_stc_accessibility_bridge")
    assert all(spec.key != "experimental_stc_accessibility_bridge" for spec in SETTING_SPECS)
    frame_source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    assert "experimental_stc_accessibility_bridge" not in frame_source
    # The Experimental-tab explainer must carry the JAWS warning.
    start = frame_source.index('"stc": (')
    assert "JAWS cannot follow the caret" in frame_source[start : start + 1200]

    import quill.ui.stc_edit_surface as mod

    source = inspect.getsource(mod)
    assert "attach_accessibility_bridge" not in source
    assert "Treat as NVDA-only" in source
