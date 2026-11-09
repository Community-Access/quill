# Chapter 7: Code and repositories

## What this chapter covers

This chapter is about the code itself and the repository around it. It covers
browsing files at any branch, tag or commit, blame and file history, opening a
file to edit, branches and comparing them, commit comments, tags and
releases, searching across GitHub, forks, templates and topics, the community
profile, insights, looking after a repository, watching, starring and
following, writing and editing gists, and cloning a repository to your
computer.

## Browsing a repository's files

**Files...** (`Alt+F`) in GitHub Items, or **Browse Repository Files...** on
any row's context menu, opens **Repository Files:** and the repository. It
reads public repositories signed out.

In Tab order:

- **Branch, tag or commit:** (`Alt+B`). Pick a branch or tag from the list,
  or type any of them, including a commit's SHA, and press Enter. **Go**
  (`Alt+G`) does the same.
- **Files** (`Alt+F`), a tree of the repository at that point.
- **Contents** (`Alt+C`), read-only, where a file's text appears.
- The status line.
- **View File** (`Alt+V`), **Open in Editor** (`Alt+E`), **README**
  (`Alt+R`), **History...** (`Alt+H`), **Blame...** (`Alt+L`) and **Close**.

In the tree, Right or Enter opens a folder, fetching it the first time, and
Left closes it. Each row says what it is: "status.py, 4.2 kilobytes", or
"docs, folder". Enter on a file shows it in **Contents** and says how many
lines it has; so does **View File**.

**README** shows the README of the selected folder, or of the folder the
selected file is in, or of the whole repository.

Some files have no text to show, and QUILL says why instead of filling
Contents with noise: a file over the 1 MB GitHub sends this way ("Open it on
GitHub instead"), a binary file, or one that is not UTF-8 text.

### Opening a file to edit

**Open in Editor** (`Alt+E`) closes Repository Files and opens the file in
QUILL's editor, through the same path as a GitHub file link. You can then
change it and send it back with **File > Open from Remote > Save to
GitHub...**, below.

**In QUILL Lite**, **Open in Editor** opens the file's text as a new untitled
document, and you hear the file's name "from GitHub, opened as a new untitled
document. Save As keeps a copy." QUILL Lite cannot save back to GitHub.

## Blame and file history

Select a file, or a folder, in Repository Files.

- **History...** (`Alt+H`) lists the commits that changed it, newest first,
  up to 50: "Fix the status bar: alice, 4 November, 1a2b3c4".
- **Blame...** (`Alt+L`) says who last changed each part of a file. Rather
  than one row per line, which would mean hearing the same commit forty times,
  neighbouring lines from the same commit are joined into one run: "Lines 10 to
  14: alice, 4 November, 1a2b3c4, Fix the status bar". Blame needs a
  signed-in account.

Both windows have the list (**Commits** or **Runs**), **Details** (`Alt+D`),
**Open Commit** (`Alt+O`), **Refresh** and **Close**. `Alt+N` and `Alt+P` move
to the next and previous row from anywhere in the window, and say the row if
focus is somewhere else, so you can read Details and keep stepping. At the
ends you hear "Last one." or "First one." Enter opens the commit on GitHub.

In the Blame window, `Alt+R` belongs to the **Runs** list, so reach **Refresh**
with Tab.

## Opening and saving files in QUILL

QUILL has three more ways in, on **File > Open from Remote**. These are QUILL's
alone.

- **GitHub Repository...** opens a simpler browser: your account, a
  **Repository (owner/repo):** field, **Branch or tag:**, the current path and a
  file list. Enter opens a folder or a file; Backspace goes up a level; F5
  refreshes. The buttons are **Open File**, **Go Up**, **Refresh**,
  **Show all refs**, **Copy URL** and **Cancel**.
- **GitHub File URL...** takes the address of one file, such as
  `https://github.com/owner/repo/blob/main/docs/readme.md`, and opens it.
- **Commit to GitHub...** sends your changes back. It was called Save to
  GitHub until November 2026; it is the same command. It works on a file you
  opened from GitHub, and asks for a commit message, starting with "Update"
  and the file's name. QUILL commits to the same repository, branch and path.
  If the file changed on GitHub since you opened it, QUILL tells you, so you
  never overwrite someone else's change. Pressing `Ctrl+S` saves on your
  computer only; sending is always this separate command.

To commit several files from your computer at once, QUILL has
**Commit Multiple Files...** on **Tools > Git and GitHub > GitHub**.

In workbench mode these rows are in the GitHub menu: **GitHub File URL...**,
**Commit to GitHub...**, and **Commit Multiple Files...** in its
**Repository Admin** submenu. Chapter 2 lists the whole menu.

## Cloning a repository

Cloning copies a whole repository to your computer, with its history, so you
can work on it in a folder of your own. Both apps can do it:

- In QUILL, **File > Open from Remote > Clone Repository...**.
- In QUILL Lite, **File > Clone Repository...**: `Alt+F`, then `Y`.
- In workbench mode, in either app, **GitHub > Clone Repository...**:
  `Alt+G`, then `C`.

The Clone Repository window asks two things:

- **Repository (owner/name or address)**: type `owner/name`, such as
  `community-access/quill`, or paste the address from GitHub's green Code
  button, or any GitHub page in the repository. When the document you have
  open is already in a GitHub repository, its name is filled in for you.
- **Into this folder**: the folder the copy goes in. QUILL makes a new folder
  inside it, named after the repository. **Browse...** picks the folder. It
  starts in the GitHub folder in your Documents folder when you have one, and in
  Documents otherwise.

Press **Clone**. QUILL says "Cloning" and the repository's name, and then,
once, how it went: "Cloned" and the name, or why it could not, in Git's own
words. A large repository can take a minute or two. You can keep working while
it runs.

When the clone is done, QUILL offers to open a file from it. In QUILL, when
the Developer profile is on, it also offers **Open as Project**, which opens
the new folder as your project.

A few things worth knowing:

- **Private repositories work when you are signed in.** QUILL hands your
  GitHub account's token to Git for this one command only. It is never written
  into the copy's settings, its remote address, or QUILL's log, so nothing in
  the new folder holds your token afterwards. To pull or push later from
  another tool, that tool signs in its own way.
- **Cloning needs Git for Windows.** If it is not installed, QUILL says so and
  offers to open its download page. Install it, then choose Clone Repository
  again.
- **The folder must be new or empty.** If a folder with the repository's name
  already has something in it, QUILL asks you to choose another folder rather
  than mixing the two.
- **Safe Mode turns cloning off**, along with everything else that reaches the
  network.

## Branches

The **Branches** view lists every branch, whether it is protected, and its
last commit. Enter on a branch opens its commits, in the Commits view, and
Backspace comes back.

Signed in, the context menu has **Delete Branch** and the branch name. To
confirm, you type the branch's name. It cannot be undone from QUILL.

### Comparing branches

Select a branch and press **Compare...** (`Alt+C`) or `Ctrl+Shift+B`. QUILL
asks for the base branch, starting with `main`, then the branch to compare
with it, starting with the one you selected. The window **Compare** and the
two branches has two tabs:

- **Commits**, with every commit between them, and how far ahead and behind
  the branches are.
- **Changed Files**, which walks each file's differences the same way the pull
  request diff does.

**Open on GitHub** (`Alt+G`) opens the comparison in your browser. Comparing
only reads, so it works signed out.

## Commit comments

On a commit row, in the Commits view or in a branch's commits, the context
menu has **Commit Comments...**. It opens the commit's comments, oldest first.
Each reads as who wrote it, the date and its first line: "octocat, 2026-11-07:
Looks good". A comment on a line of a file says where, such as "on
docs/readme.md line 12". Tab reaches the whole comment.

To add one, type it in **New comment** (`Alt+N`) and press **Post Comment**
(`Alt+P`). It goes on the whole commit unless you name a file in **File,
optional** (`Alt+F`); give a **Line, optional** (`Alt+L`) as well to put it on
one line of that file. You hear "Comment posted on" and where only when GitHub
sends the comment back, and then the list is read again. **Refresh** (`Alt+R`)
reads it again whenever you like. As a guest you can read the comments, but
posting needs a signed-in account.

## Tags and releases

The **Tags** view lists each tag and the commit it points at.

The **Releases** view lists each release: its tag, name, how many times its
files have been downloaded, how many files it has, when it was made, and
whether it is a draft or a pre-release. Enter on a release lists its files
with their download counts and sizes. Enter on a file opens its download in
your browser, and Backspace goes back to the releases. A download count is how
many times the file was fetched, not how many people fetched it, and QUILL
says so.

### Writing release notes

**Draft Release Notes...**, on a release's context menu, asks GitHub to write
notes for a release from the pull requests merged since the previous one. Give
it the release's tag, the previous tag, and, for a tag that does not exist
yet, the branch or commit it will point at. Press **Generate Draft** and the
name and notes appear, ready to read and copy with **Copy Draft**. Nothing is
published; it says so.

### Editing and publishing a release

Signed in, a release's context menu and **Actions...** have:

- **Edit Release...** opens **Edit Release** and the tag, with
  **Release name:** (`Alt+N`), **Release notes:** (`Alt+O`),
  **Draft (not published yet)** (`Alt+D`) and **Pre-release** (`Alt+P`).
  To publish a draft, uncheck Draft and press **Save**. QUILL asks first,
  because publishing notifies everyone watching the repository and makes the
  release public. What you hear afterwards is built from GitHub's reply, so a
  publish GitHub did not do is never reported as done.
- **Upload Asset...** adds a file to the release. Choose the file, confirm,
  and QUILL says how far it has got at 25, 50 and 75 percent, then
  "Uploaded" with the file's name and size.
- **Delete Asset**, inside a release's file list, removes a file after asking.
  Its download count goes with it.

In QUILL, **Tools > Git and GitHub > GitHub > Create Release...** makes a new
release: a tag, an optional title, your own notes or GitHub's, and whether to
publish it now or keep it as a draft.

## Searching

Search in GitHub Items stays inside one repository (Chapter 2). Explore
searches all of GitHub. Choose one of the search views in **View:**
(`Alt+V`), type in **Global search:** (`Alt+G`) and press Enter.

- **Global issue and PR search** finds issues and pull requests. Each row
  reads the repository, the number, the title, and which it is.
- **Code search** finds code. Each row reads the file's path, the line that
  matched, and the words that matched. Details has each excerpt. GitHub does
  not give a line number for these, so QUILL does not claim one. Code search
  needs a signed-in account.
- **Commit search** finds commits: the repository, the short SHA, the first
  line of the message, who made it and when.
- **Repository search** finds repositories: the name, the description, the
  stars and the language, and whether it is archived or a fork.

GitHub's qualifiers work in every one: `repo:owner/name`, `language:python`,
`author:alice`, `is:open`. A query GitHub cannot run comes back with GitHub's
reason.

**Save Search** keeps the current query on this computer. **Saved Searches...**
(`Alt+S`) lists them, and choosing one runs it. On a search view's context
menu, **Remove Saved Search** forgets the one in the box.

### The repository chooser

**Repository chooser**, in **View:**, lists the repositories you are most
likely to want: your pinned ones first, then the ones you opened recently,
then your own, your starred and your watched repositories. Enter on one sends
it to GitHub Items.

## Forks, templates and topics

These are on the **Repository Actions for** submenu of Explore's context
menu, which acts on the selected repository row, or on the repository in
**Repository:** when you are in one of the repository views. You need to be
signed in.

- **Sync Fork with Upstream...** brings a fork up to date with the repository
  it was forked from. QUILL counts the new commits first, so it can say
  "Merged 3 commits from" the upstream, or "Already up to date with" it.
- **Set Topics...** sets the repository's topics, the tags that help people
  find it. The box starts with the current ones. Separate them with spaces or
  commas, or leave it empty to remove them all. Topics are lower-case letters,
  numbers and hyphens, up to 20 of them.
- **Create Repository from This Template...** makes a new repository from a
  template repository. Give it a name, an optional description and
  organization, and choose whether it is private.

**Repository forks**, in **View:**, lists a repository's forks. In GitHub
Items, **View Upstream** (`Alt+U`) on a fork loads the repository it came
from. In QUILL, **Tools > Git and GitHub > GitHub > Fork Repository...** makes
a fork.

## The community profile

**Community profile checklist**, in Explore's **View:**, checks a repository
for the files GitHub recommends. The first row says the score and what is
present and missing; then one row each says "present" or "missing" for the
README, licence, contributing guide, code of conduct, issue templates and pull
request template.

## Insights

**Insights: traffic and contributors** gives a repository's last 14 days in
one sentence, such as "community-access/quill: 120 views (30 unique) and 14
clones (6 unique) in the last 14 days, 9 contributors." Each row after it is
one figure: views and clones on each day, the sites that sent people, the most
visited pages, and each contributor's commits. The list is the table.

Traffic figures need push access to the repository. Without it, QUILL says so,
and still lists the contributors.

## Looking after a repository

### In Explore, in both apps

The **Repository Actions for** submenu also holds:

- **Watch Level...**, below.
- **Archive Repository...** makes a repository read-only: no pushes, issues or
  pull requests until it is unarchived. **Unarchive Repository...** undoes it.
  Both ask first.
- **Delete Repository...** deletes the repository and everything in it: code,
  issues, pull requests, wiki and releases. It cannot be undone, so you type
  the repository's full name, exactly, to confirm. Deleting needs the token's
  `delete_repo` scope, and QUILL says so if it is missing. Sign In with GitHub
  asks for it, so an account added that way can delete; a token you added
  yourself needs the scope too (Chapter 1).

### On QUILL's Tools menu

**Tools > Git and GitHub > GitHub** has the rest. All of them need you to be
signed in, and offer to sign you in if you are not.

- **Create Repository...**: a name, a description, private or public, and an
  optional organization. QUILL then offers to set up a folder on your computer
  that stays in step with it.
- **Fork Repository...**, into your account or an organization.
- **Rename Repository...**. GitHub forwards the old address, but anything that
  has the old name written into it will need changing. You confirm by typing
  the repository's current name.
- **Change Visibility...** switches between private and public. QUILL says
  which it is now before asking, warns that making it public shows its whole
  history, and asks you to type the name.
- **Change Default Branch...**, from a list of the branches.
- **Configure Branch Protection...**: pick a branch, then the required
  reviews, required checks, and whether the rules apply to administrators.
- **Delete Branch...**, from a list that never includes the default branch.
  You type the branch's name to confirm.
- **Commit Multiple Files...**: pick files on your computer, a branch and a
  commit message, and QUILL commits them together.
- **Browse Organization Repositories...** lists your organizations, then an
  organization's repositories. Choosing one opens it in GitHub Items.

The four riskiest commands, renaming, changing visibility, deleting a branch
and merging a pull request, all make you type a name or number. A stray Enter
on one of these is much harder to put right than most things.

## Watching, starring and following

On a repository row in Explore, signed in, the context menu has
**Watch Repository**, **Unwatch Repository**, **Star Repository** and
**Unstar Repository**. Each asks first.

**Watch Level...**, on the Repository Actions submenu, sets exactly how much
you hear about a repository: "Watching: all activity", "Releases only",
"Ignoring: never notified", or "Not watching: only when participating or
mentioned". It says the current level first. GitHub does not let apps choose
"Releases only", so QUILL opens the repository's page for you to choose it
with GitHub's own Watch button, and tells you so.

On a person's row, the context menu has **Follow** or **Unfollow** and their
username. These happen straight away, without a question: "You now follow"
them. **Explore Person's Activity** shows what they have been doing.

## Gists

Explore's **My gists** view lists your gists, each with its description and
whether it is public or secret. Signed in, the context menu has:

- **New Gist...**, anywhere in the view. It starts from the document you are
  editing: the selection if there is one, otherwise the whole document, under
  the document's file name. Where there is no document, such as QUILL Lite's
  empty window, it starts blank.
- **Edit Gist...**, on a gist. QUILL reads the gist from GitHub first.
- **Star Gist** and **Unstar Gist**.
- **Delete Gist...**, which asks first. A deleted gist cannot be brought back
  from QUILL.

The gist window has **Description** (`Alt+D`), **Public gist** (`Alt+B`) when
the gist is new, the **Files** list (`Alt+F`), and **File text** (`Alt+T`) for
the chosen file. **Add File...** (`Alt+A`), **Rename File...** (`Alt+N`) and
**Delete File...** (`Alt+L`) change the list. Delete File asks first, and a
gist always keeps at least one file. Nothing goes to GitHub until **Create
Gist** or **Save Gist**, which have no access key; Cancel sends nothing.

A secret gist is unlisted, not private: anyone with its link can read it, and
GitHub does not let you switch a gist between public and secret later. When you
save, QUILL says what GitHub confirmed, such as "Gist saved. GitHub confirmed:
rename notes.md to todo.md." A file over about a megabyte reaches QUILL cut
short, so it is read-only in the gist window and never sent back; you can still
rename it.

## Other repository views in Explore

Explore has more views of one repository, each in **View:** with the
repository in **Repository:**:

- **Repository overview**, the repository at a glance.
- **Repository people** and **Collaborators and team access**.
- **Deployments and environments**.
- **Repository labels**, with **Create Label...** on the context menu.
- **GitHub Pages and builds**, for a repository with a website.
- **Repository health snapshot (opt-in)**, a set of counts that stays on this
  computer and does not rank anybody.

And views of people: **Person's repositories**, **Person's followers** and
**People followed by person**, with the username in **Person:**; and your own,
**My repositories**, **Starred repositories**, **Watched repositories**,
**People I follow**, **My followers** and **My gists** (see Gists, above).

---

- Previous: [Chapter 6: Actions and checks](lite-github-guide-06-actions-and-checks.html)
- Next: [Chapter 8: Discussions and security](lite-github-guide-08-discussions-and-security.html)
- [Contents](lite-github-guide.html)
