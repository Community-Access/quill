"""The WordPress Workbench's batch sheets and which rows have no sheet (PRD 9).

Split from :mod:`quill.ui.wordpress_workbench_sheets` (GATE-11), which
re-exports :data:`BATCH_SHEETS`. Pure data: the fields many objects share,
the Gravity Forms rows whose sheet the Gravity Forms mixin builds, and the
row kinds whose Properties are read only. wx-free.
"""

from __future__ import annotations

from quill.core.wordpress.workbench_sheets import ITEM_STATUSES
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = ["BATCH_SHEETS"]

_OPEN = ("open", "closed")

BATCH_SHEETS: dict[str, SheetSpec] = {
    "item": SheetSpec(
        "item",
        "Items",
        (
            PageSpec(
                "general",
                "General",
                (
                    FieldSpec("status", "Status", FieldKind.CHOICE, choices=ITEM_STATUSES),
                    FieldSpec("author", "Author number", FieldKind.TEXT),
                    FieldSpec("comment_status", "Comments", FieldKind.CHOICE, choices=_OPEN),
                    FieldSpec("ping_status", "Pingbacks", FieldKind.CHOICE, choices=_OPEN),
                    FieldSpec("sticky", "Sticky", FieldKind.CHECK),
                    FieldSpec("template", "Template", FieldKind.TEXT),
                    FieldSpec("parent", "Parent number", FieldKind.NUMBER),
                    FieldSpec(
                        "featured_media",
                        "Featured image",
                        FieldKind.TEXT,
                        help="The picture shown with each, by title and number. Choose from "
                        "Library lists the site's pictures; Remove Featured Image clears it.",
                    ),
                ),
            ),
            PageSpec(
                "organize",
                "Categories and Tags",
                (
                    FieldSpec("add_categories", "Add categories", FieldKind.LIST),
                    FieldSpec("remove_categories", "Remove categories", FieldKind.LIST),
                    FieldSpec("add_tags", "Add tags", FieldKind.LIST),
                    FieldSpec("remove_tags", "Remove tags", FieldKind.LIST),
                ),
            ),
        ),
    ),
    "media": SheetSpec(
        "media",
        "Media",
        (
            PageSpec(
                "general",
                "General",
                (
                    FieldSpec("title", "Title"),
                    FieldSpec("alt_text", "Alt text"),
                    FieldSpec("caption", "Caption", FieldKind.MULTILINE),
                    FieldSpec("description", "Description", FieldKind.MULTILINE),
                ),
            ),
        ),
    ),
}
"""The batch sheets: fields many objects share (section 9)."""

#: Gravity Forms rows whose sheet the Gravity Forms mixin builds (complete.md 10B.3).
_GRAVITY_SHEETS = ("form_entry", "gravity_feed", "gravity_result")

_NO_EDIT = {
    "fact",
    "help",
    "namespace",
    "ability",
    "problem",
    "site",
    "writing_type",
    "taxonomy",
    "app_password",
    "theme",
    "search_result",
    "global_style",
}
