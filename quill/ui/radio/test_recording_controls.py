"""Test These Settings in Recording Settings: 30 seconds before an hour (FUX-11).

The button records the playing station for 30 seconds with the format,
quality and Sound Enhancements chosen in the window *now* -- before OK saves
them -- through the real recording command (:mod:`quill.core.radio.test_recording`),
into a temporary folder. The **Test result** box then says what those seconds
made and what an hour will weigh at that rate. **Hear the Test** plays it.

Nothing is written into the recordings folder, nothing is added to the
recordings list or history, and no setting changes. The test folder is removed
when the window closes. A changed format, quality or Sound Enhancements choice
marks the result out of date.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

from quill.core.radio.test_recording import (
    TEST_SECONDS,
    hour_size_sentence,
    plan_test,
    settings_print,
    test_sentence,
)
from quill.core.rehearsal import stale_sentence

_log = logging.getLogger(__name__)


def playing_station(host: Any) -> tuple[str, str] | None:
    """The live station playing in *host*, as ``(name, stream_url)``, or ``None``."""
    controller = getattr(host, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    if station is None or bool(getattr(station, "is_recording", False)):
        return None
    return str(station.name), str(station.stream_url)


def filter_graph_for(host: Any, apply: bool) -> str:
    """The filter a real recording would use, for the box as it is ticked now.

    Asks the host's own :meth:`_radio_recording_filter_graph`, with the saved
    "apply" choice swapped for the window's, so the test uses exactly the
    filter a recording would.
    """
    if not apply:
        return ""
    build = getattr(host, "_radio_recording_filter_graph", None)
    saved = getattr(host, "_radio_recording_settings", None)
    if not callable(build) or saved is None:
        return ""
    host._radio_recording_settings = replace(saved, apply_sound_enhancements=True)
    try:
        return str(build())
    finally:
        host._radio_recording_settings = saved


def run_test(
    args: list[str],
    stop: threading.Event,
    popen: Callable[..., Any] = subprocess.Popen,
) -> float:
    """Run ffmpeg until it ends or *stop* is set; return the seconds it ran."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    began = time.monotonic()
    process = popen(  # noqa: S603 - argv from build_record_command, no shell
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags
    )
    deadline = began + TEST_SECONDS + 30
    while process.poll() is None:
        if stop.is_set() or time.monotonic() > deadline:
            process.terminate()
            break
        time.sleep(0.2)
    return time.monotonic() - began


class TestRecordingControls:
    """The two buttons and the result box, for :class:`RecordingSettingsDialog`."""

    def __init__(
        self,
        dialog: Any,
        sizer: Any,
        host: Any,
        read_choice: Callable[[], tuple[str, int, bool]],
        announce: Callable[[str], None],
    ) -> None:
        self._dialog = dialog
        self._host = host
        self._read_choice = read_choice
        self._announce = announce
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.test_button = wx.Button(dialog, label="Test These Settin&gs")
        self.test_button.SetHelpText(
            f"Records the playing station for {TEST_SECONDS} seconds with the format, "
            "quality and Sound Enhancements chosen here, before you press OK, into a "
            "temporary folder, and says in Test result how large an hour will be. "
            "Nothing goes into your recordings folder. Press again to stop."
        )
        self.hear_button = wx.Button(dialog, label="&Hear the Test")
        self.hear_button.SetHelpText(
            "Plays the last test recording; before a test it says there is nothing to "
            "hear yet. Pause the station first to hear it clearly. Press again to stop."
        )
        row.Add(self.test_button, 0, wx.RIGHT, 6)
        row.Add(self.hear_button, 0)
        label = wx.StaticText(dialog, label="Test res&ult:")
        self.result = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.result.SetName("Test result")
        self.result.SetHelpText(
            "How large an hour is at these settings, and what the last test recording "
            "made. It says out of date when a setting changed after the test."
        )
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT, 10)
        sizer.Add(self.result, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.test_button.Bind(wx.EVT_BUTTON, lambda _e: self.press())
        self.hear_button.Bind(wx.EVT_BUTTON, lambda _e: self.hear())
        dialog.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._stop: threading.Event | None = None
        self._folders: list[Path] = []
        self._made: Path | None = None
        self._print = ""
        self._said = ""
        self._note = ""  # a reason a press did nothing, kept as text
        self._was_current = True
        self._playing = False
        self.refresh()

    # -- the result box -------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._stop is not None

    def _current_print(self) -> str:
        fmt, kbps, apply = self._read_choice()
        station = playing_station(self._host)
        url = station[1] if station is not None else ""
        return settings_print(fmt, kbps, filter_graph_for(self._host, apply), url)

    def refresh(self) -> None:
        """Rewrite the result box for the choices in the window now."""
        fmt, kbps, _apply = self._read_choice()
        lines = [hour_size_sentence(fmt, kbps)]
        if self._note:
            lines.append(self._note)
        if self.running:
            lines.append(f"Recording a {TEST_SECONDS}-second test...")
        elif self._said:
            current = self._print == self._current_print()
            lines.append(self._said if current else f"{stale_sentence()}\n{self._said}")
            if self._was_current and not current:
                self._announce("Test result is out of date.")  # once, as it happens
            self._was_current = current
        text = "\n".join(lines)
        if self.result.GetValue() != text:
            keep = self.result.GetInsertionPoint() if self.result.HasFocus() else None
            self.result.SetValue(text)
            if keep is not None:
                self.result.SetInsertionPoint(min(keep, self.result.GetLastPosition()))

    def _refuse(self, reason: str) -> None:
        """Say why a press did nothing, and keep it as text in Test result."""
        self._note = reason
        self.refresh()
        self._announce(reason)

    # -- the buttons ------------------------------------------------------------

    def press(self) -> None:
        if self.running:
            self.stop()
            return
        self._stop_hearing()
        self._made = None  # an older test is not this one
        self._note = ""
        station = playing_station(self._host)
        if station is None:
            self._refuse("Play a live station first; the test records what is playing.")
            return
        from quill.core import http_client
        from quill.core.radio.recording import _resolve_capture_url
        from quill.core.speech.ffmpeg import find_ffmpeg

        ffmpeg = find_ffmpeg()
        if ffmpeg is None:
            self._refuse("FFmpeg is needed to record. Get it from the Help menu.")
            return
        name, url = station
        fmt, kbps, apply = self._read_choice()
        graph = filter_graph_for(self._host, apply)
        folder = Path(tempfile.mkdtemp(prefix="quill-radio-test-"))
        self._folders.append(folder)
        stop = threading.Event()
        self._stop = stop
        fingerprint = settings_print(fmt, kbps, graph, url)
        self.test_button.SetLabel("Stop the Test Recordin&g")
        self.refresh()
        started = f"Recording a {TEST_SECONDS}-second test of {name}."
        # A focused button's new name is read by the screen reader already.
        self._announce(
            started if self.test_button.HasFocus() else f"{started} Press again to stop."
        )

        def work() -> None:
            try:
                plan = plan_test(
                    ffmpeg,
                    _resolve_capture_url(url),
                    folder,
                    fmt=fmt,
                    bitrate_kbps=kbps,
                    filter_graph=graph,
                    user_agent=http_client.user_agent(),
                )
                elapsed = run_test(plan.args, stop)
                outcome: Any = (plan.out_path, elapsed)
                error: BaseException | None = None
            except BaseException as exc:  # noqa: BLE001 - said on the UI thread
                outcome, error = None, exc
            wx.CallAfter(self._finished, stop, name, fmt, kbps, fingerprint, outcome, error)

        threading.Thread(  # GATE-40-OK: one 30-second ffmpeg run; Stop terminates it
            target=work, daemon=True, name="radio-test-recording"
        ).start()

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        self._stop = None
        self.test_button.SetLabel("Test These Settin&gs")
        self.refresh()
        self._announce("Test recording stopped. Nothing was kept.")

    def _finished(
        self,
        stop: threading.Event,
        station: str,
        fmt: str,
        kbps: int,
        fingerprint: str,
        outcome: Any,
        error: BaseException | None,
    ) -> None:
        if stop is not self._stop or stop.is_set():
            return  # stopped, or the window closed
        self._stop = None
        try:
            self.test_button.SetLabel("Test These Settin&gs")
        except RuntimeError:
            return  # the window is gone
        if outcome is None:
            self._said = f"The test recording failed: {error}"
            self._print = fingerprint
            self.refresh()
            self._announce("The test recording failed. The reason is in Test result.")
            return
        out_path, elapsed = outcome
        size = out_path.stat().st_size if out_path.is_file() else 0
        seconds = _seconds_of(out_path) or min(elapsed, float(TEST_SECONDS))
        self._said = test_sentence(
            station=station, fmt=fmt, bitrate_kbps=kbps, seconds=seconds, size_bytes=size
        )
        self._print = fingerprint
        self._made = out_path if size > 0 else None
        self._was_current = True
        self.refresh()
        self._announce("Test recording done. The size of an hour is in Test result.")

    def hear(self) -> None:
        """Play the test recording, or stop it playing."""
        import winsound

        if self._playing:
            self._stop_hearing()
            return
        if self._made is None:
            self._refuse("Nothing to hear yet. Press Test These Settings first.")
            return
        try:
            wav = _playable(self._made)
            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as exc:  # noqa: BLE001 - no FFmpeg, no device, or not Windows
            _log.info("Could not play the test recording: %s", exc)
            self._announce(f"The test recording could not be played ({exc}).")
            return
        self._playing = True
        self.hear_button.SetLabel("Stop &Hearing")
        length = _seconds_of(wav) or float(TEST_SECONDS)
        wx.CallLater(int(length * 1000) + 300, self._sound_ended, wav)

    def _sound_ended(self, _wav: Path) -> None:
        if self._playing:
            self._playing = False
            try:
                self.hear_button.SetLabel("&Hear the Test")
            except RuntimeError:
                pass  # the window is gone

    def _stop_hearing(self) -> None:
        if not self._playing:
            return
        self._playing = False
        try:
            import winsound

            winsound.PlaySound(None, 0)
        except Exception:  # noqa: BLE001 - nothing to stop, or not Windows
            pass
        try:
            self.hear_button.SetLabel("&Hear the Test")
        except RuntimeError:
            pass  # the window is gone

    # -- cleanup --------------------------------------------------------------

    def _on_destroy(self, evt: Any) -> None:
        if evt.GetEventObject() is self._dialog:
            self.close()
        evt.Skip()

    def close(self) -> None:
        if self._stop is not None:
            self._stop.set()
            self._stop = None
        if self._playing:
            try:
                import winsound

                winsound.PlaySound(None, 0)
            except Exception:  # noqa: BLE001 - nothing to stop
                pass
            self._playing = False
        for folder in self._folders:
            shutil.rmtree(folder, ignore_errors=True)
        self._folders.clear()


def _seconds_of(path: Path) -> float:
    try:
        from quill.core.audio.media_probe import probe

        return float(probe(path).duration_s)
    except Exception:  # noqa: BLE001 - an unreadable file has no length
        return 0.0


def _playable(made: Path) -> Path:
    """*made* when it is WAV; otherwise a WAV decoded beside it, for winsound."""
    if made.suffix.lower() == ".wav":
        return made
    from quill.core.audio.assemble import build_decode_to_wav_command
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is needed to play it")
    out = made.with_name("test-play.wav")
    if not out.is_file():
        done = run_subprocess_safely(
            build_decode_to_wav_command(ffmpeg, made, out), timeout_seconds=60.0
        )
        if getattr(done, "returncode", 1) != 0:
            raise RuntimeError("it could not be decoded")
    return out
