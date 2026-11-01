"""Make This Right for My Player: Quill Converter's agent task (codex.md 6.7, Phase 4c).

The person says what they want ("make these 40 MP3s one M4B audiobook with a
chapter per file, at a size my phone can hold"), and an agent engine -- My
GitHub Copilot or Codex -- works it out with Converter's own tools in the shared
agent window (:mod:`quill.ui.agent_window`):

* ``converter.list_queue`` -- the queued files by name, with an id (``F1``) the
  other tools take, and what Convert would do now. Never a folder.
* ``converter.probe`` -- one file as File Properties describes it
  (``media_probe.describe``): codecs, length, rate, tags and chapters, as text.
  **The model never hears the audio**; only this text goes.
* ``converter.list_formats`` -- the formats this computer can write, with what
  each can and cannot carry, the presets, bit rates, chapter sources and effects.
* ``converter.queue_job`` -- sets the window's own choices (Convert to, Preset,
  Bit rate, Chapter marks, Effects) and starts Convert Now, Join into One File
  or Split by Chapters through the same code those commands run. It asks
  first, naming the files, the format, the bit rate and the chapters.

The job runs on the whole queue, as every Converter command does. Handlers run
on a worker thread; every touch of the window goes through ``ctx.on_ui``.
Nothing here announces: the agent window says each step and the closing
summary, once (GATE-13), and the window's own progress reports the job.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "APP",
    "INSTRUCTION_HELP",
    "MAKE_IT_RIGHT",
    "converter_task_facts",
    "converter_task_tools",
]

APP = "converter"

#: How many queued files are listed by name; the rest are counted.
_LIST_LIMIT = 200
_ACTIONS = ("convert", "join", "split")

MAKE_IT_RIGHT = AppTaskSpec(
    app=APP,
    agent_id="converter-make-it-right",
    title="Make This Right for My Player",
    instructions=(
        "You help someone who uses a screen reader with Quill Converter, which "
        "converts audio and video files on their computer. See what is queued "
        "with converter_list_queue, read files with converter_probe (text about "
        "each file; you never hear the audio), and see what this computer can "
        "write with converter_list_formats. Then start one job on the whole "
        "queue with converter_queue_job: convert each file, join them all into "
        "one file (a chapter for each file, in formats that carry chapters), or "
        "split each file at its chapters. Choose a format, preset and bit rate "
        "that fit the device the person names; mono and a low bit rate keep "
        "spoken word small. The job asks the person first, and they may say no."
    ),
    done_words={f"{APP}.queue_job": "Started a conversion"},
    noun="job",
)

INSTRUCTION_HELP = (
    "Type what you want done with the files in the queue, then press Enter. For "
    "example: make these one M4B audiobook with a chapter per file, small enough "
    "for my phone. The AI reads the files' details, never their sound, and asks "
    "you before it starts anything. While a task runs, what you type here goes to "
    "it as a follow-up."
)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def converter_task_facts(host: Any) -> str:
    """What the window shows, as text, sent with the first instruction."""
    count = len(getattr(host, "_entries", ()) or ())
    lines = [f"Queue: {_plural(count, 'item')}."]
    try:
        lines.append(f"Convert would make: {host.describe_choices()}.")
    except Exception:  # noqa: BLE001 - a half-built window still has a queue
        pass
    return "\n".join(lines)


def _queued_files(entries: list[tuple[Path, Path | None]], recurse: bool) -> list[Path]:
    """Every file the queue holds, folders opened, as Join reads them."""
    from quill.core.audio.assemble import join_inputs

    return list(join_inputs(entries, recurse=recurse))


def _bitrates() -> tuple[str, ...]:
    from quill.ui.audio_studio.convert_audio_dialog import _BITRATE_CHOICES

    return tuple(value for value, _label in _BITRATE_CHOICES if value)


def _format_name(fmt: str) -> str:
    from quill.core.audio.formats import format_label

    return format_label(fmt).split(" -- ")[0]


def _status_text(host: Any) -> str:
    try:
        bar = host.frame.GetStatusBar()
        return str(bar.GetStatusText(0)) if bar is not None else ""
    except Exception:  # noqa: BLE001 - no bar, no words
        return ""


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def converter_task_tools(host: Any, ctx: AppTaskHost) -> list[FamilyTool]:
    """Quill Converter's tools for one task."""
    known: dict[str, Path] = {}

    def queue_now() -> tuple[list[tuple[Path, Path | None]], bool]:
        def read() -> tuple[list[tuple[Path, Path | None]], bool]:
            recurse = getattr(host, "_recurse", None)
            return list(host._entries), bool(recurse.GetValue()) if recurse else True

        return ctx.on_ui(read, ([], True)) or ([], True)

    def files_now() -> list[Path]:
        entries, recurse = queue_now()
        files = _queued_files(entries, recurse)
        known.clear()
        for index, path in enumerate(files, start=1):
            known[f"F{index}"] = path
        return files

    def file_for(args: dict[str, Any]) -> Path:
        wanted = str(args.get("file", "") or "").strip()
        if not known:
            files_now()
        if wanted.upper() in known:
            return known[wanted.upper()]
        folded = wanted.casefold()
        for path in known.values():
            if folded and path.name.casefold() == folded:
                return path
        raise ToolError(
            f"There is no queued file {wanted or 'like that'}. Use converter_list_queue "
            "and pass its id, such as F1."
        )

    # -- reads ---------------------------------------------------------------

    def list_queue(_args: dict[str, Any]) -> str:
        files = files_now()
        if not files:
            return "The queue is empty. The person adds files with Add Files (Ctrl+O)."
        lines = [f"{_plural(len(files), 'file')} queued:"]
        lines += [f"F{i}. {p.name}" for i, p in enumerate(files[:_LIST_LIMIT], start=1)]
        if len(files) > _LIST_LIMIT:
            lines.append(f"... and {len(files) - _LIST_LIMIT} more.")
        now = ctx.on_ui(host.describe_choices, "")
        if now:
            lines.append(f"Convert would make now: {now}.")
        return "\n".join(lines)

    def probe_file(args: dict[str, Any]) -> str:
        from quill.core.audio.media_probe import describe, probe

        path = file_for(args)
        return "\n".join(describe(probe(path)))

    def list_formats(_args: dict[str, Any]) -> str:
        from quill.core.audio.assemble import CHAPTER_FORMATS
        from quill.core.audio.chapter_plan import CHAPTER_SOURCES
        from quill.core.audio.effect_recipes import CUSTOM_RECIPE_ID, recipe_choices
        from quill.core.audio.formats import (
            ALLOWED_SAMPLE_RATES,
            FIXED_BITRATE_FORMATS,
            LOSSLESS_FORMATS,
            MONO_ONLY_FORMATS,
            is_video_format,
            output_extension,
        )
        from quill.core.audio.presets import preset_choices

        formats = list(ctx.on_ui(lambda: list(host._formats), []) or [])
        lines = ["Formats this computer can write (id: name):"]
        for fmt in formats:
            notes = [output_extension(fmt)]
            if is_video_format(fmt):
                notes.append("video")
            if fmt in LOSSLESS_FORMATS:
                notes.append("lossless, bit rate ignored")
            if fmt in FIXED_BITRATE_FORMATS:
                notes.append("fixed bit rate")
            if fmt in MONO_ONLY_FORMATS:
                notes.append("mono only")
            if fmt in ALLOWED_SAMPLE_RATES:
                rates = ", ".join(str(r) for r in ALLOWED_SAMPLE_RATES[fmt])
                notes.append(f"sample rates {rates}")
            notes.append(
                "chapters written into the file"
                if fmt in CHAPTER_FORMATS
                else "chapters kept beside the file"
            )
            lines.append(f"- {fmt}: {_format_name(fmt)} ({'; '.join(notes)})")
        lines.append("Sound presets (id: what it is):")
        lines += [f"- {pid}: {label}" for pid, label in preset_choices("audio")]
        lines.append("Video presets (id: what it is):")
        lines += [f"- {pid}: {label}" for pid, label in preset_choices("video")]
        lines.append(f"Bit rates in kbps: {', '.join(_bitrates())}, or 0 to keep the preset's own.")
        lines.append("Chapter marks (id: where they come from):")
        lines += [f"- {key}: {label}" for key, label in CHAPTER_SOURCES]
        lines.append("Effects (id: what it does):")
        lines += [f"- {rid}: {label}" for rid, label in recipe_choices() if rid != CUSTOM_RECIPE_ID]
        return "\n".join(lines)

    # -- the job -------------------------------------------------------------

    def job_choices(args: dict[str, Any]) -> dict[str, Any]:
        """The arguments, checked against what this window offers."""
        from quill.core.audio.chapter_plan import CHAPTER_SOURCES
        from quill.core.audio.effect_recipes import CUSTOM_RECIPE_ID, recipe_choices
        from quill.core.audio.formats import is_video_format
        from quill.core.audio.presets import preset_by_id, preset_choices

        action = str(args.get("action", "convert") or "convert").strip().lower()
        if action not in _ACTIONS:
            raise ToolError("The action is convert, join or split.")
        fmt = str(args.get("format", "") or "").strip().lower()
        formats = list(ctx.on_ui(lambda: list(host._formats), []) or [])
        if fmt not in formats:
            raise ToolError(
                f"{fmt or 'That'} is not a format this computer can write. Use "
                "converter_list_formats and pass an id from it."
            )
        video = is_video_format(fmt)
        if action == "join" and video:
            raise ToolError("Join makes one sound file. Choose a sound format.")
        kind = "video" if video else "audio"
        preset = str(args.get("preset", "") or "").strip().lower()
        if preset and preset not in [pid for pid, _label in preset_choices(kind)]:
            raise ToolError(f"{preset} is not a {kind} preset. Use converter_list_formats.")
        try:
            bitrate = int(args.get("bitrate_kbps", 0) or 0)
        except (TypeError, ValueError):
            bitrate = -1
        if bitrate and str(bitrate) not in _bitrates():
            raise ToolError(f"The bit rate is one of {', '.join(_bitrates())}, or 0.")
        chapters = str(args.get("chapters", "") or "").strip().lower()
        if chapters and chapters not in [key for key, _label in CHAPTER_SOURCES]:
            raise ToolError("That is not a chapter source. Use converter_list_formats.")
        effect = str(args.get("effect", "") or "").strip().lower()
        if effect and effect not in [
            rid for rid, _l in recipe_choices() if rid != CUSTOM_RECIPE_ID
        ]:
            raise ToolError("That is not an effect. Use converter_list_formats.")
        found = preset_by_id(preset) if preset else None
        return {
            "action": action,
            "format": fmt,
            "preset": preset,
            "preset_name": found.name if found is not None else "",
            "bitrate": bitrate,
            "chapters": chapters,
            "effect": effect,
            "name": " ".join(str(args.get("file_name", "") or "").split()),
        }

    def job_words(choice: dict[str, Any], files: list[Path]) -> str:
        """The question: the files, the format, the bit rate and the chapters."""
        from quill.core.audio.assemble import CHAPTER_FORMATS
        from quill.core.audio.chapter_plan import CHAPTER_SOURCES

        names = ", ".join(p.name for p in files)
        what = f"{_plural(len(files), 'file')} ({names})" if files else "the queue"
        fmt = _format_name(choice["format"])
        how = []
        if choice["preset_name"]:
            how.append(f"{choice['preset_name']} preset")
        how.append(
            f"at {choice['bitrate']} kbps" if choice["bitrate"] else "at the preset's bit rate"
        )
        if choice["action"] == "join":
            marks = (
                "with a chapter for each file"
                if choice["format"] in CHAPTER_FORMATS
                else "with a chapter list beside it for each file"
            )
            return f"Join {what} into one {fmt} file, {', '.join(how)}, {marks}."
        chapters = dict(CHAPTER_SOURCES).get(choice["chapters"], "")
        chapter_words = f" Chapter marks: {chapters.split(' (')[0].lower()}." if chapters else ""
        if choice["action"] == "split":
            return f"Split {what} into one {fmt} file per chapter, {', '.join(how)}.{chapter_words}"
        return f"Convert {what} to {fmt}, {', '.join(how)}.{chapter_words}"

    def summarize(args: dict[str, Any]) -> str:
        try:
            choice = job_choices(args)
        except ToolError:
            return "Start a conversion of the queued files."
        return job_words(choice, files_now())

    def queue_job(args: dict[str, Any]) -> str:
        choice = job_choices(args)
        files = files_now()
        if not files:
            raise ToolError("The queue is empty, so there is nothing to convert.")
        if choice["action"] == "join" and len(files) < 2:
            raise ToolError("Join needs at least two files in the queue.")
        if ctx.on_ui(lambda: bool(host._busy), True):
            raise ToolError("A job is already running in Quill Converter.")

        def start() -> str:
            before = _status_text(host)
            _apply_choices(host, choice)
            if choice["action"] == "join":
                host.join_into_one(out_path=_join_path(host, choice, files))
            elif choice["action"] == "split":
                host.split_by_chapters()
            else:
                host.convert_or_stop()
            if bool(host._busy):
                return ""
            after = _status_text(host)
            if after and after != before:
                return after
            return "Quill Converter did not start it; its window says why."

        problem = ctx.on_ui(start, "The task was stopped.")
        if problem:
            raise ToolError(problem)
        return (
            f"Started: {job_words(choice, files)} The window shows its progress, and "
            "the Conversion Report (Ctrl+R) says how it went."
        )

    file_arg = {"type": "string", "description": "The file's id from the queue (F1)."}
    return [
        FamilyTool(
            name=f"{APP}.list_queue",
            description=(
                "List the queued files by name, with an id such as F1, and what Convert "
                "would make now."
            ),
            handler=list_queue,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.probe",
            description=(
                "Describe one queued file as File Properties does: container, codecs, "
                "length, sample rate, channels, bit rate, tags and chapters. Text only."
            ),
            handler=probe_file,
            parameters=_schema({"file": file_arg}, ("file",)),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_formats",
            description=(
                "List the formats this computer can write, with what each carries, and "
                "the presets, bit rates, chapter sources and effects to choose from."
            ),
            handler=list_formats,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.queue_job",
            description=(
                "Start one job on the whole queue: convert each file, join them into "
                "one file with a chapter per file, or split each file at its chapters. "
                "Sets the window's choices first. Asks the person."
            ),
            handler=queue_job,
            parameters=_schema(
                {
                    "action": {
                        "type": "string",
                        "enum": list(_ACTIONS),
                        "description": "convert, join or split.",
                    },
                    "format": {"type": "string", "description": "A format id (m4b, mp3)."},
                    "preset": {
                        "type": "string",
                        "description": "A preset id (optional; keeps the current one).",
                    },
                    "bitrate_kbps": {
                        "type": "integer",
                        "description": "A bit rate from the list, or 0 for the preset's.",
                    },
                    "chapters": {
                        "type": "string",
                        "description": "Where chapter marks come from (optional).",
                    },
                    "effect": {"type": "string", "description": "An effect id (optional)."},
                    "file_name": {
                        "type": "string",
                        "description": "For join: the new file's name, without extension.",
                    },
                },
                ("action", "format"),
            ),
            category=PermissionCategory.MODIFY_SELECTION,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=summarize,
        ),
    ]


def _apply_choices(host: Any, choice: dict[str, Any]) -> None:
    """Set the window's own choices, as a person would, so it shows what runs."""
    host._format.SetSelection(host._formats.index(choice["format"]))
    host._on_format_changed(None)
    if choice["preset"] in host._preset_ids:
        host._preset.SetSelection(host._preset_ids.index(choice["preset"]))
    if choice["chapters"] in host._chapter_ids:
        host._chapters.SetSelection(host._chapter_ids.index(choice["chapters"]))
    if choice["effect"] in host._effect_ids:
        host._effect.SetSelection(host._effect_ids.index(choice["effect"]))
    advanced = getattr(host, "_advanced_choices", {})
    if "adv_bitrate" in advanced:
        ctrl, table = advanced["adv_bitrate"]
        values = [str(value) for value, _label in table]
        wanted = str(choice["bitrate"] or "")
        if wanted in values:
            ctrl.SetSelection(values.index(wanted))
    host._remember()


def _join_path(host: Any, choice: dict[str, Any], files: list[Path]) -> Path:
    """Where the joined file goes: the output folder, a new name, never over a file."""
    from quill.core.audio.assemble import safe_file_title
    from quill.core.audio.formats import output_extension

    dest = Path(host._destination())
    dest.mkdir(parents=True, exist_ok=True)
    stem = safe_file_title(choice["name"], files[0].parent.name or "Joined")
    ext = output_extension(choice["format"])
    path = dest / f"{stem}{ext}"
    number = 2
    while path.exists():
        path = dest / f"{stem} ({number}){ext}"
        number += 1
    return path
