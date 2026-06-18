"""Cloud audio transcription via OpenAI Whisper-1.

Uses multipart/form-data upload (urlopen tracked by GATE-9 egress audit).
"""

from __future__ import annotations

import json
import mimetypes
import ssl
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TRANSCRIPTION_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
TRANSLATION_ENDPOINT = "https://api.openai.com/v1/audio/translations"
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

SUPPORTED_AUDIO_EXTENSIONS = frozenset({
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".webm",
    ".ogg",
    ".flac",
    ".mpeg",
    ".mpga",
})

SUPPORTED_LANGUAGES: dict[str, str] = {
    "Auto-detect": "",
    "Afrikaans": "af",
    "Arabic": "ar",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Chinese": "zh",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Russian": "ru",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Vietnamese": "vi",
}


class TranscriptionError(Exception):
    pass


class TranscriptionFileTooLargeError(TranscriptionError):
    pass


class TranscriptionFormatError(TranscriptionError):
    pass


class TranscriptionAuthError(TranscriptionError):
    pass


def transcribe_file(
    path: Path,
    api_key: str,
    language: str | None = None,
    response_format: str = "text",
    model: str = "whisper-1",
) -> str:
    """Upload audio file and return transcript text.

    *language*: ISO-639-1 code or None for auto-detect.
    *response_format*: "text" | "verbose_json" | "srt" | "vtt".

    Raises TranscriptionFileTooLargeError if file > 25 MB.
    Raises TranscriptionFormatError if extension is not supported.
    Raises TranscriptionAuthError on 401.
    """
    path = Path(path)
    _validate_file(path)

    fields: dict[str, str] = {
        "model": model,
        "response_format": response_format,
        "temperature": "0",
    }
    if language:
        fields["language"] = language

    return _post_audio(TRANSCRIPTION_ENDPOINT, path, api_key, fields)


def translate_file(
    path: Path,
    api_key: str,
    response_format: str = "text",
    model: str = "whisper-1",
) -> str:
    """Upload audio in any language; returns English transcript.

    Raises TranscriptionFileTooLargeError if file > 25 MB.
    """
    path = Path(path)
    _validate_file(path)

    fields: dict[str, str] = {
        "model": model,
        "response_format": response_format,
        "temperature": "0",
    }
    return _post_audio(TRANSLATION_ENDPOINT, path, api_key, fields)


def _validate_file(path: Path) -> None:
    if not path.exists():
        raise TranscriptionError(f"File not found: {path}")
    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
        size_mb = path.stat().st_size / (1024 * 1024)
        raise TranscriptionFileTooLargeError(
            f"File is {size_mb:.1f} MB, exceeding the 25 MB cloud limit. "
            "Split the file and transcribe each part, or use local transcription."
        )
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise TranscriptionFormatError(
            f"Unsupported audio format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
        )


def _post_audio(
    endpoint: str,
    path: Path,
    api_key: str,
    fields: dict[str, str],
) -> str:
    """Build a multipart/form-data request and POST to *endpoint*."""
    boundary = uuid.uuid4().hex
    mime_type = mimetypes.guess_type(str(path))[0] or "audio/mpeg"

    body_parts: list[bytes] = []
    for name, value in fields.items():
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )

    audio_bytes = path.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n".encode()
        + audio_bytes
        + b"\r\n"
    )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    req = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, context=ctx, timeout=300) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code == 401:
            raise TranscriptionAuthError("Authentication failed (401).") from exc
        body_text = ""
        try:
            body_text = exc.read().decode(errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise TranscriptionError(f"HTTP {exc.code}: {body_text[:200]}") from exc

    # response_format="text" returns plain text; others return JSON
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            return str(data.get("text", raw))
        except json.JSONDecodeError:
            pass
    return str(raw)
