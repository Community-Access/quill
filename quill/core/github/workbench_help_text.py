"""The GitHub Workbench's help words for windows, nodes, options and results.

Pure data behind :mod:`quill.core.github.workbench_help` (split out for
GATE-11). Plain, short, what to do before why (Part D9); check, never tick.
"""

from __future__ import annotations

__all__ = [
    "CHOICE_WORDS",
    "NODE_HELP",
    "PREF_HELP",
    "PREF_PAGES",
    "RESULT_EXPLANATIONS",
    "SURFACE_PURPOSES",
]

#: Workbench Options' pages, in order (GitHub PRD 4.1).
PREF_PAGES: tuple[str, ...] = (
    "General",
    "Notifications and Inbox",
    "Lists",
    "Repositories",
    "Privacy",
)

#: Each preference: (its page, its label with an access key, what F1 says).
#: The generated reference prints them all, which is what GATE-SETDOC reads.
PREF_HELP: dict[str, tuple[str, str, str]] = {
    "open_on": (
        "General",
        "&Open the Workbench on:",
        "Where the window opens when no menu row asks for a place: Inbox (Start Here "
        "until you have signed in), Start Here, or wherever you were last time.",
    ),
    "list_mode": (
        "General",
        "&List shows:",
        "Quick lists show a few columns, fast to arrow through; Full lists show every "
        "column GitHub Items knows for that view.",
    ),
    "default_sort": (
        "General",
        "&Sort issues and pull requests by:",
        "The order a list of issues and pull requests opens in. Newest first is the usual choice.",
    ),
    "default_state": (
        "General",
        "Show issues that &are:",
        "Open, closed or all, when a list opens. The filter box can always say "
        "is:open or is:closed for one list.",
    ),
    "poll_interval_minutes": (
        "Notifications and Inbox",
        "Check for new notifications every (&minutes):",
        "How often GitHub is checked for new notifications, from 5 minutes to a day. "
        "GitHub may ask for longer, and then it gets longer.",
    ),
    "poll_audible_tick": (
        "Notifications and Inbox",
        "Play a soun&d on each check",
        "A short sound every time GitHub is checked, so silence means the check "
        "stopped rather than found nothing. Off by default.",
    ),
    "poll_interrupt_speech": (
        "Notifications and Inbox",
        "New notifications &interrupt speech",
        "Say a new notification at once, cutting across what is being said. Off "
        "means it waits its turn.",
    ),
    "include_read_notifications": (
        "Notifications and Inbox",
        "Include &read notifications",
        "Show notifications you have already read, as well as unread ones, in Notifications.",
    ),
    "speak_column_names": (
        "Lists",
        "Say column &names before values",
        "Put each column's name before its value in a list row, as in Number 42, "
        "Title Crash on start. Off keeps rows short.",
    ),
    "health_snapshot_opt_in": (
        "Privacy",
        "Load the repository &Health Snapshot",
        "Insights, Health Snapshot reads extra data from GitHub about a repository's "
        "activity. It loads only when this is checked.",
    ),
    "first_time_help": (
        "Privacy",
        "Show &First time here? help",
        "The first few times you visit a place, its details start with a short "
        "paragraph on what it is for.",
    ),
    "use_classic_windows": (
        "Privacy",
        "Use the &classic GitHub windows",
        "Open GitHub Items and Explore GitHub, as before the Workbench, from the "
        "editor's GitHub doors. Kept for one release, then retired.",
    ),
}

#: How each choice value reads in the dialog.
CHOICE_WORDS: dict[str, str] = {
    "inbox": "Inbox",
    "start": "Start Here",
    "last": "Where I was last time",
    "quick": "Quick (a few columns)",
    "full": "Full (every column)",
    "number_desc": "Number, newest first",
    "number_asc": "Number, oldest first",
    "title_asc": "Title, A to Z",
    "title_desc": "Title, Z to A",
    "updated_desc": "Last updated, newest first",
    "updated_asc": "Last updated, oldest first",
    "comments_desc": "Most comments first",
    "open": "Open",
    "closed": "Closed",
    "all": "All",
}

#: Explain That (Shift+F9, D13): the start of a result -> what it means and what next.
RESULT_EXPLANATIONS: tuple[tuple[str, str], ...] = (
    (
        "Comment posted",
        "Your comment is on GitHub now, and everyone watching the item is told. Enter "
        "on the item reads it with its comments; F5 loads the list again.",
    ),
    (
        "Created issue",
        "The issue is on GitHub now, open, with you as its author. It is at the top of "
        "Issues after F5; Alt+Enter on it shows everything about it.",
    ),
    (
        "Closed",
        "The item is closed on GitHub. Nothing was deleted: the same command reopens it, "
        "and its comments and history stay.",
    ),
    (
        "Reopened",
        "The item is open again on GitHub, as it was before it was closed.",
    ),
    (
        "Re-running",
        "GitHub is running the workflow again from the start, on the same commit. Its "
        "new run appears in Actions Runs; F5 refreshes the list.",
    ),
    (
        "Marked read",
        "GitHub now shows the notification as read. It stays in Notifications until it "
        "is marked done; Delete marks it done.",
    ),
    (
        "Marked done",
        "The notification left your inbox on GitHub. A new comment on the same thread "
        "brings it back.",
    ),
    (
        "Unsubscribed",
        "GitHub stops telling you about that thread, unless somebody mentions you in it.",
    ),
    (
        "Starred",
        "The repository is in your stars on GitHub, under Repositories, Starred.",
    ),
    (
        "Unstarred",
        "The repository left your stars. Nothing else about it changed.",
    ),
    (
        "Added to Favorites",
        "It is kept on this computer under Repositories, Favorites. GitHub is not told.",
    ),
    (
        "Removed from Favorites",
        "It is no longer under Repositories, Favorites. GitHub was never told either way.",
    ),
    (
        "Pinned",
        "The repository is kept on this computer under Repositories, Pinned.",
    ),
    (
        "Unpinned",
        "The repository is no longer under Repositories, Pinned.",
    ),
    (
        "Saved the search",
        "The search is kept on this computer under Search, Saved Searches (Ctrl+8). "
        "Enter on it runs it again.",
    ),
    (
        "Copied",
        "It is on the clipboard. Paste it anywhere with Ctrl+V.",
    ),
    (
        "Could not",
        "GitHub refused, or could not be reached. The words after Could not say why. F5 "
        "tries the view again, and Account, GitHub API Rate Limit (Ctrl+Shift+L) says "
        "whether you have used up your requests for now.",
    ),
    (
        "Sign in",
        "This needs a GitHub account. Account, Manage GitHub Accounts (Ctrl+Shift+K) "
        "adds one; reading public repositories works without one.",
    ),
)

#: Window title (or its start) -> what the window is for, said first by F1.
SURFACE_PURPOSES: dict[str, str] = {
    "GitHub Workbench": (
        "One window for GitHub. The tree on the left says where you are, the list "
        "says what is there, and the details say what the selected one is. F6 moves "
        "between them, Enter does the obvious thing, Shift+F1 lists everything you "
        "can do, and Alt+Enter shows everything about the selection."
    ),
    "Workbench Options": (
        "The GitHub Workbench's own preferences: where it opens, how lists start, "
        "how often notifications are checked, your pinned repositories and "
        "favorites, and privacy. OK saves, Cancel changes nothing."
    ),
    "What Can I Do Here": (
        "Every action for what is selected, in the order of its context menu, with "
        "its key. Enter runs the action; a greyed one says why it is greyed."
    ),
    "Search Help": (
        "Type a few words to find a help topic, a place, a command or a GitHub "
        "word. Enter goes there, runs it or reads it."
    ),
    "What Is This": "A GitHub word, explained in plain language, with where you meet it.",
    "GitHub Workbench Keys": "Every key in the GitHub Workbench, grouped by what it does.",
    "Artifacts": "The files a workflow run kept: download one or all of them.",
    "Discussion #": "One discussion thread: read it, and reply if you are signed in.",
    "New Discussion": "Start a discussion in the repository: a category, a title and what to say.",
    "Pending Deployments": "Deployments waiting on you: approve or reject each one.",
    "What Failed": "The failing steps of a run and their log lines, in one place.",
    "Jobs for": "A run's jobs and steps, with each job's log and annotations.",
    "GitHub Items": (
        "GitHub Items, the classic window: one repository's issues, pull requests, "
        "branches, commits, tags, releases and workflow runs."
    ),
    "Explore GitHub": (
        "Explore GitHub, the classic window: searches, your own work, people and "
        "repository administration."
    ),
}

#: Words that mark a classic GitHub window title as one of the family's own,
#: so the gate covers those windows' controls without asking every one of
#: twenty-seven older dialogs for a purpose line this change did not write.
_CLASSIC_WORDS = (
    "GitHub",
    "Pull Request",
    "Issue",
    "Release",
    "Workflow",
    "Branch",
    "Commit",
    "Gist",
    "Codespace",
    "Repository",
    "Milestone",
    "Project",
    "Notification",
    "Review",
    "Label",
    "Clone",
    "Compare",
    "Timeline",
    "Diff",
)

#: ``"<template>:<key>"`` -> what F1 says about the node (D3, layer 2).
NODE_HELP: dict[str, str] = {
    ":start": (
        "Start Here: what the Workbench is, whether you are signed in, and the five "
        "keys to learn first."
    ),
    ":attention": (
        "Needs My Attention: everything waiting on you, across GitHub. Inbox first, "
        "then notifications, review requests and your own open work."
    ),
    ":inbox": (
        "Inbox: one list of what needs you, from notifications, review requests, "
        "assignments and mentions. Enter opens a row; Delete marks it done."
    ),
    ":notifications": (
        "Notifications: what GitHub has told you about, unread first. Ctrl+Q marks "
        "one read, Delete marks it done, and Ctrl+Shift+Q marks the whole view read."
    ),
    ":review_requests": (
        "Review Requests: pull requests somebody asked you to review. Enter opens the review."
    ),
    ":assigned": "Assigned to Me: issues and pull requests assigned to you, anywhere.",
    ":mentions": "Mentions: issues and pull requests where somebody wrote your name.",
    ":my_pulls": "My Open Pull Requests: pull requests you opened that are still open.",
    ":my_issues": "My Open Issues: issues you opened that are still open.",
    ":my_activity": "My Activity Feed: what you did on GitHub lately, newest first.",
    ":repositories": (
        "Repositories: the one you are working in first, then pinned, favorites, "
        "yours, starred, watched and your organizations'. Enter on a repository "
        "opens its node."
    ),
    ":pinned": (
        "Pinned: repositories you keep at hand, on this computer. Delete takes one "
        "out; Ctrl+N pins the current repository."
    ),
    ":favorites": (
        "Favorites: issues, pull requests and other items you kept, on this "
        "computer. Ctrl+D adds or removes the selected row anywhere in the window."
    ),
    ":my_repositories": "My Repositories: the repositories your account owns or can push to.",
    ":starred": "Starred: repositories you starred on GitHub.",
    ":watched": "Watched: repositories whose activity GitHub tells you about.",
    ":organizations": (
        "Organizations: the organizations you belong to. Enter on one opens its repositories."
    ),
    ":search": (
        "Search: GitHub's searches. Choose one, type in the filter box with Ctrl+E, "
        "and press Enter."
    ),
    ":search_issues": (
        "Search Issues and Pull Requests: everything GitHub finds for the words and "
        "qualifiers in the filter box, such as is:open author:@me. Ctrl+N saves the "
        "search."
    ),
    ":search_code": "Search Code: files whose text matches the filter box. Needs sign-in.",
    ":search_commits": "Search Commits: commits whose message matches the filter box.",
    ":search_repositories": (
        "Search Repositories: repositories whose name or description matches the filter box."
    ),
    ":saved_searches": (
        "Saved Searches: searches you kept, on this computer. Enter runs one; Delete removes it."
    ),
    ":people": "People: who you follow, who follows you, and anybody you look up.",
    ":following": "People I Follow: accounts you follow. Enter opens a person's node.",
    ":followers": "My Followers: accounts that follow you.",
    ":find_person": (
        "Find a Person: type a login with Ctrl+L, and the person gets a node of their own here."
    ),
    ":gists": "Gists: small shared files and snippets.",
    ":my_gists": "My Gists: gists you made. Enter edits one.",
    ":projects": (
        "Projects: your Project boards. Each repository's own Projects are under it, Ctrl+Shift+7."
    ),
    ":watches": "Watches: tell me when something happens. Coming in a later release.",
    ":across": (
        "Across Repositories: every kind of thing, by name, everywhere. Coming in a later release."
    ),
    ":help": (
        "Help and Learning: the guide, the GitHub words, the keys, what changed, "
        "and tasks in plain words that take you to the place."
    ),
    ":help_tasks": (
        "Do Something: tasks in plain words. Enter reads one; Take Me There, on its "
        "context menu, goes to the place it is about."
    ),
    ":help_words": (
        "Words: the GitHub glossary. Type a word to jump to it; the details say "
        "what it means and where you meet it."
    ),
    ":help_keys": "Keys: every key in the Workbench, grouped by what it does.",
    ":help_guide": (
        "The Guide: the GitHub Workbench Guide's chapters. Ctrl+F1 opens the guide "
        "at the chapter for where you are."
    ),
    ":help_changes": "What Changed: what is new in the GitHub Workbench in this version.",
    ":help_ask": (
        "Ask a Person: write to support@community-access.org. Nothing is sent "
        "until you send it from your own email."
    ),
    "repository:repository": (
        "A repository: its issues, pull requests, actions, code, releases and "
        "settings, each a node below. Ctrl+Shift+1 to Ctrl+Shift+0 jump to them."
    ),
    "repository:overview": "Overview: the repository's README, description and community profile.",
    "repository:issues": (
        "Issues: this repository's open issues. Ctrl+N files a new one; Delete "
        "closes the selected one after asking."
    ),
    "repository:pulls": (
        "Pull Requests: this repository's open pull requests. Enter opens the "
        "review; Ctrl+Shift+D lists the changed files."
    ),
    "repository:issues_and_pulls": (
        "Issues and Pull Requests: both in one list, newest first, the way an inbox reads."
    ),
    "repository:discussions": "Discussions: the repository's conversations that are not issues.",
    "repository:actions": "Actions: the repository's workflow runs, workflows and caches.",
    "repository:runs": (
        "Runs: each time a workflow ran. Enter shows its jobs and logs; Ctrl+Shift+W "
        "says what failed; Ctrl+Shift+F5 re-runs the failed jobs."
    ),
    "repository:workflows": "Workflows: the automations defined in the repository.",
    "repository:caches": "Caches: files Actions kept between runs. Delete removes one.",
    "repository:code": "Code: files, branches, commits, tags, and the upstream of a fork.",
    "repository:files": (
        "Files: the repository's files on its default branch, a folder at a time. "
        "Enter opens a folder, or a file in the editor."
    ),
    "repository:branches": "Branches: lines of work. Enter lists a branch's commits.",
    "repository:commits": "Commits: saved changes, newest first.",
    "repository:tags": "Tags: names for particular commits, usually versions.",
    "repository:upstream": "Upstream: the repository this one was forked from. Forks only.",
    "repository:releases": "Releases: published versions and their files. Enter lists the files.",
    "repository:labels": "Labels: tags for issues and pull requests. Enter finds the issues.",
    "repository:milestones": (
        "Milestones: goals with a date. Enter lists the issues and pull requests in one."
    ),
    "repository:repo_projects": "Projects: this repository's Project boards.",
    "repository:activity": "Activity: what happened in the repository lately.",
    "repository:people": "People: contributors, forks, and who has access.",
    "repository:contributors": "Contributors and People: who has worked on the repository.",
    "repository:forks": "Forks: copies of this repository on other accounts.",
    "repository:access": "Collaborators and Team Access: who may do what here.",
    "repository:insights": "Insights: traffic, contributors and the community profile.",
    "repository:traffic": "Traffic and Contributors: views, clones and who contributes.",
    "repository:health": (
        "Health Snapshot: extra activity data, loaded only when you turn it on in "
        "Workbench Options."
    ),
    "repository:community": "Community Profile: the README, license and guidelines GitHub checks.",
    "repository:deployments": "Deployments and Environments: where the code was deployed.",
    "repository:pages": "GitHub Pages: the website built from this repository.",
    "repository:security": "Security: alerts about vulnerable code and leaked secrets.",
    "repository:alerts": "Alerts: open security alerts. Enter reads one.",
    "repository:alerts_closed": "Dismissed and Resolved Alerts: alerts no longer open.",
    "repository:settings": "Settings: names of secrets, branch protection and general settings.",
    "repository:secrets": "Secret and Variable Names: the names only; GitHub never shows values.",
    "repository:branch_protection": (
        "Branch Protection: who may change a branch and what a change needs first. "
        "Enter opens the setting."
    ),
    "repository:general": "General: the name, visibility and default branch. Enter opens one.",
    "person:person": "A person: their repositories, activity, followers and who they follow.",
    "person:person_repositories": "Repositories: this person's public repositories.",
    "person:person_activity": "Activity: what this person did lately on GitHub.",
    "person:person_followers": "Followers: who follows this person.",
    "person:person_following": "Following: who this person follows.",
    "organization:organization": "An organization: its repositories.",
    "organization:organization_repositories": (
        "Repositories: the organization's repositories you can see."
    ),
}

#: What an empty list says instead (D4): why it is empty and what fills it.
_EMPTY: dict[str, str] = {
    ":review_requests": (
        "No pull requests need your review. When someone requests your review it "
        "appears here and in Inbox."
    ),
    ":inbox": "Nothing needs you right now. New notifications, reviews and mentions land here.",
    ":notifications": "No notifications. GitHub's new ones arrive here as they come.",
    ":saved_searches": (
        "No saved searches yet. Run a search under Search, then press Ctrl+N to keep it."
    ),
    ":pinned": "Nothing pinned yet. Ctrl+N here pins the repository you are working in.",
    ":favorites": "No favorites yet. Ctrl+D on any row keeps it here.",
    "repository:issues": "No open issues. Ctrl+N files one.",
    "repository:pulls": "No open pull requests.",
    "repository:runs": "No workflow runs. Runs appear when a workflow runs on GitHub.",
}
