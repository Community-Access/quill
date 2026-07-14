"""AI Prompt Library — named prompts for document editing and research.

Provides :class:`PromptLibrary` backed by atomic JSON storage and a fixed set
of built-in prompts that ship with QUILL. Users can add, edit, enable, and
disable prompts. Built-in prompts are always present; their text and enabled
state can be overridden but they cannot be removed.

Quillins can contribute additional prompts by placing a ``prompts.json`` file
in their directory and calling :meth:`PromptLibrary.load_quillin_prompts`.
Quillin-sourced prompts are held in memory only and are not persisted.

Prompt text may use ``{selection}`` (selected text), ``{document}`` (full
document), and ``{title}`` (document title) as substitution placeholders.

PQL (QUILL Prompt Library) file format — a JSON object::

    {
        "schema": "quill.prompt-pack/1",
        "name": "Pack display name",
        "prompts": [
            {"name": "...", "text": "...", "category": "..."}
        ]
    }
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CATEGORIES: tuple[str, ...] = ("Editing", "Writing", "Structure", "Research", "Custom")
PQP_SCHEMA = "quill.prompt-pack/1"


@dataclass
class Prompt:
    id: str
    name: str
    text: str
    category: str
    is_builtin: bool = False
    enabled: bool = True
    shortcut: str = ""
    source: str = "user"


_GRAMMAR_TEXT = (
    "You are a grammar and style editor. Review the following text and list only the "
    "corrections needed. For each correction, give: the original phrase, the corrected "
    "phrase, and a one-sentence reason. Do not rewrite the whole passage. "
    'If the text is correct, say "No issues found."\n\nText:\n{selection}'
)

BUILTIN_PROMPTS: list[Prompt] = [
    Prompt(
        id="builtin-check-grammar",
        name="Check Grammar",
        text=_GRAMMAR_TEXT,
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-improve-clarity",
        name="Improve Clarity",
        text=(
            "Rewrite the following text to be clearer and easier to read, without changing "
            "its meaning or length significantly:\n\n{selection}"
        ),
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-make-concise",
        name="Make Concise",
        text=(
            "Rewrite the following text to be more concise, removing unnecessary words "
            "while preserving the full meaning:\n\n{selection}"
        ),
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-fix-grammar",
        name="Fix Grammar",
        text=(
            "Correct all grammar, punctuation, and spelling errors in the following text. "
            "Return only the corrected text with no explanation:\n\n{selection}"
        ),
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-active-voice",
        name="Active Voice",
        text=(
            "Rewrite the following text using active voice throughout. "
            "Return only the rewritten text:\n\n{selection}"
        ),
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-formal-tone",
        name="Formal Tone",
        text="Rewrite the following text in a formal, professional tone:\n\n{selection}",
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-conversational-tone",
        name="Conversational Tone",
        text="Rewrite the following text in a friendly, conversational tone:\n\n{selection}",
        category="Editing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-continue-from-here",
        name="Continue from Here",
        text=(
            "Continue writing naturally from the following text, matching its style and "
            "voice. Write about the same length as what is provided:\n\n{selection}"
        ),
        category="Writing",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-summarize",
        name="Summarize",
        text="Write a one-paragraph summary of the following text:\n\n{selection}",
        category="Structure",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-bullet-points",
        name="Convert to Bullet Points",
        text=(
            "Convert the following text into a clear, well-organized list of "
            "bullet points:\n\n{selection}"
        ),
        category="Structure",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-define-term",
        name="Define This Term",
        text=(
            "Provide a clear, concise definition of the following term or concept. "
            "Include a brief example if helpful:\n\n{selection}"
        ),
        category="Research",
        is_builtin=True,
        source="builtin",
    ),
    Prompt(
        id="builtin-counterarguments",
        name="Find Counterarguments",
        text=(
            "List the strongest counterarguments to the following claim or argument:\n\n{selection}"
        ),
        category="Research",
        is_builtin=True,
        source="builtin",
    ),
]


class PromptLibrary:
    """Load, persist, and query AI prompts."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._prompts: dict[str, Prompt] = {}
        self._quillin_prompts: list[Prompt] = []
        for p in BUILTIN_PROMPTS:
            self._prompts[p.id] = Prompt(**asdict(p))
        if path.exists():
            self._load()

    # -- query ----------------------------------------------------------------

    def all(self) -> list[Prompt]:
        return sorted(
            list(self._prompts.values()) + self._quillin_prompts,
            key=lambda p: (p.category, p.name),
        )

    def enabled_only(self) -> list[Prompt]:
        return [p for p in self.all() if p.enabled]

    def find_by_name(self, name: str) -> Prompt | None:
        name_lower = name.lower()
        for p in self.all():
            if p.name.lower() == name_lower:
                return p
        return None

    def find_by_id(self, prompt_id: str) -> Prompt | None:
        if prompt_id in self._prompts:
            return self._prompts[prompt_id]
        for p in self._quillin_prompts:
            if p.id == prompt_id:
                return p
        return None

    # -- mutation -------------------------------------------------------------

    def add(self, name: str, text: str, category: str, shortcut: str = "") -> Prompt:
        p = Prompt(
            id=str(uuid.uuid4()),
            name=name,
            text=text,
            category=category if category in CATEGORIES else "Custom",
            shortcut=shortcut,
            source="user",
        )
        self._prompts[p.id] = p
        self._save()
        return p

    def upsert_external(
        self,
        *,
        id: str,
        name: str,
        text: str,
        category: str = "Custom",
        shortcut: str = "",
        source: str = "user",
    ) -> Prompt:
        """Insert or replace a user prompt by explicit id (import / migration).

        Unlike :meth:`add` (which mints a fresh uuid), this preserves a caller-
        supplied id so an import or a store migration is idempotent and
        reversible. Refuses to overwrite a built-in prompt. The prompt is
        persisted immediately.
        """
        existing = self._prompts.get(id)
        if existing is not None and existing.is_builtin:
            raise ValueError("Built-in prompts cannot be overwritten.")
        p = Prompt(
            id=id,
            name=name,
            text=text,
            category=category if category in CATEGORIES else "Custom",
            shortcut=shortcut,
            source=source,
        )
        self._prompts[id] = p
        self._save()
        return p

    def update(self, prompt_id: str, **kwargs: Any) -> None:
        p = self._prompts.get(prompt_id)
        if p is None:
            raise KeyError(prompt_id)
        allowed = {"name", "text", "category", "shortcut", "enabled"}
        for k, v in kwargs.items():
            if k in allowed:
                setattr(p, k, v)
        self._save()

    def remove(self, prompt_id: str) -> None:
        p = self._prompts.get(prompt_id)
        if p is None:
            raise KeyError(prompt_id)
        if p.is_builtin:
            raise ValueError("Built-in prompts cannot be removed.")
        del self._prompts[prompt_id]
        self._save()

    def enable(self, prompt_id: str) -> None:
        self.update(prompt_id, enabled=True)

    def disable(self, prompt_id: str) -> None:
        self.update(prompt_id, enabled=False)

    # -- Quillin integration --------------------------------------------------

    def load_quillin_prompts(self, prompts_json_path: Path) -> None:
        """Load prompts from a Quillin-provided prompts.json file."""
        if not prompts_json_path.exists():
            return
        try:
            items = json.loads(prompts_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(items, list):
            return
        source = prompts_json_path.parent.name
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            text = str(item.get("text", "")).strip()
            category = str(item.get("category", "Custom"))
            if not name or not text:
                continue
            if category not in CATEGORIES:
                category = "Custom"
            pid = f"{source}-{name.lower().replace(' ', '-')}"
            self._quillin_prompts.append(
                Prompt(id=pid, name=name, text=text, category=category, source=source)
            )

    # -- PQL import / export --------------------------------------------------

    def export_pqp(self, path: Path, prompt_ids: list[str] | None = None) -> int:
        """Export prompts to a .pqp file. Returns the count written."""
        prompts = (
            self.all() if prompt_ids is None else [p for p in self.all() if p.id in prompt_ids]
        )
        pack = {
            "schema": PQP_SCHEMA,
            "name": path.stem,
            "prompts": [{"name": p.name, "text": p.text, "category": p.category} for p in prompts],
        }
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(pack["prompts"])

    def import_pqp(self, path: Path) -> list[Prompt]:
        """Import prompts from a .pqp file. Returns newly added prompts."""
        data = json.loads(path.read_text(encoding="utf-8"))
        added: list[Prompt] = []
        for item in data.get("prompts", []):
            name = str(item.get("name", "")).strip()
            text = str(item.get("text", "")).strip()
            category = str(item.get("category", "Custom"))
            if not name or not text:
                continue
            if self.find_by_name(name) is not None:
                continue
            added.append(self.add(name, text, category))
        return added

    # -- persistence ----------------------------------------------------------

    def _save(self) -> None:
        from quill.core.storage import write_json_atomic

        user_prompts = [asdict(p) for p in self._prompts.values() if not p.is_builtin]
        builtin_overrides = {
            p.id: {"text": p.text, "enabled": p.enabled}
            for p in self._prompts.values()
            if p.is_builtin and self._is_overridden(p)
        }
        write_json_atomic(
            self._path,
            {
                "user_prompts": user_prompts,
                "builtin_overrides": builtin_overrides,
            },
        )

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        fields = {f for f in Prompt.__dataclass_fields__}
        for item in data.get("user_prompts", []):
            if not isinstance(item, dict):
                continue
            try:
                p = Prompt(**{k: v for k, v in item.items() if k in fields})
                self._prompts[p.id] = p
            except (TypeError, KeyError):
                continue
        for pid, override in data.get("builtin_overrides", {}).items():
            if pid in self._prompts and isinstance(override, dict):
                p = self._prompts[pid]
                if "text" in override:
                    p.text = str(override["text"])
                if "enabled" in override:
                    p.enabled = bool(override["enabled"])

    def _is_overridden(self, p: Prompt) -> bool:
        orig = next((b for b in BUILTIN_PROMPTS if b.id == p.id), None)
        if orig is None:
            return False
        return p.text != orig.text or not p.enabled
