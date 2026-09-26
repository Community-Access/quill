"""The AI menu, built in two halves: the free service, and everything else.

Extracted from :mod:`quill.ui.main_frame_menu` (GATE-11) along the seam the
2026-09-23 change created rather than an arbitrary line count. That change made
QUILL's own free AI the **front door** of the AI menu and put the whole
provider-and-agent surface behind one remembered checkbox, which turned one long
block of menu building into two clearly different jobs:

* :meth:`_build_hosted_ai_rows` -- the five rows QUILL's own service is reached
  through, shown in both modes, identical in words and chords to QUILL Lite's
  because they run the same shared code
  (:mod:`quill.ui.hosted_ai_commands`).
* :meth:`_build_advanced_ai_rows` -- provider setup, Ask Quill, the agents, the
  seven task submenus, the Library and the Hub. Everything here assumes a
  decision about which company sees your writing and an API key pasted
  somewhere, which is exactly what Basic mode exists to let somebody skip.
* :meth:`_append_ai_experience_toggle` -- the checkbox that moves between them.

Nothing is *removed* in Basic: every advanced command keeps its chord and stays
in the command palette. The mode changes what is offered, never what exists --
which is what makes it safe to default a new install to Basic.
"""

from __future__ import annotations

from quill.core.i18n import _

__all__ = ["AiMenuMixin"]


class AiMenuMixin:
    """The AI menu's two halves and the switch between them."""

    def _build_hosted_ai_rows(self, ai_menu) -> None:
        """QUILL's own free AI, the five rows, identical in Basic and Advanced.

        Same five commands, same chords and the same shared code as QUILL Lite
        (:mod:`quill.ui.hosted_ai_commands`), because it is one capability.

        The labels carry one word QUILL Lite's do not -- **Free** -- and it is
        load-bearing rather than promotional: somebody who has been trained by
        every other editor to expect a subscription prompt behind an AI menu
        needs to be told, on the row, that this one is not that. The mnemonics
        differ from QUILL Lite's for a duller reason: A, U, S and P are all
        claimed elsewhere in *this* menu once the advanced rows are showing, and
        a duplicate mnemonic is a key Windows may silently refuse to press.
        """
        ai_menu.Append(
            self._id_hosted_ai_assistant,
            self._menu_label(_("Fr&ee AI Assistant..."), "tools.hosted_ai_assistant"),
        )
        ai_menu.Append(
            self._id_hosted_ai_ask_document,
            self._menu_label(_("Ask About This &Document..."), "tools.hosted_ai_ask_document"),
        )
        ai_menu.Append(
            self._id_hosted_ai_usage,
            self._menu_label(_("Free AI Usa&ge..."), "tools.hosted_ai_usage"),
        )
        ai_menu.Append(
            self._id_hosted_ai_sign_in,
            self._menu_label(_("&Connect or Sign Out..."), "tools.hosted_ai_sign_in"),
        )
        # Reachable with the feature switched off, deliberately: the agreement is
        # how somebody turns it on, and a row that appears only once you have
        # already agreed is a door on the inside of the room.
        ai_menu.Append(
            self._id_hosted_ai_privacy,
            self._menu_label(_("Privac&y Agreement..."), "tools.hosted_ai_privacy"),
        )
        self._append_own_key_row(ai_menu)  # quill/ui/main_frame_hosted_ai.py

    def _build_advanced_ai_rows(self, ai_menu) -> None:
        """Everything the AI menu used to open with, now one checkbox away."""
        wx = self._wx
        from quill.ui.agent_editor_host import append_action_ring_menu, append_agent_menu
        from quill.ui.ai_menu_setup import append_ai_setup_items
        from quill.ui.concierge_menu import append_concierge_action

        # -- Set Up AI, general and local (the gentle on-ramps) ----------------
        # Both rows live in quill/ui/ai_menu_setup.py (GATE-11 extraction);
        # the local row is the guided Ollama path issue #1558 asked for.
        append_ai_setup_items(self, ai_menu)
        ai_menu.AppendSeparator()

        # -- The conversation (the front door) --------------------------------
        ai_menu.Append(
            self._id_ask_quill_chat,
            self._menu_label(_("&Ask Quill..."), "tools.ask_quill_chat"),
        )
        ai_menu.Append(
            self._id_ask_quill_voice,
            self._menu_label(_("Ask Quill by &Voice..."), "tools.ask_quill_conversation"),
        )
        ai_menu.Append(
            self._id_voice_reply_settings,
            self._menu_label(_("Voice &Reply Settings..."), "tools.voice_reply_settings"),
        )
        ai_menu.AppendSeparator()

        # -- Context actions + agents -----------------------------------------
        # Accessibility Tune-Up stays first-class for the screen-reader audience.
        ai_menu.Append(
            self._id_ai_accessibility_agent,
            self._menu_label(_("Accessibility &Tune-Up..."), "tools.ai_accessibility_agent"),
        )
        # "What can I do here?" is generated by the Concierge from live context;
        # "Rewrite & Improve" is the Selection Action Ring for the current file
        # type; "Run Agent" lists the full catalog. No second Basic check here:
        # this whole method only runs in Advanced now, and a gate inside a gate
        # is a gate that will disagree with the other one eventually.
        append_concierge_action(self, ai_menu)
        append_action_ring_menu(self, ai_menu)
        append_agent_menu(self, ai_menu)
        ai_menu.AppendSeparator()

        # -- Proofread --------------------------------------------------------
        proofread_menu = wx.Menu()
        proofread_menu.Append(
            self._id_check_grammar_ai,
            self._menu_label(_("Check Grammar with &AI..."), "tools.check_grammar_ai"),
        )
        proofread_menu.Append(
            self._id_ai_grammar_style,
            self._menu_label(_("&Grammar and Style Check..."), "tools.ai_grammar_style"),
        )
        proofread_menu.Append(
            self._id_ai_spell_check,
            self._menu_label(_("&Spell Check..."), "tools.ai_spell_check"),
        )
        proofread_menu.Append(
            self._id_ai_spell_check_interactive,
            self._menu_label(_("Spell Check &Interactive..."), "tools.ai_spell_check_interactive"),
        )
        ai_menu.AppendSubMenu(proofread_menu, _("&Proofread"))

        # -- Transform Selection (single-shot verbs; canonical Ctrl+Alt+Shift+ chords)
        transform_menu = wx.Menu()
        transform_menu.Append(
            self._id_ai_rewrite_selection,
            self._menu_label(_("&Rewrite Selection"), "tools.ai_rewrite_selection"),
        )
        transform_menu.Append(
            self._id_ai_summarize_selection,
            self._menu_label(_("&Summarize Selection"), "tools.ai_summarize_selection"),
        )
        transform_menu.Append(
            self._id_ai_expand_selection,
            self._menu_label(_("E&xpand Selection"), "tools.ai_expand_selection"),
        )
        transform_menu.Append(
            self._id_ai_continue_writing,
            self._menu_label(_("&Continue Writing"), "tools.ai_continue_writing"),
        )
        transform_menu.Append(
            self._id_ai_fix_grammar,
            self._menu_label(_("Fix &Grammar"), "tools.ai_fix_grammar"),
        )
        transform_menu.Append(
            self._id_ai_generate_toc,
            self._menu_label(_("Generate &Table of Contents"), "tools.ai_generate_toc"),
        )
        ai_menu.AppendSubMenu(transform_menu, _("Trans&form Selection"))

        # -- Translate --------------------------------------------------------
        translate_menu = wx.Menu()
        translate_menu.Append(
            self._id_ai_translate_selection,
            self._menu_label(_("Translate &Selection..."), "tools.ai_translate_selection"),
        )
        translate_menu.Append(
            self._id_ai_translate_document,
            self._menu_label(_("Translate &Document..."), "tools.ai_translate_document"),
        )
        ai_menu.AppendSubMenu(translate_menu, _("Tra&nslate"))

        # -- Read Aloud (AI voice) --------------------------------------------
        read_aloud_menu = wx.Menu()
        read_aloud_menu.Append(
            self._id_ai_tts_read_selection,
            self._menu_label(_("&Read Selection Aloud"), "tools.ai_tts_read_selection"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_read_document,
            self._menu_label(_("Read &Document Aloud"), "tools.ai_tts_read_document"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_stop,
            self._menu_label(_("Sto&p AI Reading"), "tools.ai_tts_stop"),
        )
        read_aloud_menu.Append(
            self._id_ai_tts_export_mp3,
            self._menu_label(_("E&xport Document as Audio..."), "tools.ai_tts_export_mp3"),
        )
        ai_menu.AppendSubMenu(read_aloud_menu, _("Read A&loud"))

        # -- Transcribe audio -------------------------------------------------
        transcribe_menu = wx.Menu()
        # One entry: the dialog's "Translate audio to English" checkbox covers
        # translation, so a separate Translate menu item would open the same dialog.
        transcribe_menu.Append(
            self._id_ai_transcribe_audio,
            self._menu_label(_("Transcri&be Audio File..."), "tools.ai_transcribe_audio"),
        )
        # The Listening Companion: run a Transcript Action (Meeting Minutes, Action
        # Items, Clean Up & Draft, ...) on the current selection or document — the same
        # magic offered after transcription, reachable anytime. Bound directly so the
        # size-budgeted main_frame module does not need to grow.
        from quill.ui.transcript_actions_ui import run_transcript_actions_on_document

        transcribe_menu.AppendSeparator()
        _ta_actions_id = wx.NewIdRef()
        transcribe_menu.Append(_ta_actions_id, _("Transcript &Actions..."))
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: run_transcript_actions_on_document(self),
            id=_ta_actions_id,
        )
        ai_menu.AppendSubMenu(transcribe_menu, _("Transcri&be Audio"))

        # -- More -------------------------------------------------------------
        more_menu = wx.Menu()
        more_menu.Append(
            self._id_ai_document_qa,
            self._menu_label(_("Document &Q&&A..."), "tools.ai_document_qa"),
        )
        more_menu.Append(
            self._id_ai_reading_order,
            self._menu_label(_("Improve &Reading Order..."), "tools.ai_reading_order"),
        )
        more_menu.Append(
            self._id_ai_thesaurus,
            self._menu_label(_("AI T&hesaurus..."), "tools.ai_thesaurus"),
        )
        more_menu.Append(
            self._id_train_style,
            self._menu_label(_("&Train Writing Style..."), "tools.train_writing_style"),
        )
        more_menu.Append(
            self._id_writing_instructions,
            self._menu_label(_("&Writing Instructions..."), "tools.writing_instructions"),
        )
        ai_menu.AppendSubMenu(more_menu, _("&More"))
        ai_menu.AppendSeparator()

        # -- AI Library (Prompts / Skills / Agents — one unified manager) -----
        # Prompts, Skills, and Agents now live in one tabbed manager with a single
        # verb set and the Promote continuum. Prompt Studio, Writing Assistant,
        # Agent Center, and Validate Agents remain reachable as commands during the
        # deprecation window, but no longer scatter the menu.
        ai_menu.Append(
            self._id_ai_library,
            self._menu_label(_("A&I Library..."), "tools.ai_library"),
        )

        # -- Configuration ----------------------------------------------------
        # The AI Hub is the single config front door. Engine switching, GitHub
        # Copilot setup, and Session Branches all now live inside the Hub (its
        # Engines and Sessions tabs), so the old "Engine & Sessions" submenu is
        # gone entirely — the menu keeps only the Hub and the Use AI switch.
        ai_menu.Append(
            self._id_ai_hub,
            self._menu_label(_("AI &Hub..."), "tools.ai_hub"),
        )
        ai_menu.AppendSeparator()
        # "Forget API Key" moved into the AI Hub as a per-provider action
        # ("Forget this provider's key"), since a single global forget is
        # ambiguous once each provider keeps its own key.

    def _append_ai_experience_toggle(self, ai_menu) -> None:
        """Basic vs Advanced, as one remembered checkbox at the foot of the menu.

        This is the whole of the escape hatch, and it is deliberately in the menu
        it governs rather than in Settings: somebody who has just noticed that
        the AI menu is short should find the way to the long one without leaving
        it. Nothing is lost in Basic -- every advanced command keeps its chord
        and stays in the command palette -- so the checkbox changes what is
        *offered*, never what exists.
        """
        wx = self._wx
        from quill.core.ai.onboarding import (
            EXPERIENCE_ADVANCED,
            EXPERIENCE_BASIC,
            is_basic_mode,
            save_experience_mode,
        )

        _adv_id = wx.NewIdRef()
        adv_item = ai_menu.AppendCheckItem(_adv_id, _("&Show advanced AI features"))
        adv_item.Check(not is_basic_mode())

        def _toggle_experience(_event: object) -> None:
            # Flip the saved mode: advanced <-> basic. Reading is_basic_mode() to pick the
            # *same* value (the original code) was a no-op — the mode never changed, so the
            # menu never toggled.
            save_experience_mode(EXPERIENCE_ADVANCED if is_basic_mode() else EXPERIENCE_BASIC)
            # The rows are appended once while the menu is built and gated on the
            # mode; a contextual refresh only enables and disables what is already
            # there and would never add or remove a row. Rebuild the whole menu
            # bar, deferred so it happens after this selection event has finished
            # dispatching.
            self._wx.CallAfter(self._build_menu)

        self.frame.Bind(wx.EVT_MENU, _toggle_experience, id=_adv_id)
