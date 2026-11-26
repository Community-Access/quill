"""What the Scribe queue runner reports, and what is said about it (PRD 7.4a).

A mixin of :class:`quill.ui.scribe_controller.ScribeController`, kept apart so
each module stays under the 600-line cap (GATE-11). It uses the controller's
queue, host, options, speaker, window and ``_say``.

* **One announcer.** Only the app holding the runner lock speaks.
* **Watch-folder jobs are said by the watch folder** (``open_as == "watch"``):
  their outcome is the watch result, said the way every watch result is, so
  the controller says nothing for them and nothing is said twice (8.1.6).
* **The streaming tab** (8.1.3) gets every chunk of its job, and is told when
  the stream has ended and when the job finishes; its completion is part of
  the one result sentence, never a second message.
* **How each moment is told is the person's choice** (:mod:`quill.core.
  scribe.feedback`): started, each stage, finished, and failed or needs you,
  each a sound, words, both or neither. By default nothing is spoken here --
  progress is read in the Conversions window and Scribe Status -- and the end
  of a job is a sound, a different one for success and for failure. Whatever
  is chosen, the sentence is still built: it goes to the status bar (quietly)
  and to Repeat Last Scribe Message, and a finished or failed one to
  Notifications too, so a missed sound never loses the result (FUX-04). Words,
  when chosen, go through the app's announcement service, so braille gets
  them as well.
* **A named set is told once** (:mod:`quill.core.scribe.sets`): its
  documents' starts, results and failures are not told one by one -- they
  are in the set's log and the Conversions window -- and ``set_done``, when
  the last of them has finished, is the set's one cue and one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.feedback import Moment, plan
from quill.core.sound_events import SoundEvent

#: Job ``open_as`` values with their own speakers or openers.
WATCH = "watch"
STREAM = "stream"

#: The sounds this module plays (named here so the sound-event audit sees
#: them posted; which one is :data:`~quill.core.scribe.feedback.MOMENT_SOUNDS`,
#: and stages use the progress ladder).
SOUNDS = (
    SoundEvent.SCRIBE_STARTED,
    SoundEvent.SCRIBE_FINISHED,
    SoundEvent.SCRIBE_FAILED,
    SoundEvent.PROGRESS_TICK,
)


class ScribeEventsMixin:
    """The runner's events, on the controller."""

    host: Any
    app_name: str
    queue: Any
    holding: bool
    _speaker: Any
    _window: Any
    _chunk_listeners: dict[str, Callable[[str], None]]
    _background: Callable[..., None]
    _last_sentence: str

    def _scribe_window_in_front(self) -> bool:  # the controller answers
        return False

    # ------------------------------------------------------------ telling

    def _tell(
        self,
        moment: Moment,
        text: str,
        *,
        percent: int = 0,
        cue: bool = True,
        stall: bool = False,
        failed: bool = False,
    ) -> None:
        """Tell *text* about *moment* the way the person chose (see the notes).

        *percent* is a milestone just crossed (its step on the progress
        ladder); *cue* False for a sentence that follows one that already had
        its sound (the batch summary after the last file's result); *stall*
        for busy and offline, which explain a job that is not moving and so go
        to the status bar like a result, though they are stage moments;
        *failed* for a set that ended with a document not made (its sound is
        the failure sound, and its notice an error).

        **A result is not overwritten by what follows it.** In a batch the
        next file starts the moment one finishes, so a start or a stage that
        nobody heard must not replace the result in the status bar or in
        Repeat Last Scribe Message: only finished and failed sentences, and
        sentences actually spoken, become the last message.
        """
        if not text:
            return
        delivery = plan(
            self.options().feedback,
            moment,
            has_sound=self._has_sound,
            scribe_window_in_front=self._scribe_window_in_front(),
            percent=percent,
            failed=failed,
        )
        ending = moment in (Moment.FINISHED, Moment.FAILED, Moment.SET_FINISHED)
        if ending or delivery.speak:
            self._last_sentence = text
        if ending or stall or (delivery.speak and moment is Moment.STARTED):
            self._show_status(text)
        if ending:
            self._record_notice(text, failed=moment is Moment.FAILED or failed)
        if delivery.sound and cue:
            self._cue(delivery.sound)
        if delivery.speak:
            self.host.scribe_announce(text)

    def _has_sound(self, event: str) -> bool:
        """Whether *event* can be heard now. With the app's sounds turned off
        altogether this is False, so a "Play a sound" moment is spoken instead:
        somebody who keeps sounds off must not get silence at the end of a
        conversion. One event switched off in Sound Scheme is that person's
        decision about that sound, and stays silent (the family rule)."""
        has = getattr(self.host, "scribe_has_sound", None)
        if callable(has):
            return bool(has(event))
        try:
            from quill.ui import sound_manager

            return bool(sound_manager.is_active() and sound_manager.has_sound_for(event))
        except Exception:  # noqa: BLE001 - no sound stack means no sound
            return False

    def _cue(self, event: str) -> None:
        """Through the app's sound scheme: its volume, its App Sounds device,
        the sound switch and each event's own off switch all apply."""
        play = getattr(self.host, "scribe_cue", None)
        if callable(play):
            play(event)
            return
        from quill.ui.companion_cues import post_cue

        post_cue(event)

    def _show_status(self, text: str) -> None:
        """In the status bar, never spoken: the reader can arrow back to it."""
        show = getattr(self.host, "scribe_status_text", None)
        if callable(show):
            try:
                show(text)
            except Exception:  # noqa: BLE001 - a status cell is never worth the queue
                pass

    def _record_notice(self, text: str, *, failed: bool) -> None:
        """Kept in Notifications, where a missed sound can be read later."""
        try:
            from quill.core.notifications import add_notice

            add_notice(
                app=self.app_name,
                title=PRODUCT_NAME,
                body=text,
                category="error" if failed else "info",
            )
        except (OSError, ValueError):
            pass

    def add_chunk_listener(self, job_id: str, listener: Callable[[str], None]) -> None:
        """Streamed HTML for *job_id* (the read-while-it-converts tab, 8.1.3)."""
        self._chunk_listeners[job_id] = listener

    def add_job_listener(self, job_id: str, listener: Callable[[str, q.Job], None]) -> None:
        """``stream_done``, ``done`` and ``error`` for *job_id*, on the UI thread."""
        listeners: dict[str, Callable[[str, q.Job], None]] = self.__dict__.setdefault(
            "_job_listeners", {}
        )
        listeners[job_id] = listener

    def _tell_job_listener(self, kind: str, job: q.Job) -> None:
        listener = self.__dict__.get("_job_listeners", {}).get(job.id)
        if listener is not None:
            try:
                listener(kind, job)
            except Exception:  # noqa: BLE001 - a closed tab must not stop the queue's speech
                self.__dict__["_job_listeners"].pop(job.id, None)

    def _on_event(self, kind: str, job: q.Job | None) -> None:
        """On the UI thread: refresh the window, then say what 7.4a allows."""
        if kind == "chunk" and job is not None:
            listener = self._chunk_listeners.get(job.id)
            if listener is not None:
                listener(job.message)
            return
        if kind == "stream_done" and job is not None:
            self._tell_job_listener(kind, job)
            return
        if self._window is not None:
            self._window.refresh(job.id if job is not None else "")
        if job is not None and kind in ("done", "error"):
            self._tell_job_listener(kind, job)
        if not self.holding or job is None:
            return
        if job.open_as == WATCH and kind != "closed_while":
            return  # the watch folder says its own results (8.1.6)
        if kind == "set_done":
            self._set_finished(job.batch)
            return
        if kind in ("started", "done", "error") and self._in_set(job):
            return  # a set is told once, when all of it is done
        if kind == "started":
            self._tell(Moment.STARTED, say.start_sentence(job))
        elif kind == "changed":
            self._stage_changed(job)
        elif kind == "done":
            self._finished(job)
            self._batch_finished(job)
        elif kind == "error":
            if job.error_code == "QUILL-SCRIBE-PAGES":
                self._tell(Moment.FAILED, say.error_sentence(job, say.pages_sentence(job.message)))
            elif job.error_code in ("QUILL-SCRIBE-NOTDOC", "QUILL-SCRIBE-TOOBIG"):
                self._tell(Moment.FAILED, job.message)  # already names Scribe and the file
            else:
                self._tell(Moment.FAILED, say.error_sentence(job, job.message))
            self._batch_finished(job)
        elif kind == "needs_you":
            marker = (job.id, job.state)
            if marker not in self._said_needs_you:
                self._said_needs_you.add(marker)
                self._tell(Moment.FAILED, say.needs_you_sentence(job, app_name=self.app_name))
        elif kind == "busy" and self._speaker.once(job, "busy"):
            self._tell(Moment.STAGE, say.busy_sentence(self.app_name), stall=True)
        elif kind == "offline" and self._speaker.once(job, "offline"):
            self._tell(Moment.STAGE, say.offline_sentence(job, app_name=self.app_name), stall=True)
        elif kind == "online":
            self._speaker.forget(job.id, "offline")  # recovery is silent
        elif kind == "closed_while":
            titles = [t for t in job.title.split("|") if t]
            if titles:
                from quill.core.scribe.library import default_download_root

                root = self.options().download_folder or str(default_download_root())
                self._tell(
                    Moment.FINISHED,
                    say.closed_while_sentence(titles, app_name=self.app_name, folder=root),
                )

    def _stage_changed(self, job: q.Job) -> None:
        """A stage or a milestone, each once (the speaker decides which); a
        milestone plays its own step of the progress ladder."""
        before = self._speaker.progress_of(job.id)
        sentence = self._speaker.on_change(job, app_in_front=True)
        self._tell(Moment.STAGE, sentence, percent=say.milestone_crossed(before, job.progress) or 0)

    def _in_set(self, job: q.Job) -> bool:
        try:
            return bool(job.batch) and self.queue.get_set(job.batch) is not None
        except (OSError, TimeoutError):
            return False

    def _set_finished(self, set_id: str) -> None:
        """The one cue and sentence for a whole set: the failure sound if any
        document was not made."""
        from quill.core.scribe import sets

        try:
            batch_set = self.queue.get_set(set_id)
            jobs = self.queue.batch_jobs(set_id)
        except (OSError, TimeoutError):
            return
        if batch_set is None or not jobs:
            return
        _done, failed, _working = sets.set_counts(jobs)
        self._tell(
            Moment.SET_FINISHED,
            sets.set_finished_sentence(batch_set, jobs),
            failed=bool(failed),
        )

    def _batch_finished(self, job: q.Job) -> None:
        """After the last file of a batch: what was made and what was not (7.4).
        A named set is told by ``set_done`` instead."""
        if not job.batch or self._in_set(job):
            return
        try:
            jobs = self.queue.batch_jobs(job.batch)
        except (OSError, TimeoutError):
            return
        if len(jobs) > 1 and all(j.state in q.FINISHED for j in jobs):
            if self._speaker.once(q.Job(id=job.batch), "batch"):
                # The last file's own result already had its sound.
                self._tell(Moment.FINISHED, say.batch_sentence(jobs), cue=False)

    def _finished(self, job: q.Job) -> None:
        """The one result sentence; open the result only where 7.4a allows."""
        # A step the app takes on the result first (Studio's chapter markers),
        # off the UI thread, and said inside the one result sentence rather
        # than after it (8.5).
        finish = getattr(self.host, "scribe_finish_job", None)
        if job.app == self.app_name and callable(finish):
            self._background(
                lambda: finish(job),
                lambda note: self._say_result(job, str(note or "")),
                lambda _error: self._say_result(job, ""),
            )
            return
        self._say_result(job, "")

    def _say_result(self, job: q.Job, note: str) -> None:
        options = self.options()
        opened = ""
        mine = job.app == self.app_name
        # An app whose results open in another app, or in a modal window, never
        # opens one by itself: the other app coming to the front would cut the
        # result sentence off, and a background job must not open a dialog (7.4a).
        on_its_own = bool(getattr(self.host, "scribe_opens_on_its_own", True))
        if mine and job.open_as == STREAM:
            # The streaming tab is already open: say it is complete (8.1.3).
            finished = getattr(self.host, "scribe_stream_finished", None)
            opened = finished(job) if callable(finished) else ""
        elif mine and on_its_own and options.open_results == "yes" and self._may_open_now():
            opened = self.open_job_result(job, speak=False)
        from quill.core.scribe.results import result_notes

        self._tell(
            Moment.FINISHED,
            say.result_sentence(
                job,
                app_name=self.app_name,
                opened=opened,
                offer=options.open_results == "offer",
                note=note,
                # the pictures, a Kindle book, an EPUB nothing here reads: once
                after=" ".join(n for n in (result_notes(job.outputs), self._host_note(job)) if n),
            ),
        )

    def _may_open_now(self) -> bool:
        """In front, and (for an app that says so) no dialog open, nothing playing."""
        if not self.host.scribe_in_front():
            return False
        may = getattr(self.host, "scribe_may_open_now", None)
        return bool(may()) if callable(may) else True

    def open_job_result(
        self, job: q.Job, *, speak: bool = True, browser: bool | None = None
    ) -> str:
        """Open Result: the first output that opens somewhere, in the tool where it
        is used (section 9). A tagged PDF, MOBI or offline page is only saved, so
        a BRF or MP3 made with it still opens. The accessible HTML is what opens
        in the editor; the offline page is a Next Step, in the browser (F2).

        The tagged PDF, and the offline page when it is all that opens, open
        only on a command the person chose (*browser*, which is *speak*
        unless given); the offline page opens in the browser:
        never in the editor, where each embedded picture would be one long
        line of base64. A result opened by itself never starts the browser."""
        from quill.core.scribe.results import ON_COMMAND_ONLY, browser_page, open_order
        from quill.core.scribe.sentences import friendly_folder

        chosen = speak if browser is None else browser
        saved = False
        for format_id, path in open_order(job.outputs):
            if not path.exists():
                continue
            saved = True
            if format_id in ON_COMMAND_ONLY and not chosen:
                continue  # the tagged PDF opens on the person's command only
            said = self.host.scribe_open_result(job, format_id, path)
            if said:
                if speak:
                    self._say(said + ".")
                return said
        page = browser_page(job.outputs)
        if page is not None and chosen:
            from quill.ui import scribe_entry
            from quill.ui.scribe_after_sentence import browser_opening

            said = "Opening the Web page for offline reading in your browser"
            hold = getattr(self.host, "scribe_hold", None)
            if callable(hold):  # the browser comes to the front after the sentence
                hold(browser_opening(page, self.host.scribe_announce), said)
            elif not scribe_entry.open_in_browser(page):
                said = ""
            if said:
                if speak:
                    self._say(said + ".")
                return said
        if speak and saved:
            where = friendly_folder(job.folder) if job.folder else "its folder"
            note = self._host_note(job)
            self._say(
                f"{job.display_name} was saved in {where}. Open Folder shows it."
                + (f" {note}" if note else "")
            )
        elif speak:
            self._say(f"{job.display_name} has no result to open yet.")
        return ""

    def _host_note(self, job: q.Job) -> str:
        """What the app alone knows about a result it cannot open (QUILL Lite
        and an EPUB), said once inside the result sentence."""
        note = getattr(self.host, "scribe_result_note", None)
        return str(note(job) or "") if callable(note) else ""

    # ---------------------------------------------------------- next steps

    def next_steps(self, job: q.Job) -> list[tuple[str, Callable[[], None]]]:
        """What can be done with *job*'s finished outputs (8.1.7): each a separate
        command the person chooses, offered by the app. Never run on their own."""
        offer = getattr(self.host, "scribe_next_steps", None)
        if not callable(offer):
            return []
        from quill.core.scribe.results import open_order

        ready = {format_id: path for format_id, path in open_order(job.outputs) if path.exists()}
        return list(offer(job, ready)) if ready else []


__all__ = ["STREAM", "WATCH", "ScribeEventsMixin"]
