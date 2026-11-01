"""One user-prompt store for the whole family (codex.md decision 18, 10D.2).

A prompt saved in any app's Ask or pad is a prompt every app can use. The
store is ``<app data>/prompts.json`` -- the very file QUILL's Prompt Library
already keeps (:class:`quill.core.prompt_library.PromptLibrary`), in its shape
(``user_prompts`` and ``builtin_overrides``), so QUILL's existing Prompt Library
keeps showing every prompt and nothing has to be read twice. Writes here keep
every key and field this module does not own.

What the Prompt Library has no field for -- a prompt's ``needs``
(``pictures``, ``tools``) and the migration's record -- lives beside it in
``prompts-family.json``, keyed by prompt id. The Prompt Library rewrites
``prompts.json`` with only its own fields, so anything kept inside that file
would be lost the first time QUILL saved; a sidecar cannot be.

**Fields.** ``{selection}``, ``{document}`` and ``{title}`` as
:func:`quill.core.prompt_fill.fill_prompt` fills them, and the new
``{context}``, filled from the app's ``ask_context()`` facts.

**The one-time migration**, on the precedent of
:mod:`quill.core.prompt_migration`, from the stores that grew apart: another
app's own ``prompts.json`` (QUILL Lite keeps one in its data folder),
``ai/assistant-prompts.json`` (:mod:`quill.core.assistant_prompts`), and the
vision custom prompts in settings (``vision_custom_prompts``; these need
pictures). User skills and agents are not prompts -- they are ``.sqp`` packs
and ``.md`` agent specs with tools and instructions of their own -- and stay
where they are.

* Identical prompts (same name and text) merge into one.
* Same name, different text: both are kept, the second named by its old store
  ("Tighten (from Prompt Studio)").
* Re-running adds nothing: every migrated prompt has a stable id.
* Old files are never written or deleted here. :func:`check_migration`
  confirms every old prompt arrived and records that check;
  :func:`stores_ready_to_retire` names the old files only once a check is
  recorded and a later release is running, so they stay for one release.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.prompt_fill import PROMPTS_FILE, fill_prompt
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "META_FILE",
    "MIGRATION_PREFIX",
    "PROMPTS_FILE",
    "FamilyPrompt",
    "FamilyPromptError",
    "FamilyPromptStore",
    "MigrationReport",
    "MigrationSource",
    "OldPrompt",
    "check_migration",
    "family_store_path",
    "fill_family_prompt",
    "migrate",
    "read_assistant_prompts",
    "read_library_file",
    "read_vision_prompts",
    "stores_ready_to_retire",
]

META_FILE = "prompts-family.json"
MIGRATION_PREFIX = "family-"
_META_VERSION = 1
_KNOWN_NEEDS = ("pictures", "tools")


class FamilyPromptError(CodedError):
    """A family prompt could not be saved; the message is a sentence for a person."""

    code = "QUILL-AI-PROMPTS-STORE-FAILED"


def family_store_path() -> Path:
    """``<app data>/prompts.json``: QUILL's data folder, which the family shares."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / PROMPTS_FILE


def fill_family_prompt(
    text: str, *, selection: str = "", document: str = "", context: str = "", title: str = ""
) -> str:
    """*text* with every family field filled; ``{context}`` is the app's facts."""
    return fill_prompt(
        text.replace("{context}", context), selection=selection, document=document, title=title
    ).strip()


@dataclass(frozen=True, slots=True)
class FamilyPrompt:
    """One user prompt, as every app's Ask and pad sees it."""

    id: str
    name: str
    text: str
    category: str = "Custom"
    shortcut: str = ""
    source: str = "user"
    enabled: bool = True
    needs: tuple[str, ...] = ()


def _clean_needs(needs: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for need in needs:
        word = str(need).strip().lower()
        if word in _KNOWN_NEEDS and word not in out:
            out.append(word)
    return tuple(out)


class FamilyPromptStore:
    """``prompts.json`` plus its sidecar, read and written without losing a field."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.meta_path = self.path.with_name(META_FILE)

    # -- reading -------------------------------------------------------------- #

    def _raw(self) -> dict[str, Any]:
        data = read_json(self.path, default={})
        return data if isinstance(data, dict) else {}

    def meta(self) -> dict[str, Any]:
        data = read_json(self.meta_path, default={})
        return data if isinstance(data, dict) else {}

    def prompts(self) -> list[FamilyPrompt]:
        """Every user prompt (built-ins are the Prompt Library's, not the family's)."""
        needs_by_id = self.meta().get("needs", {})
        if not isinstance(needs_by_id, dict):
            needs_by_id = {}
        out: list[FamilyPrompt] = []
        for item in self._raw().get("user_prompts", []):
            if not isinstance(item, dict) or item.get("is_builtin"):
                continue
            prompt_id = str(item.get("id", "")).strip()
            text = str(item.get("text", ""))
            if not prompt_id or not text.strip():
                continue
            raw_needs = needs_by_id.get(prompt_id, [])
            out.append(
                FamilyPrompt(
                    id=prompt_id,
                    name=str(item.get("name", "")).strip() or "Untitled prompt",
                    text=text,
                    category=str(item.get("category", "Custom")) or "Custom",
                    shortcut=str(item.get("shortcut", "")),
                    source=str(item.get("source", "user")),
                    enabled=bool(item.get("enabled", True)),
                    needs=_clean_needs(raw_needs if isinstance(raw_needs, list) else []),
                )
            )
        return out

    def find(self, prompt_id: str) -> FamilyPrompt | None:
        return next((p for p in self.prompts() if p.id == prompt_id), None)

    # -- writing -------------------------------------------------------------- #

    def _write_prompts(self, data: dict[str, Any]) -> None:
        data.setdefault("user_prompts", [])
        data.setdefault("builtin_overrides", {})
        try:
            write_json_atomic(self.path, data)
        except OSError as error:
            raise FamilyPromptError(f"Your prompts could not be saved: {error}") from error

    def _write_meta(self, meta: dict[str, Any]) -> None:
        meta["version"] = _META_VERSION
        try:
            write_json_atomic(self.meta_path, meta)
        except OSError as error:
            raise FamilyPromptError(f"Your prompts could not be saved: {error}") from error

    def add_many(self, prompts: Sequence[FamilyPrompt]) -> None:
        """Add or replace *prompts* by id in one write, keeping everything else."""
        if not prompts:
            return
        data = self._raw()
        items = [i for i in data.get("user_prompts", []) if isinstance(i, dict)]
        index = {str(i.get("id", "")): n for n, i in enumerate(items)}
        meta = self.meta()
        raw_needs = meta.get("needs")
        needs: dict[str, Any] = raw_needs if isinstance(raw_needs, dict) else {}
        for prompt in prompts:
            if not prompt.name.strip() or not prompt.text.strip():
                raise FamilyPromptError("A prompt needs a name and some text.")
            row = {
                "id": prompt.id,
                "name": prompt.name,
                "text": prompt.text,
                "category": prompt.category,
                "is_builtin": False,
                "enabled": prompt.enabled,
                "shortcut": prompt.shortcut,
                "source": prompt.source,
            }
            if prompt.id in index:
                items[index[prompt.id]] = {**items[index[prompt.id]], **row}
            else:
                index[prompt.id] = len(items)
                items.append(row)
            if prompt.needs:
                needs[prompt.id] = list(_clean_needs(prompt.needs))
            else:
                needs.pop(prompt.id, None)
        data["user_prompts"] = items
        self._write_prompts(data)
        meta["needs"] = needs
        self._write_meta(meta)

    def add(
        self, name: str, text: str, *, needs: Iterable[str] = (), category: str = "Custom"
    ) -> FamilyPrompt:
        prompt = FamilyPrompt(
            id=str(uuid.uuid4()),
            name=name.strip(),
            text=text,
            category=category,
            needs=_clean_needs(needs),
        )
        self.add_many([prompt])
        return prompt

    def remove(self, prompt_id: str) -> bool:
        data = self._raw()
        items = [i for i in data.get("user_prompts", []) if isinstance(i, dict)]
        kept = [i for i in items if str(i.get("id", "")) != prompt_id]
        if len(kept) == len(items):
            return False
        data["user_prompts"] = kept
        self._write_prompts(data)
        meta = self.meta()
        if isinstance(meta.get("needs"), dict):
            meta["needs"].pop(prompt_id, None)
            self._write_meta(meta)
        return True

    def record(self, key: str, value: Mapping[str, Any]) -> None:
        """Keep a migration record under *key* in the sidecar."""
        meta = self.meta()
        meta[key] = dict(value)
        self._write_meta(meta)


# -- the old stores ------------------------------------------------------------ #


@dataclass(frozen=True, slots=True)
class OldPrompt:
    """One prompt as an old store kept it."""

    old_id: str
    name: str
    text: str
    needs: tuple[str, ...] = ()
    shortcut: str = ""


@dataclass(frozen=True, slots=True)
class MigrationSource:
    """One old store: its spoken name, its file (when it is one), its prompts."""

    label: str
    prompts: tuple[OldPrompt, ...]
    path: Path | None = None


def read_library_file(path: Path, label: str) -> MigrationSource:
    """Another app's ``prompts.json`` (Prompt Library shape), user prompts only."""
    data = read_json(path, default={})
    found: list[OldPrompt] = []
    for item in data.get("user_prompts", []) if isinstance(data, dict) else []:
        if isinstance(item, dict) and not item.get("is_builtin") and str(item.get("text", "")):
            found.append(
                OldPrompt(
                    str(item.get("id", "")),
                    str(item.get("name", "")).strip() or "Untitled prompt",
                    str(item.get("text", "")),
                    shortcut=str(item.get("shortcut", "")),
                )
            )
    return MigrationSource(label, tuple(found), path)


def read_assistant_prompts(path: Path, label: str = "Prompt Studio") -> MigrationSource:
    """``ai/assistant-prompts.json``, read with the store's own parser."""
    from quill.core.assistant_prompts import CustomPrompt

    data = read_json(path, default={})
    found: list[OldPrompt] = []
    raw = data.get("prompts", []) if isinstance(data, dict) else []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        prompt = CustomPrompt.from_dict(item)
        if prompt.template:
            found.append(
                OldPrompt(prompt.prompt_id, prompt.title, prompt.template, (), prompt.shortcut)
            )
    return MigrationSource(label, tuple(found), path)


def read_vision_prompts(
    entries: Iterable[Mapping[str, Any]], label: str = "Image descriptions"
) -> MigrationSource:
    """``settings.vision_custom_prompts`` (``id``, ``title``, ``prompt``); they need pictures."""
    found = [
        OldPrompt(
            str(e.get("id", "")),
            str(e.get("title", "")).strip() or str(e.get("id", "")),
            str(e.get("prompt", "")),
            ("pictures",),
        )
        for e in entries
        if isinstance(e, Mapping) and e.get("id") and str(e.get("prompt", "")).strip()
    ]
    return MigrationSource(label, tuple(found), None)


# -- the migration ------------------------------------------------------------- #


@dataclass
class MigrationReport:
    added: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    renamed: list[str] = field(default_factory=list)

    def sentence(self) -> str:
        total = len(self.added)
        if not total and not self.merged:
            return "There were no prompts to bring together."
        words = f"{total} prompt{'' if total == 1 else 's'} brought into one list"
        if self.merged:
            words += f"; {len(self.merged)} already there"
        if self.renamed:
            words += f"; {len(self.renamed)} renamed after the store they came from"
        return words + "."


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "store"


def _migrated_id(source: MigrationSource, prompt: OldPrompt) -> str:
    return f"{MIGRATION_PREFIX}{_slug(source.label)}-{prompt.old_id or _slug(prompt.name)}"


def _same_text(a: str, b: str) -> bool:
    return " ".join(a.split()) == " ".join(b.split())


def migrate(store: FamilyPromptStore, sources: Sequence[MigrationSource]) -> MigrationReport:
    """Bring every old store's prompts into *store*, once. Never touches the old stores."""
    report = MigrationReport()
    existing = store.prompts()
    by_id = {p.id for p in existing}
    names: dict[str, list[str]] = {}
    for prompt in existing:
        names.setdefault(prompt.name.lower(), []).append(prompt.text)
    new: list[FamilyPrompt] = []
    for source in sources:
        for old in source.prompts:
            target_id = _migrated_id(source, old)
            texts = names.get(old.name.lower(), [])
            if target_id in by_id or any(_same_text(t, old.text) for t in texts):
                report.merged.append(old.name)
                continue
            name = old.name
            if texts:
                name = f"{old.name} (from {source.label})"
                report.renamed.append(name)
            new.append(
                FamilyPrompt(
                    id=target_id,
                    name=name,
                    text=old.text,
                    shortcut=old.shortcut,
                    source="migrated",
                    needs=_clean_needs(old.needs),
                )
            )
            by_id.add(target_id)
            names.setdefault(old.name.lower(), []).append(old.text)
            report.added.append(name)
    store.add_many(new)
    previous = store.meta().get("migration", {})
    previous = previous if isinstance(previous, dict) else {}
    earlier = previous.get("sources", [])
    labels = [str(label) for label in earlier] if isinstance(earlier, list) else []
    labels += [s.label for s in sources if s.label not in labels]
    store.record(
        "migration",
        {**previous, "done": datetime.now(UTC).isoformat(timespec="seconds"), "sources": labels},
    )
    return report


def check_migration(
    store: FamilyPromptStore, sources: Sequence[MigrationSource], *, release: str
) -> list[str]:
    """Confirm every old prompt's text is in *store*; record the check when it is.

    Returns the names of prompts that did *not* arrive (empty means checked).
    The record names *release*, so the old files are retired a release later.
    """
    texts = [p.text for p in store.prompts()]
    missing = [
        old.name
        for source in sources
        for old in source.prompts
        if not any(_same_text(old.text, t) for t in texts)
    ]
    if not missing:
        migration = store.meta().get("migration", {})
        store.record(
            "migration",
            {
                **(migration if isinstance(migration, dict) else {}),
                "checked": datetime.now(UTC).isoformat(timespec="seconds"),
                "checked_release": release,
            },
        )
    return missing


def stores_ready_to_retire(
    store: FamilyPromptStore, sources: Sequence[MigrationSource], *, release: str
) -> list[Path]:
    """The old files that may now be deleted: only after a recorded check, and only
    once a later release than the one that checked is running."""
    migration = store.meta().get("migration", {})
    if not isinstance(migration, dict) or not migration.get("checked"):
        return []
    checked_in = str(migration.get("checked_release", ""))
    if not checked_in or checked_in == release:
        return []
    return [s.path for s in sources if s.path is not None and s.path.exists()]
