"""Appendix C of the GitHub PRD: every object, its Properties sheet, and its filters.

One :class:`~quill.core.github.appendix_map.ObjectEntry` per object, in the
PRD's order. Each names the sheet kinds it opens, the action table's row
types that stand for it in a list, and every filter Appendix C promises:
answered here over the loaded rows (:mod:`quill.core.github.object_filters`),
sent to GitHub's search, or not yet, with why. The gate checks every sheet
kind, row type and qualifier against the code, that every sheet and every
row type is claimed, and the generated table in the PRD is written from here.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.appendix_map import HERE, NOT_YET, SEARCH, Filter, ObjectEntry
from quill.core.github.filter_builder import ATTRIBUTES

__all__ = ["APPENDIX_C", "NOT_OBJECTS", "SEARCH_NODES"]

_ROWS = "its list's rows do not carry it yet; its Properties sheet shows it"
_NO_LIST = "there is no list of these to filter yet"


def _h(words: str, key: str) -> Filter:
    return Filter(words, key, HERE)


def _s(words: str, key: str) -> Filter:
    return Filter(words, key, SEARCH)


def _n(words: str, why: str = _ROWS) -> Filter:
    return Filter(words, "", NOT_YET, why)


_NAME = _h("name", "name")
_UPDATED = _h("updated", "updated")
_REPO = _h("repository", "repo")

#: Section 17.3: every attribute GitHub's issue and pull request search takes.
_ISSUE_SEARCH = tuple(_s(a.label.lower(), a.key) for a in ATTRIBUTES if not a.local)

#: The search node whose GitHub syntax answers an entry's ``search`` filters, by object.
SEARCH_NODES: dict[str, str] = {
    "Repository": "search_repositories",
    "Commit": "search_commits",
    "Issue": "items:issues",
    "Pull request": "items:issues",
    "Person": "search_people",
}

APPENDIX_C: tuple[ObjectEntry, ...] = (
    ObjectEntry("Repository", ("repository",), ("repository",), (
        _h("owner", "owner"), _NAME, _UPDATED,
        _s("topic", "topic"), _s("language", "language"), _s("visibility", "is"),
        _s("fork or source", "fork"), _s("archived", "archived"), _s("template", "template"),
        _s("stars", "stars"), _s("forks", "forks"), _s("size", "size"),
        _s("license", "license"), _s("created", "created"), _s("pushed", "pushed"),
        _n("open issues"), _n("has issues, has wiki, has discussions, has Pages"),
        _n("your role"), _n("custom properties"),
    )),
    ObjectEntry("Branch", ("branch",), ("branch",), (
        _h("name pattern", "name"), _h("protected", "protected"),
        _h("ahead of the default branch", "ahead"), _h("behind the default branch", "behind"),
        _h("last commit date", "committed"), _h("last commit author", "author"),
        _n("has an open pull request"), _n("merged"),
    )),
    ObjectEntry("Tag", ("tag",), ("tag",), (
        _h("name pattern", "name"), _h("commit", "sha"),
        _n("date"), _n("has release"), _n("annotated"),
    )),
    ObjectEntry("Commit", ("commit",), ("commit",), (
        _h("author", "author"), _h("date", "committed"), _h("message text", "message"),
        _h("commit", "sha"),
        _s("committer", "committer"), _s("author date", "author-date"),
        _s("committer date", "committer-date"), _s("merge commits", "merge"),
        _n("path"), _n("branch"), _n("verified signature"), _n("check state"),
    )),
    ObjectEntry("File and folder", ("file",), ("file", "folder"), (
        _NAME, _n("extension"), _n("path"), _n("size"), _n("last changed"),
    )),
    ObjectEntry("Ruleset and branch protection rule", ("ruleset", "branch_protection"), (), (
        _n("target", _NO_LIST), _n("enforcement", _NO_LIST), _n("rule kind", _NO_LIST),
        _n("bypass actor", _NO_LIST),
    ), home="The Repository sheet's Branches and Rules page; Across Repositories > Rules "
        "and Branch Protection"),
    ObjectEntry("Issue", ("issue",), ("issue",), _ISSUE_SEARCH),
    ObjectEntry("Pull request", ("pull_request",), ("pull_request",), (
        *_ISSUE_SEARCH, _h("has conflicts", "conflicts"),
        _n("files changed, lines added and removed"), _n("auto-merge on"),
    )),
    ObjectEntry("Comment", ("comment",), (), (
        _n("author", _NO_LIST), _n("date", _NO_LIST), _n("edited", _NO_LIST),
        _n("hidden", _NO_LIST), _n("reactions", _NO_LIST), _n("mentions me", _NO_LIST),
    ), home="Inside a conversation: Read as Document..., Review..., Open Discussion Thread"),
    ObjectEntry("Review and review thread", (), (), (
        _n("reviewer", _NO_LIST), _n("state", _NO_LIST), _n("resolved", _NO_LIST),
        _n("outdated", _NO_LIST), _n("file", _NO_LIST),
    ), home="Review... on a pull request: its threads, Next Unresolved, Reply, Resolve",
        reason="No Properties sheet of its own yet; the review window shows each thread's "
        "file, line, state and comments."),
    ObjectEntry("Discussion", ("discussion",), ("discussion",), (
        _NAME, _UPDATED, _n("category"), _n("answered"), _n("author"), _n("label"),
        _n("state"), _n("created"), _n("comments"), _n("upvotes"),
    )),
    ObjectEntry("Discussion category", (), ("discussion_category",), (_NAME, _n("format")),
                home="Repository > Discussions > Categories, read only",
                reason="GitHub manages categories on the web only, so there is nothing to "
                "change and no sheet; Find Discussions in Category lists its discussions."),
    ObjectEntry("Label", ("label",), ("label",), (
        _NAME, _n("colour"), _n("has description"), _n("in use count"),
    )),
    ObjectEntry("Milestone", ("milestone",), ("milestone",), (
        _NAME, _n("state"), _n("due date"), _n("overdue"), _n("has due date"),
        _n("progress percentage"),
    )),
    ObjectEntry("Issue type", ("issue_type",), ("resource",), (_NAME, _n("enabled"))),
    ObjectEntry("Issue form, Markdown template, pull request template, discussion form", (),
                ("template",), (
        _NAME, _REPO, _n("kind"), _n("labels applied"), _n("field count"),
        _n("has required fields"), _n("inherited"),
    ), home="Repository > Templates: Open Template... opens its sheet in the template builder",
        reason="Its sheet is the template builder's (section 21), with a field builder and "
        "preview, not one of the Properties catalogue's."),
    ObjectEntry("Project", ("project",), ("project",), (
        _h("owner", "owner"), _UPDATED, _NAME, _n("open or closed"), _n("template"),
        _n("linked repository"),
    )),
    ObjectEntry("Project item", (), (), (
        _n("every project field, and GitHub's project filter syntax",
           "Items in a View... reads a view with its own saved filter; the item list has none"),
    ), home="The Project sheet's Items page; Items in a View... on a project",
        reason="An item's sheet is built from its project's fields when it opens "
        "(project_item_sheet), so it has no fixed kind."),
    ObjectEntry("Project field and view", (), (), (), home="The Project sheet's Fields and "
                "Views pages; New Field..., New View..., Rename and Delete on a project",
                reason="Fields and views are pages of the Project sheet."),
    ObjectEntry("Workflow", ("workflow",), ("workflow",), (
        _NAME, _h("state", "state"), _h("path", "path"), _n("last run state"),
    )),
    ObjectEntry("Workflow run", ("run",), ("run",), (
        _h("workflow", "workflow"), _h("branch", "branch"), _h("event", "event"),
        _h("status", "status"), _h("conclusion", "conclusion"), _h("created", "created"),
        _h("head commit", "sha"), _n("actor"), _n("duration"),
    )),
    ObjectEntry("Job", ("job",), (), (
        _n("status", _NO_LIST), _n("conclusion", _NO_LIST), _n("runner name", _NO_LIST),
    ), home="Jobs and Logs on a run lists its jobs"),
    ObjectEntry("Artifact and Actions cache", ("artifact", "cache"), ("cache", "resource"), (
        _NAME, _UPDATED, _n("size"), _n("created"), _n("expires"), _n("branch"),
        _n("key, ref, last used (caches)"),
    )),
    ObjectEntry("Environment", ("environment",), ("environment",), (
        _NAME, _n("has protection"),
    )),
    ObjectEntry("Deployment", ("deployment",), ("deployment",), (
        _h("date", "updated"), _n("environment"), _n("ref"), _n("creator"), _n("state"),
    )),
    ObjectEntry("Runner and runner group", ("runner",), ("runner", "resource"), (
        _NAME, _n("status"), _n("busy"), _n("labels"), _n("OS"),
    )),
    ObjectEntry("Secret and variable", ("secret", "variable"), ("resource",), (
        _NAME, _UPDATED, _n("visibility"),
    )),
    ObjectEntry("Release", ("release",), ("release",), (
        _h("draft", "draft"), _h("prerelease", "prerelease"), _h("date", "created"),
        _h("tag pattern", "tag"), _h("title", "name"), _n("latest"), _n("author"),
    )),
    ObjectEntry("Release asset", ("release_asset",), ("release_asset",), (
        _NAME, _h("size", "size"), _h("downloads", "downloads"),
        _h("content type", "type"),
    )),
    ObjectEntry("Package", ("package",), ("package",), (
        _NAME, _REPO, _UPDATED, _n("type"), _n("visibility"), _n("version tag"),
    )),
    ObjectEntry("Person", ("person",), ("person",), (
        _NAME, _s("location", "location"), _s("followers", "followers"),
        _s("repositories", "repos"), _s("type (user or organization)", "type"),
        _n("company"), _n("your relationship (following, follows you, blocked)"),
    )),
    ObjectEntry("Organization", ("organization",), ("organization",), (
        _NAME, _n("members' role", _NO_LIST), _n("members' two-factor", _NO_LIST),
        _n("membership public or private", _NO_LIST), _n("team", _NO_LIST),
    )),
    ObjectEntry("Team", ("team",), ("team",), (
        _NAME, _n("privacy"), _n("parent"), _n("member"), _n("repository"), _n("role"),
    )),
    ObjectEntry("Collaborator and invitation", ("collaborator", "invitation"),
                ("invitation", "person"), (
        _NAME, _REPO, _n("role"), _n("source"), _n("pending"),
    )),
    ObjectEntry("Gist", ("gist",), ("gist",), (
        _NAME, _UPDATED, _n("public or secret"), _n("starred"), _n("file name"),
        _n("language"),
    )),
    ObjectEntry("Codespace", ("codespace",), ("codespace",), (
        _REPO, _h("last used", "updated"), _NAME, _n("branch"), _n("state"), _n("machine"),
    )),
    ObjectEntry("Security alert", ("security_alert",), ("security_alert",), (
        _REPO, _UPDATED, _n("kind"), _n("severity"), _n("state"), _n("ecosystem"),
        _n("package"), _n("manifest"), _n("rule"), _n("tool"), _n("secret type"),
        _n("branch"), _n("created"), _n("fixed"),
    )),
    ObjectEntry("Security advisory and policy", (), ("advisory",), (
        _NAME, _n("state"), _n("severity"), _n("published"),
    ), home="Repository > Security > Advisories and Policy; each advisory's context menu",
        reason="No Properties sheet yet: Publish or Close, Request CVE, comments and the "
        "private fork are on the advisory's context menu."),
    ObjectEntry("Notification", ("notification",), ("notification",), (
        _REPO, _UPDATED, _NAME, _n("reason"), _n("type"), _n("unread"),
        _n("participating"), _n("saved"),
    )),
    ObjectEntry("Saved search, pin and favorite", (), ("saved_search", "favorite"), (_NAME,),
                home="Search > Saved Searches; Repositories > Pinned and Favorites",
                reason="A saved search is its query, run by Enter; Pin as Node, Unpin and "
                "Remove are on its context menu, so it needs no sheet."),
    ObjectEntry("Account", (), (), (), home="Account > Manage GitHub Accounts..., Workbench "
                "Level for This Account..., GitHub Permissions..., Change History..., GitHub "
                "API Rate Limit", reason="An account is QUILL's, not GitHub's: its pages are "
                "those windows."),
    ObjectEntry("Webhook (beyond Appendix C)", ("webhook",), ("webhook",), (_NAME,)),
    ObjectEntry("Deploy key (beyond Appendix C)", ("deploy_key",), ("deploy_key",), (_NAME,)),
)  # fmt: skip

#: The action table's row types that are not Appendix C objects, and why.
NOT_OBJECTS: dict[str, str] = {
    "node": "A tree node's own menu, not an object.",
    "result": "A line of a report or search answer; it opens what it names.",
    "help_topic": "A help topic in Help and Learning.",
    "admin_action": "A settings command listed as a row (Settings > General).",
    "watch": "A Workbench watch, QUILL's own; Edit Watch... changes it.",
    "pages_site": "A repository's GitHub Pages site; its settings are the Repository sheet's "
    "Pages page.",
    "key": "One of your SSH or GPG keys; Show Details and Delete Key.",
    "autolink": "A repository autolink; the Repository sheet's Autolinks page lists them.",
    "wiki": "A repository's wiki, cloned to edit.",
    "sponsorship": "A sponsorship of yours; Show Details and Cancel.",
    "sponsor_tier": "A sponsor tier; Sponsor at This Tier.",
    "discussion_section": "A heading in Discussions grouping its categories.",
    "across_item": "A row of an Across Repositories list: it opens its own object.",
    "across_status": "A repository's state in an Across Repositories list.",
    "repository_set": "A set of repositories Across Repositories works on, QUILL's own.",
    "by_name": "A label, milestone, topic or rule compared by name across repositories.",
    "fleet": "A repository's line in the Fleet list.",
}
