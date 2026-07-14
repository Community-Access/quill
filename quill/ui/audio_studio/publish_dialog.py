"""Publish a finished audiobook: RSS feed, SFTP upload, Auphonic mastering.

Opened from the Chapter Workbench's Publish... button, always for one
concrete, already-saved book. Three consent-gated sections:

- **Podcast feed (local).** Writes a self-contained ``.rss`` next to the book
  from its tags and a public media URL — no network involved.
- **SFTP upload.** Saved destinations (host/folder/URL base) with the password
  in the Windows Credential Manager; uploads the book plus its sidecars over
  QUILL's SSH client (host-key policy enforced). Explicit button per upload.
- **Auphonic.** Sends the book to the user's own Auphonic account (their API
  token, from the credential manager) for post-production, polls until done,
  and downloads the results next to the book.

The whole dialog is unavailable in Safe Mode. Long work runs on the
background task pool; every outcome is announced.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.core.publish.destinations import (
    DestinationStore,
    SftpDestination,
    load_destinations,
    save_destinations,
)
from quill.core.speech.book_file import BookFile
from quill.ui.audio_studio.pages_base import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

_log = logging.getLogger(__name__)


class PublishDialog(wx.Dialog):
    """Publish *book* to a feed, a server, or Auphonic — one explicit action each."""

    def __init__(
        self,
        parent: wx.Window,
        book: BookFile,
        *,
        data_dir: Path,
        announce: Callable[[str], None] | None = None,
        run_background: Callable[..., None] | None = None,
        trust_first_use: bool = False,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Publish Audiobook")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.publish",
        )
        self._book = book
        self._data_dir = data_dir
        self._announce_fn = announce
        self._run_background = run_background
        self._trust_first_use = trust_first_use
        self._store: DestinationStore = load_destinations(data_dir)

        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label=_("Publishing {name}").format(name=book.path.name),
            name="audio_studio.publish_heading",
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        root.Add(heading, 0, wx.ALL, 10)

        # --- Podcast feed (local) ---
        root.Add(
            wx.StaticText(
                self,
                label=_(
                    "Podcast feed: writes a .rss file next to the book (no upload)."
                    " Give the public URL where the audio will live."
                ),
            ),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        feed_row = wx.BoxSizer(wx.HORIZONTAL)
        self._media_url = wx.TextCtrl(self)
        self._media_url.SetName(_("Public media URL"))
        self._media_url.SetHint("https://example.com/podcast/" + book.path.name)
        feed_btn = wx.Button(self, label=_("Write &feed file"))
        feed_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_write_feed())
        folder_feed_btn = wx.Button(self, label=_("Folder feed (all episodes)&..."))
        folder_feed_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_folder_feed())
        feed_row.Add(self._media_url, 1, wx.EXPAND | wx.RIGHT, 6)
        feed_row.Add(feed_btn, 0, wx.RIGHT, 6)
        feed_row.Add(folder_feed_btn, 0)
        root.Add(feed_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # --- SFTP destination ---
        root.Add(
            wx.StaticText(
                self,
                label=_(
                    "Upload over SFTP: the book and its companion files go to the"
                    " chosen destination. The password is kept in the Windows"
                    " Credential Manager, never in QUILL's settings."
                ),
            ),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)
        self._dest_name = self._field(grid, _("Destination na&me:"))
        self._dest_host = self._field(grid, _("&Host:"))
        self._dest_port = wx.SpinCtrl(self, min=1, max=65535, initial=22)
        set_accessible_name(self._dest_port, _("Port"))
        grid.Add(wx.StaticText(self, label=_("P&ort:")), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._dest_port, 0)
        self._dest_user = self._field(grid, _("&Username:"))
        self._dest_dir = self._field(grid, _("Remote fol&der:"))
        self._dest_url = self._field(grid, _("Public URL &base (optional):"))
        self._dest_password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self._dest_password.SetName(_("Password"))
        grid.Add(wx.StaticText(self, label=_("&Password:")), 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(self._dest_password, 0, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._dest_pick = wx.Choice(self, choices=[d.name for d in self._store.destinations])
        self._dest_pick.SetName(_("Saved destinations"))
        self._dest_pick.Bind(wx.EVT_CHOICE, lambda _e: self._on_pick_destination())
        save_dest_btn = wx.Button(self, label=_("Save des&tination"))
        save_dest_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save_destination())
        upload_btn = wx.Button(self, label=_("&Upload book now"))
        upload_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_upload())
        dest_row.Add(self._dest_pick, 1, wx.EXPAND | wx.RIGHT, 6)
        dest_row.Add(save_dest_btn, 0, wx.RIGHT, 6)
        dest_row.Add(upload_btn, 0)
        root.Add(dest_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # --- Auphonic ---
        root.Add(
            wx.StaticText(
                self,
                label=_(
                    "Auphonic: sends the book to your own Auphonic account for"
                    " post-production (leveling, noise reduction). Needs your"
                    " Auphonic API token; results download next to the book."
                ),
            ),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        auphonic_row = wx.BoxSizer(wx.HORIZONTAL)
        self._token = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self._token.SetName(_("Auphonic API token"))
        self._load_token()
        check_btn = wx.Button(self, label=_("Check &account and load presets"))
        check_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_check_auphonic())
        auphonic_row.Add(self._token, 1, wx.EXPAND | wx.RIGHT, 6)
        auphonic_row.Add(check_btn, 0)
        root.Add(auphonic_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        preset_row = wx.BoxSizer(wx.HORIZONTAL)
        preset_row.Add(
            wx.StaticText(self, label=_("Auphonic pr&eset:")), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._preset_pick = wx.Choice(self, choices=[str(_("(account default preset)"))])
        self._preset_pick.SetName(_("Auphonic preset"))
        self._preset_pick.SetSelection(0)
        self._presets: list[object] = []
        self._credits: float | None = None
        auphonic_btn = wx.Button(self, label=_("Send to Auphonic&..."))
        auphonic_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_auphonic())
        preset_row.Add(self._preset_pick, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        preset_row.Add(auphonic_btn, 0)
        root.Add(preset_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self, wx.ID_CANCEL, label=_("Close"))
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)
        self.SetMinSize(wx.Size(640, 560))
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()

    # -- helpers -----------------------------------------------------------------

    def _field(self, grid: wx.FlexGridSizer, label: str) -> wx.TextCtrl:
        grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.TextCtrl(self)
        ctrl.SetName(label.replace("&", "").rstrip(":"))
        grid.Add(ctrl, 0, wx.EXPAND)
        return ctrl

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def _error(self, message: str) -> None:
        show_message_box(message, str(_("Publish Audiobook")), wx.OK | wx.ICON_ERROR, self)

    def _info(self, message: str) -> None:
        show_message_box(message, str(_("Publish Audiobook")), wx.OK | wx.ICON_INFORMATION, self)

    def _run(
        self,
        title: str,
        work: Callable[[Callable[[str, int, int], None]], object],
        done: Callable[[object], str],
    ) -> None:
        """Run *work* on the background pool (or inline in tests), then announce.

        *work* receives the frame's progress callable ``(message, current,
        total)`` — the same contract as ``MainFrame._run_background_task`` —
        so transfer progress reaches the status bar and the task tracker.
        """
        if self._run_background is not None:
            self._run_background(title, work, lambda result: self._announce(done(result)))
            return
        try:
            result = work(lambda _message, _current, _total: None)
        except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
            self._error(str(exc))
            return
        self._announce(done(result))

    def _progress_ui(self, title: str, message: str, cancel: threading.Event) -> object:
        """A modeless announced progress dialog with a live Cancel button."""
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        dialog = AIProgressDialog(self, title, message, on_cancel=cancel.set)
        dialog.show()
        return dialog

    # -- podcast feed -------------------------------------------------------------

    def collect_destination(self) -> SftpDestination:
        """The destination as currently typed (used by Save and Upload)."""
        return SftpDestination(
            name=self._dest_name.GetValue().strip(),
            host=self._dest_host.GetValue().strip(),
            username=self._dest_user.GetValue().strip(),
            remote_dir=self._dest_dir.GetValue().strip() or "/",
            port=int(self._dest_port.GetValue()),
            url_base=self._dest_url.GetValue().strip(),
        )

    def _on_write_feed(self) -> None:
        from quill.core.publish.rss import FeedItem, write_rss
        from quill.core.speech.ffmpeg import probe_duration_ms

        media_url = self._media_url.GetValue().strip()
        if not media_url:
            dest = self.collect_destination()
            from quill.core.publish.sftp_publish import public_url

            media_url = public_url(dest, self._book.path.name)
        if not media_url:
            self._error(str(_("Give the public URL where the audio will live (or a URL base).")))
            return
        item = FeedItem(
            path=self._book.path,
            media_url=media_url,
            title=self._book.tags.album or self._book.path.stem,
            duration_s=probe_duration_ms(self._book.path) // 1000,
            has_chapters=self._book.path.with_suffix(".chapters.json").is_file(),
        )
        out = self._book.path.with_suffix(".rss")
        try:
            written = write_rss([item], self._book.tags, out, feed_url=media_url)
        except OSError as exc:
            self._error(str(_("Could not write the feed: {error}").format(error=exc)))
            return
        self._announce(_("Wrote {name} next to the book").format(name=written.name))
        self._info(
            str(
                _(
                    "Wrote {name}. Upload it (and the audio) to your server, then"
                    " subscribe to its public URL in any podcast app."
                ).format(name=written.name)
            )
        )

    def _on_folder_feed(self) -> None:
        """Manage the whole folder as a show: every master an episode."""
        from quill.ui.audio_studio.feed_dialog import FolderFeedDialog

        with FolderFeedDialog(self, self._book.path.parent) as dlg:
            dlg.ShowModal()  # GATE-42-OK: nested modal within the publish dialog

    # -- sftp -----------------------------------------------------------------------

    def _on_pick_destination(self) -> None:
        idx = self._dest_pick.GetSelection()
        if not (0 <= idx < len(self._store.destinations)):
            return
        dest = self._store.destinations[idx]
        self._dest_name.SetValue(dest.name)
        self._dest_host.SetValue(dest.host)
        self._dest_port.SetValue(dest.port)
        self._dest_user.SetValue(dest.username)
        self._dest_dir.SetValue(dest.remote_dir)
        self._dest_url.SetValue(dest.url_base)
        self._dest_password.SetValue(self._load_password(dest) or "")

    def _on_save_destination(self) -> None:
        dest = self.collect_destination()
        if not dest.name or not dest.host:
            self._error(str(_("A destination needs at least a name and a host.")))
            return
        existing = self._store.find(dest.name)
        if existing is not None:
            self._store.destinations.remove(existing)
        self._store.destinations.append(dest)
        save_destinations(self._data_dir, self._store)
        password = self._dest_password.GetValue()
        if password:
            self._save_password(dest, password)
        self._dest_pick.Set([d.name for d in self._store.destinations])
        self._announce(_("Saved destination {name}").format(name=dest.name))

    def _load_password(self, dest: SftpDestination) -> str | None:
        try:
            from quill.platform.windows.credential_manager import load_generic_credential

            credential = load_generic_credential(dest.credential_target)
            return credential.secret if credential is not None else None
        except Exception:  # noqa: BLE001 - no credential store on this platform
            return None

    def _save_password(self, dest: SftpDestination, password: str) -> None:
        try:
            from quill.platform.windows.credential_manager import save_generic_credential

            save_generic_credential(dest.credential_target, password, user_name=dest.username)
        except Exception:  # noqa: BLE001
            _log.warning("Could not store the SFTP password in the credential manager")

    def _on_upload(self) -> None:
        from quill.core.publish.sftp_publish import companion_files, publish_files

        dest = self.collect_destination()
        if not dest.host or not dest.username:
            self._error(str(_("Fill in at least the host and username first.")))
            return
        password = self._dest_password.GetValue() or (self._load_password(dest) or "")
        if not password:
            self._error(str(_("Type the password (or save the destination with one).")))
            return
        from quill.core.publish.sftp_publish import PublishCancelled

        files = [self._book.path, *companion_files(self._book.path)]
        book = self._book
        announce = self._announce
        trust = self._trust_first_use
        cancel = threading.Event()
        progress_ui = self._progress_ui(
            str(_("Uploading audiobook")),
            str(_("Connecting to {host}...").format(host=dest.host)),
            cancel,
        )

        def work(progress: Callable[[str, int, int], None]) -> object:
            last_pct = -1

            def on_bytes(name: str, sent: int, total: int) -> None:
                # paramiko reports every block; only surface whole-percent steps
                # so the UI queue (and the screen reader) is never flooded.
                nonlocal last_pct
                pct = int(sent * 100 / total) if total else -1
                if pct == last_pct:
                    return
                last_pct = pct
                label = str(_("Uploading {name}: {pct}%").format(name=name, pct=max(pct, 0)))
                progress_ui.set_progress(pct, label)  # type: ignore[attr-defined]
                progress(label, max(pct, 0), 100)

            try:
                return publish_files(
                    dest,
                    files,
                    password,
                    trust_first_use=trust,
                    on_progress=lambda m: _log.info("publish: %s", m),
                    on_bytes=on_bytes,
                    is_cancelled=cancel.is_set,
                )
            except PublishCancelled:
                return None
            finally:
                progress_ui.close()  # type: ignore[attr-defined]

        def done(result: object) -> str:
            if result is None:
                return str(
                    _("Upload cancelled. Files already completed stay on {host}.").format(
                        host=dest.host
                    )
                )
            count = len(result) if isinstance(result, list) else 0
            return str(
                _("Published {name}: {count} file(s) uploaded to {host}").format(
                    name=book.path.name, count=count, host=dest.host
                )
            )

        announce(str(_("Uploading {name}...").format(name=book.path.name)))
        self._run(str(_("Publishing audiobook")), work, done)

    # -- auphonic ----------------------------------------------------------------------

    def _load_token(self) -> None:
        try:
            from quill.core.publish.auphonic import CREDENTIAL_TARGET
            from quill.platform.windows.credential_manager import load_generic_credential

            credential = load_generic_credential(CREDENTIAL_TARGET)
            if credential is not None:
                self._token.SetValue(credential.secret or "")
        except Exception:  # noqa: BLE001
            pass

    def selected_preset_uuid(self) -> str:
        """The chosen preset's uuid ('' = the account's default preset)."""
        idx = self._preset_pick.GetSelection()
        if idx <= 0 or idx > len(self._presets):
            return ""
        return str(getattr(self._presets[idx - 1], "uuid", ""))

    def _on_check_auphonic(self) -> None:
        """One explicit call: who am I, how many credits, which presets."""
        from quill.core.publish import auphonic

        token = self._token.GetValue().strip()
        if not token:
            self._error(
                str(_("Paste your Auphonic API token first (from your Auphonic account settings)."))
            )
            return

        def work(progress: Callable[[str, int, int], None]) -> object:
            return (auphonic.list_presets(token), auphonic.account_info(token))

        def done(result: object) -> str:
            presets, info = result  # type: ignore[misc]
            self._presets = list(presets)
            self._preset_pick.Set(
                [str(_("(account default preset)"))]
                + [getattr(p, "name", "") or getattr(p, "uuid", "") for p in self._presets]
            )
            self._preset_pick.SetSelection(0)
            self._credits = float(info.credits)
            return str(
                _(
                    "Auphonic account {user}: {credits} credits available,"
                    " {count} preset(s) loaded."
                ).format(
                    user=info.username or _("(unnamed)"),
                    credits=f"{info.credits:g}",
                    count=len(self._presets),
                )
            )

        self._announce(str(_("Checking your Auphonic account...")))
        self._run(str(_("Checking Auphonic account")), work, done)

    def _on_auphonic(self) -> None:
        from quill.core.publish import auphonic

        token = self._token.GetValue().strip()
        if not token:
            self._error(
                str(_("Paste your Auphonic API token first (from your Auphonic account settings)."))
            )
            return
        preset_uuid = self.selected_preset_uuid()
        preset_label = (
            self._preset_pick.GetStringSelection()
            if preset_uuid
            else str(_("your account's default preset"))
        )
        message = _(
            "QUILL will upload {name} to your own Auphonic account for"
            " post-production with {preset} and download the results next"
            " to the book."
        ).format(name=self._book.path.name, preset=preset_label)
        if self._credits is not None:
            message += " " + str(
                _("Your account has {credits} credits.").format(credits=f"{self._credits:g}")
            )
        answer = show_message_box(
            str(message) + " " + str(_("Continue?")),
            str(_("Send to Auphonic")),
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return
        try:
            from quill.core.publish.auphonic import CREDENTIAL_TARGET
            from quill.platform.windows.credential_manager import save_generic_credential

            save_generic_credential(CREDENTIAL_TARGET, token, user_name="auphonic")
        except Exception:  # noqa: BLE001
            _log.warning("Could not store the Auphonic token in the credential manager")
        book = self._book
        cancel = threading.Event()
        progress_ui = self._progress_ui(
            str(_("Auphonic production")),
            str(_("Uploading {name} to Auphonic...").format(name=book.path.name)),
            cancel,
        )

        def work(progress: Callable[[str, int, int], None]) -> object:
            last_pct = -1

            def transfer(verb: str, name: str, moved: int, total: int) -> None:
                nonlocal last_pct
                pct = int(moved * 100 / total) if total else -1
                if pct == last_pct:
                    return
                last_pct = pct
                label = f"{verb} {name}: {max(pct, 0)}%"
                progress_ui.set_progress(pct, label)  # type: ignore[attr-defined]
                progress(label, max(pct, 0), 100)

            try:
                try:
                    production = auphonic.start_production(
                        token,
                        book.path,
                        preset_uuid=preset_uuid,
                        on_bytes=lambda sent, total: transfer(
                            str(_("Uploading")), book.path.name, sent, total
                        ),
                        is_cancelled=cancel.is_set,
                    )
                except auphonic.AuphonicCancelled:
                    return "cancelled-upload"
                # Poll politely until done (or a clear failure); the task pool owns
                # this thread, so sleeping here never touches the UI thread.
                for _attempt in range(360):  # up to ~30 minutes
                    if cancel.is_set():
                        return "cancelled-production"
                    status = auphonic.production_status(token, production)
                    if status.done:
                        last_pct = -1
                        try:
                            return auphonic.download_results(
                                token,
                                status,
                                book.path.parent / f"{book.path.stem} (Auphonic)",
                                on_bytes=lambda name, got, total: transfer(
                                    str(_("Downloading")), name, got, total
                                ),
                                is_cancelled=cancel.is_set,
                            )
                        except auphonic.AuphonicCancelled:
                            return "cancelled-production"
                    if status.failed:
                        raise auphonic.AuphonicError(
                            f"Auphonic reported an error: {status.status_string}"
                        )
                    progress_ui.set_progress(  # type: ignore[attr-defined]
                        -1, str(_("Auphonic: {status}...").format(status=status.status_string))
                    )
                    time.sleep(5.0)
                raise auphonic.AuphonicError("Auphonic did not finish in time; check your account.")
            finally:
                progress_ui.close()  # type: ignore[attr-defined]

        def done(result: object) -> str:
            if result == "cancelled-upload":
                return str(_("Cancelled. The upload was stopped; no production started."))
            if result == "cancelled-production":
                return str(
                    _(
                        "Cancelled. The production continues in your Auphonic account;"
                        " nothing was downloaded."
                    )
                )
            count = len(result) if isinstance(result, list) else 0
            return str(
                _("Auphonic finished: {count} file(s) saved next to the book").format(count=count)
            )

        self._announce(str(_("Sending {name} to Auphonic...").format(name=book.path.name)))
        self._run(str(_("Auphonic production")), work, done)


def open_publish_dialog(frame: object, book: BookFile) -> None:
    """Open the publish dialog for *book* (refused in Safe Mode)."""
    from quill.core.paths import app_data_dir

    if bool(getattr(frame, "_safe_mode", False)):
        frame._show_message_box(  # type: ignore[attr-defined]
            str(_("Publishing is disabled in Safe Mode.")), str(_("Publish Audiobook"))
        )
        return
    settings = getattr(frame, "settings", None)
    dlg = PublishDialog(
        frame.frame,  # type: ignore[attr-defined]
        book,
        data_dir=app_data_dir(),
        announce=getattr(frame, "_announce", None),
        run_background=getattr(frame, "_run_background_task", None),
        trust_first_use=bool(getattr(settings, "ssh_trust_first_use", False)),
    )
    try:
        frame._show_modal_dialog(dlg, str(_("Publish Audiobook")))  # type: ignore[attr-defined]
    finally:
        dlg.Destroy()
