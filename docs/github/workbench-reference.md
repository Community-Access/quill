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
| What Changed (`:help_changes`) | help | What Changed: what is new in the GitHub Workbench in this version. |
| Ask a Person (`:help_ask`) | help | Ask a Person: write to support@community-access.org. Nothing is sent until you send it from your own email. |
| owner/name (`repository:repository`) | repository | A repository: its issues, pull requests, actions, code, releases and settings, each a node below. Ctrl+Shift+1 to Ctrl+Shift+0 jump to them. |
| Overview (`repository:overview`) | repository, repository | Overview: the repository's README, description and community profile. |
| Issues (`repository:issues`) | repository, repository | Issues: this repository's open issues. Ctrl+N files a new one; Delete closes the selected one after asking. |
| Pull Requests (`repository:pulls`) | repository, repository | Pull Requests: this repository's open pull requests. Enter opens the review; Ctrl+Shift+D lists the changed files. |
| Issues and Pull Requests (`repository:issues_and_pulls`) | repository, repository | Issues and Pull Requests: both in one list, newest first, the way an inbox reads. |
| Discussions (`repository:discussions`) | repository, repository | Discussions: the repository's conversations that are not issues. |
| Merge Queue (`repository:merge_queue`) | repository, repository | Merge Queue: the default branch's merge queue in order, each pull request's state. |
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
| Templates (`organization:organization_templates`) | organization, organization | Templates: the defaults in the organization's .github repository, which every repository without its own uses. Enter builds or edits one. |

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

- **issue**: Open, Comment..., Close or Reopen..., Labels..., Assignees..., Copy Link; More: Open on GitHub, Milestone..., Projects..., Edit Title..., React..., View Timeline..., Read as Document..., Summarize Discussion, Start in Local Worktree..., Assign to Copilot..., Lock or Unlock Conversation..., Pin or Unpin Issue, Transfer Issue..., Check or Uncheck a Task..., Convert Tasks to Sub-issues..., Create Branch for This Issue..., Set Issue Type..., Reorder Sub-issues..., Add to or Remove from Favorites; Properties...
- **pull_request**: Review..., File Differences..., Comment..., Merge..., Why Can't I Merge?, Auto-Merge...; More: Add to or Remove from Merge Queue..., Open Patch in Editor, Revert Pull Request..., Resolve Conflicts in a Worktree..., Copy Link, Open on GitHub, Start in Local Worktree..., Open in Codespaces..., Commit Comments..., View Timeline..., Read as Document..., Summarize Discussion, React..., Labels..., Assignees..., Milestone..., Projects..., Edit Title..., Add to or Remove from Favorites; Properties...
- **run**: Jobs and Logs, What Failed..., Re-run Failed Jobs Only, Re-run Workflow, Cancel Run..., View Artifacts...; More: Open on GitHub, Combined Check Status, Review Pending Deployments..., Approve Run from a Fork..., Delete Run..., Copy Link; Properties...
- **workflow**: Runs, Run Workflow on Branch..., Turn Workflow On or Off..., Open on GitHub, Copy Link; Properties...
- **release**: Assets, Edit Release..., Draft Release Notes..., Upload Asset..., Compare With Previous, Compare With Default; More: Copy Link, Open on GitHub; Properties...
- **release_asset**: Download, Copy Link, Delete Asset...; Properties...
- **branch**: Commits, Compare With Default, Compare Branches..., Compare With Previous, Open in Codespaces..., Copy Name, Delete Branch...; Properties...
- **commit**: Open, Commit Comments..., Set Status..., Compare With Previous, Compare With Default, Copy Link, Open on GitHub; Properties...
- **tag**: Open, Delete Tag..., Commit Comments..., Compare With Previous, Compare With Default, Copy Link, Open on GitHub; Properties...
- **invitation**: Accept Invitation..., Decline Invitation..., Open on GitHub, Copy Link; Properties...
- **notification**: Open, Mark Read, Mark Done, Snooze for One Day, Unsubscribe from Thread, Open on GitHub, Unsnooze Locally; Properties...
- **repository**: Open, Star or Unstar, Watch or Unwatch, Clone..., Pin, Add to or Remove from Favorites; More: Open on GitHub, Open in Codespaces...; Properties...
- **person**: Open, Follow or Unfollow, Open on GitHub; Properties...
- **label**: Find Issues with Label, Edit Label..., Delete Label...; Properties...
- **gist**: Edit Gist..., Star or Unstar, Copy Link, Open on GitHub, Delete Gist...; Properties...
- **discussion**: Open Discussion Thread, Read as Document..., Copy Link, Open on GitHub; Properties...
- **security_alert**: Open, Dismiss or Reopen Alert..., Open on GitHub; Properties...
- **cache**: Show Details, Delete Cache...; Properties...
- **saved_search**: Run, Remove Saved Search; Properties...
- **result**: Open, Copy Link, Open on GitHub; Properties...
- **file**: Open in Editor, Copy Link, Open on GitHub; Properties...
- **folder**: Open Folder, Open on GitHub; Properties...
- **milestone**: Find Issues in Milestone, Copy Link, Open on GitHub; Properties...
- **template**: Open Template..., Convert Form or Template..., Copy to Repositories..., Copy Link, Open on GitHub; Properties...
- **project**: Open on GitHub, Copy Link; Properties...
- **team**: Members and Access..., Copy Link, Open on GitHub; Properties...
- **organization**: Open, Open on GitHub; Properties...
- **favorite**: Open, Copy Link, Open on GitHub, Add to or Remove from Favorites; Properties...
- **admin_action**: Open; Properties...
- **watch**: Edit Watch..., Pause or Resume Watch, Check Watches Now, Remove Watch, Open on GitHub; Properties...
- **help_topic**: Open, Take Me There; Properties...
- **node**: Refresh, Open on GitHub, Help for This View; Properties...
- **across_item**: Open in Its Repository, Next Repository, Previous Repository, View More from This Repository, Read Issue Type and Fields, Every Release or Latest Only; More: Open on GitHub, Copy Link; Properties...
- **across_status**: Open, Next Repository, Previous Repository, View More from This Repository, Open on GitHub; Properties...
- **repository_set**: Use This Set, Edit Repositories..., Set Filter..., New Set..., Rename Set..., Delete Set...; Properties...
- **by_name**: Variants and Missing From, Make Them the Same..., Add to Missing..., Find Uses, Rename Everywhere..., Merge Into...; More: Close Everywhere..., Move Open Work To..., Promote to Organization..., Delete Everywhere...; Properties...
- **fleet**: Open Repository, Open on GitHub, Copy Link; Properties...

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
- **Fleet**: Every repository in a Repository Set on one line each: its revision, checks, pull requests, latest release and alerts. Under Across Repositories, Fleet.
- **Fork**: Your own copy of somebody else's repository, from which you can propose changes back. Under People, Forks.
- **Gist**: A small shared file or snippet, with its own history.
- **Inbox**: The Workbench's one list of what needs you, made from notifications, review requests, assignments and mentions.
- **Invitation**: Someone with admin access asking you to join their repository, with the access they chose. It waits under Needs My Attention > Invitations and expires after a week.
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
- **Repository Set**: A named list of repositories kept on this computer, made by hand or by a filter such as org:name. Across Repositories reads one kind of thing from all of them. Under Across Repositories, Repository Sets.
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
- **Template**: A file that shapes new issues, pull requests or discussions, such as a bug report form. Under Templates.
- **Triage**: The role that may label, assign and close issues, but not push code.
- **Upstream**: The repository a fork was copied from. Under Code, Upstream, on a fork.
- **Variable**: A value workflows use that is not secret.
- **Watch**: Asking GitHub to tell you about a repository's activity.
- **Watch rule**: A rule kept on this computer that tells you when something happens on GitHub: a run finishes, a review arrives, a release or a comment. Under Watches. Not the same as watching a repository on GitHub, which sends notifications.
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

In all: 344 yes, 1119 planned, 15 not needed and 526 left to GitHub.

**Wikis** have no API: GitHub serves each one as a Git repository (`owner/name.wiki.git`). Reading and editing them is planned under Repository > Wiki.

### REST operations, by category

#### Actions

208 operations: 43 yes, 158 planned, 7 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get GitHub Actions cache retention limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/retention-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set GitHub Actions cache retention limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/retention-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions cache storage limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/storage-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set GitHub Actions cache storage limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/storage-limit` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List OIDC custom property inclusions for an enterprise | `GET /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Create an OIDC custom property inclusion for an enterprise | `POST /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Delete an OIDC custom property inclusion for an enterprise | `DELETE /enterprises/{enterprise}/actions/oidc/customization/properties/repo/{custom_property_name}` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Get GitHub Actions cache retention limit for an organization | `GET /organizations/{org}/actions/cache/retention-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Set GitHub Actions cache retention limit for an organization | `PUT /organizations/{org}/actions/cache/retention-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Get GitHub Actions cache storage limit for an organization | `GET /organizations/{org}/actions/cache/storage-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Set GitHub Actions cache storage limit for an organization | `PUT /organizations/{org}/actions/cache/storage-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Get GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage` | Planned | Repository > Actions > Caches; Cache sheet. |
| List repositories with GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage-by-repository` | Planned | Repository > Actions > Caches; Cache sheet. |
| List GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners` | Planned | Organization sheet > Actions > Hosted runners. |
| Create a GitHub-hosted runner for an organization | `POST /orgs/{org}/actions/hosted-runners` | Planned | Organization sheet > Actions > Hosted runners. |
| List custom images for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom` | Planned | Organization sheet > Actions > Hosted runners. |
| Delete a custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | Planned | Organization sheet > Actions > Hosted runners. |
| Get a custom image definition for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | Planned | Organization sheet > Actions > Hosted runners. |
| List image versions of a custom image for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions` | Planned | Organization sheet > Actions > Hosted runners. |
| Delete an image version of custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Planned | Organization sheet > Actions > Hosted runners. |
| Get an image version of a custom image for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | Planned | Organization sheet > Actions > Hosted runners. |
| Get GitHub-owned images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/github-owned` | Planned | Organization sheet > Actions > Hosted runners. |
| Get partner images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/partner` | Planned | Organization sheet > Actions > Hosted runners. |
| Get limits on GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners/limits` | Planned | Organization sheet > Actions > Hosted runners. |
| Get GitHub-hosted runners machine specs for an organization | `GET /orgs/{org}/actions/hosted-runners/machine-sizes` | Planned | Organization sheet > Actions > Hosted runners. |
| Get platforms for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/platforms` | Planned | Organization sheet > Actions > Hosted runners. |
| Delete a GitHub-hosted runner for an organization | `DELETE /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Planned | Organization sheet > Actions > Hosted runners. |
| Get a GitHub-hosted runner for an organization | `GET /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Planned | Organization sheet > Actions > Hosted runners. |
| Update a GitHub-hosted runner for an organization | `PATCH /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | Planned | Organization sheet > Actions > Hosted runners. |
| List OIDC custom property inclusions for an organization | `GET /orgs/{org}/actions/oidc/customization/properties/repo` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Create an OIDC custom property inclusion for an organization | `POST /orgs/{org}/actions/oidc/customization/properties/repo` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Delete an OIDC custom property inclusion for an organization | `DELETE /orgs/{org}/actions/oidc/customization/properties/repo/{custom_property_name}` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Get the customization template for an OIDC subject claim for an organization | `GET /orgs/{org}/actions/oidc/customization/sub` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Set the customization template for an OIDC subject claim for an organization | `PUT /orgs/{org}/actions/oidc/customization/sub` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Get GitHub Actions permissions for an organization | `GET /orgs/{org}/actions/permissions` | Yes | Properties (Alt+Enter) on Organization |
| Set GitHub Actions permissions for an organization | `PUT /orgs/{org}/actions/permissions` | Yes | Properties (Alt+Enter) on Organization: Repositories that may use Actions |
| Get artifact and log retention settings for an organization | `GET /orgs/{org}/actions/permissions/artifact-and-log-retention` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set artifact and log retention settings for an organization | `PUT /orgs/{org}/actions/permissions/artifact-and-log-retention` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get fork PR contributor approval permissions for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set fork PR contributor approval permissions for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get private repo fork PR workflow settings for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set private repo fork PR workflow settings for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| List selected repositories enabled for GitHub Actions in an organization | `GET /orgs/{org}/actions/permissions/repositories` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set selected repositories enabled for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Disable a selected repository for GitHub Actions in an organization | `DELETE /orgs/{org}/actions/permissions/repositories/{repository_id}` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Enable a selected repository for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories/{repository_id}` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get allowed actions and reusable workflows for an organization | `GET /orgs/{org}/actions/permissions/selected-actions` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set allowed actions and reusable workflows for an organization | `PUT /orgs/{org}/actions/permissions/selected-actions` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get self-hosted runners settings for an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set self-hosted runners settings for an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| List repositories allowed to use self-hosted runners in an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Remove a repository from the list of repositories allowed to use self-hosted runners in an organization | `DELETE /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Add a repository to the list of repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get default workflow permissions for an organization | `GET /orgs/{org}/actions/permissions/workflow` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set default workflow permissions for an organization | `PUT /orgs/{org}/actions/permissions/workflow` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| List organization Actions policies | `GET /orgs/{org}/actions/policies` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Create an organization Actions policy | `POST /orgs/{org}/actions/policies` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Delete an organization Actions policy | `DELETE /orgs/{org}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Get an organization Actions policy | `GET /orgs/{org}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Update an organization Actions policy | `PUT /orgs/{org}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| List self-hosted runner groups for an organization | `GET /orgs/{org}/actions/runner-groups` | Planned | Runner group sheet. |
| Create a self-hosted runner group for an organization | `POST /orgs/{org}/actions/runner-groups` | Planned | Runner group sheet. |
| Delete a self-hosted runner group from an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}` | Planned | Runner group sheet. |
| Get a self-hosted runner group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}` | Planned | Runner group sheet. |
| Update a self-hosted runner group for an organization | `PATCH /orgs/{org}/actions/runner-groups/{runner_group_id}` | Planned | Runner group sheet. |
| List GitHub-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/hosted-runners` | Planned | Runner group sheet. |
| List repository access to a self-hosted runner group in an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | Planned | Runner group sheet. |
| Set repository access for a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | Planned | Runner group sheet. |
| Remove repository access to a self-hosted runner group in an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Planned | Runner group sheet. |
| Add repository access to a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Planned | Runner group sheet. |
| List self-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | Planned | Runner group sheet. |
| Set self-hosted runners in a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | Planned | Runner group sheet. |
| Remove a self-hosted runner from a group for an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Planned | Runner group sheet. |
| Add a self-hosted runner to a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | Planned | Runner group sheet. |
| List self-hosted runners for an organization | `GET /orgs/{org}/actions/runners` | Planned | Runner sheet. |
| Get runner version end-of-life schedule for an organization | `GET /orgs/{org}/actions/runners/deprecations/{version}` | Planned | Runner sheet. |
| List runner applications for an organization | `GET /orgs/{org}/actions/runners/downloads` | Planned | Runner sheet. |
| Create configuration for a just-in-time runner for an organization | `POST /orgs/{org}/actions/runners/generate-jitconfig` | Planned | Runner sheet. |
| Create a registration token for an organization | `POST /orgs/{org}/actions/runners/registration-token` | Planned | Runner sheet. |
| Create a remove token for an organization | `POST /orgs/{org}/actions/runners/remove-token` | Planned | Runner sheet. |
| Delete a self-hosted runner from an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}` | Planned | Runner sheet. |
| Get a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}` | Planned | Runner sheet. |
| Remove all custom labels from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels` | Planned | Runner sheet. |
| List labels for a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}/labels` | Planned | Runner sheet. |
| Add custom labels to a self-hosted runner for an organization | `POST /orgs/{org}/actions/runners/{runner_id}/labels` | Planned | Runner sheet. |
| Set custom labels for a self-hosted runner for an organization | `PUT /orgs/{org}/actions/runners/{runner_id}/labels` | Planned | Runner sheet. |
| Remove a custom label from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels/{name}` | Planned | Runner sheet. |
| List organization secrets | `GET /orgs/{org}/actions/secrets` | Yes | Properties (Alt+Enter) on Organization |
| Get an organization public key | `GET /orgs/{org}/actions/secrets/public-key` | Planned | Secret and variable sheets (write-only values). |
| Delete an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| Get an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| Create or update an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| List selected repositories for an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}/repositories` | Planned | Secret and variable sheets (write-only values). |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories` | Planned | Secret and variable sheets (write-only values). |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | Planned | Secret and variable sheets (write-only values). |
| Add selected repository to an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | Planned | Secret and variable sheets (write-only values). |
| List organization variables | `GET /orgs/{org}/actions/variables` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization variable | `POST /orgs/{org}/actions/variables` | Planned | Secret and variable sheets. |
| Delete an organization variable | `DELETE /orgs/{org}/actions/variables/{name}` | Planned | Secret and variable sheets. |
| Get an organization variable | `GET /orgs/{org}/actions/variables/{name}` | Planned | Secret and variable sheets. |
| Update an organization variable | `PATCH /orgs/{org}/actions/variables/{name}` | Planned | Secret and variable sheets. |
| List selected repositories for an organization variable | `GET /orgs/{org}/actions/variables/{name}/repositories` | Planned | Secret and variable sheets. |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories` | Planned | Secret and variable sheets. |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | Planned | Secret and variable sheets. |
| Add selected repository to an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | Planned | Secret and variable sheets. |
| List artifacts for a repository | `GET /repos/{owner}/{repo}/actions/artifacts` | Planned | Run > Artifacts; Artifact sheet. |
| Delete an artifact | `DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | Planned | Run > Artifacts; Artifact sheet. |
| Get an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | Yes | Properties (Alt+Enter) on Artifact |
| Download an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/{archive_format}` | Planned | Run > Artifacts; Artifact sheet. |
| Get GitHub Actions cache retention limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/retention-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Set GitHub Actions cache retention limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/retention-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Get GitHub Actions cache storage limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/storage-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Set GitHub Actions cache storage limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/storage-limit` | Planned | Repository > Actions > Caches; Cache sheet. |
| Get GitHub Actions cache usage for a repository | `GET /repos/{owner}/{repo}/actions/cache/usage` | Planned | Repository > Actions > Caches; Cache sheet. |
| Delete GitHub Actions caches for a repository (using a cache key) | `DELETE /repos/{owner}/{repo}/actions/caches` | Planned | Repository > Actions > Caches; Cache sheet. |
| List GitHub Actions caches for a repository | `GET /repos/{owner}/{repo}/actions/caches` | Yes | Navigator: Repository > owner/name > Actions > Caches |
| Delete a GitHub Actions cache for a repository (using a cache ID) | `DELETE /repos/{owner}/{repo}/actions/caches/{cache_id}` | Yes | context menu > Delete Cache... |
| List concurrency groups for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Get a concurrency group for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups/{concurrency_group_name}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Get a job for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}` | Yes | Properties (Alt+Enter) on Job |
| Download job logs for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` | Yes | Item > What Failed... (Ctrl+Shift+W) |
| Re-run a job from a workflow run | `POST /repos/{owner}/{repo}/actions/jobs/{job_id}/rerun` | Planned | Run sheet. |
| Download step logs for a workflow run job | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/steps/{step_number}/logs` | Planned | Job sheet. |
| Get the customization template for an OIDC subject claim for a repository | `GET /repos/{owner}/{repo}/actions/oidc/customization/sub` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| Set the customization template for an OIDC subject claim for a repository | `PUT /repos/{owner}/{repo}/actions/oidc/customization/sub` | Planned | Repository and Organization sheets > Actions > OpenID Connect. |
| List repository organization secrets | `GET /repos/{owner}/{repo}/actions/organization-secrets` | Planned | Secret and variable sheets (write-only values). |
| List repository organization variables | `GET /repos/{owner}/{repo}/actions/organization-variables` | Planned | Secret and variable sheets. |
| Get GitHub Actions permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions` | Yes | Properties (Alt+Enter) on Repository |
| Set GitHub Actions permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions` | Yes | Properties (Alt+Enter) on Repository: Actions enabled |
| Get the level of access for workflows outside of the repository | `GET /repos/{owner}/{repo}/actions/permissions/access` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set the level of access for workflows outside of the repository | `PUT /repos/{owner}/{repo}/actions/permissions/access` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get artifact and log retention settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set artifact and log retention settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get fork PR contributor approval permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set fork PR contributor approval permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get private repo fork PR workflow settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set private repo fork PR workflow settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get allowed actions and reusable workflows for a repository | `GET /repos/{owner}/{repo}/actions/permissions/selected-actions` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Set allowed actions and reusable workflows for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/selected-actions` | Planned | Repository and Organization sheets > Actions (section 18.3). |
| Get default workflow permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Repository |
| Set default workflow permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/workflow` | Yes | Properties (Alt+Enter) on Repository: Allow Actions to create and approve pull requests |
| List repository Actions policies | `GET /repos/{owner}/{repo}/actions/policies` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Create a repository Actions policy | `POST /repos/{owner}/{repo}/actions/policies` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Delete a repository Actions policy | `DELETE /repos/{owner}/{repo}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Get a repository Actions policy | `GET /repos/{owner}/{repo}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Update a repository Actions policy | `PUT /repos/{owner}/{repo}/actions/policies/{policy_id}` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| List self-hosted runners for a repository | `GET /repos/{owner}/{repo}/actions/runners` | Yes | Navigator: Repository > owner/name > Actions > Runners |
| Get runner version end-of-life schedule for a repository | `GET /repos/{owner}/{repo}/actions/runners/deprecations/{version}` | Planned | Repository > Actions > Runners |
| List runner applications for a repository | `GET /repos/{owner}/{repo}/actions/runners/downloads` | Planned | Repository > Actions > Runners |
| Create configuration for a just-in-time runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig` | Planned | Repository > Actions > Runners |
| Create a registration token for a repository | `POST /repos/{owner}/{repo}/actions/runners/registration-token` | Planned | Repository > Actions > Runners |
| Create a remove token for a repository | `POST /repos/{owner}/{repo}/actions/runners/remove-token` | Planned | Repository > Actions > Runners |
| Delete a self-hosted runner from a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}` | Planned | Repository > Actions > Runners |
| Get a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}` | Yes | Properties (Alt+Enter) on Runner |
| Remove all custom labels from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Planned | Repository > Actions > Runners |
| List labels for a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Yes | Item > Properties... (Alt+Enter) |
| Add custom labels to a self-hosted runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Planned | Repository > Actions > Runners |
| Set custom labels for a self-hosted runner for a repository | `PUT /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | Yes | Properties (Alt+Enter) on Runner: Custom labels |
| Remove a custom label from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels/{name}` | Planned | Repository > Actions > Runners |
| List workflow runs for a repository | `GET /repos/{owner}/{repo}/actions/runs` | Yes | Navigator: Repository > owner/name > Actions > Runs |
| Delete a workflow run | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}` | Yes | context menu > Delete Run... |
| Get a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}` | Yes | Properties (Alt+Enter) on Workflow Run |
| Get the review history for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/approvals` | Planned | Run sheet. |
| Approve a workflow run for a fork pull request | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve` | Yes | context menu > Approve Run from a Fork... |
| List workflow run artifacts | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts` | Yes | context menu > View Artifacts... |
| Get a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}` | Planned | Run sheet. |
| List jobs for a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs` | Planned | Job sheet. |
| Download workflow run attempt logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/logs` | Planned | Run sheet. |
| Cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/cancel` | Yes | context menu > Cancel Run... (Ctrl+Cancel) |
| List concurrency groups for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/concurrency_groups` | Planned | Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. |
| Review custom deployment protection rules for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule` | Planned | Run sheet. |
| Force cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/force-cancel` | Planned | Run sheet. |
| List jobs for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` | Yes | Properties (Alt+Enter) on Workflow Run |
| Delete workflow run logs | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | Planned | Run sheet. |
| Download workflow run logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | Planned | Run sheet. |
| Get pending deployments for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | Yes | context menu > Review Pending Deployments... |
| Review pending deployments for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | Yes | context menu > Review Pending Deployments... |
| Re-run a workflow | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun` | Yes | context menu > Re-run Workflow |
| Re-run failed jobs from a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs` | Yes | Item > Re-run Failed Jobs (Ctrl+Shift+F5) |
| Get workflow run usage | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/timing` | Yes | Properties (Alt+Enter) on Workflow Run |
| List repository secrets | `GET /repos/{owner}/{repo}/actions/secrets` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Get a repository public key | `GET /repos/{owner}/{repo}/actions/secrets/public-key` | Yes | Properties (Alt+Enter) on Secret |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| Get a repository secret | `GET /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Yes | Properties (Alt+Enter) on Secret |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/actions/secrets/{secret_name}` | Yes | Properties (Alt+Enter) on Secret: New value |
| List repository variables | `GET /repos/{owner}/{repo}/actions/variables` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Create a repository variable | `POST /repos/{owner}/{repo}/actions/variables` | Planned | Secret and variable sheets. |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/actions/variables/{name}` | Planned | Secret and variable sheets. |
| Get a repository variable | `GET /repos/{owner}/{repo}/actions/variables/{name}` | Yes | Properties (Alt+Enter) on Variable |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/actions/variables/{name}` | Yes | Properties (Alt+Enter) on Variable: Value |
| List repository workflows | `GET /repos/{owner}/{repo}/actions/workflows` | Yes | Navigator: Repository > owner/name > Actions > Workflows |
| Get a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}` | Yes | Properties (Alt+Enter) on Workflow |
| Disable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/disable` | Yes | context menu > Turn Workflow On or Off... |
| Create a workflow dispatch event | `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | Yes | Repository > Run Workflow on Branch... (Ctrl+Shift+R) |
| Enable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable` | Yes | context menu > Turn Workflow On or Off... |
| List workflow runs for a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs` | Planned | Run sheet. |
| Get workflow usage | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing` | Planned | Workflow sheet. |
| List environment secrets | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets` | Yes | Properties (Alt+Enter) on Environment |
| Get an environment public key | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/public-key` | Planned | Secret and variable sheets (write-only values). |
| Delete an environment secret | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| Get an environment secret | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| Create or update an environment secret | `PUT /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | Planned | Secret and variable sheets (write-only values). |
| List environment variables | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables` | Yes | Properties (Alt+Enter) on Environment |
| Create an environment variable | `POST /repos/{owner}/{repo}/environments/{environment_name}/variables` | Planned | Secret and variable sheets. |
| Delete an environment variable | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Planned | Secret and variable sheets. |
| Get an environment variable | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Planned | Secret and variable sheets. |
| Update an environment variable | `PATCH /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | Planned | Secret and variable sheets. |

#### Activity

34 operations: 16 yes, 18 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List public events | `GET /events` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| Get feeds | `GET /feeds` | Planned | Needs My Attention > My Activity Feed. |
| List public events for a network of repositories | `GET /networks/{owner}/{repo}/events` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List notifications for the authenticated user | `GET /notifications` | Yes | Navigator: Needs My Attention > Notifications |
| Mark notifications as read | `PUT /notifications` | Yes | Item > Mark All Read in View (Ctrl+Shift+Q) |
| Mark a thread as done | `DELETE /notifications/threads/{thread_id}` | Yes | context menu > Mark Done |
| Get a thread | `GET /notifications/threads/{thread_id}` | Yes | Properties (Alt+Enter) on Notification |
| Mark a thread as read | `PATCH /notifications/threads/{thread_id}` | Yes | Item > Mark Read (Ctrl+Q) |
| Delete a thread subscription | `DELETE /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| Get a thread subscription for the authenticated user | `GET /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| Set a thread subscription | `PUT /notifications/threads/{thread_id}/subscription` | Yes | context menu > Unsubscribe from Thread |
| List public organization events | `GET /orgs/{org}/events` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List repository events | `GET /repos/{owner}/{repo}/events` | Yes | Navigator: Repository > owner/name > Activity |
| List repository notifications for the authenticated user | `GET /repos/{owner}/{repo}/notifications` | Planned | Needs My Attention > Notifications; Notification sheet. |
| Mark repository notifications as read | `PUT /repos/{owner}/{repo}/notifications` | Planned | Needs My Attention > Notifications; Notification sheet. |
| List stargazers | `GET /repos/{owner}/{repo}/stargazers` | Planned | You page: Star (section 16.7). |
| Get stargazer count | `GET /repos/{owner}/{repo}/stargazers/count` | Planned | You page: Star (section 16.7). |
| Get repository star history | `GET /repos/{owner}/{repo}/stargazers/history` | Planned | You page: Star (section 16.7). |
| List watchers | `GET /repos/{owner}/{repo}/subscribers` | Planned | You page: Watch level (section 16.7). |
| Delete a repository subscription | `DELETE /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| Get a repository subscription | `GET /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| Set a repository subscription | `PUT /repos/{owner}/{repo}/subscription` | Yes | context menu > Watch or Unwatch |
| List repositories starred by the authenticated user | `GET /user/starred` | Planned | You page: Star (section 16.7). |
| Unstar a repository for the authenticated user | `DELETE /user/starred/{owner}/{repo}` | Yes | Properties (Alt+Enter) on Repository: Starred |
| Check if a repository is starred by the authenticated user | `GET /user/starred/{owner}/{repo}` | Yes | Item > Properties... (Alt+Enter) |
| Star a repository for the authenticated user | `PUT /user/starred/{owner}/{repo}` | Yes | Properties (Alt+Enter) on Repository: Starred |
| List repositories watched by the authenticated user | `GET /user/subscriptions` | Planned | You page: Watch level (section 16.7). |
| List events for the authenticated user | `GET /users/{username}/events` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List organization events for the authenticated user | `GET /users/{username}/events/orgs/{org}` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List public events for a user | `GET /users/{username}/events/public` | Yes | Navigator: Person > person > Activity |
| List events received by the authenticated user | `GET /users/{username}/received_events` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List public events received by a user | `GET /users/{username}/received_events/public` | Planned | Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity. |
| List repositories starred by a user | `GET /users/{username}/starred` | Planned | You page: Star (section 16.7). |
| List repositories watched by a user | `GET /users/{username}/subscriptions` | Planned | You page: Watch level (section 16.7). |

#### Agent automations

12 operations: 12 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List automations for user | `GET /agents/automations` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| List automations for a repository | `GET /agents/repos/{owner}/{repo}/automations` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Create an automation for a repository | `POST /agents/repos/{owner}/{repo}/automations` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| List available automation tools for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-tools` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| List available automation triggers for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-triggers` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Delete an automation | `DELETE /agents/repos/{owner}/{repo}/automations/{automation_id}` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Get an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Update an automation | `PATCH /agents/repos/{owner}/{repo}/automations/{automation_id}` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| List revisions for an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Get an automation revision | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions/{revision_id}` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| List tasks for an automation in a repository | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |
| Run an automation | `POST /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | Planned | Item > Copilot; Repository > Copilot (section 22.1). |

#### Agent tasks

5 operations: 5 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List tasks for repository | `GET /agents/repos/{owner}/{repo}/tasks` | Planned | Item > Copilot > Agent Sessions (section 22.1). |
| Start a task | `POST /agents/repos/{owner}/{repo}/tasks` | Planned | Item > Copilot > Agent Sessions (section 22.1). |
| Get a task by repo | `GET /agents/repos/{owner}/{repo}/tasks/{task_id}` | Planned | Item > Copilot > Agent Sessions (section 22.1). |
| List tasks | `GET /agents/tasks` | Planned | Item > Copilot > Agent Sessions (section 22.1). |
| Get a task by ID | `GET /agents/tasks/{task_id}` | Planned | Item > Copilot > Agent Sessions (section 22.1). |

#### Agents

30 operations: 30 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization secrets | `GET /orgs/{org}/agents/secrets` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get an organization public key | `GET /orgs/{org}/agents/secrets/public-key` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Delete an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Create or update an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List selected repositories for an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}/repositories` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Add selected repository to an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List organization variables | `GET /orgs/{org}/agents/variables` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Create an organization variable | `POST /orgs/{org}/agents/variables` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Delete an organization variable | `DELETE /orgs/{org}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get an organization variable | `GET /orgs/{org}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Update an organization variable | `PATCH /orgs/{org}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List selected repositories for an organization variable | `GET /orgs/{org}/agents/variables/{name}/repositories` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Add selected repository to an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List repository organization secrets | `GET /repos/{owner}/{repo}/agents/organization-secrets` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List repository organization variables | `GET /repos/{owner}/{repo}/agents/organization-variables` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List repository secrets | `GET /repos/{owner}/{repo}/agents/secrets` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get a repository public key | `GET /repos/{owner}/{repo}/agents/secrets/public-key` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get a repository secret | `GET /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/agents/secrets/{secret_name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| List repository variables | `GET /repos/{owner}/{repo}/agents/variables` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Create a repository variable | `POST /repos/{owner}/{repo}/agents/variables` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Get a repository variable | `GET /repos/{owner}/{repo}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/agents/variables/{name}` | Planned | Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). |

#### Apps

37 operations: 8 planned, 29 left to github.

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
| Get an app | `GET /apps/{app_slug}` | Planned | Organization and Repository sheets > Apps |
| List repositories accessible to the app installation | `GET /installation/repositories` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Revoke an installation access token | `DELETE /installation/token` | Left to GitHub | GitHub App installation internals: calls an app makes with its own JWT or installation token. |
| Get a subscription plan for an account | `GET /marketplace_listing/accounts/{account_id}` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List plans | `GET /marketplace_listing/plans` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List accounts for a plan | `GET /marketplace_listing/plans/{plan_id}/accounts` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get a subscription plan for an account (stubbed) | `GET /marketplace_listing/stubbed/accounts/{account_id}` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List plans (stubbed) | `GET /marketplace_listing/stubbed/plans` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List accounts for a plan (stubbed) | `GET /marketplace_listing/stubbed/plans/{plan_id}/accounts` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get an organization installation for the authenticated app | `GET /orgs/{org}/installation` | Planned | Organization and Repository sheets > Apps |
| Get a repository installation for the authenticated app | `GET /repos/{owner}/{repo}/installation` | Planned | Organization and Repository sheets > Apps |
| List app installations accessible to the user access token | `GET /user/installations` | Planned | Organization and Repository sheets > Apps |
| List repositories accessible to the user access token | `GET /user/installations/{installation_id}/repositories` | Planned | Organization and Repository sheets > Apps |
| Remove a repository from an app installation | `DELETE /user/installations/{installation_id}/repositories/{repository_id}` | Planned | Organization and Repository sheets > Apps |
| Add a repository to an app installation | `PUT /user/installations/{installation_id}/repositories/{repository_id}` | Planned | Organization and Repository sheets > Apps |
| List subscriptions for the authenticated user | `GET /user/marketplace_purchases` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| List subscriptions for the authenticated user (stubbed) | `GET /user/marketplace_purchases/stubbed` | Left to GitHub | Marketplace listings are read by app publishers with app credentials; purchases have no API. Account > Billing and Usage (Open on GitHub: Marketplace). |
| Get a user installation for the authenticated app | `GET /users/{username}/installation` | Planned | Organization and Repository sheets > Apps |

#### Billing

13 operations: 1 yes, 12 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get billing AI credit usage report for an organization | `GET /organizations/{org}/settings/billing/ai_credit/usage` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get all budgets for an organization | `GET /organizations/{org}/settings/billing/budgets` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Create a budget for an organization | `POST /organizations/{org}/settings/billing/budgets` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Delete a budget for an organization | `DELETE /organizations/{org}/settings/billing/budgets/{budget_id}` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get a budget by ID for an organization | `GET /organizations/{org}/settings/billing/budgets/{budget_id}` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Update a budget for an organization | `PATCH /organizations/{org}/settings/billing/budgets/{budget_id}` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing premium request usage report for an organization | `GET /organizations/{org}/settings/billing/premium_request/usage` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing usage report for an organization | `GET /organizations/{org}/settings/billing/usage` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing usage summary for an organization | `GET /organizations/{org}/settings/billing/usage/summary` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing AI credit usage report for a user | `GET /users/{username}/settings/billing/ai_credit/usage` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing premium request usage report for a user | `GET /users/{username}/settings/billing/premium_request/usage` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |
| Get billing usage report for a user | `GET /users/{username}/settings/billing/usage` | Yes | Navigator: People > My Billing and Usage |
| Get billing usage summary for a user | `GET /users/{username}/settings/billing/usage/summary` | Planned | Account > Billing and Usage; Organization sheet > Billing (read-only). |

#### Branches

38 operations: 7 yes, 31 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List branches | `GET /repos/{owner}/{repo}/branches` | Yes | Navigator: Repository > owner/name > Code > Branches |
| Get a branch | `GET /repos/{owner}/{repo}/branches/{branch}` | Yes | Properties (Alt+Enter) on Branch |
| Delete branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Get branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Update branch protection | `PUT /repos/{owner}/{repo}/branches/{branch}/protection` | Yes | editor GitHub menu > Configure Branch Protection... |
| Delete admin branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get admin branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Set admin branch protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Delete pull request review protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get pull request review protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Update pull request review protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Delete commit signature protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get commit signature protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Create commit signature protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Remove status check protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get status checks protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Update status check protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Remove status check contexts | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get all status check contexts | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Add status check contexts | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Set status check contexts | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Delete access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get access restrictions | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Remove app access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get apps with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Add app access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Set app access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Remove team access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get teams with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Add team access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Set team access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Remove user access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Get users with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Add user access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Set user access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |
| Rename a branch | `POST /repos/{owner}/{repo}/branches/{branch}/rename` | Yes | Properties (Alt+Enter) on Branch: Name |
| Sync a fork branch with the upstream repository | `POST /repos/{owner}/{repo}/merge-upstream` | Yes | Navigator: Repository > owner/name > Code > Upstream |
| Merge a branch | `POST /repos/{owner}/{repo}/merges` | Planned | Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). |

#### Campaigns

5 operations: 5 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List campaigns for an organization | `GET /orgs/{org}/campaigns` | Planned | Organization > Security > Campaigns (security campaigns). |
| Create a campaign for an organization | `POST /orgs/{org}/campaigns` | Planned | Organization > Security > Campaigns (security campaigns). |
| Delete a campaign for an organization | `DELETE /orgs/{org}/campaigns/{campaign_number}` | Planned | Organization > Security > Campaigns (security campaigns). |
| Get a campaign for an organization | `GET /orgs/{org}/campaigns/{campaign_number}` | Planned | Organization > Security > Campaigns (security campaigns). |
| Update a campaign | `PATCH /orgs/{org}/campaigns/{campaign_number}` | Planned | Organization > Security > Campaigns (security campaigns). |

#### Checks

12 operations: 2 yes, 6 planned, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Create a check run | `POST /repos/{owner}/{repo}/check-runs` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Get a check run | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |
| Update a check run | `PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| List check run annotations | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |
| Rerequest a check run | `POST /repos/{owner}/{repo}/check-runs/{check_run_id}/rerequest` | Yes | context menu > Combined Check Status |
| Create a check suite | `POST /repos/{owner}/{repo}/check-suites` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Update repository preferences for check suites | `PATCH /repos/{owner}/{repo}/check-suites/preferences` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| Get a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |
| List check runs in a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}/check-runs` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |
| Rerequest a check suite | `POST /repos/{owner}/{repo}/check-suites/{check_suite_id}/rerequest` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |
| List check runs for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-runs` | Yes | Properties (Alt+Enter) on Commit |
| List check suites for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-suites` | Planned | Pull request > Checks; Commit > Checks; Run sheet. |

#### Classroom

6 operations: 6 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Closed - Get an assignment | `GET /assignments/{assignment_id}` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |
| Closed - List accepted assignments for an assignment | `GET /assignments/{assignment_id}/accepted_assignments` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |
| Closed - Get assignment grades | `GET /assignments/{assignment_id}/grades` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |
| Closed - List classrooms | `GET /classrooms` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |
| Closed - Get a classroom | `GET /classrooms/{classroom_id}` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |
| Closed - List assignments for a classroom | `GET /classrooms/{classroom_id}/assignments` | Planned | Organizations > org > Classroom (read-only assignments and grades, for teachers). |

#### Code quality

4 operations: 4 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List code quality findings for a repository | `GET /repos/{owner}/{repo}/code-quality/findings` | Planned | Repository > Security > Code Quality. |
| Get a code quality finding | `GET /repos/{owner}/{repo}/code-quality/findings/{finding_number}` | Planned | Repository > Security > Code Quality. |
| Get a code quality setup configuration | `GET /repos/{owner}/{repo}/code-quality/setup` | Planned | Repository > Security > Code Quality. |
| Update a code quality setup configuration | `PATCH /repos/{owner}/{repo}/code-quality/setup` | Planned | Repository > Security > Code Quality. |

#### Code scanning

25 operations: 2 yes, 23 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get the AI Scan setting for an organization | `GET /orgs/{org}/code-scanning/ai-scan` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Update the AI Scan setting for an organization | `PATCH /orgs/{org}/code-scanning/ai-scan` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| List code scanning alerts for an organization | `GET /orgs/{org}/code-scanning/alerts` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get AI Scan enablement for a repository | `GET /repos/{owner}/{repo}/code-scanning/ai-scan` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Update AI Scan enablement for a repository | `PATCH /repos/{owner}/{repo}/code-scanning/ai-scan` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| List code scanning alerts for a repository | `GET /repos/{owner}/{repo}/code-scanning/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Update a code scanning alert | `PATCH /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| Get the status of an autofix for a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Create an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Commit an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix/commits` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| List instances of a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/instances` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| List code scanning analyses for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Delete a code scanning analysis from a repository | `DELETE /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get a code scanning analysis for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| List CodeQL databases for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Delete a CodeQL database | `DELETE /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get a CodeQL database for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Create a CodeQL variant analysis | `POST /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get the summary of a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get the analysis status of a repository in a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}/repos/{repo_owner}/{repo_name}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get a code scanning default setup configuration | `GET /repos/{owner}/{repo}/code-scanning/default-setup` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Update a code scanning default setup configuration | `PATCH /repos/{owner}/{repo}/code-scanning/default-setup` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Upload an analysis as SARIF data | `POST /repos/{owner}/{repo}/code-scanning/sarifs` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |
| Get information about a SARIF upload | `GET /repos/{owner}/{repo}/code-scanning/sarifs/{sarif_id}` | Planned | Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. |

#### Code security

20 operations: 11 planned, 9 left to github.

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
| Get code security configurations for an organization | `GET /orgs/{org}/code-security/configurations` | Planned | Organization > Security > Configurations; Repository > Security. |
| Create a code security configuration | `POST /orgs/{org}/code-security/configurations` | Planned | Organization > Security > Configurations; Repository > Security. |
| Get default code security configurations | `GET /orgs/{org}/code-security/configurations/defaults` | Planned | Organization > Security > Configurations; Repository > Security. |
| Detach configurations from repositories | `DELETE /orgs/{org}/code-security/configurations/detach` | Planned | Organization > Security > Configurations; Repository > Security. |
| Delete a code security configuration | `DELETE /orgs/{org}/code-security/configurations/{configuration_id}` | Planned | Organization > Security > Configurations; Repository > Security. |
| Get a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}` | Planned | Organization > Security > Configurations; Repository > Security. |
| Update a code security configuration | `PATCH /orgs/{org}/code-security/configurations/{configuration_id}` | Planned | Organization > Security > Configurations; Repository > Security. |
| Attach a configuration to repositories | `POST /orgs/{org}/code-security/configurations/{configuration_id}/attach` | Planned | Organization > Security > Configurations; Repository > Security. |
| Set a code security configuration as a default for an organization | `PUT /orgs/{org}/code-security/configurations/{configuration_id}/defaults` | Planned | Organization > Security > Configurations; Repository > Security. |
| Get repositories associated with a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}/repositories` | Planned | Organization > Security > Configurations; Repository > Security. |
| Get the code security configuration associated with a repository | `GET /repos/{owner}/{repo}/code-security-configuration` | Planned | Organization > Security > Configurations; Repository > Security. |

#### Codes of conduct

2 operations: 2 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all codes of conduct | `GET /codes_of_conduct` | Planned | Templates node; New Repository's licence and .gitignore choices |
| Get a code of conduct | `GET /codes_of_conduct/{key}` | Planned | Templates node; New Repository's licence and .gitignore choices |

#### Codespaces

48 operations: 2 yes, 46 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List codespaces for the organization | `GET /orgs/{org}/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Manage access control for organization codespaces | `PUT /orgs/{org}/codespaces/access` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Remove users from Codespaces access for an organization | `DELETE /orgs/{org}/codespaces/access/selected_users` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Add users to Codespaces access for an organization | `POST /orgs/{org}/codespaces/access/selected_users` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List organization secrets | `GET /orgs/{org}/codespaces/secrets` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get an organization public key | `GET /orgs/{org}/codespaces/secrets/public-key` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Delete an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create or update an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List selected repositories for an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Add selected repository to an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List codespaces for a user in organization | `GET /orgs/{org}/members/{username}/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Delete a codespace from the organization | `DELETE /orgs/{org}/members/{username}/codespaces/{codespace_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Stop a codespace for an organization user | `POST /orgs/{org}/members/{username}/codespaces/{codespace_name}/stop` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List codespaces in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create a codespace in a repository | `POST /repos/{owner}/{repo}/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List devcontainer configurations in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces/devcontainers` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List available machine types for a repository | `GET /repos/{owner}/{repo}/codespaces/machines` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get default attributes for a codespace | `GET /repos/{owner}/{repo}/codespaces/new` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Check if permissions defined by a devcontainer have been accepted by the authenticated user | `GET /repos/{owner}/{repo}/codespaces/permissions_check` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List repository secrets | `GET /repos/{owner}/{repo}/codespaces/secrets` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get a repository public key | `GET /repos/{owner}/{repo}/codespaces/secrets/public-key` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get a repository secret | `GET /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create a codespace from a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List codespaces for the authenticated user | `GET /user/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create a codespace for the authenticated user | `POST /user/codespaces` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List secrets for the authenticated user | `GET /user/codespaces/secrets` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get public key for the authenticated user | `GET /user/codespaces/secrets/public-key` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Delete a secret for the authenticated user | `DELETE /user/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get a secret for the authenticated user | `GET /user/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create or update a secret for the authenticated user | `PUT /user/codespaces/secrets/{secret_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List selected repositories for a user secret | `GET /user/codespaces/secrets/{secret_name}/repositories` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Set selected repositories for a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Remove a selected repository from a user secret | `DELETE /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Add a selected repository to a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Delete a codespace for the authenticated user | `DELETE /user/codespaces/{codespace_name}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get a codespace for the authenticated user | `GET /user/codespaces/{codespace_name}` | Yes | Properties (Alt+Enter) on Codespace |
| Update a codespace for the authenticated user | `PATCH /user/codespaces/{codespace_name}` | Yes | Properties (Alt+Enter) on Codespace: Display name |
| Export a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/exports` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Get details about a codespace export | `GET /user/codespaces/{codespace_name}/exports/{export_id}` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| List machine types for a codespace | `GET /user/codespaces/{codespace_name}/machines` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Create a repository from an unpublished codespace | `POST /user/codespaces/{codespace_name}/publish` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Start a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/start` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |
| Stop a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/stop` | Planned | Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. |

#### Collaborators

11 operations: 10 yes, 1 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List repository collaborators | `GET /repos/{owner}/{repo}/collaborators` | Yes | Navigator: Repository > owner/name > People > Collaborators and Team Access |
| Remove a repository collaborator | `DELETE /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Check if a user is a repository collaborator | `GET /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Add a repository collaborator | `PUT /repos/{owner}/{repo}/collaborators/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get repository permissions for a user | `GET /repos/{owner}/{repo}/collaborators/{username}/permission` | Yes | Account > Roles and Access > Bulk Access Changes... |
| List repository invitations | `GET /repos/{owner}/{repo}/invitations` | Yes | Properties (Alt+Enter) on Invitation |
| Delete a repository invitation | `DELETE /repos/{owner}/{repo}/invitations/{invitation_id}` | Planned | Repository sheet > Access (section 18.3). |
| Update a repository invitation | `PATCH /repos/{owner}/{repo}/invitations/{invitation_id}` | Yes | Properties (Alt+Enter) on Invitation: Role |
| List repository invitations for the authenticated user | `GET /user/repository_invitations` | Yes | Navigator: Needs My Attention > Invitations |
| Decline a repository invitation | `DELETE /user/repository_invitations/{invitation_id}` | Yes | context menu > Decline Invitation... |
| Accept a repository invitation | `PATCH /user/repository_invitations/{invitation_id}` | Yes | context menu > Accept Invitation... |

#### Commits

14 operations: 7 yes, 7 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List commit comments for a repository | `GET /repos/{owner}/{repo}/comments` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| Delete a commit comment | `DELETE /repos/{owner}/{repo}/comments/{comment_id}` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| Get a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| Update a commit comment | `PATCH /repos/{owner}/{repo}/comments/{comment_id}` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| List commits | `GET /repos/{owner}/{repo}/commits` | Yes | Navigator: Repository > owner/name > Code > Commits |
| List branches for HEAD commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/branches-where-head` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| List commit comments | `GET /repos/{owner}/{repo}/commits/{commit_sha}/comments` | Yes | context menu > Commit Comments... |
| Create a commit comment | `POST /repos/{owner}/{repo}/commits/{commit_sha}/comments` | Yes | context menu > Commit Comments... |
| List pull requests associated with a commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/pulls` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| Get a commit | `GET /repos/{owner}/{repo}/commits/{ref}` | Yes | Properties (Alt+Enter) on Commit |
| Get the combined status for a specific reference | `GET /repos/{owner}/{repo}/commits/{ref}/status` | Yes | context menu > Combined Check Status |
| List commit statuses for a reference | `GET /repos/{owner}/{repo}/commits/{ref}/statuses` | Planned | Commit sheet; Repository > Code > Commits; Commit comments. |
| Compare two commits | `GET /repos/{owner}/{repo}/compare/{basehead}` | Yes | Repository > Compare Branches... (Ctrl+Shift+B) |
| Create a commit status | `POST /repos/{owner}/{repo}/statuses/{sha}` | Yes | context menu > Set Status... |

#### Copilot

44 operations: 33 planned, 11 left to github.

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
| Get Copilot seat information and settings for an organization | `GET /orgs/{org}/copilot/billing` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| List all Copilot seat assignments for an organization | `GET /orgs/{org}/copilot/billing/seats` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Remove teams from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_teams` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Add teams to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_teams` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Remove users from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_users` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Add users to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_users` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get the Copilot code review runner configuration for an organization | `GET /orgs/{org}/copilot/code-review/runner` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set the Copilot code review runner configuration for an organization | `PUT /orgs/{org}/copilot/code-review/runner` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot code review settings for an organization | `GET /orgs/{org}/copilot/code-review/settings` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Update Copilot code review settings for an organization | `PATCH /orgs/{org}/copilot/code-review/settings` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot cloud agent permissions for an organization | `GET /orgs/{org}/copilot/coding-agent/permissions` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set Copilot cloud agent permissions for an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| List repositories enabled for Copilot cloud agent in an organization | `GET /orgs/{org}/copilot/coding-agent/permissions/repositories` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set selected repositories for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Disable a repository for Copilot cloud agent in an organization | `DELETE /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Enable a repository for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot content exclusion rules for an organization | `GET /orgs/{org}/copilot/content_exclusion` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set Copilot content exclusion rules for an organization | `PUT /orgs/{org}/copilot/content_exclusion` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/organization-1-day` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization usage metrics | `GET /orgs/{org}/copilot/metrics/reports/organization-28-day/latest` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization repository report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/repos-1-day` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization user-teams report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/user-teams-1-day` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization users usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/users-1-day` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot organization users usage metrics | `GET /orgs/{org}/copilot/metrics/reports/users-28-day/latest` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get the Copilot code review policy for an organization | `GET /orgs/{org}/copilot/policies/code-review` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set the Copilot code review policy for an organization | `PUT /orgs/{org}/copilot/policies/code-review` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot seat assignment details for a user | `GET /orgs/{org}/members/{username}/copilot` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Delete Copilot customizations for a team | `DELETE /orgs/{org}/teams/{team_slug}/copilot/customizations` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot customizations for a team | `GET /orgs/{org}/teams/{team_slug}/copilot/customizations` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Set Copilot customizations for a team | `PUT /orgs/{org}/teams/{team_slug}/copilot/customizations` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot cloud agent configuration for a repository | `GET /repos/{owner}/{repo}/copilot/cloud-agent/configuration` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Get Copilot code review settings for a repository | `GET /repos/{owner}/{repo}/copilot/code-review/settings` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |
| Update Copilot code review settings for a repository | `PATCH /repos/{owner}/{repo}/copilot/code-review/settings` | Planned | Organization > Copilot (seats, policies, usage); Account > Copilot. |

#### Copilot Spaces

28 operations: 28 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization Copilot Spaces | `GET /orgs/{org}/copilot-spaces` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Create an organization Copilot Space | `POST /orgs/{org}/copilot-spaces` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Delete an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Get an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| List collaborators for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/collaborators` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Add a collaborator to an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/collaborators` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Remove a collaborator from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set a collaborator role for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| List resources for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Create a resource for an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/resources` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Delete a resource from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Get a resource for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set a resource for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| List Copilot Spaces for a user | `GET /users/{username}/copilot-spaces` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Create a Copilot Space for a user | `POST /users/{username}/copilot-spaces` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Delete a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Get a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| List collaborators for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/collaborators` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Add a collaborator to a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/collaborators` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Remove a collaborator from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set a collaborator role for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| List resources for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Create a resource for a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/resources` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Delete a resource from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Get a resource for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |
| Set a resource for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | Planned | Account > Copilot > Spaces; Organization > Copilot > Spaces. |

#### Credentials

1 operations: 1 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Revoke a list of credentials | `POST /credentials/revoke` | Left to GitHub | For secret-scanning partners to revoke leaked credentials, not for people. |

#### Dependabot

27 operations: 2 yes, 21 planned, 4 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List Dependabot alerts for an enterprise | `GET /enterprises/{enterprise}/dependabot/alerts` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Lists the repositories Dependabot can access in an enterprise | `GET /enterprises/{enterprise}/dependabot/repository-access` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Updates Dependabot's repository access list for an enterprise | `PATCH /enterprises/{enterprise}/dependabot/repository-access` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| Set the default repository access level for Dependabot in an enterprise | `PUT /enterprises/{enterprise}/dependabot/repository-access/default-level` | Left to GitHub | Enterprise account administration (GitHub Enterprise Cloud); enterprise owners use the enterprise's own settings. Organizations > org > Enterprise (Open on GitHub). |
| List Dependabot alerts for an organization | `GET /orgs/{org}/dependabot/alerts` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Lists the repositories Dependabot can access in an organization | `GET /orgs/{org}/dependabot/repository-access` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Updates Dependabot's repository access list for an organization | `PATCH /orgs/{org}/dependabot/repository-access` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Set the default repository access level for Dependabot | `PUT /orgs/{org}/dependabot/repository-access/default-level` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| List organization secrets | `GET /orgs/{org}/dependabot/secrets` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Get an organization public key | `GET /orgs/{org}/dependabot/secrets/public-key` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Delete an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Get an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Create or update an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| List selected repositories for an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Add selected repository to an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| List Dependabot alerts for a repository | `GET /repos/{owner}/{repo}/dependabot/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a Dependabot alert | `GET /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Update a Dependabot alert | `PATCH /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| Get repository Dependabot runner settings | `GET /repos/{owner}/{repo}/dependabot/runner-settings` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Set repository Dependabot runner settings | `PUT /repos/{owner}/{repo}/dependabot/runner-settings` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| List repository secrets | `GET /repos/{owner}/{repo}/dependabot/secrets` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Get a repository public key | `GET /repos/{owner}/{repo}/dependabot/secrets/public-key` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Get a repository secret | `GET /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | Planned | Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. |

#### Dependency graph

5 operations: 1 yes, 4 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get a diff of the dependencies between commits | `GET /repos/{owner}/{repo}/dependency-graph/compare/{basehead}` | Planned | Repository > Security > Dependencies; Export SBOM. |
| Export a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom` | Yes | Repository > Export Software Bill of Materials... (Ctrl+Alt+B) |
| Fetch a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/fetch-report/{sbom_uuid}` | Planned | Repository > Security > Dependencies; Export SBOM. |
| Request generation of a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/generate-report` | Planned | Repository > Security > Dependencies; Export SBOM. |
| Create a snapshot of dependencies for a repository | `POST /repos/{owner}/{repo}/dependency-graph/snapshots` | Planned | Repository > Security > Dependencies; Export SBOM. |

#### Deploy keys

4 operations: 2 yes, 2 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List deploy keys | `GET /repos/{owner}/{repo}/keys` | Yes | Properties (Alt+Enter) on Repository |
| Create a deploy key | `POST /repos/{owner}/{repo}/keys` | Planned | Repository sheet > Deploy Keys. |
| Delete a deploy key | `DELETE /repos/{owner}/{repo}/keys/{key_id}` | Planned | Repository sheet > Deploy Keys. |
| Get a deploy key | `GET /repos/{owner}/{repo}/keys/{key_id}` | Yes | Properties (Alt+Enter) on Deploy Key |

#### Deployments

21 operations: 5 yes, 16 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List deployments | `GET /repos/{owner}/{repo}/deployments` | Planned | Repository > Deployments and Environments; Environment and Deployment sheets. |
| Create a deployment | `POST /repos/{owner}/{repo}/deployments` | Planned | Repository > Deployments and Environments; Environment and Deployment sheets. |
| Delete a deployment | `DELETE /repos/{owner}/{repo}/deployments/{deployment_id}` | Planned | Repository > Deployments and Environments; Environment and Deployment sheets. |
| Get a deployment | `GET /repos/{owner}/{repo}/deployments/{deployment_id}` | Yes | Properties (Alt+Enter) on Deployment |
| List deployment statuses | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | Yes | Properties (Alt+Enter) on Deployment |
| Create a deployment status | `POST /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | Planned | Deployment sheet > Statuses. |
| Get a deployment status | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses/{status_id}` | Planned | Deployment sheet > Statuses. |
| List environments | `GET /repos/{owner}/{repo}/environments` | Yes | Navigator: Repository > owner/name > Settings > Secret and Variable Names |
| Delete an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}` | Planned | Environment sheet. |
| Get an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}` | Yes | Properties (Alt+Enter) on Environment |
| Create or update an environment | `PUT /repos/{owner}/{repo}/environments/{environment_name}` | Yes | Properties (Alt+Enter) on Environment: Allow administrators to bypass |
| List deployment branch policies | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | Planned | Environment sheet > Branches and Tags. |
| Create a deployment branch policy | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | Planned | Environment sheet > Branches and Tags. |
| Delete a deployment branch policy | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Planned | Environment sheet > Branches and Tags. |
| Get a deployment branch policy | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Planned | Environment sheet > Branches and Tags. |
| Update a deployment branch policy | `PUT /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | Planned | Environment sheet > Branches and Tags. |
| Get all deployment protection rules for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | Planned | Environment sheet > Protection. |
| Create a custom deployment protection rule on an environment | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | Planned | Environment sheet > Protection. |
| List custom deployment rule integrations available for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/apps` | Planned | Environment sheet > Protection. |
| Disable a custom protection rule for an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | Planned | Environment sheet > Protection. |
| Get a custom deployment protection rule | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | Planned | Environment sheet > Protection. |

#### Emojis

1 operations: 1 not needed.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get emojis | `GET /emojis` | Not needed | The emoji list; comment boxes use QUILL's own emoji catalogue. Plumbing. |

#### Gists

20 operations: 8 yes, 12 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List gists for the authenticated user | `GET /gists` | Yes | Navigator: Gists > My Gists |
| Create a gist | `POST /gists` | Yes | File > New Here... (Ctrl+N) |
| List public gists | `GET /gists/public` | Planned | Gists; Gist sheet. |
| List starred gists | `GET /gists/starred` | Planned | Gists; Gist sheet. |
| Delete a gist | `DELETE /gists/{gist_id}` | Yes | context menu > Delete Gist... |
| Get a gist | `GET /gists/{gist_id}` | Yes | Properties (Alt+Enter) on Gist |
| Update a gist | `PATCH /gists/{gist_id}` | Yes | context menu > Edit Gist... |
| List gist comments | `GET /gists/{gist_id}/comments` | Planned | Gists; Gist sheet. |
| Create a gist comment | `POST /gists/{gist_id}/comments` | Planned | Gists; Gist sheet. |
| Delete a gist comment | `DELETE /gists/{gist_id}/comments/{comment_id}` | Planned | Gists; Gist sheet. |
| Get a gist comment | `GET /gists/{gist_id}/comments/{comment_id}` | Planned | Gists; Gist sheet. |
| Update a gist comment | `PATCH /gists/{gist_id}/comments/{comment_id}` | Planned | Gists; Gist sheet. |
| List gist commits | `GET /gists/{gist_id}/commits` | Planned | Gists; Gist sheet. |
| List gist forks | `GET /gists/{gist_id}/forks` | Planned | Gists; Gist sheet. |
| Fork a gist | `POST /gists/{gist_id}/forks` | Planned | Gists; Gist sheet. |
| Unstar a gist | `DELETE /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Check if a gist is starred | `GET /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Star a gist | `PUT /gists/{gist_id}/star` | Yes | context menu > Star or Unstar |
| Get a gist revision | `GET /gists/{gist_id}/{sha}` | Planned | Gists; Gist sheet. |
| List gists for a user | `GET /users/{username}/gists` | Planned | Gists; Gist sheet. |

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

2 operations: 2 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all gitignore templates | `GET /gitignore/templates` | Planned | Templates node; New Repository's licence and .gitignore choices |
| Get a gitignore template | `GET /gitignore/templates/{name}` | Planned | Templates node; New Repository's licence and .gitignore choices |

#### Interactions

16 operations: 2 yes, 14 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Remove interaction restrictions for an organization | `DELETE /orgs/{org}/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get interaction restrictions for an organization | `GET /orgs/{org}/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Set interaction restrictions for an organization | `PUT /orgs/{org}/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get pull request creation cap for an org | `GET /orgs/{org}/interaction-limits/pulls/creation-cap` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Update pull request creation cap for an org | `PATCH /orgs/{org}/interaction-limits/pulls/creation-cap` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Remove interaction restrictions for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get interaction restrictions for a repository | `GET /repos/{owner}/{repo}/interaction-limits` | Yes | Properties (Alt+Enter) on Repository |
| Set interaction restrictions for a repository | `PUT /repos/{owner}/{repo}/interaction-limits` | Yes | Properties (Alt+Enter) on Repository: Interaction limit |
| Remove users from the pull request creation cap bypass list for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get pull request creation cap bypass list for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Add users to the pull request creation cap bypass list for a repository | `PUT /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get pull request creation cap for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Update pull request creation cap for a repository | `PATCH /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Remove interaction restrictions from your public repositories | `DELETE /user/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Get interaction restrictions for your public repositories | `GET /user/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |
| Set interaction restrictions for your public repositories | `PUT /user/interaction-limits` | Planned | Repository and Organization sheets > General > Interaction Limits. |

#### Issues

66 operations: 29 yes, 37 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List issues assigned to the authenticated user | `GET /issues` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| List organization issues assigned to the authenticated user | `GET /orgs/{org}/issues` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| List assignees | `GET /repos/{owner}/{repo}/assignees` | Yes | context menu > Assignees... |
| Check if a user can be assigned | `GET /repos/{owner}/{repo}/assignees/{assignee}` | Planned | Issue > Organize: Assignees. |
| List repository issues | `GET /repos/{owner}/{repo}/issues` | Yes | Navigator: Repository > owner/name > Issues |
| Create an issue | `POST /repos/{owner}/{repo}/issues` | Yes | File > New Here... (Ctrl+N) |
| List issue comments for a repository | `GET /repos/{owner}/{repo}/issues/comments` | Planned | Comment sheet; Conversation page. |
| Delete an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment |
| Get an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment: Comment |
| Update an issue comment | `PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}` | Yes | Properties (Alt+Enter) on Comment: Comment |
| Unpin an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | Planned | Comment sheet; Conversation page. |
| Pin an issue comment | `PUT /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | Planned | Comment sheet; Conversation page. |
| List issue events for a repository | `GET /repos/{owner}/{repo}/issues/events` | Planned | Issue > Timeline. |
| Get an issue event | `GET /repos/{owner}/{repo}/issues/events/{event_id}` | Planned | Issue > Timeline. |
| Get an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}` | Yes | context menu > Show Details |
| Update an issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}` | Yes | context menu > Close or Reopen... |
| List issue artifacts | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Create an issue artifact | `POST /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Delete an issue artifact | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Get an issue artifact | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Update an issue artifact | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Remove assignees from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/assignees` | Yes | context menu > Assignees... |
| Add assignees to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/assignees` | Yes | context menu > Assignees... |
| Check if a user can be assigned to a issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/assignees/{assignee}` | Planned | Issue > Organize: Assignees. |
| List issue comments | `GET /repos/{owner}/{repo}/issues/{issue_number}/comments` | Planned | Comment sheet; Conversation page. |
| Create an issue comment | `POST /repos/{owner}/{repo}/issues/{issue_number}/comments` | Yes | Item > Comment... (Ctrl+Shift+M) |
| List dependencies an issue is blocked by | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | Planned | Issue > Relationships: blocked by, blocking. |
| Add a dependency an issue is blocked by | `POST /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | Planned | Issue > Relationships: blocked by, blocking. |
| Remove dependency an issue is blocked by | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by/{issue_id}` | Planned | Issue > Relationships: blocked by, blocking. |
| List dependencies an issue is blocking | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocking` | Planned | Issue > Relationships: blocked by, blocking. |
| List issue events | `GET /repos/{owner}/{repo}/issues/{issue_number}/events` | Planned | Issue > Timeline. |
| List issue field values for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Yes | context menu > Read Issue Type and Fields |
| Add issue field values to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Set issue field values for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Delete an issue field value from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values/{issue_field_id}` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Remove all labels from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels` | Planned | Label sheet; Issue > Organize: Labels. |
| List labels for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/labels` | Yes | context menu > Labels... |
| Add labels to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/labels` | Yes | context menu > Labels... |
| Set labels for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/labels` | Planned | Label sheet; Issue > Organize: Labels. |
| Remove a label from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}` | Yes | context menu > Labels... |
| Unlock an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/lock` | Yes | context menu > Lock or Unlock Conversation... |
| Lock an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/lock` | Yes | context menu > Lock or Unlock Conversation... |
| Get parent issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/parent` | Planned | Issue > Relationships: sub-issues. |
| List issues related to an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Add a related issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Remove a related issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/relates_to/{issue_id}` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Remove sub-issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/sub_issue` | Planned | Issue > Relationships: sub-issues. |
| List sub-issues | `GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | Yes | context menu > Reorder Sub-issues... |
| Add sub-issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | Planned | Issue > Relationships: sub-issues. |
| Reprioritize sub-issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/sub_issues/priority` | Yes | context menu > Reorder Sub-issues... |
| List issue suggestions | `GET /repos/{owner}/{repo}/issues/{issue_number}/suggestions` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Approve an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/approve` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| Dismiss an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/dismiss` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |
| List timeline events for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/timeline` | Yes | context menu > View Timeline... |
| List labels for a repository | `GET /repos/{owner}/{repo}/labels` | Yes | Navigator: Repository > owner/name > Labels |
| Create a label | `POST /repos/{owner}/{repo}/labels` | Yes | context menu > Labels... |
| Delete a label | `DELETE /repos/{owner}/{repo}/labels/{name}` | Yes | context menu > Delete Everywhere... |
| Get a label | `GET /repos/{owner}/{repo}/labels/{name}` | Yes | Properties (Alt+Enter) on Label |
| Update a label | `PATCH /repos/{owner}/{repo}/labels/{name}` | Yes | Properties (Alt+Enter) on Label: Colour |
| List milestones | `GET /repos/{owner}/{repo}/milestones` | Yes | Navigator: Repository > owner/name > Milestones |
| Create a milestone | `POST /repos/{owner}/{repo}/milestones` | Yes | context menu > Milestone... |
| Delete a milestone | `DELETE /repos/{owner}/{repo}/milestones/{milestone_number}` | Planned | Milestone sheet; Issue > Organize: Milestone. |
| Get a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}` | Yes | context menu > Milestone... |
| Update a milestone | `PATCH /repos/{owner}/{repo}/milestones/{milestone_number}` | Yes | context menu > Milestone... |
| List labels for issues in a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}/labels` | Planned | Label sheet; Issue > Organize: Labels. |
| List user account issues assigned to the authenticated user | `GET /user/issues` | Planned | Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. |

#### Licenses

3 operations: 3 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get all commonly used licenses | `GET /licenses` | Planned | Templates node; New Repository's licence and .gitignore choices |
| Get a license | `GET /licenses/{license}` | Planned | Templates node; New Repository's licence and .gitignore choices |
| Get the license for a repository | `GET /repos/{owner}/{repo}/license` | Planned | Templates node; New Repository's licence and .gitignore choices |

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

22 operations: 14 planned, 8 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization migrations | `GET /orgs/{org}/migrations` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Start an organization migration | `POST /orgs/{org}/migrations` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Get an organization migration status | `GET /orgs/{org}/migrations/{migration_id}` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Delete an organization migration archive | `DELETE /orgs/{org}/migrations/{migration_id}/archive` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Download an organization migration archive | `GET /orgs/{org}/migrations/{migration_id}/archive` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Unlock an organization repository | `DELETE /orgs/{org}/migrations/{migration_id}/repos/{repo_name}/lock` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| List repositories in an organization migration | `GET /orgs/{org}/migrations/{migration_id}/repositories` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Cancel an import | `DELETE /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get an import status | `GET /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Update an import | `PATCH /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Start an import | `PUT /repos/{owner}/{repo}/import` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get commit authors | `GET /repos/{owner}/{repo}/import/authors` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Map a commit author | `PATCH /repos/{owner}/{repo}/import/authors/{author_id}` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Get large files | `GET /repos/{owner}/{repo}/import/large_files` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| Update Git LFS preference | `PATCH /repos/{owner}/{repo}/import/lfs` | Left to GitHub | GitHub retired the Source Imports API on 12 April 2024; GitHub Importer replaces it. |
| List user migrations | `GET /user/migrations` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Start a user migration | `POST /user/migrations` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Get a user migration status | `GET /user/migrations/{migration_id}` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Delete a user migration archive | `DELETE /user/migrations/{migration_id}/archive` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Download a user migration archive | `GET /user/migrations/{migration_id}/archive` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| Unlock a user repository | `DELETE /user/migrations/{migration_id}/repos/{repo_name}/lock` | Planned | Account > Export My Data; Organization > Migrations (archives). |
| List repositories for a user migration | `GET /user/migrations/{migration_id}/repositories` | Planned | Account > Export My Data; Organization > Migrations (archives). |

#### Organizations

129 operations: 21 yes, 108 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organizations | `GET /organizations` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete an organization | `DELETE /orgs/{org}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Get an organization | `GET /orgs/{org}` | Yes | Navigator: Organization > organization |
| Update an organization | `PATCH /orgs/{org}` | Yes | Properties (Alt+Enter) on Organization: Base repository permission |
| Create an artifact deployment record | `POST /orgs/{org}/artifacts/metadata/deployment-record` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Set cluster deployment records | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Create a cluster deployment records job | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Get cluster deployment records job status | `GET /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs/{job_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Create artifact metadata storage record | `POST /orgs/{org}/artifacts/metadata/storage-record` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List artifact deployment records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/deployment-records` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List artifact storage records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/storage-records` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List attestations by bulk subject digests | `POST /orgs/{org}/attestations/bulk-list` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete attestations in bulk | `POST /orgs/{org}/attestations/delete-request` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete attestations by subject digest | `DELETE /orgs/{org}/attestations/digest/{subject_digest}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List attestation repositories | `GET /orgs/{org}/attestations/repositories` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete attestations by ID | `DELETE /orgs/{org}/attestations/{attestation_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List attestations | `GET /orgs/{org}/attestations/{subject_digest}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List users blocked by an organization | `GET /orgs/{org}/blocks` | Planned | Organization sheet > Blocked Users; Person > You: Block. |
| Unblock a user from an organization | `DELETE /orgs/{org}/blocks/{username}` | Planned | Organization sheet > Blocked Users; Person > You: Block. |
| Check if a user is blocked by an organization | `GET /orgs/{org}/blocks/{username}` | Planned | Organization sheet > Blocked Users; Person > You: Block. |
| Block a user from an organization | `PUT /orgs/{org}/blocks/{username}` | Planned | Organization sheet > Blocked Users; Person > You: Block. |
| List failed organization invitations | `GET /orgs/{org}/failed_invitations` | Planned | Organization sheet > Members. |
| List organization webhooks | `GET /orgs/{org}/hooks` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization webhook | `POST /orgs/{org}/hooks` | Planned | Organization sheet > Webhooks. |
| Delete an organization webhook | `DELETE /orgs/{org}/hooks/{hook_id}` | Planned | Organization sheet > Webhooks. |
| Get an organization webhook | `GET /orgs/{org}/hooks/{hook_id}` | Planned | Organization sheet > Webhooks. |
| Update an organization webhook | `PATCH /orgs/{org}/hooks/{hook_id}` | Planned | Organization sheet > Webhooks. |
| Get a webhook configuration for an organization | `GET /orgs/{org}/hooks/{hook_id}/config` | Planned | Organization sheet > Webhooks. |
| Update a webhook configuration for an organization | `PATCH /orgs/{org}/hooks/{hook_id}/config` | Planned | Organization sheet > Webhooks. |
| List deliveries for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries` | Planned | Organization sheet > Webhooks. |
| Get a webhook delivery for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}` | Planned | Organization sheet > Webhooks. |
| Redeliver a delivery for an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | Planned | Organization sheet > Webhooks. |
| Ping an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/pings` | Planned | Organization sheet > Webhooks. |
| Get route stats by actor | `GET /orgs/{org}/insights/api/route-stats/{actor_type}/{actor_id}` | Planned | Organization > Insights > API usage (read). |
| Get subject stats | `GET /orgs/{org}/insights/api/subject-stats` | Planned | Organization > Insights > API usage (read). |
| Get summary stats | `GET /orgs/{org}/insights/api/summary-stats` | Planned | Organization > Insights > API usage (read). |
| Get summary stats by user | `GET /orgs/{org}/insights/api/summary-stats/users/{user_id}` | Planned | Organization > Insights > API usage (read). |
| Get summary stats by actor | `GET /orgs/{org}/insights/api/summary-stats/{actor_type}/{actor_id}` | Planned | Organization > Insights > API usage (read). |
| Get time stats | `GET /orgs/{org}/insights/api/time-stats` | Planned | Organization > Insights > API usage (read). |
| Get time stats by user | `GET /orgs/{org}/insights/api/time-stats/users/{user_id}` | Planned | Organization > Insights > API usage (read). |
| Get time stats by actor | `GET /orgs/{org}/insights/api/time-stats/{actor_type}/{actor_id}` | Planned | Organization > Insights > API usage (read). |
| Get user stats | `GET /orgs/{org}/insights/api/user-stats/{user_id}` | Planned | Organization > Insights > API usage (read). |
| List app installations for an organization | `GET /orgs/{org}/installations` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List pending organization invitations | `GET /orgs/{org}/invitations` | Yes | Properties (Alt+Enter) on Organization |
| Create an organization invitation | `POST /orgs/{org}/invitations` | Planned | Organization sheet > Members. |
| Cancel an organization invitation | `DELETE /orgs/{org}/invitations/{invitation_id}` | Planned | Organization sheet > Members. |
| List organization invitation teams | `GET /orgs/{org}/invitations/{invitation_id}/teams` | Planned | Organization sheet > Members. |
| List issue fields for an organization | `GET /orgs/{org}/issue-fields` | Yes | context menu > Read Issue Type and Fields |
| Create issue field for an organization | `POST /orgs/{org}/issue-fields` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete issue field for an organization | `DELETE /orgs/{org}/issue-fields/{issue_field_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Update issue field for an organization | `PATCH /orgs/{org}/issue-fields/{issue_field_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List issue types for an organization | `GET /orgs/{org}/issue-types` | Yes | Properties (Alt+Enter) on Issue Type |
| Create issue type for an organization | `POST /orgs/{org}/issue-types` | Planned | Issue type sheet (organization). |
| Delete issue type for an organization | `DELETE /orgs/{org}/issue-types/{issue_type_id}` | Planned | Issue type sheet (organization). |
| Update issue type for an organization | `PUT /orgs/{org}/issue-types/{issue_type_id}` | Yes | Properties (Alt+Enter) on Issue Type: Colour |
| List organization members | `GET /orgs/{org}/members` | Yes | Properties (Alt+Enter) on Organization |
| Remove an organization member | `DELETE /orgs/{org}/members/{username}` | Planned | Organization sheet > Members. |
| Check organization membership for a user | `GET /orgs/{org}/members/{username}` | Planned | Organization sheet > Members. |
| Remove organization membership for a user | `DELETE /orgs/{org}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get organization membership for a user | `GET /orgs/{org}/memberships/{username}` | Planned | Organization sheet > Members. |
| Set organization membership for a user | `PUT /orgs/{org}/memberships/{username}` | Yes | Account > Roles and Access > Bulk Access Changes... |
| Get all organization roles for an organization | `GET /orgs/{org}/organization-roles` | Yes | Properties (Alt+Enter) on Organization |
| Remove all organization roles for a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}` | Planned | Organization sheet > Roles. |
| Remove an organization role from a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | Planned | Organization sheet > Roles. |
| Assign an organization role to a team | `PUT /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | Planned | Organization sheet > Roles. |
| Remove all organization roles for a user | `DELETE /orgs/{org}/organization-roles/users/{username}` | Planned | Organization sheet > Roles. |
| Remove an organization role from a user | `DELETE /orgs/{org}/organization-roles/users/{username}/{role_id}` | Planned | Organization sheet > Roles. |
| Assign an organization role to a user | `PUT /orgs/{org}/organization-roles/users/{username}/{role_id}` | Planned | Organization sheet > Roles. |
| Get an organization role | `GET /orgs/{org}/organization-roles/{role_id}` | Planned | Organization sheet > Roles. |
| List teams that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/teams` | Planned | Organization sheet > Roles. |
| List users that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/users` | Planned | Organization sheet > Roles. |
| List outside collaborators for an organization | `GET /orgs/{org}/outside_collaborators` | Yes | Properties (Alt+Enter) on Organization |
| Remove outside collaborator from an organization | `DELETE /orgs/{org}/outside_collaborators/{username}` | Planned | Organization sheet > Outside Collaborators. |
| Convert an organization member to outside collaborator | `PUT /orgs/{org}/outside_collaborators/{username}` | Planned | Organization sheet > Outside Collaborators. |
| List requests to access organization resources with fine-grained personal access tokens | `GET /orgs/{org}/personal-access-token-requests` | Yes | Properties (Alt+Enter) on Organization |
| Review requests to access organization resources with fine-grained personal access tokens | `POST /orgs/{org}/personal-access-token-requests` | Planned | Organization sheet > Token Requests. |
| Review a request to access organization resources with a fine-grained personal access token | `POST /orgs/{org}/personal-access-token-requests/{pat_request_id}` | Planned | Organization sheet > Token Requests. |
| List repositories requested to be accessed by a fine-grained personal access token | `GET /orgs/{org}/personal-access-token-requests/{pat_request_id}/repositories` | Planned | Organization sheet > Token Requests. |
| List fine-grained personal access tokens with access to organization resources | `GET /orgs/{org}/personal-access-tokens` | Planned | Organization sheet > Token Requests. |
| Update the access to organization resources via fine-grained personal access tokens | `POST /orgs/{org}/personal-access-tokens` | Planned | Organization sheet > Token Requests. |
| Update the access a fine-grained personal access token has to organization resources | `POST /orgs/{org}/personal-access-tokens/{pat_id}` | Planned | Organization sheet > Token Requests. |
| List repositories a fine-grained personal access token has access to | `GET /orgs/{org}/personal-access-tokens/{pat_id}/repositories` | Planned | Organization sheet > Token Requests. |
| Get registered app installations for external custom properties | `GET /orgs/{org}/properties/installations` | Planned | Organization sheet > Custom Properties. |
| Register an app installation for external custom properties | `POST /orgs/{org}/properties/installations` | Planned | Organization sheet > Custom Properties. |
| Get all external custom properties for a GitHub App installation in an organization | `GET /orgs/{org}/properties/installations/schema` | Planned | Organization sheet > Custom Properties. |
| Create or update external custom property values for organization repositories | `PATCH /orgs/{org}/properties/installations/values` | Planned | Organization sheet > Custom Properties. |
| Remove all external custom property values for a property across all organization repositories | `DELETE /orgs/{org}/properties/installations/values/{property_name}` | Planned | Organization sheet > Custom Properties. |
| Create or update external custom property values for a property across organization repositories | `PATCH /orgs/{org}/properties/installations/values/{property_name}` | Planned | Organization sheet > Custom Properties. |
| Get all custom properties for an organization | `GET /orgs/{org}/properties/schema` | Yes | Properties (Alt+Enter) on Organization |
| Create or update custom properties for an organization | `PATCH /orgs/{org}/properties/schema` | Planned | Organization sheet > Custom Properties. |
| Remove a custom property for an organization | `DELETE /orgs/{org}/properties/schema/{custom_property_name}` | Planned | Organization sheet > Custom Properties. |
| Get a custom property for an organization | `GET /orgs/{org}/properties/schema/{custom_property_name}` | Planned | Organization sheet > Custom Properties. |
| Create or update a custom property for an organization | `PUT /orgs/{org}/properties/schema/{custom_property_name}` | Planned | Organization sheet > Custom Properties. |
| List custom property values for organization repositories | `GET /orgs/{org}/properties/values` | Planned | Organization sheet > Custom Properties. |
| Create or update custom property values for organization repositories | `PATCH /orgs/{org}/properties/values` | Planned | Organization sheet > Custom Properties. |
| List public organization members | `GET /orgs/{org}/public_members` | Planned | Organization sheet > Members. |
| Remove public organization membership for the authenticated user | `DELETE /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization: Show my membership publicly |
| Check public organization membership for a user | `GET /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization |
| Set public organization membership for the authenticated user | `PUT /orgs/{org}/public_members/{username}` | Yes | Properties (Alt+Enter) on Organization: Show my membership publicly |
| Get all organization repository rulesets | `GET /orgs/{org}/rulesets` | Planned | Organization rulesets (section 18.3.1). |
| Create an organization repository ruleset | `POST /orgs/{org}/rulesets` | Yes | context menu > Promote to Organization... |
| List organization rule suites | `GET /orgs/{org}/rulesets/rule-suites` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Get an organization rule suite | `GET /orgs/{org}/rulesets/rule-suites/{rule_suite_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete an organization repository ruleset | `DELETE /orgs/{org}/rulesets/{ruleset_id}` | Planned | Organization rulesets (section 18.3.1). |
| Get an organization repository ruleset | `GET /orgs/{org}/rulesets/{ruleset_id}` | Planned | Organization rulesets (section 18.3.1). |
| Update an organization repository ruleset | `PUT /orgs/{org}/rulesets/{ruleset_id}` | Planned | Organization rulesets (section 18.3.1). |
| Get organization ruleset history | `GET /orgs/{org}/rulesets/{ruleset_id}/history` | Planned | Organization rulesets (section 18.3.1). |
| Get organization ruleset version | `GET /orgs/{org}/rulesets/{ruleset_id}/history/{version_id}` | Planned | Organization rulesets (section 18.3.1). |
| List security manager teams | `GET /orgs/{org}/security-managers` | Planned | Organization sheet > Security: security managers. |
| Remove a security manager team | `DELETE /orgs/{org}/security-managers/teams/{team_slug}` | Planned | Organization sheet > Security: security managers. |
| Add a security manager team | `PUT /orgs/{org}/security-managers/teams/{team_slug}` | Planned | Organization sheet > Security: security managers. |
| Get immutable releases settings for an organization | `GET /orgs/{org}/settings/immutable-releases` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Set immutable releases settings for an organization | `PUT /orgs/{org}/settings/immutable-releases` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List selected repositories for immutable releases enforcement | `GET /orgs/{org}/settings/immutable-releases/repositories` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Set selected repositories for immutable releases enforcement | `PUT /orgs/{org}/settings/immutable-releases/repositories` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Disable a selected repository for immutable releases in an organization | `DELETE /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Enable a selected repository for immutable releases in an organization | `PUT /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List hosted compute network configurations for an organization | `GET /orgs/{org}/settings/network-configurations` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Create a hosted compute network configuration for an organization | `POST /orgs/{org}/settings/network-configurations` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Delete a hosted compute network configuration from an organization | `DELETE /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Get a hosted compute network configuration for an organization | `GET /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Update a hosted compute network configuration for an organization | `PATCH /orgs/{org}/settings/network-configurations/{network_configuration_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Get a hosted compute network settings resource for an organization | `GET /orgs/{org}/settings/network-settings/{network_settings_id}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| Enable or disable a security feature for an organization | `POST /orgs/{org}/{security_product}/{enablement}` | Planned | Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. |
| List organization memberships for the authenticated user | `GET /user/memberships/orgs` | Planned | Organization sheet > Members. |
| Get an organization membership for the authenticated user | `GET /user/memberships/orgs/{org}` | Yes | Properties (Alt+Enter) on Organization |
| Update an organization membership for the authenticated user | `PATCH /user/memberships/orgs/{org}` | Planned | Organization sheet > Members. |
| List organizations for the authenticated user | `GET /user/orgs` | Yes | Navigator: Repositories > Organizations |
| List organizations for a user | `GET /users/{username}/orgs` | Yes | Properties (Alt+Enter) on Person |

#### Packages

27 operations: 4 yes, 23 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get list of conflicting packages during Docker migration for organization | `GET /orgs/{org}/docker/conflicts` | Planned | Repositories > My Packages; Package sheet. |
| List packages for an organization | `GET /orgs/{org}/packages` | Planned | Repositories > My Packages; Package sheet. |
| Delete a package for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}` | Planned | Repositories > My Packages; Package sheet. |
| Get a package for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}` | Planned | Repositories > My Packages; Package sheet. |
| Restore a package for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/restore` | Planned | Repositories > My Packages; Package sheet. |
| List package versions for a package owned by an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions` | Planned | Repositories > My Packages; Package sheet. |
| Delete package version for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Planned | Repositories > My Packages; Package sheet. |
| Get a package version for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Planned | Repositories > My Packages; Package sheet. |
| Restore package version for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Planned | Repositories > My Packages; Package sheet. |
| Get list of conflicting packages during Docker migration for authenticated-user | `GET /user/docker/conflicts` | Planned | Repositories > My Packages; Package sheet. |
| List packages for the authenticated user's namespace | `GET /user/packages` | Yes | Navigator: Repositories > My Packages |
| Delete a package for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}` | Yes | context menu > Delete Package... |
| Get a package for the authenticated user | `GET /user/packages/{package_type}/{package_name}` | Planned | Repositories > My Packages; Package sheet. |
| Restore a package for the authenticated user | `POST /user/packages/{package_type}/{package_name}/restore` | Planned | Repositories > My Packages; Package sheet. |
| List package versions for a package owned by the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions` | Yes | context menu > Delete Package Version... |
| Delete a package version for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | Yes | context menu > Delete Package Version... |
| Get a package version for the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | Planned | Repositories > My Packages; Package sheet. |
| Restore a package version for the authenticated user | `POST /user/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Planned | Repositories > My Packages; Package sheet. |
| Get list of conflicting packages during Docker migration for user | `GET /users/{username}/docker/conflicts` | Planned | Repositories > My Packages; Package sheet. |
| List packages for a user | `GET /users/{username}/packages` | Planned | Repositories > My Packages; Package sheet. |
| Delete a package for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}` | Planned | Repositories > My Packages; Package sheet. |
| Get a package for a user | `GET /users/{username}/packages/{package_type}/{package_name}` | Planned | Repositories > My Packages; Package sheet. |
| Restore a package for a user | `POST /users/{username}/packages/{package_type}/{package_name}/restore` | Planned | Repositories > My Packages; Package sheet. |
| List package versions for a package owned by a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions` | Planned | Repositories > My Packages; Package sheet. |
| Delete package version for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Planned | Repositories > My Packages; Package sheet. |
| Get a package version for a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | Planned | Repositories > My Packages; Package sheet. |
| Restore package version for a user | `POST /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | Planned | Repositories > My Packages; Package sheet. |

#### Pages

12 operations: 3 yes, 9 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Delete a GitHub Pages site | `DELETE /repos/{owner}/{repo}/pages` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Get a GitHub Pages site | `GET /repos/{owner}/{repo}/pages` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| Create a GitHub Pages site | `POST /repos/{owner}/{repo}/pages` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Update information about a GitHub Pages site | `PUT /repos/{owner}/{repo}/pages` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| List GitHub Pages builds | `GET /repos/{owner}/{repo}/pages/builds` | Yes | Navigator: Repository > owner/name > GitHub Pages |
| Request a GitHub Pages build | `POST /repos/{owner}/{repo}/pages/builds` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Get latest Pages build | `GET /repos/{owner}/{repo}/pages/builds/latest` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Get GitHub Pages build | `GET /repos/{owner}/{repo}/pages/builds/{build_id}` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Create a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Get the status of a GitHub Pages deployment | `GET /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Cancel a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}/cancel` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |
| Get a DNS health check for GitHub Pages | `GET /repos/{owner}/{repo}/pages/health` | Planned | Repository > GitHub Pages; Repository sheet > Pages. |

#### Private registries

6 operations: 6 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List private registries for an organization | `GET /orgs/{org}/private-registries` | Planned | Organization sheet > Private Registries (for Dependabot). |
| Create a private registry for an organization | `POST /orgs/{org}/private-registries` | Planned | Organization sheet > Private Registries (for Dependabot). |
| Get private registries public key for an organization | `GET /orgs/{org}/private-registries/public-key` | Planned | Organization sheet > Private Registries (for Dependabot). |
| Delete a private registry for an organization | `DELETE /orgs/{org}/private-registries/{secret_name}` | Planned | Organization sheet > Private Registries (for Dependabot). |
| Get a private registry for an organization | `GET /orgs/{org}/private-registries/{secret_name}` | Planned | Organization sheet > Private Registries (for Dependabot). |
| Update a private registry for an organization | `PATCH /orgs/{org}/private-registries/{secret_name}` | Planned | Organization sheet > Private Registries (for Dependabot). |

#### Projects

26 operations: 26 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List projects for organization | `GET /orgs/{org}/projectsV2` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get project for organization | `GET /orgs/{org}/projectsV2/{project_number}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Create draft item for organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/drafts` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List project fields for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Add a field to an organization-owned project. | `POST /orgs/{org}/projectsV2/{project_number}/fields` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get project field for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields/{field_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List items for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Add item to organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Delete project item for organization | `DELETE /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get an item for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Update project item for organization | `PATCH /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Create a view for an organization-owned project | `POST /orgs/{org}/projectsV2/{project_number}/views` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List items for an organization project view | `GET /orgs/{org}/projectsV2/{project_number}/views/{view_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Create draft item for user owned project | `POST /user/{user_id}/projectsV2/{project_number}/drafts` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Create a view for a user-owned project | `POST /users/{user_id}/projectsV2/{project_number}/views` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List projects for user | `GET /users/{username}/projectsV2` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get project for user | `GET /users/{username}/projectsV2/{project_number}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List project fields for user | `GET /users/{username}/projectsV2/{project_number}/fields` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Add field to user owned project | `POST /users/{username}/projectsV2/{project_number}/fields` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get project field for user | `GET /users/{username}/projectsV2/{project_number}/fields/{field_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List items for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Add item to user owned project | `POST /users/{username}/projectsV2/{project_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Delete project item for user | `DELETE /users/{username}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Get an item for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| Update project item for user | `PATCH /users/{username}/projectsV2/{project_number}/items/{item_id}` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |
| List items for a user project view | `GET /users/{username}/projectsV2/{project_number}/views/{view_number}/items` | Planned | Projects; Project, Project item, field and view sheets (section 16.6). |

#### Pull requests

39 operations: 12 yes, 27 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Disable Agent Merge for a pull request | `DELETE /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Get Agent Merge configuration for a pull request | `GET /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Update Agent Merge configuration for a pull request | `PUT /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| List pull requests | `GET /repos/{owner}/{repo}/pulls` | Yes | Navigator: Repository > owner/name > Pull Requests |
| Create a pull request | `POST /repos/{owner}/{repo}/pulls` | Yes | File > New Here... (Ctrl+N) |
| List review comments in a repository | `GET /repos/{owner}/{repo}/pulls/comments` | Planned | Review thread sheet; PR review. |
| Delete a review comment for a pull request | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Planned | Review thread sheet; PR review. |
| Get a review comment for a pull request | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Planned | Review thread sheet; PR review. |
| Update a review comment for a pull request | `PATCH /repos/{owner}/{repo}/pulls/comments/{comment_id}` | Planned | Review thread sheet; PR review. |
| Get a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}` | Yes | Properties (Alt+Enter) on Pull Request |
| Update a pull request | `PATCH /repos/{owner}/{repo}/pulls/{pull_number}` | Yes | Properties (Alt+Enter) on Pull Request: Into branch |
| List review comments on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/comments` | Planned | Review thread sheet; PR review. |
| Create a review comment for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments` | Yes | context menu > Review... |
| Create a reply for a review comment | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies` | Planned | Review thread sheet; PR review. |
| List commits on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Request a Copilot code review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/copilot-code-review` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| List pull requests files | `GET /repos/{owner}/{repo}/pulls/{pull_number}/files` | Yes | Item > File Differences... (Ctrl+Shift+D) |
| Check if a pull request has been merged | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Merge a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge` | Yes | Item > Merge... (Ctrl+Shift+Enter) |
| Merge a pull request asynchronously | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge-async` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Get the result of an asynchronous merge | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge-async/{uuid}` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Remove requested reviewers from a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Get all requested reviewers for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Request reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| Rerequest reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers/rerequest` | Planned | Pull request > Reviews: reviewers. |
| List reviews for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | Yes | context menu > Review... |
| Create a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | Yes | context menu > Review... |
| Delete a pending review for a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Planned | Pull request > Reviews; Review sheet. |
| Get a review for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Planned | Pull request > Reviews; Review sheet. |
| Update a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | Planned | Pull request > Reviews; Review sheet. |
| List comments for a pull request review | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments` | Planned | Pull request > Reviews; Review sheet. |
| Dismiss a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals` | Planned | Pull request > Reviews; Review sheet. |
| Submit a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events` | Planned | Pull request > Reviews; Review sheet. |
| Update a pull request branch | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/update-branch` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| List pull request stacks | `GET /repos/{owner}/{repo}/stacks` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Create a pull request stack | `POST /repos/{owner}/{repo}/stacks` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Get a pull request stack | `GET /repos/{owner}/{repo}/stacks/{stack_number}` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Add pull requests to a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/add` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |
| Remove pull requests from a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/unstack` | Planned | Pull request sheet; PR review; Review and Review thread sheets. |

#### Rate limit

1 operations: 1 yes.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get rate limit status for the authenticated user | `GET /rate_limit` | Yes | Account > GitHub API Rate Limit (Ctrl+Shift+L) |

#### Reactions

15 operations: 3 yes, 12 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List reactions for a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Create reaction for a commit comment | `POST /repos/{owner}/{repo}/comments/{comment_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Delete a commit comment reaction | `DELETE /repos/{owner}/{repo}/comments/{comment_id}/reactions/{reaction_id}` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| List reactions for an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Create reaction for an issue comment | `POST /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Delete an issue comment reaction | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions/{reaction_id}` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| List reactions for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/reactions` | Yes | context menu > React... |
| Create reaction for an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Delete an issue reaction | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/reactions/{reaction_id}` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| List reactions for a pull request review comment | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | Yes | context menu > React... |
| Create reaction for a pull request review comment | `POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Delete a pull request comment reaction | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions/{reaction_id}` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| List reactions for a release | `GET /repos/{owner}/{repo}/releases/{release_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Create reaction for a release | `POST /repos/{owner}/{repo}/releases/{release_id}/reactions` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |
| Delete a release reaction | `DELETE /repos/{owner}/{repo}/releases/{release_id}/reactions/{reaction_id}` | Planned | You page on issues, pull requests, comments, discussions, releases (section 16.7). |

#### Releases

13 operations: 10 yes, 3 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List releases | `GET /repos/{owner}/{repo}/releases` | Yes | Navigator: Repository > owner/name > Releases |
| Create a release | `POST /repos/{owner}/{repo}/releases` | Yes | editor GitHub menu > Create Release... |
| Delete a release asset | `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Delete Asset... |
| Get a release asset | `GET /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Edit Release... |
| Update a release asset | `PATCH /repos/{owner}/{repo}/releases/assets/{asset_id}` | Yes | context menu > Edit Release... |
| Generate release notes content for a release | `POST /repos/{owner}/{repo}/releases/generate-notes` | Planned | Repository > Releases; Release and Release asset sheets. |
| Get the latest release | `GET /repos/{owner}/{repo}/releases/latest` | Yes | context menu > Edit Release... |
| Get a release by tag name | `GET /repos/{owner}/{repo}/releases/tags/{tag}` | Yes | context menu > Edit Release... |
| Delete a release | `DELETE /repos/{owner}/{repo}/releases/{release_id}` | Planned | Repository > Releases; Release and Release asset sheets. |
| Get a release | `GET /repos/{owner}/{repo}/releases/{release_id}` | Yes | context menu > Edit Release... |
| Update a release | `PATCH /repos/{owner}/{repo}/releases/{release_id}` | Yes | context menu > Edit Release... |
| List release assets | `GET /repos/{owner}/{repo}/releases/{release_id}/assets` | Planned | Repository > Releases; Release and Release asset sheets. |
| Upload a release asset | `POST /repos/{owner}/{repo}/releases/{release_id}/assets` | Yes | context menu > Upload Asset... |

#### Repositories

74 operations: 39 yes, 35 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List organization repositories | `GET /orgs/{org}/repos` | Yes | Navigator: Organization > organization > Repositories |
| Create an organization repository | `POST /orgs/{org}/repos` | Yes | editor GitHub menu > Create Repository... |
| Delete a repository | `DELETE /repos/{owner}/{repo}` | Yes | Repository > Repository Actions... (Ctrl+Shift+G) |
| Get a repository | `GET /repos/{owner}/{repo}` | Yes | Navigator: Repository > owner/name |
| Update a repository | `PATCH /repos/{owner}/{repo}` | Yes | editor GitHub menu > Rename Repository... |
| List repository activities | `GET /repos/{owner}/{repo}/activity` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| Create an attestation | `POST /repos/{owner}/{repo}/attestations` | Planned | Repository > Security > Attestations (read). |
| List attestations | `GET /repos/{owner}/{repo}/attestations/{subject_digest}` | Planned | Repository > Security > Attestations (read). |
| Get all autolinks of a repository | `GET /repos/{owner}/{repo}/autolinks` | Yes | Properties (Alt+Enter) on Repository |
| Create an autolink reference for a repository | `POST /repos/{owner}/{repo}/autolinks` | Planned | Repository sheet > Autolinks. |
| Delete an autolink reference from a repository | `DELETE /repos/{owner}/{repo}/autolinks/{autolink_id}` | Planned | Repository sheet > Autolinks. |
| Get an autolink reference of a repository | `GET /repos/{owner}/{repo}/autolinks/{autolink_id}` | Planned | Repository sheet > Autolinks. |
| Disable Dependabot security updates | `DELETE /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository: Dependabot security updates |
| Check if Dependabot security updates are enabled for a repository | `GET /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository |
| Enable Dependabot security updates | `PUT /repos/{owner}/{repo}/automated-security-fixes` | Yes | Properties (Alt+Enter) on Repository: Dependabot security updates |
| List CODEOWNERS errors | `GET /repos/{owner}/{repo}/codeowners/errors` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| Delete a file | `DELETE /repos/{owner}/{repo}/contents/{path}` | Yes | context menu > Open Template... |
| Get repository content | `GET /repos/{owner}/{repo}/contents/{path}` | Yes | Navigator: Repository > owner/name > Code > Files |
| Create or update file contents | `PUT /repos/{owner}/{repo}/contents/{path}` | Yes | Navigator: Repository > owner/name > Code > Files |
| List repository contributors | `GET /repos/{owner}/{repo}/contributors` | Yes | Navigator: Repository > owner/name > People > Contributors and People |
| Create a repository dispatch event | `POST /repos/{owner}/{repo}/dispatches` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List forks | `GET /repos/{owner}/{repo}/forks` | Yes | Navigator: Repository > owner/name > People > Forks |
| Create a fork | `POST /repos/{owner}/{repo}/forks` | Yes | editor GitHub menu > Fork Repository... |
| Get the hash algorithm for a repository | `GET /repos/{owner}/{repo}/hash-algorithm` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List repository webhooks | `GET /repos/{owner}/{repo}/hooks` | Yes | Properties (Alt+Enter) on Repository |
| Create a repository webhook | `POST /repos/{owner}/{repo}/hooks` | Planned | Repository sheet > Webhooks. |
| Delete a repository webhook | `DELETE /repos/{owner}/{repo}/hooks/{hook_id}` | Planned | Repository sheet > Webhooks. |
| Get a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}` | Yes | Properties (Alt+Enter) on Webhook |
| Update a repository webhook | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}` | Yes | Properties (Alt+Enter) on Webhook: Active |
| Get a webhook configuration for a repository | `GET /repos/{owner}/{repo}/hooks/{hook_id}/config` | Planned | Repository sheet > Webhooks. |
| Update a webhook configuration for a repository | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}/config` | Planned | Repository sheet > Webhooks. |
| List deliveries for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries` | Planned | Repository sheet > Webhooks. |
| Get a delivery for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}` | Planned | Repository sheet > Webhooks. |
| Redeliver a delivery for a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | Planned | Repository sheet > Webhooks. |
| Ping a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/pings` | Planned | Repository sheet > Webhooks. |
| Test the push repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/tests` | Planned | Repository sheet > Webhooks. |
| Disable immutable releases | `DELETE /repos/{owner}/{repo}/immutable-releases` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| Check if immutable releases are enabled for a repository | `GET /repos/{owner}/{repo}/immutable-releases` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| Enable immutable releases | `PUT /repos/{owner}/{repo}/immutable-releases` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List issue types for a repository | `GET /repos/{owner}/{repo}/issue-types` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List repository languages | `GET /repos/{owner}/{repo}/languages` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List planning statuses for a repository | `GET /repos/{owner}/{repo}/planning-statuses` | Planned | Repository > Issues > Planning statuses (issue sheet choices) |
| Disable private vulnerability reporting for a repository | `DELETE /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository: Private vulnerability reporting |
| Check if private vulnerability reporting is enabled for a repository | `GET /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository |
| Enable private vulnerability reporting for a repository | `PUT /repos/{owner}/{repo}/private-vulnerability-reporting` | Yes | Properties (Alt+Enter) on Repository: Private vulnerability reporting |
| Get all custom property values for a repository | `GET /repos/{owner}/{repo}/properties/values` | Planned | Repository sheet > General: Custom Properties. |
| Create or update custom property values for a repository | `PATCH /repos/{owner}/{repo}/properties/values` | Planned | Repository sheet > General: Custom Properties. |
| Get a repository README | `GET /repos/{owner}/{repo}/readme` | Yes | Navigator: Repository > owner/name > Overview |
| Get a repository README for a directory | `GET /repos/{owner}/{repo}/readme/{dir}` | Planned | File and folder sheets; Commit to GitHub. |
| Get rules for a branch | `GET /repos/{owner}/{repo}/rules/branches/{branch}` | Yes | Properties (Alt+Enter) on Branch |
| Get all repository rulesets | `GET /repos/{owner}/{repo}/rulesets` | Yes | Navigator: Repository > owner/name > Settings > Branch Protection |
| Create a repository ruleset | `POST /repos/{owner}/{repo}/rulesets` | Yes | context menu > Add to Missing... |
| List repository rule suites | `GET /repos/{owner}/{repo}/rulesets/rule-suites` | Planned | Ruleset sheet > History (rule insights). |
| Get a repository rule suite | `GET /repos/{owner}/{repo}/rulesets/rule-suites/{rule_suite_id}` | Planned | Ruleset sheet > History (rule insights). |
| Delete a repository ruleset | `DELETE /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | context menu > Promote to Organization... |
| Get a repository ruleset | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | Properties (Alt+Enter) on Ruleset |
| Update a repository ruleset | `PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}` | Yes | Properties (Alt+Enter) on Ruleset: Approvals needed |
| Get repository ruleset history | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history` | Planned | Ruleset sheet (section 18.3.1). |
| Get repository ruleset version | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history/{version_id}` | Planned | Ruleset sheet (section 18.3.1). |
| List repository tags | `GET /repos/{owner}/{repo}/tags` | Yes | Navigator: Repository > owner/name > Code > Tags |
| Download a repository archive (tar) | `GET /repos/{owner}/{repo}/tarball/{ref}` | Planned | File and folder sheets; Commit to GitHub. |
| List repository teams | `GET /repos/{owner}/{repo}/teams` | Yes | Navigator: Repository > owner/name > People > Collaborators and Team Access |
| Get all repository topics | `GET /repos/{owner}/{repo}/topics` | Yes | Properties (Alt+Enter) on Repository: Topics |
| Replace all repository topics | `PUT /repos/{owner}/{repo}/topics` | Yes | Properties (Alt+Enter) on Repository: Topics |
| Transfer a repository | `POST /repos/{owner}/{repo}/transfer` | Yes | Repository > Transfer Repository... (Ctrl+Alt+T) |
| Disable vulnerability alerts | `DELETE /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository: Dependabot alerts |
| Check if vulnerability alerts are enabled for a repository | `GET /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository |
| Enable vulnerability alerts | `PUT /repos/{owner}/{repo}/vulnerability-alerts` | Yes | Properties (Alt+Enter) on Repository: Dependabot alerts |
| Download a repository archive (zip) | `GET /repos/{owner}/{repo}/zipball/{ref}` | Planned | File and folder sheets; Commit to GitHub. |
| Create a repository using a template | `POST /repos/{template_owner}/{template_repo}/generate` | Yes | Repository > Repository Actions... (Ctrl+Shift+G) |
| List public repositories | `GET /repositories` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |
| List repositories for the authenticated user | `GET /user/repos` | Yes | Navigator: Repositories > My Repositories |
| Create a repository for the authenticated user | `POST /user/repos` | Yes | editor GitHub menu > Create Repository... |
| List repositories for a user | `GET /users/{username}/repos` | Planned | Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. |

#### Search

7 operations: 4 yes, 3 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Search code | `GET /search/code` | Yes | Navigator: Search > Code |
| Search commits | `GET /search/commits` | Yes | Navigator: Search > Commits |
| Search issues and pull requests | `GET /search/issues` | Yes | Navigator: Search > Issues and Pull Requests |
| Search labels | `GET /search/labels` | Planned | Search branch; filter box (section 17). |
| Search repositories | `GET /search/repositories` | Yes | Navigator: Search > Repositories |
| Search topics | `GET /search/topics` | Planned | Search branch; filter box (section 17). |
| Search users | `GET /search/users` | Planned | Search branch; filter box (section 17). |

#### Secret scanning

17 operations: 2 yes, 15 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List secret scanning alerts for an organization | `GET /orgs/{org}/secret-scanning/alerts` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Bulk delete organization custom patterns | `DELETE /orgs/{org}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| List organization custom patterns | `GET /orgs/{org}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Bulk create organization custom patterns | `POST /orgs/{org}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Update an organization custom pattern | `PATCH /orgs/{org}/secret-scanning/custom-patterns/{pattern_id}` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| List organization pattern configurations | `GET /orgs/{org}/secret-scanning/pattern-configurations` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Update organization pattern configurations | `PATCH /orgs/{org}/secret-scanning/pattern-configurations` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| List secret scanning alerts for a repository | `GET /repos/{owner}/{repo}/secret-scanning/alerts` | Yes | Navigator: Repository > owner/name > Security > Alerts |
| Get a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Update a secret scanning alert | `PATCH /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | Yes | context menu > Dismiss or Reopen Alert... |
| List locations for a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}/locations` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Bulk delete repository custom patterns | `DELETE /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| List repository custom patterns | `GET /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Bulk create repository custom patterns | `POST /repos/{owner}/{repo}/secret-scanning/custom-patterns` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Update a repository custom pattern | `PATCH /repos/{owner}/{repo}/secret-scanning/custom-patterns/{pattern_id}` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Create a push protection bypass | `POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |
| Get secret scanning scan history for a repository | `GET /repos/{owner}/{repo}/secret-scanning/scan-history` | Planned | Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). |

#### Security advisories

14 operations: 14 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List global security advisories | `GET /advisories` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Get a global security advisory | `GET /advisories/{ghsa_id}` | Planned | Repository > Security > Advisories; Advisory sheet. |
| List repository security advisories for an organization | `GET /orgs/{org}/security-advisories` | Planned | Repository > Security > Advisories; Advisory sheet. |
| List repository security advisories | `GET /repos/{owner}/{repo}/security-advisories` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Create a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Privately report a security vulnerability | `POST /repos/{owner}/{repo}/security-advisories/reports` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Get a repository security advisory | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Update a repository security advisory | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | Planned | Repository > Security > Advisories; Advisory sheet. |
| List repository security advisory comments | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Create a repository advisory comment | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Get a repository advisory comment | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Update a repository advisory comment | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Request a CVE for a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/cve` | Planned | Repository > Security > Advisories; Advisory sheet. |
| Create a temporary private fork | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/forks` | Planned | Repository > Security > Advisories; Advisory sheet. |

#### Teams

32 operations: 13 yes, 3 planned, 16 left to github.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| List teams | `GET /orgs/{org}/teams` | Yes | Navigator: Organization > organization > Teams |
| Create a team | `POST /orgs/{org}/teams` | Planned | Team sheet; Organization sheet > Teams. |
| Delete a team | `DELETE /orgs/{org}/teams/{team_slug}` | Planned | Team sheet; Organization sheet > Teams. |
| Get a team by name | `GET /orgs/{org}/teams/{team_slug}` | Yes | Properties (Alt+Enter) on Team |
| Update a team | `PATCH /orgs/{org}/teams/{team_slug}` | Yes | Properties (Alt+Enter) on Team: Description |
| List pending team invitations | `GET /orgs/{org}/teams/{team_slug}/invitations` | Planned | Team sheet > Members. |
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

55 operations: 10 yes, 45 planned.

| Operation | Call | Can QUILL do it? | Where, or why |
| --- | --- | --- | --- |
| Get the authenticated user | `GET /user` | Yes | View > Say Account (Alt+9) |
| Update the authenticated user | `PATCH /user` | Yes | Properties (Alt+Enter) on Person: Bio |
| List users blocked by the authenticated user | `GET /user/blocks` | Planned | Person > You: Block (section 16.7). |
| Unblock a user | `DELETE /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person: Blocked |
| Check if a user is blocked by the authenticated user | `GET /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person |
| Block a user | `PUT /user/blocks/{username}` | Yes | Properties (Alt+Enter) on Person: Blocked |
| Set primary email visibility for the authenticated user | `PATCH /user/email/visibility` | Planned | Account > Profile and Status: Emails. |
| Delete an email address for the authenticated user | `DELETE /user/emails` | Planned | Account > Profile and Status: Emails. |
| List email addresses for the authenticated user | `GET /user/emails` | Planned | Account > Profile and Status: Emails. |
| Add an email address for the authenticated user | `POST /user/emails` | Planned | Account > Profile and Status: Emails. |
| List followers of the authenticated user | `GET /user/followers` | Planned | Person > You: Follow (section 16.7). |
| List the people the authenticated user follows | `GET /user/following` | Planned | Person > You: Follow (section 16.7). |
| Unfollow a user | `DELETE /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| Check if a person is followed by the authenticated user | `GET /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| Follow a user | `PUT /user/following/{username}` | Yes | context menu > Follow or Unfollow |
| List GPG keys for the authenticated user | `GET /user/gpg_keys` | Planned | Account > Keys. |
| Create a GPG key for the authenticated user | `POST /user/gpg_keys` | Planned | Account > Keys. |
| Delete a GPG key for the authenticated user | `DELETE /user/gpg_keys/{gpg_key_id}` | Planned | Account > Keys. |
| Get a GPG key for the authenticated user | `GET /user/gpg_keys/{gpg_key_id}` | Planned | Account > Keys. |
| List issue fields | `GET /user/issue-fields` | Planned | Account > Issue Fields (fields for your own repositories) |
| Create an issue field | `POST /user/issue-fields` | Planned | Account > Issue Fields (fields for your own repositories) |
| Delete an issue field | `DELETE /user/issue-fields/{issue_field_id}` | Planned | Account > Issue Fields (fields for your own repositories) |
| Update an issue field | `PATCH /user/issue-fields/{issue_field_id}` | Planned | Account > Issue Fields (fields for your own repositories) |
| List issue types | `GET /user/issue-types` | Planned | Account > Issue Types (types for your own repositories) |
| Create an issue type | `POST /user/issue-types` | Planned | Account > Issue Types (types for your own repositories) |
| Delete an issue type | `DELETE /user/issue-types/{issue_type_id}` | Planned | Account > Issue Types (types for your own repositories) |
| Update an issue type | `PUT /user/issue-types/{issue_type_id}` | Planned | Account > Issue Types (types for your own repositories) |
| List public SSH keys for the authenticated user | `GET /user/keys` | Planned | Account > Keys. |
| Create a public SSH key for the authenticated user | `POST /user/keys` | Planned | Account > Keys. |
| Delete a public SSH key for the authenticated user | `DELETE /user/keys/{key_id}` | Planned | Account > Keys. |
| Get a public SSH key for the authenticated user | `GET /user/keys/{key_id}` | Planned | Account > Keys. |
| List public email addresses for the authenticated user | `GET /user/public_emails` | Planned | Account > Profile and Status: Emails. |
| Delete social accounts for the authenticated user | `DELETE /user/social_accounts` | Planned | Account > Profile and Status: Social accounts. |
| List social accounts for the authenticated user | `GET /user/social_accounts` | Planned | Account > Profile and Status: Social accounts. |
| Add social accounts for the authenticated user | `POST /user/social_accounts` | Planned | Account > Profile and Status: Social accounts. |
| List SSH signing keys for the authenticated user | `GET /user/ssh_signing_keys` | Planned | Account > Keys. |
| Create a SSH signing key for the authenticated user | `POST /user/ssh_signing_keys` | Planned | Account > Keys. |
| Delete an SSH signing key for the authenticated user | `DELETE /user/ssh_signing_keys/{ssh_signing_key_id}` | Planned | Account > Keys. |
| Get an SSH signing key for the authenticated user | `GET /user/ssh_signing_keys/{ssh_signing_key_id}` | Planned | Account > Keys. |
| Get a user using their ID | `GET /user/{account_id}` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| List users | `GET /users` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| Get a user | `GET /users/{username}` | Yes | Properties (Alt+Enter) on Person |
| List attestations by bulk subject digests | `POST /users/{username}/attestations/bulk-list` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| Delete attestations in bulk | `POST /users/{username}/attestations/delete-request` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| Delete attestations by subject digest | `DELETE /users/{username}/attestations/digest/{subject_digest}` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| Delete attestations by ID | `DELETE /users/{username}/attestations/{attestation_id}` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| List attestations | `GET /users/{username}/attestations/{subject_digest}` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| List followers of a user | `GET /users/{username}/followers` | Planned | Person > You: Follow (section 16.7). |
| List the people a user follows | `GET /users/{username}/following` | Planned | Person > You: Follow (section 16.7). |
| Check if a user follows another user | `GET /users/{username}/following/{target_user}` | Yes | Properties (Alt+Enter) on Person |
| List GPG keys for a user | `GET /users/{username}/gpg_keys` | Planned | Account > Keys. |
| Get contextual information for a user | `GET /users/{username}/hovercard` | Planned | Person sheet; Account > Profile and Status, Keys, Emails; People branch. |
| List public keys for a user | `GET /users/{username}/keys` | Planned | Account > Keys. |
| List social accounts for a user | `GET /users/{username}/social_accounts` | Planned | Account > Profile and Status: Social accounts. |
| List SSH signing keys for a user | `GET /users/{username}/ssh_signing_keys` | Planned | Account > Keys. |

### GraphQL mutations, by category

#### GraphQL: Activity

4 mutations: 1 yes, 3 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addStar` | Planned | Repository > You (star, watch) |
| `removeStar` | Planned | Repository > You (star, watch) |
| `updateNotificationRestrictionSetting` | Planned | Repository > You (star, watch) |
| `updateSubscription` | Yes | Properties (Alt+Enter) on Issue: Subscribed |

#### GraphQL: Branches

4 mutations: 4 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createBranchProtectionRule` | Planned | Branch sheet > Protection |
| `deleteBranchProtectionRule` | Planned | Branch sheet > Protection |
| `mergeBranch` | Planned | Branch sheet > Protection |
| `updateBranchProtectionRule` | Planned | Branch sheet > Protection |

#### GraphQL: Checks

5 mutations: 2 planned, 3 left to github.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createCheckRun` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `createCheckSuite` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `rerequestCheckSuite` | Planned | Pull request > Checks |
| `updateCheckRun` | Left to GitHub | Only a GitHub App can create or update check runs and suites. Pull request > Checks (read). |
| `updateCheckSuitePreferences` | Planned | Pull request > Checks |

#### GraphQL: Commits

1 mutations: 1 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `createCommitOnBranch` | Planned | Repository > Code |

#### GraphQL: Copilot

5 mutations: 5 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `updateEnterpriseCopilotCodeReviewPolicy` | Planned | Repository and Organization sheets > Copilot |
| `updateOrganizationCopilotCodeReviewPolicy` | Planned | Repository and Organization sheets > Copilot |
| `updateOrganizationCopilotCodeReviewRunnerConfiguration` | Planned | Repository and Organization sheets > Copilot |
| `updateOrganizationCopilotCodeReviewSettings` | Planned | Repository and Organization sheets > Copilot |
| `updateRepositoryCopilotCodeReviewSettings` | Planned | Repository and Organization sheets > Copilot |

#### GraphQL: Dependabot

1 mutations: 1 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `dismissRepositoryVulnerabilityAlert` | Planned | Repository > Security > Alerts |

#### GraphQL: Deployments

10 mutations: 10 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `approveDeployments` | Planned | Repository > Deployments; Environment sheet |
| `createDeployment` | Planned | Repository > Deployments; Environment sheet |
| `createDeploymentStatus` | Planned | Repository > Deployments; Environment sheet |
| `createEnvironment` | Planned | Repository > Deployments; Environment sheet |
| `deleteDeployment` | Planned | Repository > Deployments; Environment sheet |
| `deleteEnvironment` | Planned | Repository > Deployments; Environment sheet |
| `pinEnvironment` | Planned | Repository > Deployments; Environment sheet |
| `rejectDeployments` | Planned | Repository > Deployments; Environment sheet |
| `reorderEnvironment` | Planned | Repository > Deployments; Environment sheet |
| `updateEnvironment` | Planned | Repository > Deployments; Environment sheet |

#### GraphQL: Discussions

13 mutations: 5 yes, 8 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addDiscussionComment` | Yes | context menu > Open Discussion Thread |
| `addDiscussionPollVote` | Planned | Repository > Discussions; Discussion sheet |
| `addUpvote` | Planned | Repository > Discussions; Discussion sheet |
| `closeDiscussion` | Planned | Repository > Discussions; Discussion sheet |
| `createDiscussion` | Yes | Navigator: Repository > owner/name > Discussions |
| `deleteDiscussion` | Planned | Repository > Discussions; Discussion sheet |
| `deleteDiscussionComment` | Planned | Repository > Discussions; Discussion sheet |
| `markDiscussionCommentAsAnswer` | Yes | context menu > Open Discussion Thread |
| `removeUpvote` | Planned | Repository > Discussions; Discussion sheet |
| `reopenDiscussion` | Planned | Repository > Discussions; Discussion sheet |
| `unmarkDiscussionCommentAsAnswer` | Yes | context menu > Open Discussion Thread |
| `updateDiscussion` | Yes | Properties (Alt+Enter) on Discussion: Title |
| `updateDiscussionComment` | Planned | Repository > Discussions; Discussion sheet |

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

51 mutations: 13 yes, 38 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addAssigneesToAssignable` | Planned | Issue sheet; Item menu |
| `addBlockedBy` | Yes | context menu > Reorder Sub-issues... |
| `addCloseIssueReferences` | Planned | Issue sheet; Item menu |
| `addComment` | Planned | Issue sheet; Item menu |
| `addLabelsToLabelable` | Planned | Issue sheet; Item menu |
| `addRelatesTo` | Planned | Issue sheet; Item menu |
| `addSubIssue` | Yes | context menu > Reorder Sub-issues... |
| `applyPendingIssueSuggestions` | Planned | Issue sheet; Item menu |
| `clearLabelsFromLabelable` | Planned | Issue sheet; Item menu |
| `closeIssue` | Yes | context menu > Close or Reopen... |
| `createIssue` | Planned | Issue sheet; Item menu |
| `createIssueField` | Planned | Issue sheet; Item menu |
| `createIssueFieldValue` | Planned | Issue sheet; Item menu |
| `createIssueType` | Planned | Issue sheet; Item menu |
| `createLabel` | Planned | Issue sheet; Item menu |
| `createLinkedBranch` | Yes | context menu > Create Branch for This Issue... |
| `deleteIssue` | Planned | Issue sheet; Item menu |
| `deleteIssueComment` | Planned | Issue sheet; Item menu |
| `deleteIssueField` | Planned | Issue sheet; Item menu |
| `deleteIssueFieldValue` | Planned | Issue sheet; Item menu |
| `deleteIssueType` | Planned | Issue sheet; Item menu |
| `deleteLabel` | Planned | Issue sheet; Item menu |
| `deleteLinkedBranch` | Planned | Issue sheet; Item menu |
| `lockLockable` | Planned | Issue sheet; Item menu |
| `minimizeComment` | Yes | context menu > View Timeline... |
| `pinIssue` | Yes | context menu > Pin or Unpin Issue |
| `pinIssueComment` | Planned | Issue sheet; Item menu |
| `rejectPendingIssueSuggestions` | Planned | Issue sheet; Item menu |
| `removeAssigneesFromAssignable` | Planned | Issue sheet; Item menu |
| `removeBlockedBy` | Yes | context menu > Reorder Sub-issues... |
| `removeCloseIssueReferences` | Planned | Issue sheet; Item menu |
| `removeLabelsFromLabelable` | Planned | Issue sheet; Item menu |
| `removeRelatesTo` | Planned | Issue sheet; Item menu |
| `removeSubIssue` | Yes | context menu > Reorder Sub-issues... |
| `reopenIssue` | Planned | Issue sheet; Item menu |
| `replaceActorsForAssignable` | Yes | Item > Assign to Copilot... (Ctrl+Shift+A) |
| `reprioritizeSubIssue` | Planned | Issue sheet; Item menu |
| `setIssueFieldValue` | Planned | Issue sheet; Item menu |
| `transferIssue` | Yes | context menu > Transfer Issue... |
| `unlockLockable` | Planned | Issue sheet; Item menu |
| `unmarkIssueAsDuplicate` | Planned | Issue sheet; Item menu |
| `unminimizeComment` | Yes | context menu > View Timeline... |
| `unpinIssue` | Yes | context menu > Pin or Unpin Issue |
| `unpinIssueComment` | Planned | Issue sheet; Item menu |
| `updateIssue` | Planned | Issue sheet; Item menu |
| `updateIssueComment` | Planned | Issue sheet; Item menu |
| `updateIssueField` | Planned | Issue sheet; Item menu |
| `updateIssueFieldValue` | Planned | Issue sheet; Item menu |
| `updateIssueIssueType` | Yes | context menu > Set Issue Type... |
| `updateIssueType` | Planned | Issue sheet; Item menu |
| `updateLabel` | Planned | Issue sheet; Item menu |

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

11 mutations: 11 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addVerifiableDomain` | Planned | Organization sheet |
| `approveVerifiableDomain` | Planned | Organization sheet |
| `deleteVerifiableDomain` | Planned | Organization sheet |
| `followOrganization` | Planned | Organization sheet |
| `regenerateVerifiableDomainToken` | Planned | Organization sheet |
| `removeOutsideCollaborator` | Planned | Organization sheet |
| `setOrganizationInteractionLimit` | Planned | Organization sheet |
| `unfollowOrganization` | Planned | Organization sheet |
| `updateOrganizationAllowPrivateRepositoryForkingSetting` | Planned | Organization sheet |
| `updateOrganizationWebCommitSignoffSetting` | Planned | Organization sheet |
| `verifyVerifiableDomain` | Planned | Organization sheet |

#### GraphQL: Packages

1 mutations: 1 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `deletePackageVersion` | Planned | Repository > Packages |

#### GraphQL: Projects

32 mutations: 8 yes, 24 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addProjectV2DraftIssue` | Planned | Projects; Project sheet |
| `addProjectV2ItemById` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `archiveProjectV2Item` | Yes | Properties (Alt+Enter) on Project |
| `clearProjectV2ItemFieldValue` | Yes | Properties (Alt+Enter) on Project |
| `convertProjectV2DraftIssueItemToIssue` | Planned | Projects; Project sheet |
| `copyProjectV2` | Planned | Projects; Project sheet |
| `createProjectV2` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `createProjectV2Field` | Planned | Projects; Project sheet |
| `createProjectV2IssueField` | Planned | Projects; Project sheet |
| `createProjectV2StatusUpdate` | Planned | Projects; Project sheet |
| `createProjectV2View` | Planned | Projects; Project sheet |
| `deleteProjectV2` | Planned | Projects; Project sheet |
| `deleteProjectV2Field` | Planned | Projects; Project sheet |
| `deleteProjectV2Item` | Yes | Properties (Alt+Enter) on Issue: Projects |
| `deleteProjectV2StatusUpdate` | Planned | Projects; Project sheet |
| `deleteProjectV2View` | Planned | Projects; Project sheet |
| `deleteProjectV2Workflow` | Planned | Projects; Project sheet |
| `linkProjectV2ToRepository` | Planned | Projects; Project sheet |
| `linkProjectV2ToTeam` | Planned | Projects; Project sheet |
| `markProjectV2AsTemplate` | Planned | Projects; Project sheet |
| `unarchiveProjectV2Item` | Yes | Properties (Alt+Enter) on Project |
| `unlinkProjectV2FromRepository` | Planned | Projects; Project sheet |
| `unlinkProjectV2FromTeam` | Planned | Projects; Project sheet |
| `unmarkProjectV2AsTemplate` | Planned | Projects; Project sheet |
| `updateProjectV2` | Yes | Properties (Alt+Enter) on Project: Title |
| `updateProjectV2Collaborators` | Planned | Projects; Project sheet |
| `updateProjectV2DraftIssue` | Planned | Projects; Project sheet |
| `updateProjectV2Field` | Planned | Projects; Project sheet |
| `updateProjectV2ItemFieldValue` | Yes | Properties (Alt+Enter) on Project |
| `updateProjectV2ItemPosition` | Planned | Projects; Project sheet |
| `updateProjectV2StatusUpdate` | Planned | Projects; Project sheet |
| `updateProjectV2View` | Planned | Projects; Project sheet |

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

36 mutations: 12 yes, 24 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addPullRequestCreationCapBypassUsers` | Planned | Pull request sheet; Item menu |
| `addPullRequestReview` | Planned | Pull request sheet; Item menu |
| `addPullRequestReviewComment` | Planned | Pull request sheet; Item menu |
| `addPullRequestReviewThread` | Planned | Pull request sheet; Item menu |
| `addPullRequestReviewThreadReply` | Planned | Pull request sheet; Item menu |
| `archivePullRequest` | Planned | Pull request sheet; Item menu |
| `closePullRequest` | Planned | Pull request sheet; Item menu |
| `convertPullRequestToDraft` | Yes | Properties (Alt+Enter) on Pull Request: Draft |
| `createPullRequest` | Planned | Pull request sheet; Item menu |
| `deletePullRequestReview` | Planned | Pull request sheet; Item menu |
| `deletePullRequestReviewComment` | Planned | Pull request sheet; Item menu |
| `dequeuePullRequest` | Yes | context menu > Add to or Remove from Merge Queue... |
| `disablePullRequestAutoMerge` | Yes | Properties (Alt+Enter) on Pull Request: Merge automatically when ready |
| `dismissPullRequestReview` | Planned | Pull request sheet; Item menu |
| `enablePullRequestAutoMerge` | Yes | Properties (Alt+Enter) on Pull Request: Merge automatically when ready |
| `enqueuePullRequest` | Yes | context menu > Add to or Remove from Merge Queue... |
| `markFileAsViewed` | Yes | context menu > Review... |
| `markPullRequestReadyForReview` | Yes | Properties (Alt+Enter) on Pull Request: Draft |
| `mergePullRequest` | Planned | Pull request sheet; Item menu |
| `removePullRequestCreationCapBypassUsers` | Planned | Pull request sheet; Item menu |
| `reopenPullRequest` | Planned | Pull request sheet; Item menu |
| `requestCopilotCodeReview` | Planned | Pull request sheet; Item menu |
| `requestReviews` | Planned | Pull request sheet; Item menu |
| `requestReviewsByLogin` | Planned | Pull request sheet; Item menu |
| `rerequestReviews` | Planned | Pull request sheet; Item menu |
| `resolveReviewThread` | Yes | context menu > Review... |
| `revertPullRequest` | Yes | context menu > Revert Pull Request... |
| `submitPullRequestReview` | Planned | Pull request sheet; Item menu |
| `unarchivePullRequest` | Planned | Pull request sheet; Item menu |
| `unmarkFileAsViewed` | Yes | context menu > Review... |
| `unresolveReviewThread` | Yes | context menu > Review... |
| `updatePullRequest` | Planned | Pull request sheet; Item menu |
| `updatePullRequestBranch` | Planned | Pull request sheet; Item menu |
| `updatePullRequestReview` | Planned | Pull request sheet; Item menu |
| `updatePullRequestReviewComment` | Planned | Pull request sheet; Item menu |
| `updateTeamReviewAssignment` | Yes | Properties (Alt+Enter) on Team: Assign reviews automatically |

#### GraphQL: Reactions

2 mutations: 2 yes.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `addReaction` | Yes | context menu > React... |
| `removeReaction` | Yes | context menu > React... |

#### GraphQL: Repositories

18 mutations: 18 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `acceptTopicSuggestion` | Planned | Repository sheet |
| `archiveRepository` | Planned | Repository sheet |
| `cloneTemplateRepository` | Planned | Repository sheet |
| `createRepository` | Planned | Repository sheet |
| `createRepositoryCustomProperty` | Planned | Repository sheet |
| `createRepositoryRuleset` | Planned | Repository sheet |
| `declineTopicSuggestion` | Planned | Repository sheet |
| `deleteRepositoryCustomProperty` | Planned | Repository sheet |
| `deleteRepositoryRuleset` | Planned | Repository sheet |
| `promoteRepositoryCustomProperty` | Planned | Repository sheet |
| `setRepositoryCustomPropertyValues` | Planned | Repository sheet |
| `setRepositoryInteractionLimit` | Planned | Repository sheet |
| `unarchiveRepository` | Planned | Repository sheet |
| `updateRepository` | Planned | Repository sheet |
| `updateRepositoryCustomProperty` | Planned | Repository sheet |
| `updateRepositoryRuleset` | Planned | Repository sheet |
| `updateRepositoryWebCommitSignoffSetting` | Planned | Repository sheet |
| `updateTopics` | Planned | Repository sheet |

#### GraphQL: Sponsors

9 mutations: 9 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `cancelSponsorship` | Planned | People > person > Sponsor; Account > Sponsors |
| `createSponsorsListing` | Planned | People > person > Sponsor; Account > Sponsors |
| `createSponsorsTier` | Planned | People > person > Sponsor; Account > Sponsors |
| `createSponsorship` | Planned | People > person > Sponsor; Account > Sponsors |
| `createSponsorships` | Planned | People > person > Sponsor; Account > Sponsors |
| `publishSponsorsTier` | Planned | People > person > Sponsor; Account > Sponsors |
| `retireSponsorsTier` | Planned | People > person > Sponsor; Account > Sponsors |
| `updatePatreonSponsorability` | Planned | People > person > Sponsor; Account > Sponsors |
| `updateSponsorshipPreferences` | Planned | People > person > Sponsor; Account > Sponsors |

#### GraphQL: Teams

1 mutations: 1 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `updateTeamsRepository` | Planned | Team sheet |

#### GraphQL: Users

8 mutations: 5 yes, 3 planned.

| Mutation | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `changeUserStatus` | Yes | Account > Set Your Status... (Ctrl+Alt+S) |
| `createUserList` | Yes | Navigator: Repositories > Star Lists |
| `deleteUserList` | Yes | context menu > Rename or Delete Star List... |
| `followUser` | Planned | Account; People > person |
| `setUserInteractionLimit` | Planned | Account; People > person |
| `unfollowUser` | Planned | Account; People > person |
| `updateUserList` | Yes | context menu > Rename or Delete Star List... |
| `updateUserListsForItem` | Yes | context menu > Star Lists... |

### GraphQL reads with no REST twin

| Query field | Can QUILL do it? | Where, or why |
| --- | --- | --- |
| `blockedBy` | Yes | context menu > Reorder Sub-issues... |
| `closingIssuesReferences` | Yes | Properties (Alt+Enter) on Pull Request |
| `compare` | Yes | Navigator: Repository > owner/name > Code > Branches |
| `contributionsCollection` | Planned | Account > Profile (the contribution table, as a table) |
| `dependencyGraphManifests` | Planned | Repository > Security > Dependencies |
| `discussionCategories` | Yes | Navigator: Repository > owner/name > Discussions |
| `discussions` | Yes | Navigator: Repository > owner/name > Discussions |
| `fundingLinks` | Planned | Repository > General (sponsor links) |
| `issueTypes` | Yes | context menu > Set Issue Type... |
| `linkedBranches` | Yes | Properties (Alt+Enter) on Issue: Linked branches |
| `lists` | Yes | Navigator: Repositories > Star Lists |
| `mergeQueue` | Yes | Item > Merge... (Ctrl+Shift+Enter) |
| `pinnedItems` | Planned | People > person > Profile; Account > Profile |
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
| Remove announcement banner from organization | `DELETE /orgs/{org}/announcement` | Cloud | Planned | Organization sheet > Announcement banner |
| Remove a SAML SSO authorization for an organization | `DELETE /orgs/{org}/credential-authorizations/{credential_id}` | Cloud | Planned | Organizations > org > Single Sign-On |
| Delete a custom repository role | `DELETE /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Planned | Organization sheet > Roles |
| Closing down - Delete a custom role | `DELETE /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Delete a custom organization role. | `DELETE /orgs/{org}/organization-roles/{role_id}` | Cloud | Planned | Organization sheet > Roles |
| Remove the connection between an external group and a team | `DELETE /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Dismiss a response on a bypass request for secret scanning | `DELETE /repos/{owner}/{repo}/bypass-responses/secret-scanning/{bypass_response_id}` | Cloud | Planned | Repository > Security > Bypass requests |
| Cancel a dismissal request for a Dependabot alert for a repository | `DELETE /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Disable Git LFS for a repository | `DELETE /repos/{owner}/{repo}/lfs` | Cloud | Planned | Repository sheet > General (Git LFS) |
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
| Get all custom property values for an organization | `GET /organizations/{org}/org-properties/values` | Cloud | Planned | Organization sheet > Custom properties |
| Get announcement banner for organization | `GET /orgs/{org}/announcement` | Cloud | Planned | Organization sheet > Announcement banner |
| Get the audit log for an organization | `GET /orgs/{org}/audit-log` | Cloud | Planned | Organizations > org > Audit Log |
| List push rule bypass requests within an organization | `GET /orgs/{org}/bypass-requests/push-rules` | Cloud | Planned | Repository > Security > Bypass requests |
| List bypass requests for secret scanning for an org | `GET /orgs/{org}/bypass-requests/secret-scanning` | Cloud | Planned | Repository > Security > Bypass requests |
| Get feature policies for an organization | `GET /orgs/{org}/copilot/feature-policies` | Cloud | Planned | Organization sheet > Copilot |
| Get model policies for an organization | `GET /orgs/{org}/copilot/model-policies` | Cloud | Planned | Organization sheet > Copilot |
| List SAML SSO authorizations for an organization | `GET /orgs/{org}/credential-authorizations` | Cloud | Planned | Organizations > org > Single Sign-On |
| List custom repository roles in an organization | `GET /orgs/{org}/custom-repository-roles` | Cloud | Planned | Organization sheet > Roles |
| Get a custom repository role | `GET /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Planned | Organization sheet > Roles |
| Closing down - Get a custom role | `GET /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| List dismissal requests for code scanning alerts for an organization | `GET /orgs/{org}/dismissal-requests/code-scanning` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| List dismissal requests for Dependabot alerts for an organization | `GET /orgs/{org}/dismissal-requests/dependabot` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| List alert dismissal requests for secret scanning for an org | `GET /orgs/{org}/dismissal-requests/secret-scanning` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Get an external group | `GET /orgs/{org}/external-group/{group_id}` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List external groups available to an organization | `GET /orgs/{org}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Closing down - List fine-grained permissions for an organization | `GET /orgs/{org}/fine_grained_permissions` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| List organization fine-grained permissions for an organization | `GET /orgs/{org}/organization-fine-grained-permissions` | Cloud | Planned | Organization sheet > Roles |
| List repository fine-grained permissions for an organization | `GET /orgs/{org}/repository-fine-grained-permissions` | Cloud | Planned | Organization sheet > Roles |
| Get GitHub Advanced Security active committers for an organization | `GET /orgs/{org}/settings/billing/advanced-security` | Cloud | Planned | Organization sheet > Billing (read-only) |
| List IdP groups for an organization | `GET /orgs/{org}/team-sync/groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List a connection between an external group and a team | `GET /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List IdP groups for a team | `GET /orgs/{org}/teams/{team_slug}/team-sync/group-mappings` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| List repository push rule bypass requests | `GET /repos/{owner}/{repo}/bypass-requests/push-rules` | Cloud | Planned | Repository > Security > Bypass requests |
| Get a repository push bypass request | `GET /repos/{owner}/{repo}/bypass-requests/push-rules/{bypass_request_number}` | Cloud | Planned | Repository > Security > Bypass requests |
| List bypass requests for secret scanning for a repository | `GET /repos/{owner}/{repo}/bypass-requests/secret-scanning` | Cloud | Planned | Repository > Security > Bypass requests |
| Get a bypass request for secret scanning | `GET /repos/{owner}/{repo}/bypass-requests/secret-scanning/{bypass_request_number}` | Cloud | Planned | Repository > Security > Bypass requests |
| List dismissal requests for code scanning alerts for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/code-scanning` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Get a dismissal request for a code scanning alert for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/code-scanning/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| List dismissal requests for Dependabot alerts for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/dependabot` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Get a dismissal request for a Dependabot alert for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| List alert dismissal requests for secret scanning for a repository | `GET /repos/{owner}/{repo}/dismissal-requests/secret-scanning` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Get an alert dismissal request for secret scanning | `GET /repos/{owner}/{repo}/dismissal-requests/secret-scanning/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
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
| Create or update custom property values for an organization | `PATCH /organizations/{org}/org-properties/values` | Cloud | Planned | Organization sheet > Custom properties |
| Set announcement banner for organization | `PATCH /orgs/{org}/announcement` | Cloud | Planned | Organization sheet > Announcement banner |
| Update feature policies for an organization | `PATCH /orgs/{org}/copilot/feature-policies` | Cloud | Planned | Organization sheet > Copilot |
| Update model policies for an organization | `PATCH /orgs/{org}/copilot/model-policies` | Cloud | Planned | Organization sheet > Copilot |
| Update a custom repository role | `PATCH /orgs/{org}/custom-repository-roles/{role_id}` | Cloud | Planned | Organization sheet > Roles |
| Closing down - Update a custom role | `PATCH /orgs/{org}/custom_roles/{role_id}` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Update a custom organization role | `PATCH /orgs/{org}/organization-roles/{role_id}` | Cloud | Planned | Organization sheet > Roles |
| Update the connection between an external group and a team | `PATCH /orgs/{org}/teams/{team_slug}/external-groups` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Create or update IdP group connections | `PATCH /orgs/{org}/teams/{team_slug}/team-sync/group-mappings` | Cloud | Left to GitHub | Identity-provider group connections are managed from the identity provider and the organization's SSO settings. Team sheet (Open on GitHub: identity provider groups). |
| Review a bypass request for secret scanning | `PATCH /repos/{owner}/{repo}/bypass-requests/secret-scanning/{bypass_request_number}` | Cloud | Planned | Repository > Security > Bypass requests |
| Review a dismissal request for a code scanning alert for a repository | `PATCH /repos/{owner}/{repo}/dismissal-requests/code-scanning/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Review a dismissal request for a Dependabot alert for a repository | `PATCH /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Review an alert dismissal request for secret scanning | `PATCH /repos/{owner}/{repo}/dismissal-requests/secret-scanning/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
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
| Revoke all credential authorizations for an organization | `POST /orgs/{org}/credential-authorizations/revoke-all` | Cloud | Planned | Organizations > org > Single Sign-On |
| Revoke a single credential type for an organization | `POST /orgs/{org}/credential-authorizations/revoke-credential-type` | Cloud | Planned | Organizations > org > Single Sign-On |
| Revoke credential authorizations for a user in an organization | `POST /orgs/{org}/credential-authorizations/{username}/revoke` | Cloud | Planned | Organizations > org > Single Sign-On |
| Revoke a single credential type for a user in an organization | `POST /orgs/{org}/credential-authorizations/{username}/revoke-credential-type` | Cloud | Planned | Organizations > org > Single Sign-On |
| Create a custom repository role | `POST /orgs/{org}/custom-repository-roles` | Cloud | Planned | Organization sheet > Roles |
| Closing down - Create a custom role | `POST /orgs/{org}/custom_roles` | Cloud | Left to GitHub | GitHub is closing this route down; the custom-repository-roles route replaces it. Organization sheet > Roles. |
| Create a custom organization role | `POST /orgs/{org}/organization-roles` | Cloud | Planned | Organization sheet > Roles |
| Create a dismissal request for a Dependabot alert for a repository | `POST /repos/{owner}/{repo}/dismissal-requests/dependabot/{alert_number}` | Cloud | Planned | Repository > Security > Alerts > Dismissal requests |
| Check license compliance for packages | `POST /repos/{owner}/{repo}/license-compliance/package-checks` | Cloud | Planned | Repository > Security > Dependencies |
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
| Enable Git LFS for a repository | `PUT /repos/{owner}/{repo}/lfs` | Cloud | Planned | Repository sheet > General (Git LFS) |
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
