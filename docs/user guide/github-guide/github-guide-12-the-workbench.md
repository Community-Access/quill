# Chapter 12: The GitHub Workbench, place by place

## What this chapter covers

The GitHub Workbench is one window for everything GitHub: what needs you,
your repositories, searches, people, gists and projects. This chapter walks
through it the way the window is laid out, one place at a time, starting with
Start Here. By the end you will know where each thing lives, how to get there
in one key, and how to ask the window what you can do wherever you are.

Every later section assumes three things, so here they are first.

- **Three panes.** The tree on the left says where you are. The list says
  what is there. The details say what the selected row is. `F6` moves from
  pane to pane and then to the status bar; `Shift+F6` goes the other way.
- **Enter does the obvious thing.** On an issue it reads it, on a pull request
  it opens the review, on a run it shows the jobs, on a repository it opens
  the repository's own place in the tree.
- **You can always ask.** `Shift+F1` lists everything you can do with what is
  selected, with each key, and says why anything greyed out is greyed. `F1`
  says what the place and the control you are on are for.

## Opening it

In either editor, turn on **View > GitHub Workbench Mode** (`Alt+V`, then
`K`), and the GitHub menu (`Alt+G`) has the doors in: the Workbench itself,
Inbox, this repository's issues, its pull requests and its Actions runs. Each
door opens the window at that place. If the window is already open, the door
brings it forward instead of opening a second one.

The Workbench is a window of its own, not a dialog. The editor stays usable
while it is open, and `Alt+Tab` moves between them. Inside the Workbench,
`Ctrl+Shift+E` brings back the editor that opened it. `Alt+F4` closes the
Workbench; `Escape` never does. Escape clears the filter box first, and then
goes back to where you were.

The window remembers where you were for each account: the place you had
selected, the branches of the tree you had open, and the repositories you
visited. Next time it opens there, unless you have chosen Inbox or Start Here
in Workbench Options.

## Start Here

The first place in the tree, and the place the window opens until you have
signed in. Its details pane says what the window is, whether you are signed
in, and the five keys to learn first: `F6`, `Enter`, `Shift+F1`, `Alt+Enter`
and `Backspace`. `Ctrl+9` comes back here from anywhere.

## Needs My Attention

Everything waiting on you, across GitHub. `Ctrl+1` goes straight to Inbox, the
first place under it.

- **Inbox** gathers what needs you: notifications, review requests,
  assignments and mentions, in one list.
- **Notifications** is GitHub's own list. `Ctrl+Q` marks the selected one
  read, `Delete` marks it done, and `Ctrl+Shift+Q` marks the whole list read;
  it asks first when there are more than twenty.
- **Review Requests**, **Assigned to Me**, **Mentions**, **My Open Pull
  Requests** and **My Open Issues** are the same work split by why it is
  yours.
- **My Activity Feed** is what you did lately.

When one of these is empty, the details pane says so and says what would fill
it, so an empty list never leaves you wondering whether it loaded.

## Repositories

The repository you are working in comes first, then Pinned, Favorites, your
own repositories, Starred, Watched and your organizations. `Ctrl+2` goes to
the repository you are working in. `Ctrl+L` opens any other one: type
`owner/name`, or paste a link, and it gets a place of its own here.

Every repository has the same places under it, in the same order, so once you
know one you know them all. `Ctrl+Shift+1` to `Ctrl+Shift+0` jump to them:

| Key | Place |
| --- | --- |
| `Ctrl+Shift+1` | Issues |
| `Ctrl+Shift+2` | Pull Requests |
| `Ctrl+Shift+3` | Discussions |
| `Ctrl+Shift+4` | Actions, on its Runs |
| `Ctrl+Shift+5` | Code, on its Files |
| `Ctrl+Shift+6` | Releases |
| `Ctrl+Shift+7` | The repository's Projects |
| `Ctrl+Shift+8` | Security |
| `Ctrl+Shift+9` | Settings |
| `Ctrl+Shift+0` | Insights |

A few things worth knowing:

- **Issues and Pull Requests** has both in one list, newest first, if you
  prefer reading them the way an inbox reads.
- **Merge Queue** lists the default branch's merge queue in order, when the
  repository has one: "2. #57 Fix the parser, running its checks", with who
  queued it and the commit it was queued at in the details. A repository
  without a merge queue lists nothing; the node's note says why. Chapter 5
  has the merge queue.
- **Files** lists the default branch a folder at a time. Enter on a folder
  opens it, and the first row, Up one folder, comes back out. Enter on a file
  opens it in the editor.
- **Settings** lists the settings you can change, General and Branch
  Protection. Enter on one opens the same dialog the editor has always used,
  and that dialog asks before anything changes.
- **Repository Actions**, `Ctrl+Shift+G`, lists everything else you can do
  with the repository: star it, fork it, clone it, Codespaces, and its
  administration. It also opens three windows of their own: **Files, History
  and Blame...**, which reads any file at any branch, tag or commit with the
  commits that changed it and who last touched each line; **Milestones...**;
  and **Projects...**.
- **Branches** has an **Against default** column: "3 ahead, 1 behind main",
  "even with main", or "the default branch". The details pane says the same
  on its own line. When GitHub did not say, the cell is blank rather than
  guessed.

`Ctrl+N` makes something new where you are: an issue in Issues, a pull request
in Pull Requests, a gist in My Gists, a saved search under Saved Searches, a
pin under Pinned, and the repositories to read in Across Repositories.
`Ctrl+Shift+N` asks what to make.

### A new issue, and issue forms

`Ctrl+N` in Issues reads the repository's issue templates first, then asks
which to start from: Blank issue, or one of the templates, each with its own
description. That list now includes GitHub's issue forms, the ones written in
YAML that show as a form with boxes on the website. Choose one and QUILL fills
it as a real form:

- Each field is its own labelled control: a text box, a larger text box for
  longer answers, a drop-down list, or a group of check boxes. A required one
  says "(required)" in its name, so you hear it before you type.
- Text from the form's authors, such as "Please search before filing", is in
  a read-only box you can read but not change.
- If something required is empty, Create Issue does not send; the line above
  the buttons says what is still missing.
- Then you get the same preview every new issue gets, and nothing is sent
  until you say yes. The issue GitHub receives reads exactly like one filed
  from the form on the website, with each answer under its own heading.

If a repository has a form QUILL cannot fill, it says so once and leaves that
one off the list; it is still there on GitHub, and Blank issue and the other
templates are still offered.

### A new pull request

`Ctrl+N` in Pull Requests opens **New Pull Request**. To start from a
particular branch, select it in Branches and press `Ctrl+Shift+N`, then choose
Pull Request.

- **Merge into** is the branch that receives the changes, usually the default
  branch. **Merge from** is the branch with your changes.
- **Title** and **Description** start from the commits. One commit gives its
  own subject and body; several give a title made from the branch name, so
  `fix/login-crash` becomes "Fix login crash".
- **Create as a draft** opens it as a draft, which cannot be merged and asks
  nobody to review it until you mark it ready.
- **Create Pull Request** is the only button that sends anything.

If the two branches are the same, or Merge from has nothing that Merge into
does not already have, QUILL says so instead of opening the window. If the
branch already has an open pull request into the same branch, you are taken
to that one rather than making a second, and your text is kept. **Cancel**
keeps what you typed too, for the rest of the session: open New Pull Request
on the same two branches and it is waiting for you.

### Comparing branches

On a branch, **Compare Branches...** (`Ctrl+Shift+B`) shows what one branch has
that the other does not, on two tabs: Commits and Changed Files. Commits are
newest first. GitHub gives at most 250 commits for one comparison, so when
there are more the tab says so, for example "Commits (250 of 1,204, newest)",
and you know you are reading the most recent ones, not all of them.

### Templates and community files

A repository's **Templates** node lists everything GitHub reads to shape new
issues, pull requests and discussions: issue forms, Markdown issue templates,
the template chooser, pull request templates, discussion forms, and the
community files (code of conduct, contributing guide, security policy,
support, governance, funding, citation and code owners). Each row says
whether the file is the repository's own, inherited from the organization's
`.github` repository, or missing.

- **Open Template...** (Enter) opens an issue or discussion form in the
  builder, with every option labelled, and anything else as text. A missing
  community file starts from a short starter. Before **Save**, QUILL checks
  the form the way GitHub will, and each problem is named on its line. Save
  says where the file will go, the default branch or a new branch with a pull
  request when the branch is protected, and asks before it commits. Templates
  only take effect once they are on the default branch.
- **New Template...** (Ctrl+N on Templates) makes an issue form, a discussion
  form, a pull request template or the chooser. An issue form can start from
  a starter (bug report, feature request, accessibility bug report, or a
  blank form) or **From a SurveyJS or XLSForm file...**: choose a SurveyJS form (`.json`) or an XLSForm (`.xlsx`), name
  the form, and it opens in the builder converted, with a sentence for every
  question type GitHub forms cannot hold, such as a signature.
- **Write it as plain text.** In a form document, Tools > Forms > **Save As
  GitHub Issue Form...** saves the form, written in QUILL's form language, as
  an issue form, after listing anything GitHub's forms cannot hold. **Open
  GitHub Issue Form...** reads an issue form back into the form language, and
  keeps the labels, title prefix and ids so a later save gives them back.
  Chapter 12 of the WordPress and Forms guide has the details.
- **Convert Form or Template...** turns a Markdown issue template into an
  issue form (each heading becomes a long text field), or an issue form into
  Markdown, after saying what the Markdown version loses.
- **Copy to Repositories...** copies a template, or the whole set with its
  chooser, to other repositories, after a preview of each one.

Three community files have a window of their own fields: **FUNDING.yml**
(sponsor platforms and names), **CITATION.cff** (title, authors, version and
DOI), and **CODEOWNERS**. In Code Owners, type a path in **Who owns this
path** and press **Look Up** to hear which rule owns it and its owners. Press
**Check Owners** to ask GitHub whether every owner exists and can write to the
repository. GitHub quietly skips an owner who cannot, so a rule meant to
protect a folder can protect nothing. Each owner gets one line in **What the
check found**, problems first: no such account, no such team, or access
below write. An email address cannot be checked from here and is listed as
unchecked rather than passed, and so is any owner GitHub did not answer for.

## Search

Choose a search, press `Ctrl+E` to move to the filter box, type, and press
Enter. Plain words narrow the list you are looking at; GitHub's own words, such
as `is:open author:@me label:bug`, ask GitHub. `Ctrl+8` goes to Saved
Searches, and `Ctrl+N` in a search keeps it there.

## People, Gists and Projects

`Ctrl+4` goes to People: who you follow and who follows you. Enter on a person
gives them a place in the tree, with their repositories and activity. Follow
or Unfollow is on a person's context menu. `Ctrl+6` goes to Projects; each
repository's own Projects are under it.

### Profiles

**People > My Profile** is your own profile, and every person's place in the
tree starts with **Profile**, theirs. GitHub's profile page is a picture, with
a calendar of green squares; here it is rows, each whole on its own:

- Who they are: "jeff (Jeff Bishop): Tucson, Arizona; 120 followers,
  following 40.", then their bio, status and website.
- Their year: "1,234 contributions in the last year: 900 commits, 120 issues,
  200 pull requests and 14 reviews."
- The calendar as numbers: the busiest day, the longest streak and when it
  ended, the current streak, and one row for each month, newest first, such
  as "October 2026: 140 contributions." Today not having a contribution yet
  does not end the current streak.
- What they pinned: "Pinned: community-access/quill, An editor, 12 stars."
  These are repository rows, so Enter opens the repository.

### My Billing and Usage

**People > My Billing and Usage** reads this month's metered use of your
account from GitHub's billing report: one row per product, such as Actions
minutes or Codespaces storage, each with its amount and what it costs after
discounts, and a last row with the month's total. It is read only; Enter
opens your billing page on GitHub.

GitHub shares these figures only with a token that is allowed to read your
plan: a classic token with the `user` scope, which Sign In with GitHub asks
for, or a fine-grained token with Plan read permission. Without that, the list does not pretend you used
nothing. Its one row says which permission is missing and that the same
figures are on GitHub's billing page.

### Gists

`Ctrl+5` goes to My Gists.

- **New Gist** (`Ctrl+N` on My Gists) starts from the editor that opened the
  Workbench: the text you have selected there, or the whole document when
  nothing is selected, named after the document's file, or notes.md for one
  you have not saved. You can add more files,
  write a description, and choose public or secret before it is sent.
- **Edit Gist** (`Enter` on a gist) reads the gist and opens it in the same
  window. If you change nothing, nothing is sent.
- **Star or Unstar** is on the context menu.
- **Delete Gist...** (`Delete` on a gist) asks first, because a deleted gist,
  its files and its history cannot be brought back.

## Across Repositories

`Ctrl+0` goes to Across Repositories: one kind of thing from several
repositories, in one list. It is for questions such as "what has been
released across all my projects this month?" or "which runs failed
anywhere?".

The first time, press `Ctrl+N` there to choose the repositories. Type them one
per line, as `owner/name` or as a link; anything that is not a repository is
left out, and QUILL tells you which. Cancel keeps the list you had. The place
itself then lists the repositories you chose, and `Ctrl+N` changes them
whenever you like. The list belongs to the account you are signed in with.

Under it are eight lists, each drawn from every chosen repository at once:

- Issues and Pull Requests
- Releases
- Workflow Runs
- Commits
- Tags
- Milestones
- Discussions
- Security Alerts

Every row starts with its repository, "owner/name: #42 Fix the crash", and
the details pane names the repository too, so Enter, Shift+Enter, Comment and
the other commands act on the right one. Rows are newest first. Each
repository gives at most 100 rows to a list, so one busy repository cannot
crowd out the rest.

The status bar says how many rows came from how many repositories, and names
every repository that could not be read and why, such as "not found, or no
access" or "Discussions are off". A repository never just goes missing from
the list. A fork whose upstream you also chose adds no issues of its own,
because on GitHub a fork's issues are its upstream's; the status bar says so,
and you read them once, under the upstream.

## Watches, and why Ctrl+3, Ctrl+4 and Ctrl+8 go places here

Watches (`Ctrl+7`) is shown but not built yet, so its key already lands on a
place that says what it will hold.

Elsewhere in the family, `Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys: a
document task, Choose Your AI, and Which AI Am I Using. The Workbench has no
AI menu, so here they keep their place in the Go row with the other digits:
`Ctrl+3` is Search, `Ctrl+4` is People and `Ctrl+8` is Saved Searches. Switch
back to the editor (`Ctrl+Shift+E`) and they are AI keys again.

## Doing things to what is selected

Enter does the obvious thing; the Applications key, or `Shift+F10`, opens the
context menu, with the obvious thing first and Properties last; and
`Alt+Enter` shows everything about the selected row on one sheet.

The keys you will use most:

| Key | Does |
| --- | --- |
| `Ctrl+Shift+M` | Comment on the selected issue or pull request |
| `Ctrl+Shift+D` | The selected pull request's changed files |
| `Ctrl+Shift+Enter` | Merge the selected pull request |
| `Ctrl+Shift+W` | Say what failed in the selected run |
| `Ctrl+Shift+F5` | Run the failed jobs again |
| `Ctrl+Shift+B` | Compare the selected branch with another |
| `Ctrl+Shift+A` | Assign the selected issue to Copilot |
| `Ctrl+Shift+T` | Start the selected issue or pull request in a local worktree |
| `Ctrl+D` | Keep the selected row under Favorites, or take it out |
| `Ctrl+Shift+C` | Copy the selected row's address |
| `Shift+Enter` | Open it on GitHub, in your browser |
| `Delete` | Remove it safely: mark a notification done, close an issue after asking |

### Taking a list with you

**Export List...** (`Ctrl+Shift+X`), on the Workbench's File menu, saves the
list you are looking at, as it is shown: its columns, its filter and its rows. Choose an Excel workbook,
a CSV file or a Markdown table in the Save window. A Markdown table is the kind
the editor reads as a table, so the Workbench offers to open it there, where the table
keys move cell by cell. It then says how many rows it wrote, and names any
columns you have hidden, because those are left out. It works on any list:
issues, pull requests, runs, alerts, people, Change History. The WordPress
Workbench's Export List is the same command.

### Bringing issues in

Two rows on the Workbench's File menu make many issues at once in the
repository you are in. Neither sends anything before you have read a preview
and pressed **Create Issues**; Cancel there sends nothing.

- **Import Issues from a Spreadsheet...** (`Ctrl+Alt+I`) reads a CSV file or
  an Excel workbook whose first row names the columns. It matches columns by
  name: Title, Body, Labels, Assignees, Milestone and Type, and the usual other
  names, such as Summary, Description, Tags or Owner. Labels and assignees can
  be several, with commas between; a milestone is named by its title. The
  preview starts with which column fills which field and which columns match
  nothing, then has a line for each row, using the row numbers your
  spreadsheet shows. A row with no title, a title longer than GitHub allows,
  or a milestone the repository does not have is skipped, with the reason.
- **New Issues from Lines...** (`Ctrl+Alt+L`) makes one issue for each line.
  It starts with the text you have selected in the editor, in a box you can
  change, and takes off list markers and check boxes, so a task list such as
  `- [ ] Write the guide` becomes an issue called Write the guide. It then asks
  whether to make them sub-issues of an issue, by number; leave it empty for
  none.

Afterwards a window lists each row or line with the issue it made, or why
GitHub refused it, and Change History has each issue made.

`Delete` always does the safe thing for the kind of row, and asks first
whenever it cannot be undone: on a branch, a label, a release's file, a gist,
an Actions cache or a workflow run it deletes that one thing, after asking. It
never deletes the repository's default branch. Enter never deletes anything.

### Everything is done here now

The old GitHub Items window is retired, and nothing hands you over to it. What
it did, the Workbench does itself, on the selected row; where a job needs a
window, such as a run's logs, that window opens in front of the Workbench and
blocks only the Workbench, never the editor. Each row's context menu has its
own list, and `Shift+F1` reads it with the keys:

- **An issue:** Comment, Close or Reopen, Labels, Assignees, Milestone, View
  Timeline, Summarize Discussion, Assign to Copilot, Lock or Unlock
  Conversation, Pin or Unpin, Transfer Issue to another repository with the
  same owner, Set Issue Type, Reorder Sub-issues, and Start in Local
  Worktree.
- **A pull request:** Review (Enter), File Differences, Merge, View Timeline
  and the rest. Merge asks how (Squash and merge, Merge commit or Rebase),
  then asks you to type the pull request's number before anything happens,
  because a merge changes the branch for everyone.
- **A workflow run:** Jobs and Logs (Enter), What Failed, Re-run Failed Jobs
  Only, Re-run Workflow, Cancel Run, View Artifacts, Combined Check Status,
  Review Pending Deployments, Approve Run from a Fork, and Delete Run.
- **A workflow:** its Runs (Enter), and Run Workflow on Branch.
- **A release:** its Assets (Enter), each with Download, Copy Link and Delete
  Asset; Edit Release; Draft Release Notes; and Upload Asset.
- **A branch:** its Commits (Enter), Compare Branches, Copy Name, and Delete
  Branch, which asks you to type the branch name.
- **A commit or a tag:** Open, and Commit Comments, to read and write comments
  on the commit and its lines.
- **A tag**, besides: Read Tag Message, and Delete Tag.
- **A label:** Find Issues with Label (Enter), Edit Label and Delete Label.
- **A security alert:** Open, and Dismiss or Reopen Alert, with a reason.
- **A discussion:** Open Discussion Thread, to read and reply.
- **An Actions cache:** Show Details and Delete Cache.
- **A runner:** Show Details, Open on GitHub (its settings page) and Copy
  Link.
- **A package:** Show Details, Open on GitHub, Delete Package Version and
  Delete Package.
- **A notification:** Open, Mark Read, Mark Done, Unsubscribe from Thread, and
  Snooze for One Day. Snoozing hides it in the Workbench on this computer
  until tomorrow and changes nothing on GitHub; Unsnooze Locally brings it
  back.
- **A repository:** Open, Star or Unstar, Watch or Unwatch, Clone, Pin, and
  Star Lists; in Star Lists, Rename or Delete Star List too.
- **A person:** Open, and Follow or Unfollow.

Summarize Discussion uses the AI connection of the editor that opened the
Workbench, and Start in Local Worktree uses its local Git. When the editor
has not given the Workbench either one, the row is greyed and says why.

Every change asks first when it cannot be undone, runs without freezing the
window, and says one sentence about what GitHub confirmed. `F9` says it
again.

## Hearing where you are

`Alt+1` to `Alt+9` say something and move nothing: where you are, what is
selected, the selected item's state, the counts, your access, GitHub's hourly
allowance, the filter, what is loading, and your account. `F9` says the last
result again, and `Shift+F9` explains it: what it means, and what you might do
next.

### Emoji by name

People write emoji on GitHub as shortcodes, `:tada:` or `:+1:`, which the
website shows as pictures and a screen reader would otherwise spell out,
colons and all. In the details pane, and in **Read as Document...**, QUILL
reads each one by its name instead: "Shipped :tada:" is "Shipped party
popper", and `:+1:` is "thumbs up". A shortcode inside code, between
backticks or in a code block, is left as typed, since there it is code, and
so is one QUILL does not know.

## Help and Learning

The last place in the tree is help you can walk through like any other list.

- **Do Something** has tasks in plain words, such as Fix a failed run. Enter
  reads the steps; Take Me There, on the context menu, goes to the place.
- **The Guide** lists this book's chapters. Enter opens one.
- **Words** is the GitHub glossary. Type a word to jump to it.
- **Keys** has every key in the window, grouped by what it does.
- **What Changed** says what is new.
- **Ask a Person** says how to write to support@community-access.org.

The help keys work everywhere in the window:

| Key | Answers |
| --- | --- |
| `F1` | What this place and this control are for |
| `Shift+F1` | What can I do here, with each key |
| `Alt+F1` | What the GitHub word for the selected row means |
| `Ctrl+F1` | This guide, at the chapter for where you are |
| `Ctrl+Shift+F1` | Search all of help: places, commands, words and tasks |
| `Alt+Shift+F1` | Every key in the window |

## Dry Run

**Tools > Dry Run** (`Ctrl+Alt+D`) is a switch for the whole Workbench.
While it is on, every command still asks its questions and shows its preview
exactly as usual, and then, at the moment it would change something on
GitHub, it stops and says what it would have sent: "Dry run: QUILL would send
PATCH /repos/octo/app/issues/7 (state, state_reason). Nothing was changed."
Lists, sheets, previews and everything else that only reads keep working.

It is for learning a command without consequences, and for checking a big
batch twice before you send it for real. The Account cell of the status bar
says "Dry Run: nothing is sent" while it is on, and it stays on until you
press `Ctrl+Alt+D` again or close QUILL. Local Git work, such as making a
worktree, does not touch GitHub and is not stopped.

## Practice on GitHub

**Help > Practice on GitHub...** (`Ctrl+Alt+P`) makes a private repository
in your own account, `quill-practice`, to learn the writes on, where nothing
matters. After asking, QUILL fills it with:

- three issues: a typo to label, assign and close; a task list to check off
  and turn into sub-issues; and a question to answer and close as not
  planned;
- two labels, "practice: bug" and "practice: question";
- a branch, `fix-greeting`, with a pull request to review and merge;
- a workflow that fails on purpose, so What Failed, Re-run and the jobs window
  have a failure to read.

You hear each part as it is made, and then the Workbench opens the repository.
The next time, the same command offers **Open It**, **Delete It and Start
Over...** and **Delete It...**; both deletions ask first. GitHub lets an app
delete a repository only when you signed in with the `delete_repo`
permission; without it, QUILL says so and tells you where on GitHub to delete
it yourself.

**Help > Tutorials** in the editor has a track of six lessons that use it,
"GitHub, on a practice repository": make it and look round; label, comment on
and close an issue; try a command with Dry Run; review and merge a pull
request; read a failed run; and delete the repository. Each step says what to
press and what you should hear.

## Workbench Options

GitHub's preferences live in the Workbench, not in the editor's Options:
**Tools > Workbench Options...**, `Ctrl+Shift+O`. It has five pages. General
says where the window opens and how lists start. Notifications and Inbox says
how often GitHub is checked, whether each check plays a sound, and whether a
new notification may interrupt speech. Lists, Repositories (your pinned
repositories and favorites) and Privacy follow. Privacy is also where you can
review the Workbench's GitHub privacy settings. The former Items and Explore
windows are retired; every GitHub management door opens the Workbench.

You never have to open it: the Workbench works as it comes.

---

- Previous: [Chapter 11: Keyboard reference](github-guide-11-keyboard-reference.html)
- Next: [Chapter 13: Properties, filters and permissions](github-guide-13-properties-filters-permissions.html)
- [Contents](github-guide.html)
