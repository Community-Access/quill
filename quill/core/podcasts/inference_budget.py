"""How long are you willing to wait? Everything else is derived from that.

The instinct on reaching a pile of tunable constants -- a silence threshold in
decibels, a cohesion window in cues, a title length in characters -- is to expose
them. That instinct is wrong here, and so is hiding everything.

**Nobody can reason about "silence threshold -35 dB".** A listener can reason
about exactly one thing: *how long am I willing to wait for this?* So there is
one control, it has three values, and every constant below is a function of it.

* **Quick** -- a published chapter list, or a transcript already downloaded.
  Never transcribes, never scans. Instant.
* **Thorough** (the default) -- fetches a published transcript if one exists;
  otherwise listens to the audio for pauses. Names sections from text it already
  has. Seconds.
* **Deep** -- transcribes the audio locally, segments that, then names the
  sections. Minutes, with progress and a real cancel.

The advanced values stay adjustable in a settings *file* for anybody who
genuinely wants them, and are deliberately absent from the UI. The failure mode
of exposing them is a listener nudging ``noise_db`` once and quietly getting
worse chapters forever, with no way to know that is what happened.

**The one derived number worth naming** is ``sample_seconds``: how much of each
candidate section is examined before it is named. This is a *cost-avoidance
measure for transcription*, never a quality choice -- where the text is already
in hand, the whole section is used, because reading less would save nothing and
lose accuracy.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

QUICK = "quick"
THOROUGH = "thorough"
DEEP = "deep"

#: The three, in the order the settings control offers them.
BUDGETS: tuple[str, ...] = (QUICK, THOROUGH, DEEP)

#: What each one promises, in the listener's terms rather than the machine's.
BUDGET_LABELS: dict[str, str] = {
    QUICK: "Quick -- only what is already here",
    THOROUGH: "Thorough -- fetch a transcript, or listen for pauses",
    DEEP: "Deep -- transcribe the episode, then work out the sections",
}

BUDGET_DESCRIPTIONS: dict[str, str] = {
    QUICK: "Instant. Uses a published chapter list or a transcript already downloaded.",
    THOROUGH: "Seconds. Fetches a published transcript if there is one; otherwise listens "
    "to the audio for pauses.",
    DEEP: "Minutes. Transcribes the episode on this machine, then works out the sections "
    "from what was said. You can cancel at any point.",
}


@dataclass(frozen=True, slots=True)
class InferenceBudget:
    """Every knob in the chapter cascade, derived from one choice.

    Constructed with :func:`for_budget` rather than by hand, so the derivation
    lives in one place and a caller cannot accidentally mix a Quick sample size
    with a Deep threshold.
    """

    name: str = THOROUGH

    #: May a published transcript be fetched when the cache is cold? The single
    #: biggest gap in the old cascade: an episode publishing a perfectly good
    #: transcript URL fell straight through to a slow audio scan because nobody
    #: had opened it yet. The best free answer available was routinely skipped.
    may_fetch_transcript: bool = True
    #: May the audio be scanned for silences? Tens of seconds.
    may_scan_audio: bool = True
    #: May the audio be transcribed locally? Minutes, and only on request.
    may_transcribe: bool = False
    #: May a model be asked to name the sections (text only, never audio)?
    may_name_sections: bool = False

    #: Silence detection. -35 dB and 1.6 s are the shipped values; Deep listens
    #: harder because it is allowed to take longer.
    noise_db: float = -35.0
    min_silence_seconds: float = 1.6
    #: No section shorter than this, whatever the detector says.
    min_chapter_ms: int = 90_000

    #: Transcript segmentation: how many cues each comparison window holds, and
    #: the most sections to produce.
    window_cues: int = 8
    max_chapters: int = 60

    #: How much of a section is examined to name it, **when naming would
    #: otherwise require transcribing audio nobody has asked to pay for**. A
    #: twelve-section hour becomes twelve minutes of transcription rather than
    #: sixty. Where the text is already in hand this is ignored and the whole
    #: section is used.
    sample_seconds: int = 60
    #: A section's first minute is very often the tail of the previous topic, an
    #: ad read, or throat-clearing, with the real subject arriving later -- so
    #: the sample is the opening *plus* a short probe from the middle. Naming a
    #: chapter after what the host was just finishing is exactly the sort of
    #: confident-but-wrong output rule A-10 exists to prevent.
    middle_probe_seconds: int = 20

    @property
    def is_instant(self) -> bool:
        return not (self.may_fetch_transcript or self.may_scan_audio or self.may_transcribe)

    @property
    def label(self) -> str:
        return BUDGET_LABELS.get(self.name, self.name)

    def describe(self) -> str:
        return BUDGET_DESCRIPTIONS.get(self.name, "")


def for_budget(name: str) -> InferenceBudget:
    """The whole configuration for one budget. Unknown names read as Thorough.

    Thorough rather than Quick for an unknown value, because it is the default
    and a settings file with a typo in it should behave like a settings file
    with nothing in it -- not like one that quietly turned the feature down.
    """
    wanted = (name or "").strip().lower()
    if wanted == QUICK:
        return InferenceBudget(
            name=QUICK,
            may_fetch_transcript=False,
            may_scan_audio=False,
            may_transcribe=False,
            may_name_sections=False,
        )
    if wanted == DEEP:
        return InferenceBudget(
            name=DEEP,
            may_fetch_transcript=True,
            may_scan_audio=True,
            may_transcribe=True,
            may_name_sections=True,
            # Listening harder is affordable when minutes are already on offer.
            noise_db=-40.0,
            min_silence_seconds=1.2,
            window_cues=10,
            max_chapters=80,
            # Deep has the whole transcript, so sampling is not a constraint --
            # it is set high only for the case where a section still has to be
            # transcribed on its own.
            sample_seconds=180,
            middle_probe_seconds=45,
        )
    return InferenceBudget(name=THOROUGH)


def describe_plan(budget: InferenceBudget) -> str:
    """What this budget will and will not do, as a sentence.

    Shown beside the setting, because "Thorough" on its own does not tell
    somebody whether their laptop is about to spend a minute on this.
    """
    allowed: list[str] = ["use a published chapter list or a transcript already here"]
    if budget.may_fetch_transcript:
        allowed.append("fetch a published transcript")
    if budget.may_scan_audio:
        allowed.append("listen to the audio for pauses")
    if budget.may_transcribe:
        allowed.append("transcribe the episode on this machine")
    if budget.may_name_sections:
        allowed.append("name the sections")
    if len(allowed) == 1:
        return f"Will {allowed[0]}."
    return "Will " + ", ".join(allowed[:-1]) + f", and {allowed[-1]}."


def from_settings(settings: object) -> InferenceBudget:
    """The budget a show's effective settings ask for.

    The individual tier switches **disable**, they do not deprioritise: a
    listener who said "never scan the audio" has said something specific and
    must be obeyed even under Deep. That asymmetry is the whole reason this
    function exists rather than the caller reading ``chapters_effort`` and
    hoping.
    """
    budget = for_budget(str(getattr(settings, "chapters_effort", THOROUGH) or THOROUGH))
    if not bool(getattr(settings, "chapters_use_transcript", True)):
        budget = replace(budget, may_fetch_transcript=False)
    if not bool(getattr(settings, "chapters_scan_audio", True)):
        budget = replace(budget, may_scan_audio=False, may_transcribe=False)
    if not bool(getattr(settings, "chapters_name_sections", False)):
        budget = replace(budget, may_name_sections=False)
    return budget


def is_enabled(settings: object, *, downloaded: bool) -> bool:
    """Whether chapters should be worked out for this episode at all.

    "when_downloaded" is the default because a downloaded episode is one the
    listener already committed to, so the work costs them nothing they had not
    accepted. "off" means off -- and it means it everywhere, which is the point
    of having one switch rather than a scattering of them.
    """
    mode = str(getattr(settings, "chapters_auto", "when_downloaded") or "when_downloaded")
    if mode == "off":
        return False
    if mode == "always":
        return True
    return bool(downloaded)
