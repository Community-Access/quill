"""Ask a model where a podcast library's shows belong, and refuse to trust it.

QUILL Cast can have two hundred subscriptions and four folders, because tidying
them is a job nobody does. A model is genuinely good at this one thing: given a
list of show titles and descriptions, it will group them the way a person would.

So the feature exists, and this module is the half that does not talk to a
model. It builds the question, reads the answer, and -- the part that matters --
**turns the answer into proposals that cannot do anything on their own.**

Three rules, and they are the whole design:

1. **Nothing moves here.** Every function returns a :class:`Proposal` list.
   Applying them is a separate, explicit act in the UI, after the listener has
   read them. A model that decides to file somebody's entire library under
   "Misc" has, at worst, wasted a screen of their time.

2. **A proposal that does not resolve is dropped, never guessed.** The model
   answers in text, so it can name a show that does not exist, a folder that
   does not exist, or the same show twice. Every field is matched back against
   the real library by id, and anything that does not match is discarded with a
   reason. The listener is told how many were discarded, because silence about
   dropped rows is how a feature starts lying about what it did.

3. **A new folder is its own kind of proposal.** "Create Interviews and put
   these four in it" is two different consents -- making a folder, and moving
   shows -- so it is two kinds of row, and the moves into a folder that was
   never created are dropped with the folder.

The model never sees a feed address, a file path or a listening position: only
titles, descriptions and the folder names that already exist. What it cannot see
it cannot leak.

wx-free, strict-typed, pure. No network: :mod:`quill.ui.podcasts.cast_ai` hands
the prompt to the shared AI service and the answer back to :func:`read_answer`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

__all__ = [
    "Library",
    "Proposal",
    "ReadResult",
    "apply_plan",
    "build_prompt",
    "describe_plan",
    "read_answer",
]

#: How many shows go in one request. A library of two hundred would make a
#: prompt no model answers well and no listener wants to review in one sitting,
#: so the UI asks in batches and this is the batch.
BATCH = 40

#: The longest description sent per show. A feed description can be a thousand
#: words of boilerplate; the first two sentences are what identifies a show, and
#: the rest is what makes the request expensive.
DESCRIPTION_CHARS = 240


@dataclass(frozen=True, slots=True)
class Show:
    """The only three things about a show this feature is allowed to send."""

    id: str
    title: str
    description: str = ""
    folder_name: str = ""


@dataclass(frozen=True, slots=True)
class Folder:
    """A folder that already exists, by id and by the name a listener reads."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Library:
    """What :func:`build_prompt` is given: shows, and the folders there are."""

    shows: tuple[Show, ...] = ()
    folders: tuple[Folder, ...] = ()


@dataclass(frozen=True, slots=True)
class Proposal:
    """One thing the listener can accept or skip, on its own.

    *kind* is ``"move"`` or ``"create"``. A ``create`` carries the folder name in
    *folder_name* and no *show_id*; a ``move`` carries both, and *folder_id* when
    the destination already exists.
    """

    kind: str
    reason: str = ""
    show_id: str = ""
    show_title: str = ""
    from_folder: str = ""
    folder_id: str = ""
    folder_name: str = ""

    def spoken(self) -> str:
        """The row as a listener hears it, and as the review list shows it.

        The action first. A list of forty of these is read top to bottom, and
        "Move" or "Create folder" is the word that decides whether the rest of
        the row is worth listening to.
        """
        if self.kind == "create":
            return f"Create folder: {self.folder_name}"
        where = self.from_folder or "no folder"
        return f"Move: {self.show_title} — from {where} to {self.folder_name}"


@dataclass(slots=True)
class ReadResult:
    """Proposals that survived, and an honest account of what did not."""

    proposals: list[Proposal] = field(default_factory=list)
    discarded: list[str] = field(default_factory=list)

    @property
    def moves(self) -> list[Proposal]:
        return [p for p in self.proposals if p.kind == "move"]

    @property
    def creates(self) -> list[Proposal]:
        return [p for p in self.proposals if p.kind == "create"]


def build_prompt(library: Library) -> str:
    """The question, as one string.

    Asks for JSON because the answer has to be matched back against real ids,
    and a prose answer would have to be guessed at. :func:`read_answer` copes
    with prose anyway -- a model that ignores the format should degrade to fewer
    proposals, not to none.
    """
    folders = ", ".join(f.name for f in library.folders) or "(none yet)"
    lines = [
        "You are helping tidy a podcast library. Group the shows below into folders by subject.",
        "",
        f"Folders that already exist: {folders}",
        "",
        "Shows:",
    ]
    for show in library.shows:
        where = f" [currently in {show.folder_name}]" if show.folder_name else ""
        description = show.description[:DESCRIPTION_CHARS].strip()
        lines.append(
            f"- id={show.id} | {show.title}{where}" + (f" | {description}" if description else "")
        )
    lines += [
        "",
        "Rules:",
        "- Prefer a folder that already exists. Only propose a new one when "
        "three or more shows would go in it.",
        "- Leave a show alone if it is already in a folder that fits. Do not "
        "propose a move that changes nothing.",
        "- Never invent a show id. Use only the ids listed above.",
        "- Give each suggestion a reason of at most twelve words.",
        "",
        "Answer with JSON only, in this shape:",
        '{"create": [{"name": "Interviews", "reason": "..."}],',
        ' "move": [{"id": "abc", "folder": "Interviews", "reason": "..."}]}',
    ]
    return "\n".join(lines)


def _json_block(text: str) -> dict[str, object] | None:
    """The first JSON object in *text*, or ``None``.

    Models wrap JSON in prose and in code fences however they were asked not to,
    so the object is found rather than assumed to be the whole answer.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start : end + 1] if 0 <= start < end else None
    if not candidate:
        return None
    try:
        loaded = json.loads(candidate)
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _clean(value: object, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit]


def read_answer(answer: str, library: Library) -> ReadResult:
    """Proposals from *answer*, every one of them resolved against *library*.

    Anything that does not resolve is discarded with a sentence saying why, and
    the sentence is shown to the listener. A feature that quietly drops half a
    model's answer is a feature whose output nobody can reason about.
    """
    result = ReadResult()
    block = _json_block(answer)
    if block is None:
        result.discarded.append(
            "The answer was not in the format asked for, so nothing was read from it."
        )
        return result

    shows = {show.id: show for show in library.shows}
    existing = {folder.name.casefold(): folder for folder in library.folders}

    # Folders first: a move into a folder nobody agreed to create is not a move.
    proposed_names: dict[str, str] = {}
    raw_creates = block.get("create")
    for entry in raw_creates if isinstance(raw_creates, list) else []:
        if not isinstance(entry, dict):
            continue
        name = _clean(entry.get("name"), 60)
        if not name:
            continue
        if name.casefold() in existing:
            result.discarded.append(f"“{name}” already exists, so it was not proposed again.")
            continue
        if name.casefold() in proposed_names:
            continue
        proposed_names[name.casefold()] = name
        result.proposals.append(
            Proposal(kind="create", folder_name=name, reason=_clean(entry.get("reason")))
        )

    seen: set[str] = set()
    raw_moves = block.get("move")
    for entry in raw_moves if isinstance(raw_moves, list) else []:
        if not isinstance(entry, dict):
            continue
        show_id = _clean(entry.get("id"), 80)
        target = _clean(entry.get("folder"), 60)
        show = shows.get(show_id)
        if show is None:
            result.discarded.append(f"No show in your library has the id “{show_id}”.")
            continue
        if show_id in seen:
            result.discarded.append(
                f"{show.title} was suggested more than once; the first was kept."
            )
            continue
        if not target:
            continue
        folder = existing.get(target.casefold())
        if folder is None and target.casefold() not in proposed_names:
            result.discarded.append(
                f"{show.title} was to go in “{target}”, which does not exist and was not proposed."
            )
            continue
        if folder is not None and show.folder_name.casefold() == folder.name.casefold():
            result.discarded.append(f"{show.title} is already in “{folder.name}”.")
            continue
        seen.add(show_id)
        result.proposals.append(
            Proposal(
                kind="move",
                show_id=show_id,
                show_title=show.title,
                from_folder=show.folder_name,
                folder_id=folder.id if folder is not None else "",
                folder_name=folder.name
                if folder is not None
                else proposed_names[target.casefold()],
                reason=_clean(entry.get("reason")),
            )
        )
    return result


def describe_plan(result: ReadResult) -> str:
    """One sentence for the status field and for the announcement.

    Counts, because a count is the one thing a listener cannot get by arrowing
    through a list, and because the number discarded is part of the truth.
    """
    if not result.proposals:
        if result.discarded:
            return f"No usable suggestions. {len(result.discarded)} were discarded."
        return "No changes suggested. Your library already reads as organised."
    moves, creates = len(result.moves), len(result.creates)
    parts = []
    if creates:
        parts.append(f"{creates} new folder{'s' if creates != 1 else ''}")
    if moves:
        parts.append(f"{moves} move{'s' if moves != 1 else ''}")
    sentence = f"Suggested: {' and '.join(parts)}. Nothing has changed yet."
    if result.discarded:
        sentence += f" {len(result.discarded)} suggestion(s) were discarded as unusable."
    return sentence


def apply_plan(accepted: list[Proposal]) -> tuple[list[str], list[Proposal]]:
    """Split *accepted* into folder names to create, then the moves, in order.

    Creates come first and moves second, because a move into a folder that has
    not been made yet cannot be carried out. Returning the two rather than doing
    them keeps this module free of the library it is planning against -- the
    caller owns every write, which is what makes "nothing moves here" true
    rather than merely intended.
    """
    creates = [p.folder_name for p in accepted if p.kind == "create"]
    moves = [p for p in accepted if p.kind == "move"]
    return creates, moves
