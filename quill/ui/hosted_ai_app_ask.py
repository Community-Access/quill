"""Ask, in a QuillVille app: the AI Conversation with the app's own facts (codex.md 10C).

The editors' Ask is the AI Conversation window (:mod:`quill.ui.hosted_ai_chat`)
with the document's passage, title and outline sent each turn. An app's Ask is
the same window, not a second one (10C.2: converge, do not multiply), with
three things only an app has:

* **Its facts, rebuilt every turn** (10C.3). The app hands over a provider,
  ``facts(question, needs)``, returning :class:`~quill.core.ai.app_ask_context.AppFacts`
  -- Quill Radio's station and what is playing, QUILL Cast's episode, show notes,
  chapters and position. They go through
  :func:`~quill.core.ai.app_ask_context.filter_facts`, so anything that needs a
  yes (Radio's listening history, a path, an email) stays behind unless the
  person chose the question that asks for it. When a fact moved since the last
  question, the window says so once, in Status, and tells the model too:
  "Now playing changed since your last question." (10C.4).
* **Its first line names the connection and the subject**: "Asking My ChatGPT
  plan about this station." (10C.2).
* **A quick list** above the message box: the app's own questions first (Radio's
  eight stay where they were), then its prompts from
  :func:`~quill.core.ai.family_prompt_catalogue.quick_prompts_for`, which end
  with the three the whole family shares. "What can I do here?" is answered on
  this computer from the app's own F1 catalogue, and nothing is sent. A prompt
  that needs something the connection in use cannot do says so in its label.

Everything else -- the transcript one Shift+Tab away, Alt+1 to Alt+0, Messages,
Export, Saved Conversations, dictation into the message box -- is the shared
window's, unchanged. Exchanges are saved through ``record_exchange`` in the
app's own folder under ``ai-sessions``, so a Radio conversation is not listed
in QUILL's Saved Conversations, or the other way round.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import wx

from quill.core.ai.app_ask_context import (
    HISTORY,
    AppFacts,
    asking_line,
    change_note,
    facts_text,
    filter_facts,
)
from quill.core.ai.family_prompt_catalogue import QuickPrompt, labelled
from quill.ui.accessible_names import set_accessible_name
from quill.ui.hosted_ai_chat import AiChatFrame, _direct_service, _talk_to_it
from quill.ui.hosted_ai_dialogs import _PAD

__all__ = [
    "TITLE",
    "AppAskFrame",
    "AskRow",
    "app_sessions_folder",
    "menu_routes",
    "open_app_ask",
    "rows_from_prompts",
    "show_picture_answer",
]

TITLE = "Ask"
_TYPE_YOUR_OWN = "Type your own question below"
_LOCAL_STATUS = "Answered on this computer. Nothing was sent."

#: ``facts(question, needs)``: one turn's facts, before anything is held back.
FactsFn = Callable[[str, str], AppFacts]


@dataclass(frozen=True, slots=True)
class AskRow:
    """One quick-list row: what it says, what it puts in the message box."""

    label: str
    text: str
    #: The app's own word for extra facts this question attaches (Radio's
    #: ``favorites``, ``recent_songs``, ``listening``), or "".
    context: str = ""
    #: Capabilities the connection must have (``pictures``, ``tools``).
    needs: tuple[str, ...] = ()
    #: Answered on this computer; nothing is sent.
    local: bool = False
    #: Kinds of fact this question may send once chosen (10C.3: the yes).
    consents: frozenset[str] = field(default_factory=frozenset)


def rows_from_prompts(prompts: Sequence[QuickPrompt]) -> list[AskRow]:
    """The family catalogue's prompts as quick-list rows; ``{context}`` is dropped,
    because the facts go with every message anyway."""
    return [
        AskRow(
            label=prompt.label,
            text=prompt.text.replace("{context}", "").strip() or prompt.label,
            needs=prompt.needs,
            local=prompt.local,
        )
        for prompt in prompts
    ]


class AppAskFrame(AiChatFrame):
    """Ask, about what is in front of the person in this app."""

    def __init__(
        self,
        parent: wx.Window,
        service: Any,
        *,
        announce: Callable[[str], None],
        facts: FactsFn,
        subject: str,
        about_facts: str,
        rows: Sequence[AskRow] = (),
        local_answer: Callable[[], str] | None = None,
        on_quick: Callable[[AskRow], str] | None = None,
        store: Path | None = None,
    ) -> None:
        # Set before the window is built: the quick list is made during it.
        self._facts_fn = facts
        self._subject = subject
        self._about_facts = about_facts
        self._rows = list(rows)
        self._local_answer = local_answer
        self._on_quick = on_quick
        self._pending: AskRow | None = None
        self._last_facts: AppFacts | None = None
        super().__init__(
            parent,
            service,
            announce=announce,
            store=store,
            context=lambda: self._turn_context(),
        )
        self.SetTitle(TITLE)

    # -- the quick list ------------------------------------------------------- #

    def _add_before_message(self, panel: wx.Panel, sizer: wx.BoxSizer) -> None:
        if not self._rows:
            return
        label = wx.StaticText(panel, label="&Quick questions")
        self._quick = wx.Choice(panel, choices=[_TYPE_YOUR_OWN, *self._row_labels()])
        set_accessible_name(self._quick, "Quick questions")
        self._quick.SetSelection(0)
        self._quick.SetHelpText(
            "Questions worth one keystroke. Arrow through them freely; press Enter, or "
            "Use This Question, to put the one you are on into the message box, where "
            "you can send it or change it. What can I do here? is answered on this "
            "computer and sends nothing."
        )
        # Enter is the choice, never the selection event: that fires on every
        # arrow press in a closed wx.Choice (reported 2026-09-29).
        self._quick.Bind(wx.EVT_CHAR_HOOK, self._on_quick_key)
        use = wx.Button(panel, label="Use &This Question")
        use.SetHelpText(
            "Puts the highlighted quick question into the message box and says what "
            "else, if anything, will go with it. Nothing is sent yet."
        )
        use.Bind(wx.EVT_BUTTON, lambda _e: self.use_quick())
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self._quick, 1, wx.RIGHT, _PAD)
        row.Add(use, 0)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)

    def _row_labels(self) -> list[str]:
        """Each row's label, with what it needs when the connection in use cannot."""
        from quill.core.ai.family_prompt_catalogue import NEED_CAPABILITY

        can_do = getattr(self._service, "can_do", None)
        have = {
            capability
            for capability in set(NEED_CAPABILITY.values())
            if callable(can_do) and can_do(capability)
        }
        return [
            labelled(row.label, row.needs, have) if row.needs else row.label for row in self._rows
        ]

    def _on_quick_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.use_quick()
            return
        event.Skip()

    def use_quick(self, index: int | None = None) -> None:
        """Put the highlighted question in the box, or answer a local one here.

        Put in the box rather than sent: the person may want to add a word, and
        a question that sends their favourites should be theirs to press Enter
        on. What else goes with it lands in Status, which does not have focus,
        so it is spoken (GATE-13).
        """
        chosen = self._quick.GetSelection() - 1 if index is None else index
        if not 0 <= chosen < len(self._rows):
            self._pending = None
            self._announce("Arrow to a question first, or type your own below.")
            return
        row = self._rows[chosen]
        if row.local:
            self._answer_here(row)
            return
        self._pending = row
        said = self._on_quick(row) if self._on_quick is not None else ""
        self._message.SetValue(row.text)
        self._message.SetFocus()
        if said:
            self._status.SetValue(said)
        self._announce(f"{said} Press Enter in Your message to send it.".strip())

    def _answer_here(self, row: AskRow) -> None:
        """A question this app answers itself, from its own F1 catalogue."""
        from quill.core.ai.spoken_answer import speakable_line

        answer = self._local_answer() if self._local_answer is not None else ""
        answer = answer.strip() or "There is no help written for this window yet."
        self._conversation.add("user", row.label)
        self._conversation.add("assistant", answer)
        self._show_transcript()
        self._status.SetValue(_LOCAL_STATUS)
        self._message.SetFocus()
        self._announce(f"{speakable_line(answer)} {_LOCAL_STATUS}")

    # -- each turn's facts -------------------------------------------------- #

    def _turn_context(self) -> list[str]:
        """This turn's facts block, held back where a yes is missing, with the
        change since the last question said once (10C.4)."""
        row, self._pending = self._pending, None
        question = self._message.GetValue().strip()
        current = filter_facts(
            self._facts_fn(question, row.context if row else ""),
            row.consents if row else (),
        )
        note = change_note(self._last_facts, current)
        self._last_facts = current
        text = facts_text(current)
        if note:
            self._status.SetValue(note)
            self._announce(note)
            text = f"{note}\n\n{text}" if text else note
        return [text] if text else []

    # -- what the window says ------------------------------------------------ #

    def _asking_line(self) -> str:
        connection = str(getattr(self._service, "connection_in_use", "") or "")
        if not connection:
            from quill.core.ai.connection_words import asking_sentence

            keyed = getattr(self._service, "_keyed", None)
            sentence = asking_sentence("")
            return str(keyed(sentence)) if callable(keyed) else sentence
        return asking_line(connection, self._subject)

    def _plain_about_text(self) -> str:
        said = (
            f" With each message go {self._about_facts}, read fresh each time; when one "
            "has changed since your last question, Status says so. Nothing that needs "
            "your yes goes unless you choose the question that asks for it."
            " Alt+1 reads the newest message aloud, Alt+2 the one before it, up to "
            "Alt+0; Messages lists them all."
        )
        if self._store is not None:
            said += (
                " The conversation is saved on this computer as it goes; Saved "
                "Conversations opens it again."
            )
        note = getattr(self._service, "conversation_note", None)
        if callable(note):
            return str(note()) + said
        return said.strip()


def open_app_ask(
    host: Any,
    *,
    app: str,
    subject: str,
    about_facts: str,
    facts: FactsFn,
    rows: Sequence[AskRow],
    local_answer: Callable[[], str] | None = None,
    on_quick: Callable[[AskRow], str] | None = None,
) -> None:
    """Open (or raise) an app's Ask from its ``HostedAiMixin`` adapter.

    The same readiness rules as the editors' Ask: the area, the agreement where
    the free AI is concerned, a connection in use that can do text, and the
    free AI's Connect step when this computer is not connected yet.
    """
    if not host._ai_ready() or not host._ai_capable("text"):
        return
    already = getattr(host, "_ai_windows", {}).get("ask")
    if already:
        from quill.ui.hosted_ai_dialogs import take_focus

        take_focus(already)
        return
    service = host._ai_service()
    if not _direct_service(service) and not service.signed_in:
        host._announce(
            "This computer is not connected to QUILL's free AI. Choose Your AI "
            "connects it, or chooses another."
        )
        host._ai_open_connect()
        return
    service.refresh_limits()
    store = app_sessions_folder(host, app)

    def build() -> AppAskFrame:
        frame = AppAskFrame(
            host._ai_parent(),
            service,
            announce=host._announce,
            facts=facts,
            subject=subject,
            about_facts=about_facts,
            rows=rows,
            local_answer=local_answer,
            on_quick=on_quick,
            store=store,
        )
        _talk_to_it(frame, host)
        return frame

    host._open_ai_window("ask", build)


def app_sessions_folder(host: Any, app: str) -> Path | None:
    """``<data>/ai-sessions/<app>``: this app's saved conversations, apart from
    QUILL's (which are the top of ``ai-sessions``, beside Ask Quill's)."""
    from quill.core.ai.sessions import SESSIONS_FOLDER

    data_dir = getattr(host._ai_host(), "data_dir", None)
    return Path(data_dir) / SESSIONS_FOLDER / app if data_dir else None


def menu_routes(menu_bar: Any) -> list[tuple[str, str]]:
    """``(menu name, "Alt+letter")`` for each top-level menu: what "What can I
    do here?" lists after the window's purpose. Never raises."""
    routes: list[tuple[str, str]] = []
    try:
        for index in range(menu_bar.GetMenuCount()):
            raw = str(menu_bar.GetMenuLabel(index))
            name = raw.replace("&", "").strip()
            at = raw.find("&")
            letter = raw[at + 1 : at + 2].upper() if 0 <= at < len(raw) - 1 else ""
            if name:
                routes.append((f"The {name} menu", f"Alt+{letter}" if letter else ""))
    except Exception:  # noqa: BLE001 - no menu bar lists nothing
        return routes
    return routes


def show_picture_answer(host: Any, answer: str) -> None:
    """A picture's description: said, because focus stays where it was, and kept
    in a result window to read again. Quill Radio's and QUILL Studio's Describe."""
    from quill.core.ai.chatgpt_ai_help import IMAGE_FEATURE
    from quill.core.ai.spoken_answer import speakable_line
    from quill.ui.hosted_ai_pad import AiResultFrame

    host._announce(speakable_line(answer))
    frame = AiResultFrame(
        host._ai_parent(),
        action=IMAGE_FEATURE,
        text=answer,
        used="",
        on_replace=None,
        on_insert=None,
        on_again=None,
        announce=host._announce,
    )
    host._show_ai_window(frame)


# Re-exported for the adapters' consent rows.
CONSENT_HISTORY: frozenset[str] = frozenset({HISTORY})
