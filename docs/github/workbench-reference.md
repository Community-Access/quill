# GitHub Workbench: keyboard and screen reader reference

QUILL and QUILL Lite share the GitHub Items and Explore windows. QUILL Lite
opens the workbench from **File > GitHub Workbench** (**Alt+F**, then **G**). In QUILL, use **File >
Open from Remote > GitHub Items**. Public repository reading works without an
account. Account views and writes require a signed-in GitHub account. Safe Mode
and the first-use network consent still apply.

In QUILL, **File > Open from Remote > Open GitHub Reference** accepts a pasted
repository or GitHub URL. The Items window also has **Open Link...** in both
QUILL and QUILL Lite. Repository links open Items; issue links select the exact
issue; pull-request links open its review reader; branch links select that
branch; and GitHub file links open in QUILL at the linked line. QUILL Lite
opens file and other unsupported object links in the browser after explaining
that the workbench has no native view for that object. Browser fallback never
attaches QUILL's GitHub token. Malformed or credential-bearing URLs are refused.

## The interaction pattern

The Items window is a repository list with a read-only detail field. Choose a
view, arrow through its rows, then Tab to read the selected item in full.
Shift+Tab returns to the list. The **Actions** button and the selected row's
context menu expose commands relevant to that item. Open the context menu with
Shift+F10, the Applications key, or right-click. **M** switches between compact
and fully labelled list speech. **Alt+N** and **Alt+P** move between comments in
an issue or PR's details. **Ctrl+F** searches GitHub in the loaded repository;
**Ctrl+Shift+F** filters the already loaded rows locally. **Ctrl+D** saves the
selected item as a favorite.

When you reopen Items, QUILL restores the last repository, view, filters, and
selected row for the same GitHub account. This is local resume state; it stores
no token and never submits a draft or changes GitHub.

The PR review window uses an actual expandable tree. The root PR contains
Changed files, General conversations when present, and Checks. Files contain
review threads. Left and Right collapse or expand; Up and Down move between
visible nodes. Tab reads the selected node's complete detail, then Shift+Tab
returns to the tree. On a thread, **Ctrl+R** replies; **Ctrl+Shift+R** resolves
or reopens it after confirmation, if GitHub permits. The context menu also
contains these commands, copy actions, and Open File Differences. A thread's
file and line select the matching file and exact changed line when its patch
still contains that line. If the line is outdated or absent, the diff explains
the missing location. No action is triggered merely by reading or expanding.
**Next Unresolved** moves among threads with a known unresolved state;
**Next Unvisited** tracks only the threads you selected in this review session.
It is local navigation and never marks GitHub notifications or threads read.

The Explore window uses a list and detail field for flat results. Its **View**
chooser switches between global search, My Work, the attention queue, activity,
repositories, people, notifications, gists, and repository-specific views. Enter opens the
selected result on GitHub; **Use Repository** sends a repository back to Items.
The context menu offers actions for the current result. Search queries saved
with **Save Search** stay on this computer and can be reopened or removed with
**Saved Searches**. The repository chooser places pinned and recent entries
first. A selected label can lead into a repository-scoped issue search. Star,
watch, notification-read, and label changes require a signed-in account.

The attention queue combines work assigned to you, requested reviews, mentions,
and pull requests with failed checks. **Queue Options** chooses up to ten
repositories and the categories to include, saves and reopens local filters,
and shows locally snoozed items. Snoozes and filters are stored separately for
each signed-in account and do not change GitHub. Each result names its source
and last update; duplicate results are combined. The status reports partial
loads instead of presenting them as a complete queue. A complete load records
the visit time so later visits can identify changed items. Opening the queue
never marks remote notifications as read.

## Repository and workflow views

Items includes issues and PRs, branches, commits, tags, releases and assets,
workflow definitions, and workflow runs. Enter on a branch opens its commits;
Backspace returns to branches. Enter on a release opens its assets and download
counts. A workflow definition can be dispatched on a chosen branch. On a run,
**Jobs and Logs** lists its jobs and loads a selected job's text log. **View
Artifacts** lists downloads. The context menu exposes the same applicable
commands as the buttons, including copy and browser actions. On an issue or PR,
**Start in Local Worktree** can prepare a separate local branch and folder when
the current checkout has a matching GitHub remote. QUILL shows the starting
local branch and any uncommitted changes first. Those changes stay in the
existing folder; the new worktree starts from the local commit and does not
fetch, push, or change the GitHub repository.

Workflow diagnostics show each job's steps, the selected attempt, and the head
SHA. Choose an earlier attempt from the attempt list; **Load Annotations** reads
the check-run annotations when GitHub grants access, and reports permission
errors instead of treating them as no findings. Annotation output is capped at
100 entries with a truncation message. Job logs are limited to 4 MB and mark
truncation. The run and job links open their exact GitHub pages.

**Projects** opens the selected repository's GitHub Projects v2 boards in a
list/detail view. Project rows show the fields available to your account;
issue details include blockers, sub-issues, and parent progress. **Next
Unblocked** moves to the next open issue or pull request without an open
blocker. The Actions menu can update supported text, number, date, single- or
multi-select, and iteration fields, or add/remove blocker and sub-issue links.
Each remote change names its target and effect in a confirmation. Permission
errors and incomplete project pages remain visible in the status.

Explore adds your repositories and work, starred and watched repositories,
people you follow and followers, a person's public repositories and activity,
repository activity and people, forks, labels, Pages site and build history,
notifications, and security alerts. Private information and certain actions
depend on the GitHub token's permissions and repository access. An API failure
appears as a status message; empty results are distinguished from errors.
The Security view combines Dependabot, code-scanning, and secret-scanning
alerts. Secret values are never loaded into the view. If the account cannot
read a category or the feature is disabled, the view labels that category
unavailable instead of presenting it as having no findings.

## Review and write safety

The review tree announces reply counts, outdated positions, resolved state,
and check status. Selecting a thread never resolves it. Reply, resolve, reopen,
review submission, branch updates, and other writes each require a deliberate
command and confirmation where appropriate. Actions are disabled if the PR is
closed, the account is signed out, or GitHub denies that permission. If the
review-thread state cannot be retrieved, threads remain readable while
resolution controls are unavailable. Refresh to observe changes made elsewhere.

The Items **Batch** menu operates on checked issue or PR rows. Its confirmation
names the targeted items. Repository deletion, visibility changes, merges,
and branch deletion have stronger typed confirmations in QUILL's administration
flows. QUILL Lite currently shares the Items, Explore, diff, and review surfaces;
the separate repository administration and Local Git menus still belong to
QUILL. This product difference is tracked in the workbench plan.

## Architecture and verification

The Items and review windows use `quill/core/github/items_provider.py` and
`pr_review.py`; review resolution uses `review_graphql.py`, line mapping uses
`diff_hunks.py`, and job log retrieval uses `workflow_job_logs.py`. Explore
uses `explore.py`; pinned repositories, favorites, recent repositories, and
saved queries use `saved_items.py`. The shared UI modules are under `quill/ui/`.
Network calls are made off the UI thread. Tests exercise provider mapping,
pagination, diff-line matching, redirect token handling, and action routing.
Manual Windows screen-reader acceptance with NVDA, JAWS, and Narrator is
user-owned follow-up. This reference does not claim a macOS assistive-technology
acceptance matrix.

For a guided walkthrough, read [Tutorial 8](../tutorials/08-github-inside-quill.md).
