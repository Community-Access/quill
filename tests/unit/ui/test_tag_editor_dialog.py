"""The Tag Editor dialog: it builds, it is accessible, and values round-trip.

The accessibility assertions here are not decoration. Each one guards a
failure a sighted developer cannot see and a screen-reader user cannot work
around: a label paired with the wrong control, a field with no name, two
controls fighting over one access key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech.audio_tags import (  # noqa: E402
    GROUPS,
    TAG_FIELDS,
    AudioTags,
    CoverArt,
)
from quill.ui.audio_studio.tag_editor import (  # noqa: E402
    CoverPagePanel,
    TagEditorDialog,
    TagPagePanel,
)

_PNG_1X1 = bytes.fromhex(
    # A real 1x1 red PNG. The hex that used to sit here had a truncated
    # IDAT, so wx refused it and the cover-art tests popped an "Unknown
    # image data format" box -- which is how that modal was found.
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c63f8cfc0f01f00050001ff89993d1d0000000049454e44ae426082"
)


@pytest.fixture(scope="module")
def wx_app():
    from quill.ui.app_context_help import ensure_help_provider

    app = wx.App()
    # Without a wx.HelpProvider every SetHelpText in the app stores nothing
    # and GetHelpText answers "" -- so the help assertions below would pass
    # vacuously on a run that had one and fail on a run that did not.
    ensure_help_provider(wx)
    yield app
    app.Destroy()


@pytest.fixture
def dialog(wx_app):
    tags = AudioTags()
    tags.set("album", "The Book")
    tags.set("publisher", "Example Press")
    tags.set("track", "3/12")
    frame = wx.Frame(None)
    dlg = TagEditorDialog(frame, tags, filename="book.mp3")
    yield dlg
    dlg.Destroy()
    frame.Destroy()


class TestBuild:
    def test_every_field_has_a_control(self, dialog) -> None:
        for tag_field in TAG_FIELDS:
            assert tag_field.key in dialog.controls, f"{tag_field.key} has no control"

    def test_there_is_a_page_per_group_plus_cover_art(self, dialog) -> None:
        assert set(dialog.pages) == {key for key, _label in GROUPS} | {"cover"}

    def test_a_boolean_field_is_a_checkbox(self, dialog) -> None:
        assert isinstance(dialog.controls["compilation"], wx.CheckBox)

    def test_a_multiline_field_is_a_box(self, dialog) -> None:
        assert dialog.controls["lyrics"].GetWindowStyle() & wx.TE_MULTILINE

    def test_a_pair_field_has_a_number_and_a_total(self, dialog) -> None:
        assert dialog.controls["track"].GetValue() == "3"
        assert dialog.totals["track"].GetValue() == "12"


class TestAccessibility:
    def test_every_control_has_help_text(self, dialog) -> None:
        """F1 must answer on every field, or GATE-STUDIO-HELP has a hole."""
        for key, ctrl in dialog.controls.items():
            assert ctrl.GetHelpText(), f"{key} has no help text"

    def test_every_control_names_itself(self, dialog) -> None:
        """VoiceOver reads a control only by its own accessible name."""
        for key, ctrl in dialog.controls.items():
            assert ctrl.GetName() not in {"", "panel", "control"}, f"{key} is unnamed"

    def test_mnemonics_are_unique_within_each_page(self, dialog) -> None:
        """Windows cycles focus between duplicates instead of pressing."""
        for group, _label in GROUPS:
            letters: list[str] = []
            for child in dialog.pages[group].GetChildren():
                label = child.GetLabel()
                if "&" in label:
                    letters.append(label[label.index("&") + 1].lower())
            assert len(letters) == len(set(letters)), f"duplicate mnemonic on {group}"

    def test_each_label_is_created_before_its_control(self, dialog) -> None:
        """A11Y-Z-ORDER: readers pair a label with the control after it."""
        for group, _label in GROUPS:
            children = list(dialog.pages[group].GetChildren())
            for i, child in enumerate(children):
                if isinstance(child, wx.StaticText) and child.GetLabel().endswith(":"):
                    assert i + 1 < len(children), f"{child.GetLabel()} labels nothing"
                    assert not isinstance(children[i + 1], wx.StaticText)

    def test_no_page_groups_its_fields_in_a_static_box(self, dialog) -> None:
        """IsDialogMessage scopes mnemonics to the enclosing StaticBox."""
        for page in dialog.pages.values():
            for child in page.GetChildren():
                assert not isinstance(child, wx.StaticBox)

    def test_the_ok_and_cancel_buttons_carry_no_mnemonic(self, dialog) -> None:
        """Enter and Escape already serve them; the letters are worth more elsewhere."""
        for button_id in (wx.ID_OK, wx.ID_CANCEL):
            button = dialog.FindWindowById(button_id)
            assert button is not None
            assert "&" not in button.GetLabel()


class TestRoundTrip:
    def test_values_seed_the_controls_and_come_back_out(self, dialog) -> None:
        assert dialog.controls["album"].GetValue() == "The Book"
        dialog.controls["album"].SetValue("Renamed")
        dialog.controls["copyright"].SetValue("2026 Example Press")
        result = dialog.result()
        assert result.get("album") == "Renamed"
        assert result.get("copyright") == "2026 Example Press"
        assert result.get("publisher") == "Example Press"

    def test_a_pair_field_rejoins_as_number_of_total(self, dialog) -> None:
        dialog.controls["disc"].SetValue("1")
        dialog.totals["disc"].SetValue("2")
        assert dialog.result().get("disc") == "1/2"

    def test_a_pair_with_no_total_keeps_just_the_number(self, dialog) -> None:
        dialog.controls["disc"].SetValue("1")
        dialog.totals["disc"].SetValue("")
        assert dialog.result().get("disc") == "1"

    def test_a_checkbox_round_trips(self, dialog) -> None:
        dialog.controls["compilation"].SetValue(True)
        assert dialog.result().get("compilation") == "1"
        dialog.controls["compilation"].SetValue(False)
        assert dialog.result().get("compilation") == ""

    def test_the_tags_passed_in_are_never_mutated(self, wx_app) -> None:
        tags = AudioTags()
        tags.set("album", "Original")
        frame = wx.Frame(None)
        dlg = TagEditorDialog(frame, tags, filename="book.mp3")
        try:
            dlg.controls["album"].SetValue("Changed")
            dlg.result()
            assert tags.get("album") == "Original"
        finally:
            dlg.Destroy()
            frame.Destroy()


class TestCoverPage:
    def test_absent_art_is_described(self, wx_app) -> None:
        frame = wx.Frame(None)
        try:
            page = CoverPagePanel(frame, None)
            assert "No cover art" in page.summary.GetLabel()
            assert page.cover is None
        finally:
            frame.Destroy()

    def test_present_art_is_described_in_words_not_only_shown(self, wx_app) -> None:
        frame = wx.Frame(None)
        try:
            page = CoverPagePanel(frame, CoverArt(data=_PNG_1X1, mime="image/png"))
            assert "PNG" in page.summary.GetLabel()
            assert "bytes" in page.summary.GetLabel()
        finally:
            frame.Destroy()

    def test_setting_art_updates_the_summary_and_says_so(self, wx_app) -> None:
        frame = wx.Frame(None)
        spoken: list[str] = []
        try:
            page = CoverPagePanel(frame, None, announce=spoken.append)
            page.set_cover(CoverArt(data=_PNG_1X1, mime="image/png"))
            assert page.cover is not None
            assert "PNG" in page.summary.GetLabel()
            assert spoken and spoken[0].startswith("Cover art loaded")
        finally:
            frame.Destroy()

    def test_removing_art_clears_it_and_says_so(self, wx_app) -> None:
        frame = wx.Frame(None)
        spoken: list[str] = []
        try:
            page = CoverPagePanel(
                frame,
                CoverArt(data=_PNG_1X1, mime="image/png"),
                announce=spoken.append,
            )
            page.remove_cover()
            assert page.cover is None
            assert "No cover art" in page.summary.GetLabel()
            assert spoken == ["Cover art removed."]
        finally:
            frame.Destroy()

    def test_removing_nothing_says_so_rather_than_pretending(self, wx_app) -> None:
        frame = wx.Frame(None)
        spoken: list[str] = []
        try:
            page = CoverPagePanel(frame, None, announce=spoken.append)
            page.remove_cover()
            assert spoken == ["There is no cover art to remove."]
        finally:
            frame.Destroy()

    def test_every_button_explains_itself(self, wx_app) -> None:
        frame = wx.Frame(None)
        try:
            page = CoverPagePanel(frame, None)
            buttons = [c for c in page.GetChildren() if isinstance(c, wx.Button)]
            assert len(buttons) == 3
            for button in buttons:
                assert button.GetHelpText(), f"{button.GetLabel()} has no help"
        finally:
            frame.Destroy()

    def test_the_cover_edit_reaches_the_dialog_result(self, wx_app) -> None:
        frame = wx.Frame(None)
        dlg = TagEditorDialog(frame, AudioTags(), filename="book.mp3")
        try:
            dlg.cover_page.set_cover(CoverArt(data=_PNG_1X1, mime="image/png"))
            result = dlg.result()
            assert result.cover is not None
            assert result.cover.data == _PNG_1X1
        finally:
            dlg.Destroy()
            frame.Destroy()


class TestPagePanelOnItsOwn:
    """A page owns its controls, so it can be used without the dialog."""

    def test_seed_and_collect_round_trip(self, wx_app) -> None:
        frame = wx.Frame(None)
        try:
            page = TagPagePanel(frame, "publishing")
            tags = AudioTags()
            tags.set("composer", "A Composer")
            page.seed(tags)
            assert page.controls["composer"].GetValue() == "A Composer"
            page.controls["isrc"].SetValue("GBAYE0000001")
            out = AudioTags()
            page.collect(out)
            assert out.get("isrc") == "GBAYE0000001"
            assert out.get("composer") == "A Composer"
        finally:
            frame.Destroy()


class TestStandaloneRoute:
    def test_the_standalone_opener_exists_and_is_wired(self) -> None:
        """GATE-REACH: a surface reached only from another dialog is unfindable."""
        import inspect

        from quill.ui import audio_studio
        from quill.ui.audio_studio.tag_editor import open_tags_in_editor

        assert callable(open_tags_in_editor)
        assert "open_tags_in_editor" in inspect.getsource(audio_studio)

    def test_the_titles_resolve_in_the_studio_help_catalogue(self) -> None:
        """GATE-STUDIO-HELP: a window with no authored purpose fails the build."""
        from quill.core.audio_studio import surface_help

        assert surface_help.is_known_title("Tag Editor")
        assert surface_help.is_known_title("Edit chapter")


class TestStandaloneStudio:
    """The standalone app's front door is a menu bar, and it ships its own deps."""

    def test_the_menu_offers_the_tag_editor(self) -> None:
        import inspect

        from quill.apps import studio

        source = inspect.getsource(studio)
        assert "open_tags_in_editor" in source
        assert "Edit &Tags Only..." in source

    def test_the_library_tree_offers_it_too(self) -> None:
        """The place somebody is already standing when they want it."""
        import inspect

        from quill.apps import studio

        assert 'menu.Append(wx.ID_ANY, "Edit &Tags Only...")' in inspect.getsource(studio)

    def test_the_standalone_build_declares_and_bundles_mutagen(self) -> None:
        """A tag editor in a build with no mutagen is a window that cannot save.

        Two separate holes: the extra was never declared, and every mutagen
        import in this codebase is lazy and inside a function -- exactly what
        PyInstaller's tracer cannot follow, which is why the spec hand-collects
        PyNaCl and yt-dlp already.
        """

        root = Path(__file__).resolve().parents[3]
        pyproject = (root / "standalone/studio/pyproject.toml").read_text(encoding="utf-8")
        assert "quill[ui,mp3]" in pyproject
        spec = (root / "standalone/studio/quill-audio-studio.spec").read_text(encoding="utf-8")
        assert 'collect_all("mutagen")' in spec
        assert "mutagen_hiddenimports" in spec
        assert "mutagen_binaries" in spec
        assert "mutagen_datas" in spec
