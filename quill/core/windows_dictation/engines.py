"""The speech engines dictation can use, and where their models live.

Three, and the first two ship **inside** QUILL Lite -- nothing is downloaded,
ever, which was a condition of the design (2026-09-25):

``moonshine``
    Moonshine tiny (English), run by sherpa-onnx on the CPU. The default: the
    fastest of the candidates on a low-end machine by a wide margin, and it
    punctuates and capitalises by itself. About 124 MB of model.
``whisper``
    Whisper tiny.en, the same runtime. Comparable accuracy and punctuation,
    slower, and the one to try when Moonshine mishears a particular voice. About
    104 MB of model.
``windows``
    Windows' own recogniser (SAPI), which is what 1.1 started with. Kept for a
    machine where the models are missing or the CPU is too old for them. It does
    not punctuate by itself and its accuracy on an untrained voice is poor,
    which is why it stopped being the default.

The candidates were measured on the same ten sentences before this was
decided; the comparison is in
``docs/design/dictation for windows only/engine-comparison.md``.

**Where the models are.** Beside the program rather than inside the shared
QuillVille runtime: every sibling app installs that runtime, and a Radio user
should not download 230 MB of speech models. So the installer puts them in
``{app}\\dictation-models`` and the portable zip in ``dictation-models`` beside
its launcher, and :func:`model_dir` looks there first. A development checkout
finds them in ``build/dictation-models``, where
``scripts/fetch_dictation_models.py`` puts them.

wx-free, and free of sherpa-onnx too: this module only knows names and paths,
so a settings dialog can ask what is installed without loading a model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DEFAULT_ENGINE",
    "ENGINES",
    "MODELS_FOLDER",
    "VAD_MODEL",
    "EngineInfo",
    "ModelFile",
    "coerce_engine",
    "engine_info",
    "model_dir",
    "model_roots",
    "package_dirs",
    "vad_model_path",
]

MODELS_FOLDER = "dictation-models"


@dataclass(frozen=True, slots=True)
class ModelFile:
    """One file a model needs: its name on disk and the SHA-256 it must have.

    The digest is checked when the file is fetched for a build
    (``scripts/fetch_dictation_models.py``), never at run time -- hashing a
    hundred megabytes on every start would cost more than it protects against
    once the installer's own signature has vouched for the bytes.
    """

    name: str
    sha256: str
    #: The file inside the upstream release archive, when it is named differently.
    source: str = ""


@dataclass(frozen=True, slots=True)
class EngineInfo:
    id: str
    #: What the settings window lists.
    label: str
    #: The one sentence F1 and the settings window say about it.
    description: str
    #: Folder under ``dictation-models``; empty for an engine with no model.
    folder: str = ""
    files: tuple[ModelFile, ...] = ()
    #: Upstream archive the files come from (sherpa-onnx's model releases).
    archive: str = ""


_SHERPA_MODELS = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"

ENGINES: tuple[EngineInfo, ...] = (
    EngineInfo(
        "moonshine",
        "Moonshine (fast, punctuates for you)",
        "Built in. Recognises speech on this computer, quickly even on a modest "
        "one, and adds punctuation and capitals by itself. English.",
        folder="moonshine-tiny-en",
        archive=_SHERPA_MODELS + "sherpa-onnx-moonshine-tiny-en-int8.tar.bz2",
        files=(
            ModelFile(
                "preprocess.onnx",
                "f33addce61a143460fe753b5ee5b7db255e5140b5b779c065b94f6c83ff0bf4e",
            ),
            ModelFile(
                "encode.int8.onnx",
                "8774dfba578de027ec6595c2c654a0836434489bc963a0db124a7f181f571acb",
            ),
            ModelFile(
                "uncached_decode.int8.onnx",
                "216737000dd5881a17aa043f6bbd286add33e4c3b0ae257153e2ec15438bdc41",
            ),
            ModelFile(
                "cached_decode.int8.onnx",
                "2aff28bba6a03d8dcf5c9feac45462629bae37317442299f28115ad09da773f6",
            ),
            ModelFile(
                "tokens.txt", "1165c2aeb9f72f457a83be2d459a09054f27490acd9b41bd43794dfd25e296ea"
            ),
            ModelFile(
                "LICENSE", "29f60769d1779eb7e196d96b8d2dd471d0263cf8200c79e55c0c00183971ee1b"
            ),
        ),
    ),
    EngineInfo(
        "whisper",
        "Whisper (accurate, punctuates for you)",
        "Built in. Recognises speech on this computer and adds punctuation and "
        "capitals by itself; a little slower than Moonshine, and worth trying if "
        "Moonshine often mishears you. English.",
        folder="whisper-tiny-en",
        archive=_SHERPA_MODELS + "sherpa-onnx-whisper-tiny.en.tar.bz2",
        files=(
            ModelFile(
                "encoder.int8.onnx",
                "0ce578b827c94a961aacb8fa14b02f096504b337e5c94be37c36238cbe3e8bc6",
                source="tiny.en-encoder.int8.onnx",
            ),
            ModelFile(
                "decoder.int8.onnx",
                "06c0e6ff6348d427e51839219d1c886c18cfdf411e629e33f5e1679bff9c1527",
                source="tiny.en-decoder.int8.onnx",
            ),
            ModelFile(
                "tokens.txt",
                "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930",
                source="tiny.en-tokens.txt",
            ),
        ),
    ),
    EngineInfo(
        "windows",
        "Windows speech recognition",
        "Windows' own recogniser. Needs nothing extra, but it does not punctuate "
        "by itself and it mishears an untrained voice often. Say punctuation "
        "aloud with this one.",
    ),
    EngineInfo(
        "voice_typing",
        "Windows voice typing (Windows+H)",
        "Hands dictation to Windows' own voice typing panel, the one Windows+H "
        "opens. Windows does the recognising and the typing, so none of "
        "dictation's commands, tones, read-back or wake phrase apply -- it is "
        "here for anybody who already knows it and prefers it.",
    ),
)

#: Finds the pauses between phrases for the two model engines. MIT licensed.
VAD_MODEL = ModelFile(
    "silero_vad.onnx", "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6"
)
VAD_URL = _SHERPA_MODELS + "silero_vad.onnx"

DEFAULT_ENGINE = "moonshine"

_BY_ID = {engine.id: engine for engine in ENGINES}


def engine_info(engine_id: str) -> EngineInfo:
    return _BY_ID[coerce_engine(engine_id)]


def coerce_engine(value: object) -> str:
    """The engine *value* names, or the default for anything else."""
    text = str(value or "").strip().lower()
    return text if text in _BY_ID else DEFAULT_ENGINE


def model_roots() -> list[Path]:
    """Every folder that may hold ``dictation-models``, most specific first.

    * ``QUILL_DICTATION_MODELS`` -- an explicit override, for tests and support.
    * ``QUILL_LAUNCHER_DIR`` -- beside the program the user started. The native
      launcher exports it; on a shared-runtime install it is the only way to
      find the installer's own folder, because ``QUILL_APP_ROOT`` is the
      runtime's.
    * ``QUILL_APP_ROOT`` -- the portable folder, for a portable copy.
    * ``build/dictation-models`` in a development checkout.
    """
    roots: list[Path] = []
    override = os.environ.get("QUILL_DICTATION_MODELS", "").strip()
    if override:
        roots.append(Path(override))
    for variable in ("QUILL_LAUNCHER_DIR", "QUILL_APP_ROOT"):
        value = os.environ.get(variable, "").strip()
        if value:
            roots.append(Path(value) / MODELS_FOLDER)
    roots.append(Path(__file__).resolve().parents[3] / "build" / MODELS_FOLDER)
    return roots


def _complete(folder: Path, files: tuple[ModelFile, ...]) -> bool:
    return all((folder / item.name).is_file() for item in files)


def model_dir(engine_id: str) -> Path | None:
    """The folder holding *engine_id*'s model, or ``None`` when it is not here."""
    engine = engine_info(engine_id)
    if not engine.folder:
        return None
    for root in model_roots():
        candidate = root / engine.folder
        if _complete(candidate, engine.files):
            return candidate
    return None


def package_dirs() -> list[Path]:
    """Folders that may hold the sherpa-onnx package itself, beside the models.

    An installed QUILL Lite runs in the shared QuillVille runtime, which
    deliberately does not freeze sherpa-onnx in (it would shadow QUILL's
    engine packs -- see standalone/runtime/quillville-runtime.spec). So the
    installer carries the package in ``dictation-models/python`` and
    :mod:`~quill.core.windows_dictation.local_recognizer` adds that folder to
    the import path when the package is not importable otherwise. The portable
    zip and a development checkout have it installed normally and never look.
    """
    return [root / "python" for root in model_roots() if (root / "python").is_dir()]


def vad_model_path() -> Path | None:
    for root in model_roots():
        candidate = root / VAD_MODEL.name
        if candidate.is_file():
            return candidate
    return None
