"""Talking to OpenAI's transcription: one phrase at a time, or live.

Two paths, chosen by the model (:func:`~quill.core.windows_dictation.openai_models.is_live_model`),
as OpenAI's speech-to-text guide describes them (read 2026-10-05):

* **Live (Realtime transcription).** One WebSocket for the dictation session.
  While you speak, the phrase's audio is appended as it arrives and OpenAI
  answers with provisional words (the live preview); at the pause the phrase is
  committed and OpenAI answers with the final text. QUILL's own voice
  detection decides where a phrase ends, so turn detection is off, which is
  what ``gpt-live-transcribe`` asks for. :class:`LiveTranscription`.
* **A phrase at a time** (``/v1/audio/transcriptions`` with ``stream=true``):
  each finished phrase is sent as a short WAV and the text streams back.
  :func:`transcribe_phrase`.

Both send your words from My Words and Phrases as ``keywords`` (the closest
thing to teaching a model your names), and the dictation language.

**The key** travels only in the ``Authorization`` header to ``api.openai.com``
over verified TLS. It is never logged, never put in an error sentence, and
never written anywhere by this module.

**What comes back when it fails** is a :class:`OpenAIDictationError` with a
sentence for a person; :class:`ModelGoneError` when the chosen model is no
longer there, which the controller says once and stops on -- never a silent
switch to another model.

wx-free. ``websockets`` (already in the shared runtime) is imported lazily, only for
the live path.
"""

from __future__ import annotations

import base64
import io
import json
import threading
import wave
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.windows_dictation.openai_models import API_ROOT

__all__ = [
    "LIVE_URL",
    "LiveTranscription",
    "ModelGoneError",
    "OpenAIDictationError",
    "keywords_for",
    "pcm16",
    "transcribe_phrase",
    "wav_bytes",
]

#: The Realtime endpoint for a transcription-only session.
LIVE_URL = "wss://api.openai.com/v1/realtime?intent=transcription"
_LIVE_RATE = 24_000
_RATE = 16_000
#: OpenAI asks for one term per keyword, no angle brackets or line breaks.
_MAX_KEYWORDS = 100


class OpenAIDictationError(CodedError):
    """OpenAI did not turn a phrase into text."""

    code = "QUILL-DICTATION-OPENAI-FAILED"
    user_hint = (
        "Check the internet connection and the key in Use My Own AI Key, or choose "
        "a built-in engine in Dictation Settings."
    )


class ModelGoneError(OpenAIDictationError):
    """The chosen OpenAI model is no longer there."""

    code = "QUILL-DICTATION-OPENAI-MODEL-GONE"
    user_hint = "Choose another OpenAI model in More Dictation Settings."


def _sentence(status: int, body: str, model: str) -> OpenAIDictationError:
    text = body.lower()
    if status == 404 or "model_not_found" in text or "does not exist" in text:
        return ModelGoneError(
            f"The OpenAI model {model} is no longer available to your key. Choose "
            "another in More Dictation Settings."
        )
    if status == 401:
        return OpenAIDictationError(
            "OpenAI did not accept the saved key. Check it in Use My Own AI Key."
        )
    if status == 429:
        return OpenAIDictationError(
            "OpenAI says the account is out of credit or sending too fast. Check "
            "your OpenAI account, or choose a built-in engine."
        )
    return OpenAIDictationError(f"OpenAI could not transcribe that (error {status}).")


def keywords_for(words: Sequence[str]) -> list[str]:
    """Your words, as OpenAI's ``keywords``: one line each, nothing it refuses."""
    out: list[str] = []
    for word in words:
        cleaned = " ".join(str(word).replace("<", " ").replace(">", " ").split())
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out[:_MAX_KEYWORDS]


def pcm16(samples: Any, rate: int = _RATE) -> bytes:
    """Float samples (-1..1, 16 kHz) as little-endian 16-bit PCM at *rate*."""
    import numpy as np

    data = np.asarray(samples, dtype=np.float32)
    if rate != _RATE and data.size:
        positions = np.linspace(0, data.size - 1, int(data.size * rate / _RATE))
        data = np.interp(positions, np.arange(data.size), data).astype(np.float32)
    pcm: bytes = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return pcm


def wav_bytes(samples: Any) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(_RATE)
        out.writeframes(pcm16(samples))
    return buffer.getvalue()


def _multipart(fields: list[tuple[str, str]], audio: bytes) -> tuple[bytes, str]:
    boundary = "quill-dictation-" + base64.urlsafe_b64encode(audio[:12] + b"bnd").decode()
    lines: list[bytes] = []
    for name, value in fields:
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            value.encode("utf-8"),
        ]
    lines += [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="phrase.wav"',
        b"Content-Type: audio/wav",
        b"",
        audio,
        f"--{boundary}--".encode(),
        b"",
    ]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


def transcribe_phrase(
    key: str,
    model: str,
    samples: Any,
    *,
    language: str = "en",
    keywords: Sequence[str] = (),
    on_delta: Callable[[str], None] | None = None,
    timeout: float = 30.0,
    prompt: str = "",
) -> str:
    """One phrase through ``/v1/audio/transcriptions``, streamed. Blocking.

    *on_delta* hears the text so far as it streams in (the preview). *prompt*
    is this document's dictation context (contexts.py), sent when there is one.
    """
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    from quill.core.net import verified_ssl_context

    fields = [("model", model), ("stream", "true")]
    if language:
        fields.append(("language", language))
    for word in keywords_for(keywords):
        fields.append(("keywords[]", word))
    if prompt.strip():
        fields.append(("prompt", prompt.strip()))
    body, content_type = _multipart(fields, wav_bytes(samples))
    request = Request(
        f"{API_ROOT}/audio/transcriptions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout, context=verified_ssl_context()) as response:
            return _read_stream(response, on_delta)
    except HTTPError as error:
        try:
            detail = error.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - the status is enough
            detail = ""
        raise _sentence(error.code, detail, model) from None
    except (URLError, OSError, TimeoutError):
        raise OpenAIDictationError(
            "OpenAI could not be reached. Check the internet connection."
        ) from None


def _read_stream(response: Any, on_delta: Callable[[str], None] | None) -> str:
    """Server-sent events (``transcript.text.delta`` / ``.done``), or plain JSON."""
    text = ""
    final = ""
    raw = b""
    for line in response:
        raw += line
        line = line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
        except ValueError:
            continue
        kind = str(event.get("type", ""))
        if kind.endswith(".delta"):
            text += str(event.get("delta", ""))
            if on_delta is not None:
                on_delta(text)
        elif kind.endswith(".done"):
            final = str(event.get("text", text))
    if final or text:
        return (final or text).strip()
    try:  # a server that answered without streaming
        return str(json.loads(raw.decode("utf-8", errors="replace")).get("text", "")).strip()
    except ValueError:
        return raw.decode("utf-8", errors="replace").strip()


def create_connection(url: str, key: str) -> Any:
    """The one WebSocket QUILL opens: ``websockets``' synchronous client, which
    the shared runtime already carries. Certificate-checked; the key only in
    the ``Authorization`` header."""
    from quill.core.net import verified_ssl_context

    try:
        from websockets.sync.client import (  # type: ignore[import-not-found,unused-ignore]
            connect,
        )
    except ImportError as error:
        raise OpenAIDictationError(
            "Live OpenAI dictation needs a part that is missing from this copy "
            "of QUILL. Choose gpt-transcribe in More Dictation Settings."
        ) from error
    return connect(
        url,
        additional_headers={"Authorization": f"Bearer {key}"},
        ssl=verified_ssl_context(),
        open_timeout=15,
        max_size=None,
    )


class LiveTranscription:
    """One Realtime transcription session for the length of a dictation session.

    :meth:`append` sends audio as it is heard, :meth:`commit` ends the phrase
    and waits for its final text. Provisional words arrive on *on_delta* (from
    the receiving thread; the recogniser hands them on through its poster).
    """

    def __init__(
        self,
        key: str,
        model: str,
        *,
        language: str = "en",
        keywords: Sequence[str] = (),
        on_delta: Callable[[str], None] | None = None,
        connect: Callable[..., Any] | None = None,
        prompt: str = "",
    ) -> None:
        self._key = key
        self._prompt = prompt.strip()
        self._model = model
        self._language = language
        self._keywords = keywords_for(keywords)
        self._on_delta = on_delta
        self._connect = connect
        self._socket: Any = None
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._final = ""
        self._partial = ""
        self._error: OpenAIDictationError | None = None
        self._reader: threading.Thread | None = None

    def open(self) -> None:
        """Connect and configure. Raises :class:`OpenAIDictationError`."""
        try:
            if self._connect is not None:  # a test's stand-in
                self._socket = self._connect(LIVE_URL, self._key)
            else:
                self._socket = create_connection(LIVE_URL, self._key)
        except OpenAIDictationError:
            raise
        except Exception as error:  # noqa: BLE001 - one sentence, never the key
            response = getattr(error, "response", None)
            status = int(getattr(response, "status_code", 0) or 0)
            if status:
                body = bytes(getattr(response, "body", b"") or b"").decode("utf-8", "replace")
                raise _sentence(status, body, self._model) from None
            raise OpenAIDictationError(
                "OpenAI could not be reached. Check the internet connection."
            ) from None
        transcription: dict[str, Any] = {"model": self._model}
        if self._language:
            transcription["language"] = self._language
        if self._keywords:
            transcription["keywords"] = self._keywords
        if self._prompt:
            transcription["prompt"] = self._prompt
        self._send({
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": _LIVE_RATE},
                        "transcription": transcription,
                        "turn_detection": None,
                    }
                },
            },
        })
        self._reader = threading.Thread(
            target=self._read, name="dictation-openai-live", daemon=True
        )
        self._reader.start()

    def append(self, samples: Any) -> None:
        audio = base64.b64encode(pcm16(samples, _LIVE_RATE)).decode("ascii")
        self._send({"type": "input_audio_buffer.append", "audio": audio})

    def commit(self, timeout: float = 15.0) -> str:
        """End the phrase; its final text, or raise with a sentence."""
        with self._lock:
            self._done.clear()
            self._final = ""
        self._send({"type": "input_audio_buffer.commit"})
        if not self._done.wait(timeout):
            raise OpenAIDictationError("OpenAI took too long to answer.")
        if self._error is not None:
            error, self._error = self._error, None
            raise error
        return self._final.strip()

    def clear(self) -> None:
        """Throw away audio appended since the last commit (Escape)."""
        self._send({"type": "input_audio_buffer.clear"})
        self._partial = ""

    def close(self) -> None:
        socket, self._socket = self._socket, None
        if socket is not None:
            try:
                socket.close()
            except Exception:  # noqa: BLE001 - it is going either way
                pass
        self._done.set()

    # -- the wire ---------------------------------------------------------- #

    def _send(self, event: dict[str, Any]) -> None:
        socket = self._socket
        if socket is None:
            raise OpenAIDictationError("The connection to OpenAI has closed.")
        try:
            socket.send(json.dumps(event))
        except Exception:  # noqa: BLE001
            raise OpenAIDictationError("The connection to OpenAI was lost.") from None

    def _read(self) -> None:
        while self._socket is not None:
            try:
                message = self._socket.recv()
            except Exception:  # noqa: BLE001 - closed, or the network went
                if self._socket is not None:
                    self._error = OpenAIDictationError("The connection to OpenAI was lost.")
                self._done.set()
                return
            if not message:
                continue
            try:
                event = json.loads(message)
            except ValueError:
                continue
            self._handle(event)

    def _handle(self, event: dict[str, Any]) -> None:
        kind = str(event.get("type", ""))
        if kind.endswith("input_audio_transcription.delta"):
            self._partial += str(event.get("delta", ""))
            if self._on_delta is not None:
                self._on_delta(self._partial)
        elif kind.endswith("input_audio_transcription.completed"):
            self._final = str(event.get("transcript", ""))
            self._partial = ""  # the next phrase's preview starts afresh
            self._done.set()
        elif kind == "error" or kind.endswith("input_audio_transcription.failed"):
            detail = event.get("error") or {}
            body = json.dumps(detail) if isinstance(detail, dict) else str(detail)
            code = 404 if "model" in body.lower() and "not" in body.lower() else 400
            if "input_audio_buffer_commit_empty" in body:
                self._final = ""
            else:
                self._error = _sentence(code, body, self._model)
            self._done.set()
