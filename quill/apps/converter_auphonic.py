"""Process with Auphonic in Quill Converter: the queue's sound files, post-produced
online through the person's own Auphonic account.

The one online exception to the Converter's local-first promise, and an
explicit one (``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``):
Convert > Process with Auphonic (Ctrl+Shift+A) checks the queue -- off the UI
thread, and without the network -- opens
:class:`~quill.ui.converter_auphonic_dialog.AuphonicDialog` for the choices,
shows one confirmation naming everything that will be sent, and only then
uploads. Convert > Auphonic Work Waiting (Ctrl+Alt+A) lists productions
Auphonic accepted whose results were not fetched, and Resume fetches them.
Neither contacts Auphonic by opening, nor does launching the app.

The job is a Converter job like the others -- the same progress bar, status
line and tray tooltip, the same quarter-way announcements, the same Stop
(Ctrl+Enter), the outcome in the Conversion Report (Ctrl+R) and the folder
behind Ctrl+Shift+F. The lifecycle itself is wx-free
(:mod:`quill.core.publish.auphonic_run`) and every request goes through the
shared client (:mod:`quill.core.publish.auphonic`), the one reviewed egress
site. The API token is the family's one Auphonic credential, in the system's
credential store under :data:`~quill.core.publish.auphonic.CREDENTIAL_TARGET`
-- the same entry the Audio Studio's publish dialog reads and writes.
Unavailable in Safe Mode.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import wx

from quill.core.audio.convert import CancelToken
from quill.core.publish.auphonic_plan import (
    AuphonicChoices,
    PendingProduction,
    Skipped,
    SourceDetails,
)
from quill.core.publish.auphonic_run import said

_TITLE = "Process with Auphonic"
_log = logging.getLogger(__name__)
#: How each outcome is said when a batch reports file by file.
_STATE_WORDS = {"waiting": "still at Auphonic"}


class ConverterAuphonicMixin:
    """Process with Auphonic and Auphonic Work Waiting. Mixed into the Converter window."""

    # -- Process with Auphonic --------------------------------------------------------

    def process_with_auphonic(self) -> None:
        """Convert > Process with Auphonic (Ctrl+Shift+A)."""
        if getattr(self, "_safe_mode", False):
            self._show_message_box("Processing with Auphonic is unavailable in Safe Mode.", _TITLE)
            return
        if self._busy:
            self._announce("A job is already running.")
            return
        paths = [entry for entry, _root in self._entries]
        if not paths:
            self._show_message_box("Add the sound files to send to the queue first.", _TITLE)
            return
        self._run_background_task(
            "Checking the files for Auphonic",
            lambda _progress: inspect_files(paths),
            self._auphonic_inspected,
        )

    def _auphonic_inspected(self, inspected: Any) -> None:
        from quill.core.publish.auphonic_plan import problem
        from quill.ui.converter_auphonic_dialog import ask_choices, confirm

        eligible, skipped, details = inspected
        if not eligible:
            reasons = "\n".join(f"{item.path.name}: {item.reason}." for item in skipped)
            self._show_message_box(
                f"None of the queued files can be sent to Auphonic.\n\n{reasons}", _TITLE
            )
            return

        def why_not(choices: AuphonicChoices, token: str) -> str:
            if not token:
                return "Type or paste your Auphonic API token first."
            return problem(choices, eligible)

        answer = ask_choices(
            self,
            eligible,
            skipped=len(skipped),
            initial=self._auphonic_initial(),
            token=load_token(),
            check=start_account_check,
            problem=why_not,
        )
        if answer is None:
            self._set_status("Nothing was sent to Auphonic.")
            return
        choices, token, remember, account = answer
        self._remember_auphonic(choices)
        from quill.core.publish.auphonic_plan import confirmation_text

        dest = self._destination()
        text = confirmation_text(choices, eligible, skipped, dest, account=account)
        if not confirm(self, text):
            self._announce("Nothing was sent to Auphonic.")
            return
        if remember:
            save_token(token)
        count = len(eligible)
        label = (
            f"Sending {choices.title} to Auphonic as one multitrack production"
            if choices.mode == "multitrack"
            else f"Sending {count} file{'s' if count != 1 else ''} to Auphonic"
        )
        self._auphonic_run(
            token,
            lambda runner: runner.send(choices, eligible, dest, details=details.get),
            label,
            dest,
            skipped=skipped,
            heading=text,
        )

    def _auphonic_initial(self) -> AuphonicChoices:
        s = self._settings
        return AuphonicChoices(
            mode=s.auphonic_mode,
            preset_uuid=s.auphonic_preset,
            preset_label=s.auphonic_preset_name,
            processing=s.auphonic_processing,
            denoise=s.auphonic_denoise,
            output_format=s.auphonic_format,
        )

    def _remember_auphonic(self, choices: AuphonicChoices) -> None:
        s = self._settings
        s.auphonic_mode, s.auphonic_processing = choices.mode, choices.processing
        s.auphonic_preset, s.auphonic_preset_name = choices.preset_uuid, choices.preset_label
        s.auphonic_denoise, s.auphonic_format = choices.denoise, choices.output_format
        self._remember()

    # -- Auphonic Work Waiting --------------------------------------------------------

    def show_auphonic_work(self) -> None:
        """Convert > Auphonic Work Waiting (Ctrl+Alt+A): read locally, Resume contacts Auphonic."""
        from quill.core.publish.auphonic_plan import load_pending, pending_path, remove_pending
        from quill.ui.converter_auphonic_dialog import ask_resume

        if getattr(self, "_safe_mode", False):
            self._show_message_box("Processing with Auphonic is unavailable in Safe Mode.", _TITLE)
            return
        if self._busy:
            self._announce("A job is already running.")
            return
        store = pending_path()
        records = load_pending(store)
        if not records:
            self._announce("No Auphonic work is waiting.")
            return

        def dismiss(record: PendingProduction) -> None:
            remove_pending(store, record.uuid)
            self._announce(f"Forgot {record.title}. It is still in your Auphonic account.")

        chosen = ask_resume(self, records, dismiss=dismiss)
        if not chosen:
            return
        token = load_token()
        if not token:
            self._show_message_box(
                "Fetching these needs your Auphonic API token, and none is stored. Open "
                "Process with Auphonic, enter the token with Remember checked, cancel at "
                "the confirmation, and resume again.",
                _TITLE,
            )
            return
        noun = "production" if len(chosen) == 1 else "productions"
        self._auphonic_run(
            token,
            lambda runner: runner.resume(chosen),
            f"Fetching {len(chosen)} {noun} from Auphonic",
            Path(chosen[0].out_dir).parent,
        )

    def _note_pending_auphonic(self) -> None:
        """At launch: say pending work exists, from the local file only."""
        from quill.core.publish.auphonic_plan import load_pending, pending_path

        count = len(load_pending(pending_path()))
        if not count:
            return
        noun = "production is" if count == 1 else "productions are"
        message = f"{count} Auphonic {noun} waiting to be fetched. Press Ctrl+Alt+A to see them."
        self._set_status(message)
        wx.CallLater(1500, self._announce, message)

    # -- the run --------------------------------------------------------------------------

    def _auphonic_run(
        self,
        token: str,
        work: Any,
        label: str,
        dest: Path,
        *,
        skipped: list[Skipped] | tuple[Skipped, ...] = (),
        heading: str = "",
    ) -> None:
        from quill.core.publish.auphonic_plan import pending_path
        from quill.core.publish.auphonic_run import FAILED, Runner, RunResult

        cancel = CancelToken()
        self._begin_work(label, cancel)
        started = time.monotonic()

        def on_outcome(outcome: Any, index: int, total: int) -> None:
            if total > 1:  # one file's outcome is the final summary itself
                words = _STATE_WORDS.get(outcome.state, outcome.state)
                wx.CallAfter(self._announce, f"{index + 1} of {total}: {outcome.name}, {words}.")

        runner = Runner(
            token,
            pending_path(),
            on_progress=lambda text, fraction: wx.CallAfter(
                self._note_progress, text, int(fraction * 1000), 1000
            ),
            on_outcome=on_outcome,
            is_cancelled=cancel.is_cancelled,
        )

        def worker() -> None:
            try:
                result = work(runner)
            except Exception as error:  # noqa: BLE001 - reported in words on the UI thread
                _log.exception("Auphonic run failed")
                from quill.core.publish.auphonic_run import Outcome

                result = RunResult([Outcome(label, FAILED, f"Auphonic work failed: {said(error)}")])
            wx.CallAfter(
                self._auphonic_done,
                result,
                dest,
                list(skipped),
                heading,
                time.monotonic() - started,
            )

        threading.Thread(target=worker, daemon=True, name="converter-auphonic").start()

    def _auphonic_done(
        self, result: Any, dest: Path, skipped: list[Skipped], heading: str, seconds: float
    ) -> None:
        from quill.core.publish.auphonic_run import SAVED

        self._end_work()
        summary = result.summary()
        if skipped:
            summary += (
                f" {len(skipped)} queued item{'s were' if len(skipped) != 1 else ' was'} not sent."
            )
        saved = [item for item in result.outcomes if item.state == SAVED and item.files]
        if len(result.outcomes) > 1 or any(item.state != SAVED for item in result.outcomes):
            summary += " Press Ctrl+R for the report."
        open_now = bool(saved) and self._settings.open_folder_when_done
        if saved and not open_now:
            summary += " Ctrl+Shift+F opens the folder."
        lines = [
            f"Auphonic report, {time.strftime('%Y-%m-%d %H:%M')}",
            f"Took {int(seconds)} seconds.",
            result.summary(),
            "",
            *result.report_lines(),
        ]
        if skipped:
            lines += ["", "Not sent:"] + [f"  {item.path.name}: {item.reason}." for item in skipped]
        if heading:
            lines += ["", "What was confirmed:", heading]
        self._last_report = "\n".join(lines)
        if len(saved) == 1 and saved[0].files:
            self._last_output = saved[0].files[0].parent
        else:
            self._last_output = dest
        self._set_status(summary)
        self._announce(summary, force=True)
        if open_now:
            self.open_output_folder()


# -- wx-free helpers (module level so tests can replace them) ----------------------------


def inspect_files(paths: list[Path]) -> tuple[list[Path], list[Skipped], dict[Path, SourceDetails]]:
    """Which queued files may be sent, and what each passes through. No network.

    ffprobe answers whether a file holds a moving picture (a cover image does
    not count) and reads its title, artist, album and chapters; without
    ffprobe, the extension decides and Auphonic reads the file's own tags.
    """
    from quill.core.audio.media_probe import probe
    from quill.core.publish.auphonic_plan import ACCEPTED_EXTENSIONS, check_inputs

    found: dict[Path, Any] = {}

    def has_video(path: Path) -> bool:
        info = probe(path)
        found[path] = info
        return any(stream.kind == "video" for stream in info.streams)

    candidates = [p for p in paths if p.suffix.lower() in ACCEPTED_EXTENSIONS]
    eligible, skipped = check_inputs(paths, has_video=has_video if candidates else None)
    details: dict[Path, SourceDetails] = {}
    for path in eligible:
        info = found.get(path)
        if info is None:
            continue
        tags = info.tags
        details[path] = SourceDetails(
            title=tags.get("title", ""),
            artist=tags.get("artist", ""),
            album=tags.get("album", ""),
            chapters=tuple((chapter.start_s, chapter.title) for chapter in info.chapters),
        )
    return eligible, skipped, details


def check_account(token: str) -> tuple[list[Any], Any]:
    """The account check: presets and credits. Never uploads anything."""
    from quill.core.publish import auphonic

    return auphonic.list_presets(token), auphonic.account_info(token)


def start_account_check(token: str, deliver: Any) -> None:
    """Run :func:`check_account` off the UI thread; ``deliver(presets, info, error)`` on it."""

    def worker() -> None:
        try:
            presets, info = check_account(token)
        except Exception as error:  # noqa: BLE001 - said in words on the UI thread
            wx.CallAfter(deliver, None, None, said(error))
            return
        wx.CallAfter(deliver, presets, info, "")

    threading.Thread(target=worker, daemon=True, name="converter-auphonic-check").start()


def load_token() -> str:
    """The family's one stored Auphonic token, or ``""``."""
    try:
        from quill.core.publish.auphonic import CREDENTIAL_TARGET
        from quill.platform.windows.credential_manager import load_generic_credential

        credential = load_generic_credential(CREDENTIAL_TARGET)
    except Exception:  # noqa: BLE001 - no credential store here
        return ""
    return (credential.secret or "").strip() if credential is not None else ""


def save_token(token: str) -> None:
    """Store *token* where the Audio Studio keeps it too (never in settings or logs)."""
    try:
        from quill.core.publish.auphonic import CREDENTIAL_TARGET
        from quill.platform.windows.credential_manager import save_generic_credential

        save_generic_credential(CREDENTIAL_TARGET, token, user_name="auphonic")
    except Exception:  # noqa: BLE001 - the run goes on; the token is just not remembered
        _log.warning("Could not store the Auphonic token in the credential manager")
