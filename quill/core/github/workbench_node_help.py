"""What F1 says about each GitHub Workbench node, and what an empty list says.

Pure data split from :mod:`quill.core.github.workbench_help_text` (GATE-11),
which re-exports both names. Plain, short, what to do before why (Part D9).
"""

from __future__ import annotations

from quill.core.github.across_help import ACROSS_NODE_HELP

__all__ = ["NODE_HELP"]

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
    "repository:runners": (
        "Runners: the machines this repository runs its own jobs on, online or not, busy "
        "or idle, with their labels. Only administrators can see them."
    ),
    ":star_lists": (
        "Star Lists: every repository on each of your star lists, the list's name first. "
        "Ctrl+N makes a list; Star Lists on any repository chooses its lists."
    ),
    ":packages": (
        "My Packages: your container images and npm, Maven, RubyGems and NuGet packages, "
        "with Delete Package Version and Delete Package on each."
    ),
    ":invitations": (
        "Invitations: repositories you have been invited to, who invited you and with what "
        "access. Accept or Decline from a row's context menu."
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
    ":my_teams": (
        "My Teams: every team you belong to, across your organizations. Alt+Enter opens "
        "a team's sheet."
    ),
    ":followers": "My Followers: accounts that follow you.",
    ":find_person": (
        "Find a Person: type a login with Ctrl+L, and the person gets a node of their own here."
    ),
    ":gists": "Gists: small shared files and snippets.",
    ":my_gists": "My Gists: gists you made. Enter edits one.",
    ":billing_usage": (
        "Billing and Usage: this month's metered use of your account, by product, "
        "from GitHub's billing report. Read only; Enter opens your billing page."
    ),
    ":projects": (
        "Projects: your Project boards. Each repository's own Projects are under it, Ctrl+Shift+7."
    ),
    ":watches": (
        "Watches: tell me when something happens. Each row is a rule: a run finishes "
        "on a repository or branch, a review arrives on a pull request, a new release, "
        "a new comment. They are checked on the notification check's interval in "
        "Workbench Options while this window is open, and each row says when it was "
        "last checked. Ctrl+N adds one, Enter edits, Delete removes. Watches never "
        "mark notifications read."
    ),
    # Across Repositories (PRD 22.11): quill/core/github/across_help.py.
    **ACROSS_NODE_HELP,
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
    "repository:templates": (
        "Templates: issue forms, Markdown templates, the chooser, pull request templates, "
        "discussion forms and community files, including those inherited from the "
        "owner's .github repository. Enter builds or edits one; Ctrl+N starts a new one."
    ),
    "repository:repo_projects": "Projects: this repository's Project boards.",
    "repository:merge_queue": (
        "Merge Queue: the default branch's merge queue in order, each pull request's state."
    ),
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
    "repository:commit_activity": (
        "Commit Activity: GitHub's statistics graphs as rows: commits and lines each week, "
        "the busiest hours, and each contributor's lines."
    ),
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
    "person:person_profile": (
        "Profile: who this person is, their year of contributions as numbers, and what they pinned."
    ),
    "person:person_repositories": "Repositories: this person's public repositories.",
    ":my_profile": (
        "My Profile: your profile as GitHub shows it, your year of contributions as numbers, "
        "and what you pinned."
    ),
    "person:person_activity": "Activity: what this person did lately on GitHub.",
    "person:person_followers": "Followers: who follows this person.",
    "person:person_following": "Following: who this person follows.",
    "organization:organization": "An organization: its repositories.",
    "organization:organization_templates": (
        "Templates: the defaults in the organization's .github repository, which every "
        "repository without its own uses. Enter builds or edits one."
    ),
    "organization:organization_teams": (
        "Teams: the organization's teams, as GitHub nests them. Alt+Enter opens a "
        "team's sheet: its members and maintainers, repositories and roles, child teams "
        "and code review assignment."
    ),
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
    ":invitations": "No invitations. When someone invites you to a repository, it is here.",
    ":saved_searches": (
        "No saved searches yet. Run a search under Search, then press Ctrl+N to keep it."
    ),
    ":pinned": "Nothing pinned yet. Ctrl+N here pins the repository you are working in.",
    ":favorites": "No favorites yet. Ctrl+D on any row keeps it here.",
    "repository:issues": "No open issues. Ctrl+N files one.",
    "repository:pulls": "No open pull requests.",
    "repository:runs": "No workflow runs. Runs appear when a workflow runs on GitHub.",
    ":watches": "No watches yet. Ctrl+N adds one: a run, a review, a release or a comment.",
}
