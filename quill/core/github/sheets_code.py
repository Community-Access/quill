"""Sheets for branches, tags, commits and files (Appendix C).

Phase 8's "branches and rules": a Branch sheet (rename, and the rules that
apply to it, read as a sentence), Tag and Commit sheets (immutable, so every
fact is read-only and the commit's comments are counted) and a File sheet.
The Ruleset sheets and classic branch protection are in
:mod:`quill.core.github.sheets_rules`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.rulesets import rule_words
from quill.core.github.sheet_engine import Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, obj, page, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["BRANCH", "COMMIT", "FILE", "TAG"]

_A, _D = WriteTier.ACCESS, WriteTier.DESTRUCTIVE
_K = FieldKind


def _branch(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "sha": str(dig(data, "commit", "sha") or ""),
        "message": str(dig(data, "commit", "commit", "message") or "").split("\n", 1)[0],
        "author": str(dig(data, "commit", "commit", "author", "name") or ""),
        "date": when(dig(data, "commit", "commit", "author", "date")),
        "protected": bool(data.get("protected")),
        "url": str(dig(data, "_links", "html") or ""),
    }


def _branch_rules(data: Mapping[str, Any]) -> dict[str, Value]:
    rules = lst(data, "items")
    words = [rule_words(rule) for rule in rules if isinstance(rule, Mapping)]
    return {"rules_here": "; ".join(words) + "." if words else "No rules apply to it."}


BRANCH = SheetDef(
    "branch",
    SheetSpec(
        "branch",
        "Branch",
        (
            page(
                "general",
                "General",
                ed(
                    "name", "Name", help="Renaming moves open pull requests and protection with it."
                ),
                ro("sha", "Last commit"),
                ro("message", "Last commit message"),
                ro("author", "Last commit author"),
                ro("date", "Last commit date", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "protection",
                "Protection",
                ro("protected", "Protected", _K.CHECK),
                ro(
                    "rules_here",
                    "Rules that apply",
                    _K.MULTILINE,
                    "Every ruleset and "
                    "protection rule on this branch, as sentences. Each ruleset's own sheet "
                    "changes it.",
                ),
            ),
            page(
                "commits",
                "Commits",
                ro(
                    "commits_note",
                    "Commits",
                    help="Enter on the branch lists its commits; "
                    "Compare Branches compares it with another.",
                ),
            ),
        ),
    ),
    (
        Read("/repos/{repo}/branches/{branch}", _branch),
        Read(
            "/repos/{repo}/rules/branches/{branch}",
            _branch_rules,
            optional=True,
            fallback={"rules_here": "GitHub did not say which rules apply."},
        ),
    ),
    {
        "name": Write(
            "/repos/{repo}/branches/{branch}/rename", "repo:write", _A, "POST", "post", "new_name"
        ),
    },
    title=lambda ident: f"Branch {ident['branch']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/tree/{ident['branch']}",
    renames=("name", "branch"),
)


def _tag(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("ref") or "").removeprefix("refs/tags/"),
        "sha": str(dig(data, "object", "sha") or ""),
        "annotated": dig(data, "object", "type") == "tag",
    }


TAG = SheetDef(
    "tag",
    SheetSpec(
        "tag",
        "Tag",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("annotated", "Annotated", _K.CHECK),
                ro(
                    "sha", "Points at", help="Tags cannot be changed; protection lives in rulesets."
                ),
            ),
            page(
                "commit",
                "Commit",
                ro("commit_note", "Commit", help="Enter on the tag opens the commit it points at."),
            ),
            page(
                "release",
                "Release",
                ro(
                    "release_note",
                    "Release",
                    help="Create a release from it with Create Release on its context menu.",
                ),
            ),
        ),
    ),
    (Read("/repos/{repo}/git/ref/tags/{tag}", _tag),),
    title=lambda ident: f"Tag {ident['tag']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/releases/tag/{ident['tag']}",
)


def _commit(data: Mapping[str, Any]) -> dict[str, Value]:
    stats = obj(data, "stats")
    files = lst(data, "files")
    return {
        "sha": str(data.get("sha") or ""),
        "message": str(dig(data, "commit", "message") or ""),
        "author": str(dig(data, "commit", "author", "name") or ""),
        "committer": str(dig(data, "commit", "committer", "name") or ""),
        "date": when(dig(data, "commit", "author", "date")),
        "verified": bool(dig(data, "commit", "verification", "verified")),
        "comments": int(dig(data, "commit", "comment_count") or 0),
        "additions": int(stats.get("additions") or 0),
        "deletions": int(stats.get("deletions") or 0),
        "files": tuple(
            f"{row.get('filename', '')}, {row.get('status', '')}"
            for row in files
            if isinstance(row, Mapping)
        ),
        "url": str(data.get("html_url") or ""),
    }


def _checks(data: Mapping[str, Any]) -> dict[str, Value]:
    runs = lst(data, "check_runs")
    return {
        "checks": tuple(
            f"{run.get('name', '')}, {run.get('conclusion') or run.get('status') or ''}"
            for run in runs
            if isinstance(run, Mapping)
        )
    }


COMMIT = SheetDef(
    "commit",
    SheetSpec(
        "commit",
        "Commit",
        (
            page(
                "general",
                "General",
                ro("sha", "Commit"),
                ro("message", "Message", _K.MULTILINE),
                ro("author", "Author"),
                ro("committer", "Committer"),
                ro("date", "Date", _K.DATE),
                ro("verified", "Verified signature", _K.CHECK),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "files",
                "Files",
                ro("files", "Files changed", _K.TABLE),
                ro("additions", "Lines added", _K.NUMBER),
                ro("deletions", "Lines removed", _K.NUMBER),
            ),
            page("checks", "Checks", ro("checks", "Checks", _K.TABLE)),
            page(
                "comments",
                "Comments",
                ro(
                    "comments",
                    "Comments",
                    _K.NUMBER,
                    "Commit Comments on its context menu reads them.",
                ),
            ),
            page(
                "branches",
                "Branches and Tags",
                ro(
                    "branches_note",
                    "Where it is",
                    help="Compare Branches shows whether a branch contains it.",
                ),
            ),
        ),
    ),
    (
        Read("/repos/{repo}/commits/{sha}", _commit),
        Read("/repos/{repo}/commits/{sha}/check-runs", _checks, optional=True),
    ),
    title=lambda ident: f"Commit {ident['sha'][:7]}",
    url=lambda ident: f"https://github.com/{ident['repo']}/commit/{ident['sha']}",
)


def _file(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "path": str(data.get("path") or ""),
        "size": f"{int(data.get('size') or 0)} bytes",
        "sha": str(data.get("sha") or ""),
        "url": str(data.get("html_url") or ""),
    }


FILE = SheetDef(
    "file",
    SheetSpec(
        "file",
        "File",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("path", "Path"),
                ro("size", "Size"),
                ro("sha", "Blob"),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "history",
                "History",
                ro(
                    "history_note",
                    "History",
                    help="History on the context menu lists the commits that changed it.",
                ),
            ),
            page(
                "owners",
                "Code Owners",
                ro(
                    "owners_note",
                    "Code owners",
                    help="Who owns it is in the repository's CODEOWNERS file.",
                ),
            ),
        ),
    ),
    (Read("/repos/{repo}/contents/{path}", _file),),
    title=lambda ident: ident["path"].rsplit("/", 1)[-1],
    url=lambda ident: f"https://github.com/{ident['repo']}/blob/HEAD/{ident['path']}",
)
