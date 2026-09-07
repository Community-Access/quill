"""The application object: the window registry and the single-instance inbox."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import wx

from quilllite import APP_NAME, recovery, speech
from quilllite import settings as settings_mod
from quilllite.editor import PLAIN, RICH
from quilllite.paths import data_dir, inbox_dir, pid_file
from quilllite.window import DocumentFrame


class QuillLiteApp(wx.App):
    def __init__(self, paths: list[Path], mode: str | None) -> None:
        self._initial_paths = paths
        self._initial_mode = mode
        self.frames: list[DocumentFrame] = []
        self.active_frame: DocumentFrame | None = None
        super().__init__(redirect=False)

    def OnInit(self) -> bool:  # noqa: N802 - wx naming
        self.SetAppName(APP_NAME)
        self.data_dir = data_dir()
        self.settings = settings_mod.load()
        try:
            pid_file().write_text(str(os.getpid()), encoding="utf-8")
        except OSError:
            pass
        opened = False
        for slot in recovery.pending():
            self.new_window(slot.mode, recovery_slot=slot)
            opened = True
        for path in self._initial_paths:
            if self.open_path(path):
                opened = True
        if not opened or self._initial_mode is not None:
            if self._initial_mode is not None or not opened:
                self.new_window(self._initial_mode or self.settings.default_mode)
        if self.frames and any(f._slot is not None for f in self.frames):
            wx.CallAfter(speech.speak, "Recovered unsaved documents from the last session")
        self._inbox_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._poll_inbox, self._inbox_timer)
        self._inbox_timer.Start(500)
        speech.prewarm()
        return True

    # -- windows --------------------------------------------------------- #

    def new_window(
        self,
        mode: str,
        path: Path | None = None,
        recovery_slot: recovery.RecoverySlot | None = None,
    ) -> DocumentFrame:
        frame = DocumentFrame(self, path=path, mode=mode, recovery_slot=recovery_slot)
        self.frames.append(frame)
        self.refresh_all_menus()
        frame.Show()
        self.focus_frame(frame)
        return frame

    def open_path(self, path: Path, reuse: DocumentFrame | None = None) -> bool:
        path = Path(path)
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        for frame in self.frames:
            if frame.path is not None and _same_file(frame.path, resolved):
                self.focus_frame(frame)
                return True
        if not path.exists():
            answer = wx.MessageBox(
                f"{path.name} does not exist. Create it?", APP_NAME, wx.YES_NO | wx.ICON_QUESTION
            )
            if answer != wx.YES:
                return False
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            except OSError as exc:
                wx.MessageBox(f"Could not create {path}.\n\n{exc}", APP_NAME, wx.OK | wx.ICON_ERROR)
                return False
        if reuse is not None:
            if reuse.load(path):
                self.focus_frame(reuse)
                return True
            return False
        mode = RICH if path.suffix.lower() == ".rtf" else PLAIN
        frame = DocumentFrame(self, path=path, mode=mode)
        if frame.path is None:  # load failed; the frame already showed the error
            frame.Destroy()
            return False
        self.frames.append(frame)
        self.refresh_all_menus()
        frame.Show()
        self.focus_frame(frame)
        return True

    def focus_frame(self, frame: DocumentFrame) -> None:
        if frame.IsIconized():
            frame.Iconize(False)
        frame.Show()
        frame.Raise()
        frame.editor.control.SetFocus()
        self.active_frame = frame

    def cycle(self, frame: DocumentFrame, step: int) -> None:
        if len(self.frames) < 2:
            speech.speak("Only one window")
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
        for frame in list(self.frames):
            if not frame.confirm_discard():
                return
        for frame in list(self.frames):
            frame.modified = False
            frame.Close()

    def refresh_all_menus(self) -> None:
        for frame in self.frames:
            try:
                frame.refresh_recent_menu()
                frame.refresh_window_menu()
            except RuntimeError:
                pass

    def save_settings(self) -> None:
        try:
            settings_mod.save(self.settings)
        except OSError:
            pass

    # -- single instance inbox ------------------------------------------- #

    def _poll_inbox(self, _event: wx.TimerEvent) -> None:
        try:
            requests = sorted(inbox_dir().glob("*.req"))
        except OSError:
            return
        for request in requests:
            try:
                lines = request.read_text(encoding="utf-8").splitlines()
                request.unlink()
            except OSError:
                continue
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line == "NEW":
                    self.new_window(self.settings.default_mode)
                elif line == "NEW:rich":
                    self.new_window(RICH)
                elif line == "NEW:plain":
                    self.new_window(PLAIN)
                else:
                    self.open_path(Path(line))


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve() or os.path.samefile(a, b)
    except OSError:
        return str(a).lower() == str(b).lower()


def hand_over_to_running_instance(paths: list[Path], mode: str | None) -> bool:
    """Ask the running instance to open the paths. True when it took the job."""
    try:
        pid = int(pid_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        pid = 0
    if sys.platform == "win32" and pid:
        try:
            import ctypes  # noqa: PLC0415

            # Lets the already-running process bring its window to the front.
            ctypes.windll.user32.AllowSetForegroundWindow(pid)
        except Exception:
            pass
    lines = [str(Path(p).resolve()) for p in paths]
    if mode is not None or not lines:
        lines.append("NEW" if mode is None else f"NEW:{mode}")
    tmp = inbox_dir() / f"{uuid.uuid4().hex}.tmp"
    try:
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, tmp.with_suffix(".req"))
    except OSError:
        return False
    return True
