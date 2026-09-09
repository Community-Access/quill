"""QuillLite -- QUILL with everything removed except the editor.

One document per window, plain text or rich text, and nothing else. It exists
for the person who wants Notepad or WordPad with QUILL's accessibility and finds
the full writing environment more than they need: no tabs, no AI, no dictation,
no conversion, no comparison, no publishing, no extensions, no setup wizard, no
command palette.

It is explicitly **not** a replacement for QUILL, and explicitly **not** a place
new features go. Anyone who wants any of the list above wants QUILL, and
QuillLite is built so it cannot grow into it: its whole product is one window
class, one editor surface and one command table.

What it does *not* reimplement is the part that took QUILL years to get right.
The editor is the same native ``RICHEDIT50W`` (:mod:`quill.ui.richedit_editing`
over :mod:`quill.ui.richedit_rtf_surface`), RTF still goes through the Text
Object Model, RTF still passes :func:`~quill.io.rtf_safety.scan_rtf_safety`
before a byte reaches the control, dialogs still go through the dialog contract,
and F1 still answers through the family's context-help engine.

**Bootstrap deliberately differs from its siblings.** Radio, Cast, Weather,
Studio and Inkwell each run one window and take the family single-instance lock
in :mod:`quill.core.ipc`, whose lock and queue live in QUILL's own data
directory. QuillLite runs *many* windows in one process and keeps a separate
data store, so it uses ``wx.SingleInstanceChecker`` (a kernel object, with no
file to go stale) plus its own inbox under
``%LOCALAPPDATA%\\QuillLite`` -- a machine that has never had QUILL installed
must not grow an ``%APPDATA%\\Quill`` folder because somebody opened a text file.

Origin: contributed as PR #1490 by Steven Scott (``doubletaponair``), MIT, and
adopted into the family here. The ``tomTrue`` bug that PR isolated is fixed in
:mod:`quill.ui.richedit_rtf_surface`, where every QUILL user gets it too.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_printing import PrintSettings
from quill.apps.lite_services import LiteServicesMixin
from quill.apps.lite_shell import QuillLiteShell
from quill.apps.lite_window import DocumentFrame
from quill.core.lite import APP_NAME, APP_VERSION
from quill.core.lite import features as features_mod
from quill.core.lite import inbox as inbox_mod
from quill.core.lite import recovery as recovery_mod
from quill.core.lite import settings as settings_mod
from quill.core.lite.paths import data_dir
from quill.ui.dialog_contract import show_message_box
from quill.ui.richedit_editing import PLAIN, RICH

__all__ = ["OPTIONAL_COMPONENTS", "REQUIRED_COMPONENTS", "QuillLiteApp", "main"]

_TITLE = APP_NAME
_VERSION = APP_VERSION
_REPO = "Community-Access/quill"

#: QuillLite is a text editor. It plays nothing, records nothing, converts
#: nothing, and therefore stages neither ffmpeg nor libmpv into the shared
#: runtime. Declared here and mirrored in ``standalone/runtime/app-profiles.json``,
#: which ``tests/unit/structure/test_app_profiles.py`` checks cannot drift.
REQUIRED_COMPONENTS: tuple[str, ...] = ()
OPTIONAL_COMPONENTS: tuple[str, ...] = ()

#: How often the inbox is checked for a request from a second launch. Half a
#: second is below the threshold at which opening a file from Explorer feels
#: like a delay, and far above the cost of one ``glob`` on an empty directory.
_INBOX_POLL_MS = 500


class ScreenReaderVoice:
    """Announcements, through a running screen reader and nowhere else.

    QuillLite has **no self-voicing fallback** -- no SAPI, no synthesized voice
    of its own -- and that is a decision rather than an omission. A second voice
    talking over NVDA or JAWS is worse than silence, and a listener who has no
    screen reader running is not the person this editor is for; for them the
    same messages are in the status bar, which is where the window puts them.

    The delivery itself is QUILL's, not a private copy: the family's
    :class:`~quill.platform.windows.prism_bridge.AnnouncementEngine` reaches
    NVDA and JAWS through Prism or accessible_output2 and Narrator through a UIA
    notification. The one thing added here is the guard -- nothing is handed to
    the engine unless a reader is actually running, which is what keeps its SAPI
    fallback from ever being reached.
    """

    #: How long a screen-reader detection is trusted before re-probing. A reader
    #: started mid-session is picked up within this; enumerating processes on
    #: every announcement would not be.
    _PROBE_INTERVAL_SECONDS = 30.0

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._reader_present = False
        self._probed_at = 0.0

    def _reader_running(self) -> bool:
        import time

        now = time.monotonic()
        if now - self._probed_at < self._PROBE_INTERVAL_SECONDS and self._probed_at:
            return self._reader_present
        self._probed_at = now
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            self._reader_present = detect_screen_reader().detected
        except Exception:  # noqa: BLE001 - detection must never break an announcement
            self._reader_present = False
        return self._reader_present

    def speak(self, message: str) -> None:
        """Say *message* if a screen reader is listening. Never raises."""
        text = (message or "").strip()
        if not text or not self._reader_running():
            return
        try:
            if self._engine is None:
                from quill.platform.windows.prism_bridge import AnnouncementEngine

                # "prism" rather than "auto": auto is allowed to self-voice.
                self._engine = AnnouncementEngine("prism")
            self._engine.announce(text, force_speech=True)
        except Exception:  # noqa: BLE001 - the status bar still carries the message
            self._engine = None

    def backend_name(self) -> str:
        """What is serving speech right now, for the ``--check`` diagnostic."""
        if not self._reader_running():
            return "none (no screen reader running)"
        self.speak("")  # builds the engine without saying anything
        state = getattr(self._engine, "state", None)
        return str(state().backend_name) if callable(state) else "unknown"


class QuillLiteApp(LiteServicesMixin, wx.App):
    """The window registry, the settings owner, and the single-instance inbox."""

    def __init__(self, paths: list[Path], mode: str | None) -> None:
        self._initial_paths = paths
        self._initial_mode = mode
        self.frames: list[DocumentFrame] = []
        self.active_frame: DocumentFrame | None = None
        self.voice = ScreenReaderVoice()
        self.print_settings: PrintSettings | None = None
        self.shell: QuillLiteShell | None = None
        #: Which areas of the app exist at all. Everything unknown is on;
        #: quill.core.lite.features.DEFAULT_OFF is the small set that starts off
        #: because it would be wrong on rather than merely unused.
        self.features: Any = None
        self.copy_tray: Any = None
        self.clip_library: Any = None
        self.abbreviations: Any = None
        #: The clipboard collector's growing buffer. One per session, shared by
        #: every document: gathering quotes out of three files into one place is
        #: exactly the case it exists for.
        self.collected = ""
        self.shutting_down = False
        #: Documents are numbered in the order they were opened, and a number is
        #: never reused inside one session: reusing it would mean "document 3"
        #: silently became a different document while somebody was away from it.
        self._next_number = 0
        super().__init__(redirect=False)

    def OnInit(self) -> bool:  # noqa: N802 - wx API shape
        self.SetAppName(APP_NAME)
        self.data_dir = data_dir()
        self.settings = settings_mod.load()
        inbox_mod.claim_instance_marker()
        # F1 help for the whole app, with QuillLite's own purpose catalogue.
        # Without activate() every SetHelpText in the app stores nothing, because
        # wx needs a HelpProvider before it will keep help text at all.
        from quill.core import lite_surface_help
        from quill.ui import app_context_help

        app_context_help.activate(lite_surface_help.purpose_for_title)

        self.print_settings = PrintSettings()
        self.features = features_mod.load_features(self.data_dir)
        self._load_optional_stores()
        self.shell = QuillLiteShell(self, (self.settings.window_width, self.settings.window_height))
        if self.settings.window_maximized:
            self.shell.Maximize(True)
        self.shell.Bind(wx.EVT_SIZE, self._remember_shell_size)
        self.SetTopWindow(self.shell)
        self.shell.Show()

        recovered = self._restore_pending_work()
        opened = recovered
        for path in self._initial_paths:
            if self.open_path(path):
                opened = True
        # Last session's documents, but never over the top of files named on the
        # command line: somebody who double-clicked a file asked for that file,
        # and burying it under yesterday's four would be answering a different
        # question.
        if not self._initial_paths and self.settings.restore_session:
            opened = self._restore_session() or opened
        if not opened or self._initial_mode is not None:
            self.new_window(self._initial_mode or self.settings.default_mode)
        if recovered:
            # The one thing the screen reader cannot deduce from the windows
            # that appeared: that they are unsaved work, not files.
            wx.CallAfter(self.voice.speak, "Recovered unsaved work from the last session")
        self._inbox_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._poll_inbox, self._inbox_timer)
        self._inbox_timer.Start(_INBOX_POLL_MS)
        return True

    def next_document_number(self) -> int:
        """The next document number, counting from 1 and never reused."""
        self._next_number += 1
        return self._next_number

    def _remember_shell_size(self, event: wx.SizeEvent) -> None:
        """Keep the shell's geometry, which is what reopens next session.

        On the shell rather than on a document: with MDI there is one window to
        remember, and a maximised child inside a small shell is still a small
        window.
        """
        if self.shell is not None and not self.shutting_down:
            self.settings.window_maximized = self.shell.IsMaximized()
            if not self.settings.window_maximized:
                width, height = self.shell.GetSize()
                self.settings.window_width = int(width)
                self.settings.window_height = int(height)
        event.Skip()

    def _restore_session(self) -> bool:
        """Reopen last session's documents, in the order they were numbered.

        Files that have gone are skipped silently rather than reported: a
        session list is a convenience, and being told about a file you deleted
        on purpose is not news.
        """
        opened = False
        for entry in list(self.settings.session_files):
            path = Path(entry)
            if path.is_file() and self.open_path(path):
                opened = True
        return opened

    def remember_session(self) -> None:
        """Record which files are open, for the next launch.

        Saved documents only. An untitled window has nothing to reopen *from*,
        and its content -- if it has any -- is the recovery store's business,
        which is a different promise with a different guarantee.
        """
        self.settings.session_files = [
            str(frame.path) for frame in self.frames if frame.path is not None
        ]
        self.save_settings()

    def _restore_pending_work(self) -> bool:
        """Open a window per recovery slot. ``True`` when there was any."""
        slots = recovery_mod.pending()
        for slot in slots:
            self.new_window(slot.mode, recovery_slot=slot)
        return bool(slots)

    # -- windows --------------------------------------------------------- #

    def new_window(
        self,
        mode: str,
        path: Path | None = None,
        recovery_slot: recovery_mod.RecoverySlot | None = None,
    ) -> DocumentFrame:
        frame = DocumentFrame(self, path=path, mode=mode, recovery_slot=recovery_slot)
        self.frames.append(frame)
        self.refresh_all_menus()
        frame.Show()
        self.focus_frame(frame)
        return frame

    def open_path(self, path: Path, reuse: DocumentFrame | None = None) -> bool:
        """Open *path*, focusing the window that already has it if there is one."""
        path = Path(path)
        existing = self._frame_for(path)
        if existing is not None:
            self.focus_frame(existing)
            return True
        if not path.exists() and not self._offer_to_create(path):
            return False
        if reuse is not None:
            if not reuse.load(path):
                return False
            self.focus_frame(reuse)
            return True
        mode = RICH if path.suffix.lower() == ".rtf" else PLAIN
        frame = DocumentFrame(self, path=path, mode=mode)
        if frame.path is None:  # the load failed and already reported why
            frame.Destroy()
            return False
        self.frames.append(frame)
        self.refresh_all_menus()
        frame.Show()
        self.focus_frame(frame)
        return True

    def open_from_dialog(self, parent: wx.Window) -> None:
        """File > Open from the shell's own menu, when no document is open."""
        from quill.core.lite.filetypes import OPEN_WILDCARD

        with wx.FileDialog(
            parent,
            "Open",
            wildcard=OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            paths = [Path(chosen) for chosen in dialog.GetPaths()]
        for path in paths:
            self.open_path(path)

    def _frame_for(self, path: Path) -> DocumentFrame | None:
        """The window already editing *path*, if any (case- and link-tolerant)."""
        for frame in self.frames:
            if frame.path is not None and _same_file(frame.path, path):
                return frame
        return None

    def _offer_to_create(self, path: Path) -> bool:
        """Notepad's oldest behaviour: a name that does not exist offers to be one."""
        answer = show_message_box(
            f"{path.name} does not exist. Create it?",
            APP_NAME,
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if answer != wx.YES:
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        except OSError as exc:
            show_message_box(
                f"Could not create {path}.\n\n{exc}",
                APP_NAME,
                wx.OK | wx.ICON_ERROR,
            )
            return False
        return True

    def focus_frame(self, frame: DocumentFrame) -> None:
        """Bring *frame* to the front of the shell and put the caret in it.

        ``Activate`` rather than ``Raise``: an MDI child is not a top-level
        window, so raising it does nothing. The shell is raised too, for the
        case where the request came from a second launch and the whole
        application is behind something else.
        """
        if self.shell is not None:
            self.shell.Iconize(False)
            self.shell.Raise()
        if frame.IsIconized():
            frame.Iconize(False)
        frame.Show()
        frame.Activate()
        try:
            frame.control.SetFocus()
        except RuntimeError:
            pass  # the child is on its way out; the next activation focuses it
        self.active_frame = frame

    def cycle(self, frame: DocumentFrame, step: int) -> None:
        if len(self.frames) < 2:
            self.voice.speak("Only one window")
            return
        index = self.frames.index(frame)
        self.focus_frame(self.frames[(index + step) % len(self.frames)])

    def forget_frame(self, frame: DocumentFrame) -> None:
        if frame in self.frames:
            self.frames.remove(frame)
        if self.active_frame is frame:
            self.active_frame = None
        self.save_settings()
        self.refresh_all_menus()

    def exit_all(self) -> None:
        """Close every document, asking about each. One refusal cancels the lot.

        The shell goes last and is what actually ends the session: closing the
        children alone would leave an empty window behind, which reads as "Exit
        did not work".
        """
        for frame in list(self.frames):
            if not frame.confirm_discard():
                return
        self.remember_session()
        for frame in list(self.frames):
            frame.modified = False  # already answered for, above
            frame.Close()
        self.shutting_down = True
        if self.shell is not None:
            self.shell.Close()

    def refresh_all_menus(self) -> None:
        for frame in self.frames:
            try:
                frame.refresh_recent_menu()
                frame.refresh_window_menu()
            except RuntimeError:
                pass  # a window mid-destruction; the list is about to be rebuilt

    def reapply_settings(self) -> None:
        """Push the current settings into every open window.

        One method rather than a loop at each call site: every setting change --
        the two View-menu toggles, the text-size keys, the font chooser and the
        Preferences window -- has to reach *all* the windows, and four
        near-identical loops is four chances for one of them to forget a step.
        Everything here is cheap enough to do wholesale.
        """
        for frame in self.frames:
            frame._apply_editor_font()
            frame.apply_theme()
            frame.editor.set_word_wrap(self.settings.word_wrap)
            frame.restart_autosave()
            frame._sync_check_items()

    def save_settings(self) -> None:
        try:
            settings_mod.save(self.settings)
        except OSError:
            pass  # a read-only profile must not make the editor unusable

    # -- the single-instance inbox --------------------------------------- #

    def _poll_inbox(self, _event: wx.TimerEvent) -> None:
        for line in inbox_mod.read_requests():
            if line == inbox_mod.NEW_DEFAULT:
                self.new_window(self.settings.default_mode)
            elif line == inbox_mod.NEW_RICH:
                self.new_window(RICH)
            elif line == inbox_mod.NEW_PLAIN:
                self.new_window(PLAIN)
            else:
                self.open_path(Path(line))


def _same_file(first: Path, second: Path) -> bool:
    """True when two paths name the same file, tolerating case and links."""
    try:
        if first.resolve() == second.resolve():
            return True
        return os.path.samefile(first, second)
    except OSError:
        return str(first).lower() == str(second).lower()


def _allow_foreground(pid: int) -> None:
    """Let the already-running instance raise its window in front of this one.

    Windows refuses a foreground change requested by a process that is not in
    the foreground; only the process that *is* may hand the right over. Without
    this the handover still opens the file -- into a window behind everything
    else, which the user then has to go and find.
    """
    if sys.platform != "win32" or not pid:
        return
    try:
        import ctypes

        ctypes.windll.user32.AllowSetForegroundWindow(pid)
    except Exception:  # noqa: BLE001 - a focus courtesy must never block a launch
        pass


def _parse_args(argv: list[str]) -> tuple[list[Path], str | None, bool, bool]:
    """``(paths, mode, check, new_instance)`` from the command line."""
    paths: list[Path] = []
    mode: str | None = None
    check = False
    new_instance = False
    for arg in argv:
        if arg == "--check":
            check = True
        elif arg == "--rich":
            mode = RICH
        elif arg == "--plain":
            mode = PLAIN
        elif arg == "--new-instance":
            new_instance = True
        elif arg in {"-h", "--help", "/?"}:
            print(_USAGE)
            raise SystemExit(0)
        else:
            paths.append(Path(arg))
    return paths, mode, check, new_instance


_USAGE = f"""{APP_NAME} {APP_VERSION} -- a notepad-scale editor built for screen readers.

  quill-lite [--rich | --plain] [file ...]

  --rich    open a new rich text window as well as any files named
  --plain   open a new plain text window as well as any files named
  --check   write a diagnostic to the data folder and exit without a window
  --new-instance
            open a second QuillLite window with its own document numbering,
            instead of handing the files to the copy that is already running
"""


def main() -> int:
    from quill.core.data_location import apply_pending_at_launch

    # Every app in the family applies a queued Data Folder move before reading
    # anything, so a move queued from one app happens at whichever app launches
    # next. QuillLite keeps its own store and so has nothing of its own to move,
    # but it is part of the family and must not be the app that strands
    # somebody's queued change.
    apply_pending_at_launch()

    paths, mode, check, new_instance = _parse_args(list(sys.argv[1:]))
    if check:
        from quill.apps.lite_check import run_check

        return run_check()

    # One process, many windows: a second launch hands its files to the first
    # and exits, so opening files from Explorer is instant and there is one
    # owner of the settings file and the recovery store.
    checker = wx.SingleInstanceChecker(f"{APP_NAME}-{wx.GetUserId()}")
    if checker.IsAnotherRunning() and not new_instance:
        _allow_foreground(inbox_mod.running_instance_pid())
        if inbox_mod.post_request(paths, mode):
            return 0
        # The handover failed (a read-only or full profile). Opening a second
        # process is worse than nothing but far better than a launch that
        # silently does nothing at all.

    from quill.stability.logging_config import configure_logging

    log_listener = configure_logging(data_dir() / "logs")
    app = QuillLiteApp(paths, mode)
    try:
        app.MainLoop()
    finally:
        inbox_mod.clear_instance_marker()
        log_listener.stop()
    del checker
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
