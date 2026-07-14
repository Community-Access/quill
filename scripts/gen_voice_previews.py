"""Generate bundled voice preview MP3 files for all QUILL TTS engines.

Reads preview text from a plain-text file (one paragraph, ideally 1-3 sentences)
and synthesizes it through every registered voice in each engine's catalog,
writing the result to ``quill/data/voice-previews/{engine}/{voice_id}.mp3``.

Requires:
  - ffmpeg on PATH (WAV → MP3 conversion)
  - Engine binaries / models already installed in their default locations
    (or specified via CLI flags)

Usage
-----
    python scripts/gen_voice_previews.py preview_text.txt
    python scripts/gen_voice_previews.py preview_text.txt --engines piper kokoro
    python scripts/gen_voice_previews.py preview_text.txt --overwrite
    python scripts/gen_voice_previews.py preview_text.txt --piper-exe C:/piper/piper.exe
    python scripts/gen_voice_previews.py preview_text.txt --dectalk-exe C:/dectalk/say.exe
    python scripts/gen_voice_previews.py preview_text.txt \
        --espeak-exe "C:/Program Files/eSpeak NG/espeak-ng.exe"

Engines: piper  kokoro  espeak  dectalk
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PREVIEW_DIR = _REPO_ROOT / "quill" / "data" / "voice-previews"
_ALL_ENGINES = ("piper", "kokoro", "espeak", "dectalk", "sapi5")


def _sapi5_short_name(voice_id: str) -> str:
    """Mirror MainFrame._pyttsx3_voice_short_name so generated files resolve in the UX.

    'HKEY_..\\TTS_MS_EN-US_DAVID_11.0' -> 'david'. Kept in sync with
    quill/ui/main_frame.py::_pyttsx3_voice_short_name.
    """
    last = voice_id.replace("/", "\\").rsplit("\\", 1)[-1]
    for part in last.upper().split("_"):
        if not part or part in {"TTS", "MS"} or "-" in part:
            continue
        try:
            float(part)
            continue
        except ValueError:
            pass
        if part.isalpha():
            return part.lower()
    return last.lower()


# ---------------------------------------------------------------------------
# WAV → MP3 via ffmpeg
# ---------------------------------------------------------------------------


def _wav_to_mp3(wav: Path, mp3: Path) -> None:
    """Convert WAV to MP3 at 128 kbps using ffmpeg."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            "-ar",
            "22050",
            str(mp3),
        ],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {wav.name}:\n{result.stderr.decode(errors='replace')}"
        )


# ---------------------------------------------------------------------------
# Per-engine generators
# ---------------------------------------------------------------------------


def _gen_piper(
    text: str,
    out_dir: Path,
    *,
    piper_exe: str | None,
    piper_model_dir: str | None,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Synthesize all catalog Piper voices. Returns (generated, skipped)."""
    from quill.core.read_aloud import (
        default_piper_model_dir,
        discover_piper_executable,
        list_piper_catalog_voices,
        synthesize_with_piper,
    )

    exe = discover_piper_executable(piper_exe or "")
    if exe is None:
        print("  [piper] SKIP — piper executable not found (pass --piper-exe)")
        return 0, 0

    model_dir = Path(piper_model_dir) if piper_model_dir else default_piper_model_dir()
    voices = list_piper_catalog_voices(model_dir)

    generated = skipped = errored = 0
    out_dir.mkdir(parents=True, exist_ok=True)

    for voice in voices:
        mp3 = out_dir / f"{voice.id}.mp3"
        if mp3.exists() and not overwrite:
            print(f"  [piper] skip  {voice.id} (already exists)")
            skipped += 1
            continue

        model_path = model_dir / f"{voice.id}.onnx"
        if not model_path.exists():
            print(f"  [piper] skip  {voice.id} (model not downloaded)")
            skipped += 1
            continue

        print(f"  [piper] gen   {voice.id} ...", end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav = Path(fh.name)
        try:
            synthesize_with_piper(text, wav, executable_path=exe, model_path=model_path)
            _wav_to_mp3(wav, mp3)
            print(f" OK  ({mp3.stat().st_size // 1024} KB)")
            generated += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errored += 1
        finally:
            wav.unlink(missing_ok=True)

    return generated, skipped, errored


def _gen_kokoro(
    text: str,
    out_dir: Path,
    *,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Synthesize all Kokoro voices. Returns (generated, skipped)."""
    from quill.core.read_aloud import kokoro_onnx_ready, list_kokoro_voices, synthesize_with_kokoro

    if not kokoro_onnx_ready():
        print("  [kokoro] SKIP — Kokoro ONNX model files not found")
        return 0, 0

    voices = list_kokoro_voices()
    generated = skipped = errored = 0
    out_dir.mkdir(parents=True, exist_ok=True)

    for voice in voices:
        mp3 = out_dir / f"{voice.id}.mp3"
        if mp3.exists() and not overwrite:
            print(f"  [kokoro] skip  {voice.id} (already exists)")
            skipped += 1
            continue

        print(f"  [kokoro] gen   {voice.id} ...", end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav = Path(fh.name)
        try:
            synthesize_with_kokoro(text, wav, voice=voice.id)
            _wav_to_mp3(wav, mp3)
            print(f" OK  ({mp3.stat().st_size // 1024} KB)")
            generated += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errored += 1
        finally:
            wav.unlink(missing_ok=True)

    return generated, skipped, errored


def _gen_sapi5(
    text: str,
    out_dir: Path,
    *,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Synthesize the installed Windows SAPI 5 voices. Returns counts.

    Files are named by the short voice name (e.g. ``david.mp3``) so the running
    app resolves them for the matching system voice; voices not present on a
    user's machine simply fall back to live synthesis.
    """
    from quill.core.read_aloud import synthesize_to_file_with_sapi5
    from quill.platform.windows import sapi5

    if not sapi5.available():
        print("  [sapi5] SKIP — Windows SAPI 5 is not available")
        return 0, 0, 0
    voices = sapi5.list_voices()

    generated = skipped = errored = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for voice in voices:
        short = _sapi5_short_name(voice.id)
        if short in seen:
            continue  # Desktop + non-Desktop variants share a short name
        seen.add(short)
        mp3 = out_dir / f"{short}.mp3"
        if mp3.exists() and not overwrite:
            print(f"  [sapi5] skip  {short} (already exists)")
            skipped += 1
            continue
        print(f"  [sapi5] gen   {short} ...", end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav = Path(fh.name)
        try:
            synthesize_to_file_with_sapi5(text, wav, voice=voice.id)
            _wav_to_mp3(wav, mp3)
            print(f" OK  ({mp3.stat().st_size // 1024} KB)")
            generated += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errored += 1
        finally:
            wav.unlink(missing_ok=True)

    return generated, skipped, errored


def _gen_espeak(
    text: str,
    out_dir: Path,
    *,
    espeak_exe: str | None,
    espeak_rate: int,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Synthesize all eSpeak English voices. Returns (generated, skipped)."""
    from quill.core.read_aloud import (
        discover_espeak_executable,
        list_espeak_english_voices,
        synthesize_with_espeak,
    )

    exe = discover_espeak_executable(espeak_exe or "")
    if exe is None:
        print("  [espeak] SKIP — espeak-ng executable not found (pass --espeak-exe)")
        return 0, 0

    voices = list_espeak_english_voices()
    generated = skipped = errored = 0
    out_dir.mkdir(parents=True, exist_ok=True)

    for voice in voices:
        mp3 = out_dir / f"{voice.id}.mp3"
        if mp3.exists() and not overwrite:
            print(f"  [espeak] skip  {voice.id} (already exists)")
            skipped += 1
            continue

        print(f"  [espeak] gen   {voice.id} ...", end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav = Path(fh.name)
        try:
            synthesize_with_espeak(text, wav, executable_path=exe, voice=voice.id, rate=espeak_rate)
            _wav_to_mp3(wav, mp3)
            print(f" OK  ({mp3.stat().st_size // 1024} KB)")
            generated += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errored += 1
        finally:
            wav.unlink(missing_ok=True)

    return generated, skipped, errored


def _gen_dectalk(
    text: str,
    out_dir: Path,
    *,
    dectalk_exe: str | None,
    dectalk_rate: int,
    overwrite: bool,
) -> tuple[int, int, int]:
    """Synthesize all DECTalk voices. Returns (generated, skipped)."""
    from quill.core.read_aloud import (
        discover_dectalk_executable,
        list_dectalk_voices,
        synthesize_to_file_with_dectalk,
    )

    exe = discover_dectalk_executable(dectalk_exe or "")
    if exe is None:
        print("  [dectalk] SKIP — DECTalk executable not found (pass --dectalk-exe)")
        return 0, 0

    voices = list_dectalk_voices()
    generated = skipped = errored = 0
    out_dir.mkdir(parents=True, exist_ok=True)

    for voice in voices:
        mp3 = out_dir / f"{voice.id}.mp3"
        if mp3.exists() and not overwrite:
            print(f"  [dectalk] skip  {voice.id} (already exists)")
            skipped += 1
            continue

        print(f"  [dectalk] gen   {voice.id} ...", end="", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            wav = Path(fh.name)
        try:
            synthesize_to_file_with_dectalk(
                text, wav, executable_path=exe, voice=voice.id, rate=dectalk_rate
            )
            _wav_to_mp3(wav, mp3)
            print(f" OK  ({mp3.stat().st_size // 1024} KB)")
            generated += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errored += 1
        finally:
            wav.unlink(missing_ok=True)

    return generated, skipped, errored


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate all bundled voice preview MP3s from a text file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "text_file",
        nargs="?",
        default=str(_REPO_ROOT / "scripts" / "phrase.txt"),
        help=(
            "Path to a plain-text file containing the preview text (1-3 sentences). "
            "Defaults to scripts/phrase.txt, the single phrase shared by all demos."
        ),
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        choices=_ALL_ENGINES,
        default=list(_ALL_ENGINES),
        metavar="ENGINE",
        help=f"Which engines to generate (default: all). Choices: {', '.join(_ALL_ENGINES)}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing MP3 files (default: skip).",
    )
    parser.add_argument("--piper-exe", metavar="PATH", help="Path to the piper executable.")
    parser.add_argument(
        "--piper-model-dir", metavar="DIR", help="Directory containing .onnx model files."
    )
    parser.add_argument(
        "--dectalk-exe",
        metavar="PATH",
        help="Path to DECtalk.dll (the synthesis runtime) or its folder.",
    )
    parser.add_argument(
        "--dectalk-rate", type=int, default=180, help="DECTalk words-per-minute rate (default 180)."
    )
    parser.add_argument("--espeak-exe", metavar="PATH", help="Path to espeak-ng executable.")
    parser.add_argument(
        "--espeak-rate", type=int, default=160, help="eSpeak words-per-minute rate (default 160)."
    )
    args = parser.parse_args(argv)

    # Verify ffmpeg is available.
    if shutil.which("ffmpeg") is None:
        print(
            "ERROR: ffmpeg not found on PATH. Install ffmpeg and ensure it is on PATH.",
            file=sys.stderr,
        )
        return 1

    # Read preview text.
    text_path = Path(args.text_file)
    if not text_path.exists():
        print(f"ERROR: text file not found: {text_path}", file=sys.stderr)
        return 1
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: text file is empty.", file=sys.stderr)
        return 1
    print(f"Preview text ({len(text)} chars): {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"Output directory: {_PREVIEW_DIR}")
    print(f"Engines: {', '.join(args.engines)}")
    print(f"Overwrite: {args.overwrite}")
    print()

    total_gen = total_skip = total_err = 0

    if "piper" in args.engines:
        print("=== Piper ===")
        g, s, e = _gen_piper(
            text,
            _PREVIEW_DIR / "piper",
            piper_exe=args.piper_exe,
            piper_model_dir=args.piper_model_dir,
            overwrite=args.overwrite,
        )
        total_gen += g
        total_skip += s
        total_err += e
        print()

    if "kokoro" in args.engines:
        print("=== Kokoro ===")
        g, s, e = _gen_kokoro(text, _PREVIEW_DIR / "kokoro", overwrite=args.overwrite)
        total_gen += g
        total_skip += s
        total_err += e
        print()

    if "espeak" in args.engines:
        print("=== eSpeak ===")
        g, s, e = _gen_espeak(
            text,
            _PREVIEW_DIR / "espeak",
            espeak_exe=args.espeak_exe,
            espeak_rate=args.espeak_rate,
            overwrite=args.overwrite,
        )
        total_gen += g
        total_skip += s
        total_err += e
        print()

    if "dectalk" in args.engines:
        print("=== DECTalk ===")
        g, s, e = _gen_dectalk(
            text,
            _PREVIEW_DIR / "dectalk",
            dectalk_exe=args.dectalk_exe,
            dectalk_rate=args.dectalk_rate,
            overwrite=args.overwrite,
        )
        total_gen += g
        total_skip += s
        total_err += e
        print()

    if "sapi5" in args.engines:
        print("=== sapi5 (Windows SAPI 5) ===")
        g, s, e = _gen_sapi5(text, _PREVIEW_DIR / "sapi5", overwrite=args.overwrite)
        total_gen += g
        total_skip += s
        total_err += e
        print()

    status = "FAILURE" if total_err else "SUCCESS"
    print(f"{status}. Generated: {total_gen}  Skipped: {total_skip}  Errors: {total_err}")
    # Non-zero exit when any requested voice failed, so callers (and the batch
    # wrapper) can detect partial failure even though other voices succeeded.
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
