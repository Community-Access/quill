"""The external-change watcher: what happens when the file changes under you.

FEAT-19, extracted from ``main_frame.py`` on 2026-09-18 to keep that module
inside its GATE-11 budget, and it is a real seam rather than an arbitrary cut:
everything here is about one question -- another program has written to the file
you have open, so what should happen to this tab? -- and none of it is reached
from anywhere else in the frame.

What changed with the move is the answer (bad.md F5, decided 2026-09-18). A
clean tab used to be replaced in place, silently, for any suffix, by calling
``path.read_text()``. For a text file a build regenerates that is convenient.
For a ``.docx`` rewritten by Word it replaced the document with its own
compressed bytes decoded into replacement characters and marked the result
clean, and said nothing -- and the person least able to notice a screenful of
replacement characters is the one this editor is built for.

So now:

* every external change **asks**, with the question carrying a "do not ask me
  again for this format" answer, kept per file suffix;
* a reload goes through :func:`quill.io.open_read.read_open_document`, the same
  funnel the open flow uses, so a format with a reader gets its reader;
* and "Open Disk Version in a New Tab" opens an actual second tab. It used to
  call ``open_file`` on the path already open, and ``open_file`` answers an
  open path by selecting that tab -- so the button that promised a comparison
  selected the tab you were already looking at and announced that it had
  opened it. For a listener, nothing happened at all.

Mixed into :class:`~quill.ui.main_frame.MainFrame`, so every method resolves
through the same MRO as before and relies on the frame's usual helpers:
``self.document``, ``self.editor``, ``self.settings``, ``self._wx``,
``self.frame``, ``self._announce``, ``self._set_status`` and
``self._create_document_tab``.
"""

from __future__ import annotations

from quill.core.document import Document
from quill.core.external_change import (
    ExternalChangeWatcher,
    FileSnapshot,
    ReloadAction,
    decide_reload,
)

__all__ = ["ExternalChangeMixin"]


class ExternalChangeMixin:
    """Watch the open file, and ask before anything replaces what is open."""

    def _start_external_change_watcher(self) -> None:
        """Start the FEAT-19 external file-change watcher for the open document."""
        wx = getattr(self, "_wx", None)
        if wx is None:
            return
        if self._external_change_watcher is not None:
            # Already watching.
            return
        if self.document.path is None:
            # No file to watch.
            return
        if not getattr(self.settings, "external_change_watch_enabled", True):
            # Watching is disabled.
            return

        self._external_change_watcher = ExternalChangeWatcher(self.document.path)
        self._external_change_watcher.prime(FileSnapshot.of(self.document.path))

        # Poll every N milliseconds (debounce interval from settings).
        debounce_ms = int(getattr(self.settings, "external_change_debounce_ms", 1000))

        def poll_external_change() -> None:
            if self._external_change_watcher is None:
                return
            change = self._external_change_watcher.poll()
            if change == "none":
                return

            decision = decide_reload(
                change,
                buffer_dirty=self.document.modified,
                watch_enabled=getattr(self.settings, "external_change_watch_enabled", True),
                auto_reload_when_clean=getattr(
                    self.settings, "external_change_auto_reload_when_clean", False
                ),
                prompt_on_conflict=getattr(
                    self.settings, "external_change_prompt_on_conflict", True
                ),
                file_name=self.document.path.name if self.document.path else "",
                remembered=self._remembered_external_change_answer(),
            )

            if decision.action == ReloadAction.RELOAD:
                self._reload_from_disk_preserving_cursor()
                self._announce(decision.announcement)
            elif decision.action == ReloadAction.KEEP_MINE:
                self._keep_my_version_of_external_change()
                self._announce(decision.announcement)
            elif decision.needs_prompt:
                # Pause the timer while the dialog is open to prevent re-entrancy.
                timer = self._external_change_timer
                if timer is not None:
                    timer.Stop()
                self._announce(decision.announcement)
                self._show_external_change_prompt(decision.action)
                # Restart the timer unless the user closed or replaced the document.
                if timer is not None and self._external_change_watcher is not None:
                    timer.Start(debounce_ms)

        self._external_change_timer = wx.Timer(self.frame)
        self.frame.Bind(
            wx.EVT_TIMER, lambda _e: poll_external_change(), self._external_change_timer
        )
        self._external_change_timer.Start(debounce_ms)

    def _stop_external_change_watcher(self) -> None:
        """Stop the FEAT-19 external file-change watcher."""
        if self._external_change_timer is not None:
            self._external_change_timer.Stop()
            self._external_change_timer = None
        self._external_change_watcher = None

    def _remembered_external_change_answer(self) -> str:
        """The answer this person asked to keep for this file's format, or "".

        The "do not ask me again" checkbox in the File Changed on Disk dialog
        (bad.md F5). Read fresh on every poll rather than cached, so ticking the
        box takes effect on the very next change rather than the next launch.
        """
        from quill.core.external_change import remembered_answer

        if self.document.path is None:
            return ""
        return remembered_answer(
            self.document.path.name,
            always_reload=getattr(self.settings, "external_change_always_reload", []),
            always_keep=getattr(self.settings, "external_change_always_keep", []),
        )

    def _remember_external_change_answer(self, value: str) -> None:
        """Record "always reload" or "always keep" for this file's format."""
        from quill.core.external_change import REMEMBER_RELOAD, format_key
        from quill.core.settings import save_settings

        if self.document.path is None or not value:
            return
        key = format_key(self.document.path.name)
        if not key:
            return
        reload_list = list(getattr(self.settings, "external_change_always_reload", []))
        keep_list = list(getattr(self.settings, "external_change_always_keep", []))
        # One answer per format: the other list gives the key up, so changing
        # your mind later is one tick rather than a contradiction on disk.
        target, other = (
            (reload_list, keep_list) if value == REMEMBER_RELOAD else (keep_list, reload_list)
        )
        if key not in target:
            target.append(key)
        if key in other:
            other.remove(key)
        self.settings.external_change_always_reload = reload_list
        self.settings.external_change_always_keep = keep_list
        save_settings(self.settings)

    def forget_external_change_answers(self) -> None:
        """Ask again about every file format (bad.md F5).

        The only way back from the "do not ask me again" checkbox, and it has to
        exist: a question that can be switched off and not on is a trap, and the
        person most likely to tick it in a hurry is the one who cannot see the
        dialog they are dismissing.
        """
        from quill.core.settings import save_settings

        forgotten = len(getattr(self.settings, "external_change_always_reload", [])) + len(
            getattr(self.settings, "external_change_always_keep", [])
        )
        if not forgotten:
            self._set_status("No file formats are being answered for you.")
            return
        self.settings.external_change_always_reload = []
        self.settings.external_change_always_keep = []
        save_settings(self.settings)
        self._set_status(
            f"Forgot {forgotten} remembered file-format answer"
            f"{'s' if forgotten != 1 else ''}. "
            "QUILL will ask again when a file changes on disk."
        )

    def _keep_my_version_of_external_change(self) -> None:
        """Leave the buffer alone and stop the watcher re-reporting this change."""
        if self._external_change_watcher is not None and self.document.path is not None:
            self._external_change_watcher.prime(FileSnapshot.of(self.document.path))

    def _read_disk_version_text(self) -> str | None:
        """What is on disk now, read through the reader for this file's format.

        The F5 defect in one line: this used to be ``path.read_text()`` for every
        suffix, so a ``.docx`` rewritten by Word came back as its own compressed
        bytes decoded into replacement characters -- and the tab was marked clean,
        so the document was gone and nothing said so. A format with a reader gets
        its reader; plain text keeps the document's own detected encoding.

        ``None`` when the file cannot be read at all, which the caller reports
        rather than pushing a guess into the editor.
        """
        path = self.document.path
        if path is None:
            return None
        from quill.io.open_read import read_open_document

        suffix = path.suffix.lower()
        try:
            loaded, _book = read_open_document(
                path,
                suffix,
                word_mode=str(self.document.source_metadata.get("word_open_mode", "")) or None,
                csv_mode=str(self.document.source_metadata.get("csv_open_mode", "")) or None,
                docx_engine=str(getattr(self.settings, "docx_read_engine", "auto")),
            )
        except Exception as error:  # noqa: BLE001 - any reader failure is one sentence
            self._set_status(f"Could not reload '{path.name}' from disk -- {error}")
            return None
        return loaded.text

    def _reload_from_disk_preserving_cursor(self) -> None:
        """Reload the document from disk, preserving the cursor and scroll position (FEAT-19)."""
        if self.document.path is None:
            return
        # Save cursor position before the reload.
        caret = self.editor.GetInsertionPoint()
        reloaded_text = self._read_disk_version_text()
        if reloaded_text is None:
            return
        self.document.set_text(reloaded_text)
        self.document.modified = False
        self.editor.SetValue(reloaded_text)
        # Restore cursor, capped to valid range.
        capped_caret = max(0, min(caret, len(reloaded_text)))
        self.editor.SetInsertionPoint(capped_caret)
        self.editor.SetSelection(capped_caret, capped_caret)
        # Prime the watcher with the new snapshot so the reload is not re-reported.
        if self._external_change_watcher is not None:
            self._external_change_watcher.prime(FileSnapshot.of(self.document.path))

    def _show_external_change_prompt(self, action: ReloadAction) -> None:
        """Show the FEAT-19 conflict or deleted-file dialog and act on the user's choice.

        PROMPT_CONFLICT: file changed on disk while buffer is dirty.
          - Reload from Disk: discard edits and reload.
          - Keep My Version: keep edits; on-disk version is ignored until next save.
          - Open Disk Version in New Tab: open the on-disk copy alongside.

        PROMPT_DELETED: file deleted or moved on disk.
          - Keep Text: keep editing; document marked modified/unsaved.
          - Save As...: immediately open Save As so the user can rescue the text.
          - Close Tab: discard and close (with dirty-check).
        """
        wx = self._wx
        if self.document.path is None:
            return
        file_name = self.document.path.name

        if action == ReloadAction.PROMPT_DELETED:
            with wx.MessageDialog(
                self.frame,
                f"'{file_name}' was deleted or moved by another program.\n\n"
                "Your text is still open in the editor and has not been lost.\n"
                "What would you like to do?",
                "File Deleted from Disk",
                # dialog_button_contract: exempt -- not a destructive prompt.
                # The buttons are relabelled Keep Text / Save As... / Close Tab,
                # so Yes IS the safe answer (keep the user's text). Defaulting
                # to No here would push the reflexive Enter toward a file
                # dialog instead of preserving what is already open.
                wx.YES_NO | wx.CANCEL | wx.ICON_WARNING,
            ) as dlg:
                set_labels = getattr(dlg, "SetYesNoCancelLabels", None)
                if callable(set_labels):
                    set_labels("Keep Text", "Save As...", "Close Tab")
                result = self._show_modal_dialog(dlg, "File Deleted from Disk")
            if result == wx.ID_YES:
                self.document.modified = True
                self._refresh_title()
                self._set_status(
                    f"'{file_name}' was deleted from disk. "
                    "Your text is unsaved. Use File > Save As to keep it."
                )
                self._stop_external_change_watcher()
            elif result == wx.ID_NO:
                self.document.modified = True
                self._refresh_title()
                self._stop_external_change_watcher()
                self.save_file_as()
            else:
                if not self.document.modified or self._confirm_discard_changes():
                    self._close_tab_at(self._active_tab_index)
            return

        # PROMPT_CLEAN and PROMPT_CONFLICT: the file changed under us. The
        # dialog is the same question either way -- what should happen to this
        # tab -- and carries the "do not ask me again for this format" answer
        # (bad.md F5).
        from quill.ui.external_change_dialog import KEEP, NEW_TAB, RELOAD, ask_external_change

        dirty = bool(self.document.modified)
        answer = ask_external_change(self.frame, file_name, buffer_dirty=dirty)
        self._remember_external_change_answer(answer.remembered_value)

        if answer.action == RELOAD:
            self._reload_from_disk_preserving_cursor()
            self._announce("Reloaded from disk.")
            self._set_status(f"Reloaded '{file_name}' from disk.")
        elif answer.action == KEEP:
            # Prime with the current on-disk snapshot so the watcher doesn't re-fire
            # immediately; the user's edits will overwrite on next save.
            self._keep_my_version_of_external_change()
            self._set_status(
                f"Keeping your version. '{file_name}' will be overwritten on next save."
                if dirty
                else f"Keeping this tab as it is. '{file_name}' changed on disk."
            )
        elif answer.action == NEW_TAB:
            self._open_disk_version_in_new_tab()

    def _open_disk_version_in_new_tab(self) -> None:
        """Open what is on disk as a SECOND tab, beside the one already open.

        It used to call ``open_file`` on the same path, and ``open_file``
        answers a path that is already open by selecting that tab -- so the
        button that promised a comparison selected the tab you were already
        looking at and announced that it had opened it (bad.md F5). Nothing
        compared, and for a listener nothing happened at all.

        The disk copy is a pathless document named "<name> (on disk)", which is
        what makes it a second tab rather than a second claim on the same file:
        two tabs on one path would leave the watcher, the save path and the
        recent list arguing about which is the file.
        """
        path = self.document.path
        if path is None or not path.exists():
            self._set_status("The file is no longer on disk.")
            return
        disk_text = self._read_disk_version_text()
        if disk_text is None:
            return
        name = path.name
        disk_document = Document(text=disk_text)
        disk_document.source_metadata["display_name"] = f"{name} (on disk)"
        disk_document.source_metadata["read_only_guard"] = True
        self._create_document_tab(disk_document, select=True)
        self._set_status(
            f"Opened the version of '{name}' that is on disk in a second tab, "
            "read-only. Your tab is untouched."
        )

    def check_external_changes_now(self) -> None:
        """Manually trigger the external file-change check for the active document.

        Useful when the user wants to see whether the file changed on disk without
        waiting for the next poll cycle, or when auto-reload is on and they want
        a chance to compare before reloading.
        """
        if self.document.path is None:
            self._set_status("No file to check.")
            return
        if not getattr(self.settings, "external_change_watch_enabled", True):
            self._set_status(
                "External-change watching is disabled. "
                "Enable it in Preferences > General to use this feature."
            )
            return

        # Ensure a watcher exists (in case the file had no path when opened).
        if self._external_change_watcher is None:
            self._start_external_change_watcher()
            if self._external_change_watcher is None:
                self._set_status("Could not start external-change watcher.")
                return

        change = self._external_change_watcher.poll()
        decision = decide_reload(
            change,
            buffer_dirty=self.document.modified,
            watch_enabled=True,
            auto_reload_when_clean=False,
            prompt_on_conflict=True,
            file_name=self.document.path.name,
        )

        if decision.action == ReloadAction.NONE:
            # No external change. force-speak the result -- nothing moves focus,
            # so the plain status would be silent under a screen reader (#13).
            self._announce_result(f"'{self.document.path.name}' matches the on-disk version.")
        elif decision.action == ReloadAction.RELOAD:
            # Somebody who asked explicitly wants to see the question, whatever
            # standing answer they have given for this format (bad.md F5).
            self._show_external_change_prompt(ReloadAction.PROMPT_CLEAN)
        else:
            self._announce(decision.announcement)
            self._show_external_change_prompt(decision.action)
