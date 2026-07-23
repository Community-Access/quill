"""QUILL Audio Studio -- audiobook and audio production as a standalone app.

The Studio wizard, Chapter Workbench, batch narration pipeline, and publish
surfaces are the exact same code QUILL ships (vendored here under the
``quill`` package); this module supplies what a standalone product needs
around them: the home window, menu bar, status bar, system tray, preferences,
voice preview, background-task host, and the entry point.

The frame implements the "MainFrame host protocol" those surfaces expect
(``_show_modal_dialog``, ``_run_background_task``, ``_preview_voice``,
``_announce``, ``settings``, ...) on top of :class:`AppShellFrame`, the same
shell Quill Radio and QUILL Cast are built on.
"""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import wx

from quill import __version__
from quill.core.audio_studio.book_prefs import (
    get_prefs,
    load_prefs,
    save_prefs,
)
from quill.core.audio_studio.book_prefs import (
    set_muted as _set_book_muted,
)
from quill.core.audio_studio.book_prefs import (
    set_volume as _set_book_volume,
)
from quill.core.audio_studio.history import (
    load_history,
    save_history,
)
from quill.core.audio_studio.library import (
    BookEntry,
    add_book,
    load_library,
    save_library,
)
from quill.core.audio_studio.library import (
    record_play as _library_record_play,
)
from quill.core.audio_studio.play_queue import (
    load_queue,
    save_queue,
)
from quill.core.audio_studio.sleep_timer import (
    SleepTimerWatcher,
    load_sleep_setting,
    save_sleep_setting,
)
from quill.core.paths import app_data_dir
from quill.core.settings import save_settings
from quill.ui.app_shell import AppShellFrame
from quill.ui.audio_studio.library_tree import (
    LibraryTreeActions,
    build_library_tree,
    selected_key,
)
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.main_frame_speech_downloads import SpeechDownloadsMixin

try:  # winsound is Windows-only; previews fall back to MCI/startfile elsewhere
    import winsound as _winsound
except ImportError:  # pragma: no cover - non-Windows
    _winsound = None  # type: ignore[assignment]

_TITLE = "QUILL Audio Studio"
_VERSION = __version__
#: Shared components this app requires, for the component-refcount registry
#: (ffmpeg for audio processing/export; mpv is opt-in, not required).
REQUIRED_COMPONENTS: tuple[str, ...] = ("ffmpeg",)
_REPO = "Community-Access/quill-audio-studio"

# Generate Captions accepts these; ffmpeg transcodes them to 16 kHz mono WAV
# before transcription (mirrors QUILL's Tools > Speech caption wildcard).
_AV_EXTS = "*.wav;*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.opus;*.wma;*.mp4;*.m4v;*.mov;*.mkv;*.webm;*.avi"
_AUDIO_VIDEO_WILDCARD = f"Audio/Video ({_AV_EXTS})|{_AV_EXTS}|All files (*.*)|*.*"


class _ProviderAskShim:
    """Adapter so the Chapter Workbench's ``ask(prompt)`` call site needs none
    of the vendored Assistant/agent machinery -- just the cloud-provider chat
    backend. ``ask`` is a blocking call; run it off the UI thread (the Workbench
    already does, via ``run_background``)."""

    def __init__(self, backend: object) -> None:
        self._backend = backend

    def ask(self, prompt: str) -> str:
        return self._backend.respond(prompt)  # type: ignore[attr-defined]


#: Formats the Chapter Workbench can open (mirrors book_file's readers).
_BOOK_WILDCARD = "Audiobooks (*.m4b;*.mp3;*.m4a)|*.m4b;*.mp3;*.m4a|All files (*.*)|*.*"
_AUDIO_WILDCARD = (
    "Audio files (*.wav;*.mp3;*.m4a;*.m4b;*.flac;*.ogg;*.opus)|"
    "*.wav;*.mp3;*.m4a;*.m4b;*.flac;*.ogg;*.opus|All files (*.*)|*.*"
)

_CLOSE_ACTION_LABELS = ("Ask when work is running", "Exit", "Minimize to Tray")
_CLOSE_ACTION_VALUES = ("ask", "exit", "minimize")


# ---------------------------------------------------------------------------
# App-local preferences (window behavior, update checks) live in their own
# small JSON file so the shared %APPDATA%/Quill settings.json stays exactly
# what QUILL wrote. Speech defaults (engine, voices, rates, chapter sound)
# intentionally stay IN the shared settings: configure a voice here and QUILL
# reads aloud with it too, and vice versa.
# ---------------------------------------------------------------------------

_PREFS_FILENAME = "audio-studio-app.json"
_PREFS_DEFAULTS: dict[str, object] = {
    "check_updates_on_startup": True,
    "alt_f4_to_tray": False,
    "close_action": "ask",
    "announce_run_milestones": True,
    "last_update_check": "",
}


def _load_app_prefs() -> dict[str, object]:
    from quill.core.storage import read_json

    prefs = dict(_PREFS_DEFAULTS)
    try:
        data = read_json(app_data_dir() / _PREFS_FILENAME, {})
        if isinstance(data, dict):
            for key in prefs:
                if key in data:
                    prefs[key] = data[key]
    except Exception:  # noqa: BLE001 - unreadable prefs mean defaults, never a crash
        pass
    if prefs["close_action"] not in _CLOSE_ACTION_VALUES:
        prefs["close_action"] = "ask"
    return prefs


def _save_app_prefs(prefs: dict[str, object]) -> None:
    from quill.core.storage import write_json_atomic

    try:
        write_json_atomic(app_data_dir() / _PREFS_FILENAME, prefs)
    except Exception:  # noqa: BLE001 - best-effort; losing a pref beats crashing
        pass


def _sapi5_voice_short_name(voice_id: str) -> str:
    """Normalize a SAPI5 registry voice ID ('...\\TTS_MS_EN-US_DAVID_11.0')
    to the lowercase short name ('david') the preview-sample catalog uses."""
    last = voice_id.replace("/", "\\").rsplit("\\", 1)[-1]
    skip = {"TTS", "MS"}
    for part in last.upper().split("_"):
        if not part or part in skip:
            continue
        if "-" in part:  # language codes: EN-US, EN-GB
            continue
        try:
            float(part)
            continue  # version numbers: 11.0
        except ValueError:
            pass
        if part.isalpha():
            return part.lower()
    return last.lower()


def _wav_duration_seconds(path: Path, *, fallback: float = 12.0) -> float:
    """Length of a PCM wav in seconds; a safe cap when it cannot be read so the
    preview wait loop never blocks the worker indefinitely."""
    try:
        import wave

        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            if rate:
                return frames / float(rate)
    except Exception:  # noqa: BLE001 - an unreadable header degrades to the cap
        pass
    return fallback


def _await_playback(
    *,
    duration: float,
    still_current: Callable[[], bool],
    purge: Callable[[], None],
    sleep: Callable[[float], None],
    now: Callable[[], float],
    poll: float = 0.05,
) -> bool:
    """Wait out an asynchronously-playing preview clip, cutting it short the
    moment it is superseded.

    Returns True if playback was interrupted (Stop pressed / a newer preview
    started): ``purge`` is called to cut the audio. Returns False when the clip
    plays to its natural end. Pure (time and sleep are injected) so the
    interruption logic is unit-tested without winsound or real threads."""
    deadline = now() + duration
    while now() < deadline:
        if not still_current():
            purge()
            return True
        sleep(poll)
    return False


class StudioAppFrame(AppShellFrame, SpeechDownloadsMixin):
    """The standalone QUILL Audio Studio window."""

    #: Voices > Download Optional Components shows only what the audio workflow
    #: uses: the speech engines, the offline dictation/transcription stack (AI
    #: chapter titles), and the ffmpeg/mpv/chapters audio pack. QUILL's
    #: document-editing components (Pandoc, PDF/Office extraction, braille,
    #: MathCAT, Node, spell dictionaries, Git tooling) are hidden -- those
    #: features do not exist in the standalone Studio, so listing them would
    #: only burden users with downloads they cannot use. The downloads mixin
    #: reads this attribute; see _Controller.components in
    #: main_frame_speech_downloads.py.
    _optional_component_allowlist = frozenset({
        "whispercpp",
        "kokoro",
        "piper",
        "espeak",
        "dectalk",
        "audio_extras",
    })

    #: The phrase every voice preview speaks -- also the phrase the bundled
    #: pre-recorded samples say, so "before download" and "after download"
    #: previews are directly comparable.
    _PREVIEW_TEXT = (
        "QUILL is where your words come to life, turning quiet thoughts into "
        "finished pages with a little sprinkle of everyday magic."
    )

    def __init__(self, *, safe_mode: bool = False) -> None:
        # Show Safe Mode in the window title so it is visible and, crucially,
        # spoken by a screen reader on focus -- otherwise the only sign of Safe
        # Mode was a feature silently refusing when the user tried to use it.
        title = f"{_TITLE} (Safe Mode)" if safe_mode else _TITLE
        self._init_app_shell(title, safe_mode=safe_mode, size=(720, 540))
        self._app_prefs = _load_app_prefs()
        self._protected_background_jobs: dict[int, str] = {}
        self._background_task_count = 0
        self._preview_generation = 0
        self._preview_cue_timer = None
        self._library_state = load_library(app_data_dir())
        self._history = load_history(app_data_dir())
        self._book_prefs_store = load_prefs(app_data_dir())
        self._play_queue = load_queue(app_data_dir())
        self._sleep_setting = load_sleep_setting(app_data_dir())
        # A delay-mode sleep timer cannot survive a restart -- its countdown was
        # relative to when it was armed, and no armed-at time is persisted -- so a
        # stale "enabled" delay setting is cleared on launch instead of the Sleep
        # Timer dialog claiming a timer is active with nothing actually armed.
        # End-of-chapter mode is kept: it re-arms from _on_player_ready when a
        # book opens.
        if self._sleep_setting.enabled and not self._sleep_setting.end_of_chapter:
            self._clear_sleep_setting()
        self._active_player: object | None = None
        self._active_book_path: str | None = None
        self._finished_current = False
        self._sleep_watcher = SleepTimerWatcher(on_sleep=lambda: wx.CallAfter(self._on_sleep_fired))
        # End-of-chapter sleep is resolved here (the delay watcher stands down
        # for it): a 1s UI poll watches the active player's chapter index and
        # stops when it advances past the chapter that was playing when the
        # timer was armed. Armed lazily so no timer runs unless it is in use.
        self._sleep_eoc_timer: wx.Timer | None = None
        self._sleep_eoc_from_chapter = -1
        self._build_menu_bar()
        self._build_main_panel()
        self._register_commands()
        self._ensure_tray_icon(self._build_tray_menu, tooltip=_TITLE)
        self._refresh_statusbar()
        # Media keys are grabbed system-wide only while a book is actually open
        # in the Workbench (registered in _on_player_ready, released in
        # _on_book_closed), so an idle Studio no longer swallows the machine's
        # Play/Stop/Next keys from other media apps.
        self._media_key_handlers = {
            "play_pause": self._on_media_play_pause,
            "stop": self._on_media_stop,
            "next": self._on_media_next_chapter,
            "previous": self._on_media_prev_chapter,
        }
        self._media_keys_active = False
        self.frame.Bind(wx.EVT_CLOSE, self._on_app_close)
        # Alt+F4-to-tray (opt-in): intercepted at the char hook, before Windows
        # turns it into a close, so a long narration run keeps going with the
        # window tucked away. The titlebar X and Exit keep close_action.
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        # Deferred (CallAfter), not inline: this touches the network, and a
        # launch is not the place to do that before the window is even up.
        wx.CallAfter(self._maybe_check_updates_on_startup)
        if self._history.resume_on_launch:
            wx.CallAfter(self._maybe_resume_last_book)

    # -- main panel -------------------------------------------------------------
    #
    # A bare frame with only a menu bar leaves keyboard focus with nowhere to
    # land. The home panel gives the app a real, named, tabbable surface: the
    # three journeys as big buttons, then the recent-books list (the library)
    # which takes focus on launch -- Enter re-opens a book for editing.

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        self._activity_text = wx.StaticText(panel, label="Ready")
        set_accessible_name(self._activity_text, "Studio activity")
        root.Add(self._activity_text, 0, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, accessible, handler in (
            (
                "&Narrate Documents...",
                "Narrate a folder of documents into speech audio or an audiobook",
                lambda _e: self.open_studio("documents"),
            ),
            (
                "&Build From Recordings...",
                "Combine a folder of recordings into one chaptered audiobook",
                lambda _e: self.open_studio("audio"),
            ),
            (
                "&Edit a Book...",
                "Open a finished audiobook in the Chapter Workbench: play it, fix "
                "chapters, edit tags, run the ACX check, publish",
                lambda _e: self.open_book_picker(),
            ),
        ):
            button = wx.Button(panel, label=label)
            set_accessible_name(button, accessible)
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)

        library_label = wx.StaticText(panel, label="&Your books:")
        root.Add(library_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._library_tree = wx.TreeCtrl(panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self._library_tree.SetName("Your books")
        set_accessible_name(
            self._library_tree,
            "Your books, grouped by Favorites, In Progress, Recently Played, and "
            "Inbox; Enter opens the selected book in the Chapter Workbench, "
            "Delete removes it, Application key opens the folder menu",
        )
        root.Add(self._library_tree, 1, wx.EXPAND | wx.ALL, 8)
        self._library_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_tree_activate)
        self._library_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._on_tree_context_menu)
        self._library_tree.Bind(wx.EVT_KEY_DOWN, self._on_tree_key)

        panel.SetSizer(root)
        self._main_panel = panel
        self._reload_library_list()
        self._library_tree.SetFocus()

    def _recent_books(self) -> list[Path]:
        from quill.core.recent import recent_audiobook_files

        try:
            return [Path(p) for p in recent_audiobook_files()]
        except Exception:  # noqa: BLE001 - an unreadable MRU is an empty library
            return []

    def _reload_library_list(self) -> None:
        """Rebuild the library tree from the persisted state + recent files.

        Kept under the original list name so the many call sites that refresh
        after a mutation (open, narrate, publish, delete) still work unchanged.
        """
        tree = getattr(self, "_library_tree", None)
        if tree is None:
            return
        keep = selected_key(tree)
        # Inbox pulls from recent files, so re-read the state each reload to
        # pick up newly opened books before they are filed into the library.
        self._library_state = load_library(app_data_dir())
        build_library_tree(tree, self._library_state, keep_key=keep)

    def _selected_book(self) -> Path | None:
        path = self._selected_book_path()
        return Path(path) if path else None

    def _selected_book_path(self) -> str | None:
        tree = getattr(self, "_library_tree", None)
        if tree is None:
            return None
        key = selected_key(tree)
        if key is None or key[0] != "book":
            return None
        return str(key[1])

    def _selected_book_entry(self) -> BookEntry | None:
        """A :class:`BookEntry` for the current selection (real or synthesized).

        Library books resolve to their stored entry; Inbox books (recent files
        not yet filed) synthesize a bare entry so the shared actions work.
        """
        path = self._selected_book_path()
        if path is None:
            return None
        for b in self._library_state.books:
            if b.path == path:
                return b
        tree = self._library_tree
        item = tree.GetSelection()
        title = tree.GetItemText(item) if item.IsOk() else Path(path).stem
        return BookEntry(path=path, title=title)

    def _open_selected_book(self) -> None:
        book = self._selected_book()
        if book is None:
            self._announce("No book selected. Narrate documents or build from recordings first.")
            return
        self.open_book(book)

    @staticmethod
    def _missing_book_announcement(title: str) -> str:
        """The one spoken message for a book whose file is gone, so every path
        (resume, Recently Played, Reveal, auto-advance) says the same thing."""
        return f"{title} is no longer where it was; it may have been moved or renamed."

    def _maybe_resume_last_book(self, **_kw) -> None:
        """Reopen the most recently played book on launch (opt-in flag)."""
        last = self._history.last_played
        if last is None:
            return
        path = Path(last.path)
        if not path.exists():
            # Don't fail silently: tell the user why the last book didn't reopen.
            self._announce(self._missing_book_announcement(path.stem))
            return
        self.open_book(path)

    def _record_play(self, path: Path) -> None:
        """Stamp recently-played history AND ingest the book into the library.

        Opening a book is the primary ingestion point: it adds the file to the
        "Your books" library (promoting it out of the recent-files Inbox) and
        stamps its last-played time so it surfaces under In Progress / Recently
        Played. Without this the library stayed empty no matter how many books
        the user opened.
        """
        import time

        now = time.time()
        try:
            self._history.record(str(path), title=path.stem, position_ms=0, chapter=0)
            save_history(app_data_dir(), self._history)
        except Exception:  # noqa: BLE001 - history is best-effort
            pass
        try:
            add_book(self._library_state, str(path), path.stem, now=now)
            _library_record_play(self._library_state, str(path), now=now)
            self._persist_library()
        except Exception:  # noqa: BLE001 - library ingest is best-effort
            pass

    # -- workbench player observation (media keys, prefs, queue, sleep) -----------

    def _on_player_ready(self, player: object, path: str) -> None:
        """Track the active workbench player and recall its per-book prefs."""
        self._active_player = player
        self._active_book_path = path
        self._finished_current = False
        self._activate_media_keys()  # a book is playing -> media keys are ours
        try:
            player.apply_book_prefs(get_prefs(self._book_prefs_store, path))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - prefs recall is best-effort
            pass
        # If an end-of-chapter sleep timer was armed before a book was open,
        # start watching now that a player exists.
        if self._sleep_setting.enabled and self._sleep_setting.end_of_chapter:
            self._arm_end_of_chapter_watch()

    def _on_book_volume(self, path: str, percent: int) -> None:
        try:
            _set_book_volume(self._book_prefs_store, path, percent)
            save_prefs(app_data_dir(), self._book_prefs_store)
        except Exception:  # noqa: BLE001 - prefs save is best-effort
            pass

    def _on_book_mute(self, path: str, muted: bool) -> None:
        try:
            _set_book_muted(self._book_prefs_store, path, muted)
            save_prefs(app_data_dir(), self._book_prefs_store)
        except Exception:  # noqa: BLE001 - prefs save is best-effort
            pass

    def _next_playable_queue_entry(self, path: str):
        """The next queue entry after the one at ``path`` whose file still
        exists, skipping missing ones (bounded by the queue length). Returns
        ``(index, entry)`` or ``(None, None)`` when nothing playable remains.

        Looking PAST missing files -- and using the same result both to announce
        and to open -- is what stops the auto-advance from promising a book it
        then silently fails to open (a missing next entry used to dead-end after
        "Up next" had already been spoken).
        """
        queue = self._play_queue
        if not queue.entries:
            return None, None
        start = next(
            (i for i, e in enumerate(queue.entries) if e.path == path),
            queue.current_index,
        )
        n = len(queue.entries)
        for step in range(1, n + 1):
            idx = (start + step) % n
            entry = queue.entries[idx]
            if entry.path == path:
                break  # wrapped back to the finished book; nothing else to play
            if Path(entry.path).exists():
                return idx, entry
        return None, None

    def _on_book_finished(self, path: str) -> None:
        """End of book: flag for queue auto-advance and announce the next item."""
        self._finished_current = True
        # Announce the next PLAYABLE queue item (missing files skipped) by
        # peeking -- do not advance here; only the open in _on_book_closed
        # advances, from the same result, so the announcement never lies.
        _idx, entry = self._next_playable_queue_entry(path)
        if entry is not None:
            self._announce(f"Finished. Up next in the queue: {entry.title}")
        else:
            self._announce("End of book.")

    def _on_book_closed(self, path: str, position_ms: int, chapter: int) -> None:
        """Workbench closed: stamp history position and advance the queue."""
        self._active_player = None
        self._active_book_path = None
        self._deactivate_media_keys()  # no book playing -> release the media keys
        self._disarm_end_of_chapter_watch()  # no player left to watch
        try:
            self._history.record(
                path,
                title=Path(path).stem,
                position_ms=position_ms,
                chapter=chapter,
            )
            save_history(app_data_dir(), self._history)
        except Exception:  # noqa: BLE001 - history is best-effort
            pass
        if self._finished_current:
            self._finished_current = False
            idx, entry = self._next_playable_queue_entry(path)
            if entry is not None:
                # Advance the queue pointer to the book we are about to open, so
                # the next finish steps forward from here (single advance). The
                # helper already skipped missing files, so this is playable.
                self._play_queue.current_index = idx
                wx.CallAfter(self.open_book, Path(entry.path))

    # -- media keys ---------------------------------------------------------------

    def _activate_media_keys(self) -> None:
        """Grab the system media keys (idempotent) while a book is playing."""
        if not self._media_keys_active:
            self._register_media_keys(self._media_key_handlers)
            self._media_keys_active = True

    def _deactivate_media_keys(self) -> None:
        """Release the system media keys (idempotent) when nothing is playing."""
        if self._media_keys_active:
            self._unregister_media_keys()
            self._media_keys_active = False

    def _on_media_play_pause(self) -> None:
        if self._active_player is not None:
            self._active_player.play_pause()  # type: ignore[attr-defined]

    def _on_media_stop(self) -> None:
        if self._active_player is not None:
            self._active_player.stop_playback()  # type: ignore[attr-defined]

    def _on_media_next_chapter(self) -> None:
        if self._active_player is not None:
            self._active_player.next_chapter()  # type: ignore[attr-defined]

    def _on_media_prev_chapter(self) -> None:
        if self._active_player is not None:
            self._active_player.previous_chapter()  # type: ignore[attr-defined]

    # -- sleep timer --------------------------------------------------------------

    def _on_sleep_fired(self, **_kw) -> None:
        was_playing = self._active_player is not None
        if was_playing:
            self._active_player.stop_playback()  # type: ignore[attr-defined]
        self._clear_sleep_setting()
        # Don't claim we stopped playback when nothing was playing.
        self._announce("Sleep timer: playback stopped" if was_playing else "Sleep timer ended.")

    def _clear_sleep_setting(self) -> None:
        """Disable and persist the sleep setting after it fires -- a sleep timer
        is one-shot, so it must not stay 'enabled' with nothing armed (the state
        that made the dialog lie about being active across launches)."""
        self._sleep_setting.enabled = False
        try:
            save_sleep_setting(app_data_dir(), self._sleep_setting)
        except Exception:  # noqa: BLE001 - setting save is best-effort
            pass

    def _arm_end_of_chapter_watch(self) -> None:
        """Start (or restart) the 1s poll that stops at the next chapter end.

        No-op without an active player -- it is armed again from
        :meth:`_on_player_ready` when a book opens. Records the chapter the
        playhead is in now; the poll stops playback once it advances past it.
        """
        player = self._active_player
        if player is None:
            return
        try:
            self._sleep_eoc_from_chapter = player.current_chapter_index()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a player without chapters just never fires
            self._sleep_eoc_from_chapter = -1
        if self._sleep_eoc_timer is None:
            self._sleep_eoc_timer = wx.Timer(self.frame)
            self.frame.Bind(
                wx.EVT_TIMER,
                lambda _e: self._poll_end_of_chapter(),
                self._sleep_eoc_timer,
            )
        self._sleep_eoc_timer.Start(1000)

    def _poll_end_of_chapter(self) -> None:
        player = self._active_player
        if player is None:
            self._disarm_end_of_chapter_watch()
            return
        try:
            current = player.current_chapter_index()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - transient; try again next tick
            return
        # The armed chapter has finished once the playhead sits in a later one.
        if current > self._sleep_eoc_from_chapter >= 0:
            self._disarm_end_of_chapter_watch()
            try:
                player.stop_playback()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - stop is best-effort
                pass
            self._clear_sleep_setting()
            self._announce("Sleep timer: stopped at end of chapter")

    def _disarm_end_of_chapter_watch(self) -> None:
        if self._sleep_eoc_timer is not None:
            self._sleep_eoc_timer.Stop()
        self._sleep_eoc_from_chapter = -1

    def _on_sleep_timer(self) -> None:
        from quill.ui.audio_studio.sleep_timer_dialog import SleepTimerDialog

        # If a delay timer is currently running, speak how much is left before
        # opening the dialog -- a remaining-time readout the dialog itself lacks.
        remaining = self._sleep_watcher.remaining_seconds()
        if remaining is not None:
            mins = max(1, round(remaining / 60))
            self._announce(
                f"Sleep timer is on with about {mins} minute{'s' if mins != 1 else ''} left."
            )
        dlg = SleepTimerDialog(self.frame, self._sleep_setting)
        try:
            if dlg.ShowModal() != wx.ID_OK:  # dialog_button_contract: standalone exempt
                return
            self._sleep_setting = dlg.value()
        finally:
            dlg.Destroy()
        try:
            save_sleep_setting(app_data_dir(), self._sleep_setting)
        except Exception:  # noqa: BLE001 - setting save is best-effort
            pass
        if self._sleep_setting.enabled and self._sleep_setting.end_of_chapter:
            # End-of-chapter mode: the delay watcher stands down; the chapter
            # poll does the stop (starting now if a book is playing, else when
            # one next opens).
            self._sleep_watcher.cancel()
            self._arm_end_of_chapter_watch()
            self._announce("Sleep timer on: stop at the end of the chapter")
        elif self._sleep_setting.enabled:
            import time

            self._disarm_end_of_chapter_watch()
            self._sleep_watcher.start(self._sleep_setting, now=time.time())
            self._announce(f"Sleep timer on: {int(self._sleep_setting.delay_minutes)} minutes")
        else:
            self._sleep_watcher.cancel()
            self._disarm_end_of_chapter_watch()
            self._announce("Sleep timer off")

    # -- play queue ---------------------------------------------------------------

    def _on_play_queue(self) -> None:
        from quill.ui.audio_studio.play_queue_dialog import PlayQueueDialog

        dlg = PlayQueueDialog(self.frame, self._play_queue, on_save=self._save_play_queue)
        try:
            dlg.ShowModal()  # dialog_button_contract: standalone exempt
        finally:
            dlg.Destroy()

    def _save_play_queue(self) -> None:
        try:
            save_queue(app_data_dir(), self._play_queue)
        except Exception:  # noqa: BLE001 - queue save is best-effort
            pass

    def _on_mute_toggle(self) -> None:
        if self._active_player is not None:
            self._active_player.toggle_mute()  # type: ignore[attr-defined]
        else:
            self._announce("No book open to mute.")

    def _remove_selected_book(self) -> None:
        entry = self._selected_book_entry()
        if entry is None:
            return
        if LibraryTreeActions.delete_book(
            self.frame, self._library_state, entry, announce=self._announce
        ):
            self._persist_library()

    def _persist_library(self) -> None:
        try:
            save_library(app_data_dir(), self._library_state)
        except Exception:  # noqa: BLE001 - a library save failure is non-fatal
            pass
        self._reload_library_list()

    def _on_tree_activate(self, _event: wx.TreeEvent) -> None:
        self._open_selected_book()

    def _on_tree_key(self, event: wx.KeyEvent) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._open_selected_book()
            return
        if code == wx.WXK_DELETE:
            self._remove_selected_book()
            return
        if code == wx.WXK_WINDOWS_MENU or code == wx.WXK_MENU:
            self._on_tree_context_menu(None)  # type: ignore[arg-type]
            return
        event.Skip()

    def _reveal_book_in_folder(self, entry: BookEntry) -> None:
        """Show the book's file in the OS file manager (Explorer / Finder).

        Replaces the old announce-only "Reveal in Workbench" passthrough, which
        did nothing. Cross-platform and fire-and-forget: Explorer's ``/select``
        opens the folder with the file highlighted (it returns a non-zero exit
        code even on success, so the result is not checked); Finder uses
        ``open -R``; other platforms open the containing folder.
        """
        import subprocess
        import sys

        path = Path(entry.path)
        if not path.exists():
            self._announce(self._missing_book_announcement(entry.title))
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", f"/select,{path}"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path.parent)])
            self._announce(f"Showing {entry.title} in your file manager")
        except Exception:  # noqa: BLE001 - a missing file manager must not crash
            self._announce("Could not open the file manager")

    def _show_library_new_folder_menu(self) -> None:
        """A minimal context menu (just New Folder) shown when no book is
        selected -- otherwise, with an empty library, New Folder lives only on a
        book's context menu and a folder can never be created (6h)."""
        menu = wx.Menu()
        new_folder_id = menu.Append(wx.ID_ANY, "&New Folder...")
        self._keep_menu_ids(new_folder_id.GetId())

        def make_folder(_e: wx.CommandEvent) -> None:
            if LibraryTreeActions.new_folder(
                self.frame, self._library_state, announce=self._announce
            ):
                self._persist_library()

        menu.Bind(wx.EVT_MENU, make_folder, id=new_folder_id.GetId())
        self._library_tree.PopupMenu(menu)
        menu.Destroy()

    def _on_tree_context_menu(self, _event: wx.TreeEvent | None) -> None:
        entry = self._selected_book_entry()
        if entry is None:
            # No book selected (e.g. an empty library): still offer New Folder so
            # folders can be created before any book exists.
            self._show_library_new_folder_menu()
            return
        menu = wx.Menu()
        open_id = menu.Append(wx.ID_ANY, "&Open in Chapter Workbench")
        reveal_id = menu.Append(wx.ID_ANY, "&Reveal in Folder")
        menu.AppendSeparator()
        fav_label = "Remove from &Favorites" if entry.favorite else "Add to &Favorites"
        fav_id = menu.Append(wx.ID_ANY, fav_label)
        move_id = menu.Append(wx.ID_ANY, "&Move to Folder...")
        menu.AppendSeparator()
        new_folder_id = menu.Append(wx.ID_ANY, "&New Folder...")
        menu.AppendSeparator()
        delete_id = menu.Append(wx.ID_ANY, "Remove from &Library")
        tree = self._library_tree

        def run(action: Callable[[], bool]) -> None:
            if action():
                self._persist_library()

        menu.Bind(
            wx.EVT_MENU,
            lambda _e: (
                LibraryTreeActions.open_book(entry, announce=self._announce),
                self.open_book(Path(entry.path)),
            ),
            id=open_id.GetId(),
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: self._reveal_book_in_folder(entry),
            id=reveal_id.GetId(),
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: run(
                lambda: LibraryTreeActions.toggle_favorite(
                    self._library_state, entry, announce=self._announce
                )
            ),
            id=fav_id.GetId(),
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: run(
                lambda: LibraryTreeActions.move_to_folder(
                    self.frame, self._library_state, entry, announce=self._announce
                )
            ),
            id=move_id.GetId(),
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: run(
                lambda: LibraryTreeActions.new_folder(
                    self.frame, self._library_state, announce=self._announce
                )
            ),
            id=new_folder_id.GetId(),
        )
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: self._remove_selected_book(),
            id=delete_id.GetId(),
        )
        self._keep_menu_ids(
            open_id.GetId(),
            reveal_id.GetId(),
            fav_id.GetId(),
            move_id.GetId(),
            new_folder_id.GetId(),
            delete_id.GetId(),
        )
        # PopupMenu takes a position (or none = current pointer / default), NOT
        # a wx.TreeItemId -- passing the selection id raised TypeError and
        # crashed the context menu, including the keyboard Applications-key path.
        # A book is selected here (we returned early otherwise), so pop at the
        # default position and always destroy the menu so it never leaks.
        tree.PopupMenu(menu)
        menu.Destroy()

    # -- menu bar ---------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu_bar = wx.MenuBar()

        studio = wx.Menu()
        open_id, narrate_id, build_id, edit_id, open_book_id, job_id = (
            wx.NewIdRef() for _ in range(6)
        )
        prefs_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        narrate_translated_id = wx.NewIdRef()
        studio.Append(open_id, "&Open Audio Studio...\tCtrl+N", "Open the Studio wizard")
        studio.AppendSeparator()
        studio.Append(narrate_id, "Narrate &Documents...", "Documents to speech audio or a book")
        studio.Append(
            narrate_translated_id,
            "Narrate a Document in Another &Language...",
            "Translate one document and speak it in the languages you choose",
        )
        studio.Append(build_id, "&Build From Recordings...", "Recordings to a chaptered book")
        studio.Append(edit_id, "&Edit a Book...", "Open a book in the Chapter Workbench")
        studio.AppendSeparator()
        studio.Append(open_book_id, "Open Boo&k File...\tCtrl+O")
        studio.Append(job_id, "Open &Job File...", "Re-run a saved .quilljob")
        studio.AppendSeparator()
        self._recent_submenu = wx.Menu()
        self._rebuild_recent_submenu(self._recent_submenu)
        studio.AppendSubMenu(self._recent_submenu, "Re&cently Played")
        self._resume_menu_item_id = wx.NewIdRef()
        studio.AppendCheckItem(
            self._resume_menu_item_id,
            "Resume Last Book on La&unch",
            "Reopen the most recently played book when the Studio starts",
        )
        studio.Check(self._resume_menu_item_id, self._history.resume_on_launch)
        studio.AppendSeparator()
        studio.Append(prefs_id, "&Preferences...\tCtrl+,")
        studio.AppendSeparator()
        studio.Append(exit_id, "E&xit")
        menu_bar.Append(studio, "&Studio")
        # Rebuild the Recently Played list each time the Studio menu opens so
        # it reflects books opened this session, not just at launch.
        self.frame.Bind(wx.EVT_MENU_OPEN, self._on_studio_menu_open)

        book = wx.Menu()
        publish_id, feed_id, acx_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        sleep_id, mute_id, queue_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        book.Append(publish_id, "&Publish a Finished Book...", "Local feed, SFTP, or Auphonic")
        book.Append(feed_id, "&Make a Podcast Feed From a Folder...")
        book.AppendSeparator()
        book.Append(acx_id, "&ACX Compliance Check...", "Measure a file against ACX limits")
        book.AppendSeparator()
        book.Append(sleep_id, "Sleep &Timer...", "Stop playback after a delay")
        book.Append(mute_id, "M&ute Playback\tCtrl+M", "Mute or unmute the active book")
        book.Append(queue_id, "Play &Queue...", "Queue books to play in order")
        menu_bar.Append(book, "&Book Tools")

        voices = wx.Menu()
        hub_id, models_id, components_id, ffmpeg_id = (wx.NewIdRef() for _ in range(4))
        pronunciation_id, captions_id = (wx.NewIdRef() for _ in range(2))
        voices.Append(hub_id, "Speech &Hub (Voices and Engines)...")
        voices.Append(models_id, "&Manage Speech Models...")
        voices.Append(
            pronunciation_id,
            "&Pronunciation Dictionaries...",
            "Teach the voices names and jargon; applied to every narration run",
        )
        voices.Append(
            captions_id,
            "Generate &Captions (Offline)...",
            "Transcribe an audio or video file to .srt or .vtt captions on this machine",
        )
        voices.AppendSeparator()
        voices.Append(components_id, "&Download Optional Components...")
        voices.Append(ffmpeg_id, "&Get FFmpeg...")
        menu_bar.Append(voices, "&Voices")

        ai = wx.Menu()
        ai_setup_id = wx.NewIdRef()
        ai.Append(
            ai_setup_id,
            "Set &Up AI...",
            "Connect an AI provider for cloud voices, chapter titles, and translation",
        )
        menu_bar.Append(ai, "&AI")

        help_menu = wx.Menu()
        guide_id, prd_id, notes_id, palette_id = (wx.NewIdRef() for _ in range(4))
        updates_id, bug_id, about_id = (wx.NewIdRef() for _ in range(3))
        log_id, diag_id = (wx.NewIdRef() for _ in range(2))
        help_menu.Append(guide_id, "User &Guide")
        help_menu.Append(prd_id, "&Product Requirements (PRD)")
        help_menu.Append(notes_id, "&Release Notes")
        help_menu.AppendSeparator()
        help_menu.Append(palette_id, "&Command Palette...\tCtrl+Shift+P")
        help_menu.AppendSeparator()
        help_menu.Append(updates_id, "Check for &Updates...")
        help_menu.Append(bug_id, "Report a &Bug...")
        help_menu.Append(log_id, "View &Log...")
        help_menu.Append(diag_id, "Save &Diagnostics...")
        help_menu.AppendSeparator()
        help_menu.Append(about_id, f"&About {_TITLE}")
        menu_bar.Append(help_menu, "&Help")

        self.frame.SetMenuBar(menu_bar)
        bindings: list[tuple[object, Callable[[], None]]] = [
            (open_id, self.open_studio),
            (narrate_id, lambda: self.open_studio("documents")),
            (narrate_translated_id, self.export_translated_speech),
            (build_id, lambda: self.open_studio("audio")),
            (edit_id, self.open_book_picker),
            (open_book_id, self.open_book_picker),
            (job_id, self.open_job_file),
            (self._resume_menu_item_id, self._toggle_resume_on_launch),
            (prefs_id, self._open_preferences),
            (exit_id, self.frame.Close),
            (publish_id, self.publish_book),
            (feed_id, self.make_podcast_feed),
            (acx_id, self.run_acx_check),
            (sleep_id, self._on_sleep_timer),
            (mute_id, self._on_mute_toggle),
            (queue_id, self._on_play_queue),
            (hub_id, self.choose_read_aloud_configuration),
            (models_id, self.open_speech_models),
            (pronunciation_id, self.open_pronunciation_dictionaries),
            (captions_id, self.generate_captions_offline),
            (components_id, self.open_optional_components),
            (ffmpeg_id, self.download_ffmpeg_component),
            (ai_setup_id, self.open_ai_setup),
            (guide_id, lambda: self._open_studio_doc("userguide")),
            (prd_id, lambda: self._open_studio_doc("prd")),
            (notes_id, lambda: self._open_studio_doc("release-notes-1.0")),
            (palette_id, self.open_command_palette),
            (updates_id, self.check_updates_manual),
            (bug_id, lambda: self.report_app_bug(source_app=_TITLE, app_version=_VERSION)),
            (log_id, self._view_log),
            (diag_id, self.save_diagnostics_bundle),
            (about_id, self._show_about),
        ]
        for item_id, handler in bindings:
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
        self._keep_menu_ids(*(item_id for item_id, _ in bindings))

    def _rebuild_recent_submenu(self, submenu: wx.Menu) -> None:
        """Populate *submenu* from the recently-played history (newest first)."""
        for item in submenu.GetMenuItems():
            submenu.Delete(item)
        books = list(self._history.books)
        if not books:
            empty = submenu.Append(wx.ID_ANY, "(empty)")
            empty.Enable(False)
            self._keep_menu_ids(empty.GetId())
            return
        recent_ids: list[object] = []
        for book in books:
            item_id = wx.NewIdRef()
            submenu.Append(item_id, book.title)
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, p=book.path: self._open_history_book(p),
                id=item_id,
            )
            recent_ids.append(item_id)
        self._keep_menu_ids(*recent_ids)

    def _open_history_book(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            self._announce(self._missing_book_announcement(p.stem))
            return
        self.open_book(p)

    def _on_studio_menu_open(self, event: wx.MenuEvent) -> None:
        # Refresh the Recently Played list + resume-check state when the
        # Studio menu opens; ignore other menus (the event fires for each).
        if event.GetMenu() is not self.frame.GetMenuBar().GetMenu(0):
            event.Skip()
            return
        self._rebuild_recent_submenu(self._recent_submenu)
        self.frame.GetMenuBar().Check(self._resume_menu_item_id, self._history.resume_on_launch)
        event.Skip()

    def _toggle_resume_on_launch(self) -> None:
        self._history.resume_on_launch = not self._history.resume_on_launch
        try:
            save_history(app_data_dir(), self._history)
        except Exception:  # noqa: BLE001 - history save is best-effort
            pass
        state = "on" if self._history.resume_on_launch else "off"
        self._announce(f"Resume last book on launch: {state}")

    def _build_menu(self) -> None:
        """SpeechDownloadsMixin calls this after installing a component to
        refresh menu state; the Studio's menus carry no engine-dependent
        labels, so refreshing the home panel is all that's needed."""
        self._refresh_statusbar()

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        studio_id, resume_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(studio_id, "Open Audio Studio...")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: (self._restore_from_tray(), self.open_studio()),
            id=studio_id,
        )
        books = self._recent_books()
        if books:
            menu.Append(resume_id, f"Resume: {books[0].stem}")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e, b=books[0]: (self._restore_from_tray(), self.open_book(b)),
                id=resume_id,
            )
        self._keep_menu_ids(studio_id, resume_id)

    def _register_commands(self) -> None:
        for command_id, title, handler in (
            ("studio.open", "Open Audio Studio...", self.open_studio),
            ("studio.narrate", "Narrate Documents...", lambda: self.open_studio("documents")),
            (
                "studio.narrate_translated",
                "Narrate a Document in Another Language...",
                self.export_translated_speech,
            ),
            ("studio.build", "Build From Recordings...", lambda: self.open_studio("audio")),
            ("studio.edit", "Edit a Book...", self.open_book_picker),
            ("studio.open_job", "Open Job File...", self.open_job_file),
            ("studio.publish", "Publish a Finished Book...", self.publish_book),
            ("studio.feed", "Make a Podcast Feed From a Folder...", self.make_podcast_feed),
            ("studio.acx", "ACX Compliance Check...", self.run_acx_check),
            ("studio.sleep_timer", "Sleep Timer...", self._on_sleep_timer),
            ("studio.mute", "Mute Playback", self._on_mute_toggle),
            ("studio.play_queue", "Play Queue...", self._on_play_queue),
            (
                "studio.speech_hub",
                "Speech Hub (Voices and Engines)...",
                self.choose_read_aloud_configuration,
            ),
            ("studio.models", "Manage Speech Models...", self.open_speech_models),
            (
                "studio.pronunciation",
                "Pronunciation Dictionaries...",
                self.open_pronunciation_dictionaries,
            ),
            ("studio.captions", "Generate Captions (Offline)...", self.generate_captions_offline),
            (
                "studio.components",
                "Download Optional Components...",
                self.open_optional_components,
            ),
            ("studio.ai_setup", "Set Up AI...", self.open_ai_setup),
            ("studio.preferences", "Preferences...", self._open_preferences),
            ("studio.updates", "Check for Updates...", self.check_updates_manual),
        ):
            self.commands.register(command_id, title, handler)

    # -- journeys -----------------------------------------------------------------

    def open_studio(self, journey: str | None = None) -> None:
        """Open the Studio wizard; *journey* pre-selects a first page.

        The wizard itself persists ``audio_studio_last_journey``, so seeding it
        here keeps the 'reopens where you were' promise consistent whether the
        user came through the wizard's own radio or a menu shortcut.
        """
        from quill.ui.batch_speech_runner import run_batch_export_to_speech

        if journey:
            try:
                self.settings.audio_studio_last_journey = journey
            except Exception:  # noqa: BLE001 - a stale settings object still opens
                pass
        run_batch_export_to_speech(self)
        self._reload_library_list()

    def export_translated_speech(self) -> None:
        """Studio > Narrate a Document in Another Language...: pick one document,
        choose target languages, and export translated speech audio beside it.

        Translation needs an AI provider or LibreTranslate, so it is unavailable
        in Safe Mode (the same gate as other AI surfaces)."""
        if self._safe_mode:
            self._show_message_box(
                "Translation needs an AI provider or LibreTranslate, which are off "
                "in Safe Mode. Restart without Safe Mode to narrate a document in "
                "another language.",
                "Narrate a Document in Another Language",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        from quill.ui.audio_studio.translated_speech_export import (
            run_translated_speech_export,
        )

        run_translated_speech_export(self)

    def open_book_picker(self) -> None:
        """Edit a Book: straight to a file picker, then the Chapter Workbench."""
        default_dir = ""
        books = self._recent_books()
        if books and books[0].parent.is_dir():
            default_dir = str(books[0].parent)
        with wx.FileDialog(
            self.frame,
            "Open a book to edit",
            defaultDir=default_dir,
            wildcard=_BOOK_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        self.open_book(path)

    def open_book(self, path: Path) -> None:
        from quill.ui.audio_studio.chapter_workbench import open_book_in_workbench

        if not path.exists():
            self._show_message_box(
                f"That book is no longer at:\n{path}\n\nIt may have been moved or renamed.",
                "Open Book",
                wx.ICON_WARNING | wx.OK,
            )
            self._reload_library_list()
            return
        open_book_in_workbench(
            self,
            path,
            on_player_ready=self._on_player_ready,
            on_finished=self._on_book_finished,
            on_volume=self._on_book_volume,
            on_mute=self._on_book_mute,
            on_closed=self._on_book_closed,
            # 6c: reachable inside the modal Workbench while a book plays.
            on_sleep_timer=self._on_sleep_timer,
            on_play_queue=self._on_play_queue,
        )
        self._record_play(path)
        self._reload_library_list()

    def open_job_file(self) -> None:
        """Open a saved .quilljob and land in the wizard with every page pre-filled."""
        from quill.core.speech.job_file import JOB_EXTENSION, JobFileError, load_job
        from quill.ui import batch_speech_runner as runner

        wildcard = f"QUILL job files (*{JOB_EXTENSION})|*{JOB_EXTENSION}|All files (*.*)|*.*"
        with wx.FileDialog(
            self.frame,
            "Open a job file",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            request = load_job(path, runner._defaults(self))
        except JobFileError as error:
            self._show_message_box(str(error), "Open Job File", wx.ICON_ERROR | wx.OK)
            return
        self._open_studio_with_defaults(request)

    def _open_studio_with_defaults(self, defaults: object) -> None:
        """The show_audio_studio loop, seeded with *defaults* (a loaded job).

        Mirrors ``quill.ui.audio_studio.show_audio_studio`` (job-reload loop,
        edit-journey dispatch) and then the runner's own post-wizard steps, so
        Studio > Open Job File... behaves exactly like loading the job from the
        wizard's first page -- just one dialog sooner.
        """
        from quill.ui import batch_speech_runner as runner
        from quill.ui.audio_studio.wizard import RELOAD_WITH_JOB, AudioStudioWizard

        def on_preview(engine: str, voice: str) -> None:
            if voice:
                self._preview_voice(engine, voice)
            else:
                self._announce("Choose a voice to preview")

        while True:
            dlg = AudioStudioWizard(
                self.frame,
                defaults=defaults,
                engine_options=runner._ENGINE_OPTIONS,
                engine_available=runner._engine_available(self),
                voices_for=runner._voices_for,
                on_preview=on_preview,
                announce_cb=self._announce,
                initial_journey="documents",
            )
            try:
                code = self._show_modal_dialog(dlg, "QUILL Audio Studio")
                if code == RELOAD_WITH_JOB and dlg.loaded_job is not None:
                    defaults = dlg.loaded_job
                    continue
                edit_path = dlg.edit_path() if code == wx.ID_OK else None
                request = dlg.result() if code == wx.ID_OK else None
            finally:
                dlg.Destroy()
            break
        if edit_path is not None:
            self.open_book(Path(edit_path))
            return
        if request is None:
            self._announce("Audio Studio cancelled")
            return
        runner._remember_sources(request)
        runner._persist_choices(self, request)
        runner._save_project_profile(self, request)
        runner._run(self, request)
        self._reload_library_list()

    # -- book tools ---------------------------------------------------------------

    def publish_book(self) -> None:
        from quill.core.speech.book_file import BookReadError, read_book
        from quill.ui.audio_studio.publish_dialog import open_publish_dialog

        book_path = self._selected_book()
        with wx.FileDialog(
            self.frame,
            "Choose the finished book to publish",
            defaultDir=str(book_path.parent) if book_path else "",
            defaultFile=book_path.name if book_path else "",
            wildcard=_BOOK_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        try:
            book = read_book(path)
        except BookReadError as error:
            self._show_message_box(str(error), "Publish a Finished Book", wx.ICON_ERROR | wx.OK)
            return
        open_publish_dialog(self, book)

    def make_podcast_feed(self) -> None:
        from quill.ui.audio_studio.feed_dialog import FolderFeedDialog

        if self._safe_mode:
            self._announce("Publishing is disabled in Safe Mode.")
            return
        with wx.DirDialog(self.frame, "Choose the folder of episodes") as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            folder = Path(dialog.GetPath())
        feed_dialog = FolderFeedDialog(self.frame, folder)
        self._show_modal_dialog(feed_dialog, "Make a Podcast Feed")
        feed_dialog.Destroy()

    def run_acx_check(self) -> None:
        """Measure any audio file against the ACX submission window."""
        from quill.core.speech.ffmpeg import ffmpeg_available

        if not ffmpeg_available():
            self._show_message_box(
                "The ACX check measures loudness with FFmpeg, which looks "
                "missing. Choose Voices > Get FFmpeg... first.",
                "ACX Compliance Check",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        with wx.FileDialog(
            self.frame,
            "Choose the audio file to measure",
            wildcard=_AUDIO_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())

        def _measure(_progress: Callable[[str, int, int], None]) -> object:
            from quill.core.speech.loudness import acx_check_file

            return acx_check_file(path)

        def _report(result: object) -> None:
            if result is None:
                self._show_message_box(
                    f"Could not measure {path.name}. The file may not be a readable audio file.",
                    "ACX Compliance Check",
                    wx.ICON_WARNING | wx.OK,
                )
                return
            lines = [
                f"{path.name}",
                "",
                f"Integrated loudness: {result.integrated_lufs:.1f} LUFS "
                f"({'OK' if result.loudness_ok else 'outside the ACX window'})",
                f"True peak: {result.true_peak_db:.1f} dBFS "
                f"({'OK' if result.peak_ok else 'too hot'})",
                f"Noise floor: {result.noise_floor_db:.1f} dBFS "
                f"({'OK' if result.noise_ok else 'too noisy'})",
                "",
            ]
            if result.ok:
                lines.append("This file passes the ACX technical checks.")
            else:
                lines.append("Recommendations:")
                lines.extend(f"- {rec}" for rec in result.recommendations())
            self._show_message_box(
                "\n".join(lines),
                "ACX Compliance Check",
                (wx.ICON_INFORMATION if result.ok else wx.ICON_WARNING) | wx.OK,
            )

        self._run_background_task(f"Measuring {path.name}", _measure, _report)

    # -- AI -----------------------------------------------------------------------

    def open_ai_setup(self) -> None:
        if self._safe_mode:
            self._announce("AI is disabled in Safe Mode.")
            return
        from quill.ui.ai_setup_wizard import run_ai_setup_wizard

        run_ai_setup_wizard(self)

    def _get_assistant(self) -> object:
        """Thin ask-shim for AI chapter titles (Chapter Workbench).

        The Studio only needs the cloud-provider chat path -- it does not vend
        the full Assistant/agent stack. ``ProviderChatBackend`` routes the
        single ``ask`` call through the user's configured provider; when no
        provider is configured ``respond`` raises, and ``propose_chapter_titles``
        catches that and keeps each chapter's existing title (see
        ``core/speech/chapter_titles.py``).
        """
        shim = getattr(self, "_assistant", None)
        if shim is None:
            from quill.core.ai.provider_backend import ProviderChatBackend

            backend = ProviderChatBackend()
            shim = _ProviderAskShim(backend)
            self._assistant = shim
        return shim

    def _get_openai_api_key(self) -> str:
        try:
            from quill.core.assistant_ai import load_keyed_provider_api_key

            return load_keyed_provider_api_key("openai")
        except Exception:  # noqa: BLE001
            return ""

    def _get_gemini_api_key(self) -> str:
        try:
            from quill.core.assistant_ai import load_provider_api_key

            return load_provider_api_key("gemini") or ""
        except Exception:  # noqa: BLE001
            return ""

    def _get_elevenlabs_api_key(self) -> str:
        try:
            from quill.platform.windows.credential_manager import load_generic_credential

            stored = load_generic_credential("ElevenLabs API key")
            return (stored.secret if stored else "") or ""
        except Exception:  # noqa: BLE001
            return ""

    # -- speech hub / registry (ports of the MainFrame speech accessors) ----------

    def _speech_registry(self) -> object:
        from quill.core.speech.service import default_registry

        configured = str(getattr(self.settings, "speech_whisper_path", "") or "") or None
        return default_registry(configured)

    def _configured_speech_provider(self, registry: object | None = None) -> object:
        from quill.core.speech.service import DEFAULT_PROVIDER_ID

        reg = registry if registry is not None else self._speech_registry()
        chosen = str(getattr(self.settings, "speech_provider", "") or "")
        if chosen:
            provider = reg.get(chosen)  # type: ignore[attr-defined]
            if provider is not None:
                return provider
        return reg.get(DEFAULT_PROVIDER_ID)  # type: ignore[attr-defined]

    def _speech_provider(self) -> object:
        """The offline transcription engine to actually run with: the user's
        chosen provider when it is ready, else the bundled whisper.cpp default.

        Unlike :meth:`_configured_speech_provider` (which keeps the chosen engine
        even when it is not ready, so Manage Speech Models opens on it), this
        honors the availability fallback so captioning always works -- a
        near-verbatim port of MainFrame's ``_speech_provider``."""
        from quill.core.speech.service import DEFAULT_PROVIDER_ID

        registry = self._speech_registry()
        chosen = str(getattr(self.settings, "speech_provider", "") or "")
        if chosen:
            provider = registry.get(chosen)  # type: ignore[attr-defined]
            try:
                if provider is not None and provider.is_available():
                    return provider
            except Exception:  # noqa: BLE001 - fall back to the bundled engine
                pass
        return registry.get(DEFAULT_PROVIDER_ID)  # type: ignore[attr-defined]

    def _installed_or_prompt(self, provider: object, title: str) -> list | None:
        """Return the provider's installed models, or None after offering to open
        Manage Speech Models to download one."""
        wx = self._wx
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if installed:
            return installed
        offer = self._show_message_box(
            "No offline speech model is installed yet. Open Manage Speech Models to download one?",
            title,
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if offer == wx.YES:
            self.open_speech_models()
        return None

    def _default_model_id(self, installed: list) -> str:
        """The model id to transcribe with: the user's explicit default when it
        is actually installed, else the catalog's recommended model, else the
        first installed model."""
        from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

        ids = [m.id for m in installed]
        preferred = str(getattr(self.settings, "speech_default_model_id", "") or "")
        if preferred and preferred in ids:
            return preferred
        return RECOMMENDED_MODEL_ID if RECOMMENDED_MODEL_ID in ids else ids[0]

    def generate_captions_offline(self) -> None:
        """Transcribe an audio/video file to timed captions on this machine, then
        save them as .srt or .vtt -- a faithful port of QUILL's Tools > Speech >
        Generate Captions (Offline). Disabled in Safe Mode."""
        wx = self._wx
        if bool(getattr(self, "_safe_mode", False)):
            self._announce("Generating captions is disabled in Safe Mode.")
            return
        provider = self._speech_provider()
        installed = self._installed_or_prompt(provider, "Generate Captions")
        if installed is None:
            return
        model_id = self._default_model_id(installed)
        with wx.FileDialog(
            self.frame,
            "Choose an audio or video file to caption",
            wildcard=_AUDIO_VIDEO_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(
            source_path=source, model_id=model_id, output_timestamps=True
        )

        def _work(progress):
            def _on_progress(fraction: float, message: str) -> None:
                progress(message, int(fraction * 100), 100)

            return provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]

        self._run_background_task(
            f"Captioning {source.name}", _work, lambda result: self._save_captions(result, source)
        )

    def _save_captions(self, result: object, source: Path) -> None:
        from quill.core.speech import formatters

        wx = self._wx
        segments = getattr(result, "segments", ()) or ()
        if not segments:
            self._announce("No timed segments were produced, so captions cannot be made.")
            return
        formats = ["SubRip captions (.srt)", "WebVTT captions (.vtt)"]
        with wx.SingleChoiceDialog(
            self.frame, "Caption format:", "Generate Captions", formats
        ) as dialog:
            if self._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
                return
            choice = dialog.GetSelection()
        if choice == 0:
            text, ext = formatters.to_srt(segments), ".srt"
        else:
            text, ext = formatters.to_vtt(segments), ".vtt"
        with wx.FileDialog(
            self.frame,
            "Save captions",
            defaultFile=f"{source.stem}{ext}",
            wildcard="Caption files (*.srt;*.vtt)|*.srt;*.vtt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save captions") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        target.write_text(text, encoding="utf-8", newline="\n")
        self._announce(f"Captions saved to {target.name}.")

    def choose_read_aloud_configuration(self) -> None:
        """Open the unified Speech Hub on the Speech (Offline) tab."""
        from quill.ui.speech_hub_dialog import TAB_SPEECH_OFFLINE

        self.open_speech_hub(TAB_SPEECH_OFFLINE)

    def open_speech_hub(self, initial_tab: int = 0) -> None:  # noqa: PLR0912,PLR0915
        """The unified Speech Hub: voices and engines, offline and online.

        A near-verbatim port of MainFrame's hub launcher; the one deliberate
        difference is the 'Export to audio' action, which here opens the Audio
        Studio wizard (this app's whole reason to exist) instead of QUILL's
        single-document export.
        """
        from quill.core.ai import elevenlabs_tts
        from quill.core.read_aloud import (
            default_piper_model_dir,
            discover_dectalk_executable,
            discover_espeak_executable,
            discover_piper_executable,
            kokoro_engine_ready,
            macos_say_available,
        )
        from quill.core.speech.engine_install import (
            is_faster_whisper_available,
            is_kokoro_onnx_available,
            is_vosk_available,
            kokoro_onnx_install_supported,
            vosk_install_supported,
        )
        from quill.core.speech.ffmpeg import ffmpeg_available
        from quill.core.speech.providers.whispercpp import resolve_whisper_executable
        from quill.core.speech.service import (
            describe_models,
            detect_has_gpu,
            detect_total_ram_gb,
            machine_summary,
        )
        from quill.ui.speech_hub_dialog import SpeechHubDialog

        elevenlabs_ready = (
            bool(self._get_elevenlabs_api_key().strip()) and elevenlabs_tts.available()
        )
        offline_engine_options: list[tuple[str, str]] = [
            ("Windows (SAPI 5)", "sapi5"),
            ("DECtalk", "dectalk"),
            ("Piper (neural, offline)", "piper"),
            ("Kokoro (neural, offline)", "kokoro"),
            ("eSpeak-NG (many languages)", "espeak"),
        ]
        if macos_say_available():
            offline_engine_options.append(("macOS (system voice)", "macos"))
        online_engine_options: list[tuple[str, str]] = [
            ("ElevenLabs (premium cloud)", "elevenlabs"),
        ]
        offline_engine_available = {
            "sapi5": True,
            "dectalk": discover_dectalk_executable(self.settings.read_aloud_dectalk_executable)
            is not None,
            "piper": discover_piper_executable() is not None,
            "kokoro": kokoro_engine_ready(),
            "espeak": discover_espeak_executable(self.settings.read_aloud_espeak_executable)
            is not None,
            "macos": macos_say_available(),
        }
        online_engine_available = {"elevenlabs": elevenlabs_ready}
        configured_engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
        offline_current_engine = (
            configured_engine
            if configured_engine in {val for _, val in offline_engine_options}
            else "sapi5"
        )
        common_ra_kwargs: dict = {
            "piper_model_dir": default_piper_model_dir(),
            "settings": self.settings,
            "preview_fn": self._preview_voice,
            "preview_stop_fn": self._stop_active_voice_preview,
            "elevenlabs_api_key": self._get_elevenlabs_api_key() if elevenlabs_ready else "",
            "has_preview_sample": (
                lambda eng, vid: self._voice_preview_sample_path(eng, vid) is not None
            ),
        }
        read_aloud_offline_kwargs: dict = {
            "engine_options": offline_engine_options,
            "current_engine": offline_current_engine,
            "engine_available": offline_engine_available,
            **common_ra_kwargs,
        }
        read_aloud_online_kwargs: dict = {
            "engine_options": online_engine_options,
            "current_engine": "elevenlabs",
            "engine_available": online_engine_available,
            **common_ra_kwargs,
        }

        registry = self._speech_registry()
        all_providers = list(registry.all())  # type: ignore[attr-defined]
        provider = self._configured_speech_provider(registry)
        total_ram = detect_total_ram_gb()
        has_gpu = detect_has_gpu()
        rows = describe_models(provider, total_ram, has_gpu)  # type: ignore[arg-type]
        common_dict_kwargs: dict = {
            "machine_summary": machine_summary(total_ram, has_gpu),
            "whispercpp_ok": resolve_whisper_executable() is not None,
            "ffmpeg_ok": ffmpeg_available(),
            "engine_ok": is_faster_whisper_available(),
            "vosk_ok": is_vosk_available(),
            "vosk_can_install": vosk_install_supported(),
            "kokoro_ok": is_kokoro_onnx_available(),
            "kokoro_can_install": kokoro_onnx_install_supported(),
            "all_providers": all_providers,
            "total_ram": total_ram,
            "has_gpu": has_gpu,
            "default_provider_id": str(getattr(self.settings, "speech_provider", "") or ""),
            "announce_cb": self._announce,
        }
        dictation_offline_kwargs: dict = {
            "provider": provider,
            "rows": rows,
            "engine_scope": "offline",
            **common_dict_kwargs,
        }
        known_offline_ids = {"whispercpp", "fasterwhisper", "vosk"}
        cloud_providers = [
            p for p in all_providers if str(getattr(p, "id", "")) not in known_offline_ids
        ]
        dictation_online_kwargs: dict | None = None
        if cloud_providers:
            cloud_provider = (
                next((p for p in cloud_providers if getattr(p, "id", "") == provider.id), None)
                or cloud_providers[0]
            )
            dictation_online_kwargs = {
                "provider": cloud_provider,
                "rows": describe_models(cloud_provider, total_ram, has_gpu),  # type: ignore[arg-type]
                "engine_scope": "online",
                **common_dict_kwargs,
            }

        hub = SpeechHubDialog(
            self.frame,
            read_aloud_offline_kwargs=read_aloud_offline_kwargs,
            read_aloud_online_kwargs=read_aloud_online_kwargs,
            dictation_offline_kwargs=dictation_offline_kwargs,
            dictation_online_kwargs=dictation_online_kwargs,
            initial_tab=initial_tab,
        )
        ra_result, dict_result = hub.show(self._show_modal_dialog)

        if ra_result is not None:
            if ra_result.action == "download":
                if ra_result.engine == "piper":
                    wx.CallAfter(self._download_piper_voice, ra_result.voice_id)
                elif ra_result.engine == "kokoro":
                    wx.CallAfter(self._download_kokoro_models)
            elif ra_result.action == "download_engine":
                if ra_result.engine == "dectalk":
                    wx.CallAfter(self.download_dectalk_exe)
                elif ra_result.engine == "piper":
                    wx.CallAfter(self.download_piper_exe)
                elif ra_result.engine == "espeak":
                    wx.CallAfter(self.download_espeak_exe)
            else:  # 'select' or 'export'
                eng = ra_result.engine
                piper_dir = default_piper_model_dir()
                self.settings.read_aloud_engine = eng
                if ra_result.voice_id:
                    if eng == "dectalk":
                        self.settings.read_aloud_dectalk_voice = ra_result.voice_id
                    elif eng == "piper":
                        onnx_path = piper_dir / f"{ra_result.voice_id}.onnx"
                        if onnx_path.exists():
                            self.settings.read_aloud_piper_model = str(onnx_path)
                        else:
                            self._show_message_box(
                                f"'{ra_result.voice_id}' is not downloaded yet.\n"
                                "Use the Download Voice button to fetch it first.",
                                "Speech Settings",
                                wx.ICON_INFORMATION | wx.OK,
                            )
                            self.settings.read_aloud_engine = offline_current_engine
                            dict_result = None
                    elif eng == "kokoro":
                        self.settings.read_aloud_kokoro_voice = ra_result.voice_id
                    elif eng == "espeak":
                        self.settings.read_aloud_espeak_voice = ra_result.voice_id
                    elif eng == "macos":
                        self.settings.read_aloud_macos_voice = ra_result.voice_id
                    elif eng == "elevenlabs":
                        self.settings.read_aloud_elevenlabs_voice = ra_result.voice_id
                    else:
                        self.settings.read_aloud_voice = ra_result.voice_id
                if eng == "sapi5":
                    self.settings.read_aloud_rate = ra_result.rate
                    self.settings.read_aloud_volume = ra_result.volume
                    self.settings.read_aloud_pitch = ra_result.pitch
                elif eng == "dectalk":
                    self.settings.read_aloud_dectalk_rate = ra_result.dectalk_rate
                elif eng == "espeak":
                    self.settings.read_aloud_espeak_rate = ra_result.espeak_rate
                elif eng == "macos":
                    self.settings.read_aloud_macos_rate = ra_result.macos_rate
                elif eng == "kokoro":
                    self.settings.read_aloud_kokoro_speed = ra_result.kokoro_speed
                save_settings(self.settings)
                engine_label = dict(offline_engine_options + online_engine_options).get(eng, eng)
                self._announce(f"Voice configured: {engine_label}")
                if ra_result.action == "export":
                    # In the Studio, "export to audio" IS the Audio Studio.
                    wx.CallAfter(self.open_studio, "documents")

        if dict_result is not None:
            chosen_provider_id = dict_result.provider_id or ""
            if chosen_provider_id and chosen_provider_id != str(
                getattr(self.settings, "speech_provider", "") or ""
            ):
                self.settings.speech_provider = chosen_provider_id
                save_settings(self.settings)
                self._announce("Speech recognition engine saved.")

    def open_pronunciation_dictionaries(self) -> None:
        """Voices > Pronunciation Dictionaries: the same manager QUILL has.

        Dictionaries live in the shared data store, so one taught here fixes
        the same name in QUILL's Read Aloud too; every narration run applies
        the enabled, in-scope dictionaries before synthesis.
        """
        from quill.ui.pronunciation_dictionary_dialog import run_pronunciation_manager

        run_pronunciation_manager(self)

    def _download_piper_voice(self, voice_id: str) -> None:
        """Download a Piper ONNX voice model in the background."""
        from quill.core.read_aloud import default_piper_model_dir
        from quill.core.voice_catalog import piper_voice_download_urls
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        piper_dir = default_piper_model_dir()
        urls = piper_voice_download_urls(voice_id)
        if urls is None:
            self._show_message_box(
                f"Cannot determine download URL for: {voice_id}",
                "Download Piper Voice",
                wx.ICON_WARNING | wx.OK,
            )
            return
        onnx_path = piper_dir / f"{voice_id}.onnx"
        json_path = piper_dir / f"{voice_id}.onnx.json"
        if onnx_path.exists() and json_path.exists():
            self._announce(f"Piper voice '{voice_id}' is already downloaded.")
            self.choose_read_aloud_configuration()
            return
        from quill.core.speech.piper_install import install_bundled_piper_voice

        if install_bundled_piper_voice(voice_id, dest_dir=piper_dir) is not None:
            self._announce(f"Piper voice '{voice_id}' installed from the offline bundle.")
            self.choose_read_aloud_configuration()
            return
        piper_dir.mkdir(parents=True, exist_ok=True)

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            f"Downloading Piper voice: {voice_id}",
            "Preparing download...",
            on_cancel=cancel.set,
        )
        progress.show()
        self._announce(f"Downloading Piper voice {voice_id}.")

        def _run() -> None:
            from quill.core.speech.piper_install import download_piper_voice

            try:
                # Mirror-first (assets-v1, SHA-verified), upstream files as fallback.
                download_piper_voice(
                    voice_id,
                    piper_dir,
                    progress=lambda fr, msg: wx.CallAfter(
                        progress.set_progress, int(fr * 100), msg
                    ),
                    should_cancel=cancel.is_set,
                )
            except Exception as error:  # noqa: BLE001 - reported on the UI thread
                message = "Download cancelled." if cancel.is_set() else f"Download failed: {error}"
                wx.CallAfter(progress.close)
                wx.CallAfter(self._set_status, message)
                return
            wx.CallAfter(progress.close)
            wx.CallAfter(self._announce, f"Piper voice {voice_id} is ready.")
            wx.CallAfter(self.choose_read_aloud_configuration)

        threading.Thread(target=_run, daemon=True).start()

    # -- component helpers the downloads mixin's Optional Components rows use ----

    def download_git(self, on_done: Callable[[bool], None] | None = None) -> None:
        self._download_tool_component("git-windows", "Git", on_done)

    def download_gh(self, on_done: Callable[[bool], None] | None = None) -> None:
        component = "gh-macos" if sys.platform == "darwin" else "gh-windows"
        self._download_tool_component(component, "GitHub CLI", on_done)

    def _download_tool_component(
        self, component: str, label: str, on_done: Callable[[bool], None] | None
    ) -> None:
        from quill.core.release_assets import fetch_component

        target = app_data_dir() / "tools" / component

        def _fetch(_progress: Callable[[str, int, int], None]) -> object:
            fetch_component(component, target)
            return True

        def _finished(_result: object) -> None:
            self._announce(f"{label} is installed.")
            if on_done is not None:
                on_done(True)

        self._run_background_task(f"Downloading {label}", _fetch, _finished)

    def _view_log(self) -> None:
        """Open the current app log in the OS default viewer, so a user can read
        what happened (e.g. an engine-download failure) without hunting for the
        file. main() writes it to <data_dir>/logs/quill.log."""
        import subprocess
        import sys

        log_file = app_data_dir() / "logs" / "quill.log"
        if not log_file.exists():
            self._announce("No log has been written yet.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(log_file))  # type: ignore[attr-defined]  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(log_file)])
            else:
                subprocess.Popen(["xdg-open", str(log_file)])
            self._announce("Opening the log.")
        except Exception:  # noqa: BLE001 - a missing viewer must not crash the app
            self._announce("Could not open the log.")

    def save_diagnostics_bundle(self) -> None:
        """Save a redacted diagnostics zip -- the downloads mixin offers this
        after a component install fails, so support has something to read."""
        from quill.stability.crash_report import build_diagnostic_bundle

        with wx.FileDialog(
            self.frame,
            "Save diagnostics bundle",
            defaultFile="quill-audio-studio-diagnostics.zip",
            wildcard="Zip files (*.zip)|*.zip",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            target = Path(dialog.GetPath())

        def _build(_progress: Callable[[str, int, int], None]) -> object:
            # Pass the configured log file so the bundle actually contains logs
            # (the reason a component-install error can be diagnosed). Without
            # logs_path the archive held only metadata.json. main() configures
            # logging to <data_dir>/logs/quill.log.
            log_file = app_data_dir() / "logs" / "quill.log"
            return build_diagnostic_bundle(
                output_path=target,
                safe_mode=self._safe_mode,
                task_snapshot=self._task_manager.snapshot(),
                logs_path=log_file if log_file.exists() else None,
            )

        def _done(_result: object) -> None:
            self._announce(f"Diagnostics bundle saved to {target}")

        self._run_background_task("Building diagnostics bundle", _build, _done)

    # -- background tasks (MainFrame protocol, on the shell's own thread model) ---

    def _run_background_task(
        self,
        label: str,
        work: Callable[[Callable[[str, int, int], None]], object],
        on_success: Callable[[object], None],
        *,
        notify_on_success: bool = False,
        notify_on_error: bool = False,
        notification_category: str = "info",
        protect_on_close: bool = False,
    ) -> None:
        """Run *work(progress)* off-thread; deliver the result on the UI thread.

        Honors the same contract MainFrame's version does: ``progress(message,
        current, total)`` may be called from the worker; errors surface as a
        dialog; ``protect_on_close`` registers real, hard-to-redo work (an
        Audio Studio export) so closing the window asks first.
        """
        del notify_on_success, notify_on_error, notification_category  # no toast center here
        self._background_task_count += 1
        task_id = self._next_task_id = getattr(self, "_next_task_id", 0) + 1
        if protect_on_close:
            self._protected_background_jobs[task_id] = label
        self._set_status(f"{label} started")
        announce_milestones = bool(self._app_prefs.get("announce_run_milestones", True))
        milestone_state = {"last": -1}

        def progress(message: str, current: int, total: int) -> None:
            wx.CallAfter(self._set_status_quiet, f"{label}: {current}/{total} - {message}")
            if announce_milestones and total > 0:
                percent = int(current * 100 / total)
                milestone = percent - (percent % 25)
                if milestone > milestone_state["last"] and milestone in (25, 50, 75):
                    milestone_state["last"] = milestone
                    wx.CallAfter(self._announce, f"{label}: {milestone} percent")

        def worker() -> None:
            try:
                result = work(progress)
            except Exception as error:  # noqa: BLE001 - surfaced on the UI thread
                wx.CallAfter(self._finish_background_task, label, task_id, error, None, on_success)
                return
            wx.CallAfter(self._finish_background_task, label, task_id, None, result, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_background_task(
        self,
        label: str,
        task_id: int,
        error: Exception | None,
        result: object,
        on_success: Callable[[object], None],
    ) -> None:
        self._background_task_count = max(0, self._background_task_count - 1)
        self._protected_background_jobs.pop(task_id, None)
        if error is not None:
            self._set_status(f"{label} failed")
            self._show_message_box(
                f"{label} failed.\n\n{error}\n\n"
                "If this keeps happening, Help > Save Diagnostics captures the "
                "details for a bug report.",
                label,
                wx.ICON_ERROR | wx.OK,
            )
            self._refresh_statusbar()
            return
        self._set_status(f"{label} finished")
        try:
            on_success(result)
        finally:
            self._refresh_statusbar()
            self._reload_library_list()

    # -- voice preview (MainFrame protocol) ---------------------------------------

    def _voice_preview_catalog_roots(self) -> list[Path]:
        roots: list[Path] = []
        app_root_raw = os.environ.get("QUILL_APP_ROOT", "").strip()
        if app_root_raw:
            app_root = Path(app_root_raw)
            roots.append(app_root / "quill" / "data" / "voice-previews")
            roots.append(app_root / "quill" / "data" / "voice-previews")
            roots.append(app_root / "tools" / "speech" / "previews")
        roots.append(Path(__file__).resolve().parents[1] / "data" / "voice-previews")
        roots.append(app_data_dir() / "speech" / "previews")
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            marker = str(root).lower()
            if marker not in seen:
                seen.add(marker)
                deduped.append(root)
        return deduped

    def _voice_preview_sample_path(self, engine: str, voice_id: str) -> Path | None:
        safe_engine = (engine or "").strip().lower()
        safe_voice = (voice_id or "").strip()
        if not safe_engine or not safe_voice:
            return None
        if safe_engine == "sapi5":
            safe_voice = _sapi5_voice_short_name(safe_voice)
            if not safe_voice:
                return None
        for root in self._voice_preview_catalog_roots():
            provider_dir = root / safe_engine
            if not provider_dir.exists():
                continue
            for extension in (".wav", ".mp3"):
                candidate = provider_dir / f"{safe_voice}{extension}"
                if candidate.exists():
                    return candidate
        return None

    def _purge_preview_playback(self) -> None:
        if _winsound is not None:
            try:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass
        try:
            import ctypes as _ct

            _ct.windll.winmm.mciSendStringW("stop quill_preview", None, 0, None)  # type: ignore[attr-defined]
            _ct.windll.winmm.mciSendStringW("close quill_preview", None, 0, None)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def _stop_active_voice_preview(self) -> None:
        """Supersede whatever preview is active: bump the generation (in-flight
        synthesis results get discarded when they check), then cut playback."""
        self._preview_generation += 1
        self._cancel_preview_cue_timer()
        self._purge_preview_playback()

    def _cancel_preview_cue_timer(self) -> None:
        """Stop any pending 'generating preview' cue so it never fires after the
        preview it belonged to is over (superseded, finished, or errored)."""
        timer = getattr(self, "_preview_cue_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - a dead timer is fine to ignore
                pass
            self._preview_cue_timer = None

    def _fire_generating_cue(self, generation: int) -> None:
        """Speak a one-shot 'please wait' cue at the start of live synthesis.
        Fires only for the current preview, and only when the
        announce-generating setting is on (default True)."""
        if getattr(self, "_preview_generation", 0) != generation:
            return
        if getattr(self.settings, "voice_preview_announce_generating", True):
            self._announce("Generating preview, please wait.")

    def _on_preview_synth_done(self, _result: object) -> None:
        """Preview worker finished; cancel any pending cue (the error path in
        _run_background_task never reaches here, so the worker's own finally also
        cancels)."""
        self._cancel_preview_cue_timer()

    def _play_preview_asset(
        self, sample_path: Path, still_current: Callable[[], bool] | None = None
    ) -> None:
        """Play a preview clip so Stop can cut it mid-phrase.

        Playback is asynchronous and this method returns only when the clip
        finishes or ``still_current`` reports the preview was superseded -- at
        which point it purges the audio. A blocking play (the old behavior)
        could not be interrupted: Stop's SND_PURGE only cancels async sounds,
        so speech ran to the end regardless of Stop (issue #4)."""
        import time as _time

        current = still_current if still_current is not None else (lambda: True)
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME | _winsound.SND_ASYNC)
            _await_playback(
                duration=_wav_duration_seconds(sample_path),
                still_current=current,
                purge=self._purge_preview_playback,
                sleep=_time.sleep,
                now=_time.monotonic,
            )
            return
        try:
            import ctypes as _ct

            _winmm = _ct.windll.winmm  # type: ignore[attr-defined]
            _alias = "quill_preview"
            _path = str(sample_path).replace('"', "")
            _winmm.mciSendStringW(f'open "{_path}" type mpegvideo alias {_alias}', None, 0, None)
            try:
                # Play async (no 'wait') and poll so a superseding Stop -- which
                # sends MCI 'stop'/'close' via _purge_preview_playback -- takes
                # effect immediately instead of after the whole clip.
                _winmm.mciSendStringW(f"play {_alias}", None, 0, None)
                buf = _ct.create_unicode_buffer(64)
                while True:
                    if not current():
                        break
                    _winmm.mciSendStringW(f"status {_alias} mode", buf, 64, None)
                    if buf.value != "playing":
                        break
                    _time.sleep(0.05)
            finally:
                _winmm.mciSendStringW(f"close {_alias}", None, 0, None)
            return
        except (AttributeError, OSError):
            pass
        if sys.platform == "darwin":
            import subprocess as _subprocess

            _subprocess.Popen(["afplay", str(sample_path)])  # noqa: S603,S607
            return
        os.startfile(str(sample_path))  # noqa: S606 - last resort: system player

    def _engine_ready(self, engine: str) -> bool:
        from quill.ui.batch_speech_runner import _engine_available

        try:
            return bool(_engine_available(self).get(engine, False))
        except Exception:  # noqa: BLE001 - a probe failure reads as not-ready
            return False

    def _preview_synthesize(self, engine: str, voice_id: str, target: Path) -> None:
        """Synthesize the preview phrase with the real engine (worker thread)."""
        from quill.core import read_aloud as ra

        s = self.settings
        text = self._PREVIEW_TEXT
        if engine == "sapi5":
            ra.synthesize_to_file_with_sapi5(
                text,
                target,
                voice=voice_id,
                rate=int(s.read_aloud_rate),
                volume=float(s.read_aloud_volume) / 100.0,
            )
        elif engine == "dectalk":
            executable = ra.discover_dectalk_executable(s.read_aloud_dectalk_executable)
            if executable is None:
                raise ra.ReadAloudUnavailableError("DECtalk is not installed")
            ra.synthesize_to_file_with_dectalk(
                text,
                target,
                executable_path=executable,
                voice=voice_id,
                rate=int(s.read_aloud_dectalk_rate),
            )
        elif engine == "piper":
            executable = ra.discover_piper_executable()
            if executable is None:
                raise ra.ReadAloudUnavailableError("Piper is not installed")
            model = ra.resolve_piper_model_path(voice_id)
            if not model.exists():
                raise ra.ReadAloudUnavailableError(f"Piper voice {voice_id} is not downloaded")
            ra.synthesize_with_piper(text, target, executable_path=executable, model_path=model)
        elif engine == "kokoro":
            ra.synthesize_with_kokoro(
                text, target, voice=voice_id, speed=float(s.read_aloud_kokoro_speed)
            )
        elif engine == "espeak":
            executable = ra.discover_espeak_executable(s.read_aloud_espeak_executable)
            if executable is None:
                raise ra.ReadAloudUnavailableError("eSpeak-NG is not installed")
            ra.synthesize_with_espeak(
                text,
                target,
                executable_path=executable,
                voice=voice_id,
                rate=int(s.read_aloud_espeak_rate),
            )
        elif engine == "macos":
            ra.synthesize_with_macos(
                text, target, voice=voice_id, rate=int(s.read_aloud_macos_rate)
            )
        else:
            raise ra.ReadAloudUnavailableError(f"Unknown engine: {engine!r}")

    def _preview_voice(
        self,
        engine: str,
        voice_id: str,
        *,
        live: bool = False,
        text: str | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        """Preview *voice_id* on a background thread (MainFrame contract).

        ``live`` True synthesizes the preview phrase with the real model.
        ``live`` False (the wizard's preview button) plays the bundled sample
        when one ships; when none does but the engine is actually installed,
        the Studio quietly upgrades to a live synthesis instead of dead-ending
        -- an audio app's preview button should always make sound if it can.
        """
        del text  # the Studio always previews its standard phrase
        import tempfile

        self._stop_active_voice_preview()
        my_generation = self._preview_generation

        def _still_current() -> bool:
            return self._preview_generation == my_generation

        def _report(state: str) -> None:
            if on_state_change is not None and _still_current():
                wx.CallAfter(on_state_change, state)

        sample = self._voice_preview_sample_path(engine, voice_id)
        if not live and sample is not None:

            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                _report("playing")
                try:
                    if _still_current():
                        self._play_preview_asset(sample, _still_current)
                finally:
                    _report("idle")
                return None

            self._run_background_task(f"Previewing {engine} voice", _play_sample, lambda _r: None)
            return

        if not self._engine_ready(engine):
            self._announce("Download this voice to hear a preview.")
            return

        def _synthesize_and_play(_progress: Callable[[str, int, int], None]) -> object:
            _report("generating")
            try:
                with tempfile.TemporaryDirectory(prefix="quill-preview-") as tmp:
                    target = Path(tmp) / "preview.wav"
                    self._preview_synthesize(engine, voice_id, target)
                    # Synthesis is done -- stop the pending "please wait" cue so
                    # it can't fire during playback (or after a fast synth).
                    wx.CallAfter(self._cancel_preview_cue_timer)
                    if _still_current() and target.exists():
                        _report("playing")
                        self._play_preview_asset(target, _still_current)
            finally:
                wx.CallAfter(self._cancel_preview_cue_timer)
                _report("idle")
            return None

        # Speak "generating, please wait" as soon as live synthesis begins, so a
        # screen-reader user always knows the preview is working. Fired almost
        # immediately (not after a 400ms delay) because fast engines -- Piper in
        # particular -- finished synthesizing the short phrase before 400ms, so
        # their cue was cancelled before it ever played. The
        # voice_preview_announce_generating setting still gates it.
        self._cancel_preview_cue_timer()
        self._preview_cue_timer = wx.CallLater(1, self._fire_generating_cue, my_generation)
        self._run_background_task(
            f"Previewing {engine} voice", _synthesize_and_play, self._on_preview_synth_done
        )

    # -- status bar ---------------------------------------------------------------

    def _set_status(self, message: str) -> None:
        self._status_message = message
        super()._set_status(message)
        activity = getattr(self, "_activity_text", None)
        if activity is not None:
            activity.SetLabel(message)

    def _set_status_quiet(self, message: str) -> None:
        """Status bar text without a spoken announcement (per-progress updates)."""
        self._status_message = message
        AppShellFrame._set_status(self, message)
        activity = getattr(self, "_activity_text", None)
        if activity is not None:
            activity.SetLabel(message)

    def _refresh_statusbar(self) -> None:
        if getattr(self, "_background_task_count", 0) > 0:
            return  # a running task owns the status line
        books = self._recent_books()
        if books:
            plural = "" if len(books) == 1 else "s"
            self._set_status_quiet(f"Ready - {len(books)} book{plural} in your library")
        else:
            self._set_status_quiet("Ready - narrate documents or build from recordings to begin")

    # -- preferences ----------------------------------------------------------------

    def _open_preferences(self) -> None:
        from quill.ui.app_preferences_dialog import (
            PreferenceCheckbox,
            PreferenceChoice,
            PreferencesDialog,
        )

        prefs = self._app_prefs
        close_index = _CLOSE_ACTION_VALUES.index(str(prefs["close_action"]))
        dialog = PreferencesDialog(
            self.frame,
            app_title=_TITLE,
            checkboxes=[
                PreferenceCheckbox(
                    "&Check for updates automatically on launch",
                    "Check for updates automatically on launch",
                    bool(prefs["check_updates_on_startup"]),
                ),
                PreferenceCheckbox(
                    "Alt+F&4 minimizes to the system tray",
                    "When on, Alt+F4 sends the Studio to the system tray with any "
                    "narration run still going, instead of closing the window. The "
                    "titlebar X and Exit keep the 'When closing the window' behavior",
                    bool(prefs["alt_f4_to_tray"]),
                ),
                PreferenceCheckbox(
                    "&Speak progress milestones during long runs",
                    "During a narration or build run, announce 25, 50, and 75 "
                    "percent so you can follow progress without checking the window",
                    bool(prefs["announce_run_milestones"]),
                ),
            ],
            choices=[
                PreferenceChoice(
                    "When &closing the window:",
                    "What the titlebar X does. 'Ask when work is running' only "
                    "prompts while an export is still going; an idle window just "
                    "closes",
                    list(_CLOSE_ACTION_LABELS),
                    close_index,
                ),
            ],
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        checkbox_values, choice_indices, _texts = result
        (
            prefs["check_updates_on_startup"],
            prefs["alt_f4_to_tray"],
            prefs["announce_run_milestones"],
        ) = checkbox_values
        prefs["close_action"] = _CLOSE_ACTION_VALUES[choice_indices[0]]
        _save_app_prefs(prefs)
        self._announce("Preferences saved")

    # -- docs / about / updates ------------------------------------------------------

    def _open_studio_doc(self, stem: str) -> None:
        titles = {
            "userguide": f"{_TITLE} User Guide",
            "release-notes-1.0": f"{_TITLE} Release Notes",
            "prd": f"{_TITLE} Product Requirements",
        }
        self.open_app_document(
            self._doc_candidates("QUILL-AS", stem),
            title=titles.get(stem, stem),
            cache_name="app-docs",
        )

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "Audiobook and audio production from QUILL, as a standalone app.\n\n"
            "Runs the same Audio Studio code as QUILL itself and shares its "
            "settings, voices, and downloaded speech engines.\n"
            f"https://github.com/{_REPO}",
            f"About {_TITLE}",
            wx.ICON_INFORMATION | wx.OK,
        )

    def check_updates_manual(self) -> None:
        self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION)

    def _maybe_check_updates_on_startup(self) -> None:
        from datetime import UTC, datetime

        prefs = self._app_prefs
        if not bool(prefs.get("check_updates_on_startup", True)):
            return
        if not self._app_update_check_due(str(prefs.get("last_update_check", ""))):
            return
        prefs["last_update_check"] = datetime.now(UTC).isoformat()
        _save_app_prefs(prefs)
        self.check_for_app_updates(repo_slug=_REPO, current_version=_VERSION, silent_no_update=True)

    # -- lifecycle --------------------------------------------------------------

    def _send_to_tray(self) -> None:
        self.frame.Hide()
        self._announce(f"{_TITLE} is still running in the system tray.")

    def _on_char_hook(self, event: wx.KeyEvent) -> None:
        if (
            event.GetKeyCode() == wx.WXK_F4
            and event.AltDown()
            and bool(self._app_prefs.get("alt_f4_to_tray", False))
        ):
            self._send_to_tray()
            return
        event.Skip()

    def _on_app_close(self, event: wx.CloseEvent) -> None:
        # Thin wrapper over the shared close flow (AppShellFrame.handle_app_close),
        # which never ShowModals from inside EVT_CLOSE -- it vetoes and defers the
        # confirm box so a rapid second Alt+F4 can't stack a second dialog and the
        # box reliably appears. "Ask" only prompts when background work is running.
        self.handle_app_close(
            event,
            close_action=str(self._app_prefs.get("close_action", "ask")),
            protected=bool(self._protected_background_jobs),
            confirm=self._studio_close_confirm,
            shutdown=self._studio_shutdown,
        )

    def _studio_close_confirm(self) -> str | None:
        """Warn that background work is still running and ask whether to exit:
        Yes -> "exit", No -> None (keep the Studio open; the user can minimize it
        instead). Run deferred by the shared close flow, never from inside
        EVT_CLOSE (see AppShellFrame.handle_app_close)."""
        running = dict(self._protected_background_jobs)
        if not running:
            return "exit"  # protected gate already checked; nothing to lose
        labels = "\n".join(f"- {label}" for label in running.values())
        answer = self._show_message_box(
            f"Work is still running:\n{labels}\n\n"
            "Exit anyway and lose it? Choose No to keep the Studio "
            "open (you can minimize it to the tray instead).",
            "Work in Progress",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        return "exit" if answer in (wx.YES, wx.ID_YES) else None

    def _studio_shutdown(self) -> None:
        self._stop_active_voice_preview()
        self._task_manager.shutdown(wait=False)
        self._sleep_watcher.shutdown()
        self._disarm_end_of_chapter_watch()
        self._deactivate_media_keys()
        self._remove_tray_icon()


def main() -> int:
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE")) or "--safe-mode" in sys.argv[1:]
    from quill.core.i18n import init_locale

    init_locale()
    # Configure file logging FIRST so anything after this -- especially failed
    # engine downloads (Whisper/Kokoro/etc.) -- lands in <data_dir>/logs/quill.log
    # and is captured by Help > Save Diagnostics. Without this the standalone
    # wrote no logs at all, so field errors were undiagnosable. Mirrors
    # quill.apps.radio.main.
    from quill.core.paths import app_data_dir
    from quill.stability.logging_config import configure_logging

    log_listener = configure_logging(app_data_dir() / "logs")
    from quill.core import components

    components.register_running_app("studio", REQUIRED_COMPONENTS)
    # Put previously-installed on-demand engine packs (Kokoro's kokoro_onnx,
    # Faster-Whisper, Vosk, MP3/mutagen) back on sys.path BEFORE the UI queries
    # readiness. The embeddable-Python launcher's ._pth lists only the stdlib,
    # and sitecustomize only exports QUILL_APP_ROOT -- so without this call an
    # engine installed in a previous session is not importable at startup, and
    # the Optional Components hub shows "Download" for an engine that is fully
    # installed (and Kokoro voices cannot be previewed or set as default).
    # QUILL's MainFrame does this at startup; the standalone shell must too.
    from quill.core.speech.engine_install import activate_engine_packs

    activate_engine_packs()
    app = wx.App()
    # Single-instance guard: a second launch would duplicate the tray icon and
    # silently steal the media-key registration from the first window. Refuse it
    # with a clear message instead. The checker must outlive MainLoop, so it is
    # held here for the app's lifetime.
    _checker = wx.SingleInstanceChecker(f"quill-audio-studio-{wx.GetUserId()}")
    if _checker.IsAnotherRunning():
        # Pre-MainLoop single-instance guard: no AppShellFrame exists yet, so the
        # SR-announcement wrapper (self._show_message_box) is unavailable here.
        wx.MessageBox(  # MSGBOX-OK: pre-frame single-instance guard, no shell yet
            f"{_TITLE} is already running.", _TITLE, wx.OK | wx.ICON_INFORMATION
        )
        log_listener.stop()
        return 0
    frame = StudioAppFrame(safe_mode=safe_mode)
    frame._log_listener = log_listener
    frame.frame.Show()
    app.MainLoop()
    log_listener.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
