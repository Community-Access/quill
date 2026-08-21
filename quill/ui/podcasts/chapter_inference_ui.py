"""Find Chapters: the explicit request that runs the inferred chapter tiers.

The free tiers (feed chapters, ID3 frames, show-note timestamps, soundbites) run
by themselves whenever an episode loads, because they are instant and their
titles were written by a person. The tiers below them are neither, so they run
only when the listener asks.

**How hard to look is one choice, and the listener makes it.** Not a silence
threshold in decibels or a cohesion window in cues -- nobody can reason about
those. One setting, three values, and every constant derived from it
(:mod:`quill.core.podcasts.inference_budget`):

* **Quick** -- only what is already here. A published chapter list, or a
  transcript already downloaded. Instant, never touches the network or ffmpeg.
* **Thorough** (the default) -- fetches a published transcript if the episode
  has one; otherwise listens to the audio for pauses. Seconds.
* **Deep** -- everything Thorough does, and may transcribe the episode locally
  and name the sections from what was said. Minutes, with a real cancel.

**Every tier the budget allows runs, and the best answer wins** -- which is the
job of :func:`quill.core.podcasts.chapter_cascade.run`, and the reason this
module hands it callables rather than deciding anything itself. The order used
to be cost order with the first non-empty answer winning, so two weak chapters
from a transcript permanently hid a better audio scan, and nothing could compare
two answers because nothing scored one.

Everything except a transcript *fetch* is local: tier 3 reads a cached
transcript, tier 4 reads the downloaded file. Safe Mode blocks only the fetch,
so the rest still works with the network off.

The result is cached against the audio file's size and mtime, so asking twice
costs nothing and replacing the file recomputes rather than showing chapters
that belong to different audio.

Lives outside ``main_frame_podcasts`` so that mixin stays under its GATE-11
budget, the same split the radio mixin uses for quick_play and song_history.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.podcasts import inference_budget
from quill.core.podcasts.chapter_cascade import CascadeInputs, announce
from quill.core.podcasts.chapter_cascade import run as run_cascade
from quill.core.podcasts.chapter_inference import (
    load_cached_inference,
    parse_timed_cues,
    save_cached_inference,
    silence_chapters_for_podcast,
)
from quill.core.podcasts.chapter_scoring import (
    SOURCE_LABELS,
    SOURCE_SILENCE,
    SOURCE_TRANSCRIPT,
    ChapterAnswer,
    apply_scores,
    describe,
    score,
)
from quill.core.podcasts.chapter_sources import MIN_EPISODE_MS, show_identity
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import InferenceBudget
from quill.core.podcasts.playback_cache import local_audio_path
from quill.ui.podcasts.chapter_cues import (
    _cue_source,
    _fetch_transcript_tier,
    _note_anchor_tier,
    _transcript_tier,
)


def _episode_total_ms(episode: Any) -> int:
    return int(getattr(episode, "duration_seconds", 0) or 0) * 1000


def _cached_answer(
    show_id: str, guid: str, audio_path: Path | None, total_ms: int
) -> ChapterAnswer | None:
    """A previous run's result, re-scored so it can be compared with a new one.

    Re-scored rather than trusted: the cache stores chapters and a source, and a
    confidence that was computed by a different version of the scorer would be a
    number nobody can account for.
    """
    chapters, source = load_cached_inference(show_id, guid, audio_path=audio_path)
    if len(chapters) < 2 or not source:
        return None
    return apply_scores(
        score(chapters, source, total_ms=total_ms, examined="a previous scan"),
        total_ms=total_ms,
    )


def _silence_tier(
    audio_path: Path | None,
    ffmpeg: str,
    budget: InferenceBudget,
    total_ms: int,
    evidence: dict[str, Any],
):
    """Tier 4: scan the audio for the pauses between sections."""

    def _run() -> list[PodcastChapter]:
        if not ffmpeg or audio_path is None or not audio_path.is_file():
            return []
        from quill.core.speech.ffmpeg import probe_duration_ms
        from quill.core.speech.silence import build_silence_detect_command, parse_silence_log
        from quill.stability.safe_subprocess import run_subprocess_safely

        completed = run_subprocess_safely(
            build_silence_detect_command(
                ffmpeg,
                audio_path,
                noise_db=budget.noise_db,
                min_silence_s=budget.min_silence_seconds,
            ),
            timeout_seconds=600.0,
        )
        scanned_ms = total_ms or probe_duration_ms(audio_path)
        evidence["examined"][SOURCE_SILENCE] = f"{scanned_ms // 60000} minutes of audio"
        return silence_chapters_for_podcast(parse_silence_log(completed.stderr or ""), scanned_ms)

    return _run


def infer_chapters(
    show_id: str,
    episode_guid: str,
    *,
    total_ms: int,
    audio_path: Path | None,
    ffmpeg: str = "",
    budget: InferenceBudget | None = None,
    show: Any = None,
    episode: Any = None,
    safe_mode: bool = False,
    ask: Callable[[str], str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> ChapterAnswer:
    """Run every tier the budget allows and return the best answer. Never raises.

    Pure orchestration so it can be exercised without wx: the caller supplies the
    ffmpeg path (empty disables the audio tier), the budget, and *ask* -- the
    model call used to name sections under Deep, absent in Safe Mode and absent
    whenever the listener has not asked for naming.
    """
    effort = budget or inference_budget.for_budget(inference_budget.THOROUGH)
    evidence: dict[str, Any] = {"cohesion_margin": 0.0, "examined": {}}

    cues_for = _cue_source(
        show,
        episode,
        show_id,
        episode_guid,
        effort,
        evidence,
        safe_mode,
        audio_path=audio_path,
        progress=progress,
    )
    inputs = CascadeInputs(
        cached=lambda: _cached_answer(show_id, episode_guid, audio_path, total_ms),
        note_anchors=_note_anchor_tier(episode, cues_for, total_ms, evidence)
        if episode is not None
        else None,
        transcript=_transcript_tier(cues_for, effort, total_ms, evidence),
        fetch_transcript=_fetch_transcript_tier(cues_for, effort, total_ms, evidence)
        if episode is not None
        else None,
        silence_scan=_silence_tier(audio_path, ffmpeg, effort, total_ms, evidence),
        total_ms=total_ms,
        examined=evidence["examined"],
    )
    answer = run_cascade(inputs, effort)
    # The margin is only known once the transcript tier has actually run, so the
    # answer is re-scored with it rather than the cascade being asked to guess.
    if answer.source == SOURCE_TRANSCRIPT and evidence["cohesion_margin"]:
        answer = apply_scores(
            score(
                list(answer.chapters),
                answer.source,
                total_ms=total_ms,
                cohesion_margin=float(evidence["cohesion_margin"]),
                examined=answer.examined,
            ),
            total_ms=total_ms,
        )
    if ask is not None and effort.may_name_sections and not answer.is_authored:
        answer = _name_sections(answer, show_id, episode_guid, effort, ask)
    return answer


def _name_sections(
    answer: ChapterAnswer,
    show_id: str,
    guid: str,
    budget: InferenceBudget,
    ask: Callable[[str], str],
) -> ChapterAnswer:
    """Retitle inferred sections by what they are *about*. Never raises.

    Only for inferred answers: an authored title was written by a person and no
    model improves on that. The text comes from the transcript already on this
    machine, so this costs one request and no transcription -- and if there is no
    transcript there is nothing to read, so the sections keep the titles they
    have rather than being given plausible inventions.
    """
    from quill.core.podcasts.chapter_naming import name_sections
    from quill.core.podcasts.transcripts import load_cached_transcript

    rows = list(answer.chapters)
    if len(rows) < 2:
        return answer
    try:
        raw = load_cached_transcript(show_id, guid)
    except Exception:  # noqa: BLE001 - no transcript is simply nothing to read
        return answer
    if not raw:
        return answer

    cues = parse_timed_cues(raw)
    if not cues:
        return answer
    texts: list[str] = []
    for index, chapter in enumerate(rows):
        end_ms = rows[index + 1].start_ms if index + 1 < len(rows) else None
        texts.append(
            " ".join(
                cue.text
                for cue in cues
                if cue.start_ms >= chapter.start_ms and (end_ms is None or cue.start_ms < end_ms)
            )
        )
    named = name_sections(rows, texts, ask, budget=budget, whole_text_available=True)
    return ChapterAnswer(
        chapters=tuple(named),
        source=answer.source,
        confidence=answer.confidence,
        examined=answer.examined,
    )


def find_chapters_for_episode(host: Any, show: Any, episode: Any) -> None:
    """Command handler: find chapters for *episode*, off the UI thread.

    Announces at every exit, because this is a request whose answer is sometimes
    "there was nothing to find" -- and a command that silently does nothing is
    indistinguishable from one that is broken.
    """
    if show is None or episode is None:
        host._announce("Play or select an episode first.")
        return

    show_id = show_identity(show)
    guid = str(getattr(episode, "guid", ""))
    if not show_id or not guid:
        host._announce("This episode cannot be identified.")
        return

    total_ms = _episode_total_ms(episode)
    if total_ms and total_ms < MIN_EPISODE_MS:
        host._announce("This episode is too short to need chapters.")
        return

    budget = _budget_for(host, show)
    # A streamed episode whose bytes are in the playback cache is scannable
    # exactly like a downloaded one -- that is the whole point of the cache.
    audio_path = local_audio_path(show, episode)
    safe_mode = bool(getattr(host, "_safe_mode", False))

    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = (find_ffmpeg() or "") if budget.may_scan_audio else ""
    scanning = bool(ffmpeg and audio_path is not None and audio_path.is_file())
    host._announce(
        "Looking for chapters. Scanning the audio may take a moment..."
        if scanning
        else "Looking for chapters..."
    )

    ask = _assistant_for(host) if budget.may_name_sections and not safe_mode else None

    def _work(**_kwargs: object) -> ChapterAnswer:
        return infer_chapters(
            show_id,
            guid,
            total_ms=total_ms,
            audio_path=audio_path,
            ffmpeg=ffmpeg,
            budget=budget,
            show=show,
            episode=episode,
            safe_mode=safe_mode,
            ask=ask,
        )

    def _done(_op: str, result: object) -> None:
        answer = result if isinstance(result, ChapterAnswer) else ChapterAnswer()
        host._wx.CallAfter(_apply, host, show_id, guid, answer)

    def _failed(*_args: object) -> None:
        host._wx.CallAfter(host._announce, "Could not look for chapters in this episode.")

    host._task_manager.submit(
        "podcast-chapter-inference", _work, on_success=_done, on_failure=_failed
    )


def _assistant_for(host: Any) -> Callable[[str], str] | None:
    """The frame's assistant as a plain ``prompt -> reply`` call, or ``None``.

    The same gate every other AI surface uses: absent in Safe Mode, and absent
    when no assistant is configured. Section naming then simply does not happen
    and the sections keep the titles the segmenter gave them, which is the
    behaviour ``chapter_naming`` is built around.
    """
    if not hasattr(host, "_get_assistant"):
        return None

    def _ask(prompt: str) -> str:
        return str(host._get_assistant().ask(prompt))

    return _ask


def _budget_for(host: Any, show: Any) -> InferenceBudget:
    """How hard to look, from this show's effective settings.

    Falls back to Thorough rather than to Quick when the settings cannot be
    read: a library that has not loaded should behave like a default install,
    not like one whose owner quietly turned the feature down.
    """
    try:
        settings = host._podcast_library.effective_settings(show)
    except Exception:  # noqa: BLE001 - a missing library is not a reason to fail
        return inference_budget.for_budget(inference_budget.THOROUGH)
    return inference_budget.from_settings(settings)


def _apply(host: Any, show_id: str, guid: str, answer: ChapterAnswer) -> None:
    """Adopt an inferred list for the playing episode, and say what happened."""
    if not answer.is_useful or len(answer.chapters) < 2:
        host._announce(
            "No chapters could be found in this episode. "
            "Its publisher did not provide any, and neither the transcript nor "
            "the audio suggested clear sections."
        )
        return

    chapters = list(answer.chapters)
    show = host._podcast_library.find_show(show_id)
    episode = show.find_episode(guid) if show is not None else None
    save_cached_inference(
        show_id,
        guid,
        chapters,
        answer.source,
        audio_path=local_audio_path(show, episode) if episode is not None else None,
    )

    # Only adopt into the player when this is still the episode being played.
    if getattr(host, "_podcast_chapters_key", None) == (show_id, guid):
        host._podcast_current_chapters = chapters
        host._podcast_chapters_source = SOURCE_LABELS.get(answer.source, answer.source)
        # Kept so "How were these found?" can answer without recomputing.
        host._podcast_chapters_report = describe(answer)

    host._announce(announce(answer))
