"""Narrate a Recording: QUILL Studio's second agent task (codex.md 6.8 and 6.3).

The person presses Ctrl+Shift+3 (AI > Narrate a Recording...) and an agent
engine -- My GitHub Copilot or Codex -- writes an accessible narrative of a
recording: what is seen and said, in order, with times. The recording is the
one Studio last made; when there is none, Studio's own file chooser asks for
one the first time a tool needs it.

* ``studio.contact_sheet(start, end, frames)`` -- one picture of up to 16
  frames from a stretch, each labelled with its time (``video_review``'s
  contact sheet, as Ask AI Questions About a Video makes it). Only when the
  connection in use can see; it asks first, naming the file and the stretch,
  and the first picture on a connection also asks where pictures go (10B.4).
* ``studio.transcript_excerpt(start, end)`` -- a read: the captions beside the
  video (an .srt or .vtt file of the same name), with their times.
* ``studio.open_in_quill(text)`` -- the narrative is shown in full first; on
  Apply it is saved as a Markdown file beside the recording (never over an
  existing file) and opened in QUILL, Studio's existing Open in QUILL route.

**Never sent:** sound or video. A connection that cannot see gets a
transcript-only narrative (codex.md 10B.5). Handlers run on a worker thread,
so every touch of Studio goes through ``ctx.on_ui``; nothing announces (GATE-13).
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, ToolImage, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "NARRATE",
    "NARRATIVE_HELP",
    "NARRATIVE_STARTER",
    "last_recording",
    "narrative_file",
    "studio_narrative_facts",
    "studio_narrative_tools",
]

APP = "studio"
#: Frames on one contact sheet at most (``picture_prep.MAX_SHEET_FRAMES``).
_MAX_FRAMES = 16
_VIDEO_SUFFIXES = (".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi")
_VIDEOS = ";".join(f"*{suffix}" for suffix in _VIDEO_SUFFIXES)

NARRATE = AppTaskSpec(
    app=APP,
    agent_id="studio-narrative",
    title="Narrate a Recording",
    instructions=(
        "You write an accessible narrative of a recording for someone who uses a "
        "screen reader: what is seen and what is said, in order, with the time of "
        "each part, in plain sentences. Read what is said with "
        "studio_transcript_excerpt. If you have studio_contact_sheet, look at the "
        "recording in stretches, at most 16 frames a stretch, and describe only "
        "what is visible; never guess what happened between frames, and quote "
        "screen text only where it is clear. Without it, narrate from the words "
        "alone and say so at the top. Then hand the narrative over once with "
        "studio_open_in_quill, as Markdown: a title, a one-paragraph overview, "
        "then a heading for each part with its time."
    ),
    done_words={f"{APP}.open_in_quill": "Opened the narrative in QUILL"},
)

NARRATIVE_STARTER = "Write an accessible narrative of this recording, with times."

NARRATIVE_HELP = (
    "Say what the narrative is for, or press Enter to write one with times. The "
    "recording is the one Studio last made, or one you choose. Pictures of frames "
    "go only if your AI can see and you say yes; sound and video never leave this "
    "computer. The narrative is shown to you in full, then opens in QUILL. While a "
    "task runs, what you type here goes to it as a follow-up."
)


def last_recording(host: Any) -> Path | None:
    """The video Studio last made, if it is still there."""
    verification = getattr(host, "_studio_last_verification", None)
    path = Path(str(getattr(verification, "path", "") or ""))
    if path.name and path.suffix.lower() in _VIDEO_SUFFIXES and path.is_file():
        return path
    return None


def narrative_file(video: Path) -> Path:
    """Where the narrative goes: beside the video, never over an existing file."""
    from quill.core.demo_recording import unique_path

    return unique_path(video.with_name(f"{video.stem} narrative.md"))


def _duration(video: Path) -> float:
    from quill.core.speech.ffmpeg import probe_duration_ms

    return probe_duration_ms(video) / 1000


def studio_narrative_facts(host: Any) -> str:
    """What is on hand, as text, sent with the first instruction."""
    from quill.core.video_review import captions_beside, spoken_time

    video = last_recording(host)
    if video is None:
        return "No recording is chosen yet; the first tool you use asks the person for one."
    lines = [f"Recording: {video.name}."]
    try:
        seconds = _duration(video)
    except Exception:  # noqa: BLE001 - a length is a help, never a blocker
        seconds = 0.0
    if seconds > 0:
        lines.append(f"Length: {spoken_time(seconds)}.")
    captions = captions_beside(video)
    lines.append(f"Captions beside it: {captions.name}." if captions else "No captions beside it.")
    return "\n".join(lines)


def _sheet(ffmpeg: str, video: Path, part: Any, frames: int) -> tuple[bytes, list[float]]:
    """The contact sheet, as Ask AI Questions About a Video makes it."""
    from quill.platform.windows.video_review import contact_sheet

    with tempfile.TemporaryDirectory(prefix="studio-ai-sheet-") as scratch:
        target = Path(scratch) / "frames.png"
        times = contact_sheet(ffmpeg, video, part, frames, target)
        return target.read_bytes(), times


def studio_narrative_tools(
    host: Any,
    ctx: AppTaskHost,
    *,
    duration: Callable[[Path], float] | None = None,
    sheet: Callable[[str, Path, Any, int], tuple[bytes, list[float]]] | None = None,
) -> list[FamilyTool]:
    """Studio's narrative tools for one task. The keywords replace FFmpeg (tests)."""
    from quill.core.ai.connection_caps import CONNECTION_NAMES
    from quill.ui.audio_studio.studio_ai_task import _connection

    length_of = duration or _duration
    make_sheet = sheet or _sheet
    chosen: dict[str, Path] = {}
    connection, can_see = ctx.on_ui(lambda: _connection(host), ("", False)) or ("", False)
    company = CONNECTION_NAMES.get(connection, "your AI")

    def known() -> Path | None:
        if "video" not in chosen:
            found = ctx.on_ui(lambda: last_recording(host), None)
            if found is not None:
                chosen["video"] = found
        return chosen.get("video")

    def video() -> Path:
        found = known()
        if found is not None:
            return found

        def choose() -> str | None:
            return host._choose_media_file(host.frame, "Video", f"Videos ({_VIDEOS})|{_VIDEOS}")

        picked = ctx.on_ui(choose, None)
        if not picked:
            raise ToolError("No recording was chosen, so there is nothing to narrate.")
        chosen["video"] = Path(picked)
        return chosen["video"]

    def stretch(args: dict[str, Any], path: Path) -> Any:
        from quill.core.demo_recording import DemoRecordingError
        from quill.core.video_review import section

        seconds = length_of(path)
        if seconds <= 0:
            raise ToolError(f"The length of {path.name} could not be read.")
        try:
            return section(
                seconds, str(args.get("start", "") or ""), str(args.get("end", "") or "")
            )
        except DemoRecordingError as error:
            raise ToolError(str(error.args[0]) if error.args else str(error)) from error

    def frames_of(args: dict[str, Any]) -> int:
        try:
            count = int(args.get("frames", 9) or 9)
        except (TypeError, ValueError):
            count = 9
        return max(1, min(_MAX_FRAMES, count))

    def span_words(args: dict[str, Any]) -> str:
        start = str(args.get("start", "") or "").strip() or "the start"
        end = str(args.get("end", "") or "").strip() or "the end"
        return f"from {start} to {end}"

    # -- reads ---------------------------------------------------------------

    def transcript_excerpt(args: dict[str, Any]) -> str:
        from quill.core.video_review import captions_beside, transcript_excerpt

        path = video()
        captions = captions_beside(path)
        if captions is None:
            raise ToolError(
                f"There are no captions beside {path.name} (an .srt or .vtt file with the "
                "same name), so nothing that is said can be read."
            )
        part = stretch(args, path)
        try:
            text = captions.read_text(encoding="utf-8")
        except OSError as error:
            raise ToolError(f"{captions.name} could not be read: {error}") from error
        excerpt = transcript_excerpt(text, part)
        if not excerpt:
            return f"Nothing is said {span_words(args)} in {captions.name}."
        return f"What is said {span_words(args)}, from {captions.name}:\n{excerpt}"

    # -- a picture -----------------------------------------------------------

    def contact_sheet(args: dict[str, Any]) -> ToolImage:
        from quill.core.ai.picture_prep import PicturePrepError, fit_image, longest_side_for
        from quill.core.demo_recording import DemoRecordingError
        from quill.core.video_review import spoken_time
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        path = video()
        if not ctx.on_ui(lambda: ask_picture_consent(host, connection), False):
            raise ToolError("The person has not agreed to send pictures on this connection.")
        ffmpeg = ctx.on_ui(lambda: host._demo_ffmpeg(), "")
        if not ffmpeg:
            raise ToolError("Taking frames needs FFmpeg, and Studio cannot find it.")
        part = stretch(args, path)
        try:
            data, times = make_sheet(str(ffmpeg), path, part, frames_of(args))
            prepared = fit_image(data, longest_side_for(connection))
        except DemoRecordingError as error:
            raise ToolError(str(error.args[0]) if error.args else str(error)) from error
        except (OSError, PicturePrepError) as error:
            raise ToolError(f"The frames could not be taken: {error}") from error
        labels = ", ".join(spoken_time(t) for t in times)
        return ToolImage(
            prepared.data,
            prepared.mime,
            description=(
                f"A contact sheet of {len(times)} frames from {path.name}, read left to "
                f"right and top to bottom, each labelled with its time: {labels}."
            ),
        )

    def sheet_summary(args: dict[str, Any]) -> str:
        found = known()
        name = found.name if found is not None else "the recording you choose"
        return (
            f"Take {frames_of(args)} frames {span_words(args)} of {name} as one picture "
            f"and send it to {company}."
        )

    # -- the hand-off ---------------------------------------------------------

    def open_in_quill(args: dict[str, Any]) -> str:
        from quill.core.storage import write_text_atomic

        text = str(args.get("text", "") or "").strip()
        if not text:
            raise ToolError("Give the whole narrative to open.")
        path = video()
        target = narrative_file(path)
        if not ctx.preview(f"Narrative of {path.name}, to save as {target.name}", text):
            raise ToolError("The person did not apply it.")
        try:
            write_text_atomic(target, text + "\n", encoding="utf-8")
        except OSError as error:
            raise ToolError(f"{target.name} could not be saved: {error}") from error
        ctx.on_ui(lambda: host.open_in_quill(str(target)), None)
        return f"Saved as {target} and opened in QUILL."

    def open_summary(_args: dict[str, Any]) -> str:
        found = known()
        if found is None:
            return "Save the narrative beside the recording you choose and open it in QUILL."
        return (
            f"Save the narrative as {narrative_file(found).name} beside {found.name} "
            "and open it in QUILL."
        )

    span = {
        "start": {
            "type": "string",
            "description": "Where to start, like 1:05; empty for the start.",
        },
        "end": {"type": "string", "description": "Where to end, like 2:30; empty for the end."},
    }
    tools = [
        FamilyTool(
            name=f"{APP}.transcript_excerpt",
            description=(
                "Read what is said in a stretch of the recording, with times, from the "
                "captions beside it."
            ),
            handler=transcript_excerpt,
            parameters=_schema(span, ()),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
    ]
    if can_see:
        tools.append(
            FamilyTool(
                name=f"{APP}.contact_sheet",
                description=(
                    "Look at a stretch of the recording as one picture of up to 16 "
                    "frames, each labelled with its time. Asks the person first, "
                    "because the picture leaves this computer."
                ),
                handler=contact_sheet,
                parameters=_schema(
                    {
                        **span,
                        "frames": {
                            "type": "integer",
                            "description": "How many frames, 1 to 16 (9 if not given).",
                        },
                    },
                    (),
                ),
                category=PermissionCategory.CAPTURE_SCREEN,
                risk=RiskLevel.MEDIUM,
                app=APP,
                summarize=sheet_summary,
            )
        )
    tools.append(
        FamilyTool(
            name=f"{APP}.open_in_quill",
            description=(
                "Hand the finished narrative over: the person sees it in full and "
                "chooses Apply, then it is saved as Markdown beside the recording and "
                "opened in QUILL."
            ),
            handler=open_in_quill,
            parameters=_schema(
                {"text": {"type": "string", "description": "The whole narrative, Markdown."}},
                ("text",),
            ),
            category=PermissionCategory.MODIFY_DOCUMENT,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=open_summary,
        )
    )
    return tools
