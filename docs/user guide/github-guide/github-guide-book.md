# The GitHub Guide for QUILL and QUILL Lite

This is the book on doing GitHub work with a screen reader in QUILL and QUILL
Lite: reading and triaging issues, reviewing pull requests line by line,
finding out why a build failed, browsing code, and keeping on top of your
notifications. It is a book of its own, beside each editor's user guide,
because there is a lot to say and you may only need part of it.

The same GitHub windows ship in both editors, and so does this book. Where the
two differ, a short paragraph starting **In QUILL Lite** says how.

## How to read this book

- **New to it?** Read Chapters 1 and 2 in order. They get you signed in and
  moving. Then go to the chapter for the job in front of you.
- **Reviewing pull requests?** Chapter 5.
- **A build failed?** Chapter 6, and its section on What Failed.
- **Something went wrong?** Chapter 10 has the sentences QUILL says when
  GitHub refuses, and what to do about each.
- **Looking up a key?** Chapter 11 has every one, window by window.
- **Using the GitHub Workbench window?** Chapter 12 walks through it, place
  by place, and Chapter 13 covers Properties, filters and permissions.

Each chapter is a level 3 heading on this page, so pressing 3 in JAWS or NVDA
moves from chapter to chapter. Every chapter page starts with its title as a
level 1 heading, its main topics are level 2 headings, and at the bottom are
links to the chapters either side and back to these contents.

## Keys at a glance

- **Opening the workbench.** In QUILL, **File > Open from Remote > GitHub
  Items...**. In QUILL Lite, **File > GitHub Workbench...**: `Alt+F`, then
  `G`.
- **Enter goes in, `Ctrl+O` opens on GitHub, Backspace comes back out.**
- **Tab** reads the selected row's details; Shift+Tab returns to the list.
- **Shift+F10** opens the context menu, which holds everything you can do
  with the selected row.
- `Alt+N` and `Alt+P` move between comments, and between rows in History and
  Blame.
- `Ctrl+Shift+W` says what failed in a workflow run.
- `Ctrl+Shift+L` says how much of GitHub's hourly allowance is left.
- In a pull request review, `Ctrl+R` replies to a thread and `Ctrl+Shift+R`
  resolves it.

This is the whole guide as one book: the same chapters as the guide's own pages, in order, each starting with its level 1 heading.

# Chapter 1: Getting started

## What this chapter covers

This chapter gets you from nothing to a repository on the screen. It explains
what the GitHub workbench is, how to open it in QUILL and in QUILL Lite, the
one question QUILL asks before it connects, how to sign in, how to keep more
than one account, and what Safe Mode does. It ends with a two-minute tour.

## What the GitHub workbench is

The GitHub workbench is a set of windows for doing GitHub work from the
keyboard: reading and triaging issues, reviewing pull requests line by line,
finding out why a workflow failed, browsing a repository's files, and
answering your notifications. You do not need Git, the GitHub website or any
other program installed. QUILL talks to GitHub directly.

The same windows ship in QUILL and in QUILL Lite. Everything in this book works
the same way in both unless a note says otherwise. Where the two differ, you
will find a short paragraph that starts **In QUILL Lite**.

There are four main windows, and you will meet them in this order:

- **GitHub Items** is where you start. It holds one repository: its issues and
  pull requests, branches, commits, tags, releases, workflows and workflow
  runs.
- **Review pull request** opens from GitHub Items. It is an outline of one pull
  request, with its changed files, its review conversations and its checks.
- **Explore GitHub** opens from GitHub Items too. It reaches across all of
  GitHub: your notifications, the work waiting for you, search, people, and
  views of a repository that do not fit in GitHub Items.
- **Repository Files** is a tree of a repository's folders and files at any
  branch, tag or commit.

Smaller windows open from these for one job each, such as the diff of a pull
request, the log of a failed job, or a discussion thread.

## Three promises

- **Reading never changes anything.** Moving through a list, expanding a pull
  request or opening a thread sends nothing to GitHub and marks nothing read.
  The one exception is said plainly where it happens: pressing Enter on a
  notification marks it read, because that is what opening it on GitHub does.
- **Every change asks first.** Anything that changes GitHub is a command you
  choose on purpose, and it asks before it sends. The confirmations default to
  No, so a stray Enter cancels. The riskiest few, such as merging or deleting a
  repository, make you type a name or number instead of pressing Yes.
- **QUILL says what GitHub did, not what it hoped.** After a change, the
  sentence you hear is built from GitHub's reply. If GitHub accepted a request
  but has not finished it yet, QUILL says that instead of claiming it is done.

## Opening the workbench

### In QUILL

QUILL keeps its GitHub commands in two places:

- **File > Open from Remote > GitHub Items...** opens GitHub Items. The same
  submenu has **Clone Repository...** for copying a repository to your
  computer, **Open GitHub Reference...** for pasting any GitHub link, and
  **Manage GitHub Accounts...** for signing in.
- **Tools > Git and GitHub > GitHub** has the commands that work on a whole
  repository, such as creating, forking and renaming one, plus
  **Notifications...**, **Security Alerts...** and Codespaces.

If you do a lot of GitHub work, turn on **View > GitHub Workbench Mode**
(`Alt+V`, then `K`). A **GitHub** menu joins the menu bar right after Tools,
with the doors into the GitHub Workbench, such as **Inbox** and **This
Repository's Pull Requests**, and the editor's own GitHub commands. `Alt+G`
opens it. Chapter 2 walks through it.

None of these has a key out of the box, so that they do not take keys a
writer needs. Press `Ctrl+Shift+P` for the Command Palette and type "GitHub" to
find any of them by name, or give one a key of your own in the Keymap Editor.

The GitHub commands belong to the feature called GitHub Remote Access. It is
on in most profiles, because reading issues and reviewing pull requests is not
coding. The Local Git commands, which are, still belong to the Developer
profile. If the GitHub rows
are missing from the File and Tools menus, GitHub Remote Access is off. Turn
it on in **Profiles and Features...**, in the **Customize and Support** submenu
of the Tools menu, or press `Alt+Shift+P` and choose a profile that has it.

### In QUILL Lite

In QUILL Lite, choose **File > GitHub Workbench...**: press `Alt+F`, then `G`.
It opens GitHub Items. Everything else in this book is reached from there.
**File > Clone Repository...** (`Alt+F`, then `Y`) copies a repository to your
computer; chapter 7 explains it.
QUILL Lite has no Tools > Git and GitHub menu, so the commands this book
describes as being on QUILL's menus are QUILL's alone. QUILL Lite has
**View > GitHub Workbench Mode** too, with its own, shorter GitHub menu.

### Where you land

GitHub Items opens with focus in the **Repository (owner/repo):** field. If
the document you have open lives in a Git folder whose remote points at
GitHub, that repository is already filled in, and you can press Enter to load
it. Otherwise type a repository as `owner/repo`, for example
`community-access/quill`, or paste its GitHub address, and press Enter.

When you reopen GitHub Items later, it comes back where you left it: the same
repository, view, filters and selected row. Chapter 2 says more about this.

## The first time: permission to connect

The first time you use any GitHub command, a window titled **GitHub Access**
asks whether QUILL may connect to GitHub. It explains that nothing is
downloaded until you choose it. Press **Continue** to go on, or **Cancel** to
stop. You are asked once. QUILL remembers your answer, and from then on the
GitHub windows open straight away.

## Signing in

You do not need an account to read public repositories. Without one, the
workbench is a read-only guest: you can read issues, pull requests, files,
workflow runs and logs of any public repository, and the commands that would
change something tell you they need a signed-in account. GitHub also allows a
guest far fewer requests an hour, so a busy session runs out sooner.

Signing in adds private repositories, your notifications and your own work,
and every command that changes GitHub. The easy way is **Sign In with
GitHub**: QUILL gets a short code from GitHub, you type it on GitHub's own
page, and you approve QUILL there. There is nothing to dig out of GitHub's
settings, and QUILL never sees your GitHub password.

### Signing in with GitHub

1. In QUILL, choose **File > Open from Remote > Manage GitHub Accounts...**.
   In QUILL Lite it's **File > Manage GitHub Accounts...**: press `Alt+F`,
   then `H`.
2. Choose **Sign In with GitHub...**, the first button. Until you have an
   account it's also the default button, so Enter does it.
3. A small window titled **Sign In with GitHub** opens. A moment later QUILL
   has a code from GitHub, something like WDJB-MJHT. It puts the code on the
   clipboard, opens github.com/login/device in your browser, and moves you to
   the **Code** field, which spells the code out a character at a time. You
   hear "The code is on the clipboard. GitHub's page is opening in your
   browser."
4. In the browser, sign in to GitHub if it asks, paste the code and choose
   **Continue**.
5. GitHub shows what QUILL is asking for, under the name QUILL, or QUILL Lite
   if you started there. Choose **Authorize**.
6. Come back to QUILL. The window closes by itself, QUILL checks with GitHub
   whose account it is, and you hear "Added and switched to GitHub account"
   and your username.

If you closed the browser tab, or it opened behind something, press **Open
the Page Again**; it's the default button, so Enter works. If the browser
doesn't open at all, the **What to do** field gives you the address to type.
**Cancel** stops the sign-in straight away and saves nothing.

A code lasts about fifteen minutes. If it runs out, or you choose Cancel on
GitHub's page instead of Authorize, the **What to do** field says so in one
sentence and nothing is saved. Close the window and choose **Sign In with
GitHub...** again for a fresh code.

To add a second account this way, sign in to that account in your browser
first. GitHub approves whichever account the browser is signed in to.

What QUILL asks GitHub to allow, and why:

- `repo`: private repositories, and everything that writes: issues, comments,
  reviews, merges, releases, discussions, workflow runs and saving files. It
  covers your notifications inbox too.
- `workflow`: saving changes to workflow files, the ones under
  .github/workflows. GitHub refuses those without it.
- `gist`: your gists.
- `read:org`: the organizations you belong to, for browsing their
  repositories and creating or forking into them.
- `project`: Projects boards.
- `security_events`: code-scanning and Dependabot alerts.
- `user`: **Set Your Status**, and following and unfollowing people.
- `read:packages` and `delete:packages`: **My Packages**, and deleting a
  package or one of its versions, which asks first.
- `admin:public_key`, `admin:gpg_key` and `admin:ssh_signing_key`: **My
  Keys**, your SSH, GPG and signing keys.
- `admin:org_hook`: an organization's **Webhooks**, for its owners.
- `delete_repo`: **Delete Repository**. It still makes you type the
  repository's full name before it deletes anything.

One sign-in covers every command in the Workbench, so you never need
anything else for any of them.

If your organization uses single sign-on, GitHub may ask you to sign in
through the organization while you approve QUILL. If your organization
restricts which apps can see its repositories, see Chapter 10.

Manage GitHub Accounts also has an **Add Token (Advanced)...** button. You
don't need it to sign in. It's there for a few special cases, such as an
organization that blocks sign-in apps, and Chapter 10 explains it under
"Advanced: using a token".

Some QUILL commands on the Tools menu need an account before they can do
anything. If you choose one while signed out, QUILL asks "This action needs a
signed-in GitHub account. Sign in now?" and opens Sign In with GitHub.

### Where your sign-in is kept

When you sign in, GitHub gives QUILL a long code that stands for your
approval, and QUILL keeps it in your operating system's own secure store: Windows Credential Manager on
Windows, or the Keychain on a Mac. A portable copy keeps it in its own
encrypted file instead. It is never written into a settings file or a log.
QUILL sends it to GitHub's own servers and nowhere else. When GitHub hands a
download to another address, such as a log or an artifact, QUILL fetches that
without the token.

The workbench's sign-in is separate from My GitHub Copilot's, even though
both go through GitHub's page under the same name. Signing out of one leaves
the other alone.

### In QUILL Lite

QUILL Lite signs in the same way, from **File > Manage GitHub Accounts...**
(`Alt+F`, then `H`), and the two editors share your accounts: one you add in
either is there in both. Signed in, QUILL Lite reviews, replies, merges and
triages your notifications just as QUILL does.

If you open the workbench before you've signed in, QUILL Lite says "You are
not signed in to GitHub" and offers three buttons. **Manage GitHub
Accounts...** is the default: sign in there, and once GitHub confirms your
account the workbench opens signed in. **Continue as Guest** opens it anyway,
to read public repositories. **Cancel** opens nothing.

## More than one account

If you have a personal account and a work account, keep both.
**Manage GitHub Accounts...** shows the active account at the top, such as
"Active account: your-name on github.com", and a list of every account you
have added. From there:

- **Use Selected Account** makes the chosen account the active one. You hear
  "Switched to GitHub account" and its name.
- **Remove Selected Account** deletes that account's token from this computer.
  It does not ask first, and it does not cancel the token on GitHub. To do
  that, open your GitHub settings, then **Applications**, then **Authorized
  OAuth Apps**, and revoke QUILL there.
- **Sign In with GitHub...** adds another account. **Add Token
  (Advanced)...** is the advanced road, in Chapter 10.
- **Done** closes the window. Escape does too.

Only github.com accounts are supported. GitHub Enterprise servers are not, yet.

Each account keeps its own place. GitHub Items remembers the last repository
and row separately for each account, and so do your local drafts and the
attention queue's settings, so switching accounts never mixes them up.

## The GitHub CLI and your account

A few things, Codespaces in particular, run through GitHub's own command-line
tool, called `gh`. It signs in on its own, separately from QUILL. Before it
runs a Codespaces command, QUILL asks `gh` which account it is using and
compares that with the account QUILL is using. If they differ, it stops and
says so, naming both, so you never create a codespace on the wrong account by
accident. Chapter 9 covers this.

## Safe Mode

When QUILL or QUILL Lite starts in Safe Mode, the GitHub windows stay closed.
Opening GitHub Items says "GitHub item browsing is disabled in Safe Mode.
Restart QUILL normally to browse a repository." The repository commands on
QUILL's Tools menu and the GitHub CLI commands are switched off the same way.
Start normally to use them again.

## A two-minute tour

This tour reads a public repository, so you can do it before you sign in.

1. Open GitHub Items: in QUILL, **File > Open from Remote > GitHub Items...**;
   in QUILL Lite, `Alt+F`, then `G`. In workbench mode, in either app, it is
   **GitHub > Repository Items...**: `Alt+G`, then `T`.
2. If this is the first time, press **Continue** in the GitHub Access window.
3. Type a repository you know, such as `community-access/quill`, and press
   Enter. You hear the repository's name, how many items loaded, and a short
   list of the keys that work here. Focus moves to the list, on the first row.
4. Arrow down the list. Each row is an issue or a pull request: its number,
   whether it is an issue or a PR, its state and its title.
5. Press Tab to reach **Details**. Read it like any text field. It holds the
   whole issue, then its comments as they load.
6. Press `Alt+N`. You move to the first comment and hear "Comment 1 of" and
   the count. Press it again for the next one, and `Alt+P` to go back.
7. Press Shift+Tab to return to the list.
8. Press Shift+F10 on a row to hear what you can do with it.
9. Press Escape to close the menu, and Escape again to close GitHub Items.

Next time you open it, you are back on the same row.

# Chapter 2: Getting around

## What this chapter covers

This chapter is about moving, not doing. It starts with GitHub Workbench Mode
and the GitHub menu, then walks through the GitHub Items window and the
Explore GitHub window control by control, explains the three keys that do most
of the moving, and covers context menus, searching, favorites, coming back
where you left off, pasting a link, and GitHub's hourly allowance. Every later
chapter builds on it.

## GitHub Workbench Mode and the GitHub menu

Normally the GitHub commands sit a few levels down, in the File and Tools
menus, where they keep out of the way of writing. When you are spending an
afternoon on issues and pull requests, you want them one key away instead.
That is what GitHub Workbench Mode is for.

Turn it on with **View > GitHub Workbench Mode**: `Alt+V`, then `K`. It is a
check item, so the View menu tells you whether it is on. QUILL says "Workbench
mode on. GitHub menu added." and a **GitHub** menu joins the menu bar right
after Tools. Press `Alt+G` to open it.

While the mode is on, the GitHub rows leave File and Tools and live in the
GitHub menu instead, so nothing is listed twice. Turn the mode off and they go
back. A row's key, if you have given it one, goes with it: keys belong to
commands, not to menus, so a key you set works in both modes.

The mode belongs to the window you turned it on in. Other windows keep their
own menus, and a new window starts with the mode off. Nothing else changes:
every other menu is where it was, and a document you have open keeps working.

### The Workbench cell on the status bar

While the mode is on, the status bar has one more cell, **Workbench**. It
reads "Workbench:" and the repository the GitHub menu works on, such as
"Workbench: community-access/quill", which is the repository the document
you have open belongs to. When the document isn't in a GitHub repository, it
just reads "Workbench". Turn the mode off and the cell goes away.

Reach it like any other cell: press `F6` to move to the status bar, then the
arrow keys to get to it. `F1` on it says what it is. QUILL never reads it out
by itself, because "Workbench mode on" has already told you the same thing;
it's there for when you want to check.

### What the GitHub menu holds

From the top:

- **Repository:** and its name, when the document you have open lives in a
  GitHub repository. It is a readout rather than a command, so your screen
  reader says it is unavailable. When there is no repository, the row is left
  out.
- **Leave Workbench Mode** (`V`), the way out, where you already are.
- **Open GitHub Workbench** (`W`): the GitHub Workbench window, where you left
  it, or on Inbox or Start Here if that is what you chose in Workbench Options.
- **Inbox** (`I`): the Workbench, on what needs you. Chapter 3 covers it.
- **This Repository's Issues** (`S`), **This Repository's Pull Requests**
  (`P`) and **Actions Runs** (`A`): the Workbench, on that part of the
  repository the document you have open belongs to.
- **From This Line** (`R`): what GitHub knows about the line you are on, or
  the lines you have selected: a link to them, who changed them, the pull
  request that brought them, a new issue quoting them, and more. Chapter 7
  covers it. In QUILL Lite its eight rows are in the menu itself, between
  separators.
- **Clone Repository...** (`C`) and, in QUILL, **Open GitHub Address...**
  (`D`), which takes a link, `owner/name` or `owner/name#42`.
- In QUILL only: **Commit to GitHub...** (`M`), **Sync Folder with GitHub...**
  (`Y`) and the **Local Git** submenu (`L`), because they are about the copy of
  the repository on your computer rather than about GitHub.
- **Manage GitHub Accounts...** (`G`) and **Open GitHub Guide** (`H`), last.
  Help keeps its own Open GitHub Guide row too.

That is the whole menu. Everything else moved into the Workbench, where it has
a place in the tree or a row in its own menus: My Work and Notifications are
under Needs My Attention, Releases is under each repository, Explore GitHub's
searches are under Search, and the repository settings and Codespaces are on
the Workbench's Repository menu. The old commands still work from the Command
Palette, and a key you gave one still works too; each opens the Workbench at
the matching place.

QUILL Lite's GitHub menu is the same menu with QUILL's own rows left out, so
the letters are the same in both apps. From This Line's rows are the one
difference in shape: a submenu in QUILL, straight in the menu in QUILL Lite,
with the same letters either way.

To leave, choose **GitHub > Leave Workbench Mode** (`Alt+G`, then `V`), or
uncheck **View > GitHub Workbench Mode**. QUILL says "Workbench mode off."
Neither has a key of its own: the mode is something you switch a few times a
day at most, and no key was free in both apps.

In QUILL Lite, the mode works in the empty window too, the one that is left
when you close every document. With the mode on there, that window is a GitHub
launcher with nothing to write in.

## The GitHub Items window, top to bottom

GitHub Items is one window with a lot in it. Here is everything in the order
Tab reaches it, with its access key where it has one. You do not need to learn
them all. The list, Details and Shift+F10 carry most of the work.

The repository row:

- **Repository (owner/repo):** the repository to load. Enter loads it. You can
  type `owner/repo`, paste a github.com address, or paste a `git@github.com:`
  remote.
- **Load**, the same as Enter in the field.
- **Pinned...**, your own short list of repositories. Reach it with Tab:
  `Alt+P` is taken by comment navigation in this window.
- **Favorites...** (`Alt+V`), the items you have starred with `Ctrl+D`.
- **Explore...** (`Alt+E`) opens Explore GitHub.
- **Projects...** (`Alt+J`) opens the repository's Projects boards.
- **View Upstream** (`Alt+U`) loads the repository a fork was made from. It is
  available only when the loaded repository is a fork, and QUILL says so when
  it loads one.
- **Files...** (`Alt+F`) opens Repository Files.
- **Milestones...**, which has no access key.

The search row:

- **Search (GitHub syntax):** (`Alt+H`, or `Ctrl+F` from anywhere in the
  window) asks GitHub.
- **Search**, the button for the same thing.
- **Open Link...** takes a pasted GitHub link.
- **Quick filter:** (`Alt+Q`, or `Ctrl+Shift+F`) narrows the rows you already
  have, on your computer.

The filter row:

- **View:** (`Alt+I`) chooses what the list shows.
- **Show:** (`Alt+S`): Both, Issues or PRs.
- **State:** (`Alt+T`): Open, Closed or All.
- **Sort:** (`Alt+O`): by number, title, last update or comment count, either
  way round.
- **List mode:** (`Alt+L`): Quick (compact) or Full (field names).
- **Columns...** (`Alt+M`) chooses which columns the list reads.
- **Back** and **Forward** step through the places you have been.

Show, State and Sort work in the Issues & PRs view only.

Then the heart of the window:

- **The list.** One row per item. You can select more than one row, for the
  Batch menu.
- **Details**, a read-only text field holding the whole of the selected row.
- **The status line**, which says what just happened.

And the button row: **Refresh**, **View More**, **Open in Browser**,
**Go To #...**, **Diff...** (`Alt+D`), **Review...** (`Alt+R`),
**Summarize** (`Alt+Z`), **Compare...** (`Alt+C`), **Batch...** (`Alt+B`),
**Actions...** (`Alt+A`) and **Close**. Diff, Review, Summarize and Batch are
for the Issues & PRs view, and Compare for the Branches view.

### The views

**View:** has seven choices:

- **Issues & PRs**: issues and pull requests together, newest first.
- **Branches**: each branch, whether it is protected, and its last commit.
- **Commits**: the latest commits, or a branch's commits after you open one.
- **Tags**: each tag and the commit it points at.
- **Releases**: each release, its download count, and whether it is a draft
  or a pre-release.
- **Workflows**: the repository's GitHub Actions workflows.
- **Workflow Runs**: recent runs, with their status and result.

The list loads 30 rows at a time. **View More** loads the next 30.

### Quick and Full rows

In **Quick** mode a row is the bare values, the way the columns show them:
"208, ISSUE, OPEN, Fix the thing". In **Full** mode each value has its name in
front, "number: 208, type: ISSUE, state: OPEN, title: Fix the thing", so a row
explains itself and QUILL also says it as you arrive on it. Press `M` in the
list to switch. Every new window starts in Quick mode.

**Columns...** opens a menu of the current view's columns as check items.
Uncheck the ones you do not want to hear. One always stays, and QUILL says
"At least one column must stay visible." if you try to remove the last.

## Enter, Ctrl+O and Backspace

Three keys do most of the moving in the list. They behave the same way
everywhere, so once you know them you can guess.

- **Enter goes in.** On a branch it opens that branch's commits. On a release
  it opens the release's files, with their download counts. On a workflow it
  offers to run it. On anything that has nowhere further to go in QUILL, such
  as an issue, Enter opens it in your browser.
- `Ctrl+O` **opens the selected row on GitHub**, in your browser, whatever it
  is.
- **Backspace comes back out.** From a branch's commits it returns to
  Branches, and from a release's files to Releases ("Back to releases.").

Two things that Enter does not do on an issue or a pull request, because they
have their own keys: to **read** one, Tab to Details; to **review** a pull
request, press `Alt+R` for **Review...**.

**Back** and **Forward** step through the places you have been in this window,
up to the last hundred: a repository, a view, a search. `Ctrl+G` (**Go To
#...**) asks for an issue or pull request number and selects it, in the Issues
& PRs view.

`Ctrl+R` reloads the current view. So does a plain `R` while the list has
focus, which means R does not jump to a row starting with R here.

## Context menus and the Actions button

Shift+F10, the Applications key or a right-click on a row opens its context
menu. It holds everything that applies to that row and only that, so it is
the quickest way to find out what you can do. Commands that change GitHub
appear only when you are signed in. With no row selected, the menu has the
commands for the whole view, such as **Refresh** and, when you are signed in,
**New Issue...**.

Every row's menu ends with the same few: **Open on GitHub**, **Copy Link**,
**Copy Details**, **Add to or Remove from Favorites**,
**Browse Repository Files...** and **Milestones...**, then
**GitHub API Rate Limit** last of all.

**Actions...** (`Alt+A`) holds the commands that write, for the current view
and selection. Signed out, it says "Write actions need a signed-in GitHub
account; this session is read-only." If nothing applies, it says "No write
actions available here. Select a row first."

Shift+F10 works the same way in Details, in the review outline, in Explore's
results and in most of the smaller windows.

## Searching and filtering

There are two boxes, and the difference matters.

- **Search** asks GitHub. Press `Ctrl+F`, type anything GitHub's own search
  understands, and press Enter: `label:bug is:open crash`, `author:alice
  is:pr`, or `created:>2026-01-01 no:assignee`. The results replace the list,
  limited to the loaded repository. Empty the box and press Enter to get the
  normal list back; you hear "Search cleared; showing the normal list."
- **Quick filter** asks nobody. Press `Ctrl+Shift+F` and type. The list
  narrows to rows containing what you typed, as you type, with nothing sent
  over the network. It does not move your focus and does not announce a count
  after every letter, which would talk over your screen reader's own typing
  echo. Escape in the box clears it.

Searching across every repository, and searching code, commits or
repositories, happens in Explore. Chapter 7 covers it.

## Pinned repositories and favorites

**Pinned...** is your short list of the repositories you really work in. It
opens a menu: one row per pinned repository, which loads it, then **Pin** or
**Unpin** for the repository you have loaded.

A favorite is one item rather than a repository: an issue, a pull request, a
branch or a release. Press `Ctrl+D` on its row and you hear "Favorited" and its
name. **Favorites...** (`Alt+V`) lists every favorite across every repository,
and choosing one opens it in your browser.

Pins, favorites and your column choices stay on this computer. They are not
synced to GitHub and not kept per account.

## What QUILL says, and what it leaves to your screen reader

Your screen reader already says the name of a window when it opens, the
control that has focus, and the row you arrive on in a list. QUILL does not
repeat any of that. It speaks only what your screen reader cannot know:

- **When a load finishes**: the repository, how many rows, and a short line of
  the keys that work in this view. A load can take a second or two, and this
  is how you know it is done. Focus moves to the list, on the first row.
- **The result of a command**: "Reply posted", "Favorited", "Cancelled;
  nothing was sent to GitHub.", or GitHub's reason for refusing.
- **Something that changed somewhere you are not**, such as a comment
  arriving in Details while you are in the list.

It deliberately stays quiet while you type in the Quick filter, while a page
of results is fetching, and when a notification is marked read as you open it.

Everything QUILL says is also written to the status line, so you can read it
again with your screen reader's review keys, and it is brailled as well as
spoken.

## Coming back where you left off

When you close GitHub Items, QUILL remembers where you were: the repository,
the view, Show, State and Sort, your search and Quick filter, the branch you
had opened, and the selected row. The next time you open it, you are back
there, and you hear "Restored the last selected GitHub item."

If that item is no longer in the first page of results, perhaps because newer
issues have pushed it down, you hear "The previous item is outside the loaded
results. Use View more or search to find it."

This is kept for each GitHub account separately. It stores where you were,
never a token, and it never sends anything to GitHub.

## Open GitHub Reference: paste any link

Someone sends you a link to an issue, a pull request, a line of a file or a
failed run. You do not need to work out where it lives. Paste it, and QUILL
opens the right window at the right place.

In QUILL, choose **File > Open from Remote > Open GitHub Reference...**. In
both apps, the **Open Link...** button in GitHub Items does the same from
inside the window. Paste a link, or type `owner/repo`, and press Enter.

- A repository link loads that repository.
- An issue link selects that issue, and a pull request link opens its review.
- A branch, commit, release, workflow or workflow run link switches to the
  matching view and selects it.
- A link to a file opens the file in the editor, at the linked lines when the
  link names them.
- A discussion link opens the thread in Explore, when you are signed in.

If the item is not in what has loaded, QUILL says so: "Could not find the
linked" item "in the loaded results. Use View more or open the link in
GitHub."

A link QUILL has no window for, such as a comparison, asks whether to open it
in your browser instead, and says that QUILL will not attach your GitHub token
to that request.

QUILL refuses a link that carries a password or a token in it, and says
"Remove credentials from the URL before opening it." Paste the plain address.

**In QUILL Lite**, a file link opens the file's text as a new untitled
document, because QUILL Lite cannot save back to GitHub. Save As keeps a copy
on your computer.

## Getting around Explore GitHub

**Explore...** (`Alt+E`) in GitHub Items opens Explore GitHub. In workbench
mode, **GitHub > Explore GitHub...** opens it from the menu bar, and **Inbox...**,
**My Work...** and **Notifications...** open it straight on those views. In
QUILL, **Tools > Git and GitHub > GitHub > Notifications...** opens it at your
notifications when the mode is off.

Explore is simpler than GitHub Items: a view, the boxes that view needs, a
list and a details field. In Tab order:

- **View:** (`Alt+V`) chooses what to show. Choosing a view loads it straight
  away.
- **Repository:** (`Alt+R`), for the views about one repository.
- A line describing the view, when it needs explaining.
- **Person:** (`Alt+P`), for the views about one person.
- **Global search:** (`Alt+G`), for the search views. GitHub's qualifiers,
  such as `repo:` and `is:open`, work here.
- **Saved Searches...** (`Alt+S`) and **Save Search**.
- **Load** (`Alt+L`). Enter in any of the boxes above does the same.
- **Queue Options...** (`Alt+O`), for the attention queue.
- **Results**, the list.
- In the notifications view only, four triage controls. Chapter 3 covers them.
- **Selected result**, the details of the row.
- The status line, then **Open on GitHub**, **Use Repository** and **Close**.

When you are signed in, Explore opens on your attention queue and loads it
straight away. Signed out, it opens on **Global issue and PR search**.

In the Results list, Enter does the natural thing for the row: a notification
opens, a discussion opens as a thread, a repository goes back to GitHub Items
(you hear "Selected repository" and its name "in the workbench."), and
anything else opens in your browser. **Use Repository** sends the selected
row's repository to GitHub Items and closes Explore.

## Rate limits and the readout

GitHub lets each account make a certain number of requests an hour, and fewer
as a guest. You rarely need to think about it, but when you do, press
`Ctrl+Shift+L` in GitHub Items or Explore. QUILL reads GitHub's own count and
says it in a sentence for each allowance, such as "GitHub API: 4,212 of 5,000
left, resets at 3:15 PM." Search and code search have allowances of their own,
and the readout includes those too. **GitHub API Rate Limit**, at the end of
every context menu, does the same.

If GitHub asks QUILL to slow down, which it does when many requests arrive
close together, QUILL stops sending until the wait is over, and says so once:
"GitHub asked QUILL to wait 60 seconds." Every request in that time stops
before it reaches the network, so you do not hear the same refusal ten times.

When the hourly allowance runs out, you hear "GitHub API rate limit reached.
Retry after" and the number of seconds.

## Quiet refreshes

QUILL remembers what GitHub last sent for many of the reads it repeats, and
asks GitHub whether anything has changed since. If nothing has, GitHub says so
in a few bytes, and that answer does not count against your allowance.

When you reload an Explore view and nothing has changed, you hear "No changes
since the last load;" and the number of results, instead of the whole count
again. Your notifications work the same way, with one more rule: GitHub tells
apps how often they may check the inbox, and QUILL keeps to it. Chapter 3
explains what you hear if you refresh sooner.

The Workbench's lists and sheets do the same. Pressing F5 on a list of issues,
pull requests, branches, commits, tags, releases, workflows or runs first asks
GitHub whether that list has changed, and if it has not, the rows you already
have stay as they are without being read again. Reopening a sheet, or the
check QUILL makes after you save one, works the same way. This matters most
for pull requests, where reading each row's size used to cost one request a
row. Nothing is kept on disk: what QUILL remembers for this lasts until you
close it.

# Chapter 3: Your inbox and your work

## What this chapter covers

GitHub sends you a notification whenever something you are part of moves. On
a busy project that is dozens a day, and the website's inbox is a long page of
links and icons. This chapter shows you how to go through it from the
keyboard: what each notification says, how to clear it, and how to keep your
place. Then it covers My Work, the attention queue that gathers everything
waiting for you and says where each pull request stands, and the activity
views.

All of this needs a signed-in account, because it is your inbox and your work.

**In QUILL Lite**, which works as a guest, these views say "Sign in to GitHub
for this account view." Use QUILL for them.

## Opening your notifications

In QUILL, choose **Tools > Git and GitHub > GitHub > Notifications...**. Explore
GitHub opens straight at your inbox. From GitHub Items, press **Explore...**
(`Alt+E`) and choose **GitHub notifications** in **View:** (`Alt+V`).

When the inbox loads, QUILL says how many are unread, once:

- "12 unread."
- "3 unread of 40.", when you are showing read ones too.
- "No unread notifications; 40 read."
- "No notifications."

## What a notification says

Each row says, in this order, whether it is unread, why it reached you, the
repository and the title: "Unread, review requested: community-access/quill
— Fix the status bar".

The reason is in words, not GitHub's code names:

- "review requested"
- "you were mentioned", or "your team was mentioned"
- "you were assigned"
- "you opened it", or "you commented"
- "you changed its state"
- "you are watching the repository", or "you subscribed"
- "a workflow run you started finished"
- "your approval was requested for a deployment"
- "security alert"
- "you were invited to the repository"
- "you were credited on a security advisory"

**Selected result** holds the rest, one line each: what the subject is (an
issue, a pull request, a release, a discussion, a commit, a workflow run, a
security alert), the repository, why you got it, its state and when it last
changed, and the link.

## Opening one

Press Enter on a notification. Two things happen.

First, QUILL marks it read, the way opening it on GitHub would. It does this
quietly. The row's first word changes from Unread to Read, which you hear when
you next arrive on it.

Then it opens the notification in the best place for it:

- **A pull request** opens in the review window, on top of Explore. Close the
  review and you are back in your inbox, on the same row.
- **An issue** opens in GitHub Items, at that issue, and Explore closes.
- **Anything else**, such as a release or a workflow run, opens in your
  browser.

## Triage: Done, Unsubscribe and Mark All Read

In the notifications view, and only there, four controls appear under the
Results list:

- **Include read notifications** (`Alt+I`), a check box. Check it to see
  notifications you have already read as well. The list reloads.
- **Mark Done** (`Alt+D`) takes the selected notification out of your inbox.
  It is the same as Done on GitHub. The Delete key in the list does the same.
- **Unsubscribe** (`Alt+U`) stops notifications from that thread for good, and
  takes it out of the inbox.
- **Mark All Read** (`Alt+A`) marks everything read.

### Keeping your place

Mark Done and Unsubscribe take the row out of the list and put you on the next
one, with focus still in the list, so you can keep going: read, Delete, read,
Delete. You hear "Marked done." or "Unsubscribed from the thread." When the
last one goes, QUILL adds "No notifications left in this list."

If you reload, QUILL puts you back on the same notification, if it is still
there.

### Mark All Read

Mark All Read asks first: "Mark every notification in your GitHub inbox read,
up to when this list was loaded? Newer notifications stay unread." That second
sentence is the safety: anything that arrived after you loaded the list stays
unread, so you never clear something you have not seen.

You hear "Marked all notifications read." On a large inbox GitHub may do the
work in the background instead. Then you hear "GitHub accepted the request and
is marking them read in the background. Refresh in a minute to check."

### The context menu

Shift+F10 on a notification has the same commands, plus one more:
**Mark Notification Read**, **Mark Done**, **Unsubscribe from Thread**, and,
for the whole view, **Mark All Read...**. Mark Notification Read marks it read
without opening it. **Inbox Rules...** is in the Item menu, below.

## Invitations

When someone invites you to a repository, GitHub sends a notification, and
the invitation itself waits in **Needs My Attention > Invitations**. Each row
says the repository, who invited you and with what access, "octo/app: ann
invited you, write access", and the details say when. Enter, or **Accept
Invitation...** on the context menu, asks and then joins you to the
repository; **Decline Invitation...** asks and says no. An invitation expires
after a week; an expired one says so, cannot be accepted, and can still be
declined to clear it away.

## Inbox rules

Some notifications always get the same answer: a Dependabot update you will
never read before it merges, a busy repository you only watch, a mention you
always want first. An inbox rule gives that answer for you as the list
arrives. In the GitHub Workbench, choose **Item > Inbox Rules...**
(`Ctrl+Alt+N`). The window lists your rules, each read as a sentence, and
**New Rule...**:

1. **What should the rule do?** Mark it done, Mark it read, or Move it to the
   top.
2. **From which repository?** An `owner/name`, or a `*` for any part, so
   `octo/*` is every repository of `octo`. Leave it blank for any. If a
   notification was selected, its repository is already filled in.
3. **Why it came to you:** any reason, or one of GitHub's, such as "you were
   mentioned" or "review requested".
4. **What it is about:** anything, or a pull request, an issue, a discussion, a
   release, a workflow run, a commit or a security alert.
5. **Words its title must contain**, or blank for any. Dependabot's titles
   start with "Bump".

A rule needs at least one of these; one with none would act on every
notification, and QUILL will not save it. Before saving, QUILL reads the rule
back and tries it on the notifications already loaded today: "When a
notification is from octo/*, about a pull request, with 'Bump' in its title:
mark it done. It matches 3 of the 41 notifications loaded today, and would
mark them done:" and their titles. Yes saves it; No saves nothing.

From then on the rules run every time Notifications loads, before you see the
list, the first rule that fits each notification deciding what happens to it.
Marking done and marking read are sent to GitHub, as if you had pressed the
keys yourself; moving to the top only changes the order here. After the list
loads you hear what they did: "Inbox rules: 3 marked done, 1 moved to the
top." To delete a rule, choose it in the Inbox Rules window and say Yes.

## How often QUILL checks

GitHub tells apps how often they may check the inbox, usually once a minute,
and asks them to keep to it. QUILL does. If you reload sooner, it keeps the
list it already has, and adds to the unread count: "GitHub asks apps to check
notifications no more often than it says; this is the list from the last
check. Try again in" and the number of seconds.

When you do reload, QUILL asks GitHub only for what has changed since last
time. An unchanged inbox comes back in a moment and costs nothing from your
hourly allowance. When the allowance is running low, QUILL waits longer
between checks on its own: twice as long under a quarter left, four times as
long under a tenth.

## My Work

**My Work**, in Explore's **View:** list, is everything open that involves
you, across every repository you can see. It runs four searches and puts the
results in one list:

- **Assigned**: open issues and pull requests assigned to you.
- **Review requested**: open pull requests waiting for your review.
- **Mentioned**: where someone mentioned you.
- **Authored**: what you opened.

An item that turns up in more than one search appears once. Its details start
with the searches that found it, so you know whether it is here because you
were assigned or because you were mentioned. Each row reads the repository,
the number, the title, and whether it is an issue or a pull request.

## The attention queue

The attention queue is a shorter, sharper list: only what is waiting for you
to act. It is the view Explore opens on when you are signed in. It gathers four
kinds of work:

- **Assigned to me**
- **Review requested**
- **Mentioned**
- **Failed checks**: open pull requests whose checks failed, in the
  repositories the queue covers.

Each row names where it came from and when it last changed. QUILL remembers
when you last finished loading the queue, so the next time it can tell you
what moved: changed items say "Changed since your last visit." in their
details, and the status line adds how many changed. The first time, it says
"This is your first recorded visit."

### Where each pull request stands

A pull request in the queue also says where it stands, in the same sentence the
review window opens with: "Approved, 2 checks failing, 1 open thread". It comes
after the row's name in the list, and in the details it follows the reason the
row is there, so you still hear why it is in your queue first.

QUILL reads every pull request's sentence in one request when the queue loads,
however many there are. It covers the twenty newest; when the queue holds more,
the status line says so, such as "Summaries cover the newest 20 of 26 pull
requests".

The sentence never calls a pull request ready on data it does not have. When
GitHub sent only part of the picture, it says "merge readiness unknown". When
GitHub did not answer for a pull request at all, its row says "Summary
unavailable" and the status line says how many.

If part of the queue could not load, perhaps because GitHub refused one of the
searches, QUILL does not pretend the list is complete. You hear the count "with
incomplete data. Check the status for details.", and the status line says
which part is missing.

### Queue Options

**Queue Options...** (`Alt+O`) opens a menu for shaping the queue. It is
available once the queue has loaded.

- **Choose Repositories...** limits the queue to up to ten repositories. Type
  them as `owner/repo`, separated by commas, or leave the box empty to search
  everything you can see.
- **Choose Categories...** picks which of the four kinds to include. Check the
  ones you want; at least one has to stay.
- **Save Current Filter...** names the current repositories and categories, so
  you can switch to them again. Each saved filter then has its own
  **Use Filter** and **Remove Filter** rows in this menu.

Filters are kept on this computer, for each account separately. None of this
changes anything on GitHub.

## Activity

Three views show what has been happening rather than what is waiting:

- **My activity feed**: events from the people you follow and the repositories
  you watch.
- **Repository activity**: recent events in the repository named in
  **Repository:**.
- **Person's public activity**: one person's public events. Type their
  username in **Person:** (`Alt+P`).

Each row reads the kind of event, the repository and who did it, such as
"Push: community-access/quill — jeff".

## A morning routine

1. Open your notifications: in QUILL, **Tools > Git and GitHub > GitHub >
   Notifications...**.
2. Listen to the unread count.
3. Arrow down. For each row, decide: read it now (Enter), clear it (Delete), or
   stop hearing about it (`Alt+U`).
4. After opening a pull request, close the review window to come back to the
   same place in the list.
5. When the inbox is clear, choose **Attention queue** in **View:** and work
   from the top.

# Chapter 4: Issues

## What this chapter covers

This chapter is about issues: reading one and its comments, replying,
reacting, reading its history, writing a new one from a template, and keeping
issues in order with labels, milestones, assignees and batch changes, and
handing an issue to Copilot's coding agent. It also
covers the housekeeping commands, Projects boards and dependencies, and
starting work on an issue in a folder of its own. Pull requests are issues
too, so most of this applies to them as well.

## Reading an issue

Load a repository, keep **View:** on **Issues & PRs**, and arrow to the issue.
Press Tab to reach **Details**. It reads like a document:

- the number, whether it is an issue or a PR, and the title;
- its state, author, when it was opened and last updated, and its link;
- its labels and assignees, when it has any, and how many comments;
- then a line of dashes, and the description.

For a pull request, Details also says whether it is a draft, whether it is
merged, its review state, which branch merges into which, and how many lines
and files it changes.

The comments load on their own a moment after you select the issue. You hear
how many, such as "4 comments loaded. Alt+N to jump to the first." They follow
the description in Details, each starting "Comment 1 of 4", then the author
and the date.

### Moving between comments

`Alt+N` moves to the next comment and `Alt+P` to the previous one, from
anywhere in the window. QUILL moves focus into Details, selects the comment
and says "Comment 2 of 4". At either end you hear "Already at first comment."
or "Already at last comment." This is the quickest way through a long
thread: press `Alt+N`, read, press `Alt+N` again.

Reactions on a comment are in words at the end of it, such as "Reactions: 3
thumbs up, 1 heart".

### A summary of the discussion

**Summarize** (`Alt+Z`) asks QUILL's AI to boil the issue and its comments
down to a few sentences: what it is about, where it stands, the open
questions and the next step. The summary goes at the top of Details and is
read out. It uses the AI connection you chose in QUILL and asks the same
questions about sending text that every AI feature asks. If no AI is set up,
it offers to set one up.

**In QUILL Lite**, Summarize says "AI summaries are unavailable here."

## Commenting

You need to be signed in to comment. Select an issue or pull request and choose **Comment...** from its context
menu or the **Item** menu. The comment window opens with the cursor in
**Comment:**. Write in Markdown; Enter starts a new line, and Ctrl+Enter posts.

The buttons under the comment put things at the cursor:

- **Insert Mention...** (`Alt+M`) lists the people in the conversation first,
  then everyone who may be assigned, and inserts `@` and the name. GitHub will
  notify them.
- **Insert Reference...** (`Alt+R`) asks for words in a title, or a number,
  and lists the issues and pull requests that match; it inserts `#` and the
  number.
- **Insert Emoji...** (`Alt+E`) finds an emoji by its name, such as "thumbs up"
  or "party".
- **Insert Saved Reply...** (`Alt+S`) lists the saved replies you keep on
  GitHub, under Settings, Saved replies.
- **Attach Files...** (`Alt+F`) explains why it cannot: GitHub lets no other
  program attach a file. Put the file in a release or a gist and paste its link,
  or attach it on github.com.
- **Preview** (`Alt+P`) reads the comment into the **Preview:** box as GitHub
  will show it, one line each, saying what every line is: "Heading 2: Plan",
  "Not done: Run it", "Quote: ...", a code block and how long it is, and what
  each image and link stands for. Its last lines name who the comment will
  notify and which issues it refers to.

**Check before posting** (`Alt+H`) is on to begin with. When you post, it looks
for things that trip a reader: an image with no description, a link that says
"click here", a heading that skips a level, a long run of capital letters, and
a comment that is only an emoji. If it finds any, it lists them and asks
whether to post anyway; No takes you back to the comment. Turn it off for a
comment you know is fine.

**Post** sends the comment; Cancel or Escape sends nothing. GitHub's refusal is
said in words if your account cannot comment.

The current Workbench posts new issue comments. Editing or deleting an
existing comment is not in its current issue actions; use GitHub.com for those
changes. For pull-request review comments, see Chapter 5.

## Reactions

Shift+F10 on the issue has **React...**, which reacts to the issue itself.
After `Alt+N`, it also has **React to This Comment...**. A list of GitHub's
eight reactions opens: thumbs up, thumbs down, laugh, hooray, confused, heart,
rocket and eyes. One you have already given reads, for example, "heart, yours:
choose to remove it", so the same list adds and takes away. You hear "Added
heart." or "Removed heart."

## The timeline

Comments are only part of an issue's story. Labels are added, people are
assigned, the issue is closed and reopened, and pull requests mention it.
Shift+F10 on the issue has **View Timeline...**, which opens the whole
history in one text field, **History, oldest first:** (`Alt+H`), one event to
a line. **Copy All** (`Alt+A`) copies it. When it loads, you hear "Timeline
loaded," and the number of events. A very long history is read up to five
hundred events, and QUILL says when it stopped early: "Only part of the
history was read."

A comment that is spam, abuse, off topic, outdated, a duplicate or resolved
can be folded away for everyone without deleting it, as GitHub's own "Hide"
does. Put the cursor on its line, the one that says "commented", and press
**Hide or Show Comment...** (`Alt+C`). Choose the reason, or **Show it again**
for one that was hidden. You hear "Hid the comment as off topic." You need
triage access to the repository.

To keep one comment at the top of the conversation, such as the answer or the
current plan, put the cursor on its line and press **Pin or Unpin Comment...**
(`Alt+P`). Choose **Pin it to the top** or **Unpin it**. GitHub shows a pinned
comment first, for everyone.

## Writing a new issue

Open a repository's **Issues** or **Issues and Pull Requests** node. Choose
**Item > New Here...** (Ctrl+N). The Workbench reads the repository's issue
templates before it opens the entry fields.

### Templates

If the repository has readable Markdown issue templates, QUILL asks which to
start from: **Blank issue**, then each fillable template with its description.
The template's title and body fill the entry fields, and its labels and
assignees are carried into the issue.

GitHub's issue forms, the YAML ones that show as a form with boxes on the
website, are on the same list, and QUILL fills them as a real form: one
labelled control per field, with "(required)" in the name of every field
that must be answered. Create Issue says what is still missing rather than
sending an incomplete issue, and the body GitHub receives reads the same as
one filed from the website. A form or template QUILL cannot fill, such as
one too large to load, is left off the list, and QUILL says so once; it is
still there on GitHub. Chapter 12 has the details.

### Title, body and preview

QUILL asks for the title and body in turn. A template can supply either as a
starting value, which you can edit. A blank issue starts with neither.

Before it sends anything, QUILL shows a preview with the repository, title,
template, labels, assignees and body. For a long body the preview shortens
what it displays and says so; the full body is sent if you confirm.

Choose **Create Issue** to send it or cancel to leave the repository
unchanged. When GitHub confirms it, the Workbench says the new issue number
and refreshes the list.

### Many issues at once

When the issues already exist somewhere else, you do not have to type them one
by one:

- **New Issue from Selection...**, in the editor's GitHub menu under From This
  Line, starts one issue quoting the lines you selected, under a link to them.
  See [From the line you are on](#from-the-line-you-are-on).
- **New Issues from Lines...** (`Ctrl+Alt+L`), on the Workbench's File menu,
  makes one issue from each line you selected, a task list included, and can
  make them sub-issues of an issue you name.
- **Import Issues from a Spreadsheet...** (`Ctrl+Alt+I`), on the same menu,
  makes one issue from each row of a CSV or Excel file, with its labels,
  assignees, milestone and type.

Both of the last two show a preview first, and say which rows GitHub would
refuse and why. See [Bringing issues in](#bringing-issues-in).

## Labels, milestones and assignees

### Labels

Labels from a Markdown template are included when the issue is created. A
blank issue starts without labels. After creation, select the issue and use
**Labels...** or **Assignees...** from its context menu to change them.

To manage labels, open the repository's **Labels** node. Select a label to
edit or delete it. To create a label while editing an issue, open the issue's
**Properties**, go to **Labels**, and choose **New Label...**.

### Milestones

Open the repository's **Milestones** node. Each one reads in words: "Release
2.0: 62 percent done, 5 open, 8 closed, due 12 December".

To create a milestone while editing an issue, open its **Properties**, go to
**Milestone**, and choose **New Milestone...**.

- **Show:** (`Alt+S`) chooses Open, Closed or All.
- **Milestones** (`Alt+M`) is the list, and **Details** (`Alt+D`) the selected
  one in full.
- **New...** (`Alt+N`) and **Edit...** (`Alt+E`) ask for a **Title:**, a
  **Description:**, and a **Due date (year-month-day):** such as 2026-12-12,
  which you can leave empty.
- **Close Milestone...** (`Alt+L`) closes the selected milestone after asking.
  On a closed one it reads **Reopen Milestone...**.

In the Workbench, a milestone's context menu also has **Delete
Milestone...**, which deletes it after asking. Its issues and pull requests
stay, with no milestone. Closing keeps the milestone and its history, and is
usually what you want.
- **Open on GitHub** (`Alt+O`) and **Refresh** (`Alt+R`).

Every change is reported from what GitHub sends back.

### Assignees

Markdown templates may provide assignees for a new issue. To change them,
select an issue and choose **Assignees...** from its context menu.

### Handing an issue to Copilot

Signed in, an issue's context menu in the Workbench (`Shift+F10` or the
Applications key) has **Assign #3 to Copilot...**, with the issue's number. It
hands the issue to Copilot's coding agent, which works on it in the background
and opens a pull request for you to review.

QUILL first asks GitHub whether Copilot can be assigned in this repository. If
it cannot, you hear why: the coding agent needs a Copilot plan that includes it,
and it has to be turned on for the repository, which an organization owner may
have to allow. Nothing is changed. If it can, QUILL asks before handing the
issue over and names anyone already assigned, who stay assigned. You hear
"Issue #3 assigned to Copilot." only when GitHub's answer lists Copilot as an
assignee. A closed issue, or one Copilot already has, gets a sentence saying so
instead.

The item is only on issues. To have Copilot look at a pull request, use
**Request Copilot Review** in the review window (Chapter 5).

## Changing many issues at once

The list lets you select more than one row. Use the usual Windows keys for a
list: hold Shift with the arrows to select a run, or hold Ctrl and press Space
to add or remove one row at a time. Then press **Batch...** (`Alt+B`):

- **Close** the selected items.
- **Reopen** them.
- **Add label to** them. QUILL asks for the label.
- **Set milestone on** them, from a list of open milestones, or
  "No milestone (clear it)".
- **Add assignees to** them, as GitHub usernames separated by commas.

Each menu row says how many items it will change, such as "Close 3 selected".
The confirmation names every item and says "This changes the items on GitHub
for everyone watching them." When it is done you hear how many GitHub
confirmed, such as "Batch change applied to 3 of 3 item(s).", and the name of
anyone GitHub would not assign.

Batch works in the Issues & PRs view, and needs you to be signed in.

## Housekeeping

Shift+F10 on an issue has a submenu called **Housekeeping for** and its
number. Signed in, it holds:

- **Lock Conversation...**, with a reason: No reason given, Off-topic, Too
  heated, Resolved or Spam. Only collaborators can comment on a locked issue.
  **Unlock Conversation** opens it again.
- **Transfer Issue...** moves the issue to another repository you can write to.
  QUILL asks for the repository as `owner/name`, then warns that labels and
  milestones are not carried across.
- **Pin Issue** and **Unpin Issue**: a repository can pin a few issues to the
  top of its issue list.
- **Set Issue Type...** chooses the issue's type, such as Bug or Feature, from
  the types the organization has set up. A repository with none says so.
- **Reorder Sub-issues...** opens a list of the issue's sub-issues in order,
  **Sub-issues, in order:**. Select one and press **Move Up** (`Alt+U`) or
  **Move Down** (`Alt+D`). You hear its new place, such as "#12 is now 2 of
  5.", read back from GitHub. Enter opens the selected sub-issue in your
  browser.

On a pull request, the submenu holds only Lock and Unlock, because the others
are for issues.

## Issue fields

An organization can give every issue extra values of its own, such as
Priority, Points or Due date; on your own account you can make them for your
own repositories (the Workbench's **People > My Issue Fields**, and an
organization's **Issue Fields**). Choose **Issue Fields...** on an issue's
context menu to see each one with this issue's value: "Priority (single
choice, field 1): High", or "Due (date, field 2): not set". A field you may
not see, or one of a kind QUILL does not know yet, says so rather than looking
empty.

Choose a field to change it. A single choice offers its choices and **Clear
it**. Any other field with a value asks **Change it...** or **Clear it**
first, so pressing Cancel never clears anything; then QUILL asks for the value
the way its kind needs: a number, a date as year-month-day (2026-12-31), or
text. Only that field is sent, so a value someone else set on another field is
kept. You hear "Points is now 5 on #4."

### Issue types and fields in the Workbench's lists

Each value keeps its type: a date reads as a date (2026-12-31), a number as a
number (3, or 2.5), a single choice as the choice's name, several choices as
their names, and text as text.

- **Columns.** In an Issues list, **View > Columns...** (`Ctrl+Shift+U`)
  offers **Issue type** and **Issue fields**. Neither shows until you choose
  it, because the fields cost GitHub one request an issue; with Issue fields
  chosen, QUILL reads the first 30 issues of the list. A cell reads
  "Priority: High; Due: 2026-12-31; Notes: empty; Owner: not set". A pull
  request leaves both cells blank, and an issue with no type says "no type".
- **Details.** An issue's details name its type, and once its fields are read,
  each field in full, such as "Field Due (date, field 2): 2026-12-31".
- **Filters.** GitHub's own search answers `type:Bug` and
  `field.priority:high`, so type either in the filter box. **Show Only** and
  **Hide** on an issue offer its type and each field value, which write those
  qualifiers for you. A field whose name has a space is not offered there.
  **View > Group By > Type** groups the list by issue type.
- **Properties.** An issue's Properties sheet (`Alt+Enter`) has an **Issue
  Fields** page after Organize: first how many fields the owner defines, then
  one read-only field each, of its own kind. **Issue Fields...** on the row
  changes them.

The states never sound alike, so a missing permission never looks like an
empty field:

| State | In a cell | In details and Properties |
|---|---|---|
| A value | Priority: High | High |
| Set to nothing | Priority: empty | set to nothing |
| Not set | Priority: not set | not set |
| Hidden from you | hidden from you | hidden from you |
| A kind QUILL does not edit yet | Odd: shimmer (read only) | shimmer (read only) |
| The read failed | unreadable, and why | could not be read, and why |

## Deleting an issue

Closing an issue keeps it, its comments and its history; that is almost always
what you want. A repository's admins can also delete an issue for good, such
as one made by mistake or full of spam: choose **Delete Issue...**. QUILL
explains that GitHub cannot bring it back, and asks you to type the issue's
number; anything else deletes nothing. A pull request cannot be deleted this
way.

## Closing, branches and task lists

In the GitHub Workbench, Shift+F10 on an issue has these too.

**Close or Reopen...** on an open issue asks why, as GitHub does: **Completed**,
**Not planned**, or **Duplicate of another issue...**, which then asks for the
other issue's number. You hear "Closed #7 as not planned." or "Closed #7 as a
duplicate of #3, Original title." A duplicate is recorded on GitHub against
the issue you named. On a closed issue the same command reopens it, and a pull
request keeps the plain question, because GitHub gives it no reason.

**Not a Duplicate...** takes back "duplicate of" when an issue was closed
against the wrong one. QUILL asks which issue it was marked a duplicate of,
then says "#7 is no longer marked a duplicate of #3, Original title." The
issue stays closed; Close or Reopen... reopens it.

**Create Branch for This Issue...** makes a branch for the work, from the
default branch, and links it to the issue, so GitHub lists it under the
issue's Development. QUILL suggests a name the way GitHub does, such as
`7-fix-the-parser`; change it if you like. A name git would refuse, or a
branch that already exists, is refused before anything is sent. Afterwards you
hear how to start: `git fetch`, then `git switch` and the name. The issue's
properties (Alt+Enter) list its **Linked branches** on the Relationships page,
beside the pull requests that will close it.

**Unlink Branch...** lists the branches linked to the issue and takes the one
you choose off its Development, after asking. The branch itself stays, with
its commits; only the link goes. The **Linked branches** list on the issue's
Relationships page does the same from the sheet: select a branch and press
Remove (or Delete) to unlink it, or Add (or Insert) to make a new one, and
the list changes as soon as GitHub has answered. A Read Only account, or QUILL
in Safe Mode, is told so and nothing is sent.

An issue's task list is the lines of its description that start with a check
box, `- [ ]` or `- [x]`.

- **Check or Uncheck a Task...** lists the tasks, each read as "Done" or "Not
  done" and its words. Enter on one turns it over and saves the description.
- **Convert Tasks to Sub-issues...** makes each task that is not an issue yet
  into an issue of its own, a sub-issue of this one, and changes its line to a
  link to the new issue, checked or not as it was. It names the tasks and asks
  first. GitHub then shows each line as the issue and its state.

Both read the description again just before saving. If somebody changed it on
GitHub while you were choosing, nothing is saved and you are told to try
again, so nobody's edit is lost.

## Relationships: parents, sub-issues and what blocks what

An issue can be part of a bigger one (its **parent**), have smaller ones
under it (its **sub-issues**), and wait on other issues (it is **blocked
by** them). Choose **Relationships...** on an issue's context menu (or the
Item menu) to see all of it in one list. You first hear a summary, such as
"#41 has a parent, #12, 3 sub-issues, 1 issue blocking it". Each row then
starts with what it is, so the kind comes first:

- "Parent: #12 Spring release (open)"
- "Sub-issue: #44 Write the help (open)"
- "Blocked by: #38 Fix the parser (closed)"
- "Related: #47 The old design (closed)", linked without either waiting on
  the other.
- "Blocking: #50 Publish (open)", an issue that waits on this one.

An issue in another repository is named with it, such as "acme/tools#7".
Enter opens the selected issue in your browser.

- **Add Sub-issue...** (`Alt+S`) asks for the issue to add. Type it as
  `#44`, as `owner/repo#44` for another repository, or paste its address
  from GitHub. If that issue is already a sub-issue of something else,
  QUILL asks before moving it here.
- **Add Blocked By...** (`Alt+B`) records that another issue must be
  finished first.
- **Add Related...** (`Alt+T`) links an issue that belongs with this one,
  such as an earlier attempt, without saying either must wait.
- **Remove** (`Alt+R`) takes away the selected sub-issue, blocked-by or
  related link, after asking. Both issues stay; only the link goes, and you can add
  it again. A parent row and a "Blocking" row are the other end of another
  issue's link, so you change them from that issue.

After each change QUILL reads the relationships back from GitHub and says
what happened, such as "#41 is now blocked by #38." **Reorder
Sub-issues...** is still there for changing their order.

## Projects

GitHub Projects are boards that track issues and pull requests across one or
more repositories, with fields of their own such as Status, Priority or
Iteration. Open the Workbench's **Projects** place or **Repository >
Projects** node to see the projects available to your account. Open a
board to read and change its items and their fields.

A project's own row has these commands too, on its context menu:

- **Add Draft Issue...**: a quick note on the board, with a title and an
  optional body, before it is a real issue.
- **New Field...**: a field of your own. Choose Text, Number, Date, or
  Single select; a single select asks for its choices, separated by commas
  ("Small, Medium, Large").
- **Delete Field...**: choose one of the fields you or your team made, and
  confirm. Every item's value in it goes too. Fields GitHub provides, such
  as Title, Assignees and Labels, are not offered.
- **Post Status Update...**: how the project is going (On track, At risk,
  Off track, Complete or Inactive), with a note and an optional target
  date, the way GitHub shows it at the top of the board.
- **Link to Repository...** and **Unlink from Repository...**: a linked
  project shows in that repository's Projects. Type the repository as
  owner/name.
- **Template...**: make the project a template, or stop. GitHub allows
  templates only in an organization, and offers them when someone there
  makes a new project.
- **Copy Project...**: a copy for another user or organization, with a new
  title. Its fields, views and workflows come with it, and its draft
  issues if you say so; its issues and pull requests do not.
- **Delete Project...**: deletes the board for good. Its issues and pull
  requests stay. QUILL asks you to type the project's title, exactly, so a
  slip of the Enter key cannot delete it.

All of these need your GitHub sign-in to include the **project** scope.

## Starting an issue in its own folder

This one is QUILL's alone. When you start work on an issue, you usually want a
new branch, kept apart from whatever else you have going. Shift+F10 on an
issue or pull request has **Start issue #N in Local Worktree...** (or
**Start pull request #N in Local Worktree...**). It uses Git's worktrees: a
second folder for the same repository, on a branch of its own.

1. QUILL uses the Git folder of the document you have open, or asks you to
   choose the local checkout of the repository.
2. It checks that the checkout's remote really is this GitHub repository, and
   stops with **Repository Does Not Match** if it is not.
3. It suggests a branch name, such as `issue-208-fix-the-status-bar`, and tells
   you which local branch it starts from and whether you have uncommitted
   changes. Those stay where they are, in the folder you already have.
4. It asks you to confirm. Nothing is fetched and nothing is sent to GitHub.
5. You choose where the new folder goes. QUILL suggests one beside the
   existing checkout.

**In QUILL Lite**, this command is not on the menu.

# Chapter 5: Pull requests and review

## What this chapter covers

Reviewing a pull request on the website means a long page of code with
comments wedged between the lines. QUILL turns it into an outline you can
walk: the pull request, its changed files, the conversations on each file, and
its checks. This chapter covers reading a pull request, the diff, commenting
on a line or a range, suggesting a change, sending a review, replying and
resolving, asking Copilot for a review, everything that gets a pull request
merged, and the whole patch, a revert and conflicts.

Reading works signed out. Everything that writes needs a signed-in account.

**In QUILL Lite**, which works as a guest, you can read every part of a
review. The commands that write say they need a signed-in account.

## Opening a pull request

In GitHub Items, select a pull request and press **Review...** (`Alt+R`), or
choose **Open Review...** from its context menu. A pull request link pasted
into **Open Link...** opens straight into its review, and so does a pull
request in your notifications.

**Diff...** (`Alt+D`) skips the outline and opens the changed files on their
own. More on that below.

## The one-sentence summary

The first thing you hear when the review opens is the whole pull request in
one sentence:

"Review loaded for pull request #42. Approved, 2 checks failing, 1 open
thread, 3 commits behind main."

The sentence is built from these, in this order, leaving out what does not
apply:

- whether it is a **draft**;
- the review decision: **Approved**, **Changes requested**,
  **Review required**, or **No review decision**;
- the checks: how many are failing or still running, or "all 4 checks
  passing";
- the open review threads, or "no open threads";
- how far behind its base branch it is, or "up to date with main";
- **merge conflicts**, if there are any;
- **auto-merge on**, if it is set;
- and whether GitHub says it can merge, it is blocked by branch rules, or
  QUILL cannot tell. QUILL never guesses "ready": when it is not sure, it says
  "merge readiness unknown".

A merged or closed pull request just says "Merged." or "Closed without
merging." The same sentence is the first line of the window, **Pull request in
one sentence**, so you can read it again. **Copy Review Summary** (`Alt+S`)
copies the fuller summary.

## The review window

In Tab order:

- The one-sentence summary, then a status line: the merge readiness, the
  review decision, the checks, and how many threads are unresolved or
  outdated.
- **Pull request outline**, the tree. This is where you spend your time.
- **Changed since my last review** (`Alt+L`), a check box. See below.
- The selected node's details, a read-only text field.
- **Review summary**, with **Check Merge Policy** beside it, and the summary
  and merge readiness in full.
- **Checks**, a list of the check runs.
- The status line.
- The buttons: **Next Unresolved** (`Alt+U`), **Next Unvisited** (`Alt+V`),
  **Open on GitHub** (`Alt+G`), **Copy Review Summary** (`Alt+S`),
  **Timeline...** (`Alt+T`), **Compose Review...** (`Alt+C`),
  **Reply to Thread...** (`Alt+R`), **Request Reviewers...** (`Alt+W`),
  **Mark Ready** (`Alt+M`) on a draft or **Convert to Draft** (`Alt+D`)
  otherwise, **Update Branch...** (`Alt+B`), **Auto-Merge and Queue...**
  (`Alt+A`), and **Close**.

The buttons that write are unavailable when you are signed out or the pull
request is closed, and Reply is available only with a thread selected.

### The outline

The tree is a real tree: Up and Down move between the rows you can see, Right
opens a branch and Left closes it. Tab reads the selected row's details, and
Shift+Tab comes back.

- The top row is the pull request: "PR #42:" and its title.
- **Changed files** holds one row per file. Each file opens to the review
  threads on it: "Line 12, alice, 2 replies, unresolved". A thread on a line
  that has since changed adds "outdated".
- **General conversations** holds threads that are not on a file, when there
  are any.
- **Pending line comments, not sent yet** holds comments you have written but
  not sent. See below.
- **Checks** holds one row per check, its result first: "success: build",
  "failure: test", or "in progress: lint" while it runs.

Enter on a row does the natural thing: on a file it opens the file's diff; on
a thread it moves you into its details to read every comment and reply; on a
check it opens the check on GitHub; on anything else it opens or closes the
branch.

Reading or expanding never changes anything. Selecting a thread does not
resolve it or mark it read.

### Moving between threads

- **Next Unresolved** (`Alt+U`) moves to the next thread that is still open,
  and says "Moved to unresolved thread by" the author, and the line. It goes
  round from the end to the start.
- **Next Unvisited** (`Alt+V`) moves to the next thread you have not selected
  in this review. It is how you make sure you have read everything. When you
  have, it says "You have visited every loaded review thread in this
  session."

Neither of these tells GitHub anything. "Visited" lives only in this window.

## Files you have viewed

GitHub remembers, for you alone, which of a pull request's files you have
viewed, so a long review can be done in sittings. Signed in, the review
window reads that after the review loads, and each row under **Changed files**
ends with its state: "src/status.py, viewed", "src/status.py, not viewed", or
"src/status.py, changed since you viewed it" when someone pushed to it after
you looked. The status line says how many you have viewed, such as "3 of 12
files viewed."

Shift+F10 on a file has:

- **Mark as Viewed**, or **Mark as Not Viewed** on one you have viewed. It is
  the same mark GitHub's Files tab shows, and you hear the new count.
- **Show Only Files Not Viewed** hides the files you have viewed, so the
  outline holds only what is left; **Show All Files** brings them back. You
  hear how many are left.
- **Comment on This File...** opens the comment window for a comment on the
  whole file rather than a line: for a file that should not be there, or one
  to rename. It posts at once, outside any review you have pending.

## Changed since my last review

When someone pushes more commits after you have reviewed, you do not want to
read every file again. Check **Changed since my last review** (`Alt+L`).
QUILL finds the commit you last reviewed and keeps only the files that have
changed since then. The tree's first branch is renamed **Files changed since
your review on** and the date, and you hear how many:

- "3 files changed since your review on 4 November."
- "No files changed since your review on 4 November."
- "You have not reviewed this pull request yet, so every file is new to you."

If the branch has been force-pushed and the commit you reviewed is gone from
GitHub, QUILL says so plainly and shows every file. Uncheck the box to see
every file again.

## The diff

Enter on a file, **Open File Differences** on a file's or thread's context
menu, or **Diff...** in GitHub Items, opens the diff window, **PR #42 diff:**
and the title.

- **Changed files**: one row per file, "modified: src/status.py +12 -3".
  Select one to hear its changes.
- **Differences** reads the changes through the same engine as QUILL's Compare
  Documents: "Difference 2 of 5. Text changed at line 41", with both sides
  named and the changed words described.
- **Selected review hunk** shows the part of the file a thread is about, when
  you came here from a thread.
- **Line marks:** (`Alt+M`) chooses how changed lines are marked in the patch
  list, from four styles designed by Kelly Ford for GHManage and The Chat
  Place: **Words** ("Added line 12", "Removed line 9", "Unchanged line 13"),
  **Short words** ("Add 12", "Del 9", "Same 13"), **Diff symbols** ("+ 12",
  "- 9", "= 13"), or **Diff symbols with changed lines**, where a removed line
  is followed straight away by the line that replaced it, marked "!-" and "!+",
  so each change is heard old then new. Symbols are shorter, but your screen
  reader says them only when it reads punctuation, and QUILL reminds you of
  that when you choose them. Your choice is kept, and it is the same choice
  Compare Files, Compare with File and WordPress's Compare with Site use.
- **Next and previous change**: in the patch list, `Alt+N` and `Alt+P` (the
  keys Kelly Ford's GHManage uses), or `F8` and `Shift+F8` (as in Compare
  Files), move to the first line of the next or previous change and say
  where you are: "Change 2 of 5, at new line 41: 1 line removed, 1 added."
  When a few lines were replaced by as many, it also says which words
  changed: "Changed Thursday to Friday."
- **Changed Lines Only** (`Alt+H`), beside it, leaves the unchanged lines
  around each change out of the patch list, so the arrows go from change to
  change. The hunk headings stay, so each change still says where it is. You
  hear how many changed lines there are and how many unchanged ones were left
  out; uncheck it to see them again.
- **Hide Whitespace Changes** (`Alt+W`) leaves out changed lines that differ
  from their partner only in spaces, tabs or blank lines, such as a block
  that was only reindented, so what is left is what really changed. You hear
  how many lines it left out.
- **Choose Commit...** (`Alt+T`) reviews one commit of the pull request at a
  time. It lists them oldest first, "3f9a2c1 Fix the parser, by ann", with
  "All commits: the whole pull request" at the top to come back. The file
  list, the differences and the patch lines then show only that commit's
  change, against the commit before it, and the summary at the top says which
  commit you are on.
- **Patch lines:** (`Alt+P`), the patch one line to a row. This is where you
  comment.
- **Comment on This Line...** (`Alt+L`), **Comment on Lines...** (`Alt+S`),
  **Copy Diff** (`Alt+C`) and **Open Diff in Default App** (`Alt+O`).
- Under them, how many of your line comments are waiting to be sent.

Opened from a thread, the diff goes straight to that thread's lines and says
"Review comment at" the file and line. If the line is no longer in the patch,
it says so and suggests the thread may be outdated.

**Open Diff in Default App** saves the diff as a `.diff` file and opens it in
whatever program your computer uses for those, and tells you where the file
is.

As you arrow through the patch lines, an added line and a removed line each
have a short sound of their own, so you can hear the shape of a change before
the words arrive. They are the sounds **Arrived on an added line of a diff**
and **Arrived on a removed line of a diff** in the Sound Scheme window, where
either can be previewed, changed or switched off, and they follow your sound
setting like every other QUILL sound. Unchanged lines and headings are silent.

## Commenting on a line or a range

In **Patch lines:**, arrow to a line and press Enter, or press
**Comment on This Line...** (`Alt+L`). To comment on several lines, hold Shift
and arrow to select them, then press Enter or **Comment on Lines...**
(`Alt+S`). With one line or none selected, Comment on Lines asks you to type
the range instead, such as `12-15`, `12 to 15` or just `12`.

GitHub takes a comment only on lines the patch shows, and a range only inside
one block of changes. QUILL checks before it sends and tells you which rule
the lines broke, such as "Line 30 is not in this file's changes, so GitHub
will not take a comment on it."

The comment window is titled with where the comment goes, such as
"Comment on line 12 of src/status.py". It has:

- **Lines you are commenting on:**, read-only, so you can check.
- **Suggest a change** (`Alt+S`), a check box. See below.
- **Comment:** (`Alt+C`), where focus starts.
- **Add to Review** (`Alt+A`), the default: keep the comment and send it with
  your review.
- **Post Now** (`Alt+P`): send it on its own, straight away.
- **Comment Window...** (`Alt+W`): write the comment in the same comment window
  as everywhere else, with Insert Mention, Insert Reference, Insert Emoji,
  Insert Saved Reply, Preview and the check before posting. Its button says
  **Use This Text**, which puts what you wrote back in the Comment box here.
- **Cancel**.

Most of the time you want **Add to Review**. GitHub then sends your comments
together, with your verdict, as one review, and people are notified once
instead of once per comment.

### Suggesting a change

Check **Suggest a change** and QUILL puts the lines you chose into the comment
as a suggestion block, ready for you to edit into what they should say. On
GitHub, the author can accept a suggestion with one button. Uncheck it to take
the block out again. A suggestion replaces lines of the new file, so it works
on added and unchanged lines, not removed ones.

## Pending comments and sending your review

Comments added to your review are kept on this computer, for your account,
until you send them. You hear "Added to your review:" and where, and how many
are waiting. They show in the outline under
**Pending line comments, not sent yet**, each with its place and the start of
its text.

On a pending comment, Enter or **Edit Pending Comment...** changes it, and
**Delete Pending Comment...** removes it after asking. It was never sent, so
it cannot be got back.

### Compose Review

When you are ready, press **Compose Review...** (`Alt+C`). The window
**Review Pull Request #42** says how many line comments go with this review,
and has:

- **Review action:**, a list: **Comment**, **Approve** or
  **Request changes**.
- **Review message:** (`Alt+M`), your overall comment. Request changes needs
  one; so does Comment, unless you have line comments.
- **Comment Window...** (`Alt+W`) writes the message in the comment window,
  with mentions, references, emoji, saved replies, the preview and the check;
  **Use This Text** brings it back.
- **Discard Saved Draft**, to throw away a saved review message.
- **Submit Review**, which sends it, and **Save Draft and Close**, which keeps
  it. Escape is Save Draft and Close.

The review message saves as you type, so closing the window loses nothing.
Submit Review is the only thing that sends. Request changes asks once more
before it goes. You hear "Review submitted on pull request #42." and how many
line comments GitHub took with it.

### When the pull request moves under you

Comments are written against one version of the code. If new commits arrive
before you send, the lines you commented on may have moved. QUILL will not
send a review whose comments were written on an older version: it says how
many were, and asks you to delete or rewrite them under Pending line comments
first. If the version changes while the Compose window is open, nothing is
sent, and QUILL tells you to reopen the draft against the current diff.

## Replying and resolving

On a thread in the outline:

- `Ctrl+R`, or **Reply to Thread...** (`Alt+R`), replies. It opens the comment
  window, **Reply to Review Thread**, with the thread's author first under
  Insert Mention, and Preview and the check as everywhere else; **Post** sends
  it. You hear "Reply posted to the review thread."
- `Ctrl+Shift+R` resolves the thread, or reopens a resolved one. It asks
  first. You hear "Review conversation resolved." If GitHub does not let you
  change it, QUILL says so.

The thread's context menu has these, plus **React to a Comment...**,
**Copy Conversation**, **Copy Thread Link**, **Open File Differences** and
**Open Thread on GitHub**.

`Ctrl+R` replies here, in the review window. In GitHub Items it refreshes.

## Getting a pull request merged

### Reviewers, draft and ready

- **Request Reviewers...** (`Alt+W`) asks for GitHub usernames, separated by
  commas. You hear "Review requested from" and their names.
- On a draft, **Mark Ready** (`Alt+M`) marks it ready for review. On one that
  is ready, **Convert to Draft** (`Alt+D`) turns it back into a draft. Both
  ask first.
- **Update Branch...** (`Alt+B`) merges the base branch into the pull
  request's branch, so it is up to date. It asks first, and is unavailable on
  a draft.

### Asking Copilot for a review

**Request Copilot Review**, on the pull request's context menu (`Shift+F10` on
the outline), asks Copilot code review to review the pull request. It has no
button or access key. You hear "Copilot review requested on pull request #4."
only when GitHub lists Copilot among the reviewers. GitHub sometimes accepts the
request and leaves Copilot off the list, which is how it answers an account or a
repository without Copilot code review; QUILL says that plainly rather than
telling you a request went in when it did not. Copilot's review arrives as
review comments, like anyone else's, and the outline shows them after a refresh.

### Merging

Merging is in the Workbench, not the review window, because it is the one
thing here that changes the base branch for everyone. Select the pull request
and press `Ctrl+Shift+Enter`, or choose **Merge...** from its context menu.

QUILL first asks GitHub whether the pull request can merge. If it cannot, you
hear why, the same answer as **Why Can't I Merge?** below, and nothing else
happens. If it can, QUILL asks how to merge: Squash and merge, Merge commit,
or Rebase, offering only the ways the repository allows. Then it asks you to
type the pull request's number to confirm, not just press Yes, and says what
will happen: that it merges into the base
branch, as of the commit QUILL checked, for example "as of commit 3f9a2c1",
and that this changes the branch for everyone. You hear "Merged #42" and the
start of the new commit.

That commit is the one that merges. If somebody pushes to the pull request
between the check and your typing the number, GitHub refuses, nothing is
merged, and QUILL says so: "Somebody pushed to #42 after commit 3f9a2c1 was
checked, so nothing was merged." Check again and you are merging what you
have actually read.

When the base branch merges only through a merge queue, Merge... does not try
to go around it: you hear that the pull request can join the queue, and **Add
to or Remove from Merge Queue...** puts it there.

### Merging several at once

To merge more than one pull request, select them in the list (hold `Shift` or
`Ctrl` with the arrow keys), then choose **Merge Selected...** from the
context menu or the Item menu. It needs at least two open pull requests
selected; anything else in the selection is left out.

1. QUILL asks once how they should merge: Squash and merge, Merge commit, or
   Rebase. Where a repository does not allow that way, QUILL uses one it does,
   and the preview says which.
2. It asks GitHub about each pull request on its own, with the same question
   as **Why Can't I Merge?**. One that cannot merge does not hold up the
   others.
3. The preview lists every pull request: "#42: will merge into main by squash
   and merge, commit 3f9a2c1.", "#43: will join the merge queue for main" when
   its branch requires a queue, or "#44: will not merge." and the reasons.
   The first line sums it up, such as "Of 3 pull requests: merge 2; 1 will
   not." Press Enter to go on, or Escape to change nothing, and then type how
   many will go in.
4. QUILL merges them one at a time, about a second apart. Just before each
   one it asks GitHub again, because merging one can make the next conflict or
   put it behind its base. A pull request that can no longer merge, or that
   has new commits since the preview, is left alone, and says why: you agreed
   to merge the commit you were shown, not a later one. A failure stops
   nothing else.

At the end you hear one sentence with the counts, such as "Merged 2 of 3 pull
requests, 1 not merged.", and the results list has a line for each pull
request. **Copy Results** copies them, and **Retry Failed** (`F8`) starts again
with only the ones that failed, preview and all.

### Why Can't I Merge?

**Why Can't I Merge?** on a pull request's context menu in the Workbench
answers the question GitHub's merge box answers with colours and icons. You
hear either that it can merge, "#42 can merge into main, as of commit
3f9a2c1.", or each reason it cannot, each with what to do:

- It is a draft: mark it ready for review first.
- It conflicts with its base: **Resolve Conflicts in a Worktree...**, in
  QUILL, takes the conflicts to your computer.
- It is behind its base, and the branch's rules want it up to date: update
  the branch.
- A reviewer requested changes, or it needs an approving review.
- A required check failed, or has not finished, named: "Required checks test
  and lint failed. Re-run or fix it." A check that failed but is not
  required is mentioned as not required, and does not stop the merge.
- A rule on the base branch blocks it for another reason: **Check Merge
  Policy** in the review window names the rules.

It also says when auto-merge is on, and its place when the pull request is
in the merge queue. The answer is always for one commit, which it names, so
you know a push after you asked may change it.

### Auto-merge and the merge queue

On a pull request's row in the Workbench, **Auto-Merge...** turns auto-merge
on, after telling you what it would be waiting for and asking how to merge,
or offers to turn it off when it is on. A pull request that can merge now has
nothing to wait for, and QUILL says so rather than switching it on. **Add to
or Remove from Merge Queue...** adds the pull request to its branch's queue,
naming the commit, or offers to take it out when it is in, saying its place.
The repository's **Merge Queue** node lists the whole queue in order.

In the review window, **Auto-Merge and Queue...** (`Alt+A`) opens a menu:

- **Enable Auto-Merge...** tells GitHub to merge the pull request by itself as
  soon as its required reviews and checks pass. QUILL asks how: Create a merge
  commit, Squash and merge, or Rebase and merge.
- **Disable Auto-Merge...** turns it off.
- **Add to Merge Queue...** puts the pull request in the branch's merge queue,
  if it has one. You hear its place in the queue.
- **Remove from Merge Queue...** takes it out.
- **Combined Check Status** says all the checks in one sentence, such as
  "3 of 4 checks pass; failing: test."

Each asks first, and reports what GitHub confirmed. When GitHub refuses for a
reason QUILL knows, it says what to do about it, for example that auto-merge
is turned off for the repository and an administrator can turn it on in the
repository's settings, or that GitHub can merge the pull request now, so there
is nothing for auto-merge to wait for.

### Merge policy

**Check Merge Policy** reads the rules on the base branch: required reviews,
required checks, code owners and the merge queue. It adds them to the review
summary, and from then on the readiness and the combined check status count
only the checks that are required ("3 of 4 required checks pass"). The rules
are read for the current version of the pull request; refresh the review after
new commits to check again. GitHub always has the last word, and QUILL says
so.

### A check that needs another run

On a check in the outline, the context menu has **Re-request Check...**,
which asks GitHub to run that check again. Some checks are older-style commit
statuses rather than check runs, and those cannot be re-run from outside;
QUILL says so. Chapter 6 covers checks and workflow runs in full.

## The whole patch, a revert, and conflicts

Three commands on a pull request's row in the GitHub Workbench do what the
web's Files tab, its Revert button and its conflict editor do.

### Open Patch in Editor

**Open Patch in Editor** opens the pull request's whole change as one
document: every changed file, one after another, as a unified diff, the same
text the website's `.diff` link gives and the text `git apply` reads. Each
file starts with a line beginning `diff --git`, so the editor's Find moves
from file to file, and each change starts with a line beginning `@@`, which
names the lines it touches. A removed line starts with a minus sign and an
added line with a plus sign.

A file GitHub sends no text change for, such as an image or a very large file,
is not left out silently: it has a line of its own starting with `#`, which
names the file and says so. When the patch opens you hear how many files it
has and how many of them have no text, for example "Opened the patch of #42.
The patch has 12 files. 1 of them has no text change GitHub can send, binary
or too large, and each is named on a line starting with #."

The patch is saved as `<repository>-pr-<number>.diff` in the folder where the
Workbench keeps the documents it opens, so Save As keeps a copy anywhere you
like.

### Revert Pull Request

On a merged pull request, **Revert Pull Request...** opens a new pull request
that undoes it, as the Revert button on the website does. QUILL asks for the
new pull request's title, which starts as `Revert "` and the old title, and
then asks whether to open it as a draft. Yes opens a draft, which nobody can
merge until it is marked ready; No opens it ready for review. Nothing is
undone until the revert is itself merged, so this is a proposal, not a
change to the branch.

You hear "Opened pull request #57, which reverts #42." A pull request that
is not merged has nothing to revert; the command is greyed, and its help says
why. You need write access to the repository.

### Resolve Conflicts in a Worktree

When a pull request cannot merge because it conflicts with its base branch,
**Resolve Conflicts in a Worktree...** gets the conflicts onto your own
computer without touching the folder you are working in:

1. QUILL asks which local checkout of the repository to use, if the document
   you have open is not in one, and finds the remote that is that
   repository on GitHub.
2. It asks first, naming the remote and both branches. This is the one step
   that uses the network, and it is your own Git that does it, with your own
   sign-in, as `git fetch` from a terminal would.
3. It makes a new folder beside your checkout, a Git worktree, on a new branch
   called `pr-<number>-conflicts` made from the pull request's branch, and
   merges the base branch into it there. Nothing is committed.
4. You hear how many files conflict and their names, and the editor's
   **Resolve Conflicts** walks each one, the same window as Tools > Local Git
   > Resolve Conflicts: each conflict in turn, with your version and theirs
   read out, and a choice for each.

When the files are resolved, commit in that folder and push the branch to the
pull request's branch; QUILL says the exact command, for example
`git push origin pr-42-conflicts:fix-parser`. The new folder stays until you
remove it with Tools > Local Git > Worktrees.

A pull request from a fork is the exception: its branch lives in the fork,
not in the repository, so QUILL says so and leaves it to a checkout of the
fork, or to its author. If the base merges with no conflicts, QUILL says that
instead, and the merge is left staged, not committed.

## Writing a new pull request

In a repository's **Pull Requests**, press `Ctrl+N`. To start from a branch,
select it in Branches, press `Ctrl+Shift+N` and choose Pull Request. The New
Pull Request window has Merge into, Merge from, Title, Description and a
Create as a draft check box. The title and description start from the
commits you are proposing, a branch that already has an open pull request is
taken to that one instead of making a second, and Cancel keeps your text for
the session. [Chapter 12](#chapter-12-the-github-workbench-place-by-place) walks through it.

# Chapter 6: Actions and checks

## What this chapter covers

GitHub Actions runs a repository's builds and tests. When a run fails, the
website gives you a page of collapsed boxes and a log thousands of lines long.
This chapter shows you how to get from "the build failed" to the line that
broke it in a few keys: the run list, What Failed, jobs and logs, and the
commands that rerun, cancel, delete and approve runs. It also covers combined
check status, deployments waiting for approval, artifacts, caches, self-hosted
runners, and the names of a repository's secrets.

Reading runs and logs works signed out for a public repository. Anything that
changes a run needs a signed-in account.

## Workflows and workflow runs

GitHub Items has two views for Actions, both in **View:** (`Alt+I`):

- **Workflows** lists the repository's workflow definitions: name, whether it
  is active, and its file.
- **Workflow Runs** lists recent runs, newest first. Each row reads the
  workflow's name, its status ("completed", "in_progress", "queued"), its
  result ("success", "failure", "cancelled"), the branch, what started it
  ("push", "pull_request", "schedule") and the run number. These are GitHub's
  own words, as GitHub sends them.

Details on a run gives the same in full, one line each, with when it started
and its link.

### Running a workflow by hand

Some workflows are set up to be started by hand. Select one in **Workflows**
and press Enter, or choose **Run Workflow on Branch...** from its context
menu. QUILL asks which branch or tag to run it on, starting with `main`, then
confirms: "Run workflow" and its name, "on" the branch, "in" the repository.
You hear "Dispatched" and the workflow and branch.

QUILL asks only for the branch. A workflow that needs other inputs before it
can start has to be run from GitHub's own page.

In QUILL, **Tools > Git and GitHub > GitHub > Dispatch Workflow...** does the
same without opening GitHub Items.

### Turning a workflow on or off

A workflow that is turned off runs on nothing: not on a push, not on a
schedule, not even Run Workflow. GitHub turns off a scheduled workflow by
itself after sixty days without activity in the repository, which is a common
reason a nightly job quietly stopped. **Turn Workflow On or Off...** on a
workflow's context menu says its state in words first, "on", "turned off" or
"turned off by GitHub after 60 days without activity", and asks before
changing it. You hear "Turned on" and its name, or "Turned off". The
workflow's Properties sheet has the same switch as its Enabled field.

### Editing a workflow

**Edit Workflow...** on a workflow's context menu opens the workflow file as a
form you read from top to bottom instead of YAML. **New Workflow...**, in
**Repository Actions...** (`Ctrl+Shift+G`), starts one from a starter that
runs on a push to main and by hand.

- **Triggers** is a list, one row per event: "On a push, branches main, paths
  ignore docs/\*\*", "Run by hand, 2 inputs", "On a schedule: 30 5 \* \* 1".
  **Add Trigger...** asks for the event, then its settings: branches, tags and
  paths for a push or pull request, one cron line per time for a schedule,
  and for Run by hand a list of inputs, each with its type, whether it is
  required, its default and, for a choice, its options.
- **Workflow Permissions...** sets what the workflow's token may do: not set,
  read everything, write everything, none, or one level per scope.
- **Jobs** is a list, one row per job: "Build (build), runs on ubuntu-latest,
  runs after Test and Lint, 4 steps". **Edit Job...** has its id, name,
  runner and a check box for each job it runs after; renaming a job carries
  every other job's needs with it. **Job Steps...** lists the steps, each a
  form with the action it uses or the commands it runs, its inputs (one
  `name: value` per line), variables and condition. **Job Permissions...**
  is the same form as the workflow's, for one job.
- **When jobs run** reads the whole dependency graph in words: "First Test
  and Lint, together. Then Build."
- **What GitHub would say** lists everything GitHub would reject the file
  for, kept current as you change it: a key GitHub does not know, a job that
  needs a job that does not exist, jobs that wait for each other in a loop, a
  step that both uses an action and runs commands, an action with no
  version, a permission GitHub does not have. Save refuses while any is
  listed.

Save asks first, naming the file, the repository and your account, then
commits to the default branch, or to a new branch with a pull request when
the default branch is protected or **Save through a pull request** is
checked. If someone changed the file on GitHub since you opened it, nothing
is overwritten and the editor opens again with your draft. Comments at the
top of the file are kept; comments inside it are not, because QUILL's YAML
reader cannot keep them, and the window says so. A file you did not change is
never rewritten.

## What Failed

This is the command to learn first. Select a failed run in **Workflow Runs**
and press `Ctrl+Shift+W`, or choose **What Failed...** from **Actions...** or
the context menu. `Ctrl+Shift+W` works only in that view; elsewhere in QUILL
it is another command.

A window titled **What Failed:** and the run opens. While it loads you hear
"Loading what failed...". When it is ready, focus lands at the top of a
read-only text field, **What failed** (`Alt+W`), and QUILL says "What failed
is ready." and the first line of the summary.

The text is one digest of everything you would otherwise dig for:

- How many jobs failed, such as "2 of 7 jobs failed."
- For each failed job, "Job 1 of 2:" with its name and result, then its failed
  steps by number and name.
- The job's annotations: the errors and warnings the tools reported, each with
  its file and line, such as "src/status.py:41: error: name is not defined".
- The last 40 meaningful lines of each failed step's log.

The log lines are cleaned up for listening. Timestamps and colour codes are
taken out, and GitHub's markers become words: "ERROR:", "WARNING:", "NOTE:",
"Command:". QUILL finds each failed step's lines by the times GitHub recorded
for that step. If GitHub gave no times, the digest says so and uses the end of
the job's log instead.

Up to ten failed jobs are shown; a run with more says how many are left and
suggests opening the run on GitHub.

**Copy All** (`Alt+C`) copies the whole digest, ready to paste into a comment
or a message. **Refresh** (`Alt+R`) reads it again, for a run that is still
going. Escape closes the window.

## Jobs and logs

For the whole picture, choose **View Jobs and Logs...** on a run. The window
**Jobs for** and the run has, in Tab order:

- **Attempt:** (`Alt+A`). A rerun makes a new attempt, and the earlier ones are
  kept. The current one is marked "(current)"; up to the latest 20 are
  offered.
- **Workflow jobs**, one row per job: its result, then its name, such as
  "failure: test (windows)".
- **Job details and log**, a read-only text field: the job's status and
  result, when it started and finished, the attempt, the commit, and every
  step with its result. After you load the log, the log is here too.
- The status line, then the buttons:
  - **Load Log** (`Alt+L`) loads the selected job's log as plain text. Enter
    on a job does the same. Focus moves to the details when it arrives.
  - **Load Annotations** (`Alt+N`) loads the errors and warnings the job's
    tools reported. If GitHub refuses, QUILL says so, rather than suggesting
    there were none.
  - **Open Job on GitHub** (`Alt+J`) and **Open Run on GitHub** (`Alt+R`).
  - **What Failed...** (`Alt+F`), the digest above, for the attempt you
    chose.
  - **Re-request Check** (`Alt+C`), see below.
  - **Follow This Job** (`Alt+W`), see below.
  - **Close**. Escape closes too.

A log over 4 MB is cut off there, with a line saying so and suggesting the job
page on GitHub. Annotations stop at 100, also with a line saying so.

### Following a job while it runs

GitHub shows a running job's log only on its own web page; the log QUILL can
load arrives when the job has finished. What QUILL can follow while it runs is
its steps. Select a running job and check **Follow This Job** (`Alt+W`): you
hear where it is, for example "build: On step 3 of 9, Run tests; 2 done", and
from then on, every few seconds, each step as it starts and as it finishes,
"Step 3, Run tests, failed.", without your having to look. When the job ends
you hear how, "build failed. Load Log reads its whole log.", and following
stops by itself. Uncheck the box to stop sooner.

At any moment, `Alt+8` says how far along the selected job is: the step it is
on, how many are done, and any that have failed so far.

## Doing something about a run

On a run in **Workflow Runs**, **Actions...** and the context menu hold the
commands that act on it. Each one asks first, and the default answer is No.
Answering No to most of them says "Cancelled; nothing was sent to GitHub."

- **Re-run Workflow** reruns every job in the run.
- **Re-run Failed Jobs Only** reruns just the jobs that failed, which is
  usually what you want after fixing a flaky test. You hear "GitHub started a
  re-run of the failed jobs of" and the run. On a run where nothing failed,
  GitHub refuses, and QUILL passes on its reason.
- **Cancel Run...** stops a run that is still going. GitHub only promises to
  stop it, so QUILL says "GitHub accepted the cancel request and is stopping"
  the run, "Refresh to check."
- **Delete Run...** deletes the run for good. The confirmation names the run,
  its branch and its result, and says its logs and artifacts go with it and
  that this cannot be undone.
- **Approve Run from a Fork...** lets a run from someone else's fork go ahead.
  GitHub holds these until a maintainer approves them, because the code in
  them has not been reviewed. The confirmation says so: approve only code you
  have read, since it runs with this repository's permissions.
- **Review Pending Deployments...**, below.
- **Combined Check Status**, below.

## Combined check status

**Combined Check Status** reads every check on the run's commit and says them
in one sentence: "Commit 1a2b3c4: 3 of 4 checks pass; failing: test." If some
are still going it adds how many, and it names any that have not reported
yet. It reads only, so it works signed out.

The review window has the same command (Chapter 5). There, after
**Check Merge Policy**, it counts only the checks the branch requires.

## Re-requesting a check

A check that failed for reasons outside the code, a network blip, say, can be
asked to run again on its own. In **Jobs and Logs**, select the job and press
**Re-request Check** (`Alt+C`). QUILL asks first, then says "GitHub queued the
check for" and the job "to run again." The review window's Checks branch has
**Re-request Check...** on each check's context menu too.

## Deployments waiting for approval

A workflow can stop before deploying to an environment, such as production,
until someone approves. **Review Pending Deployments...** on the run opens the
window **Pending Deployments:** and the run.

- **Environments waiting for review** (`Alt+E`): one check box per
  environment, saying whether you can approve it, who the reviewers are, and
  any wait timer. The ones you are allowed to approve start checked.
- **Comment (GitHub requires one)** (`Alt+C`).
- **Approve** (`Alt+A`) and **Reject** (`Alt+R`), then **Close**.

Write a comment, check the environments, and press Approve or Reject. QUILL
asks once more, naming the environments, and then says which ones GitHub
approved or rejected. If nothing is waiting, the window says "This run is not
waiting on any deployment review."

## An environment's rules

An environment's row, under Repository > Deployments, has these on its context
menu, beside Secrets... and Variables...:

- **Branch Policies...:** which branches and tags may deploy to it, when it
  allows chosen ones only. Add one by name or with a wildcard, such as
  `release/*`, and say whether it names branches or tags. Change rewrites the
  pattern; Delete removes it.
- **Protection Rules...:** GitHub Apps that must approve each deployment to it.
  Add one by choosing from the apps GitHub says are installed and can do this;
  if there are none, QUILL says so. Delete removes one.
- **Deployments...:** its newest deployments, each with its latest state:
  "production: success, 2026-11-01 11:05 by jeff (v1.0, commit 3f9a2c1)." You
  hear how many there are and the newest one's state; the list has a line
  each. To approve or reject a deployment that is waiting, use **Review
  Pending Deployments...** on the run that is waiting, above.

An environment's **Properties...** (`Alt+Enter`) puts its protection on one
sheet: the required reviewers, prevent self-review, the wait timer and whether
administrators may bypass, with the custom protection rules (the apps) listed
under them; which branches and tags may deploy, with the chosen ones listed;
how many secrets and variables it has, with their names; and its newest
deployments. The protection, the wait timer and the branch choice can be
changed there; the lists are read only, and the commands above change them.

## Starting workflows from outside

A workflow can start on `repository_dispatch`, an event sent on purpose rather
than by a push. **Send Repository Dispatch...**, on a repository's context
menu, sends one: give the event's name, as the workflow's `types` list says,
such as `deploy`, and optionally extra values as JSON, such as
`{"env": "test"}`, which the workflow reads as `github.event.client_payload`.
You hear "Sent deploy." and the run appears under Actions.

## Deleting a deployment

Under Repository > Deployments, a deployment's context menu has **Delete
Deployment...**, which removes it from the history after asking. GitHub
deletes only an inactive deployment; a newer deployment to the same
environment makes the older one inactive, and QUILL says so if you try too
early.

## Artifacts

A run can leave files behind: a built installer, a test report. On a run,
choose **View Artifacts...**. The window lists them with their size and
whether they are still available; GitHub deletes them after a while, and an
expired one cannot be downloaded.

- **Download Selected...** (`Alt+S`) and **Download All...** (`Alt+A`) ask for
  a folder, then save each artifact as a `.zip` file. If a file of that name is
  already there, QUILL asks before replacing it. A progress window with a
  **Cancel** button follows the download.
- **Refresh** (`Alt+R`), for a run still making artifacts.
- **Open Run in Browser** (`Alt+B`) and **Close**.

GitHub hands each download to a short-lived address on another server. QUILL
fetches that without your token, so the token is only ever sent to GitHub.

## Caches

Workflows keep caches to run faster: downloaded packages, build outputs. They
are listed in Explore. Choose **Actions caches** in **View:**, with the
repository in **Repository:**. The first row sums them up, such as "12 Actions
caches in community-access/quill" and their total size. Each row after it
reads the cache's key, size, branch and when it was last used, newest first.

A stale or broken cache can make a build fail in strange ways. On a cache's
row, **Delete Cache...** removes it after asking. Workflows build it again the
next time they need it.

## Self-hosted runners

A runner is the machine a workflow's jobs run on. GitHub lends its own, and a
repository can bring its own as well, called self-hosted: a lab machine with a
graphics card, a Mac for signing, a build server inside a company network.
When those jobs sit waiting forever, the first question is whether the
machine is even there.

In the GitHub Workbench, **Repository > Actions > Runners** lists them. Each
row reads the runner's name, its state and its system, such as "lab-1:
online, busy, Linux" or "old-mac: offline, macOS". "Online, idle" means it is
there and waiting for work; "online, busy" means it is running a job now;
"offline" means GitHub has not heard from it, which is why jobs that ask for
it never start. The details pane adds the runner's labels, the words a
workflow's `runs-on:` line asks for, so you can check that the job and the
machine agree. Enter, or **Open on GitHub**, opens the repository's runner
settings page.

GitHub shows runners only to the repository's administrators. Anyone else
hears "GitHub shows owner/name's runners only to its administrators." in the
node's note, rather than an empty list that looks like there are none. A
repository that uses only GitHub's own runners lists nothing.

Adding and removing runners needs you to administer the repository:

- **New Runner...**: press `Ctrl+N` in Runners. QUILL asks which system the
  machine runs, such as Linux x64 or Windows x64, then puts the commands that
  set it up on the clipboard and says so. Paste them into a terminal on that
  machine. They download the runner, check its SHA-256 checksum, and register
  it with a token that works for an hour. The token is never said or shown in
  a list.
- **Runner Labels...** on a runner adds a label, such as `gpu`, or takes away
  one that someone added. The labels GitHub gives every runner, such as
  `self-hosted` and `linux`, cannot be taken away.
- **Remove Runner...**, or the Delete key, asks first, then GitHub forgets the
  runner and the program on that machine gets no more jobs.

## Secret and variable names

**Secret and variable names**, also in Explore, lists the names of the
repository's secrets and variables, and those of each environment, with when
each was last updated: "Repository secret: DEPLOY_KEY, updated 2026-10-02". It
answers "is that secret set?" without anyone needing to see it.

The names are all you get. QUILL never reads a secret's or variable's value,
and it drops any value GitHub sends before it reaches the screen.

Both of these views need a signed-in account with access to the repository's
settings.

# Chapter 7: Code and repositories

## What this chapter covers

This chapter is about the code itself and the repository around it. It covers
browsing files at any branch, tag or commit, blame and file history, opening a
file to edit, branches and comparing them, commit comments, tags and
releases, searching across GitHub, forks, templates and topics, the community
profile, insights, looking after a repository, watching, starring and
following, your packages, writing and editing gists, and cloning a repository to your
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

## From the line you are on

When a file you have open lives in a GitHub repository on your computer, one
you cloned or a worktree, **GitHub > From This Line** (`R`) answers questions
about the line your cursor is on, or the lines you have selected. It opens the
Workbench only when it must. With workbench mode off, the same submenu is at
**Tools > Git and GitHub > GitHub > From This Line** (`L`).

- **Copy GitHub Link to This Line** (`K`) puts a link on the clipboard to
  these lines in the commit you have checked out, so it keeps showing the same
  text after the file changes: "Copied the link to lines 12 to 15."
- **Who Changed This Line?** (`O`) says the last commit that touched the line:
  "Changed by alice on 4 November 2026: Fix the status bar (1a2b3c4)." Press
  it again within ten seconds to open the pull request that brought that
  commit. Until November 2026 it was Local Git's **Who Wrote This Line...**,
  and it answered for line 1 wherever your cursor was; it now answers for the
  line you are on. Like the rest of Local Git, it needs the Developer profile
  or Developer Tools turned on.
- **Open the Pull Request for This Line** (`E`) opens that pull request
  straight away, in the Workbench's Pull Requests list narrowed to its number.
  If the commit went straight to its branch, QUILL says so.
- **Open This Line on GitHub** (`U`) opens the same link in your browser.
- **New Issue from Selection...** (`N`) starts an issue that quotes what you
  selected, as a code block, under a link to those lines. It opens the
  Workbench's own New Issue window with the title and body filled in, so you
  can change them, and nothing is sent until you have read the preview and
  said yes. Select some text first.
- **Issues Mentioning This File** (`F`) opens the Workbench's **Search >
  Issues and Pull Requests** on the file's path.
- **Comment on This Line in the Open Pull Request...** (`T`) is for a branch
  you have checked out that has an open pull request. It asks for your
  comment, in Markdown, then posts it on these lines of that pull request.
  If your copy and the pull request are at different commits, or the file has
  changes you have not committed, it says so and stops, because the line
  numbers would not match.
- **Open the GitHub Reference at the Cursor** (`R`) opens the Properties
  sheet of what is written where your cursor is, in the Workbench: `#42` or
  `GH-42` in this repository, `owner/name#42` in another, a commit hash,
  `@person`, or a GitHub address of an issue, pull request, discussion or
  commit. A bare `#42` is read from GitHub first, to know whether it is an
  issue or a pull request.
- **`Alt+Enter` on a reference** does the same without the menu: with the
  cursor on `#42`, `@person` or a GitHub address, `Alt+Enter` opens its
  Properties sheet. Anywhere else in the document `Alt+Enter` does what it
  always did, so it costs you nothing where there is no reference.

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

It also has:

- **Merge Into...**, which merges the branch into another, on GitHub, as a
  merge commit, the way GitHub's merge button would but with no pull request.
  QUILL offers the default branch first and asks before merging. You hear
  "Merged topic into main as abc1234.", or that there was nothing to merge, or
  that the two conflict and nothing was merged. Branch protection still
  applies: a protected branch that needs a pull request refuses.
- **Download Source...**, the branch's files as a zip or tar.gz file, saved
  where you choose. A tag's context menu has it too.

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

A tag can be made on its own, without a release. In the Tags view, `Ctrl+N`
(New Here, on the File menu) asks for the tag's name,
such as `v1.2.0`, and which branch, tag or commit to put it on, starting with
`main`. QUILL refuses a name git would refuse, and a tag that already exists,
before sending anything, and says "Made tag v1.2.0 on main, commit 3f9a2c1."

Then QUILL asks for a message. Leave it empty for a lightweight tag, which is
only a name for the commit. Type a message, such as "First beta", and the tag
is annotated: git keeps the message with who made it and when, the way most
projects tag a release. You hear "Made annotated tag v1.2.0 on main, commit
3f9a2c1." Cancel at any of the three questions and nothing is made.

**Read Tag Message**, on a tag's context menu, says who made an annotated tag,
when, and its message: "v1.2.0, tagged by Jeff Bishop on 2026-11-18: First
beta". For a lightweight tag it says there is no message.

**Delete Tag...** on a tag's context menu (or `Delete`) asks first. If a
release is built on the tag, the question says so, because deleting the tag
leaves the release without one. The commit itself stays; only the name goes.

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
- **Delete Release...** deletes the release, its notes and its files. Choose
  **Delete the release, keep the tag**, which leaves the tagged commit as it
  was, or **Delete the release and its tag**. It cannot be undone.

### Release evidence and attestations

**Release Evidence...**, on a release's context menu, gathers what vouches for
a release, and changes nothing. You hear one sentence, such as "v1.0:
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
that file alone. The release's **Properties...** page says whether it is
immutable, and a file's says its digest.

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

## Dependabot, code owners and configuration

These live on **Repository > Templates**, beside the community files, and on
**Repository Actions...** (`Ctrl+Shift+G`).

### Dependabot

The **Dependabot configuration** row opens `.github/dependabot.yml` as a
list of entries, one row each: "pip in /, weekly on Monday at 09:00, up to 5
pull requests, labels dependencies". **Edit Entry...** has the ecosystem, the
directories, how often, the day, time and time zone, the most open pull
requests and the target branch. Groups, ignore rules and registries are
kept as they are and counted on the row. **What Dependabot would say** lists
what it would refuse, such as two entries for the same ecosystem and folder,
and Save refuses while any is listed. When the file is missing, the row
starts one that keeps the repository's actions up to date.

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
in the file are kept. **Who owns this path** answers with the rule that
wins, as GitHub decides. **Check Owners** asks GitHub whether each owner
exists and can write. **Problems found** lists rules GitHub would skip by
their shape, the problems GitHub itself reports for the file on the default
branch, and what Check Owners found.

**Who Owns This?** on a file or folder in the repository's files says its
owners and the line of the rule that wins. From Repository Actions, **Who
Owns This Path?...** asks for any path.

### Comparing configuration with another repository

**Compare Configuration With Another Repository...**, in Repository Actions,
compares this repository's workflows, issue and pull request templates,
discussion forms, community files, Dependabot file and CODEOWNERS with
another repository, or with the owner's `.github` repository, which it
offers first. From an organization's `.github` repository its starter
workflows count too. The window checks every file that is missing here or
differs, each with the lines added and removed, and shows the selected
file's differences to read line by line. Files that are the same, or only
here, are counted and kept. **Propose Update** asks once more, then opens one
pull request with the checked files and a summary of each. Nothing changes
until that pull request is merged; QUILL never pushes these to the default
branch.

## Insights

**Insights: traffic and contributors** gives a repository's last 14 days in
one sentence, such as "community-access/quill: 120 views (30 unique) and 14
clones (6 unique) in the last 14 days, 9 contributors." Each row after it is
one figure: views and clones on each day, the sites that sent people, the most
visited pages, and each contributor's commits. The list is the table.

Traffic figures need push access to the repository. Without it, QUILL says so,
and still lists the contributors.

### Commit activity, as tables

GitHub's Insights pages draw a repository's history as charts. **Repository >
Insights > Commit Activity** in the GitHub Workbench (**Commit activity as
tables** in Explore's **View:**) reads the same numbers as rows, each a whole
sentence, newest first:

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
or more, gets no statistics from GitHub at all, and QUILL says that rather
than showing an empty table. Anyone can read these for a public repository.

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

### Transferring a repository

**Transfer Repository...** moves a repository to another person or to an
organization, with its issues, pull requests, wiki, stars and watchers. It is
on the GitHub Workbench's Repository menu (`Ctrl+Alt+T`) and on
Repository Actions (`Ctrl+Shift+G`). QUILL asks for the new owner, then asks you to type the
repository's full name, because you may lose access to it and only the new
owner can move it back.

Moving it to an organization you can create repositories in happens at once,
and you hear the new name, such as "Transferred jeff/notes; it is now
community-access/notes. The old address redirects." Moving it to a person
sends them a request they have a day to accept, and QUILL says so. Only an
owner or administrator of the repository can transfer it.

## The wiki

A wiki is a repository's own pages of documentation. GitHub keeps them as a
git repository of their own, with no API for the pages, so QUILL works on them
the way git does.

**Repository > Wiki** in the GitHub Workbench says whether the repository's
wiki is on. When it is, Enter opens it on GitHub to read, and **Clone Wiki...**
(`Ctrl+Alt+W`, on the Repository menu) opens the same Clone Repository window
as any clone, with the wiki's address already filled in, such as
`community-access/quill.wiki`. Its pages arrive in that folder as Markdown
files, one for each page, named after the page's title. Open one in the
editor, change it, then commit and push with git, and GitHub shows the change
at once. A wiki that is turned off says so, and that its administrators turn
it on in the repository's Properties, on the Features page.

## Webhooks, deploy keys and autolinks

Three of a repository's settings are lists, under **Repository > Settings**
in the GitHub Workbench. Each needs you to administer the repository; anyone
else hears that instead of an empty list.

### Webhooks

A webhook is an address GitHub sends a message to when something happens: a
continuous integration server, a chat bot, a deployment script. **Webhooks**
lists them, one sentence each: "https://ci.example.org/hook: on, JSON, push
and pull_request, last delivery succeeded (200)." A webhook whose last
delivery failed says so, with GitHub's reason, which is usually the first
thing to check when a build stopped starting.

`Ctrl+N` there adds one: the address, JSON or form, which events (just push,
everything, or a check list of the common ones), and a secret GitHub signs
each message with. The secret is typed in a password box. QUILL sends it once
and never shows, says or keeps it; GitHub never gives it back either, so to
change it you set a new one. GitHub sends a new webhook a ping straight away.

On a webhook:

- **Ping** sends it a test message.
- **Send Test Push**, on a repository's webhook, asks GitHub to send it the
  latest push as a test, if it listens for pushes.
- **Turn On or Off...** stops GitHub sending it anything, without deleting it,
  or starts it again.
- **Recent Deliveries...** lists what GitHub sent, newest first: "push at
  2026-11-18 09:30: succeeded (200)", or failed with the code it got back.
  Choose one to deliver it again, after a question.
- **Change Address or Secret...** offers the address to edit and a password
  box for a new secret; leave either as it is to keep it.
- **Delete Webhook...**, or the Delete key, asks first. Its delivery history
  goes with it.

An organization has webhooks of its own, which hear about every repository in
it: **Organizations >** the organization **> Webhooks**, with the same
commands. They need you to own the organization.

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

### Star lists

GitHub lets you sort your stars into lists of your own, such as "Screen
readers" or "Tools I use". **Repositories > Star Lists** in the GitHub
Workbench lists every repository on every list, each row starting with its
list: "Screen readers: nvaccess/nvda, NVDA". They are ordinary repository
rows, so Enter opens the repository and Star, Watch and Clone work as
anywhere else. The node's note names any list that is empty.

- **New Star List...**: press `Ctrl+N` in Star Lists. QUILL asks for the
  name, up to 32 characters, a description you can leave empty, and whether
  only you or everyone can see it.
- **Star Lists...**, on any repository's context menu, wherever it is listed,
  shows your lists with the ones it is on already checked. Check and uncheck,
  then OK. You hear "nvaccess/nvda is now on: Screen readers, Tools I use."
- **Rename or Delete Star List...**, on a row in Star Lists, works on that
  row's list: rename it or change its description, make it private or public,
  or delete it. Deleting a list leaves its repositories starred.

## Packages

GitHub Packages holds what a project publishes besides its code: container
images, and npm, Maven, RubyGems and NuGet packages. **Repositories > My
Packages** in the GitHub Workbench lists yours as one list, each row whole on
its own: "container quill-engine: private, 12 versions, from
community-access/quill, updated 2026-11-12." GitHub keeps packages by type, so
QUILL asks for each type in turn; the list is every type together, in
alphabetical order.

A package's context menu has:

- **Show Details** and **Open on GitHub**.
- **Delete Package Version...** lists the package's versions, newest first,
  with their tags, such as "sha256:bbb, tagged latest, 1.2, updated
  2026-11-12". Choose one and QUILL asks before deleting it. GitHub will not
  delete a package's only version, or one downloaded more than 5,000 times,
  and QUILL says so.
- **Delete Package...** deletes the package and every version, after you type
  its name.

GitHub keeps a deleted package or version for 30 days, and you can restore it
from the Packages page of your GitHub settings. Reading private packages needs
the `read:packages` permission and deleting needs `delete:packages`; Sign In
with GitHub asks for both, and an account signed in before November 2026 is
told to sign in again rather than seeing an empty list.

An organization's packages are under **Organizations >** the organization **>
Packages**, read and deleted the same way.

`Ctrl+N` in My Packages, or in an organization's Packages, brings back a
package deleted in the last 30 days: QUILL asks its type and name, and says
"Restored the npm package left-pad.", or that GitHub has no such deleted
package.

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

# Chapter 8: Discussions and security

## What this chapter covers

Two kinds of conversation that are not issues. Discussions are a repository's
forum: questions, ideas and announcements, with threaded replies, answers and
polls. Security alerts are GitHub telling a repository about a vulnerable
package, a weakness in the code, or a secret committed by mistake. This
chapter covers reading and taking part in both, a repository's security
policy and advisories, reporting a vulnerability privately, letting a blocked
secret through, reviewing a pull request's dependencies, an organization's
security overview, setting secrets safely, searching GitHub's Advisory
Database, and saving a software bill of materials for a security review.

## Discussions

### Finding them

In Explore, choose **Repository Discussions** in **View:** (`Alt+V`), with the
repository in **Repository:** (`Alt+R`). You need to be signed in. Each row
reads the number, the title and the category, and whether it is answered:
"#12 How do I turn off the sounds? (Q&A; Answered by alice)".

A discussion link pasted into **Open Link...** in GitHub Items opens here too.

### Reading a thread

Press Enter on a discussion, or choose **Open Discussion Thread...** from its
context menu. The window **Discussion #12:** and the repository has:

- **Thread** (`Alt+T`), a list. The first row is the discussion itself, then
  each comment followed by its replies: "Comment by bob, the answer, 2
  replies:" and its first line, then "Reply by alice:" and so on. The answer,
  if there is one, says so.
- **Text** (`Alt+X`), the selected row in full. Enter in the list takes you
  there.
- **Reply...** (`Alt+R`), **Mark as Answer...** (`Alt+M`),
  **Open on GitHub** (`Alt+O`), **Refresh** (`Alt+F`) and **Close**.

When it loads, the status line says who answered it, or "Not answered yet.",
and how many comments and replies there are. A category that does not take
answers says "This category does not take answers."

A discussion with a poll reads it one option to a line, after the question
and the total: "Poll: Which sound pack?, 25 votes in all", then "Classic: 15
votes, 60 percent".

### Replying

**Reply...** (`Alt+R`) replies to the selected comment, or to the discussion
itself when the first row is selected. It opens the comment window, titled
with which: "Reply to bob's comment", with Insert Mention (bob first),
Insert Reference, Insert Emoji, Insert Saved Reply, Preview and the check
before posting. You hear "Posted your reply". A closed discussion takes no
replies, so the button is unavailable.

### Marking the answer

In a question-and-answer category, the person who asked, or a maintainer, can
mark one comment as the answer. Select the comment and press
**Mark as Answer...** (`Alt+M`). QUILL asks first: "Mark bob's comment as the
answer to this discussion?" On the comment that is already the answer, the
button reads **Unmark Answer...**, still on `Alt+M`. A reply cannot be the
answer, only a top-level comment.

### Starting a discussion

In the **Repository Discussions** view, signed in, choose **New Discussion...**
from the context menu.

- **Category:** (`Alt+C`). Categories that take answers say ", takes answers".
- **Title:** (`Alt+T`) and **Body:** (`Alt+B`).
- **Start Discussion**, or **Cancel**.

You hear "Started the discussion" with its title and category.

### Polls as a table, and Vote...

In the GitHub Workbench, **Repository > Discussions** lists the discussions.
When one has a poll, its details end with the poll as a table: a line with
the question, the total and whether you may vote, "Poll: Which sound pack?,
25 votes in all. You may vote: Vote...", then "Option, votes, percent, your
vote:" and a row for each option, "Classic, 15 votes, 60 percent, your vote:
no". The discussion's **Properties...** has the same table on its **Poll**
page, under the question.

**Vote...** on the discussion's context menu, or **Add...** or **Change...**
under the Poll page's table, lists the options with their votes. Choose one
and you hear the outcome once, with the new count: "Voted for Classic. It has
16 votes now, of 26 in all." GitHub keeps a poll vote once it is cast: if
you have voted, Vote... says which option you chose, and **Remove** under
the table says a vote cannot be taken back. An account set to Read Only in
the Workbench (**Workbench Options**, Accounts) cannot vote: Vote... says so
and sends nothing.

### Pinned discussions: the spotlight

**Repository > Discussions > Pinned (spotlight)** lists the discussions
pinned at the top of the repository's Discussions page, first to last in
GitHub's order: "1. #12 How do I turn off the sounds? (Q&A; Answered by
alice)". The details begin "Pinned 1 of 3, by alice." Enter opens the
thread, and Vote... and Properties work as in the main list. If nothing is
pinned, the list is empty and the status bar says so.

GitHub's API reads pinned discussions but cannot pin, unpin or reorder one,
so this place is read only, and each pinned discussion's details say so. To
pin one, use **Open on GitHub** and pin it on GitHub's own page.

### Categories and their sections

**Repository > Discussions > Categories** lists the repository's discussion
categories. Where GitHub gives sections, each section is a row, "Section:
Q&A (3 categories)", and Enter opens it: its categories follow a first row,
**All sections**, which comes back. GitHub's API does not yet say which
section a category is in, so today the place lists every category in
GitHub's order, and the status bar says why once. Each category reads its
name, and ", question and answer" when a reply can be marked the answer;
Enter on one goes to Discussions with the list narrowed to that category's
name.

## Security alerts

### Finding them

In Explore, choose **Repository security alerts** in **View:**, with the
repository in **Repository:**. The view brings three kinds of alert together:

- **Dependabot**: a package the repository uses has a known vulnerability.
- **Code scanning**: a tool found a likely weakness in the code.
- **Secret scanning**: something that looks like a password or key was
  committed.

Each row reads the kind, the severity, the package or file, and a summary:
"Dependabot: high: lodash — Prototype pollution".

Reading alerts needs a signed-in account that can see the repository's
security alerts. If yours cannot read one kind, or the repository has that
kind turned off, QUILL says that kind is unavailable rather than showing it as
having no alerts. A secret's value is never loaded into the view.

In QUILL, **Tools > Git and GitHub > GitHub > Security Alerts...** lists a
repository's open Dependabot alerts on their own.

### Dismissing an alert

Not every alert needs a fix. The package might be used only in tests, or the
finding might be wrong. On an alert's row, **Dismiss Alert...** on the context
menu asks three things:

1. **Why**, from GitHub's own reasons for that kind of alert:
   - Dependabot: "A fix has already been started", "This alert is
     inaccurate or incorrect", "No bandwidth to fix this", "Vulnerable code
     is not actually used", or "Risk is tolerable to this project".
   - Code scanning: "False positive", "Won't fix" or "Used in tests".
   - Secret scanning: "False positive", "Won't fix", "Revoked" or "Used in
     tests".
2. **A comment**, which you can leave empty. GitHub takes up to 280
   characters.
3. **Are you sure**: the confirmation names the alert and the reason, and says
   everyone with access will see it as dismissed.

Cancel at any step and nothing is sent. QUILL reports the dismissal only when
GitHub sends the alert back in its new state.

### Reopening an alert

Dismissed and fixed alerts have their own view, **Dismissed and resolved
security alerts**. There, **Reopen Alert...** on the context menu asks first,
then reopens the alert.

### Copilot Autofix

On a code scanning alert, **Copilot Autofix...** says whether Copilot has a
suggested fix. When it has none, QUILL offers to ask for one; when the fix is
ready, it offers to commit it to a branch you name, with a commit message you
may leave empty, so it can go through a pull request like any other change.
**Show Every Place** lists each file and line the alert was found in.

### Letting a blocked secret through

When push protection is on, GitHub refuses a push that contains something
that looks like a password or key, and `git push` prints a placeholder id for
each one. If the secret is not real, is only used in tests, or you will fix
it later, select the repository and choose **Allow a Blocked Secret...** on
its context menu. QUILL asks for the placeholder id, then why, from GitHub's
three reasons: "It is not really a secret (a false positive)", "It is only
used in tests", or "It is real, and I will fix it later". It asks once more,
naming the repository, because the secret will stay in the repository's
history. Then you hear how long the allowance lasts, such as "GitHub will let
the GitHub personal access token through until 2026-11-19 at 18:00 UTC. Push
again now; GitHub keeps an alert for it."

### Requests to dismiss or bypass

Some organizations want a security manager to approve each dismissal or
push protection bypass. GitHub offers those requests, and reviewing them,
only on GitHub Enterprise Cloud, which QUILL does not support; review them on
GitHub's own security page with **Open on GitHub**.

## Dependency review on a pull request

Before you merge a pull request, it helps to know what it does to your
dependencies. On a pull request's context menu, **Dependency Review** compares
the dependency graph at the pull request's base commit with its head commit
and shows the answer in a window to read. The first line is the summary:
"Added 3, removed 1. 1 added dependency has known vulnerabilities." Each
change follows, the vulnerable ones first: "Added: lodash 4.17.20 (npm,
package.json), licence MIT. Vulnerable: high, GHSA-p6mc-m468-83gw, Prototype
Pollution in lodash." A repository whose dependency graph is off says so in
words. **Compare Dependencies...** on a repository does the same between any
two branches, tags or commits you type.

## An organization's security overview

On an organization's context menu, **Security Overview** counts the open
alerts in every repository you can see there, worst first: "acme/web: 3
Dependabot (1 critical, 2 high); 1 code scanning (high); 2 secret scanning."
A totals line follows. If GitHub will not show you one kind, that kind is
named and the reason given, never counted as none: missing permission is not
the same as no risk. GitHub sends 100 alerts of a kind at a time; when a kind
reaches that, QUILL says so and points you to the organization's own alert
lists, under the organization in the tree, for the rest.

## Security policy and reporting

Found a security hole in someone's project? Do not open a public issue: tell
the maintainers privately first. **Repository > Security > Policy** in the
GitHub Workbench says how. Its first row is the repository's security policy,
"Security policy: SECURITY.md. Enter opens it.", found in the root, `.github`
or `docs`, or says the repository has none. The second says whether private
vulnerability reporting is on. When it is, anyone signed in can report there,
below.

## Security advisories

A security advisory is a project's notice of a vulnerability: which package
and versions, how serious, and where it is fixed. Each has a GHSA (GitHub
Security Advisory) id, and often a CVE (Common Vulnerabilities and Exposures)
number too.

**Repository > Security > Advisories** lists a repository's advisories, one
sentence each: "GHSA-q4hm-2345-wxyz: high severity, draft: Path traversal in
the importer." Published advisories are listed for everyone; drafts and
private reports only for the repository's administrators and security
managers, and anyone else hears that rather than an empty list. The details
pane says which packages and versions are affected, which version fixes it,
who is credited, and the full description.

**New Here** in Advisories (`Ctrl+N`) asks which you want:

- **Report a vulnerability privately to the maintainers**, for anyone, when
  private reporting is on. QUILL asks for a one-line summary, then what it is,
  how to reproduce it and what it lets an attacker do, then how severe it is,
  with "Not sure" as a choice. Only the maintainers see the report.
- **Draft an advisory**, for maintainers. The same three questions, then the
  affected package and its ecosystem, such as npm or pip, which you can leave
  for later. A draft is private until it is published.

On an advisory's context menu:

- **Publish or Close Advisory...** publishes it, closes it, or makes it a
  draft again. A report someone sent privately reads "private report to
  review"; on it, the same command offers **Accept it**, which makes it a draft
  advisory that you and the reporter work on, or **Close it**. Publishing makes it public for good, puts it in GitHub's
  Advisory Database and alerts the projects that depend on the package, so
  QUILL asks you to type its GHSA id first.
- **Request CVE...** asks GitHub for a CVE number for a draft. GitHub reviews
  each request, so the number comes later.

On a draft, **Advisory Comments**, **Comment on Advisory...** and **Edit an
Advisory Comment...** are its private discussion, and **Make a Private Fork for
the Fix** makes the temporary private fork GitHub offers for working on it.

## Secrets

A secret is a value a workflow, Dependabot, a codespace or the Copilot agent
uses but nobody reads again, such as a deploy token. They are lists in the
tree: a repository's **Settings**, an organization's own node, and an
environment's **Secrets...** on its row. Each row says the secret's name and
when it changed: "Secret DEPLOY_TOKEN, changed 2026-11-02. Its value is never
shown."

A secret's value only ever goes one way, to GitHub:

- **New Here** (`Ctrl+N`) asks for its name, then its value in a password box.
  QUILL seals the value on this computer with that repository's,
  environment's or organization's own public key (a libsodium sealed box, as
  GitHub requires) and sends only the sealed form. The value is never read
  back, said, shown, logged or kept: once the call ends, it is gone.
- **Change...** on a secret's row sends a new value the same way. For an
  organization's secret you may leave the value empty to keep it, and choose
  which of the organization's repositories may use it: **all**, **private**,
  or **selected**.
- **Repositories Allowed...** on a selected secret checks the repositories
  that may use it now; check or uncheck them, and QUILL adds and removes them
  one at a time, so a change somebody else made meanwhile is kept.
- A repository's Actions secret also has a **Properties** sheet. Its **New
  value** box is a password box that always opens empty; Copy as Text says
  "hidden", the preview before it is sent says "(hidden)", the box is emptied
  once GitHub has it, and Change History records only that it was set.

## Searching the Advisory Database

**Search > Security Advisories** searches GitHub's Advisory Database, every
published advisory for every package. Type a package name, such as `lodash`,
a CVE number, or a GHSA id, then Enter. Each row reads like the ones above.

## A software bill of materials

A software bill of materials, or SBOM, is the list of every package a
repository depends on, with versions and licences. Security reviews,
procurement and some contracts ask for one. GitHub builds it from the
repository's dependency graph, in SPDX (Software Package Data Exchange), the
standard format those tools read.

In the GitHub Workbench, select a repository and choose **Repository > Export
Software Bill of Materials...** (`Ctrl+Alt+B`), or the same row on
**Repository Actions** (`Ctrl+Shift+G`). A Save dialog offers a name such as
`owner-name.spdx.json`. When it is saved you hear "Saved owner-name.spdx.json:
212 packages, in SPDX format." The file is JSON (JavaScript Object
Notation), so QUILL opens it like any other text file.

A repository whose dependency graph is turned off has nothing to export, and
QUILL says where to turn it on: the repository's settings, under Code
security. Nothing is saved in that case.

# Chapter 9: Codespaces and the GitHub CLI

## What this chapter covers

A codespace is a computer GitHub runs for you in the cloud, already set up
with a repository and its tools. This chapter covers opening the Codespaces
page from GitHub Items, QUILL's Codespaces commands, and the GitHub CLI those
commands rely on, including how QUILL makes sure it is using the same account
as you.

Codespaces can cost money. GitHub gives each account some free hours a month
and charges for more. Everything here that could start one says so before it
does.

## Opening Codespaces from GitHub Items

In both apps, the context menu of any row in GitHub Items has
**Open in GitHub Codespaces...**. On a branch, it opens Codespaces for that
branch. QUILL asks first, reminds you that starting a codespace can incur
charges, and then opens GitHub's own Codespaces page in your browser. It does
not create anything itself, and it does not send your token. You make your
choices on GitHub's page.

## The GitHub CLI

QUILL's own Codespaces commands use GitHub's command-line tool, called `gh`,
because it is the only way GitHub offers to manage codespaces from outside the
website. QUILL needs it installed. If it is not, you hear that QUILL did not
find it, with the address to get it from, `cli.github.com`.

On Windows and macOS, QUILL can fetch it for you instead:
**Help > Download Optional Components...** has the GitHub CLI, a portable copy
of about 14 MB that QUILL checks before using.

### Two sign-ins, one account

`gh` signs in to GitHub on its own, separately from QUILL. Sign in once in a
terminal with `gh auth login`. QUILL never hands `gh` its token.

Because there are two sign-ins, they can disagree: you might be signed in to
QUILL with your work account and to `gh` with your personal one. Before each
Codespaces command, QUILL asks `gh` which account it is using. If that is not
the account QUILL is using, it stops and tells you, naming both: "GitHub CLI
is signed in as" one, "but QUILL is using" the other, and asks you to switch
one of them first. This is what keeps a codespace, and its bill, off the wrong
account.

## QUILL's Codespaces commands

In QUILL, these are on **Tools > Git and GitHub > GitHub**. They are QUILL's
alone, and need the GitHub CLI and a signed-in account.

### Codespaces...

**Codespaces...** lists your codespaces. Each reads its name, its repository,
whether it is running, and how far its branch is ahead of or behind GitHub.
With none, you hear "No codespaces for" your account, and a pointer to
Create Codespace.

Choose one and a second list offers what to do with it:

- **Open in Browser (may start the codespace)**, after a confirmation, because
  opening a stopped codespace starts it.
- **View Codespace Health**: its repository, state, machine, location, when it
  was last used and created, and its Git status.
- **Stop**, which stops it running, and charging.
- **Delete**, which asks first: "Delete codespace" and its name, "This cannot
  be undone." Anything in it you have not pushed to GitHub goes with it.

### Create Codespace...

**Create Codespace...** asks for the repository as `owner/repo`, then the
branch, which you can leave empty for the default branch. It checks the CLI's
account, then asks you to confirm in a window whose title says it uses paid
GitHub compute. You hear "Created codespace" with its name and state.

These two commands are newer than the rest of the workbench, and have not yet
been tried against every kind of codespace. If one says something that does
not match what you see on GitHub, please tell us (Chapter 10).

## Other things that use Git or the CLI

**Sync Folder with GitHub...**, on the same QUILL menu, keeps a folder on your
computer in step with a repository, using Git. The QUILL user guide covers it
under
[Sync a folder with GitHub](https://community-access.github.io/quill/docs/quill-guide-14-projects-notes-and-the-quillville-family.html#sync-a-folder-with-github).

Safe Mode switches off every command in this chapter: you hear "GitHub CLI
commands are disabled in Safe Mode".

# Chapter 10: Troubleshooting, privacy and help

## What this chapter covers

When GitHub says no, QUILL tells you why in a sentence and what to do next.
This chapter lists the sentences you are most likely to hear, what each one
means and how to fix it. Then it covers using a token instead of signing
in, says exactly what the workbench sends over the network, and how to get
help from a person.

## How a refusal sounds

Most refusals have two parts: what QUILL was trying to do, and why it could
not. "Could not re-run the failed jobs. Access denied. GitHub refused this
request: check the token permissions and its organization SSO authorization."
When GitHub gave a reason of its own, QUILL adds it after "GitHub said:".

Nothing is half-done. When a command is refused, nothing was changed on
GitHub, and anything you had typed, such as a comment, a review or a new
issue, is still on your computer.

## The refusals, one by one

### "The GitHub token is invalid or expired."

The full sentence ends "Add a valid token or switch accounts." Your token has
reached its expiry date, or was cancelled on GitHub, perhaps because QUILL was
revoked under Authorized OAuth Apps. Open **Manage GitHub Accounts...**,
remove the old account, and choose **Sign In with GitHub...** again. If you
added the account with a token, you can make a new one instead: see
"Advanced: using a token", below.

### "Access denied. GitHub refused this request"

GitHub knows who you are, but will not let this token do this. One of three
things is usually true:

- **The token lacks a scope.** For example, a token without `repo` cannot
  write to a private repository, and one without `delete_repo` cannot delete
  one. Chapter 1 lists the scopes. An account added with Sign In with GitHub
  has every scope the workbench uses, so this usually means a token you added
  yourself. You cannot add a scope to a token from QUILL: edit
  the token on GitHub, or sign in with GitHub instead.
- **Your account lacks permission.** Only people with write access can merge,
  rerun or label, and only administrators can rename, archive or change
  visibility. Ask a maintainer.
- **The organization needs single sign-on.** See the next section.

Traffic in Insights is a special case. It needs push access, and QUILL says so
in plain words while still showing the contributors.

### "GitHub requires organization SSO authorization for this token."

The organization signs its members in through its own system, and your token
has not been authorized for it yet. On GitHub, open your personal access
tokens, choose **Configure SSO** beside the token, and authorize it for the
organization. Then try again. The token keeps working everywhere else in the
meantime.

### Sign In with GitHub: "The code expired before it was used."

A code from Sign In with GitHub lasts about fifteen minutes. Close the window,
choose **Sign In with GitHub...** again, and type the new code on GitHub's
page. You never have to retype an old one: each try gets a fresh code, already
on the clipboard.

### Sign In with GitHub: "The sign-in was declined on GitHub's page."

Somebody chose Cancel on GitHub's approval page instead of Authorize. Nothing
was saved. Choose **Sign In with GitHub...** again if that was a slip.

### Sign In with GitHub: "GitHub did not give a sign-in code."

QUILL could not reach github.com. Check your connection, and any proxy or
firewall that might block it, then try again. If your network will not let
QUILL through at all, **Add Token (Advanced)...** still works wherever the
workbench itself does.

### An organization's repositories are missing after Sign In with GitHub

Some organizations stop apps from seeing their repositories until an owner
approves each app. Your own repositories show up, and the organization's are
missing or refused, even though you are a member.

The fix is a one-time approval of QUILL for that organization. On GitHub,
open your settings, then **Applications**, then **Authorized OAuth Apps**,
then QUILL (or QUILL Lite). Beside the organization, choose **Request**.
GitHub emails the organization's owners, and once one of them approves, the
repositories appear the next time you refresh. If you are an owner yourself,
the button says **Grant** and works at once. You only ask once per app and
organization, however many times you sign in.

If the organization would rather not approve apps, a token still works: see
"Advanced: using a token", below.

### "GitHub could not find it, or this account cannot see it."

The full sentence ends "Refresh the list; it may already be gone." Either the
thing really is gone, perhaps deleted or transferred, or it is private and
this account cannot see it. GitHub answers both the same way, on purpose, so
that private repositories cannot be discovered by guessing. Check that you are
using the right account (`Manage GitHub Accounts...` in QUILL), and that the
token has the `repo` scope if the repository is private.

### "GitHub rate-limited this request."

You have used up an allowance, or sent many requests close together. Press
`Ctrl+Shift+L` to hear how much is left and when it resets. Signed out you get
far fewer requests, so signing in is often the fix.

Two related sentences:

- "GitHub asked QUILL to wait 60 seconds." is a short pause GitHub asks for
  after a burst of requests. QUILL waits by itself and stops sending until the
  time is up. You hear it once.
- "GitHub API rate limit reached. Retry after" a number of seconds means the
  hourly allowance is gone. It comes back at the reset time the readout gives.

### "GitHub reported a conflict" and "GitHub refused the request"

A conflict means the thing changed while you were looking at it: someone else
merged, closed or edited it. Refresh and try again.

"GitHub refused the request" with a reason means GitHub will not do this in
the current state, such as rerunning the failed jobs of a run where nothing
failed. The reason that follows is GitHub's own.

### "GitHub had a server error"

The problem is at GitHub's end. Wait a moment and try again. GitHub keeps a
status page at `githubstatus.com`.

### "Write actions need a signed-in GitHub account"

You are working as a guest, so the workbench only reads. Sign in with
**Manage GitHub Accounts...** (Chapter 1): in QUILL it's on File > Open from
Remote, and in QUILL Lite it's on File (`Alt+F`, then `H`).

### The GitHub menus are missing in QUILL

GitHub Remote Access is part of the Developer profile and is off in the
others. Press `Alt+Shift+P` and choose Developer, or turn on GitHub Remote
Access alone in **Profiles and Features...**. **Help > Why Don't I See a
Feature?** explains any missing command.

### "GitHub item browsing is disabled in Safe Mode."

QUILL started in Safe Mode, which keeps every GitHub window closed. Restart it
normally.

### A file shows no text

Repository Files shows text only for UTF-8 text files up to 1 MB, and says
which rule a file broke. Open it on GitHub, or download it there.

## Advanced: using a token

Sign In with GitHub is the way to connect, and most people never need anything
else. A token is a long code you make yourself on GitHub's website and paste
into QUILL. It's worth the trouble in a few cases:

- **You want QUILL to reach only a few repositories.** A fine-grained token
  can be limited to the repositories you pick, and to only the things you
  allow in them.
- **Your organization blocks sign-in apps** and won't approve QUILL, but
  still lets its members use tokens.
- **Your organization issues you a token** and asks you to use that one.
- **Your network blocks GitHub's sign-in page**, github.com/login/device, but
  lets the workbench itself through.

### Making a token

1. Open github.com in your browser and sign in.
2. Go to your profile settings, then **Developer settings**, then
   **Personal access tokens**.
3. For a token limited to a few repositories, choose **Fine-grained tokens**,
   then **Generate new token**, and pick the repositories and permissions.
   Otherwise choose **Tokens (classic)**, then **Generate new token
   (classic)**, and check the scopes you need. Chapter 1 lists the scopes and
   what each one does.
4. Give it a name you'll recognise, such as "QUILL on my laptop", and an
   expiry date.
5. Generate the token and copy it. GitHub shows it only once.

Some parts of GitHub, the notifications inbox among them, don't accept
fine-grained tokens. If you need those, use a classic token, or sign in with
GitHub.

If your organization uses single sign-on, there is one more step. On GitHub's
token page, choose **Configure SSO** beside the token and authorize it for the
organization. Until you do, GitHub refuses the organization's repositories
even though the token is fine everywhere else.

### Adding it to QUILL

Open **Manage GitHub Accounts...** and choose **Add Token (Advanced)...**. The
**Add GitHub Token** window has one field, **Personal access token**. Paste
the token and press **Connect**. QUILL asks GitHub who the token belongs to
before it keeps it, so a mistyped or expired token is turned away with
"GitHub did not confirm an account for that token. Nothing was saved." When
GitHub confirms it, you hear "Added and switched to GitHub account" and your
GitHub username.

The same window has **Continue Anonymously** for working as a guest, and
**Cancel**. None of its buttons has an access key, so Tab to the one you want.

To stop using a token, remove the account in Manage GitHub Accounts, then
delete the token on GitHub's token page. Removing it in QUILL doesn't cancel
it on GitHub.

### When QUILL suggests signing in instead

If you added an account with a classic token that can do a lot, such as one
with the `repo` scope, QUILL mentions it once, the next time you open Manage
GitHub Accounts: "This account uses a token. Sign In with GitHub is easier to
keep up to date." Then it asks whether to sign in with GitHub now. Choose
**Yes** to go straight to Sign In with GitHub. Choose **No** and nothing
changes: the token keeps working, the window opens as usual, and QUILL doesn't
ask again for that account. It never asks about an account you signed in with,
or about a fine-grained token, since that's the kind people choose on purpose.

### When a token is about to expire

Tokens you make yourself usually have an expiry date, and GitHub tells QUILL
when it is. If the active account's token expires within seven days, QUILL
says so the first time the workbench talks to GitHub that day, for example
"Your GitHub token for your-name expires in 3 days." If it has already
expired, you hear "Your GitHub token for your-name has expired." Either way
it's said at most once a day, and it also goes into **Notifications**, where
opening it takes you to Manage GitHub Accounts. From there, sign in with
GitHub, or add a new token.

QUILL Lite does all of this the same way.

## Privacy: what goes over the network

The workbench talks to GitHub and to nobody else, and only when you ask it to.

- **Before the first connection** QUILL asks your permission, once (Chapter
  1).
- **Requests go to GitHub's own servers**: `api.github.com` for nearly
  everything, and `uploads.github.com` when you upload a release file. They
  use encrypted connections, and QUILL refuses to follow a redirect to any
  other address while carrying your token.
- **Downloads** of logs and artifacts are handed by GitHub to a short-lived
  address elsewhere. QUILL fetches those without your token.
- **Links opened in your browser** never carry your token either.
- **The GitHub CLI** uses its own sign-in, never QUILL's token (Chapter 9).
- **AI summaries** in QUILL send the issue's text to the AI you chose, after
  the same questions as every AI feature. Nothing else in the workbench uses
  AI.

What stays on your computer and never goes to GitHub: your token (in the
operating system's secure store), your pins and favorites, where you left off,
your local drafts and pending review comments, your saved searches, the
attention queue's settings and filters, and the copies of earlier answers
QUILL keeps so that unchanged reloads cost nothing.

Safe Mode switches all of it off.

## Getting help

If something here does not work the way this book says, or you are stuck,
write to a person. Support is run by Community Access, at
**support@community-access.org**. A real person reads every message and
replies by email. Nothing you send is posted on GitHub or anywhere else in
public.

The quickest way to write is **Help > Get Help from Support...**, in both
apps. It fills in your app's version and your screen reader for you, and opens
your own mail program with the message written. Nothing is sent until you send
it from there.

It helps to say:

- which app and version you are using, and which screen reader;
- which window you were in, and what you pressed;
- what QUILL said, word for word if you can; and
- what you expected instead.

# Chapter 11: Keyboard reference

## What this chapter covers

Every key the workbench answers to, one window at a time. Keys marked as
access keys are the underlined letters of a control, pressed with Alt; they
work while that window has focus. Keys that open the windows themselves are in
Chapter 1. QUILL's GitHub menu commands have no keys out of the box, and you
can give them some in the Keymap Editor.

Throughout, Shift+F10 or the Applications key opens the context menu of
whatever has focus, and Escape closes the window you are in. The Workbench
itself is the exception: Escape never closes it, and `Alt+F4` does.

## The GitHub menu, in workbench mode

GitHub Workbench Mode is **View > GitHub Workbench Mode**: `Alt+V`, then `K`.
While it is on, `Alt+G` opens the GitHub menu, and these letters choose a row
in it. They are the same in both apps; the rows marked QUILL only are not in
QUILL Lite's menu.

| Letter | Row |
| --- | --- |
| `V` | Leave Workbench Mode |
| `W` | Open GitHub Workbench |
| `I` | Inbox |
| `S` | This Repository's Issues |
| `P` | This Repository's Pull Requests |
| `A` | Actions Runs |
| `R` | From This Line submenu (in QUILL Lite, its rows are in the menu itself) |
| `D` | Open GitHub Address... (QUILL only) |
| `C` | Clone Repository... |
| `M` | Commit to GitHub... (QUILL only) |
| `Y` | Sync Folder with GitHub... (QUILL only) |
| `L` | Local Git submenu (QUILL only) |
| `G` | Manage GitHub Accounts... |
| `H` | Open GitHub Guide |

None of these rows, and not the mode itself, has a key out of the box. A key
you give one in the Keymap Editor works in both modes.

### From This Line

The line or lines you are on, on GitHub (Chapter 7). In QUILL it is a submenu
of the GitHub menu (`R`), and of **Tools > Git and GitHub > GitHub** (`L`) when
workbench mode is off; in QUILL Lite its rows are in the GitHub menu itself.

| Letter | Row |
| --- | --- |
| `K` | Copy GitHub Link to This Line |
| `O` | Who Changed This Line? (twice: its pull request) |
| `E` | Open the Pull Request for This Line |
| `U` | Open This Line on GitHub |
| `N` | New Issue from Selection... |
| `F` | Issues Mentioning This File |
| `T` | Comment on This Line in the Open Pull Request... |
| `R` | Open the GitHub Reference at the Cursor (or `Alt+Enter` with the cursor on a reference) |

### Clone Repository

| Key | What it does |
| --- | --- |
| `Alt+R` | Move to Repository (owner/name or address) |
| `Alt+I` | Move to Into this folder |
| `Alt+B` | Browse... for the folder |
| Enter | Clone |
| Escape | Close without cloning |

## The GitHub Workbench window

These are the Workbench's own keys. Chapter 12 explains the places they take
you to. Every one of them can be changed in the Keymap Editor, and the menus
always show the key that is really bound. The old GitHub Items and Explore
GitHub windows are retired; everything they did is here.

### Going places

| Key | What it does |
| --- | --- |
| `F6`, `Shift+F6` | Next or previous pane: tree, filter box, list, details, status bar |
| `Ctrl+1` | Inbox, under Needs My Attention (`Alt+Home` too) |
| `Ctrl+2` | The repository the window opened on |
| `Ctrl+3` | Search |
| `Ctrl+4` | People |
| `Ctrl+5` | Gists |
| `Ctrl+6` | Projects |
| `Ctrl+7` | Watches, not built yet |
| `Ctrl+8` | Saved Searches |
| `Ctrl+9` | Start Here |
| `Ctrl+0` | Across Repositories |
| `Ctrl+Shift+1` to `Ctrl+Shift+0` | The current repository's Issues, Pull Requests, Discussions, Actions Runs, Files, Releases, Projects, Security, Settings and Insights |
| `Alt+Up` | The place above this one |
| `Alt+Left`, `Alt+Right` | Back and Forward |
| `Ctrl+L` | Open GitHub Address: `owner/name`, `#42`, `owner/name#42` or any GitHub link |
| `Ctrl+G` | Go to an issue or pull request by number |
| `Ctrl+Period`, `Ctrl+Shift+Period` | Next or previous unread notification |
| `Ctrl+Shift+E` | Back to the editor that opened the Workbench |

`Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys in the editors. The Workbench has
no AI menu, so here they belong to the Go row.

### Doing things to the selected row

| Key | What it does |
| --- | --- |
| Enter | The obvious thing: read an issue, review a pull request, a run's jobs, a branch's commits, a release's files |
| `Alt+Enter` | Properties: everything about it, on one sheet |
| `Shift+Enter` | Open it on GitHub, in your browser |
| `Ctrl+Enter` | Open a file in the editor |
| `Ctrl+N` | New here: issue, pull request, gist, saved search, pin, or the repositories for Across Repositories |
| `Ctrl+Shift+N` | New, asking what to make |
| `Ctrl+Shift+M` | Comment |
| `Ctrl+Shift+D` | A pull request's changed files |
| `Ctrl+Shift+Enter` | Merge a pull request |
| `Ctrl+Shift+B` | Compare a branch with another |
| `Ctrl+Shift+A` | Assign an issue to Copilot |
| `Ctrl+Shift+T` | Start an issue or pull request in a local worktree (QUILL only) |
| `Ctrl+Shift+W` | What failed in a run |
| `Ctrl+Shift+F5` | Re-run a run's failed jobs only |
| `Ctrl+Shift+R` | Run a workflow on a branch |
| `Ctrl+Shift+G` | Repository Actions |
| `Ctrl+Alt+B` | Export Software Bill of Materials |
| `Ctrl+Alt+T` | Transfer Repository |
| `Ctrl+Alt+W` | Clone Wiki |
| `Ctrl+Q`, `Ctrl+Shift+Q` | Mark a notification read; mark the whole list read |
| `Ctrl+Alt+N` | Inbox Rules... |
| `Ctrl+D` | Add to Favorites, or take it out |
| `Ctrl+C`, `Ctrl+Shift+C` | Copy the row; copy its address |
| Delete | The safe removal for the row, asking first when it cannot be undone |
| `Ctrl+Z`, `Ctrl+Y` | Undo or redo your last change on GitHub, in the tree and the list |

### Lists

| Key | What it does |
| --- | --- |
| `Ctrl+E`, `Ctrl+Shift+F` | Move to the filter box |
| `Ctrl+Alt+F` | Filter Builder |
| `Ctrl+Shift+U` | Choose columns |
| `Ctrl+A` | Select every row |
| `F5` | Refresh |
| `Ctrl+F5` | Refresh, reading everything from GitHub again |
| `Alt+Page Down` | Load more |
| `Ctrl+Shift+Page Down` | Load all |
| `Ctrl+Shift+X` | Export List: the list as shown, as Excel, CSV or a Markdown table |
| `Ctrl+Alt+I` | Import Issues from a Spreadsheet |
| `Ctrl+Alt+L` | New Issues from Lines |
| Escape | Clear the filter box, then go back |

### Account and tools

| Key | What it does |
| --- | --- |
| `Ctrl+Shift+P` | GitHub Permissions |
| `Ctrl+Shift+H` | Change History |
| `Ctrl+Alt+S` | Set Your Status |
| `Ctrl+Shift+K` | Manage GitHub Accounts |
| `Ctrl+Shift+L` | GitHub's remaining hourly allowance |
| `Ctrl+Shift+O` | Workbench Options |
| `Ctrl+Alt+D` | Dry Run on or off |
| `Alt+F4` | Close the Workbench |

### Hearing where you are, and help

| Key | What it does |
| --- | --- |
| `Alt+1` to `Alt+9` | Say where you are, the selection, the item, the counts, your access, the allowance, the filter, what is loading, the account |
| `F9`, `Shift+F9` | Say the last result again; explain it |
| `F1` | What this place and control are for |
| `Shift+F1` | What can I do here, with each key |
| `Alt+F1` | What the GitHub word for the row means |
| `Ctrl+F1` | This guide, at the right chapter |
| `Ctrl+Shift+F1` | Search all of help |
| `Ctrl+Alt+P` | Practice on GitHub |
| `Alt+Shift+T` | Take the Tour: a spoken tour of the window, a pane at a time |
| `Alt+Shift+A` | Ask How: a question in your own words, answered from this help by the AI you chose |
| `Alt+Shift+F1` | Every key in the window |
| `Ctrl+Alt+K` | Key Describer: keys say what they do instead of doing it, until `Escape` |

If you rebind a key, the menus, `Shift+F1`, `Alt+Shift+F1` and the Key
Describer all say your key. This chapter shows the keys the Workbench starts
with.

### New Pull Request

| Key | Control |
| --- | --- |
| `Alt+I` | Merge into |
| `Alt+F` | Merge from |
| `Alt+T` | Title |
| `Alt+D` | Description |
| `Alt+A` | Create as a draft |
| Enter, outside Description | Create Pull Request |
| Escape | Cancel, keeping what you typed for this session |

### An issue form

An issue form's fields are named by the form itself, so they have no access
keys; Tab moves through them in order. Enter, outside a large text box, is
Create Issue, and Escape closes without sending.

## Review pull request

| Key | What it does |
| --- | --- |
| `Ctrl+R` | Reply to the selected thread |
| `Ctrl+Shift+R` | Resolve or reopen the selected thread |
| Enter | Open a file's diff, read a thread, open a check, or open and close a branch |
| Right, Left | Open or close a branch of the outline |
| Tab, Shift+Tab | Into the details and back |

| Key | Control |
| --- | --- |
| `Alt+L` | Changed since my last review |
| `Alt+U` | Next Unresolved |
| `Alt+V` | Next Unvisited |
| `Alt+G` | Open on GitHub |
| `Alt+S` | Copy Review Summary |
| `Alt+T` | Timeline... |
| `Alt+C` | Compose Review... |
| `Alt+R` | Reply to Thread... |

| Key | Control |
| --- | --- |
| `Alt+W` | Request Reviewers... |
| `Alt+M` | Mark Ready, on a draft |
| `Alt+D` | Convert to Draft |
| `Alt+B` | Update Branch... |
| `Alt+A` | Auto-Merge and Queue... |

Check Merge Policy has no access key. Request Copilot Review is on the pull
request's context menu (`Shift+F10` on the outline) and has none either.

### Compose Review

| Key | Control |
| --- | --- |
| `Alt+M` | Review message |
| Escape | Save Draft and Close |

Review action and Submit Review have no access key; reach them with Tab.

## The diff

| Key | What it does |
| --- | --- |
| `Alt+M` | Line marks: words, short words, diff symbols, or diff symbols with changed lines |
| `Alt+N` / `Alt+P` | Next / previous change in the patch list, "Change 2 of 5" (`F8` / `Shift+F8` too) |
| `Alt+H` | Changed Lines Only |
| `Alt+W` | Hide Whitespace Changes |
| `Alt+T` | Choose Commit |
| `Alt+P` | Patch lines |
| Shift with the arrows | Select a run of patch lines |
| Enter | Comment on the line, or on the selected lines |
| `Alt+L` | Comment on This Line... |
| `Alt+S` | Comment on Lines... |
| `Alt+C` | Copy Diff |
| `Alt+O` | Open Diff in Default App |

### Commenting on a line

| Key | Control |
| --- | --- |
| `Alt+S` | Suggest a change |
| `Alt+C` | Comment |
| `Alt+A` | Add to Review, the default |
| `Alt+P` | Post Now |

## Repository Files

| Key | Control or action |
| --- | --- |
| `Alt+B` | Branch, tag or commit |
| `Alt+G` | Go |
| `Alt+F` | Files, the tree |
| `Alt+C` | Contents |
| `Alt+V` | View File |
| `Alt+E` | Open in Editor |
| `Alt+R` | README |
| `Alt+H` | History... |

| Key | Control or action |
| --- | --- |
| `Alt+L` | Blame... |
| Right, Enter | Open a folder |
| Left | Close a folder |

### History and Blame

| Key | What it does |
| --- | --- |
| `Alt+N`, `Alt+P` | Next or previous row, from anywhere in the window |
| Enter | Open the commit on GitHub |
| `Alt+O` | Open Commit |
| `Alt+D` | Details |
| `Alt+C` | The Commits list, in History |
| `Alt+R` | The Runs list in Blame; Refresh in History |

## Actions windows

### What Failed

| Key | Control |
| --- | --- |
| `Alt+W` | What failed, the text |
| `Alt+C` | Copy All |
| `Alt+R` | Refresh |

### Jobs and Logs

| Key | Control |
| --- | --- |
| `Alt+A` | Attempt |
| `Alt+L` | Load Log |
| `Alt+N` | Load Annotations |
| `Alt+J` | Open Job on GitHub |
| `Alt+R` | Open Run on GitHub |
| `Alt+F` | What Failed... |
| `Alt+C` | Re-request Check |
| `Alt+W` | Follow This Job |
| `Alt+8` | How far along the selected job is |
| Enter | Load the selected job's log |

### Pending Deployments

| Key | Control |
| --- | --- |
| `Alt+E` | Environments waiting for review |
| `Alt+C` | Comment |
| `Alt+A` | Approve |
| `Alt+R` | Reject |

### Artifacts

| Key | Control |
| --- | --- |
| `Alt+S` | Download Selected... |
| `Alt+A` | Download All... |
| `Alt+R` | Refresh |
| `Alt+B` | Open Run in Browser |

## Issue windows

### New Issue

| Key | Control |
| --- | --- |
| `Alt+T` | Title |
| `Alt+B` | Body |
| `Alt+L` | Labels |
| `Alt+A` | Assignees |

### Milestones

| Key | Control |
| --- | --- |
| `Alt+S` | Show |
| `Alt+M` | Milestones, the list |
| `Alt+D` | Details |
| `Alt+N` | New... |
| `Alt+E` | Edit... |
| `Alt+L` | Close Milestone... or Reopen Milestone... |
| `Alt+O` | Open on GitHub |
| `Alt+R` | Refresh |

### Projects and Dependencies

| Key | Control |
| --- | --- |
| `Alt+L` | Load Projects |
| `Alt+P` | Project |
| `Alt+N` | Next Unblocked |
| `Alt+A` | Actions... |

### Smaller windows

| Window | Key | Control |
| --- | --- | --- |
| Timeline | `Alt+H` | History, oldest first |
| Timeline | `Alt+A` | Copy All |
| Timeline | `Alt+C` | Hide or Show Comment |
| Timeline | `Alt+P` | Pin or Unpin Comment |
| Reorder Sub-issues | `Alt+U` | Move Up |
| Reorder Sub-issues | `Alt+D` | Move Down |
| Relationships | `Alt+S` | Add Sub-issue... |
| Relationships | `Alt+B` | Add Blocked By... |
| Relationships | `Alt+T` | Add Related... |
| Relationships | `Alt+R` | Remove |
| Roles in | `Alt+O` | Roles |
| Roles in | `Alt+W` | Who holds it |
| Roles in | `Alt+P` | Give to Person... |
| Roles in | `Alt+T` | Give to Team... |
| Roles in | `Alt+A` | Take Away... |
| Rulesets in | `Alt+U` | Rulesets |
| Rulesets in | `Alt+D` | Details |
| Rulesets in | `Alt+E` | Enforcement... |
| Rulesets in | `Alt+H` | History |
| Rulesets in | `Alt+I` | Rule Insights... |
| Rulesets in | `Alt+L` | Delete... |
| Edit Release | `Alt+N` | Release name |
| Edit Release | `Alt+O` | Release notes |
| Edit Release | `Alt+D` | Draft (not published yet) |
| Edit Release | `Alt+P` | Pre-release |
| Commit Comments | `Alt+C` | Comments |
| Commit Comments | `Alt+M` | Selected comment |
| Commit Comments | `Alt+N` | New comment |
| Commit Comments | `Alt+F`, `Alt+L` | File, optional; Line, optional |
| Commit Comments | `Alt+P` | Post Comment |
| Commit Comments | `Alt+R` | Refresh |
| New Gist, Edit Gist | `Alt+D` | Description |
| New Gist | `Alt+B` | Public gist |
| New Gist, Edit Gist | `Alt+F` | Files |
| New Gist, Edit Gist | `Alt+T` | File text |
| New Gist, Edit Gist | `Alt+A` | Add File... |
| New Gist, Edit Gist | `Alt+N` | Rename File... |
| New Gist, Edit Gist | `Alt+L` | Delete File... |

## Discussion windows

| Window | Key | Control |
| --- | --- | --- |
| Discussion thread | `Alt+T` | Thread |
| Discussion thread | `Alt+X` | Text |
| Discussion thread | `Alt+R` | Reply... |
| Discussion thread | `Alt+M` | Mark as Answer... or Unmark Answer... |
| Discussion thread | `Alt+O` | Open on GitHub |
| Discussion thread | `Alt+F` | Refresh |
| New Discussion | `Alt+C` | Category |
| New Discussion | `Alt+T`, `Alt+B` | Title, Body |

## Compare branches

| Key | Control |
| --- | --- |
| `Alt+G` | Open on GitHub |
| `Ctrl+Tab` | Switch between the Commits and Changed Files tabs |

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
  every repository's, in one list. A secret's value is never asked for, so it
  is never shown. Open a repository's Alerts to dismiss or resolve one.
- **Actions, Dependabot, Codespaces and Copilot Agent Secrets:** Change... on
  one sends a new value, sealed, or keeps it, and chooses all, private or
  selected repositories; Repositories Allowed... picks the selected ones.
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

### Each name across the set

GitHub keeps a label, a tag or a secret inside one repository, but you think
of them by name across many: "the bug label", "the v3.2.0 tag", "the
NUGET_KEY secret". Across Repositories has a place for each such kind, in four
groups:

- **Planning by Name:** Labels, Milestones, Topics.
- **Code by Name:** Tags, Branches, Rules and Branch Protection.
- **Actions by Name:** Environments, Secrets, Variables.
- **Settings by Name:** Webhooks, Deploy Keys, Autolinks.

A row is one name, such as "v3.2.0: in 4 of 4 repositories, 4 different
commits" or "main: in 30 of 30 repositories, default in 30, protected in 26".
Enter shows its variants, each with the repositories that have it, and the
repositories that lack it. A repository that could not be read, often because
reading secrets, webhooks and keys needs admin access, is named apart and
never counted as missing.

The context menu then changes it everywhere, as far as GitHub allows. Every
change shows a preview first, repository by repository, with what is blocked
and why, and then one result per repository. Each target is read again just
before it is written, so one somebody changed on GitHub meanwhile is left
alone and named.

- **Make Them the Same** (labels, milestones, rules, environments, variables,
  webhooks): choose the winning variant. An environment's custom branch list,
  and a team reviewer from another owner, are not copied. A webhook keeps its
  secret.
- **Add to Missing** (labels, milestones, topics, rulesets, variables,
  webhooks, autolinks). A deploy key cannot be added to more: GitHub accepts
  one key in one repository only.
- **Release Train** (tags): make the tag, the tag's draft release, or the tag
  and a published release, on the default branch of each repository you
  choose. A repository that already has the tag is skipped, and its tag is
  never moved.
- **Set Secret Everywhere** (secrets): type the new value once. It is sealed
  for each repository before it leaves your computer, and it is never shown,
  kept in Change History or written to the details. No secret's old value can
  be read, by anyone.
- **Rename Everywhere** (labels, branches). For a branch the preview says
  where it is the default branch, where its protection moves with it, and how
  many open pull requests GitHub retargets.
- **Turn On or Off Everywhere** (webhooks).
- **Delete Everywhere** (labels, topics, tags, environments, secrets,
  variables, webhooks, deploy keys, autolinks). A tag with a release built on
  it is kept, with the reason.
- **Promote to Organization** (rulesets, secrets, variables, webhooks): one
  organization ruleset, secret or variable for the set's repositories in that
  organization, or one organization webhook. GitHub sends an organization
  webhook for every repository in the organization, and the preview says so.
  Each repository's own copy is deleted only after the organization's one
  exists, because a repository's own secret or variable wins over the
  organization's. Labels, environments, deploy keys and autolinks have no
  organization form in GitHub, so they are not promoted.

Secrets, environments, webhooks, deploy keys and rules decide who may deploy,
what is kept secret or where data is sent, so changing them across
repositories needs Full in the Workbench.

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
  branches, tags or commits, with licences and known vulnerabilities), SBOM
  Report, Ruleset History..., Secret Scanning History, Allow a Blocked
  Secret... (the placeholder id `git push` printed, and why), Fork Workflow
  Settings and Fork Workflows from Private Repositories....
- **A commit:** Branches at This Commit, Check Run Details... (a check's
  summary and every annotation), Re-run a Check Suite..., and the reactions
  on its comments: Reactions on a Commit Comment..., React to a Commit
  Comment..., Remove My Reaction from a Commit Comment....
- **A workflow run:** Read a Step's Log..., one step at a time.
- **A pull request:** Re-request Review... and Dependency Review (what it
  changes in the dependencies, with licences and known vulnerabilities).
  **A release:** GitHub's Release
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
  Membership, My Activity Here and Security Overview (open alerts in every
  repository, worst first; a kind GitHub will not show you is said, never
  counted as none).
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

- Labels, assignees, reviewers, Projects and your reactions are lists of
  check boxes, and a repository's features (Issues, Projects, Wiki,
  Discussions) are check boxes too. Each one says its state in its own
  words, "bug, on" or "Issues, off", and Space checks or clears it once; the
  words change with it, and nothing else is said. Unchecking a Project takes
  the item out of it, along with whatever the project's own fields said
  about it, so that one cannot be undone.
- New Label..., New Milestone... and New Project... beside their lists make
  a new one on GitHub and check it straight away. If one by that name is
  already there, that is not a failure: QUILL says "bug already exists;
  using it" and checks the one GitHub has.
- An issue's **Issue type** and a pull request's **Into branch** are lists
  too, of the types your organization has and the repository's branches.
  New Issue Type... makes a type for the whole organization, which needs an
  organization owner. New Branch... makes a branch from the one the pull
  request merges into now, then selects it. "(none)" clears an issue type,
  but a pull request always merges into some branch, so choosing "(none)"
  there leaves it as it was and QUILL says so.
- **OK** saves and closes, and Enter on a check box, a list or a one-line
  box is OK. **Apply**, or `Ctrl+S`, saves and keeps the sheet open, and
  focus comes back to the check box or field you were on. `Ctrl+Enter` is
  OK from anywhere, even in a long text box. Escape is Cancel.

The context menu of an issue or pull request still names the common
changes: **Edit Title...**, **Labels...**, **Assignees...**, **Milestone...**
and **Projects...** open the sheet with focus already on that field. There
are no separate keys for single properties: `Alt+Enter`, then the page.

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
  2027.2." For each such field you choose Keep Theirs or Use Mine. Lists
  you add to and take from (labels, reviewers, Projects) never ask: only
  your own additions and removals are sent, so a label somebody else added
  while you had the sheet open stays on.
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

**Tools > Plain-Language Batch...** (`Ctrl+Shift+S`) takes the change as a
sentence, for the repository you are in:

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

There is no AI in it. QUILL reads a fixed set of words: labelled, without
label, with no label, by, assigned to, unassigned, in milestone, waiting on
me, mentioning me, open or closed, an age ("older than 90 days", "updated
before March 2024"), and oldest or newest first. The same sentence always
means the same thing, and a word it does not know is never guessed: it says
what it does read, and gives you your sentence back to correct.

It then searches GitHub and shows every item it found as a checked list.
Uncheck any you want left alone, and OK goes on to the same preview and
results as any batch above: "Change 12 issues: state to closed as
completed." Closing as a duplicate is not a batch, because each one needs the
issue it duplicates; close those one at a time with `Delete` on the row. The
WordPress Workbench's Plain-Language Batch reads ages the same way.

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

**Account > Set Your Status...** (`Ctrl+Alt+S`) reads your GitHub status, the
short message beside your name, and offers to set a new one or clear it. A new
one asks, a question at a time, for the message ("Back Monday"), an emoji by
its GitHub name (`palm_tree`, `house`, or none), whether to mark yourself busy,
which tells people asking for your review that you may answer slowly, and when
it clears itself: never, in 30 minutes, an hour, four hours, tomorrow or in a
week. You hear the status as it is now.

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
  value, then Add Condition (`Insert`). Each box reads its own label as you
  Tab to it: Attribute, Operator, Value. The values come from the repository,
  and Me is offered for every person. The query appears as you go, so you
  learn GitHub's syntax by watching it. OK puts it in the filter box; Save as
  Search also keeps it under Saved Searches.

Has Conflicts is the one GitHub's search cannot answer, so the Workbench
checks the pull requests already loaded and the Items cell of the status bar
says so. **View > Load All** (`Ctrl+Shift+Page Down`) loads every page to be
sure.

### More rows

Every list starts with one page: 30 issues or pull requests, 50 rows of
anything else. **Load More** (`Alt+Page Down`) reads one page more each time,
and **Load All** (`Ctrl+Shift+Page Down`) reads up to a thousand at once.
Both work on every list in the Workbench, Notifications, My Work, discussions,
labels and the merge queue included. When a list holds only part of what
GitHub has, the Items cell of the status bar says so, for example "Gists:
showing the first 50 items; more may exist. Load More or Load All reads the
rest.", so a short list is never mistaken for the whole of it.

### Shaping the list

- **View > Show** chooses issues, pull requests or both, and **View > Open or
  Closed** which ones.
- **View > Sort By** orders the list, and **View > Columns...**
  (`Ctrl+Shift+U`) chooses its columns.
- **View > Group By** puts the groups in the tree as nodes: by label,
  milestone, assignee, author, type, state, repository or review state. Each
  node reads with its count, and selecting it shows that group.
- Those orders and groups are an issue's. Every other list (branches, tags,
  releases, workflows, runs, discussions, notifications, alerts, people,
  teams, repositories and the rest) has **Sort By > By Column...** and
  **Group By > By Column...** instead: any of its columns, first to last or
  last to first, and for a list of one column its name, repository, kind or
  last update. Each list remembers its own choice, for this account, as it
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
organization and its teams and leaves only the repositories they were given
directly, so QUILL asks you to type their name first. On the Outside
Collaborators page, Add makes a member an outside collaborator, Change...
invites one to be a member, and Remove takes away every repository they
have here, again after their name is typed. You cannot make yourself an
outside collaborator, remove yourself while you are the last owner, or
remove the last owner.

A team's sheet lists its maintainers and members, and its Repositories page
lists every repository the team reaches with its role there. Add gives the
team a repository, Change... changes its role, and Remove takes it away. The
last maintainer cannot remove themselves. When you take admin away from a
team you are on, QUILL asks GitHub first whether that team is how you
administer the repository, and if it is, says so and changes nothing. The
General page's **Parent team** moves the team under another (empty makes it a
top-level team), and **New Team...** on an organization asks for the parent
and whether mentions notify the team.

The organization's **Members** list in the tree reads the same way ("kim,
member, two-factor off."), and Delete there asks for the name typed and keeps
the last owner. **Members Without Two-Factor** on the organization's row lists
only those, for owners.

On the pending invitations, Remove cancels the invitation (they can be
invited again), and Change... changes the role a repository invitation
offers before it is answered. GitHub cannot change an organization
invitation's role, so for one of those, Remove it and invite them again.

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
a row at a time, so you never have to read a grid:

- **Access Review: People** has a row for every person and repository pair,
  with the role they really have and where it comes from: "jeff on quill:
  Admin, from team Maintainers; also Write directly; also Read from the
  organization's base permission." The highest comes first; every other way
  they have access follows "also". An outside collaborator's direct access
  says so, and an owner's reads "from being an owner of the organization".
- **Access Review: Teams** has a row for every team and repository pair:
  "Docs on site: Reviewer, for 3 members, a child team of Maintainers."
- **Custom Property Values** has a row a repository with every custom
  property, unset ones said as "not set": "site: tier is not set; areas is
  docs and ui."

Type a name, a role or a team in the filter box, or use Show Only, to narrow
any of them, and **Export List...** (`Ctrl+Shift+X`), on the Workbench's File
menu, saves what is shown. When GitHub will
not show part of the answer, for example a repository's direct collaborators
to someone who is not its admin, the status bar says which, rather than
leaving people out silently. **Set Repositories' Custom Property...** on the
organization's row gives one property a value in several repositories at
once, and **Issue Types** under the organization lists its issue types.

### Rules in plain words

A ruleset's sheet, and a branch's protection, list every rule as a check box
with its settings, and a Summary page reads the whole thing as sentences: "On
the default branch: changes need a pull request with 2 approvals including a
code owner; checks build and test must pass; force pushes are blocked." Read
that page first.

A repository's **Settings > Rulesets** list, and an organization's
**Rulesets**, show each ruleset as a sentence; Alt+Enter opens its sheet, and
Delete removes it after you type its name.

- The **Rules** page also has **Every rule and its settings**, a line a rule
  with every setting GitHub sent: file paths, file sizes, patterns, workflows,
  code scanning tools, and any rule type QUILL has no check box for yet.
- The **Bypass** page has a check list of the roles that may bypass the rules
  (organization admins, admins, maintainers, writers, deploy keys), and lists
  everyone who may, teams and apps included. Teams and apps you have not
  changed are kept as they are.
- An organization ruleset's **Repositories** page says which repositories it
  covers, by name or by a custom property, and lets you choose them by name,
  and stop those repositories being renamed out of it.
- A branch's classic protection sheet has every setting GitHub offers:
  approvals, stale approvals, code owners, the most recent push, status
  checks and up to date, signed commits, administrators, linear history,
  force pushes, deletion, conversations, blocking new branches, locking the
  branch, and fork syncing. Its **Who** page says who may push, dismiss
  reviews and skip the pull request; saving keeps those lists exactly as they
  were.
- **Rule Insights** under a repository's settings, and under an
  organization, lists the pushes its rules passed, blocked or let through.

### An organization's roles

GitHub gives every organization roles that reach all its repositories at once:
All-repository read, triage, write, maintain and admin, the security manager,
the app manager, and any custom roles. Choose **Roles...** on an
organization's row (in the Workbench's Organizations place) to open **Roles
in** that organization.

- **Roles** lists them, each with what it is based on and what it is for.
  Choose one, and **Who holds it** fills with its people and teams, each row
  starting with "Person:" or "Team:". A person who holds the role because of a
  team says so: "Person: kim, through docs".
- **Give to Person...** (`Alt+P`) asks for a GitHub username; **Give to
  Team...** (`Alt+T`) asks for the team's short name, as it appears in the
  team's address.
- **Take Away...** (`Alt+A`) asks whether the selected person or team should
  lose only this role or every organization role. A role that comes through a
  team is taken from that team instead, and QUILL says which.

After each change QUILL reads the list back from GitHub and says what
happened, such as "sam now has all_repo_write." These need an owner's sign-in
with the **admin:org** scope.

### An organization's rulesets

An organization ruleset applies across its repositories. Choose
**Rulesets...** on the organization's row to open **Rulesets in** that
organization. Each row gives its name, its enforcement and what it targets:
"Protect main: Active, on branches".

- Choosing one reads it in plain words in **Details**, the same sentences as a
  repository's Summary page, and which repositories it covers.
- **Enforcement...** (`Alt+E`) makes it **Active** (enforced), **Evaluate**
  (reports what it would have blocked, blocks nothing, a safe way to try a
  rule first) or **Disabled**.
- **History** (`Alt+H`) lists its earlier versions, with when and by whom.
- **Rule Insights...** (`Alt+I`) lists recent pushes across the
  organization that its rulesets passed, blocked or let through on a bypass,
  for the last day, week or month.
- **Delete...** (`Alt+L`) deletes it from every repository it covers. QUILL
  asks you to type its name exactly, because this cannot be undone.

To make an organization ruleset from repositories that each have the same
one, use **Promote to Organization** under Across Repositories.

### Repository settings from the editor

With the Workbench in use, the editor's Rename Repository, Change Visibility,
Change Default Branch and Configure Branch Protection open the repository's
sheet at the right page, and Create Repository, Fork, Commit Multiple Files
and the Codespaces commands open the Workbench on the repository and run
from there.
