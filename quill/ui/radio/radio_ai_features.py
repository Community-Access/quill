"""What Quill Radio does with AI: Ask about what is on, and describe the video.

The commands behind :class:`~quill.ui.radio.radio_ai_host.RadioAiMixin`, kept
apart from the adapter so the adapter keeps having no command of its own.

**Ask** (Ctrl+Shift+8, Community > Ask...) is the family's one conversation
window (:mod:`quill.ui.hosted_ai_app_ask`) with Radio's facts: the station and
what is playing, always; your favourites and the songs heard here only when the
question needs them; and your listening history only when you choose the one
question that asks for it, which says so before anything goes. It replaced the
old Ask QUILL Radio window (codex.md 10C.2), and it now answers on whichever AI
is in use rather than only on a ChatGPT plan. Its quick list keeps Radio's nine
questions where they were, then Radio's own two prompts and the three every app
shares; "What can I do here?" is answered on this computer.

**Describe the Video** (Ctrl+F5, Video menu) takes one picture of the video
playing, on this computer, fits it to the connection in use and asks what is on
screen (codex.md 10B.5, through :mod:`quill.core.ai.picture_prep`). A connection
that cannot see sends nothing and offers the switch in one key (10A.8). The same
picture asked about again is answered from this session's cache and sends
nothing. No sound and no video file ever leaves.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["DESCRIBE_QUESTION", "RadioAiFeaturesMixin"]

#: What Describe the Video asks of the picture.
DESCRIBE_QUESTION = (
    "Describe what is on screen in this picture from a video: who or what is shown, "
    "any words on screen, and what seems to be happening. Keep it to a few sentences."
)
_ABOUT_FACTS = (
    "the station and what is playing, and your favourites or the songs heard here "
    "only when the question needs them"
)


class RadioAiFeaturesMixin:
    """Ask and Describe the Video. Mixed in through ``RadioAiMixin``."""

    # -- Ask --------------------------------------------------------------- #

    def _ai_app_ask(self) -> None:
        """Ask (Ctrl+Shift+8): the conversation about what is on (10C)."""
        from quill.core.ai.family_prompt_catalogue import quick_prompts_for
        from quill.ui.hosted_ai_app_ask import open_app_ask, rows_from_prompts

        open_app_ask(
            self,
            app="radio",
            subject="this station",
            about_facts=_ABOUT_FACTS,
            facts=self._radio_ask_facts,
            rows=[
                *self._radio_quick_rows(),
                *rows_from_prompts(_app_first(quick_prompts_for("radio"))),
            ],
            local_answer=self._radio_what_can_i_do,
            on_quick=self._radio_on_quick,
        )

    def _radio_quick_rows(self) -> list[Any]:
        """Radio's nine questions, as they were in Ask QUILL Radio."""
        from quill.core.radio.assistant_prompt import (
            NEEDS_LISTENING,
            NEEDS_PLAYING,
            QUICK_QUESTIONS,
        )
        from quill.ui.hosted_ai_app_ask import CONSENT_HISTORY, AskRow

        return [
            AskRow(
                label=question.label,
                text=question.question,
                context="" if question.needs == NEEDS_PLAYING else question.needs,
                consents=CONSENT_HISTORY if question.needs == NEEDS_LISTENING else frozenset(),
            )
            for question in QUICK_QUESTIONS
        ]

    def _radio_on_quick(self, row: Any) -> str:
        """What else a chosen question will send, said before anything goes."""
        from quill.core.radio.assistant_prompt import NEEDS_PLAYING, describe_extra

        needs = row.context or NEEDS_PLAYING
        count = _extra_for(self, needs)[1] if row.context else 0
        return str(describe_extra(needs, count=count))

    def _radio_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts (``app_ask_context.radio_context``), read fresh."""
        from quill.core.ai.app_ask_context import radio_context
        from quill.core.radio.assistant_prompt import (
            NEEDS_FAVORITES,
            NEEDS_LISTENING,
            NEEDS_RECENT_SONGS,
        )

        station, playing = _what_is_on(self)
        return radio_context(
            station,
            playing,
            question=question,
            needs=needs,
            favorites=_favorites(self) if needs in ("", NEEDS_FAVORITES) else (),
            recent_songs=_recent_songs(self) if needs in ("", NEEDS_RECENT_SONGS) else (),
            listening=_listening(self) if needs in ("", NEEDS_LISTENING) else (),
        )

    def _radio_what_can_i_do(self) -> str:
        """The local answer, from Radio's own F1 catalogue and its menus."""
        from quill.core.ai.family_prompt_catalogue import what_can_i_do_here
        from quill.core.radio.surface_help import purpose_for_title
        from quill.ui.hosted_ai_app_ask import menu_routes

        return what_can_i_do_here(
            purpose_for_title("Quill Radio"),
            commands=menu_routes(self.frame.GetMenuBar()),  # type: ignore[attr-defined]
        )

    # -- Describe the Video ------------------------------------------------ #

    def cmd_radio_describe_video(self) -> None:
        """Describe the Video (Ctrl+F5): one picture, fitted, asked about (10B.5)."""
        if not self._ai_switched_on():  # type: ignore[attr-defined]
            return
        from quill.ui.radio import video_commands

        engine = video_commands._engine(self)
        if engine is None or getattr(self, "_video_window", None) is None:
            self._announce("There is no picture to describe. Show the video first.")  # type: ignore[attr-defined]
            return
        if not self._ai_capable("pictures") or not self._ai_ready():  # type: ignore[attr-defined]
            return  # nothing sent; the switch was offered (codex.md 10A.8)
        scratch = Path(tempfile.mkdtemp(prefix="quill-radio-picture-"))
        try:
            shot = scratch / "frame.png"
            if not engine.take_snapshot(str(shot)) or not shot.is_file():
                self._announce("The picture could not be taken.")  # type: ignore[attr-defined]
                shutil.rmtree(scratch, ignore_errors=True)
                return
            self._radio_describe_picture(shot.read_bytes(), scratch, _position_s(self))
        except Exception:
            shutil.rmtree(scratch, ignore_errors=True)
            raise

    def _radio_describe_picture(self, data: bytes, scratch: Path, at: float | None) -> None:
        """Fit *data* to the connection, answer from the cache or ask, then tidy up."""
        from quill.core.ai.picture_prep import (
            PicturePrepError,
            described_by_sentence,
            prepare_request,
        )

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = str(service.connection_in_use)
        try:
            prepared = prepare_request(
                [data],
                service.capability_record(connection),
                times=(at,) if at is not None else (),
            )
        except PicturePrepError as error:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(str(error.args[0]))  # type: ignore[attr-defined]
            return
        image = prepared.images[0]
        cache = _picture_cache(self)
        cached = cache.get(image.digest, DESCRIBE_QUESTION, connection)
        if cached is not None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._radio_picture_answer(
                f"{cached} Nothing was sent: this picture was asked about already."
            )
            return
        target = scratch / ("picture.png" if image.mime == "image/png" else "picture.jpg")
        target.write_bytes(image.data)

        def done(text: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            answer = f"{prepared.inspected} {described_by_sentence(connection)} {text.strip()}"
            cache.put(
                image.digest, DESCRIBE_QUESTION, answer, connection=connection, prepared=prepared
            )
            self._radio_picture_answer(answer)

        def failed(sentence: str) -> None:
            shutil.rmtree(scratch, ignore_errors=True)
            self._announce(sentence)  # type: ignore[attr-defined]

        self._announce("Working.")  # type: ignore[attr-defined]
        service.describe_image(
            target,
            DESCRIBE_QUESTION,
            on_done=done,
            on_error=failed,
            requires=("text", "pictures"),
        )

    def _radio_picture_answer(self, answer: str) -> None:
        """Said, because focus stays on the player, and kept in a result window."""
        from quill.ui.hosted_ai_app_ask import show_picture_answer

        show_picture_answer(self, answer)


# --------------------------------------------------------------------------- #
# What Radio knows, read without raising
# --------------------------------------------------------------------------- #


def _app_first(prompts: tuple[Any, ...]) -> list[Any]:
    """Radio's own prompts before the three the family shares."""
    from quill.core.ai.family_prompt_catalogue import FAMILY_PROMPTS

    family = set(FAMILY_PROMPTS)
    return [p for p in prompts if p not in family] + [p for p in prompts if p in family]


def _what_is_on(host: Any) -> tuple[str, str]:
    """``(station name, now-playing text)``, each "" when unknown."""
    station = ""
    playing = ""
    try:
        controller = getattr(host, "_radio_controller", None)
        current = controller.state.station if controller is not None else None
        station = str(getattr(current, "name", "") or "") if current is not None else ""
    except Exception:  # noqa: BLE001 - a host without a player has no station
        station = ""
    try:
        text = getattr(host, "_radio_now_playing_text", None)
        playing = str(text() or "") if callable(text) else ""
    except Exception:  # noqa: BLE001 - an unread title is not an error here
        playing = ""
    return station, playing


def _station_key(host: Any) -> str:
    try:
        controller = getattr(host, "_radio_controller", None)
        current = controller.state.station if controller is not None else None
        if current is None:
            return ""
        return str(getattr(current, "station_uuid", "") or getattr(current, "stream_url", "") or "")
    except Exception:  # noqa: BLE001 - no station, no key
        return ""


def _favorites(host: Any) -> list[tuple[str, str]]:
    try:
        store = getattr(host, "_radio_favorites", None)
        pairs = [
            (str(getattr(fav.station, "name", "") or ""), str(getattr(fav, "folder", "") or ""))
            for fav in (getattr(store, "favorites", []) or [])
        ]
    except Exception:  # noqa: BLE001 - nothing to attach is an answer
        return []
    return [(name, folder) for name, folder in pairs if name]


def _recent_songs(host: Any) -> list[str]:
    try:
        from quill.ui.radio.song_history_commands import song_history

        return [song.display() for song in song_history(host).songs_for(_station_key(host))]
    except Exception:  # noqa: BLE001 - no log is no songs
        return []


def _listening(host: Any) -> list[tuple[str, list[str]]]:
    try:
        from quill.ui.radio.song_history_commands import song_history

        return [
            (station.station_name or station.station_key, [s.display() for s in station.songs])
            for station in song_history(host).known_stations()
        ]
    except Exception:  # noqa: BLE001 - no log is no history
        return []


def _extra_for(host: Any, needs: str) -> tuple[str, int]:
    """``(context text, how many things it names)`` for a quick question."""
    from quill.core.radio.assistant_prompt import (
        NEEDS_FAVORITES,
        NEEDS_LISTENING,
        NEEDS_RECENT_SONGS,
        extra_context,
    )

    if needs == NEEDS_FAVORITES:
        pairs = _favorites(host)
        return extra_context(needs, favorites=pairs), len(pairs)
    if needs == NEEDS_RECENT_SONGS:
        songs = _recent_songs(host)
        return extra_context(needs, recent_songs=songs), len(songs)
    if needs == NEEDS_LISTENING:
        stations = _listening(host)
        return extra_context(needs, listening=stations), len(stations)
    return "", 0


def _position_s(host: Any) -> float | None:
    try:
        controller = getattr(host, "_radio_controller", None)
        position = int(controller.position_ms()) if controller is not None else 0
    except Exception:  # noqa: BLE001 - a live stream may have no position
        return None
    return position / 1000.0 if position > 0 else None


def _picture_cache(host: Any) -> Any:
    """This session's picture cache: in memory only (10B.2 rule 7)."""
    cache = getattr(host, "_radio_picture_cache", None)
    if cache is None:
        from quill.core.ai.picture_prep import PictureCache

        cache = PictureCache()
        host._radio_picture_cache = cache
    return cache
