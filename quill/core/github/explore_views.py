"""The Explore views: their keys, spoken names, and which need a repository, a person or a sign-in.

Moved out of :mod:`quill.core.github.explore` on 2026-11-07 (GATE-11). Pure data:
the dialog reads it to build its view list, and the client to route a fetch.
"""

from __future__ import annotations

__all__ = ["AUTH_VIEWS", "PERSON_VIEWS", "REPO_VIEWS", "VIEWS"]

VIEWS: tuple[tuple[str, str], ...] = (
    ("search", "Global issue and PR search"),
    ("my_work", "My Work"),
    ("attention", "Attention queue"),
    ("activity", "My activity feed"),
    ("repositories", "My repositories"),
    ("starred", "Starred repositories"),
    ("watched", "Watched repositories"),
    ("following", "People I follow"),
    ("followers", "My followers"),
    ("gists", "My gists"),
    ("notifications", "GitHub notifications"),
    ("chooser", "Repository chooser"),
    ("person_repos", "Person's repositories"),
    ("person_activity", "Person's public activity"),
    ("person_followers", "Person's followers"),
    ("person_following", "People followed by person"),
    ("repo_overview", "Repository overview"),
    ("repo_activity", "Repository activity"),
    ("repo_people", "Repository people"),
    ("repo_forks", "Repository forks"),
    ("repo_access", "Collaborators and team access"),
    ("deployments", "Deployments and environments"),
    ("metrics", "Repository health snapshot (opt-in)"),
    ("labels", "Repository labels"),
    ("pages", "GitHub Pages and builds"),
    ("discussions", "Repository Discussions"),
    ("security", "Repository security alerts"),
)

REPO_VIEWS = frozenset({
    "repo_overview",
    "repo_activity",
    "repo_people",
    "repo_forks",
    "repo_access",
    "deployments",
    "metrics",
    "labels",
    "pages",
    "discussions",
    "security",
})
PERSON_VIEWS = frozenset({
    "person_repos",
    "person_activity",
    "person_followers",
    "person_following",
})
AUTH_VIEWS = frozenset({
    "my_work",
    "activity",
    "repositories",
    "watched",
    "following",
    "followers",
    "gists",
    "notifications",
    "discussions",
    "repo_access",
    "deployments",
    "metrics",
})
