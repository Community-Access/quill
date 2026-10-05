"""QUILL Cast's own AI features, on top of the family's shared AI (ear.md A2-A9).

:class:`~quill.ui.podcasts.cast_ai_host.CastAiMixin` is the adapter and has no
command of its own -- a test holds it to that. These are Cast's *domain*
features, the ones the editors cannot have because they have no podcast
library, and every one sends its question through the same shared service
(:meth:`_ai_service`), behind the same switch and agreement (:meth:`_ai_ready`).

Each follows ear.md's safety shape: it asks only when you ask; it sends titles,
descriptions and notes, never an address, a path or a position; what it
proposes goes through :func:`~quill.ui.podcasts.ai_review_dialog.review`, and
nothing is written until Apply; what it could not match is counted aloud.

Tidy the Podcasts I Follow sends nothing anywhere: it works from what Cast already
knows, so it works with AI help switched off.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import ai_listening as ai

__all__ = ["AI_FEATURE_ROWS", "CastDomainAiMixin"]

#: The Help > AI Features rows these add: command id, label, handler name.
#: Letters avoid the shared rows' E N G C Y O U K.
AI_FEATURE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("podcasts.ai_organise", "Organise My &Podcasts...", "ai_organise_podcasts"),
    ("podcasts.ai_about", "&What Is This Podcast About?", "ai_about_podcast"),
    ("podcasts.ai_for_me", "Is This Episode &for Me?", "ai_for_me"),
    ("podcasts.ai_summary", "&Summarise This Episode", "ai_summarise_episode"),
    ("podcasts.ai_run", "Build Me a &Listening Run...", "ai_listening_run"),
    ("podcasts.ai_playlist", "Smart Playlist from a Sen&tence...", "ai_playlist_from_sentence"),
    ("podcasts.ai_chapters", "Name These C&hapters...", "ai_name_chapters"),
    ("podcasts.tidy", "T&idy the Podcasts I Follow...", "tidy_subscriptions"),
)


class CastDomainAiMixin:
    """Cast's AI verbs. Mixed into ``PodcastsAppFrame`` beside ``CastAiMixin``."""

    # -- plumbing ------------------------------------------------------------------ #

    def _cast_ask(self, prompt: str, on_answer: Any, *, working: str = "Working.") -> bool:
        """Send *prompt* through the shared service, if AI may run. True if sent."""
        if not self._ai_ready():  # type: ignore[attr-defined]
            return False
        service = self._ai_service()  # type: ignore[attr-defined]
        self._announce(working)  # type: ignore[attr-defined]

        def _failed(sentence: str) -> None:
            from quill.ui.podcasts.failure_report import report_failure

            report_failure(self, sentence, subject="AI help")

        service.ask("ask", prompt, None, on_done=lambda text, _q: on_answer(text), on_error=_failed)
        return True

    def _ai_episode(self) -> tuple[Any, Any] | None:
        pair = self._selected_episode()  # type: ignore[attr-defined]
        if pair is not None:
            return pair  # type: ignore[no-any-return]
        state = getattr(getattr(self, "_podcast_controller", None), "state", None)
        library = self._podcast_library  # type: ignore[attr-defined]
        show = library.find_show(getattr(state, "show_id", "") or "")
        episode = show.find_episode(state.episode_guid) if show is not None else None
        return (show, episode) if show is not None and episode is not None else None

    def _ai_show(self) -> Any:
        show = self._selected_show()  # type: ignore[attr-defined]
        if show is not None:
            return show
        pair = self._ai_episode()
        return pair[0] if pair is not None else None

    def _care_note(self, show: Any) -> str:
        from quill.core.podcasts import settings_catalog
        from quill.core.podcasts.settings_resolver import value_of

        definition = settings_catalog.definition("listening_note")
        if definition is None:
            return ""
        return str(value_of(self._podcast_library, definition, show=show) or "")  # type: ignore[attr-defined]

    def _answer(self, title: str, text: str) -> None:
        from quill.ui.podcasts.ai_answer_dialog import show_answer

        self._announce(text)  # type: ignore[attr-defined]
        show_answer(self, title, text)

    # -- A3, A4, A5: answers ----------------------------------------------------------- #

    def ai_about_podcast(self) -> None:
        show = self._ai_show()
        if show is None:
            self._announce("Choose a podcast first.")  # type: ignore[attr-defined]
            return
        self._cast_ask(
            ai.about_show_prompt(show),
            lambda text: self._answer(f"About {show.title}", text),
        )

    def ai_for_me(self) -> None:
        pair = self._ai_episode()
        if pair is None:
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        show, episode = pair
        care = self._care_note(show)
        if not care.strip():
            self._announce(  # type: ignore[attr-defined]
                f"First say what you care about in {show.title}: Settings for This "
                "Podcast, What I care about in this podcast."
            )
            return
        self._cast_ask(
            ai.for_me_prompt(show, episode, care),
            lambda text: self._answer(f"Is {episode.title} for me?", text),
        )

    def ai_summarise_episode(self) -> None:
        from quill.core.podcasts.transcripts import load_cached_transcript

        pair = self._ai_episode()
        if pair is None:
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        show, episode = pair
        transcript = load_cached_transcript(show.id, episode.guid)
        prompt, source = ai.summary_prompt(episode, transcript)
        self._cast_ask(
            prompt,
            lambda text: self._answer(
                f"Summary of {episode.title}", f"From {source}: {text.strip()}"
            ),
        )

    # -- A2: organise ----------------------------------------------------------------------- #

    def ai_organise_podcasts(self) -> None:
        from quill.core.podcasts import ai_organise

        library = self._podcast_library  # type: ignore[attr-defined]
        names = {folder.id: folder.name for folder in library.folders}
        shows = [
            ai_organise.Show(
                id=show.id,
                title=show.title,
                description=str(getattr(show, "description", "") or ""),
                folder_name=names.get(show.folder_id or "", ""),
            )
            for show in library.shows
            if not getattr(show, "is_local", False)
        ]
        if len(shows) < 2:
            self._announce("There is not enough to organise yet: follow a few podcasts first.")  # type: ignore[attr-defined]
            return
        folders = tuple(ai_organise.Folder(id=f.id, name=f.name) for f in library.folders)
        batches = [
            shows[i : i + ai_organise.BATCH] for i in range(0, len(shows), ai_organise.BATCH)
        ]
        gathered = ai_organise.ReadResult()

        def _next(index: int) -> None:
            if index >= len(batches):
                self._review_organise(gathered)
                return
            batch = ai_organise.Library(shows=tuple(batches[index]), folders=folders)

            def _read(text: str) -> None:
                result = ai_organise.read_answer(text, batch)
                gathered.proposals.extend(result.proposals)
                gathered.discarded.extend(result.discarded)
                _next(index + 1)

            working = (
                "Working."
                if len(batches) == 1
                else f"Working on {index + 1} of {len(batches)} groups of podcasts."
            )
            self._cast_ask(ai_organise.build_prompt(batch), _read, working=working)

        _next(0)

    def _review_organise(self, result: Any) -> None:
        from quill.core.podcasts import ai_organise
        from quill.ui.podcasts.ai_review_dialog import review

        said = ai_organise.describe_plan(result)
        self._announce(said)  # type: ignore[attr-defined]
        if not result.proposals:
            return
        chosen = review(self, "Organise My Podcasts", said, [p.spoken() for p in result.proposals])
        if not chosen:
            return
        creates, moves = ai_organise.apply_plan([result.proposals[i] for i in chosen])
        library = self._podcast_library  # type: ignore[attr-defined]
        by_name = {folder.name.casefold(): folder.id for folder in library.folders}
        for name in creates:
            if name.casefold() not in by_name:
                by_name[name.casefold()] = library.add_folder(name).id
        moved = 0
        for move in moves:
            show = library.find_show(move.show_id)
            target = move.folder_id or by_name.get(move.folder_name.casefold(), "")
            if show is not None and target:
                show.folder_id = target
                moved += 1
        self._save_podcast_library()  # type: ignore[attr-defined]
        self._after_library_change()
        self._announce(  # type: ignore[attr-defined]
            f"Made {len(creates)} folder{'s' if len(creates) != 1 else ''} and moved "
            f"{moved} podcast{'s' if moved != 1 else ''}."
        )

    def _after_library_change(self) -> None:
        for name in ("_reload_library_tree", "_refresh_place", "_refresh_place_counts"):
            method = getattr(self, name, None)
            if callable(method):
                try:
                    method()
                except Exception:  # noqa: BLE001 - a refresh is never worth a crash
                    continue

    # -- A6: a listening run ------------------------------------------------------------- #

    def ai_listening_run(self) -> None:
        import wx

        from quill.core.podcasts.virtual_views import virtual_view_pairs

        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self.frame,  # type: ignore[attr-defined]
            "How many minutes do you have?",
            "Build Me a Listening Run",
            value="40",
        ) as entry:
            if entry.ShowModal() != wx.ID_OK:
                return
            typed = entry.GetValue().strip()
        try:
            minutes = max(5, min(600, int(typed)))
        except ValueError:
            self._announce("Type a number of minutes, such as 40.")  # type: ignore[attr-defined]
            return
        library = self._podcast_library  # type: ignore[attr-defined]
        seen: set[tuple[str, str]] = set()
        candidates: list[tuple[Any, Any]] = []
        for view in ("inbox", "new_episodes"):
            for show, episode in virtual_view_pairs(library, view):
                key = (show.id, episode.guid)
                if key in seen or episode.played or not episode.duration_seconds:
                    continue
                seen.add(key)
                candidates.append((show, episode))
        candidates = candidates[:60]
        if not candidates:
            self._announce("Nothing unheard with a known length to choose from.")  # type: ignore[attr-defined]
            return

        def _read(text: str) -> None:
            picks, discarded = ai.read_listening_run(text, candidates, minutes)
            total = sum(pick.minutes for pick in picks)
            said = f"A run of {len(picks)} episodes, {total} minutes."
            if discarded:
                said += f" {len(discarded)} suggestion(s) were dropped."
            self._announce(said)  # type: ignore[attr-defined]
            if not picks:
                return
            chosen = self._review(
                "Build Me a Listening Run", said, [pick.spoken() for pick in picks]
            )
            if not chosen:
                return
            from quill.core.podcasts import queue as queue_ops

            added = 0
            for index in chosen:
                pick = picks[index]
                if queue_ops.add_to_queue(
                    library, pick.show.id, pick.episode.guid, reason="your listening run"
                ):
                    added += 1
            self._save_podcast_library()  # type: ignore[attr-defined]
            self._after_library_change()
            self._announce(f"Added {added} episode{'s' if added != 1 else ''} to the Play Queue.")  # type: ignore[attr-defined]

        self._cast_ask(ai.listening_run_prompt(candidates, minutes, self._care_note(None)), _read)

    def _review(self, title: str, intro: str, rows: list[str]) -> list[int] | None:
        from quill.ui.podcasts.ai_review_dialog import review

        return review(self, title, intro, rows)

    # -- A7: a smart playlist from a sentence ------------------------------------------- #

    def ai_playlist_from_sentence(self) -> None:
        import wx

        with wx.TextEntryDialog(  # dialog_button_contract: exempt
            self.frame,  # type: ignore[attr-defined]
            "Describe the playlist, such as: unheard news under 20 minutes from this week",
            "Smart Playlist from a Sentence",
        ) as entry:
            if entry.ShowModal() != wx.ID_OK:
                return
            sentence = entry.GetValue().strip()
        if not sentence:
            return
        library = self._podcast_library  # type: ignore[attr-defined]

        def _read(text: str) -> None:
            name, rules, discarded = ai.read_playlist_rules(text, library)
            lines = ai.describe_rules(rules, library)
            if discarded:
                lines.append(" ".join(discarded))
            chosen = self._review(
                "Smart Playlist from a Sentence",
                f'Save "{name}" with these rules? You can change them later in Edit Rules.',
                lines,
            )
            if chosen is None:
                return
            from quill.core.podcasts.models_playlists import Playlist
            from quill.core.podcasts.subscriptions import new_id

            library.playlists.append(Playlist(id=new_id(), name=name, kind="smart", rules=rules))
            self._save_podcast_library()  # type: ignore[attr-defined]
            self._after_library_change()
            self._announce(f"Saved the smart playlist {name}.")  # type: ignore[attr-defined]

        titles = [show.title for show in library.shows]
        folders = [folder.name for folder in library.folders]
        self._cast_ask(ai.playlist_rules_prompt(sentence, titles, folders), _read)

    # -- A8: name these chapters ---------------------------------------------------------- #

    def ai_name_chapters(self) -> None:
        from pathlib import Path

        from quill.core.podcasts.chapter_inference import (
            load_cached_inference,
            parse_timed_cues,
            save_cached_inference,
        )
        from quill.core.podcasts.chapters import PodcastChapter
        from quill.core.podcasts.transcripts import load_cached_transcript_vtt

        pair = self._ai_episode()
        if pair is None:
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        show, episode = pair
        audio = Path(episode.downloaded_path) if episode.downloaded_path else None
        chapters, source = load_cached_inference(show.id, episode.guid, audio_path=audio)
        cues = parse_timed_cues(load_cached_transcript_vtt(show.id, episode.guid), "text/vtt")
        if not chapters or not cues:
            self._announce(  # type: ignore[attr-defined]
                "Name These Chapters needs chapters Cast worked out and a transcript. "
                "Use Analyse Chapters on the episode first."
            )
            return
        bounds = [c.start_ms for c in chapters] + [10**12]
        texts = [
            " ".join(cue.text for cue in cues if bounds[i] <= cue.start_ms < bounds[i + 1])
            for i in range(len(chapters))
        ]

        def _read(text: str) -> None:
            found, discarded = ai.read_chapter_titles(text, chapters)
            said = f"{len(found)} new chapter title{'s' if len(found) != 1 else ''}."
            if discarded:
                said += f" {len(discarded)} dropped."
            self._announce(said)  # type: ignore[attr-defined]
            if not found:
                return
            chosen = self._review("Name These Chapters", said, [t.spoken() for t in found])
            if not chosen:
                return
            renamed = {found[i].index: found[i].new for i in chosen}
            updated = [
                PodcastChapter(start_ms=c.start_ms, title=renamed.get(i, c.title))
                for i, c in enumerate(chapters)
            ]
            save_cached_inference(show.id, episode.guid, updated, source, audio_path=audio)
            self._announce(f"Renamed {len(renamed)} chapter{'s' if len(renamed) != 1 else ''}.")  # type: ignore[attr-defined]

        self._cast_ask(ai.chapter_titles_prompt(chapters, texts), _read)

    # -- A9: tidy (no model) -------------------------------------------------------------- #

    def tidy_subscriptions(self) -> None:
        from quill.core.podcasts import check_state

        library = self._podcast_library  # type: ignore[attr-defined]
        failing = {show.id for show in library.shows if check_state.failure_run(library, show) >= 3}
        rows = ai.tidy_rows(library, failing=failing)
        if not rows:
            self._announce("Nothing to tidy: every podcast is active and appears once.")  # type: ignore[attr-defined]
            return
        intro = (
            f"{len(rows)} podcast{'s' if len(rows) != 1 else ''} worth a look. Nothing is "
            "sent anywhere for this, and nothing changes until you apply."
        )
        chosen = self._review("Tidy the Podcasts I Follow", intro, [row.spoken() for row in rows])
        if not chosen:
            return
        paused = 0
        for index in chosen:
            row = rows[index]
            show = library.find_show(row.show_id)
            if show is None:
                continue
            if row.action == "pause":
                show.paused = True
                paused += 1
            else:
                from quill.ui.podcasts.show_actions import unsubscribe_show_prompt

                unsubscribe_show_prompt(
                    self.frame,  # type: ignore[attr-defined]
                    library,
                    show,
                    announce=self._announce,  # type: ignore[attr-defined]
                    on_change=self._save_podcast_library,  # type: ignore[attr-defined]
                )
        self._save_podcast_library()  # type: ignore[attr-defined]
        self._after_library_change()
        if paused:
            self._announce(f"Paused updates for {paused} podcast{'s' if paused != 1 else ''}.")  # type: ignore[attr-defined]

    # -- the menu -------------------------------------------------------------------------- #

    def _append_cast_ai_feature_rows(self, sub: Any) -> None:
        """Cast's own rows in Help > AI Features, after the shared ones."""
        import wx

        ids = getattr(self, "_cast_ai_feature_ids", None)
        if ids is None:
            ids = {cid: wx.NewIdRef() for cid, _label, _h in AI_FEATURE_ROWS}
            self._cast_ai_feature_ids = ids
        sub.AppendSeparator()
        for command_id, label, _handler in AI_FEATURE_ROWS:
            sub.Append(ids[command_id], label)
        if getattr(self, "_cast_ai_features_wired", False):
            return
        self._cast_ai_features_wired = True
        for command_id, label, handler_name in AI_FEATURE_ROWS:
            handler = getattr(self, handler_name)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id])  # type: ignore[attr-defined]
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id, label.replace("&", "").rstrip("."), handler
            )
        keep = getattr(self, "_keep_menu_ids", None)
        if callable(keep):
            keep(*ids.values())
