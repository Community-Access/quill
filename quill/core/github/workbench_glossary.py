"""The GitHub Workbench's glossary, tasks, key families and guide chapters.

Pure data behind :mod:`quill.core.github.workbench_help` (split out for
GATE-11): the Words node and Alt+F1 (D6), Do Something (D12), the Keys node
(Part C) and the chapter Ctrl+F1 opens.
"""

from __future__ import annotations

__all__ = ["GLOSSARY", "GUIDE_CHAPTERS", "KEY_FAMILIES", "ROW_TYPE_WORDS", "TASKS", "WHAT_CHANGED"]

#: Term -> its plain explanation, with where you meet it in the Workbench.
GLOSSARY: dict[str, str] = {
    "Repository": (
        "A project's folder on GitHub: its files, their history, and its issues and "
        "pull requests. Under Repositories in the tree."
    ),
    "Issue": (
        "A note about a bug, an idea or a task, with a conversation under it. Under "
        "a repository's Issues."
    ),
    "Pull request": (
        "A proposed change: commits on one branch that somebody asks to merge into "
        "another, with a review. Under a repository's Pull Requests."
    ),
    "Branch": (
        "A line of work: a name that follows the newest commit of one set of "
        "changes. Under Code, Branches."
    ),
    "Commit": "A saved change, with a message saying why. Under Code, Commits.",
    "Tag": "A name for one particular commit, usually a version number. Under Code, Tags.",
    "Release": (
        "A published version, with notes and files to download. Under a repository's Releases."
    ),
    "Fork": (
        "Your own copy of somebody else's repository, from which you can propose "
        "changes back. Under People, Forks."
    ),
    "Upstream": "The repository a fork was copied from. Under Code, Upstream, on a fork.",
    "Merge": (
        "Bringing a pull request's changes into the branch it targets. Item, "
        "Merge, Ctrl+Shift+Enter."
    ),
    "Squash": "Merging a pull request as one single commit, instead of all of its commits.",
    "Rebase": (
        "Replaying commits on top of another branch, so the history reads as one straight line."
    ),
    "Review": (
        "Reading a pull request's changes and approving them, asking for changes, "
        "or commenting. Enter on a pull request."
    ),
    "Draft": "A pull request that is not ready for review yet.",
    "Label": "A coloured tag on issues and pull requests, such as bug. Under Labels.",
    "Milestone": "A goal with a due date that issues and pull requests belong to.",
    "Assignee": "The person an issue or pull request is given to.",
    "Mention": "Your login written with an at sign, such as @you, which notifies you.",
    "Notification": (
        "GitHub telling you something happened on a thread you are part of. Under "
        "Needs My Attention."
    ),
    "Inbox": (
        "The Workbench's one list of what needs you, made from notifications, "
        "review requests, assignments and mentions."
    ),
    "Actions": "GitHub's automation: workflows that run on events, such as a push.",
    "Workflow": "One automation, defined in a file in the repository. Under Actions, Workflows.",
    "Run": "One time a workflow ran, with its jobs, steps and logs. Under Actions, Runs.",
    "Job": "One part of a run, on one machine, made of steps.",
    "Artifact": "A file a run produced and kept, to download.",
    "Cache": "Files Actions keeps between runs to make them faster. Under Actions, Caches.",
    "Workflow dispatch": "Starting a workflow by hand, on a branch you choose.",
    "Check": "A test or other run that reports passing or failing on a commit.",
    "Deployment": "Code sent to an environment, such as a website.",
    "Environment": "A named place code is deployed to, with its own rules and secrets.",
    "Secret": "A value, such as a password, that workflows use and GitHub never shows.",
    "Variable": "A value workflows use that is not secret.",
    "Branch protection": "Rules that decide who may change a branch and what a change needs.",
    "Ruleset": "A newer, named set of branch and tag rules that can cover many branches.",
    "Collaborator": "Somebody given access to one repository.",
    "Team": "A group of people in an organization, given access together.",
    "Organization": "An account many people share, which owns repositories and teams.",
    "Role": "What somebody may do: read, triage, write, maintain or admin.",
    "Triage": "The role that may label, assign and close issues, but not push code.",
    "Star": "A bookmark on a repository, which also shows you like it.",
    "Watch": "Asking GitHub to tell you about a repository's activity.",
    "Gist": "A small shared file or snippet, with its own history.",
    "Discussion": "A conversation in a repository that is not an issue.",
    "Project": "A board or table for planning issues and pull requests.",
    "Codespace": "A computer in the cloud with the repository ready to work on. It can cost money.",
    "Security alert": "A warning that code, a dependency or a secret in it is at risk.",
    "Rate limit": (
        "How many requests GitHub allows an account each hour. Account, GitHub API "
        "Rate Limit, Ctrl+Shift+L."
    ),
    "Saved search": "A search kept on this computer, to run again. Under Saved Searches.",
    "Favorite": "An item kept on this computer under Repositories, Favorites.",
    "Pin": "A repository kept on this computer under Repositories, Pinned.",
}

#: Each row type -> the glossary word Alt+F1 explains for it.
ROW_TYPE_WORDS: dict[str, str] = {
    "issue": "Issue",
    "pull_request": "Pull request",
    "mixed": "Issue",
    "run": "Run",
    "workflow": "Workflow",
    "release": "Release",
    "release_asset": "Artifact",
    "branch": "Branch",
    "commit": "Commit",
    "tag": "Tag",
    "notification": "Notification",
    "repository": "Repository",
    "person": "Mention",
    "label": "Label",
    "gist": "Gist",
    "discussion": "Discussion",
    "security_alert": "Security alert",
    "cache": "Cache",
    "saved_search": "Saved search",
    "file": "Repository",
    "folder": "Repository",
    "milestone": "Milestone",
    "project": "Project",
    "organization": "Organization",
    "favorite": "Favorite",
    "admin_action": "Branch protection",
    "help_topic": "Inbox",
    "result": "Repository",
    "event": "Notification",
    "deployment": "Deployment",
    "code": "Repository",
    "node": "Repository",
}

#: (id, title, steps, the node it takes you to as (template, key)).
TASKS: tuple[tuple[str, str, str, tuple[str, str]], ...] = (
    (
        "find_what_needs_me",
        "Find what needs me",
        "Press Ctrl+1 for Inbox. Arrow down the list; Enter opens a row; Delete marks "
        "it done. Notifications, review requests and mentions are the nodes below it.",
        ("", "inbox"),
    ),
    (
        "review_a_pull_request",
        "Review a pull request",
        "Press Ctrl+Shift+2 for this repository's Pull Requests, arrow to one, and "
        "press Enter to open its review. Ctrl+Shift+D lists the changed files.",
        ("repository", "pulls"),
    ),
    (
        "fix_a_failed_run",
        "Fix a failed run",
        "Press Ctrl+Shift+4 for Actions Runs, arrow to the failed run, and press "
        "Ctrl+Shift+W to hear what failed. Ctrl+Shift+F5 runs the failed jobs again.",
        ("repository", "runs"),
    ),
    (
        "file_an_issue",
        "File an issue",
        "Press Ctrl+Shift+1 for Issues, then Ctrl+N. Type a title, press Enter, then "
        "say what it is about.",
        ("repository", "issues"),
    ),
    (
        "comment_on_something",
        "Comment on an issue or pull request",
        "Select it in a list and press Ctrl+Shift+M. Type the comment and press Enter.",
        ("repository", "issues"),
    ),
    (
        "search_github",
        "Search GitHub",
        "Press Ctrl+3 for Search, choose Issues and Pull Requests, press Ctrl+E, type "
        "words or qualifiers such as is:open author:@me, and press Enter.",
        ("", "search_issues"),
    ),
    (
        "keep_a_search",
        "Keep a search to run again",
        "Run the search, then press Ctrl+N. It is under Saved Searches, Ctrl+8.",
        ("", "saved_searches"),
    ),
    (
        "open_another_repository",
        "Open another repository",
        "Press Ctrl+L and type owner/name or paste a GitHub link. It gets a node "
        "under Repositories.",
        ("", "repositories"),
    ),
    (
        "change_a_repository_setting",
        "Change a repository setting",
        "Press Ctrl+Shift+9 for Settings, then General or Branch Protection, and "
        "press Enter on the setting. Repository Actions, Ctrl+Shift+G, lists the rest.",
        ("repository", "settings"),
    ),
    (
        "choose_how_notifications_work",
        "Choose how notifications are checked",
        "Press Ctrl+Shift+O for Workbench Options and go to Notifications and Inbox.",
        ("", "notifications"),
    ),
)

KEY_FAMILIES: tuple[tuple[str, str], ...] = (
    (
        "Moving",
        "F6 and Shift+F6 move between the panes; Alt+Up goes to the parent node; "
        "Backspace or Alt+Left goes back, Alt+Right forward.",
    ),
    (
        "Places",
        "Ctrl+1 to Ctrl+0 go to the big places; Ctrl+Shift+1 to Ctrl+Shift+0 to "
        "the parts of the repository you are in.",
    ),
    (
        "Hearing",
        "Alt+1 to Alt+9 say something and move nothing: where you are, the "
        "selection, the item, the counts, your access, the rate limit, the "
        "filter, loading and your account. F9 says the last result again; "
        "Shift+F9 explains it.",
    ),
    (
        "Doing",
        "Enter does the obvious thing, Alt+Enter shows Properties, the "
        "Applications key lists the rest, Shift+F1 lists everything with its "
        "key, Delete removes safely and Ctrl+N makes something new here.",
    ),
    (
        "Finding",
        "Ctrl+E is the filter box, Ctrl+L opens a GitHub address, Ctrl+G goes "
        "to a number, and typing in the tree or a list jumps to a name.",
    ),
    (
        "Help",
        "F1 says what the focused thing is, Shift+F1 what you can do, Alt+F1 "
        "what a GitHub word means, Ctrl+F1 opens the guide here, and "
        "Ctrl+Shift+F1 searches all of help.",
    ),
)

#: (chapter number, title) of the GitHub Guide, in order.
GUIDE_CHAPTERS: tuple[tuple[str, str], ...] = (
    ("01", "Getting started"),
    ("02", "Getting around"),
    ("03", "Inbox and your work"),
    ("04", "Issues"),
    ("05", "Pull requests and review"),
    ("06", "Actions and checks"),
    ("07", "Code and repositories"),
    ("08", "Discussions and security"),
    ("09", "Codespaces and the command line"),
    ("10", "Troubleshooting"),
    ("11", "Keyboard reference"),
    ("12", "The GitHub Workbench, place by place"),
)

_CHAPTER_FOR: dict[str, str] = {
    ":start": "12",
    ":attention": "03",
    ":inbox": "03",
    ":notifications": "03",
    ":review_requests": "05",
    ":search": "02",
    ":help": "12",
    "repository:issues": "04",
    "repository:issues_and_pulls": "04",
    "repository:labels": "04",
    "repository:milestones": "04",
    "repository:pulls": "05",
    "repository:actions": "06",
    "repository:runs": "06",
    "repository:workflows": "06",
    "repository:caches": "06",
    "repository:discussions": "08",
    "repository:security": "08",
    "repository:alerts": "08",
    "repository:alerts_closed": "08",
}

WHAT_CHANGED: tuple[tuple[str, str], ...] = (
    (
        "One window for GitHub",
        "GitHub Items and Explore GitHub are now one window, the GitHub Workbench, with "
        "a tree of places. The classic windows are still there for one release: "
        "Workbench Options, Use the classic GitHub windows.",
    ),
    (
        "Menus with their keys",
        "Every row of the Workbench's menus shows its key, and a row that does not "
        "apply says why on its help line.",
    ),
    (
        "Keys you can guess",
        "Ctrl+number goes to a place, Ctrl+Shift+number to a part of the repository, "
        "and Alt+number says something without moving you.",
    ),
    (
        "Help everywhere",
        "F1, Shift+F1, Alt+F1, Ctrl+F1 and Ctrl+Shift+F1, and this Help and Learning "
        "branch of the tree.",
    ),
    (
        "Workbench Options",
        "GitHub's preferences moved out of the main Options into the Workbench's own "
        "Tools menu, Ctrl+Shift+O, and your choices came with them.",
    ),
)
