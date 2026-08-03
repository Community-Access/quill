"""Spell check and thesaurus commands for MainFrame (CQ-1 decomposition).

``SpellcheckCommandsMixin`` owns the interactive spelling surface: dictionary
status, spell-language choice, the spelling review dialogs (plain and ranked),
the misspelling list and next/previous navigation, spell-check-word-at-cursor,
the thesaurus dialog, spoken spelling helpers, the cached document dictionary,
and add-word-to-scope. Extracted verbatim from ``main_frame.py``; runs on
``MainFrame`` (``self``). Spell state (``_spell_dictionary_cache`` and
friends) stays initialized in ``MainFrame.__init__``.
"""

from __future__ import annotations

import time
from pathlib import Path

from quill.core import thesaurus as thesaurus_engine
from quill.core.marks import line_column_for_position
from quill.core.paths import app_data_dir
from quill.core.spellcheck import (
    Misspelling,
    add_word_to_scope,
    is_known_word,
    list_misspellings,
    load_combined_dictionary,
    load_scope_dictionary,
    misspelling_at_position,
    rank_misspellings_by_frequency,
    suggest_words,
)
from quill.core.spellcheck import (
    backend_info as spellcheck_backend_info,
)
from quill.core.spellcheck import (
    next_misspelling as find_next_misspelling,
)
from quill.core.spellcheck import (
    previous_misspelling as find_previous_misspelling,
)
from quill.core.spellcheck_live import live_alert_suppressed
from quill.platform.sr_announce import (
    announce,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
)


class SpellcheckCommandsMixin:
    def show_dictionary_status(self) -> None:
        wx = self._wx
        project_root = Path.cwd()
        personal_count = len(load_scope_dictionary("personal", self.document.path, project_root))
        document_count = len(load_scope_dictionary("document", self.document.path, project_root))
        project_count = len(load_scope_dictionary("project", self.document.path, project_root))
        personal_path = app_data_dir() / "dictionaries" / "personal.json"
        document_path = (
            self.document.path.with_suffix(self.document.path.suffix + ".quill-dict.json")
            if self.document.path is not None
            else None
        )
        project_path = project_root / ".quill-dictionary.json"
        backend = spellcheck_backend_info()
        thesaurus_status = "installed" if thesaurus_engine.is_available() else "not installed"
        if personal_path.exists():
            personal_line = f"- Personal: {personal_count} (stored at {personal_path})"
        else:
            personal_line = (
                f"- Personal: {personal_count} "
                f"(not created yet; add a word to create {personal_path})"
            )
        if document_path is None:
            document_line = (
                f"- Document: {document_count} (not available until the current document is saved)"
            )
        elif document_path.exists():
            document_line = f"- Document: {document_count} (stored at {document_path})"
        else:
            document_line = (
                f"- Document: {document_count} (not created yet for this document: {document_path})"
            )
        if project_path.exists():
            project_line = f"- Project: {project_count} (stored at {project_path})"
        else:
            project_line = (
                f"- Project: {project_count} (not created yet in this folder: {project_path})"
            )
        lines = [
            f"Spell-check backend: {backend.name} — {backend.detail}",
            f"Thesaurus data: {thesaurus_status} ({thesaurus_engine.data_path()})",
            "",
            "User dictionary entries:",
            personal_line,
            document_line,
            project_line,
        ]
        self._show_message_box("\n".join(lines), "Dictionary Status", wx.ICON_INFORMATION | wx.OK)
        self._set_status(
            f"Spell check: {backend.name}; user dictionaries: personal={personal_count}, "
            f"document={document_count}, project={project_count}"
        )

    def choose_spell_language(self) -> None:
        """Pick the spell-check language, downloading the dictionary on demand.

        Thin delegate to :mod:`quill.ui.spell_language`; English ships bundled and
        other languages fetch from QUILL's verified release asset (PRD 10.2.4).
        """
        from quill.ui.spell_language import open_spell_language_chooser

        open_spell_language_chooser(self._wx, self)

    def _spell_review_textctrl(self, text_ctrl: object) -> None:
        """Run the F7 spelling review over a wx text control (e.g. a Mastodon post).

        Mirrors open_spell_check_dialog but targets the given control instead of
        the editor, so corrections apply to the post text before it is sent (#549
        Mastodon proofread-before-send).
        """
        from quill.ui.spell_review import review_textctrl

        review_textctrl(
            self._wx,
            self.frame,
            text_ctrl,
            dictionary=self._spell_dictionary(),
            announce_fn=self._announce,
            settings=self.settings,
            show_modal=self._show_modal_dialog,
        )
        self._invalidate_spell_dictionary_cache()

    def open_spell_check_dialog(self) -> None:
        """Open the guided F7 Spelling Review dialog, in document order."""
        self._open_spelling_review(ranked=False)

    def spell_check_ranked(self) -> None:
        """Open the guided Spelling Review dialog, most-frequent word first.

        Kurzweil-1000-style ranked spelling, community feature request:
        the same Change/Change All/Ignore/Add to Dictionary workflow as F7,
        but ordered so a single recurring OCR error or typo -- usually the
        fastest way to clear the bulk of a long list -- is always reviewed
        first. See ReviewSession(ranked=True) for how the ordering stays
        correct as issues are fixed mid-session.
        """
        self._open_spelling_review(ranked=True)

    def _open_spelling_review(self, *, ranked: bool) -> None:
        from quill.core.spelling.session import ReviewSession
        from quill.ui.spelling_review_dialog import SpellingReviewDialog

        text = self.editor.GetValue()
        if not text.strip():
            self._set_status("Document is empty — nothing to spell check.")
            return

        dictionary = self._spell_dictionary()

        # Determine scope: selection if non-empty, else full document from caret.
        sel_start, sel_end = self.editor.GetSelection()
        if sel_start != sel_end:
            scope_start, scope_end = sel_start, sel_end
            scope_label = "selected text"
        else:
            scope_start = 0
            scope_end = len(text)
            scope_label = "document"

        session = ReviewSession(
            text=text,
            dictionary=set(dictionary),
            scope_start=scope_start,
            scope_end=scope_end,
            ranked=ranked,
        )

        if session.is_complete():
            # _set_status already speaks the message (statusbar.announce); a
            # second explicit _announce spoke it twice (#728). Match the sibling
            # "No misspellings found" path and announce once via _set_status.
            self._set_status("No misspellings found.")
            return

        def _apply(start: int, old_end: int, replacement: str) -> None:
            self.editor.Replace(start, old_end, replacement)
            self.document.set_text(self.editor.GetValue())

        doc_path = getattr(self.document, "path", None)
        from pathlib import Path as _Path

        project_root = _Path.cwd()

        dlg = SpellingReviewDialog(
            parent=self.frame,
            session=session,
            apply_fn=_apply,
            announce_fn=self._announce,
            document_path=doc_path,
            project_root=project_root,
            settings=self.settings,
            scope_label=f"{scope_label}, ranked by frequency" if ranked else scope_label,
        )

        self.editor.SetFocus()  # store focus for return
        dlg.show(self._show_modal_dialog)

        # Invalidate the spell dictionary cache so subsequent inline checks
        # reflect any words the user added to the dictionary.
        self._invalidate_spell_dictionary_cache()
        counters = session.get_counters()
        if counters.reviewed:
            self._set_status(
                f"Spelling review complete: {counters.changed} changed, "
                f"{counters.ignored_once} ignored."
            )
        else:
            self._set_status("Spelling review closed.")

    def _choose_misspelling_with_context(
        self,
        misspellings: list[Misspelling],
        text: str,
        dictionary: set[str],
    ) -> int:
        wx = self._wx
        dialog = wx.Dialog(self.frame, title="Spell Check", size=(860, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose a misspelled word, then Show Corrections to see replacement "
                    "options. Tab to Context to read the nearby sentence; use Speak Word to "
                    "hear the word and its spelling."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        choices = []
        for item in misspellings:
            line, column = line_column_for_position(text, item.start)
            choices.append(f"{item.word} (Ln {line}, Col {column})")
        chooser = wx.ListBox(dialog, choices=choices)
        set_accessible_name(chooser, "Misspelled words")
        chooser.SetSelection(0 if choices else wx.NOT_FOUND)
        root.Add(chooser, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="Context"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        context_field = wx.TextCtrl(
            dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        set_accessible_name(context_field, "Context")
        root.Add(context_field, 1, wx.ALL | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        speak_button = wx.Button(dialog, label="Speak Word")
        review_button = wx.Button(dialog, id=wx.ID_OK, label="Show Corrections...")
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons.AddStretchSpacer(1)
        buttons.Add(speak_button, 0, wx.RIGHT, 8)
        buttons.Add(review_button, 0, wx.RIGHT, 8)
        buttons.Add(cancel_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizerAndFit(root)
        review_button.SetDefault()

        def refresh_context() -> None:
            selection = chooser.GetSelection()
            if selection == wx.NOT_FOUND:
                context_field.SetValue("")
                return
            item = misspellings[selection]
            context_field.SetValue(self._misspelling_context_text(text, item))

        chooser.Bind(wx.EVT_LISTBOX, lambda _event: refresh_context())
        speak_button.Bind(
            wx.EVT_BUTTON,
            lambda _event: (
                self._speak_spellcheck_word(
                    misspellings[chooser.GetSelection()].word,
                    suggest_words(misspellings[chooser.GetSelection()].word, dictionary),
                )
                if chooser.GetSelection() != wx.NOT_FOUND
                else self._set_status("Select a misspelling to speak")
            ),
        )
        review_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_CANCEL))
        refresh_context()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        result = self._show_modal_dialog(dialog, "Spell Check")
        selection = chooser.GetSelection()
        dialog.Destroy()
        if result != wx.ID_OK:
            return wx.NOT_FOUND
        return selection

    def _misspelling_context_text(self, text: str, item: Misspelling) -> str:
        if not text:
            return item.word
        boundaries = ".!?\n"
        start = item.start
        end = item.end
        sentence_start = 0
        for marker in boundaries:
            position = text.rfind(marker, 0, start)
            if position > sentence_start:
                sentence_start = position
        if sentence_start > 0:
            sentence_start += 1
        sentence_end = len(text)
        for marker in boundaries:
            position = text.find(marker, end)
            if position != -1:
                sentence_end = min(sentence_end, position + 1)
        sentence = text[sentence_start:sentence_end].strip()
        if not sentence:
            window = 80
            excerpt_start = max(0, start - window)
            excerpt_end = min(len(text), end + window)
            sentence = text[excerpt_start:excerpt_end].strip()
            if excerpt_start > 0:
                sentence = f"...{sentence}"
            if excerpt_end < len(text):
                sentence = f"{sentence}..."
        return sentence or item.word

    def _speak_spellcheck_word(self, word: str, suggestions: list[str]) -> None:
        single_suggestion = suggestions[0] if len(suggestions) == 1 else None
        message = self._spellcheck_speech_message(word, single_suggestion)
        self._speak_with_announcement_backend(message)
        if single_suggestion is None:
            self._set_status(f'Spoke misspelling "{word}" and spelling')
        else:
            self._set_status(
                f'Spoke misspelling "{word}" and single suggestion "{single_suggestion}"'
            )

    def _spellcheck_speech_message(self, word: str, single_suggestion: str | None = None) -> str:
        parts = [
            f'Misspelled word: "{word}".',
            f"Spelling: {self._spell_word_for_speech(word)}.",
        ]
        if single_suggestion is not None:
            parts.append(f'Only suggestion: "{single_suggestion}".')
            parts.append(f"Suggestion spelling: {self._spell_word_for_speech(single_suggestion)}.")
        return " ".join(parts)

    def _spell_word_for_speech(self, word: str) -> str:
        if not word:
            return "empty"
        spoken_letters: list[str] = []
        for character in word:
            if character == "-":
                spoken_letters.append("dash")
            elif character == "_":
                spoken_letters.append("underscore")
            elif character == "'":
                spoken_letters.append("apostrophe")
            elif character.isspace():
                spoken_letters.append("space")
            else:
                spoken_letters.append(character.upper())
        return ", ".join(spoken_letters)

    def _speak_with_announcement_backend(self, message: str) -> None:
        backend = getattr(self, "_announcement_engine", None)
        if backend is not None:
            backend_error = backend.announce(message)
            if backend_error and backend_error != self._announcement_error_reported:
                self._announcement_error_reported = backend_error
                self._record_notification(backend_error, "accessibility")
            if backend_error is None and backend.state().active_backend != "status_only":
                return  # a real backend (prism / accessible_output2 / speech) already spoke
        announce(message)

    def open_misspelling_list(self) -> None:
        dictionary = self._spell_dictionary()
        misspellings = list_misspellings(self.editor.GetValue(), dictionary)
        if not misspellings:
            self._set_status("No misspellings found")
            return
        nodes = self._build_misspelling_navigator_nodes(misspellings)
        selected = self._show_tree_navigator(
            title="Misspelling List",
            root_label="Misspellings",
            nodes=nodes,
        )
        if not isinstance(selected, Misspelling):
            self._set_status("Misspelling list cancelled")
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(selected.start)
        else:
            self.editor.SetInsertionPoint(selected.start)
            self.editor.SetSelection(selected.start, selected.end)
        self.editor.SetFocus()
        self._location_ring.record(selected.start)
        self._set_status(f'Jumped to misspelling "{selected.word}"')

    def open_misspelling_list_ranked(self) -> None:
        """Kurzweil-1000-style "ranked spelling": most-frequent misspelling first.

        Community feature request. Same dialog as List Misspellings, but
        ordered by how often each word recurs rather than document position --
        fixing a single OCR misread or repeated typo (e.g. "teh" for "the")
        this way clears the bulk of a long list in a handful of steps.
        """
        dictionary = self._spell_dictionary()
        misspellings = rank_misspellings_by_frequency(
            list_misspellings(self.editor.GetValue(), dictionary)
        )
        if not misspellings:
            self._set_status("No misspellings found")
            return
        nodes = self._build_misspelling_navigator_nodes(misspellings, show_counts=True)
        selected = self._show_tree_navigator(
            title="Misspelling List (Ranked by Frequency)",
            root_label="Misspellings, most frequent first",
            nodes=nodes,
        )
        if not isinstance(selected, Misspelling):
            self._set_status("Ranked misspelling list cancelled")
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(selected.start)
        else:
            self.editor.SetInsertionPoint(selected.start)
            self.editor.SetSelection(selected.start, selected.end)
        self.editor.SetFocus()
        self._location_ring.record(selected.start)
        self._set_status(f'Jumped to misspelling "{selected.word}"')

    def _misspellings_behind_message(
        self, text: str, cursor: int, dictionary: set[str], *, ahead: bool
    ) -> str:
        """Build the spoken "none in this direction" result for F7/F8.

        F7/F8 search forward/backward from the caret and don't wrap, so right
        after typing a misspelling the caret sits past it and there is no *next*
        one -- the bare "No next misspelling" was both misleading and silent
        under a screen reader (#9). Count the misspellings in the other
        direction so the user knows to reverse instead of assuming the document
        is clean."""
        direction = "ahead" if ahead else "behind"
        other_key = "behind" if ahead else "ahead"
        other = (
            find_previous_misspelling(text, cursor, dictionary)
            if ahead
            else find_next_misspelling(text, cursor, dictionary)
        )
        if other is None:
            return "No misspellings found"
        count = sum(1 for m in list_misspellings(text, dictionary) if (m.end <= cursor) == ahead)
        plural = "" if count == 1 else "s"
        return f"No misspellings {direction}; {count} misspelling{plural} {other_key}"

    def next_misspelling(self) -> None:
        dictionary = self._spell_dictionary()
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        item = find_next_misspelling(text, cursor, dictionary)
        if item is None:
            message = self._misspellings_behind_message(text, cursor, dictionary, ahead=True)
            self._announce_result(message)
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(item.start)
        else:
            self.editor.SetInsertionPoint(item.start)
            self.editor.SetSelection(item.start, item.end)
        self.editor.SetFocus()
        self._set_status(f'Next misspelling: "{item.word}"')

    def previous_misspelling(self) -> None:
        dictionary = self._spell_dictionary()
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        item = find_previous_misspelling(text, cursor, dictionary)
        if item is None:
            message = self._misspellings_behind_message(text, cursor, dictionary, ahead=False)
            self._announce_result(message)
            return
        self._record_location_before_jump()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(item.start)
        else:
            self.editor.SetInsertionPoint(item.start)
            self.editor.SetSelection(item.start, item.end)
        self.editor.SetFocus()
        self._set_status(f'Previous misspelling: "{item.word}"')

    def spell_check_word_at_cursor(self) -> None:
        """Instantly check the word at (or nearest) the caret -- no full-document
        review, no context menu. Mirrors the MS-Office-style "F7 on a focused
        word" workflow: one keystroke, one word, a suggestion list, done.

        If the word is spelled correctly, announces that and returns immediately
        -- no dialog for the common case. If it's misspelled, offers the same
        suggestions/Add/Ignore choices as the right-click context menu, just
        reachable without a mouse or the Menu/Application key.
        """
        wx = self._wx
        text = self.editor.GetValue()
        caret = self.editor.GetInsertionPoint()
        dictionary = self._spell_dictionary()
        misspelling = misspelling_at_position(text, caret, dictionary)
        if misspelling is None:
            sel_start, sel_end = self.editor.GetSelection()
            if sel_end > sel_start:
                word = text[sel_start:sel_end]
                if not is_known_word(word, dictionary):
                    misspelling = Misspelling(word=word, start=sel_start, end=sel_end)
        if misspelling is None:
            self._set_status("No misspelling at the cursor")
            return

        suggestions = suggest_words(misspelling.word, dictionary)
        choices = list(suggestions) + ["Add to Dictionary", "Ignore"]
        with wx.SingleChoiceDialog(
            self.frame,
            f'"{misspelling.word}" is not in the dictionary. Choose a correction:',
            "Spell Check Word",
            choices=choices,
        ) as dialog:
            if hasattr(dialog, "SetSelection"):
                dialog.SetSelection(0)
            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            if self._show_modal_dialog(dialog, "Spell Check Word") != wx.ID_OK:
                self._set_status("Spell check word cancelled")
                return
            choice = dialog.GetStringSelection()

        if choice == "Add to Dictionary":
            self._add_word_to_dictionary_scope(misspelling.word, 0)
            return
        if choice == "Ignore":
            self._add_word_to_dictionary_scope(misspelling.word, 1)
            return
        self.editor.Replace(misspelling.start, misspelling.end, choice)
        self.document.set_text(self.editor.GetValue())
        self._set_status(f'Replaced "{misspelling.word}" with "{choice}"')

    def show_thesaurus(self) -> None:
        """Open the thesaurus for the selected word or the word under the caret."""
        wx = self._wx
        if not thesaurus_engine.is_available():
            message = (
                "The thesaurus data file is not installed.\n\n"
                f"Expected location:\n  {thesaurus_engine.data_path()}\n\n"
                "To enable the thesaurus, install the optional English thesaurus "
                "data file (LibreOffice MyThes en_US, ~18 MB). Reinstall Quill "
                "with the thesaurus component, or copy 'th_en_US_v2.dat' into "
                "the data folder shown above."
            )
            self._show_message_box(message, "Thesaurus Not Installed", wx.ICON_INFORMATION | wx.OK)
            self._set_status("Thesaurus data not installed")
            return

        # Determine the word to look up: selection takes priority, else the
        # word at the caret.
        text = self.editor.GetValue()
        sel_start, sel_end = self.editor.GetSelection()
        word: str | None = None
        word_start: int | None = None
        word_end: int | None = None
        if sel_end > sel_start:
            candidate = text[sel_start:sel_end].strip()
            if candidate and all(ch.isalpha() or ch == "'" for ch in candidate):
                word = candidate
                word_start = sel_start
                word_end = sel_end
        if word is None:
            located = thesaurus_engine.word_at(text, self.editor.GetInsertionPoint())
            if located is not None:
                word, word_start, word_end = located

        if not word:
            with wx.TextEntryDialog(
                self.frame,
                "Look up word in thesaurus:",
                "Thesaurus",
                value="",
            ) as dialog:
                if self._show_modal_dialog(dialog, "Thesaurus") != wx.ID_OK:
                    return
                word = dialog.GetValue().strip()
                if not word:
                    self._set_status("Thesaurus: no word entered")
                    return

        entry = thesaurus_engine.lookup(word)
        if entry is None:
            self._set_status(f'No thesaurus entry for "{word}"')
            self._show_message_box(
                f'No thesaurus entries were found for "{word}".',
                "Thesaurus",
                wx.ICON_INFORMATION | wx.OK,
            )
            return

        # Build a flat choice list grouped by part of speech so screen
        # readers announce the grouping naturally.
        choices: list[str] = []
        choice_words: list[str] = []
        for meaning in entry.meanings:
            pos = meaning.part_of_speech or "other"
            for synonym in meaning.synonyms:
                choices.append(f"[{pos}] {synonym}")
                choice_words.append(synonym)

        if not choices:
            self._set_status(f'No synonyms available for "{word}"')
            return

        replace_allowed = word_start is not None and word_end is not None
        prompt = f'Synonyms for "{word}":\n\nChoose one to copy to the clipboard' + (
            " or replace the word in the editor." if replace_allowed else "."
        )

        with wx.SingleChoiceDialog(
            self.frame,
            prompt,
            "Thesaurus",
            choices=choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Thesaurus") != wx.ID_OK:
                self._set_status("Thesaurus closed")
                return
            selection = dialog.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        chosen = choice_words[selection]

        if replace_allowed:
            actions = ["Replace word in editor", "Copy to clipboard"]
            with wx.SingleChoiceDialog(
                self.frame,
                f'Use "{chosen}":',
                "Thesaurus",
                choices=actions,
            ) as action_dialog:
                if self._show_modal_dialog(action_dialog, "Thesaurus") != wx.ID_OK:
                    return
                action = action_dialog.GetSelection()
        else:
            action = 1  # copy to clipboard

        if action == 0 and replace_allowed:
            # Preserve the original word's leading capitalisation.
            replacement = chosen
            if word[:1].isupper():
                replacement = chosen[:1].upper() + chosen[1:]
            self.editor.Replace(word_start, word_end, replacement)
            self.document.set_text(self.editor.GetValue())
            self._set_status(f'Replaced "{word}" with "{replacement}"')
        else:
            self._copy_text_to_clipboard(chosen)
            self._set_status(f'Copied "{chosen}" to clipboard')

    def _copy_text_to_clipboard(self, text: str) -> bool:
        wx = self._wx
        clipboard = wx.TheClipboard
        if not clipboard.Open():
            self._set_status("Clipboard is unavailable")
            return False
        try:
            clipboard.SetData(wx.TextDataObject(text))
            # Flush so the data survives if the app exits soon after.
            try:
                clipboard.Flush()
            except Exception:
                pass
            return True
        finally:
            clipboard.Close()

    def _announce_spellcheck_hint(self) -> None:
        if not getattr(self.settings, "announce_spelling", True):
            self._last_live_misspelling_feedback = None
            return
        dictionary = self._spell_dictionary()
        cursor = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        item = find_next_misspelling(text, cursor - 1, dictionary)
        if item is None or item.start != cursor:
            self._last_live_misspelling_feedback = None
            return
        if live_alert_suppressed(text, item.start, item.end):
            self._last_live_misspelling_feedback = None
            return
        key = (item.word.lower(), item.start, item.end)
        now = time.monotonic()
        if (
            self._last_live_misspelling_feedback == key
            and now - self._last_live_misspelling_feedback_at < 0.75
        ):
            return
        self._last_live_misspelling_feedback = key
        self._last_live_misspelling_feedback_at = now
        self._play_spelling_alert()
        self._set_status(f'Possible misspelling: "{item.word}"')

    def _play_spelling_alert(self) -> None:
        # Prefer the pack earcon; fall back to the system bell only when the
        # sound system is off or the active pack has no spelling_alert sound,
        # so the alert is never silently lost.
        from quill.core.sound_events import SoundEvent
        from quill.ui import sound_manager

        if sound_manager.is_active() and str(SoundEvent.SPELLING_ALERT) in (
            sound_manager.get_loaded_events()
        ):
            sound_manager.post_sound(SoundEvent.SPELLING_ALERT)
            return
        bell = getattr(self._wx, "Bell", None)
        if callable(bell):
            bell()

    def _spell_dictionary(self) -> set[str]:
        # Cache the combined dictionary keyed by (document path, project root).
        # Reading + parsing the three JSON scope files on every keystroke (via
        # "spell check as you type") is wasteful; we invalidate the cache when
        # a word is added or the active document changes.
        project_root = Path.cwd()
        cache_key = (self.document.path, project_root)
        cached = getattr(self, "_spell_dictionary_cache", None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        dictionary = load_combined_dictionary(self.document.path, project_root)
        self._spell_dictionary_cache = (cache_key, dictionary)
        return dictionary

    def _invalidate_spell_dictionary_cache(self) -> None:
        self._spell_dictionary_cache = None

    def _add_word_to_dictionary_scope(self, word: str, scope_index: int) -> None:
        if scope_index == 0:
            add_word_to_scope(word, "personal", self.document.path, Path.cwd())
        elif scope_index == 1:
            add_word_to_scope(word, "document", self.document.path, Path.cwd())
        elif scope_index == 2:
            add_word_to_scope(word, "project", self.document.path, Path.cwd())
        else:
            return
        self._invalidate_spell_dictionary_cache()
        self._set_status(f'Added "{word}" to dictionary')
