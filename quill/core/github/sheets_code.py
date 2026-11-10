"""Sheets for branches, tags, commits, files, rulesets and classic protection (Appendix C).

Phase 8's "branches and rules": a Branch sheet (rename, and the rules that
apply to it, read as a sentence), Tag and Commit sheets (immutable, so every
fact is read-only and the commit's comments are counted), a File sheet, the
Ruleset sheet with every rule and setting and its Summary page (section
18.3.1), and the same sheet shape for classic branch protection. GitHub
replaces a ruleset and a protection whole, so their saves go through
:func:`quill.core.github.rulesets.ruleset_body` and ``classic_body``.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.rulesets import (
    MERGE_METHODS,
    RULES,
    classic_as_rules,
    classic_body,
    rule_words,
    ruleset_body,
    ruleset_values,
    summary,
)
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, lst, obj, page, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["BRANCH", "BRANCH_PROTECTION", "COMMIT", "FILE", "RULESET", "TAG"]

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


# ---------------------------------------------------------------------------
# Rulesets (18.3.1)
# ---------------------------------------------------------------------------

_RULE_WORDS = tuple(words for _key, words in RULES)


def _ruleset(data: Mapping[str, Any]) -> dict[str, Value]:
    return {k: v for k, v in ruleset_values(data).items() if isinstance(v, (str, int, bool, tuple))}


def _compose_ruleset(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    body = ruleset_body(raw, dict(edits))
    return [("PUT", f"/repos/{ident['repo']}/rulesets/{ident['id']}", body)]


_RULES_FIELDS = (
    ed(
        "rules",
        "Rules",
        _K.CHECKLIST,
        "Each rule GitHub offers, checked when it is on.",
        choices=_RULE_WORDS,
    ),
    ed("approvals", "Approvals needed", _K.NUMBER, "For Require a pull request."),
    ed("dismiss_stale", "Dismiss stale approvals on new pushes", _K.CHECK),
    ed("code_owners", "Require a code owner's review", _K.CHECK),
    ed("last_push", "Require approval of the most recent push", _K.CHECK),
    ed("resolve_threads", "Require conversations to be resolved", _K.CHECK),
    ed("merge_methods", "Allowed merge methods", _K.CHECKLIST, choices=MERGE_METHODS),
    ed("status_checks", "Required status checks", _K.LIST, "Check names, comma-separated."),
    ed("strict", "Branch must be up to date", _K.CHECK),
)

RULESET = SheetDef(
    "ruleset",
    SheetSpec(
        "ruleset",
        "Ruleset",
        (
            page(
                "general",
                "General",
                ed("name", "Name"),
                ed(
                    "enforcement",
                    "Enforcement",
                    _K.CHOICE,
                    "Active blocks; evaluate only "
                    "reports what it would block; disabled does nothing.",
                    choices=("active", "evaluate", "disabled"),
                ),
                ro("target", "Applies to"),
            ),
            page(
                "target",
                "Target",
                ed(
                    "include",
                    "Include",
                    _K.LIST,
                    "Branch or tag patterns; ~DEFAULT_BRANCH is "
                    "the default branch and ~ALL is all of them.",
                ),
                ed("exclude", "Exclude", _K.LIST),
            ),
            page(
                "bypass",
                "Bypass",
                ro(
                    "bypass",
                    "May bypass",
                    _K.TABLE,
                    "Roles, teams and apps that may bypass it, always or for pull requests.",
                ),
            ),
            page("rules", "Rules", *_RULES_FIELDS),
            page(
                "summary",
                "Summary",
                ro("summary", "In plain words", _K.MULTILINE, "The whole ruleset as sentences."),
            ),
            page(
                "history",
                "History",
                ro(
                    "history_note",
                    "Rule insights",
                    help="Which pushes it blocked or would have: Open on GitHub.",
                ),
            ),
        ),
    ),
    (Read("/repos/{repo}/rulesets/{id}", _ruleset),),
    {
        key: Write("/repos/{repo}/rulesets/{id}", "repo:admin", _A, "PUT", "put")
        for key in (
            "name",
            "enforcement",
            "include",
            "exclude",
            "rules",
            "approvals",
            "dismiss_stale",
            "code_owners",
            "last_push",
            "resolve_threads",
            "merge_methods",
            "status_checks",
            "strict",
        )
    },
    title=lambda ident: f"Ruleset {ident.get('name') or ident['id']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/rules/{ident['id']}",
    compose=_compose_ruleset,
    adopt=("raw_json",),
)


def _protection(data: Mapping[str, Any]) -> dict[str, Value]:
    reviews = data.get("required_pull_request_reviews")
    checks = data.get("required_status_checks")

    def on(key: str) -> bool:
        found = data.get(key)
        return bool(found.get("enabled")) if isinstance(found, Mapping) else bool(found)

    return {
        "approvals": int(reviews.get("required_approving_review_count") or 0)
        if isinstance(reviews, Mapping)
        else 0,
        "status_checks": tuple(str(c) for c in (checks or {}).get("contexts") or ())
        if isinstance(checks, Mapping)
        else (),
        "enforce_admins": on("enforce_admins"),
        "linear_history": on("required_linear_history"),
        "allow_force_pushes": on("allow_force_pushes"),
        "allow_deletions": on("allow_deletions"),
        "resolve_threads": on("required_conversation_resolution"),
        "raw_json": json.dumps(dict(data)),
    }


def _protection_summary(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"summary": summary(classic_as_rules(data, "this branch"))}


def _compose_protection(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    body = classic_body(raw, dict(edits))
    return [("PUT", f"/repos/{ident['repo']}/branches/{ident['branch']}/protection", body)]


BRANCH_PROTECTION = SheetDef(
    "branch_protection",
    SheetSpec(
        "branch_protection",
        "Branch Protection",
        (
            page(
                "general",
                "General",
                ed(
                    "approvals",
                    "Approvals needed",
                    _K.NUMBER,
                    "0 turns off Require a pull request.",
                ),
                ed("status_checks", "Required status checks", _K.LIST),
                ed("enforce_admins", "Include administrators", _K.CHECK),
                ed("linear_history", "Require linear history", _K.CHECK),
                ed("allow_force_pushes", "Allow force pushes", _K.CHECK),
                ed("allow_deletions", "Allow deletion", _K.CHECK),
                ed("resolve_threads", "Require conversations to be resolved", _K.CHECK),
            ),
            page("summary", "Summary", ro("summary", "In plain words", _K.MULTILINE)),
        ),
    ),
    (
        Read("/repos/{repo}/branches/{branch}/protection", _protection),
        Read("/repos/{repo}/branches/{branch}/protection", _protection_summary),
    ),
    {
        key: Write(
            "/repos/{repo}/branches/{branch}/protection",
            "repo:admin",
            _D if key in ("allow_force_pushes", "allow_deletions") else _A,
            "PUT",
            "put",
        )
        for key in (
            "approvals",
            "status_checks",
            "enforce_admins",
            "linear_history",
            "allow_force_pushes",
            "allow_deletions",
            "resolve_threads",
        )
    },
    title=lambda ident: f"Protection of {ident['branch']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/settings/branches",
    compose=_compose_protection,
    adopt=("raw_json",),
)
