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

## Notifications triage

Explore's **GitHub notifications** view is the account's whole inbox. In QUILL,
**Tools > Git and GitHub > GitHub > Notifications** opens Explore straight at
it; in QUILL Lite, choose **Explore** in Items and pick the view. After each
load QUILL says the unread count once, for example "12 unread". Each row reads
its state, then why it arrived in words ("review requested", "you were
mentioned", "your team was mentioned"), then the repository and title.

Under the list, shown only in this view: **Include read notifications**
(Alt+I), **Mark Done** (Alt+D), **Unsubscribe** (Alt+U) and **Mark All Read**
(Alt+A). Delete in the list is Mark Done. Done and Unsubscribe take the row out
of the list and select the next row, so triage keeps its place. Mark All Read
asks first and marks only what arrived before the list loaded. Enter marks the
row read, then opens a pull request in the review window, an issue in Items at
that issue, and anything else in the browser. The context menu offers the same
actions.

QUILL honours GitHub's `X-Poll-Interval`: a refresh sooner than GitHub allows
keeps the current list and says how long to wait. A refresh after that sends
`If-Modified-Since`, so an unchanged inbox costs no rate limit.

## What failed, and run actions

On a Workflow Runs row, **What Failed** (Ctrl+Shift+W in that view, the Actions
menu or the context menu) opens a read-only text field holding one digest: each
failed job, its failed steps, the annotations with `file:line`, then the last 40
meaningful log lines of each failed step with timestamps and ANSI codes removed.
A step's lines are the ones stamped inside its start and finish times; if
GitHub gave no times, the digest says so and uses the end of the job's log.
**Jobs and Logs** has the same digest as **What Failed** (Alt+F), for the
attempt you chose, and **Re-request Check** (Alt+C) for the selected job.

The same menus add **Re-run Failed Jobs Only**, **Cancel Run** (GitHub answers
"accepted", so QUILL says it is stopping the run), **Delete Run** (the
confirmation names the run, branch and result, and says logs and artifacts go
with it), **Approve Run from a Fork**, **Review Pending Deployments** (a window
listing waiting environments as check boxes, a required comment, and Approve
and Reject) and **Combined Check Status**, a single line such as "3 of 4 checks
pass; failing: test."

## Auto-merge and the merge queue

The review window's **Auto-Merge and Queue** button (Alt+A) and the pull
request's context menu hold **Enable Auto-Merge** (with a merge-method chooser),
**Disable Auto-Merge**, **Add to Merge Queue**, **Remove from Merge Queue** and
**Combined Check Status**. After **Check Merge Policy**, the combined status
counts only required checks ("3 of 4 required checks pass"). A check node's
context menu has **Re-request Check**; a legacy commit status cannot be
re-requested and QUILL says so. Each change asks first and reports GitHub's
confirmed result. Known refusals, such as auto-merge being turned off for the
repository, are said as what to do next.

## Line comments, the timeline and reactions

| Where | Key | What it does |
| --- | --- | --- |
| Review, top line | none | The pull request in one sentence, said once on open |
| Review | Alt+L | Changed since my last review: only files changed since your reviewed commit |
| Review | Alt+T | Timeline: one line per event, newest last |
| Diff | Alt+P | Patch lines, one row per line; Shift with arrows selects a run |
| Diff | Alt+L | Comment on This Line (Enter on one line) |
| Diff | Alt+S | Comment on Lines (Enter on a run, or type a start and end) |
| Diff | Alt+M | Line marks: words or symbols |
| Diff | Alt+C, Alt+O | Copy Diff; Open Diff in Default App |
| Comment | Alt+S, Alt+A, Alt+P | Suggest a change; Add to Review; Post Now |

The summary comes from one GraphQL query (`reviewDecision`,
`statusCheckRollup`, unresolved `reviewThreads`, `autoMergeRequest`,
`mergeStateStatus`, and `baseRef.compare` for a same-repository branch). Its
readiness phrase goes through the same rules as the review header, so partial
or unknown data reads as "merge readiness unknown", never as ready. The
query takes aliases, so several pull requests can share one request.

A line comment posts through `POST /pulls/{n}/comments` with `commit_id`,
`path`, `line`, `side` and, for a range, `start_line` and `start_side`. Add to
Review keeps it in a per-account local file, pinned to the head it was written
on. Compose Review sends the review and every pending comment in one
`POST /pulls/{n}/reviews`, and refuses when the head has moved since. The
outline lists pending comments, each with Edit and Delete (Delete asks first).

Changed since my last review reads the account's latest review `commit_id`
and compares it with the head (`GET /compare/{reviewed}...{head}`). A missing
commit, after a force-push, is said plainly and the filter shows every file.

The timeline reads `GET /issues/{n}/timeline`, up to five pages of 100, and
says when it stopped early. Reactions list, add and remove through the REST
reactions endpoints for issues, issue comments and review comments; removal
deletes only the signed-in account's own reaction. Counts read in words in
comment details ("3 thumbs up, 1 heart").

## Search, insights and repository actions

| Where | Key | What it does |
| --- | --- | --- |
| Explore, View | Alt+V | Code search, Commit search, Repository search |
| Explore | Alt+G | The query; GitHub qualifiers such as `repo:` work |
| Explore, repository views | Alt+R | Insights, Community profile checklist, Actions caches, Secret and variable names |
| Explore, context menu | Shift+F10 | Repository Actions submenu; Follow, Unfollow; Delete Cache |
| Items or Explore | Ctrl+Shift+L | GitHub API Rate Limit, said as one sentence |

Searches go to `/search/code` (with the text-match media type),
`/search/commits` and `/search/repositories`. A code row reads as the path, the
line of the excerpt holding the match and the matched words; the detail holds
each excerpt. GitHub gives no file line number, so none is claimed.

Insights reads `traffic/views`, `traffic/clones`, `traffic/popular/referrers`,
`traffic/popular/paths` and `contributors`. The first row is the whole picture
in one sentence; every other row is one figure set ("Views on 2026-11-01: 120
views, 30 unique visitors"), so the list is the numbers table. A 403 on
traffic is said as needing push access, and the contributors still load. The
community profile reads `community/profile` as present or missing for each
checklist item, after the health percentage.

Repository Actions: Sync Fork with Upstream (`POST /merge-upstream`, with the
upstream's lead counted first through `compare` so the result can say "Merged
3 commits"; "Already up to date" when GitHub reports no merge), Set Topics
(`PUT /topics`, checked locally first), Watch Level (`/subscription`; Releases
only is not in GitHub's API, so it opens the repository page), Archive and
Unarchive (`PATCH` with `archived`, refused if the reply disagrees), Create
Repository from This Template (`POST /generate`) and Delete Repository, which
needs the full name typed exactly. Secret and variable names come from the
repository and each environment; values are dropped as the reply is read.

## Releases and issue housekeeping

| Where | Key | What it does |
| --- | --- | --- |
| Items, Releases | Actions or Shift+F10 | Edit Release, Upload Asset, Delete Asset (inside a release) |
| Edit Release | Alt+N, Alt+O | Name; notes |
| Edit Release | Alt+D, Alt+P | Draft (clear it to publish); Pre-release |
| Items, issue or PR | Shift+F10 | Housekeeping submenu |
| Reorder Sub-issues | Alt+U, Alt+D | Move Up; Move Down |

Edit Release finds the release again by tag (drafts have no tag URL) and sends
`PATCH /releases/{id}`; the sentence it says is built from GitHub's reply, and a
publish GitHub did not perform is reported as such. Upload Asset posts to
`uploads.github.com/.../releases/{id}/assets?name=` with redirects refused,
reading the file in blocks so progress is said at 25, 50 and 75 percent.
Delete Asset sends `DELETE /releases/assets/{id}` after a confirmation.

Housekeeping: Lock (`PUT /issues/{n}/lock` with the reason) and Unlock;
Transfer (`transferIssue`), Pin and Unpin (`pinIssue`, `unpinIssue`) and Set
Issue Type (`issueTypes`, `updateIssueIssueType`) through GraphQL; Reorder
Sub-issues sends `PATCH /sub_issues/priority` with the neighbour's ID and reads
the order back, so the list shows what GitHub holds.

## Rate limits and conditional requests

`rate_limits.py` keeps the latest `X-RateLimit-*` headers from every REST reply.
The readout reads `GET /rate_limit` (free) and GraphQL `rateLimit`. Notification
polling doubles its interval under a quarter of the allowance, quadruples it
under a tenth, and waits for the reset at zero. A secondary limit (`Retry-After`,
or a 403 or 429 naming one) is recorded once; until it passes, every request
stops before the network with "GitHub asked QUILL to wait 60 seconds", and
Explore folds the warnings it caused into that one sentence.

`conditional_requests.py` keeps the last ETag and body of each repeated read
per account (64 reads, 256 KB each, in `github_etag_cache.json`) and sends
`If-None-Match`; a 304 shows the stored body and costs no rate limit. Explore
says "No changes since the last load" when a reload found the same rows.

## Review and write safety

The review tree announces reply counts, outdated positions, resolved state,
and check status. Selecting a thread never resolves it. Reply, resolve, reopen,
review submission, branch updates, and other writes each require a deliberate
command and confirmation where appropriate. Actions are disabled if the PR is
closed, the account is signed out, or GitHub denies that permission. If the
review-thread state cannot be retrieved, threads remain readable while
resolution controls are unavailable. Refresh to observe changes made elsewhere.

The Items **Batch** menu operates on checked issue or PR rows. Its confirmation
names the targeted items. Visibility changes, merges and branch deletion have
stronger typed confirmations in QUILL's administration flows, and Delete
Repository in Explore (both apps) needs the repository's full name typed. QUILL Lite currently shares the Items, Explore, diff, and review surfaces;
the separate repository administration and Local Git menus still belong to
QUILL. This product difference is tracked in the workbench plan.

## Architecture and verification

The Items and review windows use `quill/core/github/items_provider.py` and
`pr_review.py`; review resolution uses `review_graphql.py`, line mapping uses
`diff_hunks.py`, and job log retrieval uses `workflow_job_logs.py`. Explore
uses `explore.py`; pinned repositories, favorites, recent repositories, and
saved queries use `saved_items.py`. Notifications triage is
`notification_triage.py` and `explore_notifications.py`; the failure digest is
`run_failure_digest.py`; run, check and deployment actions are `run_actions.py`;
auto-merge and the merge queue are `merge_automation.py`. Wave 4 adds
`search_views.py`, `repo_insights.py`, `repo_actions.py`, `release_admin.py`,
`issue_housekeeping.py`, `rate_limits.py` and `conditional_requests.py`, with
Explore's routing in `explore_extra_views.py`. The REST calls
PyGithub lacks go through `rest_transport.py`, which refuses redirects so the
token stays on api.github.com. The shared UI modules are under `quill/ui/`.
Network calls are made off the UI thread. Tests exercise provider mapping,
pagination, diff-line matching, redirect token handling, and action routing.
Manual Windows screen-reader acceptance with NVDA, JAWS, and Narrator is
user-owned follow-up. This reference does not claim a macOS assistive-technology
acceptance matrix.

For a guided walkthrough, read [Tutorial 8](../tutorials/08-github-inside-quill.md).
