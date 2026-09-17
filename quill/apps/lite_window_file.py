"""Opening a file, saving it, and copying unsaved work aside.

Split out of :mod:`quill.apps.lite_window` on 2026-09-10 for GATE-11: the frame
module was over the default cap and this is the largest thing in it that is not
the frame -- two hundred lines about *files*, in a class otherwise made of
window plumbing and event hooks.

What holds it together is that all three are the same risk. Every path here can
lose somebody's work, so every one of them:

* **writes atomically** (``textfile.write_bytes_atomic``: temp file, then
  ``os.replace``), so a power cut mid-save cannot leave a half-written document
  where the finished one was;
* **says what happened in words**, because a failed save is the one event where
  silence is indistinguishable from success and the cost of believing the wrong
  one is the document;
* **keeps the recovery copy beside the file and never over it**, and removes it
  only once the real save has succeeded.

The methods run on ``DocumentFrame``, which supplies ``control``, ``editor``,
``app``, ``path`` and the announcement and status hooks.
"""

from __future__ import annotations

import os
from pathlib import Path

import wx

from quill.core.lite import APP_NAME
from quill.core.lite import recovery as recovery_mod
from quill.core.lite.filetypes import is_rich_path
from quill.core.lite.textfile import (
    decode_text,
    encode_text,
    unencodable_characters,
    unencodable_warning,
    write_bytes_atomic,
)
from quill.core.sound_events import SoundEvent
from quill.io.rtf_safety import scan_rtf_safety
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import PLAIN, RICH
from quill.ui.richedit_rtf_surface import RichEditRtfError

__all__ = ["DocumentFileMixin"]

#: The temp-file suffix a rich save writes beside its target before replacing it.
#: Moved here with the two writers that use it (2026-09-10); nothing else did.
_TMP_SUFFIX = ".quilllite-tmp"


class DocumentFileMixin:
    """Load, save, and the autosave copy. Composed onto ``DocumentFrame``."""

    # ------------------------------------------------------------------ #
    # Load
    # ------------------------------------------------------------------ #

    def load(self, path: Path) -> bool:
        """Open *path* into this window. ``False`` when it could not be read."""
        path = Path(path)
        mode = RICH if is_rich_path(path.name) else PLAIN
        self._loading = True
        try:
            if mode == RICH:
                self._load_rich(path)
            else:
                self._load_plain(path)
        except (OSError, RichEditRtfError) as exc:
            self._loading = False
            self._report_failure("Open failed", f"Could not open {path.name}.\n\n{exc}")
            return False
        finally:
            self._loading = False
            # The one funnel every open goes through -- File > Open, the command
            # line, a recent file, the shell. Rich and plain both replace the
            # text without raising a text event (ChangeValue, and the TOM's own
            # set_rtf), so the mirror is told here rather than in each branch.
            self.doc_text.invalidate()
        self.path = path
        self._discard_slot()
        self.modified = False
        self._remember(path)
        self.control.SetInsertionPoint(0)
        self._update_title()
        # The file's own name decides whether it is checked, so this has to run
        # after the path is set and not at construction: a window is built
        # empty and only then told which file it holds.
        self._init_spelling()
        self._sync_check_items()
        self._touch_status()
        # After the path is set, for the same reason spelling is: the store is
        # keyed by file path, and a window is built empty and only then told
        # which file it holds. This can move the cursor, so it runs before the
        # spelling announcement rather than after -- the last thing said should
        # be about the document, not about a caret that has already moved.
        self.restore_document_memory()
        self.announce_spelling_state_if_skipped()
        return True

    def _load_rich(self, path: Path) -> None:
        """Scan the RTF for unsafe constructs, then hand the safe copy to the TOM."""
        if not self.editor.rtf_available():
            raise RichEditRtfError("Rich text needs the Windows Rich Edit control.")
        report = scan_rtf_safety(path.read_text(encoding="utf-8", errors="replace"))
        self._set_mode_internal(RICH)
        self.editor.set_rtf(report.sanitized_rtf.encode("utf-8", errors="replace"))
        self._apply_rich_theme_colour()
        if report.blocked:
            self._announce("Removed for safety: " + ", ".join(report.blocked))

    def _load_plain(self, path: Path) -> None:
        decoded = decode_text(path.read_bytes())
        self.encoding, self.newline = decoded.encoding, decoded.newline
        self._set_mode_internal(PLAIN)
        self.control.ChangeValue(decoded.text)

    def _load_recovery(self, slot: recovery_mod.RecoverySlot) -> None:
        """Restore a slot into this window, leaving it modified and unsaved.

        Two things this used to get wrong, and both of them lose work.

        **The document's own format is restored with it (F2).** The slot is
        always UTF-8 with LF line endings, because a copy of unsaved work has to
        hold whatever was typed -- and the window adopted *the slot's* encoding,
        so a cp1252 file recovered after a crash was saved back as UTF-8 and a
        CRLF one as LF. The slot records what the document was; this puts it
        back, and falls through to the slot's own only when there is nothing
        recorded (a slot written by an older build).

        **A failed restore claims nothing (F9).** It used to adopt the path,
        set the slot and mark the window modified even when the read had raised
        -- so an empty window sat under the name of a real file, and closing it
        and answering "No" deleted the only copy of the work.
        """
        self._loading = True
        restored = False
        try:
            if slot.mode == RICH and self.editor.rtf_available():
                self._set_mode_internal(RICH)
                self.editor.load_rtf(str(slot.content_path))
                self._apply_rich_theme_colour()
            else:
                decoded = decode_text(slot.content_path.read_bytes())
                self.encoding = slot.encoding or decoded.encoding
                self.newline = slot.newline or decoded.newline
                self._set_mode_internal(PLAIN)
                self.control.ChangeValue(decoded.text)
            restored = True
        except (OSError, RichEditRtfError) as exc:
            self._report_failure("Recovery failed", f"Could not restore {slot.title}.\n\n{exc}")
        finally:
            self._loading = False
            self.doc_text.invalidate()  # as in open_path: no text event fires
        if not restored:
            # The slot is left on disk deliberately. It is still the only copy
            # of that work, and the next launch will offer it again.
            self._announce(f"{slot.title} could not be recovered, and is still saved aside")
            return
        if slot.original_path and Path(slot.original_path).exists():
            self.path = Path(slot.original_path)
        self._slot = slot
        self.modified = True
        self._update_title()
        self._touch_status()

    def _remember(self, path: Path) -> None:
        """Put *path* at the head of the recent list, in every window."""
        self.app.settings.remember_recent(str(path))
        self.app.save_settings()
        self.app.refresh_all_menus()

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #

    def save(self, target: Path | None = None, text: str | None = None) -> bool:
        """Write the document. Falls through to Save As when it has no name yet.

        *text* is what to write instead of the buffer, which is how Save As
        converts a document **at write time** rather than in the window: the
        conversion is applied to the file, and only a successful write is
        allowed to change what is on screen (bad.md F1).
        """
        destination = target if target is not None else self.path
        if destination is None:
            return self.cmd_save_as()
        if target is None and self._pending_suffix:
            # A mode switch has made this name wrong for what the buffer holds
            # -- rich runs under a .txt, or Markdown under a .rtf. Save proposes
            # the renamed file; it never rewrites the one on disk into a format
            # its name does not claim (bad.md R6).
            return self.cmd_save_as()
        destination = Path(destination)
        body = self.control.GetValue() if text is None else text
        # A text override *is* the instruction to write characters rather than
        # runs: both conversions produce one, and both are saving a rich or HTML
        # document to a plain target. Without this the window is still rich at
        # write time, so Save As from .rtf to .txt wrote RTF into the .txt.
        as_rich = self.editor.mode == RICH and text is None
        if not as_rich and not self._encoding_allows(body):
            return False
        try:
            if as_rich:
                self._write_rtf(destination)
            else:
                write_bytes_atomic(
                    destination,
                    encode_text(body, encoding=self.encoding, newline=self.newline),
                )
        except (OSError, RichEditRtfError) as exc:
            self._report_failure("Save failed", f"Could not save {destination.name}.\n\n{exc}")
            return False
        if self.app.feature_enabled("backups"):
            # After the real write, never before: a backup that fails must not
            # be able to fail the save it was taken alongside.
            from quill.core.lite.backups import write_backup

            write_backup(destination, self.control.GetValue())
        self.path = destination
        self._discard_slot()
        self._set_modified(False)
        self._update_title()
        # Save As is the moment an untitled document first *has* a key, so this
        # is also the moment bookmarks set while it was untitled become
        # keepable. On a plain Save it is a checkpoint against a crash.
        self.remember_document_memory()
        # Save As can change the extension, and the extension is what decides
        # whether this document is spell-checked. A .txt saved as .json should
        # go quiet; the taught-word cache is dropped for the same reason, since
        # the document's own sidecar dictionary moved with the name.
        self._forget_spell_dictionary()
        self._remember(destination)
        self._cue(SoundEvent.DOCUMENT_SAVED)
        # Whatever the name was wrong about, it is not wrong now.
        self._pending_suffix = ""
        self._announce(f"Saved {destination.name}")
        return True

    def _encoding_allows(self, body: str) -> bool:
        """True when the save may go ahead; asks about characters that will not fit.

        The encoding a text file was read in is the one it is written back in,
        which is the right default and the reason somebody can type an em dash
        into a Windows-1252 file and lose it. ``errors="replace"`` turned each
        one into a question mark and said nothing at all -- the quietest
        possible way to damage a document, and visible only if the person
        happens to read that line again (bad.md F3).

        Three answers, which is why it is a question rather than a refusal:
        **Yes** saves as UTF-8 and keeps everything, **No** saves as asked and
        loses them knowingly, and **Cancel** stops. The status bar's Encoding
        cell follows a Yes, because the document really is UTF-8 from then on.
        """
        missing = unencodable_characters(body, self.encoding)
        if not missing:
            return True
        answer = show_message_box(
            unencodable_warning(len(missing), self.encoding),
            APP_NAME,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            self,
        )
        if answer == wx.CANCEL:
            self._announce("Save cancelled")
            return False
        if answer == wx.YES:
            self.encoding = "utf-8"
            self._touch_status()
        return True

    def _write_rtf(self, target: Path) -> None:
        """Save through the TOM to a sibling temp file, then replace the target.

        The theme colour is removed for the duration of the save, so dark mode
        never leaks light grey text into somebody's file, and restored in a
        ``finally`` so a failed save does not leave the window unreadable.
        """
        tmp = target.with_name(target.name + _TMP_SUFFIX)
        self._set_whole_document_colour(None)
        try:
            self.editor.save_rtf(str(tmp))
            os.replace(tmp, target)
        finally:
            self._apply_rich_theme_colour()
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _write_recovery_copy(self) -> None:
        """The autosave tick: copy unsaved work aside. Never raises, never blocks."""
        slot = self._slot
        if slot is None or not self.modified:
            return
        try:
            if self.editor.mode == RICH and slot.mode == RICH:
                tmp = slot.content_path.with_name(slot.content_path.name + _TMP_SUFFIX)
                self._set_whole_document_colour(None)
                try:
                    self.editor.save_rtf(str(tmp))
                finally:
                    self._apply_rich_theme_colour()
                os.replace(tmp, slot.content_path)
            else:
                if slot.mode != self.editor.mode:
                    # The document changed mode since the slot was made; a plain
                    # copy in a .rtf slot would be restored by the RTF reader.
                    recovery_mod.discard(slot)
                    slot = self._slot = recovery_mod.new_slot(
                        self.editor.mode, str(self.path) if self.path else ""
                    )
                write_bytes_atomic(
                    slot.content_path, self.control.GetValue().encode("utf-8", errors="replace")
                )
            slot.original_path = str(self.path) if self.path else ""
            # What the document is, so a restore can put it back (F2). Recorded
            # on every tick rather than at slot creation, because File > Encoding
            # and Line Endings can change either one between ticks.
            slot.encoding = self.encoding
            slot.newline = self.newline
            recovery_mod.write_meta(slot)
        except (OSError, RichEditRtfError):
            pass  # the next tick tries again; a failed copy must not interrupt typing

    def _discard_slot(self) -> None:
        if self._slot is not None:
            recovery_mod.discard(self._slot)
            self._slot = None

    def _on_autosave_tick(self, _event: wx.TimerEvent) -> None:
        self._write_recovery_copy()

    def stop_timers(self) -> None:
        """Stop everything that fires on a clock. Safe to call more than once.

        *Everything*, since 2026-09-16. It stopped the autosave and the status
        bar and left two behind: the live spell check's one-shot timer and the
        pending "and here is how it is spelled" -- both of which fire a second
        or so later, on a window that has been destroyed, into a bare ``except``
        that swallowed the evidence (bad.md S8). A timer nobody stops is a
        crash nobody can reproduce.
        """
        try:
            self._autosave.Stop()
        except RuntimeError:
            pass
        self._stop_status_timer()
        timer = getattr(self, "_spell_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except RuntimeError:
                pass
        voice = getattr(self, "_spell_voice", None)
        if voice is not None:
            voice.cancel()

    def restart_autosave(self) -> None:
        """Re-arm the timer at the current interval, after Preferences changes it."""
        self._autosave.Start(self.app.settings.autosave_seconds * 1000)
