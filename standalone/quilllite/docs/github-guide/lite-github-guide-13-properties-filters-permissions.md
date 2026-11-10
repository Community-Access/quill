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

- Labels, assignees, reviewers and your reactions are lists of check boxes.
  Space checks or clears one.
- New Label... and New Milestone... beside their lists make a new one on
  GitHub and check it straight away.
- **OK** saves and closes. **Apply**, or `Ctrl+S`, saves and keeps the sheet
  open. `Ctrl+Enter` is OK from anywhere, even in a long text box. Escape is
  Cancel.

The menus still name the common changes. **Item > Labels...**,
**Assignees...** and **Milestone...** open the sheet at the right page.
There are no separate keys for single properties: `Alt+Enter`, then the page.

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

Batches pause a second between items, because GitHub limits how quickly one
account may make changes.

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

## Filtering

The filter box (`Ctrl+E`) takes plain words, which narrow the loaded list, and
GitHub's own search terms such as `label:bug` or `no:milestone`, which ask
GitHub. Three other ways write into the same box.

- **View > Quick Filters:** Assigned to Me, Assigned To..., Opened by Me,
  Opened By..., Mentions Me, Review Requested from Me, Reviewed by Me, No
  Assignee, No Milestone, No Label, No Project, No Type, Drafts, Has
  Conflicts, Checks Failing and Updated This Week. Each one is checked while
  it is on, they combine, and the window title names them. Clear These
  Filters turns them all off.
- **Show Only and Hide:** the context menu of a row has both, with every value
  in that row: "label bug", "author dependabot".
- **The Filter Builder,** `Ctrl+Alt+F`: choose an attribute, an operator and a
  value, then Add Condition (`Insert`). The values come from the repository,
  and Me is offered for every person. The query appears as you go, so you
  learn GitHub's syntax by watching it. OK puts it in the filter box; Save as
  Search also keeps it under Saved Searches.

Has Conflicts is the one GitHub's search cannot answer, so the Workbench
checks the pull requests already loaded and the Items cell of the status bar
says so. **View > Load All** (`Ctrl+Shift+Page Down`) loads every page to be
sure.

### Shaping the list

- **View > Show** chooses issues, pull requests or both, and **View > Open or
  Closed** which ones.
- **View > Sort By** orders the list, and **View > Columns...**
  (`Ctrl+Shift+U`) chooses its columns.
- **View > Group By** puts the groups in the tree as nodes: by label,
  milestone, assignee, author, type, state, repository or review state. Each
  node reads with its count, and selecting it shows that group.
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

### Who else has access

A repository's sheet has an Access page: the people with access, the teams,
and pending invitations. Select a row and use Add..., Change... or Remove
(`Insert`, `F2` and `Delete` work too). Each change is read back to you first,
and recorded in Change History. The Workbench refuses to remove your own admin
access or the last owner, and says who else could do it. Organization and
team sheets work the same way for members and maintainers.

**Account > Roles and Access** also has:

- **My Access Here...**, your role on this repository and where it comes from;
- **View As Role...** and **Compare Roles...**, what a role may do, read-only;
- **Why Can't They?...**, what stops a person doing something, and who can
  change it;
- **Access Review...**, every person and repository pair in an organization
  with their role, copied as CSV too;
- **Bulk Access Changes...**, one team or person on many repositories at
  once, previewed, with a result per change.

### Rules in plain words

A ruleset's sheet, and a branch's protection, list every rule as a check box
with its settings, and a Summary page reads the whole thing as sentences: "On
the default branch: changes need a pull request with 2 approvals including a
code owner; checks build and test must pass; force pushes are blocked." Read
that page first.

---

- Previous: [Chapter 12: The GitHub Workbench, place by place](lite-github-guide-12-the-workbench.html)
- [Contents](github-guide.html)
