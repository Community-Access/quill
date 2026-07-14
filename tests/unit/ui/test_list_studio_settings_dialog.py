"""Unit test for the List Studio settings dialog's pure option matcher.

The dialog itself is a thin wx shell over the tested core (presets and
StructuredListSettings.to_dict/from_dict); only the option-index helper is pure,
and a regression there would mis-select a control on open.
"""

from __future__ import annotations

from quill.ui.list_studio_settings_dialog import ListStudioSettingsDialog, _index_of


def test_index_of_finds_match() -> None:
    options = [("Alpha", "a"), ("Beta", "b"), ("Gamma", "c")]
    assert _index_of(options, "b", 0) == 1


def test_index_of_returns_default_when_absent() -> None:
    options = [("Alpha", "a"), ("Beta", "b")]
    assert _index_of(options, "missing", 0) == 0


def test_result_scope_defaults_to_initial_scope() -> None:
    # __init__ only stores args (no wx objects until populate), so a placeholder wx
    # module is fine: result_scope starts at the requested scope and is finalized
    # from the radio on OK.
    doc = ListStudioSettingsDialog(
        wx=object(), document_scope_available=True, initial_scope="document"
    )
    assert doc.result_scope == "document"
    app = ListStudioSettingsDialog(wx=object(), initial_scope="app")
    assert app.result_scope == "app"
