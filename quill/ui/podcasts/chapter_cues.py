"""One transcript per episode, and every tier that reads words.

Three tiers need the same words -- the show-note anchors, the lexical
segmentation, and the fetch or the local transcription that feeds them -- and a
transcript obtained three times for one episode would be three waits and three
times the bytes for an answer that cannot differ. So there is one source, it is
memoised, and the tiers are thin wrappers over it.

**Where the words come from, cheapest first.** A transcript already cached with
its timings; then the one the episode publishes, fetched once and kept; then, and
only under Deep, one made on this machine. Each step costs an order of magnitude
more than the one above it, which is why the budget authorises each separately
and why the tier that is described as "already on this machine" must not quietly
fetch -- if it did, the tier below it could never run.

Split out of ``chapter_inference_ui`` when that module reached its GATE-11
ceiling. The seam is a real one rather than a line-count convenience: this file
is about *obtaining words*, and what remains is about *turning them into a
chapter list*.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.podcasts.chapter_inference import (
    TimedCue,
    parse_timed_cues,
    segment_with_evidence,
)
from quill.core.podcasts.chapter_scoring import SOURCE_NOTE_ANCHORS, SOURCE_TRANSCRIPT
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import InferenceBudget
from quill.core.podcasts.note_anchors import anchored_chapters, topic_phrases


def _fetch_cues(
    show: Any, episode: Any, show_id: str, guid: str, safe_mode: bool
) -> list[TimedCue]:
    """Download the transcript the episode publishes, cache it, return its cues.

    The single biggest gap in the old path: an episode publishing a perfectly
    good transcript URL fell straight through to the slow audio scan because
    nobody had happened to open it yet.
    """
    url = str(getattr(episode, "transcript_url", "") or "")
    if not url or safe_mode:
        return []
    from quill.core.podcasts import feed_auth
    from quill.core.podcasts.transcripts import (
        cues_to_vtt,
        fetch_transcript_cues,
        save_cached_transcript,
    )

    try:
        auth_header = feed_auth.auth_header_for_url(show, url) if show is not None else ""
    except Exception:  # noqa: BLE001 - an auth lookup that fails is simply no header
        auth_header = ""
    cues = fetch_transcript_cues(
        url,
        str(getattr(episode, "transcript_type", "") or ""),
        safe_mode=safe_mode,
        auth_header=auth_header,
    )
    if not cues:
        return []
    # Fetched once, kept: the next question about this episode -- chapters,
    # search, follow-along -- must not pay for the same download again. Both
    # forms, because search wants words and chapters want times, and the flat
    # form alone is why the "already on this machine" tier could never find
    # anything (see transcripts.save_cached_transcript_vtt).
    vtt = cues_to_vtt(cues)
    try:
        from quill.core.podcasts.transcripts import cues_to_text, save_cached_transcript_vtt

        save_cached_transcript(show_id, guid, cues_to_text(cues))
        save_cached_transcript_vtt(show_id, guid, vtt)
    except Exception:  # noqa: BLE001 - a cache that cannot be written is not an error
        pass
    return parse_timed_cues(vtt, "text/vtt")


def _transcribe_cues(
    audio_path: Path | None,
    show_id: str,
    guid: str,
    progress: Callable[[str], None] | None = None,
) -> list[TimedCue]:
    """Transcribe the episode on this machine, and keep the result.

    Only ever reached under Deep, and only when nothing published a transcript.
    Minutes of work, so it is cached in both forms the moment it finishes: the
    second time somebody asks about this episode -- for chapters, for search,
    to follow along -- the answer is already here.

    The engine is chosen by :func:`speech.service.preferred_chapter_provider_id`,
    **not** by the dictation ladder. Chapters want a transcript whose cues break
    at natural pauses far more than they want the last few points of word
    accuracy, and the engine that does that is the small one that ships in the
    box. Returns [] rather than raising: an engine that cannot run is a tier
    without an answer, exactly like a transcript nobody published.
    """
    if audio_path is None or not audio_path.is_file():
        return []
    try:
        from quill.core.podcasts.transcripts import (
            TranscriptCue,
            cues_to_text,
            cues_to_vtt,
            save_cached_transcript,
            save_cached_transcript_vtt,
        )
        from quill.core.speech.provider import TranscriptionRequest
        from quill.core.speech.service import build_registry, preferred_chapter_provider_id

        registry = build_registry()
        provider = registry.get(preferred_chapter_provider_id(registry))
        if provider is None:
            return []
        installed = [m.model_id for m in provider.list_installed_models()]
        model_id = installed[0] if installed else _default_model_for(provider)
        if not model_id:
            return []
        if progress is not None:
            progress("Listening to the episode. This is the slow part.")
        result = provider.transcribe_file(
            TranscriptionRequest(source_path=audio_path, model_id=model_id, output_timestamps=True)
        )
    except Exception:  # noqa: BLE001 - a tier that cannot run is one we do without
        return []

    cues = [
        TranscriptCue(
            start_ms=int(segment.start_seconds * 1000),
            end_ms=int(segment.end_seconds * 1000),
            text=segment.text.strip(),
        )
        for segment in result.segments
        if segment.text.strip()
    ]
    if not cues:
        return []
    vtt = cues_to_vtt(cues)
    try:
        save_cached_transcript(show_id, guid, cues_to_text(cues))
        save_cached_transcript_vtt(show_id, guid, vtt)
    except Exception:  # noqa: BLE001 - a cache that cannot be written is not an error
        pass
    return parse_timed_cues(vtt, "text/vtt")


def _default_model_for(provider: Any) -> str:
    """The engine's own recommended model, when none is installed yet.

    A bundled model is not "installed" in the model-manager's sense -- nothing
    was downloaded -- so asking only for installed models would refuse to use
    the very model the build shipped for this.
    """
    try:
        supported = provider.list_supported_models()
    except Exception:  # noqa: BLE001
        return ""
    return str(getattr(supported[0], "id", "")) if supported else ""


def _cue_source(
    show: Any,
    episode: Any,
    show_id: str,
    guid: str,
    budget: InferenceBudget,
    evidence: dict[str, Any],
    safe_mode: bool,
    audio_path: Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> Callable[..., list[TimedCue]]:
    """One transcript, read or fetched **once**, for every tier that needs words.

    Three tiers read the same words now -- the show-note anchors, the lexical
    segmentation, and the fetch that feeds it -- and a transcript downloaded
    three times for one episode would be three waits and three times the bytes
    for an answer that cannot differ. The memo lives in *evidence* because that
    dictionary is already the one thing every tier shares.

    *allow_fetch* is the caller's, not the budget's: the budget says whether a
    fetch is permitted at all, and the tier says whether *it* is the one that
    should pay for it. Tier 3 is "a transcript already on this machine" and must
    stay that, or the tier below it would never run.
    """

    def _get(*, allow_fetch: bool) -> list[TimedCue]:
        state: dict[str, Any] = evidence.setdefault("transcript", {"cues": None, "fetched": False})
        if state["cues"] is not None:
            return list(state["cues"])

        # The timed cache first, then the flat one. The flat one is only ever
        # useful when it happens to hold a timed format already; a transcript
        # whose timings were dropped on the way in cannot be segmented.
        try:
            from quill.core.podcasts.transcripts import (
                load_cached_transcript,
                load_cached_transcript_vtt,
            )

            raw = load_cached_transcript_vtt(show_id, guid) or load_cached_transcript(show_id, guid)
        except Exception:  # noqa: BLE001 - an unreadable cache is simply no transcript
            raw = ""
        if raw:
            cached = parse_timed_cues(raw)
            if cached:
                state["cues"] = cached
                return list(cached)
        if not allow_fetch:
            return []

        if budget.may_fetch_transcript and not safe_mode and episode is not None:
            fetched = _fetch_cues(show, episode, show_id, guid, safe_mode)
            if fetched:
                state["cues"] = fetched
                state["fetched"] = True
                return list(fetched)

        # Last, and only when the listener chose Deep: make one. Everything
        # above is seconds; this is minutes, which is why it is the only tier
        # that has to be asked for by name.
        if budget.may_transcribe:
            made = _transcribe_cues(audio_path, show_id, guid, progress)
            if made:
                state["cues"] = made
                state["transcribed"] = True
                return list(made)
        return []

    return _get


def _segment_cues(
    cues: list[TimedCue], budget: InferenceBudget, total_ms: int, evidence: dict[str, Any]
) -> list[PodcastChapter]:
    """Segment one transcript and record what the tier examined."""
    found = segment_with_evidence(
        cues,
        total_ms=total_ms,
        min_chapter_ms=budget.min_chapter_ms,
        window_seconds=budget.window_seconds,
        max_chapters=budget.max_chapters,
    )
    # The margin is the only evidence this tier has about its own quality, and
    # the scorer has always asked for it.
    evidence["cohesion_margin"] = found.cohesion_margin
    state = evidence.get("transcript", {})
    if state.get("transcribed"):
        how = ", transcribed on this machine"
    elif state.get("fetched"):
        how = ", fetched"
    else:
        how = ""
    evidence["examined"][SOURCE_TRANSCRIPT] = f"{len(cues):,} transcript lines{how}"
    return found.chapters


def _transcript_tier(
    cues_for: Callable[..., list[TimedCue]],
    budget: InferenceBudget,
    total_ms: int,
    evidence: dict[str, Any],
) -> Callable[[], list[PodcastChapter]]:
    """Tier 3: segment a transcript already on this machine."""

    def _run() -> list[PodcastChapter]:
        cues = cues_for(allow_fetch=False)
        return _segment_cues(cues, budget, total_ms, evidence) if cues else []

    return _run


def _fetch_transcript_tier(
    cues_for: Callable[..., list[TimedCue]],
    budget: InferenceBudget,
    total_ms: int,
    evidence: dict[str, Any],
) -> Callable[[], list[PodcastChapter]]:
    """Tier 3b: fetch the transcript the episode publishes, then segment it."""

    def _run() -> list[PodcastChapter]:
        cues = cues_for(allow_fetch=True)
        return _segment_cues(cues, budget, total_ms, evidence) if cues else []

    return _run


def _note_anchor_tier(
    episode: Any,
    cues_for: Callable[..., list[TimedCue]],
    total_ms: int,
    evidence: dict[str, Any],
) -> Callable[[], list[PodcastChapter]]:
    """The publisher's running order, matched to where each topic arrives.

    Most feeds describe their segments in prose and timestamp none of them, so
    for those episodes this is the only route to titles a person wrote -- and it
    needs no model. See :mod:`quill.core.podcasts.note_anchors`.
    """

    def _run() -> list[PodcastChapter]:
        description = str(getattr(episode, "description", "") or "")
        if not description:
            return []
        cues = cues_for(allow_fetch=True)
        if not cues:
            return []
        rows = anchored_chapters(description, cues, total_ms)
        if rows:
            evidence["examined"][SOURCE_NOTE_ANCHORS] = (
                f"{len(topic_phrases(description))} topics described in the show notes, "
                f"{len(cues):,} transcript lines"
            )
        return rows

    return _run
