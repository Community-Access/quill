"""Vosk speech-to-text provider (Kaldi) — optional, offline, very low resource.

Vosk is a lightweight offline ASR engine. Unlike whisper.cpp / Faster Whisper it
needs **no GPU** and runs comfortably on very low-end CPUs with a
~40 MB English model — which makes it the accessibility-reach option for old or
constrained machines. It is an optional pip dependency (``vosk``); models are ZIP
archives on alphacephei.com, pinned by their published MD5.

Design rules mirror the other optional engines:

- Lazy: ``vosk`` is imported only inside methods; ``is_available`` only *locates*
  the module (``find_spec``) so an uninstalled engine never affects startup.
- Safe: the model download runs only on an explicit user action, over verified
  HTTPS, is blocked in Safe Mode, MD5-verifies the archive, and guards against
  zip-slip on extract. The single outbound call is recorded in the
  network-egress audit.
- On-device: ``requires_network`` is False; the offline transcribe paths may use
  it. English models only.
- Honest: failures raise :class:`SpeechError` with clear, speakable messages.

The pure helper :func:`result_from_vosk` is unit-tested directly.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import ssl
import tempfile
import urllib.request
import wave
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

PROVIDER_ID = "vosk"

_VERIFIED_TLS = ssl.create_default_context()
_DOWNLOAD_TIMEOUT_S = 60.0


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #


def result_from_vosk(chunks: Iterable[Any]) -> tuple[str, tuple[TranscriptionSegment, ...]]:
    """Map Vosk recognizer result chunks to full text + segments.

    Each chunk is a parsed JSON dict from ``KaldiRecognizer`` with ``text`` and an
    optional ``result`` word list (each word carries ``start``/``end``). One
    non-empty chunk becomes one segment, timed from its first/last word. Vosk does
    not attribute speakers, so ``speaker`` is always empty.
    """
    texts: list[str] = []
    segments: list[TranscriptionSegment] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        texts.append(text)
        words = chunk.get("result")
        start = end = 0.0
        if isinstance(words, list) and words:
            try:
                start = float(words[0].get("start", 0.0))
                end = float(words[-1].get("end", 0.0))
            except (TypeError, ValueError, AttributeError):
                start = end = 0.0
        segments.append(TranscriptionSegment(start, end, text))
    return " ".join(texts).strip(), tuple(segments)


def _model_dir(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / model_id


def _vosk_model_root(model_dir: Path) -> Path | None:
    """Return the directory Vosk's ``Model`` loads (the one holding ``conf``).

    A Vosk zip extracts a single ``vosk-model-.../`` folder; accept either that
    nested folder or the model dir itself if already flattened.
    """
    if not model_dir.is_dir():
        return None
    if (model_dir / "conf").is_dir():
        return model_dir
    for sub in sorted(model_dir.iterdir()):
        if sub.is_dir() and (sub / "conf").is_dir():
            return sub
    return None


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract ``zf`` into ``dest``, refusing any member that escapes it (zip-slip)."""
    dest_resolved = dest.resolve()
    for member in zf.namelist():
        target = (dest_resolved / member).resolve()
        if dest_resolved not in target.parents and target != dest_resolved:
            raise SpeechError("The model archive contains an unsafe path and was rejected.")
    zf.extractall(dest_resolved)


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class VoskProvider:
    """Optional offline provider built on Vosk (Kaldi). CPU-only, low resource."""

    id = PROVIDER_ID
    display_name = "Vosk (offline, low-resource)"
    description = (
        "Local, private English transcription using Vosk. Tiny models, CPU-only — "
        "ideal for low-end machines. No audio leaves your computer."
    )
    requires_network = False

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded_model_id: str | None = None

    # -- availability ----------------------------------------------------- #

    def is_available(self) -> bool:
        import importlib.util

        try:
            return importlib.util.find_spec("vosk") is not None
        except Exception:  # noqa: BLE001 - any probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if not self.is_available():
            return ProviderInstallStatus(
                installed=False,
                detail="Vosk is not installed. Install QUILL's optional 'vosk' dependency.",
            )
        return ProviderInstallStatus(installed=True, detail="CPU")

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return list(catalog.VOSK_MODELS)

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [m for m in models.load_installed_models() if m.provider_id == PROVIDER_ID]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        info = catalog.vosk_model_by_id(model_id)
        size = info.approximate_size_mb if info else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            raise SpeechError("Downloading speech models is disabled in Safe Mode.")
        info = catalog.vosk_model_by_id(model_id)
        if info is None or not info.download_url:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        target = _model_dir(model_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir(exist_ok=True)
        _download_zip(info, target, progress)
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
        target = _model_dir(model_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        models.remove_installed_model(model_id, PROVIDER_ID)

    # -- transcription ---------------------------------------------------- #

    def _ensure_model(self, model_id: str) -> Any:
        if self._model is not None and self._loaded_model_id == model_id:
            return self._model
        root = _vosk_model_root(_model_dir(model_id))
        if root is None:
            raise SpeechError(
                f"The '{model_id}' Vosk model is not installed. "
                "Download it from Manage Speech Models first."
            )
        try:
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)  # silence Kaldi's stderr chatter
            self._model = Model(str(root))
        except Exception as exc:  # noqa: BLE001 - surface a clean, speakable message
            raise SpeechError(f"Could not load the Vosk model: {exc}") from exc
        self._loaded_model_id = model_id
        return self._model

    def _prepare_audio(
        self, source: Path, tmp_dir: Path, progress: ProgressCallback | None
    ) -> Path:
        """Return a 16 kHz mono WAV path Vosk can read (transcoded via ffmpeg)."""
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
        if not request.source_path.is_file():
            raise SpeechError(f"The audio file was not found: {request.source_path}")
        warnings: list[str] = []
        if request.diarize:
            warnings.append("Vosk does not label speakers; speaker turns were skipped.")
        if request.language and request.language.lower() not in ("en", "english"):
            warnings.append("This Vosk model is English; the language request was ignored.")
        model = self._ensure_model(request.model_id)
        if progress is not None:
            progress(0.1, "Transcribing...")
        with tempfile.TemporaryDirectory(prefix="quill-vosk-") as tmp:
            audio = self._prepare_audio(request.source_path, Path(tmp), progress)
            chunks = _recognize(model, audio, progress)
        text, segments = result_from_vosk(chunks)
        duration = segments[-1].end_seconds if segments else None
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=text,
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id,
            language="en",
            duration_seconds=duration,
            warnings=tuple(warnings),
        )

    def cancel(self) -> None:
        return None

    def unload(self) -> None:
        self._model = None
        self._loaded_model_id = None


def _recognize(model: Any, audio: Path, progress: ProgressCallback | None) -> list[Any]:
    """Run the Kaldi recognizer over a 16 kHz mono WAV and collect result chunks."""
    from vosk import KaldiRecognizer

    try:
        wf = wave.open(str(audio), "rb")
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(f"Could not read the prepared audio: {exc}") from exc
    with wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise SpeechError("Vosk needs 16 kHz mono 16-bit WAV audio.")
        recognizer = KaldiRecognizer(model, wf.getframerate())
        recognizer.SetWords(True)
        chunks: list[Any] = []
        total = wf.getnframes() or 1
        done = 0
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            done += 4000
            if recognizer.AcceptWaveform(data):
                chunks.append(json.loads(recognizer.Result()))
            if progress is not None:
                progress(min(0.1 + 0.85 * done / total, 0.99), "Transcribing...")
        chunks.append(json.loads(recognizer.FinalResult()))
    return chunks


def _download_zip(
    info: SpeechModelInfo, model_dir: Path, progress: ProgressCallback | None
) -> None:
    """Download and unzip a Vosk model archive from alphacephei.com into ``model_dir``.

    GATE-9 / network-egress (reviewed): the only outbound call. It runs only on an
    explicit user "download model" action, over a verified TLS context and an
    HTTPS-only URL, is blocked in Safe Mode by the caller, MD5-verifies the
    archive against the catalog's pinned hash, and guards against zip-slip.
    """
    url = info.download_url or ""
    if not url.lower().startswith("https://"):
        raise SpeechError("Model downloads must use a secure (HTTPS) address.")
    digest = hashlib.md5(usedforsecurity=False)  # integrity check vs. publisher MD5, not security
    fd, raw_temp = tempfile.mkstemp(prefix=".vosk-", suffix=".zip", dir=str(model_dir.parent))
    temp_path = Path(raw_temp)
    request = urllib.request.Request(url, headers={"User-Agent": "QUILL"})
    if progress is not None:
        progress(0.02, f"Downloading {info.display_name}...")
    try:
        with (
            urllib.request.urlopen(  # noqa: S310 - HTTPS enforced above, verified TLS
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
                    progress(
                        min(0.02 + 0.7 * (read / total), 0.72),
                        f"Downloading {info.display_name}...",
                    )
        if info.md5 and digest.hexdigest().lower() != info.md5.lower():
            raise SpeechError("The downloaded model failed its integrity check. Try again.")
        if progress is not None:
            progress(0.8, f"Extracting {info.display_name}...")
        with zipfile.ZipFile(temp_path) as zf:
            _safe_extract(zf, model_dir)
    except SpeechError:
        shutil.rmtree(model_dir, ignore_errors=True)
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean message, clean up partial state
        shutil.rmtree(model_dir, ignore_errors=True)
        raise SpeechError(f"The model download failed: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
