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
}
