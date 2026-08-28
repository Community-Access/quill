"""Where you got to in each tutorial, kept on this computer.

A small, deliberately dull file. It records two facts per lesson -- the step
you were standing on, and whether you have ever finished it -- and nothing
else. There is no score, no streak, no completion percentage across the set,
because none of those are things a person came to a radio app to collect.

Two decisions worth stating:

* **Finishing is remembered separately from position.** Re-opening a lesson you
  have already done starts you back at step one without clearing the fact that
  you did it, so "finished" keeps meaning "I have been through this".
* **An unknown slug is kept, not dropped.** A lesson renamed in a later version
  should not silently erase somebody's place in a lesson this build has never
  heard of, and the file is small enough that carrying strangers costs
  nothing.

wx-free, strict-typed, written through ``write_json_atomic`` like every other
JSON store in the app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.tutorials.model import Progress

_FILE_NAME = "radio_tutorials.json"
_FORMAT = "quill-radio-tutorial-progress"


@dataclass(slots=True)
class TutorialProgressStore:
    """Every lesson somebody has started, keyed by slug."""

    entries: dict[str, Progress] = field(default_factory=dict)
    #: The lesson to offer when the window opens with nothing selected: the
    #: last one that was open, finished or not.
    last_opened: str = ""
    #: Whether the lesson window watches the app and moves you on by itself.
    #: A preference rather than a per-lesson setting, because it is a statement
    #: about how somebody wants to be taught rather than about one lesson.
    guide_me: bool = True

    def get(self, slug: str) -> Progress | None:
        return self.entries.get(slug)

    def step_of(self, slug: str) -> int:
        entry = self.entries.get(slug)
        return entry.step if entry is not None else 0

    def is_done(self, slug: str) -> bool:
        entry = self.entries.get(slug)
        return entry.done if entry is not None else False

    def record_step(self, slug: str, step: int) -> None:
        """Remember that *slug* is open at *step*."""
        entry = self.entries.get(slug)
        done = entry.done if entry is not None else False
        self.entries[slug] = Progress(slug=slug, step=max(0, step), done=done)
        self.last_opened = slug

    def record_finished(self, slug: str) -> None:
        """Remember that *slug* was worked all the way through."""
        entry = self.entries.get(slug)
        step = entry.step if entry is not None else 0
        self.entries[slug] = Progress(slug=slug, step=step, done=True)
        self.last_opened = slug

    def forget(self, slug: str) -> bool:
        """Drop one lesson's record. True when there was one to drop."""
        return self.entries.pop(slug, None) is not None

    def forget_all(self) -> int:
        """Drop every record; returns how many there were."""
        count = len(self.entries)
        self.entries.clear()
        self.last_opened = ""
        return count

    def finished_count(self) -> int:
        return sum(1 for entry in self.entries.values() if entry.done)

    def started_count(self) -> int:
        return sum(1 for entry in self.entries.values() if not entry.done and entry.step > 0)


def store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_progress(data_dir: Path) -> TutorialProgressStore:
    """Read the store. An absent or broken file reads as an empty one."""
    try:
        raw = json.loads(store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return TutorialProgressStore()
    if not isinstance(raw, dict):
        return TutorialProgressStore()
    store = TutorialProgressStore()
    last = raw.get("last_opened")
    if isinstance(last, str):
        store.last_opened = last
    guide = raw.get("guide_me")
    if isinstance(guide, bool):
        store.guide_me = guide
    entries = raw.get("lessons")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        step_raw = entry.get("step", 0)
        step = step_raw if isinstance(step_raw, int) and not isinstance(step_raw, bool) else 0
        store.entries[slug] = Progress(
            slug=slug,
            step=max(0, step),
            done=bool(entry.get("done", False)),
        )
    return store


def save_progress(data_dir: Path, store: TutorialProgressStore) -> None:
    """Persist the store atomically."""
    from quill.core.storage import write_json_atomic

    payload = {
        "format": _FORMAT,
        "last_opened": store.last_opened,
        "guide_me": store.guide_me,
        "lessons": [
            {"slug": entry.slug, "step": entry.step, "done": entry.done}
            for entry in store.entries.values()
        ],
    }
    write_json_atomic(store_path(data_dir), payload)


def summary(store: TutorialProgressStore, total: int) -> str:
    """One sentence for the contents window's status line.

    Deliberately not a percentage. "Nine of thirty-six" is a fact; "25%
    complete" is a scoreboard, and nobody opened a radio app to be scored.
    """
    finished = store.finished_count()
    started = store.started_count()
    if not finished and not started:
        return f"{total} tutorials. None started yet."
    parts = [f"{finished} of {total} finished"]
    if started:
        parts.append(f"{started} in progress")
    return ", ".join(parts) + "."
