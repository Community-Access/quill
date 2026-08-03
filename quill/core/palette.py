from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.commands import Command
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic


@dataclass(frozen=True, slots=True)
class PaletteUsage:
    count: int
    last_used_epoch: int


def palette_usage_path() -> Path:
    return app_data_dir() / "palette-usage.json"


def load_palette_usage() -> dict[str, PaletteUsage]:
    raw = read_json(palette_usage_path(), default={})
    if not isinstance(raw, dict):
        return {}
    usage: dict[str, PaletteUsage] = {}
    for command_id, payload in raw.items():
        if not isinstance(command_id, str) or not isinstance(payload, dict):
            continue
        count = payload.get("count")
        last_used_epoch = payload.get("last_used_epoch")
        if not isinstance(count, int) or not isinstance(last_used_epoch, int):
            continue
        usage[command_id] = PaletteUsage(count=count, last_used_epoch=last_used_epoch)
    return usage


def save_palette_usage(usage: dict[str, PaletteUsage]) -> None:
    payload = {
        command_id: {
            "count": entry.count,
            "last_used_epoch": entry.last_used_epoch,
        }
        for command_id, entry in usage.items()
    }
    write_json_atomic(palette_usage_path(), payload, base=app_data_dir())


def record_palette_usage(
    usage: dict[str, PaletteUsage],
    command_id: str,
    now: datetime | None = None,
) -> dict[str, PaletteUsage]:
    current = usage.get(command_id, PaletteUsage(count=0, last_used_epoch=0))
    timestamp = int((now or datetime.now(UTC)).timestamp())
    updated = usage.copy()
    updated[command_id] = PaletteUsage(
        count=current.count + 1,
        last_used_epoch=timestamp,
    )
    return updated


def rank_commands(
    commands: Iterable[Command],
    query: str,
    usage: dict[str, PaletteUsage],
) -> list[Command]:
    mode, trimmed = _parse_mode(query)
    scored: list[tuple[int, int, int, str, Command]] = []
    for command in commands:
        score = _score_for_mode(command, trimmed, mode)
        if score <= 0:
            continue
        entry = usage.get(command.id, PaletteUsage(0, 0))
        scored.append((
            score,
            entry.count,
            entry.last_used_epoch,
            command.title.lower(),
            command,
        ))
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    return [item[4] for item in scored]


#: Intent aliases for palette search: extra words a user might type for a
#: command that appear in neither its title nor its id. Users search by what
#: they mean ("settings", "quit", "theme"), not by QUILL's vocabulary. Keyed by
#: command id; entries for ids that are not registered are simply unused.
COMMAND_ALIASES: dict[str, str] = {
    "file.new": "create blank fresh",
    "file.open": "load browse",
    "file.save": "write store keep",
    "file.save_as": "duplicate save copy",
    "file.restore_backup": "recover previous version undelete",
    "file.print": "printer paper",
    "file.open_url": "web address link internet",
    "app.preferences": "settings options configure",
    "app.exit": "quit leave shut down",
    "app.announcement_self_test": "speech test braille test output check",
    "app.report_editor_surface": "braille diagnostic surface class emulation",
    "edit.undo": "revert back mistake",
    "edit.redo": "again restore change",
    "edit.replace_all": "search substitute swap",
    "edit.copy_to_next_slot": "clipboard tray multi copy",
    "view.toggle_dark_mode": "theme light night appearance",
    "view.toggle_soft_wrap": "word wrap line wrap",
    "view.send_to_tray": "minimize background hide",
    "verbosity.where_am_i": "position location context orient",
    "tools.copy_diagnostic_summary": "debug info support report",
}


def _searchable_text(command: Command) -> str:
    binding = command.keybinding or ""
    aliases = COMMAND_ALIASES.get(command.id, "")
    return f"{command.title} {command.id} {binding} {aliases}".lower()


def _multi_term_score(command: Command, query: str) -> int:
    """Order-independent AND match: every whitespace-separated term must appear
    somewhere in title + id + shortcut + aliases ("add url" finds "URL Add")."""
    text = _searchable_text(command)
    terms = query.split()
    if all(term in text for term in terms):
        return 700
    return 0


def _match_score(command: Command, query: str) -> int:
    if not query:
        return 1
    if " " in query.strip():
        return _multi_term_score(command, query.strip())
    title = command.title.lower()
    command_id = command.id.lower()
    if query == title or query == command_id:
        return 1000
    if title.startswith(query):
        return 900
    if command_id.startswith(query):
        return 850
    if query in title:
        return 700
    if query in command_id:
        return 650
    aliases = COMMAND_ALIASES.get(command.id, "")
    if aliases and query in aliases:
        return 620
    binding = (command.keybinding or "").lower()
    if binding and query in binding:
        return 610
    title_subsequence = _subsequence_score(title, query)
    id_subsequence = _subsequence_score(command_id, query)
    return max(title_subsequence, id_subsequence)


def _score_for_mode(command: Command, query: str, mode: str) -> int:
    if mode == "id":
        return _match_text(command.id.lower(), query)
    if mode == "bound":
        if command.keybinding is None:
            return 0
        return _match_score(command, query)
    if mode == "recent":
        if not query:
            return 1
        return _match_score(command, query)
    return _match_score(command, query)


def _match_text(text: str, query: str) -> int:
    if not query:
        return 1
    if text == query:
        return 1000
    if text.startswith(query):
        return 850
    if query in text:
        return 650
    return _subsequence_score(text, query)


def _parse_mode(query: str) -> tuple[str, str]:
    trimmed = query.strip()
    if not trimmed:
        return "default", ""
    marker = trimmed[0]
    value = trimmed[1:].strip().lower()
    if marker == ">":
        return "default", value
    if marker == ":":
        return "id", value
    if marker == "?":
        return "bound", value
    if marker == "~":
        return "recent", value
    return "default", trimmed.lower()


def top_suggestion(
    usage: dict[str, PaletteUsage],
    commands: Iterable[Command],
    *,
    min_count: int = 3,
    recency_window_seconds: int = 3600,
) -> Command | None:
    """§8.2 Annisuggestion: return the command to suggest in the action bar.

    Returns the most frequently used command that has been invoked at least
    *min_count* times within the last *recency_window_seconds* seconds, or
    ``None`` if no command meets the threshold.  The UI surfaces this as a
    single-key status-bar nudge ("F6: insert table") so the user discovers
    their most-used action without hunting through menus.
    """
    from datetime import UTC, datetime

    now_epoch = int(datetime.now(UTC).timestamp())
    cutoff = now_epoch - recency_window_seconds
    command_map = {cmd.id: cmd for cmd in commands}
    best_count = 0
    best_cmd: Command | None = None
    for command_id, entry in usage.items():
        if entry.count < min_count:
            continue
        if entry.last_used_epoch < cutoff:
            continue
        if command_id not in command_map:
            continue
        if entry.count > best_count:
            best_count = entry.count
            best_cmd = command_map[command_id]
    return best_cmd


def _subsequence_score(text: str, query: str) -> int:
    position = -1
    spread = 0
    for token in query:
        next_position = text.find(token, position + 1)
        if next_position < 0:
            return 0
        if position >= 0:
            spread += next_position - position
        position = next_position
    return max(300 - spread, 1)
