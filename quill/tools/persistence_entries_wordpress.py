"""File > WordPress and Forms: their reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11, as the family,
radio and studio entries are. Every WordPress store lives under the data
folder's ``wordpress`` directory; secrets never do (Credential Manager).
"""

from __future__ import annotations

WORDPRESS_ENTRIES: dict[str, str] = {
    # The site list: names, addresses, roles and per-site switches. Real user
    # configuration that has not adopted versioned_store yet -- the backlog.
    "core/wordpress/sites.py::save_sites": "needs-versioning",
    # Working copies and their previous versions: the person's own writing,
    # self-describing and additive.
    "core/wordpress/local.py::save": "content",
    "core/wordpress/local.py::_write_versions": "content",
    # Sends waiting for a site that could not be reached.
    "core/wordpress/offline.py::_write": "content",
    # Undo records for site-wide fixes and bulk edits, and the history of
    # site checks: what was changed, so it can be put back.
    "core/wordpress/site_fixes.py::_write": "content",
    "core/wordpress/site_report.py::add": "content",
    "ui/wordpress_structure_commands.py::_keep_bulk_record": "content",
    # Earlier looks and logos kept on this computer to go back to.
    "core/wordpress/site_styles.py::keep_previous": "content",
    "core/wordpress/looks_history.py::remember": "content",
    "core/wordpress/visual_review.py::remember_logo": "content",
    # Download My Writing's index of what it fetched, so a second run only
    # fetches what changed.
    "core/wordpress/writing_archive.py::download_writing": "cache",
    # Which AI abilities a site may use (each off until turned on), and when
    # What Changed on My Sites last looked.
    "core/wordpress/abilities.py::set": "marker",
    "core/wordpress/across_sites.py::mark": "marker",
    # Forms: which site copy of each form was published, and the last ten
    # previous copies kept before an update.
    "core/forms/published.py::_write": "content",
    # --- the WordPress Workbench (W6 to W8, 2026-11-10). All go through
    # write_json_atomic, beside the site list; none holds a password (those
    # stay in Credential Manager).
    # Take a Snapshot: a copy of one site's posts, pages, terms, menus,
    # patterns and settings, in a dated folder under that site's own
    # wordpress_snapshots/<site id> directory. Made only when the person asks,
    # kept until they delete it; the settings are what WordPress's settings
    # route returns, which carries no credential.
    # Media records always; the media files themselves only when asked.
    "core/wordpress/workbench_snapshot.py::take_snapshot": "content",
    # Reviewers assigned in the editorial queue (site name, item id, route,
    # title, reviewer's name, the note): WordPress has no reviewer field, so
    # this is the only record the Review Watch can follow. No secret; an
    # unreadable entry is skipped.
    "core/wordpress/workbench_editorial.py::save_reviews": "content",
    # REST Console requests the person saved by name (site, method, route and
    # the parameters as typed), shown as Tools > Saved Requests. The console
    # says not to type a password into one that is kept.
    "core/wordpress/workbench_rest_saved.py::save_all": "content",
    # Workbench Options: watch interval, which Watches are on, and Site Sets
    # by site name. Read field by field with defaults; no secret.
    "core/wordpress/workbench_options.py::save_options": "needs-versioning",
    # The access chosen for each site (Read Only, Organize, Full), keyed by
    # site id so one site's choice never applies to another. A level, never a
    # password; an unknown or unreadable entry reads as the default.
    "core/wordpress/workbench_permissions.py::set": "marker",
    # What the last Watches round saw on each site (comment and entry ids,
    # plugin names, scheduled ids), keyed by site so sites never mix. Losing
    # it costs one round reporting everything as new; no content or secret.
    "core/wordpress/workbench_watches.py::save_state": "cache",
}
