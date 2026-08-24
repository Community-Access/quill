"""Adding something you already have: say so, and go to the one you have.

The failure this exists for is quiet and expensive. You find a station in
Browse, press Add to Favorites, and hear "Added WQXR to Favorites" -- and
nothing was added, because WQXR was already there. The store's ``add`` had
returned without doing anything and the sentence was written before anybody
asked it whether it had (list.md 11.6).

Two rules, both of which this module exists to make cheap:

* **Say it.** "You already follow The Daily" is a different fact from "Added
  The Daily", and a listener who cannot see the list has no other way to tell
  them apart.
* **Go there.** The reason somebody adds a thing twice is that they could not
  find the first one. Moving focus to the existing row answers the question
  they were actually asking, and turns a refusal into an arrival.

Pure and wx-free: the sentences live here so Quill Radio and QUILL Cast say
the same thing, and the moving is each surface's own business.
"""

from __future__ import annotations

__all__ = ["ALREADY_VERBS", "added", "already_have"]

#: kind -> how "you already have one" reads for that kind. A podcast is
#: *followed*, a station is *in your favorites*, a place is *saved*: the verb
#: is the part that tells you which list to go and look in.
ALREADY_VERBS: dict[str, str] = {
    "podcast": "You already follow {name}",
    "station": "{name} is already in your favorites",
    "place": "{name} is already saved in your places",
    "folder": "There is already a folder called {name}",
    "playlist": "There is already a playlist called {name}",
}

_GENERIC = "You already have {name}"


def already_have(kind: str, name: str, *, moved: bool = False) -> str:
    """What to say when the thing being added is already here.

    *moved* is whether focus landed on the existing row: say so when it did,
    because "you already follow this" without going there leaves the listener
    exactly where they started, which is what made them add it twice.
    """
    template = ALREADY_VERBS.get(kind, _GENERIC)
    lead = template.format(name=name.strip() or "that")
    tail = " Moving to it." if moved else " Nothing was added."
    return f"{lead}.{tail}"


def added(kind: str, name: str) -> str:
    """The other half, so the pair reads as one voice."""
    subject = name.strip() or "it"
    if kind == "podcast":
        return f"Now following {subject}."
    if kind == "place":
        return f"Saved {subject} to your places."
    return f"Added {subject} to your favorites."
