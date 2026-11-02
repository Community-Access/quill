"""Getting a picture ready to ask about, done right (codex.md 10B.2).

Every media app that asks a model about a picture or a video goes through
here, so the seven rules are kept once:

1. **Local frames first.** FFmpeg takes only what is needed: the times the
   person names, an evenly spaced contact sheet (the layout of
   :mod:`quill.core.video_review`), or scene changes (``select='gt(scene,0.3)'``,
   capped).
2. **Local text first.** When the question is about words on screen, OCR on
   this computer answers it and nothing is sent; the person is told which
   happened ("Read on this computer" or "Described by My ChatGPT plan").
3. **Fit the connection.** Downscaled to the longest side the connection takes
   and re-encoded as JPEG or PNG, never raw bytes.
4. **A strict cap.** One contact sheet of at most 16 frames, or at most 4 single
   frames, per request -- never a way around a service's limits.
5. **Timestamps carried through.** Every frame keeps its time.
6. **Say what was inspected.** "Looked at 12 frames from 00:00 to 05:30, and
   the captions beside them."
7. **Cache.** The prepared picture and the answer, by content hash and
   question, for the session: asking again sends nothing.

No video file and no sound ever leaves through this module (10B.3). wx-free,
strict-typed, and network-free: it prepares; the connection layer sends.
Subprocesses go through :func:`quill.stability.safe_subprocess.run_subprocess_safely`.
"""

from __future__ import annotations

import hashlib
import io
import re
import subprocess
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.ai.connection_caps import (
    CHATGPT,
    CODEX,
    CONNECTION_NAMES,
    COPILOT,
    FREE,
    OWN_KEY,
    PICTURES,
    ConnectionRecord,
    require,
)
from quill.core.error_codes import CodedError
from quill.core.video_review import FRAME_CHOICES, Section, frame_times, frame_width, grid

__all__ = [
    "LOCAL_SENTENCE",
    "MAX_SHEET_FRAMES",
    "MAX_SINGLE_FRAMES",
    "SCENE_THRESHOLD",
    "Frame",
    "LocalReading",
    "PictureCache",
    "PicturePrepError",
    "PreparedImage",
    "PreparedRequest",
    "build_sheet",
    "clock_time",
    "content_hash",
    "described_by_sentence",
    "extract_frames",
    "find_ffmpeg",
    "fit_image",
    "frame_command",
    "inspected_sentence",
    "longest_side_for",
    "named_times",
    "parse_scene_times",
    "prepare_request",
    "question_is_about_words",
    "read_locally",
    "scene_change_frames",
    "scene_command",
    "sheet_frames",
]

#: The most frames one contact sheet carries: the existing video_review ceiling.
MAX_SHEET_FRAMES = max(FRAME_CHOICES)
#: The most single frames one request carries.
MAX_SINGLE_FRAMES = 4
#: How different a frame must be from the last to count as a scene change.
SCENE_THRESHOLD = 0.3
#: What is said when OCR answered and nothing was sent.
LOCAL_SENTENCE = "Read on this computer."
#: OCR text shorter than this is not enough to answer a question about words.
_MIN_LOCAL_CHARS = 3

Runner = Callable[..., "subprocess.CompletedProcess[str]"]
OcrFn = Callable[[Path], str]


class PicturePrepError(CodedError):
    """A picture could not be prepared; the message is a sentence for a person."""

    code = "QUILL-AI-PICTURE-PREP-FAILED"


# -- the longest side each connection takes --------------------------------------- #

#: ``connection -> (longest side in pixels, where that was read)``. A picture
#: larger than this is shrunk by the service anyway, and a picture a service
#: shrinks comes back with invented text, so it is shrunk here, once, well.
_LONGEST_SIDE: dict[str, tuple[int, str]] = {
    CHATGPT: (2048, "platform.openai.com/docs/guides/images-vision: high detail fits 2048 square"),
    CODEX: (2048, "same OpenAI vision models as the ChatGPT plan (codex.md 10A.13)"),
    COPILOT: (2048, "conservative OpenAI-sized default for attachments until G6 (codex.md 11)"),
    OWN_KEY: (3072, "ai.google.dev/gemini-api/docs/image-understanding: tiles up to 3072"),
}

#: An own key's provider, where it differs from Gemini's 3072.
_OWN_KEY_SIDE: dict[str, tuple[int, str]] = {
    "openai": (2048, "platform.openai.com/docs/guides/images-vision: high detail fits 2048 square"),
    "claude": (
        1568,
        "docs.anthropic.com/en/docs/build-with-claude/vision: a long edge over 1568 is scaled down",
    ),
}


def longest_side_for(connection: str, own_key_provider: str = "") -> int:
    """The longest side, in pixels, a picture is fitted to for *connection*.

    Zero for a connection that cannot see at all (QUILL's free AI). On My own
    key, *own_key_provider* picks the provider's own size where it has one.
    """
    if connection == FREE:
        return 0
    if connection == OWN_KEY and own_key_provider in _OWN_KEY_SIDE:
        return _OWN_KEY_SIDE[own_key_provider][0]
    return _LONGEST_SIDE.get(connection, (2048, ""))[0]


# -- times ---------------------------------------------------------------------- #


def clock_time(seconds: float) -> str:
    """``"05:30"``, or ``"1:02:03"`` past an hour: the form answers cite."""
    total = max(0, int(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def named_times(times: Sequence[float], duration: float = 0.0) -> list[float]:
    """The times a person named, in order, without repeats, inside the video.

    Raises :class:`PicturePrepError` past :data:`MAX_SINGLE_FRAMES`: the cap
    is said, not quietly applied, so nobody believes more was looked at.
    """
    chosen: list[float] = []
    for value in times:
        moment = max(0.0, float(value))
        if duration > 0:
            moment = min(moment, max(0.0, duration - 0.05))
        moment = round(moment, 2)
        if moment not in chosen:
            chosen.append(moment)
    if len(chosen) > MAX_SINGLE_FRAMES:
        raise PicturePrepError(
            f"At most {MAX_SINGLE_FRAMES} single frames go with one question. "
            "Ask about fewer times, or ask about the stretch as a contact sheet."
        )
    return sorted(chosen)


def sheet_frames(part: Section, count: int = MAX_SHEET_FRAMES) -> list[float]:
    """Evenly spaced times for a contact sheet of at most 16 frames."""
    return frame_times(part, max(1, min(int(count), MAX_SHEET_FRAMES)))


# -- FFmpeg --------------------------------------------------------------------- #


def find_ffmpeg() -> str | None:
    """The bundled (or installed) FFmpeg every QUILL app already uses, or None."""
    from quill.core.speech.ffmpeg import find_ffmpeg as _find

    return _find()


def frame_command(ffmpeg: str, video: Path, moment: float, target: Path, width: int) -> list[str]:
    """One frame at *moment*, scaled to *width*, written to *target*."""
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{moment:.2f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-2",
        "-update",
        "1",
        str(target),
    ]


def scene_command(
    ffmpeg: str,
    video: Path,
    pattern: Path,
    *,
    threshold: float = SCENE_THRESHOLD,
    cap: int = MAX_SHEET_FRAMES,
    width: int = 640,
) -> list[str]:
    """Frames where the picture changes by more than *threshold*, at most *cap*.

    ``showinfo`` prints each kept frame's ``pts_time`` on stderr, which is how
    every frame keeps its time (:func:`parse_scene_times`).
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"select='gt(scene,{threshold:g})',scale={width}:-2,showinfo",
        "-fps_mode",
        "vfr",
        "-frames:v",
        str(max(1, min(int(cap), MAX_SHEET_FRAMES))),
        str(pattern),
    ]


_PTS_TIME = re.compile(r"\bpts_time:\s*([0-9]+(?:\.[0-9]+)?)")


def parse_scene_times(stderr: str) -> list[float]:
    """The ``pts_time`` of every frame ``showinfo`` reported, in order."""
    return [round(float(m.group(1)), 2) for m in _PTS_TIME.finditer(stderr or "")]


@dataclass(frozen=True, slots=True)
class Frame:
    """One still taken from a video, and the time it shows."""

    time: float
    path: Path


def _run(runner: Runner | None, command: list[str], timeout: float) -> Any:
    if runner is None:
        from quill.stability.safe_subprocess import run_subprocess_safely

        runner = run_subprocess_safely
    try:
        return runner(command, timeout_seconds=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PicturePrepError(f"FFmpeg could not take the frames: {error}") from error


def extract_frames(
    ffmpeg: str,
    video: Path,
    times: Sequence[float],
    scratch: Path,
    *,
    width: int = 960,
    runner: Runner | None = None,
) -> list[Frame]:
    """One PNG per time in *scratch*; a time FFmpeg could not reach is left out."""
    frames: list[Frame] = []
    for index, moment in enumerate(times):
        target = scratch / f"frame-{index:02d}.png"
        _run(runner, frame_command(ffmpeg, video, moment, target, width), 60)
        if target.is_file():
            frames.append(Frame(float(moment), target))
    if not frames:
        raise PicturePrepError("No frames could be taken from the video.")
    return frames


def scene_change_frames(
    ffmpeg: str,
    video: Path,
    scratch: Path,
    *,
    threshold: float = SCENE_THRESHOLD,
    cap: int = MAX_SHEET_FRAMES,
    runner: Runner | None = None,
) -> list[Frame]:
    """The scene-change frames, capped at *cap* (never more than 16), with times."""
    cap = max(1, min(int(cap), MAX_SHEET_FRAMES))
    pattern = scratch / "scene-%03d.png"
    done = _run(runner, scene_command(ffmpeg, video, pattern, threshold=threshold, cap=cap), 300)
    times = parse_scene_times(str(getattr(done, "stderr", "") or ""))
    files = sorted(scratch.glob("scene-*.png"))[:cap]
    return [Frame(times[i] if i < len(times) else 0.0, path) for i, path in enumerate(files)]


# -- the sheet ------------------------------------------------------------------ #


def build_sheet(frames: Sequence[Frame], *, label_size: int = 26) -> bytes:
    """A labelled contact sheet (PNG bytes) of at most 16 frames, read left to right."""
    from PIL import Image, ImageDraw, ImageFont

    if not frames:
        raise PicturePrepError("There are no frames to lay out.")
    if len(frames) > MAX_SHEET_FRAMES:
        raise PicturePrepError(f"A contact sheet holds at most {MAX_SHEET_FRAMES} frames.")
    width = frame_width(len(frames))
    images: list[tuple[float, Any]] = []
    for frame in frames:
        with Image.open(frame.path) as opened:
            picture = opened.convert("RGB")
        if picture.width != width:
            height = max(1, round(picture.height * width / picture.width))
            picture = picture.resize((width, height))
        images.append((frame.time, picture))
    columns, rows = grid(len(images))
    height = max(picture.height for _t, picture in images)
    try:
        font: Any = ImageFont.load_default(size=label_size)
    except TypeError:  # pragma: no cover - Pillow before 10.1
        font = ImageFont.load_default()
    label = label_size + 12
    sheet = Image.new("RGB", (columns * width, rows * (height + label)), "black")
    draw = ImageDraw.Draw(sheet)
    for index, (moment, picture) in enumerate(images):
        left, top = (index % columns) * width, (index // columns) * (height + label)
        draw.text((left + 8, top + 5), clock_time(moment), fill="white", font=font)
        sheet.paste(picture, (left, top + label))
    out = io.BytesIO()
    sheet.save(out, format="PNG")
    return out.getvalue()


# -- fitting the connection ------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PreparedImage:
    """A picture fitted to one connection: the bytes that would be sent."""

    data: bytes
    mime: str
    width: int
    height: int
    times: tuple[float, ...] = ()

    @property
    def digest(self) -> str:
        return content_hash(self.data)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fit_image(data: bytes, longest_side: int, *, keep_png: bool | None = None) -> PreparedImage:
    """*data* shrunk so its longest side is at most *longest_side*, re-encoded.

    PNG when the picture has transparency or was a PNG (screens of text stay
    sharp); JPEG otherwise. *keep_png* forces the choice.
    """
    from PIL import Image, UnidentifiedImageError

    if longest_side <= 0:
        raise PicturePrepError("This connection cannot see pictures. Nothing was sent.")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            fmt = (opened.format or "").upper()
            picture: Any = opened.copy()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise PicturePrepError("That is not a picture QUILL can read.") from error
    biggest = max(picture.width, picture.height)
    if biggest > longest_side:
        scale = longest_side / biggest
        size = (max(1, round(picture.width * scale)), max(1, round(picture.height * scale)))
        picture = picture.resize(size, Image.Resampling.LANCZOS)
    has_alpha = "A" in picture.getbands()
    as_png = keep_png if keep_png is not None else (has_alpha or fmt == "PNG")
    out = io.BytesIO()
    if as_png:
        if picture.mode not in ("RGB", "RGBA", "L", "LA"):
            picture = picture.convert("RGBA" if has_alpha else "RGB")
        picture.save(out, format="PNG", optimize=True)
        mime = "image/png"
    else:
        if picture.mode not in ("RGB", "L"):
            picture = picture.convert("RGB")
        picture.save(out, format="JPEG", quality=85)
        mime = "image/jpeg"
    return PreparedImage(out.getvalue(), mime, picture.width, picture.height)


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    """What one request about a picture carries, and the sentence that says so."""

    images: tuple[PreparedImage, ...]
    times: tuple[float, ...]
    inspected: str


def prepare_request(
    pictures: Sequence[bytes],
    record: ConnectionRecord,
    *,
    times: Sequence[float] = (),
    sheet_frame_count: int = 0,
    captions: bool = False,
    own_key_provider: str = "",
) -> PreparedRequest:
    """Fit *pictures* to *record*, enforcing the cap, and say what was inspected.

    Either one contact sheet (``sheet_frame_count`` frames, at most 16) or at
    most four single pictures. Raises :class:`CapabilityMissing` when the
    connection cannot see, before anything is prepared. *own_key_provider*
    sizes the picture for that provider on My own key.
    """
    require(record, PICTURES)
    if not pictures:
        raise PicturePrepError("There is no picture to ask about.")
    if sheet_frame_count:
        if len(pictures) != 1:
            raise PicturePrepError("A contact sheet goes as one picture.")
        if sheet_frame_count > MAX_SHEET_FRAMES:
            raise PicturePrepError(f"A contact sheet holds at most {MAX_SHEET_FRAMES} frames.")
    elif len(pictures) > MAX_SINGLE_FRAMES:
        raise PicturePrepError(f"At most {MAX_SINGLE_FRAMES} pictures go with one question.")
    side = longest_side_for(record.connection, own_key_provider)
    fitted = tuple(fit_image(data, side) for data in pictures)
    count = sheet_frame_count or len(pictures)
    return PreparedRequest(
        fitted, tuple(times), inspected_sentence(count, times, captions=captions)
    )


def inspected_sentence(count: int, times: Sequence[float] = (), *, captions: bool = False) -> str:
    """The sentence every answer about a picture starts with (rule 6)."""
    noun = "frame" if times else "picture"
    things = f"{count} {noun}{'' if count == 1 else 's'}"
    if times and len(times) > 1:
        span = f" from {clock_time(min(times))} to {clock_time(max(times))}"
    elif times:
        span = f" at {clock_time(times[0])}"
    else:
        span = ""
    tail = ", and the captions beside them" if captions else ""
    return f"Looked at {things}{span}{tail}."


# -- local text first ------------------------------------------------------------ #

_WORDS_QUESTION = re.compile(
    r"\b(say|says|said|read|text|words?|written|writing|title|caption|label|"
    r"spell|spelled|quote|number|heading|button|menu)\b",
    re.IGNORECASE,
)


def question_is_about_words(question: str) -> bool:
    """True when OCR alone may answer *question* ("what does it say?")."""
    return bool(_WORDS_QUESTION.search(question or ""))


@dataclass(frozen=True, slots=True)
class LocalReading:
    """What OCR on this computer found, and whether that answers the question."""

    text: str
    answered: bool
    sentence: str = field(default=LOCAL_SENTENCE)


def _default_ocr(path: Path) -> str:
    try:
        from quill.io.ocr import ocr_image

        return ocr_image(path).text
    except Exception:  # noqa: BLE001 - fall through to Tesseract
        pass
    try:
        from quill.io.tesseract_ocr import ocr_image_with_tesseract

        return ocr_image_with_tesseract(path).text
    except Exception:  # noqa: BLE001 - no OCR here means the model is needed
        return ""


def read_locally(data: bytes, question: str, *, ocr: OcrFn | None = None) -> LocalReading:
    """Try OCR on *data* first; ``answered`` when the question is about words and
    OCR found some, in which case nothing needs to be sent."""
    reader = ocr or _default_ocr
    with tempfile.TemporaryDirectory(prefix="quill-picture-ocr-") as scratch:
        target = Path(scratch) / "picture.png"
        target.write_bytes(data)
        text = (reader(target) or "").strip()
    answered = question_is_about_words(question) and len(text) >= _MIN_LOCAL_CHARS
    return LocalReading(text=text, answered=answered)


def described_by_sentence(connection: str) -> str:
    """ "Described by My ChatGPT plan." -- said when the model, not OCR, answered."""
    return f"Described by {CONNECTION_NAMES.get(connection, connection)}."


# -- the session cache ---------------------------------------------------------- #


class PictureCache:
    """The prepared picture and the answer, by content hash and question.

    For one session only and in memory only: nothing about a picture is
    written to disk. Asking the same question of the same picture again
    costs nothing and sends nothing.
    """

    def __init__(self, limit: int = 64) -> None:
        self._limit = max(1, limit)
        self._items: OrderedDict[tuple[str, str, str], tuple[PreparedRequest | None, str]] = (
            OrderedDict()
        )
        self._lock = threading.Lock()

    @staticmethod
    def _key(digest: str, question: str, connection: str) -> tuple[str, str, str]:
        return digest, " ".join(question.lower().split()), connection

    def get(self, digest: str, question: str, connection: str = "") -> str | None:
        """The answer kept for this picture and question, or None."""
        key = self._key(digest, question, connection)
        with self._lock:
            hit = self._items.get(key)
            if hit is None:
                return None
            self._items.move_to_end(key)
            return hit[1]

    def put(
        self,
        digest: str,
        question: str,
        answer: str,
        *,
        connection: str = "",
        prepared: PreparedRequest | None = None,
    ) -> None:
        key = self._key(digest, question, connection)
        with self._lock:
            self._items[key] = (prepared, answer)
            self._items.move_to_end(key)
            while len(self._items) > self._limit:
                self._items.popitem(last=False)

    def prepared(self, digest: str, question: str, connection: str = "") -> PreparedRequest | None:
        with self._lock:
            hit = self._items.get(self._key(digest, question, connection))
            return hit[0] if hit else None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
