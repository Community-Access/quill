"""Watched folders, live: the host side of qc.md 5d (C2-02).

One mixin, shared by QUILL Cast and QUILL's own podcasts, so both reach the
same Watched Folders window and the same scan. Cast also watches live: the
operating system's directory-change notice (``wx.FileSystemWatcher``) marks a
file as arriving, :class:`~quill.core.podcasts.watched_folders.SettleTracker`
waits until it has stopped growing, and only then is it brought in. A folder on
a network drive, where change notices cannot be trusted, is looked at every ten
minutes instead. A full look runs at launch and after the computer wakes,
because nothing is noticed while Cast is closed or asleep.

The slow work (hash, read the length, copy) runs on the task manager; the
library is only touched back on the UI thread, in :meth:`_apply_folder_plan`.
Safe Mode watches nothing, as it always has for watch folders.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from quill.core.podcasts import watched_folders as wf
from quill.core.podcasts.local_import import SUPPORTED_AUDIO_EXTENSIONS
from quill.core.podcasts.watched_folder_words import arrival_sentence

__all__ = ["FolderWatchMixin"]

#: How often the arriving files are looked at, while any are arriving.
_SETTLE_TICK_MS = 2000


class FolderWatchMixin:
    """Watched folders for any podcast host."""

    # -- the window and its verbs -------------------------------------------------- #

    def open_watched_folders(self) -> None:
        """Podcasts > Watched Folders... (Ctrl+Alt+W in Cast)."""
        from quill.ui.podcasts.watched_folders_window import open_watched_folders_window

        self._migrate_watched_folders()
        open_watched_folders_window(self)

    def add_watched_folder(self, *, parent: Any = None) -> wf.WatchedFolder | None:
        """Choose a folder, then its settings; start watching it."""
        import wx

        from quill.ui.podcasts.watched_folder_settings import edit_folder_settings

        owner = parent or self.frame
        with wx.DirDialog(  # dialog_button_contract: exempt
            owner, "Choose a folder for QUILL Cast to watch", style=wx.DD_DIR_MUST_EXIST
        ) as chooser:
            if chooser.ShowModal() != wx.ID_OK:
                return None
            path = chooser.GetPath()
        library = self._podcast_library
        for existing in library.watched_folders:
            if Path(existing.path) == Path(path):
                self._announce(f"{existing.display_name()} is already watched.")
                return None
        history = getattr(self, "_podcast_history", None)
        folder = wf.WatchedFolder(
            path=path,
            name=Path(path).name,
            original=str(getattr(history, "wf_default_original", "keep")),
            tell=str(getattr(history, "wf_default_tell", "each")),
            min_seconds=int(getattr(history, "wf_default_min_seconds", 30)),
            include_subfolders=bool(getattr(history, "wf_default_subfolders", True)),
        )
        if not edit_folder_settings(self, owner, folder):
            return None
        library.watched_folders.append(folder)
        self._save_podcast_library()
        self._rewatch_folders()
        self._announce(
            f"Watching {folder.display_name()}. Anything that lands there arrives in "
            "Personal Audio by itself. Looking now."
        )
        self.scan_watched_folder_now(folder.id, quiet_when_nothing=True)
        return folder

    def change_watched_folder_settings(
        self, folder: wf.WatchedFolder, *, parent: Any = None
    ) -> bool:
        from quill.ui.podcasts.watched_folder_settings import edit_folder_settings

        if not edit_folder_settings(self, parent or self.frame, folder):
            return False
        wf.set_speed(self._podcast_library, folder)
        self._save_podcast_library()
        self._rewatch_folders()
        self._announce(f"Saved the settings for {folder.display_name()}.")
        return True

    def pause_watched_folder(self, folder_id: str, paused: bool) -> None:
        folder = wf.find(self._podcast_library, folder_id)
        if folder is None:
            return
        folder.paused = paused
        self._save_podcast_library()
        self._rewatch_folders()
        if paused:
            self._announce(
                f"Paused {folder.display_name()}. Nothing new is brought in until you resume."
            )
        else:
            self._announce(f"Watching {folder.display_name()} again.")
            self.scan_watched_folder_now(folder.id, quiet_when_nothing=True)

    def remove_watched_folder(self, folder_id: str, *, parent: Any = None) -> bool:
        import wx

        from quill.ui.dialog_contract import show_message_box

        library = self._podcast_library
        folder = wf.find(library, folder_id)
        if folder is None:
            return False
        answer = show_message_box(
            f"Stop watching {folder.display_name()}? The files already brought in stay "
            "in Personal Audio, and nothing in the folder is touched.",
            "Remove Watched Folder",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            parent or self.frame,
            announce=self._announce,
        )
        if answer != wx.YES:
            return False
        library.watched_folders = [f for f in library.watched_folders if f.id != folder_id]
        self._save_podcast_library()
        self._rewatch_folders()
        self._announce(
            f"No longer watching {folder.display_name()}. Its files stay in Personal Audio."
        )
        return True

    # -- looking -------------------------------------------------------------------------- #

    def scan_watched_podcast_folders(self) -> None:
        """Look at every watched folder now (the old Scan Watched Folders)."""
        self._migrate_watched_folders()
        folders = [f for f in self._podcast_library.watched_folders if not f.paused]
        if not folders:
            self._announce("No folders are being watched. Add one in Watched Folders.")
            return
        for folder in folders:
            self.scan_watched_folder_now(folder.id, quiet_when_nothing=len(folders) > 1)

    def scan_watched_folder_now(self, folder_id: str, *, quiet_when_nothing: bool = False) -> None:
        """Look at one folder on the task manager; arrivals are applied on the UI thread."""
        library = self._podcast_library
        folder = wf.find(library, folder_id)
        if folder is None or getattr(self, "_safe_mode", False):
            return
        busy: set[str] = self.__dict__.setdefault("_folder_scans", set())
        if folder_id in busy:
            return
        busy.add(folder_id)
        known = wf.known_hashes(library)

        def _work(**_kwargs: object) -> wf.Plan:
            return wf.plan(folder, known)

        def _done(_op: str, result: object) -> None:
            busy.discard(folder_id)
            if isinstance(result, wf.Plan):
                self._apply_folder_plan(result, quiet_when_nothing=quiet_when_nothing)

        def _failed(_op: str, error: object) -> None:
            busy.discard(folder_id)
            self._folder_problem(folder, f"{folder.display_name()} could not be read: {error}")

        self._task_manager.submit(
            f"watched-folder-{folder_id}", _work, on_success=_done, on_failure=_failed
        )

    def _apply_folder_plan(self, result: wf.Plan, *, quiet_when_nothing: bool = False) -> None:
        library = self._podcast_library
        folder = wf.find(library, result.folder_id)
        if folder is None:
            return
        if result.problem:
            self._folder_problem(folder, result.problem)
            return
        self.__dict__.setdefault("_folder_problems_said", set()).discard(folder.id)
        added = wf.apply(library, folder, result)
        if result.seen or added:
            self._save_podcast_library()
        if not added:
            if not quiet_when_nothing:
                waiting = (
                    f" {result.still_arriving} still arriving." if result.still_arriving else ""
                )
                self._announce(f"Nothing new in {folder.display_name()}.{waiting}")
            return
        self._arrivals_follow_through(folder, added)
        refresh = getattr(self, "_refresh_place", None)
        if callable(refresh):
            refresh()
        counts = getattr(self, "_refresh_place_counts", None)
        if callable(counts):
            counts()
        window = getattr(self, "_watched_folders_window", None)
        if window is not None and window.frame.IsShown():
            window.refresh(keep=window._list.GetSelection())

    def _arrivals_follow_through(
        self, folder: wf.WatchedFolder, added: list[tuple[Any, Any]]
    ) -> None:
        """Queue or play by the folder's setting, write the notice, and say it."""
        from quill.core import notification_targets
        from quill.core.podcasts import notices
        from quill.core.podcasts import queue as queue_ops

        library = self._podcast_library
        history = getattr(self, "_podcast_history", None)
        if getattr(history, "inbox_personal_audio", False):
            for show, _episode in added:
                show.route_to_inbox = True  # Preferences > The Inbox (qc.md 5d)
        if folder.arrivals in ("queue", "play"):
            for show, episode in added:
                queue_ops.add_to_queue(library, show.id, episode.guid, reason="a watched folder")
            self._save_podcast_library()
        if folder.arrivals == "play":
            controller = getattr(self, "_podcast_controller", None)
            playing = bool(getattr(getattr(controller, "state", None), "episode_guid", ""))
            play = getattr(self, "_play_episode_object", None)
            if not playing and callable(play):
                play(*added[0])
        history = getattr(self, "_podcast_history", None)
        if history is not None:
            count = len(added)
            notices.record(
                history,
                notices.IMPORT_FINISHED,
                title=f"{count} new in {folder.display_name()}",
                body="; ".join(str(ep.title) for _show, ep in added[:10]),
                target=notification_targets.for_show(added[0][0].id),
            )
        said = arrival_sentence(folder, added)
        if said:
            self._announce(said)

    def _folder_problem(self, folder: wf.WatchedFolder, sentence: str) -> None:
        """Say a folder's problem once (until it recovers) and write it down."""
        from quill.ui.podcasts.failure_report import report_failure

        said: set[str] = self.__dict__.setdefault("_folder_problems_said", set())
        first = folder.id not in said
        said.add(folder.id)
        report_failure(
            self,
            f"{sentence} Still watching.",
            subject=folder.display_name(),
            background=True,
            quiet=not first,
        )

    def _migrate_watched_folders(self) -> None:
        library = self._podcast_library
        if wf.migrate(library):
            self._save_podcast_library()

    # -- live watching (QUILL Cast) ------------------------------------------------------ #

    def _start_folder_watching(self) -> None:
        """At launch: migrate, watch, and look once at everything."""
        if getattr(self, "_safe_mode", False):
            return
        self._folder_watching_live = True
        self._migrate_watched_folders()
        self._rewatch_folders()
        for folder in self._podcast_library.watched_folders:
            if not folder.paused:
                self.scan_watched_folder_now(folder.id, quiet_when_nothing=True)

    def _folders_after_resume(self) -> None:
        """After sleep: nothing was noticed while asleep, so look again."""
        if getattr(self, "_safe_mode", False):
            return
        for folder in self._podcast_library.watched_folders:
            if not folder.paused:
                self.scan_watched_folder_now(folder.id, quiet_when_nothing=True)

    def _rewatch_folders(self) -> None:
        """Watch exactly the folders that are on, local ones live, network ones polled."""
        if not getattr(self, "_folder_watching_live", False):
            return
        import wx

        watcher = getattr(self, "_folder_watcher", None)
        if watcher is not None:
            try:
                watcher.RemoveAll()
            except Exception:  # noqa: BLE001
                pass
        polled = False
        for folder in self._podcast_library.watched_folders:
            if folder.paused or not Path(folder.path).is_dir():
                continue
            if wf.is_network_path(folder.path):
                polled = True
                continue
            if watcher is None:
                watcher = wx.FileSystemWatcher()
                watcher.SetOwner(self.frame)
                self.frame.Bind(wx.EVT_FSWATCHER, self._on_folder_change)
                self._folder_watcher = watcher
            name = os.path.join(folder.path, "")  # a directory, as wx wants it
            try:
                if folder.include_subfolders:
                    watcher.AddTree(name)
                else:
                    watcher.Add(name)
            except Exception:  # noqa: BLE001 - the launch scan still covers it
                continue
        poll = getattr(self, "_folder_poll_timer", None)
        if polled and poll is None:
            poll = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda _e: self._poll_network_folders(), poll)
            self._folder_poll_timer = poll
        if poll is not None:
            if polled:
                poll.Start(wf.NETWORK_POLL_MINUTES * 60 * 1000)
            else:
                poll.Stop()

    def _poll_network_folders(self) -> None:
        for folder in self._podcast_library.watched_folders:
            if not folder.paused and wf.is_network_path(folder.path):
                self.scan_watched_folder_now(folder.id, quiet_when_nothing=True)

    def _on_folder_change(self, event: Any) -> None:
        import wx

        path = str(event.GetNewPath() or event.GetPath() or "")
        if Path(path).suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            return
        tracker = getattr(self, "_settle_tracker", None)
        if tracker is None:
            tracker = wf.SettleTracker()
            self._settle_tracker = tracker
        tracker.note(path)
        timer = getattr(self, "_settle_timer", None)
        if timer is None:
            timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda _e: self._on_settle_tick(), timer)
            self._settle_timer = timer
        if not timer.IsRunning():
            timer.Start(_SETTLE_TICK_MS)

    def _on_settle_tick(self) -> None:
        tracker = getattr(self, "_settle_tracker", None)
        if tracker is None:
            return
        settled = tracker.due()
        if not tracker.pending():
            self._settle_timer.Stop()
        wanted: set[str] = set()
        for path in settled:
            for folder in self._podcast_library.watched_folders:
                if not folder.paused and _inside(path, folder.path):
                    wanted.add(folder.id)
        for folder_id in wanted:
            self.scan_watched_folder_now(folder_id, quiet_when_nothing=True)


def _inside(path: str, folder: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
    except (OSError, ValueError):
        return False
    return True
