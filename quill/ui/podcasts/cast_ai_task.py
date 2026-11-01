"""Find and Follow: QUILL Cast's agent task (codex.md 6.5, Phase 4c).

The person says what they want ("find two good podcasts about birds, follow
them and put them in a Nature folder"), and an agent engine -- My GitHub
Copilot or Codex -- works through it with Cast's own tools in the shared agent
window (:mod:`quill.ui.agent_window`). Each tool wraps what Cast already does:

* ``podcasts.find_shows`` -- the podcast directories Add Podcast searches
  (``directory_search``), as numbered text rows with an id (``P1``).
* ``podcasts.list_followed`` and ``podcasts.recent_episodes`` -- reads, with
  ids (``F1``, ``E1``) the other tools take; they run without a question.
* ``podcasts.follow_show`` -- reads the feed the way Add Podcast does, shows
  what will be followed as text, and follows it only on Apply.
* ``podcasts.new_folder`` and ``podcasts.move_to_folder`` -- Cast's own folder
  code (``PodcastLibrary.add_folder``, ``folder_membership.move_to``), each shown
  as text first.
* ``podcasts.queue_episode`` -- adds an episode to the Play Queue, so it asks.

Nothing here unfollows, deletes or downloads: those stay the listener's own
verbs (ear.md A10). Handlers run on a worker thread, and every touch of Cast's
library goes through ``ctx.on_ui``. Nothing here announces: the agent window
says each step and the closing summary, once (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "APP",
    "FIND_AND_FOLLOW",
    "INSTRUCTION_HELP",
    "cast_task_facts",
    "cast_task_tools",
]

#: Cast's command prefix, and so its tools' namespace.
APP = "podcasts"

_FIND_LIMIT = 15
_EPISODE_LIMIT = 10
_TOP = ("", "top level", "the top level", "top", "none")
_NOT_APPLIED = "The person did not apply it."

FIND_AND_FOLLOW = AppTaskSpec(
    app=APP,
    agent_id="cast-find-and-follow",
    title="Find and Follow",
    instructions=(
        "You help someone who uses a screen reader with QUILL Cast, a podcast "
        "player. Find podcasts with podcasts_find_shows, see what they already "
        "follow with podcasts_list_followed, and use the ids those lists give "
        "(P1 for a search result, F1 for a podcast they follow, E1 for an "
        "episode). Following, making a folder, moving a podcast and queueing an "
        "episode each ask the person, and they may say no. Never suggest "
        "unfollowing or deleting anything."
    ),
    done_words={
        f"{APP}.follow_show": "Followed a podcast",
        f"{APP}.new_folder": "Made a folder",
        f"{APP}.move_to_folder": "Moved a podcast",
        f"{APP}.queue_episode": "Queued an episode",
    },
)

INSTRUCTION_HELP = (
    "Type what you want QUILL Cast to find, follow or organise, then press Enter. "
    "For example: find a podcast about birds, follow it and put it in a Nature "
    "folder. Each change asks you first and shows you what it will do. While a "
    "task runs, what you type here goes to it as a follow-up."
)


# --------------------------------------------------------------------------- #
# Words
# --------------------------------------------------------------------------- #


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _folder_name(library: Any, folder_id: str | None) -> str:
    folder = library.find_folder(folder_id) if folder_id else None
    return str(folder.name) if folder is not None else "the top level"


def _minutes(seconds: int) -> str:
    minutes = round(seconds / 60)
    return _plural(minutes, "minute") if minutes else ""


def episode_row(key: str, episode: Any) -> str:
    """One episode as a line: id, title, date, length and whether it was heard."""
    bits = [f"{key}. {episode.title}"]
    published = str(getattr(episode, "published", "") or "")[:10]
    if published:
        bits.append(published)
    length = _minutes(int(getattr(episode, "duration_seconds", 0) or 0))
    if length:
        bits.append(length)
    bits.append("played" if getattr(episode, "played", False) else "not played")
    if getattr(episode, "downloaded_path", ""):
        bits.append("downloaded")
    return ". ".join(bits) + "."


def cast_task_facts(host: Any) -> str:
    """What is on screen, as text, sent with the first instruction."""
    from quill.core.ai.app_ask_context import facts_text, filter_facts

    lines = [facts_text(filter_facts(host._cast_ask_facts("", "")))]
    selected = getattr(host, "_selected_show", None)
    try:
        show = selected() if callable(selected) else None
    except Exception:  # noqa: BLE001 - no tree, no selection
        show = None
    if show is not None:
        lines.append(f"Selected podcast: {show.title}")
    return "\n".join(line for line in lines if line.strip())


def _save(host: Any) -> None:
    """Save the library and redraw, the way Add Podcast and Organise do."""
    added = getattr(host, "_podcast_library_added_to", None)
    if callable(added):
        added()
    else:
        host._save_podcast_library()
    after = getattr(host, "_after_library_change", None)
    if callable(after):
        after()


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def cast_task_tools(
    host: Any,
    ctx: AppTaskHost,
    *,
    search: Callable[[str, bool], Any] | None = None,
    fetch: Callable[[str, bool], Any] | None = None,
) -> list[FamilyTool]:
    """Cast's tools for one task. *search* and *fetch* replace the network (tests)."""
    found: dict[str, Any] = {}
    episodes: dict[str, tuple[str, str]] = {}
    find = search or _directory_search
    read_feed = fetch or _fetch_feed
    library = host._podcast_library
    safe_mode = bool(getattr(host, "_safe_mode", False))

    def followed() -> list[Any]:
        return list(ctx.on_ui(lambda: list(library.shows), []) or [])

    def show_for(args: dict[str, Any], key: str = "show") -> Any:
        wanted = str(args.get(key, "") or "").strip()
        shows = followed()
        if wanted.upper().startswith("F") and wanted[1:].isdigit():
            index = int(wanted[1:]) - 1
            if 0 <= index < len(shows):
                return shows[index]
        folded = wanted.casefold()
        for show in shows:
            if folded and str(show.title).casefold() == folded:
                return show
        raise ToolError(
            f"You do not follow a podcast called {wanted or 'that'}. Use "
            "podcasts_list_followed and pass its id, such as F1."
        )

    def folder_for(name: str) -> str | None:
        if name.strip().casefold() in _TOP:
            return None
        folded = name.strip().casefold()
        for folder in ctx.on_ui(lambda: list(library.folders), []) or []:
            if str(folder.name).casefold() == folded:
                return str(folder.id)
        raise ToolError(f"There is no folder called {name}. Make it with podcasts_new_folder.")

    def result_for(args: dict[str, Any]) -> Any:
        wanted = str(args.get("result", "") or "").strip().upper()
        if wanted in found:
            return found[wanted]
        raise ToolError("Use podcasts_find_shows first, and pass its id, such as P1.")

    def name_of(args: dict[str, Any], key: str, resolve: Callable[[dict[str, Any]], Any]) -> str:
        try:
            return str(resolve(args).title)
        except ToolError:
            return str(args.get(key, "") or "that podcast")

    # -- reads ---------------------------------------------------------------

    def find_shows(args: dict[str, Any]) -> str:
        query = " ".join(str(args.get("query", "") or "").split())
        if not query:
            raise ToolError("Say what to look for: a name, a subject, a host.")
        if safe_mode:
            raise ToolError("Finding podcasts is off in Safe Mode.")
        result = find(query, safe_mode)
        rows = list(getattr(result, "results", []) or [])[:_FIND_LIMIT]
        if not rows:
            return str(getattr(result, "summary", lambda: "")() or f"No podcasts matched {query}.")
        mine = {str(show.feed_url) for show in followed() if show.feed_url}
        lines = [f"{_plural(len(rows), 'podcast')} for {query}:"]
        for row in rows:
            key = f"P{len(found) + 1}"
            found[key] = row
            line = f"{key}. {row.title}"
            if row.artist:
                line += f", by {row.artist}"
            if row.feed_url in mine:
                line += ". You already follow it"
            lines.append(line + ".")
        problems = list(getattr(result, "problems", []) or [])
        if problems:
            lines.append(" ".join(problems))
        return "\n".join(lines)

    def list_followed(_args: dict[str, Any]) -> str:
        def read() -> tuple[list[str], list[str]]:
            rows = []
            for index, show in enumerate(library.shows, start=1):
                unplayed = sum(1 for e in show.episodes if not e.played)
                line = f"F{index}. {show.title}. In {_folder_name(library, show.folder_id)}"
                line += f". {_plural(unplayed, 'episode')} not played"
                if getattr(show, "is_local", False):
                    line += ". Your own files"
                rows.append(line + ".")
            return rows, [str(f.name) for f in library.folders]

        rows, folders = ctx.on_ui(read, ([], [])) or ([], [])
        if not rows:
            return "No podcasts are followed yet."
        lines = [f"{_plural(len(rows), 'podcast')} followed:", *rows]
        lines.append(f"Folders: {', '.join(folders)}." if folders else "There are no folders.")
        return "\n".join(lines)

    def recent_episodes(args: dict[str, Any]) -> str:
        from quill.core.podcasts.episode_filters import newest_episodes

        show = show_for(args)
        try:
            limit = max(1, min(30, int(args.get("count", _EPISODE_LIMIT) or _EPISODE_LIMIT)))
        except (TypeError, ValueError):
            limit = _EPISODE_LIMIT
        newest = ctx.on_ui(lambda: newest_episodes(list(show.episodes), limit), []) or []
        if not newest:
            return f"{show.title} has no episodes yet."
        lines = [f"The newest {_plural(len(newest), 'episode')} of {show.title}:"]
        for episode in newest:
            key = f"E{len(episodes) + 1}"
            for known, ids in episodes.items():
                if ids == (show.id, episode.guid):
                    key = known
                    break
            episodes[key] = (show.id, episode.guid)
            lines.append(episode_row(key, episode))
        return "\n".join(lines)

    # -- what changes --------------------------------------------------------

    def follow_show(args: dict[str, Any]) -> str:
        row = result_for(args)
        if ctx.on_ui(lambda: library.find_show_by_feed_url(row.feed_url), None) is not None:
            raise ToolError(f"You already follow {row.title}.")
        try:
            info = read_feed(row.feed_url, safe_mode)
        except Exception as error:  # noqa: BLE001 - the model reads why
            raise ToolError(f"Could not read {row.title}'s feed: {error}") from error
        newest = sorted(info.episodes, key=lambda e: (e.published, e.title), reverse=True)[:3]
        text = "\n".join([
            f"Follow: {info.title or row.title}",
            *([f"By: {row.artist}"] if row.artist else []),
            f"Episodes in the feed: {len(info.episodes)}",
            *(f"- {e.title}" for e in newest),
            "It goes at the top level of your library, with your usual settings.",
        ])
        if not ctx.preview(f"Follow {row.title}", text):
            raise ToolError(_NOT_APPLIED)

        def add() -> str:
            from quill.core.podcasts.models import PodcastShow
            from quill.core.podcasts.subscriptions import new_id
            from quill.ui.podcasts.subscription_backfill import _apply_backfill

            show = PodcastShow(
                id=new_id(),
                title=info.title or row.title,
                feed_url=row.feed_url,
                homepage=info.homepage,
                artwork_url=info.artwork_url,
                tags=info.tags,
                episodes=info.episodes,
            )
            if not library.add_show(show):
                return f"You already follow {show.title}."
            _apply_backfill(library, show)
            _save(host)
            return ""

        problem = ctx.on_ui(add, "The task was stopped.")
        if problem:
            raise ToolError(problem)
        return f"Now following {info.title or row.title}, {_plural(len(info.episodes), 'episode')}."

    def new_folder(args: dict[str, Any]) -> str:
        name = " ".join(str(args.get("name", "") or "").split())
        if not name or name.casefold() in _TOP:
            raise ToolError("Give the new folder a name.")
        parent_name = str(args.get("inside", "") or "")
        parent = folder_for(parent_name)
        names = [str(f.name).casefold() for f in ctx.on_ui(lambda: list(library.folders), [])]
        if name.casefold() in names:
            raise ToolError(f"There is already a folder called {name}.")
        where = _folder_name(library, parent)
        if not ctx.preview(f"New folder {name}", f"Make a folder: {name}\nInside: {where}"):
            raise ToolError(_NOT_APPLIED)

        def add() -> None:
            library.add_folder(name, parent_folder_id=parent)
            _save(host)

        ctx.on_ui(add, None)
        return f"Made the folder {name}, in {where}."

    def move_to_folder(args: dict[str, Any]) -> str:
        from quill.core.podcasts import folder_membership

        show = show_for(args)
        target = folder_for(str(args.get("folder", "") or ""))
        source = show.folder_id
        if source == target:
            raise ToolError(f"{show.title} is already in {_folder_name(library, target)}.")
        text = (
            f"Move: {show.title}\nFrom: {_folder_name(library, source)}\n"
            f"To: {_folder_name(library, target)}"
        )
        if not ctx.preview(f"Move {show.title}", text):
            raise ToolError(_NOT_APPLIED)

        def move() -> str:
            try:
                changed = folder_membership.move_to(library, show, target, source=source)
            except ValueError as error:
                return str(error)
            if not changed:
                return "The podcast is already in that folder."
            _save(host)
            return ""

        problem = ctx.on_ui(move, "The task was stopped.")
        if problem:
            raise ToolError(problem)
        return f"Moved {show.title} to {_folder_name(library, target)}."

    def episode_for(args: dict[str, Any]) -> tuple[Any, Any]:
        wanted = str(args.get("episode", "") or "").strip().upper()
        ids = episodes.get(wanted)
        show = ctx.on_ui(lambda: library.find_show(ids[0]), None) if ids else None
        episode = show.find_episode(ids[1]) if show is not None and ids else None
        if episode is None:
            raise ToolError("Use podcasts_recent_episodes first, and pass its id, such as E1.")
        return show, episode

    def queue_episode(args: dict[str, Any]) -> str:
        from quill.core.podcasts import queue as queue_ops

        show, episode = episode_for(args)

        def add() -> bool:
            added = queue_ops.add_to_queue(
                library, show.id, episode.guid, reason="an AI task you asked for"
            )
            if added:
                _save(host)
            return bool(added)

        if not ctx.on_ui(add, False):
            raise ToolError(f"{episode.title} is already in the Play Queue.")
        return f"Added {episode.title} to the Play Queue."

    def queue_summary(args: dict[str, Any]) -> str:
        try:
            show, episode = episode_for(args)
        except ToolError:
            return "Add an episode to the Play Queue."
        return f"Add {episode.title} from {show.title} to the Play Queue."

    show_arg = {"type": "string", "description": "The podcast's id from the followed list (F1)."}
    write = {
        "category": PermissionCategory.MODIFY_DOCUMENT,
        "risk": RiskLevel.MEDIUM,
        "app": APP,
        "mutating": True,
    }
    return [
        FamilyTool(
            name=f"{APP}.find_shows",
            description=(
                "Find shows in the podcast directories by name or subject. Returns "
                "numbered rows with an id such as P1, and says which you already follow."
            ),
            handler=find_shows,
            parameters=_schema(
                {"query": {"type": "string", "description": "What to look for."}}, ("query",)
            ),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_followed",
            description=(
                "List the podcasts the person follows, with an id such as F1, the "
                "folder each is in and how many episodes are not played; then the folders."
            ),
            handler=list_followed,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.recent_episodes",
            description="List a followed podcast's newest episodes, with an id such as E1.",
            handler=recent_episodes,
            parameters=_schema(
                {
                    "show": show_arg,
                    "count": {"type": "integer", "description": "How many (1 to 30)."},
                },
                ("show",),
            ),
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.follow_show",
            description=(
                "Follow one podcast from what Find returned. Asks the person, then "
                "shows what will be followed before it is."
            ),
            handler=follow_show,
            parameters=_schema(
                {"result": {"type": "string", "description": "The id Find gave it (P1)."}},
                ("result",),
            ),
            summarize=lambda a: f"Follow the podcast {name_of(a, 'result', result_for)}.",
            **write,  # type: ignore[arg-type]
        ),
        FamilyTool(
            name=f"{APP}.new_folder",
            description=(
                "Make a new folder in the library, at the top level or inside another "
                "folder. Asks the person and shows it first."
            ),
            handler=new_folder,
            parameters=_schema(
                {
                    "name": {"type": "string", "description": "The new folder's name."},
                    "inside": {
                        "type": "string",
                        "description": "The folder to put it in (optional; top level if empty).",
                    },
                },
                ("name",),
            ),
            summarize=lambda a: f"Make a folder called {str(a.get('name', '')).strip()}.",
            **write,  # type: ignore[arg-type]
        ),
        FamilyTool(
            name=f"{APP}.move_to_folder",
            description=(
                "Move a followed podcast into a folder, or to the top level. Asks the "
                "person and shows the move first."
            ),
            handler=move_to_folder,
            parameters=_schema(
                {
                    "show": show_arg,
                    "folder": {
                        "type": "string",
                        "description": "The folder's name, or 'top level'.",
                    },
                },
                ("show", "folder"),
            ),
            summarize=lambda a: (
                f"Move {name_of(a, 'show', show_for)} to "
                f"{_target_words(str(a.get('folder', '') or ''))}."
            ),
            **write,  # type: ignore[arg-type]
        ),
        FamilyTool(
            name=f"{APP}.queue_episode",
            description="Add one episode to the end of the Play Queue. Asks the person first.",
            handler=queue_episode,
            parameters=_schema(
                {"episode": {"type": "string", "description": "The episode's id (E1)."}},
                ("episode",),
            ),
            category=PermissionCategory.MODIFY_SELECTION,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=queue_summary,
        ),
    ]


def _target_words(name: str) -> str:
    return "the top level" if name.strip().casefold() in _TOP else f"the folder {name.strip()}"


def _directory_search(query: str, safe_mode: bool) -> Any:
    """The directories Add Podcast searches, with the same credentials."""
    from quill.core.podcasts import directory_search
    from quill.ui.podcasts.preview_command import podcast_index_credentials

    key, secret = podcast_index_credentials()
    return directory_search.search(
        query, source="both", key=key, secret=secret, safe_mode=safe_mode
    )


def _fetch_feed(feed_url: str, safe_mode: bool) -> Any:
    """Read one feed the way Add Podcast does before it follows."""
    from quill.core.podcasts import feed_reader

    return feed_reader.fetch_and_parse_feed(feed_url, safe_mode=safe_mode)
