"""One-prompt-store-truth migration (AI Library, Phase 2).

QUILL grew two custom-prompt stores that never knew about each other: the
canonical :class:`~quill.core.prompt_library.PromptLibrary` (``prompts.json``,
the Prompt Library / AI Library surface) and the older
:mod:`quill.core.assistant_prompts` store (``ai/assistant-prompts.json``, the
Prompt Studio surface). A prompt saved in one was invisible in the other.

:func:`consolidate_prompts` copies every legacy ``assistant_prompts`` custom
prompt into the canonical library so the unified AI Library shows all of them.

The migration is **reversible, non-destructive, and idempotent**, mirroring
:mod:`quill.core.ai.key_migration`: each legacy prompt is added under a stable
derived id (``assistant-<prompt_id>``, ``source="migrated"``); a re-run skips any
id already present; and the legacy ``assistant-prompts.json`` file is never
modified or deleted, so the migration reverts simply by removing the migrated
prompts. It is kept in its own module so neither store grows past its budget.
"""

from __future__ import annotations

__all__ = ["MIGRATED_ID_PREFIX", "consolidate_prompts", "consolidate_prompts_quietly"]

# Prefix for the canonical-library id of a prompt copied from the legacy store.
# Stable + namespaced so the migration is idempotent and the origin is obvious.
MIGRATED_ID_PREFIX = "assistant-"


def consolidate_prompts() -> list[str]:
    """Copy legacy ``assistant_prompts`` prompts into the canonical library.

    Returns the canonical ids that were added this run (empty when there is
    nothing new). Never raises — a migration must not break startup.
    """
    migrated: list[str] = []
    try:
        from quill.core.assistant_prompts import load_custom_prompts
        from quill.core.paths import app_data_dir
        from quill.core.prompt_library import PromptLibrary

        legacy = load_custom_prompts()
        if not legacy:
            return []

        library = PromptLibrary(app_data_dir() / "prompts.json")
        for prompt in legacy:
            target_id = f"{MIGRATED_ID_PREFIX}{prompt.prompt_id}"
            if library.find_by_id(target_id) is not None:
                continue  # already migrated (or a name/id clash) — idempotent
            try:
                library.upsert_external(
                    id=target_id,
                    name=prompt.title,
                    text=prompt.template,
                    category="Custom",
                    shortcut=prompt.shortcut,
                    source="migrated",
                )
            except ValueError:
                continue  # never overwrite a built-in
            migrated.append(target_id)
    except Exception:  # noqa: BLE001 - a migration must never break startup
        return migrated
    return migrated


def consolidate_prompts_quietly() -> None:
    """Run :func:`consolidate_prompts`, swallowing any error (startup hook)."""
    try:
        consolidate_prompts()
    except Exception:  # noqa: BLE001 - prompt migration must never break startup
        pass
