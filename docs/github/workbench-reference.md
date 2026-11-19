# GitHub Workbench: keyboard and screen reader reference

This is the technical reference: what each window does and which part of
GitHub it calls. For a book on doing the work, written for screen-reader
users, read [The GitHub Guide for QUILL and QUILL Lite](https://www.quillforall.org/docs/github-guide.html),
which ships with both editors.

**The GitHub Workbench is the only GitHub management window (2026-11-10).**
Every GitHub door in both editors opens one window,
`quill/ui/workbench_frame.py` with the GitHub provider
`quill/ui/github_workbench_window.py`; its tree, menus, keys, context menus,
options and glossary are generated at the end of this page. The separate
Items and Explore management windows and their fallback preference are retired.

QUILL and QUILL Lite share the Workbench. QUILL Lite opens it from
**File > GitHub Workbench** (**Alt+F**, then **G**). In QUILL, use
**File > Open from Remote > GitHub Items**. Public repository reading works
without an account. Account views and writes require a signed-in GitHub
account. Safe Mode and first-use network consent still apply.

**GitHub Workbench Mode.** **View > GitHub Workbench Mode** (**Alt+V**, then
**K**), a per-window check item in both editors, adds a **GitHub** menu
(**Alt+G**) right after Tools and moves the GitHub rows of File > Open from
Remote and Tools > Git and GitHub into it; turning it off puts them back. Both
editors build it from one wx-free table, `quill/core/github/workbench_menu.py`
(QUILL: `quill/ui/main_frame_github_menu.py`; QUILL Lite:
`quill/apps/lite_github_workbench.py`, which also serves the empty window).
QUILL Lite's menu is the table less QUILL's own rows. Rows keep their command
ids, so a user-bound key follows the row; nothing in the mode has a default
chord. New entry points open a view directly: Inbox, My Work and Notifications
open Explore on `attention`, `my_work` and `notifications`; Issues and Pull
Requests, Actions Runs and Releases open Items on `issues`, `runs` and
`releases` (the new `initial_view` argument); Explore GitHub opens Explore on
its default. They are `quill/ui/github_workbench_commands.py`, shared, and go
through each editor's existing opener and gates. The switch announces
"Workbench mode on. GitHub menu added." and "Workbench mode off." through the
announcement service; nothing else in the mode speaks. While it is on, both
editors' status bars carry a **Workbench** cell ("Workbench: owner/name", or
"Workbench" with no repository), worded once in `workbench_menu`
(`STATUS_CELL_KEY`, `status_cell_text`): QUILL's in
`quill/ui/main_frame_github_status.py` (a `workbench` item in
`STATUS_BAR_ITEMS`, hidden by default and shown only in the mode), QUILL Lite's
in `quill/apps/lite_status_cells.py` (shown only with text). It is reached with
F6 and the arrow keys like every cell and is never announced (GATE-13); the
repository is looked up once per document path while the mode is on. It is not
remembered across sessions. In QUILL the mode needs GitHub Remote Access
(`core.github_remote`), which since 2026-11-08 no longer depends on
`core.developer`.

**Clone Repository.** QUILL: **File > Open from Remote > Clone Repository...**;
QUILL Lite: **File > Clone Repository...** (**Alt+F**, then **Y**); both:
**GitHub > Clone Repository...** in workbench mode. Shared window
`quill/ui/github_clone.py`, core `quill/core/github/clone.py`. Git is found by
`quill.core.git_binaries.find_git`: `QUILL_GIT` (dev builds only), then
`<runtime>/mingit/cmd/git.exe`, then `git` on `PATH`, then the optional
component copy. It runs `git clone -- <url> <folder>` through
`run_subprocess_safely` (argv, no shell) on the task manager. For an https
github.com clone the signed-in token travels only in the child's environment,
as `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` setting
`http.https://github.com/.extraheader` for that process; it is never in argv,
`.git/config`, the remote URL or the log, and it is registered with
`redaction.remember_secret`. `GIT_TERMINAL_PROMPT=0` stops a hidden password
prompt. An address with a user name or password in it is refused. With no git,
one sentence offers the Git for Windows download page.

**Signing in.** Manage GitHub Accounts (QUILL: **File > Open from Remote**;
QUILL Lite: **File**, **Alt+F** then **H**) offers **Sign In with GitHub...**
first, and as the default button while no account is saved. It is GitHub's
OAuth device flow (`quill/core/github/oauth_sign_in.py`, UI in
`quill/ui/github_device_sign_in.py`): QUILL posts to
`github.com/login/device/code` with the app's own OAuth client id (the same
per-app registration My GitHub Copilot uses, `copilot_auth.CLIENT_IDS`), puts
the user code on the clipboard and in a read-only field that takes focus,
opens `github.com/login/device`, and polls `github.com/login/oauth/access_token`
at GitHub's interval on a worker thread, adding five seconds on `slow_down`.
Expiry, a declined request, Cancel and a network failure each end in one
sentence in the step's What to do field. The token is then checked with
`GET /user` and saved with `save_github_account`, exactly like a pasted token,
in the same store as every other account; Copilot's token stays in its own
entry. The scopes requested are `repo workflow gist read:org project
security_events user:follow delete_repo`, each justified beside
`WORKBENCH_SCOPES`, so one sign-in covers every Workbench command. **Add Token (Advanced)...** keeps the pasted-token route for
fine-grained or limited tokens; the guides teach it only in chapter 10,
"Advanced: using a token". Organizations that restrict OAuth apps must
approve QUILL once (Settings > Applications > Authorized OAuth Apps >
Request or Grant).

**Tokens (2026-11-08).** Each account records how it was added
(`added_by`: `sign_in`, `token`, or `unknown` for accounts saved before) and a
small state (`account_state` in `github-accounts.json`, never a secret): whether
the sign-in suggestion was shown, the token's expiry as GitHub reported it, and
the day the expiry was last mentioned. `quill/core/github/token_health.py`
decides both messages. The **suggestion**: when the active account has a
classic token (`ghp_`, or `X-OAuth-Scopes` on a pasted one) with a broad scope,
Manage GitHub Accounts says "This account uses a token. Sign In with GitHub is
easier to keep up to date." once, then asks; Yes opens Sign In with GitHub, No
opens the window as usual, and it is never asked again for that account. The
**expiry warning**: `TOKEN_EXPIRY` records `GitHub-Authentication-Token-Expiration`
from every REST reply and every items-provider repository read (the token as a
SHA-256 fingerprint, in memory); each editor's Workbench gate calls
`quill/ui/github_token_expiry.py`'s `watch_token_expiry`, which, for a token
expiring within seven days or already expired (the latter from the filed
expiry, since a dead token's replies carry no header), says one sentence at most
once a day per account and adds a Notifications entry whose target
`github-accounts` opens Manage GitHub Accounts. No new network endpoint: both
read headers of replies the Workbench already receives.

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

## Repository files, blame and history

**Files** (Alt+F) in Items, or **Browse Repository Files** on its context menu,
opens Repository Files: a real tree of the repository at a branch, tag or commit
typed or picked in **Branch, tag or commit** (Alt+B). Right arrow or Enter opens
a folder (fetched the first time), Left closes it, and each file says its size.
Enter on a file or **View File** (Alt+V) shows it read-only in **Contents**.
**Open in Editor** (Alt+E) opens it for editing: QUILL uses the same path as a
GitHub file link, so Commit to GitHub works afterwards; QUILL Lite opens the text
as a new untitled document. **README** (Alt+R) shows the selected folder's or
the repository's README. Binary files and files over GitHub's 1 MB contents
limit say so instead of showing text.

**History** (Alt+H) lists the commits that changed the selected path. **Blame**
(Alt+L) lists the file in runs, neighbouring ranges from one commit joined into
one: "Lines 10 to 14: author, date, short SHA, commit title". In both lists
Alt+N and Alt+P move to the next and previous row from anywhere in the window,
and Enter or **Open Commit** (Alt+O) opens the commit on GitHub. Blame uses
GraphQL `blame(path:)` on the commit and needs a signed-in account.

## Milestones and batch changes

**Milestones** in Items (no access key; Tab to it, or use the context menu)
lists milestones as words: "Release 2.0: 61 percent done, 5 open, 8 closed, due
12 December". **Show** (Alt+S) picks open, closed or all. **New** (Alt+N) and
**Edit** (Alt+E) take a title, description and a year-month-day due date;
**Close Milestone** or **Reopen Milestone** (Alt+L) asks first. Every change is
reported from GitHub's reply.

The **Batch** menu adds **Set milestone** (the open milestones, or clear it) and
**Add assignees** (usernames separated by commas) beside Close, Reopen and Add
label. The confirmation names the items; the result counts what GitHub
confirmed, and names anyone GitHub did not assign.

## Discussions and security triage

In Explore's Discussions view, Enter (or **Open Discussion Thread** on the
context menu) opens a thread window: the discussion, then each comment followed
by its replies. It says "Answered by" and the name, and reads a poll one option
to a line ("Option A: 12 votes, 40 percent"). **Reply** (Alt+R) comments on the
discussion or replies under the selected comment; **Mark as Answer** (Alt+M)
marks or unmarks the selected comment after asking, when the category takes
answers and GitHub says you may. **New Discussion** on the view's context menu
picks a category and takes a title and body.

In the security views, **Dismiss Alert** on the context menu offers GitHub's own
reasons for that alert kind (Dependabot: `fix_started`, `inaccurate`,
`no_bandwidth`, `not_used`, `tolerable_risk`; code scanning: `false positive`,
`won't fix`, `used in tests`; secret scanning: `false_positive`, `wont_fix`,
`revoked`, `used_in_tests`), an optional comment of up to 280 characters, and a
confirmation. **Dismissed and resolved security alerts** is its own view, where
**Reopen Alert** asks and then reopens. QUILL reports a change only when the
alert's new state comes back from GitHub.

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

## Copilot, commit comments, gists and queue summaries

| Where | Key | What it does |
| --- | --- | --- |
| Review, pull request node | Shift+F10 | Request Copilot Review |
| Items, issue | Shift+F10 | Assign to Copilot (checks, then asks) |
| Items, commit | Shift+F10 | Commit Comments |
| Commit Comments | Alt+C, Alt+M | Comments; selected comment |
| Commit Comments | Alt+N, Alt+F, Alt+L | New comment; file; line |
| Commit Comments | Alt+P, Alt+R | Post Comment; Refresh |
| Explore, My gists | Shift+F10 | New Gist, Edit Gist, Star, Unstar, Delete Gist |
| Gist window | Alt+D, Alt+B | Description; Public gist (new gists only) |
| Gist window | Alt+F, Alt+T | Files; File text |
| Gist window | Alt+A, Alt+N, Alt+L | Add File; Rename File; Delete File |

Request Copilot Review sends `POST /pulls/{n}/requested_reviewers` with
`copilot-pull-request-reviewer[bot]`, the login GitHub's Copilot code review
documentation names for the REST API, and reads the reply's
`requested_reviewers` back: GitHub can answer 201 and leave Copilot off, which
is how an account or repository without Copilot code review answers, and QUILL
says so rather than reporting a request. A 422 is said as "Copilot code review
may not be available".

Assign to Copilot follows GitHub's "Using Copilot cloud agent via the API". One
GraphQL query reads `suggestedActors(capabilities: [CAN_BE_ASSIGNED])` and the
issue's ID, state and assignees; without `copilot-swe-agent` among the actors,
QUILL says the coding agent is not available and sends nothing. Otherwise it
asks, then sends `replaceActorsForAssignable` with the existing assignees' IDs
plus the agent's, so nobody already assigned is dropped. Both calls carry
`GraphQL-Features: issues_copilot_assignment_api_support,coding_agent_model_selection`.
Success is said only when the mutation's assignee list holds the agent.

Commit Comments reads `GET /commits/{sha}/comments` (100 a page, up to ten
pages, and says when there were more) and posts with `POST` to the same path,
sending `path` and `line` for a comment on a line; the deprecated diff
`position` is never sent.

Gists: `POST /gists`, `PATCH /gists/{id}`, `DELETE /gists/{id}`, and `PUT` or
`DELETE /gists/{id}/star`. The gist window edits a local draft (`gists.py`),
and saving sends one `PATCH` in which a deleted file is `null` and a renamed one
carries `filename`. A file GitHub truncated is never sent back. Create and save
are confirmed against the files and description GitHub returns.

The attention queue adds `pr_summary.py`'s sentence to each pull request row
from one aliased GraphQL request per refresh (`attention_queue_summaries.py`),
covering the twenty newest pull requests. It keeps the summary's rules: unknown
or partial data reads "merge readiness unknown", a pull request GitHub did not
answer for reads "Summary unavailable", and the row's reason stays the first
line of its details. A summary gap is said in the status line but does not mark
the queue itself incomplete.

## Review and write safety

The review tree announces reply counts, outdated positions, resolved state,
and check status. Selecting a thread never resolves it. Reply, resolve, reopen,
review submission, branch updates, and other writes each require a deliberate
command and confirmation where appropriate. Actions are disabled if the PR is
closed, the account is signed out, or GitHub denies that permission. If the
review-thread state cannot be retrieved, threads remain readable while
resolution controls are unavailable. Refresh to observe changes made elsewhere.
If the review's diff cannot be loaded, the threads and checks still appear and
QUILL says "Could not load the diff" with the reason. A refresh that finishes
after a newer one started is dropped, so it can never overwrite newer data.

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
auto-merge and the merge queue are `merge_automation.py`. Wave 3 adds
`repo_files.py` (folders, files, README, history, blame), `milestones.py`,
`discussion_actions.py`, `alert_triage.py` and `github_graphql.py`, whose
GraphQL calls go through the same REST transport. Wave 4 adds
`search_views.py`, `repo_insights.py`, `repo_actions.py`, `release_admin.py`,
`issue_housekeeping.py`, `rate_limits.py` and `conditional_requests.py`, with
Explore's routing in `explore_extra_views.py`. The last four add `copilot.py`,
`commit_comments.py`, `gists.py` and `attention_queue_summaries.py`. The REST calls
PyGithub lacks go through `rest_transport.py`, which refuses redirects so the
token stays on api.github.com. The shared UI modules are under `quill/ui/`.
Network calls are made off the UI thread. Tests exercise provider mapping,
pagination, diff-line matching, redirect token handling, and action routing.
Manual Windows screen-reader acceptance with NVDA, JAWS, and Narrator is
user-owned follow-up. This reference does not claim a macOS assistive-technology
acceptance matrix.

For a guided walkthrough, read [Tutorial 8](../tutorials/08-github-inside-quill.md).
For every window, key and refusal in plain words, read
[The GitHub Guide for QUILL and QUILL Lite](https://www.quillforall.org/docs/github-guide.html).

<!-- BEGIN GENERATED: python -m quill.tools.build_workbench_reference --write -->

## The GitHub Workbench window, generated

Everything below is generated from the tables the window is built from. The GitHub Workbench is the single GitHub management window in QUILL and QUILL Lite.

### The Navigator tree

| Node | Under | What it is |
| --- | --- | --- |
| Start Here (`:start`) | the top | Start Here: what the Workbench is, whether you are signed in, and the five keys to learn first. |
| Needs My Attention (`:attention`) | the top | Needs My Attention: everything waiting on you, across GitHub. Inbox first, then notifications, review requests and your own open work. |
| Inbox (`:inbox`) | attention | Inbox: one list of what needs you, from notifications, review requests, assignments and mentions. Enter opens a row; Delete marks it done. |
| Notifications (`:notifications`) | attention | Notifications: what GitHub has told you about, unread first. Ctrl+Q marks one read, Delete marks it done, and Ctrl+Shift+Q marks the whole view read. |
| Invitations (`:invitations`) | attention | Invitations: repositories you have been invited to, who invited you and with what access. Accept or Decline from a row's context menu. |
| Review Requests (`:review_requests`) | attention | Review Requests: pull requests somebody asked you to review. Enter opens the review. |
| Assigned to Me (`:assigned`) | attention | Assigned to Me: issues and pull requests assigned to you, anywhere. |
| Mentions (`:mentions`) | attention | Mentions: issues and pull requests where somebody wrote your name. |
| My Open Pull Requests (`:my_pulls`) | attention | My Open Pull Requests: pull requests you opened that are still open. |
| My Open Issues (`:my_issues`) | attention | My Open Issues: issues you opened that are still open. |
| My Activity Feed (`:my_activity`) | attention | My Activity Feed: what you did on GitHub lately, newest first. |
| Repositories (`:repositories`) | the top | Repositories: the one you are working in first, then pinned, favorites, yours, starred, watched and your organizations'. Enter on a repository opens its node. |
| Pinned (`:pinned`) | repositories | Pinned: repositories you keep at hand, on this computer. Delete takes one out; Ctrl+N pins the current repository. |
| Favorites (`:favorites`) | repositories | Favorites: issues, pull requests and other items you kept, on this computer. Ctrl+D adds or removes the selected row anywhere in the window. |
| My Repositories (`:my_repositories`) | repositories | My Repositories: the repositories your account owns or can push to. |
| Starred (`:starred`) | repositories | Starred: repositories you starred on GitHub. |
| Star Lists (`:star_lists`) | repositories | Star Lists: every repository on each of your star lists, the list's name first. Ctrl+N makes a list; Star Lists on any repository chooses its lists. |
| Watched (`:watched`) | repositories | Watched: repositories whose activity GitHub tells you about. |
| My Packages (`:packages`) | repositories | My Packages: your container images and npm, Maven, RubyGems and NuGet packages, with Delete Package Version and Delete Package on each. |
| Organizations (`:organizations`) | repositories | Organizations: the organizations you belong to. Enter on one opens its repositories. |
| Search (`:search`) | the top | Search: GitHub's searches. Choose one, type in the filter box with Ctrl+E, and press Enter. |
| Issues and Pull Requests (`:search_issues`) | search | Search Issues and Pull Requests: everything GitHub finds for the words and qualifiers in the filter box, such as is:open author:@me. Ctrl+N saves the search. |
| Code (`:search_code`) | search | Search Code: files whose text matches the filter box. Needs sign-in. |
| Commits (`:search_commits`) | search | Search Commits: commits whose message matches the filter box. |
| Security Advisories (`:search_advisories`) | search | Security Advisories: search GitHub's Advisory Database by package, CVE or GHSA id. |
| Repositories (`:search_repositories`) | search | Search Repositories: repositories whose name or description matches the filter box. |
| Saved Searches (`:saved_searches`) | search | Saved Searches: searches you kept, on this computer. Enter runs one; Delete removes it. |
| People (`:people`) | the top | People: who you follow, who follows you, and anybody you look up. |
| My Profile (`:my_profile`) | people | My Profile: your profile as GitHub shows it, your year of contributions as numbers, and what you pinned. |
| My Keys (`:my_keys`) | people | My Keys: your SSH keys, GPG keys and SSH signing keys, each with its fingerprint. Ctrl+N adds one. |
| Sponsorships (`:sponsorships`) | people | Sponsorships: who you sponsor on GitHub Sponsors, and who sponsors you. |
| People I Follow (`:following`) | people | People I Follow: accounts you follow. Enter opens a person's node. |
| My Followers (`:followers`) | people | My Followers: accounts that follow you. |
| My Teams (`:my_teams`) | people | My Teams: every team you belong to, across your organizations. Alt+Enter opens a team's sheet. |
| My Billing and Usage (`:billing_usage`) | people | Billing and Usage: this month's metered use of your account, by product, from GitHub's billing report. Read only; Enter opens your billing page. |
| Find a Person... (`:find_person`) | people | Find a Person: type a login with Ctrl+L, and the person gets a node of their own here. |
| Gists (`:gists`) | the top | Gists: small shared files and snippets. |
| My Gists (`:my_gists`) | gists | My Gists: gists you made. Enter edits one. |
| Projects (`:projects`) | the top | Projects: your Project boards. Each repository's own Projects are under it, Ctrl+Shift+7. |
| Watches (`:watches`) | the top | Watches: tell me when something happens. Each row is a rule: a run finishes on a repository or branch, a review arrives on a pull request, a new release, a new comment. They are checked on the notification check's interval in Workbench Options while this window is open, and each row says when it was last checked. Ctrl+N adds one, Enter edits, Delete removes. Watches never mark notifications read. |
| Across Repositories (`:across`) | the top | Across Repositories: the Repository Set in use, and under it its named sets, one kind of thing from every repository in the set, each name across the set, and the Fleet. Ctrl+N here edits the set's repositories. |
| Repository Sets (`:across_sets`) | across | Repository Sets: your named lists of repositories, each chosen from a checklist, made by a filter such as org:name topic:x, or every repository you can reach. Enter uses one; Ctrl+N makes one; Delete forgets one after asking. They stay on this computer. |
| Issues and Pull Requests (`:across_issues`) | across | Issues and Pull Requests, open, from every repository in the set, each row starting with its repository. Enter opens one in its repository; ] and [ move between repositories; type: and field: filters use issue types and fields. |
| Releases (`:across_releases`) | across | Releases from every repository in the set: the latest release of each, or every release from the row's menu. |
| Workflow Runs (`:across_runs`) | across | Workflow Runs from every repository in the set, newest first. |
| Commits (`:across_commits`) | across | Commits on the default branch of every repository in the set. |
| Tags (`:across_tags`) | across | Tags from every repository in the set. |
| Milestones (`:across_milestones`) | across | Milestones from every repository in the set. |
| Discussions (`:across_discussions`) | across | Discussions from every repository in the set that has them on. |
| Security Alerts (`:across_alerts`) | across | Security alerts from every repository in the set you may read them in. |
| Labels by Name (`:across_by_labels`) | across | Labels by Name: each label name across the set, where its colour and description differ and where it is missing. Make the copies the same, add it where missing, rename, merge or delete it everywhere, each with a preview and a result per repository. |
| Milestones by Name (`:across_by_milestones`) | across | Milestones by Name: each milestone title across the set, its due dates, descriptions and progress. Make them the same, close them everywhere, move their open work to another milestone or add the missing ones, each with a preview and a result per repository. |
| Topics by Name (`:across_by_topics`) | across | Topics by Name: each topic across the set and the repositories that lack it. Add it to the missing or remove it everywhere, with a preview and a result per repository; each repository's other topics are kept. |
| Rules and Branch Protection (`:across_by_rules`) | across | Rules and Branch Protection: each ruleset by name, and each default branch's protection, compared across the set. Make them the same as the winner, add a ruleset where it is missing, or promote one to an organization ruleset; each needs admin access and shows a preview first. |
| Fleet (`:across_fleet`) | across | Fleet: one line per repository in the set: the exact revision of its default branch, checks, open pull requests, latest release and alerts, and when it was read. A repository that could not be read keeps its line, with the reason. |
| Help and Learning (`:help`) | the top | Help and Learning: the guide, the GitHub words, the keys, what changed, and tasks in plain words that take you to the place. |
| Do Something (`:help_tasks`) | help | Do Something: tasks in plain words. Enter reads one; Take Me There, on its context menu, goes to the place it is about. |
| The Guide (`:help_guide`) | help | The Guide: the GitHub Workbench Guide's chapters. Ctrl+F1 opens the guide at the chapter for where you are. |
| Words (`:help_words`) | help | Words: the GitHub glossary. Type a word to jump to it; the details say what it means and where you meet it. |
| Keys (`:help_keys`) | help | Keys: every key in the Workbench, grouped by what it does. |
| Tutorials (`:help_tutorials`) | help | Tutorials: the GitHub lessons, each with where you are in it. Enter opens one; Walk Me Through It says it here, one step at a time. |
| What Changed (`:help_changes`) | help | What Changed: what is new in the GitHub Workbench in this version. |
| Tips (`:help_tips`) | help | Tips: QUILLBert's tips, one short thing worth trying each. They wait here and are never pushed at you. |
| Ask a Person (`:help_ask`) | help | Ask a Person: write to support@community-access.org. Nothing is sent until you send it from your own email. |
| People and Organizations (`:search_people`) | search | Search People and Organizations: accounts whose name or login matches the filter box, such as jeff or type:org location:Tucson. Enter opens one. |
| Topics (`:search_topics`) | search | Search Topics: GitHub topics matching the filter box, with what each is about. Add one to a repository on its Properties. |
| My Codespaces (`:my_codespaces`) | repositories | My Codespaces: every codespace of yours. Start, Stop, Change Machine, Export to a Branch and Delete are on each row. |
| My Codespaces Secrets (`:my_codespaces_secrets`) | people | My Codespaces Secrets: values given to your own codespaces. |
| My Email Addresses (`:my_emails`) | people | My Email Addresses: the addresses on your account. Ctrl+N adds one. |
| My Social Accounts (`:my_social_accounts`) | people | My Social Accounts: the links on your profile. |
| Blocked People (`:my_blocks`) | people | Blocked People: who cannot follow you or take part in your repositories. |
| My Followers (`:my_followers`) | people | My Followers: who follows you on GitHub. |
| My Issue Types (`:my_issue_types`) | people | My Issue Types: the kinds of issue your own repositories offer. |
| My Organizations' Memberships (`:my_org_memberships`) | people | My Organizations' Memberships: your role in each organization, and invitations. |
| My Issue Fields (`:my_issue_fields`) | people | My Issue Fields: values your own repositories' issues can carry. Ctrl+N adds one. |
| My Installed Apps (`:my_installations`) | people | My Installed Apps: the GitHub Apps installed where you can manage them. Repositories... chooses which repositories an app may reach. |
| My Public Email Addresses (`:my_public_emails`) | people | My Public Email Addresses: the addresses anyone can see on your profile. |
| Repositories I Watch (`:my_watching`) | people | Repositories I Watch: every repository you get notifications for. |
| Gists I Starred (`:my_starred_gists`) | gists | Gists I Starred: gists you starred, newest first. |
| Licences (`:licenses`) | repositories | Licences: the open source licences GitHub offers a new repository. |
| .gitignore Templates (`:gitignore_templates`) | repositories | .gitignore Templates: lists of files to leave out, offered to a new repository. |
| Codes of Conduct (`:codes_of_conduct`) | repositories | Codes of Conduct: the codes of conduct GitHub offers a repository. |
| owner/name (`repository:repository`) | repository | A repository: its issues, pull requests, actions, code, releases and settings, each a node below. Ctrl+Shift+1 to Ctrl+Shift+0 jump to them. |
| Overview (`repository:overview`) | repository, repository | Overview: the repository's README, description and community profile. |
| Issues (`repository:issues`) | repository, repository | Issues: this repository's open issues. Ctrl+N files a new one; Delete closes the selected one after asking. |
| Pull Requests (`repository:pulls`) | repository, repository | Pull Requests: this repository's open pull requests. Enter opens the review; Ctrl+Shift+D lists the changed files. |
| Issues and Pull Requests (`repository:issues_and_pulls`) | repository, repository | Issues and Pull Requests: both in one list, newest first, the way an inbox reads. |
| Discussions (`repository:discussions`) | repository, repository | Discussions: the repository's conversations that are not issues. A poll shows in the details as a table; Vote... casts your vote. |
| Merge Queue (`repository:merge_queue`) | repository, repository | Merge Queue: the default branch's merge queue in order, each pull request's state. |
| Actions (`repository:actions`) | repository, repository | Actions: the repository's workflow runs, workflows and caches. |
| Runs (`repository:runs`) | repository, actions | Runs: each time a workflow ran. Enter shows its jobs and logs; Ctrl+Shift+W says what failed; Ctrl+Shift+F5 re-runs the failed jobs. |
| Workflows (`repository:workflows`) | repository, actions | Workflows: the automations defined in the repository. |
| Runners (`repository:runners`) | repository, actions | Runners: the machines this repository runs its own jobs on, online or not, busy or idle, with their labels. Only administrators can see them. |
| Caches (`repository:caches`) | repository, actions | Caches: files Actions kept between runs. Delete removes one. |
| Code (`repository:code`) | repository, repository | Code: files, branches, commits, tags, and the upstream of a fork. |
| Files (`repository:files`) | repository, code | Files: the repository's files on its default branch, a folder at a time. Enter opens a folder, or a file in the editor. |
| Branches (`repository:branches`) | repository, code | Branches: lines of work. Enter lists a branch's commits. |
| Commits (`repository:commits`) | repository, code | Commits: saved changes, newest first. |
| Tags (`repository:tags`) | repository, code | Tags: names for particular commits, usually versions. |
| Upstream (`repository:upstream`) | repository, code | Upstream: the repository this one was forked from. Forks only. |
| Releases (`repository:releases`) | repository, repository | Releases: published versions and their files. Enter lists the files. |
| Labels (`repository:labels`) | repository, repository | Labels: tags for issues and pull requests. Enter finds the issues. |
| Milestones (`repository:milestones`) | repository, repository | Milestones: goals with a date. Enter lists the issues and pull requests in one. |
| Templates (`repository:templates`) | repository, repository | Templates: issue forms, Markdown templates, the chooser, pull request templates, discussion forms and community files, including those inherited from the owner's .github repository. Enter builds or edits one; Ctrl+N starts a new one. |
| Projects (`repository:repo_projects`) | repository, repository | Projects: this repository's Project boards. |
| Activity (`repository:activity`) | repository, repository | Activity: what happened in the repository lately. |
| People (`repository:people`) | repository, repository | People: contributors, forks, and who has access. |
| Contributors and People (`repository:contributors`) | repository, people | Contributors and People: who has worked on the repository. |
| Forks (`repository:forks`) | repository, people | Forks: copies of this repository on other accounts. |
| Collaborators and Team Access (`repository:access`) | repository, people | Collaborators and Team Access: who may do what here. |
| Insights (`repository:insights`) | repository, repository | Insights: traffic, contributors and the community profile. |
| Traffic and Contributors (`repository:traffic`) | repository, insights | Traffic and Contributors: views, clones and who contributes. |
| Health Snapshot (`repository:health`) | repository, insights | Health Snapshot: extra activity data, loaded only when you turn it on in Workbench Options. |
| Community Profile (`repository:community`) | repository, insights | Community Profile: the README, license and guidelines GitHub checks. |
| Commit Activity (`repository:commit_activity`) | repository, insights | Commit Activity: GitHub's statistics graphs as rows: commits and lines each week, the busiest hours, and each contributor's lines. |
| Deployments and Environments (`repository:deployments`) | repository, repository | Deployments and Environments: where the code was deployed. |
| Wiki (`repository:wiki`) | repository, repository | Wiki: whether the wiki is on. Enter opens it on GitHub; Clone Wiki copies its pages to a folder to edit. |
| GitHub Pages (`repository:pages`) | repository, repository | GitHub Pages: the website built from this repository. |
| Security (`repository:security`) | repository, repository | Security: alerts about vulnerable code and leaked secrets. |
| Policy (`repository:security_policy`) | repository, security | Policy: where the security policy is, and whether vulnerabilities can be reported privately. |
| Alerts (`repository:alerts`) | repository, security | Alerts: open security alerts. Enter reads one. |
| Dismissed and Resolved Alerts (`repository:alerts_closed`) | repository, security | Dismissed and Resolved Alerts: alerts no longer open. |
| Advisories (`repository:advisories`) | repository, security | Advisories: this repository's security advisories. New Here reports a vulnerability or drafts an advisory. |
| Settings (`repository:settings`) | repository, repository | Settings: names of secrets, branch protection and general settings. |
| Secret and Variable Names (`repository:secrets`) | repository, settings | Secret and Variable Names: the names only; GitHub never shows values. |
| Branch Protection (`repository:branch_protection`) | repository, settings | Branch Protection: who may change a branch and what a change needs first. Enter opens the setting. |
| General (`repository:general`) | repository, settings | General: the name, visibility and default branch. Enter opens one. |
| Webhooks (`repository:webhooks`) | repository, settings | Webhooks: the addresses GitHub tells about events here. Ctrl+N adds one; Recent Deliveries on a webhook says what was sent and redelivers it. |
| Deploy Keys (`repository:deploy_keys`) | repository, settings | Deploy Keys: SSH keys that let a server clone, pull or push this one repository. Ctrl+N adds one. |
| Autolinks (`repository:autolinks`) | repository, settings | Autolinks: prefixes such as BUG- that GitHub turns into links. Ctrl+N adds one. |
| Environments (`repository:environments`) | repository, settings | Environments: where this repository's workflows deploy, each with its protection rules. Secrets... and Variables... on a row are that environment's own. |
| Codespaces (`repository:repo_codespaces`) | repository, code | Codespaces: your codespaces for this repository. Ctrl+N makes one on a branch you name, with the machine and dev container you choose. |
| Pinned (spotlight) (`repository:discussions_pinned`) | repository, discussions | Pinned (spotlight): the discussions pinned at the top of Discussions, in GitHub's order. Read only: GitHub's API cannot pin, unpin or reorder one. |
| Categories (`repository:discussion_categories`) | repository, discussions | Categories: the repository's discussion categories, grouped by section where GitHub gives sections; Enter lists a category's discussions. |
| Actions Variables (`repository:actions_variables`) | repository, settings | Actions Variables: values workflows read as vars.NAME. Ctrl+N adds one. |
| Actions Secrets (`repository:actions_secrets`) | repository, settings | Actions Secrets: values workflows read but nobody sees again. Ctrl+N adds one. |
| Dependabot Secrets (`repository:dependabot_secrets`) | repository, settings | Dependabot Secrets: what Dependabot uses to reach private registries. |
| Codespaces Secrets (`repository:codespaces_secrets`) | repository, settings | Codespaces Secrets: values given to every codespace of this repository. |
| Copilot Agent Secrets (`repository:agent_secrets`) | repository, settings | Copilot Agent Secrets: values the Copilot coding agent may use here. |
| Copilot Agent Variables (`repository:agent_variables`) | repository, settings | Copilot Agent Variables: values the Copilot coding agent reads here. |
| Artifacts (`repository:artifacts`) | repository, actions | Artifacts: files workflow runs kept, such as builds and test reports. |
| Invitations (`repository:repo_invitations`) | repository, people | Invitations: people asked to join this repository who have not answered yet. |
| Issue Types (`repository:repo_issue_types`) | repository, settings | Issue Types: the kinds of issue this repository offers, set by its organization. |
| Code Scanning Analyses (`repository:code_scanning_analyses`) | repository, security | Code Scanning Analyses: each upload of results, newest first. Deleting one removes its results; GitHub refuses the last analysis of a tool unless asked. |
| CodeQL Databases (`repository:codeql_databases`) | repository, security | CodeQL Databases: the databases code scanning built, one per language. |
| Organization Secrets Here (`repository:repo_org_secrets`) | repository, settings | Organization Secrets Here: the organization's Actions secrets this repository may use. Change them in the organization. |
| Organization Variables Here (`repository:repo_org_variables`) | repository, settings | Organization Variables Here: the organization's Actions variables this repository may use. Change them in the organization. |
| All Issue Comments (`repository:repo_issue_comments`) | repository, activity | All Issue Comments: every comment on the repository's issues, newest changes last. |
| Commit Comments (`repository:commit_comments`) | repository, code | Commit Comments: comments on the repository's commits. Change rewrites your own. |
| Watchers (`repository:repo_watchers`) | repository, people | Watchers: who gets notifications for this repository. |
| Push Activity (`repository:repo_push_activity`) | repository, activity | Push Activity: pushes, force pushes, merges and branch changes, newest first. |
| CODEOWNERS Problems (`repository:codeowners_errors`) | repository, settings | CODEOWNERS Problems: lines in the CODEOWNERS file GitHub could not use. |
| Rule Insights (`repository:repo_rule_insights`) | repository, settings | Rule Insights: recent pushes the rulesets here passed, blocked or let through. |
| My Notifications Here (`repository:repo_my_notifications`) | repository, activity | My Notifications Here: your notifications from this repository only. |
| Custom Property Values (`repository:repo_property_values`) | repository, settings | Custom Property Values: the organization's custom properties, as set here. |
| person (`person:person`) | person | A person: their repositories, activity, followers and who they follow. |
| Profile (`person:person_profile`) | person, person | Profile: who this person is, their year of contributions as numbers, and what they pinned. |
| Sponsor (`person:person_sponsor`) | person, person | Sponsor: whether this person takes sponsorships, and each tier with its price. |
| Repositories (`person:person_repositories`) | person, person | Repositories: this person's public repositories. |
| Activity (`person:person_activity`) | person, person | Activity: what this person did lately on GitHub. |
| Followers (`person:person_followers`) | person, person | Followers: who follows this person. |
| Following (`person:person_following`) | person, person | Following: who this person follows. |
| Packages (`person:person_packages`) | person, person | Packages: this person's public packages. Show Versions lists each one's versions. |
| SSH Keys (`person:person_keys`) | person, person | SSH Keys: the public keys this person signs in to Git with; useful to check one before giving them access to a server. |
| GPG Keys (`person:person_gpg_keys`) | person, person | GPG Keys: the keys GitHub checks this person's signed commits against. |
| SSH Signing Keys (`person:person_signing_keys`) | person, person | SSH Signing Keys: SSH keys this person signs commits with. |
| Social Accounts (`person:person_social`) | person, person | Social Accounts: the links on this person's profile. |
| Gists (`person:person_gists`) | person, person | Gists: this person's public gists, newest first. |
| Starred (`person:person_starred`) | person, person | Starred: the repositories this person starred, newest first. |
| Watching (`person:person_watching`) | person, person | Watching: the repositories this person watches. |
| Projects (`person:person_projects`) | person, person | Projects: this person's public Projects. |
| People They Follow: Activity (`person:person_feed`) | person, person | People They Follow: Activity: public activity of the accounts this person follows. |
| organization (`organization:organization`) | organization | An organization: its repositories. |
| Repositories (`organization:organization_repositories`) | organization, organization | Repositories: the organization's repositories you can see. |
| Teams (`organization:organization_teams`) | organization, organization | Teams: the organization's teams, as GitHub nests them. Alt+Enter opens a team's sheet: its members and maintainers, repositories and roles, child teams and code review assignment. |
| Packages (`organization:organization_packages`) | organization, organization | Packages: this organization's container images and other packages. Ctrl+N restores one deleted in the last 30 days. |
| Webhooks (`organization:organization_webhooks`) | organization, organization | Webhooks: the addresses GitHub tells about events across this organization. Ctrl+N adds one. |
| Templates (`organization:organization_templates`) | organization, organization | Templates: the defaults in the organization's .github repository, which every repository without its own uses. Enter builds or edits one. |
| Actions Variables (`organization:org_actions_variables`) | organization, organization | Actions Variables: values every chosen repository's workflows read. |
| Actions Secrets (`organization:org_actions_secrets`) | organization, organization | Actions Secrets: values the organization's workflows read but nobody sees again. |
| Dependabot Secrets (`organization:org_dependabot_secrets`) | organization, organization | Dependabot Secrets: what Dependabot uses across the organization. |
| Codespaces Secrets (`organization:org_codespaces_secrets`) | organization, organization | Codespaces Secrets: values given to the organization's codespaces. |
| Copilot Agent Secrets (`organization:org_agent_secrets`) | organization, organization | Copilot Agent Secrets: values the coding agent may use in the organization. |
| Copilot Agent Variables (`organization:org_agent_variables`) | organization, organization | Copilot Agent Variables: values the coding agent reads in the organization. |
| Runner Groups (`organization:runner_groups`) | organization, organization | Runner Groups: which repositories may use which of the organization's runners. |
| Runners (`organization:org_runners`) | organization, organization | Runners: the organization's own machines that run jobs. |
| Larger Runners (`organization:hosted_runners`) | organization, organization | Larger Runners: GitHub's bigger machines the organization pays for. |
| Members (`organization:org_members`) | organization, organization | Members: the organization's people. Ctrl+N invites someone; Delete removes them. |
| Invitations (`organization:org_invitations`) | organization, organization | Invitations: people asked to join the organization who have not answered. |
| Blocked People (`organization:org_blocks`) | organization, organization | Blocked People: who cannot take part in the organization's repositories. |
| Outside Collaborators (`organization:outside_collaborators`) | organization, organization | Outside Collaborators: people with access to repositories but not members. |
| Security Managers (`organization:security_managers`) | organization, organization | Security Managers: teams that see and manage every security alert. |
| Custom Properties (`organization:custom_properties`) | organization, organization | Custom Properties: labels the organization gives its repositories. |
| Issue Types (`organization:org_issue_types`) | organization, organization | Issue Types: the kinds of issue, such as Bug, the organization's repositories offer. |
| Organization Roles (`organization:org_roles`) | organization, organization | Organization Roles: the roles that can be given to people and teams. |
| Code Scanning Alerts (`organization:org_code_scanning_alerts`) | organization, organization | Code Scanning Alerts: every repository's code scanning alerts in one list. Open a repository's Alerts to dismiss one. |
| Issue Fields (`organization:org_issue_fields`) | organization, organization | Issue Fields: values every repository's issues in this organization can carry, such as Priority or Due date. Ctrl+N adds one. |
| Failed Invitations (`organization:org_failed_invitations`) | organization, organization | Failed Invitations: invitations that expired or could not be delivered. |
| Public Members (`organization:org_public_members`) | organization, organization | Public Members: members who show their membership on their profile. |
| Installed Apps (`organization:org_installations`) | organization, organization | Installed Apps: the GitHub Apps installed on this organization. |
| Immutable Releases: Repositories (`organization:org_immutable_release_repos`) | organization, organization | Immutable Releases: Repositories: where published releases cannot be changed, when the organization enforces it on chosen repositories. Ctrl+N adds one. |
| Actions: Allowed Repositories (`organization:org_actions_repos`) | organization, organization | Actions: Allowed Repositories: which repositories may run Actions, when the organization allows chosen repositories only. Ctrl+N adds one. |
| Self-hosted Runners: Allowed Repositories (`organization:org_runner_repos`) | organization, organization | Self-hosted Runners: Allowed Repositories: which repositories may use the organization's self-hosted runners. Ctrl+N adds one. |
| Dependabot Alerts (`organization:org_dependabot_alerts`) | organization, organization | Dependabot Alerts: every repository's vulnerable dependencies in one list. |
| Secret Scanning Alerts (`organization:org_secret_alerts`) | organization, organization | Secret Scanning Alerts: secrets found in any repository. The secret itself is never shown here. |
| Security Advisories (`organization:org_advisories`) | organization, organization | Security Advisories: the repository advisories across this organization. |
| Recent Events (`organization:org_events`) | organization, organization | Recent Events: the organization's public activity, newest first. |
| Custom Property Values (`organization:org_property_values`) | organization, organization | Custom Property Values: every repository's custom properties in one list. Change a repository's on its Properties. |
| Saved search (`pinned_search:pinned_search`) | pinned_search | A saved search pinned as a node: its list is the search's results, read afresh each time. Unpin Node, on its row in Saved Searches, takes the node away. |

### The menu bar and its keys

#### File

| Row | Key | What it does |
| --- | --- | --- |
| New Here... | Ctrl+N | Something new where you are: an issue in Issues, a saved search in Saved Searches. |
| New... | Ctrl+Shift+N | Choose what to create, wherever you are. |
| Open GitHub Address... | Ctrl+L | Type or paste owner/name, #42, owner/name#42 or any GitHub link to go there. |
| Go to Number... | Ctrl+G | Go to an issue or pull request in this repository by its number. |
| Open on GitHub | Shift+Enter | Open the selected row, or the node, in your browser. |
| Open in Editor | Ctrl+Enter | Open the selected file in the editor that opened this window. |
| Export List... | Ctrl+Shift+X | This list as it is shown, its columns, filter and rows, as Excel, CSV or a Markdown table the editor reads as a table. The same as the WordPress Workbench's. |
| Import Issues from a Spreadsheet... | Ctrl+Alt+I | Make issues in this repository from a CSV file or an Excel workbook: columns matched by name, a preview with a line per row, then a sentence per row. |
| New Issues from Lines... | Ctrl+Alt+L | One issue per line of the editor's selection, which you can change first, optionally each a sub-issue of an issue you name. Previewed before anything is made. |
| Close Workbench | Alt+F4 | Close this window. The editor stays. |

#### Edit

| Row | Key | What it does |
| --- | --- | --- |
| Undo GitHub Change | Ctrl+Z | Reverse your last change on GitHub, where GitHub allows it. In a text box, Ctrl+Z undoes your typing instead. |
| Redo GitHub Change | Ctrl+Y | Make the change you just undid again. |
| Copy | Ctrl+C | Copy the selected rows as text; in a text box, its own selection. |
| Copy Link | Ctrl+Shift+C | Copy the selected row's address. |
| Filter... | Ctrl+E | Move to the filter box. Ctrl+Shift+F too. |
| Filter Builder... | Ctrl+Alt+F | Build a filter one condition at a time: every attribute, an operator and a value from the repository, written into the filter box as GitHub's syntax. |
| Select All | Ctrl+A | Select every row in the list; in a text box, all its text. |

#### View

| Row | Key | What it does |
| --- | --- | --- |
| Refresh | F5 | Load this view again from GitHub. |
| Refresh Ignoring Cache | Ctrl+F5 | Load this view again, asking GitHub for everything afresh. |
| Load More | Alt+PageDown | Load the next page of rows, if GitHub has more. |
| Load All | Ctrl+Shift+PageDown | Load every page, so a filter over the loaded rows is sure to see everything. |
| Show > Issues | (submenu letter) | Show issues here. |
| Show > Pull Requests | (submenu letter) | Show pull requests here. |
| Show > Both | (submenu letter) | Show both here. |
| Open or Closed > Open | (submenu letter) | Show open items. |
| Open or Closed > Closed | (submenu letter) | Show closed items. |
| Open or Closed > All | (submenu letter) | Show all items. |
| Sort By > Newest First | (submenu letter) | Order the list this way. |
| Sort By > Oldest First | (submenu letter) | Order the list this way. |
| Sort By > Title, A to Z | (submenu letter) | Order the list this way. |
| Sort By > Title, Z to A | (submenu letter) | Order the list this way. |
| Sort By > Recently Updated | (submenu letter) | Order the list this way. |
| Sort By > Least Recently Updated | (submenu letter) | Order the list this way. |
| Sort By > Most Comments | (submenu letter) | Order the list this way. |
| Sort By > By Column... | (submenu letter) | Order this list by one of its columns, first to last or last to first; remembered for this list. For lists other than Issues, which GitHub orders. |
| Quick Filters > Assigned to Me | (submenu letter) | Show only items assigned to me. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Assigned To... | (submenu letter) | Show only items assigned to someone you name. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Opened by Me | (submenu letter) | Show only items opened by me. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Opened By... | (submenu letter) | Show only items opened by someone you name. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Mentions Me | (submenu letter) | Show only items mentions me. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Review Requested from Me | (submenu letter) | Show only items review requested from me. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Reviewed by Me | (submenu letter) | Show only items reviewed by me. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > No Assignee | (submenu letter) | Show only items no assignee. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > No Milestone | (submenu letter) | Show only items no milestone. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > No Label | (submenu letter) | Show only items no label. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > No Project | (submenu letter) | Show only items no project. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > No Type | (submenu letter) | Show only items no type. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Drafts | (submenu letter) | Show only items drafts. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Has Conflicts | (submenu letter) | Show only items has conflicts. Checked when it is on; it combines with the others and with what you type in the filter box. Filtered over the loaded rows: Load All to be sure. |
| Quick Filters > Checks Failing | (submenu letter) | Show only items checks failing. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Updated This Week | (submenu letter) | Show only items updated this week. Checked when it is on; it combines with the others and with what you type in the filter box. |
| Quick Filters > Clear These Filters | (submenu letter) | Turn every quick filter off. |
| Group By > No Grouping | (submenu letter) | A flat list again. |
| Group By > Label | (submenu letter) | Put the list's groups in the tree, one node per label. |
| Group By > Milestone | (submenu letter) | Put the list's groups in the tree, one node per milestone. |
| Group By > Assignee | (submenu letter) | Put the list's groups in the tree, one node per assignee. |
| Group By > Author | (submenu letter) | Put the list's groups in the tree, one node per author. |
| Group By > Type | (submenu letter) | Put the list's groups in the tree, one node per type. |
| Group By > State | (submenu letter) | Put the list's groups in the tree, one node per state. |
| Group By > Repository | (submenu letter) | Put the list's groups in the tree, one node per repository. |
| Group By > Review State | (submenu letter) | Put the list's groups in the tree, one node per review state. |
| Group By > By Column... | (submenu letter) | Group this list by one of its columns, the groups as tree nodes; remembered for this list. For lists other than Issues, which group by the rows above. |
| Columns... | Ctrl+Shift+U | Choose which columns this list shows, and their order. |
| Back | Alt+Left | The view you were on before. Backspace too. |
| Forward | Alt+Right | The view you went back from. |
| Next Pane | F6 | Tree, filter, list, details, status bar. |
| Previous Pane | Shift+F6 | The same panes, backwards. |
| Where Am I | Alt+1 | Say the node and the filter in effect. |
| Say Selection | Alt+2 | Say how many rows are selected. |
| Say Item State | Alt+3 | Say the selected item's state in one line. |
| Say Counts | Alt+4 | Say how many rows this view holds. |
| Say Your Access | Alt+5 | Say what you can do here. |
| Say Rate Limit | Alt+6 | Say how much of the GitHub API is left. |
| Say Filter | Alt+7 | Say the filter in effect, in words. |
| Say Loading | Alt+8 | Say what is loading, or when it loaded. |
| Say Account | Alt+9 | Say the account, and whether you are signed in. |

#### Go

| Row | Key | What it does |
| --- | --- | --- |
| Inbox | Ctrl+1 | What needs you, across GitHub. Alt+Home too. |
| Current Repository | Ctrl+2 | The repository this window opened on. |
| Search | Ctrl+3 | Search GitHub. |
| People | Ctrl+4 | People you follow and who follow you. |
| Gists | Ctrl+5 | Your gists. |
| Projects | Ctrl+6 | Projects. |
| Watches | Ctrl+7 | Watches: tell me when a run finishes, a review arrives, a release or a comment. |
| Saved Searches | Ctrl+8 | Searches you saved. |
| Start Here | Ctrl+9 | What this window is and how it works. |
| Across Repositories | Ctrl+0 | One kind of thing from the repositories you chose, in one list. |
| Issues | Ctrl+Shift+1 | This repository's issues. |
| Pull Requests | Ctrl+Shift+2 | This repository's pull requests. |
| Discussions | Ctrl+Shift+3 | This repository's discussions. |
| Actions Runs | Ctrl+Shift+4 | This repository's workflow runs. |
| Files | Ctrl+Shift+5 | This repository's files. |
| Releases | Ctrl+Shift+6 | This repository's releases. |
| Repository Projects | Ctrl+Shift+7 | Its Projects. |
| Security | Ctrl+Shift+8 | Its security alerts. |
| Settings | Ctrl+Shift+9 | Its settings. |
| Insights | Ctrl+Shift+0 | Its traffic and community profile. |
| Parent Node | Alt+Up | The node above this one in the tree. |
| Next Unread | Ctrl+. | Move to the next unread row in this list. |
| Previous Unread | Ctrl+Shift+. | Move to the previous unread row in this list. |
| Pinned | (submenu letter) | Your pinned repositories; Enter goes there. |
| Favorites | (submenu letter) | Your favorite items; Enter opens one. |
| Run a Saved Search | (submenu letter) | Your saved searches; Enter runs one under Search. |

#### Item

| Row | Key | What it does |
| --- | --- | --- |
| Properties... | Alt+Enter | Everything about the selected row on one sheet. |
| Comment... | Ctrl+Shift+M | Write a comment on the selected item. |
| File Differences... | Ctrl+Shift+D | The selected pull request's changed files. |
| Merge... | Ctrl+Shift+Enter | Merge the selected pull request. |
| Assign to Copilot... | Ctrl+Shift+A | Ask Copilot to work on the selected issue. |
| Start in Local Worktree... | Ctrl+Shift+T | A branch and a folder on this computer for the selected item. |
| Read as Document... | Ctrl+Shift+I | The selected issue, pull request or discussion as one document, a heading per post: open it in the editor or save it as Markdown or HTML. |
| What Failed... | Ctrl+Shift+W | The failing steps of the selected run, and their log lines. |
| Re-run Failed Jobs | Ctrl+Shift+F5 | Run only what failed in the selected run again. |
| Mark Read | Ctrl+Q | Mark the selected notification read. |
| Mark All Read in View | Ctrl+Shift+Q | Mark every notification in this view read. Asks first when there are many. |
| Inbox Rules... | Ctrl+Alt+N | Rules that mark notifications done or read, or move them to the top, as they arrive. Each is tried on today's notifications before it is saved. |
| Add to or Remove from Favorites | Ctrl+D | Keep the selected row under Repositories, Favorites. |

#### Repository

| Row | Key | What it does |
| --- | --- | --- |
| Compare Branches... | Ctrl+Shift+B | Commits ahead and behind between two branches, and the changed files. |
| Compare With Default | Ctrl+B | The selected branch, tag, release or commit against the default branch. |
| Compare With Previous | Alt+Shift+B | The selected tag or release against the one before it, or a commit against its parent. |
| Run Workflow on Branch... | Ctrl+Shift+R | Start a workflow that can be started by hand, on a branch. |
| Repository Actions... | Ctrl+Shift+G | Everything else for this repository: star, watch, fork, clone, Codespaces, settings and administration, as a list you can run from. |
| Export Software Bill of Materials... | Ctrl+Alt+B | Save the repository's dependency graph as an SPDX file: every package it uses. |
| Transfer Repository... | Ctrl+Alt+T | Move the repository to another person or organization; asks for its name first. |
| Clone Wiki... | Ctrl+Alt+W | Copy the repository's wiki pages to a folder, to edit them as Markdown. |

#### Account

| Row | Key | What it does |
| --- | --- | --- |
| Manage GitHub Accounts... | Ctrl+Shift+K | Add, switch, sign in again or remove GitHub accounts. |
| GitHub API Rate Limit | Ctrl+Shift+L | How much of the GitHub API is left, and when it resets. |
| GitHub Permissions... | Ctrl+Shift+P | Every permission the Workbench can use, what it unlocks, whether you have it, and one step to add the missing ones. |
| Change History... | Ctrl+Shift+H | Every change the Workbench made on GitHub: before and after, and Undo where GitHub allows it. |
| Set Your Status... | Ctrl+Alt+S | Your GitHub status: a message, an emoji, busy or not, and when it clears. |
| Roles and Access > My Access Here... | (submenu letter) | Your effective role here, and where each part comes from. |
| Roles and Access > View As Role... | (submenu letter) | What a role could do here, read-only: nothing you do is sent. |
| Roles and Access > Compare Roles... | (submenu letter) | Two roles side by side: what one may do that the other may not. |
| Roles and Access > Why Can't They?... | (submenu letter) | Name a person and an action; hear what stops them and who can fix it. |
| Roles and Access > Access Review... | (submenu letter) | Every person and repository pair in an organization, with role and source: filterable, exportable as CSV. |
| Roles and Access > Bulk Access Changes... | (submenu letter) | One team or person, many repositories: previewed, then a result per change. |
| Roles and Access > Workbench Level for This Account... | (submenu letter) | Read Only, Organize or Full: what the Workbench may change with this account, whatever GitHub would allow. |

#### Tools

| Row | Key | What it does |
| --- | --- | --- |
| Workbench Options... | Ctrl+Shift+O | Where the Workbench opens, how notifications check, lists and privacy. |
| Dry Run | Ctrl+Alt+D | Turn Dry Run on or off. While it is on, every write asks and previews as usual, then stops before sending and says what it would have sent. |
| Plain-Language Batch... | Ctrl+Shift+S | Say a change to many issues or pull requests in words, such as close every issue labelled duplicate older than 90 days; check the exact items it found, then send them. No AI: the same words always mean the same thing. |
| GitHub API Console... | Ctrl+Shift+J | Send any GitHub REST request or GraphQL query: completion from GitHub's API description, what it does and needs said first, the answer as a tree. |

#### Window

| Row | Key | What it does |
| --- | --- | --- |
| Switch to Editor | Ctrl+Shift+E | Bring forward the editor that opened this window. |

#### Help

| Row | Key | What it does |
| --- | --- | --- |
| Help for This View | F1 | What this view and control do. |
| What Can I Do Here?... | Shift+F1 | Every action for the selection, its key, and why any is greyed. |
| What Is This? | Alt+F1 | The GitHub word for this row, explained. |
| GitHub Workbench Guide | Ctrl+F1 | The guide, opened at the chapter for where you are. |
| Search Help... | Ctrl+Shift+F1 | Type a few words to find a help topic, a command or a GitHub word. |
| Practice on GitHub... | Ctrl+Alt+P | Make, open or delete quill-practice, a private repository with issues, a pull request and a failing run to learn on. |
| GitHub Service Status... | Ctrl+Alt+F1 | Whether GitHub says it is working, which parts are not, and any incident. Reads www.githubstatus.com, only when you ask. |
| Workbench Keys | Alt+Shift+F1 | Every key in this window, by family. |
| Key Describer | Ctrl+Alt+K | Press keys to hear what each does here, without doing it. Escape stops. |
| Say Last Result Again | F9 | Say the last result again. |
| Explain That | Shift+F9 | What the last result means and what you might do next. |

Keys the window answers that are not menu rows:

| Key | Command id |
| --- | --- |
| Ctrl+Shift+F | `github.workbench.filter_alias` |
| Alt+Home | `github.workbench.inbox_home` |
| Ctrl+R | `github.workbench.refresh_alias` |
| Delete | `github.workbench.remove` |
| Ctrl+Cancel | `github.workbench.cancel_run` |

### Context menus, by row type

- **issue**: Open, Comment..., Close or Reopen..., Labels..., Assignees..., Copy Link; More: Open on GitHub, Milestone..., Projects..., Edit Title..., React..., View Timeline..., Read as Document..., Summarize Discussion, Start in Local Worktree..., Assign to Copilot..., Lock or Unlock Conversation..., Pin or Unpin Issue, Transfer Issue..., Check or Uncheck a Task..., Convert Tasks to Sub-issues..., Create Branch for This Issue..., Unlink Branch..., Not a Duplicate..., Set Issue Type..., Reorder Sub-issues..., Relationships..., Issue Fields..., Delete Issue..., Add to or Remove from Favorites, Link a Pull Request That Closes It..., Unlink a Pull Request...; Properties...
- **pull_request**: Review..., File Differences..., Comment..., Merge..., Why Can't I Merge?, Merge Selected...; More: Auto-Merge..., Reviews..., Open in a Codespace, Add to or Remove from Merge Queue..., Open Patch in Editor, Revert Pull Request..., Resolve Conflicts in a Worktree..., Copy Link, Open on GitHub, Start in Local Worktree..., Open in Codespaces..., Commit Comments..., View Timeline..., Read as Document..., Summarize Discussion, React..., Labels..., Assignees..., Milestone..., Projects..., Edit Title..., Add to or Remove from Favorites, Re-request Review..., Ask Copilot to Review, Agent Merge, Turn On Agent Merge, Turn Off Agent Merge...; Properties...
- **run**: Jobs and Logs, What Failed..., Re-run Failed Jobs Only, Re-run Workflow, Cancel Run..., Re-run One Job...; More: Force Cancel..., Download Logs..., Delete Logs..., Approvals, Earlier Attempts..., View Artifacts..., Open on GitHub, Combined Check Status, Review Pending Deployments..., Approve Run from a Fork..., Delete Run..., Copy Link, Read a Step's Log...; Properties...
- **workflow**: Runs, Run Workflow on Branch..., Turn Workflow On or Off..., Open on GitHub, Copy Link; Properties...
- **release**: Assets, Edit Release..., Draft Release Notes..., Upload Asset..., React..., Release Evidence...; More: Delete Release..., Compare With Previous, Compare With Default, Copy Link, Open on GitHub, GitHub's Release Notes...; Properties...
- **branch**: Commits, Compare With Default, Compare Branches..., Merge Into..., Download Source..., Compare With Previous; More: Open in Codespaces..., Copy Name, Delete Branch...; Properties...
- **commit**: Open, Commit Comments..., Set Status..., Compare With Previous, Compare With Default, Copy Link; More: Open on GitHub, Check Run Details..., Re-run a Check Suite..., Branches at This Commit, Reactions on a Commit Comment..., React to a Commit Comment..., Remove My Reaction from a Commit Comment...; Properties...
- **tag**: Open, Delete Tag..., Read Tag Message, Download Source..., Commit Comments..., Compare With Previous; More: Compare With Default, Copy Link, Open on GitHub; Properties...
- **invitation**: Accept Invitation..., Decline Invitation..., Open on GitHub, Copy Link; Properties...
- **notification**: Open, Mark Read, Mark Done, Snooze for One Day, Unsubscribe from Thread, Open on GitHub; More: Unsnooze Locally, Why?; Properties...
- **repository**: Open, Star or Unstar, Watch or Unwatch, Clone..., Send Repository Dispatch..., Pin; More: Star Lists..., Add to or Remove from Favorites, Open on GitHub, Open in Codespaces..., Rename or Delete Star List..., Fork Workflow Settings, Fork Workflows from Private Repositories..., Languages, License, Star History, Mark Its Notifications Read, Set a Custom Property..., Compare Dependencies..., SBOM Report, Ruleset History..., Secret Scanning History, Require Sign-off on Web Commits..., Sponsor Links, Dependency Manifests, Start an Agent Task..., Agent Tasks, An Agent Task's Progress..., Automations, New Automation..., Run an Automation..., Rename an Automation..., Delete an Automation..., An Automation's History..., An Automation's Tasks..., Automation Tools and Triggers, Agent Secrets from the Organization, Agent Variables from the Organization; Properties...
- **person**: Open, Follow or Unfollow, Open on GitHub; Properties...
- **label**: Find Issues with Label, Edit Label..., Delete Label...; Properties...
- **gist**: Edit Gist..., Star or Unstar, Comments..., History..., Forks..., Fork Gist; More: Copy Link, Open on GitHub, Delete Gist...; Properties...
- **discussion**: Open Discussion Thread, Read as Document..., Copy Link, Open on GitHub, Close Discussion..., Reopen Discussion; More: Delete Discussion..., Upvote, Remove Upvote, Vote..., Edit a Comment..., Delete a Comment...; Properties...
- **security_alert**: Open, Dismiss or Reopen Alert..., Copilot Autofix..., Show Every Place, Open on GitHub, Where It Was Found; Properties...
- **cache**: Show Details, Delete Cache...; Properties...
- **saved_search**: Run, Pin as Node, Unpin Node, Remove Saved Search; Properties...
- **result**: Open, Copy Link, Open on GitHub; Properties...
- **file**: Open in Editor, Copy Link, Open on GitHub; Properties...
- **folder**: Open Folder, Open on GitHub; Properties...
- **milestone**: Find Issues in Milestone, Delete Milestone..., Copy Link, Open on GitHub; Properties...
- **template**: Open Template..., Convert Form or Template..., Copy to Repositories..., Copy Link, Open on GitHub; Properties...
- **project**: Open on GitHub, Add Draft Issue..., New Field..., Delete Field..., Post Status Update..., Link to Repository...; More: Unlink from Repository..., Template..., Copy Project..., Delete Project..., Copy Link, New View..., Items in a View..., Rename a View..., Delete a View..., Rename a Field..., Add an Issue Field..., Edit a Draft..., Make a Draft an Issue..., Move an Item..., Edit a Status Update..., Delete a Status Update..., Delete a Workflow..., Share the Project..., Link a Team..., Unlink a Team...; Properties...
- **team**: Members and Access..., Copy Link, Open on GitHub, Delete Team..., Pending Invitations; Properties...
- **organization**: Open, Roles..., Rulesets..., Open on GitHub, Fork Workflow Settings, Fork Workflows from Private Repositories...; More: Dependabot Repository Access, Give Dependabot a Repository..., Take a Repository from Dependabot..., Dependabot's Default Access..., Make Someone an Outside Collaborator..., Define a Custom Property..., Set Repositories' Custom Property..., New Team..., Accept Membership, My Activity Here, Require Sign-off on Web Commits..., Follow Organization, Unfollow Organization; Properties...
- **favorite**: Open, Copy Link, Open on GitHub, Add to or Remove from Favorites; Properties...
- **admin_action**: Open; Properties...
- **watch**: Edit Watch..., Pause or Resume Watch, Check Watches Now, Remove Watch, Why?, Open on GitHub; Properties...
- **help_topic**: Open, Take Me There, Walk Me Through It, Do It; Properties...
- **node**: Refresh, Open on GitHub, Help for This View, Why?, New Organization Runner..., Just-in-Time Runner...; More: Just-in-Time Runner..., Is a Runner Version Retiring?..., Is a Runner Version Retiring?..., Email Visibility..., Interaction Limits, Limit Interactions..., Lift Interaction Limits, Set Up a Sponsors Profile..., New Sponsor Tier..., Patreon Sponsorships..., My Agent Tasks, My Automations; Properties...
- **across_item**: Open in Its Repository, Next Repository, Previous Repository, View More from This Repository, Read Issue Type and Fields, Every Release or Latest Only; More: Open on GitHub, Copy Link; Properties...
- **across_status**: Open, Next Repository, Previous Repository, View More from This Repository, Open on GitHub; Properties...
- **repository_set**: Use This Set, Edit Repositories..., Set Filter..., New Set..., Rename Set..., Delete Set...; Properties...
- **by_name**: Variants and Missing From, Make Them the Same..., Add to Missing..., Find Uses, Rename Everywhere..., Merge Into...; More: Close Everywhere..., Move Open Work To..., Promote to Organization..., Delete Everywhere...; Properties...
- **fleet**: Open Repository, Open on GitHub, Copy Link; Properties...
- **release_asset**: Download, Copy Link, Attestations..., Delete Asset...; Properties...
- **deployment**: Open, Delete Deployment..., Copy Link, Open on GitHub; Properties...
- **discussion_section**: Open Section, Open on GitHub; Properties...
- **discussion_category**: Find Discussions in Category, Copy Link, Open on GitHub; Properties...
- **runner**: Show Details, Runner Labels..., Remove Runner..., Open on GitHub, Copy Link, Removal Commands...; Properties...
- **pages_site**: Show Details, Check Site, Rebuild, Turn Off Pages..., Open on GitHub, Copy Link; Properties...
- **environment**: Show Details, Deployments..., Secrets..., Variables..., Branch Policies..., Protection Rules...; More: Delete..., Open on GitHub, Copy Link, Pin Environment, Unpin Environment, Move Environment...; Properties...
- **codespace**: Show Details, Start, Stop, Change Machine..., Export to a Branch, Publish to a New Repository...; More: Delete..., Open on GitHub, Copy Link; Properties...
- **package**: Show Details, Open on GitHub, Show Versions, Restore Package Version..., Delete Package Version..., Delete Package..., Copy Link; Properties...
- **key**: Show Details, Delete Key..., Open on GitHub; Properties...
- **advisory**: Show Details, Publish or Close Advisory..., Request CVE..., Open on GitHub, Copy Link, Advisory Comments; More: Comment on Advisory..., Edit an Advisory Comment..., Make a Private Fork for the Fix; Properties...
- **webhook**: Show Details, Ping, Send Test Push, Turn On or Off..., Recent Deliveries..., Change Address or Secret...; More: Delete Webhook..., Open on GitHub; Properties...
- **deploy_key**: Show Details, Delete Deploy Key..., Open on GitHub; Properties...
- **autolink**: Show Details, Delete Autolink..., Open on GitHub; Properties...
- **resource**: Show Details, Change..., Repositories Allowed..., Delete..., Open on GitHub, Copy Link; More: Removal Commands..., Add Runner Label..., Remove Runner Label..., Runners in This Group, Hosted Runners in This Group, Add a Runner to This Group..., Remove a Runner from This Group..., Teams It Adds To; Properties...
- **wiki**: Open on GitHub, Clone Wiki..., Copy Link; Properties...
- **sponsorship**: Show Details, Cancel Sponsorship..., Open on GitHub, Sponsorship Preferences...; Properties...
- **sponsor_tier**: Show Details, Sponsor at This Tier..., Open on GitHub, Publish Tier, Retire Tier...; Properties...

### Workbench Options

| Setting | Page | Label | What it does |
| --- | --- | --- | --- |
| `open_on` | General | Open the Workbench on | Where the window opens when no menu row asks for a place: Inbox (Start Here until you have signed in), Start Here, or wherever you were last time. |
| `list_mode` | General | List shows | Quick lists show a few columns, fast to arrow through; Full lists show every column GitHub Items knows for that view. |
| `default_sort` | General | Sort issues and pull requests by | The order a list of issues and pull requests opens in. Newest first is the usual choice. |
| `default_state` | General | Show issues that are | Open, closed or all, when a list opens. The filter box can always say is:open or is:closed for one list. |
| `poll_interval_minutes` | Notifications and Inbox | Check for new notifications every (minutes) | How often GitHub is checked for new notifications, from 5 minutes to a day. GitHub may ask for longer, and then it gets longer. |
| `poll_audible_tick` | Notifications and Inbox | Play a sound on each check | A short sound every time GitHub is checked, so silence means the check stopped rather than found nothing. Off by default. |
| `poll_interrupt_speech` | Notifications and Inbox | New notifications interrupt speech | Say a new notification at once, cutting across what is being said. Off means it waits its turn. |
| `include_read_notifications` | Notifications and Inbox | Include read notifications | Show notifications you have already read, as well as unread ones, in Notifications. |
| `speak_column_names` | Lists | Say column names before values | Put each column's name before its value in a list row, as in Number 42, Title Crash on start. Off keeps rows short. |
| `health_snapshot_opt_in` | Privacy | Load the repository Health Snapshot | Insights, Health Snapshot reads extra data from GitHub about a repository's activity. It loads only when this is checked. |
| `first_time_help` | Privacy | Show First time here? help | The first few times you visit a place, its details start with a short paragraph on what it is for. |

### GitHub words

- **Actions**: GitHub's automation: workflows that run on events, such as a push.
- **Annotated tag**: A tag that carries a message, who made it and when. Releases usually use one. A lightweight tag is only a name for a commit.
- **Artifact**: A file a run produced and kept, to download.
- **Assignee**: The person an issue or pull request is given to.
- **Attestation**: A signed record GitHub keeps of how a file was built. A release file's Attestations... lists them by the file's digest.
- **Autolink**: A prefix, such as BUG-, that GitHub turns into a link to another system.
- **Branch**: A line of work: a name that follows the newest commit of one set of changes. Under Code, Branches.
- **Branch protection**: Rules that decide who may change a branch and what a change needs.
- **Cache**: Files Actions keeps between runs to make them faster. Under Actions, Caches.
- **Check**: A test or other run that reports passing or failing on a commit.
- **Codespace**: A computer in the cloud with the repository ready to work on. It can cost money.
- **Collaborator**: Somebody given access to one repository.
- **Commit**: A saved change, with a message saying why. Under Code, Commits.
- **Deploy key**: An SSH key that reaches one repository only, for a server to clone, pull or push.
- **Deployment**: Code sent to an environment, such as a website.
- **Discussion**: A conversation in a repository that is not an issue.
- **Discussion category**: A kind of discussion, such as Q&A or Ideas. Under Discussions, Categories, by section where GitHub gives sections; Enter lists its discussions.
- **Draft**: A pull request that is not ready for review yet.
- **Environment**: A named place code is deployed to, with its own rules and secrets.
- **Favorite**: An item kept on this computer under Repositories, Favorites.
- **Fleet**: Every repository in a Repository Set on one line each: its revision, checks, pull requests, latest release and alerts. Under Across Repositories, Fleet.
- **Fork**: Your own copy of somebody else's repository, from which you can propose changes back. Under People, Forks.
- **Gist**: A small shared file or snippet, with its own history.
- **GitHub Pages**: A website GitHub publishes from a repository, from a branch or by a workflow.
- **Immutable release**: A published release whose tag and files can no longer change. Its sheet and Release Evidence... say whether a release is one.
- **Inbox**: The Workbench's one list of what needs you, made from notifications, review requests, assignments and mentions.
- **Invitation**: Someone with admin access asking you to join their repository, with the access they chose. It waits under Needs My Attention > Invitations and expires after a week.
- **Issue**: A note about a bug, an idea or a task, with a conversation under it. Under a repository's Issues.
- **Job**: One part of a run, on one machine, made of steps.
- **Key**: An SSH key lets git push and pull without a password; a GPG key or SSH signing key marks your commits Verified. GitHub keeps only the public half.
- **Label**: A coloured tag on issues and pull requests, such as bug. Under Labels.
- **Listed setting**: One of a repository's, an organization's or your own settings that GitHub keeps as a list, such as variables, secrets or members.
- **Mention**: Your login written with an at sign, such as @you, which notifies you.
- **Merge**: Bringing a pull request's changes into the branch it targets. Item, Merge, Ctrl+Shift+Enter.
- **Merge queue**: A line pull requests wait in to merge one after another, each tested with the ones ahead. Merge Selected... adds a pull request to it when its branch requires one.
- **Milestone**: A goal with a due date that issues and pull requests belong to.
- **Notification**: GitHub telling you something happened on a thread you are part of. Under Needs My Attention.
- **Organization**: An account many people share, which owns repositories and teams.
- **Package**: Something a project publishes besides its code, such as a container image or an npm package, kept on GitHub Packages in versions.
- **Pin**: A repository kept on this computer under Repositories, Pinned.
- **Poll**: A question in a discussion with options to vote for. Its details show it as a table: option, votes, percentage and your vote. Vote... casts yours.
- **Project**: A board or table for planning issues and pull requests.
- **Pull request**: A proposed change: commits on one branch that somebody asks to merge into another, with a review. Under a repository's Pull Requests.
- **Rate limit**: How many requests GitHub allows an account each hour. Account, GitHub API Rate Limit, Ctrl+Shift+L.
- **Rebase**: Replaying commits on top of another branch, so the history reads as one straight line.
- **Release**: A published version, with notes and files to download. Under a repository's Releases.
- **Release evidence**: What vouches for a release: its commit, the checks that passed, where it deployed, and its files' attestations. Release Evidence... on a release.
- **Repository**: A project's folder on GitHub: its files, their history, and its issues and pull requests. Under Repositories in the tree.
- **Repository Set**: A named list of repositories kept on this computer, made by hand or by a filter such as org:name. Across Repositories reads one kind of thing from all of them. Under Across Repositories, Repository Sets.
- **Review**: Reading a pull request's changes and approving them, asking for changes, or commenting. Enter on a pull request.
- **Role**: What somebody may do: read, triage, write, maintain or admin.
- **Ruleset**: A newer, named set of branch and tag rules that can cover many branches.
- **Run**: One time a workflow ran, with its jobs, steps and logs. Under Actions, Runs.
- **Runner**: A machine that runs a workflow's jobs. GitHub provides them, or a repository brings its own, called self-hosted, listed under Actions > Runners.
- **Saved search**: A search kept on this computer, to run again. Under Saved Searches.
- **Secret**: A value, such as a password, that workflows use and GitHub never shows.
- **Security advisory**: A notice that a package has a vulnerability: which versions, how serious, and where it is fixed. Each has a GHSA id, and often a CVE number too.
- **Security alert**: A warning that code, a dependency or a secret in it is at risk.
- **Sponsorship**: Money you pay someone through GitHub Sponsors for their open-source work, each month or once, at one of the tiers they offer.
- **Spotlight**: The discussions pinned at the top of Discussions. Under Discussions, Pinned (spotlight); read only, because GitHub's API cannot pin one.
- **Squash**: Merging a pull request as one single commit, instead of all of its commits.
- **Star**: A bookmark on a repository, which also shows you like it.
- **Star list**: One of your own named groups of starred repositories, such as Screen readers. A repository can be on several.
- **Tag**: A name for one particular commit, usually a version number. Under Code, Tags.
- **Team**: A group of people in an organization, given access together.
- **Template**: A file that shapes new issues, pull requests or discussions, such as a bug report form. Under Templates.
- **Triage**: The role that may label, assign and close issues, but not push code.
- **Upstream**: The repository a fork was copied from. Under Code, Upstream, on a fork.
- **Variable**: A value workflows use that is not secret.
- **Watch**: Asking GitHub to tell you about a repository's activity.
- **Watch rule**: A rule kept on this computer that tells you when something happens on GitHub: a run finishes, a review arrives, a release or a comment. Under Watches. Not the same as watching a repository on GitHub, which sends notifications.
- **Webhook**: An address GitHub sends a message to when something happens in a repository, such as a push. Continuous integration and chat bots use them.
- **Wiki**: A repository's own pages of documentation, kept by GitHub as a git repository of their own, owner/name.wiki.
- **Workflow**: One automation, defined in a file in the repository. Under Actions, Workflows.
- **Workflow dispatch**: Starting a workflow by hand, on a branch you choose.

<!-- END GENERATED -->

<!-- BEGIN GENERATED COVERAGE: python -m quill.tools.github_api_coverage_audit --write-doc -->

## Everything GitHub can do, and where

Generated from `quill/core/github/api_coverage.json` against the snapshot of GitHub's own API descriptions in `quill/data/github_api/` (GitHub Workbench PRD section 19). Every REST operation and GraphQL mutation GitHub publishes is listed under GitHub's category name, with one of four answers:

- **Yes**: the Workbench does it; the row says where, with its key.
- **Planned**: not yet; the row says where it will live.
- **Not needed**: plumbing a person never meets as such.
- **Left to GitHub**: the Workbench does not do it, and the row says why.

In all: 850 yes, 0 planned, 290 not needed and 867 left to GitHub.

**Wikis** have no API: GitHub serves each one as a Git repository (`owner/name.wiki.git`). Reading and editing them is planned under Repository > Wiki.

### REST operations, by category

#### Actions

208 operations: 135 yes, 25 not needed, 48 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get GitHub Actions cache retention limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/retention-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set GitHub Actions cache retention limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/retention-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions cache storage limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/storage-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set GitHub Actions cache storage limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/storage-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List OIDC custom property inclusions for an enterprise | `GET /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an OIDC custom property inclusion for an enterprise | `POST /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an OIDC custom property inclusion for an enterprise | `DELETE /enterprises/{enterprise}/actions/oidc/customization/properties/repo/{custom_property_name}` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions cache retention limit for an organization | `GET /organizations/{org}/actions/cache/retention-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Set GitHub Actions cache retention limit for an organization | `PUT /organizations/{org}/actions/cache/retention-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Get GitHub Actions cache storage limit for an organization | `GET /organizations/{org}/actions/cache/storage-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Set GitHub Actions cache storage limit for an organization | `PUT /organizations/{org}/actions/cache/storage-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Get GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| List repositories with GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage-by-repository` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| List GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners` | Yes | Navigator: Organization > organization > Larger Runners |
| Create a GitHub-hosted runner for an organization | `POST /orgs/{org}/actions/hosted-runners` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| List custom images for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Delete a custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get a custom image definition for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List image versions of a custom image for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Delete an image version of custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get an image version of a custom image for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get GitHub-owned images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/github-owned` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get partner images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/partner` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get limits on GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners/limits` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get GitHub-hosted runners machine specs for an organization | `GET /orgs/{org}/actions/hosted-runners/machine-sizes` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Get platforms for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/platforms` | Left to GitHub | Larger GitHub-hosted runners and their custom images are a paid company feature, set up once on GitHub's site. |
| Delete a GitHub-hosted runner for an organization | `DELETE /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Yes | context menu > Delete... |
| Get a GitHub-hosted runner for an organization | `GET /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a GitHub-hosted runner for an organization | `PATCH /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Yes | context menu > Change... |
| List OIDC custom property inclusions for an organization | `GET /orgs/{org}/actions/oidc/customization/properties/repo` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Create an OIDC custom property inclusion for an organization | `POST /orgs/{org}/actions/oidc/customization/properties/repo` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Delete an OIDC custom property inclusion for an organization | `DELETE /orgs/{org}/actions/oidc/customization/properties/repo/{custom_property_name}` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Get the customization template for an OIDC subject claim for an organization | `GET /orgs/{org}/actions/oidc/customization/sub` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Set the customization template for an OIDC subject claim for an organization | `PUT /orgs/{org}/actions/oidc/customization/sub` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Get GitHub Actions permissions for an organization | `GET /orgs/{org}/actions/permissions` | Yes | Properties (Alt+Enter) on Organization |
| Set GitHub Actions permissions for an organization | `PUT /orgs/{org}/actions/permissions` | Yes | Properties (Alt+Enter) on Organization: Repositories that may use Actions |
| Get artifact and log retention settings for an organization | `GET /orgs/{org}/actions/permissions/artifact-and-log-retention` | Yes | Properties (Alt+Enter) on Organization |
| Set artifact and log retention settings for an organization | `PUT /orgs/{org}/actions/permissions/artifact-and-log-retention` | Yes | Properties (Alt+Enter) on Organization: Keep artifacts and logs for days |
| Get fork PR contributor approval permissions for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | Yes | Properties (Alt+Enter) on Organization |
| Set fork PR contributor approval permissions for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | Yes | Properties (Alt+Enter) on Organization: Approval needed for workflows from |
| Get private repo fork PR workflow settings for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | Yes | context menu > Fork Workflow Settings |
| Set private repo fork PR workflow settings for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | Yes | context menu > Fork Workflows from Private Repositories... |
| List selected repositories enabled for GitHub Actions in an organization | `GET /orgs/{org}/actions/permissions/repositories` | Yes | Navigator: Organization > organization > Actions: Allowed Repositories |
| Set selected repositories enabled for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories` | Not needed | Adding and removing one repository at a time does the same, and keeps a change someone else made meanwhile; replacing the whole list would lose it. |
| Disable a selected repository for GitHub Actions in an organization | `DELETE /orgs/{org}/actions/permissions/repositories/{repository_id}` | Yes | context menu > Delete... |
| Enable a selected repository for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories/{repository_id}` | Yes | Navigator: Organization > organization > Actions: Allowed Repositories |
| Get allowed actions and reusable workflows for an organization | `GET /orgs/{org}/actions/permissions/selected-actions` | Yes | Properties (Alt+Enter) on Organization |
| Set allowed actions and reusable workflows for an organization | `PUT /orgs/{org}/actions/permissions/selected-actions` | Yes | Properties (Alt+Enter) on Organization: Allow actions made by GitHub |
| Get self-hosted runners settings for an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners` | Yes | Properties (Alt+Enter) on Organization |
| Set self-hosted runners settings for an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners` | Yes | Properties (Alt+Enter) on Organization: Repositories that may use self-hosted runners |
| List repositories allowed to use self-hosted runners in an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | Yes | Navigator: Organization > organization > Self-hosted Runners: Allowed Repositories |
| Set repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | Not needed | Adding and removing one repository at a time does the same, and keeps a change someone else made meanwhile; replacing the whole list would lose it. |
| Remove a repository from the list of repositories allowed to use self-hosted runners in an organization | `DELETE /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | Yes | context menu > Delete... |
| Add a repository to the list of repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | Yes | Navigator: Organization > organization > Self-hosted Runners: Allowed Repositories |
| Get default workflow permissions for an organization | `GET /orgs/{org}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Organization |
| Set default workflow permissions for an organization | `PUT /orgs/{org}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Organization: Workflow token permission |
| List organization Actions policies | `GET /orgs/{org}/actions/policies` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Create an organization Actions policy | `POST /orgs/{org}/actions/policies` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Delete an organization Actions policy | `DELETE /orgs/{org}/actions/policies/{policy_id}` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Get an organization Actions policy | `GET /orgs/{org}/actions/policies/{policy_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an organization Actions policy | `PUT /orgs/{org}/actions/policies/{policy_id}` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| List self-hosted runner groups for an organization | `GET /orgs/{org}/actions/runner-groups` | Yes | Navigator: Organization > organization > Runner Groups |
| Create a self-hosted runner group for an organization | `POST /orgs/{org}/actions/runner-groups` | Yes | Navigator: Organization > organization > Runner Groups |
| Delete a self-hosted runner group from an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}` | Yes | context menu > Delete... |
| Get a self-hosted runner group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a self-hosted runner group for an organization | `PATCH /orgs/{org}/actions/runner-groups/{runner_group_id}` | Yes | context menu > Change... |
| List GitHub-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/hosted-runners` | Yes | context menu > Hosted Runners in This Group |
| List repository access to a self-hosted runner group in an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | Yes | context menu > Repositories Allowed... |
| Set repository access for a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove repository access to a self-hosted runner group in an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add repository access to a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List self-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | Yes | context menu > Runners in This Group |
| Set self-hosted runners in a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | Not needed | Replaces the whole list at once; Add a Runner to This Group and Remove a Runner from This Group change one runner at a time, and keep a change someone else made meanwhile. |
| Remove a self-hosted runner from a group for an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Yes | context menu > Remove a Runner from This Group... |
| Add a self-hosted runner to a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Yes | context menu > Add a Runner to This Group... |
| List self-hosted runners for an organization | `GET /orgs/{org}/actions/runners` | Yes | Navigator: Organization > organization > Runners |
| Get runner version end-of-life schedule for an organization | `GET /orgs/{org}/actions/runners/deprecations/{version}` | Yes | context menu > Is a Runner Version Retiring?... |
| List runner applications for an organization | `GET /orgs/{org}/actions/runners/downloads` | Yes | context menu > New Organization Runner... |
| Create configuration for a just-in-time runner for an organization | `POST /orgs/{org}/actions/runners/generate-jitconfig` | Yes | context menu > Just-in-Time Runner... |
| Create a registration token for an organization | `POST /orgs/{org}/actions/runners/registration-token` | Yes | context menu > New Organization Runner... |
| Create a remove token for an organization | `POST /orgs/{org}/actions/runners/remove-token` | Yes | context menu > Removal Commands... |
| Delete a self-hosted runner from an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}` | Yes | context menu > Delete... |
| Get a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Remove all custom labels from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels` | Not needed | Replaces or clears every label at once; Runner Labels adds and removes them one at a time. |
| List labels for a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}/labels` | Not needed | Replaces or clears every label at once; Runner Labels adds and removes them one at a time. |
| Add custom labels to a self-hosted runner for an organization | `POST /orgs/{org}/actions/runners/{runner_id}/labels` | Yes | context menu > Add Runner Label... |
| Set custom labels for a self-hosted runner for an organization | `PUT /orgs/{org}/actions/runners/{runner_id}/labels` | Not needed | Replaces or clears every label at once; Add Runner Label and Remove Runner Label change them one at a time. |
| Remove a custom label from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels/{name}` | Yes | context menu > Remove Runner Label... |
| List organization secrets | `GET /orgs/{org}/actions/secrets` | Yes | Properties (Alt+Enter) on Organization |
| Get an organization public key | `GET /orgs/{org}/actions/secrets/public-key` | Yes | Navigator: Organization > organization > Actions Secrets |
| Delete an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}` | Yes | Navigator: Organization > organization > Actions Secrets |
| List selected repositories for an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List organization variables | `GET /orgs/{org}/actions/variables` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization variable | `POST /orgs/{org}/actions/variables` | Yes | Navigator: Organization > organization > Actions Variables |
| Delete an organization variable | `DELETE /orgs/{org}/actions/variables/{name}` | Yes | context menu > Delete... |
| Get an organization variable | `GET /orgs/{org}/actions/variables/{name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an organization variable | `PATCH /orgs/{org}/actions/variables/{name}` | Yes | context menu > Change... |
| List selected repositories for an organization variable | `GET /orgs/{org}/actions/variables/{name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List artifacts for a repository | `GET /repos/{owner}/{repo}/actions/artifacts` | Yes | Navigator: Repository > owner/name > Actions > Artifacts |
| Delete an artifact | `DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | Yes | context menu > Delete... |
| Get an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | Yes | Properties (Alt+Enter) on Artifact |
| Download an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/{archive_format}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get GitHub Actions cache retention limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/retention-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Set GitHub Actions cache retention limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/retention-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Get GitHub Actions cache storage limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/storage-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Set GitHub Actions cache storage limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/storage-limit` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Get GitHub Actions cache usage for a repository | `GET /repos/{owner}/{repo}/actions/cache/usage` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| Delete GitHub Actions caches for a repository (using a cache key) | `DELETE /repos/{owner}/{repo}/actions/caches` | Left to GitHub | Organization-wide cache storage and retention limits are company administration; a repository's caches are already in the Workbench. |
| List GitHub Actions caches for a repository | `GET /repos/{owner}/{repo}/actions/caches` | Yes | Navigator: Repository > owner/name > Actions > Caches |
| Delete a GitHub Actions cache for a repository (using a cache ID) | `DELETE /repos/{owner}/{repo}/actions/caches/{cache_id}` | Yes | context menu > Delete Cache... |
| List concurrency groups for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get a concurrency group for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups/{concurrency_group_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get a job for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}` | Yes | Properties (Alt+Enter) on Job |
| Download job logs for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` | Yes | Item > What Failed... (Ctrl+Shift+W) |
| Re-run a job from a workflow run | `POST /repos/{owner}/{repo}/actions/jobs/{job_id}/rerun` | Yes | context menu > Re-run One Job... |
| Download step logs for a workflow run job | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/steps/{step_number}/logs` | Yes | context menu > Read a Step's Log... |
| Get the customization template for an OIDC subject claim for a repository | `GET /repos/{owner}/{repo}/actions/oidc/customization/sub` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| Set the customization template for an OIDC subject claim for a repository | `PUT /repos/{owner}/{repo}/actions/oidc/customization/sub` | Left to GitHub | Cloud identity (OIDC) claim settings are one-off security plumbing for company deployments, set up on GitHub's site. |
| List repository organization secrets | `GET /repos/{owner}/{repo}/actions/organization-secrets` | Yes | Navigator: Repository > owner/name > Settings > Organization Secrets Here |
| List repository organization variables | `GET /repos/{owner}/{repo}/actions/organization-variables` | Yes | Navigator: Repository > owner/name > Settings > Organization Variables Here |
| Get GitHub Actions permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions` | Yes | Properties (Alt+Enter) on Repository |
| Set GitHub Actions permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions` | Yes | Properties (Alt+Enter) on Repository: Actions enabled |
| Get the level of access for workflows outside of the repository | `GET /repos/{owner}/{repo}/actions/permissions/access` | Yes | Properties (Alt+Enter) on Repository |
| Set the level of access for workflows outside of the repository | `PUT /repos/{owner}/{repo}/actions/permissions/access` | Yes | Properties (Alt+Enter) on Repository: Workflows here may be used by |
| Get artifact and log retention settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | Yes | Properties (Alt+Enter) on Repository |
| Set artifact and log retention settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | Yes | Properties (Alt+Enter) on Repository: Keep artifacts and logs for days |
| Get fork PR contributor approval permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | Yes | Properties (Alt+Enter) on Repository |
| Set fork PR contributor approval permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | Yes | Properties (Alt+Enter) on Repository: Approval needed for workflows from |
| Get private repo fork PR workflow settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | Yes | context menu > Fork Workflow Settings |
| Set private repo fork PR workflow settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | Yes | context menu > Fork Workflows from Private Repositories... |
| Get allowed actions and reusable workflows for a repository | `GET /repos/{owner}/{repo}/actions/permissions/selected-actions` | Yes | Properties (Alt+Enter) on Repository |
| Set allowed actions and reusable workflows for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/selected-actions` | Yes | Properties (Alt+Enter) on Repository: Allow actions made by GitHub |
| Get default workflow permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Repository |
| Set default workflow permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Repository: Allow Actions to create and approve pull requests |
| List repository Actions policies | `GET /repos/{owner}/{repo}/actions/policies` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Create a repository Actions policy | `POST /repos/{owner}/{repo}/actions/policies` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Delete a repository Actions policy | `DELETE /repos/{owner}/{repo}/actions/policies/{policy_id}` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| Get a repository Actions policy | `GET /repos/{owner}/{repo}/actions/policies/{policy_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a repository Actions policy | `PUT /repos/{owner}/{repo}/actions/policies/{policy_id}` | Left to GitHub | Actions policy rules are company administration, set up on GitHub's site. |
| List self-hosted runners for a repository | `GET /repos/{owner}/{repo}/actions/runners` | Yes | Navigator: Repository > owner/name > Actions > Runners |
| Get runner version end-of-life schedule for a repository | `GET /repos/{owner}/{repo}/actions/runners/deprecations/{version}` | Yes | context menu > Is a Runner Version Retiring?... |
| List runner applications for a repository | `GET /repos/{owner}/{repo}/actions/runners/downloads` | Yes | Navigator: Repository > owner/name > Actions > Runners |
| Create configuration for a just-in-time runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig` | Yes | context menu > Just-in-Time Runner... |
| Create a registration token for a repository | `POST /repos/{owner}/{repo}/actions/runners/registration-token` | Yes | Navigator: Repository > owner/name > Actions > Runners |
| Create a remove token for a repository | `POST /repos/{owner}/{repo}/actions/runners/remove-token` | Yes | context menu > Removal Commands... |
| Delete a self-hosted runner from a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}` | Yes | context menu > Remove Runner... |
| Get a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}` | Yes | Properties (Alt+Enter) on Runner |
| Remove all custom labels from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Not needed | Replaces or clears every label at once; Runner Labels adds and removes them one at a time. |
| List labels for a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Yes | Item > Properties... (Alt+Enter) |
| Add custom labels to a self-hosted runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Yes | context menu > Runner Labels... |
| Set custom labels for a self-hosted runner for a repository | `PUT /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Yes | Properties (Alt+Enter) on Runner: Custom labels |
| Remove a custom label from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels/{name}` | Yes | context menu > Runner Labels... |
| List workflow runs for a repository | `GET /repos/{owner}/{repo}/actions/runs` | Yes | Navigator: Repository > owner/name > Actions > Runs |
| Delete a workflow run | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}` | Yes | context menu > Delete Run... |
| Get a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}` | Yes | Properties (Alt+Enter) on Workflow Run |
| Get the review history for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/approvals` | Yes | context menu > Approvals |
| Approve a workflow run for a fork pull request | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve` | Yes | context menu > Approve Run from a Fork... |
| List workflow run artifacts | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts` | Yes | context menu > View Artifacts... |
| Get a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}` | Yes | context menu > Earlier Attempts... |
| List jobs for a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs` | Not needed | Check suites and an attempt's jobs are part of the run and check views, which read them by run and commit. |
| Download workflow run attempt logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/logs` | Yes | context menu > Earlier Attempts... |
| Cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/cancel` | Yes | context menu > Cancel Run... (Ctrl+Cancel) |
| List concurrency groups for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/concurrency_groups` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Review custom deployment protection rules for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule` | Left to GitHub | Only a GitHub App acting as a custom deployment protection rule answers this; a person approves through Review Pending Deployments. |
| Force cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/force-cancel` | Yes | context menu > Force Cancel... |
| List jobs for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` | Yes | Properties (Alt+Enter) on Workflow Run |
| Delete workflow run logs | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | Yes | context menu > Delete Logs... |
| Download workflow run logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | Yes | context menu > Download Logs... |
| Get pending deployments for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | Yes | context menu > Review Pending Deployments... |
| Review pending deployments for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | Yes | context menu > Review Pending Deployments... |
| Re-run a workflow | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun` | Yes | context menu > Re-run Workflow |
| Re-run failed jobs from a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs` | Yes | Item > Re-run Failed Jobs (Ctrl+Shift+F5) |
| Get workflow run usage | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/timing` | Yes | Properties (Alt+Enter) on Workflow Run |
| List repository secrets | `GET /repos/{owner}/{repo}/actions/secrets` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Get a repository public key | `GET /repos/{owner}/{repo}/actions/secrets/public-key` | Yes | Properties (Alt+Enter) on Secret |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get a repository secret | `GET /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Yes | Properties (Alt+Enter) on Secret |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Yes | Properties (Alt+Enter) on Secret: New value |
| List repository variables | `GET /repos/{owner}/{repo}/actions/variables` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Create a repository variable | `POST /repos/{owner}/{repo}/actions/variables` | Yes | Navigator: Repository > owner/name > Settings > Actions Variables |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/actions/variables/{name}` | Yes | context menu > Delete... |
| Get a repository variable | `GET /repos/{owner}/{repo}/actions/variables/{name}` | Yes | Properties (Alt+Enter) on Variable |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/actions/variables/{name}` | Yes | Properties (Alt+Enter) on Variable: Value |
| List repository workflows | `GET /repos/{owner}/{repo}/actions/workflows` | Yes | Navigator: Repository > owner/name > Actions > Workflows |
| Get a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}` | Yes | Properties (Alt+Enter) on Workflow |
| Disable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/disable` | Yes | context menu > Turn Workflow On or Off... |
| Create a workflow dispatch event | `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | Yes | Repository > Run Workflow on Branch... (Ctrl+Shift+R) |
| Enable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable` | Yes | context menu > Turn Workflow On or Off... |
| List workflow runs for a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs` | Not needed | A workflow's Runs shows the repository's runs filtered to that workflow; one route serves both. |
| Get workflow usage | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing` | Left to GitHub | How many billable minutes a workflow used is billing, which GitHub's billing pages show. |
| List environment secrets | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets` | Yes | Properties (Alt+Enter) on Environment |
| Get an environment public key | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/public-key` | Yes | context menu > Secrets... |
| Delete an environment secret | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Yes | context menu > Secrets... |
| Get an environment secret | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update an environment secret | `PUT /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Yes | context menu > Secrets... |
| List environment variables | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables` | Yes | Properties (Alt+Enter) on Environment |
| Create an environment variable | `POST /repos/{owner}/{repo}/environments/{environment_name}/variables` | Yes | context menu > Variables... |
| Delete an environment variable | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Yes | context menu > Variables... |
| Get an environment variable | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an environment variable | `PATCH /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Yes | context menu > Variables... |

#### Activity

34 operations: 29 yes, 2 not needed, 3 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List public events | `GET /events` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| Get feeds | `GET /feeds` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List public events for a network of repositories | `GET /networks/{owner}/{repo}/events` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List notifications for the authenticated user | `GET /notifications` | Yes | Navigator: Needs My Attention > Notifications |
| Mark notifications as read | `PUT /notifications` | Yes | Item > Mark All Read in View (Ctrl+Shift+Q) |
| Mark a thread as done | `DELETE /notifications/threads/{thread_id}` | Yes | context menu > Mark Done |
| Get a thread | `GET /notifications/threads/{thread_id}` | Yes | Properties (Alt+Enter) on Notification |
| Mark a thread as read | `PATCH /notifications/threads/{thread_id}` | Yes | Item > Mark Read (Ctrl+Q) |
| Delete a thread subscription | `DELETE /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| Get a thread subscription for the authenticated user | `GET /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| Set a thread subscription | `PUT /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| List public organization events | `GET /orgs/{org}/events` | Yes | Navigator: Organization > organization > Recent Events |
| List repository events | `GET /repos/{owner}/{repo}/events` | Yes | Navigator: Repository > owner/name > Activity |
| List repository notifications for the authenticated user | `GET /repos/{owner}/{repo}/notifications` | Yes | Navigator: Repository > owner/name > Activity > My Notifications Here |
| Mark repository notifications as read | `PUT /repos/{owner}/{repo}/notifications` | Yes | context menu > Mark Its Notifications Read |
| List stargazers | `GET /repos/{owner}/{repo}/stargazers` | Yes | Navigator: Repository > owner/name > People > Contributors and People |
| Get stargazer count | `GET /repos/{owner}/{repo}/stargazers/count` | Not needed | The star count is part of the repository, which every read of it returns. |
| Get repository star history | `GET /repos/{owner}/{repo}/stargazers/history` | Yes | context menu > Star History |
| List watchers | `GET /repos/{owner}/{repo}/subscribers` | Yes | Navigator: Repository > owner/name > People > Watchers |
| Delete a repository subscription | `DELETE /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| Get a repository subscription | `GET /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| Set a repository subscription | `PUT /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| List repositories starred by the authenticated user | `GET /user/starred` | Yes | Navigator: Repositories > Starred |
| Unstar a repository for the authenticated user | `DELETE /user/starred/{owner}/{repo}` | Yes | Properties (Alt+Enter) on Repository: Starred |
| Check if a repository is starred by the authenticated user | `GET /user/starred/{owner}/{repo}` | Yes | Item > Properties... (Alt+Enter) |
| Star a repository for the authenticated user | `PUT /user/starred/{owner}/{repo}` | Yes | Properties (Alt+Enter) on Repository: Starred |
| List repositories watched by the authenticated user | `GET /user/subscriptions` | Yes | Navigator: People > Repositories I Watch |
| List events for the authenticated user | `GET /users/{username}/events` | Not needed | A person's Activity node reads their public events (/users/{username}/events/public); this route differs only for yourself, whose whole activity My Activity Feed already reads. |
| List organization events for the authenticated user | `GET /users/{username}/events/orgs/{org}` | Yes | context menu > My Activity Here |
| List public events for a user | `GET /users/{username}/events/public` | Yes | Navigator: Person > person > Activity |
| List events received by the authenticated user | `GET /users/{username}/received_events` | Yes | Navigator: Needs My Attention > My Activity Feed |
| List public events received by a user | `GET /users/{username}/received_events/public` | Yes | Navigator: Person > person > People They Follow: Activity |
| List repositories starred by a user | `GET /users/{username}/starred` | Yes | Navigator: Person > person > Starred |
| List repositories watched by a user | `GET /users/{username}/subscriptions` | Yes | Navigator: Person > person > Watching |

#### Agent automations

12 operations: 10 yes, 2 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List automations for user | `GET /agents/automations` | Yes | context menu > My Automations |
| List automations for a repository | `GET /agents/repos/{owner}/{repo}/automations` | Yes | context menu > Automations |
| Create an automation for a repository | `POST /agents/repos/{owner}/{repo}/automations` | Yes | context menu > New Automation... |
| List available automation tools for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-tools` | Yes | context menu > Automation Tools and Triggers |
| List available automation triggers for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-triggers` | Yes | context menu > Automation Tools and Triggers |
| Delete an automation | `DELETE /agents/repos/{owner}/{repo}/automations/{automation_id}` | Yes | context menu > Delete an Automation... |
| Get an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an automation | `PATCH /agents/repos/{owner}/{repo}/automations/{automation_id}` | Yes | context menu > Rename an Automation... |
| List revisions for an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions` | Yes | context menu > An Automation's History... |
| Get an automation revision | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions/{revision_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List tasks for an automation in a repository | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | Yes | context menu > An Automation's Tasks... |
| Run an automation | `POST /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | Yes | context menu > Run an Automation... |

#### Agent tasks

5 operations: 3 yes, 2 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List tasks for repository | `GET /agents/repos/{owner}/{repo}/tasks` | Yes | context menu > Agent Tasks |
| Start a task | `POST /agents/repos/{owner}/{repo}/tasks` | Yes | context menu > Start an Agent Task... |
| Get a task by repo | `GET /agents/repos/{owner}/{repo}/tasks/{task_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List tasks | `GET /agents/tasks` | Yes | context menu > My Agent Tasks |
| Get a task by ID | `GET /agents/tasks/{task_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |

#### Agents

30 operations: 24 yes, 6 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization secrets | `GET /orgs/{org}/agents/secrets` | Yes | Navigator: Organization > organization > Copilot Agent Secrets |
| Get an organization public key | `GET /orgs/{org}/agents/secrets/public-key` | Yes | Navigator: Organization > organization > Copilot Agent Secrets |
| Delete an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}` | Yes | Navigator: Organization > organization > Copilot Agent Secrets |
| List selected repositories for an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List organization variables | `GET /orgs/{org}/agents/variables` | Yes | Navigator: Organization > organization > Copilot Agent Variables |
| Create an organization variable | `POST /orgs/{org}/agents/variables` | Yes | Navigator: Organization > organization > Copilot Agent Variables |
| Delete an organization variable | `DELETE /orgs/{org}/agents/variables/{name}` | Yes | context menu > Delete... |
| Get an organization variable | `GET /orgs/{org}/agents/variables/{name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an organization variable | `PATCH /orgs/{org}/agents/variables/{name}` | Yes | context menu > Change... |
| List selected repositories for an organization variable | `GET /orgs/{org}/agents/variables/{name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List repository organization secrets | `GET /repos/{owner}/{repo}/agents/organization-secrets` | Yes | context menu > Agent Secrets from the Organization |
| List repository organization variables | `GET /repos/{owner}/{repo}/agents/organization-variables` | Yes | context menu > Agent Variables from the Organization |
| List repository secrets | `GET /repos/{owner}/{repo}/agents/secrets` | Yes | Navigator: Repository > owner/name > Settings > Copilot Agent Secrets |
| Get a repository public key | `GET /repos/{owner}/{repo}/agents/secrets/public-key` | Yes | Navigator: Repository > owner/name > Settings > Copilot Agent Secrets |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get a repository secret | `GET /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Yes | Navigator: Repository > owner/name > Settings > Copilot Agent Secrets |
| List repository variables | `GET /repos/{owner}/{repo}/agents/variables` | Yes | Navigator: Repository > owner/name > Settings > Copilot Agent Variables |
| Create a repository variable | `POST /repos/{owner}/{repo}/agents/variables` | Yes | Navigator: Repository > owner/name > Settings > Copilot Agent Variables |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/agents/variables/{name}` | Yes | context menu > Delete... |
| Get a repository variable | `GET /repos/{owner}/{repo}/agents/variables/{name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/agents/variables/{name}` | Yes | context menu > Change... |

#### Apps

37 operations: 4 yes, 33 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get the authenticated app | `GET /app` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Create a GitHub App from a manifest | `POST /app-manifests/{code}/conversions` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get a webhook configuration for an app | `GET /app/hook/config` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Update a webhook configuration for an app | `PATCH /app/hook/config` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| List deliveries for an app webhook | `GET /app/hook/deliveries` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get a delivery for an app webhook | `GET /app/hook/deliveries/{delivery_id}` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Redeliver a delivery for an app webhook | `POST /app/hook/deliveries/{delivery_id}/attempts` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| List installation requests for the authenticated app | `GET /app/installation-requests` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| List installations for the authenticated app | `GET /app/installations` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Delete an installation for the authenticated app | `DELETE /app/installations/{installation_id}` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get an installation for the authenticated app | `GET /app/installations/{installation_id}` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Create an installation access token for an app | `POST /app/installations/{installation_id}/access_tokens` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Unsuspend an app installation | `DELETE /app/installations/{installation_id}/suspended` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Suspend an app installation | `PUT /app/installations/{installation_id}/suspended` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Delete an app authorization | `DELETE /applications/{client_id}/grant` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Delete an app token | `DELETE /applications/{client_id}/token` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Reset a token | `PATCH /applications/{client_id}/token` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Check a token | `POST /applications/{client_id}/token` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Create a scoped access token | `POST /applications/{client_id}/token/scoped` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get an app | `GET /apps/{app_slug}` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| List repositories accessible to the app installation | `GET /installation/repositories` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Revoke an installation access token | `DELETE /installation/token` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get a subscription plan for an account | `GET /marketplace_listing/accounts/{account_id}` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List plans | `GET /marketplace_listing/plans` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List accounts for a plan | `GET /marketplace_listing/plans/{plan_id}/accounts` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get a subscription plan for an account (stubbed) | `GET /marketplace_listing/stubbed/accounts/{account_id}` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List plans (stubbed) | `GET /marketplace_listing/stubbed/plans` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List accounts for a plan (stubbed) | `GET /marketplace_listing/stubbed/plans/{plan_id}/accounts` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get an organization installation for the authenticated app | `GET /orgs/{org}/installation` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Get a repository installation for the authenticated app | `GET /repos/{owner}/{repo}/installation` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| List app installations accessible to the user access token | `GET /user/installations` | Yes | Navigator: People > My Installed Apps |
| List repositories accessible to the user access token | `GET /user/installations/{installation_id}/repositories` | Yes | context menu > Repositories Allowed... |
| Remove a repository from an app installation | `DELETE /user/installations/{installation_id}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add a repository to an app installation | `PUT /user/installations/{installation_id}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List subscriptions for the authenticated user | `GET /user/marketplace_purchases` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List subscriptions for the authenticated user (stubbed) | `GET /user/marketplace_purchases/stubbed` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get a user installation for the authenticated app | `GET /users/{username}/installation` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |

#### Billing

13 operations: 1 yes, 1 not needed, 11 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get billing AI credit usage report for an organization | `GET /organizations/{org}/settings/billing/ai_credit/usage` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get all budgets for an organization | `GET /organizations/{org}/settings/billing/budgets` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Create a budget for an organization | `POST /organizations/{org}/settings/billing/budgets` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Delete a budget for an organization | `DELETE /organizations/{org}/settings/billing/budgets/{budget_id}` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get a budget by ID for an organization | `GET /organizations/{org}/settings/billing/budgets/{budget_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a budget for an organization | `PATCH /organizations/{org}/settings/billing/budgets/{budget_id}` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing premium request usage report for an organization | `GET /organizations/{org}/settings/billing/premium_request/usage` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing usage report for an organization | `GET /organizations/{org}/settings/billing/usage` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing usage summary for an organization | `GET /organizations/{org}/settings/billing/usage/summary` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing AI credit usage report for a user | `GET /users/{username}/settings/billing/ai_credit/usage` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing premium request usage report for a user | `GET /users/{username}/settings/billing/premium_request/usage` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |
| Get billing usage report for a user | `GET /users/{username}/settings/billing/usage` | Yes | Navigator: People > My Billing and Usage |
| Get billing usage summary for a user | `GET /users/{username}/settings/billing/usage/summary` | Left to GitHub | Billing budgets and cost reports belong to GitHub's billing pages; QUILL is a writing and coding tool, not an accounts console. |

#### Branches

38 operations: 8 yes, 30 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List branches | `GET /repos/{owner}/{repo}/branches` | Yes | Navigator: Repository > owner/name > Code > Branches |
| Get a branch | `GET /repos/{owner}/{repo}/branches/{branch}` | Yes | Properties (Alt+Enter) on Branch |
| Delete branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Get branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Update branch protection | `PUT /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Delete admin branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get admin branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Set admin branch protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Delete pull request review protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get pull request review protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Update pull request review protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Delete commit signature protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get commit signature protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Create commit signature protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Remove status check protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get status checks protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Update status check protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Remove status check contexts | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get all status check contexts | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Add status check contexts | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Set status check contexts | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Delete access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get access restrictions | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Remove app access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get apps with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Add app access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Set app access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Remove team access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get teams with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Add team access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Set team access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Remove user access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Get users with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Add user access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Set user access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Not needed | Changes one part of branch protection; the Workbench reads and sets the whole setting at once (GET/PUT /branches/{branch}/protection). |
| Rename a branch | `POST /repos/{owner}/{repo}/branches/{branch}/rename` | Yes | Properties (Alt+Enter) on Branch: Name |
| Sync a fork branch with the upstream repository | `POST /repos/{owner}/{repo}/merge-upstream` | Yes | Navigator: Repository > owner/name > Code > Upstream |
| Merge a branch | `POST /repos/{owner}/{repo}/merges` | Yes | context menu > Merge Into... |

#### Campaigns

5 operations: 1 not needed, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List campaigns for an organization | `GET /orgs/{org}/campaigns` | Left to GitHub | Security campaigns need paid GitHub Advanced Security. |
| Create a campaign for an organization | `POST /orgs/{org}/campaigns` | Left to GitHub | Security campaigns need paid GitHub Advanced Security. |
| Delete a campaign for an organization | `DELETE /orgs/{org}/campaigns/{campaign_number}` | Left to GitHub | Security campaigns need paid GitHub Advanced Security. |
| Get a campaign for an organization | `GET /orgs/{org}/campaigns/{campaign_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a campaign | `PATCH /orgs/{org}/campaigns/{campaign_number}` | Left to GitHub | Security campaigns need paid GitHub Advanced Security. |

#### Checks

12 operations: 5 yes, 3 not needed, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Create a check run | `POST /repos/{owner}/{repo}/check-runs` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Get a check run | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}` | Yes | context menu > Check Run Details... |
| Update a check run | `PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| List check run annotations | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations` | Yes | context menu > Check Run Details... |
| Rerequest a check run | `POST /repos/{owner}/{repo}/check-runs/{check_run_id}/rerequest` | Yes | context menu > Combined Check Status |
| Create a check suite | `POST /repos/{owner}/{repo}/check-suites` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Update repository preferences for check suites | `PATCH /repos/{owner}/{repo}/check-suites/preferences` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Get a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}` | Not needed | Check suites and an attempt's jobs are part of the run and check views, which read them by run and commit. |
| List check runs in a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}/check-runs` | Not needed | Check suites and an attempt's jobs are part of the run and check views, which read them by run and commit. |
| Rerequest a check suite | `POST /repos/{owner}/{repo}/check-suites/{check_suite_id}/rerequest` | Yes | context menu > Re-run a Check Suite... |
| List check runs for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-runs` | Yes | Properties (Alt+Enter) on Commit |
| List check suites for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-suites` | Not needed | Check suites and an attempt's jobs are part of the run and check views, which read them by run and commit. |

#### Classroom

6 operations: 1 not needed, 5 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Closed - Get an assignment | `GET /assignments/{assignment_id}` | Left to GitHub | GitHub Classroom's assignments and grades are read on classroom.github.com; not built, by Jeff's choice (2026-11-18). |
| Closed - List accepted assignments for an assignment | `GET /assignments/{assignment_id}/accepted_assignments` | Left to GitHub | GitHub Classroom's assignments and grades are read on classroom.github.com; not built, by Jeff's choice (2026-11-18). |
| Closed - Get assignment grades | `GET /assignments/{assignment_id}/grades` | Left to GitHub | GitHub Classroom's assignments and grades are read on classroom.github.com; not built, by Jeff's choice (2026-11-18). |
| Closed - List classrooms | `GET /classrooms` | Left to GitHub | GitHub Classroom's assignments and grades are read on classroom.github.com; not built, by Jeff's choice (2026-11-18). |
| Closed - Get a classroom | `GET /classrooms/{classroom_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Closed - List assignments for a classroom | `GET /classrooms/{classroom_id}/assignments` | Left to GitHub | GitHub Classroom's assignments and grades are read on classroom.github.com; not built, by Jeff's choice (2026-11-18). |

#### Code quality

4 operations: 1 not needed, 3 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List code quality findings for a repository | `GET /repos/{owner}/{repo}/code-quality/findings` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get a code quality finding | `GET /repos/{owner}/{repo}/code-quality/findings/{finding_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get a code quality setup configuration | `GET /repos/{owner}/{repo}/code-quality/setup` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Update a code quality setup configuration | `PATCH /repos/{owner}/{repo}/code-quality/setup` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |

#### Code scanning

25 operations: 15 yes, 3 not needed, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get the AI Scan setting for an organization | `GET /orgs/{org}/code-scanning/ai-scan` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Update the AI Scan setting for an organization | `PATCH /orgs/{org}/code-scanning/ai-scan` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| List code scanning alerts for an organization | `GET /orgs/{org}/code-scanning/alerts` | Yes | Navigator: Organization > organization > Code Scanning Alerts |
| Get AI Scan enablement for a repository | `GET /repos/{owner}/{repo}/code-scanning/ai-scan` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Update AI Scan enablement for a repository | `PATCH /repos/{owner}/{repo}/code-scanning/ai-scan` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| List code scanning alerts for a repository | `GET /repos/{owner}/{repo}/code-scanning/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a code scanning alert | `PATCH /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| Get the status of an autofix for a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | Yes | context menu > Copilot Autofix... |
| Create an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | Yes | context menu > Copilot Autofix... |
| Commit an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix/commits` | Yes | context menu > Copilot Autofix... |
| List instances of a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/instances` | Yes | context menu > Show Every Place |
| List code scanning analyses for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses` | Yes | Navigator: Repository > owner/name > Security > Code Scanning Analyses |
| Delete a code scanning analysis from a repository | `DELETE /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | Yes | context menu > Delete... |
| Get a code scanning analysis for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List CodeQL databases for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases` | Yes | Navigator: Repository > owner/name > Security > CodeQL Databases |
| Delete a CodeQL database | `DELETE /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | Yes | context menu > Delete... |
| Get a CodeQL database for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create a CodeQL variant analysis | `POST /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses` | Left to GitHub | Variant analysis runs a CodeQL query pack, built and uploaded by the CodeQL command-line tool, across many repositories; it is run from VS Code's CodeQL extension or the CLI, not typed by a person. |
| Get the summary of a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}` | Left to GitHub | Variant analysis runs a CodeQL query pack, built and uploaded by the CodeQL command-line tool, across many repositories; it is run from VS Code's CodeQL extension or the CLI, not typed by a person. |
| Get the analysis status of a repository in a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}/repos/{repo_owner}/{repo_name}` | Left to GitHub | Variant analysis runs a CodeQL query pack, built and uploaded by the CodeQL command-line tool, across many repositories; it is run from VS Code's CodeQL extension or the CLI, not typed by a person. |
| Get a code scanning default setup configuration | `GET /repos/{owner}/{repo}/code-scanning/default-setup` | Yes | Properties (Alt+Enter) on Repository |
| Update a code scanning default setup configuration | `PATCH /repos/{owner}/{repo}/code-scanning/default-setup` | Yes | Properties (Alt+Enter) on Repository: Code scanning default setup |
| Upload an analysis as SARIF data | `POST /repos/{owner}/{repo}/code-scanning/sarifs` | Yes | Navigator: Repository > owner/name > Security > Code Scanning Analyses |
| Get information about a SARIF upload | `GET /repos/{owner}/{repo}/code-scanning/sarifs/{sarif_id}` | Yes | Navigator: Repository > owner/name > Security > Code Scanning Analyses |

#### Code security

20 operations: 1 not needed, 19 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get code security configurations for an enterprise | `GET /enterprises/{enterprise}/code-security/configurations` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a code security configuration for an enterprise | `POST /enterprises/{enterprise}/code-security/configurations` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get default code security configurations for an enterprise | `GET /enterprises/{enterprise}/code-security/configurations/defaults` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a code security configuration for an enterprise | `DELETE /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Retrieve a code security configuration of an enterprise | `GET /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a custom code security configuration for an enterprise | `PATCH /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Attach an enterprise configuration to repositories | `POST /enterprises/{enterprise}/code-security/configurations/{configuration_id}/attach` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set a code security configuration as a default for an enterprise | `PUT /enterprises/{enterprise}/code-security/configurations/{configuration_id}/defaults` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get repositories associated with an enterprise code security configuration | `GET /enterprises/{enterprise}/code-security/configurations/{configuration_id}/repositories` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get code security configurations for an organization | `GET /orgs/{org}/code-security/configurations` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Create a code security configuration | `POST /orgs/{org}/code-security/configurations` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Get default code security configurations | `GET /orgs/{org}/code-security/configurations/defaults` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Detach configurations from repositories | `DELETE /orgs/{org}/code-security/configurations/detach` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Delete a code security configuration | `DELETE /orgs/{org}/code-security/configurations/{configuration_id}` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Get a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a code security configuration | `PATCH /orgs/{org}/code-security/configurations/{configuration_id}` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Attach a configuration to repositories | `POST /orgs/{org}/code-security/configurations/{configuration_id}/attach` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Set a code security configuration as a default for an organization | `PUT /orgs/{org}/code-security/configurations/{configuration_id}/defaults` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Get repositories associated with a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}/repositories` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |
| Get the code security configuration associated with a repository | `GET /repos/{owner}/{repo}/code-security-configuration` | Left to GitHub | Organization-wide code-security configurations are company administration; a repository's own security settings are in the Workbench. |

#### Codes of conduct

2 operations: 1 yes, 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all codes of conduct | `GET /codes_of_conduct` | Yes | Navigator: Repositories > Codes of Conduct |
| Get a code of conduct | `GET /codes_of_conduct/{key}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |

#### Codespaces

48 operations: 35 yes, 6 not needed, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List codespaces for the organization | `GET /orgs/{org}/codespaces` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| Manage access control for organization codespaces | `PUT /orgs/{org}/codespaces/access` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| Remove users from Codespaces access for an organization | `DELETE /orgs/{org}/codespaces/access/selected_users` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| Add users to Codespaces access for an organization | `POST /orgs/{org}/codespaces/access/selected_users` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| List organization secrets | `GET /orgs/{org}/codespaces/secrets` | Yes | Navigator: Organization > organization > Codespaces Secrets |
| Get an organization public key | `GET /orgs/{org}/codespaces/secrets/public-key` | Yes | Navigator: Organization > organization > Codespaces Secrets |
| Delete an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}` | Yes | Navigator: Organization > organization > Codespaces Secrets |
| List selected repositories for an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List codespaces for a user in organization | `GET /orgs/{org}/members/{username}/codespaces` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| Delete a codespace from the organization | `DELETE /orgs/{org}/members/{username}/codespaces/{codespace_name}` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| Stop a codespace for an organization user | `POST /orgs/{org}/members/{username}/codespaces/{codespace_name}/stop` | Left to GitHub | Who in an organization may use Codespaces, and who pays, is billing administration on GitHub's site. |
| List codespaces in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| Create a codespace in a repository | `POST /repos/{owner}/{repo}/codespaces` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| List devcontainer configurations in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces/devcontainers` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| List available machine types for a repository | `GET /repos/{owner}/{repo}/codespaces/machines` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| Get default attributes for a codespace | `GET /repos/{owner}/{repo}/codespaces/new` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| Check if permissions defined by a devcontainer have been accepted by the authenticated user | `GET /repos/{owner}/{repo}/codespaces/permissions_check` | Yes | Navigator: Repository > owner/name > Code > Codespaces |
| List repository secrets | `GET /repos/{owner}/{repo}/codespaces/secrets` | Yes | Navigator: Repository > owner/name > Settings > Codespaces Secrets |
| Get a repository public key | `GET /repos/{owner}/{repo}/codespaces/secrets/public-key` | Yes | Navigator: Repository > owner/name > Settings > Codespaces Secrets |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get a repository secret | `GET /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Yes | Navigator: Repository > owner/name > Settings > Codespaces Secrets |
| Create a codespace from a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/codespaces` | Yes | context menu > Open in a Codespace |
| List codespaces for the authenticated user | `GET /user/codespaces` | Yes | Navigator: Repositories > My Codespaces |
| Create a codespace for the authenticated user | `POST /user/codespaces` | Not needed | Makes a codespace from a repository id or a pull request; the Workbench uses the repository's and the pull request's own routes for the same thing. |
| List secrets for the authenticated user | `GET /user/codespaces/secrets` | Yes | Navigator: People > My Codespaces Secrets |
| Get public key for the authenticated user | `GET /user/codespaces/secrets/public-key` | Yes | Navigator: People > My Codespaces Secrets |
| Delete a secret for the authenticated user | `DELETE /user/codespaces/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get a secret for the authenticated user | `GET /user/codespaces/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update a secret for the authenticated user | `PUT /user/codespaces/secrets/{secret_name}` | Yes | Navigator: People > My Codespaces Secrets |
| List selected repositories for a user secret | `GET /user/codespaces/secrets/{secret_name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove a selected repository from a user secret | `DELETE /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add a selected repository to a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Delete a codespace for the authenticated user | `DELETE /user/codespaces/{codespace_name}` | Yes | context menu > Delete... |
| Get a codespace for the authenticated user | `GET /user/codespaces/{codespace_name}` | Yes | Properties (Alt+Enter) on Codespace |
| Update a codespace for the authenticated user | `PATCH /user/codespaces/{codespace_name}` | Yes | Properties (Alt+Enter) on Codespace: Display name |
| Export a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/exports` | Yes | context menu > Export to a Branch |
| Get details about a codespace export | `GET /user/codespaces/{codespace_name}/exports/{export_id}` | Yes | context menu > Export to a Branch |
| List machine types for a codespace | `GET /user/codespaces/{codespace_name}/machines` | Yes | context menu > Change Machine... |
| Create a repository from an unpublished codespace | `POST /user/codespaces/{codespace_name}/publish` | Yes | context menu > Publish to a New Repository... |
| Start a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/start` | Yes | context menu > Start |
| Stop a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/stop` | Yes | context menu > Stop |

#### Collaborators

11 operations: 11 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List repository collaborators | `GET /repos/{owner}/{repo}/collaborators` | Yes | Navigator: Repository > owner/name > People > Collaborators and Team Access |
| Remove a repository collaborator | `DELETE /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Check if a user is a repository collaborator | `GET /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Add a repository collaborator | `PUT /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get repository permissions for a user | `GET /repos/{owner}/{repo}/collaborators/{username}/permission` | Yes | Account > Roles and Access > Bulk Access Changes... |
| List repository invitations | `GET /repos/{owner}/{repo}/invitations` | Yes | Properties (Alt+Enter) on Invitation |
| Delete a repository invitation | `DELETE /repos/{owner}/{repo}/invitations/{invitation_id}` | Yes | context menu > Delete... |
| Update a repository invitation | `PATCH /repos/{owner}/{repo}/invitations/{invitation_id}` | Yes | Properties (Alt+Enter) on Invitation: Role |
| List repository invitations for the authenticated user | `GET /user/repository_invitations` | Yes | Navigator: Needs My Attention > Invitations |
| Decline a repository invitation | `DELETE /user/repository_invitations/{invitation_id}` | Yes | context menu > Decline Invitation... |
| Accept a repository invitation | `PATCH /user/repository_invitations/{invitation_id}` | Yes | context menu > Accept Invitation... |

#### Commits

14 operations: 12 yes, 2 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List commit comments for a repository | `GET /repos/{owner}/{repo}/comments` | Yes | Navigator: Repository > owner/name > Code > Commit Comments |
| Delete a commit comment | `DELETE /repos/{owner}/{repo}/comments/{comment_id}` | Yes | context menu > Delete... |
| Get a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a commit comment | `PATCH /repos/{owner}/{repo}/comments/{comment_id}` | Yes | context menu > Change... |
| List commits | `GET /repos/{owner}/{repo}/commits` | Yes | Navigator: Repository > owner/name > Code > Commits |
| List branches for HEAD commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/branches-where-head` | Yes | context menu > Branches at This Commit |
| List commit comments | `GET /repos/{owner}/{repo}/commits/{commit_sha}/comments` | Yes | context menu > Commit Comments... |
| Create a commit comment | `POST /repos/{owner}/{repo}/commits/{commit_sha}/comments` | Yes | context menu > Commit Comments... |
| List pull requests associated with a commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/pulls` | Yes | editor GitHub menu > Open the Pull Request for This Line |
| Get a commit | `GET /repos/{owner}/{repo}/commits/{ref}` | Yes | Properties (Alt+Enter) on Commit |
| Get the combined status for a specific reference | `GET /repos/{owner}/{repo}/commits/{ref}/status` | Yes | context menu > Combined Check Status |
| List commit statuses for a reference | `GET /repos/{owner}/{repo}/commits/{ref}/statuses` | Not needed | A commit's statuses are part of Combined Check Status, which already reads them. |
| Compare two commits | `GET /repos/{owner}/{repo}/compare/{basehead}` | Yes | Repository > Compare Branches... (Ctrl+Shift+B) |
| Create a commit status | `POST /repos/{owner}/{repo}/statuses/{sha}` | Yes | context menu > Set Status... |

#### Copilot

44 operations: 44 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get Copilot enterprise usage metrics for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-1-day` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot enterprise usage metrics | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-28-day/latest` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot enterprise repository report for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/repos-1-day` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot enterprise user-teams report for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/user-teams-1-day` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot users usage metrics for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-1-day` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot users usage metrics | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-28-day/latest` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the Copilot code review policy for an enterprise | `GET /enterprises/{enterprise}/copilot/policies/code-review` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the Copilot code review policy for an enterprise | `PUT /enterprises/{enterprise}/copilot/policies/code-review` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the coding agent policy for an enterprise | `PUT /enterprises/{enterprise}/copilot/policies/coding_agent` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove organizations from the enterprise coding agent policy | `DELETE /enterprises/{enterprise}/copilot/policies/coding_agent/organizations` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add organizations to the enterprise coding agent policy | `POST /enterprises/{enterprise}/copilot/policies/coding_agent/organizations` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot seat information and settings for an organization | `GET /orgs/{org}/copilot/billing` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| List all Copilot seat assignments for an organization | `GET /orgs/{org}/copilot/billing/seats` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Remove teams from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_teams` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Add teams to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_teams` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Remove users from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_users` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Add users to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_users` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get the Copilot code review runner configuration for an organization | `GET /orgs/{org}/copilot/code-review/runner` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Set the Copilot code review runner configuration for an organization | `PUT /orgs/{org}/copilot/code-review/runner` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Get Copilot code review settings for an organization | `GET /orgs/{org}/copilot/code-review/settings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Update Copilot code review settings for an organization | `PATCH /orgs/{org}/copilot/code-review/settings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Get Copilot cloud agent permissions for an organization | `GET /orgs/{org}/copilot/coding-agent/permissions` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Set Copilot cloud agent permissions for an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| List repositories enabled for Copilot cloud agent in an organization | `GET /orgs/{org}/copilot/coding-agent/permissions/repositories` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Set selected repositories for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Disable a repository for Copilot cloud agent in an organization | `DELETE /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Enable a repository for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot content exclusion rules for an organization | `GET /orgs/{org}/copilot/content_exclusion` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Set Copilot content exclusion rules for an organization | `PUT /orgs/{org}/copilot/content_exclusion` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/organization-1-day` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization usage metrics | `GET /orgs/{org}/copilot/metrics/reports/organization-28-day/latest` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization repository report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/repos-1-day` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization user-teams report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/user-teams-1-day` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization users usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/users-1-day` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot organization users usage metrics | `GET /orgs/{org}/copilot/metrics/reports/users-28-day/latest` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get the Copilot code review policy for an organization | `GET /orgs/{org}/copilot/policies/code-review` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Set the Copilot code review policy for an organization | `PUT /orgs/{org}/copilot/policies/code-review` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Get Copilot seat assignment details for a user | `GET /orgs/{org}/members/{username}/copilot` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Delete Copilot customizations for a team | `DELETE /orgs/{org}/teams/{team_slug}/copilot/customizations` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot customizations for a team | `GET /orgs/{org}/teams/{team_slug}/copilot/customizations` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Set Copilot customizations for a team | `PUT /orgs/{org}/teams/{team_slug}/copilot/customizations` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot cloud agent configuration for a repository | `GET /repos/{owner}/{repo}/copilot/cloud-agent/configuration` | Left to GitHub | Copilot Business seat, policy and usage administration is for companies that buy Copilot seats, managed on GitHub's site. |
| Get Copilot code review settings for a repository | `GET /repos/{owner}/{repo}/copilot/code-review/settings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Update Copilot code review settings for a repository | `PATCH /repos/{owner}/{repo}/copilot/code-review/settings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |

#### Copilot Spaces

28 operations: 4 not needed, 24 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization Copilot Spaces | `GET /orgs/{org}/copilot-spaces` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Create an organization Copilot Space | `POST /orgs/{org}/copilot-spaces` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Delete an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Get an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Set an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| List collaborators for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/collaborators` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Add a collaborator to an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/collaborators` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Remove a collaborator from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Set a collaborator role for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| List resources for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Create a resource for an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/resources` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Delete a resource from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Get a resource for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Set a resource for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| List Copilot Spaces for a user | `GET /users/{username}/copilot-spaces` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Create a Copilot Space for a user | `POST /users/{username}/copilot-spaces` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Delete a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Get a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Set a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| List collaborators for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/collaborators` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Add a collaborator to a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/collaborators` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Remove a collaborator from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Set a collaborator role for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| List resources for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Create a resource for a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/resources` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Delete a resource from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |
| Get a resource for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Set a resource for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Left to GitHub | Copilot Spaces is a preview; left until GitHub releases it (Jeff, 2026-11-18). |

#### Credentials

1 operations: 1 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Revoke a list of credentials | `POST /credentials/revoke` | Left to GitHub | For secret-scanning partners to revoke leaked credentials, not for people. |

#### Dependabot

27 operations: 17 yes, 4 not needed, 6 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List Dependabot alerts for an enterprise | `GET /enterprises/{enterprise}/dependabot/alerts` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Lists the repositories Dependabot can access in an enterprise | `GET /enterprises/{enterprise}/dependabot/repository-access` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Updates Dependabot's repository access list for an enterprise | `PATCH /enterprises/{enterprise}/dependabot/repository-access` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the default repository access level for Dependabot in an enterprise | `PUT /enterprises/{enterprise}/dependabot/repository-access/default-level` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List Dependabot alerts for an organization | `GET /orgs/{org}/dependabot/alerts` | Yes | Navigator: Organization > organization > Dependabot Alerts |
| Lists the repositories Dependabot can access in an organization | `GET /orgs/{org}/dependabot/repository-access` | Yes | context menu > Dependabot Repository Access |
| Updates Dependabot's repository access list for an organization | `PATCH /orgs/{org}/dependabot/repository-access` | Yes | context menu > Take a Repository from Dependabot... |
| Set the default repository access level for Dependabot | `PUT /orgs/{org}/dependabot/repository-access/default-level` | Yes | context menu > Dependabot's Default Access... |
| List organization secrets | `GET /orgs/{org}/dependabot/secrets` | Yes | Navigator: Organization > organization > Dependabot Secrets |
| Get an organization public key | `GET /orgs/{org}/dependabot/secrets/public-key` | Yes | Navigator: Organization > organization > Dependabot Secrets |
| Delete an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}` | Yes | Navigator: Organization > organization > Dependabot Secrets |
| List selected repositories for an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | Yes | context menu > Repositories Allowed... |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | Not needed | Replaces the whole list at once; Repositories Allowed adds and removes one repository at a time instead, so a change somebody else makes meanwhile is kept. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| Add selected repository to an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | Yes | context menu > Repositories Allowed... |
| List Dependabot alerts for a repository | `GET /repos/{owner}/{repo}/dependabot/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a Dependabot alert | `GET /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a Dependabot alert | `PATCH /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| Get repository Dependabot runner settings | `GET /repos/{owner}/{repo}/dependabot/runner-settings` | Left to GitHub | Where Dependabot runs is company infrastructure, set up once on GitHub's site. |
| Set repository Dependabot runner settings | `PUT /repos/{owner}/{repo}/dependabot/runner-settings` | Left to GitHub | Where Dependabot runs is company infrastructure, set up once on GitHub's site. |
| List repository secrets | `GET /repos/{owner}/{repo}/dependabot/secrets` | Yes | Navigator: Repository > owner/name > Settings > Dependabot Secrets |
| Get a repository public key | `GET /repos/{owner}/{repo}/dependabot/secrets/public-key` | Yes | Navigator: Repository > owner/name > Settings > Dependabot Secrets |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Yes | context menu > Delete... |
| Get a repository secret | `GET /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Yes | Navigator: Repository > owner/name > Settings > Dependabot Secrets |

#### Dependency graph

5 operations: 4 yes, 1 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get a diff of the dependencies between commits | `GET /repos/{owner}/{repo}/dependency-graph/compare/{basehead}` | Yes | context menu > Compare Dependencies... |
| Export a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom` | Yes | Repository > Export Software Bill of Materials... (Ctrl+Alt+B) |
| Fetch a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/fetch-report/{sbom_uuid}` | Yes | context menu > SBOM Report |
| Request generation of a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/generate-report` | Yes | context menu > SBOM Report |
| Create a snapshot of dependencies for a repository | `POST /repos/{owner}/{repo}/dependency-graph/snapshots` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |

#### Deploy keys

4 operations: 4 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List deploy keys | `GET /repos/{owner}/{repo}/keys` | Yes | Properties (Alt+Enter) on Repository |
| Create a deploy key | `POST /repos/{owner}/{repo}/keys` | Yes | Navigator: Repository > owner/name > Settings > Deploy Keys |
| Delete a deploy key | `DELETE /repos/{owner}/{repo}/keys/{key_id}` | Yes | context menu > Delete Deploy Key... |
| Get a deploy key | `GET /repos/{owner}/{repo}/keys/{key_id}` | Yes | Properties (Alt+Enter) on Deploy Key |

#### Deployments

21 operations: 16 yes, 3 not needed, 2 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List deployments | `GET /repos/{owner}/{repo}/deployments` | Yes | Navigator: Repository > owner/name > Deployments and Environments |
| Create a deployment | `POST /repos/{owner}/{repo}/deployments` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Delete a deployment | `DELETE /repos/{owner}/{repo}/deployments/{deployment_id}` | Yes | context menu > Delete Deployment... |
| Get a deployment | `GET /repos/{owner}/{repo}/deployments/{deployment_id}` | Yes | Properties (Alt+Enter) on Deployment |
| List deployment statuses | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | Yes | Properties (Alt+Enter) on Deployment |
| Create a deployment status | `POST /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Get a deployment status | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses/{status_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List environments | `GET /repos/{owner}/{repo}/environments` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Delete an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}` | Yes | context menu > Delete... |
| Get an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}` | Yes | Properties (Alt+Enter) on Environment |
| Create or update an environment | `PUT /repos/{owner}/{repo}/environments/{environment_name}` | Yes | Properties (Alt+Enter) on Environment: Allow administrators to bypass |
| List deployment branch policies | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | Yes | context menu > Branch Policies... |
| Create a deployment branch policy | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | Yes | context menu > Branch Policies... |
| Delete a deployment branch policy | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Yes | context menu > Branch Policies... |
| Get a deployment branch policy | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a deployment branch policy | `PUT /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Yes | context menu > Branch Policies... |
| Get all deployment protection rules for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | Yes | context menu > Protection Rules... |
| Create a custom deployment protection rule on an environment | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | Yes | context menu > Protection Rules... |
| List custom deployment rule integrations available for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/apps` | Yes | context menu > Protection Rules... |
| Disable a custom protection rule for an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | Yes | context menu > Protection Rules... |
| Get a custom deployment protection rule | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |

#### Emojis

1 operations: 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get emojis | `GET /emojis` | Not needed | The emoji list; comment boxes use QUILL's own emoji catalogue. Plumbing. |

#### Gists

20 operations: 17 yes, 2 not needed, 1 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List gists for the authenticated user | `GET /gists` | Yes | Navigator: Gists > My Gists |
| Create a gist | `POST /gists` | Yes | File > New Here... (Ctrl+N) |
| List public gists | `GET /gists/public` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List starred gists | `GET /gists/starred` | Yes | Navigator: Gists > Gists I Starred |
| Delete a gist | `DELETE /gists/{gist_id}` | Yes | context menu > Delete Gist... |
| Get a gist | `GET /gists/{gist_id}` | Yes | Properties (Alt+Enter) on Gist |
| Update a gist | `PATCH /gists/{gist_id}` | Yes | context menu > Edit Gist... |
| List gist comments | `GET /gists/{gist_id}/comments` | Yes | context menu > Comments... |
| Create a gist comment | `POST /gists/{gist_id}/comments` | Yes | context menu > Comments... |
| Delete a gist comment | `DELETE /gists/{gist_id}/comments/{comment_id}` | Yes | context menu > Comments... |
| Get a gist comment | `GET /gists/{gist_id}/comments/{comment_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a gist comment | `PATCH /gists/{gist_id}/comments/{comment_id}` | Yes | context menu > Comments... |
| List gist commits | `GET /gists/{gist_id}/commits` | Yes | context menu > History... |
| List gist forks | `GET /gists/{gist_id}/forks` | Yes | context menu > Forks... |
| Fork a gist | `POST /gists/{gist_id}/forks` | Yes | context menu > Fork Gist |
| Unstar a gist | `DELETE /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Check if a gist is starred | `GET /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Star a gist | `PUT /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Get a gist revision | `GET /gists/{gist_id}/{sha}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List gists for a user | `GET /users/{username}/gists` | Yes | Navigator: Person > person > Gists |

#### Git database

13 operations: 10 yes, 3 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Create a blob | `POST /repos/{owner}/{repo}/git/blobs` | Not needed | Git objects (blobs, trees, commits) are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |
| Get a blob | `GET /repos/{owner}/{repo}/git/blobs/{file_sha}` | Not needed | Git objects (blobs, trees, commits) are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |
| Create a commit | `POST /repos/{owner}/{repo}/git/commits` | Yes | editor GitHub menu > Commit Multiple Files... |
| Get a commit object | `GET /repos/{owner}/{repo}/git/commits/{commit_sha}` | Yes | editor GitHub menu > Commit Multiple Files... |
| List matching references | `GET /repos/{owner}/{repo}/git/matching-refs/{ref}` | Yes | Navigator: Repository > owner/name > Code > Tags |
| Get a reference | `GET /repos/{owner}/{repo}/git/ref/{ref}` | Yes | editor GitHub menu > Commit Multiple Files... |
| Create a reference | `POST /repos/{owner}/{repo}/git/refs` | Yes | context menu > Open Template... |
| Delete a reference | `DELETE /repos/{owner}/{repo}/git/refs/{ref}` | Yes | editor GitHub menu > Delete Branch... |
| Update a reference | `PATCH /repos/{owner}/{repo}/git/refs/{ref}` | Yes | editor GitHub menu > Commit Multiple Files... |
| Create a tag object | `POST /repos/{owner}/{repo}/git/tags` | Yes | Navigator: Repository > owner/name > Code > Tags |
| Get a tag | `GET /repos/{owner}/{repo}/git/tags/{tag_sha}` | Yes | context menu > Read Tag Message |
| Create a tree | `POST /repos/{owner}/{repo}/git/trees` | Yes | editor GitHub menu > Commit Multiple Files... |
| Get a tree | `GET /repos/{owner}/{repo}/git/trees/{tree_sha}` | Not needed | Git objects (blobs, trees, commits) are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |

#### Gitignore

2 operations: 1 yes, 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all gitignore templates | `GET /gitignore/templates` | Yes | Navigator: Repositories > .gitignore Templates |
| Get a gitignore template | `GET /gitignore/templates/{name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |

#### Interactions

16 operations: 9 yes, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Remove interaction restrictions for an organization | `DELETE /orgs/{org}/interaction-limits` | Yes | Properties (Alt+Enter) on Organization: Interaction limit |
| Get interaction restrictions for an organization | `GET /orgs/{org}/interaction-limits` | Yes | Properties (Alt+Enter) on Organization |
| Set interaction restrictions for an organization | `PUT /orgs/{org}/interaction-limits` | Yes | Properties (Alt+Enter) on Organization: Interaction limit |
| Get pull request creation cap for an org | `GET /orgs/{org}/interaction-limits/pulls/creation-cap` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Update pull request creation cap for an org | `PATCH /orgs/{org}/interaction-limits/pulls/creation-cap` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Remove interaction restrictions for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits` | Yes | Properties (Alt+Enter) on Repository: Interaction limit |
| Get interaction restrictions for a repository | `GET /repos/{owner}/{repo}/interaction-limits` | Yes | Properties (Alt+Enter) on Repository |
| Set interaction restrictions for a repository | `PUT /repos/{owner}/{repo}/interaction-limits` | Yes | Properties (Alt+Enter) on Repository: Interaction limit |
| Remove users from the pull request creation cap bypass list for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get pull request creation cap bypass list for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Add users to the pull request creation cap bypass list for a repository | `PUT /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get pull request creation cap for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Update pull request creation cap for a repository | `PATCH /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Remove interaction restrictions from your public repositories | `DELETE /user/interaction-limits` | Yes | context menu > Lift Interaction Limits |
| Get interaction restrictions for your public repositories | `GET /user/interaction-limits` | Yes | context menu > Interaction Limits |
| Set interaction restrictions for your public repositories | `PUT /user/interaction-limits` | Yes | context menu > Limit Interactions... |

#### Issues

66 operations: 46 yes, 13 not needed, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List issues assigned to the authenticated user | `GET /issues` | Not needed | Your issues across repositories; My Work already finds them with GitHub's search. |
| List organization issues assigned to the authenticated user | `GET /orgs/{org}/issues` | Not needed | Your issues across repositories; My Work already finds them with GitHub's search. |
| List assignees | `GET /repos/{owner}/{repo}/assignees` | Yes | context menu > Assignees... |
| Check if a user can be assigned | `GET /repos/{owner}/{repo}/assignees/{assignee}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List repository issues | `GET /repos/{owner}/{repo}/issues` | Yes | Navigator: Repository > owner/name > Issues |
| Create an issue | `POST /repos/{owner}/{repo}/issues` | Yes | File > New Here... (Ctrl+N) |
| List issue comments for a repository | `GET /repos/{owner}/{repo}/issues/comments` | Yes | Navigator: Repository > owner/name > Activity > All Issue Comments |
| Delete an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment |
| Get an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment: Comment |
| Update an issue comment | `PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment: Comment |
| Unpin an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | Yes | context menu > View Timeline... |
| Pin an issue comment | `PUT /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | Yes | context menu > View Timeline... |
| List issue events for a repository | `GET /repos/{owner}/{repo}/issues/events` | Not needed | An issue's events are part of its timeline, which Timeline already reads in full. |
| Get an issue event | `GET /repos/{owner}/{repo}/issues/events/{event_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}` | Yes | context menu > Show Details |
| Update an issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}` | Yes | context menu > Close or Reopen... |
| List issue artifacts | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Create an issue artifact | `POST /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Delete an issue artifact | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get an issue artifact | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an issue artifact | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Remove assignees from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/assignees` | Yes | context menu > Assignees... |
| Add assignees to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/assignees` | Yes | context menu > Assignees... |
| Check if a user can be assigned to a issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/assignees/{assignee}` | Not needed | Whether someone can be assigned is answered by the list of assignees, which the assignee picker already reads. |
| List issue comments | `GET /repos/{owner}/{repo}/issues/{issue_number}/comments` | Yes | Item > Read as Document... (Ctrl+Shift+I) |
| Create an issue comment | `POST /repos/{owner}/{repo}/issues/{issue_number}/comments` | Yes | Item > Comment... (Ctrl+Shift+M) |
| List dependencies an issue is blocked by | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | Yes | context menu > Relationships... |
| Add a dependency an issue is blocked by | `POST /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | Yes | context menu > Relationships... |
| Remove dependency an issue is blocked by | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by/{issue_id}` | Yes | context menu > Relationships... |
| List dependencies an issue is blocking | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocking` | Yes | context menu > Relationships... |
| List issue events | `GET /repos/{owner}/{repo}/issues/{issue_number}/events` | Not needed | An issue's events are part of its timeline, which Timeline already reads in full. |
| List issue field values for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Yes | context menu > Read Issue Type and Fields |
| Add issue field values to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Yes | context menu > Issue Fields... |
| Set issue field values for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Not needed | Setting one field at a time does the same, and keeps a value someone else set on another field; replacing every value would lose it. |
| Delete an issue field value from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values/{issue_field_id}` | Yes | context menu > Issue Fields... |
| Remove all labels from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels` | Not needed | Replaces or clears every label at once; the Workbench adds and removes labels one at a time, so somebody else's change is kept. |
| List labels for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/labels` | Yes | context menu > Labels... |
| Add labels to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/labels` | Yes | context menu > Labels... |
| Set labels for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/labels` | Not needed | Replaces or clears every label at once; the Workbench adds and removes labels one at a time, so somebody else's change is kept. |
| Remove a label from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}` | Yes | context menu > Labels... |
| Unlock an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/lock` | Yes | context menu > Lock or Unlock Conversation... |
| Lock an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/lock` | Yes | context menu > Lock or Unlock Conversation... |
| Get parent issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/parent` | Yes | context menu > Relationships... |
| List issues related to an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | Yes | context menu > Relationships... |
| Add a related issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | Yes | context menu > Relationships... |
| Remove a related issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/relates_to/{issue_id}` | Yes | context menu > Relationships... |
| Remove sub-issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/sub_issue` | Yes | context menu > Relationships... |
| List sub-issues | `GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | Yes | context menu > Reorder Sub-issues... |
| Add sub-issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | Yes | context menu > Relationships... |
| Reprioritize sub-issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/sub_issues/priority` | Yes | context menu > Reorder Sub-issues... |
| List issue suggestions | `GET /repos/{owner}/{repo}/issues/{issue_number}/suggestions` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Approve an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/approve` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Dismiss an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/dismiss` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| List timeline events for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/timeline` | Yes | context menu > View Timeline... |
| List labels for a repository | `GET /repos/{owner}/{repo}/labels` | Yes | Navigator: Repository > owner/name > Labels |
| Create a label | `POST /repos/{owner}/{repo}/labels` | Yes | context menu > Labels... |
| Delete a label | `DELETE /repos/{owner}/{repo}/labels/{name}` | Yes | context menu > Delete Everywhere... |
| Get a label | `GET /repos/{owner}/{repo}/labels/{name}` | Yes | Properties (Alt+Enter) on Label |
| Update a label | `PATCH /repos/{owner}/{repo}/labels/{name}` | Yes | Properties (Alt+Enter) on Label: Colour |
| List milestones | `GET /repos/{owner}/{repo}/milestones` | Yes | Navigator: Repository > owner/name > Milestones |
| Create a milestone | `POST /repos/{owner}/{repo}/milestones` | Yes | context menu > Milestone... |
| Delete a milestone | `DELETE /repos/{owner}/{repo}/milestones/{milestone_number}` | Yes | context menu > Delete Milestone... |
| Get a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}` | Yes | context menu > Milestone... |
| Update a milestone | `PATCH /repos/{owner}/{repo}/milestones/{milestone_number}` | Yes | context menu > Milestone... |
| List labels for issues in a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}/labels` | Not needed | The labels of a milestone's issues, which the issue lists filtered to that milestone already show. |
| List user account issues assigned to the authenticated user | `GET /user/issues` | Not needed | Your issues across repositories; My Work already finds them with GitHub's search. |

#### Licenses

3 operations: 2 yes, 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all commonly used licenses | `GET /licenses` | Yes | Navigator: Repositories > Licences |
| Get a license | `GET /licenses/{license}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get the license for a repository | `GET /repos/{owner}/{repo}/license` | Yes | context menu > License |

#### Markdown

2 operations: 2 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Render a Markdown document | `POST /markdown` | Not needed | Markdown rendering; the Workbench renders Markdown itself. Plumbing. |
| Render a Markdown document in raw mode | `POST /markdown/raw` | Not needed | Markdown rendering; the Workbench renders Markdown itself. Plumbing. |

#### Meta

5 operations: 5 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| GitHub API Root | `GET /` | Not needed | GitHub's own metadata (API root, IP ranges, versions, zen); nothing a person does. Plumbing. |
| Get GitHub meta information | `GET /meta` | Not needed | GitHub's own metadata (API root, IP ranges, versions, zen); nothing a person does. Plumbing. |
| Get Octocat | `GET /octocat` | Not needed | GitHub's own metadata (API root, IP ranges, versions, zen); nothing a person does. Plumbing. |
| Get all API versions | `GET /versions` | Not needed | GitHub's own metadata (API root, IP ranges, versions, zen); nothing a person does. Plumbing. |
| Get the Zen of GitHub | `GET /zen` | Not needed | GitHub's own metadata (API root, IP ranges, versions, zen); nothing a person does. Plumbing. |

#### Metrics

10 operations: 10 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get community profile metrics | `GET /repos/{owner}/{repo}/community/profile` | Yes | Navigator: Repository > owner/name > Insights > Community Profile |
| Get the weekly commit activity | `GET /repos/{owner}/{repo}/stats/code_frequency` | Yes | Navigator: Repository > owner/name > Insights > Commit Activity |
| Get the last year of commit activity | `GET /repos/{owner}/{repo}/stats/commit_activity` | Yes | Navigator: Repository > owner/name > Insights > Commit Activity |
| Get all contributor commit activity | `GET /repos/{owner}/{repo}/stats/contributors` | Yes | Navigator: Repository > owner/name > Insights > Commit Activity |
| Get the weekly commit count | `GET /repos/{owner}/{repo}/stats/participation` | Yes | Navigator: Repository > owner/name > Insights > Commit Activity |
| Get the hourly commit count for each day | `GET /repos/{owner}/{repo}/stats/punch_card` | Yes | Navigator: Repository > owner/name > Insights > Commit Activity |
| Get repository clones | `GET /repos/{owner}/{repo}/traffic/clones` | Yes | Navigator: Repository > owner/name > Insights > Traffic and Contributors |
| Get top referral paths | `GET /repos/{owner}/{repo}/traffic/popular/paths` | Yes | Navigator: Repository > owner/name > Insights > Traffic and Contributors |
| Get top referral sources | `GET /repos/{owner}/{repo}/traffic/popular/referrers` | Yes | Navigator: Repository > owner/name > Insights > Traffic and Contributors |
| Get page views | `GET /repos/{owner}/{repo}/traffic/views` | Yes | Navigator: Repository > owner/name > Insights > Traffic and Contributors |

#### Migrations

22 operations: 2 not needed, 20 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization migrations | `GET /orgs/{org}/migrations` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Start an organization migration | `POST /orgs/{org}/migrations` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Get an organization migration status | `GET /orgs/{org}/migrations/{migration_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Delete an organization migration archive | `DELETE /orgs/{org}/migrations/{migration_id}/archive` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Download an organization migration archive | `GET /orgs/{org}/migrations/{migration_id}/archive` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Unlock an organization repository | `DELETE /orgs/{org}/migrations/{migration_id}/repos/{repo_name}/lock` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| List repositories in an organization migration | `GET /orgs/{org}/migrations/{migration_id}/repositories` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Cancel an import | `DELETE /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get an import status | `GET /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Update an import | `PATCH /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Start an import | `PUT /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get commit authors | `GET /repos/{owner}/{repo}/import/authors` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Map a commit author | `PATCH /repos/{owner}/{repo}/import/authors/{author_id}` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get large files | `GET /repos/{owner}/{repo}/import/large_files` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Update Git LFS preference | `PATCH /repos/{owner}/{repo}/import/lfs` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| List user migrations | `GET /user/migrations` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Start a user migration | `POST /user/migrations` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Get a user migration status | `GET /user/migrations/{migration_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Delete a user migration archive | `DELETE /user/migrations/{migration_id}/archive` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Download a user migration archive | `GET /user/migrations/{migration_id}/archive` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| Unlock a user repository | `DELETE /user/migrations/{migration_id}/repos/{repo_name}/lock` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |
| List repositories for a user migration | `GET /user/migrations/{migration_id}/repositories` | Left to GitHub | Exporting or migrating a whole account or organization is a one-time job done on GitHub's site. |

#### Organizations

129 operations: 74 yes, 12 not needed, 43 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organizations | `GET /organizations` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| Delete an organization | `DELETE /orgs/{org}` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Get an organization | `GET /orgs/{org}` | Yes | Navigator: Organization > organization |
| Update an organization | `PATCH /orgs/{org}` | Yes | Properties (Alt+Enter) on Organization: Base repository permission |
| Create an artifact deployment record | `POST /orgs/{org}/artifacts/metadata/deployment-record` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| Set cluster deployment records | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| Create a cluster deployment records job | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| Get cluster deployment records job status | `GET /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs/{job_id}` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| Create artifact metadata storage record | `POST /orgs/{org}/artifacts/metadata/storage-record` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| List artifact deployment records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/deployment-records` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| List artifact storage records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/storage-records` | Left to GitHub | Build provenance and deployment records are read by tools in a release pipeline, not by a person. |
| List attestations by bulk subject digests | `POST /orgs/{org}/attestations/bulk-list` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations in bulk | `POST /orgs/{org}/attestations/delete-request` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations by subject digest | `DELETE /orgs/{org}/attestations/digest/{subject_digest}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List attestation repositories | `GET /orgs/{org}/attestations/repositories` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations by ID | `DELETE /orgs/{org}/attestations/{attestation_id}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List attestations | `GET /orgs/{org}/attestations/{subject_digest}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List users blocked by an organization | `GET /orgs/{org}/blocks` | Yes | Navigator: Organization > organization > Blocked People |
| Unblock a user from an organization | `DELETE /orgs/{org}/blocks/{username}` | Yes | context menu > Delete... |
| Check if a user is blocked by an organization | `GET /orgs/{org}/blocks/{username}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Block a user from an organization | `PUT /orgs/{org}/blocks/{username}` | Yes | Navigator: Organization > organization > Blocked People |
| List failed organization invitations | `GET /orgs/{org}/failed_invitations` | Yes | Navigator: Organization > organization > Failed Invitations |
| List organization webhooks | `GET /orgs/{org}/hooks` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization webhook | `POST /orgs/{org}/hooks` | Yes | Navigator: Organization > organization > Webhooks |
| Delete an organization webhook | `DELETE /orgs/{org}/hooks/{hook_id}` | Yes | context menu > Delete Webhook... |
| Get an organization webhook | `GET /orgs/{org}/hooks/{hook_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update an organization webhook | `PATCH /orgs/{org}/hooks/{hook_id}` | Yes | context menu > Turn On or Off... |
| Get a webhook configuration for an organization | `GET /orgs/{org}/hooks/{hook_id}/config` | Not needed | A webhook's settings come with the webhook, which its list and sheet already read; changes go through the config route. |
| Update a webhook configuration for an organization | `PATCH /orgs/{org}/hooks/{hook_id}/config` | Yes | context menu > Change Address or Secret... |
| List deliveries for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries` | Yes | context menu > Recent Deliveries... |
| Get a webhook delivery for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Redeliver a delivery for an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | Yes | context menu > Recent Deliveries... |
| Ping an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/pings` | Yes | context menu > Ping |
| Get route stats by actor | `GET /orgs/{org}/insights/api/route-stats/{actor_type}/{actor_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get subject stats | `GET /orgs/{org}/insights/api/subject-stats` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get summary stats | `GET /orgs/{org}/insights/api/summary-stats` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get summary stats by user | `GET /orgs/{org}/insights/api/summary-stats/users/{user_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get summary stats by actor | `GET /orgs/{org}/insights/api/summary-stats/{actor_type}/{actor_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get time stats | `GET /orgs/{org}/insights/api/time-stats` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get time stats by user | `GET /orgs/{org}/insights/api/time-stats/users/{user_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get time stats by actor | `GET /orgs/{org}/insights/api/time-stats/{actor_type}/{actor_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| Get user stats | `GET /orgs/{org}/insights/api/user-stats/{user_id}` | Left to GitHub | API usage statistics are for organizations that run integrations at scale, not something a person edits. |
| List app installations for an organization | `GET /orgs/{org}/installations` | Yes | Navigator: Organization > organization > Installed Apps |
| List pending organization invitations | `GET /orgs/{org}/invitations` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization invitation | `POST /orgs/{org}/invitations` | Yes | Navigator: Organization > organization > Invitations |
| Cancel an organization invitation | `DELETE /orgs/{org}/invitations/{invitation_id}` | Yes | context menu > Delete... |
| List organization invitation teams | `GET /orgs/{org}/invitations/{invitation_id}/teams` | Yes | context menu > Teams It Adds To |
| List issue fields for an organization | `GET /orgs/{org}/issue-fields` | Yes | context menu > Read Issue Type and Fields |
| Create issue field for an organization | `POST /orgs/{org}/issue-fields` | Yes | Navigator: Organization > organization > Issue Fields |
| Delete issue field for an organization | `DELETE /orgs/{org}/issue-fields/{issue_field_id}` | Yes | context menu > Delete... |
| Update issue field for an organization | `PATCH /orgs/{org}/issue-fields/{issue_field_id}` | Yes | context menu > Change... |
| List issue types for an organization | `GET /orgs/{org}/issue-types` | Yes | Properties (Alt+Enter) on Issue Type |
| Create issue type for an organization | `POST /orgs/{org}/issue-types` | Yes | Navigator: Organization > organization > Issue Types |
| Delete issue type for an organization | `DELETE /orgs/{org}/issue-types/{issue_type_id}` | Yes | context menu > Delete... |
| Update issue type for an organization | `PUT /orgs/{org}/issue-types/{issue_type_id}` | Yes | Properties (Alt+Enter) on Issue Type: Colour |
| List organization members | `GET /orgs/{org}/members` | Yes | Properties (Alt+Enter) on Organization |
| Remove an organization member | `DELETE /orgs/{org}/members/{username}` | Yes | context menu > Delete... |
| Check organization membership for a user | `GET /orgs/{org}/members/{username}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Remove organization membership for a user | `DELETE /orgs/{org}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get organization membership for a user | `GET /orgs/{org}/memberships/{username}` | Not needed | Reads one member, whom the organization's Members list already shows in full. |
| Set organization membership for a user | `PUT /orgs/{org}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get all organization roles for an organization | `GET /orgs/{org}/organization-roles` | Yes | Properties (Alt+Enter) on Organization |
| Remove all organization roles for a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}` | Yes | context menu > Roles... |
| Remove an organization role from a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | Yes | context menu > Roles... |
| Assign an organization role to a team | `PUT /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | Yes | context menu > Roles... |
| Remove all organization roles for a user | `DELETE /orgs/{org}/organization-roles/users/{username}` | Yes | context menu > Roles... |
| Remove an organization role from a user | `DELETE /orgs/{org}/organization-roles/users/{username}/{role_id}` | Yes | context menu > Roles... |
| Assign an organization role to a user | `PUT /orgs/{org}/organization-roles/users/{username}/{role_id}` | Yes | context menu > Roles... |
| Get an organization role | `GET /orgs/{org}/organization-roles/{role_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List teams that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/teams` | Yes | context menu > Roles... |
| List users that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/users` | Yes | context menu > Roles... |
| List outside collaborators for an organization | `GET /orgs/{org}/outside_collaborators` | Yes | Properties (Alt+Enter) on Organization |
| Remove outside collaborator from an organization | `DELETE /orgs/{org}/outside_collaborators/{username}` | Yes | context menu > Delete... |
| Convert an organization member to outside collaborator | `PUT /orgs/{org}/outside_collaborators/{username}` | Yes | context menu > Make Someone an Outside Collaborator... |
| List requests to access organization resources with fine-grained personal access tokens | `GET /orgs/{org}/personal-access-token-requests` | Yes | Properties (Alt+Enter) on Organization |
| Review requests to access organization resources with fine-grained personal access tokens | `POST /orgs/{org}/personal-access-token-requests` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| Review a request to access organization resources with a fine-grained personal access token | `POST /orgs/{org}/personal-access-token-requests/{pat_request_id}` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| List repositories requested to be accessed by a fine-grained personal access token | `GET /orgs/{org}/personal-access-token-requests/{pat_request_id}/repositories` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| List fine-grained personal access tokens with access to organization resources | `GET /orgs/{org}/personal-access-tokens` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| Update the access to organization resources via fine-grained personal access tokens | `POST /orgs/{org}/personal-access-tokens` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| Update the access a fine-grained personal access token has to organization resources | `POST /orgs/{org}/personal-access-tokens/{pat_id}` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| List repositories a fine-grained personal access token has access to | `GET /orgs/{org}/personal-access-tokens/{pat_id}/repositories` | Left to GitHub | GitHub serves this to GitHub Apps only (its reference: Only GitHub Apps can use this endpoint), so a person's sign-in is refused; owners review token requests on the organization's settings page. |
| Get registered app installations for external custom properties | `GET /orgs/{org}/properties/installations` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Register an app installation for external custom properties | `POST /orgs/{org}/properties/installations` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Get all external custom properties for a GitHub App installation in an organization | `GET /orgs/{org}/properties/installations/schema` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Create or update external custom property values for organization repositories | `PATCH /orgs/{org}/properties/installations/values` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Remove all external custom property values for a property across all organization repositories | `DELETE /orgs/{org}/properties/installations/values/{property_name}` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Create or update external custom property values for a property across organization repositories | `PATCH /orgs/{org}/properties/installations/values/{property_name}` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| Get all custom properties for an organization | `GET /orgs/{org}/properties/schema` | Yes | Properties (Alt+Enter) on Organization |
| Create or update custom properties for an organization | `PATCH /orgs/{org}/properties/schema` | Yes | context menu > Define a Custom Property... |
| Remove a custom property for an organization | `DELETE /orgs/{org}/properties/schema/{custom_property_name}` | Yes | context menu > Delete... |
| Get a custom property for an organization | `GET /orgs/{org}/properties/schema/{custom_property_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create or update a custom property for an organization | `PUT /orgs/{org}/properties/schema/{custom_property_name}` | Yes | Navigator: Organization > organization > Custom Properties |
| List custom property values for organization repositories | `GET /orgs/{org}/properties/values` | Yes | Navigator: Organization > organization > Custom Property Values |
| Create or update custom property values for organization repositories | `PATCH /orgs/{org}/properties/values` | Yes | context menu > Set Repositories' Custom Property... |
| List public organization members | `GET /orgs/{org}/public_members` | Yes | Navigator: Organization > organization > Public Members |
| Remove public organization membership for the authenticated user | `DELETE /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization: Show my membership publicly |
| Check public organization membership for a user | `GET /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization |
| Set public organization membership for the authenticated user | `PUT /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization: Show my membership publicly |
| Get all organization repository rulesets | `GET /orgs/{org}/rulesets` | Yes | context menu > Rulesets... |
| Create an organization repository ruleset | `POST /orgs/{org}/rulesets` | Yes | context menu > Promote to Organization... |
| List organization rule suites | `GET /orgs/{org}/rulesets/rule-suites` | Yes | context menu > Rulesets... |
| Get an organization rule suite | `GET /orgs/{org}/rulesets/rule-suites/{rule_suite_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Delete an organization repository ruleset | `DELETE /orgs/{org}/rulesets/{ruleset_id}` | Yes | context menu > Rulesets... |
| Get an organization repository ruleset | `GET /orgs/{org}/rulesets/{ruleset_id}` | Yes | context menu > Rulesets... |
| Update an organization repository ruleset | `PUT /orgs/{org}/rulesets/{ruleset_id}` | Yes | context menu > Rulesets... |
| Get organization ruleset history | `GET /orgs/{org}/rulesets/{ruleset_id}/history` | Yes | context menu > Rulesets... |
| Get organization ruleset version | `GET /orgs/{org}/rulesets/{ruleset_id}/history/{version_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List security manager teams | `GET /orgs/{org}/security-managers` | Yes | Navigator: Organization > organization > Security Managers |
| Remove a security manager team | `DELETE /orgs/{org}/security-managers/teams/{team_slug}` | Yes | context menu > Delete... |
| Add a security manager team | `PUT /orgs/{org}/security-managers/teams/{team_slug}` | Yes | Navigator: Organization > organization > Security Managers |
| Get immutable releases settings for an organization | `GET /orgs/{org}/settings/immutable-releases` | Yes | Properties (Alt+Enter) on Organization |
| Set immutable releases settings for an organization | `PUT /orgs/{org}/settings/immutable-releases` | Yes | Properties (Alt+Enter) on Organization: Immutable releases in |
| List selected repositories for immutable releases enforcement | `GET /orgs/{org}/settings/immutable-releases/repositories` | Yes | Navigator: Organization > organization > Immutable Releases: Repositories |
| Set selected repositories for immutable releases enforcement | `PUT /orgs/{org}/settings/immutable-releases/repositories` | Not needed | Adding and removing one repository at a time does the same, and keeps a change someone else made meanwhile; replacing the whole list would lose it. |
| Disable a selected repository for immutable releases in an organization | `DELETE /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | Yes | context menu > Delete... |
| Enable a selected repository for immutable releases in an organization | `PUT /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | Yes | Navigator: Organization > organization > Immutable Releases: Repositories |
| List hosted compute network configurations for an organization | `GET /orgs/{org}/settings/network-configurations` | Left to GitHub | Private networking for hosted runners needs a company Azure setup. |
| Create a hosted compute network configuration for an organization | `POST /orgs/{org}/settings/network-configurations` | Left to GitHub | Private networking for hosted runners needs a company Azure setup. |
| Delete a hosted compute network configuration from an organization | `DELETE /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Left to GitHub | Private networking for hosted runners needs a company Azure setup. |
| Get a hosted compute network configuration for an organization | `GET /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a hosted compute network configuration for an organization | `PATCH /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Left to GitHub | Private networking for hosted runners needs a company Azure setup. |
| Get a hosted compute network settings resource for an organization | `GET /orgs/{org}/settings/network-settings/{network_settings_id}` | Left to GitHub | Private networking for hosted runners needs a company Azure setup. |
| Enable or disable a security feature for an organization | `POST /orgs/{org}/{security_product}/{enablement}` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| List organization memberships for the authenticated user | `GET /user/memberships/orgs` | Yes | Navigator: People > My Organizations' Memberships |
| Get an organization membership for the authenticated user | `GET /user/memberships/orgs/{org}` | Yes | Properties (Alt+Enter) on Organization |
| Update an organization membership for the authenticated user | `PATCH /user/memberships/orgs/{org}` | Yes | context menu > Accept Membership |
| List organizations for the authenticated user | `GET /user/orgs` | Yes | Navigator: Repositories > Organizations |
| List organizations for a user | `GET /users/{username}/orgs` | Yes | Properties (Alt+Enter) on Person |

#### Packages

27 operations: 14 yes, 10 not needed, 3 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get list of conflicting packages during Docker migration for organization | `GET /orgs/{org}/docker/conflicts` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| List packages for an organization | `GET /orgs/{org}/packages` | Yes | Navigator: Organization > organization > Packages |
| Delete a package for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}` | Yes | context menu > Delete Package... |
| Get a package for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}` | Not needed | Reads one package, which its list already shows in full; the Workbench reads the list. |
| Restore a package for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/restore` | Yes | Navigator: Organization > organization > Packages |
| List package versions for a package owned by an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions` | Yes | context menu > Delete Package Version... |
| Delete package version for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Yes | context menu > Delete Package Version... |
| Get a package version for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Restore package version for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Yes | context menu > Restore Package Version... |
| Get list of conflicting packages during Docker migration for authenticated-user | `GET /user/docker/conflicts` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| List packages for the authenticated user's namespace | `GET /user/packages` | Yes | Navigator: Repositories > My Packages |
| Delete a package for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}` | Yes | context menu > Delete Package... |
| Get a package for the authenticated user | `GET /user/packages/{package_type}/{package_name}` | Not needed | Reads one package, which its list already shows in full; the Workbench reads the list. |
| Restore a package for the authenticated user | `POST /user/packages/{package_type}/{package_name}/restore` | Yes | Navigator: Repositories > My Packages |
| List package versions for a package owned by the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions` | Yes | context menu > Delete Package Version... |
| Delete a package version for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | Yes | context menu > Delete Package Version... |
| Get a package version for the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Restore a package version for the authenticated user | `POST /user/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Yes | context menu > Restore Package Version... |
| Get list of conflicting packages during Docker migration for user | `GET /users/{username}/docker/conflicts` | Left to GitHub | Only a GitHub App, using its own app token, or a build tool can call this; a person has no way to. |
| List packages for a user | `GET /users/{username}/packages` | Yes | Navigator: Person > person > Packages |
| Delete a package for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}` | Not needed | Only a package's owner may change it, and the owner reaches the same change through the /user route the Workbench already uses. |
| Get a package for a user | `GET /users/{username}/packages/{package_type}/{package_name}` | Not needed | Reads one package, which its list already shows in full; the Workbench reads the list. |
| Restore a package for a user | `POST /users/{username}/packages/{package_type}/{package_name}/restore` | Not needed | Only a package's owner may change it, and the owner reaches the same change through the /user route the Workbench already uses. |
| List package versions for a package owned by a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions` | Yes | context menu > Show Versions |
| Delete package version for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Not needed | Only a package's owner may change it, and the owner reaches the same change through the /user route the Workbench already uses. |
| Get a package version for a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Restore package version for a user | `POST /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Not needed | Only a package's owner may change it, and the owner reaches the same change through the /user route the Workbench already uses. |

#### Pages

12 operations: 8 yes, 1 not needed, 3 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Delete a GitHub Pages site | `DELETE /repos/{owner}/{repo}/pages` | Yes | context menu > Turn Off Pages... |
| Get a GitHub Pages site | `GET /repos/{owner}/{repo}/pages` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| Create a GitHub Pages site | `POST /repos/{owner}/{repo}/pages` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| Update information about a GitHub Pages site | `PUT /repos/{owner}/{repo}/pages` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| List GitHub Pages builds | `GET /repos/{owner}/{repo}/pages/builds` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| Request a GitHub Pages build | `POST /repos/{owner}/{repo}/pages/builds` | Yes | context menu > Rebuild |
| Get latest Pages build | `GET /repos/{owner}/{repo}/pages/builds/latest` | Yes | context menu > Check Site |
| Get GitHub Pages build | `GET /repos/{owner}/{repo}/pages/builds/{build_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments` | Left to GitHub | Pages deployments are made by the actions/deploy-pages workflow step with the workflow's own identity token, which a person does not have; a workflow run's row already shows them. |
| Get the status of a GitHub Pages deployment | `GET /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}` | Left to GitHub | Pages deployments are made by the actions/deploy-pages workflow step with the workflow's own identity token, which a person does not have; a workflow run's row already shows them. |
| Cancel a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}/cancel` | Left to GitHub | Pages deployments are made by the actions/deploy-pages workflow step with the workflow's own identity token, which a person does not have; a workflow run's row already shows them. |
| Get a DNS health check for GitHub Pages | `GET /repos/{owner}/{repo}/pages/health` | Yes | context menu > Check Site |

#### Private registries

6 operations: 1 not needed, 5 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List private registries for an organization | `GET /orgs/{org}/private-registries` | Left to GitHub | Private package registries for Dependabot are company infrastructure, set up once on GitHub's site. |
| Create a private registry for an organization | `POST /orgs/{org}/private-registries` | Left to GitHub | Private package registries for Dependabot are company infrastructure, set up once on GitHub's site. |
| Get private registries public key for an organization | `GET /orgs/{org}/private-registries/public-key` | Left to GitHub | Private package registries for Dependabot are company infrastructure, set up once on GitHub's site. |
| Delete a private registry for an organization | `DELETE /orgs/{org}/private-registries/{secret_name}` | Left to GitHub | Private package registries for Dependabot are company infrastructure, set up once on GitHub's site. |
| Get a private registry for an organization | `GET /orgs/{org}/private-registries/{secret_name}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a private registry for an organization | `PATCH /orgs/{org}/private-registries/{secret_name}` | Left to GitHub | Private package registries for Dependabot are company infrastructure, set up once on GitHub's site. |

#### Projects

26 operations: 5 yes, 21 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List projects for organization | `GET /orgs/{org}/projectsV2` | Not needed | Projects are listed through GraphQL, which also gives each Project the node id its commands need. |
| Get project for organization | `GET /orgs/{org}/projectsV2/{project_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Create draft item for organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/drafts` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| List project fields for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Add a field to an organization-owned project. | `POST /orgs/{org}/projectsV2/{project_number}/fields` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Get project field for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields/{field_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List items for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Add item to organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/items` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Delete project item for organization | `DELETE /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Get an item for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update project item for organization | `PATCH /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Create a view for an organization-owned project | `POST /orgs/{org}/projectsV2/{project_number}/views` | Yes | context menu > New View... |
| List items for an organization project view | `GET /orgs/{org}/projectsV2/{project_number}/views/{view_number}/items` | Yes | context menu > Items in a View... |
| Create draft item for user owned project | `POST /user/{user_id}/projectsV2/{project_number}/drafts` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Create a view for a user-owned project | `POST /users/{user_id}/projectsV2/{project_number}/views` | Yes | context menu > New View... |
| List projects for user | `GET /users/{username}/projectsV2` | Yes | Navigator: Person > person > Projects |
| Get project for user | `GET /users/{username}/projectsV2/{project_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List project fields for user | `GET /users/{username}/projectsV2/{project_number}/fields` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Add field to user owned project | `POST /users/{username}/projectsV2/{project_number}/fields` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Get project field for user | `GET /users/{username}/projectsV2/{project_number}/fields/{field_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List items for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Add item to user owned project | `POST /users/{username}/projectsV2/{project_number}/items` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Delete project item for user | `DELETE /users/{username}/projectsV2/{project_number}/items/{item_id}` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| Get an item for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items/{item_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update project item for user | `PATCH /users/{username}/projectsV2/{project_number}/items/{item_id}` | Not needed | The Workbench does this through GitHub's GraphQL API (quill/core/github/projects.py and project_admin.py), which covers the same project, item and field; a REST route for it would be a second way to one place. |
| List items for a user project view | `GET /users/{username}/projectsV2/{project_number}/views/{view_number}/items` | Yes | context menu > Items in a View... |

#### Pull requests

39 operations: 28 yes, 7 not needed, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Disable Agent Merge for a pull request | `DELETE /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Yes | context menu > Turn Off Agent Merge... |
| Get Agent Merge configuration for a pull request | `GET /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Yes | context menu > Agent Merge |
| Update Agent Merge configuration for a pull request | `PUT /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Yes | context menu > Turn On Agent Merge |
| List pull requests | `GET /repos/{owner}/{repo}/pulls` | Yes | Navigator: Repository > owner/name > Pull Requests |
| Create a pull request | `POST /repos/{owner}/{repo}/pulls` | Yes | File > New Here... (Ctrl+N) |
| List review comments in a repository | `GET /repos/{owner}/{repo}/pulls/comments` | Not needed | Every review comment in the repository at once; the Workbench reads each pull request's own, where they mean something. |
| Delete a review comment for a pull request | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Yes | context menu > Reviews... |
| Get a review comment for a pull request | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a review comment for a pull request | `PATCH /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Yes | context menu > Reviews... |
| Get a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}` | Yes | Properties (Alt+Enter) on Pull Request |
| Update a pull request | `PATCH /repos/{owner}/{repo}/pulls/{pull_number}` | Yes | Properties (Alt+Enter) on Pull Request: Into branch |
| List review comments on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/comments` | Yes | context menu > Review... |
| Create a review comment for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments` | Yes | context menu > Review... |
| Create a reply for a review comment | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies` | Yes | context menu > Review... |
| List commits on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits` | Yes | Item > File Differences... (Ctrl+Shift+D) |
| Request a Copilot code review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/copilot-code-review` | Yes | context menu > Ask Copilot to Review |
| List pull requests files | `GET /repos/{owner}/{repo}/pulls/{pull_number}/files` | Yes | Item > File Differences... (Ctrl+Shift+D) |
| Check if a pull request has been merged | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge` | Not needed | Whether a pull request is merged is part of the pull request itself, which every list and sheet already reads. |
| Merge a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge` | Yes | Item > Merge... (Ctrl+Shift+Enter) |
| Merge a pull request asynchronously | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge-async` | Not needed | Merges the same way as Merge..., which waits for GitHub's answer; one route per operation. |
| Get the result of an asynchronous merge | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge-async/{uuid}` | Not needed | Only follows a merge-async request, which the Workbench does not make. |
| Remove requested reviewers from a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Get all requested reviewers for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Request reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Rerequest reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers/rerequest` | Yes | context menu > Re-request Review... |
| List reviews for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | Yes | context menu > Review... |
| Create a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | Yes | context menu > Review... |
| Delete a pending review for a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Yes | context menu > Reviews... |
| Get a review for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Yes | context menu > Reviews... |
| List comments for a pull request review | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments` | Yes | context menu > Reviews... |
| Dismiss a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals` | Yes | context menu > Reviews... |
| Submit a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events` | Yes | context menu > Reviews... |
| Update a pull request branch | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/update-branch` | Yes | context menu > Review... |
| List pull request stacks | `GET /repos/{owner}/{repo}/stacks` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Create a pull request stack | `POST /repos/{owner}/{repo}/stacks` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Get a pull request stack | `GET /repos/{owner}/{repo}/stacks/{stack_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Add pull requests to a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/add` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Remove pull requests from a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/unstack` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |

#### Rate limit

1 operations: 1 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get rate limit status for the authenticated user | `GET /rate_limit` | Yes | Account > GitHub API Rate Limit (Ctrl+Shift+L) |

#### Reactions

15 operations: 15 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List reactions for a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}/reactions` | Yes | context menu > Reactions on a Commit Comment... |
| Create reaction for a commit comment | `POST /repos/{owner}/{repo}/comments/{comment_id}/reactions` | Yes | context menu > React to a Commit Comment... |
| Delete a commit comment reaction | `DELETE /repos/{owner}/{repo}/comments/{comment_id}/reactions/{reaction_id}` | Yes | context menu > Remove My Reaction from a Commit Comment... |
| List reactions for an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Create reaction for an issue comment | `POST /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Delete an issue comment reaction | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions/{reaction_id}` | Yes | context menu > React... |
| List reactions for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/reactions` | Yes | context menu > React... |
| Create reaction for an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/reactions` | Yes | context menu > React... |
| Delete an issue reaction | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/reactions/{reaction_id}` | Yes | context menu > React... |
| List reactions for a pull request review comment | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Create reaction for a pull request review comment | `POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Delete a pull request comment reaction | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions/{reaction_id}` | Yes | context menu > React... |
| List reactions for a release | `GET /repos/{owner}/{repo}/releases/{release_id}/reactions` | Yes | context menu > React... |
| Create reaction for a release | `POST /repos/{owner}/{repo}/releases/{release_id}/reactions` | Yes | context menu > React... |
| Delete a release reaction | `DELETE /repos/{owner}/{repo}/releases/{release_id}/reactions/{reaction_id}` | Yes | context menu > React... |

#### Releases

13 operations: 12 yes, 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List releases | `GET /repos/{owner}/{repo}/releases` | Yes | Navigator: Repository > owner/name > Releases |
| Create a release | `POST /repos/{owner}/{repo}/releases` | Yes | editor GitHub menu > Create Release... |
| Delete a release asset | `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Delete Asset... |
| Get a release asset | `GET /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Edit Release... |
| Update a release asset | `PATCH /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Edit Release... |
| Generate release notes content for a release | `POST /repos/{owner}/{repo}/releases/generate-notes` | Yes | context menu > GitHub's Release Notes... |
| Get the latest release | `GET /repos/{owner}/{repo}/releases/latest` | Yes | context menu > Edit Release... |
| Get a release by tag name | `GET /repos/{owner}/{repo}/releases/tags/{tag}` | Yes | context menu > Edit Release... |
| Delete a release | `DELETE /repos/{owner}/{repo}/releases/{release_id}` | Yes | context menu > Delete Release... |
| Get a release | `GET /repos/{owner}/{repo}/releases/{release_id}` | Yes | context menu > Edit Release... |
| Update a release | `PATCH /repos/{owner}/{repo}/releases/{release_id}` | Yes | context menu > Edit Release... |
| List release assets | `GET /repos/{owner}/{repo}/releases/{release_id}/assets` | Not needed | A release's assets come with the release itself, which every read of it returns. |
| Upload a release asset | `POST /repos/{owner}/{repo}/releases/{release_id}/assets` | Yes | context menu > Upload Asset... |

#### Repositories

74 operations: 64 yes, 6 not needed, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization repositories | `GET /orgs/{org}/repos` | Yes | Navigator: Organization > organization > Repositories |
| Create an organization repository | `POST /orgs/{org}/repos` | Yes | editor GitHub menu > Create Repository... |
| Delete a repository | `DELETE /repos/{owner}/{repo}` | Yes | Repository > Repository Actions... (Ctrl+Shift+G) |
| Get a repository | `GET /repos/{owner}/{repo}` | Yes | Navigator: Repository > owner/name |
| Update a repository | `PATCH /repos/{owner}/{repo}` | Yes | editor GitHub menu > Rename Repository... |
| List repository activities | `GET /repos/{owner}/{repo}/activity` | Yes | Navigator: Repository > owner/name > Activity > Push Activity |
| Create an attestation | `POST /repos/{owner}/{repo}/attestations` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List attestations | `GET /repos/{owner}/{repo}/attestations/{subject_digest}` | Yes | context menu > Attestations... |
| Get all autolinks of a repository | `GET /repos/{owner}/{repo}/autolinks` | Yes | Properties (Alt+Enter) on Repository |
| Create an autolink reference for a repository | `POST /repos/{owner}/{repo}/autolinks` | Yes | Navigator: Repository > owner/name > Settings > Autolinks |
| Delete an autolink reference from a repository | `DELETE /repos/{owner}/{repo}/autolinks/{autolink_id}` | Yes | context menu > Delete Autolink... |
| Get an autolink reference of a repository | `GET /repos/{owner}/{repo}/autolinks/{autolink_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Disable Dependabot security updates | `DELETE /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository: Dependabot security updates |
| Check if Dependabot security updates are enabled for a repository | `GET /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository |
| Enable Dependabot security updates | `PUT /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository: Dependabot security updates |
| List CODEOWNERS errors | `GET /repos/{owner}/{repo}/codeowners/errors` | Yes | Navigator: Repository > owner/name > Settings > CODEOWNERS Problems |
| Delete a file | `DELETE /repos/{owner}/{repo}/contents/{path}` | Yes | context menu > Open Template... |
| Get repository content | `GET /repos/{owner}/{repo}/contents/{path}` | Yes | Navigator: Repository > owner/name > Code > Files |
| Create or update file contents | `PUT /repos/{owner}/{repo}/contents/{path}` | Yes | Navigator: Repository > owner/name > Code > Files |
| List repository contributors | `GET /repos/{owner}/{repo}/contributors` | Yes | Navigator: Repository > owner/name > People > Contributors and People |
| Create a repository dispatch event | `POST /repos/{owner}/{repo}/dispatches` | Yes | context menu > Send Repository Dispatch... |
| List forks | `GET /repos/{owner}/{repo}/forks` | Yes | Navigator: Repository > owner/name > People > Forks |
| Create a fork | `POST /repos/{owner}/{repo}/forks` | Yes | editor GitHub menu > Fork Repository... |
| Get the hash algorithm for a repository | `GET /repos/{owner}/{repo}/hash-algorithm` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List repository webhooks | `GET /repos/{owner}/{repo}/hooks` | Yes | Properties (Alt+Enter) on Repository |
| Create a repository webhook | `POST /repos/{owner}/{repo}/hooks` | Yes | Navigator: Repository > owner/name > Settings > Webhooks |
| Delete a repository webhook | `DELETE /repos/{owner}/{repo}/hooks/{hook_id}` | Yes | context menu > Delete Webhook... |
| Get a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}` | Yes | Properties (Alt+Enter) on Webhook |
| Update a repository webhook | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}` | Yes | Properties (Alt+Enter) on Webhook: Active |
| Get a webhook configuration for a repository | `GET /repos/{owner}/{repo}/hooks/{hook_id}/config` | Not needed | A webhook's settings come with the webhook, which its list and sheet already read; changes go through the config route. |
| Update a webhook configuration for a repository | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}/config` | Yes | context menu > Change Address or Secret... |
| List deliveries for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries` | Yes | context menu > Recent Deliveries... |
| Get a delivery for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Redeliver a delivery for a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | Yes | context menu > Recent Deliveries... |
| Ping a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/pings` | Yes | context menu > Ping |
| Test the push repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/tests` | Yes | context menu > Send Test Push |
| Disable immutable releases | `DELETE /repos/{owner}/{repo}/immutable-releases` | Yes | Properties (Alt+Enter) on Repository: Immutable releases |
| Check if immutable releases are enabled for a repository | `GET /repos/{owner}/{repo}/immutable-releases` | Yes | Properties (Alt+Enter) on Repository |
| Enable immutable releases | `PUT /repos/{owner}/{repo}/immutable-releases` | Yes | Properties (Alt+Enter) on Repository: Immutable releases |
| List issue types for a repository | `GET /repos/{owner}/{repo}/issue-types` | Yes | Navigator: Repository > owner/name > Settings > Issue Types |
| List repository languages | `GET /repos/{owner}/{repo}/languages` | Yes | context menu > Languages |
| List planning statuses for a repository | `GET /repos/{owner}/{repo}/planning-statuses` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| Disable private vulnerability reporting for a repository | `DELETE /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository: Private vulnerability reporting |
| Check if private vulnerability reporting is enabled for a repository | `GET /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository |
| Enable private vulnerability reporting for a repository | `PUT /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository: Private vulnerability reporting |
| Get all custom property values for a repository | `GET /repos/{owner}/{repo}/properties/values` | Yes | Navigator: Repository > owner/name > Settings > Custom Property Values |
| Create or update custom property values for a repository | `PATCH /repos/{owner}/{repo}/properties/values` | Yes | context menu > Set a Custom Property... |
| Get a repository README | `GET /repos/{owner}/{repo}/readme` | Yes | Navigator: Repository > owner/name > Overview |
| Get a repository README for a directory | `GET /repos/{owner}/{repo}/readme/{dir}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get rules for a branch | `GET /repos/{owner}/{repo}/rules/branches/{branch}` | Yes | Properties (Alt+Enter) on Branch |
| Get all repository rulesets | `GET /repos/{owner}/{repo}/rulesets` | Yes | Navigator: Repository > owner/name > Settings > Branch Protection |
| Create a repository ruleset | `POST /repos/{owner}/{repo}/rulesets` | Yes | context menu > Add to Missing... |
| List repository rule suites | `GET /repos/{owner}/{repo}/rulesets/rule-suites` | Yes | Navigator: Repository > owner/name > Settings > Rule Insights |
| Get a repository rule suite | `GET /repos/{owner}/{repo}/rulesets/rule-suites/{rule_suite_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Delete a repository ruleset | `DELETE /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | context menu > Promote to Organization... |
| Get a repository ruleset | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | Properties (Alt+Enter) on Ruleset |
| Update a repository ruleset | `PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | Properties (Alt+Enter) on Ruleset: Approvals needed |
| Get repository ruleset history | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history` | Yes | context menu > Ruleset History... |
| Get repository ruleset version | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history/{version_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List repository tags | `GET /repos/{owner}/{repo}/tags` | Yes | Navigator: Repository > owner/name > Code > Tags |
| Download a repository archive (tar) | `GET /repos/{owner}/{repo}/tarball/{ref}` | Yes | context menu > Download Source... |
| List repository teams | `GET /repos/{owner}/{repo}/teams` | Yes | Navigator: Repository > owner/name > People > Collaborators and Team Access |
| Get all repository topics | `GET /repos/{owner}/{repo}/topics` | Yes | Properties (Alt+Enter) on Repository: Topics |
| Replace all repository topics | `PUT /repos/{owner}/{repo}/topics` | Yes | Properties (Alt+Enter) on Repository: Topics |
| Transfer a repository | `POST /repos/{owner}/{repo}/transfer` | Yes | Repository > Transfer Repository... (Ctrl+Alt+T) |
| Disable vulnerability alerts | `DELETE /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository: Dependabot alerts |
| Check if vulnerability alerts are enabled for a repository | `GET /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository |
| Enable vulnerability alerts | `PUT /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository: Dependabot alerts |
| Download a repository archive (zip) | `GET /repos/{owner}/{repo}/zipball/{ref}` | Yes | context menu > Download Source... |
| Create a repository using a template | `POST /repos/{template_owner}/{template_repo}/generate` | Yes | Repository > Repository Actions... (Ctrl+Shift+G) |
| List public repositories | `GET /repositories` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List repositories for the authenticated user | `GET /user/repos` | Yes | Navigator: Repositories > My Repositories |
| Create a repository for the authenticated user | `POST /user/repos` | Yes | editor GitHub menu > Create Repository... |
| List repositories for a user | `GET /users/{username}/repos` | Yes | Navigator: Person > person > Repositories |

#### Search

7 operations: 6 yes, 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Search code | `GET /search/code` | Yes | Navigator: Search > Code |
| Search commits | `GET /search/commits` | Yes | Navigator: Search > Commits |
| Search issues and pull requests | `GET /search/issues` | Yes | Navigator: Search > Issues and Pull Requests |
| Search labels | `GET /search/labels` | Not needed | It searches one repository's labels by that repository's id; each repository's Labels node already lists and filters them. |
| Search repositories | `GET /search/repositories` | Yes | Navigator: Search > Repositories |
| Search topics | `GET /search/topics` | Yes | Navigator: Search > Topics |
| Search users | `GET /search/users` | Yes | Navigator: Search > People and Organizations |

#### Secret scanning

17 operations: 5 yes, 1 not needed, 11 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List secret scanning alerts for an organization | `GET /orgs/{org}/secret-scanning/alerts` | Yes | Navigator: Organization > organization > Secret Scanning Alerts |
| Bulk delete organization custom patterns | `DELETE /orgs/{org}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| List organization custom patterns | `GET /orgs/{org}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| Bulk create organization custom patterns | `POST /orgs/{org}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| Update an organization custom pattern | `PATCH /orgs/{org}/secret-scanning/custom-patterns/{pattern_id}` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| List organization pattern configurations | `GET /orgs/{org}/secret-scanning/pattern-configurations` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| Update organization pattern configurations | `PATCH /orgs/{org}/secret-scanning/pattern-configurations` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| List secret scanning alerts for a repository | `GET /repos/{owner}/{repo}/secret-scanning/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a secret scanning alert | `PATCH /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| List locations for a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}/locations` | Yes | context menu > Where It Was Found |
| Bulk delete repository custom patterns | `DELETE /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| List repository custom patterns | `GET /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| Bulk create repository custom patterns | `POST /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| Update a repository custom pattern | `PATCH /repos/{owner}/{repo}/secret-scanning/custom-patterns/{pattern_id}` | Left to GitHub | Custom secret patterns need paid GitHub Advanced Security. |
| Create a push protection bypass | `POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses` | Left to GitHub | A push that secret scanning blocks is let through from git push itself, with the link GitHub prints there; it is not a Workbench step. |
| Get secret scanning scan history for a repository | `GET /repos/{owner}/{repo}/secret-scanning/scan-history` | Yes | context menu > Secret Scanning History |

#### Security advisories

14 operations: 11 yes, 3 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List global security advisories | `GET /advisories` | Yes | Navigator: Search > Security Advisories |
| Get a global security advisory | `GET /advisories/{ghsa_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List repository security advisories for an organization | `GET /orgs/{org}/security-advisories` | Yes | Navigator: Organization > organization > Security Advisories |
| List repository security advisories | `GET /repos/{owner}/{repo}/security-advisories` | Yes | Navigator: Repository > owner/name > Security > Advisories |
| Create a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories` | Yes | Navigator: Repository > owner/name > Security > Advisories |
| Privately report a security vulnerability | `POST /repos/{owner}/{repo}/security-advisories/reports` | Yes | Navigator: Repository > owner/name > Security > Advisories |
| Get a repository security advisory | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a repository security advisory | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | Yes | context menu > Publish or Close Advisory... |
| List repository security advisory comments | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | Yes | context menu > Advisory Comments |
| Create a repository advisory comment | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | Yes | context menu > Comment on Advisory... |
| Get a repository advisory comment | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Update a repository advisory comment | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | Yes | context menu > Edit an Advisory Comment... |
| Request a CVE for a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/cve` | Yes | context menu > Request CVE... |
| Create a temporary private fork | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/forks` | Yes | context menu > Make a Private Fork for the Fix |

#### Teams

32 operations: 16 yes, 16 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List teams | `GET /orgs/{org}/teams` | Yes | Navigator: Organization > organization > Teams |
| Create a team | `POST /orgs/{org}/teams` | Yes | context menu > New Team... |
| Delete a team | `DELETE /orgs/{org}/teams/{team_slug}` | Yes | context menu > Delete Team... |
| Get a team by name | `GET /orgs/{org}/teams/{team_slug}` | Yes | Properties (Alt+Enter) on Team |
| Update a team | `PATCH /orgs/{org}/teams/{team_slug}` | Yes | Properties (Alt+Enter) on Team: Description |
| List pending team invitations | `GET /orgs/{org}/teams/{team_slug}/invitations` | Yes | context menu > Pending Invitations |
| List team members | `GET /orgs/{org}/teams/{team_slug}/members` | Yes | Properties (Alt+Enter) on Team |
| Remove team membership for a user | `DELETE /orgs/{org}/teams/{team_slug}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get team membership for a user | `GET /orgs/{org}/teams/{team_slug}/memberships/{username}` | Yes | Properties (Alt+Enter) on Team |
| Add or update team membership for a user | `PUT /orgs/{org}/teams/{team_slug}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| List team repositories | `GET /orgs/{org}/teams/{team_slug}/repos` | Yes | Properties (Alt+Enter) on Team |
| Remove a repository from a team | `DELETE /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Check team permissions for a repository | `GET /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | Yes | context menu > Open Template... |
| Add or update team repository permissions | `PUT /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| List child teams | `GET /orgs/{org}/teams/{team_slug}/teams` | Yes | Properties (Alt+Enter) on Team |
| Delete a team (Legacy) | `DELETE /teams/{team_id}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Get a team (Legacy) | `GET /teams/{team_id}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Update a team (Legacy) | `PATCH /teams/{team_id}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| List pending team invitations (Legacy) | `GET /teams/{team_id}/invitations` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| List team members (Legacy) | `GET /teams/{team_id}/members` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Remove team member (Legacy) | `DELETE /teams/{team_id}/members/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Get team member (Legacy) | `GET /teams/{team_id}/members/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Add team member (Legacy) | `PUT /teams/{team_id}/members/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Remove team membership for a user (Legacy) | `DELETE /teams/{team_id}/memberships/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Get team membership for a user (Legacy) | `GET /teams/{team_id}/memberships/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Add or update team membership for a user (Legacy) | `PUT /teams/{team_id}/memberships/{username}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| List team repositories (Legacy) | `GET /teams/{team_id}/repos` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Remove a repository from a team (Legacy) | `DELETE /teams/{team_id}/repos/{owner}/{repo}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Check team permissions for a repository (Legacy) | `GET /teams/{team_id}/repos/{owner}/{repo}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| Add or update team repository permissions (Legacy) | `PUT /teams/{team_id}/repos/{owner}/{repo}` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| List child teams (Legacy) | `GET /teams/{team_id}/teams` | Left to GitHub | Legacy team-by-id route; the Workbench uses the organization and slug route for the same thing. People > My Teams (by organization and slug). |
| List teams for the authenticated user | `GET /user/teams` | Yes | Navigator: People > My Teams |

#### Users

55 operations: 44 yes, 4 not needed, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get the authenticated user | `GET /user` | Yes | View > Say Account (Alt+9) |
| Update the authenticated user | `PATCH /user` | Yes | Properties (Alt+Enter) on Person: Bio |
| List users blocked by the authenticated user | `GET /user/blocks` | Yes | Navigator: People > Blocked People |
| Unblock a user | `DELETE /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person: Blocked |
| Check if a user is blocked by the authenticated user | `GET /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person |
| Block a user | `PUT /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person: Blocked |
| Set primary email visibility for the authenticated user | `PATCH /user/email/visibility` | Yes | context menu > Email Visibility... |
| Delete an email address for the authenticated user | `DELETE /user/emails` | Yes | context menu > Delete... |
| List email addresses for the authenticated user | `GET /user/emails` | Yes | Navigator: People > My Email Addresses |
| Add an email address for the authenticated user | `POST /user/emails` | Yes | Navigator: People > My Email Addresses |
| List followers of the authenticated user | `GET /user/followers` | Yes | Navigator: People > My Followers |
| List the people the authenticated user follows | `GET /user/following` | Yes | Navigator: People > People I Follow |
| Unfollow a user | `DELETE /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| Check if a person is followed by the authenticated user | `GET /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| Follow a user | `PUT /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| List GPG keys for the authenticated user | `GET /user/gpg_keys` | Yes | Navigator: People > My Keys |
| Create a GPG key for the authenticated user | `POST /user/gpg_keys` | Yes | Navigator: People > My Keys |
| Delete a GPG key for the authenticated user | `DELETE /user/gpg_keys/{gpg_key_id}` | Yes | context menu > Delete Key... |
| Get a GPG key for the authenticated user | `GET /user/gpg_keys/{gpg_key_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List issue fields | `GET /user/issue-fields` | Yes | Navigator: People > My Issue Fields |
| Create an issue field | `POST /user/issue-fields` | Yes | Navigator: People > My Issue Fields |
| Delete an issue field | `DELETE /user/issue-fields/{issue_field_id}` | Yes | context menu > Delete... |
| Update an issue field | `PATCH /user/issue-fields/{issue_field_id}` | Yes | context menu > Change... |
| List issue types | `GET /user/issue-types` | Yes | Navigator: People > My Issue Types |
| Create an issue type | `POST /user/issue-types` | Yes | Navigator: People > My Issue Types |
| Delete an issue type | `DELETE /user/issue-types/{issue_type_id}` | Yes | context menu > Delete... |
| Update an issue type | `PUT /user/issue-types/{issue_type_id}` | Yes | context menu > Change... |
| List public SSH keys for the authenticated user | `GET /user/keys` | Yes | Navigator: People > My Keys |
| Create a public SSH key for the authenticated user | `POST /user/keys` | Yes | Navigator: People > My Keys |
| Delete a public SSH key for the authenticated user | `DELETE /user/keys/{key_id}` | Yes | context menu > Delete Key... |
| Get a public SSH key for the authenticated user | `GET /user/keys/{key_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List public email addresses for the authenticated user | `GET /user/public_emails` | Yes | Navigator: People > My Public Email Addresses |
| Delete social accounts for the authenticated user | `DELETE /user/social_accounts` | Yes | context menu > Delete... |
| List social accounts for the authenticated user | `GET /user/social_accounts` | Yes | Navigator: People > My Social Accounts |
| Add social accounts for the authenticated user | `POST /user/social_accounts` | Yes | Navigator: People > My Social Accounts |
| List SSH signing keys for the authenticated user | `GET /user/ssh_signing_keys` | Yes | Navigator: People > My Keys |
| Create a SSH signing key for the authenticated user | `POST /user/ssh_signing_keys` | Yes | Navigator: People > My Keys |
| Delete an SSH signing key for the authenticated user | `DELETE /user/ssh_signing_keys/{ssh_signing_key_id}` | Yes | context menu > Delete Key... |
| Get an SSH signing key for the authenticated user | `GET /user/ssh_signing_keys/{ssh_signing_key_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| Get a user using their ID | `GET /user/{account_id}` | Not needed | Reads one item that its list already shows in full; the Workbench reads the list. |
| List users | `GET /users` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| Get a user | `GET /users/{username}` | Yes | Properties (Alt+Enter) on Person |
| List attestations by bulk subject digests | `POST /users/{username}/attestations/bulk-list` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations in bulk | `POST /users/{username}/attestations/delete-request` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations by subject digest | `DELETE /users/{username}/attestations/digest/{subject_digest}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| Delete attestations by ID | `DELETE /users/{username}/attestations/{attestation_id}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List attestations | `GET /users/{username}/attestations/{subject_digest}` | Left to GitHub | Build provenance (attestations) is read by tools in a release pipeline, not by a person. |
| List followers of a user | `GET /users/{username}/followers` | Yes | Navigator: Person > person > Followers |
| List the people a user follows | `GET /users/{username}/following` | Yes | Navigator: Person > person > Following |
| Check if a user follows another user | `GET /users/{username}/following/{target_user}` | Yes | Properties (Alt+Enter) on Person |
| List GPG keys for a user | `GET /users/{username}/gpg_keys` | Yes | Navigator: Person > person > GPG Keys |
| Get contextual information for a user | `GET /users/{username}/hovercard` | Left to GitHub | Lists every repository, user, organization, gist or event on GitHub; a person works with their own and those they follow, which the Workbench lists. |
| List public keys for a user | `GET /users/{username}/keys` | Yes | Navigator: Person > person > SSH Keys |
| List social accounts for a user | `GET /users/{username}/social_accounts` | Yes | Navigator: Person > person > Social Accounts |
| List SSH signing keys for a user | `GET /users/{username}/ssh_signing_keys` | Yes | Navigator: Person > person > SSH Signing Keys |

### GraphQL mutations, by category

#### GraphQL: Activity

4 mutations: 1 yes, 2 not needed, 1 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addStar` | Not needed | The same change as PUT /user/starred/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |
| `removeStar` | Not needed | The same change as DELETE /user/starred/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |
| `updateNotificationRestrictionSetting` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateSubscription` | Yes | Properties (Alt+Enter) on Issue: Subscribed |

#### GraphQL: Branches

4 mutations: 4 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createBranchProtectionRule` | Not needed | The same change as PUT /repos/{owner}/{repo}/branches/{branch}/protection, the route the Workbench uses for it (already built); one route per operation. |
| `deleteBranchProtectionRule` | Not needed | The same change as DELETE /repos/{owner}/{repo}/branches/{branch}/protection, the route the Workbench uses for it (already built); one route per operation. |
| `mergeBranch` | Not needed | The same change as POST /repos/{owner}/{repo}/merges, the route the Workbench uses for it (planned there); one route per operation. |
| `updateBranchProtectionRule` | Not needed | The same change as PUT /repos/{owner}/{repo}/branches/{branch}/protection, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Checks

5 mutations: 1 not needed, 4 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createCheckRun` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `createCheckSuite` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `rerequestCheckSuite` | Not needed | The same change as POST /repos/{owner}/{repo}/check-suites/{check_suite_id}/rerequest, the route the Workbench uses for it (planned there); one route per operation. |
| `updateCheckRun` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `updateCheckSuitePreferences` | Left to GitHub | Only a GitHub App can create or update check runs and suites. |

#### GraphQL: Commits

1 mutations: 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createCommitOnBranch` | Not needed | The same change as POST /repos/{owner}/{repo}/git/commits, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Copilot

5 mutations: 5 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `updateEnterpriseCopilotCodeReviewPolicy` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateOrganizationCopilotCodeReviewPolicy` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateOrganizationCopilotCodeReviewRunnerConfiguration` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateOrganizationCopilotCodeReviewSettings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateRepositoryCopilotCodeReviewSettings` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |

#### GraphQL: Dependabot

1 mutations: 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `dismissRepositoryVulnerabilityAlert` | Not needed | The same change as PATCH /repos/{owner}/{repo}/dependabot/alerts/{alert_number}, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Deployments

10 mutations: 2 yes, 8 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `approveDeployments` | Not needed | The same change as POST /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments, the route the Workbench uses for it (already built); one route per operation. |
| `createDeployment` | Not needed | The same change as POST /repos/{owner}/{repo}/deployments, the route the Workbench uses for it (planned there); one route per operation. |
| `createDeploymentStatus` | Not needed | The same change as POST /repos/{owner}/{repo}/deployments/{deployment_id}/statuses, the route the Workbench uses for it (planned there); one route per operation. |
| `createEnvironment` | Not needed | The same change as PUT /repos/{owner}/{repo}/environments/{environment_name}, the route the Workbench uses for it (already built); one route per operation. |
| `deleteDeployment` | Not needed | The same change as DELETE /repos/{owner}/{repo}/deployments/{deployment_id}, the route the Workbench uses for it (planned there); one route per operation. |
| `deleteEnvironment` | Not needed | The same change as DELETE /repos/{owner}/{repo}/environments/{environment_name}, the route the Workbench uses for it (planned there); one route per operation. |
| `pinEnvironment` | Yes | context menu > Unpin Environment |
| `rejectDeployments` | Not needed | The same change as POST /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments, the route the Workbench uses for it (already built); one route per operation. |
| `reorderEnvironment` | Yes | context menu > Move Environment... |
| `updateEnvironment` | Not needed | The same change as PUT /repos/{owner}/{repo}/environments/{environment_name}, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Discussions

13 mutations: 13 yes.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addDiscussionComment` | Yes | context menu > Open Discussion Thread |
| `addDiscussionPollVote` | Yes | context menu > Vote... |
| `addUpvote` | Yes | context menu > Upvote |
| `closeDiscussion` | Yes | context menu > Close Discussion... |
| `createDiscussion` | Yes | Navigator: Repository > owner/name > Discussions |
| `deleteDiscussion` | Yes | context menu > Delete Discussion... |
| `deleteDiscussionComment` | Yes | context menu > Delete a Comment... |
| `markDiscussionCommentAsAnswer` | Yes | context menu > Open Discussion Thread |
| `removeUpvote` | Yes | context menu > Remove Upvote |
| `reopenDiscussion` | Yes | context menu > Reopen Discussion |
| `unmarkDiscussionCommentAsAnswer` | Yes | context menu > Open Discussion Thread |
| `updateDiscussion` | Yes | Properties (Alt+Enter) on Discussion: Title |
| `updateDiscussionComment` | Yes | context menu > Edit a Comment... |

#### GraphQL: Enterprise administration

44 mutations: 44 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `acceptEnterpriseAdministratorInvitation` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `acceptEnterpriseMemberInvitation` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `accessUserNamespaceRepository` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `addEnterpriseOrganizationMember` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `addEnterpriseSupportEntitlement` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `cancelEnterpriseAdminInvitation` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `cancelEnterpriseMemberInvitation` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `createEnterpriseOrganization` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `createIpAllowListEntry` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `deleteIpAllowListEntry` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `grantEnterpriseOrganizationsMigratorRole` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `inviteEnterpriseAdmin` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `inviteEnterpriseMember` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `regenerateEnterpriseIdentityProviderRecoveryCodes` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `removeEnterpriseAdmin` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `removeEnterpriseIdentityProvider` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `removeEnterpriseMember` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `removeEnterpriseOrganization` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `removeEnterpriseSupportEntitlement` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `revokeEnterpriseOrganizationsMigratorRole` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `setEnterpriseIdentityProvider` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `transferEnterpriseOrganization` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseAdministratorRole` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseAllowPrivateRepositoryForkingSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseDefaultRepositoryPermissionSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseDeployKeySetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanChangeRepositoryVisibilitySetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanCreateRepositoriesSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanDeleteIssuesSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanDeleteRepositoriesSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanInviteCollaboratorsSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanMakePurchasesSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanUpdateProtectedBranchesSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseMembersCanViewDependencyInsightsSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseOrganizationProjectsSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseOwnerOrganizationRole` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseProfile` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseRepositoryProjectsSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseTwoFactorAuthenticationDisallowedMethodsSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateEnterpriseTwoFactorAuthenticationRequiredSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateIpAllowListEnabledSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateIpAllowListEntry` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateIpAllowListForInstalledAppsEnabledSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| `updateIpAllowListUserLevelEnforcementEnabledSetting` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |

#### GraphQL: Git database

4 mutations: 4 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createRef` | Not needed | Refs and commits on a branch are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |
| `deleteRef` | Not needed | Refs and commits on a branch are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |
| `updateRef` | Not needed | Refs and commits on a branch are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |
| `updateRefs` | Not needed | Refs and commits on a branch are plumbing beneath commands that write files. Plumbing under Commit Multiple Files. |

#### GraphQL: Issues

51 mutations: 18 yes, 31 not needed, 2 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addAssigneesToAssignable` | Not needed | The same change as POST /repos/{owner}/{repo}/issues/{issue_number}/assignees, the route the Workbench uses for it (already built); one route per operation. |
| `addBlockedBy` | Yes | context menu > Reorder Sub-issues... |
| `addCloseIssueReferences` | Yes | context menu > Link a Pull Request That Closes It... |
| `addComment` | Not needed | The same change as POST /repos/{owner}/{repo}/issues/{issue_number}/comments, the route the Workbench uses for it (already built); one route per operation. |
| `addLabelsToLabelable` | Not needed | The same change as POST /repos/{owner}/{repo}/issues/{issue_number}/labels, the route the Workbench uses for it (already built); one route per operation. |
| `addRelatesTo` | Not needed | The Workbench does this through GitHub's REST API (relates_to on Relationships...), which changes the same thing; a second way to one place is not needed. |
| `addSubIssue` | Yes | context menu > Reorder Sub-issues... |
| `applyPendingIssueSuggestions` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `clearLabelsFromLabelable` | Not needed | The same change as DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels, the route the Workbench uses for it (planned there); one route per operation. |
| `closeIssue` | Yes | context menu > Close or Reopen... |
| `createIssue` | Not needed | The same change as POST /repos/{owner}/{repo}/issues, the route the Workbench uses for it (already built); one route per operation. |
| `createIssueField` | Not needed | The Workbench does this through GitHub's REST API (the Issue Fields lists), which changes the same thing; a second way to one place is not needed. |
| `createIssueFieldValue` | Not needed | The Workbench does this through GitHub's REST API (issue-field-values on Issue Fields...), which changes the same thing; a second way to one place is not needed. |
| `createIssueType` | Not needed | The Workbench does this through GitHub's REST API (the Issue Types lists), which changes the same thing; a second way to one place is not needed. |
| `createLabel` | Not needed | The same change as POST /repos/{owner}/{repo}/labels, the route the Workbench uses for it (already built); one route per operation. |
| `createLinkedBranch` | Yes | context menu > Create Branch for This Issue... |
| `deleteIssue` | Yes | context menu > Delete Issue... |
| `deleteIssueComment` | Not needed | The same change as DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}, the route the Workbench uses for it (already built); one route per operation. |
| `deleteIssueField` | Not needed | The Workbench does this through GitHub's REST API (the Issue Fields lists), which changes the same thing; a second way to one place is not needed. |
| `deleteIssueFieldValue` | Not needed | The Workbench does this through GitHub's REST API (issue-field-values on Issue Fields...), which changes the same thing; a second way to one place is not needed. |
| `deleteIssueType` | Not needed | The Workbench does this through GitHub's REST API (the Issue Types lists), which changes the same thing; a second way to one place is not needed. |
| `deleteLabel` | Not needed | The same change as DELETE /repos/{owner}/{repo}/labels/{name}, the route the Workbench uses for it (already built); one route per operation. |
| `deleteLinkedBranch` | Yes | context menu > Unlink Branch... |
| `lockLockable` | Not needed | The same change as PUT /repos/{owner}/{repo}/issues/{issue_number}/lock, the route the Workbench uses for it (already built); one route per operation. |
| `minimizeComment` | Yes | context menu > View Timeline... |
| `pinIssue` | Yes | context menu > Pin or Unpin Issue |
| `pinIssueComment` | Not needed | The same change as the REST route for pinning a comment; one route per operation. |
| `rejectPendingIssueSuggestions` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `removeAssigneesFromAssignable` | Not needed | The same change as DELETE /repos/{owner}/{repo}/issues/{issue_number}/assignees, the route the Workbench uses for it (already built); one route per operation. |
| `removeBlockedBy` | Yes | context menu > Reorder Sub-issues... |
| `removeCloseIssueReferences` | Yes | context menu > Unlink a Pull Request... |
| `removeLabelsFromLabelable` | Not needed | The same change as DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}, the route the Workbench uses for it (already built); one route per operation. |
| `removeRelatesTo` | Not needed | The Workbench does this through GitHub's REST API (relates_to on Relationships...), which changes the same thing; a second way to one place is not needed. |
| `removeSubIssue` | Yes | context menu > Reorder Sub-issues... |
| `reopenIssue` | Not needed | The same change as PATCH /repos/{owner}/{repo}/issues/{issue_number}, the route the Workbench uses for it (already built); one route per operation. |
| `replaceActorsForAssignable` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| `reprioritizeSubIssue` | Not needed | The Workbench does this through GitHub's REST API (sub_issues/priority on Reorder Sub-issues...), which changes the same thing; a second way to one place is not needed. |
| `setIssueFieldValue` | Not needed | The Workbench does this through GitHub's REST API (issue-field-values on Issue Fields...), which changes the same thing; a second way to one place is not needed. |
| `transferIssue` | Yes | context menu > Transfer Issue... |
| `unlockLockable` | Not needed | The same change as DELETE /repos/{owner}/{repo}/issues/{issue_number}/lock, the route the Workbench uses for it (already built); one route per operation. |
| `unmarkIssueAsDuplicate` | Yes | context menu > Not a Duplicate... |
| `unminimizeComment` | Yes | context menu > View Timeline... |
| `unpinIssue` | Yes | context menu > Pin or Unpin Issue |
| `unpinIssueComment` | Not needed | The same change as the REST route for pinning a comment; one route per operation. |
| `updateIssue` | Not needed | The same change as PATCH /repos/{owner}/{repo}/issues/{issue_number}, the route the Workbench uses for it (already built); one route per operation. |
| `updateIssueComment` | Not needed | The same change as PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}, the route the Workbench uses for it (already built); one route per operation. |
| `updateIssueField` | Not needed | The Workbench does this through GitHub's REST API (the Issue Fields lists), which changes the same thing; a second way to one place is not needed. |
| `updateIssueFieldValue` | Not needed | The Workbench does this through GitHub's REST API (issue-field-values on Issue Fields...), which changes the same thing; a second way to one place is not needed. |
| `updateIssueIssueType` | Yes | context menu > Set Issue Type... |
| `updateIssueType` | Not needed | The Workbench does this through GitHub's REST API (the Issue Types lists), which changes the same thing; a second way to one place is not needed. |
| `updateLabel` | Not needed | The same change as PATCH /repos/{owner}/{repo}/labels/{name}, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Migrations

8 mutations: 8 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `abortQueuedMigrations` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `abortRepositoryMigration` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `createAttributionInvitation` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `createMigrationSource` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `grantMigratorRole` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `revokeMigratorRole` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `startOrganizationMigration` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |
| `startRepositoryMigration` | Left to GitHub | GitHub Enterprise Importer migrations, run by administrators with the gh gei extension. |

#### GraphQL: Organizations

11 mutations: 3 yes, 2 not needed, 6 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addVerifiableDomain` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `approveVerifiableDomain` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `deleteVerifiableDomain` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `followOrganization` | Yes | context menu > Follow Organization |
| `regenerateVerifiableDomainToken` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `removeOutsideCollaborator` | Not needed | The same change as DELETE /orgs/{org}/outside_collaborators/{username}, the route the Workbench uses for it (planned there); one route per operation. |
| `setOrganizationInteractionLimit` | Not needed | The same change as PUT /orgs/{org}/interaction-limits, the route the Workbench uses for it (planned there); one route per operation. |
| `unfollowOrganization` | Yes | context menu > Unfollow Organization |
| `updateOrganizationAllowPrivateRepositoryForkingSetting` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `updateOrganizationWebCommitSignoffSetting` | Yes | context menu > Require Sign-off on Web Commits... |
| `verifyVerifiableDomain` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |

#### GraphQL: Packages

1 mutations: 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `deletePackageVersion` | Not needed | The same change as DELETE /user/packages/{package_type}/{package_name}/versions/{package_version_id}, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Projects

32 mutations: 31 yes, 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addProjectV2DraftIssue` | Yes | context menu > Add Draft Issue... |
| `addProjectV2ItemById` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `archiveProjectV2Item` | Yes | Properties (Alt+Enter) on Project |
| `clearProjectV2ItemFieldValue` | Yes | Properties (Alt+Enter) on Project |
| `convertProjectV2DraftIssueItemToIssue` | Yes | context menu > Make a Draft an Issue... |
| `copyProjectV2` | Yes | context menu > Copy Project... |
| `createProjectV2` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `createProjectV2Field` | Yes | context menu > New Field... |
| `createProjectV2IssueField` | Yes | context menu > Add an Issue Field... |
| `createProjectV2StatusUpdate` | Yes | context menu > Post Status Update... |
| `createProjectV2View` | Not needed | New View on a Project makes a view through REST, which GitHub added for both organization and personal Projects. |
| `deleteProjectV2` | Yes | context menu > Delete Project... |
| `deleteProjectV2Field` | Yes | context menu > Delete Field... |
| `deleteProjectV2Item` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `deleteProjectV2StatusUpdate` | Yes | context menu > Delete a Status Update... |
| `deleteProjectV2View` | Yes | context menu > Delete a View... |
| `deleteProjectV2Workflow` | Yes | context menu > Delete a Workflow... |
| `linkProjectV2ToRepository` | Yes | context menu > Link to Repository... |
| `linkProjectV2ToTeam` | Yes | context menu > Link a Team... |
| `markProjectV2AsTemplate` | Yes | context menu > Template... |
| `unarchiveProjectV2Item` | Yes | Properties (Alt+Enter) on Project |
| `unlinkProjectV2FromRepository` | Yes | context menu > Unlink from Repository... |
| `unlinkProjectV2FromTeam` | Yes | context menu > Unlink a Team... |
| `unmarkProjectV2AsTemplate` | Yes | context menu > Template... |
| `updateProjectV2` | Yes | Properties (Alt+Enter) on Project: Title |
| `updateProjectV2Collaborators` | Yes | context menu > Share the Project... |
| `updateProjectV2DraftIssue` | Yes | context menu > Edit a Draft... |
| `updateProjectV2Field` | Yes | context menu > Rename a Field... |
| `updateProjectV2ItemFieldValue` | Yes | Properties (Alt+Enter) on Project |
| `updateProjectV2ItemPosition` | Yes | context menu > Move an Item... |
| `updateProjectV2StatusUpdate` | Yes | context menu > Edit a Status Update... |
| `updateProjectV2View` | Yes | context menu > Rename a View... |

#### GraphQL: Projects (classic)

16 mutations: 16 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addProjectCard` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `addProjectColumn` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `cloneProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `convertProjectCardNoteToIssue` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `createProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `deleteProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `deleteProjectCard` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `deleteProjectColumn` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `importProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `linkRepositoryToProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `moveProjectCard` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `moveProjectColumn` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `unlinkRepositoryFromProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `updateProject` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `updateProjectCard` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |
| `updateProjectColumn` | Left to GitHub | GitHub retired Projects (classic); the Workbench works with Projects (version 2). Projects (version 2). |

#### GraphQL: Pull requests

36 mutations: 12 yes, 19 not needed, 5 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addPullRequestCreationCapBypassUsers` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `addPullRequestReview` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews, the route the Workbench uses for it (already built); one route per operation. |
| `addPullRequestReviewComment` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/comments, the route the Workbench uses for it (already built); one route per operation. |
| `addPullRequestReviewThread` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/comments, the route the Workbench uses for it (already built); one route per operation. |
| `addPullRequestReviewThreadReply` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies, the route the Workbench uses for it (planned there); one route per operation. |
| `archivePullRequest` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `closePullRequest` | Not needed | The same change as PATCH /repos/{owner}/{repo}/pulls/{pull_number}, the route the Workbench uses for it (already built); one route per operation. |
| `convertPullRequestToDraft` | Yes | Properties (Alt+Enter) on Pull Request: Draft |
| `createPullRequest` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls, the route the Workbench uses for it (already built); one route per operation. |
| `deletePullRequestReview` | Not needed | The same change as DELETE /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}, the route the Workbench uses for it (planned there); one route per operation. |
| `deletePullRequestReviewComment` | Not needed | The same change as DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}, the route the Workbench uses for it (planned there); one route per operation. |
| `dequeuePullRequest` | Yes | context menu > Add to or Remove from Merge Queue... |
| `disablePullRequestAutoMerge` | Yes | Properties (Alt+Enter) on Pull Request: Merge automatically when ready |
| `dismissPullRequestReview` | Not needed | The same change as PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals, the route the Workbench uses for it (planned there); one route per operation. |
| `enablePullRequestAutoMerge` | Yes | Properties (Alt+Enter) on Pull Request: Merge automatically when ready |
| `enqueuePullRequest` | Yes | context menu > Add to or Remove from Merge Queue... |
| `markFileAsViewed` | Yes | context menu > Review... |
| `markPullRequestReadyForReview` | Yes | Properties (Alt+Enter) on Pull Request: Draft |
| `mergePullRequest` | Not needed | The same change as PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge, the route the Workbench uses for it (already built); one route per operation. |
| `removePullRequestCreationCapBypassUsers` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `reopenPullRequest` | Not needed | The same change as PATCH /repos/{owner}/{repo}/pulls/{pull_number}, the route the Workbench uses for it (already built); one route per operation. |
| `requestCopilotCodeReview` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `requestReviews` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers, the route the Workbench uses for it (already built); one route per operation. |
| `requestReviewsByLogin` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers, the route the Workbench uses for it (already built); one route per operation. |
| `rerequestReviews` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers, the route the Workbench uses for it (already built); one route per operation. |
| `resolveReviewThread` | Yes | context menu > Review... |
| `revertPullRequest` | Yes | context menu > Revert Pull Request... |
| `submitPullRequestReview` | Not needed | The same change as POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events, the route the Workbench uses for it (planned there); one route per operation. |
| `unarchivePullRequest` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `unmarkFileAsViewed` | Yes | context menu > Review... |
| `unresolveReviewThread` | Yes | context menu > Review... |
| `updatePullRequest` | Not needed | The same change as PATCH /repos/{owner}/{repo}/pulls/{pull_number}, the route the Workbench uses for it (already built); one route per operation. |
| `updatePullRequestBranch` | Not needed | The same change as PUT /repos/{owner}/{repo}/pulls/{pull_number}/update-branch, the route the Workbench uses for it (planned there); one route per operation. |
| `updatePullRequestReview` | Not needed | The same change as PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}, the route the Workbench uses for it (planned there); one route per operation. |
| `updatePullRequestReviewComment` | Not needed | The same change as PATCH /repos/{owner}/{repo}/pulls/comments/{comment_id}, the route the Workbench uses for it (planned there); one route per operation. |
| `updateTeamReviewAssignment` | Yes | Properties (Alt+Enter) on Team: Assign reviews automatically |

#### GraphQL: Reactions

2 mutations: 2 yes.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addReaction` | Yes | context menu > React... |
| `removeReaction` | Yes | context menu > React... |

#### GraphQL: Repositories

18 mutations: 1 yes, 14 not needed, 3 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `acceptTopicSuggestion` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `archiveRepository` | Not needed | The same change as PATCH /repos/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |
| `cloneTemplateRepository` | Not needed | The same change as POST /repos/{template_owner}/{template_repo}/generate, the route the Workbench uses for it (already built); one route per operation. |
| `createRepository` | Not needed | The same change as POST /user/repos, the route the Workbench uses for it (already built); one route per operation. |
| `createRepositoryCustomProperty` | Not needed | The same change as PUT /orgs/{org}/properties/schema/{custom_property_name}, the route the Workbench uses for it (planned there); one route per operation. |
| `createRepositoryRuleset` | Not needed | The same change as POST /repos/{owner}/{repo}/rulesets, the route the Workbench uses for it (already built); one route per operation. |
| `declineTopicSuggestion` | Left to GitHub | A preview GitHub may still change (issue artifacts and suggestions, stacked pull requests, pull request creation caps, code quality, planning statuses, concurrency groups); not built, by Jeff's choice (2026-11-18). |
| `deleteRepositoryCustomProperty` | Not needed | The same change as DELETE /orgs/{org}/properties/schema/{custom_property_name}, the route the Workbench uses for it (planned there); one route per operation. |
| `deleteRepositoryRuleset` | Not needed | The same change as DELETE /repos/{owner}/{repo}/rulesets/{ruleset_id}, the route the Workbench uses for it (already built); one route per operation. |
| `promoteRepositoryCustomProperty` | Left to GitHub | Company administration or a paid feature (Copilot Business policies, AI scanning, security products, verified domains, billing minutes, deleting a whole organization), done on GitHub's site. |
| `setRepositoryCustomPropertyValues` | Not needed | The same change as PATCH /repos/{owner}/{repo}/properties/values, the route the Workbench uses for it (planned there); one route per operation. |
| `setRepositoryInteractionLimit` | Not needed | The same change as PUT /repos/{owner}/{repo}/interaction-limits, the route the Workbench uses for it (already built); one route per operation. |
| `unarchiveRepository` | Not needed | The same change as PATCH /repos/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |
| `updateRepository` | Not needed | The same change as PATCH /repos/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |
| `updateRepositoryCustomProperty` | Not needed | The same change as PUT /orgs/{org}/properties/schema/{custom_property_name}, the route the Workbench uses for it (planned there); one route per operation. |
| `updateRepositoryRuleset` | Not needed | The same change as PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}, the route the Workbench uses for it (already built); one route per operation. |
| `updateRepositoryWebCommitSignoffSetting` | Yes | context menu > Require Sign-off on Web Commits... |
| `updateTopics` | Not needed | The same change as PUT /repos/{owner}/{repo}/topics, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Sponsors

9 mutations: 8 yes, 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `cancelSponsorship` | Yes | context menu > Cancel Sponsorship... |
| `createSponsorsListing` | Yes | context menu > Set Up a Sponsors Profile... |
| `createSponsorsTier` | Yes | context menu > New Sponsor Tier... |
| `createSponsorship` | Yes | context menu > Sponsor at This Tier... |
| `createSponsorships` | Not needed | The same change as createSponsorship, the route the Workbench uses for it (already built); one route per operation. |
| `publishSponsorsTier` | Yes | context menu > Publish Tier |
| `retireSponsorsTier` | Yes | context menu > Retire Tier... |
| `updatePatreonSponsorability` | Yes | context menu > Patreon Sponsorships... |
| `updateSponsorshipPreferences` | Yes | context menu > Sponsorship Preferences... |

#### GraphQL: Teams

1 mutations: 1 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `updateTeamsRepository` | Not needed | The same change as PUT /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}, the route the Workbench uses for it (already built); one route per operation. |

#### GraphQL: Users

8 mutations: 5 yes, 3 not needed.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `changeUserStatus` | Yes | Account > Set Your Status... (Ctrl+Alt+S) |
| `createUserList` | Yes | Navigator: Repositories > Star Lists |
| `deleteUserList` | Yes | context menu > Rename or Delete Star List... |
| `followUser` | Not needed | The same change as PUT /user/following/{username}, the route the Workbench uses for it (already built); one route per operation. |
| `setUserInteractionLimit` | Not needed | The same change as PUT /user/interaction-limits, the route the Workbench uses for it (planned there); one route per operation. |
| `unfollowUser` | Not needed | The same change as DELETE /user/following/{username}, the route the Workbench uses for it (already built); one route per operation. |
| `updateUserList` | Yes | context menu > Rename or Delete Star List... |
| `updateUserListsForItem` | Yes | context menu > Star Lists... |

### GraphQL reads with no REST twin

| Query field | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `DiscussionCategory section` | Left to GitHub | GitHub's GraphQL DiscussionCategory has no section field, so Discussions > Categories lists the categories in GitHub's order and says why, in the list's note. Open on GitHub: the repository's Discussions page. |
| `blockedBy` | Yes | context menu > Reorder Sub-issues... |
| `closingIssuesReferences` | Yes | Properties (Alt+Enter) on Pull Request |
| `compare` | Yes | Navigator: Repository > owner/name > Code > Branches |
| `contributionsCollection` | Yes | Navigator: People > My Profile |
| `dependencyGraphManifests` | Yes | context menu > Dependency Manifests |
| `discussionCategories` | Yes | Navigator: Repository > owner/name > Discussions > Categories |
| `discussions` | Yes | Navigator: Repository > owner/name > Discussions |
| `fundingLinks` | Yes | context menu > Sponsor Links |
| `issueTypes` | Yes | context menu > Set Issue Type... |
| `linkedBranches` | Yes | Properties (Alt+Enter) on Issue: Linked branches |
| `lists` | Yes | Navigator: Repositories > Star Lists |
| `mergeQueue` | Yes | Item > Merge... (Ctrl+Shift+Enter) |
| `pinDiscussion (pin, unpin, reorder)` | Left to GitHub | GitHub's GraphQL API reads pinned discussions (Repository.pinnedDiscussions) but has no mutation to pin, unpin or reorder one, so Discussions > Pinned (spotlight) is read only and says so. Open on GitHub: the discussion's page. |
| `pinnedDiscussions` | Yes | Navigator: Repository > owner/name > Discussions > Pinned (spotlight) |
| `pinnedItems` | Yes | Navigator: People > My Profile |
| `projectsV2` | Yes | Navigator: Repository > owner/name > Projects |
| `rateLimit` | Yes | Account > GitHub API Rate Limit (Ctrl+Shift+L) |
| `reviewDecision` | Yes | Navigator: Repository > owner/name > Pull Requests |
| `reviewThreads` | Yes | context menu > Review... |
| `statusCheckRollup` | Yes | context menu > Combined Check Status |
| `subIssues` | Yes | context menu > Reorder Sub-issues... |
| `suggestedActors` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| `viewerPermission` | Yes | Account > Roles and Access > My Access Here... |

### GitHub Enterprise Cloud and Enterprise Server only

Operations api.github.com's description does not have, read from GitHub's own Enterprise Cloud and Enterprise Server descriptions. For a Server row, the edition column gives the first and last Server version that has it. The Workbench signs in to GitHub.com accounts only, so Server-only rows are left to the server's own pages.

| Operation | Call | Edition | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- | --- |
| Delete a custom image from the enterprise | `DELETE /enterprises/{enterprise}/actions/hosted-runners/images/custom/{image_definition_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an image version of custom image from the enterprise | `DELETE /enterprises/{enterprise}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a GitHub-hosted runner for an enterprise | `DELETE /enterprises/{enterprise}/actions/hosted-runners/{hosted_runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Disable a selected organization for GitHub Actions in an enterprise | `DELETE /enterprises/{enterprise}/actions/permissions/organizations/{org_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an enterprise Actions policy | `DELETE /enterprises/{enterprise}/actions/policies/{policy_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a self-hosted runner group from an enterprise | `DELETE /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove organization access to a self-hosted runner group in an enterprise | `DELETE /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/organizations/{org_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove a self-hosted runner from a group for an enterprise | `DELETE /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a self-hosted runner from an enterprise | `DELETE /enterprises/{enterprise}/actions/runners/{runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove all custom labels from a self-hosted runner for an enterprise | `DELETE /enterprises/{enterprise}/actions/runners/{runner_id}/labels` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove a custom label from a self-hosted runner for an enterprise | `DELETE /enterprises/{enterprise}/actions/runners/{runner_id}/labels/{name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove announcement banner from enterprise | `DELETE /enterprises/{enterprise}/announcement` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Uninstall a GitHub App from an enterprise-owned organization | `DELETE /enterprises/{enterprise}/apps/organizations/{org}/installations/{installation_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an audit log streaming configuration for an enterprise | `DELETE /enterprises/{enterprise}/audit-log/streams/{stream_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove enterprise teams from the Copilot subscription for an enterprise | `DELETE /enterprises/{enterprise}/copilot/billing/selected_enterprise_teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove users from the Copilot subscription for an enterprise | `DELETE /enterprises/{enterprise}/copilot/billing/selected_users` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete the custom agents source for an enterprise | `DELETE /enterprises/{enterprise}/copilot/custom-agents/source` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke enterprise-delegated credential authorizations | `DELETE /enterprises/{enterprise}/credential-authorizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove all enterprise roles from a team | `DELETE /enterprises/{enterprise}/enterprise-roles/teams/{team_slug}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove an enterprise role from a team | `DELETE /enterprises/{enterprise}/enterprise-roles/teams/{team_slug}/{role_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove all enterprise roles from a user | `DELETE /enterprises/{enterprise}/enterprise-roles/users/{username}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove enterprise user role assignment | `DELETE /enterprises/{enterprise}/enterprise-roles/users/{username}/{role_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a hosted compute network configuration from an enterprise | `DELETE /enterprises/{enterprise}/network-configurations/{network_configuration_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove an organization custom property definition from an enterprise | `DELETE /enterprises/{enterprise}/org-properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove a custom property for an enterprise | `DELETE /enterprises/{enterprise}/properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an enterprise repository ruleset | `DELETE /enterprises/{enterprise}/rulesets/{ruleset_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Bulk delete enterprise custom patterns | `DELETE /enterprises/{enterprise}/secret-scanning/custom-patterns` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a budget | `DELETE /enterprises/{enterprise}/settings/billing/budgets/{budget_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a cost center | `DELETE /enterprises/{enterprise}/settings/billing/cost-centers/{cost_center_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove resources from a cost center | `DELETE /enterprises/{enterprise}/settings/billing/cost-centers/{cost_center_id}/resource` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove team membership | `DELETE /enterprises/{enterprise}/teams/{enterprise-team}/memberships/{username}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an organization assignment | `DELETE /enterprises/{enterprise}/teams/{enterprise-team}/organizations/{org}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an enterprise team | `DELETE /enterprises/{enterprise}/teams/{team_slug}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete a Visual Studio subscription user match | `DELETE /enterprises/{enterprise}/visual-studio-subscriptions/{visual_studio_subscription_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove announcement banner from organization | `DELETE /orgs/{org}/announcement` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Remove a SAML SSO authorization for an organization | `DELETE /orgs/{org}/credential-authorizations/{credential_id}` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| Delete a custom repository role | `DELETE /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Closing down - Delete a custom role | `DELETE /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Delete a custom organization role. | `DELETE /orgs/{org}/organization-roles/{role_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Remove the connection between an external group and a team | `DELETE /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Dismiss a response on a bypass request for secret scanning | `DELETE /repos/{owner}/{repo}/bypass-responses/secret-scanning/{bypass_response_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Cancel a dismissal request for a Dependabot alert for a repository | `DELETE /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Disable Git LFS for a repository | `DELETE /repos/{owner}/{repo}/lfs` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Delete a SCIM group from an enterprise | `DELETE /scim/v2/enterprises/{enterprise}/Groups/{scim_group_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Delete a SCIM user from an enterprise | `DELETE /scim/v2/enterprises/{enterprise}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Delete a SCIM user from an organization | `DELETE /scim/v2/organizations/{org}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Enterprise Server statistics | `GET /enterprise-installation/{enterprise_or_org}/server-statistics` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions cache usage for an enterprise | `GET /enterprises/{enterprise}/actions/cache/usage` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List GitHub-hosted runners for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List custom images for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/images/custom` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise custom image definition for GitHub Actions Hosted Runners | `GET /enterprises/{enterprise}/actions/hosted-runners/images/custom/{image_definition_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List image versions of a custom image for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/images/custom/{image_definition_id}/versions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an image version of an enterprise custom image for GitHub Actions Hosted Runners | `GET /enterprises/{enterprise}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub-owned images for GitHub-hosted runners in an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/images/github-owned` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get partner images for GitHub-hosted runners in an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/images/partner` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get limits on GitHub-hosted runners for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/limits` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub-hosted runners machine specs for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/machine-sizes` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get platforms for GitHub-hosted runners in an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/platforms` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a GitHub-hosted runner for an enterprise | `GET /enterprises/{enterprise}/actions/hosted-runners/{hosted_runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions permissions for an enterprise | `GET /enterprises/{enterprise}/actions/permissions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get artifact and log retention settings for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/artifact-and-log-retention` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get fork PR contributor approval permissions for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/fork-pr-contributor-approval` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get private repo fork PR workflow settings for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/fork-pr-workflows-private-repos` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List selected organizations enabled for GitHub Actions in an enterprise | `GET /enterprises/{enterprise}/actions/permissions/organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get allowed actions and reusable workflows for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/selected-actions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get self-hosted runners permissions for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/self-hosted-runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get default workflow permissions for an enterprise | `GET /enterprises/{enterprise}/actions/permissions/workflow` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise Actions policies | `GET /enterprises/{enterprise}/actions/policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise Actions policy | `GET /enterprises/{enterprise}/actions/policies/{policy_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List self-hosted runner groups for an enterprise | `GET /enterprises/{enterprise}/actions/runner-groups` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a self-hosted runner group for an enterprise | `GET /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List organization access to a self-hosted runner group in an enterprise | `GET /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List self-hosted runners in a group for an enterprise | `GET /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List self-hosted runners for an enterprise | `GET /enterprises/{enterprise}/actions/runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get runner version end-of-life schedule for an enterprise | `GET /enterprises/{enterprise}/actions/runners/deprecations/{version}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List runner applications for an enterprise | `GET /enterprises/{enterprise}/actions/runners/downloads` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a self-hosted runner for an enterprise | `GET /enterprises/{enterprise}/actions/runners/{runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List labels for a self-hosted runner for an enterprise | `GET /enterprises/{enterprise}/actions/runners/{runner_id}/labels` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get announcement banner for enterprise | `GET /enterprises/{enterprise}/announcement` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get enterprise-owned organizations that can have GitHub Apps installed | `GET /enterprises/{enterprise}/apps/installable_organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get repositories belonging to an enterprise-owned organization | `GET /enterprises/{enterprise}/apps/installable_organizations/{org}/accessible_repositories` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List GitHub Apps installed on an enterprise-owned organization | `GET /enterprises/{enterprise}/apps/organizations/{org}/installations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the repositories accessible to a given GitHub App installation | `GET /enterprises/{enterprise}/apps/organizations/{org}/installations/{installation_id}/repositories` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the audit log for an enterprise | `GET /enterprises/{enterprise}/audit-log` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the audit log stream key for encrypting secrets | `GET /enterprises/{enterprise}/audit-log/stream-key` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List audit log stream configurations for an enterprise | `GET /enterprises/{enterprise}/audit-log/streams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List one audit log streaming configuration via a stream ID | `GET /enterprises/{enterprise}/audit-log/streams/{stream_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List push rule bypass requests within an enterprise | `GET /enterprises/{enterprise}/bypass-requests/push-rules` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List bypass requests for secret scanning for an enterprise | `GET /enterprises/{enterprise}/bypass-requests/secret-scanning` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List code scanning alerts for an enterprise | `GET /enterprises/{enterprise}/code-scanning/alerts` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get code security and analysis features for an enterprise | `GET /enterprises/{enterprise}/code_security_and_analysis` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise consumed licenses | `GET /enterprises/{enterprise}/consumed-licenses` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get model policies for agent apps | `GET /enterprises/{enterprise}/copilot/apps/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List all Copilot seat assignments for an enterprise | `GET /enterprises/{enterprise}/copilot/billing/seats` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot content exclusion rules for an enterprise | `GET /enterprises/{enterprise}/copilot/content_exclusion` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get custom agents for an enterprise | `GET /enterprises/{enterprise}/copilot/custom-agents` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the source organization for custom agents in an enterprise | `GET /enterprises/{enterprise}/copilot/custom-agents/source` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get feature policies for an enterprise | `GET /enterprises/{enterprise}/copilot/feature-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot Fusion model policies for an enterprise | `GET /enterprises/{enterprise}/copilot/fusion/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get model policies for an enterprise | `GET /enterprises/{enterprise}/copilot/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot usage records for an enterprise | `GET /enterprises/{enterprise}/copilot/usage-records` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise token inventory | `GET /enterprises/{enterprise}/credentials` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise token inventory export | `GET /enterprises/{enterprise}/credentials/exports/{export_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise token inventory item | `GET /enterprises/{enterprise}/credentials/{inventory_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List alert dismissal requests for secret scanning for an enterprise | `GET /enterprises/{enterprise}/dismissal-requests/secret-scanning` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get all enterprise roles for an enterprise | `GET /enterprises/{enterprise}/enterprise-roles` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise role | `GET /enterprises/{enterprise}/enterprise-roles/{role_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List teams that are assigned to an enterprise role | `GET /enterprises/{enterprise}/enterprise-roles/{role_id}/teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List users that are assigned to an enterprise role | `GET /enterprises/{enterprise}/enterprise-roles/{role_id}/users` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get innersource vulnerability sync status for an enterprise | `GET /enterprises/{enterprise}/innersource-vulnerabilities/sync/status/{job_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise installation for the authenticated app | `GET /enterprises/{enterprise}/installation` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get the license compliance policy for an enterprise | `GET /enterprises/{enterprise}/license-compliance/policies/{policy_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a license sync status | `GET /enterprises/{enterprise}/license-sync-status` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get Copilot seat assignment details for an enterprise user | `GET /enterprises/{enterprise}/members/{username}/copilot` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise teams for a user | `GET /enterprises/{enterprise}/members/{username}/teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List hosted compute network configurations for an enterprise | `GET /enterprises/{enterprise}/network-configurations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a hosted compute network configuration for an enterprise | `GET /enterprises/{enterprise}/network-configurations/{network_configuration_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a hosted compute network settings resource for an enterprise | `GET /enterprises/{enterprise}/network-settings/{network_settings_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get organization custom properties schema for an enterprise | `GET /enterprises/{enterprise}/org-properties/schema` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an organization custom property definition from an enterprise | `GET /enterprises/{enterprise}/org-properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List custom property values for organizations in an enterprise | `GET /enterprises/{enterprise}/org-properties/values` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get custom properties for an enterprise | `GET /enterprises/{enterprise}/properties/schema` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a custom property for an enterprise | `GET /enterprises/{enterprise}/properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise repository ruleset | `GET /enterprises/{enterprise}/rulesets/{ruleset_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get enterprise ruleset history | `GET /enterprises/{enterprise}/rulesets/{ruleset_id}/history` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get enterprise ruleset version | `GET /enterprises/{enterprise}/rulesets/{ruleset_id}/history/{version_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List secret scanning alerts for an enterprise | `GET /enterprises/{enterprise}/secret-scanning/alerts` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise custom patterns | `GET /enterprises/{enterprise}/secret-scanning/custom-patterns` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise pattern configurations | `GET /enterprises/{enterprise}/secret-scanning/pattern-configurations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List public monitoring alerts for an enterprise | `GET /enterprises/{enterprise}/secret-scanning/public-monitoring-alerts` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a public monitoring alert for an enterprise | `GET /enterprises/{enterprise}/secret-scanning/public-monitoring-alerts/{alert_number}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Advanced Security active committers for an enterprise | `GET /enterprises/{enterprise}/settings/billing/advanced-security` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get billing AI credit usage report for an enterprise | `GET /enterprises/{enterprise}/settings/billing/ai_credit/usage` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get all budgets | `GET /enterprises/{enterprise}/settings/billing/budgets` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a budget by ID | `GET /enterprises/{enterprise}/settings/billing/budgets/{budget_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get user states for a multi-user budget | `GET /enterprises/{enterprise}/settings/billing/budgets/{budget_id}/user-states` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get all cost centers for an enterprise | `GET /enterprises/{enterprise}/settings/billing/cost-centers` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get cost center membership for a resource | `GET /enterprises/{enterprise}/settings/billing/cost-centers/memberships` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a cost center by ID | `GET /enterprises/{enterprise}/settings/billing/cost-centers/{cost_center_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get billing premium request usage report for an enterprise | `GET /enterprises/{enterprise}/settings/billing/premium_request/usage` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List usage report exports | `GET /enterprises/{enterprise}/settings/billing/reports` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a usage report export | `GET /enterprises/{enterprise}/settings/billing/reports/{report_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get billing usage report for an enterprise | `GET /enterprises/{enterprise}/settings/billing/usage` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get billing usage summary for an enterprise | `GET /enterprises/{enterprise}/settings/billing/usage/summary` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List enterprise teams | `GET /enterprises/{enterprise}/teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List members in an enterprise team | `GET /enterprises/{enterprise}/teams/{enterprise-team}/memberships` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get enterprise team membership | `GET /enterprises/{enterprise}/teams/{enterprise-team}/memberships/{username}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get organization assignments | `GET /enterprises/{enterprise}/teams/{enterprise-team}/organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get organization assignment | `GET /enterprises/{enterprise}/teams/{enterprise-team}/organizations/{org}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get model policies for an enterprise team | `GET /enterprises/{enterprise}/teams/{team_id}/copilot/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get an enterprise team | `GET /enterprises/{enterprise}/teams/{team_slug}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get a list of Visual Studio subscriptions for the enterprise | `GET /enterprises/{enterprise}/visual-studio-subscriptions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Closing down - List custom repository roles in an organization | `GET /organizations/{organization_id}/custom_roles` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Get all custom property values for an organization | `GET /organizations/{org}/org-properties/values` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get announcement banner for organization | `GET /orgs/{org}/announcement` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get the audit log for an organization | `GET /orgs/{org}/audit-log` | Cloud | Left to GitHub | The organization audit log API needs GitHub Enterprise Cloud. |
| List push rule bypass requests within an organization | `GET /orgs/{org}/bypass-requests/push-rules` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List bypass requests for secret scanning for an org | `GET /orgs/{org}/bypass-requests/secret-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get feature policies for an organization | `GET /orgs/{org}/copilot/feature-policies` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get model policies for an organization | `GET /orgs/{org}/copilot/model-policies` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List SAML SSO authorizations for an organization | `GET /orgs/{org}/credential-authorizations` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| List custom repository roles in an organization | `GET /orgs/{org}/custom-repository-roles` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get a custom repository role | `GET /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Closing down - Get a custom role | `GET /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| List dismissal requests for code scanning alerts for an organization | `GET /orgs/{org}/dismissal-requests/code-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List dismissal requests for Dependabot alerts for an organization | `GET /orgs/{org}/dismissal-requests/dependabot` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List alert dismissal requests for secret scanning for an org | `GET /orgs/{org}/dismissal-requests/secret-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get an external group | `GET /orgs/{org}/external-group/{group_id}` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List external groups available to an organization | `GET /orgs/{org}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Closing down - List fine-grained permissions for an organization | `GET /orgs/{org}/fine_grained_permissions` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| List organization fine-grained permissions for an organization | `GET /orgs/{org}/organization-fine-grained-permissions` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List repository fine-grained permissions for an organization | `GET /orgs/{org}/repository-fine-grained-permissions` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get GitHub Advanced Security active committers for an organization | `GET /orgs/{org}/settings/billing/advanced-security` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List IdP groups for an organization | `GET /orgs/{org}/team-sync/groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List a connection between an external group and a team | `GET /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List IdP groups for a team | `GET /orgs/{org}/teams/{team_slug}/team-sync/group-mappings` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List repository push rule bypass requests | `GET /repos/{owner}/{repo}/bypass-requests/push-rules` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get a repository push bypass request | `GET /repos/{owner}/{repo}/bypass-requests/push-rules/{bypass_request_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List bypass requests for secret scanning for a repository | `GET /repos/{owner}/{repo}/bypass-requests/secret-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get a bypass request for secret scanning | `GET /repos/{owner}/{repo}/bypass-requests/secret-scanning/{bypass_request_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List dismissal requests for code scanning alerts for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/code-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get a dismissal request for a code scanning alert for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/code-scanning/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List dismissal requests for Dependabot alerts for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/dependabot` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get a dismissal request for a Dependabot alert for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List alert dismissal requests for secret scanning for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/secret-scanning` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Get an alert dismissal request for secret scanning | `GET /repos/{owner}/{repo}/dismissal-requests/secret-scanning/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| List provisioned SCIM groups for an enterprise | `GET /scim/v2/enterprises/{enterprise}/Groups` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Get SCIM provisioning information for an enterprise group | `GET /scim/v2/enterprises/{enterprise}/Groups/{scim_group_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| List SCIM provisioned identities for an enterprise | `GET /scim/v2/enterprises/{enterprise}/Users` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Get SCIM provisioning information for an enterprise user | `GET /scim/v2/enterprises/{enterprise}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| List SCIM provisioned identities | `GET /scim/v2/organizations/{org}/Users` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Get SCIM provisioning information for a user | `GET /scim/v2/organizations/{org}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| List IdP groups for a team (Legacy) | `GET /teams/{team_id}/team-sync/group-mappings` | Cloud | Left to GitHub | Legacy team-by-id route; the organization and slug route does the same. People > My Teams (by organization and slug). |
| Update a GitHub-hosted runner for an enterprise | `PATCH /enterprises/{enterprise}/actions/hosted-runners/{hosted_runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a self-hosted runner group for an enterprise | `PATCH /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set announcement banner for enterprise | `PATCH /enterprises/{enterprise}/announcement` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Toggle installation repository access between selected and all repositories | `PATCH /enterprises/{enterprise}/apps/organizations/{org}/installations/{installation_id}/repositories` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Grant repository access to an organization installation | `PATCH /enterprises/{enterprise}/apps/organizations/{org}/installations/{installation_id}/repositories/add` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove repository access from an organization installation | `PATCH /enterprises/{enterprise}/apps/organizations/{org}/installations/{installation_id}/repositories/remove` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update code security and analysis features for an enterprise | `PATCH /enterprises/{enterprise}/code_security_and_analysis` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update model policies for enterprise apps | `PATCH /enterprises/{enterprise}/copilot/apps/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update feature policies for an enterprise | `PATCH /enterprises/{enterprise}/copilot/feature-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update Copilot Fusion model policies for an enterprise | `PATCH /enterprises/{enterprise}/copilot/fusion/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update model policies for an enterprise | `PATCH /enterprises/{enterprise}/copilot/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a hosted compute network configuration for an enterprise | `PATCH /enterprises/{enterprise}/network-configurations/{network_configuration_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update organization custom property definitions on an enterprise | `PATCH /enterprises/{enterprise}/org-properties/schema` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update custom property values for organizations in an enterprise | `PATCH /enterprises/{enterprise}/org-properties/values` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update custom properties for an enterprise | `PATCH /enterprises/{enterprise}/properties/schema` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update an enterprise custom pattern | `PATCH /enterprises/{enterprise}/secret-scanning/custom-patterns/{pattern_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update enterprise pattern configurations | `PATCH /enterprises/{enterprise}/secret-scanning/pattern-configurations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a public monitoring alert for an enterprise | `PATCH /enterprises/{enterprise}/secret-scanning/public-monitoring-alerts/{alert_number}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a budget | `PATCH /enterprises/{enterprise}/settings/billing/budgets/{budget_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update a cost center | `PATCH /enterprises/{enterprise}/settings/billing/cost-centers/{cost_center_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update model policies for an enterprise team | `PATCH /enterprises/{enterprise}/teams/{team_id}/copilot/model-policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update an enterprise team | `PATCH /enterprises/{enterprise}/teams/{team_slug}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update custom property values for an organization | `PATCH /organizations/{org}/org-properties/values` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Set announcement banner for organization | `PATCH /orgs/{org}/announcement` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Update feature policies for an organization | `PATCH /orgs/{org}/copilot/feature-policies` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Update model policies for an organization | `PATCH /orgs/{org}/copilot/model-policies` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Update a custom repository role | `PATCH /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Closing down - Update a custom role | `PATCH /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Update a custom organization role | `PATCH /orgs/{org}/organization-roles/{role_id}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Update the connection between an external group and a team | `PATCH /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Create or update IdP group connections | `PATCH /orgs/{org}/teams/{team_slug}/team-sync/group-mappings` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Review a bypass request for secret scanning | `PATCH /repos/{owner}/{repo}/bypass-requests/secret-scanning/{bypass_request_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Review a dismissal request for a code scanning alert for a repository | `PATCH /repos/{owner}/{repo}/dismissal-requests/code-scanning/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Review a dismissal request for a Dependabot alert for a repository | `PATCH /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Review an alert dismissal request for secret scanning | `PATCH /repos/{owner}/{repo}/dismissal-requests/secret-scanning/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Update an attribute for a SCIM enterprise group | `PATCH /scim/v2/enterprises/{enterprise}/Groups/{scim_group_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Update an attribute for a SCIM enterprise user | `PATCH /scim/v2/enterprises/{enterprise}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Update an attribute for a SCIM user | `PATCH /scim/v2/organizations/{org}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Create or update IdP group connections (Legacy) | `PATCH /teams/{team_id}/team-sync/group-mappings` | Cloud | Left to GitHub | Legacy team-by-id route; the organization and slug route does the same. People > My Teams (by organization and slug). |
| Disable access restrictions for an enterprise | `POST /enterprises/{enterprise}/access-restrictions/disable` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Enable access restrictions for an enterprise | `POST /enterprises/{enterprise}/access-restrictions/enable` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a GitHub-hosted runner for an enterprise | `POST /enterprises/{enterprise}/actions/hosted-runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an enterprise Actions policy | `POST /enterprises/{enterprise}/actions/policies` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a self-hosted runner group for an enterprise | `POST /enterprises/{enterprise}/actions/runner-groups` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create configuration for a just-in-time runner for an Enterprise | `POST /enterprises/{enterprise}/actions/runners/generate-jitconfig` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a registration token for an enterprise | `POST /enterprises/{enterprise}/actions/runners/registration-token` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a remove token for an enterprise | `POST /enterprises/{enterprise}/actions/runners/remove-token` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add custom labels to a self-hosted runner for an enterprise | `POST /enterprises/{enterprise}/actions/runners/{runner_id}/labels` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Install a GitHub App on an enterprise-owned organization | `POST /enterprises/{enterprise}/apps/organizations/{org}/installations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an audit log streaming configuration for an enterprise | `POST /enterprises/{enterprise}/audit-log/streams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add enterprise teams to the Copilot subscription for an enterprise | `POST /enterprises/{enterprise}/copilot/billing/selected_enterprise_teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add users to the Copilot subscription for an enterprise | `POST /enterprises/{enterprise}/copilot/billing/selected_users` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Grant credential authorizations for enterprise organizations | `POST /enterprises/{enterprise}/credential-authorizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke all credential authorizations for an enterprise | `POST /enterprises/{enterprise}/credential-authorizations/revoke-all` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke a single credential type for an enterprise | `POST /enterprises/{enterprise}/credential-authorizations/revoke-credential-type` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke credential authorizations for a user in an enterprise | `POST /enterprises/{enterprise}/credential-authorizations/{username}/revoke` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke a single credential type for a user in an enterprise | `POST /enterprises/{enterprise}/credential-authorizations/{username}/revoke-credential-type` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an enterprise token inventory export | `POST /enterprises/{enterprise}/credentials/exports` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Sync innersource vulnerabilities for an enterprise | `POST /enterprises/{enterprise}/innersource-vulnerabilities/sync` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a hosted compute network configuration for an enterprise | `POST /enterprises/{enterprise}/network-configurations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an enterprise repository ruleset | `POST /enterprises/{enterprise}/rulesets` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Bulk create enterprise custom patterns | `POST /enterprises/{enterprise}/secret-scanning/custom-patterns` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a budget | `POST /enterprises/{enterprise}/settings/billing/budgets` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a new cost center | `POST /enterprises/{enterprise}/settings/billing/cost-centers` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add resources to a cost center | `POST /enterprises/{enterprise}/settings/billing/cost-centers/{cost_center_id}/resource` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create a usage report export | `POST /enterprises/{enterprise}/settings/billing/reports` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an enterprise team | `POST /enterprises/{enterprise}/teams` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Bulk add team members | `POST /enterprises/{enterprise}/teams/{enterprise-team}/memberships/add` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Bulk remove team members | `POST /enterprises/{enterprise}/teams/{enterprise-team}/memberships/remove` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add organization assignments | `POST /enterprises/{enterprise}/teams/{enterprise-team}/organizations/add` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Remove organization assignments | `POST /enterprises/{enterprise}/teams/{enterprise-team}/organizations/remove` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Enable or disable a security feature | `POST /enterprises/{enterprise}/{security_product}/{enablement}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Revoke all credential authorizations for an organization | `POST /orgs/{org}/credential-authorizations/revoke-all` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| Revoke a single credential type for an organization | `POST /orgs/{org}/credential-authorizations/revoke-credential-type` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| Revoke credential authorizations for a user in an organization | `POST /orgs/{org}/credential-authorizations/{username}/revoke` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| Revoke a single credential type for a user in an organization | `POST /orgs/{org}/credential-authorizations/{username}/revoke-credential-type` | Cloud | Left to GitHub | Credential authorizations are for organizations that sign in with SAML single sign-on, which needs GitHub Enterprise Cloud. |
| Create a custom repository role | `POST /orgs/{org}/custom-repository-roles` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Closing down - Create a custom role | `POST /orgs/{org}/custom_roles` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Create a custom organization role | `POST /orgs/{org}/organization-roles` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Create a dismissal request for a Dependabot alert for a repository | `POST /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Check license compliance for packages | `POST /repos/{owner}/{repo}/license-compliance/package-checks` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Provision a SCIM enterprise group | `POST /scim/v2/enterprises/{enterprise}/Groups` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Provision a SCIM enterprise user | `POST /scim/v2/enterprises/{enterprise}/Users` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Provision and invite a SCIM user | `POST /scim/v2/organizations/{org}/Users` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Set the GitHub Actions OIDC custom issuer policy for an enterprise | `PUT /enterprises/{enterprise}/actions/oidc/customization/issuer` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set GitHub Actions permissions for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set artifact and log retention settings for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/artifact-and-log-retention` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set fork PR contributor approval permissions for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/fork-pr-contributor-approval` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set private repo fork PR workflow settings for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/fork-pr-workflows-private-repos` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set selected organizations enabled for GitHub Actions in an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Enable a selected organization for GitHub Actions in an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/organizations/{org_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set allowed actions and reusable workflows for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/selected-actions` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set self-hosted runners permissions for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/self-hosted-runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set default workflow permissions for an enterprise | `PUT /enterprises/{enterprise}/actions/permissions/workflow` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update an enterprise Actions policy | `PUT /enterprises/{enterprise}/actions/policies/{policy_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set organization access for a self-hosted runner group in an enterprise | `PUT /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/organizations` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add organization access to a self-hosted runner group in an enterprise | `PUT /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/organizations/{org_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set self-hosted runners in a group for an enterprise | `PUT /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/runners` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add a self-hosted runner to a group for an enterprise | `PUT /enterprises/{enterprise}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set custom labels for a self-hosted runner for an enterprise | `PUT /enterprises/{enterprise}/actions/runners/{runner_id}/labels` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update an existing audit log stream configuration | `PUT /enterprises/{enterprise}/audit-log/streams/{stream_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set Copilot content exclusion rules for an enterprise | `PUT /enterprises/{enterprise}/copilot/content_exclusion` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the source organization for custom agents in an enterprise | `PUT /enterprises/{enterprise}/copilot/custom-agents/source` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Assign an enterprise role to a team | `PUT /enterprises/{enterprise}/enterprise-roles/teams/{team_slug}/{role_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Assign an enterprise role to an enterprise user | `PUT /enterprises/{enterprise}/enterprise-roles/users/{username}/{role_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the license compliance policy for an enterprise | `PUT /enterprises/{enterprise}/license-compliance/policies/{policy_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update an organization custom property definition on an enterprise | `PUT /enterprises/{enterprise}/org-properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Promote a custom property to an enterprise | `PUT /enterprises/{enterprise}/properties/schema/organizations/{org}/{custom_property_name}/promote` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create or update a custom property for an enterprise | `PUT /enterprises/{enterprise}/properties/schema/{custom_property_name}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Update an enterprise repository ruleset | `PUT /enterprises/{enterprise}/rulesets/{ruleset_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add team member | `PUT /enterprises/{enterprise}/teams/{enterprise-team}/memberships/{username}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add an organization assignment | `PUT /enterprises/{enterprise}/teams/{enterprise-team}/organizations/{org}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Add or update a Visual Studio subscription user match | `PUT /enterprises/{enterprise}/visual-studio-subscriptions/{visual_studio_subscription_id}` | Cloud | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Enable Git LFS for a repository | `PUT /repos/{owner}/{repo}/lfs` | Cloud | Left to GitHub | Needs GitHub Enterprise Cloud, which QUILL does not target. |
| Set SCIM information for a provisioned enterprise group | `PUT /scim/v2/enterprises/{enterprise}/Groups/{scim_group_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Set SCIM information for a provisioned enterprise user | `PUT /scim/v2/enterprises/{enterprise}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Update a provisioned organization membership | `PUT /scim/v2/organizations/{org}/Users/{scim_user_id}` | Cloud | Left to GitHub | SCIM provisioning is driven by an identity provider, not by a person. Organizations > org > Enterprise (Open on GitHub). |
| Delete a global webhook | `DELETE /admin/hooks/{hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a public key | `DELETE /admin/keys/{key_ids}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a pre-receive environment | `DELETE /admin/pre-receive-environments/{pre_receive_environment_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a pre-receive hook | `DELETE /admin/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a personal access token | `DELETE /admin/tokens/{token_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a user | `DELETE /admin/users/{username}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete an impersonation OAuth token | `DELETE /admin/users/{username}/authorizations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a grant | `DELETE /applications/grants/{grant_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete an authorization | `DELETE /authorizations/{authorization_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Remove the global announcement banner | `DELETE /enterprise/announcement` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Delete a SSH key | `DELETE /manage/v1/access/ssh` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Remove pre-receive hook enforcement for an organization | `DELETE /orgs/{org}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Remove pre-receive hook enforcement for a repository | `DELETE /repos/{owner}/{repo}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Demote a site administrator | `DELETE /users/{username}/site_admin` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Unsuspend a user | `DELETE /users/{username}/suspended` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List global webhooks | `GET /admin/hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a global webhook | `GET /admin/hooks/{hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List public keys | `GET /admin/keys` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List pre-receive environments | `GET /admin/pre-receive-environments` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a pre-receive environment | `GET /admin/pre-receive-environments/{pre_receive_environment_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the download status for a pre-receive environment | `GET /admin/pre-receive-environments/{pre_receive_environment_id}/downloads/latest` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List pre-receive hooks | `GET /admin/pre-receive-hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a pre-receive hook | `GET /admin/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List personal access tokens | `GET /admin/tokens` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List your grants | `GET /applications/grants` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a single grant | `GET /applications/grants/{grant_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List your authorizations | `GET /authorizations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a single authorization | `GET /authorizations/{authorization_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the global announcement banner | `GET /enterprise/announcement` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List Enterprise Live Migrations | `GET /enterprise/live-migrations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get an Enterprise Live Migration | `GET /enterprise/live-migrations/{migration_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get license information | `GET /enterprise/settings/license` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get all statistics | `GET /enterprise/stats/all` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get comment statistics | `GET /enterprise/stats/comments` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get gist statistics | `GET /enterprise/stats/gists` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get hooks statistics | `GET /enterprise/stats/hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get issue statistics | `GET /enterprise/stats/issues` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get milestone statistics | `GET /enterprise/stats/milestones` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get organization statistics | `GET /enterprise/stats/orgs` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get pages statistics | `GET /enterprise/stats/pages` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get pull request statistics | `GET /enterprise/stats/pulls` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get repository statistics | `GET /enterprise/stats/repos` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get security products statistics | `GET /enterprise/stats/security-products` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get users statistics | `GET /enterprise/stats/users` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get GitHub Actions cache usage policy for an enterprise | `GET /enterprises/{enterprise}/actions/cache/usage-policy` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the configured SSH keys | `GET /manage/v1/access/ssh` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the system requirement check results for configured cluster nodes | `GET /manage/v1/checks/system-requirements` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the status of services running on all cluster nodes | `GET /manage/v1/cluster/status` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the status of a ghe-config-apply run | `GET /manage/v1/config/apply` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List events from ghe-config-apply | `GET /manage/v1/config/apply/events` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the enterprise license information | `GET /manage/v1/config/license` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Check a license | `GET /manage/v1/config/license/check` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get GHES node metadata for all nodes | `GET /manage/v1/config/nodes` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the GHES settings | `GET /manage/v1/config/settings` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the status of maintenance mode | `GET /manage/v1/maintenance` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the status of services running on all replica nodes | `GET /manage/v1/replication/status` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the upgrade package download status | `GET /manage/v1/upgrade/download/status` | Server 3.22 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get the upgrade status | `GET /manage/v1/upgrade/status` | Server 3.22 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get all GHES release versions for all nodes | `GET /manage/v1/version` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List pre-receive hooks for an organization | `GET /orgs/{org}/pre-receive-hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a pre-receive hook for an organization | `GET /orgs/{org}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get GitHub Actions cache usage policy for a repository | `GET /repos/{owner}/{repo}/actions/cache/usage-policy` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List pre-receive hooks for a repository | `GET /repos/{owner}/{repo}/pre-receive-hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get a pre-receive hook for a repository | `GET /repos/{owner}/{repo}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| List repository cache replication status | `GET /repos/{owner}/{repo}/replicas/caches` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update a global webhook | `PATCH /admin/hooks/{hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update LDAP mapping for a team | `PATCH /admin/ldap/teams/{team_id}/mapping` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update LDAP mapping for a user | `PATCH /admin/ldap/users/{username}/mapping` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update an organization name | `PATCH /admin/organizations/{org}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update a pre-receive environment | `PATCH /admin/pre-receive-environments/{pre_receive_environment_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update a pre-receive hook | `PATCH /admin/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update the username for a user | `PATCH /admin/users/{username}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update an existing authorization | `PATCH /authorizations/{authorization_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set the global announcement banner | `PATCH /enterprise/announcement` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set GitHub Actions cache usage policy for an enterprise | `PATCH /enterprises/{enterprise}/actions/cache/usage-policy` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update pre-receive hook enforcement for an organization | `PATCH /orgs/{org}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set GitHub Actions cache usage policy for a repository | `PATCH /repos/{owner}/{repo}/actions/cache/usage-policy` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Update pre-receive hook enforcement for a repository | `PATCH /repos/{owner}/{repo}/pre-receive-hooks/{pre_receive_hook_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create a global webhook | `POST /admin/hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Ping a global webhook | `POST /admin/hooks/{hook_id}/pings` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Sync LDAP mapping for a team | `POST /admin/ldap/teams/{team_id}/sync` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Sync LDAP mapping for a user | `POST /admin/ldap/users/{username}/sync` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create an organization | `POST /admin/organizations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create a pre-receive environment | `POST /admin/pre-receive-environments` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Start a pre-receive environment download | `POST /admin/pre-receive-environments/{pre_receive_environment_id}/downloads` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create a pre-receive hook | `POST /admin/pre-receive-hooks` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create a user | `POST /admin/users` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create an impersonation OAuth token | `POST /admin/users/{username}/authorizations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create a new authorization | `POST /authorizations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Create an Enterprise Live Migration | `POST /enterprise/live-migrations` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Cancel an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/cancel` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Cutover an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/cutover` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Pause an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/pause` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Resume an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/resume` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Revert cutover for an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/revert-cutover` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Start an Enterprise Live Migration | `POST /enterprise/live-migrations/{migration_id}/start` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set a new SSH key | `POST /manage/v1/access/ssh` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Trigger a ghe-config-apply run | `POST /manage/v1/config/apply` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Initialize instance configuration with license and password | `POST /manage/v1/config/init` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set the status of maintenance mode | `POST /manage/v1/maintenance` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Apply an upgrade | `POST /manage/v1/upgrade/apply` | Server 3.22 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Download an upgrade package | `POST /manage/v1/upgrade/download` | Server 3.22 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get-or-create an authorization for a specific app | `PUT /authorizations/clients/{client_id}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Get-or-create an authorization for a specific app and fingerprint | `PUT /authorizations/clients/{client_id}/{fingerprint}` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Upload an enterprise license | `PUT /manage/v1/config/license` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Set settings | `PUT /manage/v1/config/settings` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Promote a user to be a site administrator | `PUT /users/{username}/site_admin` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |
| Suspend a user | `PUT /users/{username}/suspended` | Server 3.18 to 3.22 | Left to GitHub | Only on GitHub Enterprise Server, and the Workbench connects to GitHub.com accounts only (accounts.py refuses other hosts). Open on GitHub: the server's own pages. |

<!-- END GENERATED COVERAGE -->
