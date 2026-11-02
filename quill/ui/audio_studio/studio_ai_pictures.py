"""Describe a Folder, Describe Again and Save Described Copies in QUILL Studio.

These follow the approach of Kelly Ford's Image Description Toolkit (MIT; see
the third-party notices), in Studio's own architecture: Choose Your AI, the
capability gate, the 10B.4 consent and the task manager.

**Describe a Folder** (Ctrl+Shift+F5) describes every picture in a folder,
one at a time, in the prompt style you choose, with the photo's date, camera
and lens read on this computer and sent as context if you leave that checked
(its GPS location only if you check that too). Before anything is sent, one
question names the picture count and who receives them, and a ceiling per run
keeps it modest. Results are kept one file per picture under Studio's data, so
running the same folder again carries on where it stopped, and the
descriptions open in QUILL as one document. **Stop Describing the Folder**
(Alt+Shift+F5) stops after the picture in hand.

**Describe Again** (Ctrl+Alt+F5) adds another description -- another style,
or another AI chosen first in Choose Your AI -- to the last picture you
described, or to a folder or one picture of it, and keeps the earlier ones
beside it to compare.

**Save Described Copies** (Ctrl+Alt+F6) writes each picture's latest
description into a copy of it in a folder you choose; the originals are never
touched (:mod:`quill.io.picture_metadata`). Nothing is sent.

Mixed into ``StudioAiMixin`` beside :mod:`studio_ai_features`, so the adapter
keeps having no command of its own.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["StudioPicturesMixin"]

_FOLDER_TITLE = "Describe a Folder"
_AGAIN_TITLE = "Describe Again"
_COPIES_TITLE = "Save Described Copies"


class StudioPicturesMixin:
    """The picture-batch commands. Mixed in through ``StudioAiMixin``."""

    _studio_picture_run: Any = None
    _studio_last_folder: Path | None = None

    # -- Describe a Folder ------------------------------------------------------ #

    def cmd_studio_describe_folder(self) -> None:
        """Describe a Folder (Ctrl+Shift+F5): every picture in a folder, kept and resumable."""
        if self._studio_run_busy():
            return
        route = self._choose_vision_connection()  # type: ignore[attr-defined]
        if route is None:
            return
        from quill.core.ai.picture_batch import default_ceiling
        from quill.ui.audio_studio.studio_picture_dialogs import DescribeFolderDialog

        provider = self._studio_route_provider(route)
        last = self._studio_last_folder
        dialog = DescribeFolderDialog(
            self.frame,  # type: ignore[attr-defined]
            choose_folder=self._studio_choose_folder,
            folder=str(last) if last else "",
            ceiling=default_ceiling(route.provider, provider),
        )
        try:
            while True:
                if self._show_modal_dialog(dialog, _FOLDER_TITLE) != _ok():  # type: ignore[attr-defined]
                    return
                choices = dialog.choices()
                if choices.folder and Path(choices.folder).is_dir():
                    break
                self._show_message_box(  # type: ignore[attr-defined]
                    "Choose a folder of pictures first.", _FOLDER_TITLE, _error_style()
                )
        finally:
            dialog.Destroy()
        folder = Path(choices.folder)
        self._studio_plan_and_run(
            folder,
            route,
            choices,
            plan_kwargs={"subfolders": choices.subfolders},
        )

    def cmd_studio_describe_folder_stop(self) -> None:
        """Stop Describing the Folder (Alt+Shift+F5): stop after the picture in hand."""
        run = self._studio_picture_run
        if run is None or run.ended:
            self._announce("No folder is being described.")  # type: ignore[attr-defined]
            return
        run.stop()
        self._announce("Stopping after the picture being described.")  # type: ignore[attr-defined]

    def _studio_run_busy(self) -> bool:
        run = self._studio_picture_run
        if run is None or run.ended:
            return False
        key = self._studio_key("studio.describe_folder_stop")
        tail = f" Press {key} to stop." if key else ""
        self._announce(f"A folder is being described: {run.status}{tail}")  # type: ignore[attr-defined]
        return True

    def _studio_plan_and_run(
        self,
        folder: Path,
        route: Any,
        choices: Any,
        *,
        plan_kwargs: dict[str, Any],
        again: bool = False,
    ) -> None:
        """Count the pictures off the UI thread, ask once, then run."""
        from quill.core.ai.picture_batch import default_results_root, plan_batch, results_folder

        settings = self._studio_run_settings(route, choices)
        results = results_folder(default_results_root(), folder)
        if again:

            def needs(_picture: Path, result: Any) -> bool:
                return result is None or not any(
                    d.same_source(
                        settings.style, settings.connection, settings.model, settings.provider
                    )
                    for d in result.descriptions
                )

            plan_kwargs = {**plan_kwargs, "needs": needs}

        def work(**_kwargs: Any) -> Any:
            return plan_batch(folder, results, ceiling=choices.ceiling, **plan_kwargs)

        def planned(_task: Any, plan: Any) -> None:
            self._studio_confirm_run(plan, route, settings, again=again)

        def failed(_task: Any, error: BaseException) -> None:
            self._announce(str(error.args[0]) if error.args else str(error))  # type: ignore[attr-defined]

        self._announce("Counting the pictures.")  # type: ignore[attr-defined]
        self._task_manager.submit(  # type: ignore[attr-defined]
            "Count the pictures in a folder",
            work,
            on_success=planned,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),  # type: ignore[attr-defined]
        )

    def _studio_confirm_run(self, plan: Any, route: Any, settings: Any, *, again: bool) -> None:
        from quill.core.ai.photo_details import details_phrase
        from quill.core.ai.picture_batch import confirmation_sentence

        self._studio_last_folder = plan.folder
        if not plan.pictures:
            self._announce(f"There are no pictures in {plan.folder.name}.")  # type: ignore[attr-defined]
            return
        if not plan.to_send:
            how = "in that style from this AI " if again else ""
            self._announce(  # type: ignore[attr-defined]
                f"Every picture in {plan.folder.name} is described {how}already. "
                "Describe Again adds a description in another style."
            )
            return
        question = confirmation_sentence(
            plan,
            route.host,
            with_what=details_phrase(details=settings.details, location=settings.location),
        )
        title = _AGAIN_TITLE if again else _FOLDER_TITLE
        answer = self._show_message_box(question, title, _question_style())  # type: ignore[attr-defined]
        if answer not in _yes():
            return
        self._studio_start_run(plan, settings)

    def _studio_start_run(self, plan: Any, settings: Any) -> None:
        from quill.ui.audio_studio.studio_picture_run import PictureRun

        run = PictureRun(self, plan, settings)
        self._studio_picture_run = run
        key = self._studio_key("studio.describe_folder_stop")
        tail = f" Press {key} to stop." if key else ""
        count = len(plan.to_send)
        noun = "picture" if count == 1 else "pictures"
        self._announce(f"Describing {count} {noun}.{tail}")  # type: ignore[attr-defined]
        run.start()

    def _studio_run_settings(self, route: Any, choices: Any) -> Any:
        from quill.ui.audio_studio.studio_picture_run import RunSettings

        return RunSettings(
            connection=route.provider,
            model=str(route.model or ""),
            provider=self._studio_route_provider(route),
            style=choices.style,
            style_title=choices.style_title,
            prompt=choices.prompt,
            details=choices.details,
            location=choices.location,
        )

    def _studio_route_provider(self, route: Any) -> str:
        if route.provider != "own_key":
            return ""
        return str(getattr(self._ai_service(), "own_key_provider", "") or "")  # type: ignore[attr-defined]

    # -- Describe Again ------------------------------------------------------------ #

    def cmd_studio_describe_again(self) -> None:
        """Describe Again (Ctrl+Alt+F5): another description beside the ones there."""
        if self._studio_run_busy():
            return
        route = self._choose_vision_connection()  # type: ignore[attr-defined]
        if route is None:
            return
        from quill.core.ai.picture_batch import (
            default_ceiling,
            default_results_root,
            load_results,
            results_folder,
        )
        from quill.ui.audio_studio.studio_picture_dialogs import DescribeAgainDialog

        targets: list[tuple[str, str, Any]] = []
        last = getattr(self, "_studio_last_picture", None)
        if last is not None:
            targets.append((f"The picture you described last, {last[2]}", "picture", None))
        folder = self._studio_last_folder
        if folder is not None:
            done = load_results(results_folder(default_results_root(), folder))
            if done:
                targets.append((f"Every picture in {folder.name}", "folder", folder))
                targets += [
                    (f"{r.relative}, in {folder.name}", "one", folder / r.relative) for r in done
                ]
        targets.append(("A folder you described before...", "choose", None))
        model = f", {route.model}" if route.model else ""
        dialog = DescribeAgainDialog(
            self.frame,  # type: ignore[attr-defined]
            targets=[label for label, _kind, _payload in targets],
            going_to=f"{route.name}{model}",
            ceiling=default_ceiling(route.provider, self._studio_route_provider(route)),
        )
        try:
            if self._show_modal_dialog(dialog, _AGAIN_TITLE) != _ok():  # type: ignore[attr-defined]
                return
            choices = dialog.choices()
        finally:
            dialog.Destroy()
        _label, kind, payload = targets[min(choices.target, len(targets) - 1)]
        if kind == "picture":
            self._studio_describe_picture_again(route, choices)
            return
        if kind == "choose":
            chosen = self._studio_choose_folder(self.frame, "")  # type: ignore[attr-defined]
            if not chosen:
                return
            payload = Path(chosen)
        if kind == "one":
            self._studio_plan_and_run(
                payload.parent if folder is None else folder,
                route,
                choices,
                plan_kwargs={"only": (payload,)},
                again=True,
            )
            return
        self._studio_plan_and_run(payload, route, choices, plan_kwargs={}, again=True)

    def _studio_describe_picture_again(self, route: Any, choices: Any) -> None:
        """The last picture described, in another style or from another AI, kept beside
        the earlier descriptions and shown together."""
        data, at, _name = self._studio_last_picture  # type: ignore[attr-defined]
        service = self._ai_service()  # type: ignore[attr-defined]
        record = service.capability_record(route.provider)
        settings = self._studio_run_settings(route, choices)
        scratch = Path(tempfile.mkdtemp(prefix="quill-studio-again-"))
        self._announce("Working.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> Any:
            from quill.core.ai.photo_details import details_line, read_photo_details
            from quill.core.ai.picture_prep import prepare_request

            prepared = prepare_request(
                [data],
                record,
                times=(at,) if at is not None else (),
                own_key_provider=settings.provider,
            )
            line = ""
            if settings.details:
                line = details_line(read_photo_details(data), location=settings.location)
            prompt = f"{line}\n\n{settings.prompt}" if line else settings.prompt
            image = prepared.images[0]
            target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
            target.write_bytes(image.data)
            return prepared, target, prompt

        def ready(_task: Any, result: Any) -> None:
            prepared, target, prompt = result
            self._studio_ask_again(prepared, target, prompt, settings, scratch)

        def failed(_task: Any, error: BaseException) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(str(error.args[0]) if error.args else str(error))  # type: ignore[attr-defined]

        self._task_manager.submit(  # type: ignore[attr-defined]
            "Prepare a picture to describe again",
            work,
            on_success=ready,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),  # type: ignore[attr-defined]
        )

    def _studio_ask_again(
        self, prepared: Any, target: Path, prompt: str, settings: Any, scratch: Path
    ) -> None:
        from quill.core.ai.picture_batch import Description, describe_label
        from quill.core.ai.picture_prep import described_by_sentence
        from quill.ui.audio_studio.studio_ai_features import _picture_cache

        label = describe_label(
            Description(
                text="",
                connection=settings.connection,
                model=settings.model,
                style=settings.style,
                style_title=settings.style_title,
                provider=settings.provider,
            )
        )
        image = prepared.images[0]
        cache = _picture_cache(self)
        cached = cache.get(image.digest, prompt, settings.connection)
        if cached is not None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._studio_show_side_by_side(label, cached, sent=False)
            return

        def done(text: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            answer = (
                f"{prepared.inspected} {described_by_sentence(settings.connection)} {text.strip()}"
            )
            cache.put(
                image.digest, prompt, answer, connection=settings.connection, prepared=prepared
            )
            self._studio_show_side_by_side(label, answer, sent=True)

        def failed(sentence: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(sentence)  # type: ignore[attr-defined]

        self._ai_service().describe_image(  # type: ignore[attr-defined]
            target, prompt, on_done=done, on_error=failed, requires=("text", "pictures")
        )

    def _studio_show_side_by_side(self, label: str, answer: str, *, sent: bool) -> None:
        answers: list[tuple[str, str]] = list(getattr(self, "_studio_last_answers", None) or [])
        if not sent:
            answer = f"{answer} Nothing was sent: this was asked already."
        answers.append((label, answer))
        self._studio_last_answers = answers
        blocks = [f"Description {n}: {lab}\n{text}" for n, (lab, text) in enumerate(answers, 1)]
        self._studio_picture_answer("\n\n".join(reversed(blocks)))  # type: ignore[attr-defined]

    # -- Save Described Copies ------------------------------------------------------ #

    def cmd_studio_save_described_copies(self) -> None:
        """Save Described Copies (Ctrl+Alt+F6): descriptions written into copies, never
        into the pictures themselves. Nothing is sent."""
        from quill.core.ai.picture_batch import default_results_root, results_folder

        last = self._studio_last_folder
        chosen = self._studio_choose_folder(
            self.frame,  # type: ignore[attr-defined]
            str(last) if last else "",
            "Choose the folder of pictures you described",
        )
        if not chosen:
            return
        folder = Path(chosen)
        results = results_folder(default_results_root(), folder)
        if not results.is_dir() or not any(results.glob("*.json")):
            self._announce(  # type: ignore[attr-defined]
                f"No descriptions were found for {folder.name}. Describe it with Describe a "
                "Folder first."
            )
            return
        target = self._studio_choose_folder(
            self.frame,  # type: ignore[attr-defined]
            "",
            "Choose where the described copies go",
        )
        if not target:
            return
        destination = Path(target)
        if destination.resolve() == folder.resolve():
            self._show_message_box(  # type: ignore[attr-defined]
                "The copies need a different folder from the pictures, so the pictures "
                "themselves are never changed. Choose another folder.",
                _COPIES_TITLE,
                _error_style(),
            )
            return
        self._studio_last_folder = folder
        self._announce("Saving described copies.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> Any:
            from quill.core.ai.picture_batch import load_results
            from quill.io.picture_metadata import write_described_copies

            return write_described_copies(load_results(results), destination)

        def done(_task: Any, outcome: Any) -> None:
            self._announce(outcome.sentence(destination.name))  # type: ignore[attr-defined]

        def failed(_task: Any, error: BaseException) -> None:
            self._announce(str(error.args[0]) if error.args else str(error))  # type: ignore[attr-defined]

        self._task_manager.submit(  # type: ignore[attr-defined]
            "Save described copies",
            work,
            on_success=done,
            on_failure=failed,
            ui_lifetime=self._demo_lifetime(),  # type: ignore[attr-defined]
        )

    # -- shared ------------------------------------------------------------------------ #

    def _studio_choose_folder(
        self, parent: Any, default: str = "", message: str = "Choose a folder of pictures"
    ) -> str | None:
        import wx

        dialog = wx.DirDialog(
            parent, message, defaultPath=default, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )
        try:
            if self._show_modal_dialog(dialog, message) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return str(dialog.GetPath())
        finally:
            dialog.Destroy()

    def _studio_key(self, command_id: str) -> str:
        try:
            return str(self._binding_for(command_id) or "")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no keymap names no key
            return ""


def _ok() -> int:
    import wx

    return int(wx.ID_OK)


def _yes() -> tuple[int, int]:
    import wx

    return int(wx.YES), int(wx.ID_YES)


def _question_style() -> int:
    import wx

    return int(wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)


def _error_style() -> int:
    import wx

    return int(wx.OK | wx.ICON_ERROR)
