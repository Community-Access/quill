"""Live-wx tests for the Simple File Open dialog (#620) and its routing in
``MainFrame.open_file``.

These tests exercise the dialog against real wx controls on Windows and are
skipped on Linux CI where wxPython is unavailable.
"""

from __future__ import annotations

import tempfile

import pytest
import wx  # type: ignore[import-not-found]  # pytest.importorskip below

pytest.importorskip("wx")  # noqa: E402

from pathlib import Path  # noqa: E402

from quill.ui.simple_open_dialog import (  # noqa: E402
    SimpleOpenDialog,
    SimpleOpenResult,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def sample_dir():
    with tempfile.TemporaryDirectory(prefix="simple_open_") as tmp:
        root = Path(tmp)
        (root / "a.txt").write_text("hello", encoding="utf-8")
        (root / "b.md").write_text("# heading", encoding="utf-8")
        (root / "c.html").write_text("<p>html</p>", encoding="utf-8")
        (root / "d.rtf").write_text("{\\rtf1 hi}", encoding="utf-8")
        (root / "ignored.png").write_text("fake", encoding="utf-8")
        # Subdirectory so the parent-row test has somewhere to go up from.
        sub = root / "subdir"
        sub.mkdir()
        (sub / "deep.txt").write_text("deep", encoding="utf-8")
        yield root


# ---------------------------------------------------------------------------
# Dialog construction and filter behavior
# ---------------------------------------------------------------------------


def test_dialog_controls_have_accessible_names(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            assert dialog.dialog.GetName() == "simple_open"
            assert dialog._path_ctrl.GetName() == "Path"
            assert dialog._filter_choice.GetName() == "File type filter"
            assert dialog._list.GetName() == "Files"
            assert dialog._status.GetName() == "Status"
            assert dialog._btn_up.GetName() == "Up to parent folder"
            assert dialog._btn_hidden.GetName() == "Show hidden files"
            assert dialog._btn_recent.GetName() == "Recent locations"
            assert dialog._btn_fallback.GetName() == "Use Windows dialog instead"
            assert dialog._btn_ok.GetName() == "Open selected file"
            assert dialog._btn_cancel.GetName() == "Cancel"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_supported_filter_excludes_non_text_files(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            labels = dialog._list.GetStrings()
            # Default filter is "Supported files" (txt, md, html, htm, rtf).
            # The .png file must not appear; subdir and txt/md/html/rtf must.
            assert any("a.txt" in label for label in labels)
            assert any("b.md" in label for label in labels)
            assert any("c.html" in label for label in labels)
            assert any("d.rtf" in label for label in labels)
            assert any("subdir" in label for label in labels)
            assert not any("ignored.png" in label for label in labels)
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_all_files_filter_includes_everything(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            # Switch the filter dropdown to "All files" (last entry, index 5).
            dialog._filter_choice.SetSelection(5)
            dialog._on_filter_changed(None)
            labels = dialog._list.GetStrings()
            assert any("ignored.png" in label for label in labels)
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_parent_row_present_when_not_at_filesystem_root(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            labels = dialog._list.GetStrings()
            assert labels[0] == ".. (parent directory)"
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_go_up_navigates_to_parent_directory(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir / "subdir")
        try:
            assert dialog._cwd == sample_dir / "subdir"
            dialog._go_up()
            assert dialog._cwd == sample_dir
            labels = dialog._list.GetStrings()
            assert any("subdir" in label for label in labels)
            assert any("a.txt" in label for label in labels)
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_result_factory_helpers_distinguish_outcomes():
    opened = SimpleOpenResult.opened(Path("/tmp/x.txt"))
    assert opened.path == Path("/tmp/x.txt")
    assert opened.fallback is False
    assert opened.cancelled is False

    fallback = SimpleOpenResult.use_native()
    assert fallback.path is None
    assert fallback.fallback is True
    assert fallback.cancelled is False

    cancelled = SimpleOpenResult.cancel()
    assert cancelled.path is None
    assert cancelled.fallback is False
    assert cancelled.cancelled is True


def test_dialog_rejects_nonexistent_path(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            dialog._path_ctrl.SetValue(str(sample_dir / "does_not_exist.txt"))
            dialog._on_path_enter(None)
            status = dialog._status.GetLabel()
            assert "does not exist" in status
            # Dialog must stay open and the result must still be the cancelled
            # default — pressing Enter on a bad path must not close the dialog.
            assert dialog._result.cancelled is True
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_dialog_accepts_directory_in_path_field(wx_app, sample_dir):
    parent = wx.Frame(None)
    try:
        dialog = SimpleOpenDialog(parent, initial_dir=sample_dir)
        try:
            dialog._path_ctrl.SetValue(str(sample_dir / "subdir"))
            dialog._on_path_enter(None)
            # Compare resolved paths: on CI runners the temp dir is an 8.3 short
            # path (RUNNER~1) while the dialog stores the resolved long form.
            assert dialog._cwd.resolve() == (sample_dir / "subdir").resolve()
            # The subdir contains deep.txt.
            labels = dialog._list.GetStrings()
            assert any("deep.txt" in label for label in labels)
        finally:
            dialog.dialog.Destroy()
    finally:
        parent.Destroy()


# ---------------------------------------------------------------------------
# Routing in MainFrame.open_file
# ---------------------------------------------------------------------------


def test_simple_open_mixin_routes_to_simple_dialog_when_setting_true(wx_app, sample_dir):
    from quill.ui.main_frame_simple_open import SimpleOpenMixin

    parent = wx.Frame(None)
    try:
        calls = {"simple": 0, "native": 0}

        class Stub(SimpleOpenMixin):
            def __init__(self):
                self._wx = wx
                self.frame = parent
                self._last_file_dir = ""
                self.recent_files = []
                from types import SimpleNamespace

                self.settings = SimpleNamespace(use_simple_file_dialog=True, startup_folder="")

            def _prompt_simple_open_dialog(self):
                calls["simple"] += 1
                return None  # user cancelled

            def _prompt_native_open_dialog(self):
                calls["native"] += 1
                return None

            def _show_modal_dialog(self, dialog, label):
                return dialog.ShowModal()

            def _announce(self, msg):
                pass

            def _file_dialog_default_dir(self):
                return ""

        stub = Stub()
        result = stub._prompt_for_open_path()
        assert result is None
        assert calls == {"simple": 1, "native": 0}
    finally:
        parent.Destroy()


def test_simple_open_mixin_routes_to_native_dialog_when_setting_false(wx_app, sample_dir):
    from quill.ui.main_frame_simple_open import SimpleOpenMixin

    parent = wx.Frame(None)
    try:
        calls = {"simple": 0, "native": 0}

        class Stub(SimpleOpenMixin):
            def __init__(self):
                self._wx = wx
                self.frame = parent
                self._last_file_dir = ""
                self.recent_files = []
                from types import SimpleNamespace

                self.settings = SimpleNamespace(use_simple_file_dialog=False, startup_folder="")

            def _prompt_simple_open_dialog(self):
                calls["simple"] += 1
                return None

            def _prompt_native_open_dialog(self):
                calls["native"] += 1
                return None

            def _show_modal_dialog(self, dialog, label):
                return dialog.ShowModal()

            def _announce(self, msg):
                pass

            def _file_dialog_default_dir(self):
                return ""

        stub = Stub()
        result = stub._prompt_for_open_path()
        assert result is None
        assert calls == {"simple": 0, "native": 1}
    finally:
        parent.Destroy()


def test_fallback_routes_to_native_after_simple(wx_app, sample_dir):
    """The ``Use Windows Dialog`` button inside the simple dialog must route
    the next prompt to the native dialog. ``_prompt_for_open_path`` is the
    public dispatcher; a fallback from ``_prompt_simple_open_dialog`` returns
    ``None`` and the dispatcher re-prompts with native. We assert this with a
    stub where the simple dialog returns None (= fallback) on the first call.
    """
    from quill.ui.main_frame_simple_open import SimpleOpenMixin

    parent = wx.Frame(None)
    try:
        calls = {"simple": 0, "native": 0}
        native_seen_after_simple = []

        class Stub(SimpleOpenMixin):
            def __init__(self):
                self._wx = wx
                self.frame = parent
                self._last_file_dir = ""
                self.recent_files = []
                from types import SimpleNamespace

                self.settings = SimpleNamespace(use_simple_file_dialog=True, startup_folder="")

            def _prompt_simple_open_dialog(self):
                calls["simple"] += 1
                # The real ``_prompt_simple_open_dialog`` sets this flag on
                # the instance when the user pressed the fallback button.
                self._simple_dialog_wants_fallback = True
                return None  # user pressed "Use Windows Dialog" -> fallback

            def _prompt_native_open_dialog(self):
                calls["native"] += 1
                native_seen_after_simple.append(calls["simple"])
                return None

            def _show_modal_dialog(self, dialog, label):
                return dialog.ShowModal()

            def _announce(self, msg):
                pass

            def _file_dialog_default_dir(self):
                return ""

        stub = Stub()
        stub._prompt_for_open_path()
        assert calls == {"simple": 1, "native": 1}
        # The native call came after the simple call.
        assert native_seen_after_simple == [1]
    finally:
        parent.Destroy()


# ---------------------------------------------------------------------------
# Setting registration
# ---------------------------------------------------------------------------


def test_use_simple_file_dialog_setting_default_is_false():
    from quill.core.settings import Settings

    assert Settings().use_simple_file_dialog is False


def test_use_simple_file_dialog_setting_round_trips_through_from_dict():
    from quill.core.settings import Settings

    # The loader honors the JSON key.
    loaded_true = Settings.from_dict({"use_simple_file_dialog": True})
    assert loaded_true.use_simple_file_dialog is True

    loaded_false = Settings.from_dict({"use_simple_file_dialog": False})
    assert loaded_false.use_simple_file_dialog is False

    # Unknown keys are ignored, so the default survives.
    loaded_default = Settings.from_dict({})
    assert loaded_default.use_simple_file_dialog is False


def test_use_simple_file_dialog_setting_spec_is_registered():
    from quill.core.settings_registry import find_spec
    from quill.core.settings_specs import SETTING_SPECS

    spec = find_spec("use_simple_file_dialog")
    assert spec is not None
    assert spec.group == "general"
    assert spec.kind == "bool"
    # The label is the user-facing string.
    assert "simple" in spec.label.lower()
    # Confirm the spec is in the global tuple (so the audit can find it).
    assert any(s.key == "use_simple_file_dialog" for s in SETTING_SPECS)
