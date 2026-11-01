"""What QUILL Studio does with AI: Ask, Describe a Picture, and screenshot questions.

The commands and hooks behind :class:`~quill.ui.audio_studio.studio_ai_host.StudioAiMixin`,
kept apart from the adapter so the adapter keeps having no command of its own.
Every request goes to the AI in use in Choose Your AI, through the shared
service, behind Safe Mode, the family's AI Off and the capability gate.

**Ask** (Ctrl+6, AI > Ask...) is the family's one conversation window
(:mod:`quill.ui.hosted_ai_app_ask`) about your recording setup: the last
pre-flight check, what it measured, the last recording check, the recording
running now and the book open in the Chapter Workbench (by name), read fresh
every turn (``app_ask_context.studio_context``). Never a picture, never sound.
Its quick list starts with "Is my setup ready?" and "Does this recording look
right?", then the three every app shares.

**Describe a Picture** (Ctrl+F5) asks about one picture file, or one frame of a
video at the time you give: taken on this computer, fitted to the connection
(:mod:`quill.core.ai.picture_prep`) and described, with the time when it is a
frame. The same picture asked about again is answered from this session's
cache and sends nothing.

**The agent tasks** (codex.md Phase 4c): Recording Pre-flight Check (Ctrl+3,
:mod:`~quill.ui.audio_studio.studio_ai_task`) and Narrate a Recording
(Ctrl+Shift+3, :mod:`~quill.ui.audio_studio.studio_ai_narrative`), in the
shared agent window, on Copilot or Codex.

**Screenshot questions.** The Screenshot Inspector and Ask AI About a Video
send to the connection in use as well -- Studio's own picture chooser folded
into Choose Your AI. A connection that cannot see sends nothing and offers the
switch in one key (10A.8). The first picture on each connection asks once where
pictures go (10B.4, :mod:`quill.core.ai.picture_consent`); every screenshot is
still confirmed before it goes, because a screenshot is never sent silently.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["DESCRIBE_QUESTION", "StudioAiFeaturesMixin"]

#: What Describe a Picture asks.
DESCRIBE_QUESTION = (
    "Describe this picture in a few sentences: who or what is shown, any words in it, "
    "and what seems to be happening."
)
_ABOUT_FACTS = (
    "the last pre-flight check and what it measured, the last recording check, the "
    "recording running now and the book open, by name"
)
_PICTURES = "*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp"
_VIDEOS = "*.mp4;*.m4v;*.mov;*.mkv;*.webm;*.avi"
_WILDCARD = (
    f"Pictures and videos ({_PICTURES};{_VIDEOS})|{_PICTURES};{_VIDEOS}|"
    f"Pictures ({_PICTURES})|{_PICTURES}|Videos ({_VIDEOS})|{_VIDEOS}"
)
_TITLE = "Describe a Picture"


class StudioAiFeaturesMixin:
    """Ask, Describe a Picture and the picture route. Mixed in through ``StudioAiMixin``."""

    # -- Ask ------------------------------------------------------------------ #

    def _ai_app_ask(self) -> None:
        """Ask (Ctrl+6): the conversation about your recording setup (10C)."""
        from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS, quick_prompts_for
        from quill.ui.hosted_ai_app_ask import open_app_ask, rows_from_prompts

        prompts = quick_prompts_for("studio")
        ordered = [p for p in prompts if p not in FAMILY_PROMPTS] + list(FAMILY_PROMPTS)
        open_app_ask(
            self,
            app="studio",
            subject="your recording setup",
            about_facts=_ABOUT_FACTS,
            facts=self._studio_ask_facts,
            rows=rows_from_prompts(ordered),
            local_answer=self._studio_what_can_i_do,
        )

    def _studio_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts (``app_ask_context.studio_context``), read fresh."""
        del question, needs
        from quill.core.ai.app_ask_context import studio_context

        summary, findings, measured = getattr(self, "_studio_last_check", None) or ("", (), None)
        recorder = getattr(self, "_demo", None)
        try:
            recording = str(recorder.status_line()) if recorder is not None else ""
        except Exception:  # noqa: BLE001 - a recorder mid-stop has no status
            recording = ""
        book = str(getattr(self, "_active_book_path", "") or "")
        return studio_context(
            plan_summary=summary,
            findings=findings,
            capture=_measured(measured),
            verification=getattr(self, "_studio_last_verification", None),
            recording=recording,
            book=Path(book).stem if book else "",
        )

    def _studio_what_can_i_do(self) -> str:
        """The local answer, from Studio's own F1 catalogue and its menus."""
        from quill.core.ai.family_prompt_catalogue import what_can_i_do_here
        from quill.core.audio_studio.surface_help import purpose_for_title
        from quill.ui.hosted_ai_app_ask import menu_routes

        return what_can_i_do_here(
            purpose_for_title("QUILL Studio"),
            commands=menu_routes(self.frame.GetMenuBar()),  # type: ignore[attr-defined]
        )

    # -- the picture route ----------------------------------------------------- #

    def _studio_picture_route(self) -> Any:
        """The connection a picture would go to now, as a ``PictureRoute``.

        ``provider`` is ``off`` when nothing in use can see, so automatic
        analysis pauses rather than sending anywhere else.
        """
        from quill.core.ai.connection_caps import CONNECTION_NAMES
        from quill.core.ai.picture_consent import receiver
        from quill.core.studio_capture_ai import PictureRoute

        try:
            if not self._ai_host().feature_enabled("hosted_ai"):  # type: ignore[attr-defined]
                return PictureRoute("off")
            service = self._ai_service()  # type: ignore[attr-defined]
            connection = str(service.connection_in_use or "")
            if not connection or not service.can_do("pictures"):
                return PictureRoute("off")
            provider = str(getattr(service, "own_key_provider", "") or "openai")
            return PictureRoute(
                connection,
                model=str(service.connection_model(connection) or ""),
                host=receiver(connection, provider),
                name=CONNECTION_NAMES.get(connection, connection),
            )
        except Exception:  # noqa: BLE001 - an unreadable connection sends nothing
            return PictureRoute("off")

    def _studio_picture_consent(self, route: Any) -> bool:
        """10B.4: the first picture on a connection says where pictures go, once."""
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        return ask_picture_consent(self, route.provider)

    def _choose_vision_connection(self) -> Any:
        """The connection a picture may go to, after the gate and the consent; or None."""
        if not self._ai_switched_on():  # type: ignore[attr-defined]
            return None
        # The capability first: a connection that cannot see is offered the
        # switch, and never asks for the free AI's agreement first.
        if not self._ai_capable("pictures") or not self._ai_ready():  # type: ignore[attr-defined]
            return None  # nothing sent; the switch was offered (codex.md 10A.8)
        route = self._studio_picture_route()
        if route.provider == "off" or not self._studio_picture_consent(route):
            return None
        return route

    def _approve_capture_ai(self) -> Any:
        """The connection, then the per-screenshot yes: never sent silently (10B.4)."""
        import wx

        route = self._choose_vision_connection()
        if route is None:
            return None
        model = f"Model: {route.model}\n" if route.model else ""
        result = self._show_message_box(  # type: ignore[attr-defined]
            f"Send this complete screenshot to {route.name}?\n{model}"
            f"It goes to {route.host}.\n\n"
            "The image may contain private information. No automatic redaction has been "
            "applied.\nAI observations are uncertain and do not verify privacy or correctness.",
            "Send screenshot to AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        return route if result in (wx.YES, wx.ID_YES) else None

    def _automatic_vision_connection(self, preferences: dict[str, Any]) -> Any:
        """The connection automatic analysis would use now. No dialogs: when it is
        not the approved one, ``auto_ai_allowed`` says no and analysis pauses."""
        del preferences
        return self._studio_picture_route()

    def _studio_send_inspection(
        self,
        evidence: Any,
        prompt_parts: tuple[str, str, str],
        route: Any,
        on_success: Any,
        on_failure: Any,
        lifetime: Any,
        can_send: Any = None,
    ) -> Any:
        """Prepare the screenshot off the UI thread, then ask the connection in use.

        ``prepare_inspection`` asks the capability registry and verifies the
        file before anything is written; the shared service asks again before
        anything leaves (GATE-CAPS). Returns the preparing task, whose
        cancellation stops the answer being delivered.
        """
        from quill.core.studio_capture_ai import prepare_inspection

        instructions, question, history = prompt_parts
        service = self._ai_service()  # type: ignore[attr-defined]
        record = service.capability_record(route.provider)
        scratch = Path(tempfile.mkdtemp(prefix="quill-studio-inspect-"))

        def work(*, cancellation_token: Any = None, **_kwargs: Any) -> Any:
            if self._safe_mode:  # type: ignore[attr-defined]
                raise RuntimeError("AI is disabled in Safe Mode.")
            return prepare_inspection(
                evidence,
                record=record,
                folder=scratch,
                instructions=instructions,
                question=question,
                history=history,
                cancellation_token=cancellation_token,
                can_send=can_send,
            )

        def prepared(task: Any, request: Any) -> None:
            if task is not None and task.cancellation_token.is_cancelled():
                shutil.rmtree(scratch, ignore_errors=True)
                return

            def done(text: str) -> None:
                shutil.rmtree(scratch, ignore_errors=True)
                if not lifetime.is_alive:
                    return
                on_success(
                    task,
                    f"AI ({route.name}{', ' + route.model if route.model else ''}); uncertain.\n"
                    f"Question: {question or 'Inspect screenshot'}\n"
                    f"{request.prepared.inspected} {text.strip() or 'No response.'}",
                )

            def failed(sentence: str) -> None:
                shutil.rmtree(scratch, ignore_errors=True)
                if lifetime.is_alive:
                    on_failure(task, RuntimeError(sentence))

            service.describe_image(
                request.path,
                request.prompt,
                on_done=done,
                on_error=failed,
                requires=("text", "pictures"),
            )

        def broke(task: Any, error: BaseException) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            on_failure(task, error)

        holder: dict[str, Any] = {}
        task = self._task_manager.submit(  # type: ignore[attr-defined]
            "Prepare a screenshot question",
            work,
            on_success=lambda _t, request: prepared(holder.get("task"), request),
            on_failure=lambda _t, error: broke(holder.get("task"), error),
            ui_lifetime=lifetime,
        )
        holder["task"] = task
        return task

    # -- the agent tasks (codex.md 6.1, 6.8) ----------------------------------- #

    def cmd_ai_task(self) -> None:
        """Recording Pre-flight Check (Ctrl+3, codex.md 6.1): the set-up checked
        with Studio's own tools, answered as a short checklist. Enter starts it."""
        from quill.ui.audio_studio.studio_ai_task import (
            INSTRUCTION_HELP,
            PREFLIGHT,
            STARTER,
            studio_preflight_facts,
            studio_preflight_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            PREFLIGHT,
            lambda ctx: studio_preflight_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            starter=STARTER,
            context=lambda: studio_preflight_facts(self),
        )

    def cmd_studio_ai_narrative(self) -> None:
        """Narrate a Recording (Ctrl+Shift+3, codex.md 6.8): an accessible narrative
        of the last recording, or one you choose, opened in QUILL after you read it."""
        from quill.ui.audio_studio.studio_ai_narrative import (
            NARRATE,
            NARRATIVE_HELP,
            NARRATIVE_STARTER,
            studio_narrative_facts,
            studio_narrative_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            NARRATE,
            lambda ctx: studio_narrative_tools(self, ctx),
            instruction_help=NARRATIVE_HELP,
            starter=NARRATIVE_STARTER,
            context=lambda: studio_narrative_facts(self),
        )

    # -- Describe a Picture ---------------------------------------------------- #

    def cmd_studio_describe_picture(self) -> None:
        """Describe a Picture (Ctrl+F5): one picture, or one video frame, described."""
        route = self._choose_vision_connection()
        if route is None:
            return
        path = self._studio_choose_picture()
        if path is None:
            return
        at: float | None = None
        if path.suffix.lower() in _VIDEOS.replace("*", "").split(";"):
            at = self._studio_ask_time()
            if at is None:
                return
        ffmpeg = self._demo_ffmpeg() if at is not None else ""  # type: ignore[attr-defined]
        if at is not None and not ffmpeg:
            self._announce("Taking a frame needs FFmpeg. Use Voices, Get FFmpeg.")  # type: ignore[attr-defined]
            return
        scratch = Path(tempfile.mkdtemp(prefix="quill-studio-picture-"))
        self._announce("Working.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> bytes:
            if at is None:
                return path.read_bytes()
            from quill.core.ai.picture_prep import extract_frames

            frames = extract_frames(str(ffmpeg), path, [at], scratch)
            return frames[0].path.read_bytes()

        def took(_task: Any, data: bytes) -> None:
            self._studio_describe_bytes(data, scratch, at, route)

        def failed(_task: Any, error: BaseException) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            message = str(error.args[0]) if error.args else str(error)
            self._announce(f"The picture could not be read: {message}")  # type: ignore[attr-defined]

        self._task_manager.submit(  # type: ignore[attr-defined]
            "Read a picture",
            work,
            on_success=took,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),  # type: ignore[attr-defined]
        )

    def _studio_describe_bytes(
        self, data: bytes, scratch: Path, at: float | None, route: Any
    ) -> None:
        """Fit *data* to the connection, answer from the cache or ask, then tidy up."""
        from quill.core.ai.picture_prep import (
            PicturePrepError,
            described_by_sentence,
            prepare_request,
        )

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = route.provider
        try:
            prepared = prepare_request(
                [data],
                service.capability_record(connection),
                times=(at,) if at is not None else (),
            )
        except PicturePrepError as error:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(str(error.args[0]))  # type: ignore[attr-defined]
            return
        image = prepared.images[0]
        cache = _picture_cache(self)
        cached = cache.get(image.digest, DESCRIBE_QUESTION, connection)
        if cached is not None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._studio_picture_answer(
                f"{cached} Nothing was sent: this picture was asked about already."
            )
            return
        target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
        target.write_bytes(image.data)

        def done(text: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            answer = f"{prepared.inspected} {described_by_sentence(connection)} {text.strip()}"
            cache.put(
                image.digest, DESCRIBE_QUESTION, answer, connection=connection, prepared=prepared
            )
            self._studio_picture_answer(answer)

        def failed(sentence: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(sentence)  # type: ignore[attr-defined]

        service.describe_image(
            target,
            DESCRIBE_QUESTION,
            on_done=done,
            on_error=failed,
            requires=("text", "pictures"),
        )

    def _studio_picture_answer(self, answer: str) -> None:
        from quill.ui.hosted_ai_app_ask import show_picture_answer

        show_picture_answer(self, answer)

    def _studio_choose_picture(self) -> Path | None:
        import wx

        from quill.core.paths import app_data_dir

        last = str(getattr(getattr(self, "_last_capture", None), "path", "") or "")
        folder = str(Path(last).parent) if last else str(app_data_dir() / "studio-captures")
        dialog = wx.FileDialog(
            self.frame,  # type: ignore[attr-defined]
            "Choose a picture or a video",
            defaultDir=folder,
            defaultFile=Path(last).name if last else "",
            wildcard=_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, _TITLE) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def _studio_ask_time(self) -> float | None:
        """The moment of the video to describe, as seconds; None on Cancel."""
        import wx

        from quill.core.demo_recording import DemoRecordingError
        from quill.core.video_review import parse_time

        dialog = wx.TextEntryDialog(
            self.frame,  # type: ignore[attr-defined]
            "Which moment of the video? Write minutes and seconds, like 2:10.",
            _TITLE,
            "0:00",
        )
        try:
            if self._show_modal_dialog(dialog, _TITLE) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            text = dialog.GetValue()
        finally:
            dialog.Destroy()
        try:
            return parse_time(text)
        except DemoRecordingError as error:
            self._announce(str(error.args[0]))  # type: ignore[attr-defined]
            return None


def _measured(facts: Any) -> dict[str, str]:
    """The few pre-flight measurements worth a sentence, from ``PreflightFacts``."""
    if facts is None:
        return {}
    found: dict[str, str] = {
        "Displays": str(getattr(facts, "display_count", "") or ""),
        "Screen capture": str(getattr(facts, "video_backend", "") or ""),
        "Video encoder": str(getattr(facts, "h264_encoder", "") or ""),
        "Microphone held by": str(getattr(facts, "microphone_holder", "") or ""),
        "Camera": str(getattr(facts, "camera_error", "") or ""),
    }
    dropped = getattr(facts, "trial_dropped_share", None)
    if dropped is not None:
        found["Frames dropped in the trial"] = f"{round(float(dropped) * 100)} percent"
    if getattr(facts, "on_battery", False):
        found["Power"] = "on battery"
    return {name: value for name, value in found.items() if value}


def _picture_cache(host: Any) -> Any:
    """This session's picture cache: in memory only (10B.2 rule 7)."""
    cache = getattr(host, "_studio_picture_cache", None)
    if cache is None:
        from quill.core.ai.picture_prep import PictureCache

        cache = PictureCache()
        host._studio_picture_cache = cache
    return cache
