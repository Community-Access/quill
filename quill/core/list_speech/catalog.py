"""The list types a List Speech Template can be written for, and their fields.

A *list type* is one kind of row a screen reader speaks: a GitHub issue, a
notification, a WordPress post. Each declares the **fields** a template may
use, the three built-in presets (Brief, Balanced, Detailed) and a real-looking
sample row for the editor's live preview. The catalog is declarative data, so
adding a field or a list type is one entry and nothing else.

A field has two names. ``title`` is what the editor's picker shows ("Last
updated"). ``spoken_label`` is the word said before the value when labels are
on ("updated yesterday"); it is empty for a value that already says what it
is ("open", "Draft", "3 comments"), so those are never labelled twice.

Wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "BALANCED",
    "BRIEF",
    "DETAILED",
    "LIST_TYPES",
    "FieldDef",
    "ListType",
    "Preset",
    "get_list_type",
    "list_type_ids",
]

BRIEF = "brief"
BALANCED = "balanced"
DETAILED = "detailed"


@dataclass(frozen=True, slots=True)
class FieldDef:
    """One field a row of a list type can say."""

    id: str
    title: str
    spoken_label: str = ""


@dataclass(frozen=True, slots=True)
class Preset:
    """A built-in template: a name, the fields in order, and whether labels are said."""

    id: str
    title: str
    fields: tuple[str, ...]
    labels: bool = False


@dataclass(frozen=True, slots=True)
class ListType:
    """A kind of list: its fields, its presets and a sample row for the preview."""

    id: str
    title: str
    #: Lists that read alike share a family, so one template can serve them all.
    family: str
    fields: tuple[FieldDef, ...]
    presets: tuple[Preset, ...]
    sample: Mapping[str, str]

    def field(self, field_id: str) -> FieldDef | None:
        return next((f for f in self.fields if f.id == field_id), None)

    def field_ids(self) -> tuple[str, ...]:
        return tuple(f.id for f in self.fields)

    def preset(self, preset_id: str) -> Preset | None:
        return next((p for p in self.presets if p.id == preset_id), None)


def _presets(
    brief: tuple[str, ...], balanced: tuple[str, ...], detailed: tuple[str, ...]
) -> tuple[Preset, ...]:
    return (
        Preset(BRIEF, "Brief", brief),
        Preset(BALANCED, "Balanced", balanced),
        Preset(DETAILED, "Detailed", detailed, labels=True),
    )


_ISSUE_FIELDS = (
    FieldDef("number", "Number"),
    FieldDef("title", "Title"),
    FieldDef("state", "State"),
    FieldDef("author", "Author", "by"),
    FieldDef("updated", "Last updated (date)", "updated"),
    FieldDef("updated_ago", "Last updated (how long ago)", "updated"),
    FieldDef("labels", "Labels", "labels"),
    FieldDef("assignees", "Assigned to", "assigned to"),
    FieldDef("comments", "Comment count"),
)

_ISSUE_SAMPLE = {
    "number": "number 42",
    "title": "Login fails after password reset",
    "state": "open",
    "author": "octocat",
    "updated": "2026-11-26",
    "updated_ago": "yesterday",
    "labels": "bug, accessibility",
    "assignees": "mona",
    "comments": "3 comments",
}

_PULL_FIELDS = (
    *_ISSUE_FIELDS,
    FieldDef("branches", "Branches", "branches"),
    FieldDef("review", "Review status", "review"),
)

_PULL_SAMPLE = {
    **_ISSUE_SAMPLE,
    "title": "Speak list rows from templates",
    "branches": "feat/list-speech into main",
    "review": "approved",
}

LIST_TYPES: tuple[ListType, ...] = (
    ListType(
        id="github_issues",
        title="GitHub issues",
        family="github_items",
        fields=_ISSUE_FIELDS,
        presets=_presets(
            ("number", "title", "state"),
            ("number", "title", "state", "updated_ago", "comments"),
            (
                "number",
                "title",
                "state",
                "author",
                "updated_ago",
                "labels",
                "assignees",
                "comments",
            ),
        ),
        sample=_ISSUE_SAMPLE,
    ),
    ListType(
        id="github_pulls",
        title="GitHub pull requests",
        family="github_items",
        fields=_PULL_FIELDS,
        presets=_presets(
            ("number", "title", "state"),
            ("number", "title", "state", "review", "updated_ago"),
            (
                "number",
                "title",
                "state",
                "author",
                "review",
                "branches",
                "updated_ago",
                "labels",
                "comments",
            ),  # fmt: skip
        ),
        sample=_PULL_SAMPLE,
    ),
    ListType(
        id="github_notifications",
        title="GitHub notifications",
        family="github_notifications",
        fields=(
            FieldDef("status", "Read or unread"),
            FieldDef("reason", "Why you got it", "because"),
            FieldDef("repository", "Repository", "in"),
            FieldDef("title", "Title"),
            FieldDef("kind", "What it is about"),
            FieldDef("updated", "Last updated (date)", "updated"),
            FieldDef("updated_ago", "Last updated (how long ago)", "updated"),
        ),
        presets=_presets(
            ("status", "title"),
            ("status", "reason", "repository", "title"),
            ("status", "reason", "repository", "kind", "title", "updated_ago"),
        ),
        sample={
            "status": "Unread",
            "reason": "you were asked to review",
            "repository": "Community-Access/quill",
            "title": "Speak list rows from templates",
            "kind": "pull request",
            "updated": "2026-11-27",
            "updated_ago": "today",
        },
    ),
    ListType(
        id="github_repositories",
        title="GitHub repositories",
        family="github_repositories",
        fields=(
            FieldDef("name", "Name"),
            FieldDef("description", "Description"),
            FieldDef("visibility", "Public or private"),
            FieldDef("language", "Language", "written in"),
            FieldDef("stars", "Star count"),
            FieldDef("updated_ago", "Last updated (how long ago)", "updated"),
        ),
        presets=_presets(
            ("name",),
            ("name", "description", "visibility"),
            ("name", "description", "visibility", "language", "stars", "updated_ago"),
        ),
        sample={
            "name": "Community-Access/quill",
            "description": "Screen-reader-first apps for Windows",
            "visibility": "public",
            "language": "Python",
            "stars": "120 stars",
            "updated_ago": "2 days ago",
        },
    ),
    ListType(
        id="wordpress_posts",
        title="WordPress posts and pages",
        family="wordpress_content",
        fields=(
            FieldDef("status", "Status"),
            FieldDef("title", "Title"),
            FieldDef("author", "Author", "author"),
            FieldDef("modified", "Last changed", "updated"),
            FieldDef("date", "Publish date", "dated"),
            FieldDef("site", "Site", "on"),
        ),
        presets=_presets(
            ("status", "title"),
            ("status", "title", "author", "modified"),
            ("status", "title", "author", "modified", "date", "site"),
        ),
        sample={
            "status": "Draft",
            "title": "Welcome post",
            "author": "Jeff",
            "modified": "yesterday",
            "date": "",
            "site": "Example Blog",
        },
    ),
    ListType(
        id="wordpress_comments",
        title="WordPress comments",
        family="wordpress_comments",
        fields=(
            FieldDef("author", "Author", "from"),
            FieldDef("status", "Status"),
            FieldDef("on", "Post it is on", "on"),
            FieldDef("when", "When", "sent"),
            FieldDef("excerpt", "Start of the comment"),
            FieldDef("site", "Site", "at"),
        ),
        presets=_presets(
            ("author", "status"),
            ("author", "status", "on", "when"),
            ("author", "status", "on", "when", "excerpt", "site"),
        ),
        sample={
            "author": "Pat",
            "status": "Pending",
            "on": "Welcome post",
            "when": "yesterday",
            "excerpt": "Thanks for the clear walkthrough",
            "site": "Example Blog",
        },
    ),
    ListType(
        id="wordpress_media",
        title="WordPress media",
        family="wordpress_media",
        fields=(
            FieldDef("title", "Title"),
            FieldDef("type", "Kind of file"),
            FieldDef("alt_text", "Alt text", "alt text"),
            FieldDef("uploaded", "When it was uploaded", "uploaded"),
        ),
        presets=_presets(
            ("title", "type"),
            ("title", "type", "alt_text"),
            ("title", "type", "alt_text", "uploaded"),
        ),
        sample={
            "title": "Team photo",
            "type": "picture",
            "alt_text": "none",
            "uploaded": "yesterday",
        },
    ),
    ListType(
        id="wordpress_users",
        title="WordPress users",
        family="wordpress_users",
        fields=(
            FieldDef("name", "Name"),
            FieldDef("username", "Username", "username"),
            FieldDef("role", "Role"),
            FieldDef("email", "Email address", "email"),
        ),
        presets=_presets(
            ("name", "role"),
            ("name", "username", "role"),
            ("name", "username", "role", "email"),
        ),
        sample={
            "name": "Pat Lee",
            "username": "patlee",
            "role": "Editor",
            "email": "pat@example.com",
        },
    ),
)

_BY_ID = {t.id: t for t in LIST_TYPES}


def get_list_type(list_type_id: str) -> ListType | None:
    """The list type with this id, or None for an id this build does not know."""
    return _BY_ID.get(list_type_id)


def list_type_ids() -> tuple[str, ...]:
    return tuple(t.id for t in LIST_TYPES)
