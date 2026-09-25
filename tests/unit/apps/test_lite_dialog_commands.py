"""The commands that open a window: what they hand it, and what they do after.

Eighteen handlers, and until 2026-09-11 every one of them was shape-only --
known to exist, never exercised. They are the hardest group to reach and the
one with the most places to hide a bug, because each is three separable things:

1. **What the window is handed.** Preferences gets the settings object and the
   feature areas; Spelling Suggestions gets the suggestions for the word the
   caret is *in*, not one starting under it; Go To Anything gets headings
   converted to line numbers. Hand over the wrong thing and the window is
   perfectly built and useless.
2. **What happens on cancel.** Nothing should -- and "nothing" includes not
   saving, not rebuilding menus, and not announcing. A command that reports
   success after Escape is worse than one that fails.
3. **What happens on OK.** The save, the reload, the rebuild, the sentence.

The seam is ``DialogRecorder`` (see ``conftest.py``): every dialog entry point
is replaced by a stub that records how it was called and answers **cancel**
unless a test says otherwise. Cancel-by-default is deliberate; it is the branch
people forget to write and forget to test.
"""

from __future__ import annotations

import pytest
import wx

# --------------------------------------------------------------------------- #
# Read-only windows: About, Shortcuts, Describe Character
# --------------------------------------------------------------------------- #


def test_about_names_the_app_the_version_and_where_the_data_lives(lite_window, lite_dialogs):
    """The data folder is the useful half.

    "Where did my settings go" and "where is my recovered work" are the two
    questions this window exists to answer, and neither is guessable.
    """
    from quill.core.lite import APP_NAME, APP_VERSION

    win = lite_window("hello")
    win.cmd_about()

    title, body = lite_dialogs.args_for("show_text_window")[1:3]
    assert title == f"About {APP_NAME}"
    assert APP_VERSION in body
    assert str(win.app.data_dir) in body


def test_about_gives_the_support_address(lite_window, lite_dialogs):
    """Where to write is not guessable either, and About is where people look
    for it first. Every app in the family prints it here."""
    from quill.core.support_message import SUPPORT_EMAIL

    win = lite_window("hello")
    win.cmd_about()
    assert SUPPORT_EMAIL in lite_dialogs.args_for("show_text_window")[2]


def test_get_help_from_support_writes_as_quilllite(lite_window, monkeypatch):
    """The small product has to name itself.

    Whoever answers should never have to guess which of nine products somebody
    was running, and QUILL Lite is the one most likely to be somebody's first --
    and only -- Quill app.
    """
    import quill.ui.support_dialog as support_dialog
    from quill.core.lite import APP_NAME, APP_VERSION

    calls: list[dict] = []
    monkeypatch.setattr(
        support_dialog,
        "open_support_message",
        lambda host, **kwargs: calls.append(kwargs),
    )

    win = lite_window("hello")
    win.cmd_get_help_from_support()

    assert calls == [{"source_app": APP_NAME, "app_version": APP_VERSION}]


def test_about_says_quilllite_is_a_companion_rather_than_a_replacement(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.cmd_about()
    body = lite_dialogs.args_for("show_text_window")[2]
    assert "companion" in body
    assert "not a replacement" in body


def test_shortcuts_lists_what_is_actually_bound(lite_window, lite_dialogs):
    """Built from the live keymap, so a rebound key shows its new chord.

    A shortcut window listing the defaults would be wrong for exactly the people
    who most need it: the ones who changed a key because the default did not
    work for them.
    """
    win = lite_window("hello")
    win.app.keymap = {"cmd_copy": "Ctrl+Insert"}
    win.cmd_shortcuts()

    title, body = lite_dialogs.args_for("show_text_window")[1:3]
    assert title == "Keyboard shortcuts"
    assert "Ctrl+Insert" in body


def test_describe_character_detail_opens_a_window_on_the_character_at_the_caret(
    lite_window, lite_dialogs
):
    """A window rather than a sentence, because the detail is several lines and
    speech cannot be re-read -- a window can be arrowed through."""
    win = lite_window("aéb", cursor=1)
    win.cmd_describe_character_detail()

    title, body = lite_dialogs.args_for("show_text_window_marks")[1:3]
    assert title == "Character at the cursor"
    assert "e9" in body.lower() or "233" in body
    assert win.control.focused is True


def test_context_help_asks_the_shared_engine(lite_window, lite_dialogs):
    """F1 is one engine for all nine apps; QUILL Lite only has to route to it."""
    win = lite_window("hello")
    win.cmd_context_help()
    assert lite_dialogs.args_for("show_help") == (win,)


# --------------------------------------------------------------------------- #
# Preferences
# --------------------------------------------------------------------------- #


def test_preferences_is_handed_the_settings_the_areas_and_the_profiles(lite_window, lite_dialogs):
    from quill.apps.lite_preferences import PreferencesResult
    from quill.core.lite.features import AREAS, PROFILES

    win = lite_window("hello")
    lite_dialogs.answer("edit_preferences", PreferencesResult(False, False))
    win.cmd_preferences()

    kwargs = lite_dialogs.kwargs_for("edit_preferences")
    assert lite_dialogs.args_for("edit_preferences")[1] is win.app.settings
    assert list(kwargs["areas"]) == list(AREAS)
    assert list(kwargs["profiles"]) == list(PROFILES)
    assert callable(kwargs["announce"])


def test_preferences_cancelled_saves_nothing_and_says_nothing(lite_window, lite_dialogs):
    from quill.apps.lite_preferences import PreferencesResult

    win = lite_window("hello")
    lite_dialogs.answer("edit_preferences", PreferencesResult(False, False))
    before = (win.app.saved_settings, win.app.rebuilt_menus)
    win.cmd_preferences()
    assert (win.app.saved_settings, win.app.rebuilt_menus) == before
    assert win.announcements == []


def test_preferences_saved_reapplies_without_rebuilding_the_menus(lite_window, lite_dialogs):
    """A changed setting costs a re-apply. A changed *feature set* costs a menu
    rebuild, which is much more expensive -- so the two are reported apart."""
    from quill.apps.lite_preferences import PreferencesResult

    win = lite_window("hello")
    lite_dialogs.answer("edit_preferences", PreferencesResult(True, False))
    win.cmd_preferences()

    assert win.app.saved_settings == 1
    assert win.app.reapplied == 1
    assert win.app.rebuilt_menus == 0
    assert win.announcements[-1] == "Preferences saved"


def test_a_changed_feature_profile_rebuilds_every_menu_and_says_so(lite_window, lite_dialogs):
    from quill.apps.lite_preferences import PreferencesResult

    win = lite_window("hello")
    lite_dialogs.answer("edit_preferences", PreferencesResult(True, True))
    win.cmd_preferences()

    assert win.app.saved_features == 1
    assert win.app.rebuilt_menus == 1
    assert "menus have been rebuilt" in win.announcements[-1]


# --------------------------------------------------------------------------- #
# Customize Features
# --------------------------------------------------------------------------- #


def test_customize_features_cancelled_changes_nothing(lite_window, lite_dialogs):
    win = lite_window("hello")
    lite_dialogs.answer("AppFeaturesDialog", _dialog_answering(False))
    before = (win.app.saved_features, win.app.rebuilt_menus)
    win.cmd_customize_features()
    assert (win.app.saved_features, win.app.rebuilt_menus) == before
    assert win.announcements == []


def test_customize_features_saved_writes_both_files_and_rebuilds(lite_window, lite_dialogs):
    """Both files: a profile can move a *setting* as well as a set of areas, and
    the dialog only ever writes to the objects -- persisting is the caller's."""
    win = lite_window("hello")
    lite_dialogs.answer("AppFeaturesDialog", _dialog_answering(True))
    win.cmd_customize_features()

    assert win.app.saved_features == 1
    assert win.app.saved_settings == 1
    assert win.app.rebuilt_menus == 1
    assert "Features saved" in win.announcements[-1]


def test_customize_features_is_shown_not_show_modal(lite_window, lite_dialogs):
    """The shipped bug this pins: it was called with the wrong method name.

    ``show_modal`` raised AttributeError inside the menu handler, where wx
    swallows it -- so Customize Features was a menu item that did nothing at
    all, silently. A stand-in that only has ``show`` catches a regression.
    """
    win = lite_window("hello")
    answered = _dialog_answering(False)
    lite_dialogs.answer("AppFeaturesDialog", answered)
    win.cmd_customize_features()
    assert answered.shown == 1


def _dialog_answering(result: bool):
    """A dialog object whose only method is ``show()`` -- see the test above."""

    class _Dialog:
        shown = 0

        def show(self) -> bool:
            type(self).shown += 1
            return result

    return _Dialog()


# --------------------------------------------------------------------------- #
# Keyboard Manager
# --------------------------------------------------------------------------- #


def test_keyboard_manager_is_handed_the_live_keymap(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.app.keymap = {"cmd_copy": "Ctrl+C"}
    lite_dialogs.answer("KeymapEditorDialog", _keymap_dialog(None))
    win.cmd_keyboard_manager()
    assert lite_dialogs.kwargs_for("KeymapEditorDialog")["keymap"] is win.app.keymap


def test_keyboard_manager_cancelled_leaves_the_keys_alone(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.app.keymap = {"cmd_copy": "Ctrl+C"}
    lite_dialogs.answer("KeymapEditorDialog", _keymap_dialog(None))
    win.cmd_keyboard_manager()
    assert win.app.keymap == {"cmd_copy": "Ctrl+C"}
    assert win.app.saved_keymaps == []
    assert win.announcements == []


def test_saving_keys_replaces_the_keymap_and_says_the_menus_were_rebuilt(lite_window, lite_dialogs):
    """Every window, not just this one.

    A menu bar showing one key while its neighbour shows another is a worse bug
    than the stale key it would be replacing.
    """
    win = lite_window("hello")
    lite_dialogs.answer("KeymapEditorDialog", _keymap_dialog({"cmd_copy": "Ctrl+Insert"}))
    win.cmd_keyboard_manager()

    assert win.app.keymap == {"cmd_copy": "Ctrl+Insert"}
    assert win.app.saved_keymaps == [{"cmd_copy": "Ctrl+Insert"}]
    assert "rebuilt" in win.announcements[-1]


def _keymap_dialog(result):
    class _Dialog:
        def show(self):
            return result

    return _Dialog()


# --------------------------------------------------------------------------- #
# Sound Scheme and the spelling voice
# --------------------------------------------------------------------------- #


def test_sound_scheme_opens_without_needing_the_spelling_area(lite_window, monkeypatch):
    """Deliberately not gated by Customize Features.

    Somebody who has silenced everything needs a way back, and a switch that
    can switch itself off is a door that locks from the inside.
    """
    import quill.ui.sound_scheme_dialog as dialog_module

    opened: list[dict] = []

    class _Unchanged:
        changed = False

    class _Dialog:
        def __init__(self, *_a, **kwargs):
            opened.append(kwargs)

        def show(self):
            return _Unchanged()

    monkeypatch.setattr(dialog_module, "SoundSchemeDialog", _Dialog)
    win = lite_window("hello")
    monkeypatch.setattr(win.app, "feature_enabled", lambda _area: False)
    win.cmd_sound_scheme()

    assert opened, "Sound Scheme must open even with every feature area off"
    assert win.announcements == [], "an unchanged scheme must not claim it saved one"


def test_sound_scheme_lists_only_the_events_quilllite_can_actually_post(lite_window, monkeypatch):
    """Without the app id the window offered a hundred and forty rows, most of
    which this app never posts -- a list where almost nothing does anything."""
    import quill.ui.sound_scheme_dialog as dialog_module

    opened: list[dict] = []

    class _Dialog:
        def __init__(self, *_a, **kwargs):
            opened.append(kwargs)

        def show(self):
            return type("Result", (), {"changed": False})()

    monkeypatch.setattr(dialog_module, "SoundSchemeDialog", _Dialog)
    win = lite_window("hello")
    win.cmd_sound_scheme()
    assert opened[0]["app_id"] == "quilllite"


def test_spelling_voice_settings_cancelled_saves_nothing(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.cmd_spelling_voice_settings()
    assert win.app.saved_settings == 0
    assert win.announcements == []


def test_saving_the_spelling_voice_refreshes_every_open_document(lite_window, lite_dialogs):
    """A pause that is 600 ms in document 2 and 900 ms in document 3 is a pause
    you cannot learn, so the refresh reaches every frame rather than this one."""
    win = lite_window("hello")
    other = lite_window("second")
    win.app.frames = [win, other]
    lite_dialogs.answer("edit_spelling_voice", True)

    win.app.settings.spell_aloud_delay_ms = 1200
    win.cmd_spelling_voice_settings()

    assert win.app.saved_settings == 1
    assert other._spell_voice.policy.delay_ms == 1200
    assert win.announcements[-1] == "Spelling announcements saved"


def test_the_spelling_voice_window_is_reachable_with_spelling_switched_off(
    lite_window, lite_dialogs, monkeypatch
):
    """Every other spelling command acts on a document and is rightly refused.
    This one is a preference, and the settings survive the area being off."""
    win = lite_window("hello")
    monkeypatch.setattr(win.app, "feature_enabled", lambda _area: False)
    win.cmd_spelling_voice_settings()
    assert "edit_spelling_voice" in lite_dialogs.names()


# --------------------------------------------------------------------------- #
# Spell review and suggestions
# --------------------------------------------------------------------------- #


def test_spell_review_is_never_gated_by_the_file_type_rule(lite_window, lite_dialogs, tmp_path):
    """The rule decides what happens when nobody has said anything.

    F7 is somebody saying something, so it runs on a .py file too.
    """
    win = lite_window("teh code", cursor=0)
    win.path = tmp_path / "module.py"
    win._spell_dictionary_cache = {"code"}
    win.cmd_spell_review()
    assert "review_textctrl" in lite_dialogs.names()


def test_spell_review_forgets_the_cached_dictionary_afterwards(lite_window, lite_dialogs):
    """The review can teach words. A cache kept across it would keep calling
    them wrong until the document was closed."""
    win = lite_window("teh")
    win._spell_dictionary_cache = {"the"}
    win.cmd_spell_review()
    assert win._spell_dictionary_cache is None


def test_spell_word_at_cursor_offers_suggestions_for_the_word_the_caret_is_in(
    lite_window, lite_dialogs
):
    """Inside the word, not starting at it.

    ``misspelling_at`` answers only for a word beginning at the caret, so
    Shift+F7 in the middle of a misspelled word used to say there was nothing
    there -- which is every press not made in the instant after typing a space.
    """
    win = lite_window("the quick brxwn fox", cursor=13)
    win._spell_dictionary_cache = {"the", "quick", "brown", "fox"}
    win.cmd_spell_word_at_cursor()

    kwargs = lite_dialogs.kwargs_for("choose_from_rows")
    assert kwargs["title"] == "Spelling Suggestions"
    assert "brxwn" in kwargs["label"]
    assert kwargs["rows"], "a word with no suggestions should not open the window"


def test_choosing_a_suggestion_replaces_the_word_and_says_which(lite_window, lite_dialogs):
    win = lite_window("the quick brxwn fox", cursor=13)
    win._spell_dictionary_cache = {"the", "quick", "brown", "fox"}
    lite_dialogs.answer("choose_from_rows", "brown")
    win.cmd_spell_word_at_cursor()

    assert win.control.GetValue() == "the quick brown fox"
    assert win.modified is True
    assert win.announcements[-1] == "Replaced with brown"


def test_cancelling_the_suggestion_list_leaves_the_word_alone(lite_window, lite_dialogs):
    win = lite_window("the quick brxwn fox", cursor=13)
    win._spell_dictionary_cache = {"the", "quick", "brown", "fox"}
    win.cmd_spell_word_at_cursor()
    assert win.control.GetValue() == "the quick brxwn fox"
    assert win.modified is False


def test_a_correctly_spelled_word_opens_no_window(lite_window, lite_dialogs):
    win = lite_window("the quick brown fox", cursor=12)
    win._spell_dictionary_cache = {"the", "quick", "brown", "fox"}
    win.cmd_spell_word_at_cursor()
    assert lite_dialogs.names() == []
    assert win.announcements[-1] == "No misspelling at the cursor"


def test_each_suggestion_spells_itself_out_on_arrival(lite_window, lite_dialogs):
    """Eight near-identical spellings is exactly where a listener cannot tell
    one row from the next: "receive" and "recieve" are the same sound."""
    win = lite_window("the quick brxwn fox", cursor=13)
    win._spell_dictionary_cache = {"the", "quick", "brown", "fox"}
    win.cmd_spell_word_at_cursor()
    assert callable(lite_dialogs.kwargs_for("choose_from_rows")["on_highlight"])


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #


def test_editor_font_cancelled_changes_nothing(lite_window, fake_wx_dialog, wx_app):
    fake_wx_dialog("FontDialog", wx.ID_CANCEL)
    win = lite_window("hello")
    before = (win.app.settings.font_name, win.app.settings.font_size)
    win.cmd_editor_font()
    assert (win.app.settings.font_name, win.app.settings.font_size) == before
    assert win.app.saved_settings == 0


def test_editor_font_applies_to_every_window_and_is_announced(lite_window, fake_wx_dialog, wx_app):
    """An app-wide setting, not a per-document one: a face that differs between
    documents is a face you cannot rely on."""
    fake_wx_dialog(
        "FontDialog", wx.ID_OK, GetFontData=_font_data("Consolas", 14), Destroy=lambda: None
    )
    win = lite_window("hello")
    win.cmd_editor_font()

    assert (win.app.settings.font_name, win.app.settings.font_size) == ("Consolas", 14)
    assert win.app.saved_settings == 1
    assert win.app.reapplied == 1
    assert win.announcements[-1] == "Editor font Consolas, 14 point"


def test_selection_font_is_refused_outside_rich_text_and_names_this_document(lite_window):
    """The refusal names the document it is refusing in, which is the useful half.

    A font for a *selection* is rich text and nothing else. An untitled buffer
    has no markup either, so the sentence offers **both** ways forward -- rich
    text, or giving this document a markup language -- rather than the single
    piece of advice that used to be right about half the time.
    """
    win = lite_window("hello", mode="plain")
    win.cmd_selection_font()
    said = win.announcements[-1]
    assert "no formatting" in said
    assert "Alt Shift F" in said
    assert "Control Alt F6" in said


def test_selection_font_sets_the_face_and_the_size_on_the_selection(
    lite_window, fake_wx_dialog, wx_app
):
    fake_wx_dialog("FontDialog", wx.ID_OK, GetFontData=_font_data("Arial", 18))
    win = lite_window("hello", mode="rich")
    win.cmd_selection_font()

    assert ("set_font_name", "Arial") in win.editor.calls
    assert ("set_font_size", 18) in win.editor.calls
    assert win.modified is True
    assert win.announcements[-1] == "Arial, 18 point"


def test_selection_font_cancelled_touches_the_editor_not_at_all(
    lite_window, fake_wx_dialog, wx_app
):
    fake_wx_dialog("FontDialog", wx.ID_CANCEL)
    win = lite_window("hello", mode="rich")
    win.cmd_selection_font()
    assert win.editor.calls == []
    assert win.modified is False


def _font_data(face: str, size: int):
    """``GetFontData().GetChosenFont()`` down to the two getters wx uses."""

    class _Font:
        def GetFaceName(self):  # noqa: N802 - wx API shape
            return face

        def GetPointSize(self):  # noqa: N802 - wx API shape
            return size

    class _Data:
        def GetChosenFont(self):  # noqa: N802 - wx API shape
            return _Font()

    return _Data()


# --------------------------------------------------------------------------- #
# Palette, Go To Anything, Go To Line
# --------------------------------------------------------------------------- #


def test_the_palette_is_built_from_the_live_registry(lite_window, lite_dialogs):
    """The one surface that shows a command's key beside its name while you are
    looking for the command, which is how a key gets learned."""
    win = lite_window("hello")
    lite_dialogs.answer("CommandPaletteDialog", _palette())
    win.cmd_command_palette()
    assert lite_dialogs.names() == ["CommandPaletteDialog"]
    assert callable(lite_dialogs.kwargs_for("CommandPaletteDialog")["binding_for"])


def test_the_palette_returns_focus_to_the_document(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.control.focused = False
    lite_dialogs.answer("CommandPaletteDialog", _palette())
    win.cmd_command_palette()
    assert win.control.focused is True


def test_go_to_anything_converts_headings_to_line_numbers(lite_window, lite_dialogs):
    """The dialog speaks in line numbers and calls back through
    ``go_to_line_number``, so the conversion happens on the way in rather than
    the dialog being taught about character offsets."""
    win = lite_window("Title\nbody\nSecond\nmore", mode="rich")
    win.editor.heading_rows = [(0, 1, "Title"), (11, 2, "Second")]
    lite_dialogs.answer("GoToAnythingDialog", _palette())
    win.cmd_go_to_anything()

    assert lite_dialogs.kwargs_for("GoToAnythingDialog")["headings"] == [
        ("Title", 1),
        ("Second", 3),
    ]


def test_go_to_anything_offers_no_headings_from_a_plain_document(lite_window, lite_dialogs):
    win = lite_window("Title\nbody", mode="plain")
    win.editor.heading_rows = [(0, 1, "Title")]
    lite_dialogs.answer("GoToAnythingDialog", _palette())
    win.cmd_go_to_anything()
    assert lite_dialogs.kwargs_for("GoToAnythingDialog")["headings"] == []


def _palette():
    """The palette pair. ``show_modal_and_run`` takes the parent frame in
    ``cmd_go_to_anything`` and nothing in ``cmd_command_palette``, so the stub
    accepts both rather than pinning one caller's signature."""

    class _Dialog:
        def show_modal_and_run(self, *_args):
            return None

    return _Dialog()


def _showable():
    """A modeless dialog: built, then ``Show()``n and left open."""

    class _Dialog:
        shown = 0

        def Show(self):  # noqa: N802 - wx API shape
            type(self).shown += 1

        def Bind(self, *_a, **_k):  # noqa: N802 - wx API shape
            return None

        def Raise(self):  # noqa: N802 - wx API shape
            return None

    return _Dialog()


def test_goto_is_offered_the_current_line_and_the_total(lite_window, lite_dialogs):
    win = lite_window("one\ntwo\nthree", cursor=5)
    win.cmd_goto_line()
    kwargs = lite_dialogs.kwargs_for("ask_go_to")
    assert (kwargs["line"], kwargs["last_line"]) == (2, 3)


def test_goto_offers_the_kinds_quilllite_has_and_not_pages(lite_window, lite_dialogs):
    """QUILL Lite has no pagination model, and a greyed row for a thing the
    product does not do is a row to walk past forever (bad.md 5.4)."""
    win = lite_window("# One\n\nbody\n", cursor=0)
    win.set_document_language("markdown", announce=False)
    win.cmd_goto_line()
    assert set(lite_dialogs.kwargs_for("ask_go_to")["kinds"]) == {"Bookmark", "Heading"}


def test_goto_offers_the_headings_led_by_their_level(lite_window, lite_dialogs):
    win = lite_window("# One\n\nbody\n\n## Two\n", cursor=0)
    win.set_document_language("markdown", announce=False)
    win.cmd_goto_line()
    headings = lite_dialogs.kwargs_for("ask_go_to")["kinds"]["Heading"]
    assert [target.label for target in headings] == ["Heading 1, One", "Heading 2, Two"]


def test_goto_offers_the_bookmarks_led_by_their_digit(lite_window, lite_dialogs):
    """Led by the digit so "3, Enter" needs no extra chord (bad.md 5.2)."""
    win = lite_window("one\ntwo\nthree", cursor=4)
    win.cmd_set_bookmark_3()
    win.cmd_goto_line()
    bookmarks = lite_dialogs.kwargs_for("ask_go_to")["kinds"]["Bookmark"]
    assert [target.label for target in bookmarks] == ["3, two"]


def test_goto_cancelled_leaves_the_caret_where_it_was(lite_window, lite_dialogs):
    win = lite_window("one\ntwo\nthree", cursor=5)
    win.cmd_goto_line()
    assert win.control.GetInsertionPoint() == 5


def test_goto_moves_to_the_start_of_the_chosen_line(lite_window, lite_dialogs):
    from quill.ui.go_to_dialog import GoToResult

    win = lite_window("one\ntwo\nthree", cursor=0)
    lite_dialogs.answer("ask_go_to", GoToResult(line=3))
    win.cmd_goto_line()
    assert win.control.GetInsertionPoint() == len("one\ntwo\n")


def test_goto_moves_to_a_chosen_place(lite_window, lite_dialogs):
    from quill.ui.go_to_dialog import GoToResult

    win = lite_window("one\ntwo\nthree", cursor=0)
    lite_dialogs.answer("ask_go_to", GoToResult(position=8))
    win.cmd_goto_line()
    assert win.control.GetInsertionPoint() == 8


def test_goto_past_the_end_lands_on_the_last_position(lite_window, lite_dialogs):
    """Clamped rather than refused. A number somebody typed from a stale count
    should still take them somewhere sensible."""
    from quill.ui.go_to_dialog import GoToResult

    win = lite_window("one\ntwo", cursor=0)
    lite_dialogs.answer("ask_go_to", GoToResult(line=99))
    win.cmd_goto_line()
    assert win.control.GetInsertionPoint() == win.control.GetLastPosition()


# --------------------------------------------------------------------------- #
# Replace and abbreviations
# --------------------------------------------------------------------------- #


def test_replace_opens_the_replace_dialog_seeded_with_the_selection(lite_window, lite_dialogs):
    """Seeded with what is selected, so "replace this word" is two keys rather
    than two keys and retyping the word."""
    dialog = _showable()
    lite_dialogs.answer("ReplaceDialog", dialog)
    win = lite_window("alpha beta alpha")
    win.control.SetSelection(0, 5)
    win.cmd_replace()

    assert lite_dialogs.args_for("ReplaceDialog")[1] == "alpha"
    assert dialog.shown == 1


def test_manage_abbreviations_says_so_when_the_area_is_off(lite_window, lite_dialogs):
    """And names the key that turns it back on. A refusal that does not say how
    to undo itself leaves the listener with silence and no next move."""
    win = lite_window("hello")
    win.app.abbreviations = None
    win.cmd_manage_abbreviations()
    assert "Alt+Shift+A" in win.announcements[-1]


def test_manage_abbreviations_writes_back_and_reloads(lite_window, monkeypatch):
    """The dialog edits the library in place; the write-back is the caller's,
    and the reload is what makes a second window see the same list."""
    import quill.ui.abbreviation_manager_dialog as manager_module
    import quill.ui.dialog_contract as contract

    class _Manager:
        def __init__(self, *_a, **_k):
            self.dialog = object()

        def close(self):
            return None

    monkeypatch.setattr(manager_module, "AbbreviationManagerDialog", _Manager)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: wx.ID_OK)

    win = lite_window("hello")
    win.app.abbreviations = {"btw": "by the way"}
    win.cmd_manage_abbreviations()
    assert win.app.reloaded_abbreviations == 1


@pytest.mark.parametrize(
    ("start_enabled", "expected"),
    [(True, "Abbreviations off"), (False, "Abbreviations on")],
)
def test_toggle_abbreviations_flips_the_area_and_says_which_way(
    lite_window, monkeypatch, start_enabled, expected
):
    """The one feature that acts *while you type*, so it gets a key rather than
    a dialog: the moment you want it off is the moment it has just expanded
    something you meant to keep."""
    win = lite_window("hello")
    monkeypatch.setattr(win.app, "feature_enabled", lambda _area: start_enabled)
    win.app.features = _features()
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))

    win.cmd_toggle_abbreviations()

    assert win.app.features.set_calls == [("abbreviations", not start_enabled)]
    assert win.app.saved_features == 1
    assert win.app.reloaded_abbreviations == 1
    assert win.announcements[-1] == expected


def test_toggle_abbreviations_rebuilds_the_menus_after_the_event_not_during_it(
    lite_window, monkeypatch
):
    """wxMSW does not survive having a menu deleted while it is still
    dispatching that menu's event, so the rebuild goes through CallAfter."""
    deferred: list[object] = []
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: deferred.append(fn))

    win = lite_window("hello")
    win.app.features = _features()
    win.cmd_toggle_abbreviations()

    assert win.app.rebuilt_menus == 0, "the rebuild must not happen inline"
    assert deferred == [win.app.rebuild_all_menus]


def _features():
    class _Features:
        def __init__(self):
            self.set_calls = []

        def set_enabled(self, area, enabled):
            self.set_calls.append((area, enabled))

    return _Features()


class _Field:
    """Just enough of a read-only text control for the About hook."""

    def __init__(self, value: str) -> None:
        self.value = value
        self.caret = 0

    def __bool__(self) -> bool:
        return True

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self.value

    def SetValue(self, value: str) -> None:  # noqa: N802
        self.value = value

    def AppendText(self, text: str) -> None:  # noqa: N802
        self.value += text
        self.caret = len(self.value)

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def SetInsertionPoint(self, where: int) -> None:  # noqa: N802
        self.caret = where

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self.value)


def test_about_hands_its_text_to_the_ai_usage_hook(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.cmd_about()
    assert lite_dialogs.kwargs_for("show_text_window")["on_ready"] == win.ai_about_usage


def test_about_shows_the_support_id_and_the_servers_usage(lite_window, monkeypatch):
    """Asked for 2026-09-25: the number support asks for, and the allowance,
    where people look. The usage is fetched from the server every time, and
    the caret stays where the reader left it."""
    from quill.core.ai.gateway_client import GatewayQuota

    class Service:
        signed_in = True
        support_id = "2DFD-22DB"

        def fetch_quota(self, *, on_done, on_error):
            on_done(GatewayQuota(monthly_cap=100, monthly_used=4, daily_cap=20, daily_used=1))

    win = lite_window("hello")
    monkeypatch.setattr(win, "_ai_service", lambda: Service())
    field = _Field("QUILL Lite 1.0")
    win.ai_about_usage(field)

    assert "Support ID for this computer: 2DFD-22DB" in field.value
    assert "96 of 100 requests left" in field.value
    assert "Asking QUILL" not in field.value
    assert field.caret == 0


def test_about_says_nothing_about_ai_when_not_connected(lite_window, monkeypatch):
    class Service:
        signed_in = False
        support_id = ""

    win = lite_window("hello")
    monkeypatch.setattr(win, "_ai_service", lambda: Service())
    field = _Field("QUILL Lite 1.0")
    win.ai_about_usage(field)
    assert field.value == "QUILL Lite 1.0"


def test_a_support_message_carries_the_ai_support_id(monkeypatch):
    """Read from the host by the support flow itself, so every app's message
    carries it without every call site having to pass it."""
    import quill.ui.support_dialog as support_dialog

    seen: dict = {}
    monkeypatch.setattr(support_dialog, "_server_path", lambda *a, **k: False)

    class Dialog:
        def __init__(self, host, wx, **kwargs):
            seen.update(kwargs)

        def show(self):
            pass

    monkeypatch.setattr(support_dialog, "_SupportDialog", Dialog)
    host = type("Host", (), {"ai_support_facts": lambda self: {"QUILL AI support ID": "X1"}})()
    support_dialog.open_support_message(host, source_app="QuillLite", app_version="1.0")
    assert seen["extra"] == {"QUILL AI support ID": "X1"}
