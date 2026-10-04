"""Crash recovery on QUILL's main window (qc.md F-08, extracted 2026-10-03).

After an unclean exit: what to offer, the recovery window, recovering or
sending a report, and clearing the logs afterwards. One lifetime -- the
offer made at start-up and settled once -- moved whole out of ``MainFrame``;
the host contract is unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

from quill import __version__
from quill.core.diagnostics import record_diagnostic_event
from quill.core.document import Document
from quill.core.locations import LocationRing
from quill.core.paths import app_data_dir
from quill.core.recovery import (
    latest_crash_report,
    mark_recovery_offer_dismissed,
    mark_recovery_offer_recovered,
    read_recovery_snapshot,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class CrashRecoveryMixin:
    """The crash-recovery offer and window; mixed into MainFrame."""

    def _clear_recovery_logs(self, logs_path: Path) -> int:
        """Delete log files in *logs_path*; return how many were removed.

        A file held open by the active logger (typically the current
        ``quill.log`` on Windows) cannot be unlinked, so it is truncated to zero
        bytes instead and still counted as cleared. Best effort: anything that
        can be neither removed nor truncated is skipped.
        """
        removed = 0
        try:
            entries = [entry for entry in logs_path.iterdir() if entry.is_file()]
        except OSError:
            return 0
        for entry in entries:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                try:
                    entry.write_bytes(b"")
                    removed += 1
                except OSError:
                    continue
        return removed

    def _unclean_exit_context(self) -> str:
        """The session facts an unclean-exit report has to carry (#1464/#1466/#1480).

        Everything here is already gathered for a crash *with* a traceback --
        version, portable flag, screen reader, the last commands. An unclean
        exit has no traceback by definition, so this context is the only
        evidence it can offer, and three reports arrived without any of it.
        Built through the same builder the tracebacked path uses, so the two
        kinds of report cannot describe one session two ways.

        Every lookup is defensive: a report that raises while describing a
        crash is a report nobody gets.
        """
        import platform as platform_module

        from quill import __version__
        from quill.stability.crash_submit import build_session_context

        try:
            from quill.core.diagnostics import load_diagnostic_events

            recent = [event.name for event in load_diagnostic_events(limit=50)]
        except Exception:  # noqa: BLE001 - a missing command log is not a reason to file nothing
            recent = []
        try:
            from quill.core.storage_mode import portable_root_dir

            portable = portable_root_dir() is not None
        except Exception:  # noqa: BLE001 - see above
            portable = False
        reader = ""
        if sys.platform == "win32":
            try:
                from quill.platform.windows.sr_detect import detect_screen_reader

                detected = detect_screen_reader()
                if detected is not None and getattr(detected, "detected", False):
                    reader = str(getattr(detected, "name", "") or "")
            except Exception:  # noqa: BLE001 - see above
                reader = ""
        return build_session_context(
            app_version=__version__ or "",
            portable=portable,
            screen_reader_name=reader or None,
            recent_commands=recent,
            platform_name=platform_module.platform(),
        )

    def _send_crash_report(self, offer: object, logs_path: Path) -> bool:
        """Email Support from the Crash Recovery dialog. Returns True to close it.

        Opens the user's own mail program with a redacted report of the
        unclean exit addressed to support@community-access.org -- the same
        handoff as Help > Get Help from Support. Nothing is sent until the
        user sends it there. Returns True when a mail program answered (the
        dialog closes); False when none did, in which case the report is on
        the clipboard and the dialog stays open. Until 2026-09-26 this filed
        a public GitHub issue with a bundled token; neither exists now.
        """
        from quill.stability.crash_email import (
            NEWLINE,
            build_crash_support_message,
            build_log_summary,
            find_stall_evidence,
        )
        from quill.ui.support_dialog import send_by_mail

        # #1013/#1045/#1046: quote the evidence begin_session() captured on
        # the offer, not a fresh scan -- by now this session's own logging can
        # have pushed the original evidence out of the scan window.
        evidence = getattr(offer, "error_evidence", None)
        evidence_section = (
            f"Error evidence that triggered this offer:\n{evidence}\n\n" if evidence else ""
        )
        # Group D (#1079/#1085/#1095): stitch the real traceback from the last
        # crash-*.txt, bounded near the crashed session's snapshot mtime so an
        # ancient crash is never attached.
        snapshot = getattr(offer, "snapshot", None)
        try:
            floor = snapshot.stat().st_mtime - 300 if snapshot is not None else None
        except OSError:
            floor = None
        crash_report = latest_crash_report(app_data_dir() / "crash-reports", min_mtime=floor)
        crash_section = (
            f"Last local crash report (full traceback):\n{crash_report}\n\n" if crash_report else ""
        )
        # #1464/#1466/#1480: an unclean exit has no traceback, so the session
        # context and any UI-stall lines are the evidence; stalls go first.
        stall = find_stall_evidence(logs_path)
        stall_section = (
            "UI stalls recorded before the exit:" + NEWLINE + stall + NEWLINE * 2 if stall else ""
        )
        body = (
            "QUILL offered crash recovery after an unclean exit. Written from "
            "the Crash Recovery dialog.\n\n"
            + self._unclean_exit_context()
            + stall_section
            + crash_section
            + evidence_section
            + build_log_summary(logs_path)
        )
        import platform as platform_module

        facts_of = getattr(self, "ai_support_facts", None)
        message = build_crash_support_message(
            summary="QUILL detected an unclean exit",
            body=body,
            app_version=__version__ or "0.0.0",
            platform_name=platform_module.platform(),
            extra=facts_of() if callable(facts_of) else {},
        )
        if send_by_mail(self, message, title="Crash Recovery"):
            self._record_notification("Crash report opened in your mail program", "support")
            self._set_status("Crash report ready in your mail program")
            return True
        self._set_status("No mail program: crash report copied to the clipboard")
        return False

    def _prepare_crash_recovery_payload(
        self,
        offer: object,
        cancellation_token: object = None,
        operation_id: object = None,
        progress_callback: object = None,
    ) -> dict[str, object]:
        """Read the recovery snapshot + ensure the logs dir exist on a worker.

        This is the slow bit that used to block the UI thread for >30s on
        machines with large autosave files (#179).  No ``wx`` calls happen
        here, so the result is safe to deliver back through
        :class:`TaskManager` for the UI thread to render.
        """
        from quill.core.recovery import read_recovery_snapshot

        logs_path = app_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)

        preview_text = ""
        try:
            full, _had_rep = read_recovery_snapshot(offer.snapshot)
            lines = full.splitlines()
            preview_text = "\n".join(lines[:30])
            if len(lines) > 30:
                preview_text += f"\n\n... ({len(lines) - 30} more lines)"
        except OSError:
            preview_text = "(Could not read snapshot preview)"

        return {
            "logs_path": logs_path,
            "preview_text": preview_text,
        }

    def _offer_crash_recovery(self) -> None:
        """Show the crash-recovery dialog after offloading snapshot I/O.

        The pre-modal ``mkdir`` + ``read_recovery_snapshot`` work is submitted
        to :class:`TaskManager` so the UI thread stays responsive while the
        autosave file is being read (#179).  The actual ``wx.Dialog`` +
        ``ShowModal`` calls still run inside this method (on the UI thread,
        after the worker delivers its result), so the dialog-inventory
        qualname ``MainFrame._offer_crash_recovery`` is preserved.
        """
        if not self._recovery_offers:
            return
        offer = self._recovery_offers[0]

        # M-28 / §8.2: adaptive prompt text after repeated dismissals.
        if offer.dismissal_count >= 3:
            intro = (
                "You have dismissed this recovery offer "
                f"{offer.dismissal_count} time(s). "
                "Press Restore to keep the recovered version, "
                "or Skip to discard it and continue with a blank document. "
                "Pressing Skip again will keep the in-memory version; "
                "press Restore now to save your work."
            )
        else:
            intro = (
                "Quill detected an unclean exit. Restore the latest autosave snapshot, "
                "open the logs folder, or save diagnostics before continuing."
            )

        # Hold a slot so the ``TaskManager`` callback can reach the offer and
        # intro without re-reading instance state.  The callback runs on the
        # UI thread (via ``call_ui_safely``), so it is safe to call back into
        # ``self._show_crash_recovery_dialog`` from inside the modal loop.
        ctx: dict[str, object] = {"offer": offer, "intro": intro}

        def _on_prepared(_operation_id: str, prepared: object) -> None:
            if not isinstance(prepared, dict):
                return
            self._show_crash_recovery_dialog(ctx, prepared)

        def _on_failed(_operation_id: str, _exc: BaseException) -> None:
            self._report_startup_task_failure("crash recovery")

        self._task_manager.submit(
            name="crash-recovery-prepare",
            func=self._prepare_crash_recovery_payload,
            on_success=_on_prepared,
            on_failure=_on_failed,
            offer=offer,
        )

    def _show_crash_recovery_dialog(
        self, ctx: dict[str, object], prepared: dict[str, object]
    ) -> None:
        """Build the crash-recovery modal and run the click loop on the UI thread.

        Kept in its own method so the dialog-inventory gate can attribute the
        ``wx.Dialog`` + ``wx.MessageDialog`` constructions to a stable qualname
        (``MainFrame._show_crash_recovery_dialog``).  Called by
        :meth:`_offer_crash_recovery` once ``TaskManager`` reports the
        snapshot read is done.
        """
        wx = self._wx
        offer = ctx["offer"]
        intro = ctx["intro"]
        logs_path = prepared["logs_path"]
        preview_text = prepared["preview_text"]

        dialog = wx.Dialog(self.frame, title="Crash Recovery", size=(780, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(dialog, label=intro),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        # §8.2: read-only snapshot preview so the user can decide before restoring.
        root.Add(
            wx.StaticText(dialog, label="Snapshot preview (first 30 lines):"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        # TE_RICH2 is required for screen-reader accessibility on Windows. A plain
        # ES_READONLY EDIT control (the default for TE_MULTILINE | TE_READONLY) does
        # not expose its value through UIA or IA2 when read-only, so NVDA and JAWS
        # announce the field but read no content. Switching to a RichEdit control via
        # TE_RICH2 fixes this — the accessible value is correctly reported.
        # SetName gives the control a programmatic accessible name; the preceding
        # StaticText label is not automatically associated with the TextCtrl on Windows
        # so without SetName screen readers announce "edit" with no context.
        # If the snapshot file was empty (e.g. Quill crashed before writing any
        # content), preview_text is "". An empty string is indistinguishable from a
        # control that failed to populate, so we show a descriptive fallback instead.
        preview_ctrl = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP | wx.TE_RICH2,
        )
        preview_ctrl.SetName("Snapshot preview")
        preview_ctrl.SetValue(preview_text if preview_text else "(snapshot is empty)")
        root.Add(preview_ctrl, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        root.Add(wx.StaticText(dialog, label="Logs folder"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        logs_field = wx.TextCtrl(dialog, style=wx.TE_READONLY)
        set_accessible_name(logs_field, "Logs folder")
        logs_field.SetValue(str(logs_path))
        root.Add(logs_field, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        restore_button = wx.Button(dialog, id=wx.ID_YES, label="Restore Latest Snapshot")
        open_logs_button = wx.Button(dialog, label="Open Logs Folder")
        clear_logs_button = wx.Button(dialog, label="Clear Logs")
        save_diagnostics_button = wx.Button(dialog, label="Save Diagnostics...")
        # Email Support (2026-09-26): was "Send Bug Report", which filed a
        # public GitHub issue. It now opens the mail program to support@.
        send_report_button = wx.Button(dialog, label="Email Support")
        skip_label = "Discard and Continue" if offer.dismissal_count >= 3 else "Skip Recovery"
        skip_button = wx.Button(dialog, id=wx.ID_NO, label=skip_label)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(restore_button, 0, wx.RIGHT, 6)
        buttons.Add(open_logs_button, 0, wx.RIGHT, 6)
        buttons.Add(clear_logs_button, 0, wx.RIGHT, 6)
        buttons.Add(save_diagnostics_button, 0, wx.RIGHT, 6)
        buttons.Add(send_report_button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        buttons.Add(skip_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)

        restore_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_YES))
        open_logs_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_APPLY))
        clear_logs_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLEAR))
        save_diagnostics_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_SAVE))
        send_report_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_HELP))
        skip_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_NO))
        dialog.SetDefaultItem(restore_button)
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        restore_button.SetFocus()
        dialog._quill_keep_initial_focus = True

        try:
            while True:
                result = self._show_modal_dialog(
                    dialog, "Crash Recovery", restore_editor_focus=False
                )
                if result == wx.ID_APPLY:
                    self.open_logs_folder()
                    continue
                if result == wx.ID_CLEAR:
                    removed = self._clear_recovery_logs(logs_path)
                    if removed:
                        message = (
                            f"Removed {removed} log file{'s' if removed != 1 else ''} from:\n"
                            f"{logs_path}"
                        )
                    else:
                        message = f"There were no log files to remove in:\n{logs_path}"
                    with wx.MessageDialog(
                        self.frame, message, "Logs Cleared", wx.OK | wx.ICON_INFORMATION
                    ) as confirm:
                        self._show_modal_dialog(confirm, "Logs Cleared", restore_editor_focus=False)
                    self._set_status(f"Cleared {removed} log file(s)")
                    continue
                if result == wx.ID_SAVE:
                    self.save_diagnostics_bundle()
                    continue
                if result == wx.ID_HELP:
                    if self._send_crash_report(offer, logs_path):
                        mark_recovery_offer_dismissed(offer)
                        return
                    continue
                if result != wx.ID_YES:
                    mark_recovery_offer_dismissed(offer)
                    record_diagnostic_event(
                        "recovery",
                        "offer-dismissed",
                        detail=f"session={offer.session_id}; snapshot={offer.snapshot}",
                    )
                    self._set_status("Skipped crash recovery")
                    self._record_notification("Crash recovery offer dismissed", "recovery")
                    return
                try:
                    recovered_text, had_replacements = read_recovery_snapshot(offer.snapshot)
                except OSError as error:
                    record_diagnostic_event(
                        "recovery",
                        "snapshot-read-failed",
                        detail=(
                            f"session={offer.session_id}; snapshot={offer.snapshot}; error={error}"
                        ),
                    )
                    self._show_message_box(
                        f"Could not restore snapshot: {error}",
                        "Crash Recovery",
                        wx.ICON_ERROR | wx.OK,
                    )
                    self._set_status("Crash recovery failed")
                    return
                self._create_document_tab(
                    Document(text=recovered_text, path=None, modified=True),
                    select=True,
                )
                # Rich-mode sessions also snapshot RTF bytes (.rtfsnap): the
                # plain text alone would recover the words but lose the
                # formatting. Best-effort restore through the surface's TOM.
                self._maybe_restore_rich_snapshot(offer.snapshot)
                # §8.2: warn when bytes were silently replaced during decode.
                if had_replacements:
                    self._record_notification(
                        "This file had undecodable bytes; some characters may have been replaced "
                        "(shown as •).",
                        "recovery",
                    )
                mark_recovery_offer_recovered(offer)
                record_diagnostic_event(
                    "recovery",
                    "snapshot-recovered",
                    detail=f"session={offer.session_id}; snapshot={offer.snapshot}",
                )
                self._location_ring = LocationRing()
                # §8.4: restore the cursor to where the user was working.
                restore_pos = offer.cursor_position
                if restore_pos > 0 and self.editor is not None:
                    try:
                        wx.CallAfter(self.editor.SetInsertionPoint, restore_pos)
                        self._location_ring.record(restore_pos)
                    except Exception:  # noqa: BLE001
                        self._location_ring.record(0)
                else:
                    self._location_ring.record(0)
                self._refresh_title()
                status = "Recovered latest autosave snapshot"
                if had_replacements:
                    status += " (some bytes replaced — check notifications)"
                self._set_status(status)
                self._record_notification("Recovered autosave snapshot", "recovery")
                return
        finally:
            dialog.Destroy()
