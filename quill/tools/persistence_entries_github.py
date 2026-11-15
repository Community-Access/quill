"""The GitHub workbench's reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 when the GitHub
workbench (2026-11-07) brought five write sites. Every one writes through
``write_json_atomic``; none holds a token (tokens live in the credential store).
"""

from __future__ import annotations

GITHUB_ENTRIES: dict[str, str] = {
    # The account list: non-secret login and host per account, schema-stamped.
    "core/github/accounts.py::_persist": "versioned",
    # Local issue and review drafts, kept until they are submitted or discarded.
    "core/github/local_drafts.py::_write": "content",
    # Pending line comments, kept until they go out with the review (Wave 2).
    "core/github/line_comment_drafts.py::_write": "content",
    # The diff's line-mark style (words or symbols), shared by both editors.
    "core/github/review_preferences.py::save_line_marks": "marker",
    # The attention queue's snoozes and the remembered place in each view:
    # regenerable state, and losing it only costs a re-sort.
    "core/github/attention_queue.py::save": "cache",
    "core/github/navigation_state.py::save": "cache",
    # Wave 4: the last ETag and body of each repeated GitHub read, per account,
    # so a refresh can send If-None-Match; losing it costs one full read.
    "core/github/conditional_requests.py::save": "cache",
    # A one-time marker written while moving saved items to per-account files.
    "core/github/saved_items.py::load": "marker",
    # --- the GitHub Workbench (2026-11-10). All four go through write_json_atomic.
    # Change History: every write the Workbench made, schema-stamped. Each entry
    # names its account and is kept 90 days (pruned on load and on save, and
    # clearable at once); before and after values pass the known-secret and
    # token redaction, and secret fields are never logged at all.
    "core/github/change_log.py::save": "versioned",
    # Where the Workbench window was (last node, expanded nodes, open
    # repositories and people), under each account's key in the same resume
    # file as navigation_state.save; capped per account and in accounts kept.
    # No token or content, only node paths; losing it costs a re-navigation.
    "core/github/navigation_state.py::save_workbench_place": "cache",
    # Each account's chosen Workbench access (Read Only, Organize, Full),
    # schema-stamped and keyed by account login. A level, never a token; kept
    # until the person changes it, and an unreadable file reads as the default.
    "core/github/permissions.py::set": "versioned",
    # Workbench Options (github_workbench.json): schema-stamped, coerced field
    # by field on read. Preferences only, the same for every account; no secret.
    "core/github/workbench_prefs.py::save_prefs": "versioned",
    # Watches (PRD 22.5): each account's watch rules and what each last saw
    # (ids of runs, reviews, releases and comments, capped), schema-stamped,
    # keyed by account; no token, no content. Losing it loses the rules.
    "core/github/watches.py::save": "versioned",
    # The API Console's saved requests (PRD 22.2), per account, schema-stamped:
    # a name, a method, a path and a body the person typed. No token.
    "core/github/api_console.py::save": "versioned",
    # Repository Sets (Across Repositories, PRD 22.11): per account, version
    # stamped; names, owner/name lists and filter text only, never a token or
    # fetched content. Losing it costs choosing the repositories again.
    "core/github/repository_sets.py::save": "versioned",
}
