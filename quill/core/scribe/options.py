"""The family's Scribe for Documents options (PRD 7.7), one set for every app.

Kept in the shared QUILL data folder (``scribe/options.json``), not in each
app's ``settings.json``: the PRD's goal 5 is one sign-in, one queue and one
set of choices for the whole family, and the Options page is "shared and
mirrored in each app's options". So QUILL and QUILL Lite read the same file
and cannot drift, and the settings vocabulary gate has nothing to reconcile.

Tokens never go here; they are in the vault (:mod:`.auth`). Nor does a PDF
password, ever.

wx-free.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from quill.core.scribe.model import ScribeSettings, valid_formats
from quill.core.storage import read_json, write_json_atomic

#: "Open each result when it is ready" (7.7): open it, offer it, or neither.
OPEN_CHOICES: tuple[tuple[str, str], ...] = (
    ("yes", "Open it"),
    ("offer", "Ask me first"),
    ("no", "Don't open"),
)
#: "Speak each stage" (7.4a). Start, finish and errors are always spoken.
SPEAK_CHOICES: tuple[tuple[str, str], ...] = (
    ("front", "Only while a QUILL app is in front"),
    ("always", "Always"),
    ("never", "Never"),
)


@dataclass(slots=True)
class ScribeOptions:
    default_formats: list[str] = field(default_factory=lambda: ["docx"])
    #: The last formats chosen in the convert dialog, which beat the default.
    last_formats: list[str] = field(default_factory=list)
    #: Empty means ``Documents\\Scribe for Documents``.
    download_folder: str = ""
    open_results: str = "yes"
    offer_low_text_pdf: bool = True
    speak_stages: str = "front"
    #: Pneuma's batch exception (7.4): off until Pneuma grants it.
    batch_exception: bool = False
    #: Local default settings, kept apart from Scribe's account defaults.
    settings: dict[str, Any] = field(default_factory=dict)
    #: The privacy lines (10.1.2) are added to the first upload's consent only.
    first_upload_done: bool = False

    def local_settings(self) -> ScribeSettings:
        return ScribeSettings.from_mapping(self.settings)

    def formats_for(self, app_default: list[str] | None = None) -> list[str]:
        """The formats to tick: the last choice, else the app's, else the default."""
        for candidate in (self.last_formats, app_default or [], self.default_formats):
            chosen = valid_formats(candidate)
            if chosen:
                return chosen
        return ["docx"]


def options_path() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "scribe" / "options.json"


def load_options(path: Path | None = None) -> ScribeOptions:
    data = read_json(path or options_path(), {})
    if not isinstance(data, dict):
        return ScribeOptions()
    base = ScribeOptions()
    open_ids = {key for key, _ in OPEN_CHOICES}
    speak_ids = {key for key, _ in SPEAK_CHOICES}
    return ScribeOptions(
        default_formats=valid_formats(data.get("default_formats")) or base.default_formats,
        last_formats=valid_formats(data.get("last_formats")),
        download_folder=str(data.get("download_folder") or ""),
        open_results=str(data.get("open_results"))
        if data.get("open_results") in open_ids
        else "yes",
        offer_low_text_pdf=bool(data.get("offer_low_text_pdf", True)),
        speak_stages=str(data.get("speak_stages"))
        if data.get("speak_stages") in speak_ids
        else "front",
        batch_exception=bool(data.get("batch_exception", False)),
        settings=ScribeSettings.from_mapping(data.get("settings") or {}).to_dict()
        if data.get("settings")
        else {},
        first_upload_done=bool(data.get("first_upload_done", False)),
    )


def save_options(options: ScribeOptions, path: Path | None = None) -> None:
    write_json_atomic(path or options_path(), asdict(options))


__all__ = [
    "OPEN_CHOICES",
    "SPEAK_CHOICES",
    "ScribeOptions",
    "load_options",
    "options_path",
    "save_options",
]
