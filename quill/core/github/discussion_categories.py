"""Repository > Discussions > Categories: grouped by section where GitHub gives sections.

GitHub's Discussions page can group categories into sections. Where a reply
names a category's section, the Categories place lists one row a section
("Section: Q&A (3 categories)"); Enter opens it, and its first row, "All
sections", comes back. GitHub's GraphQL API does not give sections today
(``DiscussionCategory`` has no section field), so the place lists the
categories in GitHub's order and says why once, as the list's note
(:data:`SECTIONS_NOT_IN_API`), rather than inventing a grouping. Enter on a
category lists the repository's discussions in it.

The categories come from
:meth:`~quill.core.github.discussion_actions.GitHubDiscussionActionsMixin.fetch_discussion_categories`,
the call New Discussion already makes. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import quote

from quill.core.github.discussion_actions import DiscussionCategory
from quill.core.github.explore_models import ExploreRow

__all__ = ["ALL_SECTIONS", "SECTIONS_NOT_IN_API", "category_rows"]

#: The first row inside a section: Enter on it lists every section again.
ALL_SECTIONS = "All sections"

SECTIONS_NOT_IN_API = (
    "GitHub's API does not say which section a category is in, so the categories "
    "are listed in GitHub's order; the sections show on the repository's Discussions page."
)

_NO_SECTION = "No section"


def _plural(count: int) -> str:
    return "1 category" if count == 1 else f"{count} categories"


def _category_row(category: DiscussionCategory, repository: str) -> ExploreRow:
    kind = (
        "Question and answer: a reply can be marked the answer."
        if category.answerable
        else "Open-ended discussion."
    )
    lines = [f"Category: {category.name}", f"Format: {kind}"]
    if category.section:
        lines.append(f"Section: {category.section}")
    if category.description:
        lines.extend(["", category.description])
    lines.extend(["", "Enter lists the discussions in this category."])
    slug = quote(category.slug or category.name, safe="")
    return ExploreRow(
        category.name + (", question and answer" if category.answerable else ""),
        "\n".join(lines),
        f"https://github.com/{repository}/discussions/categories/{slug}",
        repository,
        "discussion_category",
        category.name,
        title=category.name,
    )


def category_rows(
    categories: Sequence[DiscussionCategory], repository: str, section: str = ""
) -> tuple[list[ExploreRow], str]:
    """``(rows, note)``: sections, one section's categories, or every category with a note."""
    if not any(category.section for category in categories):
        return [_category_row(c, repository) for c in categories], SECTIONS_NOT_IN_API
    groups: dict[str, list[DiscussionCategory]] = {}
    for category in categories:
        groups.setdefault(category.section or _NO_SECTION, []).append(category)
    url = f"https://github.com/{repository}/discussions"
    if section and section in groups:
        back = ExploreRow(ALL_SECTIONS, "Enter lists every section again.", url, repository,
                          "discussion_section", "")  # fmt: skip
        return [back, *(_category_row(c, repository) for c in groups[section])], ""
    return [
        ExploreRow(
            f"Section: {name} ({_plural(len(members))})",
            f"Section {name}: " + ", ".join(c.name for c in members) + ".\nEnter opens it.",
            url,
            repository,
            "discussion_section",
            name,
            title=name,
        )
        for name, members in groups.items()
    ], ""
