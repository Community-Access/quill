"""Quill Media Player reaches the family's AI through the shared small-app adapter.

codex.md Phase 3 (10E.8). The player had two AI commands, Summarize This
Chapter and AI Recap of Where I Am, and both ran on QUILL's AI Hub own key and
nothing else. Now the player runs the shared hosted AI through
:class:`~quill.ui.hosted_ai_app_adapter.AppAiMixin` -- hooks only -- with its
own "QUILL Media Player" sign-in, so Choose Your AI, Which AI Am I Using, the
one AI Usage list, the AI line in the main window and Safe Mode's refusal all
come from the code every app shares.

What the player *does* with AI is :class:`PlayerAiFeaturesMixin`:

* **Ask** (Ctrl+Shift+8, AI > Ask...) about the book: its title, the chapter,
  the place in it and the list of chapters (``app_ask_context.player_context``
  plus a Chapters fact), read fresh for each question.
* **Summarize This Chapter (AI)** (Ctrl+Alt+C) and **AI Recap of Where I Am**
  (Ctrl+Alt+R): the two recaps, on whichever AI is in use. They stay in the
  Playback menu on the keys they always had (rule 5); they are not repeated in
  the AI menu, because a key claimed twice in one bar fails the gate.
* **Find the Part Where...** (Ctrl+F3): the agent task
  (:mod:`quill.apps.player_ai_task`): finds a place by chapters, bookmarks and
  times and moves there after asking. There is no transcript source.

**Audio never leaves.** The text a recap is made from is the book's own, or a
transcript of at most five minutes made on this computer
(:mod:`quill.ui.media.recap_actions`), found off the UI thread. Protected BARD
content is refused before anything is gathered, and an answer is remembered per
book and chapter so asking again sends nothing.

**Keys.** Ctrl+1 to Ctrl+9 are the Window menu's, so Ask is Ctrl+Shift+8, Which
AI Ctrl+F8 and Choose Your AI Ctrl+Shift+F8, as in Quill Radio, QUILL Cast and
Quill Weather (``app_keymaps.py``, ``app_ai_keys.py``).
"""

from __future__ import annotations

from typing import Any

from quill.ui.hosted_ai_app_adapter import AppAiMixin

__all__ = [
    "AGENT_NAME",
    "AI_ROWS",
    "CHAPTER_SUMMARY_TITLE",
    "RECAP_ROWS",
    "RECAP_TITLE",
    "PlayerAiFeaturesMixin",
    "PlayerAiMixin",
]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Media Player"
CHAPTER_SUMMARY_TITLE = "Chapter Summary"
RECAP_TITLE = "Recap"

#: How many chapters Ask's Chapters fact names before it says how many more.
_MAX_CHAPTERS = 80

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C F H O S P). The recaps are not here: they live
#: in the Playback menu (RECAP_ROWS).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("tools.hosted_ai_task", "&Find the Part Where...", "cmd_ai_task"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)

#: The two recaps, in the Playback menu where they have always been, with the
#: same labels and keys (rule 5: nothing moves).
RECAP_ROWS: tuple[tuple[str, str, str], ...] = (
    ("player.ai_chapter_summary", "Summarize This &Chapter (AI)", "cmd_player_chapter_summary"),
    ("player.ai_recap", "AI &Recap of Where I Am", "cmd_player_recap"),
)


class PlayerAiFeaturesMixin:
    """The two recaps and the book facts Ask reads. Mixed in through ``PlayerAiMixin``."""

    # -- the Playback menu's two rows ------------------------------------------ #

    def _append_player_recap_rows(self, menu: Any) -> None:
        """Summarize This Chapter and AI Recap of Where I Am, labelled with their keys."""
        import wx

        for command_id, label, handler_name in RECAP_ROWS:
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(label, command_id))  # type: ignore[attr-defined]
            handler = getattr(self, handler_name)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)  # type: ignore[attr-defined]
            self._keep_menu_ids(item_id)  # type: ignore[attr-defined]
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                label.replace("&", ""),
                handler,
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )

    # -- the commands ---------------------------------------------------------- #

    def cmd_ai_task(self) -> None:
        """Find the Part Where (Ctrl+F3, codex.md 6.11): find a place by chapters,
        bookmarks and times in the shared agent window, and move there after
        asking. No transcript is made; the audio never leaves."""
        from quill.apps.player_ai_task import (
            FIND_THE_PART,
            INSTRUCTION_HELP,
            player_task_facts,
            player_task_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            FIND_THE_PART,
            lambda ctx: player_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            context=lambda: player_task_facts(self),
        )

    def cmd_player_chapter_summary(self) -> None:
        """Summarize This Chapter (AI) (Ctrl+Alt+C), on the AI in use."""
        self._player_recap("chapter")

    def cmd_player_recap(self) -> None:
        """AI Recap of Where I Am (Ctrl+Alt+R), on the AI in use."""
        self._player_recap("recap")

    def _player_recap(self, kind: str) -> None:
        from quill.core.media.recap import recap_prompt
        from quill.ui.media import recap_actions

        if self._ai_refuse_safe_mode():  # type: ignore[attr-defined]
            return
        if not self._book_key and self._book_path is None:  # type: ignore[attr-defined]
            from quill.apps.player import _TITLE

            self._show_message_box("Open a book first.", _TITLE)  # type: ignore[attr-defined]
            return
        ctx = self._player_recap_context(kind)
        if recap_actions.is_protected(ctx.book_key):
            self._announce(recap_actions.BARD_REFUSAL)  # type: ignore[attr-defined]
            return
        if not self._ai_ready() or not self._ai_capable("text"):  # type: ignore[attr-defined]
            return
        title = CHAPTER_SUMMARY_TITLE if kind == "chapter" else RECAP_TITLE
        service = recap_actions.recap_service()
        cached = service.cached(kind, ctx)
        if cached:
            self._app_ai_show(cached, title=title)  # type: ignore[attr-defined]
            return

        def answered(text: str) -> None:
            service.remember(kind, ctx, text)
            self._app_ai_show(text or "No summary was produced.", title=title)  # type: ignore[attr-defined]

        def got_text(text: str) -> None:
            self._app_ai_request(  # type: ignore[attr-defined]
                recap_prompt(kind, text), answered, working="Asking the AI."
            )

        starting = "Summarizing this chapter." if kind == "chapter" else "Recapping where you are."
        self._announce(f"{starting} This may take a moment.")  # type: ignore[attr-defined]
        recap_actions.gather_in_background(service, ctx, got_text, self._announce)  # type: ignore[attr-defined]

    def _player_recap_context(self, kind: str) -> Any:
        """The chapter and the stretch of audio a recap is made from.

        A chapter summary covers the chapter; a recap covers the chapter's start
        up to the current point (the transcript is capped at five minutes).
        """
        from quill.core.media import ChapterContext

        index = self._player.current_chapter_index()  # type: ignore[attr-defined]
        chapters = self._chapters  # type: ignore[attr-defined]
        title, start, duration = "", 0, 0
        if 0 <= index < len(chapters):
            chapter = chapters[index]
            title = getattr(chapter, "title", "")
            start = int(getattr(chapter, "start_ms", 0))
            duration = int(getattr(chapter, "duration_ms", 0))
        if kind == "recap":
            playhead = self._player.playhead_ms()  # type: ignore[attr-defined]
            duration = max(1_000, playhead - start)
        book_path = self._book_path  # type: ignore[attr-defined]
        return ChapterContext(
            book_key=self._book_key or "book",  # type: ignore[attr-defined]
            chapter_index=index,
            title=title,
            text=None,
            audio_path=str(book_path) if book_path else "",
            start_ms=start,
            duration_ms=duration,
        )

    # -- what Ask is told ---------------------------------------------------------- #

    def _player_ai_place(self) -> tuple[str, int, int]:
        """The chapter's title, its number from one, and how many there are."""
        chapters = self._chapters  # type: ignore[attr-defined]
        if chapters:
            index = self._player.current_chapter_index()  # type: ignore[attr-defined]
            if 0 <= index < len(chapters):
                return str(getattr(chapters[index], "title", "")), index + 1, len(chapters)
            return "", 0, len(chapters)
        playlist = self._playlist  # type: ignore[attr-defined]
        index = self._playlist_index  # type: ignore[attr-defined]
        if 0 <= index < len(playlist):
            return str(playlist[index][0]), index + 1, len(playlist)
        return "", 0, len(playlist)

    def _player_chapter_listing(self) -> str:
        """The book's chapters (or tracks), one a line, indented by heading level."""
        nodes = self._chapter_nodes  # type: ignore[attr-defined]
        lines = [
            f"{'  ' * max(0, int(depth) - 1)}{number}. {title}"
            for number, (title, _payload, depth) in enumerate(nodes[:_MAX_CHAPTERS], start=1)
        ]
        if len(nodes) > _MAX_CHAPTERS:
            lines.append(f"... and {len(nodes) - _MAX_CHAPTERS} more")
        return "\n".join(lines)


class PlayerAiMixin(PlayerAiFeaturesMixin, AppAiMixin):
    """The shared hosted-AI commands on Quill Media Player's frame: hooks, no commands."""

    _AI_APP = "player"
    _AI_AGENT_NAME = AGENT_NAME
    _AI_ROWS = AI_ROWS
    _AI_SUBJECT = "this book"
    _AI_ABOUT_FACTS = (
        "the book's title, the chapter, your place in it and the list of chapters; never the audio"
    )

    def _app_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts: the book, the chapter, the place and the chapter list."""
        del question, needs
        from quill.core.ai.app_ask_context import AppFacts, Fact, player_context

        if not self._book_key and self._book_path is None:  # type: ignore[attr-defined]
            return AppFacts("player", (Fact("Book", "no book is open"),))
        title, number, count = self._player_ai_place()
        try:
            position_s: float | None = self._player.playhead_ms() / 1000.0  # type: ignore[attr-defined]
            duration_s: float | None = self._player.length_ms() / 1000.0  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no engine: the place is unknown, not an error
            position_s = duration_s = None
        context = player_context(
            self._now_playing.GetValue(),  # type: ignore[attr-defined]
            chapter_title=title,
            chapter_number=number,
            chapter_count=count,
            position_s=position_s,
            duration_s=duration_s or None,
        )
        listing = self._player_chapter_listing()
        if not listing:
            return context
        return AppFacts("player", context.facts + (Fact("Chapters", listing),))

    def _app_ai_purpose(self) -> str:
        from quill.core.media.surface_help import purpose_for_title

        return purpose_for_title("Quill Media Player")
