"""Which dictation model suits this computer, and why (dict.md D-22).

Given the two-second check (:mod:`~quill.core.windows_dictation.speed_check`:
Moonshine tiny's speed here, the processor cores and the memory), the dictation
language and what the person cares about most, :func:`recommend` names **one**
model and says why in a sentence a listener can take in at once:

    "Moonshine base, Lightweight: keeps up on this computer's 8 GB and 4 cores,
    about 0.3 seconds after you pause; stays on this computer; a 141 MB
    download."

**It never switches anything.** There is no automatic mode (dictation design,
section 1: the model is sticky). The recommendation is a line of text in the
windows where a model is chosen; the person still chooses.

**How it chooses.** Only models with a measurement (``model_types.MEASURED``)
are candidates, because a reason needs a number, and only ones that know the
language. A candidate must keep up: inside the 0.25 one-thread budget, or, for
"The fewest mistakes" and on a computer with 16 GB and four cores, on the two
threads dictation uses. It must also fit beside the screen reader in memory
(600 MB on a computer under 7 GB, 1.6 GB under 15 GB), and in what is *free*
when you ask, less half a gigabyte kept back for the screen reader. Spanish is
ranked by real Spanish speech, and only models measured in Spanish are offered
for it. Of those left, the fewest
word errors win; ties go to the bigger model of the pair, except on a modest
computer, where the built-in model wins a tie because a download that is no
more accurate is not worth having. "The quickest response" takes the
lightest. When nothing keeps up, the lightest built-in model for the language
is named, with the warning that it may lag.

**Estimates, said so.** Every figure comes from ten recordings of a synthetic
voice (dictation design, section 6), so the reasons say "estimate" until the
real-voice benchmark (B-1) exists.

The GPU, when one is detected, is mentioned only to say it changes nothing:
every dictation model runs on the processor.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable
from quill.core.windows_dictation.model_types import (
    LIGHTWEIGHT,
    MEASURED,
    RAM_TIERS,
    TIER_MEANINGS,
    megabytes,
    ram_tier_budget_mb,
    tier_for,
)
from quill.core.windows_dictation.speech_language import coerce_speech_language
from quill.core.windows_dictation.speed_check import (
    _CAPABLE_TINY,
    _WEAK_TINY,
    BUDGET,
    SpeedCheck,
)

__all__ = [
    "ESTIMATE_NOTE",
    "PRIORITIES",
    "PRIORITY_ACCURACY",
    "PRIORITY_BALANCED",
    "PRIORITY_SPEED",
    "Recommendation",
    "engine_tier",
    "for_this_computer",
    "recommend",
]

PRIORITY_BALANCED = "balanced"
PRIORITY_SPEED = "speed"
PRIORITY_ACCURACY = "accuracy"
#: ``(value, label)`` for a chooser, the default first.
PRIORITIES: tuple[tuple[str, str], ...] = (
    (PRIORITY_BALANCED, "A balance of speed and accuracy"),
    (PRIORITY_SPEED, "The quickest response"),
    (PRIORITY_ACCURACY, "The fewest mistakes"),
)
_CHOSEN_FOR = {
    PRIORITY_BALANCED: "Chosen for a balance of speed and accuracy.",
    PRIORITY_SPEED: "Chosen for the quickest response.",
    PRIORITY_ACCURACY: "Chosen for the fewest mistakes this computer can keep up with.",
}
ESTIMATE_NOTE = "Measured on one computer with real recordings; yours may differ."
_NEVER_SWITCHES = "QUILL never changes your model by itself: choose this one if you want it."

#: The built-in engines' cost against Moonshine tiny: Whisper tiny.en measured
#: 0.20 against Moonshine tiny's 0.05 (dictation design, section 6). Spanish
#: runs the multilingual tiny of the same size.
_BUILT_IN_COST = {"moonshine": 1.0, "whisper": 2.6}  # whisper: real speech, 2026-10-22
_BUILT_IN_LANGUAGES = {"moonshine": ("en",), "whisper": ("en", "es")}
_BUILT_IN_NAMES = {"moonshine": "Moonshine (built in)", "whisper": "Whisper (built in)"}
#: Moonshine tiny on the measuring machine; scales "after you pause" to here.
_MEASURED_TINY = 0.05
#: When word errors tie, the model earlier here wins: the bigger of a pair, with
#: Whisper tiny last because it is slower than Moonshine for the same score.
_TIE_ORDER = (
    "nemotron",
    "parakeet_unified",
    "whisper_turbo",
    "whisper_medium",
    "moonshine_base",
    "parakeet",
    "moonshine",
    "whisper",
    "whisper_small",
    "whisper_base",
)
_LANGUAGE_NAMES = {"en": "English", "es": "Spanish"}
#: Megabytes kept free beside a model, for the screen reader and the editor.
_FREE_RESERVE_MB = 500


@dataclass(frozen=True, slots=True)
class _Candidate:
    id: str
    name: str
    cost_factor: float
    built_in: bool
    download_bytes: int

    @property
    def tier(self) -> str:
        return tier_for(self.cost_factor, MEASURED[self.id].word_errors)


@dataclass(frozen=True, slots=True)
class Recommendation:
    """One model and why. :attr:`sentence` is the one line; :attr:`reasons`
    are the sentences behind it, for a details box."""

    #: The engine id to save in ``windows_dictation_engine`` if the person agrees.
    model_id: str
    name: str
    tier: str
    built_in: bool
    download_bytes: int
    sentence: str
    reasons: tuple[str, ...]
    #: ``True`` when even this, the lightest that fits, may fall behind a talker.
    may_lag: bool = False

    @property
    def line(self) -> str:
        """What the windows show: "Recommended for this computer: ..."."""
        return f"Recommended for this computer: {self.sentence}"

    @property
    def details(self) -> str:
        """The line and every reason, one per line, for a read-only text box."""
        return "\n".join((self.line, *self.reasons))


def engine_tier(engine_id: str) -> str:
    """The tier of a dictation engine id, or ``""`` for one that is not a model
    (Windows speech recognition, voice typing, OpenAI)."""
    model = downloadable(engine_id)
    if model is not None:
        return model.tier
    cost = _BUILT_IN_COST.get(engine_id)
    if cost is None:
        return ""
    return tier_for(cost, MEASURED[engine_id].word_errors)


def _errors(engine_id: str, language: str) -> float:
    """Percent of words wrong for *language*: Spanish has its own figure."""
    measured = MEASURED[engine_id]
    if language == "es" and measured.word_errors_es is not None:
        return measured.word_errors_es
    return measured.word_errors


def _candidates(language: str) -> list[_Candidate]:
    found = [
        _Candidate(engine_id, _BUILT_IN_NAMES[engine_id], cost, True, 0)
        for engine_id, cost in _BUILT_IN_COST.items()
        if language in _BUILT_IN_LANGUAGES[engine_id]
    ]
    found += [
        _Candidate(model.id, model.name, model.cost_factor, False, model.download_bytes)
        for model in CATALOGUE
        if model.id in MEASURED and language in model.languages
    ]
    if language == "es":  # a Spanish reason needs a Spanish number
        found = [c for c in found if MEASURED[c.id].word_errors_es is not None]
    return found


def _tiny_here(check: SpeedCheck) -> float:
    if check.tiny is not None:
        return check.tiny
    return _WEAK_TINY if check.weak else _CAPABLE_TINY


def _tier_cap_mb(check: SpeedCheck) -> int:
    """The catalogue's memory tier for this computer's total (D-26)."""
    memory = check.memory_gb
    if memory is None:  # unmeasured: a modest computer is treated as 4 GB, else 8
        return ram_tier_budget_mb(4.0 if check.weak else 8.0)
    return ram_tier_budget_mb(memory)


def _memory_cap_mb(check: SpeedCheck) -> int:
    """How much memory dictation may take beside the screen reader here: the
    tier for the total, and no more than is free now less a reserve. Never
    below the smallest tier, so the built-in models are always possible."""
    cap = _tier_cap_mb(check)
    if check.available_gb is not None:
        free_mb = int(check.available_gb * 1024) - _FREE_RESERVE_MB
        cap = min(cap, max(RAM_TIERS[0][1], free_mb))
    return cap


def _machine(check: SpeedCheck) -> str:
    cores = f"{check.cores} core" + ("" if check.cores == 1 else "s")
    if check.memory_gb is None:
        return f"this computer's {cores}"
    return f"this computer's {round(check.memory_gb)} GB and {cores}"


def _sort_key(
    candidate: _Candidate, *, built_in_first: bool, language: str = "en"
) -> tuple[float, int, int]:
    order = _TIE_ORDER.index(candidate.id) if candidate.id in _TIE_ORDER else len(_TIE_ORDER)
    preference = 0 if (candidate.built_in or not built_in_first) else 1
    return (_errors(candidate.id, language), preference, order)


def recommend(
    check: SpeedCheck,
    language: str = "en",
    privacy: str = "local",
    *,
    priority: str = PRIORITY_BALANCED,
    has_gpu: bool | None = None,
) -> Recommendation:
    """The model that suits this computer for *language*, and why.

    *privacy* is ``"local"`` (the default) or ``"any"``; every candidate keeps the
    speech on this computer either way, because the one internet engine needs
    the person's own key and consent and is never offered unasked. *priority*
    is one of :data:`PRIORITIES`; anything else counts as the balance.
    *has_gpu* defaults to what the check found.
    """
    language = coerce_speech_language(language)
    if priority not in _CHOSEN_FOR:
        priority = PRIORITY_BALANCED
    tiny = _tiny_here(check)
    memory_cap = _memory_cap_mb(check)
    roomy = not check.weak and check.memory_gb is not None and check.memory_gb >= 15.0
    two_threads = priority == PRIORITY_ACCURACY or (priority == PRIORITY_BALANCED and roomy)
    limit = 2 * BUDGET if two_threads else BUDGET
    candidates = _candidates(language)

    def speed(candidate: _Candidate) -> float:
        return tiny * candidate.cost_factor

    def excluded(candidate: _Candidate) -> str:
        """Why *candidate* is not for this computer, or ``""``."""
        if MEASURED[candidate.id].peak_mb > memory_cap:
            if memory_cap < _tier_cap_mb(check):
                return "needs more memory than is free on this computer right now"
            return "needs more memory than this computer can spare beside your screen reader"
        if speed(candidate) > 2 * BUDGET:
            return "would lag behind your speech here"
        if speed(candidate) > limit:
            return "would take a second processor thread here, which can slow your screen reader"
        return ""

    allowed = [c for c in candidates if not excluded(c)]
    lightest = not allowed
    if lightest:
        chosen = min((c for c in candidates if c.built_in), key=lambda c: c.cost_factor)
    elif priority == PRIORITY_SPEED:
        chosen = min(allowed, key=lambda c: (c.cost_factor, _errors(c.id, language)))
    else:
        built_in_first = check.weak and priority == PRIORITY_BALANCED
        chosen = min(
            allowed,
            key=lambda c: _sort_key(c, built_in_first=built_in_first, language=language),
        )

    machine = _machine(check)
    pace = speed(chosen)
    may_lag = pace > 2 * BUDGET
    if may_lag:
        keeps_up = f"may lag behind your speech on {machine}"
    elif pace <= BUDGET:
        keeps_up = f"keeps up on {machine}"
    else:
        keeps_up = f"keeps up on {machine} using two processor threads"
    if lightest:
        keeps_up = f"the lightest model for {_LANGUAGE_NAMES[language]}; it {keeps_up}"
    after = MEASURED[chosen.id].after_pause * tiny / _MEASURED_TINY
    download = (
        "already installed" if chosen.built_in else f"a {megabytes(chosen.download_bytes)} download"
    )
    sentence = (
        f"{chosen.name}, {chosen.tier}: {keeps_up}, about {after:.1f} seconds after you "
        f"pause; stays on this computer; {download}."
    )

    reasons: list[str] = [_CHOSEN_FOR[priority], TIER_MEANINGS[chosen.tier]]
    if language == "es":
        errors = _errors(chosen.id, language)
        reasons.append(f"With real Spanish speakers, it got {errors:g} percent of words wrong.")
    else:
        errors = MEASURED[chosen.id].word_errors
        reasons.append(f"In our test it got {errors:g} percent of words wrong.")
    if pace > BUDGET and not may_lag:
        reasons.append(
            "It uses more of the processor than the built-in engines, so your screen "
            "reader may answer a little more slowly while you dictate."
        )
    better = sorted(
        (
            c
            for c in candidates
            if _errors(c.id, language) < _errors(chosen.id, language) and excluded(c)
        ),
        key=lambda c: _sort_key(c, built_in_first=False, language=language),
    )
    if better:
        reasons.append(f"{better[0].name} makes fewer mistakes but {excluded(better[0])}.")
    if chosen.built_in and chosen.tier == LIGHTWEIGHT and not lightest:
        reasons.append("Nothing to download: it is already on this computer.")
    if check.has_gpu if has_gpu is None else has_gpu:
        reasons.append(
            "Your graphics card is not used: dictation models run on the processor, "
            "so it does not change this advice."
        )
    if check.tiny is None:
        reasons.append("The speed was estimated from the processor and memory, not timed.")
    if privacy != "local":
        reasons.append("Only models that keep your speech on this computer are recommended.")
    reasons += [ESTIMATE_NOTE, _NEVER_SWITCHES]
    return Recommendation(
        model_id=chosen.id,
        name=chosen.name,
        tier=chosen.tier,
        built_in=chosen.built_in,
        download_bytes=chosen.download_bytes,
        sentence=sentence,
        reasons=tuple(reasons),
        may_lag=may_lag,
    )


def for_this_computer(language: str = "en", priority: str = PRIORITY_BALANCED) -> Recommendation:
    """:func:`recommend` on this session's timed check, or on the cores and
    memory alone when none has run yet. Instant: for windows that open without
    timing anything (Choose Model, Set Up, Dictation Settings)."""
    from dataclasses import replace

    from quill.core.windows_dictation.speed_check import _available_gb, latest

    # The timed check is kept for the session; free memory is read now, because
    # what was free an hour ago says nothing about what dictation can have.
    return recommend(replace(latest(), available_gb=_available_gb()), language, priority=priority)
