"""The Explore views: their keys, spoken names, and which need a repository, a person or a sign-in.

Moved out of :mod:`quill.core.github.explore` on 2026-11-07 (GATE-11). Pure data:
the dialog reads it to build its view list, and the client to route a fetch.
"""

from __future__ import annotations

__all__ = ["AUTH_VIEWS", "PERSON_VIEWS", "QUERY_VIEWS", "REPO_VIEWS", "VIEWS", "VIEW_NOTES"]

VIEWS: tuple[tuple[str, str], ...] = (
    ("search", "Global issue and PR search"),
    ("code_search", "Code search"),
    ("commit_search", "Commit search"),
    ("repo_search", "Repository search"),
    ("user_search", "People search"),
    ("topic_search", "Topic search"),
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
    ("person_profile", "Person's profile"),
    ("person_sponsor", "Sponsor a person"),
    ("person_repos", "Person's repositories"),
    ("person_activity", "Person's public activity"),
    ("person_followers", "Person's followers"),
    ("person_following", "People followed by person"),
    ("person_packages", "Person's packages"),
    ("my_codespaces", "My codespaces"),
    ("repo_codespaces", "Repository codespaces"),
    ("repo_packages", "Repository packages"),
    ("repo_environments", "Repository environments"),
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
    ("insights", "Insights: traffic and contributors"),
    ("community", "Community profile checklist"),
    ("commit_stats", "Commit activity as tables"),
    ("security_policy", "Security policy and reporting"),
    ("advisories", "Repository security advisories"),
    ("webhooks", "Repository webhooks"),
    ("deploy_keys", "Repository deploy keys"),
    ("autolinks", "Repository autolinks"),
    ("org_webhooks", "Organization webhooks"),
    ("org_packages", "Organization packages"),
    ("wiki", "Repository wiki"),
    ("advisory_search", "GitHub Advisory Database"),
    ("actions_caches", "Actions caches"),
    ("secrets", "Secret and variable names"),
    ("merge_queue", "Merge queue"),
    ("invitations", "Repository invitations"),
    ("my_packages", "My packages"),
    ("star_lists", "Star lists"),
    ("my_profile", "My profile"),
    ("my_keys", "My SSH and GPG keys"),
    ("sponsorships", "My sponsorships"),
    ("runners", "Self-hosted runners"),
    ("billing_usage", "Billing and usage"),
    ("security_closed", "Dismissed and resolved security alerts"),
)

REPO_VIEWS = frozenset({
    "repo_codespaces",
    "repo_packages",
    "repo_environments",
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
    "insights",
    "community",
    "commit_stats",
    "security_policy",
    "advisories",
    "webhooks",
    "deploy_keys",
    "autolinks",
    "wiki",
    "actions_caches",
    "secrets",
    "security_closed",
    "merge_queue",
    "runners",
})
QUERY_VIEWS = frozenset({
    "search",
    "code_search",
    "commit_search",
    "repo_search",
    "user_search",
    "topic_search",
})
"""Views that run the query typed in the search box."""
PERSON_VIEWS = frozenset({
    "person_profile",
    "person_sponsor",
    "person_repos",
    "person_activity",
    "person_followers",
    "person_following",
    "person_packages",
})
AUTH_VIEWS = frozenset({
    "repo_environments",
    "person_packages",
    "my_codespaces",
    "repo_codespaces",
    "repo_packages",
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
    "code_search",
    "insights",
    "actions_caches",
    "secrets",
    "billing_usage",
    "merge_queue",
    "invitations",
    "runners",
    "my_packages",
    "star_lists",
    "my_profile",
    "my_keys",
    "sponsorships",
})

VIEW_NOTES: dict[str, str] = {
    "merge_queue": (
        "The default branch's merge queue, in order. A repository without one lists "
        "nothing: a merge queue is turned on by a branch rule, in an organization's repository."
    ),
    "metrics": (
        "Opt-in snapshot: loads repository health counts from GitHub. "
        "The results stay on this device and do not rank contributors."
    ),
    "code_search": "Searches code on GitHub. Needs a signed-in account; try repo:owner/name.",
    "insights": (
        "Traffic needs push access to the repository; contributors are listed for anyone."
    ),
    "secrets": "Names only. QUILL never reads a secret's or variable's value.",
}
"""The line shown under the view chooser for views that need explaining."""


def _resource_views() -> tuple[tuple[tuple[str, str], ...], frozenset[str]]:
    """The resource engine's lists (resource_specs.py), and which need a repository."""
    from quill.core.github.resource_specs import RESOURCE_SPECS

    # The list's own label, after whose it is ("Organization Custom Properties"):
    # built from the noun, it read "custom propertys" and "email addresss".
    owner = {"repository": "Repository ", "organization": "Organization ", "person": "Person's "}
    views = tuple(
        (f"res_{spec.key}", f"{owner.get(spec.scope, '')}{spec.label}") for spec in RESOURCE_SPECS
    )
    repo = frozenset(f"res_{spec.key}" for spec in RESOURCE_SPECS if spec.scope == "repository")
    return views, repo


_RESOURCE_VIEWS, _RESOURCE_REPO_VIEWS = _resource_views()
VIEWS = VIEWS + _RESOURCE_VIEWS
REPO_VIEWS = REPO_VIEWS | _RESOURCE_REPO_VIEWS
AUTH_VIEWS = AUTH_VIEWS | {key for key, _title in _RESOURCE_VIEWS}
