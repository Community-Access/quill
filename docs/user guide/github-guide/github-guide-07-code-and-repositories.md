# Chapter 7: Code and repositories

## What this chapter covers

You are here because you want the code itself, or the repository around it:
a file at an old tag, who changed a line, what a branch adds, a release to
publish, or a setting to change. Everything in this chapter happens in the
GitHub Workbench, under a repository's place in the tree, or from the line
you are on in the editor.

You will browse files at any branch, tag or commit, read blame and history,
compare branches, tag and publish releases, check a download, search all of
GitHub, and look after a repository: its settings, Pages site, wiki,
webhooks, packages, stars and watchers. You will also clone a repository to
your computer.

By the end you will know where each of these lives in the Workbench, which
key reaches it, and which ones ask before they change anything.

Reading a public repository works signed out. Anything that changes GitHub
needs a signed-in account, and blame and code search need one too.

**In QUILL Lite**, the Workbench is the same. QUILL Lite cannot send a file
back to GitHub from the editor, and it has no Local Git or Tools menu rows;
each section says where that matters.

## Browsing a repository's files

**Code > Files** under a repository (`Ctrl+Shift+5`) lists the default
branch a folder at a time. Enter on a folder opens it, and its first row, Up
one folder, comes back out. Enter on a file opens it in the editor
(`Ctrl+Enter` does the same, from the File menu's **Open in Editor**). Each
row says what it is, a file with its size or a folder.

For any branch, tag or commit, open **Files, History and Blame...** from
**Repository > Repository Actions...** (`Ctrl+Shift+G`). On a branch row it
starts at that branch. The **Repository Files** window has, in Tab order:

- **Branch, tag or commit:** (`Alt+B`). Pick a branch or tag from the list,
  or type any of them, including a commit's SHA, and press Enter. **Go**
  (`Alt+G`) does the same.
- **Files** (`Alt+F`), a tree of the repository at that point. Right or Enter
  opens a folder, fetching it the first time, and Left closes it. Each row
  says what it is: "status.py, 4.2 kilobytes", or "docs, folder".
- **Contents** (`Alt+C`), read only, where a file's text appears.
- The status line.
- **View File** (`Alt+V`), **Open in Editor** (`Alt+E`), **README**
  (`Alt+R`), **History...** (`Alt+H`), **Blame...** (`Alt+L`) and **Close**.

Enter on a file shows it in Contents and says how many lines it has; so does
**View File**. **README** shows the README of the selected folder, of the
folder the selected file is in, or of the whole repository.

Some files have no text to show, and QUILL says why instead of filling
Contents with noise: a file over the 1 MB GitHub sends this way ("Open it on
GitHub instead"), a binary file, or one that is not UTF-8 text.

### Opening a file to edit

**Open in Editor** opens the file in QUILL's editor, through the same path as
a GitHub file link. Change it, then send it back with **Commit to GitHub...**
(see [Opening and saving files in QUILL](#opening-and-saving-files-in-quill)).

**In QUILL Lite**, Open in Editor opens the file's text as a new untitled
document, and you hear the file's name "from GitHub, opened as a new untitled
document. Save As keeps a copy." QUILL Lite cannot commit back to GitHub.

## Blame and file history

Select a file or a folder in Repository Files.

- **History...** (`Alt+H`) lists the commits that changed it, newest first:
  "Fix the status bar: alice, 4 November, 1a2b3c4".
- **Blame...** (`Alt+L`) says who last changed each part of a file.
  Neighbouring lines from the same commit are joined into one run, so you do
  not hear the same commit forty times: "Lines 10 to 14: alice, 4 November,
  1a2b3c4, Fix the status bar". Blame needs a signed-in account.

Both windows have the list (**Commits** or **Runs**), **Details** (`Alt+D`),
**Open Commit** (`Alt+O`), **Refresh** (`Alt+F`) and **Close**. `Alt+N` and
`Alt+P` move to the next and previous row from anywhere in the window, and
say the row when focus is elsewhere, so you can read Details and keep
stepping. At the ends you hear "Last one." or "First one." Enter opens the
commit on GitHub.

## From the line you are on

When the file you have open lives in a GitHub repository on your computer,
one you cloned or a worktree, **GitHub > From This Line** (`R`) answers
questions about the line your cursor is on, or the lines you have selected.
With workbench mode off, the same submenu is at **Tools > Git and GitHub >
GitHub > From This Line** (`L`). It opens the Workbench only when it must.

- **Copy GitHub Link to This Line** (`K`) puts a link to these lines on the
  clipboard, at the commit you have checked out, so it keeps showing the same
  text after the file changes: "Copied the link to lines 12 to 15."
- **Who Changed This Line?** (`O`) says the last commit that touched the
  line: "Changed by alice on 4 November 2026: Fix the status bar (1a2b3c4)."
  Press it again within ten seconds to open the pull request that brought the
  commit. Like the rest of Local Git, it needs the Developer profile or
  Developer Tools turned on.
- **Open the Pull Request for This Line** (`Q`) opens that pull request in
  the Workbench's Pull Requests, narrowed to its number. If the commit went
  straight to its branch, QUILL says so.
- **Open This Line on GitHub** (`U`) opens the same link in your browser.
- **New Issue from Selection...** (`L`) starts an issue that quotes what you
  selected, as a code block, under a link to those lines. It opens the
  Workbench's New Issue window filled in, and nothing is sent until you have
  read the preview and said yes. Select some text first.
- **Issues Mentioning This File** (`F`) opens the Workbench's **Search >
  Issues and Pull Requests** on the file's path.
- **Comment on This Line in the Open Pull Request...** (`T`) is for a branch
  you have checked out that has an open pull request. It asks for your
  comment, in Markdown, and posts it on these lines. If your copy and the pull
  request are at different commits, or the file has changes you have not
  committed, it says so and stops, because the line numbers would not match.
- **Open the GitHub Reference at the Cursor** (`R`) opens the Properties
  sheet of what is written where your cursor is, in the Workbench: `#42` or
  `GH-42` in this repository, `owner/name#42` in another, a commit hash,
  `@person`, or a GitHub address of an issue, pull request, discussion or
  commit. A bare `#42` is read from GitHub first, to know whether it is an
  issue or a pull request.
- **`Alt+Enter` on a reference** does the same without the menu: with the
  cursor on `#42`, `@person` or a GitHub address, `Alt+Enter` opens its
  Properties sheet. Anywhere else in the document `Alt+Enter` does what it
  always did.

The link points at the commit you have checked out. If that commit is not on
GitHub yet, QUILL says the link will not open until you push; if the file has
changes you have not committed, it says the line on GitHub may differ. All of
these need git, and **Help > Download Optional Components** has a portable
copy. Safe Mode turns them off. A private repository needs a signed-in account
to open its pull requests or to comment. None of the rows has a key out of the
box; give the ones you use a key in the Keymap Editor.

**In QUILL Lite** the eight rows sit straight in the GitHub menu, between
separators, with the same letters, because QUILL Lite's GitHub menu has no
submenus. With workbench mode off, they are in the Command Palette.

## Opening and saving files in QUILL

QUILL has three more ways in, on **File > Open from Remote**. They are
QUILL's alone.

- **GitHub Repository...** opens a simple file browser: your account, a
  **Repository (owner/repo):** box with **Load**, **Branch or tag:**, the
  current path and a file list. Enter opens a folder or a file; Backspace goes
  up a level; `F5` refreshes. The buttons are **Open File**, **Go Up**,
  **Refresh**, **Show all refs**, **Copy URL** and **Cancel**.
- **GitHub File URL...** takes the address of one file, such as
  `https://github.com/owner/repo/blob/main/docs/readme.md`, and opens it.
- **Commit to GitHub...** sends your changes back. It works on a file you
  opened from GitHub, and asks for a commit message, starting with "Update"
  and the file's name. QUILL commits to the same repository, branch and path.
  If the file changed on GitHub since you opened it, QUILL tells you, so you
  never overwrite someone else's change. `Ctrl+S` saves on your computer
  only; sending is always this separate command.

To commit several files from your computer at once, use **Commit Multiple
Files...** on **Tools > Git and GitHub > GitHub**.

In workbench mode these rows are in the GitHub menu: **Commit to GitHub...**
is there directly, and **GitHub File URL...** and **Commit Multiple Files...**
are under Repository Actions. Chapter 2 lists the whole menu.

## Cloning a repository

Cloning copies a whole repository to your computer, with its history, so you
can work on it in a folder of your own. Both editors can do it:

- In QUILL, **File > Open from Remote > Clone Repository...**.
- In QUILL Lite, **File > Clone Repository...**: `Alt+F`, then `Y`.
- In workbench mode, in either editor, **GitHub > Clone Repository...**:
  `Alt+G`, then `C`.
- In the Workbench, **Clone...** on a repository row, or **Clone
  Repository...** in Repository Actions.

The Clone Repository window asks two things:

- **Repository (owner/name or address)**: type `owner/name`, such as
  `community-access/quill`, or paste the address from GitHub's green Code
  button, or any GitHub page in the repository. When the document you have
  open is already in a GitHub repository, its name is filled in.
- **Into this folder**: QUILL makes a new folder inside it, named after the
  repository. **Browse...** picks the folder. It starts in the GitHub folder
  in your Documents folder when you have one, and in Documents otherwise.

Press **Clone**. QUILL says "Cloning" and the repository's name, and then,
once, how it went: "Cloned" and the name, or why it could not, in Git's own
words. A large repository can take a minute or two, and you can keep working
while it runs.

When the clone is done, QUILL offers to open a file from it. In QUILL, when
the Developer profile is on, it also offers **Open as Project**.

A few things worth knowing:

- **Private repositories work when you are signed in.** QUILL hands your
  token to Git for this one command only. It is never written into the
  copy's settings, its remote address, or QUILL's log.
- **Cloning needs Git for Windows.** If it is missing, QUILL says so and
  offers to open its download page.
- **The folder must be new or empty.** If a folder with the repository's name
  already has something in it, QUILL asks you to choose another.
- **Safe Mode turns cloning off**, along with everything else that reaches
  the network.

## Branches

**Code > Branches** under a repository lists every branch, whether it is
protected, and its last commit. Its **Against default** column says "3
ahead, 1 behind main", "even with main" or "the default branch". Enter on a
branch opens its commits, and Backspace comes back.

A branch's context menu (`Shift+F10`) has:

- **Merge Into...**, which merges the branch into another on GitHub, as a
  merge commit, with no pull request. QUILL offers the default branch first
  and asks before merging. You hear "Merged topic into main as abc1234.", or
  that there was nothing to merge, or that the two conflict and nothing was
  merged. Branch protection still applies: a branch that needs a pull request
  refuses.
- **Download Source...**, the branch's files as a zip or tar.gz file, saved
  where you choose. A tag has it too.
- **Copy Name**, **Open in Codespaces...** (Chapter 9), and **Delete
  Branch...**, or the `Delete` key. To confirm, you type the branch's name.
  It cannot be undone from QUILL, and the default branch is never offered.

### Comparing branches

Select a branch and press **Compare Branches...** (`Ctrl+Shift+B`). QUILL
asks for the base branch, starting with the default branch, and compares the
selected branch against it. Two quicker ways skip the question:

- **Compare With Default** (`Ctrl+B`): a branch against the default branch,
  which is what it adds; or a tag, release or commit against the default
  branch, which is what has happened since.
- **Compare With Previous** (`Alt+Shift+B`): a tag or release against the
  one before it, or a commit against its parent.

The **Compare** window has two tabs:

- **Commits**, newest first, and how far ahead and behind the branches are.
  GitHub gives at most 250 commits for one comparison, so when there are more
  the tab says so, such as "Commits (250 of 1,204, newest)".
- **Changed Files**, which walks each file's differences the same way the
  pull request diff does.

**Open on GitHub** (`Alt+G`) opens the comparison in your browser, and **Open
Pull Request** (`Alt+P`) opens the pull request already open between the two,
greyed when there is none. Comparing only reads, so it works signed out. A
`compare` link pasted into **Open GitHub Address...** (`Ctrl+L`) opens the
same window.

## Setting a commit's status

People who run their own checks outside GitHub Actions, in a test lab or by
hand, report the result on the commit as a status. On a commit row, **Set
Status...** asks what happened (passed, failed, still running, or could not
run), the check's name as it shows among the commit's checks (it starts as
`manual`), a few words, and a link to the details if there is one. It shows
beside the commit's other checks, and branch protection can require it like
any other. You hear "Set lab tests to failed on commit 3f9a2c1." You need
write access.

## Commit comments

On a commit row, under **Code > Commits** or in a branch's commits, the
context menu has **Commit Comments...**. A tag has it too. It opens the
commit's comments, oldest first, in **Comments:** (`Alt+C`). Each reads as who
wrote it, the date and its first line: "octocat, 2026-11-07: Looks good". A
comment on a line of a file says where, such as "on docs/readme.md line 12".
**Selected comment:** (`Alt+M`) has the whole of it.

To add one, type it in **New comment:** (`Alt+N`) and press **Post Comment**
(`Alt+P`). It goes on the whole commit unless you name a file in **File,
optional:** (`Alt+F`); give a **Line, optional:** (`Alt+L`) as well to put it
on one line of that file. You hear "Comment posted on" and where only when
GitHub sends the comment back. **Refresh** (`Alt+R`) reads the list again.
Signed out you can read the comments, but posting needs an account.

**Code > Commit Comments** lists every commit comment in the repository.
Change... rewrites one of yours, and `Delete` deletes it after asking.

## Tags and releases

**Code > Tags** lists each tag and the commit it points at.

To make a tag on its own, without a release, press `Ctrl+N` (**File > New
Here...**) in Tags. QUILL asks for the tag's name, such as `v1.2.0`, and
which branch, tag or commit to put it on, starting with `main`. It refuses a
name git would refuse, and a tag that already exists, before sending
anything. Then it asks for a message. Leave it empty for a lightweight tag,
which is only a name for a commit. Type a message, such as "First beta", and
the tag is annotated: git keeps the message with who made it and when, the
way most projects tag a release. You hear "Made annotated tag v1.2.0 on main,
commit 3f9a2c1." Cancel at any of the three questions and nothing is made.

On a tag's context menu:

- **Read Tag Message** says who made an annotated tag, when, and its
  message: "v1.2.0, tagged by Jeff Bishop on 2026-11-18: First beta". For a
  lightweight tag it says there is no message.
- **Delete Tag...**, or `Delete`, asks first. If a release is built on the
  tag, the question says so, because deleting the tag leaves the release
  without one. The commit stays; only the name goes.

**Releases** under a repository (`Ctrl+Shift+6`) lists each release: its tag,
name, how many times its files have been downloaded, how many files it has,
when it was made, and whether it is a draft or a pre-release. Enter on a
release lists its files with their download counts and sizes, and Backspace
goes back. A download count is how many times the file was fetched, not how
many people fetched it, and QUILL says so.

A file's context menu has **Download**, **Copy Link**, **Attestations...**
and **Delete Asset...**. Deleting a file asks first, and its download count
goes with it.

### Writing release notes

**Draft Release Notes...**, on a release's context menu, asks GitHub to write
notes from the pull requests merged since the previous release. Give it the
release's tag, the previous tag, and, for a tag that does not exist yet, the
branch or commit it will point at. Press **Generate Draft**: **Draft name:**
and **Draft body (Markdown):** fill in, ready to read, and **Copy Draft**
copies them. Nothing is published, and the window says so.

**GitHub's Release Notes...**, under More on the same menu, shows the notes
GitHub writes from the changes since another tag, in a window to read and
copy.

### Editing and publishing a release

Signed in, a release's context menu has:

- **Edit Release...** opens **Edit Release** and the tag, with **Release
  name:** (`Alt+N`), **Release notes:** (`Alt+O`), **Draft (not published
  yet)** (`Alt+D`) and **Pre-release** (`Alt+P`). To publish a draft, uncheck
  Draft and press **Save**. QUILL asks first, because publishing notifies
  everyone watching the repository and makes the release public. What you
  hear afterwards is built from GitHub's reply, so a publish GitHub did not do
  is never reported as done.
- **Upload Asset...** adds a file to the release. Choose the file and
  confirm. When it is done you hear "Uploaded", the file's name and size, and
  the release.
- **Delete Release...**, under More, deletes the release, its notes and its
  files. Choose **Delete the release, keep the tag**, which leaves the tagged
  commit as it was, or **Delete the release and its tag**. It cannot be
  undone.

To make a new release, press `Ctrl+N` in Releases, or use **Create
Release...** in Repository Actions. In QUILL it is also on
**Tools > Git and GitHub > GitHub**, which opens the Workbench's Releases and runs it there. It
asks for the repository, a tag, an optional title, whether GitHub should
write the notes from the merged pull requests or you will, and whether to
save it as a draft. You hear "Created draft release" or "Created published
release", with its tag and address.

**In QUILL Lite**, Create Release is not there: make the tag in Tags, then
publish the release on GitHub with **Open on GitHub**.

### Release evidence and attestations

**Release Evidence...**, on a release's context menu, gathers what vouches
for a release, and changes nothing. You hear one sentence, such as "v1.0:
Immutable; 4 of 4 checks pass; 1 deployments; 2 of 2 files attested.", and a
list follows with a line each:

- whether it is a draft or a pre-release, and when it was published;
- whether it is **immutable**: once GitHub has made a release immutable, its
  tag and files cannot change, so what you check now is what people download;
- the commit its tag points at (a draft whose tag does not exist yet has
  none);
- the checks on that commit, and which passed, failed or are still running;
- each deployment of that commit: which environment, its latest state, when
  and by whom;
- each file, by its digest, with GitHub's **artifact attestations** for it,
  such as build provenance or a software bill of materials.

QUILL reads GitHub's attestation records but does not check their
signatures; the list says so, and `gh attestation verify` is the tool that
does. A part GitHub would not show you is said as "Could not read", never as
none, so a missing permission is never mistaken for missing evidence.

**Attestations...**, on one file in a release's file list, is the same for
that file alone. The release's **Properties...** (`Alt+Enter`) says whether it
is immutable, and a file's says its digest.

### Checking a download

**Check Download...**, on one file in a release's file list, checks the copy
you downloaded. Download the file first (Enter opens it in your browser),
then choose **Check Download...**: an Open box starts in your Downloads
folder with the file's name filled in. QUILL works out the SHA-256 of your
copy on this computer, compares it with the digest GitHub has for the file,
read fresh, and says whether it matches. A copy that does not match is said
so, with the start of both values: do not use it, download it again. A file
GitHub keeps no digest for, one uploaded before GitHub kept them, is said as
not checkable, never as a match. A match says the bytes are the ones GitHub
holds; it does not say who built them, which is what the attestations'
signatures are for.

## Searching

**Search** (`Ctrl+3`) searches all of GitHub. Choose the kind of search under
it, press `Ctrl+E` to move to the filter box, type, and press Enter.

- **Issues and Pull Requests** finds both. Each row reads the repository, the
  number, the title, and which it is.
- **Code** finds code. Each row reads the file's path, the line that matched,
  and the words that matched; the details have each excerpt. GitHub gives no
  line number for these, so QUILL does not claim one. Code search needs a
  signed-in account.
- **Commits** finds commits: the repository, the short SHA, the first line of
  the message, who made it and when.
- **Repositories** finds repositories: the name, the description, the stars
  and the language, and whether it is archived or a fork.
- **Security Advisories**, **People and Organizations** and **Topics** are in
  Chapter 8 and Chapter 12.

GitHub's own qualifiers work in every one: `repo:owner/name`,
`language:python`, `author:alice`, `is:open`. A query GitHub cannot run comes
back with GitHub's reason. Plain words in the filter box of any other list
only narrow the rows already there.

`Ctrl+N` in a search keeps it under **Saved Searches** (`Ctrl+8`). There,
Enter runs one, **Pin as Node** gives it a place of its own in the tree,
**Unpin Node** takes that place away, and **Remove Saved Search** forgets it.
**Go > Run a Saved Search** lists them from anywhere.

## Forks, templates and topics

A fork is your own copy of someone else's repository. **Fork Repository...**
in Repository Actions (`Ctrl+Shift+G`) makes one, in your account or an
organization; in QUILL it is also on **Tools > Git and GitHub > GitHub**. On a
fork, **Code > Upstream** opens the repository it came from, and **People >
Forks** under any repository lists its forks. The repository's
**Properties** (`Alt+Enter`) has a **Fork** page: whether it is a fork, what
it was forked from, and, for an organization's private repositories, whether
forking is allowed.

**Topics** are the tags that help people find a repository. They are on the
**General** page of its Properties: separate them with commas, lower-case
letters, numbers and hyphens, up to 20. Clear the box to remove them all.

A **template repository** is one other repositories can start from. Whether
a repository is one is on the **Templates** page of its Properties.

On a repository row's context menu (`Shift+F10`):

- **Sync Fork with Upstream...** brings a fork up to date with the repository
  it came from, after asking. QUILL counts the new commits first, so it can
  say "Merged 3 commits from" the upstream, or "Already up to date with" it.
- **Create Repository from This Template...** opens Create Repository with
  the template filled in: give it a name, an optional description and owner,
  choose private or public, and whether to copy all of the template's
  branches or only its default one.
- **Delete Repository...** is under
  [Looking after a repository](#looking-after-a-repository).

## The community profile

**Insights > Community Profile** under a repository checks it for the files
GitHub recommends. The first row says the score and what is present and
missing; then one row each says "present" or "missing" for the README,
licence, contributing guide, code of conduct, issue templates and pull
request template. **Templates** under the repository is where you make the
missing ones (Chapter 12).

## Dependabot, code owners and configuration

These live on **Templates** under a repository, beside the community files,
and on **Repository Actions...** (`Ctrl+Shift+G`).

### Dependabot

The **Dependabot configuration** row opens `.github/dependabot.yml` as a
list of entries, one row each: "pip in /, weekly on Monday at 09:00, up to 5
pull requests, labels dependencies". **Edit Entry...** has the ecosystem, the
directories, how often, the day, time and time zone, the most open pull
requests and the target branch. Groups, ignore rules and registries are kept
as they are and counted on the row. **What Dependabot would say** lists what
it would refuse, such as two entries for the same ecosystem and folder, and
Save refuses while any is listed. When the file is missing, the row starts
one that keeps the repository's actions up to date.

On a pull request Dependabot opened, **Dependabot Commands...** lists its
commands with what each does: rebase, recreate, merge or squash and merge
when checks pass, cancel merge, reopen, close, and ignore this dependency or
this major, minor or patch version. The one you choose is posted as a
comment after QUILL asks, and Dependabot answers in the thread.

### Code owners

The **CODEOWNERS** row opens a table of rules, one row each with its line,
path pattern and owners. Order matters: **the last matching rule wins**, so
**Move Up** and **Move Down** can change who reviews a folder. **Add
Rule...** adds at the end, where a rule wins over everything above it. Notes
in the file are kept. **Who owns this path** answers with the rule that wins,
as GitHub decides. **Check Owners** asks GitHub whether each owner exists and
can write. **Problems found** lists rules GitHub would skip by their shape,
the problems GitHub itself reports for the file on the default branch, and
what Check Owners found. **Settings > CODEOWNERS Problems** under the
repository lists GitHub's own report on its own.

**Who Owns This?**, on a file or folder in Files, says its owners and the
line of the rule that wins. **Who Owns This Path?...**, in Repository
Actions, asks for any path.

### Comparing configuration with another repository

**Compare Configuration With Another Repository...**, in Repository Actions,
compares this repository's workflows, issue and pull request templates,
discussion forms, community files, Dependabot file and CODEOWNERS with another
repository, or with the owner's `.github` repository, which it offers first.
From an organization's `.github` repository its starter workflows count too.
The window checks every file that is missing here or differs, each with the
lines added and removed, and shows the selected file's differences to read
line by line. Files that are the same, or only here, are counted and kept.
**Propose Update** asks once more, then opens one pull request with the
checked files and a summary of each. Nothing changes until that pull request
is merged; QUILL never pushes these to the default branch.

## Insights

**Insights** under a repository (`Ctrl+Shift+0`) has four places.

**Traffic and Contributors** gives the last 14 days in one sentence, such as
"community-access/quill: 120 views (30 unique) and 14 clones (6 unique) in
the last 14 days, 9 contributors." Each row after it is one figure: views and
clones on each day, the sites that sent people, the most visited pages, and
each contributor's commits. Traffic figures need push access. Without it,
QUILL says so and still lists the contributors.

**Health Snapshot** is a set of counts that stays on this computer and ranks
nobody. It loads only when **Load the repository Health Snapshot** is checked
on the Privacy page of **Workbench Options** (`Ctrl+Shift+O`).
It says how many ready pull requests are waiting for a review and how long
the oldest has waited, without naming who was asked.

**Community Profile** is described above.

### Commit activity, as tables

GitHub's Insights pages draw a repository's history as charts. **Insights >
Commit Activity** reads the same numbers as rows, each a whole sentence,
newest first:

- **Last 4 weeks**: "Last 4 weeks: 30 commits, 10 by the owner."
- **Commits each week**, for the last twelve weeks, with the busiest day:
  "Commit activity, week of 2026-11-09: 14 commits. Busiest Tuesday, 5."
- **Lines each week**: "Code frequency, week of 2026-11-09: 1,204 lines
  added, 310 removed."
- **The ten busiest hours of the week**, GitHub's punch card: "Busiest hour 1:
  Tuesdays at 14:00 UTC, 23 commits." Times are UTC (Coordinated Universal
  Time), as GitHub counts them.
- **Each contributor**, most commits first: "Contributor sam: 120 commits,
  3,000 lines added, 900 removed."

The first row sums it up. GitHub works these numbers out in the background,
so the first time you open a repository's Commit Activity the first row may
say "GitHub is still counting its statistics; refresh in a moment." Press
`F5` a few seconds later. A repository with no commits, or with 10,000 commits
or more, gets no statistics from GitHub at all, and QUILL says so rather than
showing an empty table. Anyone can read these for a public repository.

## Looking after a repository

### Repository settings in Properties

`Alt+Enter` on a repository opens its Properties: a page for each part of
GitHub's settings. You change a field, and nothing is sent until you save;
Chapter 13 has how saving and undoing work.

- **General**: the name, description, website, topics and default branch.
  Renaming moves the repository, and GitHub forwards the old address.
- **You**: whether you have starred it, and your **Watch level** (below).
- **Fork** and **Templates**: above.
- **Features**: issues, projects, the wiki and discussions on or off, and
  whether web commits need a sign-off.
  **Sponsor button links** reads the links from the repository's
  FUNDING.yml. Whether the Sponsor button shows is a setting GitHub's API
  cannot change, so the field only reads and says so.
- **Merging**: which merge methods are allowed, auto-merge, suggesting branch
  updates, deleting head branches after merging, and the default title and
  message of a squash merge and of a merge commit.
- **Branches and Rules**, **Access**, **Actions** and **Security**: branch protection and
  rulesets, who has access, whether Actions runs and what its token may do,
  and Dependabot, private vulnerability reporting, secret scanning and push
  protection. Chapter 13 covers rules and access.
- **Pages**: the site's address and source, the custom domain and Enforce
  HTTPS. See [GitHub Pages](#github-pages).
- **Environments**, **Webhooks**, **Deploy Keys**, **Autolinks**, and
  **Secrets and Variables**: tables of each, which are also lists of their own
  in the tree.
- **Insights**: stars, forks, watchers and open issues, read only.
- **Danger Zone**: the visibility, private or public, and **Archived**. An
  archived repository is read only for everyone until it is unarchived.
  Making a repository public shows its whole history, and the save asks
  first.

**Delete Repository...**, on a repository row's context menu, deletes the
repository and everything in it: code, issues, pull requests, wiki and
releases. It cannot be undone, so you type the repository's full name,
exactly, to confirm. Deleting needs the token's `delete_repo` scope, and
QUILL says so if it is missing. Sign In with GitHub asks for it; a token you
made yourself needs it too (Chapter 1).

### From the editor's Tools menu

In QUILL, **Tools > Git and GitHub > GitHub** has the same jobs as editor
commands. Each opens the Workbench at the right place and does the job
there, so there is one way to do each thing:

- **Rename Repository...** and **Change Default Branch...** open the
  repository's Properties at General.
- **Change Visibility...** opens it at Danger Zone.
- **Configure Branch Protection...** opens it at Branches and Rules.
- **Delete Branch...** opens **Code > Branches**; press `Delete` on the
  branch.
- **Create Release...**, **Dispatch Workflow...** and **Security Alerts...**
  open Releases, Workflows and Alerts.
- **Browse Organization Repositories...** opens **Repositories >
  Organizations**.
- **Create Repository...**, **Fork Repository...** and **Commit Multiple
  Files...** open their own windows, in front of the Workbench.

**Create Repository...** asks everything GitHub can set when a repository is
made: the owner (blank for your own account, or an organization), the name, a
description and a website, and private or public. Then how it starts: from a
**template** (owner/name), with or without all of the template's branches; or
fresh, with a README, a **.gitignore template** and a **licence**. When
GitHub would refuse a combination, such as a README as well as a template,
the window stays open and the Problem box at its top says why, before
anything is sent. QUILL then offers to set up a folder on your computer that
stays in step with it.

The riskiest commands, renaming, changing visibility, deleting a branch or a
repository, and merging a pull request, all make you type a name or number.
A stray Enter on one of these is much harder to put right than most things.

### Transferring a repository

**Transfer Repository...** moves a repository to another person or to an
organization, with its issues, pull requests, wiki, stars and watchers. It is
on the Workbench's **Repository** menu (`Ctrl+Alt+T`) and in Repository
Actions. QUILL asks for the new owner,
then its name there (keep it to leave it unchanged), then, for an
organization, the teams there that should have access, by name, separated by
commas. A team the organization does not have is named before anything
moves.

Last it asks you to type the repository's full name, because you may lose
access to it and only the new owner can move it back.

Moving it to an organization you can create repositories in happens at once,
and you hear the new name, such as "Transferred jeff/notes; it is now
community-access/notes. The old address redirects." Moving it to a person
sends them a request they have a day to accept, and QUILL says so. Only an
owner or administrator of the repository can transfer it.

## GitHub Pages

**GitHub Pages** under a repository lists its website and recent builds.
`Ctrl+N` there is **Turn On Pages...**: from a branch (which branch, and the
top of it or `/docs`), or by a GitHub Actions workflow. On the site's row:

- **Check Site** says how the latest build went and whether a custom domain
  points at GitHub Pages.
- **Rebuild** asks GitHub for a fresh build.
- **Turn Off Pages...** stops publishing the site after asking, and leaves
  the repository as it is.

Everything else about the site is on the **Pages** page of the repository's
Properties. A site deployed by a workflow is deployed by the workflow's own
`actions/deploy-pages` step, so QUILL does not deploy one itself.

## The wiki

A wiki is a repository's own pages of documentation. GitHub keeps them as a
git repository of their own, with no API for the pages, so QUILL works on
them the way git does.

**Wiki** under a repository says whether its wiki is on. When it is, Enter
opens it on GitHub to read, and **Clone Wiki...** (`Ctrl+Alt+W`, on the
Repository menu) opens the Clone Repository window with the wiki's address
filled in, such as `community-access/quill.wiki`. Its pages arrive as
Markdown files, one for each page, named after the page's title.

The Wiki row's context menu also edits it here:

- **Edit Wiki Pages...** copies the wiki to QUILL's own folder the first
  time, and brings that copy up to date after that, then lists its pages,
  Home first. Enter on a page opens it in the editor. Change it and save it as
  you would any file; nothing reaches GitHub yet.
- **New Wiki Page...** asks for a title and makes the page's file, named the
  way GitHub names one (spaces become hyphens), then opens it.
- **Publish Wiki Changes...** says which pages changed and asks before it
  sends them, naming the wiki and your account. It asks for a short
  description of the change, commits the pages with it and pushes them, and
  everyone who can read the wiki sees them at once. When someone else
  changed the wiki meanwhile, your change goes on top of theirs. When you both
  changed the same lines, nothing is forced: it says so, and your edits stay
  committed in the copy for you to compare.

GitHub makes a wiki's git repository only when its first page is saved on the
web, so a brand-new wiki says to save its Home page there once first.

These commands use git, which Git for Windows provides. A wiki that is turned
off says so, and that its administrators turn it on in the repository's
Properties, on the Features page.

## GitHub Models prompt files

A prompt file is a `.prompt.yml` file that GitHub Models reads: the model and
its settings, the messages with their `{{variables}}`, rows of test data, and
the evaluators that judge each answer. **Prompt Files...** on a repository's
row, or on the repository's own place, lists every prompt file on the default
branch. The details read the selected one as its parts: its name, its model,
each message by role, how many test rows it has, its evaluators, and any
problem GitHub Models would trip on, such as a variable no test row fills.
**Open in Editor** opens the file to edit, and saving it there commits it, as
with any file you open from GitHub.

QUILL does not run a prompt or an evaluation, because it has no GitHub
Models client. Run one on the repository's Models page on GitHub, or with
`gh models run` and `gh models eval`.

## Opening github.dev

**Open in github.dev**, on a file of a repository or on a pull request, opens
GitHub's free web editor in your browser at exactly that file or pull
request. Nothing is created and nothing costs money; a codespace, which can
cost money, is Chapter 9.

## Webhooks, deploy keys and autolinks

Three of a repository's settings are lists under **Settings** in the
repository's place. Each needs you to administer the repository; anyone else
hears that instead of an empty list.

### Webhooks

A webhook is an address GitHub sends a message to when something happens: a
continuous integration server, a chat bot, a deployment script. **Webhooks**
lists them, one sentence each: "https://ci.example.org/hook: on, JSON, push
and pull_request, last delivery succeeded (200)." A webhook whose last
delivery failed says so, with GitHub's reason, which is usually the first
thing to check when a build stopped starting.

`Ctrl+N` there adds one: the address, JSON or form, which events (just push,
everything, or a list of the common ones to check), and a secret GitHub signs
each message with. The secret is typed in a password box. QUILL sends it once
and never shows, says or keeps it; GitHub never gives it back either, so to
change it you set a new one. GitHub sends a new webhook a ping straight away.

On a webhook:

- **Ping** sends it a test message.
- **Send Test Push** asks GitHub to send it the latest push as a test, if it
  listens for pushes.
- **Turn On or Off...** stops GitHub sending it anything, without deleting
  it, or starts it again.
- **Recent Deliveries...** lists what GitHub sent, newest first: "push at
  2026-11-18 09:30: succeeded (200)", or failed with the code it got back.
  Choose one to deliver it again, after a question.
- **Change Address or Secret...** offers the address to edit and a password
  box for a new secret; leave either as it is to keep it.
- **Delete Webhook...**, or `Delete`, asks first. Its delivery history goes
  with it.

An organization has webhooks of its own, which hear about every repository
in it: **Webhooks** under the organization's place, with the same commands.
They need you to own the organization.

### Deploy keys

A deploy key is an SSH key that reaches this one repository only, so a server
can clone or pull it without anyone's account. **Deploy Keys** lists them:
"Deploy key CI, read only, ED25519, SHA256:ZkAs..., added 2026-01-02, last
used 2026-11-17." `Ctrl+N` adds one from a `.pub` file or a paste, then asks
for a name and whether it may only read, or push too. A private key, or
anything that is not an SSH public key, is refused before anything is sent.
**Delete Deploy Key...** asks first.

### Autolinks

An autolink turns a prefix into a link to another system, so `TICKET-123` in
an issue links to your tracker. **Autolinks** lists them: "TICKET- links to
https://jira.example.org/browse/TICKET-<num>, numbers only." `Ctrl+N` asks for
the prefix, the address with `<num>` where the reference goes, and whether
letters may follow the prefix or only numbers. **Delete Autolink...** asks
first; text already written keeps its words, without the link.

To make a webhook, deploy key or autolink the same across many repositories,
use **Settings by Name** under Across Repositories (Chapter 12).

## Watching, starring and following

On a repository row's context menu:

- **Star or Unstar** asks which, then does it: "Starred owner/name."
- **Watch or Unwatch** opens the repository's Properties at the **You** page,
  on **Watch level**: **all activity**, **participating and mentions**, or
  **ignore**. Watching only some kinds of activity, such as releases only, is
  set on GitHub's own page, because GitHub has no API for it; the **Custom
  watching** field says so, and **Open on GitHub** (`Shift+Enter`) goes
  there.

**Repositories > Starred** and **Repositories > Watched** list what you star
and watch, and **People > Watchers** under a repository lists who watches it.

On a person's row, **Follow or Unfollow** asks which, then says "You now
follow" them, or that you no longer do. **People I Follow** and **My
Followers** are under People.

### Star lists

GitHub lets you sort your stars into lists of your own, such as "Screen
readers" or "Tools I use". **Repositories > Star Lists** lists every
repository on every list, each row starting with its list: "Screen readers:
nvaccess/nvda, NVDA". They are ordinary repository rows, so Enter opens the
repository and Star, Watch and Clone work as anywhere else. The place's note
names any list that is empty.

- **New Star List...**: press `Ctrl+N` in Star Lists. QUILL asks for the
  name, up to 32 characters, a description you can leave empty, and whether
  only you or everyone can see it.
- **Star Lists...**, on any repository's context menu, shows your lists with
  the ones it is on already checked. Check and uncheck, then OK. You hear
  "nvaccess/nvda is now on: Screen readers, Tools I use."
- **Rename or Delete Star List...**, on a row in Star Lists, works on that
  row's list: rename it or change its description, make it private or public,
  or delete it. Deleting a list leaves its repositories starred.

## Packages

GitHub Packages holds what a project publishes besides its code: container
images, and npm, Maven, RubyGems and NuGet packages. **Repositories > My
Packages** lists yours as one list, each row whole on its own: "container
quill-engine: private, 12 versions, from community-access/quill, updated
2026-11-12." GitHub keeps packages by type, so QUILL asks for each type in
turn; the list is every type together, in alphabetical order.

A package's context menu has:

- **Show Details**, **Open on GitHub** and **Copy Link**.
- **Show Versions** lists every version in a window to read.
- **Delete Package Version...** lists the versions, newest first, with their
  tags, such as "sha256:bbb, tagged latest, 1.2, updated 2026-11-12". Choose
  one, and QUILL asks before deleting it.
  To confirm, you type the package's name, because a version's own name is
  often a long digest.
  GitHub will not delete a package's only version, or one downloaded more
  than 5,000 times, and QUILL says so.
- **Restore Package Version...** lists the versions deleted in the last 30
  days and brings back the one you choose.
- **Delete Package...** deletes the package and every version, after you type
  its name.

GitHub keeps a deleted package or version for 30 days. `Ctrl+N` in My
Packages, or in an organization's Packages, brings back a whole deleted
package: QUILL asks its type and name, and says "Restored the npm package
left-pad.", or that GitHub has no such deleted package. Reading private
packages needs the `read:packages` permission and deleting needs
`delete:packages`. Sign In with GitHub asks for both; an account signed in
before they were asked for is told to sign in again rather than shown an
empty list.

An organization's packages are under **Packages** in the organization's
place, and a person's under **Packages** in theirs.
A repository's own are under **Packages** in the repository's place: the
packages its owner published from it. Another person's packages can be read,
and their versions listed, but only they can change them.

## Gists

A gist is a small piece of text or code you share, with its own history.
**Gists > My Gists** (`Ctrl+5`) lists yours, each with its description and
whether it is public or secret. Chapter 12 has every gist command; in short:

- **New Gist** (`Ctrl+N` in My Gists) starts from the editor that opened the
  Workbench: the selection if there is one, otherwise the whole document,
  under the document's file name.
- **Edit Gist...** (Enter on a gist) reads it from GitHub first.
- **Star or Unstar**, **Comments...**, **History...**, **Forks...**, **Fork
  Gist**, and **Delete Gist...**, which asks first.

The gist window has **Description:** (`Alt+D`), **Public gist** (`Alt+B`)
when the gist is new, **Files:** (`Alt+F`), and **File text:** (`Alt+T`) for
the chosen file. **Add File...** (`Alt+A`), **Rename File...** (`Alt+N`) and
**Delete File...** (`Alt+L`) change the list. Delete File asks first, and a
gist always keeps at least one file. Nothing goes to GitHub until **Create
Gist** or **Save Gist**; Cancel sends nothing.

A secret gist is unlisted, not private: anyone with its link can read it, and
GitHub does not let you switch a gist between public and secret later. When
you save, QUILL says what GitHub confirmed, such as "Gist saved. GitHub
confirmed: rename notes.md to todo.md." A file over about a megabyte reaches
QUILL cut short, so it is read only in the gist window and never sent back;
you can still rename it.

## Other places under a repository

Every repository's place has more lists, each read the same way:

- **Overview**, the repository at a glance.
- **People > Contributors and People**, **Collaborators and Team Access**,
  **Invitations** and **Watchers** (Chapter 13 has access).
- **Labels** and **Milestones** (Chapter 4).
- **Deployments and Environments** (Chapter 6).
- **Activity > All Issue Comments**, **Push Activity** and **My Notifications
  Here**, read only.
- **Code > Codespaces** (Chapter 9).

## A walk-through: from a branch to a tagged release

This uses the practice repository. If you have not made it, choose **Help >
Practice on GitHub...** (`Ctrl+Alt+P`) in the Workbench first.

1. Press `Ctrl+L`, type `quill-practice` with your login in front, such as
   `jeff/quill-practice`, and press Enter. The repository gets a place in
   the tree.
2. Press `Ctrl+Shift+5`. You hear the Files list. Arrow to `README.md` and
   press Enter: it opens in the editor. Press `Alt+Tab` to come back to the
   Workbench.
3. Press `Ctrl+Shift+G`, choose **Files, History and Blame...**, Tab to
   Files, select `README.md`, and press `Alt+H`. You hear the commits that
   changed it. Press `Alt+N` to step through them, then Escape.
4. Arrow up the tree to **Code > Branches** and select `fix-greeting`. You
   hear how far it is ahead of the default branch. Press `Ctrl+B`: the
   Compare window opens on its Commits tab. Press `Ctrl+Tab` for Changed
   Files, then Escape.
5. Go to **Code > Tags** and press `Ctrl+N`. Type `v0.1.0`, press Enter, keep
   `main`, press Enter, type "First practice tag" as the message, and press
   Enter. You hear "Made annotated tag v0.1.0 on main" and the commit.
6. In QUILL, press `Ctrl+Shift+6` for Releases, then `Ctrl+N`. Keep the
   repository, type `v0.1.0` as the tag, answer Yes to GitHub writing the
   notes and Yes to a draft. On the new release, press
   `Shift+F10` and choose **Release Evidence...**: you hear one sentence
   about it, and the list follows.
7. To tidy up, `Delete` on the release removes it after asking; choose
   **Delete the release and its tag**.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has **Make a repository to practise on**,
which makes the practice repository and walks round it, including its files
and branches.

---

- Previous: [Chapter 6: Actions and checks](github-guide-06-actions-and-checks.html)
- Next: [Chapter 8: Discussions and security](github-guide-08-discussions-and-security.html)
- [Contents](github-guide.html)
