"""One Describe a Folder run in QUILL Studio, one picture at a time, stoppable.

The plan and the words are :mod:`quill.core.ai.picture_batch`; this drives it.
Each picture goes the way Describe a Picture's one picture goes: read and
fitted to the connection off the UI thread (:mod:`quill.core.ai.picture_prep`,
through the task manager), then sent through the shared service's
``describe_image``, which asks the capability gate again before anything
leaves. Its result is kept off the UI thread too, before the next picture
starts, so a run that stops -- by Stop, a failed request or Studio closing --
has kept everything it was sent.

Progress is said now and then as counts, never once per picture; the end is
one sentence, and the document of every description opens in QUILL.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["PictureRun", "RunSettings"]


@dataclass(frozen=True, slots=True)
class RunSettings:
    """How every picture in one run is described."""

    connection: str
    model: str
    provider: str
    style: str
    style_title: str
    prompt: str
    details: bool
    location: bool


class PictureRun:
    """One run over a :class:`~quill.core.ai.picture_batch.BatchPlan`.

    *host* is QUILL Studio's frame: ``_task_manager``, ``_ai_service()``,
    ``_announce``, ``_demo_lifetime()`` and ``open_in_quill``.
    """

    def __init__(self, host: Any, plan: Any, settings: RunSettings, *, on_end: Any = None) -> None:
        from quill.core.ai.picture_batch import ProgressCounter

        self._host = host
        self.plan = plan
        self.settings = settings
        self._queue = list(plan.to_send)
        self._index = 0
        self._progress = ProgressCounter(len(self._queue))
        self._skipped: list[str] = []
        self._task: Any = None
        self._lifetime = host._demo_lifetime()
        self._scratch = Path(tempfile.mkdtemp(prefix="quill-studio-folder-"))
        self._on_end = on_end
        self.stopping = False
        self.ended = False
        self._error = ""

    # -- the outside ------------------------------------------------------------ #

    @property
    def status(self) -> str:
        return f"{self._progress.finished} of {len(self._queue)} described."

    def start(self) -> None:
        self._next()

    def stop(self) -> None:
        """Stop after the picture in hand: a request already sent is kept, not lost."""
        if self.ended:
            return
        self.stopping = True
        task = self._task
        if task is not None:
            try:
                task.cancellation_token.cancel()
            except Exception:  # noqa: BLE001 - a finished task has nothing to cancel
                pass

    # -- one picture -------------------------------------------------------------- #

    def _alive(self) -> bool:
        return bool(getattr(self._lifetime, "is_alive", True))

    def _next(self) -> None:
        if self.stopping or self._index >= len(self._queue):
            self._finish()
            return
        picture = self._queue[self._index]
        self._index += 1
        service = self._host._ai_service()
        record = service.capability_record(self.settings.connection)
        settings = self.settings
        scratch = self._scratch

        def work(*, cancellation_token: Any = None, **_kwargs: Any) -> Any:
            from quill.core.ai.photo_details import details_line, read_photo_details
            from quill.core.ai.picture_batch import read_picture
            from quill.core.ai.picture_prep import prepare_request

            data = read_picture(picture)
            details = read_photo_details(data)
            prepared = prepare_request([data], record, own_key_provider=settings.provider)
            image = prepared.images[0]
            target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
            target.write_bytes(image.data)
            line = details_line(details, location=settings.location) if settings.details else ""
            prompt = f"{line}\n\n{settings.prompt}" if line else settings.prompt
            return picture, target, prompt, details, bool(line)

        self._task = self._host._task_manager.submit(
            "Prepare a picture to describe",
            work,
            on_success=lambda _t, result: self._prepared(*result),
            on_failure=lambda _t, error: self._unreadable(picture, error),
            ui_lifetime=self._lifetime,
        )

    def _unreadable(self, picture: Path, error: BaseException) -> None:
        from quill.core.ai.picture_batch import BatchError
        from quill.core.ai.picture_prep import PicturePrepError

        if self.stopping:
            self._finish()
            return
        if not isinstance(error, (BatchError, PicturePrepError)):
            self._error = str(error.args[0]) if error.args else str(error)
            self._finish()
            return
        self._skipped.append(picture.name)
        self._said(self._progress.step(skipped=True))
        self._next()

    def _prepared(self, picture: Path, target: Path, prompt: str, details: Any, sent: bool) -> None:
        if self.stopping:
            self._finish()
            return

        def done(text: str) -> None:
            if self._alive():
                self._keep(picture, text, details, sent)

        def failed(sentence: str) -> None:
            if self._alive():
                self._error = sentence
                self._finish()

        self._host._ai_service().describe_image(
            target, prompt, on_done=done, on_error=failed, requires=("text", "pictures")
        )

    def _keep(self, picture: Path, text: str, details: Any, sent: bool) -> None:
        from quill.core.ai.photo_details import spoken_date
        from quill.core.ai.picture_batch import (
            Description,
            load_result,
            new_result,
            result_path,
            save_result,
            with_description,
        )

        plan, settings = self.plan, self.settings
        description = Description(
            text=text.strip(),
            connection=settings.connection,
            model=settings.model,
            style=settings.style,
            style_title=settings.style_title,
            provider=settings.provider if settings.connection == "own_key" else "",
            at=datetime.now().isoformat(timespec="seconds"),
            details_sent=sent,
            location_sent=sent and settings.location and bool(details.has_location),
        )

        def work(**_kwargs: Any) -> None:
            path = result_path(plan.results, plan.folder, picture)
            result = load_result(path)
            if result is None or not result.matches(picture):
                result = new_result(
                    plan.folder,
                    picture,
                    taken=spoken_date(details.taken) if details.taken else "",
                    camera=details.camera,
                    lens=details.lens,
                )
            save_result(path, with_description(result, description))

        def kept(_task: Any, _result: Any) -> None:
            self._said(self._progress.step())
            self._next()

        def lost(_task: Any, error: BaseException) -> None:
            self._error = str(error.args[0]) if error.args else str(error)
            self._finish()

        self._task = self._host._task_manager.submit(
            "Keep a picture description",
            work,
            on_success=kept,
            on_failure=lost,
            ui_lifetime=self._lifetime,
        )

    # -- the end ------------------------------------------------------------------ #

    def _said(self, sentence: str) -> None:
        if sentence:
            self._host._announce(sentence)

    def _finish(self) -> None:
        if self.ended:
            return
        self.ended = True
        shutil.rmtree(self._scratch, ignore_errors=True)
        plan = self.plan
        described = self._progress.described
        left = len(plan.pending) - described - len(self._skipped)
        stopped = self.stopping or bool(self._error)

        def work(**_kwargs: Any) -> Path | None:
            from quill.core.ai.picture_batch import load_results, write_document

            if not load_results(plan.results):
                return None
            return write_document(plan.results, plan.folder)

        def written(_task: Any, document: Path | None) -> None:
            from quill.core.ai.picture_batch import finished_sentence

            sentence = finished_sentence(described, self._skipped, left=left, stopped=stopped)
            if self._error:
                sentence = f"{self._error} {sentence}"
            if document is not None and described and not stopped:
                sentence += " The descriptions open in QUILL."
                self._host._announce(sentence)
                self._host.open_in_quill(str(document))
            else:
                if document is not None and described:
                    sentence += f" What was described is in {document.name}."
                self._host._announce(sentence)
            self._ended()

        def unwritten(_task: Any, error: BaseException) -> None:
            message = str(error.args[0]) if error.args else str(error)
            self._host._announce(message)
            self._ended()

        self._host._task_manager.submit(
            "Write the picture descriptions",
            work,
            on_success=written,
            on_failure=unwritten,
            ui_lifetime=self._lifetime,
        )

    def _ended(self) -> None:
        if callable(self._on_end):
            self._on_end(self)
