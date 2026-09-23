"""The View menu: how the document looks, and how big it is.

Split from :mod:`quill.apps.lite_window_commands` because it is a different
question. That module is about the document -- open it, save it, search it,
format it. This one changes nothing in the document at all: theme, wrap, text
size, the editor font, the status bar, and the Preferences window that gathers
them. A change here is never an edit and never marks the file modified.

Two rules the whole menu obeys:

* **Every window, at once.** A setting is the app's, not the window's, so each
  change is saved and then pushed through
  :meth:`~quill.apps.lite.QuillLiteApp.reapply_settings` to every open document.
  A theme that applied only to the window you were in would be a bug people
  reported as "it forgets".
* **The view, not the text.** In rich text the size control is a *zoom*: run
  point sizes are the heading ladder, so enlarging by rewriting them would
  silently re-level every heading in the document.
"""

from __future__ import annotations

import wx

from quill.apps.lite_preferences import edit_preferences
from quill.core.lite import APP_NAME
from quill.core.metrics import compute_document_stats
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentViewCommandsMixin"]

#: What Reset Text Size resets to -- the settings default, stated once.
_DEFAULT_POINTS = 12


class DocumentViewCommandsMixin:
    """The ``cmd_*`` handlers for the View menu.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame`, which supplies
    ``app``, ``control``, ``_announce`` and the status-bar methods.
    """

    def cmd_toggle_dark(self) -> None:
        settings = self.app.settings
        settings.theme = "system" if settings.theme == "dark" else "dark"
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Dark mode on" if settings.theme == "dark" else "Dark mode off")

    def cmd_toggle_wrap(self) -> None:
        settings = self.app.settings
        settings.word_wrap = not settings.word_wrap
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Word wrap on" if settings.word_wrap else "Word wrap off")

    def _set_text_size(self, points: int) -> None:
        """Change the text size in every window, and say what it became."""
        settings = self.app.settings
        settings.font_size = points
        settings.normalized()  # clamps into range, so 4 and 400 both land somewhere legible
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce(f"{settings.font_size} point")

    def cmd_zoom_in(self) -> None:
        self._set_text_size(self.app.settings.font_size + 1)

    def cmd_zoom_out(self) -> None:
        self._set_text_size(self.app.settings.font_size - 1)

    def cmd_zoom_reset(self) -> None:
        self._set_text_size(_DEFAULT_POINTS)

    def cmd_editor_font(self) -> None:
        """Choose the editor's face and size for every window."""
        settings = self.app.settings
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                settings.font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=settings.font_name,
            )
        )
        with wx.FontDialog(self, data) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        settings.font_name = font.GetFaceName()
        settings.font_size = font.GetPointSize()
        settings.normalized()
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce(f"Editor font {settings.font_name}, {settings.font_size} point")

    def cmd_preferences(self) -> None:
        """Every setting in one window, including the two with no menu item.

        The feature profile is offered here as well as in Customize Features,
        because "make this Notepad" is a preference in every sense of the word
        and Customize Features is named after the mechanism rather than the
        wish. The areas and the profiles go in for that; a changed profile is
        reported separately, because it is written to a different file and
        costs a rebuild of every open window's menu bar.
        """
        from quill.core.lite.features import AREAS, PROFILES

        result = edit_preferences(
            self,
            self.app.settings,
            features=self.app.features,
            areas=AREAS,
            profiles=PROFILES,
            announce=self._announce,
        )
        self.control.SetFocus()
        if not result.changed:
            return
        self.app.save_settings()
        self.app.reapply_settings()
        if not result.features_changed:
            self._announce("Preferences saved")
            return
        self.app.save_features()
        self.app.rebuild_all_menus()
        self._announce("Preferences saved. The menus have been rebuilt.")

    def cmd_statistics(self) -> None:
        """Speak the document's size. The same numbers the status bar carries,
        said out loud, because a listener is not watching it."""
        stats = compute_document_stats(self.control.GetValue())
        self._announce(
            f"{stats.words:,} words, {stats.characters:,} characters, {stats.lines:,} lines"
        )

    def cmd_focus_status_bar(self) -> None:
        """F6: move into the status bar. Escape there comes back here."""
        if not getattr(self.app.settings, "show_status_bar", True):
            # A key that does nothing is indistinguishable from a broken key,
            # and a hidden bar is the one state where F6 has nowhere to go. Say
            # what happened and how to undo it, in one sentence.
            self._announce("The status bar is hidden. Alt+Shift+B shows it again.")
            return
        self.focus_status_bar()

    def cmd_toggle_status_bar(self) -> None:
        """Notepad's View > Status Bar, for every open document at once.

        An app-wide setting rather than a per-window one: it says how you want
        to work, and a bar that is there in document 2 and gone in document 3 is
        a bar you cannot rely on.
        """
        settings = self.app.settings
        settings.show_status_bar = not settings.show_status_bar
        self.app.save_settings()
        self.app.reapply_settings()
        self._announce("Status bar shown" if settings.show_status_bar else "Status bar hidden")

    # ------------------------------------------------------------------ #
    # Which features exist at all
    # ------------------------------------------------------------------ #

    def cmd_customize_features(self) -> None:
        """Turn whole areas of QuillLite on or off.

        The way QuillLite stays small is not that it does little -- it is that
        somebody who does not want rich text can remove the Format menu
        *entirely* rather than learn to ignore it. This is also where the three
        areas that ship switched off are found, which is the difference between
        "off by default" and "hidden".

        The list is searchable and comes with profiles, because seventeen
        checkboxes is a long way to Tab and "give me the small one" should not
        require ticking most of them. Both live in the shared dialog; what is
        QuillLite's is which areas exist and what the four profiles mean
        (:mod:`quill.core.lite.features`).

        The settings object goes in as well, because two of those profiles claim
        one: Notepad and WordPad are named after products whose identity *is*
        what Ctrl+N creates, and a Notepad profile that took the Format menu away
        and still made rich text documents would be keeping the letter of its
        name while breaking its promise.
        """
        from quill.core.lite.features import AREAS, PROFILES
        from quill.ui.app_features_dialog import AppFeaturesDialog

        ai_was_on = self.app.feature_enabled("hosted_ai")
        dialog = AppFeaturesDialog(
            self,
            app_title=APP_NAME,
            areas=AREAS,
            settings=self.app.features,
            profiles=PROFILES,
            app_settings=self.app.settings,
            announce_cb=self._announce,
        )
        # `show`, not `show_modal`: the method is called show, and the wrong
        # name raised AttributeError inside the menu handler, where wx swallows
        # it -- so Customize Features was a menu item that did nothing.
        if not dialog.show():
            self.control.SetFocus()
            return
        self.app.save_features()
        # A profile may have changed a setting as well as a set of areas, and
        # the dialog only ever writes to the object -- persisting it is the
        # caller's, exactly as it is for the features.
        self.app.save_settings()
        self.app.rebuild_all_menus()
        self.control.SetFocus()
        self._announce("Features saved. The menus have been rebuilt.")
        # Switching AI help on here is one of the three doors to the agreement,
        # and the only one somebody can arrive at without meaning to -- a profile
        # can turn the area on, and a profile is not consent. Asked *after* the
        # features are saved, so declining leaves the area on and unusable rather
        # than undoing a change they did make.
        if not ai_was_on and self.app.feature_enabled("hosted_ai"):
            self._offer_ai_privacy_on_enable()

    def cmd_toggle_quiet_mode(self) -> None:
        """Alt+Shift+M: silence every sound at once, and bring them back.

        One key rather than a visit to a settings window, because "make it
        stop" is a thing somebody needs *while* the noise is happening -- on a
        call, in a quiet room, or simply having had enough of an earcon today.
        A feature you have to go and find is one that does not help at the
        moment you need it.

        Sound-off rather than event-by-event: this is the blunt instrument on
        purpose, and the fine-grained answer already exists one menu item away
        in Sound Scheme. It writes the same shared setting QUILL's own toggle
        writes, so silencing one editor silences the family -- which is what
        somebody who wanted quiet meant.

        The confirmation is spoken, never played. A cue saying "sounds are off"
        would be the one sound that ignores the instruction, and a cue saying
        "sounds are on" arrives before the user can know it was allowed to.
        """
        from quill.core.settings import load_settings, save_settings
        from quill.ui import sound_manager

        settings = load_settings()
        quiet = bool(getattr(settings, "sound_enabled", True))
        settings.sound_enabled = not quiet
        save_settings(settings)
        sound_manager.on_settings_changed(settings)
        self._announce("Quiet mode on. All sounds silenced." if quiet else "Sounds on.")
        self._sync_check_items()

    def sound_is_quiet(self) -> bool:
        """Whether sound is off right now, for the menu's check mark.

        Read live rather than cached: the setting is shared with QUILL and with
        every other window here, so a copy held on one frame would be stale the
        moment somebody used the key in another.
        """
        try:
            from quill.core.settings import load_settings

            return not bool(getattr(load_settings(), "sound_enabled", True))
        except Exception:  # noqa: BLE001 - a menu mark is never worth an error
            return False

    def cmd_sound_scheme(self) -> None:
        """Every sound QuillLite can make, in one window you can hear.

        The same window QUILL opens, over the same shared pack format, because
        the sounds are the same sounds -- a listener who has built a scheme in
        one editor should find it offered in the other rather than having to
        build it twice. QuillLite writes its choice to the shared sound
        settings, which is the one place the player reads from.

        Not gated by Customize Features: somebody who has silenced everything
        needs a way back, and a switch that can switch itself off is a door that
        locks from the inside.
        """
        from pathlib import Path

        from quill.core.paths import app_data_dir
        from quill.core.settings import load_settings, save_settings
        from quill.core.sound_pack import available_sound_packs
        from quill.core.sound_scheme import user_schemes
        from quill.ui import sound_manager
        from quill.ui.sound_scheme_dialog import SoundSchemeDialog, draft_for_pack

        sound_settings = load_settings()
        current = str(getattr(sound_settings, "sound_pack_path", ""))
        disabled_raw = str(getattr(sound_settings, "sound_events_disabled", ""))
        data_dir = app_data_dir()
        schemes: list[tuple[str, str]] = [
            (pack.name, pack.setting_value) for pack in available_sound_packs()
        ]
        schemes.extend((scheme.name, scheme.setting_value) for scheme in user_schemes(data_dir))
        dialog = SoundSchemeDialog(
            self,
            draft=draft_for_pack(current),
            disabled=frozenset(e.strip() for e in disabled_raw.split(",") if e.strip()),
            data_dir=data_dir,
            available=schemes,
            current_pack=current,
            play=lambda path: sound_manager.preview_file(Path(path)),
            announce=self._announce,
            app_title=APP_NAME,
            # So the list is only what QuillLite can actually play. Without it
            # the window offered a hundred and forty rows, most of which this
            # app never posts.
            app_id="quilllite",
        )
        result = dialog.show()
        self.control.SetFocus()
        if not result.changed:
            return
        sound_settings.sound_events_disabled = result.disabled_csv
        sound_settings.sound_pack_path = result.pack_path
        save_settings(sound_settings)
        sound_manager.on_settings_changed(sound_settings)
        self._announce("Sound scheme saved")

    # ------------------------------------------------------------------ #
    # Finding a command without knowing its key
    # ------------------------------------------------------------------ #

    def cmd_command_palette(self) -> None:
        """Every command QuillLite has, searchable, with its key beside it.

        A menu bar answers "what is under Format?"; a palette answers "how do I
        sort lines?", which is the question somebody actually has. It is also
        the only surface that shows a command's key *next to its name* while you
        are looking for the command -- which is how a key gets learned.
        """
        from quill.ui.palette import CommandPaletteDialog

        palette = CommandPaletteDialog(
            self,
            self.app.command_registry(self),
            announce_fn=self._announce,
            binding_for=self.app.binding_for,
        )
        palette.show_modal_and_run()
        self.control.SetFocus()

    def cmd_go_to_anything(self) -> None:
        """One box for commands, headings and bookmarks together.

        Off by default: the palette, the headings list and the bookmark list each
        already answer their own part of this, and a second front door before
        anybody asked for one is a second thing to explain.
        """
        from quill.ui.palette import GoToAnythingDialog

        # The dialog speaks in line numbers and calls back through
        # go_to_line_number, so headings are converted on the way in rather than
        # the dialog being taught about offsets.
        headings: list[tuple[str, int]] = []
        if self.editor.mode == RICH:
            text = self.control.GetValue()
            headings = [
                (heading, text.count("\n", 0, min(offset, len(text))) + 1)
                for offset, _level, heading in self.editor.all_headings()
            ]
        dialog = GoToAnythingDialog(
            self,
            self.app.command_registry(self),
            headings=headings,
            announce_fn=self._announce,
            binding_for=self.app.binding_for,
        )
        dialog.show_modal_and_run(self)
        self.control.SetFocus()
