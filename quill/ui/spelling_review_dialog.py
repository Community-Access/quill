"""F7 Spelling Review modal dialog for QUILL.

Presentation logic only. All workflow state lives in ReviewSession
(quill.core.spelling.session). The dialog calls session methods and applies
the returned editor-replace tuples via the _apply callback.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.spelling.announcements import AccessibilityAnnouncer
from quill.core.spelling.models import ReviewCounters, SpellingIssue
from quill.core.spelling.session import ReviewSession
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

if TYPE_CHECKING:
    pass


class SpellingReviewDialog:
    """Guided, accessible F7 spelling review dialog.

    Parameters
    ----------
    parent:
        wx parent window.
    session:
        A fully-constructed ReviewSession.
    apply_fn:
        Callable(start, old_end, replacement) — drives editor.Replace().
        Must execute on the main thread.
    announce_fn:
        Callable(message) — used for accessibility announcements.
    document_path:
        Path to the open document (for Add to Dictionary scope).
    project_root:
        Project root path (for Add to Dictionary scope).
    settings:
        QUILL Settings object; reads spell_review_verbosity,
        spell_review_spell_word, spell_review_spell_word_pause_ms.
    scope_label:
        Human description of the scope ("selected text" or "document").
    """

    def __init__(
        self,
        parent: object,
        session: ReviewSession,
        apply_fn: Callable[[int, int, str], None],
        announce_fn: Callable[[str], None],
        document_path: Path | None,
        project_root: Path | None,
        settings: object,
        scope_label: str = "document",
        personal_dir: Path | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._session = session
        self._apply_fn = apply_fn
        self._doc_path = document_path
        self._project_root = project_root
        self._scope_label = scope_label
        self._settings = settings
        self._personal_dir = personal_dir
        self._announce_fn = announce_fn

        verbosity = str(getattr(settings, "spell_review_verbosity", "balanced"))
        spell_word = bool(getattr(settings, "spell_review_spell_word", True))
        spell_pause = int(getattr(settings, "spell_review_spell_word_pause_ms", 800))
        self._announcer = AccessibilityAnnouncer(
            announce_fn,
            verbosity=verbosity,
            spell_word=spell_word,
            spell_word_pause_ms=spell_pause,
            timer_factory=wx.CallLater,
            # The shared voicing preferences: how letters are said, whether
            # capitals are named, whether each suggestion spells itself as you
            # arrow onto it. The two spell_review_* values above still win over
            # their equivalents in here, because they are the review's own.
            settings=settings,
        )

        self._current_issue: SpellingIssue | None = None
        self._context_word_start = 0
        self._context_word_end = 0

        self.dialog = wx.Dialog(
            parent,
            title="Spelling Review",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 460))
        self.dialog.SetSize(wx.Size(700, 540))
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Issue type label ("Not in dictionary: word")
        self._issue_label = wx.StaticText(self.dialog, label="")
        self._issue_label.SetFont(self._issue_label.GetFont().Bold())
        root.Add(self._issue_label, 0, wx.ALL, 10)

        # Context field
        ctx_label = wx.StaticText(
            self.dialog,
            label="Conte&xt around word (Alt+W to reselect, Ctrl+R to read the sentence aloud):",
        )
        root.Add(ctx_label, 0, wx.LEFT | wx.RIGHT, 10)

        self._context = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
        )
        self._context.SetName("Context")
        self._context.SetMinSize(wx.Size(-1, 90))
        root.Add(self._context, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Change-to field
        change_row = wx.BoxSizer(wx.HORIZONTAL)
        change_label = wx.StaticText(self.dialog, label="Change &to:")
        self._change_to = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._change_to.SetName("Change to")
        change_row.Add(change_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        change_row.Add(self._change_to, 1, wx.EXPAND)
        root.Add(change_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Suggestions list
        sugg_label = wx.StaticText(self.dialog, label="&Suggestions:")
        root.Add(sugg_label, 0, wx.LEFT | wx.RIGHT, 10)

        self._suggestions = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._suggestions.SetName("Suggestions")
        self._suggestions.SetMinSize(wx.Size(-1, 80))
        root.Add(self._suggestions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Review order. This was two commands until 2026-09-16 -- Spell Check
        # and Spell Check (Ranked by Frequency), the same dialog opened two
        # ways, on two chords, in two menu rows. One verb registered twice is
        # how a pair drifts (bad.md 7.1), and the F7 chord family had no room
        # left for the second one anyway. A checkbox instead, which also gives
        # QuillLite ranked review for the first time -- it shares this dialog
        # and never had the second command.
        self._ranked_box = wx.CheckBox(self.dialog, label="Review most-&frequent words first")
        self._ranked_box.SetValue(self._session.is_ranked())
        self._ranked_box.SetToolTip(
            "Walk the list by how often each word recurs rather than by "
            "position, so fixing one repeated typo clears the bulk of it."
        )
        root.Add(self._ranked_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Action buttons — row 1
        btn1 = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_change = wx.Button(self.dialog, label="Chan&ge")
        self._btn_change_all = wx.Button(self.dialog, label="Change &All")
        self._btn_ignore_once = wx.Button(self.dialog, label="&Ignore Once")
        self._btn_ignore_all = wx.Button(self.dialog, label="Ignore A&ll")
        for btn in (
            self._btn_change,
            self._btn_change_all,
            self._btn_ignore_once,
            self._btn_ignore_all,
        ):
            btn1.Add(btn, 0, wx.RIGHT, 6)
        root.Add(btn1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Action buttons — row 2
        btn2 = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_read_sentence = wx.Button(self.dialog, label="&Read Sentence")
        self._btn_add_dict = wx.Button(self.dialog, label="Add to &Dictionary")
        self._btn_undo = wx.Button(self.dialog, label="&Undo Last")
        self._btn_close = wx.Button(self.dialog, label="&Close")
        for btn in (self._btn_read_sentence, self._btn_add_dict, self._btn_undo, self._btn_close):
            btn2.Add(btn, 0, wx.RIGHT, 6)
        root.Add(btn2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        apply_modal_ids(
            self.dialog,
            affirmative_id=self._btn_change.GetId(),
            escape_id=self._btn_close.GetId(),
        )

        self.dialog.SetSizer(root)
        self._bind_events()

    def _bind_events(self) -> None:
        wx = self._wx

        # Suggestion list selection → update Change to field.
        self._suggestions.Bind(wx.EVT_LISTBOX, self._on_suggestion_select)

        # Review order, live: the session re-scans, so the remaining
        # issues reorder without losing what has been corrected.
        self._ranked_box.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_ranked_toggled())

        # Enter in Change-to field → Change.
        self._change_to.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._on_change())

        # Buttons.
        self._btn_change.Bind(wx.EVT_BUTTON, lambda _e: self._on_change())
        self._btn_change_all.Bind(wx.EVT_BUTTON, lambda _e: self._on_change_all())
        self._btn_ignore_once.Bind(wx.EVT_BUTTON, lambda _e: self._on_ignore_once())
        self._btn_ignore_all.Bind(wx.EVT_BUTTON, lambda _e: self._on_ignore_all())
        self._btn_read_sentence.Bind(wx.EVT_BUTTON, lambda _e: self._read_sentence_in_context())
        self._btn_add_dict.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_dict())
        self._btn_undo.Bind(wx.EVT_BUTTON, lambda _e: self._on_undo())
        self._btn_close.Bind(wx.EVT_BUTTON, lambda _e: self._on_close())

        # Alt+W: reselect word in context.
        self.dialog.Bind(
            wx.EVT_CHAR_HOOK,
            self._on_char_hook,
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_ranked_toggled(self) -> None:
        """Re-order what is left, say what changed, and remember the choice."""
        ranked = bool(self._ranked_box.GetValue())
        self._session.set_ranked(ranked)
        if self._settings is not None:
            try:
                self._settings.spell_review_ranked = ranked
            except Exception:  # noqa: BLE001 - a stub settings object in tests
                pass
        if self._session.is_complete():
            self._show_completion()
            return
        self._populate_current_issue()
        # The reader has already said "checked"/"unchecked" -- that is the
        # control's own state and announcing it again would be GATE-13
        # over-announcing. What it cannot say is that the list underneath was
        # reordered and a different word is now in front of you, so that is
        # what gets said, with the position to prove it moved.
        self._announcer.announce_action_result(
            "Most frequent first." if ranked else "Document order.",
            self._session.position(),
            self._session.total(),
        )

    def _on_char_hook(self, event: object) -> None:
        wx = self._wx
        key = event.GetKeyCode()  # type: ignore[attr-defined]
        mods = event.GetModifiers()  # type: ignore[attr-defined]
        if key == ord("W") and mods == wx.MOD_ALT:
            self._reselect_word()
            return
        if key == ord("R") and mods == wx.MOD_CONTROL:
            self._read_sentence_in_context()
            return
        event.Skip()  # type: ignore[attr-defined]

    def _on_suggestion_select(self, event: object) -> None:
        sel = self._suggestions.GetSelection()
        if sel != self._wx.NOT_FOUND:
            suggestion = self._suggestions.GetString(sel)
            self._change_to.SetValue(suggestion)
            # Spell it out after a pause, which is the whole point of a
            # suggestion list to somebody listening: choosing between "receive"
            # and "recieve" by ear is exactly as impossible here as it was in
            # the document. The announcer has been built with these settings
            # since it shipped and nothing was calling it, so the twelve
            # Announcements settings QUILL could reach did nothing on this
            # list -- and QuillLite had done it all along, which is rule 10
            # backwards (bad.md P1.14). Arrowing on cancels the pending one.
            self._announcer.spell_suggestion(str(suggestion))
        event.Skip()  # type: ignore[attr-defined]

    def _on_change(self) -> None:
        replacement = self._change_to.GetValue()
        if not replacement:
            return
        issue = self._session.current()
        if issue is None:
            return
        old_word = issue.word
        ops = self._session.apply_change(replacement)
        for start, old_end, repl in ops:
            self._apply_fn(start, old_end, repl)
        msg = f"Changed {old_word} to {replacement}."
        self._advance_or_complete(msg)

    def _on_change_all(self) -> None:
        replacement = self._change_to.GetValue()
        if not replacement:
            return
        issue = self._session.current()
        if issue is None:
            return
        old_word = issue.word
        ops = self._session.apply_change_all(replacement)
        count = len(ops)
        for start, old_end, repl in ops:
            self._apply_fn(start, old_end, repl)
        noun = "replacement" if count == 1 else "replacements"
        msg = f"Changed all occurrences of {old_word} to {replacement}. {count} {noun}."
        self._advance_or_complete(msg)

    def _on_ignore_once(self) -> None:
        issue = self._session.current()
        if issue is None:
            return
        word = issue.word
        self._session.apply_ignore_once()
        self._advance_or_complete(f"Ignored {word} once.")

    def _on_ignore_all(self) -> None:
        issue = self._session.current()
        if issue is None:
            return
        word = issue.word
        self._session.apply_ignore_all()
        self._advance_or_complete(f"Ignored all occurrences of {word} for this session.")

    def _on_add_dict(self) -> None:
        issue = self._session.current()
        if issue is None:
            return
        word = issue.word
        self._session.add_to_dict(
            "personal", self._doc_path, self._project_root, self._personal_dir
        )
        self._advance_or_complete(f"Added {word} to dictionary.")

    def _on_undo(self) -> None:
        ops = self._session.undo_last()
        for start, old_end, repl in ops:
            self._apply_fn(start, old_end, repl)
        self._populate_current_issue()

    def _on_close(self) -> None:
        self.dialog.EndModal(self._wx.ID_CLOSE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance_or_complete(self, action_msg: str) -> None:
        # Reaching the end when the review started at the caret is not the end
        # of the review: it is the moment to come back round to the top, which
        # is what Word does and what ``spell_review_wrap_to_beginning`` has
        # promised in Preferences while being read by nothing (bad.md S7).
        if self._session.should_wrap():
            self._announcer.announce_wrap_prompt()
            self._session.wrap_to_beginning()
            if not self._session.is_complete():
                self._populate_current_issue()
                return
        if self._session.is_complete():
            self._announcer.announce_action_result(
                action_msg, self._session.total() + 1, self._session.total()
            )
            self._show_completion()
        else:
            idx = self._session.position()
            total = self._session.total()
            self._announcer.announce_action_result(action_msg, idx, total)
            self._populate_current_issue()

    def _populate_current_issue(self) -> None:
        issue = self._session.current()
        if issue is None:
            self._show_completion()
            return

        self._current_issue = issue
        self._context_word_start = issue.context_word_start
        self._context_word_end = issue.context_word_end

        idx = self._session.position()
        total = self._session.total()

        self.dialog.SetTitle(f"Spelling Review — Issue {idx} of {total}")
        self._issue_label.SetLabel(f"Not in dictionary: {issue.word}")

        self._context.SetValue(issue.context_text)
        self._context.SetSelection(issue.context_word_start, issue.context_word_end)

        self._suggestions.Clear()
        for s in issue.suggestions:
            self._suggestions.Append(s)
        if issue.suggestions:
            self._suggestions.SetSelection(0)

        default = issue.suggestions[0] if issue.suggestions else issue.word
        self._change_to.SetValue(default)
        self._change_to.SetSelection(-1, -1)

        self._btn_undo.Enable(self._session.can_undo())

        if not issue.suggestions:
            self._announcer.announce_no_suggestions()

        self._wx.CallAfter(self._focus_context)

    def _focus_context(self) -> None:
        self._context.SetFocus()
        self._context.SetSelection(self._context_word_start, self._context_word_end)

    def _reselect_word(self) -> None:
        self._context.SetFocus()
        self._context.SetSelection(self._context_word_start, self._context_word_end)

    def _read_sentence_in_context(self) -> None:
        """Read the sentence(s) surrounding the misspelling aloud (Ctrl+R / button).

        Speaks the same context text shown in the Context field so the user hears
        the misspelling in situ. No-op when no issue is current."""
        issue = self._current_issue
        if issue is None:
            return
        self._announcer.announce_context_sentence(issue.context_text)

    def _show_completion(self) -> None:
        counters = self._session.get_counters()
        self._announcer.announce_complete(counters)
        self._show_summary_and_close(counters)

    def _show_summary_and_close(self, counters: ReviewCounters) -> None:
        wx = self._wx

        parts: list[str] = []
        if counters.changed:
            parts.append(f"{counters.changed} changed")
        if counters.changed_all:
            parts.append(f"{counters.changed_all} changed via Change All")
        if counters.ignored_once:
            parts.append(f"{counters.ignored_once} ignored once")
        if counters.ignored_all:
            parts.append(f"{counters.ignored_all} ignored for session")
        if counters.added_to_dict:
            parts.append(f"{counters.added_to_dict} added to dictionary")

        summary = ", ".join(parts) if parts else "No changes made."
        show_message_box(
            f"Spelling review complete.\n\n{summary}",
            "Spelling Review",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
        )
        self.dialog.EndModal(wx.ID_OK)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show(self, show_modal_dialog: Callable) -> None:
        """Open the dialog. Populates the first issue then blocks."""
        issue = self._session.current()
        if issue is None:
            self._announcer.announce_no_issues(self._scope_label)
            return

        self._populate_current_issue()
        total = self._session.total()
        self._announcer.announce_opening(self._scope_label, 1, total, issue.word)
        show_modal_dialog(self.dialog, "Spelling Review")
        self.dialog.Destroy()
