"""The shapes of an optional speech model, shared by the catalogue modules.

Split out of :mod:`~quill.core.windows_dictation.model_catalog` (GATE-11) when
the Whisper family joined it; that module re-exports the ones callers use.

Pure data and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BALANCED",
    "CPU_ONLY",
    "GROUPS",
    "HIGH_ACCURACY",
    "HOTWORDS",
    "HOTWORD_MODELS",
    "LIGHTWEIGHT",
    "MEASURED",
    "MODEST",
    "RAM_TIERS",
    "SHERPA_SOURCE",
    "STREAMING_KINDS",
    "STRONG",
    "TASKS",
    "TIERS",
    "TIER_MEANINGS",
    "TIMESTAMPS",
    "TOO_BIG",
    "TRANSCRIBE",
    "TRANSLATE",
    "DownloadFile",
    "DownloadableModel",
    "Measured",
    "estimated_peak_mb",
    "file",
    "legacy_tier",
    "megabytes",
    "ram_tier_budget_mb",
    "ram_tier_for",
    "ram_tier_sentence",
    "tasks_for",
    "tier_for",
]

_HF = "https://huggingface.co/"
#: Said in every model's description (the owner's wording, 2026-10-05).
CPU_ONLY = "Runs on your computer's processor; no graphics card needed."

#: The Speech Models list's groups, in the order it shows them.
GROUPS: tuple[str, ...] = (
    "The models VS Code offers",
    "Whisper, English only",
    "Whisper, many languages",
    "Lighter",
)


@dataclass(frozen=True, slots=True)
class DownloadFile:
    """One file of a model: its name on disk, the part it plays, and its pin."""

    name: str
    #: ``encoder``, ``decoder``, ``joiner``, ``tokens`` or ``licence``.
    role: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DownloadableModel:
    """An optional model, as Dictation Settings lists it and dictation runs it."""

    #: Also the engine id saved in ``windows_dictation_engine`` once chosen.
    id: str
    name: str
    #: One line: what it is good for. The list shows it beside the name.
    good_for: str
    #: Plain words, a few sentences, for the details box and F1.
    description: str
    group: str
    #: How sherpa-onnx loads it: ``nemotron`` (streaming transducer),
    #: ``nemo_transducer`` (Parakeet), ``whisper`` or ``moonshine_v2``.
    kind: str
    #: Languages dictation offers with it (``en``, ``es``).
    languages: tuple[str, ...]
    works_best_on: str
    #: Published accuracy, naming what was measured and where it was published.
    accuracy: str
    repo: str
    commit: str
    files: tuple[DownloadFile, ...]
    licence: str
    licence_url: str
    #: Who publishes the files, for the consent sentence.
    source: str
    #: Seconds of computing per second of speech on one thread, as a multiple of
    #: the bundled Moonshine tiny's on the same recordings on the same machine
    #: (measured 2026-10-05 with dictbench, dict.md 4.5; Distil-Whisper and
    #: large-v3, not downloaded whole, are estimated from their sizes). The
    #: two-second check multiplies this computer's Moonshine tiny time by it.
    cost_factor: float
    #: Folder under the downloads root.
    folder: str
    #: VS Code's own default, shown as the suggested download.
    suggested: bool = False

    @property
    def download_bytes(self) -> int:
        return sum(item.size for item in self.files)

    @property
    def disk_bytes(self) -> int:
        """The same as the download: the files are stored as they arrive."""
        return self.download_bytes

    @property
    def engine_label(self) -> str:
        """The row in the Speech engine list once it is downloaded."""
        return f"{self.name} (downloaded)"

    @property
    def tier(self) -> str:
        """Lightweight, Balanced or High accuracy (D-22, :func:`tier_for`)."""
        measured = MEASURED.get(self.id)
        return tier_for(self.cost_factor, measured.word_errors if measured else None)

    @property
    def language_names(self) -> str:
        return " and ".join({"en": "English", "es": "Spanish"}[code] for code in self.languages)

    # -- the shared layer's catalogue fields (dict.md D-26) ------------------- #
    #
    # Derived, never typed per model, for the same reason the tier is: a new
    # entry gets them by having a kind, languages and a measurement.

    @property
    def streaming(self) -> bool:
        """Recognises while you speak (sherpa-onnx's online recogniser)."""
        return self.kind in STREAMING_KINDS

    @property
    def ram_tier(self) -> int:
        """4, 8 or 16: the smallest computer, in GB of memory, this model fits on
        beside a screen reader (:func:`ram_tier_for`)."""
        measured = MEASURED.get(self.id)
        peak = measured.peak_mb if measured else estimated_peak_mb(self.download_bytes)
        return ram_tier_for(peak)

    @property
    def tasks(self) -> frozenset[str]:
        """What it can do: :data:`TASKS` (:func:`tasks_for`)."""
        return tasks_for(self.id, self.kind, self.languages)

    @property
    def source_url(self) -> str:
        """The pinned repository page, for the licence and the details box."""
        return f"{_HF}{self.repo}/tree/{self.commit}"

    def url(self, item: DownloadFile) -> str:
        return f"{_HF}{self.repo}/resolve/{self.commit}/{item.name}"


def megabytes(size: int) -> str:
    """``"682 MB"`` -- decimal megabytes, as Hugging Face and download dialogs show."""
    if size >= 1_000_000_000:
        return f"{size / 1_000_000_000:.1f} GB"
    return f"{round(size / 1_000_000):,} MB"


def file(name: str, role: str, size: int, sha256: str) -> DownloadFile:
    return DownloadFile(name, role, size, sha256)


SHERPA_SOURCE = "Hugging Face (converted for sherpa-onnx by its authors)"
MODEST = "Runs on most computers, but slower than the built-in engines."
STRONG = "A computer with four or more processor cores and 8 GB of memory or more."
TOO_BIG = (
    "A fast computer with 16 GB of memory. Far too slow for live dictation on a "
    "dual-core computer with 8 GB; there it is only for when you can wait."
)


# -- tiers (D-22) ---------------------------------------------------------------- #
#
# One vocabulary for every place a speech model is chosen: dictation's Speech
# engine list and Speech Models, QUILL Transcribe's Choose Model and Set Up, and
# QUILL's Manage Speech Models and guided offline-speech setup. Named in dict.md
# D-22; the tier is derived, never typed per model, so a new catalogue entry
# gets one by having a cost factor.

LIGHTWEIGHT = "Lightweight"
BALANCED = "Balanced"
HIGH_ACCURACY = "High accuracy"
TIERS: tuple[str, ...] = (LIGHTWEIGHT, BALANCED, HIGH_ACCURACY)

#: One plain sentence per tier, for details boxes and F1.
TIER_MEANINGS: dict[str, str] = {
    LIGHTWEIGHT: "Lightweight: keeps up comfortably even on a modest computer.",
    BALANCED: (
        "Balanced: more work than the built-in engines; keeps up on a computer with "
        "four or more cores."
    ),
    HIGH_ACCURACY: (
        "High accuracy: the fewest mistakes, for the most work; needs a capable "
        "computer, or patience."
    ),
}

#: The cost-factor bands. Moonshine tiny measured 0.05 seconds of computing per
#: second of speech on the measuring machine (dictation design, section 6), so a
#: model up to 5 times its cost stays inside the 0.25 one-thread budget there
#: (Lightweight), and up to 10 times keeps up on the two threads dictation uses
#: (Balanced). speed_check.BUDGET is the same 0.25; it is not imported here
#: because speed_check imports the catalogue, which imports this module.
_LIGHT_MAX_COST = 5.0
_BALANCED_MAX_COST = 10.0
#: A Balanced-cost model whose measured word errors are this low or lower is
#: labelled High accuracy: the most accurate model measured, at a price a
#: four-core computer can pay (Nemotron, 2.5 percent).
_HIGH_ACCURACY_WORD_ERRORS = 2.5


@dataclass(frozen=True, slots=True)
class Measured:
    """What scripts/dictbench.py measured for one model.

    ``word_errors`` and ``after_pause`` are still the 2026-10-05 synthetic-voice
    figures (ten recordings, one thread; dictation design, section 6), an
    estimate until B-1's English real-voice run is written in. ``peak_mb`` and
    ``word_errors_es`` are real speech (2026-10-22 machine run: LibriSpeech,
    LibriVox held-out, FLEURS), and the peaks are the highest seen on any set,
    because a model must fit the worst minute, not the average one.
    """

    #: Percent of words wrong, English (synthetic voice).
    word_errors: float
    #: Seconds from the end of speech to the text, on the measuring machine.
    after_pause: float
    #: Most memory while recognising, in megabytes (real speech).
    peak_mb: int
    #: Percent of words wrong in Spanish, real speech: the mean of FLEURS
    #: Spanish and the LibriVox Spanish held-out set. ``None`` = not measured,
    #: and a model with no Spanish figure is never recommended for Spanish.
    word_errors_es: float | None = None


#: Keyed by engine id (built in) or catalogue id (downloads). A model missing
#: here was not measured and is never recommended: a reason needs a number.
MEASURED: dict[str, Measured] = {
    "moonshine": Measured(3.4, 0.2, 584),
    # Spanish is the multilingual tiny: 30.5 FLEURS, 27.0 LibriVox.
    "whisper": Measured(3.4, 0.7, 521, word_errors_es=28.8),
    # Real speech scored 50 to 73 percent wrong on 2026-10-22 against 3.4 on the
    # synthetic voice: under investigation, so its synthetic figure stays.
    "moonshine_base": Measured(3.4, 0.3, 461),
    # Spanish 12.6 FLEURS, 16.1 LibriVox.
    "whisper_base": Measured(5.1, 1.4, 806, word_errors_es=14.4),
    "parakeet_unified": Measured(3.4, 1.2, 1278),
    # Spanish 4.4 FLEURS, 7.3 LibriVox: the most accurate Spanish model measured.
    "parakeet": Measured(4.2, 1.2, 1136, word_errors_es=5.9),
    # Spanish 6.4 FLEURS, 8.0 LibriVox.
    "nemotron": Measured(2.5, 1.5, 1538, word_errors_es=7.2),
    # Spanish 6.0 FLEURS, 7.8 LibriVox; accurate, but over the speed budget.
    "whisper_small": Measured(5.1, 4.7, 1435, word_errors_es=6.9),
    "whisper_medium": Measured(3.4, 11.2, 2100),
    "whisper_turbo": Measured(3.4, 15.4, 2128),
}


def tier_for(cost_factor: float, word_errors: float | None = None) -> str:
    """The tier for a model costing *cost_factor* times Moonshine tiny, given
    its *word_errors* (percent) when they were measured."""
    if cost_factor <= _LIGHT_MAX_COST:
        return LIGHTWEIGHT
    if cost_factor <= _BALANCED_MAX_COST:
        if word_errors is not None and word_errors <= _HIGH_ACCURACY_WORD_ERRORS:
            return HIGH_ACCURACY
        return BALANCED
    return HIGH_ACCURACY


#: QUILL's Locked Dictation catalogue names two of the live models under other
#: ids; they take the live model's tier, so one model is never two tiers. The
#: cost factors are the live catalogue's (not imported: it imports this module).
_LEGACY_SAME_AS: dict[str, tuple[str, float]] = {
    "nemotron-streaming-en-0.6b": ("nemotron", 8.0),
    "parakeet-tdt-0.6b-v3": ("parakeet", 6.3),
}


# -- memory tiers, tasks and streaming (D-26) --------------------------------- #

#: ``(tier in GB, megabytes dictation may take beside a screen reader there)``.
#: The same budgets model_advice holds a recommendation to, and the same as
#: scripts/bench_machine_run.py's: 600 MB on a 4 GB computer, 1.6 GB on an 8 GB
#: one (the baseline since 2026-10-22, dictation design section 1), 4 GB above.
#: model_advice also caps by the memory *free* when it is asked.
RAM_TIERS: tuple[tuple[int, int], ...] = ((4, 600), (8, 1600), (16, 4000))

#: sherpa-onnx loader kinds that stream (online recognisers).
STREAMING_KINDS = frozenset({"nemotron"})

TRANSCRIBE = "transcribe"
TRANSLATE = "translate"
TIMESTAMPS = "timestamps"
HOTWORDS = "hotwords"
TASKS: tuple[str, ...] = (TRANSCRIBE, TRANSLATE, TIMESTAMPS, HOTWORDS)

#: Models measured to learn My Words while listening (D-28). A model joins only
#: once the real-voice benchmark (B-1) shows hotwords help it with no regression
#: elsewhere. None has yet: Nemotron's streaming decoder is greedy-only and
#: Parakeet's NeMo hotwords came out upper-cased and garbled (measured
#: 2026-10-05, dictation design, section 5 B); English Zipformer transducers,
#: the realistic route, are not in the catalogue yet.
HOTWORD_MODELS: frozenset[str] = frozenset()


def ram_tier_for(peak_mb: int) -> int:
    """The smallest memory tier whose budget holds a model peaking at *peak_mb*."""
    for tier, budget in RAM_TIERS:
        if peak_mb <= budget:
            return tier
    return RAM_TIERS[-1][0]


def ram_tier_budget_mb(memory_gb: float) -> int:
    """What dictation may take beside the screen reader on a computer with
    *memory_gb* of memory: the budget of the largest tier it reaches. A 4 GB
    computer reports a little under 4, so the bands are 7 and 15."""
    if memory_gb < 7.0:
        return RAM_TIERS[0][1]
    if memory_gb < 15.0:
        return RAM_TIERS[1][1]
    return RAM_TIERS[2][1]


def estimated_peak_mb(download_bytes: int) -> int:
    """Peak memory for a model nobody measured, from its download: the int8
    weights plus working memory (the measured models ran 1.2 to 2.6 times
    their download, the small ones highest)."""
    download_mb = download_bytes / 1_000_000
    return int(max(download_mb * 1.3, download_mb + 200))


def ram_tier_sentence(tier: int) -> str:
    """``"Fits a computer with 8 GB of memory or more."``"""
    return f"Fits a computer with {tier} GB of memory or more."


def tasks_for(model_id: str, kind: str, languages: tuple[str, ...]) -> frozenset[str]:
    """Every model transcribes, and every model gives phrase timestamps (the
    voice detector cuts the phrases, so the times are the same for all).
    Multilingual Whisper translates into English (``task="translate"``);
    hotwords only for :data:`HOTWORD_MODELS`."""
    found = {TRANSCRIBE, TIMESTAMPS}
    if kind == "whisper" and set(languages) - {"en"}:
        found.add(TRANSLATE)
    if model_id in HOTWORD_MODELS:
        found.add(HOTWORDS)
    return frozenset(found)


def legacy_tier(model_id: str, size_mb: int, accuracy_tier: str) -> str:
    """The tier for a model in QUILL's whisper.cpp / Faster Whisper catalogue
    (``quill.core.speech.catalog``), which has sizes and accuracy words rather
    than measured costs: 200 MB or less is Lightweight, a "high" or "highest"
    accuracy model is High accuracy, everything between is Balanced."""
    same = _LEGACY_SAME_AS.get(model_id)
    if same is not None:
        live_id, cost = same
        measured = MEASURED.get(live_id)
        return tier_for(cost, measured.word_errors if measured else None)
    if size_mb <= 200:
        return LIGHTWEIGHT
    if accuracy_tier in {"high", "highest"}:
        return HIGH_ACCURACY
    return BALANCED
