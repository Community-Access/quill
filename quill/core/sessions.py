from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quill.core.document import Document
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic


def sessions_dir() -> Path:
    return app_data_dir() / "sessions"


def recent_sessions_path() -> Path:
    return sessions_dir() / "recent-sessions.json"


def load_recent_sessions() -> list[Path]:
    raw = read_json(recent_sessions_path(), default=[])
    if not isinstance(raw, list):
        return []
    results: list[Path] = []
    for item in raw:
        if isinstance(item, str):
            results.append(Path(item))
    return results


def add_recent_session(path: Path, limit: int) -> list[Path]:
    normalized = path.resolve()
    existing = [entry.resolve() for entry in load_recent_sessions()]
    deduped = [entry for entry in existing if entry != normalized]
    updated = [normalized, *deduped][:limit]
    write_json_atomic(recent_sessions_path(), [str(entry) for entry in updated])
    return updated


def clear_recent_sessions() -> None:
    write_json_atomic(recent_sessions_path(), [])


def build_session_payload(
    title: str,
    active_index: int,
    documents: list[Document],
    caret_positions: list[int] | None = None,
) -> dict[str, object]:
    positions = caret_positions or [0] * len(documents)
    if len(positions) < len(documents):
        positions = list(positions) + [0] * (len(documents) - len(positions))
    # The zip() contract is one-to-one: every document pairs with a
    # position. The defensive padding above already normalises the lengths
    # to match, so the assert is a loud guard against future refactors
    # breaking that invariant; strict=True turns a regression into a
    # ValueError instead of silently dropping trailing documents.
    assert len(positions) == len(documents), (
        f"caret_positions length {len(positions)} must match documents length {len(documents)}"
    )
    return {
        "version": 1,
        "title": title,
        "saved_at": datetime.now(UTC).isoformat(),
        "active_index": active_index,
        "documents": [
            _document_payload(doc, pos) for doc, pos in zip(documents, positions, strict=True)
        ],
    }


def save_session(path: Path, payload: dict[str, object], limit: int = 10) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, payload)
    add_recent_session(path, limit)


def load_session(path: Path) -> dict[str, object]:
    raw = read_json(path, default={})
    if not isinstance(raw, dict):
        return {}
    return raw


def session_title(payload: dict[str, object], fallback: str) -> str:
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return fallback


def documents_from_session(payload: dict[str, object]) -> list[Document]:
    """Reconstruct the document list saved with a session.

    Three cases (#342):

    * The ``documents`` key is missing from the payload — return a single
      untitled :class:`Document` so the editor opens with something to type
      into.  This is the "I have never seen this session before" fallback.
    * The ``documents`` key is present and is a list — return exactly
      what the list deserialises to, including the empty list.  An empty
      list means "the user explicitly saved with no open documents", which
      the editor must honour rather than substituting a placeholder.
    * The ``documents`` key is present but is not a list — treat the
      payload as malformed and fall back to a single untitled document.
    """
    if "documents" not in payload:
        return [Document()]
    documents_payload = payload.get("documents")
    if not isinstance(documents_payload, list):
        return [Document()]

    documents: list[Document] = []
    for item in documents_payload:
        if isinstance(item, dict):
            documents.append(_document_from_payload(item))
    return documents


def caret_positions_from_session(payload: dict[str, object]) -> list[int]:
    """Return per-document caret positions saved with the session (§8.4).

    Returns a list that is the same length as ``documents_from_session()``.
    Missing or invalid entries default to 0 (start of document).
    """
    documents_payload = payload.get("documents", [])
    if not isinstance(documents_payload, list):
        return [0]
    positions: list[int] = []
    for item in documents_payload:
        if isinstance(item, dict):
            raw = item.get("caret_position", 0)
            positions.append(int(raw) if isinstance(raw, int) else 0)
        else:
            positions.append(0)
    return positions or [0]


def active_index_from_session(payload: dict[str, object], count: int) -> int:
    active_index = payload.get("active_index", 0)
    if not isinstance(active_index, int):
        return 0
    if count <= 0:
        return 0
    return max(0, min(active_index, count - 1))


def _document_payload(document: Document, caret_position: int = 0) -> dict[str, object]:
    return {
        "text": document.text,
        "path": str(document.path) if document.path is not None else None,
        "modified": document.modified,
        "encoding": document.encoding,
        "line_ending": document.line_ending,
        "source_metadata": document.source_metadata,
        # §8.4 "Resume from where I left off": editor caret position at save time.
        "caret_position": int(caret_position),
    }


def _document_from_payload(payload: dict[str, object]) -> Document:
    path_value = payload.get("path")
    path = Path(path_value) if isinstance(path_value, str) and path_value else None
    text_value = payload.get("text", "")
    modified = bool(payload.get("modified", False))
    encoding = payload.get("encoding", "utf-8")
    line_ending = payload.get("line_ending", "\n")
    source_metadata = payload.get("source_metadata", {})
    if not isinstance(text_value, str):
        text_value = ""
    if not isinstance(encoding, str):
        encoding = "utf-8"
    if not isinstance(line_ending, str):
        line_ending = "\n"
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    return Document(
        text=text_value,
        path=path,
        modified=modified,
        encoding=encoding,
        line_ending=line_ending,
        source_metadata=source_metadata,
    )
