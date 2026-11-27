"""The List Speech Templates window: keyboard routes, names and one sentence per action."""

from __future__ import annotations

import pytest

from quill.core.list_speech.store import load_library

wx = pytest.importorskip("wx")


@pytest.fixture
def dialog(wx_session_app, tmp_path, monkeypatch):
    from quill.core.list_speech import store
    from quill.ui import list_speech_dialog as mod

    monkeypatch.setattr(store, "library_path", lambda: tmp_path / "t.json")
    monkeypatch.setattr(mod, "load_library", lambda: store.load_library(tmp_path / "t.json"))
    monkeypatch.setattr(
        mod, "save_library", lambda lib: store.save_library(lib, tmp_path / "t.json")
    )
    said: list[str] = []
    window = mod.ListSpeechDialog(None, list_type="github_issues", announce_cb=said.append)
    yield window, said, tmp_path / "t.json"
    window.dialog.Destroy()


def test_every_control_has_an_accessible_name(dialog) -> None:
    window, _said, _path = dialog
    for control in (
        window._types,
        window._source,
        window._fields,
        window._picker,
        window._separator,
        window._preview,
        window._fallback,
    ):
        assert control.GetName() and control.GetName() != "listBox"


def test_move_down_says_where_the_field_landed(dialog) -> None:
    window, said, _path = dialog
    window._fields.SetSelection(0)
    window._move(1)
    assert said[-1] == "Number moved to position 2 of 5."
    assert window._fields.GetSelection() == 1
    assert window._preview.GetValue().startswith("Login fails")


def test_choosing_a_preset_and_using_it_is_saved(dialog) -> None:
    window, said, path = dialog
    window._source.SetSelection(window._sources.index("builtin:brief"))
    window._on_source(None)
    assert said[-1] == "Brief chosen."
    window._use_it(False)
    assert said[-1] == "Now used for GitHub issues."
    library, notice = load_library(path)
    assert library.assignments["github_issues"] == "builtin:brief" and notice == ""


def test_labels_toggle_changes_the_preview(dialog) -> None:
    window, said, _path = dialog
    window._source.SetSelection(window._sources.index("builtin:detailed"))
    window._on_source(None)
    window._labels.SetValue(False)
    window._on_labels(None)
    assert said[-1] == "Field labels off." and "by octocat" not in window._preview.GetValue()


def test_removed_field_is_named_not_blank(dialog) -> None:
    from dataclasses import replace

    window, _said, _path = dialog
    state = window._state
    window._state = replace(state, draft=replace(state.draft, fields=(*state.draft.fields, "gone")))
    window._refresh()
    assert "gone" in window._note.GetLabel() and "gone (not offered)" in window._fields.GetStrings()
