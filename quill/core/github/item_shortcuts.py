"""The two keys a Workbench list answers with no menu: Delete and Ctrl+N (Part C, C3).

Moved out of :mod:`quill.core.github.item_actions` (which re-exports both) to
keep that module under its size budget; the tables themselves are unchanged
in meaning. wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = ["DELETE_COMMANDS", "NEW_HERE"]

#: What Delete does on each row type (Part C, C3): always a safe removal, an
#: undoable one or one that asks first, and never on a type that has none.
DELETE_COMMANDS: dict[str, str] = {
    "notification": "github.workbench.mark_done",
    "saved_search": "github.workbench.remove_search",
    "favorite": "github.workbench.favorite",
    "issue": "github.workbench.close_reopen",
    "pull_request": "github.workbench.close_reopen",
    "branch": "github.workbench.delete_branch",
    "label": "github.workbench.delete_label",
    "release_asset": "github.workbench.delete_asset",
    "gist": "github.workbench.delete_gist",
    "cache": "github.workbench.delete_cache",
    "run": "github.workbench.delete_run",
    "watch": "github.workbench.remove_watch",
    "repository_set": "github.workbench.across_delete_set",
    "tag": "github.workbench.delete_tag",
    "key": "github.workbench.delete_key",
    "webhook": "github.workbench.delete_webhook",
    "deploy_key": "github.workbench.delete_deploy_key",
    "autolink": "github.workbench.delete_autolink",
}

#: What Ctrl+N makes on each node (C3, "New, here"), by the node's key.
NEW_HERE: dict[str, str] = {
    "issues": "github.workbench.new_issue",
    "issues_and_pulls": "github.workbench.new_issue",
    "pulls": "github.workbench.new_pull",
    "saved_searches": "github.workbench.save_search",
    "search_issues": "github.workbench.save_search",
    "releases": "github.workbench.new_release",
    "tags": "github.workbench.new_tag",
    "star_lists": "github.workbench.new_star_list",
    "advisories": "github.workbench.new_advisory",
    "my_keys": "github.workbench.new_key",
    "webhooks": "github.workbench.new_webhook",
    "deploy_keys": "github.workbench.new_deploy_key",
    "autolinks": "github.workbench.new_autolink",
    "my_gists": "github.workbench.new_gist",
    "across": "github.workbench.choose_repositories",
    "across_sets": "github.workbench.across_new_set",
    "pinned": "github.workbench.pin_repository",
    "watches": "github.workbench.add_watch",
    "templates": "github.workbench.new_template",
    "discussions": "github.workbench.new_discussion",
}
