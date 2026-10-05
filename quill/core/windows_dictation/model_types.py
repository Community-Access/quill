"""The shapes of an optional speech model, shared by the catalogue modules.

Split out of :mod:`~quill.core.windows_dictation.model_catalog` (GATE-11) when
the Whisper family joined it; that module re-exports the ones callers use.

Pure data and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CPU_ONLY",
    "GROUPS",
    "MODEST",
    "SHERPA_SOURCE",
    "STRONG",
    "TOO_BIG",
    "DownloadFile",
    "DownloadableModel",
    "file",
    "megabytes",
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
    def language_names(self) -> str:
        return " and ".join({"en": "English", "es": "Spanish"}[code] for code in self.languages)

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
