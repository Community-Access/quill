"""The family-wide choice files' reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when Slider Keys (2026-10-26) joined App Sounds as one small file
of choices every Quill app reads. The seam is real: both are one file for the
whole family in the shared data folder, rather than a field per app.
"""

from __future__ import annotations

FAMILY_ENTRIES: dict[str, str] = {
    # Where each app's own sounds play (app_sounds.json), and which way the
    # arrow keys move a slider in every app (slider_keys.json).
    "core/app_sounds_store.py::save": "marker",
    "core/slider_key_layout.py::save": "marker",
    # Saved find-and-replace jobs, in each editor's own data folder: lists the
    # user made, whose shape only ever grows (both editors, 2026-11-07).
    "core/replace_jobs.py::save_replace_jobs": "content",
    # The Command Key's own small file (command-key.json): whether the one-time
    # hint has been said, and the answer to the Jev consent question.
    "ui/command_key_hosts.py::_save_state": "marker",
    # Beacon's own settings, atomic since the family settings audit
    # (2026-11-20): accessibility, the external player, routing rules and
    # sync. Small, self-describing; an unreadable file reads as defaults.
    "apps/beacon/a11y.py::save": "marker",
    "apps/beacon/external_player.py::save_settings": "marker",
    "apps/beacon/routing.py::save_rules": "content",
    "apps/beacon/sync_ui.py::save_config": "marker",
    # Sync conflicts waiting for review: the user's notes, additive.
    "apps/beacon/sync_ui.py::_persist_conflicts": "content",
    "apps/beacon/sync_ui.py::resolve_conflict": "content",
    # Scribe for Documents, one set for the whole family in the shared data
    # folder, per Windows user (2026-11-21): the options and the documents
    # converted so far are the person's own, additive; the queue is jobs and
    # the family's action count, and the runner lock is who runs it.
    "core/scribe/options.py::save_options": "marker",
    "core/scribe/library.py::record": "content",
    "core/scribe/queue.py::_write": "content",
    "core/scribe/queue.py::try_acquire": "marker",
    # The Scribe live regression run's own record (run.json), written into the
    # run's dated folder outside the repository: a QA output the tool makes for
    # the person who ran it, never read by an app (2026-11-23).
    "tools/scribe_live/layout.py::save_record": "export",
}
