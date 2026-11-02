"""The one-time family prompt migration, run at startup (codex.md decision 18, 10D.2).

:mod:`quill.core.ai.family_prompts` knows how to bring old stores together;
this module decides *which* stores, *when*, and makes sure the run can never
cost anybody a launch. Both editors call :func:`schedule` once at startup with
their task manager's ``submit``, so the file reads and the one write happen on a
worker thread, never the UI thread.

**The old stores** (:func:`discover_sources`), in the order they are merged,
which is also the order a clashing name is kept bare: QUILL's own Prompt
Library already *is* the family store, so its prompts always keep their names.
Then Prompt Studio (``ai/assistant-prompts.json``), the image-description
prompts in QUILL's settings (``vision_custom_prompts``, which need pictures),
and QUILL Lite's own ``prompts.json`` in its data folder.

**Once, per store.** The sidecar's ``migration`` record lists every store that
has been brought in; a store on the list is not read again. A store whose file
does not exist yet (QUILL Lite installed after QUILL first ran) is not put on
the list, so the editor that launches after it arrives brings it in. A store
whose file cannot be read as JSON is left off the list too, and said in the
log, so nothing in it is lost to a run that could not see it.

**Never harmful.** Old files are only read, never written or deleted (they stay
for one release; :func:`~quill.core.ai.family_prompts.stores_ready_to_retire`
names them once a check is recorded). A family store that is itself unreadable
is left alone rather than rewritten with only the migrated prompts. Nothing is
written at all when there is nothing to bring in and the family folder does not
exist, so QUILL Lite on a computer without QUILL grows no QUILL folder for an
empty list. :func:`run_quietly` logs and returns ``None`` on any failure.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.ai.family_prompts import (
    FamilyPromptStore,
    MigrationReport,
    MigrationSource,
    family_store_path,
    migrate,
    read_assistant_prompts,
    read_library_file,
    read_vision_prompts,
)

__all__ = [
    "LITE_LABEL",
    "STUDIO_LABEL",
    "TASK_NAME",
    "VISION_LABEL",
    "FoundSource",
    "discover_sources",
    "done_labels",
    "run",
    "run_quietly",
    "schedule",
]

logger = logging.getLogger(__name__)

TASK_NAME = "family-prompt-migration"
STUDIO_LABEL = "Prompt Studio"
VISION_LABEL = "Image descriptions"
LITE_LABEL = "QUILL Lite"


@dataclass(frozen=True, slots=True)
class FoundSource:
    """One old store as found on this computer.

    ``present`` is whether it may be recorded as brought in: its file exists and
    could be read. A missing or unreadable store is merged from nothing and
    tried again at the next launch.
    """

    source: MigrationSource
    present: bool


def _readable(path: Path) -> bool:
    """Whether *path* exists and holds a JSON object; an unreadable one is logged."""
    if not path.exists():
        return False
    try:
        return isinstance(json.loads(path.read_text(encoding="utf-8")), dict)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        logger.warning("Family prompts: %s could not be read; left for later: %s", path, error)
        return False


def _lite_prompts_path() -> Path:
    from quill.core.lite.paths import data_file

    return data_file("prompts.json")


def _studio_prompts_path() -> Path:
    from quill.core.assistant_prompts import prompts_path

    return prompts_path()


def _quill_settings_path() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "settings.json"


def discover_sources(
    *,
    studio: Path | None = None,
    quill_settings: Path | None = None,
    lite: Path | None = None,
) -> list[FoundSource]:
    """Every old store, read; the paths are for the tests, the defaults are real."""
    found: list[FoundSource] = []
    studio_path = studio if studio is not None else _studio_prompts_path()
    ok = _readable(studio_path)
    found.append(
        FoundSource(
            read_assistant_prompts(studio_path, STUDIO_LABEL)
            if ok
            else MigrationSource(STUDIO_LABEL, (), studio_path),
            ok,
        )
    )
    settings_path = quill_settings if quill_settings is not None else _quill_settings_path()
    ok = _readable(settings_path)
    entries: list[Any] = []
    if ok:
        raw = json.loads(settings_path.read_text(encoding="utf-8")).get("vision_custom_prompts")
        entries = raw if isinstance(raw, list) else []
    # path=None: the settings file is never an old store to retire.
    found.append(FoundSource(read_vision_prompts(entries, VISION_LABEL), ok))
    lite_path = lite if lite is not None else _lite_prompts_path()
    ok = _readable(lite_path)
    found.append(
        FoundSource(
            read_library_file(lite_path, LITE_LABEL)
            if ok
            else MigrationSource(LITE_LABEL, (), lite_path),
            ok,
        )
    )
    return found


def done_labels(store: FamilyPromptStore) -> set[str]:
    """The stores the sidecar says were already brought in."""
    record = store.meta().get("migration", {})
    sources = record.get("sources", []) if isinstance(record, dict) else []
    return {str(label) for label in sources} if isinstance(sources, list) else set()


def run(
    store: FamilyPromptStore | None = None,
    found: Sequence[FoundSource] | None = None,
) -> MigrationReport | None:
    """Bring in every store not brought in yet. ``None`` when nothing was done.

    May raise on a disk error; :func:`run_quietly` is the startup entry point.
    """
    store = store if store is not None else FamilyPromptStore(family_store_path())
    if store.path.exists() and not _readable(store.path):
        return None  # never rewrite somebody's list with only the migrated half
    done = done_labels(store)
    pending = [
        item
        for item in (found if found is not None else discover_sources())
        if item.present and item.source.label not in done
    ]
    if not pending:
        return None
    if not any(item.source.prompts for item in pending) and not store.path.parent.exists():
        return None  # nothing to bring, and no family folder to create for it
    report = migrate(store, [item.source for item in pending])
    logger.info("Family prompts: %s", report.sentence())
    return report


def run_quietly(**_task_kwargs: Any) -> MigrationReport | None:
    """:func:`run`, with every failure logged and swallowed: startup goes on.

    Accepts the task manager's ``cancellation_token`` / ``operation_id``.
    """
    try:
        return run()
    except Exception:  # noqa: BLE001 - a prompt migration must never break startup
        logger.exception("Family prompts: the one-time migration failed; startup continues")
        return None


def schedule(
    submit: Callable[..., Any],
    *,
    on_done: Callable[[MigrationReport], None] | None = None,
) -> bool:
    """Hand :func:`run_quietly` to *submit* (a task manager's ``submit``). Never raises.

    *on_done* is called on the UI thread with the report, only when prompts were
    brought in, so a window holding a cached list can drop it and read again.
    """

    def delivered(_operation_id: str, report: Any) -> None:
        if on_done is not None and isinstance(report, MigrationReport) and report.added:
            on_done(report)

    def failed(_operation_id: str, error: BaseException) -> None:
        logger.warning("Family prompts: the migration task failed: %s", error)

    try:
        submit(TASK_NAME, run_quietly, on_success=delivered, on_failure=failed)
    except Exception:  # noqa: BLE001 - scheduling is never worth a failed launch
        logger.exception("Family prompts: the migration could not be scheduled")
        return False
    return True
