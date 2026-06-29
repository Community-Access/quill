"""whisper.cpp speech-to-text provider (#617 section 4.1).

The default offline provider. It drives a whisper.cpp command-line executable
(``whisper-cli`` / ``main``) as a subprocess via
:func:`quill.stability.safe_subprocess.run_subprocess_safely`, and downloads GGML
models over HTTPS from the Hugging Face Hub whisper.cpp repository
(``ggerganov/whisper.cpp``) — the source listed in #617 — without adding a heavy
``huggingface_hub`` dependency.

Design rules (#617 section 8.2 / section 17):

- Lazy: nothing here is imported at QUILL startup; the registry constructs the
  provider, and heavy work happens only on an explicit user action.
- Safe: the executable basename must be on a narrow allowlist; downloads are
  HTTPS-only with a verified TLS context, run only on an explicit user action,
  are blocked in Safe Mode, and are tracked by the network-egress audit.
- Honest: failures raise :class:`SpeechError` with a clear, speakable message.

The pure helpers (:func:`parse_whisper_json`, :func:`build_whisper_command`,
:func:`resolve_whisper_executable`) are unit-tested directly; the subprocess and
download paths are thin wrappers over them.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from quill.core.speech import catalog, models
from quill.core.speech.provider import (
    InstalledSpeechModel,
    ProgressCallback,
    ProviderInstallStatus,
    SizeEstimate,
    SpeechError,
    SpeechModelInfo,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)

PROVIDER_ID = "whispercpp"

# Narrow security allowlist for the whisper.cpp CLI basename (with/without the
# Windows .exe suffix). QUILL never runs an arbitrary executable for speech.
_ALLOWED_BASENAMES = frozenset({
    "whisper-cli",
    "whisper",
    "main",
    "whisper-cli.exe",
    "whisper.exe",
    "main.exe",
})

_VERIFIED_TLS = ssl.create_default_context()
_DOWNLOAD_TIMEOUT_S = 30.0
_TRANSCRIBE_TIMEOUT_S = 1800.0  # 30 min ceiling for a long file


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #


def parse_whisper_json(text: str) -> TranscriptionResult:
    """Parse whisper.cpp ``-oj`` JSON output into a TranscriptionResult."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpeechError(f"Could not read the transcription output: {exc}") from exc
    if not isinstance(data, dict):
        raise SpeechError("Transcription output was not in the expected format.")
    raw_items = [item for item in (data.get("transcription") or []) if isinstance(item, dict)]
    # whisper.cpp tinydiarize (-tdrz) appends "[SPEAKER_TURN]" at each turn change.
    # Only label speakers when such markers are present (i.e. diarization ran).
    diarized = any("[SPEAKER_TURN]" in str(item.get("text", "")) for item in raw_items)
    segments: list[TranscriptionSegment] = []
    speaker_number = 1
    for item in raw_items:
        offsets = item.get("offsets", {}) if isinstance(item.get("offsets"), dict) else {}
        raw_text = str(item.get("text", ""))
        turn_after = "[SPEAKER_TURN]" in raw_text
        seg_text = raw_text.replace("[SPEAKER_TURN]", "").strip()
        speaker = f"Speaker {speaker_number}" if diarized else ""
        try:
            segments.append(
                TranscriptionSegment(
                    float(offsets.get("from", 0)) / 1000.0,
                    float(offsets.get("to", 0)) / 1000.0,
                    seg_text,
                    speaker=speaker,
                )
            )
        except (TypeError, ValueError):
            continue
        if turn_after:
            speaker_number += 1
    full_text = " ".join(seg.text for seg in segments if seg.text).strip()
    language = None
    result_block = data.get("result")
    if isinstance(result_block, dict):
        language = result_block.get("language")
    duration = segments[-1].end_seconds if segments else None
    return TranscriptionResult(
        full_text=full_text,
        segments=tuple(segments),
        provider_id=PROVIDER_ID,
        language=language,
        duration_seconds=duration,
    )


def build_whisper_command(
    executable: str,
    model_path: Path,
    audio_path: Path,
    output_base: Path,
    request: TranscriptionRequest,
) -> list[str]:
    """Build the whisper.cpp argv for a transcription (JSON output)."""
    args = [
        executable,
        "-m",
        str(model_path),
        "-f",
        str(audio_path),
        "-oj",
        "-of",
        str(output_base),
    ]
    if request.language:
        args += ["-l", request.language]
    if request.translate_to_english:
        args.append("-tr")
    if request.diarize:
        args.append("-tdrz")  # whisper.cpp tinydiarize: mark speaker turns
    return args


def engine_search_dirs() -> list[Path]:
    """QUILL-managed locations where a bundled/downloaded whisper.cpp may live.

    1. ``{QUILL_APP_ROOT}/tools/speech/whispercpp`` — the optional installer
       component (InnoSetup) / portable bundle, mirroring the DECtalk/Piper layout.
    2. ``<data>/speech-engine`` — an engine downloaded at runtime.
    """
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "speech" / "whispercpp")
    dirs.append(models.app_data_dir() / "speech-engine")
    return dirs


def resolve_whisper_executable(configured_path: str | None = None) -> str | None:
    """Find an allowed whisper.cpp executable, or None if not installed.

    Resolution order: a configured path, then the QUILL-managed engine locations
    (installer component / portable bundle / downloaded engine), then the system
    PATH. In every case the basename must be on the security allowlist, so QUILL
    only ever launches a known whisper.cpp executable.
    """
    if configured_path:
        candidate = Path(configured_path)
        if candidate.name.lower() in _ALLOWED_BASENAMES and candidate.is_file():
            return str(candidate)
    bundled_names = (
        "whisper-cli.exe",
        "whisper-cli",
        "main.exe",
        "main",
        "whisper.exe",
        "whisper",
    )
    for directory in engine_search_dirs():
        for name in bundled_names:
            probe = directory / name
            if probe.is_file() and probe.name.lower() in _ALLOWED_BASENAMES:
                return str(probe)
    for name in ("whisper-cli", "whisper", "main"):
        found = shutil.which(name)
        if found and Path(found).name.lower() in _ALLOWED_BASENAMES:
            return found
    return None


def _model_path(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / f"ggml-{model_id}.bin"


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class WhisperCppProvider:
    """The default offline whisper.cpp provider."""

    id = PROVIDER_ID
    display_name = "Whisper (offline)"
    description = "Local, private transcription using whisper.cpp. No audio leaves your computer."

    def __init__(self, executable_path: str | None = None) -> None:
        self._configured = executable_path

    # -- availability ----------------------------------------------------- #

    def executable(self) -> str | None:
        return resolve_whisper_executable(self._configured)

    def is_available(self) -> bool:
        return self.executable() is not None

    def get_install_status(self) -> ProviderInstallStatus:
        exe = self.executable()
        if exe is None:
            return ProviderInstallStatus(
                installed=False,
                detail=(
                    "The offline speech engine is not installed yet. Use "
                    "Tools > Speech > Download Offline Speech Engine to fetch it "
                    "(about 8 MB, verified), or place whisper-cli under "
                    "tools/speech/whispercpp."
                ),
            )
        return ProviderInstallStatus(installed=True, detail=exe)

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return list(catalog.WHISPER_CPP_MODELS)

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [m for m in models.load_installed_models() if m.provider_id == PROVIDER_ID]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        info = catalog.model_by_id(model_id)
        size = info.approximate_size_mb if info else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        # H-SAFE-1: refuse network model downloads in Safe Mode (same process-level
        # QUILL_SAFE_MODE flag the assistant network calls check).
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            raise SpeechError("Downloading speech models is disabled in Safe Mode.")
        info = catalog.model_by_id(model_id)
        if info is None or not info.download_url:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        target = _model_path(model_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        _download_to_file(info, target, progress)
        installed = InstalledSpeechModel(
            id=model_id,
            display_name=info.display_name,
            path=target,
            size_mb=info.approximate_size_mb,
            provider_id=PROVIDER_ID,
            sha256=info.sha256,
            installed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )
        models.record_installed_model(installed)
        return installed

    def remove_model(self, model_id: str) -> None:
        target = _model_path(model_id)
        if target.exists():
            target.unlink()
        models.remove_installed_model(model_id, PROVIDER_ID)

    # -- transcription ---------------------------------------------------- #

    def _prepare_audio(
        self, source: Path, tmp_dir: Path, progress: ProgressCallback | None
    ) -> Path:
        """Return an audio path whisper.cpp can read (16 kHz mono WAV).

        whisper.cpp only reliably reads 16 kHz mono WAV. When ffmpeg is available
        we transcode any input (mp3, m4a, mp4, stereo/48k WAV, ...) into the temp
        dir; the caller's ``TemporaryDirectory`` cleans it up. Without ffmpeg we
        pass a ``.wav`` straight through (best effort) but refuse other formats
        with a clear, actionable message instead of letting whisper.cpp fail.
        """
        from quill.core.speech import ffmpeg as ffmpeg_tools

        if ffmpeg_tools.ffmpeg_available():
            try:
                return ffmpeg_tools.transcode_to_wav(source, out_dir=tmp_dir, progress=progress)
            except ffmpeg_tools.TranscodeError as exc:
                raise SpeechError(f"Could not prepare the audio for transcription: {exc}") from exc
        if source.suffix.lower() != ".wav":
            raise SpeechError(
                f"This audio format ({source.suffix or 'unknown'}) needs ffmpeg to convert "
                f"it first. {ffmpeg_tools.INSTALL_HINT} Or provide a 16 kHz mono WAV file."
            )
        return source

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        from quill.stability.safe_subprocess import run_subprocess_safely

        exe = self.executable()
        if exe is None:
            raise SpeechError(
                "The whisper.cpp program was not found. Install it before transcribing."
            )
        model_path = _model_path(request.model_id)
        if not model_path.is_file():
            raise SpeechError(
                f"The '{request.model_id}' speech model is not installed. "
                "Download it from Manage Speech Models first."
            )
        if not request.source_path.is_file():
            raise SpeechError(f"The audio file was not found: {request.source_path}")
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = self._prepare_audio(request.source_path, Path(tmp), progress)
            if progress is not None:
                progress(0.05, "Transcribing...")
            output_base = Path(tmp) / "transcript"
            args = build_whisper_command(exe, model_path, audio_path, output_base, request)
            try:
                completed = run_subprocess_safely(args, timeout_seconds=_TRANSCRIBE_TIMEOUT_S)
            except OSError as exc:
                raise SpeechError(f"Could not run whisper.cpp: {exc}") from exc
            if completed.returncode != 0:
                detail = (completed.stderr or "").strip()[:300]
                raise SpeechError(f"Transcription failed (code {completed.returncode}). {detail}")
            json_path = output_base.with_suffix(".json")
            if not json_path.is_file():
                raise SpeechError("Transcription produced no output.")
            result = parse_whisper_json(json_path.read_text(encoding="utf-8", errors="replace"))
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=result.full_text,
            segments=result.segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id,
            language=result.language,
            duration_seconds=result.duration_seconds,
            warnings=result.warnings,
        )

    def cancel(self) -> None:
        # Subprocess runs are bounded by a timeout; cooperative cancel of an
        # in-flight whisper.cpp run lands with the streaming work in S3.
        return None

    def unload(self) -> None:
        return None


def _download_to_file(
    info: SpeechModelInfo, target: Path, progress: ProgressCallback | None
) -> None:
    """Stream a model file from the Hugging Face Hub over verified HTTPS.

    GATE-9 / network-egress: this is the only outbound call here; it runs only on
    an explicit user "download model" action, uses a verified TLS context, and is
    blocked in Safe Mode by the caller. The file is written to a temp path and
    atomically moved into place, then sha256-verified when a hash is known.
    """
    url = info.download_url or ""
    if not url.lower().startswith("https://"):
        raise SpeechError("Model downloads must use a secure (HTTPS) address.")
    headers = {"User-Agent": "QUILL"}
    from quill.core.speech.hf_auth import load_hf_token

    token = load_hf_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    digest = hashlib.sha256()
    fd, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".part", dir=str(target.parent)
    )
    temp_path = Path(raw_temp)
    try:
        with (
            urllib.request.urlopen(  # noqa: S310 - HTTPS enforced above
                request, timeout=_DOWNLOAD_TIMEOUT_S, context=_VERIFIED_TLS
            ) as response,
            os.fdopen(fd, "wb") as out,
        ):
            total = int(response.headers.get("Content-Length", 0) or 0)
            read = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                read += len(chunk)
                if progress is not None and total > 0:
                    progress(min(read / total, 0.99), f"Downloading {info.display_name}...")
        if info.sha256 and digest.hexdigest().lower() != info.sha256.lower():
            raise SpeechError("The downloaded model failed its integrity check. Try again.")
        os.replace(temp_path, target)
    except SpeechError:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean message, clean up the partial file
        temp_path.unlink(missing_ok=True)
        from quill.core.speech.hf_auth import RATE_LIMIT_HELP, looks_rate_limited

        if looks_rate_limited(exc):
            raise SpeechError(RATE_LIMIT_HELP) from exc
        raise SpeechError(f"The model download failed: {exc}") from exc
