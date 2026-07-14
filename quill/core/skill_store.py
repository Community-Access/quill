"""Persistent skill store — installed ``.sqp`` multi-step AI workflows.

Skills used to be import-and-run only: the Skill Library dialog parsed a ``.sqp``
file and ran it, but nothing was saved, so there was no "my skills" to manage.
This module gives skills the same persistent, manageable shape that
:class:`~quill.core.prompt_library.PromptLibrary` gives prompts, so the unified
AI Library can offer Run / Import / Enable / Remove / Export on a real library.

A :class:`SkillStore` keeps each installed skill as its **original ``.sqp``
source** (markdown-with-front-matter) in an installed-skills directory, plus a
small JSON index for enabled-state. Source is preserved verbatim (never
re-serialized from the parsed model) so round-tripping a skill never loses
formatting or fields the parser doesn't model. Each skill's id is a stable slug
of its name, so re-importing the same skill replaces it rather than duplicating.

This module is wx-free and fully unit-testable. The UI maps it onto the existing
:func:`~quill.core.skill_pack.parse_skill` / ``run_skill`` primitives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.skill_pack import SkillValidationError, parse_skill

__all__ = ["InstalledSkill", "SkillStore", "slugify_skill_name"]

_INDEX_FILE = "skills.json"
_SQP_SUFFIX = ".sqp"


def slugify_skill_name(name: str) -> str:
    """A stable, filesystem-safe id derived from a skill name.

    Lowercased, non-alphanumeric runs collapsed to single hyphens, trimmed. Empty
    or all-symbol names fall back to ``skill`` so an id is always non-empty.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "skill"


@dataclass(frozen=True, slots=True)
class InstalledSkill:
    """One installed skill: its identity, metadata, source, and enabled state."""

    id: str
    name: str
    description: str
    author: str
    version: str
    source: str
    enabled: bool = True


class SkillStore:
    """List, persist, and manage installed ``.sqp`` skills in a directory."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory

    # -- query ----------------------------------------------------------------

    def all(self) -> list[InstalledSkill]:
        """Every installed skill that still parses, sorted by display name.

        A ``.sqp`` file that no longer parses is skipped rather than raising, so
        one bad file never breaks the whole library view.
        """
        if not self._dir.exists():
            return []
        state = self._load_state()
        skills: list[InstalledSkill] = []
        for path in self._dir.glob(f"*{_SQP_SUFFIX}"):
            skill = self._read(path, state)
            if skill is not None:
                skills.append(skill)
        skills.sort(key=lambda s: s.name.lower())
        return skills

    def find_by_id(self, skill_id: str) -> InstalledSkill | None:
        path = self._path_for(skill_id)
        return self._read(path, self._load_state()) if path.exists() else None

    def find_by_name(self, name: str) -> InstalledSkill | None:
        return self.find_by_id(slugify_skill_name(name))

    def get_source(self, skill_id: str) -> str:
        """The raw ``.sqp`` source for a skill, or '' when not installed."""
        path = self._path_for(skill_id)
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    # -- mutation -------------------------------------------------------------

    def add_source(self, source: str) -> InstalledSkill:
        """Install a skill from ``.sqp`` source text. Raises on invalid source.

        The id is the slug of the parsed name, so re-installing a skill with the
        same name replaces it (no duplicates). Returns the installed skill.
        """
        pack = parse_skill(source)  # raises SkillValidationError on bad source
        skill_id = slugify_skill_name(pack.name)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path_for(skill_id).write_text(source, encoding="utf-8")
        skill = self._read(self._path_for(skill_id), self._load_state())
        assert skill is not None  # we just wrote valid source
        return skill

    def import_sqp(self, path: Path) -> InstalledSkill:
        """Install a skill from a ``.sqp`` file on disk."""
        return self.add_source(path.read_text(encoding="utf-8"))

    def export_sqp(self, skill_id: str, path: Path) -> None:
        """Write a skill's source to ``path``. Raises KeyError if not installed."""
        source = self.get_source(skill_id)
        if not source:
            raise KeyError(skill_id)
        path.write_text(source, encoding="utf-8")

    def remove(self, skill_id: str) -> None:
        """Delete an installed skill and forget its enabled-state."""
        path = self._path_for(skill_id)
        if not path.exists():
            raise KeyError(skill_id)
        path.unlink()
        state = self._load_state()
        if skill_id in state:
            del state[skill_id]
            self._save_state(state)

    def enable(self, skill_id: str) -> None:
        self._set_enabled(skill_id, True)

    def disable(self, skill_id: str) -> None:
        self._set_enabled(skill_id, False)

    # -- internals ------------------------------------------------------------

    def _path_for(self, skill_id: str) -> Path:
        return self._dir / f"{skill_id}{_SQP_SUFFIX}"

    def _read(self, path: Path, state: dict[str, bool]) -> InstalledSkill | None:
        try:
            source = path.read_text(encoding="utf-8")
            pack = parse_skill(source)
        except (OSError, SkillValidationError):
            return None
        skill_id = path.stem
        return InstalledSkill(
            id=skill_id,
            name=pack.name,
            description=pack.description,
            author=pack.author,
            version=pack.version,
            source=source,
            enabled=state.get(skill_id, True),
        )

    def _set_enabled(self, skill_id: str, value: bool) -> None:
        if not self._path_for(skill_id).exists():
            raise KeyError(skill_id)
        state = self._load_state()
        state[skill_id] = value
        self._save_state(state)

    def _load_state(self) -> dict[str, bool]:
        from quill.core.storage import read_json

        data = read_json(self._dir / _INDEX_FILE, default={})
        if not isinstance(data, dict):
            return {}
        return {str(k): bool(v) for k, v in data.items()}

    def _save_state(self, state: dict[str, bool]) -> None:
        from quill.core.storage import write_json_atomic

        self._dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self._dir / _INDEX_FILE, state)
