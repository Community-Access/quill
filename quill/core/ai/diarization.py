"""Speaker diarization for QUILL.

Phase 1: Deepgram Nova-3 (single API call, utterances array, 2 GB file limit).
Phase 2: pyannote.audio (local, optional Quillin extension).
"""

from __future__ import annotations

import json
import mimetypes
import ssl
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError

DEEPGRAM_ENDPOINT = "https://api.deepgram.com/v1/listen"
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB (Deepgram limit)


class DiarizationError(CodedError):
    code = "QUILL-AI-DIARIZATION-FAILED"


class DiarizationAuthError(DiarizationError):
    pass


class DiarizationFileTooLargeError(DiarizationError):
    pass


@dataclass(frozen=True)
class SpeakerTurn:
    speaker_id: str  # "SPEAKER_0", "SPEAKER_1", etc.
    speaker_label: str  # "Speaker 1", "Speaker 2", etc.
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class DiarizationResult:
    turns: list[SpeakerTurn] = field(default_factory=list)
    speaker_count: int = 0
    duration_seconds: float = 0.0
    provider: str = "deepgram"


def diarize_file(
    path: Path,
    provider: str,
    api_key: str,
    max_speakers: int = 6,
    language: str | None = None,
) -> DiarizationResult:
    """Dispatch to the appropriate provider and return structured speaker turns."""
    path = Path(path)
    if not path.exists():
        raise DiarizationError(f"File not found: {path}")

    if provider == "deepgram":
        return _diarize_deepgram(path, api_key, max_speakers, language)
    if provider == "pyannote":
        return _diarize_pyannote(path, max_speakers)
    raise DiarizationError(f"Unknown diarization provider: {provider}")


def format_diarization(
    result: DiarizationResult,
    speaker_names: dict[str, str] | None = None,
    include_timestamps: bool = True,
    timestamp_format: str = "[{hh:02d}:{mm:02d}:{ss:02d}]",
) -> str:
    """Render *result* as a formatted transcript string."""
    lines: list[str] = []
    names = speaker_names or {}

    for turn in result.turns:
        label = names.get(turn.speaker_id, turn.speaker_label)
        if include_timestamps:
            total = int(turn.start_seconds)
            hh, rem = divmod(total, 3600)
            mm, ss = divmod(rem, 60)
            ts = timestamp_format.format(hh=hh, mm=mm, ss=ss)
            lines.append(f"{label} {ts}: {turn.text}")
        else:
            lines.append(f"{label}: {turn.text}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deepgram implementation
# ---------------------------------------------------------------------------


def _diarize_deepgram(
    path: Path,
    api_key: str,
    max_speakers: int,
    language: str | None,
) -> DiarizationResult:
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_gb = file_size / (1024**3)
        raise DiarizationFileTooLargeError(
            f"File is {size_gb:.1f} GB, exceeding the 2 GB Deepgram limit."
        )

    params: list[str] = [
        "model=nova-3",
        "diarize=true",
        "punctuate=true",
        "utterances=true",
        "diarize_version=latest",
    ]
    if language:
        params.append(f"language={language}")
    if max_speakers:
        params.append(f"max_speakers={max_speakers}")
    url = DEEPGRAM_ENDPOINT + "?" + "&".join(params)

    mime_type = mimetypes.guess_type(str(path))[0] or "audio/mpeg"
    audio_bytes = path.read_bytes()
    req = Request(
        url,
        data=audio_bytes,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": mime_type,
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, context=ctx, timeout=600) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        if exc.code == 401:
            raise DiarizationAuthError("Deepgram authentication failed (401).") from exc
        body = ""
        try:
            body = exc.read().decode(errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise DiarizationError(f"Deepgram HTTP {exc.code}: {body[:200]}") from exc

    return _parse_deepgram_response(data)


def _parse_deepgram_response(data: dict) -> DiarizationResult:
    utterances = []
    try:
        utterances = data["results"]["utterances"]
    except (KeyError, TypeError):
        pass

    turns: list[SpeakerTurn] = []
    speaker_ids: set[str] = set()
    duration = 0.0

    for utt in utterances:
        speaker_num = int(utt.get("speaker", 0))
        speaker_id = f"SPEAKER_{speaker_num}"
        speaker_label = f"Speaker {speaker_num + 1}"
        start = float(utt.get("start", 0.0))
        end = float(utt.get("end", 0.0))
        text = str(utt.get("transcript", "")).strip()
        speaker_ids.add(speaker_id)
        duration = max(duration, end)
        turns.append(
            SpeakerTurn(
                speaker_id=speaker_id,
                speaker_label=speaker_label,
                start_seconds=start,
                end_seconds=end,
                text=text,
            )
        )

    return DiarizationResult(
        turns=turns,
        speaker_count=len(speaker_ids),
        duration_seconds=duration,
        provider="deepgram",
    )


# ---------------------------------------------------------------------------
# pyannote.audio local implementation
# ---------------------------------------------------------------------------


def _diarize_pyannote(path: Path, max_speakers: int) -> DiarizationResult:
    """Local speaker diarization via pyannote.audio.

    Requires HuggingFace token stored under QUILL:huggingface:token.
    Downloads ~250 MB of model weights on first use.
    """
    try:
        from pyannote.audio import Pipeline  # type: ignore[import-not-found,import-untyped]
    except ImportError as exc:
        raise DiarizationError(
            "pyannote.audio is not installed. Install it with: pip install pyannote.audio"
        ) from exc

    hf_token = _load_hf_token()
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    diarization = pipeline(str(path), max_speakers=max_speakers)

    turns: list[SpeakerTurn] = []
    speaker_ids: set[str] = set()
    duration = 0.0

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_num = int(speaker.split("_")[1]) if "_" in speaker else 0
        speaker_id = f"SPEAKER_{speaker_num}"
        speaker_label = f"Speaker {speaker_num + 1}"
        speaker_ids.add(speaker_id)
        duration = max(duration, turn.end)
        turns.append(
            SpeakerTurn(
                speaker_id=speaker_id,
                speaker_label=speaker_label,
                start_seconds=turn.start,
                end_seconds=turn.end,
                text="",  # populated by align step when combined with Whisper
            )
        )

    return DiarizationResult(
        turns=turns,
        speaker_count=len(speaker_ids),
        duration_seconds=duration,
        provider="pyannote",
    )


def _load_hf_token() -> str:
    try:
        from quill.platform.windows.credential_store import load_secret

        token = load_secret("QUILL:huggingface:token") or ""
        return token
    except Exception:  # noqa: BLE001
        return ""


def align_transcript_with_speakers(
    whisper_words: list[dict],
    speaker_turns: list[SpeakerTurn],
) -> list[SpeakerTurn]:
    """Assign Whisper word-level timestamps to speaker segments.

    *whisper_words*: list of {"word": str, "start": float, "end": float} from
    Whisper verbose_json with timestamp_granularities=["word"].
    """
    result_turns: list[SpeakerTurn] = []
    for turn in speaker_turns:
        words_in_turn = [
            w["word"]
            for w in whisper_words
            if turn.start_seconds <= (w.get("start", 0) + w.get("end", 0)) / 2 <= turn.end_seconds
        ]
        text = " ".join(words_in_turn).strip()
        result_turns.append(
            SpeakerTurn(
                speaker_id=turn.speaker_id,
                speaker_label=turn.speaker_label,
                start_seconds=turn.start_seconds,
                end_seconds=turn.end_seconds,
                text=text,
            )
        )
    return result_turns
