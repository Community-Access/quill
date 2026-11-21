"""Appendix A and B of the GitHub PRD: every retired button, menu row and action, and its home.

The Explore and GitHub Items *views* are not here: each is read from its own
registry with the tree node that is its home (see
:mod:`quill.core.github.appendix_map`). What is here is everything else the
classic windows and the editor's GitHub menu had. The gate fails when a ref
stops resolving, when one of those windows grows a control no row names, and
when the editor's GitHub menu gains a row no row names. wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.appendix_map import Home

__all__ = ["APPENDIX_A", "APPENDIX_B"]

_ITEMS = "GitHub Items' and Explore GitHub's buttons and choices"
_MENU = "The editor's GitHub menu rows (Workbench Mode)"
_PREFS = "Preferences"

_ADMIN = (
    "github.create_repository",
    "github.fork_repository",
    "github.rename_repository",
    "github.change_repository_visibility",
    "github.change_default_branch",
    "github.configure_branch_protection",
    "github.delete_branch",
    "github.commit_multiple_files",
    "github.browse_organization",
    "github.create_release",
    "github.dispatch_workflow",
    "github.view_security_alerts",
)
_LINE = (
    "github.copy_line_link",
    "localgit.blame_at_cursor",
    "github.open_line_pull",
    "github.open_line",
    "github.issue_from_selection",
    "github.issues_mentioning_file",
    "github.comment_on_line",
    "github.open_reference_at_cursor",
)
_LOCAL_GIT = (
    "localgit.uncommitted_changes",
    "localgit.switch_branch",
    "localgit.stash_changes",
    "localgit.manage_stashes",
    "localgit.bisect_start",
    "localgit.bisect_reset",
    "localgit.resolve_conflicts",
    "localgit.interactive_rebase",
    "localgit.rebase_abort",
    "localgit.worktrees",
    "localgit.new_worktree",
)

APPENDIX_A: tuple[Home, ...] = (
    # -- the classic windows' buttons and choices --------------------------------
    Home(_ITEMS, "Repository box and Load",
         "The Repositories node; File > Open GitHub Address... (Ctrl+L) takes owner/name",
         ("node:repositories", "menu:open_address"),
         labels=("Repository (owner/repo):", "Repository:", "Load")),
    Home(_ITEMS, "Pinned...", "Repositories > Pinned; Tools > Workbench Options > Repositories",
         ("node:pinned", "prefpage:Repositories", "row:repository.pin_repository"),
         labels=("Pinned...",)),
    Home(_ITEMS, "Favorites...", "Repositories > Favorites; Item > Add to or Remove from "
         "Favorites (Ctrl+D)", ("node:favorites", "menu:favorite"), labels=("Favorites...",)),
    Home(_ITEMS, "Explore...", "Gone as a window: each of its views is a node (above)",
         ("node:search",), reason="Explore GitHub was a second window; its views are nodes.",
         labels=("Explore...",)),
    Home(_ITEMS, "Projects...", "The Projects node; Repository > Projects; Repository Actions... "
         "> Projects...", ("node:projects", "node:repository.repo_projects",
                           "repoaction:github.workbench.projects_window"),
         labels=("Projects...",)),
    Home(_ITEMS, "View Upstream", "Repository > Code > Upstream (a fork's own node)",
         ("node:repository.upstream",), labels=("View Upstream",)),
    Home(_ITEMS, "Files...", "Repository > Code > Files; Go > Files (Ctrl+Shift+5); Repository "
         "Actions... > Files, History and Blame...",
         ("node:repository.files", "menu:go_files", "repoaction:github.workbench.files_window"),
         labels=("Files...",)),
    Home(_ITEMS, "Milestones...", "Repository > Milestones; Repository Actions... > "
         "Milestones...", ("node:repository.milestones",
                           "repoaction:github.workbench.milestones_window"),
         labels=("Milestones...",)),
    Home(_ITEMS, "Search box and Search", "The filter box (Ctrl+E); the Search branch",
         ("menu:filter", "node:search"), labels=("Search (GitHub syntax):", "Search",
                                                 "Global search:")),
    Home(_ITEMS, "Open Link...", "File > Open GitHub Address... (Ctrl+L)",
         ("menu:open_address",), labels=("Open Link...",)),
    Home(_ITEMS, "Quick filter", "The filter box (Ctrl+E); Edit > Filter Builder... (Ctrl+Alt+F)",
         ("menu:filter", "menu:filter_builder"), labels=("Quick filter:",)),
    Home(_ITEMS, "View and Person choices", "The tree: each view is a node; People > Find a "
         "Person... opens anyone's", ("node:repository.code", "node:find_person"),
         labels=("View:", "Person:")),
    Home(_ITEMS, "Show choice", "The Issues, Pull Requests and Issues and Pull Requests nodes; "
         "View > Issues, Pull Requests, Both", ("node:repository.issues", "node:repository.pulls",
                                                 "menu:show_issues", "menu:show_prs",
                                                 "menu:show_both"), labels=("Show:",)),
    Home(_ITEMS, "State, Sort", "View > Open, Closed, All; View > Newest First and the other "
         "sorts", ("menu:state_open", "menu:state_closed", "menu:state_all",
                   "menu:sort_number_desc"), labels=("State:", "Sort:")),
    Home(_ITEMS, "List mode", "Tools > Workbench Options > General: the list mode",
         ("pref:list_mode",), labels=("List mode:",)),
    Home(_ITEMS, "Columns...", "View > Columns... (Ctrl+Shift+U) for this list; Tools > "
         "Workbench Options > Lists for the defaults", ("menu:columns", "prefpage:Lists"),
         labels=("Columns...",)),
    Home(_ITEMS, "Back, Forward", "View > Back (Alt+Left, Backspace), Forward (Alt+Right)",
         ("menu:back", "menu:forward"), labels=("Back", "Forward")),
    Home(_ITEMS, "Refresh", "View > Refresh (F5)", ("menu:refresh",), labels=("Refresh",)),
    Home(_ITEMS, "View More", "View > Load More (Alt+Page Down), Load All",
         ("menu:load_more", "menu:load_all"), labels=("View More",)),
    Home(_ITEMS, "Open in Browser", "File > Open on GitHub (Shift+Enter); on every context menu",
         ("menu:open_on_github",), labels=("Open in Browser", "Open on GitHub")),
    Home(_ITEMS, "Go To #...", "File > Go to Number... (Ctrl+G)", ("menu:go_to_number",),
         labels=("Go To #...",)),
    Home(_ITEMS, "Diff...", "Item > File Differences... (Ctrl+Shift+D); the pull request's "
         "context menu", ("menu:diff", "row:pull_request.diff"), labels=("Diff...",)),
    Home(_ITEMS, "Review...", "Review... on a pull request's context menu; its default action",
         ("row:pull_request.review",), labels=("Review...",)),
    Home(_ITEMS, "Summarize", "Summarize Discussion on an issue's or pull request's context menu",
         ("row:issue.summarize", "row:pull_request.summarize"), labels=("Summarize",)),
    Home(_ITEMS, "Compare...", "Repository > Compare Branches... (Ctrl+Shift+B); a branch's "
         "context menu", ("menu:compare", "row:branch.compare"), labels=("Compare...",)),
    Home(_ITEMS, "Batch...", "Select several rows, then Item > Properties... (Alt+Enter) edits "
         "them together; Merge Selected... on pull requests",
         ("menu:properties", "row:pull_request.merge_selected"), labels=("Batch...",)),
    Home(_ITEMS, "Actions...", "The Item menu, and each row's context menu (Shift+F10)",
         ("menu:properties", "menu:comment"), labels=("Actions...",)),
    Home(_ITEMS, "Saved Searches..., Save Search", "Search > Saved Searches; New Here (Ctrl+N) "
         "in a search saves it", ("node:saved_searches", "new:search_issues",
                                  "menu:go_saved_searches"),
         labels=("Saved Searches...", "Save Search")),
    Home(_ITEMS, "Close", "File > Close Workbench (Alt+F4)", ("menu:close",), labels=("Close",)),
    # -- the editor's GitHub menu --------------------------------------------------
    Home(_MENU, "Leave Workbench Mode", "Stays", ("editor:view.github_workbench_mode",)),
    Home(_MENU, "GitHub Items..., Repository Items...", "Open GitHub Workbench (the same command)",
         ("editor:file.open_github_items", "door:file.open_github_items")),
    Home(_MENU, "Inbox...", "Stays: opens Needs My Attention > Inbox",
         ("editor:github.workbench_inbox", "door:github.workbench_inbox", "node:inbox")),
    Home(_MENU, "My Work..., Notifications...", "Command ids kept, each opening its node; the "
         "rows left the menu", ("editor:github.workbench_my_work", "door:github.workbench_my_work",
                                "editor:github.view_notifications",
                                "door:github.view_notifications", "node:notifications")),
    Home(_MENU, "Issues and Pull Requests...", "This Repository's Issues and This Repository's "
         "Pull Requests", ("editor:github.workbench_issues", "door:github.workbench_issues",
                           "editor:github.workbench_pulls", "door:github.workbench_pulls")),
    Home(_MENU, "Actions Runs...", "Stays: opens the repository's Actions > Runs",
         ("editor:github.workbench_actions_runs", "door:github.workbench_actions_runs")),
    Home(_MENU, "Releases..., Explore GitHub...", "Command ids kept, opening Releases and Search; "
         "Open GitHub Workbench replaces the rows",
         ("editor:github.workbench_releases", "door:github.workbench_releases",
          "editor:github.workbench_explore", "door:github.workbench_explore")),
    Home(_MENU, "Open GitHub Reference..., GitHub File URL...", "Open GitHub Address... in the "
         "editor; File > Open GitHub Address... (Ctrl+L) in the Workbench",
         ("editor:file.open_github_reference", "editor:file.open_github_file_url",
          "menu:open_address")),
    Home(_MENU, "Open a Repository..., Clone Repository...", "Clone stays; Open a Repository "
         "is File > Open GitHub Address... (Ctrl+L) in the Workbench",
         ("editor:file.open_github_repository", "editor:github.clone_repository",
          "menu:open_address")),
    Home(_MENU, "Commit to GitHub..., Sync Folder with GitHub...", "Stay (QUILL only)",
         ("editor:file.github_save_back", "editor:sync.sync_folder")),
    Home(_MENU, "Repository Admin submenu", "Repository > Repository Actions... (Ctrl+Shift+G) "
         "lists every one; with the Workbench in use each opens its node or sheet page",
         tuple(f"editor:{c}" for c in _ADMIN) + tuple(f"door:{c}" for c in _ADMIN)
         + tuple(f"repoaction:{c}" for c in _ADMIN)),
    Home(_MENU, "Codespaces submenu", "Repository > Code > Codespaces; Repository Actions...",
         ("editor:github.list_codespaces", "editor:github.create_codespace",
          "door:github.list_codespaces", "door:github.create_codespace",
          "node:repository.repo_codespaces")),
    Home(_MENU, "From This Line submenu", "Stays in the editor (PRD 22.3)",
         tuple(f"editor:{c}" for c in _LINE)),
    Home(_MENU, "Local Git submenu", "Stays in the editor",
         tuple(f"editor:{c}" for c in _LOCAL_GIT)),
    Home(_MENU, "Manage GitHub Accounts..., Open GitHub Guide", "Stay; also Account > Manage "
         "GitHub Accounts... (Ctrl+Shift+K) and Help > GitHub Workbench Guide (Ctrl+F1)",
         ("editor:file.github_manage_accounts", "editor:help.github_guide",
          "menu:manage_accounts", "menu:guide_chapter")),
    # -- preferences -------------------------------------------------------------
    Home(_PREFS, "Notification poll interval, sound on each check, interrupt speech",
         "Tools > Workbench Options > Notifications and Inbox",
         ("pref:poll_interval_minutes", "pref:poll_audible_tick", "pref:poll_interrupt_speech")),
    Home(_PREFS, "Queue Options... (Choose Repositories..., Choose Categories..., Save Current "
         "Filter...)", "Item > Inbox Rules... (Ctrl+Alt+N); on the Inbox, the filter box "
         "(repo:, owner:) narrows by repository",
         ("menu:inbox_rules", "node:inbox",
          "code:quill/ui/github_explore_queue.py#Choose Categories"),
         reason="Choose Categories and Save Current Filter have no Workbench home yet: the "
         "Inbox reads the choices the classic window saved.",
         labels=("Queue Options...",)),
    Home(_PREFS, "Include read notifications", "Tools > Workbench Options > Notifications and "
         "Inbox", ("pref:include_read_notifications",)),
    Home(_PREFS, "Health snapshot opt-in", "Tools > Workbench Options > Privacy",
         ("pref:health_snapshot_opt_in",)),
    Home(_PREFS, "Columns, list mode, sort, state defaults", "Tools > Workbench Options > "
         "General and Lists", ("pref:list_mode", "pref:default_sort", "pref:default_state",
                               "prefpage:Lists")),
    Home(_PREFS, "Last view, filter, selection, history (resume state)", "Kept on this "
         "computer; Tools > Workbench Options > Privacy > Forget Where I Was clears it",
         ("prefpage:Privacy", "code:quill/ui/github_workbench_options.py#Forget &Where I Was")),
)  # fmt: skip

_B = "Existing actions"

APPENDIX_B: tuple[Home, ...] = (
    Home(_B, "Set Topics...", "Repository Properties (Alt+Enter), General: Topics",
         ("sheet:repository.general.topics",), sheet="Repository > General: Topics",
         sheet_refs=("sheet:repository.general.topics",)),
    Home(_B, "Sync Fork with Upstream...", "Sync Fork with Upstream... on a repository's context "
         "menu; Repository > Code > Upstream", ("row:repository.sync_fork",
                                                "node:repository.upstream"),
         sheet="Repository > Fork: the fork, its parent and source",
         sheet_refs=("sheet:repository.fork.parent",)),
    Home(_B, "Archive Repository..., Unarchive Repository...", "Repository Properties, Danger "
         "Zone: Archived", ("sheet:repository.danger.archived",),
         sheet="Repository > Danger Zone: Archived",
         sheet_refs=("sheet:repository.danger.archived",)),
    Home(_B, "Delete Repository...", "Delete Repository... on a repository's context menu, with "
         "its typed confirmation (tier 3)", ("row:repository.delete_repository",),
         sheet="Repository > Danger Zone", sheet_refs=("sheet:repository.danger",)),
    Home(_B, "Create Repository from This Template...", "Create Repository from This "
         "Template... on a repository's context menu", ("row:repository.use_template",),
         sheet="Repository > Templates: Template repository",
         sheet_refs=("sheet:repository.templates.is_template",)),
    Home(_B, "Watch Level...", "Watch or Unwatch on a repository's context menu; the level on "
         "its sheet", ("row:repository.watch", "sheet:repository.you.custom_watch"),
         sheet="Repository > You: Watch, with custom events",
         sheet_refs=("sheet:repository.you.watch", "sheet:repository.you.custom_watch")),
    Home(_B, "Use Repository", "Gone: selecting the repository's node is \"use\"",
         ("node:repository.repository",), reason="Selecting a repository's node uses it.",
         labels=("Use Repository",)),
    Home(_B, "Add Blocker..., Remove Blocker..., Add Sub-issue..., Remove Sub-issue...",
         "Relationships... and Reorder Sub-issues... on an issue's context menu",
         ("row:issue.relationships", "row:issue.sub_issues"),
         sheet="Issue > Relationships: parent, sub-issues, linked",
         sheet_refs=("sheet:issue.relationships.parent", "sheet:issue.relationships.sub_issues")),
    Home(_B, "Next Unblocked", "Repository Actions... > Projects... (the board): Next Unblocked",
         ("repoaction:github.workbench.projects_window",
          "code:quill/ui/github_projects_dialog.py#&Next Unblocked"),
         sheet="Issue > Relationships", sheet_refs=("sheet:issue.relationships",)),
    Home(_B, "Possible Duplicate Issues (check when filing)", "Close or Reopen... closes as a "
         "duplicate of an issue named; Not a Duplicate... on an issue's context menu",
         ("row:issue.close_reopen", "row:issue.not_duplicate",
          "code:quill/ui/github_items_dialog_issue_templates.py#Possible Duplicate Issues"),
         reason="Find Possible Duplicates is not built in the Workbench yet; the check when "
         "filing runs in the classic New Issue form only.",
         sheet="Issue > Relationships: linked", sheet_refs=("sheet:issue.relationships.linked",)),
    Home(_B, "Projects and Dependencies, Edit Project Field..., Refresh Board", "The Projects "
         "node; Projects... on an issue or pull request; Repository Actions... > Projects...",
         ("node:projects", "row:issue.projects", "repoaction:github.workbench.projects_window",
          "code:quill/ui/github_projects_dialog.py#Edit Project Field..."),
         sheet="Issue or pull request > Projects; the Project sheet",
         sheet_refs=("sheet:issue.projects.projects", "sheet:project.fields")),
    Home(_B, "Compose Review..., Request Changes, Request Reviewers..., Request Copilot Review",
         "Review... and Reviews... on a pull request; Ask Copilot to Review",
         ("row:pull_request.review", "row:pull_request.manage_reviews",
          "row:pull_request.copilot_code_review"),
         sheet="Pull request > Reviews: reviewers and teams",
         sheet_refs=("sheet:pull_request.reviews.reviewers",
                     "sheet:pull_request.reviews.team_reviewers")),
    Home(_B, "Mark Ready, convert to draft", "Pull request Properties, General: Draft; Mark "
         "Ready in Review...", ("sheet:pull_request.general.draft",
                                "code:quill/ui/github_pr_review_dialog.py#&Mark Ready"),
         sheet="Pull request > General: Draft", sheet_refs=("sheet:pull_request.general.draft",)),
    Home(_B, "Update Branch...", "Review... on a pull request: Update Branch",
         ("row:pull_request.review", "code:quill/ui/github_pr_review_dialog.py#_update_branch"),
         sheet="Pull request > Branches: base and head",
         sheet_refs=("sheet:pull_request.branches.base",)),
    Home(_B, "Enable Auto-Merge..., Disable Auto-Merge...", "Auto-Merge... on a pull request",
         ("row:pull_request.auto_merge",), sheet="Pull request > Merge: auto-merge",
         sheet_refs=("sheet:pull_request.merge.auto_merge",)),
    Home(_B, "Add to Merge Queue..., Remove from Merge Queue...", "Add to or Remove from Merge "
         "Queue... on a pull request", ("row:pull_request.merge_queue",),
         sheet="Pull request > Merge", sheet_refs=("sheet:pull_request.merge",)),
    Home(_B, "Check Merge Policy", "Why Can't I Merge? on a pull request",
         ("row:pull_request.why_cant_merge",), sheet="Pull request > Merge: merged",
         sheet_refs=("sheet:pull_request.merge.merged",)),
    Home(_B, "Re-request Check..., Copy Check Details", "Inside Review..., unchanged",
         ("row:pull_request.review", "code:quill/ui/github_pr_review_menus.py#Re-request Check...",
          "code:quill/ui/github_pr_review_menus.py#Copy Check Details"),
         sheet="Pull request > Checks", sheet_refs=("sheet:pull_request.checks",)),
    Home(_B, "Next Unresolved, Reply to Thread..., Copy Thread Link", "Inside Review..., "
         "unchanged", ("row:pull_request.review",
                       "code:quill/ui/github_pr_review_dialog.py#Next &Unresolved",
                       "code:quill/ui/github_pr_review_menus.py#Reply to Thread...",
                       "code:quill/ui/github_pr_review_menus.py#Copy Thread Link"),
         sheet="Pull request > Reviews: review comments",
         sheet_refs=("sheet:pull_request.reviews.review_comments",)),
    Home(_B, "Pending comment edit and delete", "Inside Review..., unchanged",
         ("row:pull_request.review",
          "code:quill/ui/github_pr_review_menus.py#Edit Pending Comment...",
          "code:quill/ui/github_pr_review_menus.py#Delete Pending Comment...")),
    Home(_B, "Copy Conversation, Copy Review Summary, Copy File Name, Copy Pull Request Link",
         "Inside Review...; Edit > Copy (Ctrl+C) and Copy Link (Ctrl+Shift+C) everywhere",
         ("menu:copy", "menu:copy_link",
          "code:quill/ui/github_pr_review_menus.py#Copy Conversation",
          "code:quill/ui/github_pr_review_menus.py#Copy Review Summary",
          "code:quill/ui/github_pr_review_menus.py#Copy File Name",
          "code:quill/ui/github_pr_review_menus.py#Copy Pull Request Link")),
    Home(_B, "React to Pull Request..., React to a Comment...", "React... on an issue or pull "
         "request", ("row:issue.react", "row:pull_request.react"),
         sheet="Issue, pull request and discussion > You: reactions",
         sheet_refs=("sheet:issue.you.reactions", "sheet:pull_request.you.reactions",
                     "sheet:discussion.you.reactions")),
    Home(_B, "Mark discussion answer, unmark answer", "Open Discussion Thread: Mark as Answer",
         ("row:discussion.discussion_thread",
          "code:quill/ui/github_discussion_dialog.py#&Mark as Answer..."),
         sheet="Discussion > Answer", sheet_refs=("sheet:discussion.answer.answered_by",)),
    Home(_B, "Create milestone", "New Milestone... in every milestone picker; Repository "
         "Actions... > Milestones...", ("sheet:issue.organize.milestone",
                                        "repoaction:github.workbench.milestones_window"),
         sheet="Milestone sheet: title, description, due date, state, progress",
         sheet_refs=("sheet:milestone.general", "sheet:milestone.progress")),
    Home(_B, "Lock Conversation... (with reason), Unlock Conversation", "Lock or Unlock "
         "Conversation... on an issue", ("row:issue.lock",),
         sheet="Issue or pull request > Conversation: Locked, with reason",
         sheet_refs=("sheet:issue.conversation.locked", "sheet:pull_request.conversation.locked")),
    Home(_B, "Dependabot, code scanning and secret scanning alerts; Dismiss Alert..., Reopen "
         "Alert...", "Repository > Security > Alerts; Dismiss or Reopen Alert... on an alert",
         ("node:repository.alerts", "row:security_alert.dismiss_alert"),
         sheet="Security alert sheet: state, reason, severity, location",
         sheet_refs=("sheet:security_alert.general.state", "sheet:security_alert.location")),
    Home(_B, "Pull request and issue templates and forms", "Repository > Templates; New Here "
         "(Ctrl+N) in Issues fills a form", ("node:repository.templates",
                                              "row:template.open_template", "new:issues"),
         sheet="Repository > Templates", sheet_refs=("sheet:repository.templates",)),
    Home(_B, "Thread subscription (Unsubscribe from Thread)", "Unsubscribe from Thread on a "
         "notification", ("row:notification.unsubscribe",),
         sheet="Notification > You: Subscribed", sheet_refs=("sheet:notification.you.subscribed",)),
)  # fmt: skip
