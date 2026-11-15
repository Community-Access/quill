"""F1's words for the Across Repositories nodes (PRD 22.11, GX16).

Split from :mod:`quill.core.github.workbench_help_text` (GATE-11), whose
``NODE_HELP`` merges :data:`ACROSS_NODE_HELP`, so the help gate and the F1
reference read these like every other node.

wx-free.
"""

from __future__ import annotations

__all__ = ["ACROSS_NODE_HELP"]

ACROSS_NODE_HELP: dict[str, str] = {
    ":across": (
        "Across Repositories: the Repository Set in use, and under it its named sets, "
        "one kind of thing from every repository in the set, each name across the set, "
        "and the Fleet. Ctrl+N here edits the set's repositories."
    ),
    ":across_sets": (
        "Repository Sets: your named lists of repositories, each chosen from a checklist, "
        "made by a filter such as org:name topic:x, or every repository you can reach. "
        "Enter uses one; Ctrl+N makes one; Delete forgets one after asking. They stay on "
        "this computer."
    ),
    ":across_issues": (
        "Issues and Pull Requests, open, from every repository in the set, each row "
        "starting with its repository. Enter opens one in its repository; ] and [ move "
        "between repositories; type: and field: filters use issue types and fields."
    ),
    ":across_releases": (
        "Releases from every repository in the set: the latest release of each, or every "
        "release from the row's menu."
    ),
    ":across_runs": "Workflow Runs from every repository in the set, newest first.",
    ":across_commits": "Commits on the default branch of every repository in the set.",
    ":across_tags": "Tags from every repository in the set.",
    ":across_milestones": "Milestones from every repository in the set.",
    ":across_discussions": "Discussions from every repository in the set that has them on.",
    ":across_alerts": "Security alerts from every repository in the set you may read them in.",
    ":across_by_labels": (
        "Labels by Name: each label name across the set, where its colour and description "
        "differ and where it is missing. Make the copies the same, add it where missing, "
        "rename, merge or delete it everywhere, each with a preview and a result per "
        "repository."
    ),
    ":across_by_milestones": (
        "Milestones by Name: each milestone title across the set, its due dates, "
        "descriptions and progress. Make them the same, close them everywhere, move their "
        "open work to another milestone or add the missing ones, each with a preview and a "
        "result per repository."
    ),
    ":across_by_topics": (
        "Topics by Name: each topic across the set and the repositories that lack it. "
        "Add it to the missing or remove it everywhere, with a preview and a result per "
        "repository; each repository's other topics are kept."
    ),
    ":across_by_rules": (
        "Rules and Branch Protection: each ruleset by name, and each default branch's "
        "protection, compared across the set. Make them the same as the winner, add a "
        "ruleset where it is missing, or promote one to an organization ruleset; each needs "
        "admin access and shows a preview first."
    ),
    ":across_fleet": (
        "Fleet: one line per repository in the set: the exact revision of its default "
        "branch, checks, open pull requests, latest release and alerts, and when it was "
        "read. A repository that could not be read keeps its line, with the reason."
    ),
}
