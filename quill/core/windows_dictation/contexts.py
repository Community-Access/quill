"""What a document is, for dictation: "a formal letter", "notes to a friend".

dict.md 3.8 (gap 9), with the owner's answer to question 10: per document,
remembered by the document's path, with a short list of saved contexts to pick
from. **Dictation Context for This Document...** in Tools > Dictation writes it;
"dictation context formal letter" picks a saved one by voice.

**Where it is used, and where it is not.**

* OpenAI dictation sends it as the transcription ``prompt`` -- the one thing the
  transcription API accepts besides your words and the language -- so it hears
  "Dear Ms. Alvarez" rather than "dear miss alvarez" in a formal letter.
* Tidy Dictated Text sends it beside My Dictation Instructions, as a marked
  part, so the tidy-up keeps a casual note casual.
* The engines on this computer take no prompt (sherpa-onnx's Whisper and the
  transducers have no such input), and the window says so in a sentence. No
  pretending.

**Privacy.** It goes only where the audio or the text already goes: to OpenAI
when you chose OpenAI, to the AI when you asked for Tidy. Nothing new leaves
the computer because of it.

**The file.** ``dictation-contexts.json`` beside ``dictation.md``, so a portable
copy keeps it in the portable folder. Written atomically; documents that no
longer exist are dropped when it is saved.

wx-free.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import write_json_atomic

__all__ = [
    "FILE_NAME",
    "MAX_CHARACTERS",
    "STARTERS",
    "ContextStore",
    "contexts_path",
    "document_key",
    "load",
    "save",
]

FILE_NAME = "dictation-contexts.json"
_SCHEMA = 1
#: Generous for a description, and well inside OpenAI's prompt length.
MAX_CHARACTERS = 600

#: Offered in the chooser beside your own saved contexts. Plain descriptions,
#: because the person reading them may be about to pick one by voice.
STARTERS: dict[str, str] = {
    "Formal letter": "A formal letter to a client or an organisation. Full sentences, "
    "no contractions, titles such as Ms. and Dr. written out properly.",
    "Note to a friend": "A casual note to a friend. Contractions are fine, short sentences.",
    "Technical writing": "Technical writing about software and computers. Product names, "
    "version numbers and keyboard keys written as they are spelled.",
    "Meeting notes": "Notes from a meeting: names of people, actions and dates.",
    "Story": "A story, with dialogue in quotation marks.",
}


def contexts_path(profile_path: Path) -> Path:
    """The contexts file beside *profile_path* (``dictation.md``)."""
    return Path(profile_path).with_name(FILE_NAME)


def document_key(path: str | os.PathLike[str] | None) -> str:
    """How a document is remembered: its full path, case-folded on Windows.
    An untitled document has no key and is remembered only by its window."""
    if not path:
        return ""
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _clean(text: object) -> str:
    return " ".join(str(text or "").split())[:MAX_CHARACTERS]


@dataclass(slots=True)
class ContextStore:
    """Your saved contexts by name, and each document's context by path."""

    saved: dict[str, str] = field(default_factory=dict)
    documents: dict[str, str] = field(default_factory=dict)

    def for_document(self, path: str | os.PathLike[str] | None) -> str:
        return self.documents.get(document_key(path), "")

    def set_for_document(self, path: str | os.PathLike[str] | None, text: str) -> None:
        """Remember *text* for the document at *path*; empty text forgets it."""
        key = document_key(path)
        if not key:
            return
        text = _clean(text)
        if text:
            self.documents[key] = text
        else:
            self.documents.pop(key, None)

    def save_as(self, name: str, text: str) -> None:
        name, text = " ".join(name.split()), _clean(text)
        if name and text:
            self.saved[name] = text

    def choices(self) -> dict[str, str]:
        """Every context to choose from: yours first, then the starters."""
        return {**self.saved, **{k: v for k, v in STARTERS.items() if k not in self.saved}}


def load(path: Path) -> ContextStore:
    """The store at *path*; empty when there is none or it cannot be read."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ContextStore()
    if not isinstance(data, dict):
        return ContextStore()
    saved = data.get("saved")
    documents = data.get("documents")
    return ContextStore(
        saved={str(k): _clean(v) for k, v in saved.items()} if isinstance(saved, dict) else {},
        documents=(
            {str(k): _clean(v) for k, v in documents.items()} if isinstance(documents, dict) else {}
        ),
    )


def save(path: Path, store: ContextStore) -> None:
    """Write *store* atomically, dropping documents that no longer exist."""
    documents = {key: text for key, text in store.documents.items() if text and Path(key).exists()}
    store.documents = documents
    write_json_atomic(
        Path(path),
        {"schema": _SCHEMA, "saved": dict(store.saved), "documents": documents},
    )
