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
| Watched (`:watched`) | repositories | Watched: repositories whose activity GitHub tells you about. |
| Organizations (`:organizations`) | repositories | Organizations: the organizations you belong to. Enter on one opens its repositories. |
| Search (`:search`) | the top | Search: GitHub's searches. Choose one, type in the filter box with Ctrl+E, and press Enter. |
| Issues and Pull Requests (`:search_issues`) | search | Search Issues and Pull Requests: everything GitHub finds for the words and qualifiers in the filter box, such as is:open author:@me. Ctrl+N saves the search. |
| Code (`:search_code`) | search | Search Code: files whose text matches the filter box. Needs sign-in. |
| Commits (`:search_commits`) | search | Search Commits: commits whose message matches the filter box. |
| Repositories (`:search_repositories`) | search | Search Repositories: repositories whose name or description matches the filter box. |
| Saved Searches (`:saved_searches`) | search | Saved Searches: searches you kept, on this computer. Enter runs one; Delete removes it. |
| People (`:people`) | the top | People: who you follow, who follows you, and anybody you look up. |
| People I Follow (`:following`) | people | People I Follow: accounts you follow. Enter opens a person's node. |
| My Followers (`:followers`) | people | My Followers: accounts that follow you. |
| My Teams (`:my_teams`) | people | My Teams: every team you belong to, across your organizations. Alt+Enter opens a team's sheet. |
| Find a Person... (`:find_person`) | people | Find a Person: type a login with Ctrl+L, and the person gets a node of their own here. |
| Gists (`:gists`) | the top | Gists: small shared files and snippets. |
| My Gists (`:my_gists`) | gists | My Gists: gists you made. Enter edits one. |
| Projects (`:projects`) | the top | Projects: your Project boards. Each repository's own Projects are under it, Ctrl+Shift+7. |
| Watches (`:watches`) | the top | Watches: tell me when something happens. Coming in a later release. |
| Across Repositories (`:across`) | the top | Across Repositories: every kind of thing, by name, everywhere. Coming in a later release. |
| Help and Learning (`:help`) | the top | Help and Learning: the guide, the GitHub words, the keys, what changed, and tasks in plain words that take you to the place. |
| Do Something (`:help_tasks`) | help | Do Something: tasks in plain words. Enter reads one; Take Me There, on its context menu, goes to the place it is about. |
| The Guide (`:help_guide`) | help | The Guide: the GitHub Workbench Guide's chapters. Ctrl+F1 opens the guide at the chapter for where you are. |
| Words (`:help_words`) | help | Words: the GitHub glossary. Type a word to jump to it; the details say what it means and where you meet it. |
| Keys (`:help_keys`) | help | Keys: every key in the Workbench, grouped by what it does. |
| What Changed (`:help_changes`) | help | What Changed: what is new in the GitHub Workbench in this version. |
| Ask a Person (`:help_ask`) | help | Ask a Person: write to support@community-access.org. Nothing is sent until you send it from your own email. |
| owner/name (`repository:repository`) | repository | A repository: its issues, pull requests, actions, code, releases and settings, each a node below. Ctrl+Shift+1 to Ctrl+Shift+0 jump to them. |
| Overview (`repository:overview`) | repository, repository | Overview: the repository's README, description and community profile. |
| Issues (`repository:issues`) | repository, repository | Issues: this repository's open issues. Ctrl+N files a new one; Delete closes the selected one after asking. |
| Pull Requests (`repository:pulls`) | repository, repository | Pull Requests: this repository's open pull requests. Enter opens the review; Ctrl+Shift+D lists the changed files. |
| Issues and Pull Requests (`repository:issues_and_pulls`) | repository, repository | Issues and Pull Requests: both in one list, newest first, the way an inbox reads. |
| Discussions (`repository:discussions`) | repository, repository | Discussions: the repository's conversations that are not issues. |
| Actions (`repository:actions`) | repository, repository | Actions: the repository's workflow runs, workflows and caches. |
| Runs (`repository:runs`) | repository, actions | Runs: each time a workflow ran. Enter shows its jobs and logs; Ctrl+Shift+W says what failed; Ctrl+Shift+F5 re-runs the failed jobs. |
| Workflows (`repository:workflows`) | repository, actions | Workflows: the automations defined in the repository. |
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
| Deployments and Environments (`repository:deployments`) | repository, repository | Deployments and Environments: where the code was deployed. |
| GitHub Pages (`repository:pages`) | repository, repository | GitHub Pages: the website built from this repository. |
| Security (`repository:security`) | repository, repository | Security: alerts about vulnerable code and leaked secrets. |
| Alerts (`repository:alerts`) | repository, security | Alerts: open security alerts. Enter reads one. |
| Dismissed and Resolved Alerts (`repository:alerts_closed`) | repository, security | Dismissed and Resolved Alerts: alerts no longer open. |
| Settings (`repository:settings`) | repository, repository | Settings: names of secrets, branch protection and general settings. |
| Secret and Variable Names (`repository:secrets`) | repository, settings | Secret and Variable Names: the names only; GitHub never shows values. |
| Branch Protection (`repository:branch_protection`) | repository, settings | Branch Protection: who may change a branch and what a change needs first. Enter opens the setting. |
| General (`repository:general`) | repository, settings | General: the name, visibility and default branch. Enter opens one. |
| person (`person:person`) | person | A person: their repositories, activity, followers and who they follow. |
| Repositories (`person:person_repositories`) | person, person | Repositories: this person's public repositories. |
| Activity (`person:person_activity`) | person, person | Activity: what this person did lately on GitHub. |
| Followers (`person:person_followers`) | person, person | Followers: who follows this person. |
| Following (`person:person_following`) | person, person | Following: who this person follows. |
| organization (`organization:organization`) | organization | An organization: its repositories. |
| Repositories (`organization:organization_repositories`) | organization, organization | Repositories: the organization's repositories you can see. |
| Teams (`organization:organization_teams`) | organization, organization | Teams: the organization's teams, as GitHub nests them. Alt+Enter opens a team's sheet: its members and maintainers, repositories and roles, child teams and code review assignment. |

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
| Watches | Ctrl+7 | Watches: tell me when it happens. Coming later. |
| Saved Searches | Ctrl+8 | Searches you saved. |
| Start Here | Ctrl+9 | What this window is and how it works. |
| Across Repositories | Ctrl+0 | Every kind of thing, by name, everywhere. Coming later. |
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
| What Failed... | Ctrl+Shift+W | The failing steps of the selected run, and their log lines. |
| Re-run Failed Jobs | Ctrl+Shift+F5 | Run only what failed in the selected run again. |
| Mark Read | Ctrl+Q | Mark the selected notification read. |
| Mark All Read in View | Ctrl+Shift+Q | Mark every notification in this view read. Asks first when there are many. |
| Add to or Remove from Favorites | Ctrl+D | Keep the selected row under Repositories, Favorites. |

#### Repository

| Row | Key | What it does |
| --- | --- | --- |
| Compare Branches... | Ctrl+Shift+B | Commits ahead and behind between two branches, and the changed files. |
| Run Workflow on Branch... | Ctrl+Shift+R | Start a workflow that can be started by hand, on a branch. |
| Repository Actions... | Ctrl+Shift+G | Everything else for this repository: star, watch, fork, clone, Codespaces, settings and administration, as a list you can run from. |

#### Account

| Row | Key | What it does |
| --- | --- | --- |
| Manage GitHub Accounts... | Ctrl+Shift+K | Add, switch, sign in again or remove GitHub accounts. |
| GitHub API Rate Limit | Ctrl+Shift+L | How much of the GitHub API is left, and when it resets. |
| GitHub Permissions... | Ctrl+Shift+P | Every permission the Workbench can use, what it unlocks, whether you have it, and one step to add the missing ones. |
| Change History... | Ctrl+Shift+H | Every change the Workbench made on GitHub: before and after, and Undo where GitHub allows it. |
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
| Workbench Keys | Alt+Shift+F1 | Every key in this window, by family. |
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

- **issue**: Open, Comment..., Close or Reopen..., Labels..., Assignees..., Copy Link; More: Open on GitHub, Milestone..., React..., View Timeline..., Summarize Discussion, Start in Local Worktree..., Assign to Copilot..., Lock or Unlock Conversation..., Pin or Unpin Issue, Transfer Issue..., Set Issue Type..., Reorder Sub-issues..., Add to or Remove from Favorites; Properties...
- **pull_request**: Review..., File Differences..., Comment..., Merge..., Copy Link, Open on GitHub; More: Start in Local Worktree..., Open in Codespaces..., Commit Comments..., View Timeline..., Summarize Discussion, React..., Labels..., Assignees..., Add to or Remove from Favorites; Properties...
- **run**: Jobs and Logs, What Failed..., Re-run Failed Jobs Only, Re-run Workflow, Cancel Run..., View Artifacts...; More: Open on GitHub, Combined Check Status, Review Pending Deployments..., Approve Run from a Fork..., Delete Run..., Copy Link; Properties...
- **workflow**: Runs, Run Workflow on Branch..., Open on GitHub, Copy Link; Properties...
- **release**: Assets, Edit Release..., Draft Release Notes..., Upload Asset..., Copy Link, Open on GitHub; Properties...
- **release_asset**: Download, Copy Link, Delete Asset...; Properties...
- **branch**: Commits, Compare Branches..., Open in Codespaces..., Copy Name, Delete Branch...; Properties...
- **commit**: Open, Commit Comments..., Copy Link, Open on GitHub; Properties...
- **tag**: Open, Commit Comments..., Copy Link, Open on GitHub; Properties...
- **notification**: Open, Mark Read, Mark Done, Snooze for One Day, Unsubscribe from Thread, Open on GitHub, Unsnooze Locally; Properties...
- **repository**: Open, Star or Unstar, Watch or Unwatch, Clone..., Pin, Add to or Remove from Favorites; More: Open on GitHub, Open in Codespaces...; Properties...
- **person**: Open, Follow or Unfollow, Open on GitHub; Properties...
- **label**: Find Issues with Label, Edit Label..., Delete Label...; Properties...
- **gist**: Edit Gist..., Star or Unstar, Copy Link, Open on GitHub, Delete Gist...; Properties...
- **discussion**: Open Discussion Thread, Copy Link, Open on GitHub; Properties...
- **security_alert**: Open, Dismiss or Reopen Alert..., Open on GitHub; Properties...
- **cache**: Show Details, Delete Cache...; Properties...
- **saved_search**: Run, Remove Saved Search; Properties...
- **result**: Open, Copy Link, Open on GitHub; Properties...
- **file**: Open in Editor, Copy Link, Open on GitHub; Properties...
- **folder**: Open Folder, Open on GitHub; Properties...
- **milestone**: Find Issues in Milestone, Copy Link, Open on GitHub; Properties...
- **project**: Open on GitHub, Copy Link; Properties...
- **team**: Members and Access..., Copy Link, Open on GitHub; Properties...
- **organization**: Open, Open on GitHub; Properties...
- **favorite**: Open, Copy Link, Open on GitHub, Add to or Remove from Favorites; Properties...
- **admin_action**: Open; Properties...
- **help_topic**: Open, Take Me There; Properties...
- **node**: Refresh, Open on GitHub, Help for This View; Properties...

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
- **Artifact**: A file a run produced and kept, to download.
- **Assignee**: The person an issue or pull request is given to.
- **Branch**: A line of work: a name that follows the newest commit of one set of changes. Under Code, Branches.
- **Branch protection**: Rules that decide who may change a branch and what a change needs.
- **Cache**: Files Actions keeps between runs to make them faster. Under Actions, Caches.
- **Check**: A test or other run that reports passing or failing on a commit.
- **Codespace**: A computer in the cloud with the repository ready to work on. It can cost money.
- **Collaborator**: Somebody given access to one repository.
- **Commit**: A saved change, with a message saying why. Under Code, Commits.
- **Deployment**: Code sent to an environment, such as a website.
- **Discussion**: A conversation in a repository that is not an issue.
- **Draft**: A pull request that is not ready for review yet.
- **Environment**: A named place code is deployed to, with its own rules and secrets.
- **Favorite**: An item kept on this computer under Repositories, Favorites.
- **Fork**: Your own copy of somebody else's repository, from which you can propose changes back. Under People, Forks.
- **Gist**: A small shared file or snippet, with its own history.
- **Inbox**: The Workbench's one list of what needs you, made from notifications, review requests, assignments and mentions.
- **Issue**: A note about a bug, an idea or a task, with a conversation under it. Under a repository's Issues.
- **Job**: One part of a run, on one machine, made of steps.
- **Label**: A coloured tag on issues and pull requests, such as bug. Under Labels.
- **Mention**: Your login written with an at sign, such as @you, which notifies you.
- **Merge**: Bringing a pull request's changes into the branch it targets. Item, Merge, Ctrl+Shift+Enter.
- **Milestone**: A goal with a due date that issues and pull requests belong to.
- **Notification**: GitHub telling you something happened on a thread you are part of. Under Needs My Attention.
- **Organization**: An account many people share, which owns repositories and teams.
- **Pin**: A repository kept on this computer under Repositories, Pinned.
- **Project**: A board or table for planning issues and pull requests.
- **Pull request**: A proposed change: commits on one branch that somebody asks to merge into another, with a review. Under a repository's Pull Requests.
- **Rate limit**: How many requests GitHub allows an account each hour. Account, GitHub API Rate Limit, Ctrl+Shift+L.
- **Rebase**: Replaying commits on top of another branch, so the history reads as one straight line.
- **Release**: A published version, with notes and files to download. Under a repository's Releases.
- **Repository**: A project's folder on GitHub: its files, their history, and its issues and pull requests. Under Repositories in the tree.
- **Review**: Reading a pull request's changes and approving them, asking for changes, or commenting. Enter on a pull request.
- **Role**: What somebody may do: read, triage, write, maintain or admin.
- **Ruleset**: A newer, named set of branch and tag rules that can cover many branches.
- **Run**: One time a workflow ran, with its jobs, steps and logs. Under Actions, Runs.
- **Saved search**: A search kept on this computer, to run again. Under Saved Searches.
- **Secret**: A value, such as a password, that workflows use and GitHub never shows.
- **Security alert**: A warning that code, a dependency or a secret in it is at risk.
- **Squash**: Merging a pull request as one single commit, instead of all of its commits.
- **Star**: A bookmark on a repository, which also shows you like it.
- **Tag**: A name for one particular commit, usually a version number. Under Code, Tags.
- **Team**: A group of people in an organization, given access together.
- **Triage**: The role that may label, assign and close issues, but not push code.
- **Upstream**: The repository a fork was copied from. Under Code, Upstream, on a fork.
- **Variable**: A value workflows use that is not secret.
- **Watch**: Asking GitHub to tell you about a repository's activity.
- **Workflow**: One automation, defined in a file in the repository. Under Actions, Workflows.
- **Workflow dispatch**: Starting a workflow by hand, on a branch you choose.

<!-- END GENERATED -->
