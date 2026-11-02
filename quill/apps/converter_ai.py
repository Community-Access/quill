"""Quill Converter reaches the family's AI through the shared small-app adapter.

codex.md Phase 3 (10E.7). Quill Converter had no AI. Now it runs the shared
hosted AI through :class:`~quill.ui.hosted_ai_app_adapter.AppAiMixin` -- hooks
only -- with its own "QUILL Converter" sign-in, so Choose Your AI, Which AI Am
I Using, the one AI Usage list, the AI line in the main window and Safe Mode's
refusal all come from the code every app shares.

What Quill Converter *does* with AI is :class:`ConverterAiFeaturesMixin`:

* **Ask** (Ctrl+Shift+8, AI > Ask...) about the queue: each queued file as File
  Properties describes it (``media_probe``), the Convert to choice, and the last
  conversion's report (``app_ask_context.converter_context``).
* **Will This Play on My Device?** (Ctrl+Shift+D): asks which device, reads the
  queued files, and sends one request.
* **Make This Right for My Player...** (Ctrl+F3): the agent task
  (:mod:`quill.apps.converter_ai_task`), which reads the queue as text and
  starts one Convert, Join or Split job after asking.

**The model never hears the audio.** Only probe text goes: codecs, lengths,
sample rates, tags, file names. Folders never go (``scrub`` strips any path that
slips in, and the text built here names files only).

**Never blocks.** ffprobe runs on the task manager, never on the UI thread; its
answers are kept by path, size and modification time, so Ask's facts -- built on
the UI thread every turn -- come from that cache, and a file not read yet is
named as such while a background read fills it in for the next turn.

**Keys.** Ctrl+1 to Ctrl+9 are the Window menu's, so Ask is Ctrl+Shift+8, Which
AI Ctrl+F8 and Choose Your AI Ctrl+Shift+F8, as in Quill Weather, Quill Radio,
QUILL Cast and QUILL Transcribe (``app_keymaps.py``, ``app_ai_keys.py``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.ui.hosted_ai_app_adapter import AppAiMixin

__all__ = [
    "AGENT_NAME",
    "AI_ROWS",
    "WILL_PLAY_TITLE",
    "ConverterAiFeaturesMixin",
    "ConverterAiMixin",
]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Converter"
WILL_PLAY_TITLE = "Will This Play on My Device?"
WHICH_DEVICE = (
    "Which device? For example an iPhone, a car stereo or an Echo. "
    "Leave it empty for the usual ones."
)

#: How many files are read and described; the rest are counted
#: (``converter_context`` describes the first twenty).
_PROBE_LIMIT = 20

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C D M H O S P).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("converter.ai_will_play", "Will This Play on My &Device?...", "cmd_converter_will_play"),
    ("tools.hosted_ai_task", "&Make This Right for My Player...", "cmd_ai_task"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)

_ProbeKey = tuple[str, int, int]


def _probe_key(path: Path) -> _ProbeKey | None:
    """What a probe answer is kept under: the file, its size and its modification time."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), int(stat.st_size), int(stat.st_mtime_ns))


def _read_queue(
    entries: Sequence[tuple[Path, Path | None]], known: set[_ProbeKey]
) -> tuple[dict[str, tuple[Path, ...]], dict[_ProbeKey, Any]]:
    """Off the UI thread: every queued folder's media files, and a probe of each of
    the first files not already read."""
    from quill.core.audio.formats import INPUT_EXTENSIONS
    from quill.core.audio.media_probe import probe

    folders: dict[str, tuple[Path, ...]] = {}
    files: list[Path] = []
    for path, root in entries:
        if root is None:
            files.append(path)
            continue
        try:
            found = tuple(
                sorted(
                    p
                    for p in path.rglob("*")
                    if p.is_file() and p.suffix.lower() in INPUT_EXTENSIONS
                )
            )
        except OSError:
            found = ()
        folders[str(path)] = found
        files.extend(found)
    probed: dict[_ProbeKey, Any] = {}
    for path in files[:_PROBE_LIMIT]:
        key = _probe_key(path)
        if key is not None and key not in known:
            probed[key] = probe(path)
    return folders, probed


class ConverterAiFeaturesMixin:
    """Will This Play on My Device? and the queue Ask reads. Mixed in through
    ``ConverterAiMixin``."""

    def cmd_ai_task(self) -> None:
        """Make This Right for My Player (Ctrl+F3, codex.md 6.7): the queue, read as
        text, then one Convert, Join or Split job, in the shared agent window. The
        job asks first, naming the files, format, bit rate and chapters; the
        audio never leaves."""
        from quill.apps.converter_ai_task import (
            INSTRUCTION_HELP,
            MAKE_IT_RIGHT,
            converter_task_facts,
            converter_task_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            MAKE_IT_RIGHT,
            lambda ctx: converter_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            context=lambda: converter_task_facts(self),
        )

    def cmd_converter_will_play(self) -> None:
        """Will This Play on My Device? (Ctrl+Shift+D): the queue, against a device."""
        if self._ai_refuse_safe_mode():  # type: ignore[attr-defined]
            return
        if not self._entries:  # type: ignore[attr-defined]
            self._announce("The queue is empty. Add files first, then ask.")  # type: ignore[attr-defined]
            return
        if not self._ai_ready() or not self._ai_capable("text"):  # type: ignore[attr-defined]
            return
        device = self._converter_ask_device()
        if device is None:
            self._set_status("Will This Play on My Device? cancelled.")  # type: ignore[attr-defined]
            return
        self._announce("Reading the queued files.")  # type: ignore[attr-defined]
        self._converter_ai_read(lambda: self._converter_will_play_send(device))

    def _converter_ask_device(self) -> str | None:
        """Which device, in a text entry; None when cancelled."""
        import wx

        dialog = wx.TextEntryDialog(self.frame, WHICH_DEVICE, WILL_PLAY_TITLE)  # type: ignore[attr-defined]
        try:
            if self._show_modal_dialog(dialog, WILL_PLAY_TITLE) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return str(dialog.GetValue()).strip()
        finally:
            dialog.Destroy()

    def _converter_will_play_send(self, device: str) -> None:
        from quill.core.ai.app_ask_context import facts_text
        from quill.core.ai.app_requests import will_play_prompt

        facts = self._converter_ai_facts()
        count = len(self._converter_ai_known()[0])
        where = f"on {device}" if device else "on the usual devices"
        self._app_ai_request(  # type: ignore[attr-defined]
            will_play_prompt(facts_text(facts), device),
            lambda text: self._app_ai_show(  # type: ignore[attr-defined]
                text or "No answer came back.", title=WILL_PLAY_TITLE
            ),
            working=f"Asking whether {count} file{'' if count == 1 else 's'} will play {where}.",
        )

    # -- the queue, read off the UI thread ---------------------------------------- #

    def _converter_ai_probes(self) -> dict[_ProbeKey, Any]:
        cache = getattr(self, "_converter_ai_probe_cache", None)
        if cache is None:
            cache = {}
            self._converter_ai_probe_cache = cache
        return cache

    def _converter_ai_folders(self) -> dict[str, tuple[Path, ...]]:
        folders = getattr(self, "_converter_ai_folder_cache", None)
        if folders is None:
            folders = {}
            self._converter_ai_folder_cache = folders
        return folders

    def _converter_ai_known(self) -> tuple[list[Path], list[str]]:
        """The queue's files as far as this thread knows, and folders not read yet."""
        files: list[Path] = []
        unread: list[str] = []
        folders = self._converter_ai_folders()
        for path, root in self._entries:  # type: ignore[attr-defined]
            if root is None:
                files.append(path)
            elif str(path) in folders:
                files.extend(folders[str(path)])
            else:
                unread.append(f"{path.name} (a folder)")
        return files, unread

    def _converter_ai_read(self, then: Callable[[], None] | None = None) -> None:
        """Read the queue in the background, then run *then* on the UI thread."""
        entries = list(self._entries)  # type: ignore[attr-defined]
        known = set(self._converter_ai_probes())

        def work(**_kwargs: Any) -> object:
            return _read_queue(entries, known)

        def done(_op: str, result: Any) -> None:
            folders, probed = result
            self._converter_ai_folders().update(folders)
            self._converter_ai_probes().update(probed)
            if then is not None:
                then()

        def failed(_op: str, error: BaseException) -> None:
            if then is not None:
                self._announce(f"Could not read the queued files. {error}")  # type: ignore[attr-defined]

        self._task_manager.submit(  # type: ignore[attr-defined]
            "converter-ai-probe", work, on_success=done, on_failure=failed
        )

    def _converter_ai_facts(self) -> Any:
        """The queue, the Convert to choice and the last report, from the cache only.

        Never blocks: a file not read yet is named, and its read is started so
        the next turn has it.
        """
        from dataclasses import replace

        from quill.core.ai.app_ask_context import Fact, converter_context
        from quill.core.audio.formats import format_label
        from quill.core.audio.media_probe import MediaInfo

        files, unread = self._converter_ai_known()
        cache = self._converter_ai_probes()
        infos: list[Any] = []
        for index, path in enumerate(files):
            if index >= _PROBE_LIMIT:
                infos.append(MediaInfo(path=path))  # counted, not described
                continue
            key = _probe_key(path)
            info = cache.get(key) if key is not None else None
            if info is None:
                unread.append(path.name)
            else:
                infos.append(info)
        context = converter_context(
            infos,
            output_format=format_label(self._chosen_format()),  # type: ignore[attr-defined]
            last_result=str(getattr(self, "_last_report", "") or ""),
        )
        if not unread:
            return context
        self._converter_ai_read()  # fresh for the next turn
        names = ", ".join(unread)
        return replace(context, facts=(*context.facts, Fact("Not read yet", names)))


class ConverterAiMixin(ConverterAiFeaturesMixin, AppAiMixin):
    """The shared hosted-AI commands on Quill Converter's frame: hooks, no commands."""

    _AI_APP = "converter"
    _AI_AGENT_NAME = AGENT_NAME
    _AI_ROWS = AI_ROWS
    _AI_SUBJECT = "these files"
    _AI_ABOUT_FACTS = (
        "each queued file's details as File Properties gives them, by file name and "
        "never its folder, the Convert to choice, and the last conversion's report"
    )

    def _app_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts: the queue as read so far, never waiting on a read."""
        del question, needs
        return self._converter_ai_facts()

    def _app_ai_purpose(self) -> str:
        from quill.core.converter_surface_help import purpose_for_title

        return purpose_for_title("Quill Converter")
