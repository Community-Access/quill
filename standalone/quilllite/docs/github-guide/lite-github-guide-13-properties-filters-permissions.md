# Chapter 13: Properties, filters and permissions

## What this chapter covers

Everything the GitHub Workbench shows has a Properties sheet, and the sheet is
where you change it. This chapter covers the sheet, changing many things at
once, undoing a change, filtering a list on anything, and the permissions side:
what you are allowed to do, how to get what you are missing, and how to manage
who else has access.

## Properties: Alt+Enter on anything

Select a row in the list and press `Alt+Enter`. A Properties sheet opens for
it: an issue, a pull request, a repository, a label, a milestone, a branch, a
release, a workflow run, a person, a team, a gist, an alert, and the rest.
**Item > Properties...** and the last row of every context menu open the same
sheet. In the tree, `Alt+Enter` on a repository opens the repository's own
sheet.

The sheet is a set of pages. The first is always General.

- `Ctrl+Tab` and `Ctrl+Shift+Tab` move between pages, and `Ctrl+1` to
  `Ctrl+9` jump to one.
- Every fact is a box you can Tab to and read, even the ones you cannot
  change, so a braille display can pan through them. Dates are written out.
- `F5` loads it again from GitHub. `Ctrl+Shift+C` copies the whole sheet as
  text, and the Copy Link and Open on GitHub buttons do what they say.

The sheet remembers the page you used last for each kind of thing. If you set
milestones all morning, the next issue's sheet opens on Organize.

### Changing things

A field you are allowed to change is an ordinary control. A field you are not
allowed to change is read-only, and the line under it says why, for example
"changing this needs triage access to owner/name; you have read access", and
who can change that. `F1` on the field says the same.

- Labels, assignees, reviewers and your reactions are lists of check boxes,
  and a repository's features (Issues, Projects, Wiki, Discussions) are
  check boxes too. Each one says its state in its own words, "bug, on" or
  "Issues, off", and Space checks or clears it once; the words change with
  it, and nothing else is said.
- New Label... and New Milestone... beside their lists make a new one on
  GitHub and check it straight away. If one by that name is already there,
  that is not a failure: QUILL Lite says "bug already exists; using it" and
  checks the one GitHub has.
- **OK** saves and closes, and Enter on a check box, a list or a one-line
  box is OK. **Apply**, or `Ctrl+S`, saves and keeps the sheet open, and
  focus comes back to the check box or field you were on. `Ctrl+Enter` is
  OK from anywhere, even in a long text box. Escape is Cancel.

The menus still name the common changes. **Item > Labels...**,
**Assignees...** and **Milestone...** open the sheet at the right page.
There are no separate keys for single properties: `Alt+Enter`, then the page.

### You: your own relationships

Anything you can have a relationship with has a **You** page, right after
General: the second page, so `Ctrl+2` reaches it. It holds every relationship
GitHub offers with that thing, each as a control you change like any other
field, and saving sends only the ones you changed and says what happened in
one sentence: "owner/name: starred on; watch level all activity."

- **A repository:** Starred, and Watch level (all activity, participating and
  mentions, or ignore).
- **A person:** Following and Blocked.
- **An organization:** Following, and Show my membership publicly.
- **An issue:** Subscribed, your reactions (a check box for each of the
  eight), and Pinned to the repository.
- **A pull request:** Subscribed and your reactions.
- **A discussion:** Subscribed, your reactions and Upvoted.
- **A release:** your reactions. **A gist:** Starred. **A notification:**
  Subscribed.

Some relationships GitHub's API cannot change, and those are read-only boxes
whose `F1` says why in one sentence: whether something is **Pinned to your
profile** (customize your pins on your GitHub profile page), whether you are
**Sponsoring** someone (that spends money at a tier you choose, so it is done
from their Sponsor node, never a check box), whether a pull request or a
discussion is pinned (GitHub pins only issues through its API), and whether
somebody follows you, which is theirs to change. The menu rows you already
know, such as Star or Unstar, Watch or Unwatch, Follow or Unfollow, React...
and Pin or Unpin Issue, send the same requests as the You page. Read Only and
Safe Mode lock the You page like every other page, with the reason under each
field.

### Saving safely

- **If somebody else changed it meanwhile,** the sheet says so before
  anything is sent: "Changed on GitHub since you opened this: milestone is now
  2027.2." For each such field you choose Keep Theirs or Use Mine.
- **Only what really changed is reported.** After saving, the Workbench reads
  the object again and says one sentence about what changed: "Issue #42:
  added bug, removed docs." GitHub sometimes accepts a change it then ignores,
  usually because of access; when that happens the sentence names the field.
- **Access and settings are previewed.** A change to who has access, or to a
  repository setting, is read back to you in words first, and Enter goes
  ahead. Anything hard to reverse, such as making a private repository
  public, also asks you to type its name.

## Many at once

Select several rows (Shift and Ctrl with the arrows, or `Ctrl+A`) and press
`Alt+Enter`. One sheet opens for all of them, titled "Properties of 5
issues".

- A field that is the same on all of them shows its value. One that differs
  says Mixed and is left alone unless you change it.
- A label on some of them is a check box in its third state, read as "bug, on
  3 of 5". Check it to put it on all of them, clear it to take it off all of
  them, or leave it.
- You hear a preview first: "Change 14 issues: add bug, remove triage. 3 of
  them already have bug." Enter goes ahead.
- Then a list of results, one line per item: Done, Skipped because it was
  already so, or Failed and why. Copy Results copies them, and Retry Failed
  (`F8`) runs the failed ones again.
- The You page works here too. Select twelve repositories in a search,
  press `Alt+Enter`, and check Starred or set Watch level on the You page:
  each repository is starred, or watched, with a result line for each.

Batches pause a second between items, because GitHub limits how quickly one
account may make changes.

### Saying it in words

**Plain-Language Batch...**, on the Workbench's Tools menu (`Ctrl+Shift+S`
there), takes the change as a sentence, for the repository you are in:

- "close every issue labelled duplicate older than 90 days"
- "close all issues labeled stale that nobody touched in 90 days as not
  planned"
- "add label triage to every issue with no label", or "remove label wontfix
  from all closed issues"
- "assign alice to every open issue labelled bug", or "unassign me from all
  pull requests"
- "which pull requests are waiting on me, oldest first?" shows them in the
  list, and "how many issues are labelled bug?" says how many. Neither
  changes anything.

There is no AI in it. QUILL Lite reads a fixed set of words: labelled,
without label, with no label, by, assigned to, unassigned, in milestone,
waiting on me, mentioning me, open or closed, an age ("older than 90 days",
"updated before March 2024"), and oldest or newest first. The same sentence
always means the same thing, and a word it does not know is never guessed:
it says what it does read, and gives you your sentence back to correct.

It then searches GitHub and shows every item it found as a checked list.
Uncheck any you want left alone, and OK goes on to the same preview and
results as any batch above. Closing as a duplicate is not a batch, because
each one needs the issue it duplicates; close those one at a time with
`Delete` on the row.

## Undoing a change

`Ctrl+Z` in the list or the tree undoes your last change on GitHub, where
GitHub allows it, and `Ctrl+Y` makes it again. In a text box they undo and
redo your typing as usual. The same commands are **Edit > Undo GitHub
Change** and **Redo GitHub Change**.

**Account > Change History...** (`Ctrl+Shift+H`) lists every change the
Workbench has made, newest first: what, when, before and after, and whether
GitHub confirmed it. Undo This Change reverses the selected one. You can save
the list as a CSV file or clear it. It stays on this computer for 90 days, and
a secret's value is never in it.

**Set Your Status...**, on the Workbench's Account menu, reads your GitHub
status, the short message beside your name, and offers to set a new one or
clear it. A new one asks, a question at a time, for the message, an emoji by
its GitHub name (`palm_tree`, `house`, or none), whether to mark yourself busy,
and when it clears itself. You hear the status as it is now.

## Filtering

The filter box (`Ctrl+E`) takes plain words, which narrow the loaded list, and
GitHub's own search terms such as `label:bug` or `no:milestone`, which ask
GitHub. Three other ways write into the same box.

- **Quick Filters,** on the Workbench's View menu: Assigned to Me, Assigned To..., Opened by Me,
  Opened By..., Mentions Me, Review Requested from Me, Reviewed by Me, No
  Assignee, No Milestone, No Label, No Project, No Type, Drafts, Has
  Conflicts, Checks Failing and Updated This Week. Each one is checked while
  it is on, they combine, and the window title names them. Clear These
  Filters turns them all off.
- **Show Only and Hide:** the context menu of a row has both, with every value
  in that row: "label bug", "author dependabot".
- **The Filter Builder,** `Ctrl+Alt+F`: choose an attribute, an operator and a
  value, then Add Condition (`Insert`). Each box reads its own label as you
  Tab to it: Attribute, Operator, Value. The values come from the repository,
  and Me is offered for every person. The query appears as you go, so you
  learn GitHub's syntax by watching it. OK puts it in the filter box; Save as
  Search also keeps it under Saved Searches.

Has Conflicts is the one GitHub's search cannot answer, so the Workbench
checks the pull requests already loaded and the Items cell of the status bar
says so. **Load All** on the Workbench's View menu (`Ctrl+Shift+Page Down`) loads
every page to be sure.

### More rows

Every list starts with one page: 30 issues or pull requests, 50 rows of
anything else. **Load More**, on the Workbench's View menu (Alt+Page Down
there), reads one page more each time, and **Load All** on the same menu reads
up to a thousand at once.
Both work on every list in the Workbench, Notifications, My Work, discussions,
labels and the merge queue included. When a list holds only part of what
GitHub has, the Items cell of the status bar says so, for example "Gists:
showing the first 50 items; more may exist. Load More or Load All reads the
rest.", so a short list is never mistaken for the whole of it.

### Shaping the list

- On the Workbench's View menu, **Show** chooses issues, pull requests or
  both, and **Open or Closed** which ones.
- **Sort By** on the same menu orders the list, and **Columns...**
  (`Ctrl+Shift+U`) chooses its columns.
- **Group By**, also on the View menu, puts the groups in the tree as nodes: by label,
  milestone, assignee, author, type, state, repository or review state. Each
  node reads with its count, and selecting it shows that group.
- Those orders and groups are an issue's. Every other list (branches, tags,
  releases, workflows, runs, discussions, notifications, alerts, people,
  teams, repositories and the rest) has **By Column...** at the end of Sort
  By and of Group By instead: any of its columns, first to last or last to
  first, and for a list of one column its name, repository, kind or last
  update. Each list remembers its own choice, for this account, as it
  remembers its columns.
- **Your place is kept.** Coming back to a list, with Back (`Backspace`) or
  from a sheet, a dialog or a document, puts you on the row you left, even
  if it has moved; a refresh while you are in a group keeps you in that
  group, on that row.
- **Go > Next Unread** (`Ctrl+Period`) and **Previous Unread**
  (`Ctrl+Shift+Period`) move between unread notifications. Go also has
  submenus for your pinned repositories, favorites and saved searches.

## Permissions

### Yours

**Account > GitHub Permissions...** (`Ctrl+Shift+P`) lists every permission
the Workbench can use, what it unlocks, and whether you have it, such as
"project: set an item's projects and edit project fields. You do not have
it."

- **Add Permissions...** asks for every missing one the next time you sign in
  with GitHub, so you approve once on GitHub's page.
- **Copy Command** copies the `gh auth refresh` command that adds them for the
  GitHub command-line tool.
- **Classic Token Page** opens GitHub's new-token page with the scopes listed,
  and **Fine-grained Steps** copies what to set on a fine-grained token, by
  GitHub's own names.
- **Check Again** reads your permissions again and says what changed.

A fine-grained token does not tell anyone its permissions, so for one of those
the list says "This token's permissions are set on GitHub" rather than
guessing.

### Read Only, Organize or Full

**Account > Roles and Access > Workbench Level for This Account...** sets
what the Workbench may change with an account, whatever GitHub would allow.
Read Only changes nothing, which suits demonstrating or looking around
someone else's organization. Organize allows labels, assignees, comments and
the like, but not access, settings or deleting. Full allows everything your
access allows. Safe Mode makes every account Read Only.

### The smallest permissions that would do

**Account > Roles and Access > Least Privilege Advice...** is a report: it
changes no token and no setting. It is based on what the Workbench saw this
account do on this computer: the kinds of request it sent (never which
repository or person), the changes that passed the Workbench level check and
how far each reached, Change History, the scopes GitHub names for a classic
token, and every time GitHub refused a request and said which permission it
wanted. From those it suggests:

- the smallest Workbench level that covers what you did (Read Only, Organize
  or Full);
- for a classic token, the scopes that are enough, the ones it has that were
  never used, and a broad scope where a narrower one would do, with a link to
  GitHub's new-token page with just those checked;
- for a fine-grained token, the permissions by GitHub's own names, read-only
  or read and write, and what no fine-grained token can reach.

It then says what it cannot know. It saw only this computer's use, not
another computer, the `gh` command or GitHub's website. GitHub does not list a
fine-grained token's exact permissions, so the report can say only what
worked and what was refused. And it cannot tell whether a repository is
private, so `repo` is suggested only where that would matter. To change a
token, use GitHub's Settings, Developer settings.

### Who else has access

A repository's sheet has an Access page: the people with access, the teams,
and pending invitations. Select a row and use Add..., Change... or Remove
(`Insert`, `F2` and `Delete` work too). Each change is read back to you first,
and recorded in Change History. The Workbench refuses to remove your own admin
access or the last owner, and says who else could do it. Organization and
team sheets work the same way for members and maintainers.

On an organization's sheet, each member reads with their role and whether
two-factor sign-in is on: "kim, person, member, direct, two-factor off".
GitHub shows two-factor only to owners; anyone else hears "two-factor not
shown to you". Change... on a member offers member, owner, or outside
collaborator; making someone an outside collaborator takes them out of the
organization and its teams, so QUILL Lite asks you to type their name first.
On the Outside Collaborators page, Add makes a member an outside
collaborator, Change... invites one to be a member, and Remove takes away
every repository they have here, again after their name is typed. You cannot
make yourself an outside collaborator, remove yourself while you are the last
owner, or remove the last owner.

A team's Repositories page lists every repository the team reaches with its
role there: Add, Change... and Remove work on it too. The last maintainer
cannot remove themselves, and taking admin away from a team you are on is
refused when that team is how you administer the repository. The General
page's **Parent team** moves the team under another, and **New Team...** asks
for the parent and whether mentions notify the team. The organization's
**Members** list reads "kim, member, two-factor off.", and **Members Without
Two-Factor** on the organization's row lists only those, for owners.

**Account > Roles and Access** also has:

- **My Access Here...**, your role on this repository and where it comes from;
- **View As Role...** and **Compare Roles...**, what a role may do, read-only;
- **Why Can't They?...**, what stops a person doing something, and who can
  change it;
- **Access Review...**, every person and repository pair in an organization
  with their role, copied as CSV too;
- **Bulk Access Changes...**, one team or person on many repositories at
  once, previewed, with a result per change.

### Who has what, and why

Under an organization in the tree, three lists answer "who can do what here"
a row at a time:

- **Access Review: People**: "jeff on quill: Admin, from team Maintainers;
  also Write directly; also Read from the organization's base permission."
  The highest role comes first, and every other way they have access follows
  "also".
- **Access Review: Teams**: "Docs on site: Reviewer, for 3 members, a child
  team of Maintainers."
- **Custom Property Values**: a row a repository with every custom property,
  unset ones said as "not set".

The filter box and Show Only narrow them, and **Export List...**
(`Ctrl+Shift+X`), on the Workbench's File menu, saves what is shown. When GitHub will not show part of the answer, the status bar
says which. **Set Repositories' Custom Property...** on the organization's
row sets one property in several repositories at once.

### Rules in plain words

A ruleset's sheet, and a branch's protection, list every rule as a check box
with its settings, and a Summary page reads the whole thing as sentences: "On
the default branch: changes need a pull request with 2 approvals including a
code owner; checks build and test must pass; force pushes are blocked." Read
that page first.

A repository's **Settings > Rulesets** list, and an organization's
**Rulesets**, show each ruleset as a sentence; Alt+Enter opens its sheet, and
Delete removes it after you type its name. The sheet's Rules page also lists
every rule with every setting GitHub sent; its Bypass page has a check list of
the roles that may bypass the rules, keeping teams and apps as they are; and
an organization ruleset's Repositories page says which repositories it covers
and lets you choose them by name. A branch's classic protection sheet has
every setting GitHub offers, and its **Who** page says who may push, dismiss
reviews and skip the pull request; saving keeps those lists as they were.

---

- Previous: [Chapter 12: The GitHub Workbench, place by place](lite-github-guide-12-the-workbench.html)
- [Contents](github-guide.html)
