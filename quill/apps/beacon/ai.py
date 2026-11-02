"""QuillBeacon reaches the family's AI through the shared small-app adapter.

codex.md Phase 3 (10E.11, 10B.5, 10C.3). Beacon's Assist menu had three local
helpers and no AI. They stay, and stay first; after them, behind a separator,
come the shared hosted AI's rows, run through
:class:`~quill.ui.hosted_ai_app_adapter.AppAiMixin` with Beacon's own
"QUILL Beacon" sign-in -- Choose Your AI, Which AI Am I Using, the one AI Usage
list, the AI line at the foot of the results pane and Safe Mode's refusal all
come from the code every app shares. No new top-level menu.

What Beacon *does* with AI is :class:`BeaconAiFeaturesMixin`:

* **Ask** (Ctrl+6, Assist > Ask...) about what is in front of you: the search
  and its results' titles and notes when a search is typed, else the selected
  beacon's title, note and tags (``app_ask_context.beacon_context``). Never the
  library's location or any file path.
* **Describe a Saved Picture** (Ctrl+F5): the selected beacon's picture -- an
  image attachment, or the saved screenshot the beacon points at. The words in
  it are read on this computer first (Windows OCR, when it is there); then the
  capability gate, then the first-time picture consent, then the picture is
  fitted and sent once (10B.2). The answer is shown, then offered as a note in
  one Yes/No, No the default. A connection that cannot see, when the person
  does not switch, gets the words read on this computer and nothing is sent.
* **Organize What I Saved...** (Ctrl+3): the agent task
  (:mod:`quill.apps.beacon.ai_task`): search, read, tag and move saved items,
  each change shown as text and made only on Apply, one Ctrl+Z each.

**Keys (decision 14).** Beacon has no Window menu and no Ctrl+digit key, so the
editors' Ctrl+6, Ctrl+8 and Ctrl+4 hold (``APP_KEYMAPS["beacon"]``).

**Not a shell app.** ``BeaconFrame`` is a plain ``wx.Frame``: the adapter treats
it as its own frame, reads keys from ``APP_KEYMAPS``, keeps menu ids on the
frame and reads Safe Mode from ``_safe_mode`` or the command line. Beacon has
no task manager, so the one background job here (reading the picture and its
words) runs on the family's ``thread_submit`` and comes back with
``wx.CallAfter``, as Beacon's capture bridge does. Nothing runs on a timer.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.ui.hosted_ai_app_adapter import AppAiMixin

__all__ = [
    "AGENT_NAME",
    "AI_ROWS",
    "DESCRIBE_TITLE",
    "LOCAL_TITLE",
    "BeaconAiFeaturesMixin",
    "BeaconAiMixin",
]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Beacon"
DESCRIBE_TITLE = "Describe a Saved Picture"
LOCAL_TITLE = "Read on This Computer"
NOTE_CAPTION = "Add to Note"

#: The AI rows appended to the Assist menu, after its three local helpers
#: (Suggest &Tags, Suggest &Relationships, &Summarize Note): command id, label,
#: handler name; "" is a separator. Letters are unique within Assist
#: (T R S, then A W C D G H O I P).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("", "", ""),
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("beacon.describe_picture", "&Describe a Saved Picture...", "cmd_beacon_describe_picture"),
    ("tools.hosted_ai_task", "Or&ganize What I Saved...", "cmd_ai_task"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "A&I Usage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)

_PICTURE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"})


def _local_path(uri: str) -> Path | None:
    """A file on this computer named by *uri* (a path or a file: URL), or None."""
    if not uri:
        return None
    if uri.lower().startswith("file:"):
        from urllib.parse import urlparse
        from urllib.request import url2pathname

        return Path(url2pathname(urlparse(uri).path))
    if "://" in uri:
        return None
    return Path(uri)


def _is_picture(uri: str, mime: str = "") -> bool:
    if mime.lower().startswith("image/"):
        return True
    path = _local_path(uri)
    return path is not None and path.suffix.lower() in _PICTURE_SUFFIXES


def _ocr_text(path: Path) -> str:
    """The words Windows OCR reads in *path*; nothing when it is not there or fails."""
    try:
        from quill.io.ocr import ocr_image

        return str(ocr_image(path).text or "").strip()
    except Exception:  # noqa: BLE001 - OCR is a help, never a requirement
        return ""


class BeaconAiFeaturesMixin:
    """Describe a Saved Picture and what Ask reads. Mixed in through ``BeaconAiMixin``."""

    # -- Describe a Saved Picture ------------------------------------------------ #

    def cmd_ai_task(self) -> None:
        """Organize What I Saved (Ctrl+3, codex.md 6.10): search, read, tag and move
        saved items in the shared agent window. Each tag or move is shown as text
        and waits for Apply; nothing is deleted, opened or published."""
        from quill.apps.beacon.ai_task import (
            INSTRUCTION_HELP,
            ORGANIZE,
            beacon_task_facts,
            beacon_task_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            ORGANIZE,
            lambda ctx: beacon_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            context=lambda: beacon_task_facts(self),
        )

    def cmd_beacon_describe_picture(self) -> None:
        """Describe a Saved Picture (Ctrl+F5): OCR here first, then one picture sent."""
        if not self._ai_switched_on():  # type: ignore[attr-defined]  # Safe Mode
            return
        beacon = self._selected_beacon()  # type: ignore[attr-defined]
        if beacon is None:
            self._announce("Select a beacon first")  # type: ignore[attr-defined]
            return
        path, missing = self._beacon_picture_path(beacon)
        if path is None:
            self._announce(  # type: ignore[attr-defined]
                "This beacon's picture is not on this computer any more. Nothing was sent."
                if missing
                else "This beacon has no saved picture. Nothing was sent."
            )
            return
        beacon_id = beacon.beacon_id
        self._announce("Reading the picture on this computer.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> tuple[bytes, str]:
            return path.read_bytes(), _ocr_text(path)

        def read(_name: str, result: Any) -> None:
            data, words = result
            self._beacon_ai_call_after(self._beacon_picture_read, beacon_id, data, words)

        def failed(_name: str, error: BaseException) -> None:
            message = str(error.args[0]) if error.args else str(error)
            self._beacon_ai_call_after(
                self._announce,  # type: ignore[attr-defined]
                f"The picture could not be read: {message}",
            )

        self._beacon_ai_submit("beacon-read-picture", work, read, failed)

    def _beacon_picture_path(self, beacon: Any) -> tuple[Path | None, bool]:
        """The beacon's picture on disk: its newest image attachment, else the
        saved file it points at. ``(None, True)`` when one is named but gone."""
        store = self.store  # type: ignore[attr-defined]
        named: list[str] = [
            att.uri
            for att in reversed(store.attachments_for(beacon.beacon_id))
            if att.kind == "file" and _is_picture(att.uri, att.mime)
        ]
        res = store.get_resource(beacon.resource_id) if beacon.resource_id else None
        if res is not None and _is_picture(res.primary_uri, res.mime):
            named.append(res.primary_uri)
        for uri in named:
            path = _local_path(uri)
            if path is not None and path.is_file():
                return path, False
        return None, bool(named)

    def _beacon_picture_read(self, beacon_id: str, data: bytes, words: str) -> None:
        """Back on the UI thread with the picture and its words: gate, consent, send."""
        if not self:  # the window closed while the picture was read
            return
        if not self._ai_capable("pictures"):  # type: ignore[attr-defined]
            self._beacon_words_only(beacon_id, words)
            return
        if not self._ai_ready():  # type: ignore[attr-defined]
            return
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = str(service.connection_in_use or "")
        if not ask_picture_consent(self, connection):
            self._announce("Nothing was sent.")  # type: ignore[attr-defined]
            return
        self._beacon_describe_bytes(beacon_id, data, words, connection)

    def _beacon_words_only(self, beacon_id: str, words: str) -> None:
        """The connection cannot see and nothing was switched: the OCR words alone."""
        service = self._ai_service()  # type: ignore[attr-defined]
        if not getattr(service, "connection_in_use", "") or service.can_do("pictures"):
            return  # no AI in use (Choose Your AI opened), or nothing to fall back from
        if getattr(self, "_ai_windows", {}).get("choose"):
            return  # Choose Your AI is open on the row that can; it has the focus
        if not words:
            self._announce(  # type: ignore[attr-defined]
                "No words were read in the picture on this computer. Nothing was sent."
            )
            return
        self._beacon_picture_answer(
            beacon_id, f"Nothing was sent. Words read on this computer: {words}", LOCAL_TITLE
        )

    def _beacon_describe_bytes(
        self, beacon_id: str, data: bytes, words: str, connection: str
    ) -> None:
        """Fit the picture to the connection, answer from the cache or ask once."""
        import shutil
        import tempfile

        from quill.core.ai.app_requests import beacon_picture_question
        from quill.core.ai.connection_caps import CapabilityMissing
        from quill.core.ai.picture_prep import (
            PicturePrepError,
            described_by_sentence,
            prepare_request,
        )

        service = self._ai_service()  # type: ignore[attr-defined]
        try:
            prepared = prepare_request([data], service.capability_record(connection))
        except (PicturePrepError, CapabilityMissing) as error:
            self._announce(str(error.args[0]) if error.args else str(error))  # type: ignore[attr-defined]
            return
        question = beacon_picture_question(words)
        image = prepared.images[0]
        cache = self._beacon_picture_cache()
        cached = cache.get(image.digest, question, connection)
        if cached is not None:
            self._beacon_picture_answer(
                beacon_id,
                f"{cached} Nothing was sent: this picture was asked about already.",
                DESCRIBE_TITLE,
            )
            return
        scratch = Path(tempfile.mkdtemp(prefix="quill-beacon-picture-"))
        target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
        target.write_bytes(image.data)
        self._announce("Asking about the picture.")  # type: ignore[attr-defined]

        def done(text: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            answer = f"{prepared.inspected} {described_by_sentence(connection)} {text.strip()}"
            cache.put(image.digest, question, answer, connection=connection, prepared=prepared)
            if self:
                self._beacon_picture_answer(beacon_id, answer, DESCRIBE_TITLE)

        def failed(sentence: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            if self:
                self._announce(sentence)  # type: ignore[attr-defined]

        service.describe_image(
            target, question, on_done=done, on_error=failed, requires=("text", "pictures")
        )

    def _beacon_picture_cache(self) -> Any:
        """This session's picture cache: in memory only (10B.2 rule 7)."""
        cache = getattr(self, "_beacon_ai_picture_cache", None)
        if cache is None:
            from quill.core.ai.picture_prep import PictureCache

            cache = PictureCache()
            self._beacon_ai_picture_cache = cache
        return cache

    # -- the answer, offered as a note ---------------------------------------------- #

    def _beacon_picture_answer(self, beacon_id: str, answer: str, title: str) -> None:
        """Show *answer*, then offer it as a note once its window is on screen."""
        self._app_ai_show(answer, title=title)  # type: ignore[attr-defined]
        self._ai_later(self._beacon_offer_note, beacon_id, answer)  # type: ignore[attr-defined]

    def _beacon_offer_note(self, beacon_id: str, answer: str) -> None:
        if not self:
            return
        window = getattr(self, "_last_shown_ai_window", None)
        if self._beacon_ai_yes_no(
            "Add this to the beacon's note?", NOTE_CAPTION, window if window else self
        ):
            self._beacon_add_to_note(beacon_id, answer)

    def _beacon_ai_yes_no(self, message: str, caption: str, parent: Any) -> bool:
        """One Yes/No, No the default."""
        import wx

        from quill.ui.dialog_contract import show_message_box

        style = wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        return show_message_box(message, caption, style, parent) in (wx.YES, wx.ID_YES)

    def _beacon_add_to_note(self, beacon_id: str, text: str) -> None:
        """Append *text* to the beacon's note through the store, as one undo step."""
        from quill.apps.beacon.undo import restore_beacons, snapshot_beacons

        store = self.store  # type: ignore[attr-defined]
        beacon = store.get_beacon(beacon_id)
        if beacon is None:
            self._announce("That beacon is gone. Nothing was added.")  # type: ignore[attr-defined]
            return
        snaps = snapshot_beacons(store, [beacon_id])
        beacon.note = f"{beacon.note.rstrip()}\n\n{text}" if beacon.note.strip() else text
        store.put_beacon(beacon)
        self.undo.push(  # type: ignore[attr-defined]
            "Add picture description to note", lambda: restore_beacons(store, snaps)
        )
        cache = getattr(self, "_results_cache", [])
        for index, row in enumerate(cache):
            if row.beacon_id == beacon_id:
                cache[index] = beacon
        selected = self._selected_beacon()  # type: ignore[attr-defined]
        if selected is not None and selected.beacon_id == beacon_id:
            self._show_details(beacon)  # type: ignore[attr-defined]
        self._announce("Added to the note. Ctrl+Z undoes it.")  # type: ignore[attr-defined]

    # -- background work, Beacon's way ------------------------------------------------ #

    def _beacon_ai_submit(
        self,
        name: str,
        work: Callable[..., Any],
        on_success: Callable[[str, Any], None],
        on_failure: Callable[[str, BaseException], None],
    ) -> None:
        """One daemon job off the UI thread; its callbacks marshal back themselves."""
        from quill.ui.update_download import thread_submit

        thread_submit(name, work, on_success=on_success, on_failure=on_failure)

    def _beacon_ai_call_after(self, func: Any, *args: Any) -> None:
        import wx

        if wx.GetApp() is not None:
            wx.CallAfter(func, *args)
        else:
            func(*args)


class BeaconAiMixin(BeaconAiFeaturesMixin, AppAiMixin):
    """The shared hosted-AI commands on Beacon's frame: hooks, no commands."""

    _AI_APP = "beacon"
    _AI_AGENT_NAME = AGENT_NAME
    _AI_ROWS = AI_ROWS
    _AI_SUBJECT = "this beacon or these search results"
    _AI_ABOUT_FACTS = (
        "the search and its results' titles and notes, or the selected beacon's title, "
        "note and tags, never where your library or any file is kept"
    )

    def _build_assist_menu(self, mb: Any) -> None:
        """Assist: the three local helpers first (10E.11), then the AI rows."""
        import wx

        m_assist = wx.Menu()
        self._add(  # type: ignore[attr-defined]
            m_assist,
            "Suggest &Tags\tCtrl+Shift+T",
            self._on_suggest_tags,  # type: ignore[attr-defined]
            "Suggest tags for the selected beacon from its text",
        )
        self._add(  # type: ignore[attr-defined]
            m_assist,
            "Suggest &Relationships\tCtrl+Shift+K",
            self._on_suggest_relationships,  # type: ignore[attr-defined]
            "Suggest related beacons by shared tags, collections, or domain",
        )
        self._add(  # type: ignore[attr-defined]
            m_assist,
            "&Summarize Note\tCtrl+Shift+M",
            self._on_summarize,  # type: ignore[attr-defined]
            "Produce an extractive summary of the selected beacon's note",
        )
        self._append_app_ai_rows(m_assist)
        mb.Append(m_assist, "&Assist")

    def _app_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts, from what is on screen: no file path, ever."""
        del question, needs
        from quill.core.ai.app_ask_context import beacon_context

        query = str(getattr(self, "last_query", "") or "").strip()
        if query:
            rows = getattr(self, "_results_cache", [])[:20]
            return beacon_context(search=query, results=[(b.title, b.note) for b in rows])
        beacon = self._selected_beacon()  # type: ignore[attr-defined]
        if beacon is None:
            return beacon_context()
        return beacon_context(note_title=beacon.title, note_text=beacon.note, tags=beacon.tags)

    def _app_ai_purpose(self) -> str:
        from quill.apps.beacon.surface_help import purpose_for_title

        return purpose_for_title("QuillBeacon")
