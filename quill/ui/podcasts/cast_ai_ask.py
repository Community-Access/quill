"""QUILL Cast's Ask, "What did I miss?", and pictures (codex.md 10E.4, 10B.5).

Mixed into :class:`~quill.ui.podcasts.cast_ai_features.CastDomainAiMixin`, so
the adapter (:mod:`quill.ui.podcasts.cast_ai_host`) keeps having no command of
its own. Everything goes to the AI in use through the shared service, behind
the same switch and agreement as the rest of Cast's AI.

**Ask** (Ctrl+Shift+8, Help > AI Features > Ask...) is the family's one
conversation window (:mod:`quill.ui.hosted_ai_app_ask`) about the episode in
front of you: the show, the episode, where you are in it, the chapter you are
in, the chapter list and the show notes, read fresh every turn -- never the
audio. Its quick list starts with Cast's own two prompts, "What did I miss in
this episode?" and "Is this episode worth my time?", then the three every app
shares.

**What Did I Miss in This Episode?** sends the show notes, the chapters, your
position and, when Cast has one cached, the transcript up to where you are, and
asks only about what came before.

**Ask About an Image** (Ctrl+Alt+F5) offers the pictures Cast already knows
the address of -- the podcast's artwork and any pictures in the show notes --
and, last, a picture file on this computer. A chosen picture is fetched then,
once, because you asked (``picture_fetch``), fitted to the connection
(``picture_prep``) and described. On a connection that cannot see nothing is
fetched or sent; the switch is offered, and when the show notes wrote alt text
for their pictures, that is read instead.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["CastAskMixin", "PICTURE_QUESTION"]

#: What Ask About an Image asks of a Cast picture.
PICTURE_QUESTION = (
    "Describe this picture in a few sentences. If it has words in it, say what they say."
)
_FILE_ROW = "A picture file on this computer..."
_ABOUT_FACTS = "the episode, its show notes, its chapters and where you are in it"


class CastAskMixin:
    """Ask, What Did I Miss and Cast's pictures."""

    # -- Ask ---------------------------------------------------------------- #

    def _ai_app_ask(self) -> None:
        """Ask (Ctrl+Shift+8): the conversation about this episode (10C)."""
        from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS, quick_prompts_for
        from quill.ui.hosted_ai_app_ask import open_app_ask, rows_from_prompts

        prompts = quick_prompts_for("cast")
        ordered = [p for p in prompts if p not in FAMILY_PROMPTS] + list(FAMILY_PROMPTS)
        open_app_ask(
            self,
            app="cast",
            subject="this episode",
            about_facts=_ABOUT_FACTS,
            facts=self._cast_ask_facts,
            rows=rows_from_prompts(ordered),
            local_answer=self._cast_what_can_i_do,
        )

    def _cast_episode_facts(self) -> dict[str, Any]:
        """What Cast knows about the episode in front of the person, read now."""
        from quill.core.podcasts.show_notes import html_to_plain_text

        pair = self._ai_episode()  # type: ignore[attr-defined]
        if pair is None:
            show = self._ai_show()  # type: ignore[attr-defined]
            return {"show": str(getattr(show, "title", "") or "")}
        show, episode = pair
        playing = self._cast_is_playing(show, episode)
        position_ms = self._cast_position_ms(episode, playing)
        chapters = (
            [
                (str(chapter.title), chapter.start_ms / 1000.0)
                for chapter in (getattr(self, "_podcast_current_chapters", None) or [])
            ]
            if playing
            else []
        )
        return {
            "show": str(show.title),
            "episode": str(episode.title),
            "notes": html_to_plain_text(str(episode.description or "")),
            "chapters": chapters,
            "position_s": position_ms / 1000.0 if position_ms > 0 else None,
            "duration_s": float(episode.duration_seconds or 0) or None,
            "ids": (show.id, episode.guid),
        }

    def _cast_is_playing(self, show: Any, episode: Any) -> bool:
        state = getattr(getattr(self, "_podcast_controller", None), "state", None)
        return bool(
            state is not None
            and getattr(state, "show_id", None) == show.id
            and getattr(state, "episode_guid", None) == episode.guid
        )

    def _cast_position_ms(self, episode: Any, playing: bool) -> int:
        if playing:
            try:
                return int(self._podcast_controller.position_ms())  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - fall back to the saved place
                pass
        return int(getattr(episode, "position_ms", 0) or 0)

    def _cast_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts (``app_ask_context.cast_context``), read fresh."""
        del question, needs
        from quill.core.ai.app_ask_context import cast_context

        facts = self._cast_episode_facts()
        return cast_context(
            facts.get("show", ""),
            facts.get("episode", ""),
            notes=facts.get("notes", ""),
            chapters=facts.get("chapters", ()),
            position_s=facts.get("position_s"),
            duration_s=facts.get("duration_s"),
        )

    def _cast_what_can_i_do(self) -> str:
        """The local answer, from Cast's own F1 catalogue and its menus."""
        from quill.core.ai.family_prompt_catalogue import what_can_i_do_here
        from quill.core.podcasts.surface_help import purpose_for_title
        from quill.ui.hosted_ai_app_ask import menu_routes

        return what_can_i_do_here(
            purpose_for_title("QUILL Cast"),
            commands=menu_routes(self.frame.GetMenuBar()),  # type: ignore[attr-defined]
        )

    # -- What did I miss? (10E.4) ------------------------------------------- #

    def ai_what_did_i_miss(self) -> None:
        """What Did I Miss in This Episode?: only what came before your place."""
        from quill.core.ai.app_ai_prompts import cast_missed_prompt
        from quill.core.podcasts.transcripts import load_cached_transcript

        facts = self._cast_episode_facts()
        if not facts.get("episode"):
            self._announce("Choose an episode first.")  # type: ignore[attr-defined]
            return
        if facts.get("position_s") is None:
            self._announce(  # type: ignore[attr-defined]
                f"You have not started {facts['episode']} yet, so there is nothing to miss."
            )
            return
        show_id, guid = facts["ids"]
        prompt = cast_missed_prompt(
            facts["show"],
            facts["episode"],
            notes=facts["notes"],
            chapters=facts["chapters"],
            position_s=facts["position_s"],
            transcript=load_cached_transcript(show_id, guid),
        )
        self._cast_ask(  # type: ignore[attr-defined]
            prompt,
            lambda text: self._answer(f"What I missed in {facts['episode']}", text),  # type: ignore[attr-defined]
        )

    # -- pictures (10B.5) ---------------------------------------------------- #

    def cmd_ai_image(self) -> None:
        """Ask About an Image (Ctrl+Alt+F5): a picture Cast knows of, or a file."""
        if not self._ai_switched_on():  # type: ignore[attr-defined]
            return
        pictures = self._cast_pictures()
        if not self._ai_capable("pictures"):  # type: ignore[attr-defined]
            alts = [picture.alt for picture in pictures if picture.alt]
            if alts:
                self._announce(  # type: ignore[attr-defined]
                    "The show notes describe their pictures: " + " ".join(f"{a}." for a in alts)
                )
            return  # nothing fetched or sent; the switch was offered (10A.8)
        if not self._cast_picture_consent():
            return  # 10B.4: No, the default, fetches and sends nothing
        index = self._cast_choose_picture([p.label for p in pictures])
        if index is None:
            return
        if index >= len(pictures):
            super().cmd_ai_image()  # type: ignore[misc]
            return
        self._cast_describe_picture(pictures[index])

    def _cast_picture_consent(self) -> bool:
        """10B.4: the first picture on a connection says where pictures go, once.
        Asked before a picture is chosen, so No fetches nothing either."""
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        connection = str(self._ai_service().connection_in_use or "")  # type: ignore[attr-defined]
        return ask_picture_consent(self, connection)

    def _cast_pictures(self) -> list[Any]:
        from quill.core.podcasts.picture_fetch import pictures_for

        pair = self._ai_episode()  # type: ignore[attr-defined]
        show = pair[0] if pair is not None else self._ai_show()  # type: ignore[attr-defined]
        if show is None:
            return []
        episode = pair[1] if pair is not None else None
        return pictures_for(
            episode_title=str(getattr(episode, "title", "") or ""),
            episode_art=str(getattr(episode, "artwork_url", "") or ""),
            show_title=str(show.title),
            show_art=str(getattr(show, "artwork_url", "") or ""),
            notes_html=str(getattr(episode, "description", "") or ""),
        )

    def _cast_choose_picture(self, labels: list[str]) -> int | None:
        """Which picture: Cast's, then a file. ``None`` on Cancel."""
        import wx

        from quill.ui.dialog_contract import show_modal_dialog

        dialog = wx.SingleChoiceDialog(  # dialog_button_contract: exempt
            self.frame,  # type: ignore[attr-defined]
            "Which picture should the AI describe? Cast fetches it only now, once.",
            "Ask About an Image",
            [*labels, _FILE_ROW],
        )
        try:
            if show_modal_dialog(dialog, "Ask About an Image") != wx.ID_OK:
                return None
            return int(dialog.GetSelection())
        finally:
            dialog.Destroy()

    def _cast_describe_picture(self, picture: Any) -> None:
        """Fetch the one picture, fit it to the connection, and ask."""
        from quill.core.podcasts.picture_fetch import fetch_picture

        safe = bool(getattr(self, "_safe_mode", False))
        self._announce("Fetching the picture.")  # type: ignore[attr-defined]
        _background(
            self,
            "cast-picture-fetch",
            lambda: fetch_picture(picture.url, safe_mode=safe),
            on_done=lambda data: self._cast_ask_about_picture(picture, data),
            on_error=self._announce,  # type: ignore[attr-defined]
        )

    def _cast_ask_about_picture(self, picture: Any, data: bytes) -> None:
        from quill.core.ai.picture_prep import (
            PictureCache,
            PicturePrepError,
            described_by_sentence,
            prepare_request,
        )

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = str(service.connection_in_use)
        try:
            prepared = prepare_request([data], service.capability_record(connection))
        except PicturePrepError as error:
            self._announce(str(error.args[0]))  # type: ignore[attr-defined]
            return
        image = prepared.images[0]
        cache = getattr(self, "_cast_picture_cache", None)
        if cache is None:
            cache = PictureCache()
            self._cast_picture_cache = cache
        title = picture.label.split(":")[0]
        cached = cache.get(image.digest, PICTURE_QUESTION, connection)
        if cached is not None:
            self._answer(title, f"{cached} Nothing was sent: this picture was asked about already.")  # type: ignore[attr-defined]
            return
        scratch = Path(tempfile.mkdtemp(prefix="quill-cast-picture-"))
        target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
        target.write_bytes(image.data)

        def done(text: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            answer = f"{prepared.inspected} {described_by_sentence(connection)} {text.strip()}"
            cache.put(
                image.digest, PICTURE_QUESTION, answer, connection=connection, prepared=prepared
            )
            self._answer(title, answer)  # type: ignore[attr-defined]

        def failed(sentence: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(sentence)  # type: ignore[attr-defined]

        self._announce("Working.")  # type: ignore[attr-defined]
        service.describe_image(
            target, PICTURE_QUESTION, on_done=done, on_error=failed, requires=("text", "pictures")
        )


def _background(
    host: Any,
    name: str,
    work: Callable[[], Any],
    *,
    on_done: Callable[[Any], None],
    on_error: Callable[[str], None],
) -> None:
    """Run *work* off the UI thread; the callbacks land on it."""
    import wx

    def done(_op: str, result: Any) -> None:
        wx.CallAfter(on_done, result)

    def failed(_op: str, error: BaseException) -> None:
        from quill.ui.hosted_ai_connection_route import plain_sentence

        wx.CallAfter(on_error, plain_sentence(error))

    tasks = getattr(host, "_task_manager", None)
    if tasks is not None:
        tasks.submit(name, lambda **_kw: work(), on_success=done, on_failure=failed)
        return
    from quill.ui.update_download import thread_submit

    thread_submit(name, lambda **_kw: work(), on_success=done, on_failure=failed)
