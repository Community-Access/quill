"""Branchable, resumable AI writing sessions (AI-20).

A writing session is a *tree* of turns, not a flat transcript. Every turn has a
parent, so a writer can go back to an earlier point, try a second rewrite of a
section, and keep both branches without losing state. The active branch tip is
``current_turn_id``; appending a turn adds a child of the current tip, and
*branching* simply moves the tip back to an earlier turn so the next append
creates a sibling.

This module is UI-framework-agnostic (no ``wx`` imports) and fully
deterministic: identifier and timestamp generation can be injected for tests.
Sessions are persisted as schema-stable JSON under ``<data>/ai-sessions`` with
atomic writes, matching the rest of ``quill.core``.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
_ROLES = frozenset({ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM})

_SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Injectable generators (overridable in tests for determinism)
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionTurn:
    """One turn in the session tree."""

    turn_id: str
    parent_id: str | None
    role: str
    text: str
    created_at: str
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "parent_id": self.parent_id,
            "role": self.role,
            "text": self.text,
            "created_at": self.created_at,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionTurn:
        return cls(
            turn_id=str(data["turn_id"]),
            parent_id=(None if data.get("parent_id") is None else str(data["parent_id"])),
            role=str(data.get("role", ROLE_USER)),
            text=str(data.get("text", "")),
            created_at=str(data.get("created_at", "")),
            label=(None if data.get("label") is None else str(data["label"])),
        )


@dataclass(frozen=True)
class WritingSession:
    """An immutable snapshot of a branchable writing session."""

    session_id: str
    title: str
    created_at: str
    updated_at: str
    turns: tuple[SessionTurn, ...]
    current_turn_id: str | None

    # -- lookups ---------------------------------------------------------

    def turn(self, turn_id: str) -> SessionTurn | None:
        for turn in self.turns:
            if turn.turn_id == turn_id:
                return turn
        return None

    def children(self, turn_id: str | None) -> tuple[SessionTurn, ...]:
        return tuple(turn for turn in self.turns if turn.parent_id == turn_id)

    # -- serialization ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_turn_id": self.current_turn_id,
            "turns": [turn.to_dict() for turn in self.turns],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WritingSession:
        turns = tuple(SessionTurn.from_dict(item) for item in data.get("turns", []))
        return cls(
            session_id=str(data["session_id"]),
            title=str(data.get("title", "Untitled session")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            turns=turns,
            current_turn_id=(
                None if data.get("current_turn_id") is None else str(data["current_turn_id"])
            ),
        )


@dataclass(frozen=True)
class SessionSummary:
    """A lightweight listing entry for the session browser."""

    session_id: str
    title: str
    updated_at: str
    turn_count: int
    branch_count: int


# ---------------------------------------------------------------------------
# Construction and editing (pure functions returning new snapshots)
# ---------------------------------------------------------------------------


def new_session(
    title: str,
    *,
    id_factory: Callable[[], str] = _new_id,
    clock: Callable[[], str] = _now,
) -> WritingSession:
    """Create an empty session with no turns and no active tip."""

    timestamp = clock()
    return WritingSession(
        session_id=id_factory(),
        title=title.strip() or "Untitled session",
        created_at=timestamp,
        updated_at=timestamp,
        turns=(),
        current_turn_id=None,
    )


def append_turn(
    session: WritingSession,
    role: str,
    text: str,
    *,
    label: str | None = None,
    id_factory: Callable[[], str] = _new_id,
    clock: Callable[[], str] = _now,
) -> WritingSession:
    """Append a turn as a child of the current tip and advance the tip.

    If the current tip was moved back to an earlier turn (see
    :func:`branch_from`), this creates a *sibling* branch at that point.
    """

    if role not in _ROLES:
        raise ValueError(f"Unknown role: {role!r}")

    timestamp = clock()
    turn = SessionTurn(
        turn_id=id_factory(),
        parent_id=session.current_turn_id,
        role=role,
        text=text,
        created_at=timestamp,
        label=label,
    )
    return replace(
        session,
        turns=session.turns + (turn,),
        current_turn_id=turn.turn_id,
        updated_at=timestamp,
    )


def branch_from(
    session: WritingSession,
    turn_id: str,
    *,
    clock: Callable[[], str] = _now,
) -> WritingSession:
    """Move the active tip back to ``turn_id`` so the next append branches.

    This does not delete anything; both branches remain. Raises ``KeyError``
    if the turn is not part of the session.
    """

    if session.turn(turn_id) is None:
        raise KeyError(turn_id)
    return replace(session, current_turn_id=turn_id, updated_at=clock())


def resume(
    session: WritingSession,
    turn_id: str,
    *,
    clock: Callable[[], str] = _now,
) -> WritingSession:
    """Set the active tip to ``turn_id`` to continue from that point."""

    return branch_from(session, turn_id, clock=clock)


def relabel_turn(
    session: WritingSession,
    turn_id: str,
    label: str | None,
    *,
    clock: Callable[[], str] = _now,
) -> WritingSession:
    """Attach or clear a human-friendly label on a turn (for navigation)."""

    target = session.turn(turn_id)
    if target is None:
        raise KeyError(turn_id)
    updated = tuple(
        replace(turn, label=label) if turn.turn_id == turn_id else turn for turn in session.turns
    )
    return replace(session, turns=updated, updated_at=clock())


# ---------------------------------------------------------------------------
# Navigation and inspection
# ---------------------------------------------------------------------------


def path_to(session: WritingSession, turn_id: str) -> tuple[SessionTurn, ...]:
    """Return the lineage from the root to ``turn_id`` (inclusive, in order)."""

    by_id = {turn.turn_id: turn for turn in session.turns}
    if turn_id not in by_id:
        raise KeyError(turn_id)
    chain: list[SessionTurn] = []
    cursor: str | None = turn_id
    seen: set[str] = set()
    while cursor is not None and cursor in by_id and cursor not in seen:
        seen.add(cursor)
        turn = by_id[cursor]
        chain.append(turn)
        cursor = turn.parent_id
    chain.reverse()
    return tuple(chain)


def current_path(session: WritingSession) -> tuple[SessionTurn, ...]:
    """The conversation along the active branch, root to current tip."""

    if session.current_turn_id is None:
        return ()
    return path_to(session, session.current_turn_id)


def branch_tips(session: WritingSession) -> tuple[SessionTurn, ...]:
    """Return the leaf turns — the end of every distinct branch."""

    has_children = {turn.parent_id for turn in session.turns if turn.parent_id is not None}
    return tuple(turn for turn in session.turns if turn.turn_id not in has_children)


def branch_points(session: WritingSession) -> tuple[SessionTurn, ...]:
    """Return turns that have more than one child (where the tree forks)."""

    counts: dict[str, int] = {}
    for turn in session.turns:
        if turn.parent_id is not None:
            counts[turn.parent_id] = counts.get(turn.parent_id, 0) + 1
    forks = {turn_id for turn_id, count in counts.items() if count > 1}
    return tuple(turn for turn in session.turns if turn.turn_id in forks)


@dataclass(frozen=True)
class BranchComparison:
    """The result of comparing two branch tips."""

    common_ancestor_id: str | None
    left_only: tuple[SessionTurn, ...]
    right_only: tuple[SessionTurn, ...]


def compare_branches(
    session: WritingSession, left_turn_id: str, right_turn_id: str
) -> BranchComparison:
    """Compare two branches: find their fork point and the turns unique to each."""

    left_path = path_to(session, left_turn_id)
    right_path = path_to(session, right_turn_id)
    right_ids = {turn.turn_id for turn in right_path}

    common_ancestor_id: str | None = None
    for turn in reversed(left_path):
        if turn.turn_id in right_ids:
            common_ancestor_id = turn.turn_id
            break

    def _after(path: tuple[SessionTurn, ...]) -> tuple[SessionTurn, ...]:
        if common_ancestor_id is None:
            return path
        index = next(i for i, t in enumerate(path) if t.turn_id == common_ancestor_id)
        return path[index + 1 :]

    return BranchComparison(
        common_ancestor_id=common_ancestor_id,
        left_only=_after(left_path),
        right_only=_after(right_path),
    )


# ---------------------------------------------------------------------------
# Screen-reader-friendly summaries
# ---------------------------------------------------------------------------


def summarize_session(session: WritingSession) -> str:
    """One-line spoken summary of a session."""

    turn_count = len(session.turns)
    tips = branch_tips(session)
    branch_count = len(tips) if tips else (1 if turn_count else 0)
    turn_word = "turn" if turn_count == 1 else "turns"
    branch_word = "branch" if branch_count == 1 else "branches"
    return f"{session.title}: {turn_count} {turn_word}, {branch_count} {branch_word}."


def describe_branches(session: WritingSession) -> str:
    """A spoken description of each branch tip, for the branch browser."""

    tips = branch_tips(session)
    if not tips:
        return "This session has no turns yet."
    lines: list[str] = []
    for index, tip in enumerate(tips, start=1):
        depth = len(path_to(session, tip.turn_id))
        name = tip.label or _preview(tip.text)
        active = " (current)" if tip.turn_id == session.current_turn_id else ""
        lines.append(f"Branch {index}: {name} — {depth} turns{active}")
    return "\n".join(lines)


def _preview(text: str, limit: int = 60) -> str:
    collapsed = " ".join(text.split())
    if not collapsed:
        return "(empty)"
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "\u2026"


# ---------------------------------------------------------------------------
# Branch-browser view model (consumed by the accessible UI surface)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BranchRow:
    """One selectable row in the accessible branch browser."""

    turn_id: str
    label: str
    depth: int
    is_current: bool


def branch_rows(session: WritingSession) -> tuple[BranchRow, ...]:
    """Selectable rows — one per branch tip — for the branch-browser list.

    Each row carries the tip ``turn_id`` (for one-key jump/resume), a spoken
    ``label`` that marks the current branch, the branch ``depth``, and an
    ``is_current`` flag so the UI can pre-select and announce the active branch.
    """

    rows: list[BranchRow] = []
    for index, tip in enumerate(branch_tips(session), start=1):
        depth = len(path_to(session, tip.turn_id))
        name = tip.label or _preview(tip.text)
        is_current = tip.turn_id == session.current_turn_id
        suffix = " (current)" if is_current else ""
        rows.append(
            BranchRow(
                turn_id=tip.turn_id,
                label=f"Branch {index}: {name} — {depth} turns{suffix}",
                depth=depth,
                is_current=is_current,
            )
        )
    return tuple(rows)


def format_comparison(session: WritingSession, left_turn_id: str, right_turn_id: str) -> str:
    """A screen-reader-pageable comparison of two branches for the compare view."""

    comparison = compare_branches(session, left_turn_id, right_turn_id)
    lines: list[str] = []
    if comparison.common_ancestor_id is None:
        lines.append("These branches share no common point.")
    else:
        ancestor = session.turn(comparison.common_ancestor_id)
        where = _preview(ancestor.text) if ancestor is not None else "the start"
        lines.append(f"Branches diverge after: {where}")
    lines.append("")
    lines.append(f"Only on the first branch ({len(comparison.left_only)} turns):")
    for turn in comparison.left_only:
        lines.append(f"  {turn.role}: {_preview(turn.text)}")
    lines.append("")
    lines.append(f"Only on the second branch ({len(comparison.right_only)} turns):")
    for turn in comparison.right_only:
        lines.append(f"  {turn.role}: {_preview(turn.text)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


#: The folder name sessions live in, under whichever app's data folder.
SESSIONS_FOLDER = "ai-sessions"


def sessions_dir(directory: Path | None = None) -> Path:
    """Where sessions are kept: *directory*, else QUILL's ``ai-sessions``.

    *directory* lets the shared hosted-AI conversation window keep its
    conversations under whichever app it runs in -- QUILL's own data folder
    (the same folder Ask Quill writes, so AI Session Branches sees them too)
    or QUILL Lite's -- with this one store and its one format.
    """
    return directory if directory is not None else app_data_dir() / SESSIONS_FOLDER


def _session_path(session_id: str, directory: Path | None = None) -> Path:
    # Guard against path traversal in the identifier.
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")
    if not safe or safe != session_id:
        raise ValueError(f"Unsafe session id: {session_id!r}")
    return sessions_dir(directory) / f"{safe}.json"


def save_session(session: WritingSession, *, directory: Path | None = None) -> Path:
    """Persist a session atomically and return its path."""

    path = _session_path(session.session_id, directory)
    write_json_atomic(path, session.to_dict())
    return path


def record_exchange(
    session: WritingSession | None,
    user_text: str,
    assistant_text: str,
    *,
    directory: Path | None = None,
) -> WritingSession | None:
    """Add one question and its answer to *session* and save it.

    Starts a session titled after the first message when *session* is
    ``None``. Returns the updated session, or the one it was given when there
    is nothing to record (an empty side). Extracted from Ask Quill's panel
    (``quill/ui/assistant_panel.py``) so the hosted-AI conversation window
    saves the same way into the same store; both call this.
    """
    if not user_text.strip() or not assistant_text.strip():
        return session
    if session is None:
        title = " ".join(user_text.split())[:60] or "Writing session"
        session = new_session(title)
    session = append_turn(session, ROLE_USER, user_text)
    session = append_turn(session, ROLE_ASSISTANT, assistant_text)
    save_session(session, directory=directory)
    return session


def load_session(session_id: str, *, directory: Path | None = None) -> WritingSession | None:
    path = _session_path(session_id, directory)
    data = read_json(path, default=None)
    if not isinstance(data, dict):
        return None
    return WritingSession.from_dict(data)


def delete_session(session_id: str, *, directory: Path | None = None) -> bool:
    path = _session_path(session_id, directory)
    if path.exists():
        path.unlink()
        return True
    return False


def list_sessions(*, directory: Path | None = None) -> tuple[SessionSummary, ...]:
    """List saved sessions, most recently updated first."""

    directory = sessions_dir(directory)
    if not directory.exists():
        return ()
    summaries: list[SessionSummary] = []
    for path in directory.glob("*.json"):
        data = read_json(path, default=None)
        if not isinstance(data, dict):
            continue
        try:
            session = WritingSession.from_dict(data)
        except (KeyError, ValueError):
            continue
        tips = branch_tips(session)
        branch_count = len(tips) if tips else (1 if session.turns else 0)
        summaries.append(
            SessionSummary(
                session_id=session.session_id,
                title=session.title,
                updated_at=session.updated_at,
                turn_count=len(session.turns),
                branch_count=branch_count,
            )
        )
    summaries.sort(key=lambda item: item.updated_at, reverse=True)
    return tuple(summaries)


def most_recent_session() -> WritingSession | None:
    """Load the most recently updated session, for continue-most-recent."""

    summaries = list_sessions()
    if not summaries:
        return None
    return load_session(summaries[0].session_id)
