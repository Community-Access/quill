"""Identify This Song: the command, its menu row, and the wiring to a worker.

The pipeline and every sentence live in :mod:`quill.core.radio.song_recognition`;
this module only gathers what that needs from the running app -- the key, fpcalc,
and a sample from the buffer -- and speaks the answer when it comes back.

Order matters, and it is the order a listener can act on: no key first (the one
step they must take by hand), then no fpcalc, then nothing playing or the wrong
engine, and only then any audio. Every refusal is a sentence; nothing here can
fail silently, because a key that does nothing is indistinguishable from a
broken one.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

#: ``(command id, palette title)``.
COMMAND_ID = "radio.identify_song"
PALETTE_TITLE = "Internet Radio: Identify This Song"


def append_menu_item(host: Any, menu: Any, wx: Any) -> Any:
    """Identify This Song, on Playback beside What's Playing. Returns the id."""
    item_id = wx.NewIdRef()
    # The id written out, not COMMAND_ID: the keyboard reference harvests
    # titles from literal _menu_label calls.
    menu.Append(item_id, host._menu_label("Identif&y This Song", "radio.identify_song"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: identify_song(host), id=item_id)
    return item_id


def _sample_dir() -> Path:
    """A private folder for one sample, in the machine-local cache."""
    from quill.core.paths import machine_local_dir

    root = machine_local_dir() / "radio-recognition"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="sample-", dir=root))


def identify_song(host: Any) -> None:
    """Listen to what is playing and say what AcoustID thinks it is."""
    from quill.core.radio import acoustid, chromaprint, song_recognition

    controller = getattr(host, "_radio_controller", None)
    station = getattr(getattr(controller, "state", None), "station", None)
    blocker = song_recognition.precheck(key=acoustid.stored_key(), fpcalc=chromaprint.find_fpcalc())
    if blocker:
        host._announce(blocker)
        return
    if controller is None or station is None:
        host._announce("Nothing is playing.")
        return
    if getattr(host, "_safe_mode", False):
        host._announce("Song recognition is disabled in Safe Mode.")
        return
    engine = getattr(controller, "_mpv_engine", None)
    if engine is None or not controller._is_mpv_active():
        host._announce(song_recognition.NEEDS_MPV)
        return
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        host._announce("Song recognition is unavailable right now.")
        return
    try:
        folder = _sample_dir()
    except OSError:
        host._announce("Song recognition could not make a place to keep the sample.")
        return
    sample = folder / "sample"
    if not engine.dump_recent_audio(song_recognition.SAMPLE_SECONDS, str(sample)):
        shutil.rmtree(folder, ignore_errors=True)
        host._announce(song_recognition.NOT_ENOUGH_AUDIO)
        return
    start_worker(host, task_manager, sample, folder)


def start_worker(host: Any, task_manager: Any, sample: Path, folder: Path) -> None:
    """Fingerprint and look up *sample* off the UI thread, then speak the answer."""
    from quill.core.radio import acoustid, chromaprint, song_recognition

    key = acoustid.stored_key()
    fpcalc = chromaprint.find_fpcalc() or ""
    safe_mode = bool(getattr(host, "_safe_mode", False))
    host._announce(song_recognition.LISTENING)

    def _work(**_kwargs: Any) -> Any:
        try:
            return song_recognition.recognise(sample, key=key, fpcalc=fpcalc, safe_mode=safe_mode)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def _ok(_op: str, result: Any) -> None:
        host._wx.CallAfter(host._announce, result.sentence)

    def _failed(_op: str, _error: BaseException) -> None:
        host._wx.CallAfter(host._announce, song_recognition.DID_NOT_FINISH)

    task_manager.submit("radio-identify-song", _work, on_success=_ok, on_failure=_failed)
