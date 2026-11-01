"""Quill Inkwell reaches the family's AI through the shared small-app adapter.

codex.md Phase 3 (10E.10, 6.12). Quill Inkwell had no AI. Now it runs the
shared hosted AI through :class:`~quill.ui.hosted_ai_app_adapter.AppAiMixin`
-- hooks only -- with its own "QUILL Inkwell" sign-in, so Choose Your AI, Which
AI Am I Using, the one AI Usage list, the AI line in the main window and Safe
Mode's refusal all come from the code every app shares.

What Quill Inkwell *does* with AI is :class:`InkwellAiFeaturesMixin`:

* **Ask** (Ctrl+Shift+8, AI > Ask...) about the abbreviation library: each
  abbreviation by name and expansion, most used first
  (``app_ask_context.inkwell_context``), read from the library in memory for
  each question.
* **Suggest Abbreviations from a Document** (Ctrl+Shift+A): the person picks a
  document, says yes to sending its text (a whole document needs a yes,
  codex.md 10C.3), and reviews what comes back in a list whose check boxes all
  start cleared. Only the checked ones are added, through the same library
  save Manage Abbreviations uses; nothing proposed can overwrite an entry
  (:func:`quill.core.ai.app_requests.parse_suggestions`).
* **Add Abbreviations from a Document...** (Ctrl+F3): the agent task
  (:mod:`quill.apps.inkwell_ai_task`), which can read the library and talk the
  set over before it shows every entry and adds them on Apply.

**Never driven by a model.** System-wide expansion, the keyboard hook and the
matcher never see the AI, and no typed text is ever read or sent. The file's
name and folder stay on this computer: only its text goes, and only on a yes.

**Keys.** Ctrl+1 to Ctrl+9 are the Window menu's, so Ask is Ctrl+Shift+8, Which
AI Ctrl+F8 and Choose Your AI Ctrl+Shift+F8, as in Quill Radio, QUILL Cast and
QUILL Transcribe; Privacy Agreement is Alt+Shift+F2 because Ctrl+Alt+Shift+K is
the Quick Insert Key (``app_keymaps.py``, ``app_ai_keys.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.hosted_ai_app_adapter import AppAiMixin

__all__ = [
    "AGENT_NAME",
    "AI_ROWS",
    "CONFIRM_TITLE",
    "DOCUMENT_SUFFIXES",
    "InkwellAiFeaturesMixin",
    "InkwellAiMixin",
    "UnreadableDocument",
    "read_document_text",
    "send_sentence",
]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Inkwell"
#: The yes-or-no before a document's text goes anywhere.
CONFIRM_TITLE = "Send the Document?"
#: The file picker's title.
PICK_TITLE = "Choose a Document"

#: What Suggest Abbreviations reads, cheaply and on this computer.
DOCUMENT_SUFFIXES = (".txt", ".text", ".md", ".markdown", ".docx", ".rtf")
_WILDCARD = (
    "Documents (*.txt;*.md;*.docx;*.rtf)|*.txt;*.text;*.md;*.markdown;*.docx;*.rtf"
    "|Plain text (*.txt)|*.txt|Markdown (*.md)|*.md;*.markdown"
    "|Word documents (*.docx)|*.docx|Rich text (*.rtf)|*.rtf"
)

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C D B H O S P).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    (
        "inkwell.ai_suggest",
        "Suggest Abbreviations from a &Document...",
        "cmd_inkwell_suggest",
    ),
    ("tools.hosted_ai_task", "Add A&bbreviations from a Document...", "cmd_ai_task"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)


class UnreadableDocument(Exception):  # noqa: N818 - a sentence, not a crash
    """A document Suggest Abbreviations cannot read; the message is said as is."""


def read_document_text(path: Path) -> str:
    """The text of *path*: plain text, Markdown, Word (.docx) or RTF. wx-free.

    Raises :class:`UnreadableDocument` with a sentence to say otherwise.
    """
    suffix = path.suffix.lower()
    if suffix not in DOCUMENT_SUFFIXES:
        raise UnreadableDocument(
            f"Quill Inkwell cannot read {path.name}. "
            "Choose a plain text, Markdown, Word or rich text document."
        )
    try:
        if suffix == ".docx":
            from quill.io.docx_text import read_docx_text

            text = read_docx_text(path)
            if text is None:
                raise UnreadableDocument(f"Could not read {path.name} as a Word document.")
            return text
        if suffix == ".rtf":
            from quill.io.rtf import read_rtf_document

            return read_rtf_document(path).text
        from quill.io.text import read_text_document

        return read_text_document(path).text
    except UnreadableDocument:
        raise
    except Exception as error:  # noqa: BLE001 - any reader failure is one sentence
        raise UnreadableDocument(f"Could not read {path.name}. {error}") from error


def send_sentence(file_name: str, text: str, connection_name: str) -> str:
    """The question before sending: the file, roughly how much goes, and to whom."""
    from quill.core.ai.app_requests import INKWELL_DOCUMENT_CHARS

    stripped = text.strip()
    whole = len(stripped) <= INKWELL_DOCUMENT_CHARS
    words = len(stripped[:INKWELL_DOCUMENT_CHARS].split())
    noun = "word" if words == 1 else "words"
    amount = f"All {words:,} {noun} of" if whole else f"The first {words:,} {noun} of"
    return (
        f"{amount} {file_name} go to {connection_name} to suggest abbreviations. "
        "The file's name and folder stay on this computer. Send them?"
    )


class InkwellAiFeaturesMixin:
    """Suggest Abbreviations from a Document. Mixed in through ``InkwellAiMixin``."""

    def cmd_ai_task(self) -> None:
        """Add Abbreviations from a Document (Ctrl+F3, codex.md 6.12): pick a
        document, talk it over, and add the abbreviations in the shared agent
        window. Every entry is shown before any is added; a clash is left out.
        System-wide expansion is never driven by the model."""
        from quill.apps.inkwell_ai_task import (
            ADD_FROM_DOCUMENT,
            INSTRUCTION_HELP,
            inkwell_task_facts,
            inkwell_task_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            ADD_FROM_DOCUMENT,
            lambda ctx: inkwell_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            context=lambda: inkwell_task_facts(self),
        )

    def cmd_inkwell_suggest(self) -> None:
        """Suggest Abbreviations from a Document (Ctrl+Shift+A)."""
        if not self._ai_ready() or not self._ai_capable("text"):  # type: ignore[attr-defined]
            return
        path = self._inkwell_pick_document()
        if path is None:
            return
        self._announce(f"Reading {path.name}.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> object:
            try:
                return read_document_text(path)
            except UnreadableDocument as error:
                return error

        def done(_op: str, result: object) -> None:
            self._inkwell_ai_call_after(self._inkwell_document_read, path, result)

        self._task_manager.submit("inkwell-ai-read", work, on_success=done, on_failure=None)  # type: ignore[attr-defined]

    def _inkwell_pick_document(self) -> Path | None:
        """The document to read, from the standard Open window; None on Cancel."""
        import wx

        dialog = wx.FileDialog(
            self.frame,  # type: ignore[attr-defined]
            PICK_TITLE,
            wildcard=_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, PICK_TITLE) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return Path(dialog.GetPath())
        finally:
            dialog.Destroy()

    def _inkwell_ai_call_after(self, func: Any, *args: Any) -> None:
        import wx

        if wx.GetApp() is not None:
            wx.CallAfter(func, *args)
        else:
            func(*args)

    def _inkwell_document_read(self, path: Path, result: object) -> None:
        """The text is read: ask before any of it goes, then send it."""
        if isinstance(result, BaseException):
            self._announce(str(result))  # type: ignore[attr-defined]
            return
        text = str(result or "")
        if not text.strip():
            self._announce(f"{path.name} has no text to suggest abbreviations from.")  # type: ignore[attr-defined]
            return
        if not self._inkwell_confirm_send(path.name, text):
            self._announce("Nothing was sent.")  # type: ignore[attr-defined]
            return
        from quill.core.ai.app_requests import inkwell_suggest_prompt

        existing = self._inkwell_existing_names()
        self._app_ai_request(  # type: ignore[attr-defined]
            inkwell_suggest_prompt(text, existing),
            lambda answer: self._inkwell_suggestions_answered(path.name, answer),
            working=f"Asking for abbreviations from {path.name}.",
        )

    def _inkwell_connection_name(self) -> str:
        from quill.core.ai.connection_caps import CONNECTION_NAMES

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = str(getattr(service, "connection_in_use", "") or "")
        return CONNECTION_NAMES.get(connection, "the AI in use")

    def _inkwell_confirm_send(self, file_name: str, text: str) -> bool:
        """One Yes or No, No the default, naming the file, how much and to whom."""
        import wx

        sentence = send_sentence(file_name, text, self._inkwell_connection_name())
        dialog = wx.MessageDialog(
            self.frame,  # type: ignore[attr-defined]
            sentence,
            CONFIRM_TITLE,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        try:
            return bool(self._show_modal_dialog(dialog, CONFIRM_TITLE) == wx.ID_YES)  # type: ignore[attr-defined]
        finally:
            dialog.Destroy()

    def _inkwell_existing_names(self) -> list[str]:
        library = getattr(self, "_library", None)
        return [a.abbreviation for a in getattr(library, "abbreviations", ())]

    def _inkwell_suggestions_answered(self, file_name: str, answer: str) -> None:
        """The proposals: reviewed one by one, and only the checked ones added."""
        from quill.core.ai.app_requests import parse_suggestions

        proposals = parse_suggestions(answer, self._inkwell_existing_names())
        if not proposals:
            self._announce(f"No new abbreviations came back for {file_name}.")  # type: ignore[attr-defined]
            return
        chosen = self._inkwell_review_suggestions(proposals)
        if chosen is None:
            self._announce("No abbreviations were added.")  # type: ignore[attr-defined]
            return
        added = self._inkwell_add_suggestions(chosen)
        if added == 0:
            self._announce("No abbreviations were added.")  # type: ignore[attr-defined]
        elif added == 1:
            self._announce("Added 1 abbreviation.")  # type: ignore[attr-defined]
        else:
            self._announce(f"Added {added} abbreviations.")  # type: ignore[attr-defined]

    def _inkwell_review_suggestions(
        self, proposals: list[tuple[str, str]]
    ) -> list[tuple[str, str]] | None:
        """The review window; the checked proposals on OK, None on Cancel."""
        import wx

        from quill.apps.inkwell_suggest_dialog import SUGGEST_TITLE, SuggestionsDialog

        dialog = SuggestionsDialog(self.frame, proposals)  # type: ignore[attr-defined]
        try:
            if self._show_modal_dialog(dialog, SUGGEST_TITLE) != wx.ID_OK:  # type: ignore[attr-defined]
                return None
            return dialog.checked()
        finally:
            dialog.Destroy()

    def _inkwell_add_suggestions(self, chosen: list[tuple[str, str]]) -> int:
        """Add *chosen* to the shared library, the way New from Clipboard saves.

        The library is read again first, so an entry QUILL added meanwhile is
        kept, and a proposal that now clashes with one is left out.
        """
        import uuid

        from quill.core.abbreviations import (
            Abbreviation,
            load_abbreviation_library,
            save_abbreviation_library,
        )

        if not chosen:
            return 0
        data_dir = self._data_dir  # type: ignore[attr-defined]
        library = load_abbreviation_library(data_dir)
        taken = {a.abbreviation.lower() for a in library.abbreviations}
        added = 0
        for abbreviation, expansion in chosen:
            if abbreviation.lower() in taken:
                continue
            taken.add(abbreviation.lower())
            library.abbreviations.append(
                Abbreviation(id=str(uuid.uuid4()), abbreviation=abbreviation, expansion=expansion)
            )
            added += 1
        if added:
            library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(library, data_dir)
        self._library = library
        self._library_stamp = None
        self._reload_list()  # type: ignore[attr-defined]
        self._refresh_status()  # type: ignore[attr-defined]
        return added


class InkwellAiMixin(InkwellAiFeaturesMixin, AppAiMixin):
    """The shared hosted-AI commands on Quill Inkwell's frame: hooks, no commands."""

    _AI_APP = "inkwell"
    _AI_AGENT_NAME = AGENT_NAME
    _AI_ROWS = AI_ROWS
    _AI_SUBJECT = "your abbreviations"
    _AI_ABOUT_FACTS = (
        "your abbreviations by name and expansion, most used first; never anything "
        "you type in other programs"
    )

    def _app_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts: the library already in memory, never typed text."""
        del question, needs
        from quill.core.ai.app_ask_context import inkwell_context

        library = getattr(self, "_library", None)
        return inkwell_context(list(getattr(library, "abbreviations", ())))

    def _app_ai_purpose(self) -> str:
        from quill.core.inkwell_surface_help import purpose_for_title

        return purpose_for_title("Quill Inkwell")
