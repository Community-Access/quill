# GitHub Workbench: product requirements

| | |
|---|---|
| Product | The GitHub Workbench, in QUILL and QUILL Lite |
| Owner | Jeff Bishop, Community Access |
| Status | Accepted by Jeff, 2026-11-09, with every decision taken as recommended (decision 11 as he amended it). This is the accepted scope; current implementation status and later scope decisions are in the [Workbench implementation status](../planning/workbench-implementation-status.md) |
| Version | 1.0 of this PRD, 2026-11-09 |
| Grew from | `github-workbench-menus-plan.md` (2026-11-07) and this file's plan of 2026-11-09 |
| Code it was checked against | `Community-Access/quill` main at `c9da793`, then `a72efa13b` |
| API it was checked against | GitHub's OpenAPI description 1.1.4 (1,272 operations) and public GraphQL schema (284 mutations), both read 2026-11-09 |
| Reference app | Kelly Ford's GHManage 1.1.0 (`kellylford/GHManage` at `60f3b71`), released 2026-11-09 |

UX means user experience, PR means pull request, and API means the
programming interface GitHub offers, throughout.

## How this document is organized

- **Part A, the product:** what it is, who it is for, what it must achieve,
  and what a great day with it sounds like.
- **Part B, the design:** sections 1 to 22, the window, tree, menus,
  Properties, editing, filtering, permissions, templates, and the creative
  sweep. Section numbers there are stable, and code and other plans cite
  them.
- **Part C, the keyboard:** every key, by family, with the rules that chose
  them.
- **Part D, help:** F1 and everything around it, which Jeff asked to be
  "extensive, amazing and purely awesome throughout".
- **Part E, requirements:** numbered, testable requirements (GH-R-...), each
  pointing back to the design.
- **Part F, quality:** accessibility, performance, reliability, security,
  privacy, and how it is tested.
- **Part G, rollout:** phases, risks and open decisions in one place.
- **Appendices A to D:** every existing feature's new home, every existing
  action's home, every object's Properties sheet, and the permissions
  catalogue.
- **Appendices E and F:** GitHub's whole REST API and GraphQL API, every
  operation and mutation, with its Workbench home, its scope and its tier.

## Part A: the product

### A1. In one paragraph

The GitHub Workbench is a window in QUILL and QUILL Lite where everything you
can do on GitHub can be done from the keyboard, heard clearly, read in
braille, and understood without already knowing GitHub. It has a tree for
where you are, a list for what is there, and details for the one you
picked. Alt+Enter opens the Properties of anything. Every fact is readable,
every editable thing is editable, every list filters on every attribute,
every permission is known before it bites and manageable where GitHub lets
it be managed, and F1 answers everywhere. It is the GitHub that a blind
maintainer, a new contributor and an organization owner can all run all day.

### A2. The short version

- **One window: the GitHub Workbench.** It is a top-level window with its own
  menu bar and its own taskbar button. It is not a modal dialog, so you can
  Alt+Tab between it and QUILL or QUILL Lite. Open a file from it and the file
  opens in the editor; Alt+Tab takes you back to where you were in GitHub.
- **Three panes, the Outlook and File Explorer pattern:** a Navigator tree on
  the left (where you are), a list (what is there), and a details pane (about
  the selected item). F6 moves between them.
- **Nothing is removed.** Every view in GitHub Items and Explore GitHub, every
  button, and every context-menu row gets a named home: a tree node, a menu
  bar row, or a context-menu row. Appendix A lists every one.
- **The 30 buttons and choices above and below the list become a menu bar.**
  The window shows a tree, a filter box, a list, details and a status bar,
  and nothing else.
- **Context menus only offer what applies to the selected item.** The
  default action comes first, Properties comes last.
- **Alt+Enter is Properties, on everything:** repositories, branches, issues,
  pull requests, projects, milestones, labels, releases, runs, people, teams,
  organizations, gists, alerts, environments, rulesets, templates
  (sections 15 and 16, Appendix C).
- **Edit everything GitHub lets you edit,** one item or a hundred at once,
  checked on GitHub afterwards and undoable where GitHub allows (section 16).
- **Star, watch, follow, subscribe, react, block, sponsor, pin:** every
  relationship you can have with a thing, on its You page (section 16.7).
- **Filter on every attribute,** from the filter box, a Filter Builder, the
  Filter menu, or "show only items like this one" on any cell (section 17).
- **Permissions, rigidly:** known before offering, explained when missing,
  added all at once, managed on every object that has them, previewed before
  anything risky, recorded afterwards (section 18, Appendix D).
- **Build and fill every kind of template,** and issue forms filled natively
  instead of sending you to GitHub (section 21).
- **And further:** Copilot agents, GitHub Models, a workflow builder, merge
  conflicts in the editor, an API Console as the escape hatch, threads read as
  documents, Watches that tell you when something happens, plain-language
  batches, import and export, a practice repository, View As Role
  (section 22).
- **Everything is measured:** a coverage gate compares the Workbench with
  GitHub's own API description (section 19, Appendices E and F).
- **Keys you will enjoy:** Windows and Outlook habits first, then families
  that teach themselves: Ctrl+number to go, Alt+number to hear, Delete to
  remove safely. Changing anything is one key, Alt+Enter, and typing always
  moves through the list (Part C).
- **Help that teaches:** F1 on every node, row, field and menu item; Shift+F1
  for "what can I do here, and with which keys"; a GitHub glossary; a search
  of all help that can run what it finds; tutorials and a practice
  repository (Part D).
- **GitHub preferences live in the Workbench,** in its own file, shared by
  both editors; the main Options dialog gains nothing (section 4.1).

### A3. The problem

Section 1 records what a new user meets today, verified in the code: two
modal windows with overlapping jobs, about 28 controls before the list, a
context menu of 15 rows across three scopes, Codespaces offered on every
item, F1 on 6 controls, and a GitHub menu with seven doors that lead to two
windows. Beyond that:

- **Most of GitHub cannot be changed here.** Labels can be added in a batch
  but not removed; there is no general way to set an item's assignees or
  milestone, or edit its title; access, rules, environments and Actions
  settings are not reachable.
- **Issue forms are "link-only":** the most common kind of template sends
  people to the web, which is exactly what they came here to avoid.
- **Permissions surprise people.** A missing scope or role shows up as an
  error at the moment of use, one feature at a time, and GitHub sometimes
  ignores a write and still answers success.
- **github.com is hard work with a screen reader.** Project boards, the
  rulesets editor, the conflict editor, settings pages and the access pages
  are among its least accessible screens, and they are where the power is.

### A4. Goals

1. **Parity with GitHub:** anything GitHub's API lets a person do, the
   Workbench lets them do, measured by GATE-GITHUB-COVER (section 19).
2. **Better than parity where it matters:** the things github.com makes hard
   by ear (boards, rules, access, conflicts, long threads) are easier here.
3. **Findable without knowing GitHub:** where, what, about; one home per
   feature; greyed with a reason rather than hidden.
4. **Safe at any scale:** every change previewed, verified, recorded and,
   where GitHub allows, undoable; nobody locks themselves out.
5. **Help everywhere, and good:** F1 on 100 percent of nodes, rows, fields
   and commands, in a human voice.
6. **Fast:** it never makes you wait on a keystroke, and it is careful with
   GitHub's rate limits.
7. **One Workbench for the family:** QUILL and QUILL Lite open the same
   window; QUILL Lite is never ahead.

### A5. Not goals

- Replacing Git. Local Git stays in the editor (section 6).
- Hosting anything. The Workbench talks only to GitHub (and, by consent, to
  githubstatus.com).
- GitHub Enterprise Server administration and enterprise accounts
  (Appendix F marks them out of scope). GitHub Enterprise Cloud organizations
  are in scope.
- Classic Projects, which GitHub has retired.
- Visual charts as the only form of anything. Every insight is a table or a
  sentence first.

### A6. People it is for

| Person | What they come to do | What delights them |
|---|---|---|
| Jeff, a blind maintainer of a busy family of apps | triage, review, merge, release, keep CI green, answer people | Inbox zero by keyboard; "Merged #1811" with its sound; What Failed in one key |
| A new contributor | file a good issue, make a first pull request | Start Here, issue forms that read like a conversation, the practice repository |
| A project lead | plan with milestones and Projects | a board read as a list, iterations with dates, status updates |
| A reviewer | read and comment on changes line by line | review one commit at a time, viewed files, threads as a document |
| An organization owner | members, teams, access, rules, Actions policy | the access matrix, View As Role, bulk changes with a preview |
| A security responder | alerts, advisories, push protection | one alert list, dismiss with a reason, Autofix as a pull request |
| A teacher | classroom assignments, student repositories | Classroom node, bulk access, templates |
| A writer using GitHub for docs | wiki, Pages, Markdown | wiki edited in the editor, Pages settings, posts checked for accessibility |
| A Copilot user | hand work to the agent, watch it, review it | Assign to Copilot, a session log to read, the agent's pull request in review |

### A7. Journeys: what a good morning sounds like

Each journey is also a usability task in section 12 and a scenario test in
Part F.

1. **Morning triage.** Jeff presses the Workbench door, lands on Inbox
   (Ctrl+1 if he was elsewhere), and hears "Inbox (14)". Down Arrow reads each
   row in full. Delete marks one done, Ctrl+Q marks one read, Enter opens the
   next in details, and Alt+Enter on one opens its Properties, where the
   Organize page takes a label and a milestone.
   Fourteen rows later: "Inbox is empty. Nice work." with the done sound.
2. **A run failed.** A Watch says "The build failed on main: test_paths."
   Ctrl+Shift+W (What Failed) reads the failing step and its first error.
   Ctrl+Enter opens the failing file in the editor at the line. He fixes it,
   commits from the editor, Alt+Tabs back, Ctrl+Shift+F5 re-runs failed jobs.
   The Watch says "Build passed" twenty minutes later while he is writing.
3. **A first issue.** A new contributor opens the Workbench for the first time,
   meets Start Here, presses Ctrl+N on Issues, chooses "Accessibility bug
   report", and fills a form whose every field is a labelled control with its
   help on F1. Submit says "Filed #57. Thank you." They never visit github.com.
4. **Giving a volunteer access.** An organization owner opens the repository's
   Properties (Alt+Enter), goes to Access (Ctrl+Tab), presses Insert, types a
   login, chooses Triage, and hears the preview: "Invite kellylford with
   Triage on Community-Access/quill. They will be able to label, close and
   assign issues; not push code." Before granting it, View As Role shows the
   Workbench as Triage sees it.
5. **Planning a release.** A project lead selects 23 issues with a filter
   (`no:milestone label:accepted`), presses Alt+Enter for one sheet for all 23,
   goes to Organize, picks New Milestone... in the Milestone list,
   types 2027.1 and a due date, and hears "Created milestone 2027.1. 23 issues
   are in it." The project's board, read as Status groups in the tree, shows
   them all in "Planned".
6. **Reviewing a pull request.** Enter on the pull request opens review. The
   reviewer reads one commit at a time, marks files viewed, leaves two line
   comments and a suggestion, then Read as Document exports the whole thread
   to braille-friendly text for a closer read before approving.
7. **Rules that read like sentences.** An admin opens the main branch's ruleset
   and reads the Summary page: "Changes to main need a pull request with two
   approvals, including a code owner; build and test must pass; force pushes
   are blocked; maintainers may bypass." One check box adds "require signed
   commits"; the preview says what changes for whom.
8. **Anything else.** Someone needs a GitHub feature the Workbench has not
   built yet. Tools > GitHub API Console finds it by name from GitHub's own
   description, shows the scope it needs, runs it with a preview, and saves it
   as a menu row with a key for next time.

### A8. Delight, on purpose

Delight here is speed, certainty and a little warmth, never noise:

- **One sentence per outcome,** specific and short: "Starred
  owner/name. 1,205 stars." "#42: added bug, removed docs." Never "Operation
  completed successfully."
- **Sounds for moments,** from the family's sound scheme and the shared
  action-feedback channels (sound, speech, both, silent): done, merged,
  passed, failed, new notification, Watch fired, inbox empty. Each can be
  turned off; a failure is always also spoken.
- **Counts where you look,** never announced: "Pull Requests (12 open)".
- **Celebrations that fit:** inbox empty, milestone complete ("2027.1 is
  done: 42 of 42 closed"), first pull request merged in a repository, a run
  green after a red streak. Each is one sentence, once.
- **No dead ends:** every greyed row says why and offers the fix; every empty
  list says what would fill it; every error says what to do next.
- **It remembers you:** where you were, what was expanded, your columns, your
  filters, per account.
- **It never makes you hunt for a key:** every menu row shows its key, Shift+F1
  lists the keys for what you are on, and the Key Describer names any key you
  press.

### A9. How success is measured

| Measure | Target before the Workbench becomes the default |
|---|---|
| GitHub coverage (section 19) | Every in-scope REST operation and GraphQL mutation classified; `missing` zero; `planned` shrinking each release |
| Help coverage (Part D) | 100 percent of nodes, row types, fields and Workbench commands with authored help; GATE-GITHUB-HELP at zero |
| The section 12 tasks with five people | Every task completed; median wrong turns at most one; each task faster than the same task on github.com with a screen reader |
| Screen readers | NVDA, JAWS and Narrator checks recorded for every phase in `docs/qa/screen-reader-checks-2026-10.md` |
| Keystroke latency | Under 100 ms for every key that does not wait on the network (Part F) |
| "Link-only" and "open on GitHub to do this" rows | Only where GitHub offers no API, each listed in the coverage table |
| Support mail about the Workbench | Tracked by subject at support@community-access.org; no repeat question goes unanswered in help |

### A10. History of this plan

The plan began on 2026-11-07 as the menus plan's decision 7 ("a modeless
Workbench with its own menus, as its own plan"). On 2026-11-09 Jeff's brief
was: include everything, but make it manageable and easy to use, with great
help and F1 everywhere. The same evening he widened it: every object gets a
Properties sheet on Alt+Enter; anything editable is editable; filtering on
every attribute; permissions rigidly and amazingly controlled across all
objects; all combinations offered; "if I can do it in GitHub I should be able
to do it with an accessible interface"; templates; then "think very
creatively", and finally this PRD, with the REST and GraphQL information
embedded and help that is "extensive, amazing and purely awesome
throughout". Workbench Mode and the editor's GitHub menu (PR 1797) stay; this
PRD changes what they open.

## Part B: the design (sections 1 to 22)

## 1. What a new user meets today (verified in the code)

1. **Two windows with overlapping jobs.**
   - GitHub Items has 7 views: Issues & PRs, Branches, Commits, Tags,
     Releases, Workflows, Workflow Runs.
   - Explore GitHub has **35** views in one choice list, mixing four kinds of
     thing: searches, your own work, people, and repository administration
     (security alerts, secret names, Actions caches).
   - Enter on an issue in Explore closes Explore and opens it in Items.
     A new user has to learn which window holds what.
2. **Both are modal**, and so is the PR review reader opened from them. While
   any of them is open, the editor cannot be reached. You cannot read an issue
   and the code it is about side by side.
3. **There are about 28 controls before you reach the list** in GitHub Items:
   - **Repository row:** the repository box and Load, Pinned, Favorites,
     Explore, Projects, View Upstream, Files, Milestones.
   - **Search row:** the search box and Search, Open Link, and a quick filter.
   - **Filter row:** the View, Show, State, Sort and List mode choices, then
     Columns, Back and Forward.

   Below the list there are 12 more buttons: Refresh, View More, Open in
   Browser, Go To #, Diff, Review, Summarize, Compare, Batch, Actions, and
   Close. Tabbing through all of that is the first thing anyone does.
4. **The context menu on an issue has about 15 rows plus a submenu,** mixing
   three scopes:
   - **About the item:** React, Timeline, Summarize, Worktree.
   - **About the repository:** Browse Repository Files, Milestones, Open in
     GitHub Codespaces.
   - **About the app:** GitHub API Rate Limit.

   **Open in GitHub Codespaces is the first row on every item,** including
   issues, releases, tags and runs. Explore's context menu has about 25 rows
   across its row types.
5. **Seven doors in the editor's GitHub menu lead into the two windows.**
   - Three of them answer "what needs me": Inbox, My Work and Notifications.
   - "Issues and Pull Requests..." and "Repository Items..." open the same
     dialog on different views.
6. **F1 is thin.**
   - GitHub Items sets authored help on 5 controls; Explore sets it on 1.
   - The nine per-app help gates (GATE-<APP>-HELP) do not cover
     `quill/ui/github_*`. Twenty-seven modules there build windows.
7. **A correction to what I said in chat:** GitHub Items *does* have a
   Show: Both / Issues / PRs choice, as GHManage does. It stays, and becomes
   easier to find (section 3.3).

## 2. Principles

1. **Where, what, about.** The tree says where you are, the list says what is
   there, and details say what this one is. Every screen follows this pattern.
2. **Every feature has one home, chosen by what kind of thing it is.**
   - Something you **look at** is a tree node.
   - Something you **do** is a menu bar row.
   - Something you **do to the selected item** is also on its context menu.

   The same command can sit in both menus: one command id, one handler, one
   key. That is two routes to one command, not a second implementation.
3. **Default action first, and Enter does it.** Open for an issue, Review for a
   PR, Jobs and Logs for a run, Assets for a release, Commits for a branch.
4. **Scope follows the selection.** Item commands go on the item, repository
   commands on the repository node, account commands on the Account menu, and
   app diagnostics under Help or the status bar.
5. **Rare means one level down, never removed, never behind a setting.** Admin
   and occasional features live in a named folder or a More submenu.
6. **Explain instead of failing.** A node that needs sign-in, push access or an
   opt-in is always shown. Its details pane says what it needs and offers the
   fix, such as Sign In... or Turn On....
7. **GATE-13 still holds.** The screen reader says titles, focus and selection;
   the Workbench only says results and changes the reader cannot see.
8. **QUILL Lite is never ahead.** The window lives in `quill/ui`, and both
   editors open the same window.

## 3. The window

### 3.1 Shape and behaviour

- **A top-level `wx.Frame`**, titled "GitHub Workbench - owner/name". It has
  its own menu bar and status bar, and appears in the taskbar and Alt+Tab.
  Because it is a frame, its Close button must be bound through
  `dialog_contract.bind_close_button` (the close-button contract).
- **One Workbench per app.** Opening it again brings the same window forward,
  at the place the door asked for. In QUILL Lite, all document windows share
  one Workbench (decision 1).
- **Back to the editor.** Alt+Tab works, and Window > Switch to Editor raises
  the editor that opened the Workbench. These open in the editor and raise it:
  Open in Editor on a file, Open File Reference, and
  Start in Local Worktree.
- **Dialogs launched from the Workbench stay dialogs** (PR review, diff,
  timeline, jobs and logs, release editing, and the rest). They are parented
  to the Workbench, so they block only the Workbench and never the editor.
- **It remembers** its size, pane sizes, last node and expanded nodes, per
  account, in the Workbench's own files, never in the main Settings
  (section 4.1).
- **Closing:** Alt+F4 and File > Close Workbench close it. Escape clears
  the filter box, then goes Back, and never closes the window (decision 5).

### 3.2 The panes

| Pane | What it is | Notes |
|---|---|---|
| Navigator (tree) | Where you are: accounts, repositories, searches, people | Native `wx.TreeCtrl` (section 9) |
| Filter box | One text box above the list | Replaces both the search box and the quick filter. Plain words filter the loaded list; GitHub qualifiers (`is:open label:bug`) query GitHub. Enter runs, Escape clears. |
| List | The items in the selected node | Today's `wx.ListCtrl`, with Quick and Full modes and Columns kept as they are |
| Details | The selected item, or the node's help when the list is empty | Today's read-only details text, with Alt+N and Alt+P for comments |
| Status bar | Account, repository, your access, item count, filter, loading, API rate limit, Workbench access level | A row of cells you arrow across and act on (section 3.2.1); also read by the screen reader's status-bar command; never announced |

F6 and Shift+F6 cycle through the tree, filter, list, details and the status
bar.

#### 3.2.1 A status bar you can move through and act on

Jeff, 2026-11-09: "the status bars ... should allow you to arrow across them
and use context menus to take action." The family already does this twice:
QUILL's editor status bar (`StatusBarMixin`) and Quill Radio's
(`quill/ui/radio/status_bar.py`), and the Workbench follows the same contract,
built once in the shared engine so the WordPress Workbench gets it too:

- **Reached with F6, and only F6.** The cells take no Tab stops, so Tab never
  detours through them. F6 from the details pane lands on the first cell;
  Escape goes back to where you were.
- **Arrow across:** Left and Right move cell to cell, Home and End jump to the
  ends. Each cell reads as its name and value: "Account, jeffbishop",
  "Rate limit, 4,812 of 5,000 left".
- **Enter does the obvious thing; the context menu does the rest** (the
  Applications key, Shift+F10, or a right-click). Every menu ends with Copy
  (the cell's text) and Help for This Cell (F1).
- **Labels lead with what they are, not a bare number,** as Quill Radio learned:
  a cell is never just "12".
- **Mirrored to the real status bar** too, so NVDA's and JAWS's status-bar
  read keys say the same facts, and Alt+1 to Alt+9 (Part C, C4) speak a cell
  without moving there.

| Cell | Reads | Enter | Context menu |
|---|---|---|---|
| Account | "Account, jeffbishop" | Switch Account... | Switch Account; Manage GitHub Accounts...; GitHub Permissions...; Sign In Again; Change History |
| Repository | "Repository, Community-Access/quill" | Select its node in the tree | Properties (Alt+Enter); Open on GitHub; Copy Link; Clone...; Star or Unstar; Watch Level...; Choose Another Repository... |
| Your access | "You have Admin, through owners" | What Can I Do Here? | What Can I Do Here?; View As Role...; Why Can't I...? |
| Items | "40 pull requests, 3 selected" | Select All | Select All; Clear Selection; Export List...; Columns...; Load All |
| Filter | "Filter, review-requested:@me" or "No filter" | Filter Builder... | Edit in Filter Builder; Clear Filter; Save as Search...; Pin to Needs My Attention; Show Only Open / Closed / All |
| Loading | "Loading, 3 of 8 pages" or "Up to date, 14:05" | Refresh (F5) | Refresh; Refresh Ignoring Cache; Cancel Loading; Load All |
| Rate limit | "Rate limit, 4,812 of 5,000 left, resets 15:40" | Say the full report | Full Report; Copy; What Uses the Most? |
| Watches | "2 Watches waiting" (only when there are any) | Go to Watches | Go to Watches; Pause Watches for an Hour |
| Workbench access | "Full" or "Read Only" | Change... | Read Only; Organize; Full; Dry Run on or off (section 22.8) |

A cell that has nothing to say right now is left out rather than shown empty,
and the order never changes, so muscle memory holds.

### 3.3 The Navigator tree

Counts follow names in brackets, GHManage's form, for example
"Pull Requests (12 open)". They load lazily and are never announced.

```
Start Here                       what this window is, sign-in state, the guide
Needs My Attention
    Inbox                        (Explore's attention queue)
    Notifications (n unread)
    Review Requests              (My Work, split by reason)
    Assigned to Me
    Mentions
    My Open Pull Requests
    My Open Issues
    My Activity Feed
Repositories
    <current repository>         the one the active document belongs to
    Pinned            > repositories
    Favorites         > repositories and saved items
    My Repositories   > repositories
    Starred           > repositories
    Watched           > repositories
    Organizations     > organization > repositories
Search
    Issues and Pull Requests
    Code
    Commits
    Repositories
    Saved Searches    > each saved search
People
    People I Follow
    My Followers
    Find a Person...  > person > Repositories, Activity, Followers, Following
Gists
    My Gists
Projects
```

Every repository node has the same children, in this order:

```
owner/name
    Overview                     README, description, community profile
    Issues (n open)
    Pull Requests (n open)
    Issues and Pull Requests     the inbox-style combined list (decision 3)
    Discussions
    Actions
        Runs
        Workflows
        Caches
    Code
        Files
        Branches
        Commits
        Tags
        Upstream                 forks only
    Releases
    Labels
    Milestones
    Projects
    Activity
    People
        Contributors and People
        Forks
        Collaborators and Team Access
    Insights
        Traffic and Contributors
        Health Snapshot          opt-in
        Community Profile
    Deployments and Environments
    GitHub Pages
    Security
        Alerts
        Dismissed and Resolved Alerts
    Settings
        Secret and Variable Names
        Branch Protection
        General                  name, visibility, default branch
```

- **Issues and Pull Requests are separate nodes,** so the Show choice becomes
  a preset of the node. View > Show still switches between them, so nothing
  is lost and the inbox-style list is one node away.
- **Drill-downs move the tree with them.**
  - Enter on a branch selects that branch's Commits.
  - Enter on a person selects that person's node.
  - Enter on a label lists the issues carrying it.
  - Enter on a release lists its assets.
  - Enter on a run lists its jobs.

  Back and Forward (Backspace, Alt+Left, Alt+Right) walk the same history.
  The tree always answers "where am I", and the status bar shows the trail.
- **Nodes needing sign-in or permission** are always shown. Selecting one
  explains what it needs in details, and the menu offers the fix.

## 4. The menu bar

Every row follows the menu accelerator rule: a visible key route on each row,
and no key claimed twice. The menus are built from a wx-free table, the way
`workbench_menu.py` already is, so tests can walk them. Rows that do not apply
are greyed, and their help string says why ("Needs push access", "Select a
pull request"). That is GHManage's answer to "what can I do here?".

- **File**
  - New Issue..., New Pull Request..., New Discussion..., New Gist...,
    Create Release..., Create Repository...
  - Open GitHub Address... (this is today's Open Link, Open GitHub Reference
    and GitHub File URL in one box), Go to Number..., Open a Repository...,
    Clone Repository...
  - Open on GitHub, Open in Editor
  - Close Workbench
- **Edit**
  - Copy Link, Copy Details
  - Filter... (moves focus to the filter box)
  - Select All (for batch work)
- **View**
  - Show (Issues / Pull Requests / Both), State (Open / Closed / All),
    Sort, Quick or Full list, Columns...
  - Refresh, Load More (today's View More)
  - Back, Forward
- **Go:** the same places as the tree, for people who prefer menus. Inbox,
  Notifications, Review Requests, Current Repository, Issues, Pull Requests,
  Actions Runs, Releases, then Pinned, Favorites and Saved Searches as
  submenus. The editor's GitHub-menu doors land here.
- **Item:** everything that acts on the selected row, greyed where it does
  not apply.
  - Open or Review, File Differences, Comment, Reply to Thread, Edit or Delete
    This Comment, React, React to This Comment.
  - Close or Reopen, Labels, Assignees, Milestone, Lock or Unlock
    Conversation, Pin or Unpin, Transfer Issue, Set Issue Type, Reorder
    Sub-issues.
  - Assign to Copilot, Merge Pull Request, Start in Local Worktree,
    Summarize Discussion, View Timeline, Commit Comments.
  - For runs: What Failed, Re-run, Re-run Failed Jobs Only, Cancel, Delete,
    Approve Run from a Fork, Review Pending Deployments, Combined Check
    Status, View Jobs and Logs, View Artifacts.
  - For releases: Edit Release, Draft Release Notes, Upload Asset,
    Delete Asset.
  - Add to or Remove from Favorites, and a Batch submenu (assignees and
    milestone on a multiple selection).
- **Repository**
  - Watch or Unwatch, Star or Unstar, Fork..., Browse Files, Compare
    Branches..., View Upstream, Run Workflow on Branch...,
    Dispatch Workflow...
  - Codespaces: Open in Codespaces..., Codespaces..., Create Codespace....
    Every Codespaces row keeps its confirmation that a Codespace can cost
    money.
  - Settings: Rename, Change Visibility, Change Default Branch, Configure
    Branch Protection, Delete Branch, Commit Multiple Files.
  - Security Alerts.
- **Account**
  - Switch Account, Manage GitHub Accounts..., Sign In or Sign Out.
  - Notification and Inbox Options (today's Queue Options, Choose Categories,
    Choose Repositories, Save Current Filter).
  - GitHub API Rate Limit.
- **Tools:** Workbench Options... (section 4.1). Windows' own place for
  options, so it is where people look.
- **Window:** Switch to Editor, and in QUILL Lite, the list of document
  windows.
- **Help**
  - Help for This View (F1 also does this)
  - Getting Started, which opens Start Here
  - GitHub Workbench Guide
  - Workbench Keys

### 4.1 Workbench Options: GitHub preferences live here

GitHub preferences belong to the Workbench, so the main Options dialog in
QUILL and QUILL Lite stays about writing.

- **Where:** Tools > Workbench Options... in the Workbench's menu bar. It is a
  tabbed dialog parented to the Workbench, so it never blocks the editor. The
  editor's own Options dialog gets no GitHub page and no GitHub controls
  (decision 6).
- **Storage:** its own file, `github_workbench.json` in the app data folder.
  - Loaded and saved by a wx-free `quill/core/github/workbench_prefs.py`,
    written atomically through `write_json_atomic` and schema-validated,
    like every other store.
  - Next to it, the existing per-account resume file
    (`github_items_context.json`, from `navigation_state.py`) keeps holding
    "where I was" state: last view, filter, selection and history.
    Preferences are things a person chooses; resume state is things the
    window remembers.
- **One store for both editors.** QUILL and QUILL Lite read and write the same
  file through the same module, so the two cannot drift. "QUILL Lite is never
  ahead" holds by construction, and the settings vocabulary audit has nothing
  to pair because neither editor's `Settings` holds these fields.
- **Pages:**
  - **General:** where the Workbench opens (Inbox, Start Here or the last
    place), Quick or Full list by default, default sort, and default state
    (open, closed, all).
  - **Notifications and Inbox:** how often to check for new notifications,
    whether a new one plays a tick, whether that interrupts speech, whether
    read notifications are included, and the Inbox categories and
    repositories (today's Queue Options, Choose Categories and
    Choose Repositories).
  - **Lists:** columns per view and whether column names are spoken (today's
    Columns... dialog, which stays on View for the current list).
  - **Repositories:** pinned repositories and favorites, to manage them in one
    place.
  - **Privacy and opt-ins:** the Health Snapshot opt-in, and what the
    Workbench keeps on this device, with Clear History and Clear Favorites.
- **What moves out of the main Settings**, with a one-time migration that
  reads the old value, writes it into `github_workbench.json`, and drops the
  old key on the next save:
  - `github_poll_interval_minutes`, `github_poll_audible_tick` and
    `github_poll_interrupt_speech` (in `quill/core/settings.py`).
  - `monitor_policy.py` and `settings_specs.py` read the interval from the
    Workbench store instead. The `MONITOR_GITHUB` clamp still applies.
  - `git_sync_last_folder` stays in the editor's Settings: Sync Folder is an
    editor command, not a Workbench one.
  - The settings vocabulary snapshot and the settings documentation inventory
    (GATE-SETDOC) are regenerated in the same change, so the removal is
    reviewed, not silent.
- **Help and gates.**
  - Every control on every page has inline `SetHelpText`, under
    GATE-GITHUB-HELP (section 7).
  - The documentation half of GATE-SETDOC is extended to read
    `workbench_prefs.py`'s fields, so a new Workbench preference is
    `missing` until the GitHub Guide documents it.
  - Defaults must make the Workbench fully usable without ever opening this
    dialog.

## 5. Context menus

Rules, tested from the table:

1. The first row is the default action, the one Enter does.
2. Only rows about the selected row. No repository-scope or app-scope rows on
   an item.
3. About eight rows, then a **More** submenu. More mirrors the Item menu, so
   nothing is reachable only by right-clicking.
4. Codespaces only on a repository, a branch or a PR.
5. GitHub API Rate Limit appears on no context menu. It lives under the
   Account menu and in the status bar.
6. **The last row of every context menu is Properties... (Alt+Enter),** on
   every row type in the table below and on every tree node. It is the same
   command as Item > Properties... and the same sheet (section 15).

| Row type | Context menu (More holds the rest of the Item menu) |
|---|---|
| Issue | Open; Comment...; Close or Reopen; Labels...; Assignees...; Copy Link; Open on GitHub; More |
| Pull request | Review...; File Differences...; Comment...; Merge...; Copy Link; Open on GitHub; More (Start in Local Worktree, Open in Codespaces, Commit Comments, Timeline, Summarize, React and the rest) |
| Workflow run | Jobs and Logs; What Failed...; Re-run Failed Jobs Only; Re-run Workflow; Cancel Run...; View Artifacts...; Open on GitHub; More |
| Workflow | Runs; Run Workflow on Branch...; Open on GitHub; Copy Link |
| Release | Assets; Edit Release...; Draft Release Notes...; Upload Asset...; Copy Link; Open on GitHub; More |
| Release asset | Download; Copy Link; Delete Asset... |
| Branch | Commits; Compare Branches...; Open in Codespaces...; Copy Name; Delete Branch... |
| Commit, Tag | Open; Commit Comments...; Copy Link; Open on GitHub |
| Notification | Open; Mark Read; Mark Done; Snooze for One Day; Unsubscribe from Thread; Open on GitHub; More (Mark All Read, Unsnooze Locally) |
| Repository row | Open (selects its node); Star or Unstar; Watch or Unwatch; Clone...; Pin; Favorite; Open on GitHub |
| Person | Open (selects their node); Follow or Unfollow; Open on GitHub |
| Label | Find Issues with Label; Edit Label...; Delete Label...; Create Label... |
| Gist | Edit Gist...; Star or Unstar; Copy Link; Open on GitHub; Delete Gist... |
| Discussion | Open Discussion Thread; Copy Link; Open on GitHub |
| Security alert | Open; Dismiss Alert... or Reopen Alert...; Open on GitHub |
| Actions cache | Delete Cache... |
| Saved search | Run; Remove Saved Search |
| A tree node | Refresh; Open on GitHub; Pin or Favorite (for repositories); Help for This View |

## 6. The editor side

The GitHub menu in Workbench Mode becomes a short list of doors:

```
Leave Workbench Mode
-
Open GitHub Workbench
Inbox
This Repository's Issues
This Repository's Pull Requests
Actions Runs
-
Open GitHub Address...
Clone Repository...
-
Commit to GitHub...          (QUILL only)
Sync Folder with GitHub...   (QUILL only)
Local Git                  >
-
Manage GitHub Accounts...
Open GitHub Guide
```

- **Repository Admin and Codespaces move into the Workbench's Repository
  menu.** Their command ids stay registered, and each one opens the Workbench
  and runs the command there. Keys, the Menu Editor, the Key Describer and the
  documentation-chord gates therefore stay valid.
- **My Work, Notifications, Releases, Repository Items and Explore GitHub
  stay as command ids** that open the Workbench at the matching node. They
  leave the menu, so Inbox is the one door for "what needs me".
- **Local Git stays in the editor.** It is about the working copy the document
  is in, not about GitHub.
- **The normal-mode homes** (File > Open from Remote, Tools > Git and GitHub)
  keep their rows for one release so nobody's habits break, then slim down
  the same way (decision 4).

## 7. F1 everywhere, and help that teaches

- **One engine.** F1 uses the shared `app_context_help` and `control_help`:
  first the window's purpose, then help for whatever has focus.
  - **On a tree node:** what the node shows, what you can do there, and what
    it needs (sign-in, push access, opt-in).
  - **On the list:** the node's help, then what the selected row type can do
    and its default action.
  - **On a menu row:** its command topic from `topics.json`. Every
    Workbench command id gets a topic, and `check_help_coverage --strict`
    is made strict for the `github.*` namespace.
- **One catalogue of authored words,** `quill/core/github/workbench_help.py`
  (wx-free). It holds node help keyed by the tree table's node keys, and row
  help keyed by command id. A test fails when a node or row has no help.
- **Inline `SetHelpText` on every control,** at the construction site, as the
  help gates require.
- **A new gate, GATE-GITHUB-HELP.** `quill/tools/github_help_audit.py`,
  rostered in `platform_report`, covers the Workbench and every
  `quill/ui/github_*` window. It starts from today's missing list and may only
  shrink. The goal is zero before the Workbench ships as the default.
- **Empty states are help.** When a list is empty, still loading, or needs
  sign-in, the details pane says why and what to do. It is not announced;
  the reader reads it when the user arrives there.
- **Start Here,** the first node, is a short getting-started page: what the
  three panes are, F6, Enter, the context-menu key, Back, and F1, plus
  sign-in state and a link to the guide (decision 2).
- **Generated references.** `docs/github/workbench-reference.md` is generated
  from the tree, menu and context tables, and drift-gated, like the keyboard
  and F1 references. The Workbench's help also renders into
  `docs/f1-help-reference.md`.
- **The GitHub Guide is rewritten around the tree:** one chapter per
  top-level node, with Start Here first.

## 8. Keyboard

The existing keys inside GitHub Items keep working:

- Ctrl+D: favorite
- Ctrl+R: refresh
- Ctrl+Shift+L: API rate limit
- Ctrl+Shift+W: what failed
- Ctrl+Shift+F: filter
- Ctrl+Shift+B: compare branches

The proposed window keys, each checked against the family rules before
adoption:

| Key | Does |
|---|---|
| F6, Shift+F6 | Next or previous pane |
| Enter | Default action |
| Applications key, Shift+F10 | Context menu |
| Backspace, Alt+Left / Alt+Right | Back / Forward |
| F5 (and Ctrl+R) | Refresh |
| Ctrl+L | Open GitHub Address (the browser habit) |
| Ctrl+Shift+F, Ctrl+E | Filter box (Ctrl+E is the Outlook and Explorer search habit) |
| F1 | Help for this view and control |
| Alt+Enter | Properties of the selected object: a row, a tree node, or several selected rows at once (section 15) |
| Ctrl+Alt+F | Filter Builder (section 17.2). Ctrl+Shift+F and Ctrl+E stay the filter box |
| Right / Left in the tree | Expand / collapse, or go to parent |
| Typing in the tree or list | Type-ahead to a name |

The Workbench gets its own entry in `keymap.APP_KEYMAPS` (decision 7). That
way its keys appear in the keyboard reference and the Key Describer, and the
editor's chords are not consumed by it (rule 7).

## 9. Making the tree work well with a screen reader

- **Use the native Win32 tree (`wx.TreeCtrl`),** which NVDA, JAWS and
  Narrator handle well, not a `wx.dataview` tree. Phase 1 starts with a spike
  that proves this with all three readers.
- **Short names, count last:** "Notifications (12 unread)". The reader
  announces level and expanded state itself, so the name never says them.
- **Children load lazily,** with a placeholder child so a node reads as
  collapsed. While loading, the details pane says so; nothing is announced.
- **Never more than four levels deep:** for example Repositories, then
  owner/name, then Actions, then Runs.
- **Expanded state and the last node are remembered.** A big account must
  not mean re-expanding everything each time.

## 10. How it is built

- **`quill/core/github/workbench_tree.py`** (wx-free) is the tree as data. One
  `NodeSpec` per node holds:
  - key, label and parent
  - scope: none, account, repository, person or query
  - what it needs (sign-in, push access, opt-in)
  - its loader (an existing Items or Explore fetch), columns and row type

  **The "nothing dropped" test:** every key in `github_items_view.VIEWS` and
  `explore_views.VIEWS` appears in the tree exactly once.
- **`quill/core/github/workbench_window_menu.py`** is the menu bar as a table.
- **`quill/core/github/item_actions.py`** is the context menus as a table:
  ordered rows per row type, each with its scope. Tests check rules 1 to 5 in
  section 5.
- **`quill/ui/github_workbench_window.py`** is the frame, assembled from
  mixins, as `MainFrame` is. The existing Items and Explore mixins keep doing
  the fetching and acting; the window only arranges them.
- **QUILL and QUILL Lite both open it** through
  `github_workbench_commands.py`, which already sits between them.
- **The existing gates the work must keep green:**
  - menu accelerators and access keys (GATE-14), over the new bar
  - GATE-13 and GATE-BRAILLE
  - the close-button contract and dialog inventory
  - GATE-REACH (the new window must be reachable; the old dialogs become
    parked, then retired)
  - GATE-11 module size budgets (`github_items_dialog.py` is large; extract,
    don't grow)
  - DPI sizing through `dip()`
  - GATE-LITE-COVER for any new Lite handler
  - both documentation-chord gates
  - the network egress audit: no new calls, because the Workbench reuses the
    existing fetches
  - the settings vocabulary audit and GATE-SETDOC, regenerated for the three
    poll settings that leave the main Settings (section 4.1)
- **The profile gap from the menus plan** (decision 1 there) still needs an
  answer before shipping. In QUILL, the Workbench is gated behind the
  Developer profile; in QUILL Lite, it is on everywhere.

## 11. Phases

Each phase is its own PR with every gate green.

- **Phase 0 - quick wins in today's dialogs (small; ships on its own).**
  - Context menus follow section 5: Codespaces off issue, release, tag and
    run rows; repository rows and Rate Limit off item menus; default first;
    a More submenu.
  - `SetHelpText` on every control in GitHub Items and Explore.
  - Drop the "Opening GitHub Items" announcement the menus plan found.
- **Phase 1 - the spike (medium).**
  - The frame, with tree, list and details hosting the 7 Items views only,
    behind a developer flag.
  - NVDA, JAWS and Narrator checks; timing on a large account.
  - Decide go or no-go on `wx.TreeCtrl`.
- **Phase 2 - everything in the tree (large).**
  - The 35 Explore views become nodes, with drill-downs, Back and Forward,
    and the status bar.
  - The "nothing dropped" test passes.
- **Phase 3 - menus and context menus (medium).**
  - The menu bar and context tables. The button rows go away.
  - Workbench Options and `github_workbench.json`, with the one-time
    migration of the three poll settings out of the main Settings
    (section 4.1).
- **Phase 4 - the editor side (medium).**
  - The short GitHub menu; old command ids open Workbench nodes; QUILL Lite
    in the same change.
- **Phase 5 - help and docs (medium).**
  - The help catalogue complete; GATE-GITHUB-HELP strict at zero; Start Here.
  - The generated Workbench reference; the GitHub Guide rewrite.
  - Release notes that tell the story: one window, a tree, F1 everywhere.
- **Phase 6 - retire the old windows (small).**
  - GitHub Items and Explore stay parked for one release as a fallback
    (decision 4), then are deleted.

Phases 7 to 11, for Properties, editing, filtering, permissions and coverage,
are in section 20.

## 12. Checking it with people

Before Phase 3 and again before Phase 6, run the same tasks with about five
people: new to GitHub and experienced, screen-reader users and sighted.
Count wrong turns and time per task. For example:

- Find the pull requests waiting for your review.
- Re-run only the failed jobs of the latest run.
- Draft release notes for the latest release.
- Find who has access to the repository.
- Read the issue a notification is about, then open the file it names in
  the editor and come back.

Record the open checks in `docs/qa/screen-reader-checks-2026-10.md`.

## 13. Decisions for Jeff

**All decided, 2026-11-09.** Jeff: "Yes, accept them." Every recommendation
in this section and in G3 (decisions 1 to 25) is accepted as written, with
decision 11 as Jeff amended it (no per-property keys).

1. **One Workbench per app,** shared by all of QUILL Lite's document windows?
   Recommendation: yes.
2. **Start Here** always first, or moved to the bottom once you are signed in?
   Recommendation: always present; after the first sign-in, the Workbench
   opens on Inbox instead of on Start Here.
3. **Keep a combined Issues and Pull Requests node** next to the two separate
   ones? Recommendation: yes, for GHManage users and inbox-style readers.
4. **The old dialogs and normal-mode menu rows:** keep them for one release,
   then retire them? Recommendation: yes.
5. **Escape** clears the filter, then goes Back, and never closes the window?
   Recommendation: yes. Alt+F4 closes it.
6. **Workbench Options as the only home for GitHub preferences** (section 4.1),
   with nothing GitHub in the editors' main Options? Recommendation: yes. One
   optional extra: a single "GitHub Workbench Options..." link row on the
   main Options dialog's Advanced page, as a signpost for people who look
   there first. Recommendation: no, to keep the main Options clean; F1 on
   the main Options says where GitHub preferences live instead.
7. **The Workbench's own `APP_KEYMAPS` entry?** Recommendation: yes.
8. **Names:** "GitHub Workbench" for the window, "Needs My Attention" for the
   attention branch, and "Inbox" for the queue inside it.
9. **The profile gap** from the menus plan, decision 1.
10. **Alt+Enter for Properties** in the Workbench, with Properties... as the
    last row of every context menu and the Item menu? Recommendation: yes.
11. **Keys for single properties: none** (decided by Jeff, 2026-11-09). Alt+Enter
    opens the Properties sheet and typing always moves through the list.
    GHManage's bare-letter keys and the earlier Alt+Shift proposal are both
    dropped.
12. **Secrets write-only, as GitHub keeps them,** with Set Value... encrypting
    on this machine and never showing, logging or keeping the value.
    **Decided** (Jeff, 2026-11-09: "yes, implement this: PyNaCl"). PyNaCl was
    already a core dependency (`PyNaCl>=1.6.2`, bundled for Quillin signing),
    so no package was added. Built first in Explore GitHub on branch
    `feat/github-secret-values`: Set New Value, New Secret, New Variable, Edit
    Value and Delete, for repository and environment scopes.
13. **The four tiers and their defaults** (section 18.4), tier 1 saving at once
    unless Workbench Options asks first? Recommendation: yes.
14. **Read Only, Organize and Full per account,** with Safe Mode making every
    account Read Only? Recommendation: yes.
15. **Change History kept 90 days** on this device by default?
    Recommendation: yes, clearable at any time.
16. **The vendored API snapshot and GATE-GITHUB-COVER** as the measure of
    "everything"? Recommendation: yes, started early (Phase 11) so its
    missing list drives Phases 7 to 10.
17. **The access matrix and bulk access changes** for organization owners
    (section 18.3.2): in the first permissions PR, or after the Access pages
    have been used for a release? Recommendation: after, so the single-object
    pages are proven first.
18. **Saving a template:** straight to the default branch, or to a new branch
    with a pull request by default? Recommendation: a pull request by
    default when the branch is protected, straight to the branch otherwise,
    with the other choice one check box away.
19. **The API Console** (section 22.2) for everyone, or only in the Developer
    profile and QUILL Lite? Recommendation: everyone, under Tools, because it
    is the guarantee behind "anything GitHub can do".
20. **View As Role** (section 22.10) in the first permissions PR?
    Recommendation: yes; it is read-only and it is the clearest way to
    understand a role before granting it.
21. **Watches** (section 22.5) fetch on the existing notification poll and
    never poll faster than it? Recommendation: yes.

## 14. GitHub features QUILL does not have yet

Checked against the code at `c9da793` by searching `quill/core/github` and the
GitHub UI modules for each feature, and against
`docs/planning/github-roadmap.md` (the GX01 to GX15 waves). "Roadmap" means
the wave already promises it. Each row gives the feature's home in the new
tree, so adding it later does not reshape anything.

### 14.1 Worth adding (people will look for these)

| Feature | Status today | New home |
|---|---|---|
| Close reason: completed, not planned, or duplicate of #n | Not found: closing has no reason | Item > Close Issue... asks the reason; the details pane shows it |
| Linked pull requests and branches for an issue ("Development"), and "create a branch for this issue" | Not found | Issue details; Item > Linked Pull Requests; Item > Create Branch for Issue... (next to Start in Local Worktree) |
| Saved replies | Roadmap GX05 and GX12, not built | Item > Insert Saved Reply in every comment box; Tools > Workbench Options > Saved Replies |
| Wiki | Roadmap GX12, not built | Repository > Wiki (pages as a list, read in details, edit in the editor) |
| Repository invitations: accept or decline | Seen only as a notification type | Needs My Attention > Invitations |
| Edit description, website and features (issues, wiki, discussions, projects on or off) | Rename, visibility, default branch and topics only | Repository > Settings > General |
| Rulesets: read them | Read only inside merge readiness, with a link out | Repository > Settings > Rulesets (read-only list; editing stays on github.com) |
| Enable or disable a workflow | Not found | Workflow context menu; Item menu |
| Revert a merged pull request | Not found | PR context menu > More > Revert... |
| Security policy, private vulnerability reports, repository security advisories | Not found (an advisory credit appears only as a notification reason) | Repository > Security > Policy; Security > Advisories (roadmap GX11) |

### 14.2 Worth adding later (useful, less often)

| Feature | Status today | New home |
|---|---|---|
| Packages (GitHub Packages, container registry) | Not found; only token scopes mention it | Repository > Packages; Repositories > My Packages |
| Teams and organization members | Out of scope by a code comment ("Organizations in, Teams out"); roadmap GX13 adds team permissions. Now in scope: section 18.3.3 | Repositories > Organizations > org > Members, Teams; People > My Teams |
| Insights charts as tables: commit activity, code frequency, punch card | Not found | Repository > Insights (tables, never charts only) |
| Dependency graph and software bill of materials (SBOM) export | Not found | Repository > Security > Dependencies |
| Tags: create and delete outside a release | Not found | Repository > Code > Tags context menu |
| Hide a comment (moderation: spam, off-topic, outdated) | Not found | Comment context in details > Hide Comment... |
| Transfer a repository | Not found (only issues transfer) | Repository > Settings > Transfer... |
| Self-hosted runners | Not found | Repository > Actions > Runners (read-only) |
| Star lists | Not found | Repositories > Starred > each list |
| Your profile and status | Not found | Account > Profile and Status... |

### 14.3 Brought in after all (Jeff, 2026-11-09: "If I can do it in GitHub I should be able to do it")

The first draft of this plan left these to github.com on purpose. Jeff's
brief overrules that: risk is answered with permission checks, previews and
typed confirmations (section 18.4), not by leaving a feature out. Each now has
a home and a Properties sheet:

- **Webhooks:** Repository > Settings > Webhooks, and the same for an
  organization. Create, edit the address, content type and events (every
  event GitHub offers, as a check list), turn on or off, see recent
  deliveries and their responses, redeliver, ping. The webhook secret is
  write-only: you can set a new one, never read the old one.
- **Deploy keys:** Repository > Settings > Deploy Keys. Add (title, key,
  read-only or read-write), delete. The key text is shown as GitHub shows it.
- **Autolink references:** Repository > Settings > Autolinks. Add a prefix and
  URL template (alphanumeric or numeric), delete.
- **Secret and variable values:** variables are read and written in full.
  Secrets stay write-only, as GitHub itself keeps them: Set Value... encrypts
  the new value with the repository's or environment's or organization's
  public key before it leaves the machine, and the value is never shown,
  logged, spoken or kept. Organization secrets also choose which
  repositories may use them (all, private only, or selected).
- **Billing and usage:** Account > Billing and Usage, read-only: Actions
  minutes, Packages and Codespaces storage, Copilot seats, as tables.
- **Organization audit log:** Organizations > org > Audit Log, read-only and
  filterable by actor, action, repository and date (needs `read:audit_log`
  and an organization plan that offers the API).
- **SSH and GPG keys, SSH signing keys:** Account > Keys. List, add, delete.
- **Personal access tokens:** an organization owner can review, approve and
  deny fine-grained token requests, and revoke access, under Organizations >
  org > Token Requests. Creating a token has no API, so Account > Tokens
  opens the right GitHub page and the Workbench checks the result
  (section 18.1).
- **Sponsors:** People > person > Sponsor, and Account > Sponsors for your
  own sponsorships and sponsors, read and manage what the API allows.

What is left on github.com is only what GitHub offers no API for, and the
coverage table says so row by row (section 19): Marketplace purchases,
creating a token, changing your password or two-factor settings, and
enterprise-level billing. Each still gets an "Open on GitHub" row in its
natural place.

### 14.4 How to keep this list honest

The "nothing dropped" test (section 10) guards what exists. For what does not
exist yet, add a `PLANNED` table next to the tree table in
`workbench_tree.py`, with the rows in 14.1 and 14.2. Each row holds the
feature, its roadmap ID if any, and its future node, and is not shown in the
window. When one is built, it moves from `PLANNED` into the tree in the same
change. The generated Workbench reference can then list "coming later"
features from the same table.

## 15. Properties: Alt+Enter on anything

### 15.1 The rule

Every object the Workbench can show has a Properties sheet, and Alt+Enter
opens it from anywhere the object appears: a list row, a tree node, a search
result, a notification (the sheet of the thing the notification is about), a
line in the details pane that names an object (a label, a milestone, a person,
a linked pull request), and inside the PR review reader (the pull request, or
the comment or thread at the cursor).

Three routes, one command (`github.workbench.properties`):

- **Alt+Enter**, the File Explorer and Outlook habit for Properties.
- **Item > Properties...**, the last row of the Item menu.
- **Properties...**, the last row of every context menu (section 5, rule 6).

On a tree node, the sheet is the node's own object: the repository on
`owner/name`, the organization on an organization, the person on a person,
the milestone on a milestone, the project on a project. On a folder node
that is not an object (Needs My Attention, Search), Alt+Enter opens that
view's options: its columns, sort, default filter and refresh interval.

In the editor, the GitHub menu gains **Properties of This Repository...**,
which opens the Workbench on the repository's sheet. It has no default chord
in the editor (rule 7: editor chords are for the editor); the Workbench owns
Alt+Enter.

### 15.2 The shape of a sheet

- **A dialog parented to the Workbench,** so it never blocks the editor. Its
  title is the object's kind and name: "Issue #42 Properties - owner/name".
  The reader says the title; the Workbench says nothing on opening (GATE-13).
- **Pages on a `wx.Notebook`.** Ctrl+Tab and Ctrl+Shift+Tab move between
  pages, Ctrl+Page Down and Ctrl+Page Up too. The first page is always
  **General**. The pages per object type are in Appendix C.
- **Every fact is a focusable control with a label.** Read-only facts are
  read-only text boxes, never bare static text, so Tab reaches them and the
  reader reads them, and a braille user can pan through them. Dates are
  written out ("9 November 2026, 14:05, 3 hours ago"), never relative only.
- **Editable when you may, explained when you may not.** A field you have
  permission to change is a normal control. A field you may not change is
  read-only, and its F1 help and the line under it say why and what would
  change that: "Read only: changing labels needs triage access to
  owner/name. You have read access. An owner or admin can give it to you."
  (section 18.2).
- **Every list on a sheet is a real list.** Labels, assignees, reviewers,
  collaborators, teams, events, branches: a `wx.ListCtrl` or a check list, each
  row reading in full, for example "bug, checked" (GHManage 1.1.0's form),
  with type-ahead, Space to toggle, and Add..., Remove and Change... buttons
  where the list can change.
- **What you need does not have to exist yet.** Every picker ends with a
  New... row or button that creates the thing and uses it at once: New
  Label..., New Milestone..., New Project..., New Issue Type..., New Branch...,
  New Environment..., New Team..., New Discussion Category... (GHManage 1.1.0
  does this for milestones, labels and projects).
- **OK, Cancel, Apply.** OK saves and closes, Cancel discards, Apply saves
  and stays. Enter is OK and Escape is Cancel, so neither carries an access
  key (GATE-14). Only changed fields are sent.
- **Copy.** Every sheet has Copy as Text (all pages as plain text, for a
  note or an email) and Copy Link. Ctrl+C in a read-only field copies the
  field.
- **Open on GitHub** on every sheet, for the rare page GitHub shows that the
  API does not.
- **Several objects at once.** Alt+Enter on a multiple selection opens one
  sheet for all of them: "Properties of 5 issues". A field the same on all
  shows its value; a field that differs says "Mixed" and leaves it alone
  unless you change it. Check lists become three-state: "bug, on 3 of 5".
  Saving changes only the fields you touched, on every item, and the result
  says per item what happened (section 16.4).
- **Fresh, and honest about it.** The sheet loads current values when it
  opens and shows "Loaded at 14:05" in its status line. F5 on a sheet reloads.

### 15.3 Saving safely

- **Someone else's change is kept.** Before saving, the sheet compares what
  it loaded with what is on GitHub now (ETag or `updated_at`). A field
  someone else changed meanwhile is listed: "Changed on GitHub since you
  opened this: milestone is now 2027.2." For each, Keep Theirs or Use Mine.
  Fields nobody else touched save without asking.
- **Nothing is claimed that did not happen.** After saving, the Workbench
  reads the object again and compares. GitHub ignores some writes from
  people without access and still answers success (GHManage 1.1.0 found this
  for milestones, labels and assignees), so the only success message is one
  the re-read proves. A field that did not take says so, by name.
- **One sentence says what changed:** "#42: added bug, removed docs; milestone
  2027.1; assigned to kellylford." Spoken and brailled through the
  announcement service, since the reader cannot see a change on GitHub.
- **Undo.** Every save is a step in Edit > Undo GitHub Change (Ctrl+Z in the
  list, when focus is not in a text box), section 16.5.

## 16. Edit everything GitHub lets you edit

### 16.1 The rule

If GitHub's API can change it, the Workbench can change it, from the object's
Properties sheet, and from a menu row where it is common. Appendix C lists, per object type, every editable field and the
command that edits it. The coverage gate (section 19) keeps that list
complete as GitHub grows.

This replaces a rule in today's code. `items_provider.update_items` describes
batch work as "the one deliberate exception to the viewer's read-only rule",
limited to close, reopen and adding labels, with "no deletions". That rule
is lifted: removal and replacement are as available as adding, with the
safety of section 18.4 instead of a missing feature.

### 16.2 What can be changed on an issue or pull request

The full list is in Appendix C. The common ones, all on the General,
Organize and Conversation pages:

- **Title and description** (body), in a multi-line box with the same
  Markdown help as New Issue; Ctrl+Enter saves (GHManage's form).
- **State:** open, closed as completed, closed as not planned, closed as a
  duplicate of #n; reopen. For a pull request: open, closed, draft, ready
  for review.
- **Labels, assignees, milestone, issue type, projects,** each with its
  picker and New... row.
- **Project fields** for every project the item is in: status, iteration,
  dates, numbers, text, single-select, each by its own type of control
  (section 16.6).
- **Relationships:** parent issue, sub-issues and their order, blocked by,
  blocking, duplicates, linked pull requests and branches ("Development").
- **Pull request only:** base branch, reviewers (people and teams) and their
  removal, Copilot review, auto-merge and its method, merge queue,
  maintainers may edit, update branch.
- **Conversation:** lock with a reason, unlock, pin and unpin, transfer to
  another repository, subscribe and unsubscribe, hide (minimize) a comment
  with a reason, unhide, edit and delete your comments, reactions.

### 16.3 One key for every change: Alt+Enter

Jeff, 2026-11-09: "I want Alt+Enter, and typing should just move through
the list. I don't need fancy keys to modify specific properties, just bring
up the property sheet."

- **There are no per-property keys.** Every change to an object starts the
  same way: Alt+Enter, then the page. The sheet opens on General with focus
  on its first field, and Ctrl+Tab or Ctrl+1 to Ctrl+9 reach any page.
- **Typing always moves through the list** and the tree, to the first row
  whose text starts with what you typed, as in File Explorer. No letter is
  ever a command there, so a typed name can never change anything.
- **The menus still name every change** (Item > Labels..., Milestone... and
  the rest), for people who browse menus; those rows open the sheet at the
  right page and carry no key of their own.
- **The sheet remembers the last page** you used for each kind of object,
  so if you set milestones all morning, Alt+Enter on the next issue opens on
  Organize with focus in the Milestone list.

### 16.4 Many items at once

- **Select, then change.** Shift and Ctrl selection in the list (and Select
  All), then Alt+Enter for the combined sheet.
- **Every field works in batch** that GitHub lets you set per item: labels
  added and removed, assignees, milestone, type, projects and project
  fields, state with reason, lock, transfer, reviewers.
- **A preview before more than one item changes.** "Change 14 issues: add
  bug, remove triage, set milestone 2027.1. 3 of them already have bug."
  Enter goes ahead.
- **A result per item.** A results list (not a message box) shows each item
  with Done, Skipped (already so), or Failed and why. Copy Results copies it.
  Failed ones can be retried with one button.
- **Paced for the rate limit.** Batches respect GitHub's secondary rate
  limits, and the status bar shows progress ("Changing 6 of 14"), which is
  never announced except at the end.

### 16.5 Undo GitHub Change

- Every save records what it changed, before and after, in the session's
  GitHub change history (Account > Change History, section 18.5).
- **Edit > Undo GitHub Change** reverses the last one where GitHub allows
  it: labels, assignees, milestone, type, project fields, title, body,
  state, lock, pin, reviewers, branch protection and ruleset settings,
  repository settings, collaborator roles.
- A change GitHub cannot reverse (a deleted branch, a deleted release
  asset, a transferred issue in a repository you cannot reach) is marked
  "cannot be undone" in its confirmation before it happens, never after.

### 16.6 Projects, edited richly

Projects (GitHub's Projects, version 2) are where most of the "everything"
lives, so they get their own treatment:

- **A project node** in the tree for each project you can see: yours, each
  organization's, and those linked to the current repository.
- **Views as children:** each saved view of the project (table, board,
  roadmap) is a child node, and the list shows its items with its columns,
  its filter and its sort. A board view is read as a list grouped by its
  column field, one group node per column, so "Status: In Progress (5)" is a
  place you can go.
- **Every field type has its own control:** single select (a list),
  iteration (a list with dates: "Iteration 4, 4 to 17 November"), date (a
  date box), number, text, and the built-in fields (assignees, labels,
  milestone, repository, reviewers, linked pull requests). Moving an item to
  another column is changing its single-select field, from the sheet, a
  or Item > Move To.
- **Project properties:** title, short description, README, visibility
  (public or private), closed or open, template, linked repositories, and
  the project's access list (section 18.3).
- **Fields and views are editable:** add, rename, reorder and delete fields;
  add, rename and delete single-select options and iterations; create,
  rename, copy and delete views; set a view's filter, sort, group and
  visible fields.
- **Items:** add an issue or pull request by number or address, add a draft
  item, convert a draft to an issue, archive and restore, delete, reorder.
- **Workflows and status updates:** turn the project's built-in workflows on
  and off; post, edit and read status updates (on track, at risk, off
  track, with dates).

### 16.7 You and the object: star, watch, follow and the rest

Every sheet whose object you can have a relationship with has a **You** page,
right after General, holding every such relationship GitHub offers. Each is
also a context-menu row and a menu row, and each answers in one sentence
("Starred owner/name. 1,204 stars.").

- **Repositories:** Star and Unstar; add to or remove from your star lists
  (create, rename and delete lists too); Watch level: all activity,
  participating and mentions, ignore, or custom (issues, pull requests,
  releases, discussions, security alerts, each a check box); Fork; Pin to
  your profile and unpin; Pin in the Workbench and Favorite; Sponsor the
  owner where they accept it.
- **People:** Follow and Unfollow; Block and Unblock (and, for an
  organization owner, block from the organization); Sponsor; see whether
  they follow you; Report opens GitHub's report page, which has no API.
- **Organizations:** Follow and Unfollow; leave an organization you belong
  to; accept or decline an invitation; make your membership public or
  private.
- **Issues, pull requests, discussions, commits, releases:** Subscribe and
  Unsubscribe (with GitHub's reasons: all activity, or only when mentioned);
  react with each of the eight reactions, and remove yours; pin an issue to
  the repository; favorite and pin in the Workbench.
- **Gists:** Star and Unstar; Fork; Pin to your profile.
- **Notifications:** Mark Read, Mark Unread, Mark Done, Snooze, Unsubscribe
  from Thread, Ignore Repository, and Watch Level for its repository, all on
  the notification's own sheet as well as its context menu.
- **Topics:** Enter on a topic opens its repositories as a search. GitHub
  has no API for following a topic, so the coverage table says so.
- **Your own profile:** name, bio, company, location, website, social
  accounts, pronouns, hireable, profile README (edited in the editor), status
  text, emoji and busy flag with an expiry, pinned repositories and gists in
  order, contribution settings that the API offers; email addresses (add,
  remove, make public, primary is read-only through the API).

Batch works here too: select twelve repositories in a search and Star them,
or set their Watch level, in one step, with a result per row.

## 17. Filtering on every attribute

### 17.1 One filter, four ways in

The list's filter is one query. Four ways write it, and they stay in step:

1. **The filter box** (Ctrl+E or Ctrl+Shift+F): type GitHub's own search
   syntax, `is:open label:bug -label:wontfix milestone:2027.1 assignee:@me`,
   or plain words. Plain words filter the loaded list; qualifiers query
   GitHub.
2. **The Filter Builder** (Ctrl+Alt+F, or Edit > Filter Builder...): a dialog
   that lists every attribute of the current list's row type, each with an
   operator and a value picker filled from the repository (section 17.2).
   OK writes the query into the filter box, so people learn the syntax by
   watching it appear.
3. **The Filter menu** (View > Filter), for the everyday ones, each a checked
   row that combines with the others (GHManage 1.1.0's form): Assigned to Me,
   Assigned To..., Opened by Me, Opened By..., Mentions Me, Review Requested
   from Me, Reviewed by Me, No Assignee, No Milestone, No Label, No Project,
   No Type, Drafts, Has Conflicts, Checks Failing, Updated This Week, and
   Clear These Filters. The status bar and window title name what is on:
   "owner/name - 4 issues (open), assigned to me, no milestone."
4. **Show only items like this** on any cell: the context menu of a row
   offers Show Only, and Hide, for each value in it. "Show only label:bug",
   "Hide author:dependabot", "Show only milestone:2027.1". This is the
   fastest filter there is, and it teaches the syntax too.

Filters stay on as you move between repositories, as State does, until
cleared, and any filter can be saved: Save Search makes it a node under
Search > Saved Searches, and Pin makes it a node under Needs My Attention.

### 17.2 The Filter Builder

- One row per condition: attribute, operator, value.
- **Operators per type:** is, is not, any of, none of, has none
  (`no:label`), has any; before, after, between, in the last n days (dates);
  more than, less than, between (numbers); contains (text).
- **Values come from the repository:** its labels, milestones, assignable
  people, authors seen, projects and their field options, issue types,
  branches, reviewers and teams, so you choose rather than spell.
  `@me` is offered as "Me" for every person field.
- **Any of and none of** in one row write GitHub's comma and minus forms:
  `label:bug,ui`, `-label:docs`.
- **Or between groups** where GitHub search allows it (`OR` and brackets in
  issue search), and a plain note where it does not.
- **Sort and order** are part of the builder: created, updated, comments,
  reactions of each kind, interactions, and for projects any field.
- **Save as Search** and **Save as Default for This View** on the builder.

### 17.3 Every attribute, honestly

- **Server first.** Every attribute GitHub search can filter on is sent to
  GitHub, so the filter reaches items that were never in the loaded list.
- **Local where GitHub cannot.** A few attributes GitHub's search does not
  index (a project field on a list that is not a project view, a workflow
  run's duration, a release asset's size) are filtered over the loaded rows,
  and the status bar says so: "Filtered locally: 40 loaded. Load All to be
  sure." Load All fetches every page first.
- **The attribute lists per row type are in Appendix C,** in the Filter
  column. The highlights for issues and pull requests: state and state
  reason, type, labels, milestone, assignee, author, mentions, commenter,
  involves, team mentions, project and every project field, issue type,
  parent issue, has sub-issues, blocked or blocking, linked pull request,
  created, updated, closed and merged dates, comment count, each reaction's
  count, interactions, locked, archived repository, draft, review state,
  review requested from a person or team, reviewed by, base and head
  branch, checks and status, merge state, language, visibility, and
  "has none" for every list attribute.

### 17.4 Grouping

View > Group By puts the list's groups in the tree as child nodes, which a
screen reader reads far better than group rows inside a list: Issues > by
Milestone > 2027.1 (12). Group by label, milestone, assignee, author, type,
project status or any project field, repository (in cross-repository
lists), review state, or workflow. Ungroup returns the flat list.

## 18. Permissions, rigidly and completely

Permissions have two halves, and the Workbench does both: knowing what
**you** may do and getting you what you need, and managing what **others**
may do on everything GitHub lets you control.

### 18.1 Your permissions: one place, all at once

GHManage 1.1.0 added Help > GitHub Permissions...: every extra permission,
what it is for, whether `gh` has it, and one command that adds every one that
is missing. The Workbench does the same and goes further.

- **Account > GitHub Permissions...** lists every permission any Workbench
  feature can use, grouped by what it unlocks, each row reading in full:
  "project: set an item's projects and edit project fields. You have it."
  The scopes it covers: `repo`, `public_repo`, `read:org`, `admin:org`,
  `write:org`, `project`, `read:project`, `notifications`, `user`,
  `user:follow`, `user:email`, `gist`, `workflow`, `write:packages`,
  `read:packages`, `delete:packages`, `delete_repo`, `admin:repo_hook`,
  `admin:org_hook`, `admin:public_key`, `admin:gpg_key`,
  `admin:ssh_signing_key`, `security_events`, `codespace`, `copilot`,
  `read:audit_log`. Optional, risky ones (`delete_repo`, `delete:packages`,
  `admin:org`) are unchecked by default and each says why you might want it.
- **One step adds every missing one.** For the OAuth device sign-in (PR 1794),
  Add Permissions... runs the device flow again asking for the old scopes plus
  the new ones, and you approve once on GitHub. For a classic token, it opens
  GitHub's token page with the scopes listed to copy. For a fine-grained
  token, it lists the repository and organization permissions to set, by
  GitHub's names ("Issues: Read and write"). For `gh`, Copy Command gives
  `gh auth refresh -h github.com -s ...`, GHManage's form.
- **Check Again** reads the permissions again and says what changed.
- **Missing a permission at the moment you need it** gives a box with the
  one permission, Add It, and All Permissions..., never a bare error.
- **Fine-grained tokens and GitHub Apps** do not list scopes in a header, so
  the Workbench asks GitHub per object instead (section 18.2) and says
  "This token's permissions are set on GitHub" rather than guessing.

### 18.2 Knowing before offering

- **Every object says what you may do with it.** GitHub's GraphQL API answers
  per object: `viewerPermission` on a repository (admin, maintain, write,
  triage, read), and `viewerCanUpdate`, `viewerCanDelete`, `viewerCanClose`,
  `viewerCanReopen`, `viewerCanReact`, `viewerCanSubscribe`,
  `viewerCanMinimize`, `viewerCanLabel` and their kin on issues, pull
  requests, comments and discussions. The Workbench fetches these with the
  object and keeps them with it.
- **Greyed with a reason, never hidden.** A row or field you cannot use is
  greyed (menus) or read-only (sheets), and its help says exactly why: the
  role you have, the role it needs, and who can grant it. "Delete Branch
  needs write access and the branch is protected by the ruleset Main
  branch; only maintainers may bypass it."
- **Every write declares what it needs.** In the wx-free action table, each
  write command and each editable sheet field names its requirement: a
  repository role, an organization role, a token scope, a `viewerCan` field,
  a plan feature, or a combination. A test fails when a write command or
  editable field has none, so a new write cannot ship without knowing who
  may use it (GATE-GITHUB-PERM, section 18.6).
- **Effective access, explained.** On any repository, Account > What Can I
  Do Here? lists your effective role and where it comes from: "Write,
  through the team Docs; Read, as the organization's base permission. The
  higher one counts."

### 18.3 Managing access: every object that has it

Every object with an access list gets an **Access** page on its Properties
sheet, the same shape everywhere: a list of who has access (people, teams,
roles, apps), each row "kellylford, person, Maintain, direct" or "Docs, team,
Write, through organization"; and Add..., Change Role..., Remove, and
Show Pending Invitations. Appendix D is the full catalogue; in brief:

- **Repositories:** collaborators and their role (read, triage, write,
  maintain, admin, and the organization's custom repository roles); teams and
  their role; outside collaborators; pending invitations (cancel, change
  role); the effective access of anyone, and why.
- **Organizations:** members and their role (member, owner), billing
  managers, security managers, moderators, outside collaborators, pending
  invitations and failed invitations; the base repository permission;
  member privileges (who may create public, private and internal
  repositories, fork private ones, create Pages sites, create teams, change
  visibility, delete and transfer repositories, invite outside
  collaborators); organization roles and custom repository roles; two-factor
  requirement (read).
- **Teams:** name, description, privacy (visible or secret), parent team,
  notifications on or off; members and their role (member, maintainer); the
  team's repositories and its role on each; the team's projects and role.
- **Branches and tags:** classic branch protection and rulesets in full
  (section 18.3.1).
- **Environments:** required reviewers (people and teams, up to six), prevent
  self-review, wait timer, which branches and tags may deploy, whether admins
  may bypass, and the environment's own secrets and variables.
- **Actions:** which actions may run (all, local only, or selected, with
  patterns for allowed actions and reusable workflows), the default
  `GITHUB_TOKEN` permission (read, or read and write), whether Actions may
  create and approve pull requests, approval for workflows from forks and
  first-time contributors, artifact and log retention, and runner groups and
  which repositories may use them.
- **Projects:** visibility, and who may read, write or administer it,
  people and teams, plus the organization's base project role.
- **Packages:** visibility, and which repositories, teams and people may read,
  write or administer it, and whether it inherits access from its repository.
- **Codespaces:** who in an organization may create them, and which
  repositories they may be created for; a repository's devcontainer and
  machine types (read).
- **Security:** private vulnerability reporting on or off, Dependabot alerts
  and security updates on or off, secret scanning and push protection on or
  off, code scanning default setup, and who may dismiss alerts.
- **Deploy keys and webhooks** (section 14.3), each read-only or
  read-write, each event chosen.
- **Gists:** public or secret.
- **Interaction limits:** limit who may comment, open issues and open pull
  requests in a repository or across an organization (existing users,
  contributors only, collaborators only) and for how long.

#### 18.3.1 Branch protection and rulesets, every combination

These hold the most combinations GitHub offers, so their sheet is laid out
for it:

- **Target:** branch or tag patterns to include and exclude, the default
  branch, all branches; for organization rulesets, which repositories by
  name pattern or property.
- **Enforcement:** active, evaluate (report only), disabled.
- **Bypass list:** roles, teams and apps, each "always" or "for pull requests
  only".
- **Rules, each a check box with its settings:** restrict creation, updates
  and deletion; require linear history; require deployments to succeed (which
  environments); require signed commits; require a pull request (approvals
  needed, dismiss stale approvals, require code owner review, require
  approval of the most recent push, require conversation resolution, allowed
  merge methods); require status checks (which checks, from which app,
  strict or not); block force pushes; require code scanning results (tool,
  severity); require a merge queue (method, group size, wait times, build
  concurrency); commit message, author email, committer email and branch
  name patterns; file path, extension and size restrictions (push rulesets).
- **Classic branch protection** stays editable for repositories that use it,
  on the same sheet, with Convert to Ruleset... where GitHub allows.
- **Read it as sentences.** A Summary page writes the whole rule set in plain
  words: "On main: changes need a pull request with 2 approvals including a
  code owner; checks build and test must pass; force pushes are blocked;
  maintainers may bypass." That page is the one people will read first.

#### 18.3.2 All combinations: matrices and bulk changes

"All combinations and permutations" means the Workbench can answer and change
access from any side:

- **Who can do what here?** On a repository, organization, team, project or
  package: everyone with access and their role, filterable by role and by
  source (direct, team, organization base).
- **What can this person do?** On a person or team in an organization: every
  repository and their role on each, filterable, sortable by role.
- **The access matrix.** Organizations > org > Access Review: a list with one
  row per person and repository pair, columns for role and source, filterable
  on every column (section 17), exportable as CSV, readable row by row. This
  is the accessible form of a grid nobody can read with a screen reader.
- **Bulk changes, any direction.** Give a team Write on 12 repositories;
  remove an outside collaborator from all of an organization's repositories;
  copy one repository's collaborators, teams, labels, milestones, branch
  rules and environments to others; apply one ruleset to every repository
  matching a pattern. Each shows the full list of changes before anything
  happens (section 18.4), and a result per change after.
- **Templates of access.** Save a repository's access, labels, rules and
  settings as a named template under Tools > Workbench Options > Templates,
  and apply it to a new or existing repository.

#### 18.3.3 Teams, end to end

Today QUILL can only read which teams have access to a repository
(Explore's Collaborators and Team Access view), and `repo_admin.py` still
carries the old decision "Organizations in, Teams out". This PRD overrules
it: teams are how organizations give access, so the Workbench manages them
completely, through GitHub's 32 team operations (Appendix E, REST: teams) and
the team mutations and viewer fields of Appendix F.

- **Where teams live in the tree:** Organizations > org > Teams, shown as
  GitHub nests them, so a child team is a child node ("Docs (5 members, 3
  child teams)"). People > My Teams lists every team you belong to, across
  organizations. Needs My Attention > Review Requests gains "for my teams",
  split from the ones asked of you by name.
- **Creating a team:** Ctrl+N on the Teams node opens a new team's sheet:
  name, description, visibility (visible or secret), parent team,
  notifications on or off, its first members and maintainers, and its first
  repositories with a role on each. The preview reads the whole team back
  before it is made.
- **The Team sheet** (Alt+Enter on any team, wherever it appears: the tree,
  an Access page, a review request, a mention):
  - **General:** name, slug (read-only), description, visibility, parent
    team, notifications, created, and "You are a maintainer of this team".
  - **Members:** every member with their role (member or maintainer) and
    whether they belong directly or through a child team; pending
    invitations; Insert adds people (several at once), F2 changes a role,
    Delete removes.
  - **Repositories:** every repository the team can reach and its role
    (read, triage, write, maintain, admin, or a custom role); Insert adds
    repositories by name or pattern, F2 changes the role, Delete removes.
  - **Projects:** the projects the team can reach and its role on each.
  - **Child Teams:** add, move under another parent, remove.
  - **Code Review:** code review assignment on or off, round robin or load
    balance, how many reviewers, whether to notify the whole team, and
    members to skip.
  - **Identity Provider:** for organizations that sync teams with an
    identity provider, the linked groups (read, and linked or unlinked where
    GitHub allows).
  - **Danger Zone:** delete the team (tier 3; its child teams move up, and
    the preview names every repository that loses the team's access).
- **What can this team do?** The Repositories page sorted by role, and the
  access matrix (18.3.2) filtered to the team, answer it from the team's
  side; a repository's Access page answers it from the repository's side.
- **Every combination, in batch:** add one person to many teams, many people
  to one team, give one team a role on many repositories, copy one team's
  repositories and roles to another, or move a set of people from one team
  to another, each with the preview and a result per change.
- **Teams in filters:** `team-review-requested:org/docs` and `team:org/docs`
  in the Filter Builder, with the organization's teams as the values, and
  Show Only on any team name in a row.
- **Permissions to manage teams:** organization owners manage every team;
  team maintainers manage their own team's members and settings; members can
  create teams when the organization's member privileges allow it
  (Appendix D). The sheet greys what you cannot change and says which of
  those you are.

### 18.4 Rigid control: nothing risky without a preview

Every write command is in one of four tiers, set in the action table and
tested:

| Tier | Examples | What happens |
|---|---|---|
| 0, organizing | labels, assignees, milestone, project fields, reactions, subscribe | Saves at once; undoable |
| 1, visible to others | comments, close and reopen, review, request reviewers, edit title | Saves at once by default; Workbench Options can ask first |
| 2, access and settings | roles, teams, invitations, branch rules, rulesets, Actions permissions, environments, visibility, webhooks, interaction limits | A preview lists every change in words; Enter applies; undoable where GitHub allows |
| 3, destructive or hard to reverse | delete a repository, branch, tag, release, package, project, team, environment, webhook; transfer; make a private repository public; remove an admin or owner; turn off branch protection | The preview, then the object's name typed to confirm, as Delete Repository does today |

Guards that hold whatever the tier:

- **No self-lockout.** Removing your own admin role, the last owner of an
  organization, or the only admin of a repository is refused with the reason,
  and the sheet says who else could do it.
- **No surprise exposure.** Making a repository, project, package or gist
  public says what becomes visible (open issues, Actions logs, secrets
  names never, wiki) before it happens.
- **Batch deletes list every item** in the preview, and never run unattended.
- **Read-only accounts.** Tools > Workbench Options > Accounts can set an
  account to Read Only, Organize (tiers 0 and 1), or Full. A Read Only account
  is ideal for demonstrating, teaching or reviewing someone else's
  organization: every write is greyed, with "This account is read only in
  the Workbench" as the reason.
- **Safe Mode** (`QUILL_SAFE_MODE=1`) makes every account Read Only for the
  session.

### 18.5 A record of every change

- **Account > Change History** lists every write the Workbench made for each
  account: when, what object, what changed before and after, the tier, and
  whether GitHub confirmed it. Filterable like any list; Copy and Save as CSV.
- Kept on this device in the Workbench's own store, written atomically, for
  as long as Workbench Options says (default 90 days), and clearable from
  Privacy and opt-ins. Secret values and tokens never appear in it.
- **Undo GitHub Change** (section 16.5) works from this list too, on any
  row GitHub allows.

### 18.6 Gates

- **GATE-GITHUB-PERM:** every write command and every editable sheet field
  declares its requirement and its tier (section 18.2 and 18.4); a test fails
  on one without.
- **The action table drives the greying,** so menus, context menus,
  Shift+F1 and sheets cannot disagree about what you may do.
- **The network egress audit** gains a row for each new kind of endpoint (the
  access, ruleset, webhook, key and audit-log APIs). They are all to
  `api.github.com`, which the audit already knows, but the inventory names
  them so the review is real.

## 19. "Absolutely everything", measured

Jeff's brief is that anything doable on GitHub has a way here. A list written
by hand goes stale the week GitHub adds a feature, so coverage is measured
against GitHub's own description of itself:

- **The source:** GitHub publishes its REST API as an OpenAPI description
  (`github/rest-api-description`) and its GraphQL schema. A snapshot of both
  is vendored under `quill/data/github_api/`, refreshed by a script on
  purpose, never fetched by the app or by tests.
- **The coverage table:** `quill/core/github/api_coverage.json` classifies
  every REST operation and every GraphQL mutation (and the queries the
  Workbench reads) as one of:
  - `covered`: the command id or sheet field that does it;
  - `planned`: its row in the `PLANNED` table (section 14.4) and its future
    home;
  - `no_api_needed`: low-level plumbing the user never meets as such (Git
    trees and blobs, which Commit Multiple Files uses underneath; emojis;
    Markdown rendering; meta);
  - `out_of_scope`: GitHub Enterprise Server administration, and GitHub App
    installation internals, each with a one-line reason.
- **GATE-GITHUB-COVER:** a new operation in a refreshed snapshot is `missing`
  and fails until somebody classifies it. The `planned` list may only shrink
  release over release, like every other backlog gate. Rostered in
  `platform_report`.
- **The generated reference** (`docs/github/workbench-reference.md`) gains a
  "Everything GitHub can do, and where" chapter from the same table, by
  GitHub's own category names: Actions, Activity, Billing, Branches, Checks,
  Code scanning, Codespaces, Collaborators, Commits, Copilot, Dependabot,
  Dependency graph, Deploy keys, Deployments, Discussions, Gists, Interactions,
  Issues, Labels, Milestones, Organizations, Packages, Pages, Projects, Pull
  requests, Reactions, Releases, Repositories, Rulesets, Search, Secret
  scanning, Security advisories, Sponsors, Teams, Users, Webhooks, Wikis.
  Someone asking "can QUILL do X?" gets the answer and the key in one place.
- **Wikis** have no API; GitHub serves them as a Git repository
  (`owner/name.wiki.git`). The Workbench reads and writes them through that
  repository (clone, edit in the editor, commit), so they are `covered` by the
  Git route, not left out.

## 20. Phases for sections 15 to 22

These follow Phase 5 and come before the old windows retire, each its own PR
with every gate green. Phase 0's quick wins can take a first slice of each.

- **Phase 7 - the Properties engine (medium).** The wx-free sheet model
  (`quill/core/github/properties.py`: pages, fields, requirement, tier,
  loader, saver), the one dialog that renders any model, Alt+Enter and the
  Properties rows, conflict check, verify after save, the change sentence.
  First sheets: issue, pull request, repository, label, milestone.
- **Phase 8 - every object's sheet (large, several PRs).** Appendix C row by
  row, in this order: items and their organizing (GHManage parity first:
  milestone, labels, assignees, projects, title and body), projects and
  their fields and views, branches and rules, releases and assets, Actions,
  people, teams and organizations, security, the rest. Batch
  sheets with the first PR.
- **Phase 9 - filtering (medium).** The Filter menu toggles, Show Only and
  Hide on cells, the Filter Builder, Group By as tree nodes, local filtering
  with its honest status line.
- **Phase 10 - permissions (large).** GitHub Permissions with one-step add,
  `viewerCan` fetching and greying with reasons, GATE-GITHUB-PERM, tiers and
  previews, read-only accounts, Change History and Undo GitHub Change, then
  the Access pages and the access matrix and bulk changes.
- **Phase 11 - coverage (small, then ongoing).** The vendored snapshot, the
  coverage table, GATE-GITHUB-COVER, and the generated chapter. Starting it
  early is useful: its `missing` list is the honest backlog for Phases 7
  to 10.
- **Phase 12 - templates (medium, two PRs).** First, filling issue forms and
  discussion forms natively, with golden body tests, which removes
  "link-only". Then the Templates node, the builder sheets, the chooser,
  `interop_github.py` with round-trip tests against real forms, the checks,
  starters, conversions, saving, Copy to Repositories, and community files.
- **Phase 13 - thinking further (section 22; several PRs, in this order).**
  The API Console first (it is the safety net for everything else), then
  Read as Document and the post checks, Watches, the editor commands, lists
  in and out, View As Role and Compare Roles, Dry Run and the practice
  repository, then the missing GitHub features of 22.1 as the coverage gate
  lists them.

## 21. Building templates: issue forms, pull request templates and more

### 21.1 Where it stands today

- `quill/core/github/issue_templates.py` reads Markdown issue templates
  (front matter: name, about, title, labels, assignees), and New Issue...
  offers them.
- **A YAML issue form is "link-only":** its row says "open in GitHub to fill
  its structured fields." So the richest kind of template, the one most
  projects now use, cannot be filled in QUILL at all, and nothing in QUILL
  can build one.
- QUILL already owns an accessible form engine: `quill/core/forms`, the QAF
  model shared with QUILL Accessible Forms, with BFL (forms written as plain
  text), Fill It In Yourself, accessibility checks, and interop with
  SurveyJS and XLSForm. Templates build on it rather than beside it.

### 21.2 What GitHub offers, all of it covered

| Kind | Where it lives | What it holds |
|---|---|---|
| Issue form | `.github/ISSUE_TEMPLATE/*.yml` | name, description, title, labels, assignees, projects, type; body of markdown, input, textarea, dropdown and checkboxes elements, each with id, label, description, placeholder, value, render, options, multiple, default, and required validation |
| Markdown issue template | `.github/ISSUE_TEMPLATE/*.md` | front matter (name, about, title, labels, assignees) and a Markdown body |
| Template chooser | `.github/ISSUE_TEMPLATE/config.yml` | whether blank issues are allowed; contact links (name, URL, about) |
| Pull request template | `pull_request_template.md` in the root, `docs` or `.github`; several in `PULL_REQUEST_TEMPLATE/` | a Markdown body; with several, chosen by the `template=` address parameter |
| Discussion category form | `.github/DISCUSSION_TEMPLATE/<category>.yml` | the issue form schema, for one discussion category |
| Organization defaults | the organization's `.github` repository | every kind above, used by repositories that have none of their own |
| Community health files | root, `docs` or `.github` | CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, GOVERNANCE, FUNDING.yml, CITATION.cff, CODEOWNERS |

### 21.3 The Templates node and its sheets

- **Repository > Templates** in the tree lists every template the repository
  has, and those it inherits from its organization (marked "inherited from
  org/.github"), one row each: "Bug report, issue form, adds bug and triage,
  6 fields, 3 required." Organizations > org > Templates does the same for
  the organization's defaults.
- **Alt+Enter on a template** opens its sheet:
  - **General:** name, description, file name, kind; the title prefix; the
    labels, assignees, projects and issue type it applies, each with its
    picker and New... row. A label that does not exist yet is flagged and
    offered to be created, since GitHub silently drops labels that do not
    exist.
  - **Fields:** the form's elements as a list, one row each: "Steps to
    reproduce, long text, required." Add Field... asks the type (short text,
    long text, dropdown, check boxes, instructions), then opens that field's
    sheet. Alt+Up and Alt+Down move a field; Duplicate and Delete do what
    they say.
  - **Each field's sheet:** label, description, placeholder, default value,
    id (made from the label, editable, checked for uniqueness), required;
    for long text, render as code in a language (shell, YAML and so on); for a
    dropdown, its options in order, multiple choice, and default; for check
    boxes, each option and whether that one is required; for instructions,
    the Markdown text.
  - **Preview:** the form exactly as a person filing an issue will meet it,
    filled in with the keyboard, using Fill It In Yourself. The issue body it
    would produce is shown below, as GitHub will write it.
  - **Checks:** the problems list for this template (section 21.5).
  - **Source:** the YAML or Markdown, read-only, with Open in Editor.
- **The Chooser sheet** (Repository > Templates, Alt+Enter on the node):
  blank issues allowed or not; contact links as a list to add, edit, remove
  and reorder; and the order templates appear in. GitHub orders them by file
  name, so Move Up and Move Down rename with number prefixes ("01-bug.yml")
  and say so.

### 21.4 Three ways to build one

1. **The builder above,** for people who want every option labelled.
2. **As plain text, in the editor.** Write the form in BFL, the plain-text
   form language QUILL's Forms already reads, and Save as GitHub Issue
   Form... writes the YAML. Open a GitHub issue form and it reads back as
   BFL. A new interop module, `quill/core/forms/interop_github.py`, maps the
   QAF model to GitHub's schema and back, beside the SurveyJS and XLSForm
   ones; where a QAF feature has no GitHub equivalent (scores, conditions,
   payments), the export says which and leaves it out.
3. **The YAML itself,** in the editor, with Check This File (Navigate > Code)
   validating it against GitHub's issue form rules as you work, in the
   Problems pane.

And three ways to start: **a starter** (bug report, feature request,
question, documentation, accessibility bug report with the screen reader,
browser and assistive technology fields people forget to ask for, security
report pointing to private reporting); **a copy** of a template from any
repository you can read; or **a conversion**: a Markdown template to an
issue form (its `###` headings become long-text fields), an issue form to
Markdown (which loses the structure, and says so first), and SurveyJS,
XLSForm or QAF forms where their field types map.

### 21.5 Checks that catch what GitHub only reports after you commit

GitHub shows a broken issue form as an error on its template chooser, after
it is on the default branch. The Workbench checks before saving, with each
problem on its line:

- Required keys: name and description; at least one field that is not
  instructions; every field but instructions has a label.
- Ids and labels unique; ids only letters, numbers, hyphens and underscores.
- Dropdowns and check boxes have options, and the options are unique and not
  "None", which GitHub reserves.
- Labels, assignees, projects and type exist and you may set them.
- Accessibility, from the Forms checks: a placeholder is never the only
  label, descriptions are short, required fields are marked, instructions
  use headings in order, and link text says where it goes.

### 21.6 Saving

- **Save** commits the template through the Commit to GitHub route, to the
  default branch, or to a new branch with a pull request (decision 18). The
  sheet says templates only take effect from the default branch.
- Needs write access to the repository, or to the organization's `.github`
  repository for defaults (section 18.2). It is tier 1: visible to others.
- **Copy to Repositories...** applies one template, or a whole set with its
  chooser, to many repositories at once, with the preview and the result per
  repository of section 18.3.2.

### 21.7 Filling every kind natively

- **New Issue... with an issue form** opens the form as a real dialog: each
  field a labelled control, required fields marked and checked, errors next
  to their fields and announced, dropdowns as lists, check boxes as check
  boxes. Submit writes the body exactly as GitHub would: each field as a
  `### Label` heading and its answer, `_No response_` for an empty optional
  field, check boxes as `- [X]` and `- [ ]`, and long text rendered as code
  fenced in its language. It applies the template's title prefix, labels,
  assignees, projects and type. "Link-only" goes away.
- **New Discussion...** in a category with a form does the same.
- **New Pull Request...** offers the repository's pull request templates when
  there are several, and fills the one chosen into the description.
- **Possible duplicates** (Appendix B) are still checked when filing.
- **Golden tests** pin the body format against bodies GitHub produced, so a
  form filed from QUILL is indistinguishable from one filed on the web.

### 21.8 Community health files

The other files GitHub reads from a repository get the same treatment on
Repository > Templates > Community Files: each listed as present, inherited
or missing (the Community Profile checklist, Appendix A); Create from
starter... for each; edited in the editor; and FUNDING.yml, CITATION.cff and
CODEOWNERS each with a small sheet of their own fields (sponsor platforms
and names; title, authors, version, DOI; path patterns and their owners,
with a check that every owner exists and has write access).

## 22. Thinking further: what else GitHub does, and what only this Workbench could do

Jeff, 2026-11-09: "think very creatively here, as I don't think everything is
captured." This section is a second sweep in two directions: GitHub features
the sections above still leave out, and things an accessible Workbench can
do that github.com cannot.

### 22.1 GitHub features still missing above

Each with its home, so it lands in the `PLANNED` table (section 14.4) and the
coverage gate (section 19) from day one.

- **Copilot, all of it.** Coding agent sessions: assign an issue, watch the
  session's log as it works, steer it with a comment, stop it, review its
  pull request (Item > Copilot). Copilot code review settings per repository.
  Custom instruction files (`.github/copilot-instructions.md`,
  `.github/instructions/*.instructions.md`, `AGENTS.md`), each with a sheet and
  edited in the editor. Organization Copilot seats, policies, content
  exclusions and usage metrics as tables (Organizations > org > Copilot).
- **GitHub Models.** Prompt files (`.prompt.yml`) in a repository: a sheet for
  the model, messages, variables and test data; run a prompt against a model
  and compare models side by side as text; evaluations as a results list.
- **Building workflows.** The template builder's approach applied to Actions
  YAML (Repository > Actions > New Workflow...): starter workflows from
  GitHub, triggers as check boxes with their filters, jobs as a list, steps
  as a list, each step's action found by search with its inputs as labelled
  controls, versions pinned to a commit with one choice, permissions per job
  (section 18.3), and the job graph read as "test needs build". Required
  workflows for an organization. Check This File for workflow YAML.
- **Dependabot configuration** (`.github/dependabot.yml`): ecosystems,
  directories, schedule, groups, ignore rules, reviewers, labels, private
  registries, as a sheet; and the `@dependabot` comment commands (rebase,
  recreate, ignore this major version) as Item > Dependabot rows on its pull
  requests.
- **Merge conflicts.** When a pull request conflicts, Item > Resolve
  Conflicts... checks out the branches in a local worktree, opens each
  conflicted file in the editor at its first conflict, offers Keep Ours,
  Keep Theirs, Keep Both per conflict, and commits the result. GitHub's web
  conflict editor is one of its least accessible pages.
- **Pull request review, the remaining pieces:** mark a file as viewed and
  filter to unviewed files; multi-line and file-level comments; hide
  whitespace changes; split or unified diff as two ways of reading; review
  one commit at a time; "changes since your last review".
- **Task lists inside bodies.** The `- [ ]` items in an issue's body are a
  list on the issue's sheet: check one off and the body is updated; convert
  an item to a sub-issue.
- **Merge queues as places.** Repository > Merge Queue: each queued branch's
  entries in order, with their checks, Remove and Jump to front (admins).
- **Commit statuses** (Item > Set Status... on a commit) for people who drive
  their own automation, and deployment protection rules from apps (read).
- **Repository creation, fully:** owner, name (checked as you type),
  description, visibility, a README, a `.gitignore` from GitHub's list, a
  license from GitHub's list with each license explained in plain words, a
  template with or without all its branches, and the starting labels,
  milestones, rules and access from a saved template (section 18.3.2).
- **Moving work in and out:** export your account's data or an organization
  migration archive (where the API allows) and download it; import issues
  from CSV with a preview (section 22.7); fork with only the default branch.
- **Git LFS:** files tracked, storage used, and file locks (who holds which
  lock, lock, unlock, force unlock with permission).
- **Insights in words:** Pulse for a week or month ("12 pull requests
  merged by 5 people"), forks with ahead and behind as the network graph's
  readable form, traffic referrers, popular paths, clones, and the
  dependency graph and dependents.
- **Your contributions:** the contribution graph as a table by week and day,
  with streaks, totals and the repositories contributed to, read row by row.
- **GitHub Apps and OAuth apps:** apps installed on an organization or
  repository, which repositories each may reach (add, remove), suspend and
  unsuspend, and requests to install; apps you have authorized.
- **OpenID Connect:** the subject claim template for an organization or
  repository, for people deploying to clouds from Actions.
- **Security, the remaining pieces:** push protection bypass requests and
  alert dismissal requests to review and decide; Copilot Autofix suggestions
  on code scanning alerts, applied as a pull request; the organization
  security overview as a table; dependency review on a pull request.
- **Discussions, the remaining pieces:** spotlight, category sections, and
  polls built in the template builder's style.
- **GitHub status:** a status bar cell and Help > Is GitHub Working? that
  read githubstatus.com (a new egress row, with consent).

### 22.2 The escape hatch: an API Console

Whatever this plan misses, and whatever GitHub ships next week, should still
be reachable. **Tools > GitHub API Console...** is a dialog where you choose
REST or GraphQL, write the path or query (with completion from the vendored
API description, section 19), see what permission it needs, and send it as
the current account. The answer is shown as a tree you can walk with the
arrow keys, each node reading "title: Fix the crash", with Copy Value, Copy
Path and Save as JSON. Writes go through the same tiers and previews as
everything else, and land in Change History. Any request can be saved as a
named command, and a saved command can be given a key and put on the Item
menu, so a power user can add the feature they need the day they need it.

### 22.3 GitHub from the editor, where the code is

The Workbench is for GitHub; the editor is where people already are. These
editor commands open no window unless they must (QUILL and QUILL Lite both):

- **Copy GitHub Link to This Line** (or selection), as a permalink to the
  commit.
- **Who Changed This Line?** speaks the last commit, author and date for the
  line, and a second press opens the pull request that brought it.
- **Open This Line on GitHub,** and **Open the Pull Request for This Line.**
- **New Issue from Selection...** files an issue quoting the selection with
  its permalink.
- **Issues Mentioning This File** opens the Workbench filtered to them.
- **Comment on This Line in the Open Pull Request** when the document is part
  of a pull request checked out in a worktree.
- References in any document (`#42`, `owner/name#42`, `@person`, commit
  hashes) are recognized; Alt+Enter on one opens its Properties sheet.

### 22.4 Reading GitHub like a document

- **Read as Document** (Item menu) opens an issue, pull request or discussion
  thread as a read-only document in the editor: one heading per comment
  ("kellylford, 9 November, 14:05"), quotes as quotes, code as code, so
  heading navigation, find, Read Aloud, braille and every reading tool QUILL
  has work on a GitHub conversation. Export it to Word, EPUB or DAISY to read
  later or offline.
- **Comment boxes are editors.** Mentions (`@`), references (`#`) and emoji
  (`:`) complete as you type; Markdown preview reads aloud; saved replies
  insert; attachments upload.
- **What you post is accessible.** Before a comment, issue, pull request or
  release posts, the Workbench checks it as QUILL checks documents: an image
  with no alt text (and an offer to describe it with AI), headings out of
  order, link text like "here", a table with no header row. It offers, never
  blocks.
- **Pictures, diagrams and math in issues** are read the way QUILL reads
  them in Markdown pages: Mermaid diagrams as their accessible text, math as
  speech, and images described on request.
- **Braille-shaped rows.** A Workbench Options choice makes list rows short
  enough for a 40-cell display: "#42 open bug Fix crash" instead of the full
  sentence.

### 22.5 Watches: tell me when it happens

GitHub's notifications are about threads. People also want to know about
moments. **Watch This...** on any object sets a watch, kept in the
Workbench and listed under Needs My Attention > Watches:

- this pull request's checks finish, or any check fails;
- this run finishes;
- this pull request is approved, merged, or gets a new review;
- this issue is closed, or gets a comment from a particular person;
- a release is published in this repository;
- my rate limit is back;
- this person opens a pull request in this repository.

When it happens, the Workbench says it in one sentence and plays the
moment's sound, through the shared action-feedback channels (sound, speech,
both, silent), even while you are writing in the editor. Watches check on the
same schedule as notifications (decision 21) and cost no extra requests
where an ETag says nothing changed.

### 22.6 Plain language in, a previewed batch out

The Command Key work (PRs 1796, 1800, 1801) gives QUILL a way to say a
command. The Workbench gives it GitHub actions to say:

- "Close every issue labeled stale that nobody touched in 90 days."
- "Give the Docs team write on every repository whose name starts with
  quill."
- "Which pull requests are waiting on me, oldest first?"

A sentence becomes a query and a set of changes, shown in the same preview
as any batch (section 16.4), with the same tiers; nothing runs until Enter.
AI is also offered where it saves real work: suggest labels and a type for a
new issue, explain a ruleset or an access list in plain words, draft a
reply, summarize a long thread, explain why a run failed (today's What
Failed, everywhere).

### 22.7 Lists in and out

- **Export any list** as CSV, Excel, Markdown table or a QUILL table document,
  with the columns showing: issues, members, the access matrix, alerts,
  runs, Change History.
- **Import issues** from CSV or a spreadsheet: map columns to title, body,
  labels, assignees, milestone, type and project fields, preview every issue,
  create them with a result per row.
- **Issues from a task list:** select lines in a document and New Issues from
  Lines makes one issue per line, optionally as sub-issues of a parent.
- **Copy settings between repositories:** labels, milestones, templates,
  rules, environments, access, Actions permissions and repository settings,
  each a check box, with the preview (section 18.3.2).

### 22.8 Learning GitHub, safely

- **GitHub words on F1.** Every GitHub term in the Workbench (fork, rebase,
  squash, ruleset, environment, triage) has a one-paragraph explanation in
  the help catalogue, and F1 on any row offers it.
- **Tutorials:** Help > Tutorials gains GitHub lessons in the shared
  tutorials engine: your first issue, your first pull request, reviewing,
  re-running a failed run, setting up a template, giving someone access.
- **A practice repository.** Help > Practice on GitHub... creates a private
  repository in your account named for practice, seeds it with issues, a
  pull request and a failing run, and offers to delete it when you finish, so
  people can learn tier 3 actions on something that does not matter.
- **Dry Run,** a Workbench-wide switch on the status bar: every write shows
  its preview and stops there, saying "Dry run: nothing was changed." Useful
  for learning and for checking a big batch twice.

### 22.9 Several accounts, side by side

- **Compare Accounts:** what each of your signed-in accounts can do on this
  repository, in one list.
- **Act As...** on any write: do this one change as another of your
  accounts, named in the preview, without switching the whole Workbench.

### 22.10 Permissions you can see before you grant them

- **View As Role...** on a repository or organization: the Workbench greys
  and explains every menu row, context row and sheet field as a person with
  that role would meet it (read, triage, write, maintain, admin, or a custom
  role, or "this team" or "this person"). Read-only, and the clearest answer
  to "what will they be able to do?".
- **Compare Roles...** lists what one role can do that another cannot, in
  GitHub's own words, including custom roles' added permissions.
- **Why Can't They?** on a person and an action: the role they have, the
  role or rule that stops them, and the smallest change that would let them.

### 22.11 Across repositories: every kind of thing, by name, everywhere

Jeff, 2026-11-09: "can I handle all tags and labels in their own places and
not tied to a specific thing?", then "think broadly if other combinations
such as this exist." They do, and they share one shape.

**The pattern.** GitHub keeps many things inside one repository (a label, a
milestone, a tag, a secret, a webhook), but people think of them by name
across many: "the bug label", "the 2027.1 milestone", "the production
environment", "our CI workflow". So each such kind gets a place of its own,
above any one repository, where a row is a name and the sheet is that name
everywhere it exists.

**Where it lives.** A new top-level branch, **Across Repositories**
(Ctrl+0, and on the Go menu), with one child per kind:

| Kind | A row reads | What you can do everywhere at once |
|---|---|---|
| Labels | "bug: in 14 repositories, 3 colours, 2 descriptions, 212 open items" | rename everywhere; make colour and description the same (choose which variant wins); merge two labels into one (relabel every item, then delete the old one); copy to more repositories; delete everywhere; find every item with it |
| Milestones | "2027.1: in 9 repositories, due dates differ, 61 of 80 closed" | align title, due date and description; close everywhere; move open items to the next milestone everywhere; create in more repositories |
| Tags (Git) | "v3.2.0: in 4 repositories, on 4 different commits" | create a tag in many repositories (a release train); delete everywhere; compare what each points at |
| Releases | "3.2.0: published in 3, draft in 1" | publish all drafts together; edit notes together; list assets everywhere |
| Topics | "accessibility: on 22 repositories" | add or remove a topic on many repositories |
| Issue types | (already organization-wide) | listed here too, with where each is used |
| Branches | "main: default in 30 repositories, protected in 26" | find the 4 unprotected; rename a branch everywhere (with GitHub's redirects); delete merged branches of the same name |
| Rules and branch protection | "Main branch rules: 18 repositories, 4 variants" | make them the same; promote to one organization ruleset |
| Environments | "production: in 7 repositories, reviewers differ" | align reviewers, wait timers and branch policies |
| Secrets and variables (names) | "NUGET_KEY: in 11 repositories" | set a new value everywhere at once (write-only, section 14.3); delete everywhere; promote to one organization secret with those repositories selected |
| Webhooks | "https://hooks.example.org/ci: on 9 repositories" | change the address or events everywhere; turn off everywhere |
| Deploy keys and autolinks | by title or prefix | add to many, remove everywhere |
| Workflows | "ci.yml: 12 repositories, 3 versions of the file" | compare the versions; update every copy from one (as pull requests); run on all; turn on or off everywhere |
| Templates and community files | "Bug report form: 10 repositories, 2 versions" | make them the same (section 21.6); add the missing ones |
| Dependabot and CODEOWNERS | by setting or owner | align configuration; replace an owner everywhere |
| People | "kellylford: collaborator on 6, team member in 2" | the access matrix (section 18.3.2), from the person's side |
| Teams | (already organization-wide) | where each has access, and the role |
| Repository settings | "Allow auto-merge: on in 20, off in 8" | make any setting the same across many (merge methods, features, delete head branches, security features) |
| Saved replies, favorites, watch levels, stars | yours, across everything | manage in one list |
| Alerts | "lodash, high: in 5 repositories" | the security overview by package or rule; dismiss or fix everywhere |
| Packages and Pages | by name | visibility and access together |

**Scopes, the other half of every combination.** Each place works over a
scope you choose: every repository you can administer, one organization,
your own repositories, or a **Repository Set**, a named list kept in the
Workbench ("QuillVille family", "Docs sites"), made by hand or by a filter
(`org:Community-Access topic:quillville`). Sets appear under Across
Repositories and can be the scope of any batch anywhere in the Workbench.

**Differences are the point.** Every row says where the copies differ, and
the sheet's **Variants** page lists each variant with the repositories that
have it, so "make them the same" is a choice of which variant wins, shown in
the preview repository by repository. A **Missing From** page lists the
repositories in scope that lack it, with Add to These.

**Prefer what GitHub already shares.** Where GitHub has an organization-wide
form (organization rulesets, organization secrets and variables,
organization webhooks, issue types, custom properties, and default labels for
new repositories where its API offers them, to verify), the sheet offers
**Promote to Organization**, which creates the shared one and removes the
copies, with the preview.

**Kind by scope by operation.** Every kind in the table, over every scope,
with every operation the kind allows, is one row of the action table, so the
coverage of combinations is tested like everything else (GATE-GITHUB-COVER
counts a cross-repository operation as covered only when the single
repository one is).

### 22.12 The fourth sweep: smaller things still missing

- **More than github.com.** GitHub Enterprise Cloud with data residency
  (`*.ghe.com`) and GitHub Enterprise Server as hosts for an account, used as
  a person uses github.com (issues, pull requests, Actions); only their
  server administration stays out of scope.
- **Use the GitHub CLI's sign-in.** If `gh` is installed and signed in, the
  Workbench can use that account (GHManage's model), as one more kind of
  account beside the device sign-in and tokens.
- **Inbox rules,** Outlook's idea for notifications: "mark Dependabot pull
  requests done after they merge", "move mentions from this repository to the
  top", each a rule with a condition and an action, previewed on today's
  Inbox before it is saved.
- **The maintainer's batch merges:** merge every passing Dependabot pull
  request in a set of repositories, with the preview and a result per pull
  request.
- **Fleet view:** a node for a Repository Set that shows each repository's
  default-branch checks, open pull requests, latest release and alerts in one
  list, read row by row ("quill: checks passing, 4 open pull requests, 3.2.0,
  no alerts").
- **Issue fields,** GitHub's organization-defined fields on issues (the
  schema's `viewerCanSeeIssueFields`), on the Issue sheet and in filters.
- **Follow a running job's log live,** new lines read as they arrive on
  request, with Alt+8 for how far along it is.
- **Hearing a diff:** a short sound for added and removed lines (through the
  family's sound scheme, optional), and Read Changes Only, which skips
  unchanged context.
- **Emoji shortcodes** (`:rocket:`) read by name everywhere.
- **Least privilege advisor:** the token health check (`token_health.py`)
  extended to say which scopes the account has but the Workbench never used,
  and how to narrow them.
- **Release trains:** create the same release in several repositories, with
  notes drafted per repository and one preview (22.11, Releases).
- **Artifact attestations and immutable releases:** read who built an
  artifact and from what, on the Release and Run sheets.
- **Who Owns This File?** in the editor, from CODEOWNERS.

## Part C: the keyboard

Section 8 listed the first keys. This part is the whole map. Every key here is
a proposal until it passes the checks in C1; the Workbench's own
`keymap.APP_KEYMAPS` entry (decision 7) holds the result, the keyboard
reference is generated from it, and the Key Describer names every key.

### C1. How the keys were chosen

1. **Windows, Outlook and File Explorer first.** A key a listener already
   knows from those wins over a key we invent (family rule 1's spirit):
   Alt+Enter is Properties, Delete removes, F5 refreshes, Ctrl+Q and
   Ctrl+U mark read and unread, Ctrl+1 to Ctrl+9 jump between places,
   Alt+Up goes to the parent, Ctrl+L goes to an address, Ctrl+E searches.
2. **Families that teach themselves.** Once you know one key in a family you
   can guess the rest:
   - **Ctrl+number goes** to a top-level place; **Ctrl+Shift+number** goes
     to a part of the current repository.
   - **Alt+number says** something about where you are, and never moves you.
   - **Ctrl+Shift+letter acts** on the selected item (comment, what failed,
     compare, copy link).
   - **F-keys keep their Windows meanings:** F1 help, F5 refresh,
     F6 pane, F10 menu.
3. **Plain letters belong to type-ahead** in the tree and the lists, so a
   listener can always jump to a name by typing it. No letter is ever a
   command, and there is no option to make one (decision 11).
4. **One key changes things: Alt+Enter.** No key sets a single property;
   the Properties sheet does all of it (section 16.3).
5. **Nothing a screen reader owns.** No Insert or Caps Lock combinations; no
   Ctrl+Alt+arrow keys, which NVDA and JAWS use for table navigation; no
   Alt+Shift or Ctrl+Shift alone, which switch keyboard layouts; nothing
   with the Windows key.
6. **Nothing the family owns system-wide.** Checked against the system-wide
   show and hide keys (Ctrl+Alt+Shift+Q and R among them), `DEFAULT_ALIASES`,
   and the other apps' global hotkeys, as the free-chord check requires.
7. **No Ctrl+Alt+letter for anything typed into a text box,** because on
   many European layouts Ctrl+Alt is AltGr and types a character.
8. **Every command has a key or a written reason** (family rule 8); rare
   commands get a key, not a short one (rule 9); destructive commands never
   get a single bare key.
9. **Everything is rebindable** through the Menu Editor and key settings, and
   the menu shows whatever is bound (`_menu_label`).

### C2. Moving around the window

| Key | Does |
|---|---|
| F6, Shift+F6 | Next or previous pane: tree, filter box, list, details |
| Ctrl+1 | Needs My Attention (Inbox selected) |
| Ctrl+2 | Repositories, on the current repository |
| Ctrl+3 | Search |
| Ctrl+4 | People |
| Ctrl+5 | Gists |
| Ctrl+6 | Projects |
| Ctrl+7 | Watches |
| Ctrl+8 | Saved Searches |
| Ctrl+9 | Start Here |
| Ctrl+0 | Across Repositories (section 22.11) |
| Ctrl+Shift+1 | This repository's Issues |
| Ctrl+Shift+2 | Pull Requests |
| Ctrl+Shift+3 | Discussions |
| Ctrl+Shift+4 | Actions (Runs) |
| Ctrl+Shift+5 | Code (Files) |
| Ctrl+Shift+6 | Releases |
| Ctrl+Shift+7 | Projects for this repository |
| Ctrl+Shift+8 | Security |
| Ctrl+Shift+9 | Settings |
| Ctrl+Shift+0 | Insights |
| Alt+Home | Inbox, from anywhere (the browser's home habit) |
| Alt+Up | The parent node (File Explorer) |
| Backspace, Alt+Left | Back |
| Alt+Right | Forward |
| Ctrl+L | Open GitHub Address: paste or type any GitHub link, `owner/name`, `#42` or `owner/name#42` |
| Ctrl+G | Go to Number in the current repository |
| Ctrl+E, Ctrl+Shift+F | The filter box |
| Ctrl+Alt+F | Filter Builder (no text box has focus when it is pressed, so AltGr is not a concern) |
| Ctrl+Shift+E | Switch to the editor that opened the Workbench |
| F5 | Refresh this view |
| Ctrl+F5 | Refresh, ignoring what is cached |
| Alt+F4 | Close the Workbench |
| Escape | Clear the filter, then go Back; never closes the window (decision 5) |

In the tree, the native keys work as they always do: Right and Left expand,
collapse and go to the parent, the asterisk on the number pad expands all
below, Home and End go to the first and last node, and typing goes to a
name.

### C3. Doing things to what is selected

| Key | Does |
|---|---|
| Enter | The default action: Open, Review, Jobs and Logs, Assets, Commits, select a person's or repository's node |
| Alt+Enter | Properties (section 15) |
| Shift+Enter | Open on GitHub, in your browser |
| Ctrl+Enter | Open in the editor: the file, the failing line, or the thread as a document (section 22.4) |
| Applications key, Shift+F10 | Context menu (default first, Properties last) |
| Shift+F1 | What Can I Do Here?: every action for this item and its key, read as a list you can run from (Part D) |
| Delete | Remove, safely: on a notification, Mark Done (undoable); on a pin, favorite, saved search or watch, remove it; on an issue or pull request, Close... with its reason; on a branch, label, milestone, release, asset, comment you wrote, gist, cache, environment or webhook, its delete confirmation (tier 3, never immediate) |
| Ctrl+N | New, here: a new issue in Issues, a pull request in Pull Requests, a label in Labels, a milestone, branch, release, discussion, gist, project item, environment, webhook or saved search in theirs |
| Ctrl+Shift+N | New...: choose what to create, anywhere |
| Ctrl+C | Copy the row as text |
| Ctrl+Shift+C | Copy Link |
| Ctrl+Space | Add to or take from the selection |
| Ctrl+A | Select all |
| Ctrl+D | Add to or remove from Favorites |
| Ctrl+Shift+M | Comment on the selected item |
| Ctrl+Shift+Enter | Merge... the selected pull request (opens the merge dialog) |
| Ctrl+Shift+W | What Failed, for a run or a pull request's checks |
| Ctrl+Shift+F5 | Re-run failed jobs |
| Ctrl+Break | Cancel the selected run (asks first) |
| Ctrl+Shift+B | Compare Branches |
| Ctrl+Shift+L | GitHub API Rate Limit |
| Ctrl+Shift+A | Assign to Copilot |
| Ctrl+Shift+T | Start in Local Worktree |
| Ctrl+Shift+D | File Differences |
| Ctrl+Z | Undo GitHub Change, when focus is not in a text box (section 16.5) |
| Ctrl+Shift+Z, Ctrl+Y | Redo the change you just undid |

### C4. Hearing where you are: Alt+number

These say something and move nothing. Each is also a status bar cell, so the
screen reader's status bar command reads the same facts. They are the only
announcements the Workbench makes on request, and GATE-13 allows them
because the user asked.

| Key | Says |
|---|---|
| Alt+1 | Where am I: "Repositories, Community-Access/quill, Pull Requests, filtered to review-requested:@me" |
| Alt+2 | The selection: "3 of 40 selected, all pull requests" |
| Alt+3 | The selected item's state in one line: "#1811, open, checks passing, 1 approval, mergeable" |
| Alt+4 | Counts for this view: "40 open, 12 closed this week, 3 need your review" |
| Alt+5 | You here: "You have Admin on Community-Access/quill, through the owners team" |
| Alt+6 | The API rate limit: "4,812 of 5,000 left, resets at 15:40" |
| Alt+7 | The filter in effect, in words |
| Alt+8 | What is loading, and how far along it is |
| Alt+9 | The account and whether the Workbench is Read Only, Organize or Full for it |
| F9 | Say the last result again (the family's repeat key) |

### C5. Notifications and the Inbox

| Key | Does |
|---|---|
| Ctrl+Q | Mark read (Outlook) |
| Ctrl+U | Mark unread (Outlook) |
| Delete | Mark done |
| Ctrl+Period, Ctrl+Shift+Period | Next and previous unread, in any list |
| Ctrl+Shift+Q | Mark everything in this view read (asks first when more than 20) |
| Ctrl+Shift+I | Ignore this repository's notifications |

### C6. On a Properties sheet

| Key | Does |
|---|---|
| Ctrl+Tab, Ctrl+Shift+Tab | Next or previous page |
| Ctrl+Page Down, Ctrl+Page Up | Next or previous page |
| Ctrl+1 to Ctrl+9 | Page 1 to 9 by number, read in the page's tab name |
| Enter | OK, except in a multi-line box |
| Ctrl+Enter | OK from anywhere, including a multi-line box |
| Escape | Cancel |
| Ctrl+S | Apply: save and stay |
| F5 | Reload from GitHub |
| Ctrl+Shift+C | Copy the whole sheet as text |
| Shift+Enter | Open this object on GitHub |
| F1 | Help on the field; a second press, help on the page |
| Insert | Add to the focused list (a label, a collaborator, a rule, a contact link, a field) |
| Delete | Remove from the focused list |
| F2 | Change the focused row (a role, a name) |
| Alt+Up, Alt+Down | Move the focused row up or down, where order matters (sub-issues, template fields, options, contact links, views) |
| Space | Check or uncheck in a check list |
| Alt+Enter | Properties of the object in the focused row (a label on an issue, a team on an Access page), opening a sheet on top |

### C7. In the Filter Builder, previews and results

| Key | Does |
|---|---|
| Insert | Add a condition |
| Delete | Remove the focused condition |
| Ctrl+Enter | Apply the filter |
| Ctrl+S | Save as a search |
| Enter, in a preview | Go ahead with every change listed |
| Escape, in a preview | Change nothing |
| Ctrl+C, in a preview or results | Copy the list |
| F8, in results | Retry the failed rows |

### C8. In the PR review reader and diff

The existing review keys stay exactly as they are (Next Unresolved, Reply to
Thread, Copy Thread Link, pending comment edit and delete). Added:

| Key | Does |
|---|---|
| Alt+Enter | Properties of the thread, comment or file at the cursor |
| Ctrl+Shift+V | Mark this file viewed or not viewed |
| Ctrl+Shift+U | Next unviewed file |
| Ctrl+Shift+H | Hide or show whitespace changes |
| Ctrl+Shift+K | Review one commit at a time: choose the commit |

### C9. In the editor

The editor gains no new default chords for GitHub (family rule 7: editor
chords are for the editor). Its GitHub menu rows and the commands of
section 22.3 (Copy GitHub Link to This Line, Who Changed This Line?, and the
rest) each get a written "no default key" reason, are reachable from the
Command Palette, and can be bound by the user. One exception is proposed for
decision: Alt+Enter on a GitHub reference in a document (`#42`,
`owner/name#42`, `@person`) opens its Properties, but only when the cursor is
on such a reference; anywhere else Alt+Enter does what it did before.

### C10. Keys you can see, learn and change

- **Every menu row shows its key,** rendered from what is bound.
- **Shift+F1** lists the actions and keys for the selected thing (Part D).
- **Help > Workbench Keys** opens the keyboard reference for the Workbench,
  generated from `APP_KEYMAPS`, grouped by the families above.
- **The Key Describer** names any key you press and what it does here,
  including keys that do nothing here ("Ctrl+Shift+Enter merges a pull
  request; select one first").
- **Keyboard practice:** Help > Practice the Keys walks the families with the
  practice repository (section 22.8), one family a lesson.
- **Rebinding** follows the family's Menu Editor and key settings; a rebound
  key follows into every menu label, the reference and Shift+F1.

## Part D: help, everywhere and excellent

Jeff, 2026-11-09: help must be "extensive, amazing and purely awesome
throughout this experience." Section 7 set the engine and the gate. This part
is the whole experience.

### D1. The promise

Wherever you are and whatever has focus, help has an answer, it is written
for someone who has never used GitHub, it says what you can do next and with
which key, and it is never more than one key away. Nothing is "self
explanatory". Nothing is help only for sighted users.

### D2. The help keys

| Key | Answers |
|---|---|
| F1 | Help for this window and for what has focus. Pressed again, the next layer out (field, then page, then node, then window) |
| Shift+F1 | What Can I Do Here?: every action available for the selection, its key, and why any greyed one is greyed, as a list where Enter runs the action |
| Ctrl+F1 | The GitHub Workbench Guide, opened at the chapter for this node |
| Alt+F1 | What Is This?: the GitHub term at the cursor or on the selected row, explained (fork, rebase, squash, ruleset, environment, triage, draft, merge queue, and every other term in the glossary) |
| Ctrl+Shift+F1 | Search Help: type a few words, see every help topic, command and setting that matches, and run a command straight from the results |
| Help > Tutorials | The GitHub lessons in the shared tutorials engine |

### D3. Layers: what F1 says, where

1. **The window:** what the Workbench is for, the three panes, F6, Enter,
   Alt+Enter, the context menu key, Back, and where to start.
2. **A tree node:** what this place shows, what you can do here, what it
   needs (sign-in, a permission, a plan feature, an opt-in), and whether you
   have it. For example, Settings > Branch Protection: "The rules that decide
   who may change each branch and how. You have Admin here, so you can change
   them. Ctrl+N adds a rule; Alt+Enter on a rule opens all its settings."
3. **The list:** the node's help, then what the selected row type is and its
   default action, then the five most useful keys for it.
4. **A row:** the item in a sentence ("Pull request #1811, open, from
   claude/wxpython-4-3-2 into main, checks passing"), then its actions.
5. **A sheet page:** what the page covers and when you would come here.
6. **A sheet field:** what it means on GitHub, what the choices do, the
   default, who can change it, and an example. A read-only field adds why it
   is read-only and what would change that.
7. **A menu row:** its topic from `topics.json`, its key, and, if greyed,
   why.
8. **A dialog:** its purpose and then its controls, through the same engine.

### D4. Help that appears without asking

None of this is announced; it is in the place the reader reaches next.

- **Empty states:** an empty list's details pane says why it is empty and
  what would fill it: "No pull requests need your review. When someone
  requests your review it appears here and in Inbox."
- **Greyed rows and read-only fields** carry their reason as their help
  string and their accessible description.
- **Previews** explain each change in words a newcomer understands, and what
  it means for the people affected ("They will be able to label and close
  issues, not push code").
- **Errors** say what happened, what it means and what to do, with a button
  for the fix where there is one. Each carries its `QUILL-GITHUB-...` error
  code (GATE-EC), and the code's help page is one key away.
- **The first time** you meet a place, its details pane opens with a short
  "First time here?" paragraph, until you have used the place three times or
  choose Do Not Show Again.
- **Start Here** (Ctrl+9): what the Workbench is, sign-in state, the five keys
  to learn first, the guide, the tutorials, and the practice repository.

### D5. What Can I Do Here? (Shift+F1)

The single most useful help in the window. For whatever is selected (a row,
several rows, a node, a sheet field), it opens a list of every action that
could apply, in the order of the context menu, each row reading "Close issue,
Delete" or "Merge, greyed: the required check build has not
passed." Enter runs the action; F1 on a row explains it. It is built from the
same action table as the menus, so it can never disagree with them.

### D6. The GitHub glossary (Alt+F1)

About two hundred GitHub terms, each in one plain paragraph with an example
and the place in the Workbench where you meet it: from "Actions" to
"workflow dispatch", including roles (read, triage, write, maintain, admin),
every rule in a ruleset, every notification reason, every alert kind, and the
words GitHub uses for states ("draft", "merge queue", "stale review"). It
lives in the help catalogue (`workbench_help.py`), renders into the F1
reference, and is searchable from Search Help.

### D7. Search Help (Ctrl+Shift+F1)

A dialog with one search box and one results list. It searches everything:
node help, row help, field help, menu topics, the glossary, the guide's
headings, settings, tutorials and keys. Each result says what it is ("Command:
Re-run failed jobs, Ctrl+Shift+F5") and Enter does the obvious thing: runs a
command, goes to a node, opens a setting, starts a tutorial, or opens a help
topic. Typing "who can merge" finds the merge requirements, the ruleset
rules, View As Role, and Why Can't They?.

### D8. The guide, the reference and the tutorials

- **The GitHub Workbench Guide** is rewritten around the tree: an
  Introduction, then one chapter per top-level node, then chapters for
  Properties, editing, filtering, permissions, templates and the keyboard,
  each opening with why you are here, what you will do and what you will have
  by the end (the family's guide structure), with chapter cross-references,
  and a keyboard reference at the end.
- **The Workbench reference** (`docs/github/workbench-reference.md`) is
  generated from the tree, menu, context, sheet and action tables, plus the
  coverage table's "everything GitHub can do, and where", and drift-gated.
- **The F1 reference** (`docs/f1-help-reference.md`) includes every Workbench
  help string.
- **Tutorials** (Help > Tutorials), each a short guided lesson on the practice
  repository: your first look around; triage an inbox; file an issue with a
  form; review a pull request; fix a failed run; plan a milestone; organize a
  project board; give someone access; write a branch rule; build an issue
  form; use the API Console.
- **Release notes** tell the story of each Workbench release in the family's
  human voice (the docs voice rule): what you can now do, and the key.

### D9. How help is written

- **A human voice:** plain words, short sentences, what to do before why, no
  marketing, none of the AI tells the family's docs rule lists, and no
  engineering rationale in user-facing help.
- **Check, never tick,** for check boxes; "Community Access"; no emoji.
- **One idea per help string,** an example where it helps, and the key.
- **Accurate to the account:** help that depends on your permission says
  what you have now, not only what is needed.
- **Translatable:** every string through the family's gettext path.

### D10. Gates that keep help excellent

- **GATE-GITHUB-HELP** (section 7): every control, node, row type, sheet page
  and field has authored help; the `missing` list starts from today's and may
  only shrink; zero before the Workbench becomes the default.
- **`check_help_coverage --strict`** over the `github.*` namespace: every
  command has a topic.
- **The action table test:** every action has a Shift+F1 row and a reason
  string for each way it can be greyed.
- **The glossary test:** every GitHub term used in a node, row or field name
  has a glossary entry.
- **The generated references** (GATE-KEYREF, GATE-HELPREF) drift-gated, and
  both documentation-chord gates over the guide.
- **A review step:** a person reads each new help string aloud before it
  merges, because a gate can prove help exists, not that it helps.

### D11. Help is a place, not only a key

Jeff, 2026-11-09: help "must be a huge huge part of both WordPress and GitHub
workbenches, it must be rich and delightful." So help gets its own branch at
the bottom of the tree, **Help and Learning**, the same in both Workbenches
(the shared engine's help module, section 3 of the WordPress PRD):

```
Help and Learning
    Start Here                 (Ctrl+9) what this is, your sign-in, the five keys to learn first
    Do Something               tasks in plain words, each one a guided walk (D12)
    The Guide                  every chapter as a node; the details pane reads it
    Words                      the glossary as a list: filter it, Alt+Enter on a word
    Keys                       every key by family, and the keys for where you were
    Tutorials                  each lesson, with your progress ("4 of 11 done")
    What Changed               what is new in the Workbench, in this version
    Tips                       QUILLBert's tips, one at a time, never pushed at you (D16)
    Ask a Person               write to support, with what you were doing attached (D17)
```

Every node there is a list like any other, so a person can type-ahead to a
topic, filter it, export it, and Alt+Enter on a topic for its Properties
(what it covers, the keys it teaches, the commands it can run, the tutorials
that practise it).

### D12. Do Something: help that takes you there and walks with you

The fastest help is the one that does the first step for you.

- **A task list in plain words,** grouped by what people come to do: "Find
  what needs me", "Fix a failed run", "Give someone access", "Write a branch
  rule", "Moderate comments", "Fix pictures without alt text", "Update
  plugins safely". Each task names the keys it uses.
- **Take Me There** on any topic or task moves focus to the place and the
  control it is about: the right node, the right row, the right page of the
  right sheet. It says only where it put you.
- **Walk Me Through It** runs the task as a guided walk on the real data (or
  the practice repository and practice site, if you choose): each step says
  what to do and waits for you to do it, F1 repeats the step, Shift+F1 lists
  the steps, Escape stops. The tutorials engine already does this for lessons;
  here any help topic can.
- **Do It** on a topic whose answer is one command runs it, with its usual
  preview, so reading "how do I re-run failed jobs" ends with them re-running.

### D13. Every result can explain itself

- **F9** says the last result again (the family's key, Part C).
- **Shift+F9, Explain That,** says what the last result means and what you
  might do next, in a paragraph: "Re-ran 2 failed jobs of the build on main.
  They run again from the start, on the same commit. A Watch can tell you
  when they finish: Alt+Enter on the run, then Watch."
- **Why?** is on everything automatic: why a Watch fired, why a row is greyed,
  why a filter is local, why an entry was held as spam, why a rule moved a
  notification, why a sheet field is read-only. Shift+F1 on the item lists it
  first.
- **Previews explain every change** in the reader's terms, and F1 in a preview
  explains the change under focus in more depth.

### D14. Help that knows your situation

- **Examples from your own data.** Help uses what is in front of you: "On
  Community-Access/quill, this rule would block force pushes to main, which
  you did twice last month." "On Community Radio, Day and name would make this
  post's address https://.../2026/11/09/morning-show/."
- **Aware of your role and plan.** Help says what you can do now and, when
  you cannot, what you would need, and who on this repository or site can
  give it to you.
- **Aware of the site or account:** a WordPress topic knows which plugins the
  site runs ("Your site uses Yoast, so this page also has SEO fields"); a
  GitHub topic knows whether the organization uses rulesets or classic
  protection.
- **Aware of where you came from:** help on a node you reached from a
  notification starts with the notification's reason.

### D15. Help you can take with you

- **Key cards:** Help > Keys > Make a Key Card writes the keys for this
  Workbench as a one-page document, a QUILL table, or a braille file (BRF),
  through QUILL's own braille output, ready to emboss or read on a display.
- **The guide as a book:** Word, EPUB and DAISY exports of the whole guide,
  from the same source as F1.
- **Listen to the tour:** the guide's introduction and each chapter as spoken
  audio, made with the family's voices, and short episodes of the QUILL
  podcast walking through each Workbench.
- **Offline:** all of help is on this computer; nothing needs the internet
  except Ask a Person and the optional AI answers of D18.

### D16. Delight, in help

- **QUILLBert and QUILLBee,** the family's two friends from its release notes:
  QUILLBert finds things worth trying ("Tip: Alt+Enter on a label shows every
  repository that has it."), QUILLBee explains ("A ruleset is a list of rules
  for branches..."). They speak in help and tips only, never in results, and
  each has one line, not a personality to wade through. A Workbench Options
  choice turns them into plain help.
- **Tips at the right moment, never pushed:** the Tips node holds them; a tip
  is offered in the details pane only the third time you do something the
  slow way ("You can select all twelve and press Alt+Enter once."), once per
  tip, and Do Not Show Tips stops them.
- **Small celebrations** as the product's A8 describes, each with a line of
  help on what you might do next.
- **Plain, warm and short:** the voice of D9, with one example in every topic
  and the key on every action.

### D17. Ask a Person

- **Help > Ask a Person** (and Ask a Person in Help and Learning) writes to
  support@community-access.org from the family's support form, with what
  you were doing attached if you choose: the node, the row type, the last
  result, the help topic you were reading, and the Workbench version. Never a
  token, a secret, or any GitHub or WordPress content unless you paste it.
- **Report a Help Problem** on any help topic sends its topic id and your
  note the same way, so a confusing sentence is fixed rather than endured.

### D18. Ask the Workbench (optional AI)

For people who prefer to ask: **Help > Ask How**, in plain words ("how do I
give the Docs team access to every repository?"). The answer is built only
from the Workbench's own help catalogue, guide and action table, through the
family's Ask AI with the person's chosen provider, and it always ends with
Take Me There, Walk Me Through It or Do It for the commands it names. It never
acts on its own, it says when the help does not cover a question, and it is
off unless the person has an AI connection (Choose Your AI).

### D19. One source for all of it

Every help string is written once, in the shared help catalogue, and used
everywhere it appears: F1, Shift+F1, Explain That, the Guide, Words, Search
Help, key cards, the generated references, tutorials, release notes and Ask
How. A topic is a record (id, title, body, example, keys, commands, related
words, related topics, the places it applies to, and the roles and plans it
mentions), so each of those surfaces is generated, and a change appears in
all of them at once.

### D20. Help quality, measured

- **Coverage:** GATE-GITHUB-HELP and GATE-WORDPRESS-HELP at zero, every node,
  row type, field, command, error and result sentence with help (D10).
- **Every result has an Explain That paragraph;** a test fails on an
  announcement without one.
- **Every task in Do Something has a walk** that the test suite runs end to
  end on the practice repository or practice site.
- **Braille length:** the first sentence of each topic fits a 40-cell display
  line where it can, because it is what a braille reader meets first.
- **Read aloud:** a person reads each new topic aloud before it merges (D10),
  and the section 12 sessions with people include "find the answer in help"
  as a task, timed.

## Part E: requirements

Each requirement has an id, a strength (**Must** ships before the Workbench is
the default; **Should** ships in the program; **May** if time allows) and
the section that designs it. Each Must has at least one test, named in the
phase's PR. Ids are never renumbered; a dropped requirement keeps its id with
"withdrawn".

### E1. The window and its panes

- GH-R-001 Must: the Workbench is a top-level frame with its own menu bar,
  status bar and taskbar button, one per app (3.1).
- GH-R-002 Must: it never blocks the editor; its dialogs block only it (3.1).
- GH-R-003 Must: F6 and Shift+F6 cycle tree, filter, list and details (3.2).
- GH-R-004 Must: it remembers size, panes, last node, expanded nodes,
  columns and filters per account (3.1).
- GH-R-005 Must: Escape clears the filter, then goes Back, and never closes
  the window (3.1).
- GH-R-006 Must: Switch to Editor and Open in Editor raise the editor that
  opened it (3.1).
- GH-R-007 Must: the status bar is reached with F6, arrowed across, and every
  cell has Enter and a context menu with Copy and Help, mirrored to the real
  status bar, built in the shared engine on the family's existing focusable
  status bar pattern (3.2.1).

### E2. The tree

- GH-R-010 Must: the tree is a native `wx.TreeCtrl`, at most four levels
  deep, loading lazily, with counts after names that are never announced
  (3.3, 9).
- GH-R-011 Must: every view in GitHub Items and Explore appears exactly once
  (the "nothing dropped" test) (10).
- GH-R-012 Must: nodes needing sign-in, permission or an opt-in are shown,
  explained, and offer the fix (3.3).
- GH-R-013 Must: drill-downs move the tree, and Back and Forward walk one
  history (3.3).
- GH-R-014 Should: Group By puts groups in the tree as child nodes (17.4).

### E3. Menus and context menus

- GH-R-020 Must: every menu row shows its key; no key is claimed twice;
  greyed rows carry a reason (4).
- GH-R-021 Must: context menus hold only rows for the selected row type, the
  default first and Properties last, with More mirroring the Item menu (5).
- GH-R-022 Must: Codespaces appears only on repositories, branches and pull
  requests; Rate Limit on no context menu (5).
- GH-R-023 Must: menus, context menus, Shift+F1 and sheets are
  all built from one action table (10, 18.6, D5).

### E4. Properties

- GH-R-030 Must: Alt+Enter, Item > Properties... and the context menu's last
  row open the Properties sheet of the selected object, for every object type
  in Appendix C (15.1).
- GH-R-031 Must: every fact is a focusable labelled control; read-only facts
  are read-only text boxes (15.2).
- GH-R-032 Must: an editable field is editable exactly when the user may
  change it, and read-only with a reason otherwise (15.2, 18.2).
- GH-R-033 Must: a multiple selection opens one sheet with Mixed values and
  three-state check lists, saving only touched fields (15.2).
- GH-R-034 Must: before saving, someone else's changes are detected and the
  user chooses per field; after saving, the object is read again and only a
  verified change is reported as done (15.3).
- GH-R-035 Must: every picker ends with New... that creates and uses the
  thing (15.2).
- GH-R-036 Should: Alt+Enter on a GitHub reference in a document opens its
  sheet (C9, 22.3).

### E5. Editing

- GH-R-040 Must: every field GitHub's API can change has a control on its
  object's sheet; the coverage gate proves it (16.1, 19).
- GH-R-041 Must: removal and replacement are as available as adding,
  lifting today's add-only batch rule (16.1).
- GH-R-042 Withdrawn (2026-11-09): per-property keys. Alt+Enter opens the
  sheet instead (16.3).
- GH-R-043 Must: batches preview, run paced for the rate limit, and report a
  result per item with retry (16.4).
- GH-R-044 Must: Undo GitHub Change reverses any reversible change, and an
  irreversible one says so before it happens (16.5).
- GH-R-045 Must: Projects (version 2): every field type, views, items,
  workflows and status updates are readable and editable (16.6).
- GH-R-046 Must: every relationship (star, watch level, follow, subscribe,
  react, block, sponsor, pin) on a You page and in batch (16.7).

### E6. Filtering

- GH-R-050 Must: one query, written by the filter box, the Filter Builder,
  the Filter menu and Show Only or Hide on cells, all in step (17.1).
- GH-R-051 Must: every attribute GitHub search supports is sent to GitHub;
  every other attribute filters locally with an honest status line and Load
  All (17.3).
- GH-R-052 Must: every list attribute has "has none"; every person field has
  "Me" (17.2).
- GH-R-053 Must: filters can be saved as searches and pinned as nodes (17.1).
- GH-R-054 Should: Or groups where GitHub search allows them (17.2).

### E7. Permissions

- GH-R-060 Must: Account > GitHub Permissions lists every scope the Workbench
  can use, what each unlocks, and whether you have it, and adds every missing
  one in one step for each sign-in kind (18.1).
- GH-R-061 Must: the viewer fields of Appendix F.1 are fetched with each
  object and drive greying with reasons (18.2).
- GH-R-062 Must: every write command and editable field declares its
  requirement and tier; GATE-GITHUB-PERM fails on one without (18.2, 18.6).
- GH-R-063 Must: every object with an access list has an Access page with
  Add, Change Role, Remove and pending invitations (18.3, Appendix D).
- GH-R-064 Must: rulesets and branch protection expose every rule and
  setting GitHub offers, with a plain-words Summary page (18.3.1).
- GH-R-065 Must: tier 2 changes preview in words; tier 3 adds typed
  confirmation; self-lockout is refused (18.4).
- GH-R-066 Must: Read Only, Organize and Full per account; Safe Mode makes
  every account Read Only (18.4).
- GH-R-067 Must: Change History records every write, with before and after,
  and never a secret (18.5).
- GH-R-068 Should: the access matrix, bulk access changes and access
  templates (18.3.2).
- GH-R-069 Should: View As Role, Compare Roles and Why Can't They? (22.10).

### E8. Templates

- GH-R-070 Must: issue forms and discussion forms are filled natively, with
  bodies identical to GitHub's (21.7).
- GH-R-071 Must: every template kind in 21.2 can be listed, created, edited
  field by field, checked, previewed and saved (21.3 to 21.6).
- GH-R-072 Should: forms can be written as BFL and converted to and from
  GitHub's schema through `interop_github.py` (21.4).
- GH-R-073 Should: Copy to Repositories for templates and community files
  (21.6, 21.8).

### E9. Beyond parity

- GH-R-080 Must: the API Console reaches any REST or GraphQL operation, with
  scope shown, tiers applied and Change History kept (22.2).
- GH-R-081 Should: Read as Document for threads, with export (22.4).
- GH-R-082 Should: posts are checked for accessibility before sending, offering
  and never blocking (22.4).
- GH-R-083 Should: Watches with one-sentence results and sounds through the
  shared feedback channels (22.5).
- GH-R-084 Should: the editor commands of 22.3.
- GH-R-085 Should: export of any list; import of issues from CSV (22.7).
- GH-R-086 May: plain-language batches through the Command Key work (22.6).
- GH-R-087 Should: Dry Run and the practice repository (22.8).
- GH-R-088 Should: the GitHub features listed in 22.1, each as the coverage
  gate schedules it.

### E10. Keyboard

- GH-R-090 Must: every key in Part C passes the checks in C1 before adoption
  and lives in the Workbench's `APP_KEYMAPS` entry.
- GH-R-091 Must: the families of Part C hold: Ctrl+number goes, Alt+number
  says, F-keys keep Windows meanings, and Alt+Enter is the one key that
  changes things.
- GH-R-092 Must: typing always moves through the tree and lists; no letter
  is ever a command (16.3).
- GH-R-093 Must: every key is rebindable, and the rebinding follows into
  menus, the reference, Shift+F1 and the Key Describer (C10).

### E11. Help

- GH-R-100 Must: F1 answers on every node, row, sheet page, field, menu row
  and dialog, in layers (D3).
- GH-R-101 Must: Shift+F1 What Can I Do Here? for every selection (D5).
- GH-R-102 Must: Alt+F1 glossary, Ctrl+F1 guide chapter, Ctrl+Shift+F1 Search
  Help (D2, D6, D7).
- GH-R-103 Must: empty states, greyed rows, previews and errors carry help
  (D4).
- GH-R-104 Must: GATE-GITHUB-HELP at zero and the help tests of D10 green.
- GH-R-105 Should: the GitHub tutorials of D8.
- GH-R-106 Must: Help and Learning in the tree, with every node of D11 (D11).
- GH-R-107 Must: Take Me There and Walk Me Through It on every help topic and
  task; Do It where the answer is one command (D12).
- GH-R-108 Must: Shift+F9 Explain That for every result, and Why? on every
  automatic behaviour (D13).
- GH-R-109 Should: examples from the person's own data and situation (D14).
- GH-R-115 Should: key cards in print and braille, the guide as a book, the
  spoken tour (D15).
- GH-R-116 Should: QUILLBert and QUILLBee tips at the right moment, with an
  option for plain help (D16).
- GH-R-117 Must: Ask a Person and Report a Help Problem, never sending a
  secret (D17).
- GH-R-118 May: Ask How through the family's AI, grounded only in the help
  catalogue (D18).
- GH-R-119 Must: one source for every help surface (D19), and the measures of
  D20.

### E12. Speech, braille and sound

- GH-R-110 Must: the Workbench announces only what the reader cannot see
  (results, background changes, Watches) and nothing on focus, title or
  selection (GATE-13).
- GH-R-111 Must: every announcement is also brailled (GATE-BRAILLE).
- GH-R-112 Must: one sentence per outcome, naming what changed (A8).
- GH-R-113 Must: sounds go through the shared action-feedback channels; a
  failure or a count is always spoken (A8).
- GH-R-114 Should: a braille-shaped row option (22.4).

### E13. Settings

- GH-R-120 Must: every GitHub preference lives in Workbench Options, stored
  in `github_workbench.json` through `workbench_prefs.py`, shared by both
  editors; nothing GitHub in the main Options (4.1).
- GH-R-121 Must: the three poll settings migrate out of the main Settings
  once, with the vocabulary audit and GATE-SETDOC regenerated (4.1).
- GH-R-122 Must: the Workbench is fully usable without opening Workbench
  Options (4.1).

### E14. API use

- GH-R-130 Must: only `api.github.com`, `github.com` sign-in pages,
  `uploads.github.com` for assets and, with consent, githubstatus.com; each
  new endpoint family named in the network egress audit (18.6).
- GH-R-131 Must: conditional requests (ETag) for every repeated read
  (`conditional_requests.py`), and secondary rate limits respected.
- GH-R-132 Must: GraphQL where it is the only API (Appendix F) and where one
  query replaces many REST calls; REST otherwise.
- GH-R-133 Must: the vendored API snapshot and `api_coverage.json` drive
  GATE-GITHUB-COVER (19, Appendices E and F).

### E15. Teams

- GH-R-140 Must: teams are created, edited, nested, filled, given
  repository and project roles, and deleted, from the Team sheet and the
  Teams node; the old "Teams out" decision in `repo_admin.py` is removed in
  the same change (18.3.3).
- GH-R-141 Must: team code review assignment is readable and editable
  (18.3.3).
- GH-R-142 Should: batch membership and batch repository roles across teams
  (18.3.3).
- GH-R-143 Should: People > My Teams and team review requests in Needs My
  Attention (18.3.3).

### E16. Across repositories

- GH-R-150 Must: Across Repositories has a place for every kind in the 22.11
  table, a row per name with its variants and where it is missing.
- GH-R-151 Must: every operation a kind allows in one repository is offered
  across a scope, with the preview and a result per repository (22.11).
- GH-R-152 Must: Repository Sets, by hand or by filter, usable as the scope of
  any batch (22.11).
- GH-R-153 Should: Promote to Organization wherever GitHub has a shared form
  (22.11).
- GH-R-154 Should: the fourth sweep of 22.12, each as the coverage gate
  schedules it.

## Part F: quality

### F1. Accessibility

- **Screen readers:** NVDA, JAWS and Narrator, checked for every phase, with
  results in `docs/qa/screen-reader-checks-2026-10.md`. The tree spike in
  Phase 1 is the go or no-go for the window's shape.
- **Braille:** every announcement brailled; rows readable on a 40-cell
  display with the short-row option.
- **Keyboard only:** every action reachable without a mouse (Part C); no
  action only on a context menu (rule 3 in section 5).
- **Low vision:** per-monitor DPI sizing through `dip()`; high contrast
  themes followed; nothing conveyed by colour alone (labels name their
  colour, states are words).
- **Motion and sound:** no animation; every sound optional; nothing time
  limited without a way to extend it.
- **Cognitive load:** one home per feature, the default action first, plain
  words, and the first-time paragraphs of D4.
- **The family gates:** menu accelerators, GATE-13, GATE-14,
  GATE-BRAILLE, the close-button contract, dialog inventory, GATE-REACH,
  GATE-DPI, and axe-core checks on any HTML the Workbench produces (exported
  documents, the generated reference).

### F2. Performance

| Moment | Budget |
|---|---|
| Opening the Workbench, warm | under 1 second to the tree, with the last node's cached rows |
| A keystroke that does not wait on GitHub | under 100 ms |
| Expanding a cached tree node | under 150 ms |
| A list's first rows from GitHub | under 1.5 seconds on a normal connection, with "Loading" in the status bar and Alt+8 |
| A Properties sheet | open under 500 ms from cache, refreshed in the background, fields updated in place |
| A list of 10,000 rows | scrolls and types-ahead without lag (virtual list) |
| A batch of 100 changes | paced to stay inside GitHub's secondary limits, progress in the status bar |

Never time a budget under `tracemalloc` (the GATE-PERF lesson).

### F3. Reliability

- **All network work on `QuillTaskManager`,** results back through
  `wx.CallAfter`; the UI thread never waits on GitHub.
- **Offline and errors:** cached views stay readable with "Offline, showing
  what was loaded at 14:05"; writes are refused with the reason, never
  queued silently; every failure has a coded error and help (D4).
- **Rate limits:** the remaining budget is known (Alt+6); work pauses before
  the limit and resumes on its own, and says so once.
- **Atomic local stores:** preferences, resume state, Change History,
  Watches and saved commands through `write_json_atomic`, schema-validated.
- **Crash reports** go through the family's redaction.

### F4. Security and privacy

- **Credentials** stay where they are today (`token_store.py`, Credential
  Manager, DPAPI). The Workbench never shows, logs, speaks or exports a
  token.
- **Secret values** are write-only: encrypted on this machine with the
  target's public key (GitHub's sealed-box scheme) before sending, through
  PyNaCl, which QUILL already ships for Quillin signing (decision 12, decided).
  The first slice is built: `quill/core/github/secret_values.py` and Explore's
  secret and variable writes (branch `feat/github-secret-values`).
- **Webhook secrets and deploy keys** are set, never read back.
- **No telemetry.** Change History, Watches and saved commands stay on this
  device and are clearable.
- **The API Console** applies the same tiers, previews and history as every
  other write; it cannot bypass Read Only or Safe Mode.
- **Untrusted content:** issue bodies, comments, templates and logs are data.
  Nothing from GitHub is executed; templates are parsed, never run (as
  `issue_templates.py` already promises).

### F5. Testing

- **wx-free tables first:** tree, menus, context rows, sheets, fields,
  actions, filters, tiers and help are data in `quill/core/github`, so most
  rules are unit tests (sections 10 and 18.6).
- **Recorded API responses** for every loader and saver, including GitHub's
  silent-ignore cases, so tests never call GitHub.
- **Golden bodies** for issue forms (21.7) and golden previews for tier 2 and 3
  changes.
- **GATE-LITE-COVER** for every QUILL Lite handler, by behavioural test.
- **A live regression run** against a practice organization, the way
  WordPress has `docs/qa/wordpress-live-run.py`, run by the parent session
  before a Workbench branch merges, with the account's consent and its
  credentials kept in Credential Manager.
- **The section 12 tasks** with five people before Phase 3 and Phase 6.
- **The suite rules:** `machine_global` marks for anything touching the
  clipboard, global hotkeys or screen-reader bridges; serial re-runs before
  believing a parallel failure.

### F6. Dependencies (checked 2026-11-09 against `pyproject.toml` and the shared runtime)

Every one is bundled in the installers and portables, never downloaded at
run time (the family's bundle-everything rule), pinned, and listed in the
third-party notices and the runtime inventory. Adding any new one is Jeff's
decision; this list is that decision's input.

**Already shipped, nothing to add:** PyNaCl (secret values; already a core
dependency, approved for this use), PyGithub, requests, openpyxl (Excel import
and export), feedparser, markitdown, Pandoc (EPUB, Word and DAISY exports),
the braille output (key cards in BRF), wxPython's native `wx.TreeCtrl`, and,
in the shared runtime, Node, the language servers and ripgrep. GraphQL needs
no library: `github_graphql.py` already speaks it over HTTPS.

**New, small, Python:**

| Package | For | Licence | Note |
|---|---|---|---|
| PyYAML | reading issue forms, discussion forms, the template chooser, Dependabot and workflow files | MIT | already in the runtime as another package's dependency; declare it directly |
| ruamel.yaml | editing those YAML files while keeping their comments and order (the template builder, the workflow builder, the Dependabot sheet) | MIT | new |
| jsonschema | checking issue forms against GitHub's form schema before saving | MIT | already in the runtime through `mcp`; declare it directly, or use QUILL's own schema checker if it covers draft 2020-12 |

**New, bundled tools:**

| Tool | For | Licence | Note |
|---|---|---|---|
| Git for Windows (MinGit) | Resolve Conflicts, Start in Local Worktree, the wiki, Clone | GPL-2.0, as a separate program | `git_binaries.py` today prefers the system's Git and fetches a copy on demand; the bundle-everything rule says bundle MinGit in the shared runtime instead (about 50 MB) |
| actionlint | Check This File for workflow YAML | MIT | a new executable for Check This File, so it needs the same approval the syntax-checker allowlist had (`CHECKER_TOOLS`) |

**The GitHub CLI (`gh`): bundle it too** (corrected 2026-11-09, after Jeff
asked "why can't we ship gh?"). There is no reason not to: it is MIT
licensed and redistributable, QUILL already uses it (`gh_bridge.py` drives
Codespaces through it, and `git_binaries.py` already allows `gh.exe` and
fetches a copy on demand, which is the same bundle-everything gap as Git).
So the shared runtime ships a pinned `gh` beside MinGit (roughly 40 MB more).
Two cautions, written into the design:

- **One sign-in, not two.** `gh` keeps its own sign-in. The Workbench uses
  QUILL's sign-in by default and passes its token to the bundled `gh` for
  each call (`GH_TOKEN` in that process only), so a person never has to sign
  in twice. The "use the GitHub CLI's sign-in" account (22.12) is for people
  who already use `gh` in a terminal and want the Workbench to follow it.
- **Pinned, and still preferred from the system when newer.** Like Git, a
  system copy is used when present; the bundled one is the floor, updated
  with each runtime.

**Data, not libraries:** the vendored GitHub API description and GraphQL
schema (section 19). Raw, they are 14 MB and 1.6 MB; the app ships a trimmed
form (operation ids, paths, methods, arguments, scopes and descriptions,
about 2 MB) for the API Console and the coverage gate, and tests keep the
full files.

**Services, not dependencies,** each with consent and a network egress row:
githubstatus.com (Is GitHub Working?).

## Part G: rollout, risks and decisions

### G1. Phases

Phases 0 to 6 are in section 11, Phases 7 to 13 in section 20. In one line
each:

| Phase | What ships |
|---|---|
| 0 | Quick wins in today's dialogs: context menus, F1, one announcement dropped |
| 1 | The spike: the frame with the 7 Items views, three readers, go or no-go |
| 2 | Everything in the tree, nothing dropped |
| 3 | Menus, context menus, Workbench Options and the settings migration |
| 4 | The editor side: short GitHub menu, doors into nodes |
| 5 | Help and docs: the catalogue, GATE-GITHUB-HELP at zero, the guide (Part D) |
| 6 | Retire GitHub Items and Explore after one release |
| 7 | The Properties engine and the first sheets |
| 8 | Every object's sheet and batch |
| 9 | Filtering |
| 10 | Permissions |
| 11 | Coverage: the snapshot, the table, GATE-GITHUB-COVER (start early) |
| 12 | Templates: native filling first, then the builder |
| 13 | Beyond parity: API Console first, then the rest of section 22 |
| 14 | Across Repositories and Repository Sets (22.11): labels, milestones and tags first, then the rest of the table; the fourth sweep (22.12) |

Part C's keys ship with the phase that ships their command; Part D's help
ships with every phase, never after.

### G2. Risks

| Risk | What reduces it |
|---|---|
| `wx.TreeCtrl` reads badly in one reader | Phase 1 spike decides before anything depends on it |
| The scope is enormous | the coverage gate makes it a measured backlog; each phase ships on its own |
| GitHub changes its API | the vendored snapshot is refreshed on purpose; new rows fail as `missing` |
| A write silently does nothing | verify after every save (15.3) |
| Someone locks themselves or their organization out | tiers, previews, self-lockout refusal, Read Only accounts (18.4) |
| Rate limits on big organizations | ETags, pacing, lazy loading, cached views |
| Keys collide with a reader or a layout | the C1 checks, the Key Describer, rebinding |
| Help falls behind features | help ships in the same PR as its feature; GATE-GITHUB-HELP |
| `github_items_dialog.py` and friends grow past their size budgets | extract into mixins and wx-free tables; GATE-11 |
| Secret values need sealed-box encryption | Resolved: PyNaCl is already a core dependency, approved for this by Jeff on 2026-11-09 (decision 12) |

### G3. Decisions

Section 13 holds decisions 1 to 21, each with a recommendation; 22 to 25
follow. All 25 were accepted on 2026-11-09.
The keyboard adds two more:

22. **Delete on an issue or pull request opens Close... with its reason,**
    never deletes? Recommendation: yes.
23. **Alt+Enter in the editor on a GitHub reference only** (C9)?
    Recommendation: yes, and nowhere else in the editor.
24. **Across Repositories** as a top-level branch on Ctrl+0, with labels,
    milestones and tags first (22.11)? Recommendation: yes.
25. **One shared engine with the WordPress Workbench** (the [WordPress
    Workbench PRD](./wordpress-workbench-prd.md), section 3, accepted
    2026-11-09): build the frame, tree, actions,
    Properties, filters, history, help and coverage provider-neutral from
    GitHub's Phase 1 onward? Recommendation: yes; WordPress's decision 1
    already takes it.

## Appendices

## Appendix A: every feature and its new home

### GitHub Items' views

| Today | New home |
|---|---|
| Issues & PRs | Repository > Issues; > Pull Requests; > Issues and Pull Requests |
| Branches | Repository > Code > Branches |
| Commits | Repository > Code > Commits |
| Tags | Repository > Code > Tags |
| Releases | Repository > Releases |
| Workflows | Repository > Actions > Workflows |
| Workflow Runs | Repository > Actions > Runs |

### GitHub Items' buttons and choices

| Today | New home |
|---|---|
| Repository box and Load | The Repositories node; File > Open a Repository...; Open GitHub Address... |
| Pinned... | Repositories > Pinned; Tools > Workbench Options > Repositories |
| Favorites... | Repositories > Favorites; Item > Add to or Remove from Favorites |
| Explore... | Gone as a window: everything is in the tree |
| Projects... | Projects node; Repository > Projects |
| View Upstream | Repository > Code > Upstream; Repository > View Upstream |
| Files... | Repository > Code > Files; Repository > Browse Files |
| Milestones... | Repository > Milestones |
| Search box and Search | Filter box; the Search branch |
| Open Link... | File > Open GitHub Address... (Ctrl+L) |
| Quick filter | Filter box |
| View choice | The tree |
| Show choice | Issues and Pull Requests nodes; View > Show |
| State, Sort | View > State; View > Sort |
| List mode | View > Quick or Full list |
| Columns... | View > Columns... (current list); Tools > Workbench Options > Lists (defaults) |
| Back, Forward | View > Back, Forward; Backspace, Alt+Left, Alt+Right |
| Refresh | View > Refresh (F5, Ctrl+R) |
| View More | View > Load More |
| Open in Browser | File > Open on GitHub; on every context menu |
| Go To #... | File > Go to Number... |
| Diff... | Item > File Differences...; PR context menu |
| Review... | Item > Review...; default action for a PR |
| Summarize | Item > Summarize Discussion |
| Compare... | Repository > Compare Branches...; branch context menu |
| Batch... | Item > Batch (multiple selection) |
| Actions... | The Item menu |
| Close | File > Close Workbench; Alt+F4 |

### Explore GitHub's views

| Today | New home |
|---|---|
| Global issue and PR search | Search > Issues and Pull Requests |
| Code search | Search > Code |
| Commit search | Search > Commits |
| Repository search | Search > Repositories |
| My Work | Needs My Attention > Review Requests, Assigned to Me, Mentions, My Open Pull Requests, My Open Issues |
| Attention queue | Needs My Attention > Inbox |
| My activity feed | Needs My Attention > My Activity Feed |
| My repositories | Repositories > My Repositories |
| Starred repositories | Repositories > Starred |
| Watched repositories | Repositories > Watched |
| People I follow | People > People I Follow |
| My followers | People > My Followers |
| My gists | Gists > My Gists |
| GitHub notifications | Needs My Attention > Notifications |
| Repository chooser | The Repositories branch itself |
| Person's repositories, public activity, followers, people followed | People > person > Repositories, Activity, Followers, Following |
| Repository overview | Repository > Overview |
| Repository activity | Repository > Activity |
| Repository people | Repository > People > Contributors and People |
| Repository forks | Repository > People > Forks |
| Collaborators and team access | Repository > People > Collaborators and Team Access |
| Deployments and environments | Repository > Deployments and Environments |
| Repository health snapshot (opt-in) | Repository > Insights > Health Snapshot |
| Repository labels | Repository > Labels |
| GitHub Pages and builds | Repository > GitHub Pages |
| Repository Discussions | Repository > Discussions |
| Repository security alerts | Repository > Security > Alerts |
| Insights: traffic and contributors | Repository > Insights > Traffic and Contributors |
| Community profile checklist | Repository > Insights > Community Profile |
| Actions caches | Repository > Actions > Caches |
| Secret and variable names | Repository > Settings > Secret and Variable Names |
| Dismissed and resolved security alerts | Repository > Security > Dismissed and Resolved Alerts |
| Saved Searches..., Save Search | Search > Saved Searches; filter box > Save Search |

### The editor's GitHub menu rows (Workbench Mode)

| Today | New home |
|---|---|
| Leave Workbench Mode | Stays |
| Inbox... | Stays: opens Needs My Attention > Inbox |
| My Work..., Notifications... | Command ids kept, open their nodes; rows leave the menu |
| Issues and Pull Requests... | Becomes This Repository's Issues and This Repository's Pull Requests |
| Actions Runs... | Stays |
| Releases..., Repository Items..., Explore GitHub... | Command ids kept, open their nodes; Open GitHub Workbench replaces the rows |
| Open GitHub Reference..., GitHub File URL... | Open GitHub Address... |
| Open a Repository..., Clone Repository... | Clone stays; Open a Repository moves to Workbench > File |
| Commit to GitHub..., Sync Folder with GitHub... | Stay (QUILL only) |
| Repository Admin submenu | Workbench > Repository > Settings, Fork, Create Repository (File > Create Repository...), Browse Organization Repositories (Repositories > Organizations), Create Release (File), Dispatch Workflow, Security Alerts |
| Local Git submenu | Stays in the editor |
| Codespaces submenu | Workbench > Repository > Codespaces |
| Manage GitHub Accounts..., Open GitHub Guide | Stay |

### Preferences

| Today | New home |
|---|---|
| Notification poll interval, audible tick, interrupt speech (main Settings) | Tools > Workbench Options > Notifications and Inbox |
| Queue Options..., Choose Categories..., Choose Repositories..., Save Current Filter... | Tools > Workbench Options > Notifications and Inbox; Account > Notification and Inbox Options |
| Include read notifications | Tools > Workbench Options > Notifications and Inbox |
| Health snapshot opt-in | Tools > Workbench Options > Privacy and opt-ins |
| Columns, list mode, sort, state defaults | Tools > Workbench Options > General and Lists |
| Last view, filter, selection, history (resume state) | Stays in `github_items_context.json`; cleared from Privacy and opt-ins |

## Appendix B: existing actions not covered above

Found in the GitHub UI modules on a second pass. Each keeps its handler. Its
menu home is decided here, and (Jeff, 2026-11-09: "all of this needs to be
covered as well") each one also has a place on its object's Properties sheet,
so Alt+Enter reaches every one of them.

| Existing action | New home | On the Properties sheet |
|---|---|---|
| Set Topics... | Repository > Settings > General | Repository > General: Topics |
| Sync Fork with Upstream... | Repository menu; Repository > Code > Upstream context menu | Repository > Fork: Sync with Upstream, with ahead and behind counts |
| Archive Repository..., Unarchive Repository... | Repository > Settings | Repository > Danger Zone: Archived |
| Delete Repository... | Repository > Settings (last, with its typed confirmation) | Repository > Danger Zone: Delete (tier 3) |
| Create Repository from This Template... | Repository menu, shown only for template repositories | Repository > General: Template repository, and Use This Template... |
| Watch Level... | Repository > Watch Level... (replaces the bare Watch and Unwatch pair on the menu bar; both stay on context menus) | Repository > You: Watch level, with custom events |
| Use Repository | Gone: selecting the repository's node is "use" | Not needed |
| Add Blocker..., Remove Blocker..., Add Sub-issue..., Remove Sub-issue... | Item > Relationships submenu | Issue > Relationships: parent, sub-issues in order, blocked by, blocking |
| Next Unblocked | Go > Next Unblocked (Projects and Dependencies) | Issue > Relationships: "Unblocked" line, and Go to Next Unblocked |
| Possible Duplicate Issues (check when filing) | Stays in New Issue...; also Item > Find Possible Duplicates | Issue > Relationships: Possible duplicates, and Close as Duplicate of... |
| Projects and Dependencies, Edit Project Field..., Refresh Board | The Projects node (board as a list, linear order); Item > Edit Project Field... | Issue or PR > Projects: every field of every project; Project sheet (section 16.6) |
| Compose Review..., Request Changes, Request Reviewers..., Request Copilot Review | PR context menu > Review...; Item > Review submenu | Pull request > Reviews: reviewers and teams, their states, Request, Remove, Request Copilot Review |
| Mark Ready, convert to draft | Item > Mark Ready for Review / Convert to Draft | Pull request > General: Draft |
| Update Branch... | Item > Update Branch... | Pull request > Branches: base, head, behind by n, Update Branch (merge or rebase) |
| Enable Auto-Merge..., Disable Auto-Merge... | Item > Merge submenu | Pull request > Merge: auto-merge and its method |
| Add to Merge Queue..., Remove from Merge Queue... | Item > Merge submenu | Pull request > Merge: merge queue position |
| Check Merge Policy | Item > Merge submenu > Why Can't I Merge?; the PR's details pane | Pull request > Merge: every requirement, met or not, in words |
| Re-request Check..., Copy Check Details | Item > Checks submenu | Pull request > Checks: each check, state, duration, Re-run, Copy Details |
| Next Unresolved, Reply to Thread..., Copy Thread Link | Inside PR review, unchanged | Review thread sheet: file, line, state, Resolve or Reopen, Reply |
| Pending comment edit and delete | Inside PR review, unchanged | Comment sheet: body, Edit, Delete (pending review comments) |
| Copy Conversation, Copy Review Summary, Copy File Name, Copy Pull Request Link | Edit > Copy submenu (rows greyed where they do not apply) | Every sheet: Copy as Text, Copy Link |
| React to Pull Request..., React to a Comment... | Item > React... | Issue, PR, comment and discussion > You: reactions, each with its count and whether it is yours |
| Mark discussion answer, unmark answer | Discussion comment context menu | Discussion comment sheet: Answer |
| Create milestone | Repository > Milestones node context menu > New Milestone... | Milestone sheet: title, description, due date, state, progress; New... in every milestone picker |
| Lock Conversation... (with reason), Unlock Conversation | Item > Lock Conversation... | Issue or PR > Conversation: Locked, with reason |
| Dependabot, code scanning and secret scanning alerts; Dismiss Alert..., Reopen Alert... | Repository > Security > Alerts (one list, a Kind column); alert context menu | Alert sheet: kind, severity, package or rule, location, state, Dismiss with reason and comment, Reopen, Assign |
| Pull request and issue templates and forms | New Issue... and New Pull Request..., which now fill issue forms natively (section 21.7) | Repository > Templates: a sheet per template with a field builder, preview and checks (section 21) |
| Thread subscription (Unsubscribe from Thread) | Notification context menu, unchanged | Notification and item > You: Subscribed, with reason |

## Appendix C: every object, its Properties sheet, and its filters

One entry per object type. **Pages** are the sheet's pages in order (General
first, You second where it applies). **Change** is every field you can edit,
given the permission. **Do** is every action on the object beyond editing.
**Filter** is what its list can be filtered and sorted on, every one of
which also has "has none" where the attribute is a list. Every entry also
has Copy as Text, Copy Link, Open on GitHub and F1 on every field, which are
not repeated.

### Repositories and code

**Repository**
- Pages: General, You, Fork, Features, Merging, Branches and Rules,
  Access, Actions, Environments, Security, Pages, Webhooks, Deploy Keys,
  Autolinks, Secrets and Variables, Templates, Insights, Danger Zone.
- Change: name, description, website, topics, visibility, default branch,
  template repository, social preview (open on GitHub; no API), features
  (issues, projects, wiki, discussions, sponsorships, preserve this
  repository), merge methods allowed (merge, squash, rebase) and their default
  commit messages, allow auto-merge, always suggest updating branches,
  automatically delete head branches, allow forking (organization private
  repositories), require contributors to sign off on web commits, custom
  properties (organization), Pages source and domain and HTTPS, security
  features (section 18.3), interaction limits.
- Do: star, watch, fork, sync fork, clone, open in Codespaces, create from
  template, transfer, archive and unarchive, delete, run workflow, compare
  branches, generate release notes, export the access list.
- Filter: owner, name, topic, language, visibility, fork or source,
  archived, template, stars, forks, open issues, size, license, created,
  updated, pushed, has issues, has wiki, has discussions, has Pages, your
  role (admin, maintain, write, triage, read), custom properties.

**Branch**
- Pages: General, Protection, Commits, Compare.
- Change: name (rename), protection or rulesets that target it (link to the
  rule's sheet).
- Do: commits, compare with any branch, create a pull request, create a
  branch from it, delete, restore a deleted branch from its pull request,
  open in Codespaces, start in a local worktree, set as default.
- Filter: name pattern, protected, ahead and behind the default branch,
  last commit date, last commit author, has an open pull request, merged.

**Tag**
- Pages: General, Commit, Release.
- Change: none (tags are immutable; protection lives in rulesets).
- Do: create (lightweight or annotated, on any commit), delete, create a
  release from it, compare with another tag.
- Filter: name pattern, date, has release, annotated.

**Commit**
- Pages: General, Files, Checks, Comments, Branches and Tags.
- Change: none (commits are immutable); comments on it are editable.
- Do: comment, comment on a line, revert (as a pull request), cherry-pick to
  a branch (as a pull request), create a branch or tag here, browse files at
  this commit, compare with its parent or any commit.
- Filter: author, committer, date range, path, branch, message text,
  verified signature, check state.

**File and folder (repository contents)**
- Pages: General, History, Blame (as a list of line ranges), Code Owners.
- Change: contents (opens in the editor; Commit to GitHub saves), name and
  path (move), delete.
- Do: open in editor, open at a commit, copy permalink, history, blame,
  create a file here, upload files, download.
- Filter: name, extension, path, size, last changed.

**Ruleset and branch protection rule**
- Pages: General, Target, Bypass, Rules, Summary, History (rule insights).
- Change: everything in section 18.3.1.
- Do: create, copy to other repositories, export and import as JSON, delete,
  evaluate mode on and off, view rule insights (which pushes it blocked or
  would have).
- Filter: target, enforcement, rule kind, bypass actor.

### Issues, pull requests and conversations

**Issue**
- Pages: General, You, Organize, Projects, Relationships, Development,
  Conversation, Timeline, Access (who can triage it, read-only).
- Change: title, body, state and state reason, labels, assignees,
  milestone, issue type, projects and every project field, parent,
  sub-issues and their order, blocked by and blocking, lock and reason, pin,
  subscribe.
- Do: comment, edit and delete your comments, hide others' comments with a
  reason (with permission), react, transfer, convert to discussion, create a
  branch for it, link a pull request, assign to Copilot, summarize, find
  possible duplicates, close as duplicate, delete (admins).
- Filter: everything in section 17.3.

**Pull request**
- Pages: General, You, Organize, Projects, Branches, Reviews, Checks,
  Merge, Files, Commits, Relationships, Conversation, Timeline.
- Change: title, body, draft or ready, base branch, labels, assignees,
  milestone, projects and their fields, reviewers and teams, maintainers
  may edit, auto-merge and method, lock, subscribe.
- Do: review (comment, approve, request changes), reply and resolve
  threads, suggest changes, commit suggestions, update branch (merge or
  rebase), merge (each allowed method, with message), add to merge queue,
  close, reopen, revert, request Copilot review, start in local worktree,
  open in Codespaces, diff, re-run checks, delete the head branch after merge.
- Filter: section 17.3, plus review state, review requested, reviewed by,
  checks, merge state, base, head, draft, merged date, files changed, lines
  added and removed (local), auto-merge on.

**Comment** (on an issue, pull request, commit, discussion or gist)
- Pages: General, You, History (edit history).
- Change: body (yours, or anyone's with permission).
- Do: reply, quote reply, react, hide with a reason and unhide, delete,
  report (opens GitHub), copy link.
- Filter: author, date, edited, hidden, reactions, mentions me.

**Review and review thread**
- Pages: General (state, author, submitted), Threads; for a thread: file,
  line range, side, outdated, resolved, comments.
- Change: a pending review's body and comments; a thread's resolved state.
- Do: submit, dismiss a review with a message (with permission), resolve,
  reopen, reply, copy thread link, go to the line in the diff or the editor.
- Filter: reviewer, state, resolved, outdated, file.

**Discussion**
- Pages: General, You, Category, Answer, Conversation, Poll.
- Change: title, body, category, labels, lock, pin (and pin settings).
- Do: comment, reply, mark and unmark an answer, upvote, react, transfer,
  convert to an issue (from an issue: convert to discussion), close with a
  reason (resolved, outdated, duplicate), reopen, delete, vote in a poll.
- Filter: category, answered, author, label, state, created, updated,
  comments, upvotes.

**Discussion category**
- Pages: General.
- Change: name, emoji, description, format (open-ended, question and answer,
  announcement, poll), section. (GitHub manages categories on the web only
  today; the coverage table keeps the row so it moves when an API appears.)
- Filter: format.

**Label**
- Pages: General, Usage.
- Change: name, colour (by name, with the nearest common colour spoken, and
  as hex), description.
- Do: create, delete, find issues and pull requests with it, copy to other
  repositories, apply GitHub's default label set.
- Filter: name, colour, has description, in use count.

**Milestone**
- Pages: General, Progress, Items.
- Change: title, description, due date, state (open or closed).
- Do: create, delete, list its items, move all open items to another
  milestone, copy to other repositories.
- Filter: state, due date, overdue, has due date, progress percentage.

**Issue type** (organization)
- Pages: General.
- Change: name, description, colour, enabled.
- Do: create, delete, list issues of this type.
- Filter: enabled.

**Issue form, Markdown template, pull request template, discussion form**
- Pages: General, Fields, Preview, Checks, Source (section 21.3).
- Change: every key GitHub's schema has, and every field's every attribute;
  the chooser's blank-issues switch, contact links and order.
- Do: create from a starter, copy, convert, write as BFL, check, save to a
  branch or with a pull request, copy to repositories, delete, fill it in.
- Filter: kind, labels applied, field count, has required fields, inherited,
  repository (organization view).

### Projects

**Project** (Projects, version 2)
- Pages: General, Fields, Views, Items, Workflows, Status Updates, Access,
  Linked Repositories.
- Change: everything in section 16.6.
- Do: create (blank or from a template), copy, close and reopen, delete,
  mark as template, link and unlink repositories and teams, export a view as
  CSV.
- Filter (the projects list): owner, open or closed, template, updated,
  linked repository.

**Project item**
- Pages: General, Fields, Content (the issue, pull request or draft).
- Change: every field value, position, archived.
- Do: open the issue or pull request, convert a draft to an issue, archive,
  restore, delete, move to a column.
- Filter: every project field, by its type, plus GitHub's project filter
  syntax (`status:"In progress" iteration:@current -assignee:@me`).

**Project field and view**
- Pages: General, Options (single select) or Iterations (iteration); for a
  view: Layout, Filter, Sort, Group, Fields.
- Change: name, type at creation, options and their order, colours and
  descriptions, iterations and their dates and breaks; a view's name, layout,
  filter, sort, group, and visible fields in order.
- Do: create, copy, delete.

### Actions and deployments

**Workflow**
- Pages: General, Runs, Triggers, Usage.
- Change: enabled or disabled.
- Do: run (with its inputs, each as a labelled control by its type), open the
  workflow file in the editor, view runs, create a status badge link.
- Filter: name, state, path, last run state.

**Workflow run**
- Pages: General, Jobs, Artifacts, Annotations, Logs, Usage, Deployments.
- Change: none.
- Do: what failed, re-run all, re-run failed jobs, re-run one job (with
  debug logging on or off), cancel, force cancel, approve a fork run, review
  pending deployments, delete, delete logs, download logs and artifacts.
- Filter: workflow, branch, event, actor, status, conclusion, created,
  duration (local), head commit.

**Job**
- Pages: General, Steps, Log, Annotations.
- Do: re-run, open its log in the editor, go to the failing step.
- Filter: status, conclusion, runner name.

**Artifact and Actions cache**
- Pages: General.
- Do: download, delete; for caches, delete by key or prefix.
- Filter: name, size, created, expires, branch (caches: key, ref, last used).

**Environment**
- Pages: General, Protection, Branches and Tags, Secrets, Variables,
  Deployments.
- Change: everything in section 18.3 for environments.
- Do: create, delete, view deployments.
- Filter: name, has protection.

**Deployment**
- Pages: General, Statuses.
- Do: create a status (in progress, success, failure, inactive), delete an
  inactive deployment.
- Filter: environment, ref, creator, state, date.

**Runner and runner group**
- Pages: General, Labels, Repositories (groups).
- Change: labels; a group's name, visibility and repositories.
- Do: remove a runner, create a registration token link (opens GitHub's
  setup steps), create, rename and delete groups.
- Filter: status, busy, labels, OS.

**Secret and variable** (repository, environment, organization, Codespaces,
Dependabot)
- Pages: General, Repositories (organization).
- Change: variables' values; secrets' values write-only (decision 12);
  organization visibility (all, private, selected) and selected repositories.
- Do: create, delete.
- Filter: name, updated, visibility.

### Releases and packages

**Release**
- Pages: General, Notes, Assets, Discussion.
- Change: tag, target, title, notes, draft, prerelease, latest, make
  discussion.
- Do: create, generate notes, publish a draft, delete, upload assets,
  compare with the previous release.
- Filter: draft, prerelease, latest, author, date, tag pattern.

**Release asset**
- Pages: General.
- Change: name, label.
- Do: download, delete, copy link.
- Filter: name, size, downloads, content type.

**Package** (container, npm, Maven, NuGet, RubyGems)
- Pages: General, Versions, Access, Repository.
- Change: visibility, access (section 18.3), linked repository.
- Do: delete or restore a package or a version, copy the install command.
- Filter: type, visibility, repository, updated, version tag.

### People, teams and organizations

**Person**
- Pages: General, You, Repositories, Activity, Followers, Following,
  Organizations, Sponsors.
- Change (your own profile): section 16.7.
- Do: follow, block, sponsor, invite to a repository or organization, see
  their access here (section 18.3.2).
- Filter: name, location, company, followers, repositories, type (user or
  organization), your relationship (following, follows you, blocked).

**Organization**
- Pages: General, You, Members, Teams, Outside Collaborators,
  Invitations, Roles, Member Privileges, Repositories, Projects, Packages,
  Actions, Security, Webhooks, Secrets and Variables, Issue Types, Custom
  Properties, Audit Log, Token Requests, Billing.
- Change: profile (name, description, email, location, website, blog),
  everything in section 18.3 for organizations, default repository
  settings, custom properties schema.
- Do: invite, remove, convert a member to outside collaborator, set
  membership visibility, leave, follow.
- Filter (members list): role, two-factor on or off (owners), membership
  public or private, team.

**Team**
- Pages: General, Members, Repositories, Projects, Child Teams, Discussions
  (legacy, read), Review Assignment.
- Change: name, description, privacy, parent, notifications, members and
  roles, repository and project roles, code review assignment (round robin
  or load balance, how many, exclusions).
- Do: create, delete, add and remove members and repositories in batch.
- Filter: privacy, parent, member, repository, role.

**Collaborator and invitation**
- Pages: General (role, source, since).
- Change: role.
- Do: remove, resend (cancel and invite again), cancel.
- Filter: role, source, pending.

### Gists and Codespaces

**Gist**
- Pages: General, You, Files, Revisions, Forks, Comments.
- Change: description, secret to public (GitHub cannot make a public gist
  secret again, and the sheet says so before you change it), files (add,
  rename, edit, delete).
- Do: star, fork, clone, pin to profile, comment, delete, open a revision.
- Filter: public or secret, starred, file name, language, updated.

**Codespace**
- Pages: General, Machine, Ports, Usage.
- Change: display name, machine type, idle timeout, retention.
- Do: create (each with its cost confirmation), start, stop, rebuild, open in
  VS Code or the browser, export unpushed changes to a branch, delete.
- Filter: repository, branch, state, machine, last used.

### Security

**Security alert** (Dependabot, code scanning, secret scanning)
- Pages: General, Location, History, Fix.
- Change: state, dismissal reason and comment, assignee (code scanning).
- Do: dismiss, reopen, open the file at the line, create a Dependabot
  security update pull request, view the advisory, resolve a secret alert
  with a reason (revoked, false positive, used in tests, won't fix).
- Filter: kind, severity, state, ecosystem, package, manifest, rule, tool,
  secret type, branch, created, fixed.

**Security advisory** (repository) **and policy**
- Pages: General, Affected Products, Credits, Collaborators, Private Fork.
- Change: summary, description, severity and CVSS, CWEs, affected packages
  and versions, patched versions, credits, collaborators.
- Do: create a draft, request a CVE, create a private fork, publish, close;
  edit SECURITY.md in the editor; turn private vulnerability reporting on or
  off; accept or reject a private report.
- Filter: state, severity, published.

### Notifications, searches and the Workbench's own things

**Notification**
- Pages: General (reason, repository, subject, last update), You.
- Do: section 16.7.
- Filter: reason, repository, type, unread, participating, date, saved.

**Saved search, pin and favorite**
- Pages: General.
- Change: name, query, the tree branch it appears under, its columns.
- Do: run, copy the query, delete.

**Account** (a QUILL GitHub account)
- Pages: General, Permissions, Workbench Access (Read Only, Organize, Full),
  Change History, Rate Limit.
- Change: display name in QUILL, Workbench access level, default account.
- Do: sign in again, add permissions, switch to, remove from QUILL.

## Appendix D: the permissions catalogue

What each kind of permission controls, and where in the Workbench it is set.
Section 18.3 describes the pages; this is the checklist the Access pages are
built and tested against.

| Object | Who can be granted access | Roles or settings | Workbench home |
|---|---|---|---|
| Repository | people, teams, outside collaborators | read, triage, write, maintain, admin, custom roles | Repository sheet > Access |
| Repository (organization base) | every member | none, read, write, admin | Organization sheet > Member Privileges |
| Organization | people | member, owner; billing manager, security manager, moderator, custom organization roles | Organization sheet > Members, Roles |
| Organization member privileges | every member | create public, private, internal repositories; fork private; create Pages; create teams; change visibility; delete and transfer; invite outside collaborators; see member list | Organization sheet > Member Privileges |
| Team | people | member, maintainer; team privacy; parent | Team sheet > Members |
| Team on a repository or project | teams | repository roles; project read, write, admin | Team sheet > Repositories, Projects |
| Branches and tags | roles, teams, apps (bypass) | each rule in section 18.3.1; enforcement | Ruleset sheet; Branch sheet > Protection |
| Environment | people, teams (reviewers) | required reviewers, prevent self-review, wait timer, deployment branches and tags, admin bypass | Environment sheet > Protection |
| Actions (repository and organization) | repositories (organization), workflows | allowed actions and patterns, `GITHUB_TOKEN` default permission, create and approve pull requests, fork approval policy, retention | Repository or Organization sheet > Actions |
| Runner groups | repositories, workflows | which repositories and workflows may use the group | Runner group sheet |
| Secrets and variables (organization) | repositories | all, private only, selected | Secret sheet > Repositories |
| Project | people, teams, organization base | read, write, admin; visibility | Project sheet > Access |
| Package | people, teams, repositories | read, write, admin; inherit from repository; visibility | Package sheet > Access |
| Codespaces (organization) | members, repositories | who may create, for which repositories, spending limits (read) | Organization sheet > Codespaces |
| Security features | repository, organization | private vulnerability reporting, Dependabot alerts and updates, secret scanning and push protection, code scanning setup, security managers | Repository or Organization sheet > Security |
| Interaction limits | everyone outside a level | existing users, contributors only, collaborators only; duration | Repository or Organization sheet > General |
| Deploy keys | a key | read-only or read-write | Repository sheet > Deploy Keys |
| Webhooks | an address | events, active, content type, secret (write-only) | Repository or Organization sheet > Webhooks |
| Fine-grained token requests (organization) | people's tokens | approve, deny, revoke | Organization sheet > Token Requests |
| Gists | everyone | public or secret | Gist sheet > General |
| Your account in the Workbench | this device | Read Only, Organize, Full | Account sheet > Workbench Access |
| Your token or sign-in | QUILL | scopes or fine-grained permissions | Account > GitHub Permissions... |

Each row is a test case for GATE-GITHUB-PERM: the Access page exists, every
role GitHub lists for it can be chosen, every change previews in words, and
the tier is right.

## Appendix E: the REST API, every operation and its home

Generated from GitHub's published OpenAPI description (`github/rest-api-description`, `api.github.com`, version 1.1.4), read 2026-11-09: **1272 operations in 51 categories**. This is the snapshot section 19 vendors; `api_coverage.json` will carry the same rows with their status (`covered`, `planned`, `no_api_needed`, `out_of_scope`) and command id.

How to read each table:

- **Operation** is GitHub's own name for it.
- **Call** is the method and path.
- **Classic scope** is the token scope GitHub's description says it needs, where it says one. Fine-grained tokens and the OAuth sign-in are checked per object (section 18.2), so a dash means the description names none, not that none is needed.
- **Tier** is the confirmation tier of section 18.4 as a starting point: read, 1 (visible to others), 2 (access and settings), 3 (destructive). Phase 10 reviews each write row by hand; for example deleting a label is tier 3 here and may be judged tier 2.

Categories, in order of size:

- actions: 208 operations, in scope
- orgs: 129 operations, in scope
- repos: 73 operations, in scope
- issues: 66 operations, in scope
- codespaces: 48 operations, in scope
- users: 47 operations, in scope
- copilot: 44 operations, in scope
- pulls: 39 operations, in scope
- branches: 38 operations, in scope
- apps: 37 operations, in scope
- activity: 34 operations, in scope
- teams: 32 operations, in scope
- agents: 30 operations, in scope
- copilot-spaces: 28 operations, in scope
- dependabot: 27 operations, in scope
- packages: 27 operations, in scope
- projects: 26 operations, in scope
- code-scanning: 25 operations, in scope
- migrations: 22 operations, in scope
- deployments: 21 operations, in scope
- code-security: 20 operations, in scope
- gists: 20 operations, in scope
- secret-scanning: 17 operations, in scope
- interactions: 16 operations, in scope
- reactions: 15 operations, in scope
- security-advisories: 14 operations, in scope
- commits: 14 operations, in scope
- billing: 13 operations, in scope
- git: 13 operations, plumbing (no_api_needed)
- releases: 13 operations, in scope
- agent-automations: 12 operations, in scope
- checks: 12 operations, in scope
- pages: 12 operations, in scope
- collaborators: 11 operations, in scope
- metrics: 10 operations, in scope
- search: 7 operations, in scope
- classroom: 6 operations, in scope
- private-registries: 6 operations, in scope
- meta: 5 operations, plumbing (no_api_needed)
- agent-tasks: 5 operations, in scope
- campaigns: 5 operations, in scope
- dependency-graph: 5 operations, in scope
- code-quality: 4 operations, in scope
- deploy-keys: 4 operations, in scope
- licenses: 3 operations, in scope
- codes-of-conduct: 2 operations, in scope
- gitignore: 2 operations, in scope
- markdown: 2 operations, plumbing (no_api_needed)
- credentials: 1 operations, out of scope
- emojis: 1 operations, plumbing (no_api_needed)
- rate-limit: 1 operations, in scope

### REST: actions (208 operations)

Home: Repository > Actions; Organization sheet > Actions; Run, Job, Workflow, Artifact, Cache, Runner, Secret and Variable sheets. Coverage: in scope.

#### actions / artifacts (5)

Home: Run > Artifacts; Artifact sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List artifacts for a repository | `GET /repos/{owner}/{repo}/actions/artifacts` | `repo` | read |
| Delete an artifact | `DELETE /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | `repo` | 3 |
| Get an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}` | `repo` | read |
| Download an artifact | `GET /repos/{owner}/{repo}/actions/artifacts/{artifact_id}/{archive_format}` | `repo` | read |
| List workflow run artifacts | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts` | `repo` | read |

#### actions / cache (18)

Home: Repository > Actions > Caches; Cache sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get GitHub Actions cache retention limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/retention-limit` | `admin:enterprise` | read |
| Set GitHub Actions cache retention limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/retention-limit` | `admin:enterprise` | 1 |
| Get GitHub Actions cache storage limit for an enterprise | `GET /enterprises/{enterprise}/actions/cache/storage-limit` | `admin:enterprise` | read |
| Set GitHub Actions cache storage limit for an enterprise | `PUT /enterprises/{enterprise}/actions/cache/storage-limit` | `admin:enterprise` | 1 |
| Get GitHub Actions cache retention limit for an organization | `GET /organizations/{org}/actions/cache/retention-limit` | `admin:organization` | read |
| Set GitHub Actions cache retention limit for an organization | `PUT /organizations/{org}/actions/cache/retention-limit` | `admin:organization` | 1 |
| Get GitHub Actions cache storage limit for an organization | `GET /organizations/{org}/actions/cache/storage-limit` | `admin:organization` | read |
| Set GitHub Actions cache storage limit for an organization | `PUT /organizations/{org}/actions/cache/storage-limit` | `admin:organization` | 1 |
| Get GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage` | `read:org` | read |
| List repositories with GitHub Actions cache usage for an organization | `GET /orgs/{org}/actions/cache/usage-by-repository` | `read:org` | read |
| Get GitHub Actions cache retention limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/retention-limit` | `admin:repository` | read |
| Set GitHub Actions cache retention limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/retention-limit` | `admin:repository` | 1 |
| Get GitHub Actions cache storage limit for a repository | `GET /repos/{owner}/{repo}/actions/cache/storage-limit` | `admin:repository` | read |
| Set GitHub Actions cache storage limit for a repository | `PUT /repos/{owner}/{repo}/actions/cache/storage-limit` | `admin:repository` | 1 |
| Get GitHub Actions cache usage for a repository | `GET /repos/{owner}/{repo}/actions/cache/usage` | `repo` | read |
| Delete GitHub Actions caches for a repository (using a cache key) | `DELETE /repos/{owner}/{repo}/actions/caches` | `repo` | 3 |
| List GitHub Actions caches for a repository | `GET /repos/{owner}/{repo}/actions/caches` | `repo` | read |
| Delete a GitHub Actions cache for a repository (using a cache ID) | `DELETE /repos/{owner}/{repo}/actions/caches/{cache_id}` | `repo` | 3 |

#### actions / concurrency-groups (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List concurrency groups for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups` | `repo` | read |
| Get a concurrency group for a repository | `GET /repos/{owner}/{repo}/actions/concurrency_groups/{concurrency_group_name}` | `repo` | read |
| List concurrency groups for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/concurrency_groups` | `repo` | read |

#### actions / hosted-runners (16)

Home: Organization sheet > Actions > Hosted runners.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners` | `manage_runner:org` | read |
| Create a GitHub-hosted runner for an organization | `POST /orgs/{org}/actions/hosted-runners` | `manage_runners:org` | 1 |
| List custom images for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom` | `manage_runners:org` | read |
| Delete a custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | `manage_runners:org` | 3 |
| Get a custom image definition for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}` | `manage_runners:org` | read |
| List image versions of a custom image for an organization | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions` | `manage_runners:org` | read |
| Delete an image version of custom image from the organization | `DELETE /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | `manage_runners:org` | 3 |
| Get an image version of a custom image for GitHub Actions Hosted Runners | `GET /orgs/{org}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}` | `manage_runners:org` | read |
| Get GitHub-owned images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/github-owned` | - | read |
| Get partner images for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/images/partner` | - | read |
| Get limits on GitHub-hosted runners for an organization | `GET /orgs/{org}/actions/hosted-runners/limits` | - | read |
| Get GitHub-hosted runners machine specs for an organization | `GET /orgs/{org}/actions/hosted-runners/machine-sizes` | - | read |
| Get platforms for GitHub-hosted runners in an organization | `GET /orgs/{org}/actions/hosted-runners/platforms` | - | read |
| Delete a GitHub-hosted runner for an organization | `DELETE /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | - | 3 |
| Get a GitHub-hosted runner for an organization | `GET /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | `manage_runners:org` | read |
| Update a GitHub-hosted runner for an organization | `PATCH /orgs/{org}/actions/hosted-runners/{hosted_runner_id}` | `manage_runners:org` | 1 |

#### actions / oidc (10)

Home: Repository and Organization sheets > Actions > OpenID Connect.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List OIDC custom property inclusions for an enterprise | `GET /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | `admin:enterprise` | read |
| Create an OIDC custom property inclusion for an enterprise | `POST /enterprises/{enterprise}/actions/oidc/customization/properties/repo` | `admin:enterprise` | 2 |
| Delete an OIDC custom property inclusion for an enterprise | `DELETE /enterprises/{enterprise}/actions/oidc/customization/properties/repo/{custom_property_name}` | `admin:enterprise` | 3 |
| List OIDC custom property inclusions for an organization | `GET /orgs/{org}/actions/oidc/customization/properties/repo` | `read:org` | read |
| Create an OIDC custom property inclusion for an organization | `POST /orgs/{org}/actions/oidc/customization/properties/repo` | `admin:org` | 2 |
| Delete an OIDC custom property inclusion for an organization | `DELETE /orgs/{org}/actions/oidc/customization/properties/repo/{custom_property_name}` | `admin:org` | 3 |
| Get the customization template for an OIDC subject claim for an organization | `GET /orgs/{org}/actions/oidc/customization/sub` | `read:org` | read |
| Set the customization template for an OIDC subject claim for an organization | `PUT /orgs/{org}/actions/oidc/customization/sub` | `write:org` | 2 |
| Get the customization template for an OIDC subject claim for a repository | `GET /repos/{owner}/{repo}/actions/oidc/customization/sub` | `repo` | read |
| Set the customization template for an OIDC subject claim for a repository | `PUT /repos/{owner}/{repo}/actions/oidc/customization/sub` | `repo` | 2 |

#### actions / permissions (36)

Home: Repository and Organization sheets > Actions (section 18.3).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get GitHub Actions permissions for an organization | `GET /orgs/{org}/actions/permissions` | `admin:org` | read |
| Set GitHub Actions permissions for an organization | `PUT /orgs/{org}/actions/permissions` | `admin:org` | 2 |
| Get artifact and log retention settings for an organization | `GET /orgs/{org}/actions/permissions/artifact-and-log-retention` | `admin:org` | read |
| Set artifact and log retention settings for an organization | `PUT /orgs/{org}/actions/permissions/artifact-and-log-retention` | `admin:org` | 2 |
| Get fork PR contributor approval permissions for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | `admin:org` | read |
| Set fork PR contributor approval permissions for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-contributor-approval` | `admin:org` | 2 |
| Get private repo fork PR workflow settings for an organization | `GET /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | - | read |
| Set private repo fork PR workflow settings for an organization | `PUT /orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` | - | 2 |
| List selected repositories enabled for GitHub Actions in an organization | `GET /orgs/{org}/actions/permissions/repositories` | `admin:org` | read |
| Set selected repositories enabled for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories` | `admin:org` | 2 |
| Disable a selected repository for GitHub Actions in an organization | `DELETE /orgs/{org}/actions/permissions/repositories/{repository_id}` | `admin:org` | 3 |
| Enable a selected repository for GitHub Actions in an organization | `PUT /orgs/{org}/actions/permissions/repositories/{repository_id}` | `admin:org` | 2 |
| Get allowed actions and reusable workflows for an organization | `GET /orgs/{org}/actions/permissions/selected-actions` | `admin:org` | read |
| Set allowed actions and reusable workflows for an organization | `PUT /orgs/{org}/actions/permissions/selected-actions` | `admin:org` | 2 |
| Get self-hosted runners settings for an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners` | `admin:org` | read |
| Set self-hosted runners settings for an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners` | `admin:org` | 2 |
| List repositories allowed to use self-hosted runners in an organization | `GET /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | `admin:org` | read |
| Set repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories` | `admin:org` | 2 |
| Remove a repository from the list of repositories allowed to use self-hosted runners in an organization | `DELETE /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | `admin:org` | 3 |
| Add a repository to the list of repositories allowed to use self-hosted runners in an organization | `PUT /orgs/{org}/actions/permissions/self-hosted-runners/repositories/{repository_id}` | `admin:org` | 2 |
| Get default workflow permissions for an organization | `GET /orgs/{org}/actions/permissions/workflow` | `admin:org` | read |
| Set default workflow permissions for an organization | `PUT /orgs/{org}/actions/permissions/workflow` | `admin:org` | 2 |
| Get GitHub Actions permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions` | `repo` | read |
| Set GitHub Actions permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions` | `repo` | 2 |
| Get the level of access for workflows outside of the repository | `GET /repos/{owner}/{repo}/actions/permissions/access` | `repo` | read |
| Set the level of access for workflows outside of the repository | `PUT /repos/{owner}/{repo}/actions/permissions/access` | `repo` | 2 |
| Get artifact and log retention settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | `repo` | read |
| Set artifact and log retention settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` | `repo` | 2 |
| Get fork PR contributor approval permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | `repo` | read |
| Set fork PR contributor approval permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` | `repo` | 2 |
| Get private repo fork PR workflow settings for a repository | `GET /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | `repo` | read |
| Set private repo fork PR workflow settings for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-workflows-private-repos` | `repo` | 2 |
| Get allowed actions and reusable workflows for a repository | `GET /repos/{owner}/{repo}/actions/permissions/selected-actions` | `repo` | read |
| Set allowed actions and reusable workflows for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/selected-actions` | `repo` | 2 |
| Get default workflow permissions for a repository | `GET /repos/{owner}/{repo}/actions/permissions/workflow` | `repo` | read |
| Set default workflow permissions for a repository | `PUT /repos/{owner}/{repo}/actions/permissions/workflow` | `repo` | 2 |

#### actions / policies (10)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization Actions policies | `GET /orgs/{org}/actions/policies` | - | read |
| Create an organization Actions policy | `POST /orgs/{org}/actions/policies` | - | 1 |
| Delete an organization Actions policy | `DELETE /orgs/{org}/actions/policies/{policy_id}` | - | 3 |
| Get an organization Actions policy | `GET /orgs/{org}/actions/policies/{policy_id}` | - | read |
| Update an organization Actions policy | `PUT /orgs/{org}/actions/policies/{policy_id}` | - | 1 |
| List repository Actions policies | `GET /repos/{owner}/{repo}/actions/policies` | - | read |
| Create a repository Actions policy | `POST /repos/{owner}/{repo}/actions/policies` | - | 1 |
| Delete a repository Actions policy | `DELETE /repos/{owner}/{repo}/actions/policies/{policy_id}` | - | 3 |
| Get a repository Actions policy | `GET /repos/{owner}/{repo}/actions/policies/{policy_id}` | - | read |
| Update a repository Actions policy | `PUT /repos/{owner}/{repo}/actions/policies/{policy_id}` | - | 1 |

#### actions / secrets (20)

Home: Secret and variable sheets (write-only values).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization secrets | `GET /orgs/{org}/actions/secrets` | `admin:org` | read |
| Get an organization public key | `GET /orgs/{org}/actions/secrets/public-key` | `repo` | read |
| Delete an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}` | `repo` | 3 |
| Get an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}` | `repo` | read |
| Create or update an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}` | `repo` | 2 |
| List selected repositories for an organization secret | `GET /orgs/{org}/actions/secrets/{secret_name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories` | `admin:org` | 2 |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization secret | `PUT /orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` | `admin:org`, `repo` | 2 |
| List repository organization secrets | `GET /repos/{owner}/{repo}/actions/organization-secrets` | `repo` | read |
| List repository secrets | `GET /repos/{owner}/{repo}/actions/secrets` | `repo` | read |
| Get a repository public key | `GET /repos/{owner}/{repo}/actions/secrets/public-key` | `repo` | read |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/actions/secrets/{secret_name}` | `repo` | 3 |
| Get a repository secret | `GET /repos/{owner}/{repo}/actions/secrets/{secret_name}` | `repo` | read |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/actions/secrets/{secret_name}` | `repo` | 2 |
| List environment secrets | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets` | `repo` | read |
| Get an environment public key | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/public-key` | `repo` | read |
| Delete an environment secret | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | `repo` | 3 |
| Get an environment secret | `GET /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | `repo` | read |
| Create or update an environment secret | `PUT /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` | `repo` | 2 |

#### actions / self-hosted-runner-groups (14)

Home: Runner group sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List self-hosted runner groups for an organization | `GET /orgs/{org}/actions/runner-groups` | `admin:org` | read |
| Create a self-hosted runner group for an organization | `POST /orgs/{org}/actions/runner-groups` | `admin:org` | 2 |
| Delete a self-hosted runner group from an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}` | `admin:org` | 3 |
| Get a self-hosted runner group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}` | `admin:org` | read |
| Update a self-hosted runner group for an organization | `PATCH /orgs/{org}/actions/runner-groups/{runner_group_id}` | `admin:org` | 2 |
| List GitHub-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/hosted-runners` | `admin:org` | read |
| List repository access to a self-hosted runner group in an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | `admin:org` | read |
| Set repository access for a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories` | `admin:org` | 2 |
| Remove repository access to a self-hosted runner group in an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | `admin:org` | 3 |
| Add repository access to a self-hosted runner group in an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | `admin:org` | 2 |
| List self-hosted runners in a group for an organization | `GET /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | `admin:org` | read |
| Set self-hosted runners in a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners` | `admin:org` | 2 |
| Remove a self-hosted runner from a group for an organization | `DELETE /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | `admin:org` | 3 |
| Add a self-hosted runner to a group for an organization | `PUT /orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}` | `admin:org` | 2 |

#### actions / self-hosted-runners (26)

Home: Runner sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List self-hosted runners for an organization | `GET /orgs/{org}/actions/runners` | `admin:org` | read |
| Get runner version end-of-life schedule for an organization | `GET /orgs/{org}/actions/runners/deprecations/{version}` | `admin:org` | read |
| List runner applications for an organization | `GET /orgs/{org}/actions/runners/downloads` | `admin:org` | read |
| Create configuration for a just-in-time runner for an organization | `POST /orgs/{org}/actions/runners/generate-jitconfig` | `repo` | 2 |
| Create a registration token for an organization | `POST /orgs/{org}/actions/runners/registration-token` | `repo` | 2 |
| Create a remove token for an organization | `POST /orgs/{org}/actions/runners/remove-token` | `repo` | 2 |
| Delete a self-hosted runner from an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}` | `repo` | 3 |
| Get a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}` | `admin:org` | read |
| Remove all custom labels from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels` | `admin:org` | 3 |
| List labels for a self-hosted runner for an organization | `GET /orgs/{org}/actions/runners/{runner_id}/labels` | `admin:org` | read |
| Add custom labels to a self-hosted runner for an organization | `POST /orgs/{org}/actions/runners/{runner_id}/labels` | `admin:org` | 2 |
| Set custom labels for a self-hosted runner for an organization | `PUT /orgs/{org}/actions/runners/{runner_id}/labels` | `admin:org` | 2 |
| Remove a custom label from a self-hosted runner for an organization | `DELETE /orgs/{org}/actions/runners/{runner_id}/labels/{name}` | `admin:org` | 3 |
| List self-hosted runners for a repository | `GET /repos/{owner}/{repo}/actions/runners` | `repo` | read |
| Get runner version end-of-life schedule for a repository | `GET /repos/{owner}/{repo}/actions/runners/deprecations/{version}` | `repo` | read |
| List runner applications for a repository | `GET /repos/{owner}/{repo}/actions/runners/downloads` | `repo` | read |
| Create configuration for a just-in-time runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig` | - | 2 |
| Create a registration token for a repository | `POST /repos/{owner}/{repo}/actions/runners/registration-token` | `repo` | 2 |
| Create a remove token for a repository | `POST /repos/{owner}/{repo}/actions/runners/remove-token` | `repo` | 2 |
| Delete a self-hosted runner from a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}` | `repo` | 3 |
| Get a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}` | `repo` | read |
| Remove all custom labels from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | `repo` | 3 |
| List labels for a self-hosted runner for a repository | `GET /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | `repo` | read |
| Add custom labels to a self-hosted runner for a repository | `POST /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | `repo` | 2 |
| Set custom labels for a self-hosted runner for a repository | `PUT /repos/{owner}/{repo}/actions/runners/{runner_id}/labels` | `repo` | 2 |
| Remove a custom label from a self-hosted runner for a repository | `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}/labels/{name}` | `repo` | 3 |

#### actions / variables (20)

Home: Secret and variable sheets.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization variables | `GET /orgs/{org}/actions/variables` | `admin:org` | read |
| Create an organization variable | `POST /orgs/{org}/actions/variables` | `repo` | 2 |
| Delete an organization variable | `DELETE /orgs/{org}/actions/variables/{name}` | `repo` | 3 |
| Get an organization variable | `GET /orgs/{org}/actions/variables/{name}` | `repo` | read |
| Update an organization variable | `PATCH /orgs/{org}/actions/variables/{name}` | `admin:org` | 2 |
| List selected repositories for an organization variable | `GET /orgs/{org}/actions/variables/{name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories` | `admin:org` | 2 |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization variable | `PUT /orgs/{org}/actions/variables/{name}/repositories/{repository_id}` | `admin:org`, `repo` | 2 |
| List repository organization variables | `GET /repos/{owner}/{repo}/actions/organization-variables` | `repo` | read |
| List repository variables | `GET /repos/{owner}/{repo}/actions/variables` | `repo` | read |
| Create a repository variable | `POST /repos/{owner}/{repo}/actions/variables` | `repo` | 2 |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/actions/variables/{name}` | `repo` | 3 |
| Get a repository variable | `GET /repos/{owner}/{repo}/actions/variables/{name}` | `repo` | read |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/actions/variables/{name}` | `repo` | 2 |
| List environment variables | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables` | `repo` | read |
| Create an environment variable | `POST /repos/{owner}/{repo}/environments/{environment_name}/variables` | `repo` | 2 |
| Delete an environment variable | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | `repo` | 3 |
| Get an environment variable | `GET /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | `repo` | read |
| Update an environment variable | `PATCH /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` | `repo` | 2 |

#### actions / workflow-jobs (5)

Home: Job sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get a job for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}` | `repo` | read |
| Download job logs for a workflow run | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` | `repo` | read |
| Download step logs for a workflow run job | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/steps/{step_number}/logs` | `repo` | read |
| List jobs for a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs` | `repo` | read |
| List jobs for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` | `repo` | read |

#### actions / workflow-runs (19)

Home: Run sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Re-run a job from a workflow run | `POST /repos/{owner}/{repo}/actions/jobs/{job_id}/rerun` | `repo` | 1 |
| List workflow runs for a repository | `GET /repos/{owner}/{repo}/actions/runs` | `repo` | read |
| Delete a workflow run | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}` | `repo` | 3 |
| Get a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}` | `repo` | read |
| Get the review history for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/approvals` | `repo` | read |
| Approve a workflow run for a fork pull request | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve` | `repo` | 1 |
| Get a workflow run attempt | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}` | `repo` | read |
| Download workflow run attempt logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/logs` | `repo` | read |
| Cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/cancel` | `repo` | 1 |
| Review custom deployment protection rules for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/deployment_protection_rule` | `repo` | 1 |
| Force cancel a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/force-cancel` | `repo` | 1 |
| Delete workflow run logs | `DELETE /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | `repo` | 3 |
| Download workflow run logs | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` | `repo` | read |
| Get pending deployments for a workflow run | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | `repo` | read |
| Review pending deployments for a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments` | `repo` | 1 |
| Re-run a workflow | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun` | `repo` | 1 |
| Re-run failed jobs from a workflow run | `POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs` | `repo` | 1 |
| Get workflow run usage | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/timing` | `repo` | read |
| List workflow runs for a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs` | `repo` | read |

#### actions / workflows (6)

Home: Workflow sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository workflows | `GET /repos/{owner}/{repo}/actions/workflows` | `repo` | read |
| Get a workflow | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}` | `repo` | read |
| Disable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/disable` | `repo` | 1 |
| Create a workflow dispatch event | `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | `repo` | 1 |
| Enable a workflow | `PUT /repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable` | `repo` | 1 |
| Get workflow usage | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing` | `repo` | read |

### REST: activity (34 operations)

Home: Needs My Attention (Notifications, Activity Feed); Repository > You (star, watch); Person > Activity. Coverage: in scope.

#### activity / events (9)

Home: Needs My Attention > My Activity Feed; Repository > Activity; Person > Activity.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List public events | `GET /events` | - | read |
| List public events for a network of repositories | `GET /networks/{owner}/{repo}/events` | - | read |
| List public organization events | `GET /orgs/{org}/events` | - | read |
| List repository events | `GET /repos/{owner}/{repo}/events` | - | read |
| List events for the authenticated user | `GET /users/{username}/events` | - | read |
| List organization events for the authenticated user | `GET /users/{username}/events/orgs/{org}` | - | read |
| List public events for a user | `GET /users/{username}/events/public` | - | read |
| List events received by the authenticated user | `GET /users/{username}/received_events` | - | read |
| List public events received by a user | `GET /users/{username}/received_events/public` | - | read |

#### activity / feeds (1)

Home: Needs My Attention > My Activity Feed.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get feeds | `GET /feeds` | - | read |

#### activity / notifications (10)

Home: Needs My Attention > Notifications; Notification sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List notifications for the authenticated user | `GET /notifications` | - | read |
| Mark notifications as read | `PUT /notifications` | - | 1 |
| Mark a thread as done | `DELETE /notifications/threads/{thread_id}` | - | 3 |
| Get a thread | `GET /notifications/threads/{thread_id}` | - | read |
| Mark a thread as read | `PATCH /notifications/threads/{thread_id}` | - | 1 |
| Delete a thread subscription | `DELETE /notifications/threads/{thread_id}/subscription` | - | 3 |
| Get a thread subscription for the authenticated user | `GET /notifications/threads/{thread_id}/subscription` | - | read |
| Set a thread subscription | `PUT /notifications/threads/{thread_id}/subscription` | - | 1 |
| List repository notifications for the authenticated user | `GET /repos/{owner}/{repo}/notifications` | - | read |
| Mark repository notifications as read | `PUT /repos/{owner}/{repo}/notifications` | - | 1 |

#### activity / starring (8)

Home: You page: Star (section 16.7).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List stargazers | `GET /repos/{owner}/{repo}/stargazers` | - | read |
| Get stargazer count | `GET /repos/{owner}/{repo}/stargazers/count` | - | read |
| Get repository star history | `GET /repos/{owner}/{repo}/stargazers/history` | - | read |
| List repositories starred by the authenticated user | `GET /user/starred` | - | read |
| Unstar a repository for the authenticated user | `DELETE /user/starred/{owner}/{repo}` | - | 3 |
| Check if a repository is starred by the authenticated user | `GET /user/starred/{owner}/{repo}` | - | read |
| Star a repository for the authenticated user | `PUT /user/starred/{owner}/{repo}` | - | 1 |
| List repositories starred by a user | `GET /users/{username}/starred` | - | read |

#### activity / watching (6)

Home: You page: Watch level (section 16.7).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List watchers | `GET /repos/{owner}/{repo}/subscribers` | - | read |
| Delete a repository subscription | `DELETE /repos/{owner}/{repo}/subscription` | - | 3 |
| Get a repository subscription | `GET /repos/{owner}/{repo}/subscription` | - | read |
| Set a repository subscription | `PUT /repos/{owner}/{repo}/subscription` | - | 1 |
| List repositories watched by the authenticated user | `GET /user/subscriptions` | - | read |
| List repositories watched by a user | `GET /users/{username}/subscriptions` | - | read |

### REST: agent-automations (12 operations)

Home: Item > Copilot; Repository > Copilot (section 22.1). Coverage: in scope.

#### agent-automations / agent-automations (12)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List automations for user | `GET /agents/automations` | `repo` | read |
| List automations for a repository | `GET /agents/repos/{owner}/{repo}/automations` | `repo` | read |
| Create an automation for a repository | `POST /agents/repos/{owner}/{repo}/automations` | `repo` | 1 |
| List available automation tools for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-tools` | `repo` | read |
| List available automation triggers for a repository | `GET /agents/repos/{owner}/{repo}/automations/available-triggers` | `repo` | read |
| Delete an automation | `DELETE /agents/repos/{owner}/{repo}/automations/{automation_id}` | `repo` | 3 |
| Get an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}` | `repo` | read |
| Update an automation | `PATCH /agents/repos/{owner}/{repo}/automations/{automation_id}` | `repo` | 1 |
| List revisions for an automation | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions` | - | read |
| Get an automation revision | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/revisions/{revision_id}` | - | read |
| List tasks for an automation in a repository | `GET /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | - | read |
| Run an automation | `POST /agents/repos/{owner}/{repo}/automations/{automation_id}/tasks` | `repo` | 1 |

### REST: agent-tasks (5 operations)

Home: Item > Copilot > Agent Sessions (section 22.1). Coverage: in scope.

#### agent-tasks / agent-tasks (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List tasks for repository | `GET /agents/repos/{owner}/{repo}/tasks` | - | read |
| Start a task | `POST /agents/repos/{owner}/{repo}/tasks` | - | 1 |
| Get a task by repo | `GET /agents/repos/{owner}/{repo}/tasks/{task_id}` | - | read |
| List tasks | `GET /agents/tasks` | - | read |
| Get a task by ID | `GET /agents/tasks/{task_id}` | - | read |

### REST: agents (30 operations)

Home: Item > Copilot; Repository > Copilot; Organization > Copilot (section 22.1). Coverage: in scope.

#### agents / secrets (15)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization secrets | `GET /orgs/{org}/agents/secrets` | `admin:org` | read |
| Get an organization public key | `GET /orgs/{org}/agents/secrets/public-key` | `admin:org` | read |
| Delete an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}` | `admin:org`, `repo` | 3 |
| Get an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}` | `admin:org`, `repo` | read |
| Create or update an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}` | `admin:org`, `repo` | 2 |
| List selected repositories for an organization secret | `GET /orgs/{org}/agents/secrets/{secret_name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories` | `admin:org` | 2 |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization secret | `PUT /orgs/{org}/agents/secrets/{secret_name}/repositories/{repository_id}` | `admin:org`, `repo` | 2 |
| List repository organization secrets | `GET /repos/{owner}/{repo}/agents/organization-secrets` | `repo` | read |
| List repository secrets | `GET /repos/{owner}/{repo}/agents/secrets` | `repo` | read |
| Get a repository public key | `GET /repos/{owner}/{repo}/agents/secrets/public-key` | `repo` | read |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/agents/secrets/{secret_name}` | `repo` | 3 |
| Get a repository secret | `GET /repos/{owner}/{repo}/agents/secrets/{secret_name}` | `repo` | read |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/agents/secrets/{secret_name}` | `repo` | 2 |

#### agents / variables (15)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization variables | `GET /orgs/{org}/agents/variables` | `admin:org` | read |
| Create an organization variable | `POST /orgs/{org}/agents/variables` | `admin:org`, `repo` | 2 |
| Delete an organization variable | `DELETE /orgs/{org}/agents/variables/{name}` | `admin:org`, `repo` | 3 |
| Get an organization variable | `GET /orgs/{org}/agents/variables/{name}` | `admin:org`, `repo` | read |
| Update an organization variable | `PATCH /orgs/{org}/agents/variables/{name}` | `admin:org` | 2 |
| List selected repositories for an organization variable | `GET /orgs/{org}/agents/variables/{name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories` | `admin:org` | 2 |
| Remove selected repository from an organization variable | `DELETE /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization variable | `PUT /orgs/{org}/agents/variables/{name}/repositories/{repository_id}` | `admin:org`, `repo` | 2 |
| List repository organization variables | `GET /repos/{owner}/{repo}/agents/organization-variables` | `repo` | read |
| List repository variables | `GET /repos/{owner}/{repo}/agents/variables` | `repo` | read |
| Create a repository variable | `POST /repos/{owner}/{repo}/agents/variables` | `repo` | 2 |
| Delete a repository variable | `DELETE /repos/{owner}/{repo}/agents/variables/{name}` | `repo` | 3 |
| Get a repository variable | `GET /repos/{owner}/{repo}/agents/variables/{name}` | `repo` | read |
| Update a repository variable | `PATCH /repos/{owner}/{repo}/agents/variables/{name}` | `repo` | 2 |

### REST: apps (37 operations)

Home: Organization and Repository sheets > Apps (installations, repository access); most app-JWT calls are out of scope. Coverage: in scope.

#### apps / apps (14)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the authenticated app | `GET /app` | - | read |
| Create a GitHub App from a manifest | `POST /app-manifests/{code}/conversions` | - | 1 |
| List installation requests for the authenticated app | `GET /app/installation-requests` | - | read |
| List installations for the authenticated app | `GET /app/installations` | - | read |
| Delete an installation for the authenticated app | `DELETE /app/installations/{installation_id}` | - | 3 |
| Get an installation for the authenticated app | `GET /app/installations/{installation_id}` | - | read |
| Create an installation access token for an app | `POST /app/installations/{installation_id}/access_tokens` | - | 1 |
| Unsuspend an app installation | `DELETE /app/installations/{installation_id}/suspended` | - | 3 |
| Suspend an app installation | `PUT /app/installations/{installation_id}/suspended` | - | 1 |
| Create a scoped access token | `POST /applications/{client_id}/token/scoped` | - | 1 |
| Get an app | `GET /apps/{app_slug}` | - | read |
| Get an organization installation for the authenticated app | `GET /orgs/{org}/installation` | - | read |
| Get a repository installation for the authenticated app | `GET /repos/{owner}/{repo}/installation` | - | read |
| Get a user installation for the authenticated app | `GET /users/{username}/installation` | - | read |

#### apps / installations (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repositories accessible to the app installation | `GET /installation/repositories` | - | read |
| Revoke an installation access token | `DELETE /installation/token` | - | 3 |
| List app installations accessible to the user access token | `GET /user/installations` | - | read |
| List repositories accessible to the user access token | `GET /user/installations/{installation_id}/repositories` | - | read |
| Remove a repository from an app installation | `DELETE /user/installations/{installation_id}/repositories/{repository_id}` | - | 3 |
| Add a repository to an app installation | `PUT /user/installations/{installation_id}/repositories/{repository_id}` | - | 1 |

#### apps / marketplace (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get a subscription plan for an account | `GET /marketplace_listing/accounts/{account_id}` | - | read |
| List plans | `GET /marketplace_listing/plans` | - | read |
| List accounts for a plan | `GET /marketplace_listing/plans/{plan_id}/accounts` | - | read |
| Get a subscription plan for an account (stubbed) | `GET /marketplace_listing/stubbed/accounts/{account_id}` | - | read |
| List plans (stubbed) | `GET /marketplace_listing/stubbed/plans` | - | read |
| List accounts for a plan (stubbed) | `GET /marketplace_listing/stubbed/plans/{plan_id}/accounts` | - | read |
| List subscriptions for the authenticated user | `GET /user/marketplace_purchases` | - | read |
| List subscriptions for the authenticated user (stubbed) | `GET /user/marketplace_purchases/stubbed` | - | read |

#### apps / oauth-applications (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete an app authorization | `DELETE /applications/{client_id}/grant` | - | 3 |
| Delete an app token | `DELETE /applications/{client_id}/token` | - | 3 |
| Reset a token | `PATCH /applications/{client_id}/token` | - | 1 |
| Check a token | `POST /applications/{client_id}/token` | - | 1 |

#### apps / webhooks (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get a webhook configuration for an app | `GET /app/hook/config` | - | read |
| Update a webhook configuration for an app | `PATCH /app/hook/config` | - | 2 |
| List deliveries for an app webhook | `GET /app/hook/deliveries` | - | read |
| Get a delivery for an app webhook | `GET /app/hook/deliveries/{delivery_id}` | - | read |
| Redeliver a delivery for an app webhook | `POST /app/hook/deliveries/{delivery_id}/attempts` | - | 2 |

### REST: billing (13 operations)

Home: Account > Billing and Usage; Organization sheet > Billing (read-only). Coverage: in scope.

#### billing / budgets (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all budgets for an organization | `GET /organizations/{org}/settings/billing/budgets` | - | read |
| Create a budget for an organization | `POST /organizations/{org}/settings/billing/budgets` | - | 1 |
| Delete a budget for an organization | `DELETE /organizations/{org}/settings/billing/budgets/{budget_id}` | - | 3 |
| Get a budget by ID for an organization | `GET /organizations/{org}/settings/billing/budgets/{budget_id}` | - | read |
| Update a budget for an organization | `PATCH /organizations/{org}/settings/billing/budgets/{budget_id}` | - | 1 |

#### billing / usage (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get billing AI credit usage report for an organization | `GET /organizations/{org}/settings/billing/ai_credit/usage` | - | read |
| Get billing premium request usage report for an organization | `GET /organizations/{org}/settings/billing/premium_request/usage` | - | read |
| Get billing usage report for an organization | `GET /organizations/{org}/settings/billing/usage` | - | read |
| Get billing usage summary for an organization | `GET /organizations/{org}/settings/billing/usage/summary` | - | read |
| Get billing AI credit usage report for a user | `GET /users/{username}/settings/billing/ai_credit/usage` | - | read |
| Get billing premium request usage report for a user | `GET /users/{username}/settings/billing/premium_request/usage` | - | read |
| Get billing usage report for a user | `GET /users/{username}/settings/billing/usage` | - | read |
| Get billing usage summary for a user | `GET /users/{username}/settings/billing/usage/summary` | - | read |

### REST: branches (38 operations)

Home: Branch sheet; Branch sheet > Protection; Ruleset sheet (section 18.3.1). Coverage: in scope.

#### branches / branch-protection (33)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection` | - | 3 |
| Get branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection` | - | read |
| Update branch protection | `PUT /repos/{owner}/{repo}/branches/{branch}/protection` | - | 2 |
| Delete admin branch protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | - | 3 |
| Get admin branch protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | - | read |
| Set admin branch protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/enforce_admins` | - | 2 |
| Delete pull request review protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | - | 3 |
| Get pull request review protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | - | read |
| Update pull request review protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_pull_request_reviews` | - | 2 |
| Delete commit signature protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | - | 3 |
| Get commit signature protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | - | read |
| Create commit signature protection | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_signatures` | - | 2 |
| Remove status check protection | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | - | 3 |
| Get status checks protection | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | - | read |
| Update status check protection | `PATCH /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks` | - | 2 |
| Remove status check contexts | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | - | 3 |
| Get all status check contexts | `GET /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | - | read |
| Add status check contexts | `POST /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | - | 2 |
| Set status check contexts | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts` | - | 2 |
| Delete access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | - | 3 |
| Get access restrictions | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions` | - | read |
| Remove app access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | - | 3 |
| Get apps with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | - | read |
| Add app access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | - | 2 |
| Set app access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/apps` | - | 2 |
| Remove team access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | - | 3 |
| Get teams with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | - | read |
| Add team access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | - | 2 |
| Set team access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/teams` | - | 2 |
| Remove user access restrictions | `DELETE /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | - | 3 |
| Get users with access to the protected branch | `GET /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | - | read |
| Add user access restrictions | `POST /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | - | 2 |
| Set user access restrictions | `PUT /repos/{owner}/{repo}/branches/{branch}/protection/restrictions/users` | - | 2 |

#### branches / branches (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List branches | `GET /repos/{owner}/{repo}/branches` | - | read |
| Get a branch | `GET /repos/{owner}/{repo}/branches/{branch}` | - | read |
| Rename a branch | `POST /repos/{owner}/{repo}/branches/{branch}/rename` | - | 1 |
| Sync a fork branch with the upstream repository | `POST /repos/{owner}/{repo}/merge-upstream` | - | 1 |
| Merge a branch | `POST /repos/{owner}/{repo}/merges` | - | 1 |

### REST: campaigns (5 operations)

Home: Organization > Security > Campaigns (security campaigns). Coverage: in scope.

#### campaigns / campaigns (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List campaigns for an organization | `GET /orgs/{org}/campaigns` | `security_events` | read |
| Create a campaign for an organization | `POST /orgs/{org}/campaigns` | `security_events` | 1 |
| Delete a campaign for an organization | `DELETE /orgs/{org}/campaigns/{campaign_number}` | `security_events` | 3 |
| Get a campaign for an organization | `GET /orgs/{org}/campaigns/{campaign_number}` | `security_events` | read |
| Update a campaign | `PATCH /orgs/{org}/campaigns/{campaign_number}` | `security_events` | 1 |

### REST: checks (12 operations)

Home: Pull request > Checks; Commit > Checks; Run sheet. Coverage: in scope.

#### checks / runs (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a check run | `POST /repos/{owner}/{repo}/check-runs` | - | 1 |
| Get a check run | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}` | `repo` | read |
| Update a check run | `PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}` | - | 1 |
| List check run annotations | `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations` | `repo` | read |
| Rerequest a check run | `POST /repos/{owner}/{repo}/check-runs/{check_run_id}/rerequest` | - | 1 |
| List check runs in a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}/check-runs` | `repo` | read |
| List check runs for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-runs` | `repo` | read |

#### checks / suites (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a check suite | `POST /repos/{owner}/{repo}/check-suites` | - | 1 |
| Update repository preferences for check suites | `PATCH /repos/{owner}/{repo}/check-suites/preferences` | - | 1 |
| Get a check suite | `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}` | `repo` | read |
| Rerequest a check suite | `POST /repos/{owner}/{repo}/check-suites/{check_suite_id}/rerequest` | - | 1 |
| List check suites for a Git reference | `GET /repos/{owner}/{repo}/commits/{ref}/check-suites` | `repo` | read |

### REST: classroom (6 operations)

Home: Organizations > org > Classroom (read-only assignments and grades, for teachers). Coverage: in scope.

#### classroom / classroom (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Closed - Get an assignment | `GET /assignments/{assignment_id}` | - | read |
| Closed - List accepted assignments for an assignment | `GET /assignments/{assignment_id}/accepted_assignments` | - | read |
| Closed - Get assignment grades | `GET /assignments/{assignment_id}/grades` | - | read |
| Closed - List classrooms | `GET /classrooms` | - | read |
| Closed - Get a classroom | `GET /classrooms/{classroom_id}` | - | read |
| Closed - List assignments for a classroom | `GET /classrooms/{classroom_id}/assignments` | - | read |

### REST: code-quality (4 operations)

Home: Repository > Security > Code Quality. Coverage: in scope.

#### code-quality / code-quality (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List code quality findings for a repository | `GET /repos/{owner}/{repo}/code-quality/findings` | `repo` | read |
| Get a code quality finding | `GET /repos/{owner}/{repo}/code-quality/findings/{finding_number}` | `repo` | read |
| Get a code quality setup configuration | `GET /repos/{owner}/{repo}/code-quality/setup` | `repo` | read |
| Update a code quality setup configuration | `PATCH /repos/{owner}/{repo}/code-quality/setup` | `repo` | 1 |

### REST: code-scanning (25 operations)

Home: Repository > Security > Alerts (Kind: code scanning); Alert sheet; Repository > Security setup. Coverage: in scope.

#### code-scanning / code-scanning (25)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the AI Scan setting for an organization | `GET /orgs/{org}/code-scanning/ai-scan` | - | read |
| Update the AI Scan setting for an organization | `PATCH /orgs/{org}/code-scanning/ai-scan` | - | 1 |
| List code scanning alerts for an organization | `GET /orgs/{org}/code-scanning/alerts` | - | read |
| Get AI Scan enablement for a repository | `GET /repos/{owner}/{repo}/code-scanning/ai-scan` | `security_events` | read |
| Update AI Scan enablement for a repository | `PATCH /repos/{owner}/{repo}/code-scanning/ai-scan` | `repo` | 1 |
| List code scanning alerts for a repository | `GET /repos/{owner}/{repo}/code-scanning/alerts` | `security_events` | read |
| Get a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | `security_events` | read |
| Update a code scanning alert | `PATCH /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}` | `security_events` | 1 |
| Get the status of an autofix for a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | `security_events` | read |
| Create an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix` | `security_events` | 1 |
| Commit an autofix for a code scanning alert | `POST /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/autofix/commits` | `repo` | 1 |
| List instances of a code scanning alert | `GET /repos/{owner}/{repo}/code-scanning/alerts/{alert_number}/instances` | `security_events` | read |
| List code scanning analyses for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses` | `security_events` | read |
| Delete a code scanning analysis from a repository | `DELETE /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | `repo` | 3 |
| Get a code scanning analysis for a repository | `GET /repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}` | `security_events` | read |
| List CodeQL databases for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases` | `repo` | read |
| Delete a CodeQL database | `DELETE /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | `repo` | 3 |
| Get a CodeQL database for a repository | `GET /repos/{owner}/{repo}/code-scanning/codeql/databases/{language}` | `repo` | read |
| Create a CodeQL variant analysis | `POST /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses` | `repo` | 1 |
| Get the summary of a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}` | `security_events` | read |
| Get the analysis status of a repository in a CodeQL variant analysis | `GET /repos/{owner}/{repo}/code-scanning/codeql/variant-analyses/{codeql_variant_analysis_id}/repos/{repo_owner}/{repo_name}` | `security_events` | read |
| Get a code scanning default setup configuration | `GET /repos/{owner}/{repo}/code-scanning/default-setup` | `repo` | read |
| Update a code scanning default setup configuration | `PATCH /repos/{owner}/{repo}/code-scanning/default-setup` | `repo` | 1 |
| Upload an analysis as SARIF data | `POST /repos/{owner}/{repo}/code-scanning/sarifs` | `security_events` | 1 |
| Get information about a SARIF upload | `GET /repos/{owner}/{repo}/code-scanning/sarifs/{sarif_id}` | `security_events` | read |

### REST: code-security (20 operations)

Home: Organization > Security > Configurations; Repository > Security. Coverage: in scope.

#### code-security / configurations (20)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get code security configurations for an enterprise | `GET /enterprises/{enterprise}/code-security/configurations` | `read:enterprise` | read |
| Create a code security configuration for an enterprise | `POST /enterprises/{enterprise}/code-security/configurations` | `admin:enterprise` | 1 |
| Get default code security configurations for an enterprise | `GET /enterprises/{enterprise}/code-security/configurations/defaults` | `read:enterprise` | read |
| Delete a code security configuration for an enterprise | `DELETE /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | `admin:enterprise` | 3 |
| Retrieve a code security configuration of an enterprise | `GET /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | `read:enterprise` | read |
| Update a custom code security configuration for an enterprise | `PATCH /enterprises/{enterprise}/code-security/configurations/{configuration_id}` | `admin:enterprise` | 1 |
| Attach an enterprise configuration to repositories | `POST /enterprises/{enterprise}/code-security/configurations/{configuration_id}/attach` | `admin:enterprise` | 1 |
| Set a code security configuration as a default for an enterprise | `PUT /enterprises/{enterprise}/code-security/configurations/{configuration_id}/defaults` | `admin:enterprise` | 1 |
| Get repositories associated with an enterprise code security configuration | `GET /enterprises/{enterprise}/code-security/configurations/{configuration_id}/repositories` | `read:enterprise` | read |
| Get code security configurations for an organization | `GET /orgs/{org}/code-security/configurations` | `read:org` | read |
| Create a code security configuration | `POST /orgs/{org}/code-security/configurations` | `write:org` | 1 |
| Get default code security configurations | `GET /orgs/{org}/code-security/configurations/defaults` | `read:org` | read |
| Detach configurations from repositories | `DELETE /orgs/{org}/code-security/configurations/detach` | - | 3 |
| Delete a code security configuration | `DELETE /orgs/{org}/code-security/configurations/{configuration_id}` | `write:org` | 3 |
| Get a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}` | `write:org` | read |
| Update a code security configuration | `PATCH /orgs/{org}/code-security/configurations/{configuration_id}` | `write:org` | 1 |
| Attach a configuration to repositories | `POST /orgs/{org}/code-security/configurations/{configuration_id}/attach` | - | 1 |
| Set a code security configuration as a default for an organization | `PUT /orgs/{org}/code-security/configurations/{configuration_id}/defaults` | - | 1 |
| Get repositories associated with a code security configuration | `GET /orgs/{org}/code-security/configurations/{configuration_id}/repositories` | `read:org` | read |
| Get the code security configuration associated with a repository | `GET /repos/{owner}/{repo}/code-security-configuration` | `repo` | read |

### REST: codes-of-conduct (2 operations)

Home: Repository > Templates > Community Files (Create from starter). Coverage: in scope.

#### codes-of-conduct / codes-of-conduct (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all codes of conduct | `GET /codes_of_conduct` | - | read |
| Get a code of conduct | `GET /codes_of_conduct/{key}` | - | read |

### REST: codespaces (48 operations)

Home: Repository > Codespaces; Codespace sheet; Organization > Codespaces; Secrets. Coverage: in scope.

#### codespaces / codespaces (16)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List codespaces in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces` | `codespace` | read |
| Create a codespace in a repository | `POST /repos/{owner}/{repo}/codespaces` | `codespace` | 1 |
| List devcontainer configurations in a repository for the authenticated user | `GET /repos/{owner}/{repo}/codespaces/devcontainers` | `codespace` | read |
| Get default attributes for a codespace | `GET /repos/{owner}/{repo}/codespaces/new` | `codespace` | read |
| Check if permissions defined by a devcontainer have been accepted by the authenticated user | `GET /repos/{owner}/{repo}/codespaces/permissions_check` | `codespace` | read |
| Create a codespace from a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/codespaces` | `codespace` | 1 |
| List codespaces for the authenticated user | `GET /user/codespaces` | `codespace` | read |
| Create a codespace for the authenticated user | `POST /user/codespaces` | `codespace` | 1 |
| Delete a codespace for the authenticated user | `DELETE /user/codespaces/{codespace_name}` | `codespace` | 3 |
| Get a codespace for the authenticated user | `GET /user/codespaces/{codespace_name}` | `codespace` | read |
| Update a codespace for the authenticated user | `PATCH /user/codespaces/{codespace_name}` | `codespace` | 1 |
| Export a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/exports` | `codespace` | 1 |
| Get details about a codespace export | `GET /user/codespaces/{codespace_name}/exports/{export_id}` | `codespace` | read |
| Create a repository from an unpublished codespace | `POST /user/codespaces/{codespace_name}/publish` | `codespace` | 1 |
| Start a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/start` | `codespace` | 1 |
| Stop a codespace for the authenticated user | `POST /user/codespaces/{codespace_name}/stop` | `codespace` | 1 |

#### codespaces / machines (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List available machine types for a repository | `GET /repos/{owner}/{repo}/codespaces/machines` | `codespace` | read |
| List machine types for a codespace | `GET /user/codespaces/{codespace_name}/machines` | `codespace` | read |

#### codespaces / organization-secrets (9)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization secrets | `GET /orgs/{org}/codespaces/secrets` | `admin:org` | read |
| Get an organization public key | `GET /orgs/{org}/codespaces/secrets/public-key` | `admin:org` | read |
| Delete an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}` | `admin:org` | 3 |
| Get an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}` | `admin:org` | read |
| Create or update an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}` | `admin:org` | 1 |
| List selected repositories for an organization secret | `GET /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories` | `admin:org` | 1 |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization secret | `PUT /orgs/{org}/codespaces/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 1 |

#### codespaces / organizations (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List codespaces for the organization | `GET /orgs/{org}/codespaces` | `admin:org` | read |
| Manage access control for organization codespaces | `PUT /orgs/{org}/codespaces/access` | `admin:org` | 1 |
| Remove users from Codespaces access for an organization | `DELETE /orgs/{org}/codespaces/access/selected_users` | `admin:org` | 3 |
| Add users to Codespaces access for an organization | `POST /orgs/{org}/codespaces/access/selected_users` | `admin:org` | 1 |
| List codespaces for a user in organization | `GET /orgs/{org}/members/{username}/codespaces` | `admin:org` | read |
| Delete a codespace from the organization | `DELETE /orgs/{org}/members/{username}/codespaces/{codespace_name}` | `admin:org` | 3 |
| Stop a codespace for an organization user | `POST /orgs/{org}/members/{username}/codespaces/{codespace_name}/stop` | `admin:org` | 1 |

#### codespaces / repository-secrets (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository secrets | `GET /repos/{owner}/{repo}/codespaces/secrets` | `repo` | read |
| Get a repository public key | `GET /repos/{owner}/{repo}/codespaces/secrets/public-key` | `repo` | read |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | `repo` | 3 |
| Get a repository secret | `GET /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | `repo` | read |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/codespaces/secrets/{secret_name}` | `repo` | 1 |

#### codespaces / secrets (9)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List secrets for the authenticated user | `GET /user/codespaces/secrets` | `codespace`, `codespace:secrets` | read |
| Get public key for the authenticated user | `GET /user/codespaces/secrets/public-key` | `codespace`, `codespace:secrets` | read |
| Delete a secret for the authenticated user | `DELETE /user/codespaces/secrets/{secret_name}` | `codespace`, `codespace:secrets` | 3 |
| Get a secret for the authenticated user | `GET /user/codespaces/secrets/{secret_name}` | `codespace`, `codespace:secrets` | read |
| Create or update a secret for the authenticated user | `PUT /user/codespaces/secrets/{secret_name}` | `codespace`, `codespace:secrets` | 2 |
| List selected repositories for a user secret | `GET /user/codespaces/secrets/{secret_name}/repositories` | `codespace`, `codespace:secrets` | read |
| Set selected repositories for a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories` | `codespace`, `codespace:secrets` | 2 |
| Remove a selected repository from a user secret | `DELETE /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | `codespace`, `codespace:secrets` | 3 |
| Add a selected repository to a user secret | `PUT /user/codespaces/secrets/{secret_name}/repositories/{repository_id}` | `codespace`, `codespace:secrets` | 2 |

### REST: collaborators (11 operations)

Home: Repository sheet > Access (section 18.3). Coverage: in scope.

#### collaborators / collaborators (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository collaborators | `GET /repos/{owner}/{repo}/collaborators` | - | read |
| Remove a repository collaborator | `DELETE /repos/{owner}/{repo}/collaborators/{username}` | - | 3 |
| Check if a user is a repository collaborator | `GET /repos/{owner}/{repo}/collaborators/{username}` | - | read |
| Add a repository collaborator | `PUT /repos/{owner}/{repo}/collaborators/{username}` | - | 2 |
| Get repository permissions for a user | `GET /repos/{owner}/{repo}/collaborators/{username}/permission` | - | read |

#### collaborators / invitations (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository invitations | `GET /repos/{owner}/{repo}/invitations` | - | read |
| Delete a repository invitation | `DELETE /repos/{owner}/{repo}/invitations/{invitation_id}` | - | 3 |
| Update a repository invitation | `PATCH /repos/{owner}/{repo}/invitations/{invitation_id}` | - | 2 |
| List repository invitations for the authenticated user | `GET /user/repository_invitations` | - | read |
| Decline a repository invitation | `DELETE /user/repository_invitations/{invitation_id}` | - | 3 |
| Accept a repository invitation | `PATCH /user/repository_invitations/{invitation_id}` | - | 2 |

### REST: commits (14 operations)

Home: Commit sheet; Repository > Code > Commits; Commit comments. Coverage: in scope.

#### commits / comments (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List commit comments for a repository | `GET /repos/{owner}/{repo}/comments` | - | read |
| Delete a commit comment | `DELETE /repos/{owner}/{repo}/comments/{comment_id}` | - | 3 |
| Get a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}` | - | read |
| Update a commit comment | `PATCH /repos/{owner}/{repo}/comments/{comment_id}` | - | 1 |
| List commit comments | `GET /repos/{owner}/{repo}/commits/{commit_sha}/comments` | - | read |
| Create a commit comment | `POST /repos/{owner}/{repo}/commits/{commit_sha}/comments` | - | 1 |

#### commits / commits (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List commits | `GET /repos/{owner}/{repo}/commits` | - | read |
| List branches for HEAD commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/branches-where-head` | - | read |
| List pull requests associated with a commit | `GET /repos/{owner}/{repo}/commits/{commit_sha}/pulls` | - | read |
| Get a commit | `GET /repos/{owner}/{repo}/commits/{ref}` | - | read |
| Compare two commits | `GET /repos/{owner}/{repo}/compare/{basehead}` | - | read |

#### commits / statuses (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the combined status for a specific reference | `GET /repos/{owner}/{repo}/commits/{ref}/status` | - | read |
| List commit statuses for a reference | `GET /repos/{owner}/{repo}/commits/{ref}/statuses` | - | read |
| Create a commit status | `POST /repos/{owner}/{repo}/statuses/{sha}` | - | 1 |

### REST: copilot (44 operations)

Home: Organization > Copilot (seats, policies, usage); Account > Copilot. Coverage: in scope.

#### copilot / copilot-cloud-agent-management (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get Copilot cloud agent configuration for a repository | `GET /repos/{owner}/{repo}/copilot/cloud-agent/configuration` | `repo` | read |

#### copilot / copilot-code-review (10)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the Copilot code review policy for an enterprise | `GET /enterprises/{enterprise}/copilot/policies/code-review` | `read:enterprise` | read |
| Set the Copilot code review policy for an enterprise | `PUT /enterprises/{enterprise}/copilot/policies/code-review` | `admin:enterprise` | 1 |
| Get the Copilot code review runner configuration for an organization | `GET /orgs/{org}/copilot/code-review/runner` | - | read |
| Set the Copilot code review runner configuration for an organization | `PUT /orgs/{org}/copilot/code-review/runner` | - | 1 |
| Get Copilot code review settings for an organization | `GET /orgs/{org}/copilot/code-review/settings` | - | read |
| Update Copilot code review settings for an organization | `PATCH /orgs/{org}/copilot/code-review/settings` | - | 1 |
| Get the Copilot code review policy for an organization | `GET /orgs/{org}/copilot/policies/code-review` | - | read |
| Set the Copilot code review policy for an organization | `PUT /orgs/{org}/copilot/policies/code-review` | - | 1 |
| Get Copilot code review settings for a repository | `GET /repos/{owner}/{repo}/copilot/code-review/settings` | `repo` | read |
| Update Copilot code review settings for a repository | `PATCH /repos/{owner}/{repo}/copilot/code-review/settings` | `repo` | 1 |

#### copilot / copilot-coding-agent-management (9)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Set the coding agent policy for an enterprise | `PUT /enterprises/{enterprise}/copilot/policies/coding_agent` | - | 1 |
| Remove organizations from the enterprise coding agent policy | `DELETE /enterprises/{enterprise}/copilot/policies/coding_agent/organizations` | - | 3 |
| Add organizations to the enterprise coding agent policy | `POST /enterprises/{enterprise}/copilot/policies/coding_agent/organizations` | - | 1 |
| Get Copilot cloud agent permissions for an organization | `GET /orgs/{org}/copilot/coding-agent/permissions` | `read:org` | read |
| Set Copilot cloud agent permissions for an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions` | `admin:org` | 1 |
| List repositories enabled for Copilot cloud agent in an organization | `GET /orgs/{org}/copilot/coding-agent/permissions/repositories` | `read:org` | read |
| Set selected repositories for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories` | `admin:org` | 1 |
| Disable a repository for Copilot cloud agent in an organization | `DELETE /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | `admin:org` | 3 |
| Enable a repository for Copilot cloud agent in an organization | `PUT /orgs/{org}/copilot/coding-agent/permissions/repositories/{repository_id}` | `admin:org` | 1 |

#### copilot / copilot-content-exclusion-management (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get Copilot content exclusion rules for an organization | `GET /orgs/{org}/copilot/content_exclusion` | - | read |
| Set Copilot content exclusion rules for an organization | `PUT /orgs/{org}/copilot/content_exclusion` | `copilot` | 1 |

#### copilot / copilot-team-customizations (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete Copilot customizations for a team | `DELETE /orgs/{org}/teams/{team_slug}/copilot/customizations` | `admin:org` | 3 |
| Get Copilot customizations for a team | `GET /orgs/{org}/teams/{team_slug}/copilot/customizations` | `admin:org`, `read:org` | read |
| Set Copilot customizations for a team | `PUT /orgs/{org}/teams/{team_slug}/copilot/customizations` | `admin:org` | 1 |

#### copilot / copilot-usage-metrics (12)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get Copilot enterprise usage metrics for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-1-day` | - | read |
| Get Copilot enterprise usage metrics | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-28-day/latest` | - | read |
| Get Copilot enterprise repository report for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/repos-1-day` | - | read |
| Get Copilot enterprise user-teams report for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/user-teams-1-day` | - | read |
| Get Copilot users usage metrics for a specific day | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-1-day` | - | read |
| Get Copilot users usage metrics | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-28-day/latest` | - | read |
| Get Copilot organization usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/organization-1-day` | `read:org` | read |
| Get Copilot organization usage metrics | `GET /orgs/{org}/copilot/metrics/reports/organization-28-day/latest` | `read:org` | read |
| Get Copilot organization repository report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/repos-1-day` | `read:org` | read |
| Get Copilot organization user-teams report for a specific day | `GET /orgs/{org}/copilot/metrics/reports/user-teams-1-day` | `read:org` | read |
| Get Copilot organization users usage metrics for a specific day | `GET /orgs/{org}/copilot/metrics/reports/users-1-day` | `read:org` | read |
| Get Copilot organization users usage metrics | `GET /orgs/{org}/copilot/metrics/reports/users-28-day/latest` | `read:org` | read |

#### copilot / copilot-user-management (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get Copilot seat information and settings for an organization | `GET /orgs/{org}/copilot/billing` | - | read |
| List all Copilot seat assignments for an organization | `GET /orgs/{org}/copilot/billing/seats` | - | read |
| Remove teams from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_teams` | - | 3 |
| Add teams to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_teams` | - | 1 |
| Remove users from the Copilot subscription for an organization | `DELETE /orgs/{org}/copilot/billing/selected_users` | - | 3 |
| Add users to the Copilot subscription for an organization | `POST /orgs/{org}/copilot/billing/selected_users` | - | 1 |
| Get Copilot seat assignment details for a user | `GET /orgs/{org}/members/{username}/copilot` | - | read |

### REST: copilot-spaces (28 operations)

Home: Account > Copilot > Spaces; Organization > Copilot > Spaces. Coverage: in scope.

#### copilot-spaces / collaborators (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List collaborators for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/collaborators` | `read:org` | read |
| Add a collaborator to an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/collaborators` | `write:org` | 2 |
| Remove a collaborator from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | `write:org` | 3 |
| Set a collaborator role for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | `write:org` | 2 |
| List collaborators for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/collaborators` | `user` | read |
| Add a collaborator to a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/collaborators` | `user` | 2 |
| Remove a collaborator from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | `user` | 3 |
| Set a collaborator role for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/collaborators/{actor_type}/{actor_identifier}` | `user` | 2 |

#### copilot-spaces / copilot-spaces (10)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization Copilot Spaces | `GET /orgs/{org}/copilot-spaces` | `read:org` | read |
| Create an organization Copilot Space | `POST /orgs/{org}/copilot-spaces` | `read:org` | 1 |
| Delete an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}` | - | 3 |
| Get an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}` | `read:org` | read |
| Set an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}` | `read:org` | 1 |
| List Copilot Spaces for a user | `GET /users/{username}/copilot-spaces` | `read:user` | read |
| Create a Copilot Space for a user | `POST /users/{username}/copilot-spaces` | `read:user` | 1 |
| Delete a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}` | `user` | 3 |
| Get a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}` | `repo` | read |
| Set a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}` | `read:user` | 1 |

#### copilot-spaces / resources (10)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List resources for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources` | `read:org` | read |
| Create a resource for an organization Copilot Space | `POST /orgs/{org}/copilot-spaces/{space_number}/resources` | `write:org` | 1 |
| Delete a resource from an organization Copilot Space | `DELETE /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `write:org` | 3 |
| Get a resource for an organization Copilot Space | `GET /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `read:org` | read |
| Set a resource for an organization Copilot Space | `PUT /orgs/{org}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `write:org` | 1 |
| List resources for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources` | `read:user` | read |
| Create a resource for a Copilot Space for a user | `POST /users/{username}/copilot-spaces/{space_number}/resources` | `write:user` | 1 |
| Delete a resource from a Copilot Space for a user | `DELETE /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `write:user` | 3 |
| Get a resource for a Copilot Space for a user | `GET /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `read:user` | read |
| Set a resource for a Copilot Space for a user | `PUT /users/{username}/copilot-spaces/{space_number}/resources/{space_resource_id}` | `write:user` | 1 |

### REST: credentials (1 operations)

Home: Out of scope: credential revocation is for apps and scanning partners. Coverage: out of scope.

#### credentials / revoke (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Revoke a list of credentials | `POST /credentials/revoke` | - | 1 |

### REST: dependabot (27 operations)

Home: Repository > Security > Alerts (Kind: Dependabot); Alert sheet; Dependabot secrets; dependabot.yml sheet. Coverage: in scope.

#### dependabot / alerts (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List Dependabot alerts for an enterprise | `GET /enterprises/{enterprise}/dependabot/alerts` | `repo`, `security_events` | read |
| List Dependabot alerts for an organization | `GET /orgs/{org}/dependabot/alerts` | `security_events` | read |
| List Dependabot alerts for a repository | `GET /repos/{owner}/{repo}/dependabot/alerts` | `security_events` | read |
| Get a Dependabot alert | `GET /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | `security_events` | read |
| Update a Dependabot alert | `PATCH /repos/{owner}/{repo}/dependabot/alerts/{alert_number}` | `security_events` | 1 |

#### dependabot / repository-access (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Lists the repositories Dependabot can access in an enterprise | `GET /enterprises/{enterprise}/dependabot/repository-access` | - | read |
| Updates Dependabot's repository access list for an enterprise | `PATCH /enterprises/{enterprise}/dependabot/repository-access` | - | 1 |
| Set the default repository access level for Dependabot in an enterprise | `PUT /enterprises/{enterprise}/dependabot/repository-access/default-level` | - | 1 |
| Lists the repositories Dependabot can access in an organization | `GET /orgs/{org}/dependabot/repository-access` | - | read |
| Updates Dependabot's repository access list for an organization | `PATCH /orgs/{org}/dependabot/repository-access` | `write:org` | 1 |
| Set the default repository access level for Dependabot | `PUT /orgs/{org}/dependabot/repository-access/default-level` | `write:org` | 1 |

#### dependabot / runner-settings (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get repository Dependabot runner settings | `GET /repos/{owner}/{repo}/dependabot/runner-settings` | - | read |
| Set repository Dependabot runner settings | `PUT /repos/{owner}/{repo}/dependabot/runner-settings` | - | 1 |

#### dependabot / secrets (14)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization secrets | `GET /orgs/{org}/dependabot/secrets` | `admin:org` | read |
| Get an organization public key | `GET /orgs/{org}/dependabot/secrets/public-key` | `admin:org` | read |
| Delete an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}` | `admin:org` | 3 |
| Get an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}` | `admin:org` | read |
| Create or update an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}` | `admin:org` | 2 |
| List selected repositories for an organization secret | `GET /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | `admin:org` | read |
| Set selected repositories for an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories` | `admin:org` | 2 |
| Remove selected repository from an organization secret | `DELETE /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 3 |
| Add selected repository to an organization secret | `PUT /orgs/{org}/dependabot/secrets/{secret_name}/repositories/{repository_id}` | `admin:org` | 2 |
| List repository secrets | `GET /repos/{owner}/{repo}/dependabot/secrets` | `repo` | read |
| Get a repository public key | `GET /repos/{owner}/{repo}/dependabot/secrets/public-key` | `repo` | read |
| Delete a repository secret | `DELETE /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | `repo` | 3 |
| Get a repository secret | `GET /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | `repo` | read |
| Create or update a repository secret | `PUT /repos/{owner}/{repo}/dependabot/secrets/{secret_name}` | `repo` | 2 |

### REST: dependency-graph (5 operations)

Home: Repository > Security > Dependencies; Export SBOM. Coverage: in scope.

#### dependency-graph / dependency-review (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get a diff of the dependencies between commits | `GET /repos/{owner}/{repo}/dependency-graph/compare/{basehead}` | - | read |

#### dependency-graph / dependency-submission (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a snapshot of dependencies for a repository | `POST /repos/{owner}/{repo}/dependency-graph/snapshots` | `repo` | 1 |

#### dependency-graph / sboms (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Export a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom` | - | read |
| Fetch a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/fetch-report/{sbom_uuid}` | - | read |
| Request generation of a software bill of materials (SBOM) for a repository. | `GET /repos/{owner}/{repo}/dependency-graph/sbom/generate-report` | - | read |

### REST: deploy-keys (4 operations)

Home: Repository sheet > Deploy Keys. Coverage: in scope.

#### deploy-keys / deploy-keys (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List deploy keys | `GET /repos/{owner}/{repo}/keys` | - | read |
| Create a deploy key | `POST /repos/{owner}/{repo}/keys` | - | 2 |
| Delete a deploy key | `DELETE /repos/{owner}/{repo}/keys/{key_id}` | - | 3 |
| Get a deploy key | `GET /repos/{owner}/{repo}/keys/{key_id}` | - | read |

### REST: deployments (21 operations)

Home: Repository > Deployments and Environments; Environment and Deployment sheets. Coverage: in scope.

#### deployments / branch-policies (5)

Home: Environment sheet > Branches and Tags.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List deployment branch policies | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | `repo` | read |
| Create a deployment branch policy | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies` | `repo` | 2 |
| Delete a deployment branch policy | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | `repo` | 3 |
| Get a deployment branch policy | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | `repo` | read |
| Update a deployment branch policy | `PUT /repos/{owner}/{repo}/environments/{environment_name}/deployment-branch-policies/{branch_policy_id}` | `repo` | 2 |

#### deployments / deployments (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List deployments | `GET /repos/{owner}/{repo}/deployments` | - | read |
| Create a deployment | `POST /repos/{owner}/{repo}/deployments` | `repo`, `repo_deployment` | 1 |
| Delete a deployment | `DELETE /repos/{owner}/{repo}/deployments/{deployment_id}` | `repo`, `repo_deployment` | 3 |
| Get a deployment | `GET /repos/{owner}/{repo}/deployments/{deployment_id}` | - | read |

#### deployments / environments (4)

Home: Environment sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List environments | `GET /repos/{owner}/{repo}/environments` | `repo` | read |
| Delete an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}` | `repo` | 3 |
| Get an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}` | `repo` | read |
| Create or update an environment | `PUT /repos/{owner}/{repo}/environments/{environment_name}` | `repo` | 2 |

#### deployments / protection-rules (5)

Home: Environment sheet > Protection.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all deployment protection rules for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | `repo` | read |
| Create a custom deployment protection rule on an environment | `POST /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules` | `repo` | 2 |
| List custom deployment rule integrations available for an environment | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/apps` | `repo` | read |
| Disable a custom protection rule for an environment | `DELETE /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | `repo` | 3 |
| Get a custom deployment protection rule | `GET /repos/{owner}/{repo}/environments/{environment_name}/deployment_protection_rules/{protection_rule_id}` | `repo` | read |

#### deployments / statuses (3)

Home: Deployment sheet > Statuses.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List deployment statuses | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | - | read |
| Create a deployment status | `POST /repos/{owner}/{repo}/deployments/{deployment_id}/statuses` | `repo_deployment` | 1 |
| Get a deployment status | `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses/{status_id}` | - | read |

### REST: emojis (1 operations)

Home: Plumbing: emoji completion in comment boxes. Coverage: plumbing (no_api_needed).

#### emojis / emojis (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get emojis | `GET /emojis` | - | read |

### REST: gists (20 operations)

Home: Gists; Gist sheet. Coverage: in scope.

#### gists / comments (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List gist comments | `GET /gists/{gist_id}/comments` | - | read |
| Create a gist comment | `POST /gists/{gist_id}/comments` | - | 1 |
| Delete a gist comment | `DELETE /gists/{gist_id}/comments/{comment_id}` | - | 3 |
| Get a gist comment | `GET /gists/{gist_id}/comments/{comment_id}` | - | read |
| Update a gist comment | `PATCH /gists/{gist_id}/comments/{comment_id}` | - | 1 |

#### gists / gists (15)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List gists for the authenticated user | `GET /gists` | - | read |
| Create a gist | `POST /gists` | - | 1 |
| List public gists | `GET /gists/public` | - | read |
| List starred gists | `GET /gists/starred` | - | read |
| Delete a gist | `DELETE /gists/{gist_id}` | - | 3 |
| Get a gist | `GET /gists/{gist_id}` | - | read |
| Update a gist | `PATCH /gists/{gist_id}` | - | 1 |
| List gist commits | `GET /gists/{gist_id}/commits` | - | read |
| List gist forks | `GET /gists/{gist_id}/forks` | - | read |
| Fork a gist | `POST /gists/{gist_id}/forks` | - | 1 |
| Unstar a gist | `DELETE /gists/{gist_id}/star` | - | 3 |
| Check if a gist is starred | `GET /gists/{gist_id}/star` | - | read |
| Star a gist | `PUT /gists/{gist_id}/star` | - | 1 |
| Get a gist revision | `GET /gists/{gist_id}/{sha}` | - | read |
| List gists for a user | `GET /users/{username}/gists` | - | read |

### REST: git (13 operations)

Home: Plumbing under Commit Multiple Files, tags and refs; Tag sheet (create, move, delete). Coverage: plumbing (no_api_needed).

#### git / blobs (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a blob | `POST /repos/{owner}/{repo}/git/blobs` | - | 1 |
| Get a blob | `GET /repos/{owner}/{repo}/git/blobs/{file_sha}` | - | read |

#### git / commits (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a commit | `POST /repos/{owner}/{repo}/git/commits` | - | 1 |
| Get a commit object | `GET /repos/{owner}/{repo}/git/commits/{commit_sha}` | - | read |

#### git / refs (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List matching references | `GET /repos/{owner}/{repo}/git/matching-refs/{ref}` | - | read |
| Get a reference | `GET /repos/{owner}/{repo}/git/ref/{ref}` | - | read |
| Create a reference | `POST /repos/{owner}/{repo}/git/refs` | - | 1 |
| Delete a reference | `DELETE /repos/{owner}/{repo}/git/refs/{ref}` | - | 3 |
| Update a reference | `PATCH /repos/{owner}/{repo}/git/refs/{ref}` | - | 1 |

#### git / tags (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a tag object | `POST /repos/{owner}/{repo}/git/tags` | - | 1 |
| Get a tag | `GET /repos/{owner}/{repo}/git/tags/{tag_sha}` | - | read |

#### git / trees (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a tree | `POST /repos/{owner}/{repo}/git/trees` | - | 1 |
| Get a tree | `GET /repos/{owner}/{repo}/git/trees/{tree_sha}` | - | read |

### REST: gitignore (2 operations)

Home: New Repository... (gitignore picker). Coverage: in scope.

#### gitignore / gitignore (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all gitignore templates | `GET /gitignore/templates` | - | read |
| Get a gitignore template | `GET /gitignore/templates/{name}` | - | read |

### REST: interactions (16 operations)

Home: Repository and Organization sheets > General > Interaction Limits. Coverage: in scope.

#### interactions / orgs (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Remove interaction restrictions for an organization | `DELETE /orgs/{org}/interaction-limits` | - | 3 |
| Get interaction restrictions for an organization | `GET /orgs/{org}/interaction-limits` | - | read |
| Set interaction restrictions for an organization | `PUT /orgs/{org}/interaction-limits` | - | 2 |
| Get pull request creation cap for an org | `GET /orgs/{org}/interaction-limits/pulls/creation-cap` | - | read |
| Update pull request creation cap for an org | `PATCH /orgs/{org}/interaction-limits/pulls/creation-cap` | - | 2 |

#### interactions / repos (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Remove interaction restrictions for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits` | - | 3 |
| Get interaction restrictions for a repository | `GET /repos/{owner}/{repo}/interaction-limits` | - | read |
| Set interaction restrictions for a repository | `PUT /repos/{owner}/{repo}/interaction-limits` | - | 2 |
| Remove users from the pull request creation cap bypass list for a repository | `DELETE /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | - | 3 |
| Get pull request creation cap bypass list for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | - | read |
| Add users to the pull request creation cap bypass list for a repository | `PUT /repos/{owner}/{repo}/interaction-limits/pulls/bypass-list` | - | 2 |
| Get pull request creation cap for a repository | `GET /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | - | read |
| Update pull request creation cap for a repository | `PATCH /repos/{owner}/{repo}/interaction-limits/pulls/creation-cap` | - | 2 |

#### interactions / user (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Remove interaction restrictions from your public repositories | `DELETE /user/interaction-limits` | - | 3 |
| Get interaction restrictions for your public repositories | `GET /user/interaction-limits` | - | read |
| Set interaction restrictions for your public repositories | `PUT /user/interaction-limits` | - | 2 |

### REST: issues (66 operations)

Home: Issue and Pull request sheets; Label, Milestone and Issue type sheets; comments; timeline. Coverage: in scope.

#### issues / artifacts (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue artifacts | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | - | read |
| Create an issue artifact | `POST /repos/{owner}/{repo}/issues/{issue_number}/artifacts` | - | 1 |
| Delete an issue artifact | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | - | 3 |
| Get an issue artifact | `GET /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | - | read |
| Update an issue artifact | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/artifacts/{artifact_number}` | - | 1 |

#### issues / assignees (5)

Home: Issue > Organize: Assignees.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List assignees | `GET /repos/{owner}/{repo}/assignees` | - | read |
| Check if a user can be assigned | `GET /repos/{owner}/{repo}/assignees/{assignee}` | - | read |
| Remove assignees from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/assignees` | - | 3 |
| Add assignees to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/assignees` | - | 1 |
| Check if a user can be assigned to a issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/assignees/{assignee}` | - | read |

#### issues / comments (8)

Home: Comment sheet; Conversation page.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue comments for a repository | `GET /repos/{owner}/{repo}/issues/comments` | - | read |
| Delete an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}` | - | 3 |
| Get an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}` | - | read |
| Update an issue comment | `PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}` | - | 1 |
| Unpin an issue comment | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | - | 3 |
| Pin an issue comment | `PUT /repos/{owner}/{repo}/issues/comments/{comment_id}/pin` | - | 1 |
| List issue comments | `GET /repos/{owner}/{repo}/issues/{issue_number}/comments` | - | read |
| Create an issue comment | `POST /repos/{owner}/{repo}/issues/{issue_number}/comments` | - | 1 |

#### issues / events (3)

Home: Issue > Timeline.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue events for a repository | `GET /repos/{owner}/{repo}/issues/events` | - | read |
| Get an issue event | `GET /repos/{owner}/{repo}/issues/events/{event_id}` | - | read |
| List issue events | `GET /repos/{owner}/{repo}/issues/{issue_number}/events` | - | read |

#### issues / issue-dependencies (4)

Home: Issue > Relationships: blocked by, blocking.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List dependencies an issue is blocked by | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | - | read |
| Add a dependency an issue is blocked by | `POST /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` | - | 1 |
| Remove dependency an issue is blocked by | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by/{issue_id}` | - | 3 |
| List dependencies an issue is blocking | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocking` | - | read |

#### issues / issue-field-values (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue field values for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | - | read |
| Add issue field values to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | - | 1 |
| Set issue field values for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values` | - | 1 |
| Delete an issue field value from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/issue-field-values/{issue_field_id}` | - | 3 |

#### issues / issues (15)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issues assigned to the authenticated user | `GET /issues` | - | read |
| List organization issues assigned to the authenticated user | `GET /orgs/{org}/issues` | - | read |
| List repository issues | `GET /repos/{owner}/{repo}/issues` | - | read |
| Create an issue | `POST /repos/{owner}/{repo}/issues` | - | 1 |
| Get an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}` | - | read |
| Update an issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}` | - | 1 |
| Unlock an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/lock` | - | 3 |
| Lock an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/lock` | - | 1 |
| List issues related to an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | - | read |
| Add a related issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/relates_to` | - | 1 |
| Remove a related issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/relates_to/{issue_id}` | - | 3 |
| List issue suggestions | `GET /repos/{owner}/{repo}/issues/{issue_number}/suggestions` | - | read |
| Approve an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/approve` | - | 1 |
| Dismiss an issue suggestion | `POST /repos/{owner}/{repo}/issues/{issue_number}/suggestions/{suggestion_id}/dismiss` | - | 1 |
| List user account issues assigned to the authenticated user | `GET /user/issues` | - | read |

#### issues / labels (11)

Home: Label sheet; Issue > Organize: Labels.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Remove all labels from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels` | - | 3 |
| List labels for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/labels` | - | read |
| Add labels to an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/labels` | - | 1 |
| Set labels for an issue | `PUT /repos/{owner}/{repo}/issues/{issue_number}/labels` | - | 1 |
| Remove a label from an issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}` | - | 3 |
| List labels for a repository | `GET /repos/{owner}/{repo}/labels` | - | read |
| Create a label | `POST /repos/{owner}/{repo}/labels` | - | 1 |
| Delete a label | `DELETE /repos/{owner}/{repo}/labels/{name}` | - | 3 |
| Get a label | `GET /repos/{owner}/{repo}/labels/{name}` | - | read |
| Update a label | `PATCH /repos/{owner}/{repo}/labels/{name}` | - | 1 |
| List labels for issues in a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}/labels` | - | read |

#### issues / milestones (5)

Home: Milestone sheet; Issue > Organize: Milestone.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List milestones | `GET /repos/{owner}/{repo}/milestones` | - | read |
| Create a milestone | `POST /repos/{owner}/{repo}/milestones` | - | 1 |
| Delete a milestone | `DELETE /repos/{owner}/{repo}/milestones/{milestone_number}` | - | 3 |
| Get a milestone | `GET /repos/{owner}/{repo}/milestones/{milestone_number}` | - | read |
| Update a milestone | `PATCH /repos/{owner}/{repo}/milestones/{milestone_number}` | - | 1 |

#### issues / sub-issues (5)

Home: Issue > Relationships: sub-issues.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get parent issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/parent` | - | read |
| Remove sub-issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/sub_issue` | - | 3 |
| List sub-issues | `GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | - | read |
| Add sub-issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` | - | 1 |
| Reprioritize sub-issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/sub_issues/priority` | - | 1 |

#### issues / timeline (1)

Home: Issue > Timeline.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List timeline events for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/timeline` | - | read |

### REST: licenses (3 operations)

Home: New Repository... (license picker, explained); Repository > General: License. Coverage: in scope.

#### licenses / licenses (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all commonly used licenses | `GET /licenses` | - | read |
| Get a license | `GET /licenses/{license}` | - | read |
| Get the license for a repository | `GET /repos/{owner}/{repo}/license` | - | read |

### REST: markdown (2 operations)

Home: Plumbing: comment preview. Coverage: plumbing (no_api_needed).

#### markdown / markdown (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Render a Markdown document | `POST /markdown` | - | 1 |
| Render a Markdown document in raw mode | `POST /markdown/raw` | - | 1 |

### REST: meta (5 operations)

Home: Plumbing: API root, GitHub's addresses; Help > Is GitHub Working?. Coverage: plumbing (no_api_needed).

#### meta / meta (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| GitHub API Root | `GET /` | - | read |
| Get GitHub meta information | `GET /meta` | - | read |
| Get Octocat | `GET /octocat` | - | read |
| Get all API versions | `GET /versions` | - | read |
| Get the Zen of GitHub | `GET /zen` | - | read |

### REST: metrics (10 operations)

Home: Repository > Insights (traffic, community profile, statistics as tables). Coverage: in scope.

#### metrics / community (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get community profile metrics | `GET /repos/{owner}/{repo}/community/profile` | - | read |

#### metrics / statistics (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the weekly commit activity | `GET /repos/{owner}/{repo}/stats/code_frequency` | - | read |
| Get the last year of commit activity | `GET /repos/{owner}/{repo}/stats/commit_activity` | - | read |
| Get all contributor commit activity | `GET /repos/{owner}/{repo}/stats/contributors` | - | read |
| Get the weekly commit count | `GET /repos/{owner}/{repo}/stats/participation` | - | read |
| Get the hourly commit count for each day | `GET /repos/{owner}/{repo}/stats/punch_card` | - | read |

#### metrics / traffic (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get repository clones | `GET /repos/{owner}/{repo}/traffic/clones` | - | read |
| Get top referral paths | `GET /repos/{owner}/{repo}/traffic/popular/paths` | - | read |
| Get top referral sources | `GET /repos/{owner}/{repo}/traffic/popular/referrers` | - | read |
| Get page views | `GET /repos/{owner}/{repo}/traffic/views` | - | read |

### REST: migrations (22 operations)

Home: Account > Export My Data; Organization > Migrations (archives). Coverage: in scope.

#### migrations / orgs (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization migrations | `GET /orgs/{org}/migrations` | - | read |
| Start an organization migration | `POST /orgs/{org}/migrations` | - | 1 |
| Get an organization migration status | `GET /orgs/{org}/migrations/{migration_id}` | - | read |
| Delete an organization migration archive | `DELETE /orgs/{org}/migrations/{migration_id}/archive` | - | 3 |
| Download an organization migration archive | `GET /orgs/{org}/migrations/{migration_id}/archive` | - | read |
| Unlock an organization repository | `DELETE /orgs/{org}/migrations/{migration_id}/repos/{repo_name}/lock` | - | 3 |
| List repositories in an organization migration | `GET /orgs/{org}/migrations/{migration_id}/repositories` | - | read |

#### migrations / source-imports (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Cancel an import | `DELETE /repos/{owner}/{repo}/import` | - | 3 |
| Get an import status | `GET /repos/{owner}/{repo}/import` | - | read |
| Update an import | `PATCH /repos/{owner}/{repo}/import` | - | 1 |
| Start an import | `PUT /repos/{owner}/{repo}/import` | - | 1 |
| Get commit authors | `GET /repos/{owner}/{repo}/import/authors` | - | read |
| Map a commit author | `PATCH /repos/{owner}/{repo}/import/authors/{author_id}` | - | 1 |
| Get large files | `GET /repos/{owner}/{repo}/import/large_files` | - | read |
| Update Git LFS preference | `PATCH /repos/{owner}/{repo}/import/lfs` | - | 1 |

#### migrations / users (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List user migrations | `GET /user/migrations` | - | read |
| Start a user migration | `POST /user/migrations` | - | 1 |
| Get a user migration status | `GET /user/migrations/{migration_id}` | - | read |
| Delete a user migration archive | `DELETE /user/migrations/{migration_id}/archive` | - | 3 |
| Download a user migration archive | `GET /user/migrations/{migration_id}/archive` | - | read |
| Unlock a user repository | `DELETE /user/migrations/{migration_id}/repos/{repo_name}/lock` | - | 3 |
| List repositories for a user migration | `GET /user/migrations/{migration_id}/repositories` | - | read |

### REST: orgs (129 operations)

Home: Organization sheet: Members, Roles, Member Privileges, Webhooks, Custom Properties, Token Requests, Security managers, Rulesets. Coverage: in scope.

#### orgs / api-insights (9)

Home: Organization > Insights > API usage (read).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get route stats by actor | `GET /orgs/{org}/insights/api/route-stats/{actor_type}/{actor_id}` | - | read |
| Get subject stats | `GET /orgs/{org}/insights/api/subject-stats` | - | read |
| Get summary stats | `GET /orgs/{org}/insights/api/summary-stats` | - | read |
| Get summary stats by user | `GET /orgs/{org}/insights/api/summary-stats/users/{user_id}` | - | read |
| Get summary stats by actor | `GET /orgs/{org}/insights/api/summary-stats/{actor_type}/{actor_id}` | - | read |
| Get time stats | `GET /orgs/{org}/insights/api/time-stats` | - | read |
| Get time stats by user | `GET /orgs/{org}/insights/api/time-stats/users/{user_id}` | - | read |
| Get time stats by actor | `GET /orgs/{org}/insights/api/time-stats/{actor_type}/{actor_id}` | - | read |
| Get user stats | `GET /orgs/{org}/insights/api/user-stats/{user_id}` | - | read |

#### orgs / artifact-metadata (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create an artifact deployment record | `POST /orgs/{org}/artifacts/metadata/deployment-record` | - | 2 |
| Set cluster deployment records | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}` | - | 2 |
| Create a cluster deployment records job | `POST /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs` | - | 2 |
| Get cluster deployment records job status | `GET /orgs/{org}/artifacts/metadata/deployment-record/cluster/{cluster}/jobs/{job_id}` | - | read |
| Create artifact metadata storage record | `POST /orgs/{org}/artifacts/metadata/storage-record` | - | 2 |
| List artifact deployment records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/deployment-records` | - | read |
| List artifact storage records | `GET /orgs/{org}/artifacts/{subject_digest}/metadata/storage-records` | - | read |

#### orgs / attestations (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List attestations by bulk subject digests | `POST /orgs/{org}/attestations/bulk-list` | - | 2 |
| Delete attestations in bulk | `POST /orgs/{org}/attestations/delete-request` | - | 2 |
| Delete attestations by subject digest | `DELETE /orgs/{org}/attestations/digest/{subject_digest}` | - | 3 |
| List attestation repositories | `GET /orgs/{org}/attestations/repositories` | - | read |
| Delete attestations by ID | `DELETE /orgs/{org}/attestations/{attestation_id}` | - | 3 |
| List attestations | `GET /orgs/{org}/attestations/{subject_digest}` | - | read |

#### orgs / blocking (4)

Home: Organization sheet > Blocked Users; Person > You: Block.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List users blocked by an organization | `GET /orgs/{org}/blocks` | - | read |
| Unblock a user from an organization | `DELETE /orgs/{org}/blocks/{username}` | - | 3 |
| Check if a user is blocked by an organization | `GET /orgs/{org}/blocks/{username}` | - | read |
| Block a user from an organization | `PUT /orgs/{org}/blocks/{username}` | - | 2 |

#### orgs / custom-properties (13)

Home: Organization sheet > Custom Properties.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get registered app installations for external custom properties | `GET /orgs/{org}/properties/installations` | - | read |
| Register an app installation for external custom properties | `POST /orgs/{org}/properties/installations` | - | 2 |
| Get all external custom properties for a GitHub App installation in an organization | `GET /orgs/{org}/properties/installations/schema` | - | read |
| Create or update external custom property values for organization repositories | `PATCH /orgs/{org}/properties/installations/values` | - | 2 |
| Remove all external custom property values for a property across all organization repositories | `DELETE /orgs/{org}/properties/installations/values/{property_name}` | - | 3 |
| Create or update external custom property values for a property across organization repositories | `PATCH /orgs/{org}/properties/installations/values/{property_name}` | - | 2 |
| Get all custom properties for an organization | `GET /orgs/{org}/properties/schema` | - | read |
| Create or update custom properties for an organization | `PATCH /orgs/{org}/properties/schema` | - | 2 |
| Remove a custom property for an organization | `DELETE /orgs/{org}/properties/schema/{custom_property_name}` | - | 3 |
| Get a custom property for an organization | `GET /orgs/{org}/properties/schema/{custom_property_name}` | - | read |
| Create or update a custom property for an organization | `PUT /orgs/{org}/properties/schema/{custom_property_name}` | - | 2 |
| List custom property values for organization repositories | `GET /orgs/{org}/properties/values` | - | read |
| Create or update custom property values for organization repositories | `PATCH /orgs/{org}/properties/values` | - | 2 |

#### orgs / issue-fields (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue fields for an organization | `GET /orgs/{org}/issue-fields` | - | read |
| Create issue field for an organization | `POST /orgs/{org}/issue-fields` | `admin:org` | 2 |
| Delete issue field for an organization | `DELETE /orgs/{org}/issue-fields/{issue_field_id}` | `admin:org` | 3 |
| Update issue field for an organization | `PATCH /orgs/{org}/issue-fields/{issue_field_id}` | `admin:org` | 2 |

#### orgs / issue-types (4)

Home: Issue type sheet (organization).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue types for an organization | `GET /orgs/{org}/issue-types` | - | read |
| Create issue type for an organization | `POST /orgs/{org}/issue-types` | `admin:org` | 2 |
| Delete issue type for an organization | `DELETE /orgs/{org}/issue-types/{issue_type_id}` | `admin:org` | 3 |
| Update issue type for an organization | `PUT /orgs/{org}/issue-types/{issue_type_id}` | `admin:org` | 2 |

#### orgs / members (18)

Home: Organization sheet > Members.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List failed organization invitations | `GET /orgs/{org}/failed_invitations` | - | read |
| List pending organization invitations | `GET /orgs/{org}/invitations` | - | read |
| Create an organization invitation | `POST /orgs/{org}/invitations` | - | 2 |
| Cancel an organization invitation | `DELETE /orgs/{org}/invitations/{invitation_id}` | - | 3 |
| List organization invitation teams | `GET /orgs/{org}/invitations/{invitation_id}/teams` | - | read |
| List organization members | `GET /orgs/{org}/members` | - | read |
| Remove an organization member | `DELETE /orgs/{org}/members/{username}` | - | 3 |
| Check organization membership for a user | `GET /orgs/{org}/members/{username}` | - | read |
| Remove organization membership for a user | `DELETE /orgs/{org}/memberships/{username}` | - | 3 |
| Get organization membership for a user | `GET /orgs/{org}/memberships/{username}` | - | read |
| Set organization membership for a user | `PUT /orgs/{org}/memberships/{username}` | - | 2 |
| List public organization members | `GET /orgs/{org}/public_members` | - | read |
| Remove public organization membership for the authenticated user | `DELETE /orgs/{org}/public_members/{username}` | - | 3 |
| Check public organization membership for a user | `GET /orgs/{org}/public_members/{username}` | - | read |
| Set public organization membership for the authenticated user | `PUT /orgs/{org}/public_members/{username}` | - | 2 |
| List organization memberships for the authenticated user | `GET /user/memberships/orgs` | - | read |
| Get an organization membership for the authenticated user | `GET /user/memberships/orgs/{org}` | - | read |
| Update an organization membership for the authenticated user | `PATCH /user/memberships/orgs/{org}` | - | 2 |

#### orgs / network-configurations (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List hosted compute network configurations for an organization | `GET /orgs/{org}/settings/network-configurations` | `read:network_configurations` | read |
| Create a hosted compute network configuration for an organization | `POST /orgs/{org}/settings/network-configurations` | `write:network_configurations` | 2 |
| Delete a hosted compute network configuration from an organization | `DELETE /orgs/{org}/settings/network-configurations/{network_configuration_id}` | `write:network_configurations` | 3 |
| Get a hosted compute network configuration for an organization | `GET /orgs/{org}/settings/network-configurations/{network_configuration_id}` | `read:network_configurations` | read |
| Update a hosted compute network configuration for an organization | `PATCH /orgs/{org}/settings/network-configurations/{network_configuration_id}` | `write:network_configurations` | 2 |
| Get a hosted compute network settings resource for an organization | `GET /orgs/{org}/settings/network-settings/{network_settings_id}` | `read:network_configurations` | read |

#### orgs / organization-roles (10)

Home: Organization sheet > Roles.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all organization roles for an organization | `GET /orgs/{org}/organization-roles` | `admin:org` | read |
| Remove all organization roles for a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}` | `admin:org` | 3 |
| Remove an organization role from a team | `DELETE /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | `admin:org` | 3 |
| Assign an organization role to a team | `PUT /orgs/{org}/organization-roles/teams/{team_slug}/{role_id}` | `admin:org` | 2 |
| Remove all organization roles for a user | `DELETE /orgs/{org}/organization-roles/users/{username}` | `admin:org` | 3 |
| Remove an organization role from a user | `DELETE /orgs/{org}/organization-roles/users/{username}/{role_id}` | `admin:org` | 3 |
| Assign an organization role to a user | `PUT /orgs/{org}/organization-roles/users/{username}/{role_id}` | `admin:org` | 2 |
| Get an organization role | `GET /orgs/{org}/organization-roles/{role_id}` | `admin:org` | read |
| List teams that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/teams` | `admin:org` | read |
| List users that are assigned to an organization role | `GET /orgs/{org}/organization-roles/{role_id}/users` | `admin:org` | read |

#### orgs / orgs (14)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organizations | `GET /organizations` | - | read |
| Delete an organization | `DELETE /orgs/{org}` | - | 3 |
| Get an organization | `GET /orgs/{org}` | `admin:org` | read |
| Update an organization | `PATCH /orgs/{org}` | `admin:org`, `repo` | 2 |
| List app installations for an organization | `GET /orgs/{org}/installations` | `admin:read` | read |
| Get immutable releases settings for an organization | `GET /orgs/{org}/settings/immutable-releases` | `admin:org` | read |
| Set immutable releases settings for an organization | `PUT /orgs/{org}/settings/immutable-releases` | `admin:org` | 2 |
| List selected repositories for immutable releases enforcement | `GET /orgs/{org}/settings/immutable-releases/repositories` | `admin:org` | read |
| Set selected repositories for immutable releases enforcement | `PUT /orgs/{org}/settings/immutable-releases/repositories` | `admin:org` | 2 |
| Disable a selected repository for immutable releases in an organization | `DELETE /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | `admin:org` | 3 |
| Enable a selected repository for immutable releases in an organization | `PUT /orgs/{org}/settings/immutable-releases/repositories/{repository_id}` | `admin:org` | 2 |
| Enable or disable a security feature for an organization | `POST /orgs/{org}/{security_product}/{enablement}` | - | 2 |
| List organizations for the authenticated user | `GET /user/orgs` | - | read |
| List organizations for a user | `GET /users/{username}/orgs` | - | read |

#### orgs / outside-collaborators (3)

Home: Organization sheet > Outside Collaborators.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List outside collaborators for an organization | `GET /orgs/{org}/outside_collaborators` | - | read |
| Remove outside collaborator from an organization | `DELETE /orgs/{org}/outside_collaborators/{username}` | - | 3 |
| Convert an organization member to outside collaborator | `PUT /orgs/{org}/outside_collaborators/{username}` | - | 2 |

#### orgs / personal-access-tokens (8)

Home: Organization sheet > Token Requests.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List requests to access organization resources with fine-grained personal access tokens | `GET /orgs/{org}/personal-access-token-requests` | - | read |
| Review requests to access organization resources with fine-grained personal access tokens | `POST /orgs/{org}/personal-access-token-requests` | - | 2 |
| Review a request to access organization resources with a fine-grained personal access token | `POST /orgs/{org}/personal-access-token-requests/{pat_request_id}` | - | 2 |
| List repositories requested to be accessed by a fine-grained personal access token | `GET /orgs/{org}/personal-access-token-requests/{pat_request_id}/repositories` | - | read |
| List fine-grained personal access tokens with access to organization resources | `GET /orgs/{org}/personal-access-tokens` | - | read |
| Update the access to organization resources via fine-grained personal access tokens | `POST /orgs/{org}/personal-access-tokens` | - | 2 |
| Update the access a fine-grained personal access token has to organization resources | `POST /orgs/{org}/personal-access-tokens/{pat_id}` | - | 2 |
| List repositories a fine-grained personal access token has access to | `GET /orgs/{org}/personal-access-tokens/{pat_id}/repositories` | - | read |

#### orgs / rule-suites (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization rule suites | `GET /orgs/{org}/rulesets/rule-suites` | - | read |
| Get an organization rule suite | `GET /orgs/{org}/rulesets/rule-suites/{rule_suite_id}` | - | read |

#### orgs / rules (7)

Home: Organization rulesets (section 18.3.1).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all organization repository rulesets | `GET /orgs/{org}/rulesets` | - | read |
| Create an organization repository ruleset | `POST /orgs/{org}/rulesets` | - | 2 |
| Delete an organization repository ruleset | `DELETE /orgs/{org}/rulesets/{ruleset_id}` | - | 3 |
| Get an organization repository ruleset | `GET /orgs/{org}/rulesets/{ruleset_id}` | - | read |
| Update an organization repository ruleset | `PUT /orgs/{org}/rulesets/{ruleset_id}` | - | 2 |
| Get organization ruleset history | `GET /orgs/{org}/rulesets/{ruleset_id}/history` | - | read |
| Get organization ruleset version | `GET /orgs/{org}/rulesets/{ruleset_id}/history/{version_id}` | - | read |

#### orgs / security-managers (3)

Home: Organization sheet > Security: security managers.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List security manager teams | `GET /orgs/{org}/security-managers` | - | read |
| Remove a security manager team | `DELETE /orgs/{org}/security-managers/teams/{team_slug}` | - | 3 |
| Add a security manager team | `PUT /orgs/{org}/security-managers/teams/{team_slug}` | - | 2 |

#### orgs / webhooks (11)

Home: Organization sheet > Webhooks.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization webhooks | `GET /orgs/{org}/hooks` | - | read |
| Create an organization webhook | `POST /orgs/{org}/hooks` | - | 2 |
| Delete an organization webhook | `DELETE /orgs/{org}/hooks/{hook_id}` | - | 3 |
| Get an organization webhook | `GET /orgs/{org}/hooks/{hook_id}` | - | read |
| Update an organization webhook | `PATCH /orgs/{org}/hooks/{hook_id}` | - | 2 |
| Get a webhook configuration for an organization | `GET /orgs/{org}/hooks/{hook_id}/config` | - | read |
| Update a webhook configuration for an organization | `PATCH /orgs/{org}/hooks/{hook_id}/config` | - | 2 |
| List deliveries for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries` | - | read |
| Get a webhook delivery for an organization webhook | `GET /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}` | - | read |
| Redeliver a delivery for an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | - | 2 |
| Ping an organization webhook | `POST /orgs/{org}/hooks/{hook_id}/pings` | - | 2 |

### REST: packages (27 operations)

Home: Repositories > My Packages; Package sheet. Coverage: in scope.

#### packages / packages (27)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get list of conflicting packages during Docker migration for organization | `GET /orgs/{org}/docker/conflicts` | `read:packages` | read |
| List packages for an organization | `GET /orgs/{org}/packages` | `read:packages` | read |
| Delete a package for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}` | - | 3 |
| Get a package for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}` | `read:packages` | read |
| Restore a package for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/restore` | - | 1 |
| List package versions for a package owned by an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions` | `read:packages` | read |
| Delete package version for an organization | `DELETE /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | - | 3 |
| Get a package version for an organization | `GET /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}` | `read:packages` | read |
| Restore package version for an organization | `POST /orgs/{org}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | - | 1 |
| Get list of conflicting packages during Docker migration for authenticated-user | `GET /user/docker/conflicts` | `read:packages` | read |
| List packages for the authenticated user's namespace | `GET /user/packages` | `read:packages` | read |
| Delete a package for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}` | - | 3 |
| Get a package for the authenticated user | `GET /user/packages/{package_type}/{package_name}` | `read:packages` | read |
| Restore a package for the authenticated user | `POST /user/packages/{package_type}/{package_name}/restore` | - | 1 |
| List package versions for a package owned by the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions` | `read:packages` | read |
| Delete a package version for the authenticated user | `DELETE /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | - | 3 |
| Get a package version for the authenticated user | `GET /user/packages/{package_type}/{package_name}/versions/{package_version_id}` | `read:packages` | read |
| Restore a package version for the authenticated user | `POST /user/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | - | 1 |
| Get list of conflicting packages during Docker migration for user | `GET /users/{username}/docker/conflicts` | `read:packages` | read |
| List packages for a user | `GET /users/{username}/packages` | `read:packages` | read |
| Delete a package for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}` | - | 3 |
| Get a package for a user | `GET /users/{username}/packages/{package_type}/{package_name}` | `read:packages` | read |
| Restore a package for a user | `POST /users/{username}/packages/{package_type}/{package_name}/restore` | - | 1 |
| List package versions for a package owned by a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions` | `read:packages` | read |
| Delete package version for a user | `DELETE /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | - | 3 |
| Get a package version for a user | `GET /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}` | `read:packages` | read |
| Restore package version for a user | `POST /users/{username}/packages/{package_type}/{package_name}/versions/{package_version_id}/restore` | - | 1 |

### REST: pages (12 operations)

Home: Repository > GitHub Pages; Repository sheet > Pages. Coverage: in scope.

#### pages / pages (12)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete a GitHub Pages site | `DELETE /repos/{owner}/{repo}/pages` | `repo` | 3 |
| Get a GitHub Pages site | `GET /repos/{owner}/{repo}/pages` | `repo` | read |
| Create a GitHub Pages site | `POST /repos/{owner}/{repo}/pages` | `repo` | 1 |
| Update information about a GitHub Pages site | `PUT /repos/{owner}/{repo}/pages` | `repo` | 1 |
| List GitHub Pages builds | `GET /repos/{owner}/{repo}/pages/builds` | `repo` | read |
| Request a GitHub Pages build | `POST /repos/{owner}/{repo}/pages/builds` | - | 1 |
| Get latest Pages build | `GET /repos/{owner}/{repo}/pages/builds/latest` | `repo` | read |
| Get GitHub Pages build | `GET /repos/{owner}/{repo}/pages/builds/{build_id}` | `repo` | read |
| Create a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments` | - | 1 |
| Get the status of a GitHub Pages deployment | `GET /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}` | - | read |
| Cancel a GitHub Pages deployment | `POST /repos/{owner}/{repo}/pages/deployments/{pages_deployment_id}/cancel` | - | 1 |
| Get a DNS health check for GitHub Pages | `GET /repos/{owner}/{repo}/pages/health` | `repo` | read |

### REST: private-registries (6 operations)

Home: Organization sheet > Private Registries (for Dependabot). Coverage: in scope.

#### private-registries / organization-configurations (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List private registries for an organization | `GET /orgs/{org}/private-registries` | `admin:org` | read |
| Create a private registry for an organization | `POST /orgs/{org}/private-registries` | `admin:org` | 1 |
| Get private registries public key for an organization | `GET /orgs/{org}/private-registries/public-key` | `admin:org` | read |
| Delete a private registry for an organization | `DELETE /orgs/{org}/private-registries/{secret_name}` | `admin:org` | 3 |
| Get a private registry for an organization | `GET /orgs/{org}/private-registries/{secret_name}` | `admin:org` | read |
| Update a private registry for an organization | `PATCH /orgs/{org}/private-registries/{secret_name}` | `admin:org` | 1 |

### REST: projects (26 operations)

Home: Projects; Project, Project item, field and view sheets (section 16.6). Coverage: in scope.

#### projects / drafts (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create draft item for organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/drafts` | - | 1 |
| Create draft item for user owned project | `POST /user/{user_id}/projectsV2/{project_number}/drafts` | - | 1 |

#### projects / fields (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List project fields for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields` | - | read |
| Add a field to an organization-owned project. | `POST /orgs/{org}/projectsV2/{project_number}/fields` | - | 1 |
| Get project field for organization | `GET /orgs/{org}/projectsV2/{project_number}/fields/{field_id}` | - | read |
| List project fields for user | `GET /users/{username}/projectsV2/{project_number}/fields` | - | read |
| Add field to user owned project | `POST /users/{username}/projectsV2/{project_number}/fields` | - | 1 |
| Get project field for user | `GET /users/{username}/projectsV2/{project_number}/fields/{field_id}` | - | read |

#### projects / items (12)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List items for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items` | - | read |
| Add item to organization owned project | `POST /orgs/{org}/projectsV2/{project_number}/items` | - | 1 |
| Delete project item for organization | `DELETE /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | - | 3 |
| Get an item for an organization owned project | `GET /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | - | read |
| Update project item for organization | `PATCH /orgs/{org}/projectsV2/{project_number}/items/{item_id}` | - | 1 |
| List items for an organization project view | `GET /orgs/{org}/projectsV2/{project_number}/views/{view_number}/items` | - | read |
| List items for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items` | - | read |
| Add item to user owned project | `POST /users/{username}/projectsV2/{project_number}/items` | - | 1 |
| Delete project item for user | `DELETE /users/{username}/projectsV2/{project_number}/items/{item_id}` | - | 3 |
| Get an item for a user owned project | `GET /users/{username}/projectsV2/{project_number}/items/{item_id}` | - | read |
| Update project item for user | `PATCH /users/{username}/projectsV2/{project_number}/items/{item_id}` | - | 1 |
| List items for a user project view | `GET /users/{username}/projectsV2/{project_number}/views/{view_number}/items` | - | read |

#### projects / projects (4)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List projects for organization | `GET /orgs/{org}/projectsV2` | - | read |
| Get project for organization | `GET /orgs/{org}/projectsV2/{project_number}` | - | read |
| List projects for user | `GET /users/{username}/projectsV2` | - | read |
| Get project for user | `GET /users/{username}/projectsV2/{project_number}` | - | read |

#### projects / views (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create a view for an organization-owned project | `POST /orgs/{org}/projectsV2/{project_number}/views` | - | 1 |
| Create a view for a user-owned project | `POST /users/{user_id}/projectsV2/{project_number}/views` | - | 1 |

### REST: pulls (39 operations)

Home: Pull request sheet; PR review; Review and Review thread sheets. Coverage: in scope.

#### pulls / agent-merge (3)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Disable Agent Merge for a pull request | `DELETE /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | - | 3 |
| Get Agent Merge configuration for a pull request | `GET /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | - | read |
| Update Agent Merge configuration for a pull request | `PUT /agents/repos/{owner}/{repo}/pulls/{pull_number}/agent-merge` | - | 1 |

#### pulls / comments (7)

Home: Review thread sheet; PR review.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List review comments in a repository | `GET /repos/{owner}/{repo}/pulls/comments` | - | read |
| Delete a review comment for a pull request | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}` | - | 3 |
| Get a review comment for a pull request | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}` | - | read |
| Update a review comment for a pull request | `PATCH /repos/{owner}/{repo}/pulls/comments/{comment_id}` | - | 1 |
| List review comments on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/comments` | - | read |
| Create a review comment for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments` | - | 1 |
| Create a reply for a review comment | `POST /repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies` | - | 1 |

#### pulls / copilot-code-review (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Request a Copilot code review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/copilot-code-review` | - | 1 |

#### pulls / pulls (11)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List pull requests | `GET /repos/{owner}/{repo}/pulls` | - | read |
| Create a pull request | `POST /repos/{owner}/{repo}/pulls` | - | 1 |
| Get a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}` | - | read |
| Update a pull request | `PATCH /repos/{owner}/{repo}/pulls/{pull_number}` | - | 1 |
| List commits on a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits` | - | read |
| List pull requests files | `GET /repos/{owner}/{repo}/pulls/{pull_number}/files` | - | read |
| Check if a pull request has been merged | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge` | - | read |
| Merge a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge` | - | 1 |
| Merge a pull request asynchronously | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge-async` | - | 1 |
| Get the result of an asynchronous merge | `GET /repos/{owner}/{repo}/pulls/{pull_number}/merge-async/{uuid}` | - | read |
| Update a pull request branch | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/update-branch` | - | 1 |

#### pulls / review-requests (4)

Home: Pull request > Reviews: reviewers.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Remove requested reviewers from a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | - | 3 |
| Get all requested reviewers for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | - | read |
| Request reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers` | - | 1 |
| Rerequest reviewers for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers/rerequest` | - | 1 |

#### pulls / reviews (8)

Home: Pull request > Reviews; Review sheet.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List reviews for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | - | read |
| Create a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` | - | 1 |
| Delete a pending review for a pull request | `DELETE /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | - | 3 |
| Get a review for a pull request | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | - | read |
| Update a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}` | - | 1 |
| List comments for a pull request review | `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments` | - | read |
| Dismiss a review for a pull request | `PUT /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/dismissals` | - | 1 |
| Submit a review for a pull request | `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/events` | - | 1 |

#### pulls / stacks (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List pull request stacks | `GET /repos/{owner}/{repo}/stacks` | - | read |
| Create a pull request stack | `POST /repos/{owner}/{repo}/stacks` | - | 1 |
| Get a pull request stack | `GET /repos/{owner}/{repo}/stacks/{stack_number}` | - | read |
| Add pull requests to a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/add` | - | 1 |
| Remove pull requests from a pull request stack | `POST /repos/{owner}/{repo}/stacks/{stack_number}/unstack` | - | 1 |

### REST: rate-limit (1 operations)

Home: Account > GitHub API Rate Limit; status bar. Coverage: in scope.

#### rate-limit / rate-limit (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get rate limit status for the authenticated user | `GET /rate_limit` | - | read |

### REST: reactions (15 operations)

Home: You page on issues, pull requests, comments, discussions, releases (section 16.7). Coverage: in scope.

#### reactions / reactions (15)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List reactions for a commit comment | `GET /repos/{owner}/{repo}/comments/{comment_id}/reactions` | - | read |
| Create reaction for a commit comment | `POST /repos/{owner}/{repo}/comments/{comment_id}/reactions` | - | 1 |
| Delete a commit comment reaction | `DELETE /repos/{owner}/{repo}/comments/{comment_id}/reactions/{reaction_id}` | - | 3 |
| List reactions for an issue comment | `GET /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | - | read |
| Create reaction for an issue comment | `POST /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions` | - | 1 |
| Delete an issue comment reaction | `DELETE /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions/{reaction_id}` | - | 3 |
| List reactions for an issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/reactions` | - | read |
| Create reaction for an issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/reactions` | - | 1 |
| Delete an issue reaction | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/reactions/{reaction_id}` | - | 3 |
| List reactions for a pull request review comment | `GET /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | - | read |
| Create reaction for a pull request review comment | `POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions` | - | 1 |
| Delete a pull request comment reaction | `DELETE /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions/{reaction_id}` | - | 3 |
| List reactions for a release | `GET /repos/{owner}/{repo}/releases/{release_id}/reactions` | - | read |
| Create reaction for a release | `POST /repos/{owner}/{repo}/releases/{release_id}/reactions` | - | 1 |
| Delete a release reaction | `DELETE /repos/{owner}/{repo}/releases/{release_id}/reactions/{reaction_id}` | - | 3 |

### REST: releases (13 operations)

Home: Repository > Releases; Release and Release asset sheets. Coverage: in scope.

#### releases / assets (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete a release asset | `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` | - | 3 |
| Get a release asset | `GET /repos/{owner}/{repo}/releases/assets/{asset_id}` | - | read |
| Update a release asset | `PATCH /repos/{owner}/{repo}/releases/assets/{asset_id}` | - | 1 |
| List release assets | `GET /repos/{owner}/{repo}/releases/{release_id}/assets` | - | read |
| Upload a release asset | `POST /repos/{owner}/{repo}/releases/{release_id}/assets` | - | 1 |

#### releases / releases (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List releases | `GET /repos/{owner}/{repo}/releases` | - | read |
| Create a release | `POST /repos/{owner}/{repo}/releases` | `workflow` | 1 |
| Generate release notes content for a release | `POST /repos/{owner}/{repo}/releases/generate-notes` | - | 1 |
| Get the latest release | `GET /repos/{owner}/{repo}/releases/latest` | - | read |
| Get a release by tag name | `GET /repos/{owner}/{repo}/releases/tags/{tag}` | - | read |
| Delete a release | `DELETE /repos/{owner}/{repo}/releases/{release_id}` | - | 3 |
| Get a release | `GET /repos/{owner}/{repo}/releases/{release_id}` | - | read |
| Update a release | `PATCH /repos/{owner}/{repo}/releases/{release_id}` | `workflow` | 1 |

### REST: repos (73 operations)

Home: Repository sheet (General, Features, Merging, Webhooks, Autolinks, Rules, Pages, Security, Danger Zone); File and folder sheets. Coverage: in scope.

#### repos / attestations (2)

Home: Repository > Security > Attestations (read).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Create an attestation | `POST /repos/{owner}/{repo}/attestations` | - | 1 |
| List attestations | `GET /repos/{owner}/{repo}/attestations/{subject_digest}` | - | read |

#### repos / autolinks (4)

Home: Repository sheet > Autolinks.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all autolinks of a repository | `GET /repos/{owner}/{repo}/autolinks` | - | read |
| Create an autolink reference for a repository | `POST /repos/{owner}/{repo}/autolinks` | - | 2 |
| Delete an autolink reference from a repository | `DELETE /repos/{owner}/{repo}/autolinks/{autolink_id}` | - | 3 |
| Get an autolink reference of a repository | `GET /repos/{owner}/{repo}/autolinks/{autolink_id}` | - | read |

#### repos / contents (7)

Home: File and folder sheets; Commit to GitHub.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete a file | `DELETE /repos/{owner}/{repo}/contents/{path}` | - | 3 |
| Get repository content | `GET /repos/{owner}/{repo}/contents/{path}` | - | read |
| Create or update file contents | `PUT /repos/{owner}/{repo}/contents/{path}` | `repo` | 1 |
| Get a repository README | `GET /repos/{owner}/{repo}/readme` | - | read |
| Get a repository README for a directory | `GET /repos/{owner}/{repo}/readme/{dir}` | - | read |
| Download a repository archive (tar) | `GET /repos/{owner}/{repo}/tarball/{ref}` | - | read |
| Download a repository archive (zip) | `GET /repos/{owner}/{repo}/zipball/{ref}` | - | read |

#### repos / custom-properties (2)

Home: Repository sheet > General: Custom Properties.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get all custom property values for a repository | `GET /repos/{owner}/{repo}/properties/values` | - | read |
| Create or update custom property values for a repository | `PATCH /repos/{owner}/{repo}/properties/values` | - | 2 |

#### repos / forks (2)

Home: Repository > Fork; Repository > People > Forks.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List forks | `GET /repos/{owner}/{repo}/forks` | - | read |
| Create a fork | `POST /repos/{owner}/{repo}/forks` | - | 1 |

#### repos / issue-types (1)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List issue types for a repository | `GET /repos/{owner}/{repo}/issue-types` | `repo` | read |

#### repos / repos (33)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization repositories | `GET /orgs/{org}/repos` | - | read |
| Create an organization repository | `POST /orgs/{org}/repos` | `public_repo`, `repo` | 1 |
| Delete a repository | `DELETE /repos/{owner}/{repo}` | `delete_repo` | 3 |
| Get a repository | `GET /repos/{owner}/{repo}` | - | read |
| Update a repository | `PATCH /repos/{owner}/{repo}` | - | 1 |
| List repository activities | `GET /repos/{owner}/{repo}/activity` | - | read |
| Disable Dependabot security updates | `DELETE /repos/{owner}/{repo}/automated-security-fixes` | - | 3 |
| Check if Dependabot security updates are enabled for a repository | `GET /repos/{owner}/{repo}/automated-security-fixes` | - | read |
| Enable Dependabot security updates | `PUT /repos/{owner}/{repo}/automated-security-fixes` | - | 1 |
| List CODEOWNERS errors | `GET /repos/{owner}/{repo}/codeowners/errors` | - | read |
| List repository contributors | `GET /repos/{owner}/{repo}/contributors` | - | read |
| Create a repository dispatch event | `POST /repos/{owner}/{repo}/dispatches` | `repo` | 1 |
| Get the hash algorithm for a repository | `GET /repos/{owner}/{repo}/hash-algorithm` | - | read |
| Disable immutable releases | `DELETE /repos/{owner}/{repo}/immutable-releases` | - | 3 |
| Check if immutable releases are enabled for a repository | `GET /repos/{owner}/{repo}/immutable-releases` | - | read |
| Enable immutable releases | `PUT /repos/{owner}/{repo}/immutable-releases` | - | 1 |
| List repository languages | `GET /repos/{owner}/{repo}/languages` | - | read |
| Disable private vulnerability reporting for a repository | `DELETE /repos/{owner}/{repo}/private-vulnerability-reporting` | - | 3 |
| Check if private vulnerability reporting is enabled for a repository | `GET /repos/{owner}/{repo}/private-vulnerability-reporting` | - | read |
| Enable private vulnerability reporting for a repository | `PUT /repos/{owner}/{repo}/private-vulnerability-reporting` | - | 1 |
| List repository tags | `GET /repos/{owner}/{repo}/tags` | - | read |
| List repository teams | `GET /repos/{owner}/{repo}/teams` | `public_repo`, `repo` | read |
| Get all repository topics | `GET /repos/{owner}/{repo}/topics` | - | read |
| Replace all repository topics | `PUT /repos/{owner}/{repo}/topics` | - | 1 |
| Transfer a repository | `POST /repos/{owner}/{repo}/transfer` | - | 1 |
| Disable vulnerability alerts | `DELETE /repos/{owner}/{repo}/vulnerability-alerts` | - | 3 |
| Check if vulnerability alerts are enabled for a repository | `GET /repos/{owner}/{repo}/vulnerability-alerts` | - | read |
| Enable vulnerability alerts | `PUT /repos/{owner}/{repo}/vulnerability-alerts` | - | 1 |
| Create a repository using a template | `POST /repos/{template_owner}/{template_repo}/generate` | `public_repo`, `repo` | 1 |
| List public repositories | `GET /repositories` | - | read |
| List repositories for the authenticated user | `GET /user/repos` | - | read |
| Create a repository for the authenticated user | `POST /user/repos` | `public_repo`, `repo` | 1 |
| List repositories for a user | `GET /users/{username}/repos` | - | read |

#### repos / rule-suites (2)

Home: Ruleset sheet > History (rule insights).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository rule suites | `GET /repos/{owner}/{repo}/rulesets/rule-suites` | - | read |
| Get a repository rule suite | `GET /repos/{owner}/{repo}/rulesets/rule-suites/{rule_suite_id}` | - | read |

#### repos / rules (8)

Home: Ruleset sheet (section 18.3.1).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get rules for a branch | `GET /repos/{owner}/{repo}/rules/branches/{branch}` | - | read |
| Get all repository rulesets | `GET /repos/{owner}/{repo}/rulesets` | - | read |
| Create a repository ruleset | `POST /repos/{owner}/{repo}/rulesets` | - | 2 |
| Delete a repository ruleset | `DELETE /repos/{owner}/{repo}/rulesets/{ruleset_id}` | - | 3 |
| Get a repository ruleset | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}` | - | read |
| Update a repository ruleset | `PUT /repos/{owner}/{repo}/rulesets/{ruleset_id}` | - | 2 |
| Get repository ruleset history | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history` | - | read |
| Get repository ruleset version | `GET /repos/{owner}/{repo}/rulesets/{ruleset_id}/history/{version_id}` | - | read |

#### repos / webhooks (12)

Home: Repository sheet > Webhooks.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository webhooks | `GET /repos/{owner}/{repo}/hooks` | - | read |
| Create a repository webhook | `POST /repos/{owner}/{repo}/hooks` | - | 2 |
| Delete a repository webhook | `DELETE /repos/{owner}/{repo}/hooks/{hook_id}` | - | 3 |
| Get a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}` | - | read |
| Update a repository webhook | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}` | - | 2 |
| Get a webhook configuration for a repository | `GET /repos/{owner}/{repo}/hooks/{hook_id}/config` | `read:repo_hook`, `repo` | read |
| Update a webhook configuration for a repository | `PATCH /repos/{owner}/{repo}/hooks/{hook_id}/config` | `write:repo_hook`, `repo` | 2 |
| List deliveries for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries` | - | read |
| Get a delivery for a repository webhook | `GET /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}` | - | read |
| Redeliver a delivery for a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/deliveries/{delivery_id}/attempts` | - | 2 |
| Ping a repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/pings` | - | 2 |
| Test the push repository webhook | `POST /repos/{owner}/{repo}/hooks/{hook_id}/tests` | - | 2 |

### REST: search (7 operations)

Home: Search branch; filter box (section 17). Coverage: in scope.

#### search / search (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Search code | `GET /search/code` | - | read |
| Search commits | `GET /search/commits` | - | read |
| Search issues and pull requests | `GET /search/issues` | - | read |
| Search labels | `GET /search/labels` | - | read |
| Search repositories | `GET /search/repositories` | - | read |
| Search topics | `GET /search/topics` | - | read |
| Search users | `GET /search/users` | - | read |

### REST: secret-scanning (17 operations)

Home: Repository > Security > Alerts (Kind: secret scanning); bypass requests (section 22.1). Coverage: in scope.

#### secret-scanning / custom-patterns (8)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Bulk delete organization custom patterns | `DELETE /orgs/{org}/secret-scanning/custom-patterns` | `write:org` | 3 |
| List organization custom patterns | `GET /orgs/{org}/secret-scanning/custom-patterns` | `read:org` | read |
| Bulk create organization custom patterns | `POST /orgs/{org}/secret-scanning/custom-patterns` | `write:org` | 1 |
| Update an organization custom pattern | `PATCH /orgs/{org}/secret-scanning/custom-patterns/{pattern_id}` | `write:org` | 1 |
| Bulk delete repository custom patterns | `DELETE /repos/{owner}/{repo}/secret-scanning/custom-patterns` | `repo` | 3 |
| List repository custom patterns | `GET /repos/{owner}/{repo}/secret-scanning/custom-patterns` | `repo` | read |
| Bulk create repository custom patterns | `POST /repos/{owner}/{repo}/secret-scanning/custom-patterns` | `repo` | 1 |
| Update a repository custom pattern | `PATCH /repos/{owner}/{repo}/secret-scanning/custom-patterns/{pattern_id}` | `repo` | 1 |

#### secret-scanning / push-protection (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List organization pattern configurations | `GET /orgs/{org}/secret-scanning/pattern-configurations` | `read:org` | read |
| Update organization pattern configurations | `PATCH /orgs/{org}/secret-scanning/pattern-configurations` | `write:org` | 1 |

#### secret-scanning / secret-scanning (7)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List secret scanning alerts for an organization | `GET /orgs/{org}/secret-scanning/alerts` | `repo`, `security_events` | read |
| List secret scanning alerts for a repository | `GET /repos/{owner}/{repo}/secret-scanning/alerts` | `repo`, `security_events` | read |
| Get a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | `repo`, `security_events` | read |
| Update a secret scanning alert | `PATCH /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}` | `repo`, `security_events` | 1 |
| List locations for a secret scanning alert | `GET /repos/{owner}/{repo}/secret-scanning/alerts/{alert_number}/locations` | `repo`, `security_events` | read |
| Create a push protection bypass | `POST /repos/{owner}/{repo}/secret-scanning/push-protection-bypasses` | `repo` | 1 |
| Get secret scanning scan history for a repository | `GET /repos/{owner}/{repo}/secret-scanning/scan-history` | `repo`, `security_events` | read |

### REST: security-advisories (14 operations)

Home: Repository > Security > Advisories; Advisory sheet. Coverage: in scope.

#### security-advisories / global-advisories (2)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List global security advisories | `GET /advisories` | - | read |
| Get a global security advisory | `GET /advisories/{ghsa_id}` | - | read |

#### security-advisories / repository-advisories (12)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List repository security advisories for an organization | `GET /orgs/{org}/security-advisories` | `repo`, `repository_advisories:write` | read |
| List repository security advisories | `GET /repos/{owner}/{repo}/security-advisories` | `repo`, `repository_advisories:read` | read |
| Create a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories` | `repo`, `repository_advisories:write` | 1 |
| Privately report a security vulnerability | `POST /repos/{owner}/{repo}/security-advisories/reports` | - | 1 |
| Get a repository security advisory | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | `repo`, `repository_advisories:read` | read |
| Update a repository security advisory | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}` | `repo`, `repository_advisories:write` | 1 |
| List repository security advisory comments | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | - | read |
| Create a repository advisory comment | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments` | - | 1 |
| Get a repository advisory comment | `GET /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | `repo`, `repository_advisories:read` | read |
| Update a repository advisory comment | `PATCH /repos/{owner}/{repo}/security-advisories/{ghsa_id}/comments/{comment_id}` | `repo`, `repository_advisories:write` | 1 |
| Request a CVE for a repository security advisory | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/cve` | `repo`, `repository_advisories:write` | 1 |
| Create a temporary private fork | `POST /repos/{owner}/{repo}/security-advisories/{ghsa_id}/forks` | - | 1 |

### REST: teams (32 operations)

Home: Team sheet; Organization sheet > Teams. Coverage: in scope.

#### teams / members (13)

Home: Team sheet > Members.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List pending team invitations | `GET /orgs/{org}/teams/{team_slug}/invitations` | - | read |
| List team members | `GET /orgs/{org}/teams/{team_slug}/members` | - | read |
| Remove team membership for a user | `DELETE /orgs/{org}/teams/{team_slug}/memberships/{username}` | - | 3 |
| Get team membership for a user | `GET /orgs/{org}/teams/{team_slug}/memberships/{username}` | - | read |
| Add or update team membership for a user | `PUT /orgs/{org}/teams/{team_slug}/memberships/{username}` | - | 2 |
| List pending team invitations (Legacy) | `GET /teams/{team_id}/invitations` | - | read |
| List team members (Legacy) | `GET /teams/{team_id}/members` | - | read |
| Remove team member (Legacy) | `DELETE /teams/{team_id}/members/{username}` | - | 3 |
| Get team member (Legacy) | `GET /teams/{team_id}/members/{username}` | - | read |
| Add team member (Legacy) | `PUT /teams/{team_id}/members/{username}` | - | 2 |
| Remove team membership for a user (Legacy) | `DELETE /teams/{team_id}/memberships/{username}` | - | 3 |
| Get team membership for a user (Legacy) | `GET /teams/{team_id}/memberships/{username}` | - | read |
| Add or update team membership for a user (Legacy) | `PUT /teams/{team_id}/memberships/{username}` | - | 2 |

#### teams / teams (19)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List teams | `GET /orgs/{org}/teams` | - | read |
| Create a team | `POST /orgs/{org}/teams` | - | 2 |
| Delete a team | `DELETE /orgs/{org}/teams/{team_slug}` | - | 3 |
| Get a team by name | `GET /orgs/{org}/teams/{team_slug}` | - | read |
| Update a team | `PATCH /orgs/{org}/teams/{team_slug}` | - | 2 |
| List team repositories | `GET /orgs/{org}/teams/{team_slug}/repos` | `read:org`, `repo` | read |
| Remove a repository from a team | `DELETE /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | - | 3 |
| Check team permissions for a repository | `GET /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | - | read |
| Add or update team repository permissions | `PUT /orgs/{org}/teams/{team_slug}/repos/{owner}/{repo}` | - | 2 |
| List child teams | `GET /orgs/{org}/teams/{team_slug}/teams` | - | read |
| Delete a team (Legacy) | `DELETE /teams/{team_id}` | - | 3 |
| Get a team (Legacy) | `GET /teams/{team_id}` | - | read |
| Update a team (Legacy) | `PATCH /teams/{team_id}` | - | 2 |
| List team repositories (Legacy) | `GET /teams/{team_id}/repos` | - | read |
| Remove a repository from a team (Legacy) | `DELETE /teams/{team_id}/repos/{owner}/{repo}` | - | 3 |
| Check team permissions for a repository (Legacy) | `GET /teams/{team_id}/repos/{owner}/{repo}` | - | read |
| Add or update team repository permissions (Legacy) | `PUT /teams/{team_id}/repos/{owner}/{repo}` | - | 2 |
| List child teams (Legacy) | `GET /teams/{team_id}/teams` | - | read |
| List teams for the authenticated user | `GET /user/teams` | - | read |

### REST: users (47 operations)

Home: Person sheet; Account > Profile and Status, Keys, Emails; People branch. Coverage: in scope.

#### users / attestations (5)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List attestations by bulk subject digests | `POST /users/{username}/attestations/bulk-list` | - | 1 |
| Delete attestations in bulk | `POST /users/{username}/attestations/delete-request` | - | 1 |
| Delete attestations by subject digest | `DELETE /users/{username}/attestations/digest/{subject_digest}` | - | 3 |
| Delete attestations by ID | `DELETE /users/{username}/attestations/{attestation_id}` | - | 3 |
| List attestations | `GET /users/{username}/attestations/{subject_digest}` | - | read |

#### users / blocking (4)

Home: Person > You: Block (section 16.7).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List users blocked by the authenticated user | `GET /user/blocks` | - | read |
| Unblock a user | `DELETE /user/blocks/{username}` | - | 3 |
| Check if a user is blocked by the authenticated user | `GET /user/blocks/{username}` | - | read |
| Block a user | `PUT /user/blocks/{username}` | - | 2 |

#### users / emails (5)

Home: Account > Profile and Status: Emails.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Set primary email visibility for the authenticated user | `PATCH /user/email/visibility` | - | 1 |
| Delete an email address for the authenticated user | `DELETE /user/emails` | `user` | 3 |
| List email addresses for the authenticated user | `GET /user/emails` | `user:email` | read |
| Add an email address for the authenticated user | `POST /user/emails` | `user` | 1 |
| List public email addresses for the authenticated user | `GET /user/public_emails` | `user:email` | read |

#### users / followers (8)

Home: Person > You: Follow (section 16.7).

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List followers of the authenticated user | `GET /user/followers` | - | read |
| List the people the authenticated user follows | `GET /user/following` | - | read |
| Unfollow a user | `DELETE /user/following/{username}` | `user:follow` | 3 |
| Check if a person is followed by the authenticated user | `GET /user/following/{username}` | - | read |
| Follow a user | `PUT /user/following/{username}` | `user:follow` | 1 |
| List followers of a user | `GET /users/{username}/followers` | - | read |
| List the people a user follows | `GET /users/{username}/following` | - | read |
| Check if a user follows another user | `GET /users/{username}/following/{target_user}` | - | read |

#### users / gpg-keys (5)

Home: Account > Keys.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List GPG keys for the authenticated user | `GET /user/gpg_keys` | `read:gpg_key` | read |
| Create a GPG key for the authenticated user | `POST /user/gpg_keys` | `write:gpg_key` | 1 |
| Delete a GPG key for the authenticated user | `DELETE /user/gpg_keys/{gpg_key_id}` | `admin:gpg_key` | 3 |
| Get a GPG key for the authenticated user | `GET /user/gpg_keys/{gpg_key_id}` | `read:gpg_key` | read |
| List GPG keys for a user | `GET /users/{username}/gpg_keys` | - | read |

#### users / keys (5)

Home: Account > Keys.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List public SSH keys for the authenticated user | `GET /user/keys` | `read:public_key` | read |
| Create a public SSH key for the authenticated user | `POST /user/keys` | `write:public_key` | 1 |
| Delete a public SSH key for the authenticated user | `DELETE /user/keys/{key_id}` | `admin:public_key` | 3 |
| Get a public SSH key for the authenticated user | `GET /user/keys/{key_id}` | `read:public_key` | read |
| List public keys for a user | `GET /users/{username}/keys` | - | read |

#### users / social-accounts (4)

Home: Account > Profile and Status: Social accounts.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Delete social accounts for the authenticated user | `DELETE /user/social_accounts` | `user` | 3 |
| List social accounts for the authenticated user | `GET /user/social_accounts` | - | read |
| Add social accounts for the authenticated user | `POST /user/social_accounts` | `user` | 1 |
| List social accounts for a user | `GET /users/{username}/social_accounts` | - | read |

#### users / ssh-signing-keys (5)

Home: Account > Keys.

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| List SSH signing keys for the authenticated user | `GET /user/ssh_signing_keys` | `read:ssh_signing_key` | read |
| Create a SSH signing key for the authenticated user | `POST /user/ssh_signing_keys` | `write:ssh_signing_key` | 1 |
| Delete an SSH signing key for the authenticated user | `DELETE /user/ssh_signing_keys/{ssh_signing_key_id}` | `admin:ssh_signing_key` | 3 |
| Get an SSH signing key for the authenticated user | `GET /user/ssh_signing_keys/{ssh_signing_key_id}` | `read:ssh_signing_key` | read |
| List SSH signing keys for a user | `GET /users/{username}/ssh_signing_keys` | - | read |

#### users / users (6)

| Operation | Call | Classic scope | Tier |
|---|---|---|---|
| Get the authenticated user | `GET /user` | `read:user` | read |
| Update the authenticated user | `PATCH /user` | - | 1 |
| Get a user using their ID | `GET /user/{account_id}` | - | read |
| List users | `GET /users` | - | read |
| Get a user | `GET /users/{username}` | - | read |
| Get contextual information for a user | `GET /users/{username}/hovercard` | `repo` | read |

## Appendix F: the GraphQL API, every mutation and every viewer answer

Generated from GitHub's public GraphQL schema (`schema.docs.graphql`), read 2026-11-09: **284 mutations in 22 categories**, and **42 types** that tell the signed-in person what they may do. GraphQL is the only API for several things the Workbench needs: Projects (version 2) fields and views, Discussions, sub-issue order, issue types on items, pinned items, minimizing comments, merge queue entries, and most of Sponsors.

### F.1 What you may do: the viewer fields, by type

These are what section 18.2 fetches with each object, so a menu row or sheet field is greyed with a reason instead of failing. One line per type.

| Type | Fields |
|---|---|
| Assignable | `viewerCanAssign` |
| Closable | `viewerCanClose`, `viewerCanReopen` |
| Commit | `viewerCanSubscribe`, `viewerSubscription` |
| CommitComment | `viewerCanDelete`, `viewerCanMinimize`, `viewerCanReact`, `viewerCanUnminimize`, `viewerCanUpdate`, `viewerCannotUpdateReasons` |
| Deletable | `viewerCanDelete` |
| Discussion | `viewerCanClose`, `viewerCanDelete`, `viewerCanLabel`, `viewerCanReact`, `viewerCanReopen`, `viewerCanSubscribe`, `viewerCanUpdate`, `viewerCanUpvote`, `viewerSubscription` |
| DiscussionComment | `viewerCanDelete`, `viewerCanMarkAsAnswer`, `viewerCanMinimize`, `viewerCanReact`, `viewerCanUnmarkAsAnswer`, `viewerCanUnminimize`, `viewerCanUpdate`, `viewerCanUpvote`, `viewerCannotUpdateReasons` |
| DiscussionPoll | `viewerCanVote` |
| EnterpriseTeam | `viewerCanAdminister` |
| Gist | `viewerHasStarred` |
| GistComment | `viewerCanDelete`, `viewerCanMinimize`, `viewerCanUnminimize`, `viewerCanUpdate`, `viewerCannotUpdateReasons` |
| Issue | `viewerCanAssign`, `viewerCanClose`, `viewerCanDelete`, `viewerCanLabel`, `viewerCanReact`, `viewerCanReopen`, `viewerCanSetFields`, `viewerCanSetMilestone`, `viewerCanSubscribe`, `viewerCanType`, `viewerCanUpdate`, `viewerCanUpdateMetadata`, `viewerCannotUpdateReasons`, `viewerSubscription` |
| IssueComment | `viewerCanDelete`, `viewerCanMinimize`, `viewerCanPin`, `viewerCanReact`, `viewerCanUnminimize`, `viewerCanUnpin`, `viewerCanUpdate`, `viewerCannotUpdateReasons` |
| Labelable | `viewerCanLabel` |
| MarketplaceListing | `viewerCanAddPlans`, `viewerCanApprove`, `viewerCanDelist`, `viewerCanEdit`, `viewerCanEditCategories`, `viewerCanEditPlans`, `viewerCanRedraft`, `viewerCanReject`, `viewerCanRequestApproval` |
| Milestone | `viewerCanClose`, `viewerCanReopen` |
| Minimizable | `viewerCanMinimize`, `viewerCanUnminimize` |
| Organization | `viewerCanAdminister`, `viewerCanChangePinnedItems`, `viewerCanCreateProjects`, `viewerCanCreateRepositories`, `viewerCanCreateTeams`, `viewerCanSponsor`, `viewerIsFollowing`, `viewerIsSponsoring` |
| Pinnable | `viewerCanPin`, `viewerCanUnpin` |
| ProfileOwner | `viewerCanChangePinnedItems` |
| Project | `viewerCanClose`, `viewerCanReopen`, `viewerCanUpdate` |
| ProjectOwner | `viewerCanCreateProjects` |
| ProjectV2 | `viewerCanClose`, `viewerCanReopen`, `viewerCanUpdate` |
| PullRequest | `viewerCanApplySuggestion`, `viewerCanAssign`, `viewerCanClose`, `viewerCanDeleteHeadRef`, `viewerCanDisableAutoMerge`, `viewerCanEditFiles`, `viewerCanEnableAutoMerge`, `viewerCanLabel`, `viewerCanMergeAsAdmin`, `viewerCanReact`, `viewerCanReopen`, `viewerCanSubscribe`, `viewerCanUpdate`, `viewerCanUpdateBranch`, `viewerCannotUpdateReasons`, `viewerSubscription` |
| PullRequestReview | `viewerCanDelete`, `viewerCanMinimize`, `viewerCanReact`, `viewerCanUnminimize`, `viewerCanUpdate`, `viewerCannotUpdateReasons` |
| PullRequestReviewComment | `viewerCanDelete`, `viewerCanMinimize`, `viewerCanReact`, `viewerCanUnminimize`, `viewerCanUpdate`, `viewerCannotUpdateReasons` |
| PullRequestReviewThread | `viewerCanReply`, `viewerCanResolve`, `viewerCanUnresolve` |
| PullRequestThread | `viewerCanReply`, `viewerCanResolve`, `viewerCanUnresolve` |
| Reactable | `viewerCanReact` |
| RefUpdateRule | `viewerCanPush` |
| Release | `viewerCanReact` |
| Repository | `viewerCanAdminister`, `viewerCanCreateIssues`, `viewerCanCreateProjects`, `viewerCanSeeIssueFields`, `viewerCanSubscribe`, `viewerCanUpdateTopics`, `viewerHasStarred`, `viewerPermission`, `viewerSubscription` |
| Sponsorable | `viewerCanSponsor`, `viewerIsSponsoring` |
| Starrable | `viewerHasStarred` |
| Subscribable | `viewerCanSubscribe`, `viewerSubscription` |
| Team | `viewerCanAdminister`, `viewerCanSubscribe`, `viewerSubscription` |
| Topic | `viewerHasStarred` |
| Updatable | `viewerCanUpdate` |
| UpdatableComment | `viewerCannotUpdateReasons` |
| User | `viewerCanChangePinnedItems`, `viewerCanCreateProjects`, `viewerCanFollow`, `viewerCanSponsor`, `viewerIsFollowing`, `viewerIsSponsoring` |
| Votable | `viewerCanUpvote` |
| WorkflowRunFile | `viewerCanPushRepository`, `viewerCanReadRepository` |

### F.2 Mutations, by category

#### GraphQL: activity (4 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addStar` | Adds a star to a Starrable. |
| `removeStar` | Removes a star from a Starrable. |
| `updateNotificationRestrictionSetting` | Update the setting to restrict notifications to only verified or approved domains available to an owner. |
| `updateSubscription` | Updates the state for subscribable subjects. |

#### GraphQL: branches (4 mutations, in scope)

| Mutation | What it does |
|---|---|
| `createBranchProtectionRule` | Create a new branch protection rule |
| `deleteBranchProtectionRule` | Delete a branch protection rule |
| `mergeBranch` | Merge a head into a branch. |
| `updateBranchProtectionRule` | Update a branch protection rule |

#### GraphQL: checks (5 mutations, in scope)

| Mutation | What it does |
|---|---|
| `createCheckRun` | Create a check run. |
| `createCheckSuite` | Create a check suite |
| `rerequestCheckSuite` | Rerequests an existing check suite. |
| `updateCheckRun` | Update a check run |
| `updateCheckSuitePreferences` | Modifies the settings of an existing check suite |

#### GraphQL: commits (1 mutations, in scope)

| Mutation | What it does |
|---|---|
| `createCommitOnBranch` | Appends a commit to the given branch as the authenticated user.  This mutation creates a commit whose parent is the HEAD of the provided branch and also updates that branch to point to the new commit. It can be thought of as similar to `git commit`.  ### Locating a Branch  Commits are appended to a `branch` of type `Ref`. This must refer to a git branch (i.e.  the fully qualified path must begin with `refs/heads/`, although including this prefix is optional.  Callers may specify the `branch` to commit to either by its global node ID or by passing both of `repositoryNameWithOwner` and `refName`.  For more details see the documentation for `CommittableBranch`.  ### Describing Changes  `fileChanges` are specified as a `FilesChanges` object describing `FileAdditions` and `FileDeletions`.  Please see the documentation for `FileChanges` for more information on how to use this argument to describe any set of file changes.  ### Authorship  Similar to the web commit interface, this mutation does not support specifying the author or committer of the commit and will not add support for this in the future.  A commit created by a successful execution of this mutation will be authored by the owner of the credential which authenticates the API request.  The committer will be identical to that of commits authored using the web interface.  If you need full control over author and committer information, please use the Git Database REST API instead.  ### Commit Signing  Commits made using this mutation are automatically signed by GitHub if supported and will be marked as verified in the user interface. |

#### GraphQL: copilot (5 mutations, in scope)

| Mutation | What it does |
|---|---|
| `updateEnterpriseCopilotCodeReviewPolicy` | Updates an enterprise's Copilot code review policy using the existing policy propagation and notification behavior. |
| `updateOrganizationCopilotCodeReviewPolicy` | Updates an organization's Copilot code review policy when the enterprise delegates control to organization administrators. |
| `updateOrganizationCopilotCodeReviewRunnerConfiguration` | Sets the runner configuration that Copilot code review uses for an organization. A LABELED runner requires at least one label or a runner group. Invalid input does not change the configuration. |
| `updateOrganizationCopilotCodeReviewSettings` | Updates an organization's Copilot code review settings. Omitted settings are not changed. |
| `updateRepositoryCopilotCodeReviewSettings` | Updates a repository's Copilot code review settings. Omitted settings are not changed. |

#### GraphQL: dependabot (1 mutations, in scope)

| Mutation | What it does |
|---|---|
| `dismissRepositoryVulnerabilityAlert` | Dismisses the Dependabot alert. |

#### GraphQL: deployments (10 mutations, in scope)

| Mutation | What it does |
|---|---|
| `approveDeployments` | Approve all pending deployments under one or more environments |
| `createDeployment` | Creates a new deployment event. |
| `createDeploymentStatus` | Create a deployment status. |
| `createEnvironment` | Creates an environment or simply returns it if already exists. |
| `deleteDeployment` | Deletes a deployment. |
| `deleteEnvironment` | Deletes an environment |
| `pinEnvironment` | Pin an environment to a repository |
| `rejectDeployments` | Reject all pending deployments under one or more environments |
| `reorderEnvironment` | Reorder a pinned repository environment |
| `updateEnvironment` | Updates an environment. |

#### GraphQL: discussions (13 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addDiscussionComment` | Adds a comment to a Discussion, possibly as a reply to another comment. |
| `addDiscussionPollVote` | Vote for an option in a discussion poll. |
| `addUpvote` | Add an upvote to a discussion or discussion comment. |
| `closeDiscussion` | Close a discussion. |
| `createDiscussion` | Create a discussion. |
| `deleteDiscussion` | Delete a discussion and all of its replies. |
| `deleteDiscussionComment` | Delete a discussion comment. If it has replies, wipe it instead. |
| `markDiscussionCommentAsAnswer` | Mark a discussion comment as the chosen answer for discussions in an answerable category. |
| `removeUpvote` | Remove an upvote to a discussion or discussion comment. |
| `reopenDiscussion` | Reopen a discussion. |
| `unmarkDiscussionCommentAsAnswer` | Unmark a discussion comment as the chosen answer for discussions in an answerable category. |
| `updateDiscussion` | Update a discussion |
| `updateDiscussionComment` | Update the contents of a comment on a Discussion |

#### GraphQL: enterprise-admin (44 mutations, out of scope: enterprise and migration administration)

| Mutation | What it does |
|---|---|
| `acceptEnterpriseAdministratorInvitation` | Accepts a pending invitation for a user to become an administrator of an enterprise. |
| `acceptEnterpriseMemberInvitation` | Accepts a pending invitation for a user to become an unaffiliated member of an enterprise. |
| `accessUserNamespaceRepository` | Access user namespace repository for a temporary duration. |
| `addEnterpriseOrganizationMember` | Adds enterprise members to an organization within the enterprise. |
| `addEnterpriseSupportEntitlement` | Adds a support entitlement to an enterprise member. |
| `cancelEnterpriseAdminInvitation` | Cancels a pending invitation for an administrator to join an enterprise. |
| `cancelEnterpriseMemberInvitation` | Cancels a pending invitation for an unaffiliated member to join an enterprise. |
| `createEnterpriseOrganization` | Creates an organization as part of an enterprise account. User-authenticated requests make the viewer an owner. Users listed in `adminLogins` are invited as owners unless owner invitations are disabled, in which case they are added directly. Installation requests also add existing enterprise members directly. Invitation failures do not roll back organization creation. A personal access token used to create an organization is implicitly permitted to update the organization it created, if the organization is part of an enterprise that has SAML enabled or uses Enterprise Managed Users. If the organization is not part of such an enterprise, and instead has SAML enabled for it individually, the token will then require SAML authorization to continue working against that organization. |
| `createIpAllowListEntry` | Creates a new IP allow list entry. |
| `deleteIpAllowListEntry` | Deletes an IP allow list entry. |
| `grantEnterpriseOrganizationsMigratorRole` | Grant the migrator role to a user for all organizations under an enterprise account. |
| `inviteEnterpriseAdmin` | Invite someone to become an administrator of the enterprise. |
| `inviteEnterpriseMember` | Invite someone to become an unaffiliated member of the enterprise. |
| `regenerateEnterpriseIdentityProviderRecoveryCodes` | Regenerates the identity provider recovery codes for an enterprise |
| `removeEnterpriseAdmin` | Removes an administrator from the enterprise. |
| `removeEnterpriseIdentityProvider` | Removes the identity provider from an enterprise. Owners of enterprises both with and without Enterprise Managed Users may use this mutation. |
| `removeEnterpriseMember` | Completely removes a user from the enterprise asynchronously. |
| `removeEnterpriseOrganization` | Removes an organization from the enterprise |
| `removeEnterpriseSupportEntitlement` | Removes a support entitlement from an enterprise member. |
| `revokeEnterpriseOrganizationsMigratorRole` | Revoke the migrator role to a user for all organizations under an enterprise account. |
| `setEnterpriseIdentityProvider` | Creates or updates the identity provider for an enterprise. |
| `transferEnterpriseOrganization` | Transfer an organization from one enterprise to another enterprise. |
| `updateEnterpriseAdministratorRole` | Updates the role of an enterprise administrator. |
| `updateEnterpriseAllowPrivateRepositoryForkingSetting` | Sets whether private repository forks are enabled for an enterprise. |
| `updateEnterpriseDefaultRepositoryPermissionSetting` | Sets the base repository permission for organizations in an enterprise. |
| `updateEnterpriseDeployKeySetting` | Sets whether deploy keys are allowed to be created and used for an enterprise. |
| `updateEnterpriseMembersCanChangeRepositoryVisibilitySetting` | Sets whether organization members with admin permissions on a repository can change repository visibility. |
| `updateEnterpriseMembersCanCreateRepositoriesSetting` | Sets the members can create repositories setting for an enterprise. |
| `updateEnterpriseMembersCanDeleteIssuesSetting` | Sets the members can delete issues setting for an enterprise. |
| `updateEnterpriseMembersCanDeleteRepositoriesSetting` | Sets the members can delete repositories setting for an enterprise. |
| `updateEnterpriseMembersCanInviteCollaboratorsSetting` | Sets whether members can invite collaborators are enabled for an enterprise. |
| `updateEnterpriseMembersCanMakePurchasesSetting` | Sets whether or not an organization owner can make purchases. |
| `updateEnterpriseMembersCanUpdateProtectedBranchesSetting` | Sets the members can update protected branches setting for an enterprise. |
| `updateEnterpriseMembersCanViewDependencyInsightsSetting` | Sets the members can view dependency insights for an enterprise. |
| `updateEnterpriseOrganizationProjectsSetting` | Sets whether organization projects are enabled for an enterprise. |
| `updateEnterpriseOwnerOrganizationRole` | Updates the role of an enterprise owner with an organization. |
| `updateEnterpriseProfile` | Updates an enterprise's profile. |
| `updateEnterpriseRepositoryProjectsSetting` | Sets whether repository projects are enabled for a enterprise. |
| `updateEnterpriseTwoFactorAuthenticationDisallowedMethodsSetting` | Sets the two-factor authentication methods that users of an enterprise may not use. |
| `updateEnterpriseTwoFactorAuthenticationRequiredSetting` | Sets whether two factor authentication is required for all users in an enterprise. |
| `updateIpAllowListEnabledSetting` | Sets whether an IP allow list is enabled on an owner. |
| `updateIpAllowListEntry` | Updates an IP allow list entry. |
| `updateIpAllowListForInstalledAppsEnabledSetting` | Sets whether IP allow list configuration for installed GitHub Apps is enabled on an owner. |
| `updateIpAllowListUserLevelEnforcementEnabledSetting` | Sets whether IP allow list user-level enforcement is enabled on an enterprise. |

#### GraphQL: git (4 mutations, in scope)

| Mutation | What it does |
|---|---|
| `createRef` | Create a new Git Ref. |
| `deleteRef` | Delete a Git Ref. |
| `updateRef` | Update a Git Ref. |
| `updateRefs` | Creates, updates and/or deletes multiple refs in a repository.  This mutation takes a list of `RefUpdate`s and performs these updates on the repository. All updates are performed atomically, meaning that if one of them is rejected, no other ref will be modified.  `RefUpdate.beforeOid` specifies that the given reference needs to point to the given value before performing any updates. A value of `0000000000000000000000000000000000000000` can be used to verify that the references should not exist.  `RefUpdate.afterOid` specifies the value that the given reference will point to after performing all updates. A value of `0000000000000000000000000000000000000000` can be used to delete a reference.  If `RefUpdate.force` is set to `true`, a non-fast-forward updates for the given reference will be allowed. |

#### GraphQL: issues (51 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addAssigneesToAssignable` | Adds assignees to an assignable object. |
| `addBlockedBy` | Adds a 'blocked by' relationship to an issue. |
| `addCloseIssueReferences` | Adds one or more pull requests as manually linked closing references on an issue. The target must be an issue, not a pull request. |
| `addComment` | Adds a comment to an Issue or Pull Request. |
| `addLabelsToLabelable` | Adds labels to a labelable object. |
| `addRelatesTo` | Adds a 'relates to' relationship between two issues. |
| `addSubIssue` | Adds a sub-issue to a given issue |
| `applyPendingIssueSuggestions` | Applies a batch of pending issue suggestions to an issue. |
| `clearLabelsFromLabelable` | Clears all labels from a labelable object. |
| `closeIssue` | Close an issue. |
| `createIssue` | Creates a new issue. |
| `createIssueField` | Creates a new issue field. |
| `createIssueFieldValue` | Creates a new issue field value for an issue. |
| `createIssueType` | Creates a new issue type |
| `createLabel` | Creates a new label. |
| `createLinkedBranch` | Create a branch linked to an issue. |
| `deleteIssue` | Deletes an Issue object. |
| `deleteIssueComment` | Deletes an IssueComment object. |
| `deleteIssueField` | Deletes an issue field. |
| `deleteIssueFieldValue` | Deletes an issue field value from an issue. |
| `deleteIssueType` | Delete an issue type |
| `deleteLabel` | Deletes a label. |
| `deleteLinkedBranch` | Unlink a branch from an issue. |
| `lockLockable` | Lock a lockable object |
| `minimizeComment` | Minimizes a comment on an Issue, Commit, Pull Request, or Gist |
| `pinIssue` | Pin an issue to a repository |
| `pinIssueComment` | Pins an Issue Comment. |
| `rejectPendingIssueSuggestions` | Rejects a batch of pending issue suggestions on an issue atomically. |
| `removeAssigneesFromAssignable` | Removes assignees from an assignable object. |
| `removeBlockedBy` | Removes a 'blocked by' relationship from an issue. |
| `removeCloseIssueReferences` | Removes one or more manually linked pull requests from an issue. Auto-detected closing references from pull request body keywords are not removed; edit the pull request body instead. |
| `removeLabelsFromLabelable` | Removes labels from a Labelable object. |
| `removeRelatesTo` | Removes a 'relates to' relationship between two issues. |
| `removeSubIssue` | Removes a sub-issue from a given issue |
| `reopenIssue` | Reopen a issue. |
| `replaceActorsForAssignable` | Replaces all actors for assignable object. |
| `reprioritizeSubIssue` | Reprioritizes a sub-issue to a different position in the parent list. |
| `setIssueFieldValue` | Sets the value of an IssueFieldValue. |
| `transferIssue` | Transfer an issue to a different repository |
| `unlockLockable` | Unlock a lockable object |
| `unmarkIssueAsDuplicate` | Unmark an issue as a duplicate of another issue. |
| `unminimizeComment` | Unminimizes a comment on an Issue, Commit, Pull Request, or Gist |
| `unpinIssue` | Unpin a pinned issue from a repository |
| `unpinIssueComment` | Unpins an Issue Comment. |
| `updateIssue` | Updates an Issue. |
| `updateIssueComment` | Updates an IssueComment object. |
| `updateIssueField` | Updates an issue field. |
| `updateIssueFieldValue` | Updates an existing issue field value for an issue. |
| `updateIssueIssueType` | Updates the issue type on an issue |
| `updateIssueType` | Update an issue type |
| `updateLabel` | Updates an existing label. |

#### GraphQL: migrations (8 mutations, out of scope: enterprise and migration administration)

| Mutation | What it does |
|---|---|
| `abortQueuedMigrations` | Clear all of a customer's queued migrations |
| `abortRepositoryMigration` | Abort a repository migration queued or in progress. |
| `createAttributionInvitation` | Invites a user to claim reattributable data |
| `createMigrationSource` | Creates a GitHub Enterprise Importer (GEI) migration source. |
| `grantMigratorRole` | Grant the migrator role to a user or a team. |
| `revokeMigratorRole` | Revoke the migrator role from a user or a team. |
| `startOrganizationMigration` | Starts a GitHub Enterprise Importer organization migration. |
| `startRepositoryMigration` | Starts a GitHub Enterprise Importer (GEI) repository migration. |

#### GraphQL: orgs (11 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addVerifiableDomain` | Adds a verifiable domain to an owning account. |
| `approveVerifiableDomain` | Approve a verifiable domain for notification delivery. |
| `deleteVerifiableDomain` | Deletes a verifiable domain. |
| `followOrganization` | Follow an organization. |
| `regenerateVerifiableDomainToken` | Regenerates a verifiable domain's verification token. |
| `removeOutsideCollaborator` | Removes outside collaborator from all repositories in an organization. |
| `setOrganizationInteractionLimit` | Set an organization level interaction limit for an organization's public repositories. |
| `unfollowOrganization` | Unfollow an organization. |
| `updateOrganizationAllowPrivateRepositoryForkingSetting` | Sets whether private repository forks are enabled for an organization. |
| `updateOrganizationWebCommitSignoffSetting` | Sets whether contributors are required to sign off on web-based commits for repositories in an organization. |
| `verifyVerifiableDomain` | Verify that a verifiable domain has the expected DNS record. |

#### GraphQL: classic projects (16 mutations, out of scope: these are classic Projects, which GitHub has retired in favour of Projects (version 2))

| Mutation | What it does |
|---|---|
| `addProjectCard` | Adds a card to a ProjectColumn. Either `contentId` or `note` must be provided but **not** both. |
| `addProjectColumn` | Adds a column to a Project. |
| `cloneProject` | Creates a new project by cloning configuration from an existing project. |
| `convertProjectCardNoteToIssue` | Convert a project note card to one associated with a newly created issue. |
| `createProject` | Creates a new project. |
| `deleteProject` | Deletes a project. |
| `deleteProjectCard` | Deletes a project card. |
| `deleteProjectColumn` | Deletes a project column. |
| `importProject` | Creates a new project by importing columns and a list of issues/PRs. |
| `linkRepositoryToProject` | Creates a repository link for a project. |
| `moveProjectCard` | Moves a project card to another place. |
| `moveProjectColumn` | Moves a project column to another place. |
| `unlinkRepositoryFromProject` | Deletes a repository link from a project. |
| `updateProject` | Updates an existing project. |
| `updateProjectCard` | Updates an existing project card. |
| `updateProjectColumn` | Updates an existing project column. |

#### GraphQL: packages (1 mutations, in scope)

| Mutation | What it does |
|---|---|
| `deletePackageVersion` | Delete a package version. |

#### GraphQL: projects (32 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addProjectV2DraftIssue` | Creates a new draft issue and add it to a Project. |
| `addProjectV2ItemById` | Links an existing content instance to a Project. |
| `archiveProjectV2Item` | Archives a ProjectV2Item |
| `clearProjectV2ItemFieldValue` | This mutation clears the value of a field for an item in a Project. Currently only text, number, date, assignees, labels, single-select, multi-select, iteration and milestone fields are supported. |
| `convertProjectV2DraftIssueItemToIssue` | Converts a projectV2 draft issue item to an issue. |
| `copyProjectV2` | Copy a project. |
| `createProjectV2` | Creates a new project. |
| `createProjectV2Field` | Create a new project field. |
| `createProjectV2IssueField` | Create a new project issue field. |
| `createProjectV2StatusUpdate` | Creates a status update within a Project. |
| `createProjectV2View` | Creates a new view in a project. |
| `deleteProjectV2` | Delete a project. |
| `deleteProjectV2Field` | Delete a project field. |
| `deleteProjectV2Item` | Deletes an item from a Project. |
| `deleteProjectV2StatusUpdate` | Deletes a project status update. |
| `deleteProjectV2View` | Deletes a view from a project. |
| `deleteProjectV2Workflow` | Deletes a project workflow. |
| `linkProjectV2ToRepository` | Links a project to a repository. |
| `linkProjectV2ToTeam` | Links a project to a team. |
| `markProjectV2AsTemplate` | Mark a project as a template. Note that only projects which are owned by an Organization can be marked as a template. |
| `unarchiveProjectV2Item` | Unarchives a ProjectV2Item |
| `unlinkProjectV2FromRepository` | Unlinks a project from a repository. |
| `unlinkProjectV2FromTeam` | Unlinks a project to a team. |
| `unmarkProjectV2AsTemplate` | Unmark a project as a template. |
| `updateProjectV2` | Updates an existing project. |
| `updateProjectV2Collaborators` | Update the collaborators on a team or a project |
| `updateProjectV2DraftIssue` | Updates a draft issue within a Project. |
| `updateProjectV2Field` | Update a project field. |
| `updateProjectV2ItemFieldValue` | This mutation updates the value of a field for an item in a Project. Currently only single-select, multi-select, text, number, date, and iteration fields are supported. |
| `updateProjectV2ItemPosition` | This mutation updates the position of the item in the project, where the position represents the priority of an item. |
| `updateProjectV2StatusUpdate` | Updates a status update within a Project. |
| `updateProjectV2View` | Updates an existing view in a project. |

#### GraphQL: pulls (36 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addPullRequestCreationCapBypassUsers` | Add users to the pull request creation cap bypass list. Bypassed users can create pull requests regardless of the configured cap. Only users with maintainer permissions can manage the bypass list. You can add a maximum of 100 users per request. The bypass list can only hold a maximum of 100 users. |
| `addPullRequestReview` | Adds a review to a Pull Request. |
| `addPullRequestReviewComment` | Adds a comment to a review. |
| `addPullRequestReviewThread` | Adds a new thread to a pending Pull Request Review. |
| `addPullRequestReviewThreadReply` | Adds a reply to an existing Pull Request Review Thread. |
| `archivePullRequest` | Archive a pull request. Closes and marks the pull request as archived. Users with the triage role or higher can archive pull requests. |
| `closePullRequest` | Close a pull request. |
| `convertPullRequestToDraft` | Converts a pull request to draft |
| `createPullRequest` | Create a new pull request |
| `deletePullRequestReview` | Deletes a pull request review. |
| `deletePullRequestReviewComment` | Deletes a pull request review comment. |
| `dequeuePullRequest` | Remove a pull request from the merge queue. |
| `disablePullRequestAutoMerge` | Disable auto merge on the given pull request |
| `dismissPullRequestReview` | Dismisses an approved or rejected pull request review. |
| `enablePullRequestAutoMerge` | Enable the default auto-merge on a pull request. |
| `enqueuePullRequest` | Add a pull request to the merge queue. |
| `markFileAsViewed` | Mark a pull request file as viewed |
| `markPullRequestReadyForReview` | Marks a pull request ready for review. |
| `mergePullRequest` | Merge a pull request.  > [!NOTE] > We recommend using the [asynchronous merge REST API](${externalDocsUrl}/rest/pulls/pulls#merge-a-pull-request-asynchronously) instead. > This mutation does not support stacked pull requests. |
| `removePullRequestCreationCapBypassUsers` | Remove users from the pull request creation cap bypass list. Only users with maintainer permissions can manage the bypass list. |
| `reopenPullRequest` | Reopen a pull request. |
| `requestCopilotCodeReview` | Requests a Copilot code review.  Every call attempts to advance the Copilot code review lifecycle for the pull request: if no Copilot review has been requested yet, an initial request is created; if the most recent Copilot review has already completed, a new request is created automatically to continue the lifecycle. If a Copilot code review request is already pending, no new request is created and `failureReason` is `REQUEST_CONFLICT`. |
| `requestReviews` | Set review requests on a pull request. |
| `requestReviewsByLogin` | Set review requests on a pull request using login strings instead of IDs. |
| `rerequestReviews` | Rerequest reviews on a pull request. |
| `resolveReviewThread` | Marks a review thread as resolved. |
| `revertPullRequest` | Create a pull request that reverts the changes from a merged pull request. |
| `submitPullRequestReview` | Submits a pending pull request review. |
| `unarchivePullRequest` | Unarchive a pull request. Removes the archived flag from the pull request. Does not automatically reopen or unlock the pull request. Users with the triage role or higher can unarchive pull requests. |
| `unmarkFileAsViewed` | Unmark a pull request file as viewed |
| `unresolveReviewThread` | Marks a review thread as unresolved. |
| `updatePullRequest` | Update a pull request |
| `updatePullRequestBranch` | Merge or Rebase HEAD from upstream branch into pull request branch |
| `updatePullRequestReview` | Updates the body of a pull request review. |
| `updatePullRequestReviewComment` | Updates a pull request review comment. |
| `updateTeamReviewAssignment` | Updates team review assignment. |

#### GraphQL: reactions (2 mutations, in scope)

| Mutation | What it does |
|---|---|
| `addReaction` | Adds a reaction to a subject. |
| `removeReaction` | Removes a reaction from a subject. |

#### GraphQL: repos (18 mutations, in scope)

| Mutation | What it does |
|---|---|
| `acceptTopicSuggestion` | Applies a suggested topic to the repository. |
| `archiveRepository` | Marks a repository as archived. |
| `cloneTemplateRepository` | Create a new repository with the same files and directory structure as a template repository. |
| `createRepository` | Create a new repository. |
| `createRepositoryCustomProperty` | Create a repository custom property. |
| `createRepositoryRuleset` | Create a repository ruleset |
| `declineTopicSuggestion` | Rejects a suggested topic for the repository. |
| `deleteRepositoryCustomProperty` | Delete a repository custom property. |
| `deleteRepositoryRuleset` | Delete a repository ruleset |
| `promoteRepositoryCustomProperty` | Promote a repository custom property to the enterprise level. |
| `setRepositoryCustomPropertyValues` | Set repository custom property values for a repository. |
| `setRepositoryInteractionLimit` | Sets an interaction limit setting for a repository. |
| `unarchiveRepository` | Unarchives a repository. |
| `updateRepository` | Update information about a repository. |
| `updateRepositoryCustomProperty` | Update a repository custom property. |
| `updateRepositoryRuleset` | Update a repository ruleset |
| `updateRepositoryWebCommitSignoffSetting` | Sets whether contributors are required to sign off on web-based commits for a repository. |
| `updateTopics` | Replaces the repository's topics with the given topics. |

#### GraphQL: sponsors (9 mutations, in scope)

| Mutation | What it does |
|---|---|
| `cancelSponsorship` | Cancel an active sponsorship. |
| `createSponsorsListing` | Create a GitHub Sponsors profile to allow others to sponsor you or your organization. |
| `createSponsorsTier` | Create a new payment tier for your GitHub Sponsors profile. |
| `createSponsorship` | Start a new sponsorship of a maintainer in GitHub Sponsors, or reactivate a past sponsorship. |
| `createSponsorships` | Make many sponsorships for different sponsorable users or organizations at once. Can only sponsor those who have a public GitHub Sponsors profile. |
| `publishSponsorsTier` | Publish an existing sponsorship tier that is currently still a draft to a GitHub Sponsors profile. |
| `retireSponsorsTier` | Retire a published payment tier from your GitHub Sponsors profile so it cannot be used to start new sponsorships. |
| `updatePatreonSponsorability` | Toggle the setting for your GitHub Sponsors profile that allows other GitHub accounts to sponsor you on GitHub while paying for the sponsorship on Patreon. Only applicable when you have a GitHub Sponsors profile and have connected your GitHub account with Patreon. |
| `updateSponsorshipPreferences` | Change visibility of your sponsorship and opt in or out of email updates from the maintainer. |

#### GraphQL: teams (1 mutations, in scope)

| Mutation | What it does |
|---|---|
| `updateTeamsRepository` | Update team repository. |

#### GraphQL: users (8 mutations, in scope)

| Mutation | What it does |
|---|---|
| `changeUserStatus` | Update your status on GitHub. |
| `createUserList` | Creates a new user list. |
| `deleteUserList` | Deletes a user list. |
| `followUser` | Follow a user. |
| `setUserInteractionLimit` | Set a user level interaction limit for an user's public repositories. |
| `unfollowUser` | Unfollow a user. |
| `updateUserList` | Updates an existing user list. |
| `updateUserListsForItem` | Updates which of the viewer's lists an item belongs to |
