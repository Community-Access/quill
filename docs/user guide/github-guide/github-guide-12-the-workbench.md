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
  Once you have opened a place in the tree, its name says how many rows it
  had, such as "Issues (12)", or "Issues (30 or more)" when GitHub had more
  than one page. The count is added after you move away, so it is never read
  out while you are on the place; you hear it the next time you arrive.
  Searches have no count, because their rows depend on what you typed.
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
goes back to where you were. In Details, it returns you to the list instead.

The window remembers where you were for each account: its size and how wide
the tree is, the place you had selected, the branches of the tree you had
open, and the repositories you visited. Next time it opens there, unless you have chosen Inbox or Start Here
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

A search you use all the time can have a place of its own in the tree. In
Saved Searches, choose **Pin as Node** on its context menu: it appears under
Saved Searches, named by the search, and opening it asks GitHub for the
results afresh. **Unpin Node** takes the place away and keeps the saved
search; **Remove Saved Search** takes both.

Besides issues, code, commits, advisories and repositories, Search has:

- **People and Organizations:** accounts whose name or login matches, such
  as `jeff`, or with GitHub's words, `type:org location:Tucson`. Each row
  says whether it is a person or an organization; Enter opens one.
- **Topics:** GitHub topics, with what each is about and whether GitHub
  features it, such as "Accessibility: For everyone (featured)".

## People, Gists and Projects

`Ctrl+4` goes to People: who you follow and who follows you. Enter on a person
gives them a place in the tree, with their repositories and activity. Follow
or Unfollow is on a person's context menu.

A person's place also lists what GitHub shows of them publicly, read only:
**SSH Keys**, **GPG Keys** and **SSH Signing Keys** (check one before giving
them access to a server: "SSH key 4, ending abcdefgh."), **Social Accounts**,
**Gists**, **Starred**, **Watching**, **Projects**, and **People They Follow:
Activity**. `Ctrl+6` goes to Projects; each
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

### My Keys

**People > My Keys** lists the keys GitHub keeps for you, all three kinds
together, one sentence each:

- "SSH key Laptop, ED25519, SHA256:ZkAs..., added 2025-01-02, last used
  2026-11-17." An SSH key lets git push and pull without a password.
- "GPG key 3AA5C34371567BD2, for jeff@example.org, signs commits, expires
  2027-01-01." A GPG key marks your commits Verified.
- "SSH signing key Laptop, ED25519, SHA256:ZkAs..., added 2025-01-02." So
  does an SSH signing key.

The SHA256 fingerprint is the same one `ssh-keygen -lf` prints for the key on
your computer, so you can tell which key is which without reading the key
itself.

`Ctrl+N` there adds a key. QUILL asks which kind, then whether to read it from
a file, starting in your `.ssh` folder, or paste it, then a name, suggesting
the name written at the end of the key. It checks the key before sending: an
SSH key where a GPG key belongs, or anything that is a private key, is refused
with a sentence saying so, and nothing is sent. You hear "Added SSH key
Laptop" and its fingerprint.

**Delete Key...** on a key's row, or the Delete key, asks first and says what
stops working without it: pushing over SSH, or commits showing as Verified.

### Sponsorships

GitHub Sponsors lets you pay someone for their open-source work, each month or
once. **People > Sponsorships** lists both directions: "You sponsor sam: $5 a
month, since 2025-02-01." and "jo sponsors you: $25 once, since 2026-03-04."

Every person's place in the tree has **Sponsor**. Its first row says whether
they take sponsorships, whether you sponsor them already, and what they say
about it; each row after it is one of their tiers, with its price: "$5 a
month: Coffee. Keeps the lights on."

Sponsoring spends real money, so QUILL is careful:

- **Sponsor at This Tier...** on a tier asks whether everyone may see it or
  only them, then says the price again, and that GitHub charges the payment
  method on your account now and each month until you cancel, and has you
  type their login. Only then is anything sent. You hear "You now sponsor sam
  privately, $5 a month." GitHub's own custom-amount tier is not offered here;
  open their page on GitHub for that.
- **Cancel Sponsorship...** on someone you sponsor asks first, then stops it.
  Nothing more is charged for it.

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
- **Comments...** lists the gist's comments, oldest first, with "Add a
  comment..." at the top; choose one of yours to change or delete it.
- **History...** lists every saved version, newest first: "2026-11-02 by
  jeff: 3 lines added, 1 removed."
- **Forks...** lists who copied it, and **Fork Gist** copies someone else's
  gist to your own, where you can change it.
- **Delete Gist...** (`Delete` on a gist) asks first, because a deleted gist,
  its files and its history cannot be brought back.
- **Gists I Starred**, under Gists, lists the gists you starred, with who
  wrote each.

## Lists of settings

Many of the things GitHub keeps as lists, such as secrets, issue types or the
repositories a setting covers, are nodes in the tree that all work the same
way. Each row reads as a sentence. `Ctrl+N` adds one, where GitHub allows it;
Change... on the context menu changes the selected one; `Delete` deletes it, after asking.
Where a list can only be read, it says so when it is empty, and the context
menu has no Add or Delete.

These were added on 2026-11-18.

**Under People, for your own account:**

- **My Issue Fields:** values your own repositories' issues can carry, such as
  Priority or Due date. `Ctrl+N` asks for its name, its kind (text, number,
  date, or single select), its choices for a single select, separated by
  commas, and a description.
- **My Installed Apps:** the GitHub Apps installed where you can manage them,
  and whether each reaches all repositories or chosen ones. **Repositories...**
  on a row checks which repositories it may reach; QUILL adds and removes them
  one at a time, so a change someone else made meanwhile is kept.
- **My Public Email Addresses** and **Repositories I Watch:** read only.

**Under Repositories**, three of GitHub's own lists, read only: **Licences**,
**.gitignore Templates** and **Codes of Conduct**, the choices a new
repository offers.

**Under an organization:**

- **Issue Fields:** the organization's issue fields, the same way as yours,
  plus who may see their values (everyone, or members only).
- **Failed Invitations**, **Public Members** and **Installed Apps:** read only.
- **Immutable Releases: Repositories**, **Actions: Allowed Repositories** and
  **Self-hosted Runners: Allowed Repositories:** the repositories a setting
  applies to when the organization chooses them one by one. `Ctrl+N` asks for a
  repository, as its name or owner/name; `Delete` takes one off. Set the
  setting itself to "chosen repositories" on the organization's Properties
  first.
- **Dependabot Alerts**, **Secret Scanning Alerts**, **Security Advisories:**
  every repository's, in one list. A secret's value is never shown. Open a
  repository's Alerts to dismiss or resolve one.
- **Recent Events:** the organization's public activity, newest first.
- **Custom Property Values:** every repository's custom properties in one list.

**Under a repository:**

- **Activity > All Issue Comments**, **Push Activity** (pushes, force pushes,
  merges and branch changes) and **My Notifications Here:** read only.
- **Code > Commit Comments:** comments on commits. Change... rewrites one of yours;
  `Delete` deletes it.
- **People > Watchers:** who gets notifications for it.
- **Settings > CODEOWNERS Problems:** lines in the CODEOWNERS file GitHub could
  not use, with its suggestion.
- **Settings > Rule Insights:** recent pushes its rulesets passed, blocked or
  let through on a bypass.
- **Settings > Custom Property Values:** the organization's properties as this
  repository has them.

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
- **A runner:** Show Details, Runner Labels, Remove Runner, Open on GitHub
  (its settings page) and Copy Link.
- **A package:** Show Details, Open on GitHub, Delete Package Version and
  Delete Package.
- **A security advisory:** Show Details, Publish or Close Advisory, Request
  CVE, Open on GitHub and Copy Link.
- **A key:** Show Details, Delete Key and Open on GitHub.
- **A webhook:** Show Details, Ping, Recent Deliveries, Change Address or
  Secret, and Delete Webhook.
- **A deploy key or an autolink:** Show Details, Delete, and Open on GitHub.
- **The wiki:** Open on GitHub and Clone Wiki.
- **A sponsorship:** Show Details and Cancel Sponsorship. **A sponsor tier:**
  Show Details and Sponsor at This Tier.
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

Those sentences follow the same setting as the editor's copy and paste, **When
a command does something, give me** (QUILL Guide, chapter 11):

- A change that worked plays the task-complete sound. If its sentence names
  or counts what changed, such as "Created bug" or "Saved 3 changes to Issue
  #12", it is always spoken as well, because no sound can carry a name or a
  number. Only a bare acknowledgement, such as "Saved." or "Copied.", follows
  the setting: the sound, the words, both or neither, as it does for
  `Ctrl+C`.
- Something that did not work, starting "Could not", plays the error sound
  when sounds are on, and is always spoken, whatever the setting, so you
  always hear why.
- Everything else, such as "Open a repository first", is spoken with no
  sound.

`F9` says the last result even when you only heard its sound.

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
  reads the steps. The context menu has three more:
  - **Take Me There** goes to the place the task is about.
  - **Walk Me Through It** goes there too, then says the first step only.
    When you have done it, the next step is said, and so on to the end. `F1`
    says the step again, `Shift+F1` lists all the steps with where you are,
    and `Escape` stops the walk. A step that only moves the selection, such
    as "Arrow down the list", counts as done when you run the next command.
  - **Do It** runs the one command a task comes down to, where it belongs,
    with its usual dialog: File an issue opens New Issue in the repository's
    Issues. It is greyed on tasks that take more than one command.
- **The Guide** lists this book's chapters. Enter opens one.
- **Words** is the GitHub glossary. Type a word to jump to it.
- **Keys** has every key in the window, grouped by what it does.
- **Tutorials** lists the GitHub lessons, each with where you are in it
  ("done", "step 3 of 7"), and says how many you have done. Enter opens the
  lesson in the editor's Tutorials window. Walk Me Through It, on the context
  menu, says it here instead, one step at a time, with your keys. In QUILL
  Lite, which has no GitHub lessons of its own, Enter walks it here too.
- **What Changed** says what is new.
- **Tips** holds QUILLBert's tips, one short thing worth trying in each.
  They wait in this list and are never pushed at you. Once in a while a tip
  also comes to you at the right moment: the third time you do something the
  long way (arrow through a long list without the filter, open Properties on
  one row after another, press Load More again and again), the tip for the
  short way is added to the end of the details pane, once, and is not spoken,
  so it interrupts nothing. **Offer a tip when it would help**, in Workbench
  Options, General, turns those off; they all stay in Tips.
- **Words** are explained by QUILLBee, QUILLBert's friend, in one line each.
  **Plain help, without QUILLBert and QUILLBee**, in Workbench Options,
  General, says the same words without the two names.
- **Ask a Person** says how to write to support@community-access.org, and
  has **Report a Help Problem**: for help that was wrong, missing or hard to
  follow. Enter opens a message in your own email, already saying where you
  were and the last thing the Workbench said, for you to change and send.
  The Workbench sends nothing, and no token or password is ever in it.

`F1` ends with an example from your own work when the window knows enough:
the repository you are on and the row you have selected ("On
Community-Access/quill, #42 Crash on start is selected: Alt+Enter opens
everything about it"), or the account you are signed in as. It uses only what
the window has already loaded, and sends nothing anywhere.

**Help > Take the Tour** (`Alt+Shift+T`) is a spoken tour of the window, a
pane at a time: what the pane is, and one thing to do there. `F6` moves on to
the next pane and the next step, `F1` says the step again, `Shift+F1` lists
the steps, and `Escape` skips the rest. The tour starts by itself the first
time you open the Workbench, once, unless **Show First time here? help** is
off.

**Help > Ask How...** (`Alt+Shift+A`) takes a question in your own words,
such as "how do I keep only the issues with a word in them?". The answer is
built only from this help (the tasks, places, words and options, and every
menu row with its key), by the AI you chose in the editor's Choose Your AI.
When the help does not cover the question it says so, and when nothing in the
help comes near the question the AI is not asked at all. The answer is shown
in a list, with a **Do It** row for each command it names; nothing runs until
you choose a row. Only your question and the help's own words are sent: no
repository, token or GitHub content. It is greyed without an AI connection,
and off in Safe Mode.

The keys are also on a **key card** you can print or emboss, made from the
same key table as the window: `docs/github/key-card.html` to print, and
`docs/github/key-card-braille-ready.txt`, laid out 40 cells by 25 lines a
page, for QUILL's Braille Mode or a braille translator to make the BRF. The
whole of this guide is also one book, `github-guide-book.epub`, beside these
pages.

The help keys work everywhere in the window:

| Key | Answers |
| --- | --- |
| `F1` | What this place and this control are for |
| `Shift+F1` | What can I do here, with each key |
| `Alt+F1` | What the GitHub word for the selected row means |
| `Ctrl+F1` | This guide, at the chapter for where you are |
| `Ctrl+Shift+F1` | Search all of help: places, commands, words and tasks |
| `Alt+Shift+F1` | Every key in the window |
| `Ctrl+Alt+K` | Key Describer: press keys to hear what each does here, without doing it; `Escape` stops |

**Why?** explains something the Workbench did on its own, with no key from
you. When there is something to explain, `Shift+F1` lists Why? first, and
watch and notification rows also have it on their context menu. It covers:

- **A watch:** what it looks for, how often it is checked, when it was last
  checked, and what it found.
- **A notification:** the reason GitHub gave for sending it, and what
  decides that.
- **A filter:** whether it went to GitHub as a search, or covers only the
  rows already loaded, and how to read more when it does.

Shift+F1 already says why a command is greyed, and a sheet says why a field
is read-only beside the field.

**Why?** explains something the Workbench did on its own, with no key from
you. When there is something to explain, `Shift+F1` lists Why? first, and
watch and notification rows also have it on their context menu. It covers:

- **A watch:** what it looks for, how often it is checked, when it was last
  checked, and what it found.
- **A notification:** the reason GitHub gave for sending it, and what
  decides that.
- **A filter:** whether it went to GitHub as a search, or covers only the
  rows already loaded, and how to read more when it does.

Shift+F1 already says why a command is greyed, and a sheet says why a field
is read-only beside the field.

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

## Is it GitHub, or is it me?

When GitHub is slow or failing, the Workbench's errors can look like your own
mistake. **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) reads GitHub's
public status page, www.githubstatus.com, and shows what it says: whether
GitHub says everything is working, which parts are slow or down, and any
incident GitHub is working on, with its latest update.

It is the one Workbench command that reads a site other than GitHub itself,
so the first time it asks before reading. QUILL sends only the request:
nothing about you, your accounts or your repositories. It reads the page
only when you choose the command, never on its own, and the command is
greyed in Safe Mode.

## More commands on rows

Many rows have commands that make one call to GitHub and say what came
back, or show a longer answer in a window to read and copy. They are on the
row's context menu (`Shift+F10`, under More when the menu is long) and on
the Item menu. Each asks before it changes anything, and anything that
holds a token (a runner's setup or removal commands) goes to the clipboard
and is never said or shown.

- **A repository:** Languages, License, Star History, Mark Its Notifications
  Read, Set a Custom Property..., Compare Dependencies... (between two
  branches, tags or commits, with known vulnerabilities), SBOM Report,
  Ruleset History..., Secret Scanning History, Fork Workflow Settings and
  Fork Workflows from Private Repositories....
- **A commit:** Branches at This Commit, Check Run Details... (a check's
  summary and every annotation), Re-run a Check Suite..., and the reactions
  on its comments: Reactions on a Commit Comment..., React to a Commit
  Comment..., Remove My Reaction from a Commit Comment....
- **A workflow run:** Read a Step's Log..., one step at a time.
- **A pull request:** Re-request Review.... **A release:** GitHub's Release
  Notes..., the notes GitHub writes from the changes since another tag.
- **A secret scanning alert:** Where It Was Found. **A security advisory:**
  Advisory Comments, Comment on Advisory..., Edit an Advisory Comment...,
  Make a Private Fork for the Fix.
- **Runners:** in a repository's Runners or an organization's, Just-in-Time
  Runner... (a runner that takes one job) and Is a Runner Version
  Retiring?...; in an organization's, New Organization Runner...; on a
  runner, Removal Commands..., and on an organization's runner Add Runner
  Label... and Remove Runner Label.... **A runner group:** Runners in This
  Group, Hosted Runners in This Group, Add a Runner to This Group...,
  Remove a Runner from This Group....
- **An organization:** Dependabot Repository Access, Give Dependabot a
  Repository..., Take a Repository from Dependabot..., Dependabot's Default
  Access..., Make Someone an Outside Collaborator..., Define a Custom
  Property..., Set Repositories' Custom Property..., New Team..., Accept
  Membership and My Activity Here.
- **A team:** Pending Invitations and Delete Team.... **An invitation to an
  organization:** Teams It Adds To.
- **A Project:** New View... and Items in a View....
- **A discussion:** Close Discussion... (resolved, outdated or a duplicate),
  Reopen Discussion, Delete Discussion..., Upvote, Remove Upvote, Vote... (in its
  poll), Edit a Comment... and Delete a Comment....
- **An issue:** Link a Pull Request That Closes It... and Unlink a Pull
  Request....
- **An environment:** Pin Environment, Unpin Environment and Move
  Environment....
- **A repository or an organization:** Require Sign-off on Web Commits....
  **An organization:** Follow Organization and Unfollow Organization. **A
  repository:** Sponsor Links (its FUNDING.yml) and Dependency Manifests.
- **A Project, inside:** Rename a View..., Delete a View..., Rename a
  Field..., Add an Issue Field..., Edit a Draft..., Make a Draft an
  Issue..., Move an Item..., Edit a Status Update..., Delete a Status
  Update..., Delete a Workflow..., Share the Project..., Link a Team... and
  Unlink a Team....
- **Your sponsorships:** Set Up a Sponsors Profile..., New Sponsor Tier...
  and Patreon Sponsorships...; on a sponsorship, Sponsorship
  Preferences...; on one of your tiers, Publish Tier and Retire Tier....
- **Copilot's cloud agent, on a repository:** Start an Agent Task..., Agent
  Tasks, An Agent Task's Progress..., Automations, New Automation..., Run an
  Automation..., Rename an Automation..., Delete an Automation..., An
  Automation's History..., An Automation's Tasks..., Automation Tools and
  Triggers, Agent Secrets from the Organization and Agent Variables from the
  Organization. **On a pull request:** Ask Copilot to Review, Agent Merge,
  Turn On Agent Merge and Turn Off Agent Merge.... **On your profile:** My
  Agent Tasks and My Automations. These need a Copilot plan with the cloud
  agent, and GitHub calls them a preview: QUILL sends only what GitHub
  documents and reads you GitHub's own answer.
- **Your emails:** Email Visibility.... **Your profile:** Interaction
  Limits, Limit Interactions... and Lift Interaction Limits.

A few of these use parts of GitHub newer than the description QUILL was
built against (closing references, a Project's views and issue fields).
Those first read from GitHub what the change needs, and if GitHub has
changed it, they send nothing and say to use Open on GitHub instead.

## Workbench Options

GitHub's preferences live in the Workbench, not in the editor's Options:
**Tools > Workbench Options...**, `Ctrl+Shift+O`. It has five pages. General
says where the window opens and how lists start. Notifications and Inbox says
how often GitHub is checked, whether each check plays a sound, and whether a
new notification may interrupt speech. Lists, Repositories (your pinned
repositories and favorites) and Privacy follow. Privacy is also where you can
review the Workbench's GitHub privacy settings. The former Items and Explore
windows are retired; every GitHub management door opens the Workbench.

Lists also has **Short rows for braille**: each list row becomes one short
line for a braille display, the number and title first, no column names, and
short words (`cl` for closed, `PR` for pull request, `3c` for three comments,
`9 Nov` for a date). Nothing is cut off, and Details still says everything.
Columns... still chooses what the line holds. General has **Offer a tip when
it would help** and **Plain help, without QUILLBert and QUILLBee**.

You never have to open it: the Workbench works as it comes.

---

- Previous: [Chapter 11: Keyboard reference](github-guide-11-keyboard-reference.html)
- Next: [Chapter 13: Properties, filters and permissions](github-guide-13-properties-filters-permissions.html)
- [Contents](github-guide.html)
