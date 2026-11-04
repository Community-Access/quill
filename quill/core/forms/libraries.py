"""Choice libraries: the ready-made lists BAF ships (countries, states, months...).

A field points at one by name (``choice_library``; ``@library countries`` or
``select "Country" countries`` in BFL), and the list is filled in when the
form is shown, so a form stays short and the lists stay current.

The data (``libraries/baf_libraries.json``) was taken from BAF's
``includes/class-baf-choice-libraries.php`` by running its own registration
code, so names, values and labels are BAF's exactly: 124 libraries, three of
them cascading (countries to states, continents to countries, time-zone
regions to time zones). Three are worked out from the year instead of stored:
``years``, ``years_future`` and ``birth_years``.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from quill.core.forms.errors import ChoiceLibraryError


class Choice(dict[str, str]):
    """A choice as the model holds one (``{"value", "label"}``), readable as attributes too."""

    @property
    def value(self) -> str:
        return self["value"]

    @property
    def label(self) -> str:
        return self["label"]


def _choice(value: Any, label: Any) -> Choice:
    return Choice(value=str(value), label=str(label))


DATA_PATH = Path(__file__).parent / "libraries" / "baf_libraries.json"


@dataclass(frozen=True)
class LibraryInfo:
    id: str
    label: str
    count: int  # 0 for a cascading list until its parent is chosen
    cascade_parent: str | None = None


@lru_cache(maxsize=1)
def _data() -> dict[str, Any]:
    try:
        data: dict[str, Any] = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ChoiceLibraryError(f"The choice libraries could not be read: {exc}") from exc
    return dict(data["libraries"])


def library_ids() -> list[str]:
    return sorted(_data())


def exists(library_id: str) -> bool:
    return library_id in _data()


def info(library_id: str) -> LibraryInfo:
    entry = _entry(library_id)
    cascade = entry.get("cascade")
    count = _year_span(entry) if "years" in entry else len(entry.get("choices", []))
    return LibraryInfo(
        library_id, str(entry["label"]), count, cascade["parent"] if cascade else None
    )


def all_info() -> list[LibraryInfo]:
    return [info(i) for i in library_ids()]


def _entry(library_id: str) -> dict[str, Any]:
    entry = _data().get(library_id)
    if entry is None:
        raise ChoiceLibraryError(f"There is no choice library called {library_id!r}.")
    return dict(entry)


def _year_span(entry: dict[str, Any]) -> int:
    span = entry["years"]
    return abs(int(span["to"]) - int(span["from"])) + 1


def choices(
    library_id: str, parent_value: str | None = None, *, today: dt.date | None = None
) -> list[Choice]:
    """A library's choices; for a cascading one, those for ``parent_value``.

    A cascading library with no parent value is empty, as on the site: State
    has nothing to offer until Country is chosen.
    """
    entry = _entry(library_id)
    if "years" in entry:
        year = (today or dt.date.today()).year
        start, stop = year + int(entry["years"]["from"]), year + int(entry["years"]["to"])
        step = 1 if stop >= start else -1
        return [_choice(y, y) for y in range(start, stop + step, step)]
    cascade = entry.get("cascade")
    if cascade:
        if parent_value is None:
            return []
        rows = cascade["map"].get(parent_value) or cascade["map"].get(parent_value.upper(), [])
        return [_choice(r[0], r[1]) for r in rows]
    return [_choice(row[0], row[1]) for row in entry.get("choices", [])]


def search(query: str) -> list[LibraryInfo]:
    """Libraries whose name or label contains every word of ``query``."""
    words = query.lower().split()
    return [i for i in all_info() if all(w in (i.id + " " + i.label).lower() for w in words)]


def choices_for(
    item: dict[str, Any], model: dict[str, Any] | None = None, parent_value: str | None = None
) -> list[tuple[str, str]]:
    """``(value, label)`` for every answer a field offers.

    Its own choices first; else a library the form defines (``choice_libraries``);
    else one of BAF's built-in libraries (a cascade's, given the parent's
    answer); else the fixed scales of ``rating`` (1 to 5) and ``nps`` (0 to 10).
    A library that does not exist offers nothing: that is Check This Form's finding.
    """
    if item.get("choices"):
        return [(str(c["value"]), str(c.get("label", c["value"]))) for c in item["choices"]]
    name = item.get("choice_library") or (item.get("cascade") or {}).get("library")
    if name:
        own = ((model or {}).get("choice_libraries") or {}).get(name)
        if own is not None:
            return [(str(c["value"]), str(c.get("label", c["value"]))) for c in own]
        try:
            return [(c["value"], c["label"]) for c in choices(str(name), parent_value)]
        except ChoiceLibraryError:
            return []
    if item.get("type") == "rating":
        return [(str(n), f"{n} out of 5") for n in range(1, 6)]
    if item.get("type") == "nps":
        return [(str(n), str(n)) for n in range(11)]
    return []
