"""Console DECtalk synthesizer: a stdin/-w wrapper around ``DECtalk.dll``.

Why this exists
---------------
The DECtalk package shipped in ``dectalk/dectalk`` releases contains
``AMD64\\speak.exe``, which its own ``devops/vs2022/dt_copyfiles.bat`` builds
from "Sample Speak Window.exe" -- it is the *graphical* sample, not a console
synthesizer. Driving it like a CLI (``-file``/``-wav``/``-dict``) makes it enter
Windows message handling and fast-fail with ``0xC000041D``
(``STATUS_FATAL_USER_CALLBACK_EXCEPTION``). The package ships no console
``say.exe``.

This module is the equivalent console wrapper: it loads ``DECtalk.dll`` directly
through its documented Text-To-Speech API and writes a wave file, using
``DO_NOT_USE_AUDIO_DEVICE`` so it never opens an audio device or a window. It is
deliberately self-contained (standard library only, no ``quill`` imports) so it
can be spawned as ``python dectalk_say.py`` in a short-lived child process. That
isolation matters: the DLL locates its dictionary relative to the current
working directory, and changing cwd process-wide inside the wx UI thread would
be unsafe, so synthesis runs out-of-process.

Interface
---------
    <payload on stdin, cp1252-encoded>
    python dectalk_say.py --dll <path to DECtalk.dll> -w <output.wav>

The DECtalk payload (voice command, rate command, and text, e.g.
``[:nb] [:ra 180] Hello.``) is read from standard input. Output is a RIFF/WAVE
file at the engine's native rate. Exit status is ``0`` on success; non-zero with
a diagnostic on stderr otherwise.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import wave
from ctypes import wintypes
from pathlib import Path

# DECtalk / mmsystem constants (see dectalk src/dapi/src/api/ttsapi.h).
_DO_NOT_USE_AUDIO_DEVICE = 0x80000000
_TTS_FORCE = 1
_WAVE_MAPPER = 0xFFFFFFFF
# Native engine format that this DECtalk build emits (11.025 kHz, mono). The
# nominal 16-bit code (0x0008) is rejected by the vs2022 build's
# OpenWaveOutFile; 0x0004 is the format it actually renders.
_WAVE_FORMAT_NATIVE = 0x0004
_DICTIONARY_NAME = "dtalk_us.dic"
_VOICE_MODULE_NAME = "dtalk_us.dll"


class DectalkSayError(RuntimeError):
    """Raised when DECtalk synthesis fails; message is a user-facing diagnostic."""


def _resolve_runtime(dll_path: Path) -> tuple[Path, Path]:
    """Return (dll_path, dll_dir), validating the runtime layout.

    ``dll_path`` may point at ``DECtalk.dll`` itself or at the directory that
    contains it. The directory must also hold the dictionary and the language
    voice module (in ``lib/``), matching the official package layout.
    """
    dll_path = dll_path.expanduser()
    if dll_path.is_dir():
        candidate = dll_path / "DECtalk.dll"
    else:
        candidate = dll_path
    # os.add_dll_directory and a clean cwd switch both require absolute paths.
    candidate = candidate.resolve()
    if candidate.name.lower() != "dectalk.dll":
        raise DectalkSayError(
            f"DECtalk runtime must be DECtalk.dll, not {candidate.name!r}. "
            "speak.exe is the graphical sample and cannot synthesize."
        )
    if not candidate.is_file():
        raise DectalkSayError(f"DECtalk.dll was not found at {candidate}")
    dll_dir = candidate.parent
    missing = [
        name
        for name, path in (
            (_DICTIONARY_NAME, dll_dir / _DICTIONARY_NAME),
            (_VOICE_MODULE_NAME, dll_dir / "lib" / _VOICE_MODULE_NAME),
        )
        if not path.exists()
    ]
    if missing:
        raise DectalkSayError(
            f"DECtalk runtime at {dll_dir} is missing required files: {', '.join(missing)}"
        )
    return candidate, dll_dir


def synthesize(dll_path: Path, payload: bytes, output_path: Path) -> None:
    """Synthesize ``payload`` (cp1252 DECtalk text) to ``output_path`` as WAV.

    Loads ``DECtalk.dll`` and drives Startup -> OpenWaveOutFile -> Speak -> Sync
    -> Close -> Shutdown with the audio device disabled. The current working
    directory is switched to the runtime folder for the duration of the call so
    DECtalk can locate its dictionary; callers should run this in a dedicated
    process because that cwd change is process-global.
    """
    candidate, dll_dir = _resolve_runtime(dll_path)
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # The voice module is loaded by DECtalk via a bare LoadLibrary, which honours
    # PATH and the cwd but not add_dll_directory; put lib/ on PATH explicitly.
    os.environ["PATH"] = os.pathsep.join([
        str(dll_dir / "lib"),
        str(dll_dir),
        os.environ.get("PATH", ""),
    ])
    os.add_dll_directory(str(dll_dir))
    os.add_dll_directory(str(dll_dir / "lib"))

    previous_cwd = os.getcwd()
    os.chdir(str(dll_dir))  # so DECtalk finds dtalk_us.dic
    try:
        dll = ctypes.WinDLL(str(candidate))
        dll.TextToSpeechStartup.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        dll.TextToSpeechOpenWaveOutFile.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        dll.TextToSpeechSpeak.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint]
        for name in (
            "TextToSpeechSync",
            "TextToSpeechCloseWaveOutFile",
            "TextToSpeechShutdown",
        ):
            getattr(dll, name).argtypes = [ctypes.c_void_p]

        handle = ctypes.c_void_p()
        rc = dll.TextToSpeechStartup(
            None, ctypes.byref(handle), _WAVE_MAPPER, _DO_NOT_USE_AUDIO_DEVICE
        )
        if rc != 0:
            # MMSYSERR_ERROR from startup specifically means the dictionary was
            # not located; surface that distinctly.
            detail = " (DECtalk dictionary not found)" if rc == 1 else ""
            raise DectalkSayError(f"TextToSpeechStartup failed (code {rc}){detail}")
        try:
            rc = dll.TextToSpeechOpenWaveOutFile(
                handle, str(output_path).encode("mbcs"), _WAVE_FORMAT_NATIVE
            )
            if rc != 0:
                raise DectalkSayError(f"TextToSpeechOpenWaveOutFile failed (code {rc})")
            rc = dll.TextToSpeechSpeak(handle, payload, _TTS_FORCE)
            if rc != 0:
                raise DectalkSayError(f"TextToSpeechSpeak failed (code {rc})")
            # Trailing whitespace flushes the final phonemes (mirrors say.c).
            dll.TextToSpeechSpeak(handle, b"        ", _TTS_FORCE)
            dll.TextToSpeechSync(handle)
            dll.TextToSpeechCloseWaveOutFile(handle)
        finally:
            dll.TextToSpeechShutdown(handle)
    finally:
        os.chdir(previous_cwd)

    _validate_wave(output_path)


def _validate_wave(path: Path) -> None:
    """Ensure ``path`` is a non-empty RIFF/WAVE file containing audio frames."""
    if not path.exists():
        raise DectalkSayError("DECtalk produced no output file")
    if path.stat().st_size <= 44:  # 44 bytes == an empty WAV header
        raise DectalkSayError("DECtalk produced an empty wave file (no audio)")
    try:
        with wave.open(str(path)) as handle:
            if handle.getnframes() <= 0:
                raise DectalkSayError("DECtalk wave file contains no audio frames")
    except wave.Error as exc:
        raise DectalkSayError(f"DECtalk output is not a valid WAVE file: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize DECtalk text (stdin) to a wave file.")
    parser.add_argument("--dll", required=True, help="Path to DECtalk.dll or its folder.")
    parser.add_argument("-w", "--wave", required=True, help="Output wave file path.")
    args = parser.parse_args(argv)

    payload = sys.stdin.buffer.read()
    if not payload.strip():
        print("dectalk_say: empty payload on stdin", file=sys.stderr)
        return 2
    try:
        synthesize(Path(args.dll), payload, Path(args.wave))
    except DectalkSayError as exc:
        print(f"dectalk_say: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"dectalk_say: could not load DECtalk runtime: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
