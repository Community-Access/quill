# The GitHub Guide for QUILL and QUILL Lite

This is the book on doing GitHub work with a screen reader in QUILL and QUILL
Lite: answering what needs you, reading and triaging issues, reviewing pull
requests line by line, finding out why a build failed, browsing code, and
looking after repositories, teams and access. It is a book of its own, beside
each editor's user guide, because there is a lot to say and you may only need
part of it.

You write in the editor, and you do GitHub work in the GitHub Workbench, one
window for everything GitHub. The same Workbench ships in both editors, and so
does this book. Where the two differ, a short paragraph starting **In QUILL
Lite** says how, and Chapter 14 lists every difference.

## How to read this book

- **New to it?** Read Chapters 1 and 2, in that order. They get you signed in
  and show you round the Workbench. Then go to the chapter for the job in
  front of you.
- **Clearing your inbox?** Chapter 3.
- **Issues?** Chapter 4. **Reviewing pull requests?** Chapter 5.
- **A build failed?** Chapter 6, and its section on What Failed.
- **Looking after a repository, an organization or who has access?**
  Chapters 7, 8 and 13.
- **Looking something up?** Chapter 11 has every key, Chapter 12 every place
  in the Workbench, and Appendix A what GitHub needs for each part.
- **Something went wrong?** Chapter 10 has the sentences QUILL says when
  something fails, and what to do about each.

Every chapter starts with why you are there, what you will do and what you
will have at the end, and most end with a walk-through on a practice
repository of your own and the guided lesson that goes with it. Headings are
real headings: each chapter is a level 3 heading on this page, so pressing 3
in JAWS or NVDA moves from chapter to chapter, and inside a chapter its topics
are level 2 headings. At the bottom of every chapter are links to the chapters
either side and back to these contents.

## Keys at a glance

- **Opening the Workbench.** In QUILL, **File > Open from Remote > GitHub
  Items...**. In QUILL Lite, **File > GitHub Workbench...**: `Alt+F`, then
  `G`. In either, **View > GitHub Workbench Mode** adds a GitHub menu
  (`Alt+G`) with the doors in.
- **`F6`** moves between the tree, the filter, the list, the details and the
  status bar.
- **Enter** does the obvious thing, **Backspace** comes back out, and
  **`Shift+Enter`** opens the row on GitHub.
- **`Ctrl+1` to `Ctrl+0`** go to a place: Inbox, the current repository,
  Search, People, Gists, Projects, Watches, Saved Searches, Start Here and
  Across Repositories. **`Ctrl+Shift+1` to `Ctrl+Shift+0`** go to a part of
  the repository: Issues, Pull Requests, Discussions, Actions and the rest.
- **`Alt+1` to `Alt+9`** say something without moving you: where you are,
  what is selected, the item's state, and more.
- **`Alt+Enter`** shows everything about the selected row on one sheet, where
  you can change it.
- **`Shift+F1`** says everything you can do with the selected row, with each
  key, and why anything is greyed. **`F1`** says what the place and the
  control are for.
- **`Ctrl+Z`** takes back your last change on GitHub, where GitHub allows it.
- **`Ctrl+E`** moves to the filter box.

[Chapter 11](#chapter-11-keyboard-reference) has every key.

This is the whole guide as one book: the same chapters as the guide's own pages, in order, each starting with its level 1 heading.

# Chapter 1: Getting started

## What this chapter covers

You are here because you want to do GitHub work from the keyboard, without
fighting the website: read issues, review pull requests, find out why a build
failed, and answer what needs you. QUILL does all of that in one window, the
GitHub Workbench.

In this chapter you open the Workbench in QUILL or QUILL Lite, answer the one
question QUILL asks before it connects, sign in, and add a second account if
you have one. You also choose how much the Workbench may change for each
account, and learn what Safe Mode does.

By the end you will be signed in, with the Workbench open on your Inbox, and
you will know how to get back to it from the editor.

## What the GitHub Workbench is

The GitHub Workbench is one window for everything GitHub: what needs you,
your repositories, searches, people, gists and projects. It works like
Windows Explorer or Outlook:

- **The tree**, on the left, says where you are: Inbox, a repository's Issues,
  its Actions runs, Search, People.
- **The list** shows what is in the place you chose: one row per issue, pull
  request, run or person.
- **The details** say more about the row you are on.

You do not need Git, the GitHub website or any other program. QUILL talks to
GitHub directly. A few jobs open a window of their own in front of the
Workbench, such as a pull request review, the log of a failed job, or a
discussion thread. They block only the Workbench, never the editor.

The same Workbench ships in QUILL and in QUILL Lite, and so does this book.
Where the two differ, a short paragraph starting **In QUILL Lite** says how,
and [Chapter 14](#chapter-14-github-in-quill-lite) puts every difference in
one place.

## Three promises

- **Reading never changes anything.** Moving through a list, opening a
  place, reading a pull request or a log sends nothing to GitHub and marks
  nothing read. Where opening something does mark it read, the chapter says
  so.
- **The bigger the change, the more QUILL asks.** Small organizing changes,
  such as adding a label, are saved at once, and `Ctrl+Z` takes them back.
  Changes other people will see are saved at once too. Changes to access and
  settings show a preview in words first. Anything destructive or hard to
  reverse, such as a merge or deleting a branch, shows a preview and then has
  you type its name or number.
- **QUILL says what GitHub did, not what it hoped.** The sentence you hear
  after a change is built from GitHub's reply. If GitHub accepted a request
  but has not finished it, QUILL says that instead of claiming it is done.

## Opening the Workbench

### In QUILL

There are three ways in.

- **File > Open from Remote > GitHub Workbench...** opens the Workbench. The
  same submenu has **Clone Repository...**, **Open GitHub Reference...** for a
  pasted GitHub link, and **Manage GitHub Accounts...**.
- **The GitHub menu.** Turn on **View > GitHub Workbench Mode** (`Alt+V`, then
  `K`) and a **GitHub** menu joins the menu bar after Tools. `Alt+G` opens it.
  **Open GitHub Workbench** (`W`) opens the window, and **Inbox** (`I`), **This
  Repository's Issues** (`S`), **This Repository's Pull Requests** (`P`) and
  **Actions Runs** (`A`) open it at that place. Chapter 2 walks through the
  menu.
- **Tools > Git and GitHub > GitHub.** Its rows, such as **Notifications...**,
  **Security Alerts...** or **Configure Branch Protection...**, open the
  Workbench at the matching place.

If the Workbench is already open, any of these brings it forward instead of
opening a second one. None of them has a key out of the box, so they do not
take keys a writer needs. Press `Ctrl+Shift+P` for the Command Palette and
type "GitHub" to find any of them by name, or give one a key in the Keymap
Editor.

The GitHub commands belong to the feature called GitHub Remote Access. It is
on in most profiles. If the GitHub rows are missing from the File and Tools
menus, turn it on in **Tools > Customize and Support > Profiles and
Features...**, or press `Alt+Shift+P` and choose a profile that has it. The
Local Git commands belong to the Developer profile.

### In QUILL Lite

Choose **File > GitHub Workbench...**: press `Alt+F`, then `G`. **File >
Clone Repository...** (`Alt+F`, then `Y`) copies a repository to your
computer, and **File > Manage GitHub Accounts...** (`Alt+F`, then `H`) signs
you in. QUILL Lite has **View > GitHub Workbench Mode** too, with a shorter
GitHub menu: the same rows, less the ones about the copy on your computer.

### Where you land

Until you have signed in, the Workbench opens on **Start Here**, which says
what the window is and the five keys to learn first. Once you are signed in,
it opens on **Inbox**: everything waiting on you. You can choose Start Here,
or wherever you were last time, in **Tools > Workbench Options...**
(`Ctrl+Shift+O`), on the General page.

If the document you have open lives in a folder whose Git remote points at
GitHub, that repository becomes the Workbench's current repository, and
`Ctrl+2` goes straight to it. The window remembers, for each account, its
size, the branches of the tree you had open, and the repositories you
visited.

## The first time: permission to connect

The first time you use any GitHub command, a window titled **GitHub Access**
asks whether QUILL may connect to GitHub. Nothing is downloaded until you
choose it. Press **Continue** to go on, or **Cancel** to stop. You are asked
once, and QUILL remembers your answer.

## Signing in

You do not need an account to read public repositories. Without one, the
Workbench is a guest: you can read the issues, pull requests, files, runs and
logs of any public repository, and anything that would change GitHub says it
needs a signed-in account. GitHub also allows a guest far fewer requests an
hour, so a busy session runs out sooner.

Signing in adds private repositories, your Inbox and notifications, your own
work, and every command that changes GitHub. The easy way is **Sign In with
GitHub**: QUILL gets a short code from GitHub, you enter it on GitHub's own
page, and you approve QUILL there. QUILL never sees your GitHub password.

### Signing in with GitHub

1. Open **Manage GitHub Accounts...**. In QUILL it is in **File > Open from
   Remote**; in QUILL Lite, press `Alt+F`, then `H`; in the Workbench, choose
   **Account > Manage GitHub Accounts...** (`Ctrl+Shift+K`).
2. Choose **Sign In with GitHub...**, the first button. Until you have an
   account it is also the default button, so Enter does it.
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
the Page Again**; it is the default button, so Enter works. If the browser
does not open at all, the **What to do** field gives you the address to type.
**Cancel** stops the sign-in and saves nothing.

A code lasts about fifteen minutes. If it runs out, or you choose Cancel on
GitHub's page, the **What to do** field says so in one sentence and nothing is
saved. Choose **Sign In with GitHub...** again for a fresh code.

To add a second account this way, sign in to that account in your browser
first. GitHub approves whichever account the browser is signed in to.

### What QUILL asks GitHub to allow

One sign-in covers every command in the Workbench. QUILL asks for these, and
**Account > GitHub Permissions...** (`Ctrl+Shift+P`) in the Workbench lists
the same, with what each one unlocks and whether you have it:

- `repo`: private repositories, and everything that writes: issues, comments,
  reviews, merges, releases, discussions, workflow runs and saving files. It
  covers your notifications too.
- `workflow`: saving changes to files under .github/workflows.
- `gist`: your gists.
- `read:org`: the organizations you belong to.
- `project`: Projects.
- `security_events`: code scanning and Dependabot alerts.
- `user`: your status, following people, and your billing figures.
- `read:packages` and `delete:packages`: your packages, and deleting one,
  which asks first.
- `admin:public_key`, `admin:gpg_key` and `admin:ssh_signing_key`: your SSH,
  GPG and signing keys.
- `admin:org_hook`: an organization's webhooks, for its owners.
- `delete_repo`: deleting a repository. It still makes you type the full name
  before it deletes anything.

If your organization uses single sign-on, GitHub may ask you to sign in
through the organization while you approve QUILL. If your organization
restricts which apps can see its repositories, see Chapter 10.

Manage GitHub Accounts also has **Add Token (Advanced)...**. You do not need
it to sign in. It is for a few special cases, such as an organization that
blocks sign-in apps, or a GitHub Enterprise Server, and Chapter 10 explains it
under "Advanced: using a token".

### Where your sign-in is kept

When you sign in, GitHub gives QUILL a long code that stands for your
approval. QUILL keeps it in your operating system's secure store: Windows
Credential Manager, or the Keychain on a Mac. A portable copy keeps it in its
own encrypted file. It is never written into a settings file or a log, and it
is sent to GitHub's own servers and nowhere else. When GitHub hands a download
to another address, such as a log or an artifact, QUILL fetches that without
it.

The Workbench's sign-in is separate from My GitHub Copilot's, even though
both go through GitHub's page under the same name. Signing out of one leaves
the other alone.

### In QUILL Lite

QUILL Lite signs in the same way, and the two editors share your accounts: an
account you add in either is there in both. If you open the Workbench before
you have signed in, QUILL Lite says "You are not signed in to GitHub" and
offers three buttons. **Manage GitHub Accounts...** is the default: sign in
there, and the Workbench opens signed in. **Continue as Guest** opens it to
read public repositories. **Cancel** opens nothing.

## More than one account

If you have a personal account and a work account, keep both. **Manage GitHub
Accounts...** shows the active account at the top, such as "Active account:
your-name on github.com", and a list of every account you have added. From
there:

- **Use Selected Account** makes the chosen account the active one. You hear
  "Switched to GitHub account" and its name.
- **Remove Selected Account** deletes that account's sign-in from this
  computer. It does not cancel the approval on GitHub. To do that, open your
  GitHub settings, then **Applications**, then **Authorized OAuth Apps**, and
  revoke QUILL there.
- **Sign In with GitHub...** adds another account. **Add Token
  (Advanced)...** is the advanced road, in Chapter 10.
- **Use GitHub CLI Sign-In...** adds the account GitHub's command-line tool,
  `gh`, is already signed in to, without signing in again. QUILL asks which
  server (github.com unless you change it), asks `gh` for its sign-in, checks
  with GitHub whose it is, and asks "Add your-name on github.com to QUILL with
  that sign-in?" before it keeps anything. QUILL then keeps its own copy:
  signing out of `gh` later does not sign QUILL out, and removing the account
  in QUILL does not touch `gh`. If `gh` is not installed or not signed in to
  that server, QUILL says so and nothing changes.
- **Done** closes the window. Escape does too.

Each account keeps its own place. The Workbench remembers where you were, your
pinned repositories, your saved searches, your repository sets and your local
drafts separately for each account, so switching never mixes them up.

Two of your accounts can also work together. **Account > Roles and Access >
Compare Accounts...** shows what each can do on a repository, side by side,
and **Act As Another Account...** sends one action as another of your
accounts, such as approving your own pull request with your second account.
Chapter 13 covers both.

### A GitHub Enterprise Server

An account can be on your company's own GitHub Enterprise Server as well as on
github.com. Add it with **Add Token (Advanced)...**: make a token on that
server, paste it, and type the server's name, such as github.example.com, in
**GitHub server**. Or, if `gh` is signed in to that server, use **Use GitHub
CLI Sign-In...** and type the server's name. Sign In with GitHub is for
github.com only. The account shows as "your-name (github.example.com)", and
the same name on github.com is a separate account.

QUILL sends that account's token to its own server and nowhere else, and
never sends a github.com token to the server. An older Enterprise Server lacks
some things github.com has. When it does, QUILL says "This server's GitHub
does not have" that thing, and names the server and its version.

## How much the Workbench may change

Each account has a **Workbench level**, which limits what the Workbench may
change with it, whatever GitHub itself would allow. Set it in the Workbench
with **Account > Roles and Access > Workbench Level for This Account...**.

- **Read Only:** nothing is sent. Every command that would change GitHub says
  why it cannot.
- **Organize:** organizing changes, such as labels, assignees and comments,
  and changes other people will see. Nothing about access, settings or
  deleting.
- **Full:** everything GitHub lets the account do. This is where every
  account starts.

Read Only is a good choice for an account you only want to read with, such
as an administrator account you keep for emergencies. The level is checked
once, on every change, before anything is sent. Chapter 13 says more, and
**Least Privilege Advice...** on the same submenu suggests the smallest level
and permissions that cover what you actually do.

## The GitHub CLI and your account

A few things, Codespaces in particular, run through `gh`. It signs in on its
own, separately from QUILL. Before it runs a Codespaces command, QUILL asks
`gh` which account it is using and compares it with QUILL's. If they differ,
QUILL stops and names both, so you never make a codespace on the wrong
account by accident. Chapter 9 covers this.

## Safe Mode

When QUILL or QUILL Lite starts in Safe Mode, the Workbench stays closed.
Opening it says "GitHub item browsing is disabled in Safe Mode. Restart QUILL
normally to browse a repository." The repository commands on QUILL's Tools
menu and the GitHub CLI commands are off too, and every account counts as Read
Only. Start normally to use them again.

## A two-minute tour

This tour reads a public repository, so you can do it before you sign in.

1. Open the Workbench: in QUILL, **File > Open from Remote > GitHub
   Items...**; in QUILL Lite, `Alt+F`, then `G`.
2. If this is the first time, press **Continue** in the GitHub Access window.
   You land on Start Here, with its details in the details pane.
3. Press `Ctrl+L`, type a repository you know, such as
   `community-access/quill`, and press Enter. It gets a place of its own in
   the tree, and you are on it.
4. Press `Ctrl+Shift+1` for its Issues. The list loads. Press `F6` to move to
   the list, then arrow down. Each row is an issue: its number, title and
   state.
5. Press `F6` again to reach the details. Read them like any text field, then
   press `Shift+F6` to go back to the list.
6. Press `Shift+F1`. You hear everything you can do with the selected issue,
   with each key, and why anything greyed is greyed. Press Escape.
7. Press `Alt+1`. QUILL says where you are and the filter in effect, without
   moving you.
8. Press `Alt+F4` to close the Workbench. The editor is where you left it.

Next time you open it, it comes back to the places you visited.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has the GitHub lessons, in
both editors. "Make a repository to practise on" makes `quill-practice`, a
private repository of your own with issues, a pull request and a failing run
to learn on, and walks you round it. Each step says what to press and what
you should hear. Chapter 12 says more about the practice repository.

# Chapter 2: A tour of the GitHub Workbench

## What this chapter covers

Most of this book happens in the GitHub Workbench, so it is worth ten minutes
to learn how the window moves. Every later chapter assumes you know what is
here.

In this chapter you meet the GitHub menu that opens the Workbench from the
editor, then the window itself: its tree, its lists, the filter, Properties,
the context menu, how QUILL asks before it changes anything, `Ctrl+Z` and
Change History, the status bar, and the help keys. It ends with a
walk-through of your first five minutes.

By the end you will know where everything lives, how to get anywhere in one
or two keys, and how to ask the window what you can do wherever you are.

## GitHub Workbench Mode and the GitHub menu

Normally the editor's GitHub commands sit a few levels down, in the File and
Tools menus, where they keep out of the way of writing. When you are spending
an afternoon on issues and pull requests, you want them one key away. That is
what GitHub Workbench Mode is for.

Turn it on with **View > GitHub Workbench Mode**: `Alt+V`, then `K`. It is a
check item, so the View menu tells you whether it is on. QUILL says "Workbench
mode on. GitHub menu added." and a **GitHub** menu joins the menu bar after
Tools. Press `Alt+G` to open it.

While the mode is on, the GitHub rows leave File and Tools and live in the
GitHub menu, so nothing is listed twice. Turn the mode off and they go back.
A key you gave a row goes with it, because keys belong to commands, not menus.
The mode belongs to the window you turned it on in; a new window starts with
it off.

### The Workbench cell on the status bar

While the mode is on, the editor's status bar has one more cell,
**Workbench**. It reads "Workbench:" and the repository the GitHub menu works
on, such as "Workbench: community-access/quill": the repository the document
you have open belongs to. When the document is not in a GitHub repository, it
reads "Workbench". Press `F6` to reach the status bar, then the arrow keys.
`F1` on the cell says what it is. QUILL never reads it out by itself.

### What the GitHub menu holds

From the top:

- **Repository:** and its name, when the document you have open lives in a
  GitHub repository. It is a readout, not a command, so your screen reader
  says it is unavailable.
- **Leave Workbench Mode** (`V`), the way out.
- **Open GitHub Workbench** (`W`): the Workbench window.
- **Inbox** (`I`): the Workbench, on what needs you. Chapter 3 covers it.
- **This Repository's Issues** (`S`), **This Repository's Pull Requests**
  (`P`) and **Actions Runs** (`A`): the Workbench, on that part of the
  document's repository.
- **From This Line** (`R`): what GitHub knows about the line you are on: a
  link to it, who changed it, the pull request that brought it, a new issue
  quoting it, and more. Chapter 7 covers it. In QUILL Lite its rows are in
  the menu itself, with the same letters.
- **Open GitHub Address...** (`D`), in QUILL only: a pasted link, `owner/name`
  or `owner/name#42`, opened at the right place.
- **Clone Repository...** (`C`).
- In QUILL only: **Commit to GitHub...** (`M`), **Sync Folder with GitHub...**
  (`Y`) and the **Local Git** submenu (`L`), because they are about the copy
  on your computer rather than about GitHub.
- **Manage GitHub Accounts...** (`G`) and **Open GitHub Guide** (`H`), last.

Everything else is in the Workbench. The editor's older GitHub commands, such
as My Work, Notifications, Releases and Explore GitHub, still work from the
Command Palette, and a key you gave one still works; each opens the Workbench
at the matching place.

To leave, choose **GitHub > Leave Workbench Mode** (`Alt+G`, then `V`), or
uncheck **View > GitHub Workbench Mode**. QUILL says "Workbench mode off."

**In QUILL Lite**, the mode works in the empty window too, the one left when
you close every document. With the mode on there, that window is a GitHub
launcher with nothing to write in.

## Opening the Workbench

Chapter 1 has every way in. The Workbench is a window of its own, not a
dialog: the editor stays usable while it is open, and `Alt+Tab` moves between
them. Inside the Workbench, **Window > Switch to Editor** (`Ctrl+Shift+E`)
brings back the editor that opened it. `Alt+F4` closes the Workbench; Escape
never does.

## The panes

The window has five parts, in this order:

1. **The tree**, on the left, says where you are.
2. **The filter box** narrows the list.
3. **The list** shows what is in the place you chose.
4. **The details** say more about the row you are on.
5. **The status bar** says who you are signed in as, the repository, how many
   rows there are, the filter, and whether the list is up to date.

`F6` moves to the next part, and `Shift+F6` to the one before. **View > Where
Am I** (`Alt+1`) says the place and the filter in effect, without moving you.

## Finding your way round the tree

The tree works like any tree view. Up and Down Arrow move, Right Arrow opens a
branch and Left Arrow closes it. When you arrive on a place, its list loads by
itself. `Alt+Up` goes to the place above the one you are on.

From the top, the tree holds:

- **Start Here**: what the window is, and the five keys to learn first.
- **Needs My Attention**: your Inbox, notifications, invitations, review
  requests and your own open work. Chapter 3.
- **Repositories**: the current repository first, then Pinned, Favorites,
  your own, Starred, Watched and your organizations. Every repository has the
  same places under it, in the same order: Issues, Pull Requests, Discussions,
  Actions, Code, Releases, Projects, Security, Settings, Insights and more.
- **Search**, with your saved searches under it, then **People**,
  **Gists**, **Projects**, **Watches** and **Across Repositories**.
- **Help and Learning**: tasks, the guide, words, keys, tutorials and tips.

Once you have opened a place, its name in the tree says how many rows it had,
such as "Issues (12)", or "Issues (30 or more)" when GitHub had more pages.
The count is added after you move away, so you hear it the next time you
arrive.

### The Go keys

You rarely need to walk the tree. These keys go straight to a place:

| Key | Goes to |
| --- | --- |
| `Ctrl+1` | Inbox (`Alt+Home` too) |
| `Ctrl+2` | The current repository |
| `Ctrl+3` | Search |
| `Ctrl+4` | People |
| `Ctrl+5` | Gists |
| `Ctrl+6` | Projects |
| `Ctrl+7` | Watches |
| `Ctrl+8` | Saved Searches |
| `Ctrl+9` | Start Here |
| `Ctrl+0` | Across Repositories |
| `Ctrl+Shift+1` to `Ctrl+Shift+0` | The current repository's Issues, Pull Requests, Discussions, Actions runs, Files, Releases, Projects, Security, Settings and Insights |

`Ctrl+L` (**File > Open GitHub Address...**) takes `owner/name`, or a link to
anything in a repository, and gives that repository a place of its own in the
tree, with you on it. A compare link opens the comparison, and `#42` opens
issue or pull request 42 in the repository you are in. `Ctrl+G` (**File >
Go to Number...**) goes to an issue or pull request in the current repository
by its number.

Elsewhere in QUILL, `Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys. The Workbench
has no AI menu, so here they keep their place in the row of digits. Switch
back to the editor and they are AI keys again.

## Reading a list

Each row reads as one line, the way the columns show it: "42, Fix the crash
on start, open". **Tools > Workbench Options...** (`Ctrl+Shift+O`) chooses
between Quick lists, a few columns that are fast to arrow through, and Full
lists, with every column. On the Lists page, **Say column names before
values** puts each column's name in front of its value.

- **View > Columns...** (`Ctrl+Shift+U`) chooses which columns the list
  shows, and their order.
- **View > Sort By** orders the list. On lists other than Issues, **By
  Column...** sorts on any column, and the list remembers it.
- **View > Group By** puts the list's groups in the tree, one place per
  label, milestone, assignee, author, type, state, repository or review
  state, so you can walk one group at a time.
- **View > Show** and **View > Open or Closed** choose issues, pull requests
  or both, open, closed or all.

GitHub sends a list a page at a time. **View > Load More**
(`Alt+PageDown`) asks for the next page, and **Load All**
(`Ctrl+Shift+PageDown`) asks for every page. `F5` loads the place again; when
nothing has changed, GitHub says so in a few bytes and the rows stay as they
were, which costs nothing from your hourly allowance. `Ctrl+F5` asks for
everything afresh.

When you come back to a list, you are on the row you left, even after a
refresh. **Go > Next Unread** (`Ctrl+.`) and **Previous Unread**
(`Ctrl+Shift+.`) move between unread rows.

## Enter, Shift+Enter and Backspace

Three keys do most of the moving, the same way everywhere:

- **Enter does the obvious thing.** On an issue it reads it, on a pull
  request it opens the review, on a run it shows the jobs, on a repository it
  opens the repository's place in the tree, on a folder it opens the folder.
- `Shift+Enter` **opens the selected row on GitHub**, in your browser.
  `Ctrl+Enter` opens a file in the editor.
- **Backspace comes back out**, to the place you were before. **View > Back**
  (`Alt+Left`) and **Forward** (`Alt+Right`) step through the places you have
  been.

## The filter

`Ctrl+E` moves to the filter box (`Ctrl+Shift+F` does too). Type, and press
Enter.

- **Plain words** narrow the rows already loaded, on your computer.
- **GitHub's own words**, such as `is:open author:@me label:bug`, ask GitHub,
  so the list holds everything that matches, not only what was loaded.

**Edit > Filter Builder...** (`Ctrl+Alt+F`) builds a filter one condition at a
time: choose what to filter on, how, and a value from the repository, such as
one of its labels, and it writes GitHub's words into the filter box for you.
**View > Quick Filters** has the common ones as check items: Assigned to Me,
Opened by Me, Review Requested from Me, No Assignee, Checks Failing, Updated
This Week and more. They combine with each other and with what you typed.

Escape in the filter box clears it. **View > Say Filter** (`Alt+7`) says the
filter in effect in words. Chapter 13 has more on filtering.

## Properties

`Alt+Enter` (**Item > Properties...**) shows everything about the selected
row on one sheet, in pages, the way Windows shows a file's properties. On a
sheet you can change what GitHub lets you change, such as an issue's labels,
a repository's settings or a team's members, and save it all at once. Select
several rows first and the sheet changes all of them together. Chapter 13
covers Properties in full.

## The context menu and the Item menu

The Applications key, or `Shift+F10`, opens the selected row's context menu.
It holds everything you can do with that row, with the obvious thing first and
Properties last; a long menu puts the rest under **More**. The **Item** and
**Repository** menus on the menu bar hold the commands you use most, each with
its key.

**Help > What Can I Do Here?** (`Shift+F1`) is the quickest way to find out
what you can do. It lists every command for the selected row, with its key,
and says why anything greyed is greyed.

`Delete` always does the safe thing for the kind of row, and asks first
whenever it cannot be undone: it marks a notification done, closes an issue,
or deletes a branch, a label or a run after asking. It never deletes the
repository's default branch. Enter never deletes anything.

## How QUILL asks before it changes GitHub

How much QUILL asks depends on how much a change matters:

- **Organizing**, such as adding a label or an assignee: saved at once, and
  `Ctrl+Z` takes it back.
- **Visible to others**, such as a comment: saved at once.
- **Access and settings**, such as giving someone a role or changing branch
  protection: a preview in words first, and nothing is sent until you say
  yes.
- **Destructive or hard to reverse**, such as a merge, or deleting a branch
  or a repository: a preview, and then you type its name or number to
  confirm.

On top of that, each account has a Workbench level, Read Only, Organize or
Full, which Chapter 1 explains. Changes run without freezing the window, and
each one ends with a sentence about what GitHub confirmed. `F9` says the last
one again, and `Shift+F9` explains it: what it means, and what you might do
next.

### Trying a command without sending it

**Tools > Dry Run** (`Ctrl+Alt+D`) is a switch for the whole Workbench. While
it is on, every command asks its questions and shows its preview as usual,
then stops at the moment it would change GitHub and says what it would have
sent. Everything that only reads keeps working. The status bar's Account cell
says "Dry Run: nothing is sent" while it is on. Chapter 12 has more.

## Taking a change back

**Edit > Undo GitHub Change** (`Ctrl+Z`) reverses your last change on GitHub,
where GitHub allows it. It reads the item again first, and stops and says so
if someone else has changed it since. **Redo GitHub Change** (`Ctrl+Y`) makes
it again. In a text box, `Ctrl+Z` undoes your typing instead.

**Account > Change History...** (`Ctrl+Shift+H`) lists every change the
Workbench made on GitHub, newest first, with before and after, and Undo on
each one where GitHub allows it. A merge, a deleted branch or a sent comment
cannot be undone this way; the chapters for each say what can.

## The status bar

The status bar has five cells: **Account** (signed in or not, and Dry Run),
**Repository**, **Items** (how many rows are shown and selected), **Filter**
and **Loading** (loading, or when the list was last brought up to date). Press
`F6` until you reach it, then the arrow keys. Enter on a cell does its job:
Repository goes to the repository's place, Items to the list, Filter to the
filter box.

You do not need to visit it. **View** has a key for each thing it says, and
more:

| Key | Says |
| --- | --- |
| `Alt+1` | Where you are, and the filter |
| `Alt+2` | How many rows are selected |
| `Alt+3` | The selected item's state |
| `Alt+4` | How many rows the place holds |
| `Alt+5` | What you can do here |
| `Alt+6` | How much of GitHub's hourly allowance is left |
| `Alt+7` | The filter, in words |
| `Alt+8` | What is loading, or when it loaded |
| `Alt+9` | The account, and whether you are signed in |

## What QUILL says, and what it leaves to your screen reader

Your screen reader already says the window's name, the control that has focus,
the row you arrive on and the place you select in the tree. QUILL does not
repeat any of that. It speaks only what your screen reader cannot know: the
result of a command, a load that finished somewhere you are not looking, or
GitHub's reason for refusing. Everything it says is brailled as well as
spoken.

Results follow the same setting as the editor's copy and paste, **When a
command does something, give me** (QUILL Guide, chapter 11). A bare "Saved."
follows the setting: a sound, the words, both or neither. A result that names
or counts something, such as "Created bug", is always spoken, because no
sound can carry a name. Anything that did not work starts "Could not", plays
the error sound when sounds are on, and is always spoken.

## Open GitHub Reference: paste any link

Someone sends you a link to an issue, a pull request, a line of a file or a
failed run. You do not need to work out where it lives.

In QUILL, choose **File > Open from Remote > Open GitHub Reference...**, or
**GitHub > Open GitHub Address...** in workbench mode. Paste a link, or type
`owner/name` or `owner/name#42`, and press Enter.

- A repository link opens the Workbench on that repository.
- An issue, pull request, discussion, release, branch, tag or commit link
  opens the Workbench at the matching list in that repository: Issues, Pull
  Requests, Discussions, Releases, Branches, Tags or Commits. Press `Ctrl+G`
  and type the number, or use the filter, to reach the one you asked for. Any
  other link into a repository, such as a run, opens the repository's own
  place.
- A link to a file opens the file in the editor, at the linked lines when the
  link names them.
- A link QUILL has no place for asks whether to open it in your browser, and
  says QUILL will not attach your GitHub sign-in to that request.

QUILL refuses a link that carries a password or a token in it. Paste the
plain address.

Inside the Workbench, `Ctrl+L` does the repository part of this, as **The Go
keys** above says.

**In QUILL Lite**, open the Workbench and use `Ctrl+L`. A file link opens the
file's text as a new untitled document.

## Rate limits and the readout

GitHub lets each account make a certain number of requests an hour, and fewer
as a guest. You rarely need to think about it. When you do, press
`Ctrl+Shift+L` (**Account > GitHub API Rate Limit**) or `Alt+6`. QUILL reads
GitHub's own count and says it in a sentence, such as "GitHub API: 4,212 of
5,000 left, resets at 3:15 PM." Search and code search have allowances of
their own, and the readout includes those too.

If GitHub asks QUILL to slow down, QUILL stops sending until the wait is over
and says so once: "GitHub asked QUILL to wait 60 seconds." When the hourly
allowance runs out, you hear "GitHub API rate limit reached. Retry after" and
the number of seconds.

QUILL remembers what GitHub last sent for the reads it repeats, and asks
whether anything changed since. If nothing has, that answer does not count
against your allowance. Nothing is kept on disk for this; it lasts until you
close QUILL.

## F1, and help for every place

The help keys work everywhere in the window:

| Key | Answers |
| --- | --- |
| `F1` | What this place and the control you are on are for |
| `Shift+F1` | What you can do here, with each key, and why anything is greyed |
| `Alt+F1` | What the GitHub word for the selected row means |
| `Ctrl+F1` | This guide, at the chapter for where you are |
| `Ctrl+Shift+F1` | Search all of help: places, commands, words and tasks |
| `Alt+Shift+F1` | Every key in the window |
| `Ctrl+Alt+K` | Key Describer: press keys to hear what each does, without doing it; Escape stops |
| `F11` | Say or Type a Command: type what you want, such as "show the pull requests" |
| `F9` and `Shift+F9` | The last result again, and what it means |

The last place in the tree, **Help and Learning**, is help you can walk like
any list: tasks in plain words with **Walk Me Through It**, this guide's
chapters, the GitHub words, every key, the tutorials and QUILLBert's tips.
Chapter 12 covers it.

## A walk-through: your first five minutes

You need to be signed in for this, and it changes nothing on GitHub.

1. Open the Workbench. You land on Inbox, and the list loads.
2. Press `Alt+4`. You hear how many rows Inbox holds.
3. Press `Ctrl+2` for the current repository, or `Ctrl+L`, type
   `community-access/quill` and press Enter.
4. Press `Ctrl+Shift+2` for its pull requests. Press `F6` until you are in
   the list, and arrow down.
5. Press `Ctrl+E`, type `is:open review:required`, and press Enter. The list
   holds only open pull requests that still need a review. Press `Alt+7` to
   hear the filter in words.
6. Press `Shift+F1` on a pull request to hear what you can do with it. Press
   Escape.
7. Press `Alt+Enter`. The pull request's Properties sheet opens on its first
   page. Press `Ctrl+Tab` to move through the pages, then Escape to close it
   without changing anything.
8. Press `Backspace`. You are back where you were before the repository.
9. Press `Ctrl+F1`. This guide opens at the chapter for the place you are on.

## Practising on a repository of your own

**Help > Practice on GitHub...** (`Ctrl+Alt+P`) makes `quill-practice`, a
private repository in your own account, with issues, labels, a pull request
and a run that fails on purpose. Every write in this book can be tried there,
where nothing matters. Chapter 12 has the details, and **Help > Tutorials**
(`Ctrl+F2`) has lessons that use it, starting with "Make a repository to
practise on".

# Chapter 3: Your inbox and your work

## What this chapter covers

GitHub tells you whenever something you are part of moves. On a busy project
that is dozens of notifications a day, and the website shows them as a long
page of links and icons. In QUILL they are a list you work through from the
keyboard.

In this chapter you open Needs My Attention, read what each notification
says, mark it read or done, put it off for a day, and stop hearing about a
thread. You set up inbox rules for the notifications that always get the same
answer, answer an invitation, and use the lists that split your open work by
why it is yours.

By the end you will be able to clear your inbox every morning, and know where
to look for the reviews, assignments and mentions waiting on you.

All of this needs a signed-in account, because it is your own inbox and your
own work. Until you sign in, each of these places says so and names the way
in: **Manage GitHub Accounts...** (`Ctrl+Shift+K` in the Workbench). Chapter 1
shows how.

## Needs My Attention

Everything waiting on you is under **Needs My Attention**, near the top of the
Workbench's tree. `Ctrl+1` goes straight to its first place, Inbox, from
anywhere in the window, and so does `Alt+Home`. From the editor, the GitHub
menu's **Inbox** row opens the Workbench there (Chapter 2 has the GitHub
menu).

The places under it, in order:

| Place | What it holds |
| --- | --- |
| Inbox | What needs you to act: work assigned to you, review requests, mentions, and pull requests whose checks failed |
| Notifications | GitHub's own notifications, unread ones |
| Invitations | Repositories you have been invited to |
| Review Requests | Pull requests waiting for your review, or your team's |
| Assigned to Me | Issues and pull requests assigned to you |
| Mentions | Issues and pull requests where someone wrote your name |
| My Open Pull Requests | Pull requests you opened that are still open |
| My Open Issues | Issues you opened that are still open |
| My Activity Feed | What you did on GitHub lately, newest first |

When one of them is empty, its details say so and say what would fill it, so
an empty list never leaves you wondering whether it loaded.

## Reading your notifications

Arrow down the tree to **Notifications**. The list loads by itself. Press
`Tab` to move into it, or `F6` to move from pane to pane.

Each row says, in this order, whether it is unread, why it reached you, the
repository and the title: "Unread, review requested: community-access/quill",
then the title.

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

The details pane holds the rest, one line each: what the subject is (an
issue, a pull request, a release, a discussion, a commit, a workflow run or a
security alert), the repository, why you got it, whether it is read and when
it last changed, and its link.

**Why?**, on a notification's context menu, says the reason in a sentence and
what decides it, such as watching the repository or being on a team.

Notifications lists the unread ones. A notification you mark read leaves the
list the next time it loads.

## Opening a notification

**Enter** moves you to the details pane, so you can read the notification in
full. To act on what it is about:

- `Shift+Enter` opens it on GitHub, in your browser.
- `Ctrl+Shift+C` copies its address.
- `Ctrl+L` (**File > Open GitHub Address...**) takes an address or a number,
  such as `owner/name#42`, and goes to its place in the tree. Chapter 2 has
  more on it.

Opening a notification does not mark it read. Mark it read yourself when you
have dealt with it, as the next section shows.

## Clearing your inbox: Mark Read, Mark Done, Snooze and Unsubscribe

Each of these is on a notification's context menu (`Shift+F10` or the
Applications key), and the commonest have keys of their own:

| Command | Key | What it does |
| --- | --- | --- |
| Mark Read | `Ctrl+Q` | Marks it read, here and on GitHub. You hear "Marked read." |
| Mark Done | `Delete` | Takes it out of your inbox, the same as Done on GitHub. You hear "Marked done." |
| Unsubscribe from Thread | none | Stops notifications from that thread for good, and takes it out of the inbox. You hear "Unsubscribed." |
| Snooze for One Day | none | Notes on this computer that you have put it off until tomorrow. GitHub is not told. You hear "Snoozed here for one day. GitHub was not changed." |
| Unsnooze Locally | none | Takes the snooze off again. |
| Mark All Read in View | `Ctrl+Shift+Q` | Marks every notification in the list read. |

After Mark Read, Mark Done or Unsubscribe the list loads again.

A snoozed notification leaves the list until the next day, and the status
bar says how many are hidden. Turn on **Include read notifications** in
Workbench Options to see them again, each starting "Snoozed here until", so
you can Unsnooze one. That option also shows notifications you have already
read, as well as unread ones.

GitHub asks apps to wait between checks of your notifications. A refresh
sooner than that shows the list from the last check and says how many
seconds to wait.

`Ctrl+.` moves to the next unread row in the list, and `Ctrl+Shift+.` to the
one before, so you can skip what you have already read.

### Mark All Read

**Item > Mark All Read in View** (`Ctrl+Shift+Q`) marks every notification in
the list read. When there are more than twenty, it asks first: "Mark all 41
notifications in this view read?" You then hear how many it marked, such as
"Marked 41 read."

### Keeping your place

When you come back to Notifications with Back (`Alt+Left`), or the list loads
again after a change, QUILL returns you to the row you left rather than the
top of the list.

## Invitations

When someone invites you to a repository, GitHub sends a notification, and
the invitation itself waits in **Needs My Attention > Invitations**. Each row
says the repository, who invited you and with what access: "octo/app: ann
invited you, write access". The details say when.

- **Enter**, or **Accept Invitation...** on the context menu, asks first, then
  joins you to the repository.
- **Decline Invitation...** asks first, then says no.

An invitation expires after a week. An expired one ends in "expired", cannot
be accepted, and can still be declined to clear it away.

An organization's invitation is different. On an organization's row,
**Your Invitation** says whether it has invited you. GitHub lets apps accept
an organization's invitation but not decline one, so it also says where on
GitHub to decline it. **Accept Membership**, on the same menu, joins you.

## Inbox rules

Some notifications always get the same answer: a Dependabot update you will
never read before it merges, a busy repository you only watch, a mention you
always want first. An inbox rule gives that answer for you as the list
arrives.

Choose **Item > Inbox Rules...** (`Ctrl+Alt+N`). The window lists your rules,
each read as a sentence, and **New Rule...** at the end. A new rule asks five
questions, one at a time:

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

A rule needs at least one of these. One with none would act on every
notification, so QUILL will not save it.

Before saving, QUILL reads the rule back and tries it on the notifications
already loaded today: "When a notification is from octo/*, about a pull
request, with 'Bump' in its title: mark it done. It matches 3 of the 41
notifications loaded today, and would mark them done:" and their titles. Yes
saves it; No saves nothing.

From then on the rules run every time Notifications loads, before you see the
list. The first rule that fits a notification decides what happens to it.
Marking done and marking read are sent to GitHub, as if you had pressed the
keys yourself. Moving to the top only changes the order here. The status bar
then says what the rules did, such as "Inbox rules: 3 marked done, 1 moved to
the top."

To delete a rule, choose it in the Inbox Rules window and say Yes.

Rules are kept on this computer.

## How often QUILL checks

The Workbench reads Notifications when you arrive on it, and again when you
press `F5` (**View > Refresh**). Each time, QUILL asks GitHub only for what
has changed since the last read. An unchanged inbox comes back in a moment
and costs nothing from your hourly allowance.

While QUILL is open, it can also check for new notifications in the
background. **Tools > Workbench Options...** (`Ctrl+Shift+O`), on the
**Notifications and Inbox** page, sets how often, from 5 minutes to a day,
whether each check plays a short sound, and whether a new notification may
interrupt what is being said. GitHub may ask for longer between checks, and
then it gets longer. When your hourly allowance runs low, QUILL waits longer
on its own: twice as long with under a quarter left, four times as long with
under a tenth.

## The Inbox: what needs you to act

**Inbox** is the short, sharp list: only what is waiting for you to do
something. It gathers four kinds of open work, the most recently updated
first:

- **Assigned to me**
- **Review requested**, from you or from a team you are on
- **Mentioned**
- **Failed checks**: your own open pull requests whose checks failed

Each row's details start with where it came from, so you know whether it is
there because you were assigned or because you were mentioned. An item found
for more than one reason appears once, its details starting "Also:" and every
reason. A review asked
of a team you are on, rather than of you by name, ends in "team review
request", because someone else on the team may take it.

### Where each pull request stands

A pull request in the Inbox also says where it stands, in the same sentence
the review window opens with: "Approved, 2 checks failing, 1 open thread". It
comes after the row's name in the list, and in the details it follows the
reason the row is there.

QUILL reads every pull request's sentence in one request when the Inbox
loads. It covers the twenty newest. When there are more, the status bar says
so, such as "Summaries cover the newest 20 of 26 pull requests".

The sentence never calls a pull request ready on data it does not have. When
GitHub sent only part of the picture, it says "merge readiness unknown". When
GitHub did not answer for a pull request at all, its row says "Summary
unavailable".

If part of the Inbox could not load, perhaps because GitHub refused one of
the searches, QUILL does not pretend the list is complete. The status bar
says which part is missing.

## Your open work, split by why it is yours

The next five places under Needs My Attention are the same work split by
reason:

- **Review Requests** holds two kinds: pull requests that ask you by name,
  and those that ask a team you belong to. A team's row ends in "team review
  request". The pull request's own Properties sheet (`Alt+Enter`) names the
  team under Team reviewers. GitHub's search cannot say which team from the
  list itself. Enter on a pull request here opens its review (Chapter 5).
- **Assigned to Me**, **Mentions**, **My Open Pull Requests** and **My Open
  Issues** are what their names say, across every repository you can see.

An item that turns up for more than one reason appears once in each list it
fits. Its details start with every reason that found it.

Every list here works like any other in the Workbench: the filter box
(`Ctrl+E`) narrows it, **View > Sort By** and **View > Group By** shape it,
and **File > Export List...** (`Ctrl+Shift+X`) saves it. Chapter 13 has
filtering and grouping.

## Activity

Three places show what has been happening rather than what is waiting:

- **Needs My Attention > My Activity Feed**: what you did lately.
- **Activity**, under a repository: its recent events.
- **Activity**, under a person: their public events. Enter on a person, in
  People or anywhere else, gives them a place in the tree.

Each row reads the kind of event, the repository and who did it.

## A walk-through: clearing your inbox in the morning

You start the day with a handful of notifications. Here is the routine.

1. Open the Workbench and press `Ctrl+1`. You hear "Inbox", and how many rows
   it has. These are the things waiting on you to act.
2. Arrow down the tree to **Notifications**, and press `Tab` to move into the
   list. You hear the first row, such as "Unread, review requested:", the
   repository and the title.
3. Press `Enter` to read it in full in the details pane. Press `Shift+Tab` to
   go back to the list.
4. Decide. If you have dealt with it, press `Ctrl+Q`: you hear "Marked read."
   If it needs nothing from you, press `Delete`: you hear "Marked done." If
   you never want to hear about that thread again, choose **Unsubscribe from
   Thread** from the context menu.
5. When the list is clear, arrow down the tree to **Review Requests** and
   work from the top. Enter on a pull request opens its review.

If the same kind of notification turns up every morning, make an inbox rule
for it with `Ctrl+Alt+N`, and tomorrow it is dealt with before you arrive.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has **Triage your inbox**,
a six-minute lesson that goes to the Inbox, looks at Review Requests, marks a
notification read, snoozes one and brings it back. Each step says what to
press and what you should hear.

# Chapter 4: Issues

## What this chapter covers

Issues are how a project keeps its list of work: bugs, ideas, questions and
tasks. Most days on GitHub start with one. On the website an issue is a long
page of comments, labels in coloured boxes and a sidebar of settings. In the
Workbench it is a row in a list, its details in a pane beside it, and a
Properties sheet with everything you can change.

In this chapter you read an issue and its comments, comment and react, read
its history, write a new issue from a template or a form, label it, put it in
a milestone, assign it, close it with a reason, and break it into sub-issues.
You also change many issues at once, keep issue fields and Projects up to
date, and start work on an issue in a branch and folder of its own.

By the end you will be able to take an issue from filed to closed without
leaving the keyboard. Pull requests are issues too, so most of this works on
them as well; Chapter 5 covers what is theirs alone.

Reading works signed out, on public repositories. Everything that changes an
issue needs a signed-in account, and the access GitHub gives you on that
repository: commenting needs only a sign-in, labels, assignees and milestones
need triage, and locking needs write.

**In QUILL Lite**, everything here works the same, except two commands that
need the editor's own connections: **Summarize Discussion** needs QUILL's AI
connection, and **Start in Local Worktree...** needs QUILL's local Git. In
QUILL Lite both are greyed, and `Shift+F1` says why.

## Finding an issue

A repository's issues are in its **Issues** place in the tree. `Ctrl+Shift+1`
goes there from anywhere in the repository. **Issues and Pull Requests**,
two places further down, lists both together, newest first.

- `Ctrl+G` (**File > Go to Number...**) goes to an issue or pull request in
  this repository by its number.
- `Ctrl+L` (**File > Open GitHub Address...**) takes `#42` for this
  repository, `owner/name#42`, or a link pasted from anywhere, and goes there.
- `Ctrl+E` moves to the filter box. Plain words narrow the list you are
  looking at; GitHub's own words, such as `is:open label:bug`, ask GitHub.
- **View > Open or Closed** chooses open, closed or all, and **View > Quick
  Filters** has the common ones, such as Assigned to Me, No Label and Updated
  This Week. Chapter 13 has filtering, sorting and grouping in full.

## Reading an issue

Arrow to the issue and press **Enter**. Focus moves to the details pane,
which reads like a document:

- the number, whether it is an issue or a pull request, and the title;
- its state, author, when it was opened and last updated, and its link;
- its labels and assignees, when it has any, and how many comments;
- its type and issue fields, when the repository uses them;
- then a line of dashes, and the description.

`Shift+Tab` goes back to the list.

Shortcodes such as `:tada:` are read by their names, "party popper", so you
do not hear colons spelled out.

### Reading the comments

The details pane holds the description, then the comments, oldest first,
each starting "Comment 1 of 3", its author and its date. QUILL reads them
the first time you select the issue; until they arrive the pane ends
"Reading the comments...". If you are in the pane when they land, you hear
"3 comments read; they follow the description." To read the
whole conversation with a heading for each post, choose **Read as
Document...** (`Ctrl+Shift+I`). It asks how you want it:

- **Open in Editor** opens the thread as one document, a heading per post
  with its author and date, so your screen reader's heading keys move from
  post to post. You hear "Opened #12 in the editor, 5 posts."
- **Save as Markdown...** or **Save as HTML...** saves it to keep.

### A summary of the discussion

**Summarize Discussion**, on the issue's context menu, asks QUILL's AI to boil
the issue and its comments down to a few sentences: what it is about, where
it stands, the open questions and the next step. The summary goes at the top
of the details pane, with the issue's link under it, and focus moves there.
You hear "Summary ready for #12." It uses the AI connection you chose in
QUILL, and asks the same questions about sending text that every AI feature
asks. With no AI set up, you hear "AI is not set up, so there is no
summary."

## Commenting

Select the issue and choose **Comment...** (`Ctrl+Shift+M`). It is on the
context menu and the **Item** menu too. The comment window opens with the
cursor in **Comment:**. Write in Markdown; Enter starts a new line, and
`Ctrl+Enter` posts.

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
  program attach a file. Put the file in a release or a gist and paste its
  link, or attach it on github.com.
- **Preview** (`Alt+P`) reads the comment into the **Preview:** box as GitHub
  will show it, one line each, saying what every line is: "Heading 2: Plan",
  "Not done: Run it", "Quote: ...", a code block and how long it is, and what
  each image and link stands for. Its last lines name who the comment will
  notify and which issues it refers to.

**Check before posting** (`Alt+H`) is checked to begin with. When you post, it
looks for things that trip a reader: an image with no description, a link
that says "click here", a heading that skips a level, a long run of capital
letters, and a comment that is only an emoji. If it finds any, it lists them
and asks whether to post anyway; No takes you back to the comment. Clear the
check box for a comment you know is fine.

**Post** sends the comment, and you hear "Comment posted on #12." Escape sends
nothing. If your account cannot comment, GitHub's refusal is said in words.

To change or delete a comment you already posted on an issue, use the issue's
page on GitHub (`Shift+Enter`). Chapter 5 covers a pull request's review
comments, and Chapter 8 a discussion's.

## Reactions

**React...** on the issue opens its Properties sheet at the **You** page, on
**Your reactions**: a check box for each of GitHub's eight reactions, thumbs
up, thumbs down, laugh, hooray, confused, heart, rocket and eyes, checked when
you have given it. Check or clear one and save.

**React to a Comment...** reacts to one of the issue's comments instead. It
asks which comment, then which reaction; choosing one you already gave takes
it back. You hear "Added a heart to ann's comment." or "Took back your heart
from ann's comment."

**Subscribe or Unsubscribe...** chooses how much you hear about the issue:
**All activity**, or **Only when you take part or are mentioned**. You hear,
for example, "Subscribed to #12: you hear of all its activity." The same is
the **Subscribed** check box on the You page.

## The timeline

Comments are only part of an issue's story. Labels are added, people are
assigned, the issue is closed and reopened, and pull requests mention it.
**View Timeline...** on the context menu opens the whole history in one text
box, **History, oldest first:** (`Alt+H`), one event to a line. **Copy All**
(`Alt+A`) copies it. A very long history is read up to five hundred events,
and QUILL says when it stopped early: "Only part of the history was read."

Two more buttons act on the comment whose line the cursor is on, the line
that says "commented":

- **Hide or Show Comment...** (`Alt+C`) folds a comment away for everyone
  without deleting it, as GitHub's own Hide does, for spam, abuse, off topic,
  outdated, a duplicate or resolved. Choose the reason, or **Show it again**
  for one that was hidden. You hear "Hid the comment as off topic." You need
  triage access.
- **Pin or Unpin Comment...** (`Alt+P`) keeps one comment at the top of the
  conversation, such as the answer or the current plan. Choose **Pin it to the
  top** or **Unpin it**. GitHub shows a pinned comment first, for everyone.

## Writing a new issue

Go to a repository's **Issues** or **Issues and Pull Requests**, and press
`Ctrl+N` (**File > New Here...**). The Workbench reads the repository's issue
templates first.

### Templates and issue forms

If the repository has templates, QUILL asks which to start from: **Blank
issue**, then each template with its description.

- **A Markdown template** fills the New Issue window with its title, body,
  labels and assignees, ready for you to change.
- **An issue form**, the kind written in YAML that shows on the website as a
  form with boxes, opens as a real form: one labelled control per field, with
  "(required)" in the name of every field that must be answered. Create Issue
  says what is still missing rather than sending an incomplete issue, and the
  issue GitHub receives reads the same as one filed from the website.

A form or template QUILL cannot fill, such as one too large to load, is left
off the list, and QUILL says so once; it is still there on GitHub. Chapter 12
has more on templates and forms, including building your own.

### The New Issue window

The window has **Title:**, **Body:**, **Labels (comma-separated):** and
**Assignees (GitHub usernames):**. Labels and assignees are optional, and
must already exist in the repository.

What you type is saved on this computer as you go, so closing the window by
mistake loses nothing: the next New Issue in that repository says "Recovered
a local draft", and **Discard Saved Draft** throws it away. A draft is never
sent by itself.

**Create Issue** is the only button that sends anything, and it shows a
preview first: the repository, title, template, labels, assignees and body.
For a long body the preview is shortened and says so; the full body is sent.
Yes sends it, and you hear "Created issue #43." The list loads again with the
new issue in it.

### Many issues at once

When the issues already exist somewhere else, you do not have to type them
one by one:

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

**Labels...**, **Assignees...** and **Milestone...**, on the issue's context
menu, open its Properties sheet (`Alt+Enter`) at the **Organize** page, with
focus on that field:

- **Labels** is a list of every label in the repository, each a check box,
  checked when the issue has it. **New Label...** beside it makes one.
- **Assignees** is the same for the people who may be assigned, up to ten.
- **Milestone** is a choice of the repository's milestones, or none. **New
  Milestone...** beside it makes one, and chooses it.

Change what you like and press OK, or `Ctrl+S` to save and keep the sheet
open. QUILL sends only what you changed, reads the issue back, and says what
GitHub kept. `Ctrl+Z` in the list undoes it. Chapter 13 has the sheet in
full.

### Labels

A repository's **Labels** place lists its labels, each with its description.

- **Enter**, or **Find Issues with Label**, lists the issues and pull requests
  with that label.
- **Edit Label...** changes its name, colour or description.
- **Delete Label...**, or the Delete key, deletes it after asking. It comes
  off every issue that had it.

To make a label, use **New Label...** beside Labels on any issue's sheet.

### Milestones

A repository's **Milestones** place lists its milestones. Each reads in
words: "Release 2.0: 62 percent done, 5 open, 8 closed, due 12 December".

- **Enter**, or **Find Issues in Milestone**, lists its issues and pull
  requests.
- `Alt+Enter` opens its sheet, where the title, description and due date
  (typed as year-month-day, such as 2026-12-12) can be changed.
- **Delete Milestone...** deletes it after asking. Its issues and pull
  requests stay, with no milestone. Closing it keeps the milestone and its
  history, and is usually what you want.

**Repository > Repository Actions...** (`Ctrl+Shift+G`) also has
**Milestones...**, a window of its own:

- **Show:** (`Alt+S`) chooses Open, Closed or All.
- **Milestones** (`Alt+M`) is the list, and **Details** (`Alt+D`) the selected
  one in full.
- **New...** (`Alt+N`) and **Edit...** (`Alt+E`) ask for a **Title:**, a
  **Description:**, and a **Due date (year-month-day):**, which you can leave
  empty.
- **Close Milestone...** (`Alt+L`) closes the selected milestone after asking.
  On a closed one it reads **Reopen Milestone...**.
- **Open on GitHub** (`Alt+O`) and **Refresh** (`Alt+R`).

Every change is reported from what GitHub sends back.

### Handing an issue to Copilot

**Assign to Copilot...** (`Ctrl+Shift+A`) hands the issue to Copilot's coding
agent, which works on it in the background and opens a pull request for you
to review.

QUILL first asks GitHub whether Copilot can be assigned in this repository. If
it cannot, you hear why: the coding agent needs a Copilot plan that includes
it, and it has to be turned on for the repository, which an organization owner
may have to allow. Nothing is changed. If it can, QUILL asks before handing
the issue over and names anyone already assigned, who stay assigned. You hear
that it is assigned only when GitHub's answer lists Copilot as an assignee. A
closed issue, or one Copilot already has, gets a sentence saying so instead.

The command is only on issues. To have Copilot look at a pull request, choose
**Ask Copilot to Review** on the pull request (Chapter 5).

## Closing and reopening

**Close or Reopen...** on an open issue asks why, as GitHub does:
**Completed**, **Not planned**, or **Duplicate of another issue...**, which
then asks for the other issue's number. You hear "Closed #7 as completed.",
"Closed #7 as not planned." or "Closed #7 as a duplicate of #3, Original
title." A duplicate is recorded on GitHub against the issue you named.

The Delete key on an issue does the same: it closes, after asking, and never
deletes. On a closed issue the same command reopens it. A pull request keeps
the plain question, because GitHub gives it no reason.

**Not a Duplicate...** takes back "duplicate of" when an issue was closed
against the wrong one. QUILL asks which issue it was marked a duplicate of,
then says "#7 is no longer marked a duplicate of #3, Original title." The
issue stays closed; Close or Reopen... reopens it.

## Changing many issues at once

Select several issues: hold Shift with the arrows to select a run, hold Ctrl
and press Space to add or take away one row, or press `Ctrl+A` for them all.
Then press `Alt+Enter`. One Properties sheet opens for all of them, titled
"Properties of 5 issues". A field that differs says Mixed and is left alone
unless you change it, and a label on some of them reads "bug, on 3 of 5".

You hear a preview first, such as "Change 14 issues: add bug, remove triage.",
then a result for each issue: Done, Skipped because it was already so, or
Failed and why. **Retry Failed** (`F8`) runs the failed ones again.

To say the change in words instead, choose **Tools > Plain-Language Batch...**
(`Ctrl+Shift+S`) and type it, such as "close every issue labelled duplicate
older than 90 days" or "add label triage to every issue with no label". QUILL
finds the issues without any AI, shows them as a checked list for you to
check, and then runs the same preview and results.

Chapter 13 has both in full.

## Housekeeping

These are on the issue's context menu, under **More** when the menu is long:

- **Edit Title...** opens the sheet at the title.
- **Lock or Unlock Conversation...** opens the sheet at the **Conversation**
  page, where **Locked** is a check box. Only people with write access can
  comment on a locked issue. Locking needs write access.
- **Pin or Unpin Issue** pins the issue to the top of the repository's issue
  list, or takes it off. A repository can pin up to three.
- **Transfer Issue...** moves the issue to another repository with the same
  owner. QUILL asks for the repository as `owner/name`, then warns that labels
  and milestones that do not exist there are dropped, and that assignees who
  cannot be assigned there are removed. You hear "Moved #7 to" the repository
  and its new address.
- **Set Issue Type...** chooses the issue's type, such as Bug or Feature, from
  the types the organization has set up. A repository with none says so.
- **Reorder Sub-issues...** opens a list of the issue's sub-issues in order,
  **Sub-issues, in order:**. Select one and press **Move Up** (`Alt+U`) or
  **Move Down** (`Alt+D`). You hear its new place, such as "#12 is now 2 of
  5.", read back from GitHub. Enter opens the selected sub-issue in your
  browser.

## Issue fields

An organization can give every issue extra values of its own, such as
Priority, Points or Due date. On your own account you can make them for your
own repositories, under **People > My Issue Fields**; an organization's are
under its **Issue Fields**. Chapter 12 has both lists.

**Issue Fields...**, on an issue's context menu, lists each field with this
issue's value: "Priority (single choice, field 1): High", or "Due (date,
field 2): not set". A field you may not see, or one of a kind QUILL does not
know yet, says so rather than looking empty.

Choose a field to change it. A single choice offers its choices and **Clear
it**. Any other field with a value asks **Change it...** or **Clear it**
first, so pressing Cancel never clears anything; then QUILL asks for the value
the way its kind needs: a number, a date as year-month-day (2026-12-31), or
text. Only that field is sent, so a value someone else set on another field is
kept. You hear "Points is now 5 on #4."

### Issue types and fields in the lists

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
  Fields** page after Organize: first how many fields the owner defines and
  which are not set or set to nothing, then one field each, of its own kind.
  A date (typed as 2026-12-31), a number, a single choice (a list, with
  "(none)" to clear it) and text are changed right there; leaving one empty
  clears it. Saving sends the same request **Issue Fields...** on the row
  sends, then reads the issue again and says only what GitHub kept. Several
  choices, and field types QUILL does not know yet, stay read only. Select
  several issues and press `Alt+Enter` to set a field on all of them: a field
  whose values differ shows Mixed, and each issue is changed and checked on
  its own, with a result for each. Changing a field needs triage access.

The states never sound alike, so a missing permission never sounds like an
empty field:

| State | In a cell | In details and Properties |
| --- | --- | --- |
| A value | Priority: High | High |
| Set to nothing | Priority: empty | set to nothing |
| Not set | Priority: not set | not set |
| Hidden from you | hidden from you | hidden from you |
| A kind QUILL does not change yet | Odd: shimmer (read only) | shimmer (read only) |
| The read failed | unreadable, and why | could not be read, and why |

## Deleting an issue

Closing an issue keeps it, its comments and its history, and that is almost
always what you want. A repository's admins can also delete an issue for
good, such as one made by mistake or full of spam: choose **Delete
Issue...**. QUILL explains that GitHub cannot bring it back, and asks you to
type the issue's number; anything else deletes nothing. A pull request cannot
be deleted this way.

## Branches and task lists

**Create Branch for This Issue...** makes a branch for the work, from the
default branch, and links it to the issue, so GitHub lists it under the
issue's Development. QUILL suggests a name the way GitHub does, such as
`7-fix-the-parser`; change it if you like. A name git would refuse, or a
branch that already exists, is refused before anything is sent. Afterwards
you hear how to start: `git fetch`, then `git switch` and the name. The
issue's Properties sheet lists its **Linked branches** on the Relationships
page, beside the pull requests that will close it.

**Unlink Branch...** lists the branches linked to the issue and takes the one
you choose off its Development, after asking. The branch itself stays, with
its commits; only the link goes. The **Linked branches** list on the
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

## From an issue to a pull request

**Start Pull Request for This Issue...** on an open issue does the first steps
of the work at once. It asks for a branch name, starting with the one GitHub
would suggest (`42-fix-the-parser`), then says what it will do and asks
first:

1. Make the branch from the default branch, linked to the issue as its
   Development. A branch of that name that already exists is used as it is.
2. Add one empty commit, "Start work on #42", when the branch has no commit of
   its own, because GitHub will not open a pull request with nothing to
   compare.
3. Open a draft pull request whose text begins `Closes #42`, so merging it
   closes the issue. A repository without draft pull requests gets an
   ordinary one, and the sentence afterwards says so.

To work on it, fetch the branch and switch to it, or use Start in Local
Worktree, below.

**Related...** on an issue lists the pull requests that close it, what
mentioned it, and what its text links to (Chapter 8).

**Draft Task Breakdown with AI...** sends the issue's title and text to the AI
connection you chose in QUILL, and opens what comes back in the editor as a
draft of small, ordered tasks. The draft is headed as one, cites the issue's
link, and says when part of the text had to be left out. Nothing is posted:
copy what you keep into a comment or into sub-issues yourself.

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
  related link, after asking. Both issues stay; only the link goes, and you
  can add it again. A parent row and a "Blocking" row are the other end of
  another issue's link, so you change them from that issue.

After each change QUILL reads the relationships back from GitHub and says
what happened, such as "#41 is now blocked by #38." **Reorder Sub-issues...**
changes their order.

## Projects

GitHub Projects are boards that track issues and pull requests across one or
more repositories, with fields of their own such as Status, Priority or
Iteration. `Ctrl+6` goes to **Projects**, the ones your account can see, and
a repository's own are under its **Projects** place (`Ctrl+Shift+7`).

**Projects...** on an issue opens its sheet at the **Projects** page: each
open Project it could be in, a check box, checked when it is. Clearing one
takes the issue out of that Project, with its field values. **New
Project...** beside the list makes one.

A Project's own row has these commands on its context menu:

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

Under **More** are the board's views, fields, drafts, items, status updates,
workflows and sharing, each with a command of its own; Chapter 12 lists them.

**Repository > Repository Actions...** (`Ctrl+Shift+G`) has **Projects...**,
a window for reading and changing a board's items and their fields, with
**Next Unblocked** for the next item nothing is waiting on.

All of these need your GitHub sign-in to include the **project** scope.

## Starting an issue in its own folder

When you start work on an issue, you usually want a new branch, kept apart
from whatever else you have going. **Start in Local Worktree...**
(`Ctrl+Shift+T`) on an issue or pull request does that with Git's worktrees: a
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

**In QUILL Lite**, this command is greyed, because it needs QUILL's local Git.

## A walk-through: one issue, from open to closed

This uses the practice repository. If you do not have it yet, choose **Help >
Practice on GitHub...** (`Ctrl+Alt+P`) in the Workbench; it makes a private
repository called `quill-practice` with three issues to work on.

1. In the Workbench, go to `quill-practice`, then press `Ctrl+Shift+1`. You
   hear "Issues", and the list holds the three practice issues.
2. Arrow to the issue about the greeting's typo and press `Enter`. You are in
   the details pane, reading its description. Press `Shift+Tab` to go back to
   the list.
3. Press `Shift+F10` and choose **Labels...**. The Properties sheet opens on
   the Organize page, at Labels. Check **practice: bug** with Space, and press
   Enter. You hear what GitHub kept.
4. Press `Ctrl+Shift+M`. The comment window opens. Type "I will fix this
   today." and press `Ctrl+Enter`. You hear "Comment posted on" and the
   issue's number.
5. Press `Delete`. QUILL asks why you are closing it. Choose **Completed**.
   You hear "Closed", the number, "as completed."
6. Changed your mind? Arrow to the issue again, which **View > Open or
   Closed > All** shows, and choose **Close or Reopen...**. It asks, then
   reopens it.

That is the whole life of most issues: a label, a word, and closing it.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has these lessons on the
practice repository, each saying what to press and what you should hear:

- **Label, comment on and close an issue**: the walk-through above.
- **Build an issue form**: a form in the repository's Templates.
- **File an issue with a form**: filling the form you built.
- **Plan a milestone**: make one, put an issue in it, and give it a due date.
- **Organize a project board**: a Project with the practice issues on it.

# Chapter 5: Pull requests and review

## What this chapter covers

Somebody has asked you to review their change, or you want to get your own
change merged. On the website that means a long page of code with comments
wedged between the lines, and a merge box that speaks in colours and icons.

In this chapter you find the pull requests that need you, read one as an
outline you can walk, read its changes line by line, comment on a line or a
range, suggest a change, and send your review. Then you find out whether it
can merge, and why not, and merge it, one or several at a time.

By the end you will know how to review a pull request from start to finish
without the website, and how to get one merged safely.

Reading works signed out. Everything that writes needs a signed-in account.
Merging, re-running and the other changes also need your account's Workbench
level to allow them: Organize or Full. Chapter 13 explains the levels.

**In QUILL Lite**, which works as a guest, you can read every part of a
review. The commands that write say they need a signed-in account.

## Finding the pull requests that need you

Pull requests live in three places in the GitHub Workbench's tree:

- **Needs My Attention > Review Requests** lists every pull request someone
  has asked you to review, in any repository. It holds two kinds: those that
  ask you by name, and those that ask a team you belong to. A team's row ends
  in "team review request", so you know someone else on the team may take
  it. The pull request's own sheet names the team under Team reviewers.
  `Ctrl+1` goes to Inbox, just above it, which marks them the same way.
- **Needs My Attention > My Open Pull Requests** lists the ones you opened
  that are still open.
- A repository's **Pull Requests**, `Ctrl+Shift+2`, lists that repository's
  open ones. Its **Merge Queue** lists the default branch's merge queue in
  order, when the repository has one.

**View > Quick Filters** narrows a list of pull requests without typing:
Review Requested from Me, Reviewed by Me, Drafts, Has Conflicts and Checks
Failing are there, with the others. Each is checked while it is on, and they
combine. Chapter 13 covers filtering in full.

## Opening a pull request

Select a pull request and press Enter. That is **Review...**, the first row of
its context menu, and it opens the review window described below. A pull
request link pasted into **File > Open GitHub Address...** (`Ctrl+L`) goes
straight to it, and so does a pull request in your notifications.

**File Differences...** (`Ctrl+Shift+D`, on the Item menu) skips the outline
and opens the changed files on their own. More on that below.

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

`Shift+F10` on a file has:

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

Enter on a file in the outline, **Open File Differences** on a file's or
thread's context menu, or **File Differences...** (`Ctrl+Shift+D`) on a pull
request in the Workbench, opens the diff window, **PR #42 diff:** and the
title.

- **Changed files**: one row per file, "modified: src/status.py +12 -3".
  Select one to hear its changes.
- **Differences** reads the changes through the same engine as QUILL's Compare
  Documents: "Difference 2 of 5. Text changed at line 41", with both sides
  named and the changed words described. `F8` and `Shift+F8` move to the next
  and previous difference and say which one it is.
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
- **Changed Lines Only** (`Alt+H`) leaves the unchanged lines around each
  change out of the patch list, so the arrows go from change to change. The
  hunk headings stay, so each change still says where it is. You hear how
  many changed lines there are and how many unchanged ones were left out;
  uncheck it to see them again.
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
- **Explain Selected Change with AI**, beside **Close**, sends the selected
  file's change to the AI connection you chose in QUILL, after asking, and
  says what it does. The answer names the file and the commit it read. It is
  greyed until you select a file, and when no AI is set up.

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

Escape closes the diff and takes you back to where you opened it.

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

GitHub never lets you approve your own pull request. If you keep a second
account for that, see [Approving with another of your
accounts](#approving-with-another-of-your-accounts) below.

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

`Ctrl+R` replies only here, in the review window. In the Workbench it
refreshes the list.

## Reviews already sent

**Reviews...**, on a pull request's context menu in the Workbench (under
More), lists every review the pull request has had, with who sent it and its
verdict. Choose one, then what to do with it: read its comments, and change
or delete one of them; change its summary; dismiss it, when GitHub lets you;
or, for a review still pending, submit it or delete it. Anything that changes
a review asks first.

**Re-request Review...** asks people who have already reviewed to look
again, after you have pushed changes. Give their GitHub names, separated by
commas.

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

**Request Copilot Review**, on the pull request's context menu in the review
window (`Shift+F10` on the outline), asks Copilot code review to review the
pull request. It has no button or access key. You hear "Copilot review
requested on pull request #4." only when GitHub lists Copilot among the
reviewers. GitHub sometimes accepts the request and leaves Copilot off the
list, which is how it answers an account or a repository without Copilot code
review; QUILL says that plainly rather than telling you a request went in
when it did not. Copilot's review arrives as review comments, like anyone
else's, and the outline shows them after a refresh.

In the Workbench, **Ask Copilot to Review**, on a pull request's context menu
under More, does the same from the list. The same menu has **Agent Merge**,
**Turn On Agent Merge** and **Turn Off Agent Merge...**, which let Copilot's
cloud agent merge the pull request once its checks and reviews allow. These
need a Copilot plan with the cloud agent; Chapter 12 has the rest of
Copilot's commands.

### Merging

Merging is in the Workbench, not the review window, because it is the one
thing here that changes the base branch for everyone. Select the pull request
and press `Ctrl+Shift+Enter`, or choose **Merge...** from its context menu or
the Item menu.

QUILL first asks GitHub whether the pull request can merge. If it cannot, you
hear why, the same answer as **Why Can't I Merge?** below, and nothing else
happens. If it can, QUILL asks how to merge: Squash and merge, Merge commit,
or Rebase, offering only the ways the repository allows. Then it asks you to
type the pull request's number to confirm, not just press Yes, and says what
will happen: that it merges into the base branch, as of the commit QUILL
checked, for example "as of commit 3f9a2c1", and that this changes the branch
for everyone and cannot be undone from QUILL. You hear "Merged #42" and the
start of the new commit.

That commit is the one that merges. If somebody pushes to the pull request
between the check and your typing the number, GitHub refuses, nothing is
merged, and QUILL says so: "Somebody pushed to #42 after commit 3f9a2c1 was
checked, so nothing was merged." Check again and you are merging what you
have actually read.

When the base branch merges only through a merge queue, Merge... does not try
to go around it: you hear that the pull request can join the queue, and **Add
to or Remove from Merge Queue...** puts it there.

A merge cannot be taken back with `Ctrl+Z`. To undo one, use **Revert Pull
Request...**, below.

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
- A rule on the base branch blocks it for another reason: the rule is
  named, as below.

Each blocking rule is said by name, so you know whom to ask or what to fix.
QUILL reads the rules that apply to the base branch (its rulesets, and its
branch protection when you can read it) and says:

- which required check failed, has not finished, or has not reported on
  the commit, and which ruleset wants it: "Check build, which the ruleset
  "Protect main" requires, failed. Re-run or fix it."
- how many approving reviews a rule wants, and how many there are;
- when a rule wants a code owner's review, which line of the CODEOWNERS file
  is waiting, with its pattern, who could approve, and a changed file it
  covers: "none from @docs-team has approved: .github/CODEOWNERS line 3,
  /docs/, owns 2 changed files, such as docs/guide.md." A team counts as
  approved when one of its members has;
- which rule makes the branch merge only through its merge queue.

What QUILL could not read, such as branch protection without admin access,
is said at the end, so a missing permission never sounds like "no rule".
GitHub's answer is the one that counts: naming the rules never turns "can
merge" into "cannot". **Merge Selected...** names the rules the same way in
its preview, for each pull request that will not merge.

It also says when auto-merge is on, and its place when the pull request is
in the merge queue. The answer is always for one commit, which it names, so
you know a push after you asked may change it.

### Watch Readiness

**Watch Readiness**, on an open pull request's context menu in the
Workbench, adds a watch (under Watches, `Ctrl+7`) that tells you once when
the pull request becomes able to merge, and once when it stops, naming the
rule that blocks it then. It is checked with your other watches, on the same
interval, and said the same way. The first check only learns where it
stands, and while GitHub is still working out whether it can merge, nothing
is said. You can also add one from Watches with **Add Watch...**, choosing "A
pull request becomes able to merge, or stops being able to". The watch is
kept on this computer only; nothing is changed on GitHub.

### Auto-merge and the merge queue

On a pull request's row in the Workbench, **Auto-Merge...** turns auto-merge
on, after telling you what it would be waiting for and asking how to merge,
or offers to turn it off when it is on. A pull request that can merge now has
nothing to wait for, and QUILL says so rather than switching it on. **Add to
or Remove from Merge Queue...** adds the pull request to its branch's queue,
naming the commit, or offers to take it out when it is in, saying its place.
The repository's **Merge Queue** place lists the whole queue in order.

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

**Check Merge Policy**, in the review window, reads the rules on the base
branch: required reviews, required checks, code owners and the merge queue. It
adds them to the review summary, and from then on the readiness and the
combined check status count only the checks that are required ("3 of 4
required checks pass"). The rules are read for the current version of the
pull request; refresh the review after new commits to check again. GitHub
always has the last word, and QUILL says so.

### A check that needs another run

On a check in the outline, the context menu has **Re-request Check...**,
which asks GitHub to run that check again. Some checks are older-style commit
statuses rather than check runs, and those cannot be re-run from outside;
QUILL says so. Chapter 6 covers checks and workflow runs in full.

### Approving with another of your accounts

GitHub never lets the author approve their own pull request. If you keep two
accounts in QUILL, say a personal one and one for the project, **Account >
Roles and Access > Act As Another Account...** sends one action as the other
account. Select the pull request first. QUILL lists your other signed-in
accounts, then the actions that fit: **Approve this pull request**, **Comment
on it**, or **Close or reopen it**. It checks whose token it really is before
sending, names the account in the question, and names it again in the result:
"Approved pull request #42 in owner/name as jeff-project." The other account's
own Workbench level applies, so a Read Only account sends nothing.

**Compare Accounts...**, on the same submenu, shows two of your accounts side
by side on this repository: each one's role, as GitHub answered that account.
Chapter 13 has both in full.

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
   **Resolve Conflicts** walks each one, the same window as QUILL's
   **Tools > Git and GitHub > Local Git > Resolve Conflicts...**: each conflict in turn, with your version and theirs
   read out, and a choice for each.

When the files are resolved, commit in that folder and push the branch to the
pull request's branch; QUILL says the exact command, for example
`git push origin pr-42-conflicts:fix-parser`. The new folder stays until you
remove it with **Tools > Git and GitHub > Local Git > Worktrees...**.

A pull request from a fork is the exception: its branch lives in the fork,
not in the repository, so QUILL says so and leaves it to a checkout of the
fork, or to its author. If the base merges with no conflicts, QUILL says that
instead, and the merge is left staged, not committed.

This one is QUILL's alone. **In QUILL Lite**, which has no Local Git, the row
is greyed and says why.

## Dependabot's pull requests

A pull request Dependabot opened, to update a package, has **Dependabot
Commands...** on its context menu. It lists the commands Dependabot answers in
a comment, such as rebase, recreate, merge, or ignore this version, each with
what it does. Choosing one posts it as a comment, after asking, and Dependabot
does the rest.

## Drafts, github.dev and Related

A few more commands on a pull request's row:

- **Draft Description with AI...** and **Draft Reviewer Brief with AI...**
  send the pull request's changed files and their patches, at its head
  commit, to the AI connection you chose in QUILL, and open the draft in the
  editor. The draft is headed as one, lists its sources (each file at that
  commit, and the commit itself), and says when part of the change was left
  out because it was too long. It never claims tests ran unless the evidence
  says so. QUILL posts nothing: paste what you keep into the description or
  a comment.
- **Draft Release Notes with AI...** on selected issues and pull requests
  drafts notes from those rows only. **Draft Release Notes...** on a release
  drafts them without AI.
- Without an AI connection these rows are greyed, and `Shift+F1` says why.
- **Open in github.dev** opens the pull request in GitHub's free web editor,
  in your browser; nothing is created and nothing costs money.
- **Related...** lists the issues it closes, what mentioned it, and what its
  text links to (Chapter 8).

## Writing a new pull request

In a repository's **Pull Requests**, press `Ctrl+N`. To start from a branch,
select it in Branches, press `Ctrl+Shift+N` and choose Pull Request. The New
Pull Request window has Merge into, Merge from, Title, Description and a
Create as a draft check box. The title and description start from the
commits you are proposing, a branch that already has an open pull request is
taken to that one instead of making a second, and Cancel keeps your text for
the session. [Chapter 12](#chapter-12-the-github-workbench-place-by-place) walks through it.

On an issue, **Start Pull Request for This Issue...** makes a branch linked
to the issue and a draft pull request that closes it, in one step. Chapter 4
has it.

## A walk-through: reviewing and merging the practice pull request

The practice repository has a branch, `fix-greeting`, with a pull request
waiting for you. Make it first with **Help > Practice on GitHub...**
(`Ctrl+Alt+P`) if you have not. Nothing here matters if it goes wrong.

1. In the Workbench, press `Ctrl+L`, type `quill-practice` and press Enter.
   You arrive on the repository's own place in the tree.
2. Press `Ctrl+Shift+2` for its Pull Requests, then F6 to the list. You hear
   the pull request that fixes the greeting.
3. Press Enter. The review window opens, and you hear "Review loaded for pull
   request" and the one sentence.
4. Arrow down to **Changed files**, press Right Arrow, and press Enter on the
   file. The diff opens.
5. Press `Alt+P` for the patch lines and `Alt+H` to check Changed Lines Only.
   Arrow down: an added line and a removed line each have their own sound.
   `F8` jumps to the next change.
6. Press Escape to close the diff, and Escape again to close the review.
7. Back on the pull request in the Workbench, press `Shift+F10` and choose
   **Why Can't I Merge?**. You hear that it can merge into main, as of a
   commit it names. The practice run fails on purpose, but it is not a
   required check, so it does not stop the merge.
8. Press `Ctrl+Shift+Enter`. Choose Squash and merge, type the pull request's
   number, and press Enter. You hear "Merged" and the new commit.

You made the pull request yourself, so GitHub would not have let you approve
it. On someone else's, Compose Review (`Alt+C`) in step 6 is where you send
Approve.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has **Review and merge a pull request**, on
the practice repository: list the pull requests, read the change, ask whether
it can merge, and merge it. Each step says what to press and what you should
hear. **Try a command without sending it** shows Dry Run, which lets you try
Merge... and see what it would send without sending it.

# Chapter 6: Actions and checks

## What this chapter covers

GitHub Actions runs a repository's builds and tests. When a run fails, the
website gives you a page of collapsed boxes and a log thousands of lines long.
You want the line that broke, and you want it quickly.

In this chapter you find a repository's runs, get from "the build failed" to
the failing step in one key, read jobs and logs, and rerun, cancel, delete and
approve runs. Then you start, turn on and off, and edit workflows, approve
deployments that are waiting, and look after artifacts, caches, runners and
the names of a repository's secrets.

By the end you will know how to find out why any run failed, and how to do
something about it, without opening a browser.

Reading runs and logs works signed out for a public repository. Anything that
changes a run needs a signed-in account, and a Workbench level that allows
it: Organize for rerunning, cancelling and starting runs, and Full for
approving deployments and fork runs and for deleting. Chapter 13 explains the
levels.

## Finding a repository's runs

Every repository in the GitHub Workbench's tree has an **Actions** place.
`Ctrl+Shift+4` goes straight to its **Runs**. Under Actions are:

- **Runs**: each time a workflow ran, newest first. A row reads the
  workflow's name, its status ("completed", "in_progress", "queued"), its
  result ("success", "failure", "cancelled"), the branch, what started it
  ("push", "pull_request", "schedule") and the run number. These are GitHub's
  own words, as GitHub sends them. The details pane gives the same in full,
  one line each, with when it started and its link.
- **Workflows**: the repository's workflow definitions, with whether each is
  active, and its file. Enter on a workflow lists its runs.
- **Artifacts**: files the runs kept, such as builds and test reports.
- **Caches**: files Actions kept between runs.
- **Runners**: the repository's own machines, for its administrators.

**Across Repositories > Workflow Runs** (`Ctrl+0`) lists the runs of every
repository in your set in one list, newest first, for "which runs failed
anywhere?". Chapter 12 has Across Repositories.

## What Failed

This is the command to learn first. Select a failed run in **Runs** and press
`Ctrl+Shift+W`, or choose **What Failed...** from its context menu or the
Item menu.

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

For the whole picture, press Enter on a run, or choose **Jobs and Logs** from
its context menu. The window **Jobs for** and the run has, in Tab order:

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

On a run's context menu, under More, three more read the logs another way:
**Read a Step's Log...** reads one step at a time, **Download Logs...** saves
every log of the run as a zip file, and **Earlier Attempts...** says how an
earlier attempt went, or reads its logs.

### Following a job while it runs

GitHub shows a running job's log only on its own web page; the log QUILL can
load arrives when the job has finished. What QUILL can follow while it runs is
its steps. Select a running job and check **Follow This Job** (`Alt+W`): you
hear where it is, for example "build: On step 3 of 9, Run tests; 2 done", and
from then on, every few seconds, each step as it starts and as it finishes,
"Step 3, Run tests, failed.", without your having to look. When the job ends
you hear how, "build failed. Load Log reads its whole log.", and following
stops by itself. Uncheck the box to stop sooner.

At any moment in this window, `Alt+8` says how far along the selected job is:
the step it is on, how many are done, and any that have failed so far.

To hear when a whole run finishes without keeping a window open, add a watch
under **Watches** (`Ctrl+7`). Chapter 12 has Watches.

## Doing something about a run

On a run in **Runs**, the context menu and the Item menu hold the commands
that act on it. Each one asks first, and the default answer is No.

- **Re-run Failed Jobs Only** (`Ctrl+Shift+F5`) reruns just the jobs that
  failed, which is usually what you want after fixing a flaky test. You hear
  "GitHub started a re-run of the failed jobs of" and the run. Pressing it
  twice never starts two reruns. On a run where nothing failed, GitHub
  refuses, and QUILL passes on its reason.
- **Re-run Workflow** reruns every job in the run. You hear "Re-running" and
  the workflow.
- **Re-run One Job...** reruns a single job, with debug logs if you ask for
  them.
- **Cancel Run...** stops a run that is still going. GitHub only promises to
  stop it, so QUILL says "GitHub accepted the cancel request and is stopping"
  the run. Refresh (`F5`) to check. **Force Cancel...**, under More, is for a
  run that Cancel has not stopped.
- **Delete Run...** deletes the run for good. The question names the run,
  its branch and its result, and says its logs and artifacts go with it and
  that this cannot be undone. **Delete Logs...** deletes only its logs; the
  run stays.
- **Approve Run from a Fork...** lets a run from someone else's fork go ahead.
  GitHub holds these until a maintainer approves them, because the code in
  them has not been reviewed. The question says so: approve only code you
  have read, since it runs with this repository's permissions. You hear
  "GitHub approved" the run, and that it will start shortly.
- **Review Pending Deployments...** and **Approvals**, below.
- **Combined Check Status**, below.

When GitHub refuses an Actions request, QUILL says why in words. It might
need write access to Actions, or a log or artifact may have gone after the
repository's retention period. This applies to turning a workflow on or
off, starting or re-running it, reading a job's log and downloading an
artifact.

## Combined check status

**Combined Check Status** reads every check on the run's commit and says them
in one sentence: "Commit 1a2b3c4: 3 of 4 checks pass; failing: test." If some
are still going it adds how many, and it names any that have not reported
yet. It reads only, so it works signed out.

The review window has the same command (Chapter 5). There, after
**Check Merge Policy**, it counts only the checks the branch requires.

A commit's own row, under Code, has two more: **Check Run Details...**, a
check's summary and every annotation, and **Re-run a Check Suite...**.

## Re-requesting a check

A check that failed for reasons outside the code, a network blip, say, can be
asked to run again on its own. In **Jobs and Logs**, select the job and press
**Re-request Check** (`Alt+C`). QUILL asks first, then says "GitHub queued the
check for" and the job "to run again." The review window's Checks branch has
**Re-request Check...** on each check's context menu too.

## Starting a workflow

### Running a workflow by hand

Some workflows are set up to be started by hand. Choose **Run Workflow on
Branch...** (`Ctrl+Shift+R`) from the Repository menu, or from a workflow's
context menu in **Workflows**. It runs the workflow you selected, in that
repository. QUILL asks for the branch or tag, starting with `main`, then asks
"Run the workflow CI on main in owner/name?", and you hear that GitHub
accepted it and that its run appears in Runs shortly. QUILL asks only for the
branch, not for a workflow's other inputs; a workflow that needs those before
it can start has to be run from GitHub's own page.

It works the same in QUILL and QUILL Lite. QUILL's editor also has
**Dispatch Workflow...**, in the Workbench's **Repository Actions...**
(`Ctrl+Shift+G`) and in **Tools > Git and GitHub > GitHub**, which asks for the
repository and the workflow's file name as well.

### Starting workflows from outside

A workflow can start on `repository_dispatch`, an event sent on purpose rather
than by a push. **Send Repository Dispatch...**, on a repository's context
menu, sends one: give the event's name, as the workflow's `types` list says,
such as `deploy`, and optionally extra values as JSON, such as
`{"env": "test"}`, which the workflow reads as `github.event.client_payload`.
You hear "Sent deploy." and the run appears under Actions.

## Looking after workflows

### Turning a workflow on or off

A workflow that is turned off runs on nothing: not on a push, not on a
schedule, not even Run Workflow. GitHub turns off a scheduled workflow by
itself after sixty days without activity in the repository, which is a common
reason a nightly job quietly stopped. **Turn Workflow On or Off...** on a
workflow's context menu says its state in words first, "on", "turned off" or
"turned off by GitHub after 60 days without activity", and asks before
changing it. You hear "Turned on" and its name, or "Turned off". The
workflow's Properties sheet (`Alt+Enter`) has the same switch as its Enabled
field.

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

Chapter 7 has Dependabot's configuration, code owners, and comparing a
repository's configuration with another's.

## Deployments and environments

### Deployments waiting for approval

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

**Approvals**, on the run's context menu, says who approved or rejected its
deployments afterwards.

### An environment's rules

A repository's environments are listed under **Settings > Environments**.
`Ctrl+N` there makes one: it asks for the name, whether any branch or only
protected branches may deploy to it, and how many minutes each deployment
waits (0 for none). An environment that already has the name is never
replaced; QUILL says so instead. Reviewers and a chosen list of branches are
set on its sheet afterwards. An environment's row has these on its context
menu, beside **Secrets...** and **Variables...**, which are that
environment's own:

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
- **Pin Environment**, **Unpin Environment** and **Move Environment...**,
  under More, choose the order GitHub shows environments in.

An environment's **Properties...** (`Alt+Enter`) puts its protection on one
sheet: the required reviewers, prevent self-review, the wait timer and whether
administrators may bypass, with the custom protection rules (the apps) listed
under them; which branches and tags may deploy, with the chosen ones listed;
how many secrets and variables it has, with their names; and its newest
deployments. The protection, the wait timer and the branch choice can be
changed there; the lists are read only, and the commands above change them.

To compare an environment's rules across many repositories, make them the
same, or add an environment to the repositories that lack it, use **Across
Repositories > Actions by Name > Environments by Name** (Chapter 12).

### Deleting a deployment

The repository's **Deployments and Environments** place lists where the code
was deployed. A deployment's context menu has **Delete Deployment...**, which
removes it from the history after asking. GitHub deletes only an inactive
deployment; a newer deployment to the same environment makes the older one
inactive, and QUILL says so if you try too early.

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

The repository's **Actions > Artifacts** place lists every run's artifacts
together.

## Caches

Workflows keep caches to run faster: downloaded packages, build outputs. They
are listed in the repository's **Actions > Caches**. The first row sums them
up, such as "12 Actions caches in community-access/quill" and how much space
the listed ones use. Each row after it reads the cache's key, size, branch
and when it was last used, newest first.

A stale or broken cache can make a build fail in strange ways. On a cache's
row, **Delete Cache...**, or the Delete key, removes it after asking.
Workflows build it again the next time they need it.

## Self-hosted runners

A runner is the machine a workflow's jobs run on. GitHub lends its own, and a
repository can bring its own as well, called self-hosted: a lab machine with a
graphics card, a Mac for signing, a build server inside a company network.
When those jobs sit waiting forever, the first question is whether the
machine is even there.

The repository's **Actions > Runners** lists them. Each row reads the
runner's name, its state and its system, such as "lab-1: online, busy, Linux"
or "old-mac: offline, macOS". "Online, idle" means it is there and waiting for
work; "online, busy" means it is running a job now; "offline" means GitHub has
not heard from it, which is why jobs that ask for it never start. The details
pane adds the runner's labels, the words a workflow's `runs-on:` line asks
for, so you can check that the job and the machine agree. **Open on GitHub**
opens the repository's runner settings page.

GitHub shows runners only to the repository's administrators. Anyone else
hears "GitHub shows owner/name's runners only to its administrators." in the
place's note, rather than an empty list that looks like there are none. A
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
- **Removal Commands...** puts the commands that unregister a runner on its
  own machine on the clipboard, again without saying or showing the token.

An organization's runners, runner groups and larger runners are under the
organization in the tree. Chapter 12 lists the commands on them, such as
**Just-in-Time Runner...** and **Is a Runner Version Retiring?...**.

## Secret and variable names

A repository's **Settings > Secret and Variable Names** lists the names of the
repository's secrets and variables, and those of each environment, with when
each was last updated: "Repository secret: DEPLOY_KEY, updated 2026-10-02". It
answers "is that secret set?" without anyone needing to see it.

The names are all you get. QUILL never reads a secret's or variable's value,
and it drops any value GitHub sends before it reaches the screen. Reading the
names needs a signed-in account with access to the repository's settings.

To set a secret's value, or add, change and delete variables, use
**Settings > Actions Secrets** and **Actions Variables**. Chapter 8 covers
secrets, and how a value is sealed on your computer before it is sent.

## A walk-through: reading the practice repository's failed run

The practice repository has a workflow that fails on purpose. Make it first
with **Help > Practice on GitHub...** (`Ctrl+Alt+P`) if you have not.

1. In the Workbench, press `Ctrl+L`, type `quill-practice` and press Enter.
2. Press `Ctrl+Shift+4` for its Runs, then F6 to the list. You hear a row
   starting "failure, Practice checks".
3. Press `Ctrl+Shift+W`. The What Failed window opens, and you hear "What
   failed is ready." and the first line. Arrow down: the failing step is
   called Fail on purpose, and its last log lines follow.
4. Press Escape to close it.
5. Press Enter on the same run. The jobs window opens. Arrow to the failed
   job and press `Alt+L` to load its whole log. Press Escape when you are
   done.
6. Press `Ctrl+Shift+F5` and answer Yes. You hear that GitHub started a re-run
   of the failed jobs. It fails again, which is the point here; in a real
   repository you would fix it first.
7. Press `F5` after a minute to refresh the list and hear the new attempt.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has **Read a failed run**, on the practice
repository: list the runs, read what failed, and run only the failure again.
**Try a command without sending it** shows Dry Run, so you can try Delete
Run... and hear what it would send without sending it.

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
line by line, each line marked in your Line marks style. `F8` and `Shift+F8`
move to the next and previous change. Files that are the same, or only here,
are counted and kept.
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

# Chapter 8: Discussions and security

## What this chapter covers

You are here for one of two kinds of conversation that are not issues.
Discussions are a repository's forum: questions, ideas and announcements,
with threaded replies, answers and polls. Security alerts are GitHub telling a
repository about a vulnerable package, a weakness in the code, or a secret
committed by mistake.

You will read and take part in discussions, vote in a poll, mark an answer
and start a discussion of your own. Then you will find and triage security
alerts, let a blocked secret through, review what a pull request does to your
dependencies, read an organization's security overview, report a
vulnerability privately, work on an advisory, set secrets safely, search
GitHub's Advisory Database, and save a software bill of materials.

By the end you will know where each lives in the Workbench, what each asks
before it sends anything, and why QUILL says "could not read" rather than
"none" when GitHub will not show you something.

Discussions and security alerts need a signed-in account. Published
advisories and the Advisory Database can be read signed out.

## Discussions

### Finding them

**Discussions** under a repository (`Ctrl+Shift+3`) lists them. Each row reads
the number, the title and the category, and whether it is answered: "#12 How
do I turn off the sounds? (Q&A; Answered by alice)". A discussion link pasted
into **Open GitHub Address...** (`Ctrl+L`) opens here too.

Under Discussions are two more places:

- **Pinned (spotlight)** lists the discussions pinned at the top of the
  repository's Discussions page, first to last in GitHub's order: "1. #12 How
  do I turn off the sounds? (Q&A; Answered by alice)". The details begin
  "Pinned 1 of 3, by alice." Enter opens the thread, and Vote... and
  Properties work as in the main list. If nothing is pinned, the list is empty
  and the status bar says so. GitHub's API reads pinned discussions but cannot
  pin, unpin or reorder one, so this place is read only, and each pinned
  discussion's details say so. To pin one, use **Open on GitHub**
  (`Shift+Enter`) and pin it on GitHub's own page.
- **Categories** lists the repository's discussion categories. Where GitHub
  gives sections, each section is a row, "Section: Q&A (3 categories)", and
  Enter opens it: its categories follow a first row, **All sections**, which
  comes back. GitHub's API does not yet say which section a category is in,
  so today the place lists every category in GitHub's order, and the status
  bar says why once. Each category reads its name, and ", question and
  answer" when a reply can be marked the answer. Enter on one goes to
  Discussions with the list narrowed to that category's name.

### Reading a thread

Press Enter on a discussion, or choose **Open Discussion Thread** from its
context menu. The window **Discussion #12:** and the repository has:

- **Thread** (`Alt+T`), a list. The first row is the discussion itself, then
  each comment followed by its replies: "Comment by bob, the answer, 2
  replies:" and its first line, then "Reply by alice:" and so on.
- **Text** (`Alt+X`), the selected row in full. Enter in the list takes you
  there.
- **Reply...** (`Alt+R`), **Mark as Answer...** (`Alt+M`), **Open on
  GitHub** (`Alt+O`), **Refresh** (`Alt+F`) and **Close**.

When it loads, the status line says who answered it, or "Not answered yet.",
and how many comments and replies there are. A category that does not take
answers says "This category does not take answers."

To keep the whole thread, **Read as Document...** (`Ctrl+Shift+I`) on the
discussion's row opens it as one document, a heading per post, in the editor,
or saves it as Markdown or HTML.

### Replying

**Reply...** (`Alt+R`) replies to the selected comment, or to the discussion
itself when the first row is selected. It opens the comment window, titled
with which: "Reply to bob's comment", with Insert Mention (bob first), Insert
Reference, Insert Emoji, Insert Saved Reply, Preview and the check before
posting. You hear "Posted your reply". A closed discussion takes no replies,
so the button is unavailable.

To change or remove a comment you may edit, use **Edit a Comment...** or
**Delete a Comment...** on the discussion's row. Each asks which comment;
Delete asks again before it deletes.

### Marking the answer

In a question-and-answer category, the person who asked, or a maintainer, can
mark one comment as the answer. Select the comment in the thread and press
**Mark as Answer...** (`Alt+M`). QUILL asks first: "Mark bob's comment as the
answer to this discussion?" On the comment that is already the answer, the
button reads **Unmark Answer...**, still on `Alt+M`. Only a top-level comment
can be the answer, never a reply.

### Starting a discussion

In Discussions, press `Ctrl+N`. QUILL reads the repository's categories and
asks which; a category that takes answers says ", takes answers".

- When the category has its own discussion form, the form opens as a real
  form, a labelled control for each question, the same way an issue form
  does (Chapter 4).
- Otherwise the **New Discussion** window asks for **Title:** (`Alt+T`) and
  **Body:** (`Alt+B`).

**Start Discussion** shows what will be sent and asks once more. You hear
"Started discussion #14 in Q&A." If the category's form asks for labels,
the question says that starting a discussion this way does not add them.

### Polls as a table, and Vote...

When a discussion has a poll, its details end with the poll as a table: a
line with the question, the total and whether you may vote, "Poll: Which
sound pack?, 25 votes in all. You may vote: Vote...", then "Option, votes,
percent, your vote:" and a row for each option, "Classic, 15 votes, 60
percent, your vote: no". In the thread window the poll reads one option to a
line instead: "Classic: 15 votes, 60 percent". The discussion's
**Properties...** (`Alt+Enter`) has the same table on its **Poll** page,
under the question.

**Vote...** on the discussion's context menu, or **Add...** or **Change...**
under the Poll page's table, lists the options with their votes. Choose one
and you hear the outcome once, with the new count: "Voted for Classic. It has
16 votes now, of 26 in all." GitHub keeps a poll vote once it is cast: if you
have voted, Vote... says which option you chose, and **Remove** under the
table says a vote cannot be taken back. An account whose Workbench level is
Read Only (**Account > Roles and Access > Workbench Level for This
Account...**) cannot vote: Vote... says so and sends nothing.

### Upvoting, closing and deleting

A discussion's context menu also has:

- **Upvote** and **Remove Upvote**. An upvote helps a discussion rise in the
  list.
- **Close Discussion...**, which asks whether it is resolved, outdated or a
  duplicate, and **Reopen Discussion**. You hear "Closed the discussion." or
  "Reopened the discussion."
- **Delete Discussion...**, which deletes it with every comment in it after
  asking, because it cannot be undone. It needs admin access to the
  repository.

### From a discussion to an issue

When a discussion turns into work, **Create Issue from Discussion...** on its
row opens an issue for it. It reads the discussion first, then asks for the
issue's title, the discussion's to start with, and its text, which begins
with a link back to the discussion and quotes it; change either as you like.
Last it asks how, naming the repository and your account: open the issue and
comment on the discussion with the issue's link, or open the issue only.
Nothing is sent until you answer.

GitHub has no way, in its API, to turn an issue into a discussion or a
discussion into an issue; its web page does that, through **Open on GitHub**.

### What links to what: Related...

**Related...** on a discussion, an issue or a pull request lists the items
linked to it, each with its repository, its state and how it is linked: the
pull requests that close an issue, the issues a pull request closes, what
mentioned it, and the issues, pull requests and discussions its own text and
comments link to. Enter opens the selected one on GitHub, and Copy Link
copies its address. GitHub keeps no record of what links to a discussion, so
a discussion's list is only what the discussion and its replies link to, and
the list says so. When GitHub would not say what something is, the list says
that part is unread, never that there is none.

## Security alerts

### Finding them

**Security** under a repository (`Ctrl+Shift+8`) has the repository's
security places. **Alerts** brings three kinds of alert together:

- **Dependabot**: a package the repository uses has a known vulnerability.
- **Code scanning**: a tool found a likely weakness in the code.
- **Secret scanning**: something that looks like a password or key was
  committed.

Each row reads the kind, the severity, the package or file, and a summary:
"Dependabot: high: lodash, Prototype pollution".

Reading alerts needs a signed-in account that can see the repository's
security alerts. If yours cannot read one kind, or the repository has that
kind turned off, QUILL says that kind is unavailable rather than showing it
as having no alerts. A secret's value is never asked for, so it is never in
the list, the details, or a file you export with **Export List...**
(`Ctrl+Shift+X`).

In QUILL, **Tools > Git and GitHub > GitHub > Security Alerts...** opens the
Workbench at this place.

An alert's context menu has **Open**, **Dismiss or Reopen Alert...**,
**Copilot Autofix...**, **Show Every Place**, **Open on GitHub** and, on a
secret scanning alert, **Where It Was Found**.

### Dismissing an alert

Not every alert needs a fix. The package might be used only in tests, or the
finding might be wrong. **Dismiss or Reopen Alert...** on an open alert asks
three things:

1. **Why**, from GitHub's own reasons for that kind of alert:
   - Dependabot: "A fix has already been started", "This alert is
     inaccurate or incorrect", "No bandwidth to fix this", "Vulnerable code
     is not actually used", or "Risk is tolerable to this project".
   - Code scanning: "False positive", "Won't fix" or "Used in tests".
   - Secret scanning: "False positive", "Won't fix", "Revoked" or "Used in
     tests".
2. **A comment**, which you can leave empty. GitHub takes up to 280
   characters.
3. **Are you sure**: the question names the alert and the reason, and says
   everyone with access will see it as dismissed.

Cancel at any step and nothing is sent. QUILL reports the dismissal only when
GitHub sends the alert back in its new state.

An alert's Properties sheet (`Alt+Enter`) closes it the same way. Each kind
closes in its own words: a Dependabot or code scanning alert is dismissed, a
secret is resolved, and the sheet offers only that kind's reasons. A choice
that does not fit the kind is refused before anything is sent. GitHub marks
an alert fixed itself, so the sheet does not offer that.

### Reopening an alert

Dismissed and fixed alerts have their own place, **Security > Dismissed and
Resolved Alerts**. There, **Dismiss or Reopen Alert...** asks first, then
reopens the alert.

### Copilot Autofix

On a code scanning alert, **Copilot Autofix...** says whether Copilot has a
suggested fix. When it has none, QUILL offers to ask for one; when the fix is
ready, it offers to commit it to a branch you name, with a commit message you
may leave empty, so it can go through a pull request like any other change.
**Show Every Place** lists each file and line the alert was found in.

### Code scanning analyses

**Security > Code Scanning Analyses** lists the analyses GitHub has for the
repository, and **CodeQL Databases** the databases CodeQL built. `Ctrl+N` in
Code Scanning Analyses is **Upload SARIF File...**: results from a scanning
tool you ran yourself, for the branch you name.

### Letting a blocked secret through

When push protection is on, GitHub refuses a push that contains something
that looks like a password or key, and `git push` prints a placeholder id for
each one. If the secret is not real, is only used in tests, or you will fix it
later, select the repository and choose **Allow a Blocked Secret...** on its
context menu. QUILL asks for the placeholder id, then why, from GitHub's
three reasons: "It is not really a secret (a false positive)", "It is only
used in tests", or "It is real, and I will fix it later". It asks once more,
naming the repository, because the secret will stay in the repository's
history. Then you hear how long the allowance lasts, such as "GitHub will let
the GitHub personal access token through until 2026-11-19 at 18:00 UTC. Push
again now; GitHub keeps an alert for it."

**Secret Scanning History**, on a repository's context menu, says when
GitHub last scanned the repository for secrets, and how.

### Requests to dismiss or bypass

Some organizations want a security manager to approve each dismissal or push
protection bypass. GitHub offers those requests, and reviewing them, only on
GitHub Enterprise Cloud, which QUILL does not support; review them on
GitHub's own security page with **Open on GitHub**.

## Dependency review on a pull request

Before you merge a pull request, it helps to know what it does to your
dependencies. On a pull request's context menu, **Dependency Review**
compares the dependency graph at the pull request's base commit with its head
commit and shows the answer in a window to read. The first line is the
summary: "Added 3, removed 1. 1 added dependency has known vulnerabilities."
Each change follows, the vulnerable ones first: "Added: lodash 4.17.20 (npm,
package.json), licence MIT. Vulnerable: high, GHSA-p6mc-m468-83gw, Prototype
Pollution in lodash." A repository whose dependency graph is off says so in
words.

**Compare Dependencies...** on a repository does the same between any two
branches, tags or commits you type, and **Dependency Manifests** lists the
files GitHub reads the dependencies from.

## An organization's security overview

On an organization's context menu, **Security Overview** counts the open
alerts in every repository you can see there, worst first: "acme/web: 3
Dependabot (1 critical, 2 high); 1 code scanning (high); 2 secret scanning."
A totals line follows. If GitHub will not show you one kind, that kind is
named and the reason given, never counted as none: a missing permission is
not the same as no risk.

GitHub sends 100 alerts of a kind at a time, so the overview reads every page
of each list, however many there are. A small window shows that it is
reading, with Cancel (or `Escape`) to stop before the next page. Nothing is
said while it reads; at the end the report's last line says how much it read:
"Read every page: 351 alerts in 6 pages." If you stop it, the Workbench says
how many it had read and shows nothing, because part of a count would read as
the whole of it.

The organization's place also has the alerts themselves, every repository's
in one list: **Dependabot Alerts**, **Code Scanning Alerts**, **Secret
Scanning Alerts** and **Security Advisories**. Open a repository's own Alerts
to dismiss or resolve one. **Security Managers** lists the teams that may
manage security for every repository there.

## Security policy and reporting

Found a security hole in someone's project? Do not open a public issue: tell
the maintainers privately first. **Security > Policy** under the repository
says how. Its first row is the repository's security policy, "Security
policy: SECURITY.md. Enter opens it.", found in the root, `.github` or
`docs`, or says the repository has none. The second says whether private
vulnerability reporting is on. When it is, anyone signed in can report, as
below.

## Security advisories

A security advisory is a project's notice of a vulnerability: which package
and versions, how serious, and where it is fixed. Each has a GHSA (GitHub
Security Advisory) id, and often a CVE (Common Vulnerabilities and Exposures)
number too.

**Security > Advisories** lists a repository's advisories, one sentence each:
"GHSA-q4hm-2345-wxyz: high severity, draft: Path traversal in the importer."
Published advisories are listed for everyone; drafts and private reports only
for the repository's administrators and security managers, and anyone else
hears that rather than an empty list. The details say which packages and
versions are affected, which version fixes it, who is credited, and the full
description.

`Ctrl+N` in Advisories asks which you want:

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
  review"; on it, the same command offers **Accept it**, which makes it a
  draft advisory you and the reporter work on, or **Close it**. Publishing
  makes it public for good, puts it in GitHub's Advisory Database and alerts
  the projects that depend on the package, so QUILL asks you to type its GHSA
  id first.
- **Request CVE...** asks GitHub for a CVE number for a draft. GitHub reviews
  each request, so the number comes later.
- **Advisory Comments**, **Comment on Advisory...** and **Edit an Advisory
  Comment...** are a draft's private discussion, and **Make a Private Fork for
  the Fix** makes the temporary private fork GitHub offers for working on it.

## Secrets

A secret is a value a workflow, Dependabot, a codespace or the Copilot agent
uses but nobody reads again, such as a deploy token. They are lists in the
tree: under a repository's **Settings**, **Actions Secrets**, **Dependabot
Secrets**, **Codespaces Secrets** and **Copilot Agent Secrets**; the same four
under an organization's place; and an environment's **Secrets...** on its
row. **Settings > Organization Secrets Here** lists the organization's secrets
this repository may use. Each row says the secret's name and when it changed:
"Secret DEPLOY_TOKEN, changed 2026-11-02. Its value is never shown."

A secret's value only ever goes one way, to GitHub:

- `Ctrl+N` asks for its name, then its value in a password box. QUILL seals
  the value on this computer with that repository's, environment's or
  organization's own public key (a libsodium sealed box, as GitHub requires)
  and sends only the sealed form. The value is never read back, said, shown,
  logged or kept: once the call ends, it is gone.
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

To set one secret in many repositories at once, use **Secrets by Name** under
Across Repositories (Chapter 12).

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

Select a repository and choose **Repository > Export Software Bill of
Materials...** (`Ctrl+Alt+B`), or the same row in **Repository Actions...**
(`Ctrl+Shift+G`). A Save window offers a name such as `owner-name.spdx.json`.
When it is saved you hear "Saved owner-name.spdx.json: 212 packages, in SPDX
format." The file is JSON (JavaScript Object Notation), so QUILL opens it like
any other text file. **SBOM Report**, on a repository's context menu, reads
the same list in a window instead of saving it.

A repository whose dependency graph is turned off has nothing to export, and
QUILL says where to turn it on: the repository's settings, under Code
security. Nothing is saved in that case.

## A walk-through: your first discussion

This uses the practice repository, which you make with **Help > Practice on
GitHub...** (`Ctrl+Alt+P`). Discussions are off in a new repository, so the
first step turns them on.

1. Select the practice repository in the tree and press `Alt+Enter`. Its
   Properties open. Move to the **Features** page, check **Discussions**, and
   save. You hear that the change was saved.
2. Press `Ctrl+Shift+3`. You arrive in Discussions, and the details say it is
   empty and what would fill it.
3. Press `Ctrl+N`. Choose **General** from the categories. In the New
   Discussion window, type a title in **Title:**, a line in **Body:**, and
   press **Start Discussion**. Answer Yes to the question. You hear "Started
   discussion" with its number and category, and it is in the list.
4. Press Enter on it. The thread window opens on the discussion itself.
   Press `Alt+R`, type a reply, and post it. You hear "Posted your reply".
   Press Escape to close the thread.
5. Press `Shift+F10` and choose **Close Discussion...**, then **Resolved**.
   You hear "Closed the discussion."
6. Press `Ctrl+Shift+8`, then arrow to **Alerts**. A new repository has
   none, or has a kind turned off; either way the list says which, rather
   than claiming there are no alerts.

# Chapter 9: Codespaces and the GitHub CLI

## What this chapter covers

A codespace is a computer GitHub runs for you in the cloud, already set up
with a repository and its tools. You might want one to try a pull request
without setting anything up on your own computer, or to work on a machine
bigger than yours.

In this chapter you list, make, start, stop and delete codespaces in the
GitHub Workbench, and meet the GitHub CLI, the command-line tool a few of
QUILL's own Codespaces commands use, and how QUILL keeps the two sign-ins on
the same account.

By the end you will know where your codespaces are, what each command does
before you run it, and how to keep one from running, and charging, when you
are not using it.

Codespaces can cost money. GitHub gives each account some free hours a month
and charges for more, for as long as a codespace runs. Everything here needs a
signed-in account.

## Your codespaces in the Workbench

Two places in the tree list codespaces:

- **Repositories > My Codespaces** lists every codespace of yours, in any
  repository.
- A repository's **Code > Codespaces** lists your codespaces for that one
  repository.

Each row is one sentence: the codespace's name, its repository and branch,
its state as GitHub words it (such as Available or Shutdown), its machine, and
when it was last used. Its context menu has:

- **Show Details**: the same, with its address on GitHub.
- **Start** and **Stop**. Start asks first, and says who GitHub bills: you,
  or the organization that pays for the repository's codespaces. No is the
  default, so Enter starts nothing. You hear "Starting" and its name, or
  "Stopping" and its name, and that its files are kept. A stopped codespace
  does not charge for computing time.
- **Change Machine...** lists the machines GitHub offers for it and uses the
  one you choose from its next start. When there is no other, QUILL says so.
- **Export to a Branch** puts the codespace's changes on a branch of their
  own, and says when that is done.
- **Publish to a New Repository...**, for a codespace made from a template:
  give the new repository a name, or leave it empty for GitHub's, and choose
  private or public.
- **Delete...**, under More, asks first: changes you have not pushed or
  exported are lost.
- **Open on GitHub** and **Copy Link**.

## Making a codespace

There are three ways:

- **In a repository's Code > Codespaces**, press `Ctrl+N`. QUILL asks which
  branch, starting with `main`, then reads what a codespace for that
  repository can use and asks which machine, and which dev container when
  the repository has more than one. Then it asks whether to make it, and
  says who GitHub bills. You hear "Making the codespace" and its name, and
  that it takes a minute or two to start.
- **On an open pull request**, **Open in a Codespace** asks the same
  question, then makes one on the pull request's branch. Use it to try a
  change for real before you review it.
- **Open in Codespaces...**, on the context menu of a repository, branch or
  pull request, asks first, reminds you that starting a codespace can cost
  money, and then opens GitHub's own Codespaces page in your browser. It
  makes nothing itself and does not send your token. You make your choices
  on GitHub's page.

**Start**, **Ctrl+N** and **Open in a Codespace** each ask before GitHub
starts charging, for example "Make a codespace for pull request #42? It costs
money for every hour it runs, and for its storage until you delete it.
GitHub bills the organization acme." No is the default button. When GitHub
does not say who pays, QUILL says it is you unless the repository's
organization pays for Codespaces. **Stop** it when you are done.

If a repository's dev container asks for permissions you have not accepted,
QUILL says so and makes nothing. Open the repository's Codespaces on GitHub
once to accept them, then try again.

Values your codespaces read, such as a key for a private package registry,
are kept as secrets: **People > My Codespaces Secrets** for yours,
**Settings > Codespaces Secrets** for one repository's, and an organization's
own. Chapter 8 covers secrets.

## The GitHub CLI

Two of QUILL's Codespaces commands, below, use GitHub's command-line tool,
called `gh`. Everything in the Workbench above talks to GitHub directly and
does not need it. If `gh` is not installed when a command needs it, you hear
that QUILL did not find it, with the address to get it from, `cli.github.com`.

On Windows and macOS, QUILL can fetch it for you instead:
**Help > Download Optional Components...** has the GitHub CLI, a portable copy
of about 14 MB that QUILL checks before using. A copy of `gh` already
installed on your computer is always used first.

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

### Using gh's sign-in in QUILL

It works the other way too. If `gh` is already signed in, you do not have to
sign in to QUILL again. In **Manage GitHub Accounts...** (`Ctrl+Shift+K` in
the Workbench), choose **Use GitHub CLI Sign-In...**. QUILL asks which
server's sign-in to use, `github.com` or your GitHub Enterprise Server's
name, asks `gh` for it, checks with GitHub which account it is, and asks you
before it keeps it. Chapter 1 covers accounts in full.

## QUILL's Codespaces commands

These two are QUILL's alone, and need the GitHub CLI and a signed-in
account. In QUILL they are on **Tools > Git and GitHub > GitHub**, and in the
Workbench's **Repository Actions...** (`Ctrl+Shift+G`).

### Codespaces...

**Codespaces...** lists your codespaces. Each reads its name, its repository,
whether it is running, and how far its branch is ahead of or behind GitHub.
With none, you hear "No codespaces for" your account, and a pointer to
Create Codespace.

Choose one and a second list offers what to do with it:

- **Open in Browser (may start the codespace)**, after a question, because
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

**In QUILL Lite**, which has neither command, use the Workbench's own
Codespaces places above. They do not need the GitHub CLI.

## Other things that use Git or the CLI

**Sync Folder with GitHub...**, on the same QUILL menu, keeps a folder on your
computer in step with a repository, using Git. The QUILL user guide covers it
under
Sync a folder with GitHub.

Safe Mode switches off every command in this chapter. The Workbench does not
open in Safe Mode, and the CLI commands say "GitHub CLI commands are disabled
in Safe Mode".

## A walk-through: a codespace for the practice pull request, and back

This one costs a few minutes of GitHub's free codespace hours. Make the
practice repository first with **Help > Practice on GitHub...**
(`Ctrl+Alt+P`) if you have not.

1. In the Workbench, press `Ctrl+L`, type `quill-practice` and press Enter.
2. Press `Ctrl+Shift+2` for its Pull Requests, and F6 to the list.
3. On the pull request that fixes the greeting, press `Shift+F10`, open More,
   and choose **Open in a Codespace**. You hear "Making the codespace" and its
   name.
4. Go to **Repositories > My Codespaces** and press `F5` after a minute or
   two. Its row says Available when it is running.
5. Press `Shift+F10` on it and choose **Stop**. You hear "Stopping" and its
   name, and that its files are kept.
6. When you no longer need it, choose **Delete...** from the same menu and
   answer Yes.

# Chapter 10: Troubleshooting, privacy and help

## What this chapter covers

Something did not work, and you want to know why and what to do. QUILL never
answers with a bare error code. When GitHub says no, or QUILL holds a change
back, you hear one sentence that says what it was trying to do, why it could
not, and usually what to do next.

This chapter collects those sentences, grouped by when you meet them, with
the reason behind each and the fix. Then it covers using a token instead of
signing in, says exactly what the Workbench sends over the network, and how
to reach a person.

By the end you should be back at work, and know whether the problem was
GitHub, your account or the Workbench.

## Before you start: four quick checks

Most problems are one of these:

1. **Are you signed in, and as whom?** `Alt+9` in the Workbench says the
   account, and whether you are signed in at all. A guest only reads.
2. **What is this account's Workbench level?** `Alt+5` says what you can do
   here. An account set to Read Only or Organize is held back on purpose; see
   "Held back by the Workbench", below.
3. **Is Dry Run on?** The Account cell of the status bar says "Dry Run:
   nothing is sent" while it is. `Ctrl+Alt+D` turns it off.
4. **Is it GitHub?** **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) says
   whether GitHub itself is having trouble. See "Is it GitHub, or is it me?",
   below.

## How a refusal sounds

Most refusals have two parts: what QUILL was trying to do, and why it could
not. "Could not re-run the failed jobs. Access denied. GitHub refused this
request: check the token permissions and its organization SSO authorization."
When GitHub gave a reason of its own, QUILL adds it after "GitHub said:".

Nothing is half-done. When a command is refused, nothing was changed on
GitHub, and anything you had typed, such as a comment, a review or a new
issue, is still on your computer.

`F9` says the last result again, and `Shift+F9` explains it: what it means,
and what you might do next.

## The refusals, one by one

The sentences come in three groups, by who said no:

- [Held back by the Workbench](#held-back-by-the-workbench): QUILL stopped
  the change itself, because of the account's level, Safe Mode, Dry Run or a
  check on another account. Nothing was sent.
- [Connecting and signing in](#connecting-and-signing-in): adding an
  account, a token or a server.
- [When GitHub refuses](#when-github-refuses): GitHub received the request
  and said no.

## Held back by the Workbench

These sentences come from QUILL, not GitHub. Nothing was sent.

### "Cannot ...: it needs Full in the Workbench, and this account is Organize"

Each account has a Workbench level: **Read Only**, **Organize** or **Full**.
It limits what the Workbench may change with that account, whatever GitHub
would allow. Organize allows organizing and comments, such as labels,
reactions and closing issues, but not access, settings or deleting. The full
sentence ends "Account, Roles and Access, Workbench Level for This Account
changes it." Do that if you meant to make the change; Chapter 13 explains the
levels.

On a Properties sheet the same rule shows as a sentence beside the field,
such as "This account is set to Organize in the Workbench, which allows
organizing and comments, not access, settings or deleting."

### "This account is read only in the Workbench."

The account is set to Read Only, so no command changes anything on GitHub
with it. **Account > Roles and Access > Workbench Level for This Account...**
changes it.

### "QUILL is in Safe Mode, so the Workbench changes nothing on GitHub."

In Safe Mode every account is Read Only until QUILL is started normally. A
command refused this way says "and QUILL is in Safe Mode, which keeps every
account Read Only until QUILL is started normally." Workbench Options cannot
change that; restarting QUILL normally does.

### "GitHub item browsing is disabled in Safe Mode."

The full sentence ends "Restart QUILL normally to browse a repository." QUILL
started in Safe Mode, which keeps GitHub's network services off, so the
Workbench does not open. Restart it normally.

### "Dry run: QUILL would send ... Nothing was changed."

Dry Run is on (`Ctrl+Alt+D`, on the Tools menu). Every command still asks and
previews, then stops at the moment it would change GitHub and says what it
would have sent. Press `Ctrl+Alt+D` again to send for real. Chapter 12 has
more.

### "Cannot act as ...", from Act As Another Account

**Act As Another Account...** sends one action as another of your signed-in
accounts. Before it sends, QUILL asks GitHub whose that account's saved token
is, and holds the action to that account's own Workbench level.

- "Cannot act as kelly-test on github.com: its saved token now belongs to
  someone-else, so nothing was sent. Sign in again as kelly-test from Manage
  GitHub Accounts." The token was replaced, or now belongs to a different
  login. Sign that account in again.
- "Cannot act as kelly-test on github.com: GitHub did not say whose its saved
  token is, so nothing was sent." GitHub did not answer. Try again, or sign
  the account in again.
- A sentence starting "Cannot approve this pull request as kelly-test: it
  needs ..." means the other account's level does not allow it. Change that
  account's level, not yours.
- "Act As needs a second signed-in account: Account, Manage GitHub Accounts
  adds one."

### Compare Accounts

**Compare Accounts...** shows two of your accounts side by side, each as
GitHub answered that account's own token.

- "Compare Accounts needs two signed-in accounts: Account, Manage GitHub
  Accounts adds another."
- "Cannot compare these: they are on different servers, and a repository
  lives on one." One account is on github.com and the other on a GitHub
  Enterprise Server.
- "The token saved for jeff now belongs to someone-else, so nothing is shown
  for jeff." QUILL checks whose each token is before it shows anything, so
  one account's access never appears under another's name. Sign that account
  in again.

### "Open a repository first. Ctrl+L opens one by name or link."

The command works on one repository and you are not in one. Go to a
repository in the tree, or press `Ctrl+L` and type `owner/name`.

## Connecting and signing in

### "The GitHub token is invalid or expired."

The full sentence ends "Add a valid token or switch accounts." Your token has
reached its expiry date, or was cancelled on GitHub, perhaps because QUILL was
revoked under Authorized OAuth Apps. Open **Manage GitHub Accounts...**
(`Ctrl+Shift+K` in the Workbench), remove the old account, and choose **Sign
In with GitHub...** again. If you added the account with a token, you can make
a new one instead: see "Advanced: using a token", below.

### Sign In with GitHub: "That code expired before it was used."

The full sentence ends "Nothing was saved." A code from Sign In with GitHub
lasts about fifteen minutes. Choose **Sign In with GitHub...** again, and type
the new code on GitHub's page. You never retype an old one: each try gets a
fresh code, already on the clipboard.

### Sign In with GitHub: the sign-in was declined

Somebody chose Cancel on GitHub's approval page instead of Authorize. Nothing
was saved. Choose **Sign In with GitHub...** again if that was a slip.

### Sign In with GitHub: "GitHub did not give a sign-in code."

The full sentence ends "Check the connection and try again." QUILL could not
reach github.com. Check your connection, and any proxy or firewall that might
block it. If your network will not let QUILL reach GitHub's sign-in page,
**Add Token (Advanced)...** still works wherever the Workbench itself does.

Sign In with GitHub is for github.com only. For a GitHub Enterprise Server,
make a token on that server and add it with **Add Token (Advanced)...**, or
use the GitHub CLI's sign-in.

### Use GitHub CLI Sign-In: what it can say

**Use GitHub CLI Sign-In...**, in Manage GitHub Accounts, adds the account the
GitHub CLI (`gh`) is already signed in to. It can say:

- "QUILL did not find the GitHub CLI (gh). Sign In with GitHub works without
  it." Install the CLI, or use Sign In with GitHub.
- "The GitHub CLI is not signed in to github.com. Run gh auth login there
  first, or use Sign In with GitHub."
- "The GitHub CLI answered with something that is not a GitHub token."

When it works, QUILL names the account and server and asks before it keeps
its own copy. Signing out of the CLI later does not sign QUILL out.

### "GitHub did not confirm an account for that token. Nothing was saved."

From **Add Token (Advanced)...**: QUILL asks GitHub who a token belongs to
before it keeps it, and GitHub did not say. The token is mistyped, expired,
or made on a different server from the one under **GitHub server**.

### A GitHub Enterprise Server name is refused

When you type a server under **GitHub server**, QUILL can say:

- "A GitHub server is reached over HTTPS only."
- "Type the server's name only, such as github.example.com, without a path."
- A sentence ending "is not a server name QUILL can reach."

Type the server's name alone, as your administrator gives it.

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
organization.

If the organization would rather not approve apps, a token still works: see
"Advanced: using a token", below.

### "Write actions need a signed-in GitHub account"

The full sentence ends "this session is read-only." Some commands say "To
comment you need a signed-in GitHub account" instead. You are working as a
guest, so the Workbench only reads. Sign in with **Manage GitHub
Accounts...** (Chapter 1): in the Workbench it is **Account > Manage GitHub
Accounts...** (`Ctrl+Shift+K`); in QUILL it is also on **File > Open from
Remote**, and in QUILL Lite on **File** (`Alt+F`, then `H`).

### The GitHub menus are missing in QUILL

GitHub Remote Access is part of the Developer profile and is off in the
others. Press `Alt+Shift+P` and choose Developer, or turn on GitHub Remote
Access alone in **Profiles and Features...**. **Help > Why Don't I See a
Feature?** explains any missing command.

## When GitHub refuses

### "Access denied. GitHub refused this request"

The full sentence goes on "check the token permissions and its organization
SSO authorization." GitHub knows who you are, but will not let this token do
this. One of three things is usually true:

- **The token lacks a permission or scope.** When GitHub names what it
  needed, QUILL says it: "GitHub says it needs the token permission
  contents=write." for a fine-grained token, or "GitHub accepts the scope repo
  for it." for a classic one. You cannot add a permission to a token from
  QUILL: edit the token on GitHub, or sign in with GitHub instead. An account
  added with Sign In with GitHub has every scope the Workbench uses, so this
  usually means a token you added yourself. **Account > GitHub Permissions...**
  (`Ctrl+Shift+P`) lists every permission and whether you have it.
- **Your account lacks permission on GitHub.** Only people with write access
  can merge, rerun or label, and only administrators can rename, archive or
  change visibility. **Account > Roles and Access > My Access Here...** says
  your role here and where it comes from. Ask a maintainer.
- **The organization needs single sign-on.** See the next section.

Traffic in Insights is a special case. It needs push access, and QUILL says so
in plain words while still showing the contributors.

### "GitHub requires organization SSO authorization for this token."

The full sentence ends "In your GitHub token settings, authorize it for the
organization, then try again." The organization signs its members in through
its own system, and your token has not been authorized for it yet. On GitHub,
open your personal access tokens, choose **Configure SSO** beside the token,
and authorize it for the organization. The token keeps working everywhere else
in the meantime.

### "GitHub could not find it, or this account cannot see it."

The full sentence ends "Refresh the list; it may already be gone." Either the
thing really is gone, perhaps deleted or transferred, or it is private and
this account cannot see it. GitHub answers both the same way, on purpose, so
that private repositories cannot be discovered by guessing. Check the account
with `Alt+9`, and that the token can read private repositories if this one is
private.

### "This server's GitHub does not have ..."

Only on a GitHub Enterprise Server. The sentence names the server and, when
QUILL knows it, its version: "This server's GitHub does not have this, or this
account cannot see it: GitHub Enterprise Server at github.example.com, version
3.12, answered 'not found'. An older server lacks some of what GitHub.com has;
its administrator can say which version it runs." The feature is newer than
your server. Ask the administrator whether an upgrade is planned, or do it on
the server's own pages.

### "GitHub rate-limited this request."

The full sentence ends "Wait before retrying." You have used up an allowance,
or sent many requests close together. Press `Ctrl+Shift+L` to hear how much is
left and when it resets, or `Alt+6` to hear it in one line. Signed out you get
far fewer requests, so signing in is often the fix.

Two related sentences:

- "GitHub asked QUILL to wait 60 seconds." is a short pause GitHub asks for
  after a burst of requests. QUILL waits by itself and stops sending until the
  time is up. You hear it once.
- "GitHub API rate limit reached. Retry after" a number of seconds means the
  hourly allowance is gone. It comes back at the reset time the readout gives.

### "GitHub reported a conflict" and "GitHub refused the request"

A conflict means the thing changed while you were looking at it: someone else
merged, closed or edited it. Refresh (`F5`) and try again.

"GitHub refused the request" with a reason means GitHub will not do this in
the current state, such as rerunning the failed jobs of a run where nothing
failed. The reason that follows is GitHub's own.

### "GitHub had a server error"

The sentence gives the code, such as "(HTTP 502)", and ends "Wait a moment and
retry." The problem is at GitHub's end. Check GitHub's status, below.

### "GitHub redirected the request; QUILL did not follow it"

The sentence ends "so your token stayed on api.github.com" (or on your
Enterprise Server). QUILL never carries your token to another address. Use
**Open on GitHub** (`Shift+Enter`) for that item instead.

### A file shows no text

The Workbench shows text only for text files up to 1 MB, the most GitHub sends
this way, and says which rule a file broke. Open it on GitHub, or download it
there.

## Is it GitHub, or is it me?

When GitHub is slow or failing, the Workbench's errors can look like your own
mistake. **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) reads GitHub's
public status page, www.githubstatus.com, and says what it says: "GitHub
says: All Systems Operational.", or which parts are slow or down, and any
incident GitHub is working on, with its latest update.

The first time, it asks before reading the page. If the page cannot be read,
you hear "QUILL could not read GitHub's status page" and why. The command is
greyed in Safe Mode.

## When the help itself is wrong

If a help sentence, a step in this book or a tutorial was wrong, missing or
hard to follow, tell us. In the Workbench's tree, open **Help and Learning >
Ask a Person**, and press Enter on **Report a Help Problem**. It opens a
message in your own email, already saying where you were and the last thing
the Workbench said, for you to change and send. The Workbench sends nothing,
and no token or password is ever in it.

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
- **Your account is on a GitHub Enterprise Server.** Sign In with GitHub is
  for github.com only.
- **Your network blocks GitHub's sign-in page**, github.com/login/device, but
  lets the Workbench itself through.

### Making a token

1. Open github.com, or your Enterprise Server, in your browser and sign in.
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

Not sure which scopes to give it? **Account > Roles and Access > Least
Privilege Advice...** lists the smallest scopes, fine-grained permissions and
Workbench level that cover what QUILL saw this account do. Chapter 13 has
more.

### Adding it to QUILL

Open **Manage GitHub Accounts...** and choose **Add Token (Advanced)...**. The
**Add GitHub Token** window has two fields:

- **Personal access token:** paste the token.
- **GitHub server:** `github.com`, or your GitHub Enterprise Server's name,
  such as `github.example.com`. The token is only ever sent to this server.

Press **Connect**. QUILL asks GitHub who the token belongs to before it keeps
it. When GitHub confirms it, you hear "Added and switched to GitHub account"
and your GitHub username.

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
changes: the token keeps working, and QUILL doesn't ask again for that
account. It never asks about an account you signed in with, or about a
fine-grained token, since that's the kind people choose on purpose.

### When a token is about to expire

Tokens you make yourself usually have an expiry date, and GitHub tells QUILL
when it is. If the active account's token expires within seven days, QUILL
says so the first time the Workbench talks to GitHub that day, for example
"Your GitHub token for your-name expires in 3 days." If it has already
expired, you hear "Your GitHub token for your-name has expired." Either way
it's said at most once a day, and it also goes into **Notifications**, where
opening it takes you to Manage GitHub Accounts. From there, sign in with
GitHub, or add a new token.

QUILL Lite does all of this the same way.

## Privacy: what goes over the network

The Workbench talks to GitHub, and only when you ask it to. Two other
addresses are read, each only when you choose the command that reads it.

- **Before the first connection** QUILL asks your permission, once (Chapter
  1).
- **Requests go to GitHub's own servers**: `api.github.com` for nearly
  everything, and `uploads.github.com` when you upload a release file. An
  account on a GitHub Enterprise Server talks to that server only, and its
  token is never sent anywhere else. Connections are encrypted, and QUILL
  refuses to follow a redirect to any other address while carrying your
  token.
- **Signing in** uses github.com's own sign-in page and code, with QUILL's
  public app id. Your password never passes through QUILL.
- **Downloads** of logs and artifacts are handed by GitHub to a short-lived
  address elsewhere. QUILL fetches those without your token.
- **Compare Accounts and Act As** send each account's own token to that
  account's own server, and nowhere else.
- **GitHub Service Status** reads www.githubstatus.com, after asking the first
  time. It sends nothing about you, your accounts or your repositories.
- **Links opened in your browser** never carry your token.
- **The GitHub CLI** uses its own sign-in, never QUILL's token (Chapter 9).
  Use GitHub CLI Sign-In reads the CLI's sign-in once, after asking, and
  keeps QUILL's own copy.
- **AI** is used only where you ask for it, such as Summarize Discussion. It
  sends the text to the AI you chose, after the same questions as every AI
  feature.
- **Help > Ask How...** (`Alt+Shift+A`) sends your question and the
  Workbench's own help text to the AI you chose, and nothing about your
  repositories. It is greyed without an AI and in Safe Mode.

What stays on your computer and never goes to GitHub: your token (in the
operating system's secure store), each account's Workbench level, your pins
and favorites, where you left off, your local drafts and pending review
comments, your saved searches, access templates, Change History, the
attention queue's settings and filters, and the copies of earlier answers
QUILL keeps so that unchanged reloads cost nothing.

Safe Mode switches all of it off.

## Getting help

If something here does not work the way this book says, or you are stuck,
write to a person. Support is run by Community Access, at
**support@community-access.org**. A real person reads every message and
replies by email. Nothing you send is posted on GitHub or anywhere else in
public.

The quickest way to write is **Help > Get Help from Support...**
(`Ctrl+Alt+F2`), in both editors. It fills in your app's version and your
screen reader for you, and opens your own mail program with the message
written. Nothing is sent until you send it from there.

It helps to say:

- which app and version you are using, and which screen reader;
- where in the Workbench you were (`Alt+1` says it), and what you pressed;
- what QUILL said, word for word if you can (`F9` says it again); and
- what you expected instead.

# Chapter 11: Keyboard reference

## What this chapter covers

You know what you want to do and want the key for it. This chapter lists
every key the GitHub Workbench and the windows it opens answer to, one window
at a time, so you can look one up without reading a whole chapter.

It starts with the GitHub menu in the editors, then the Workbench's own keys
grouped by what they do, then each smaller window. By the end you will have
the few keys worth learning first, and know where to find the rest.

Keys marked as access keys are the underlined letters of a control, pressed
with Alt; they work while that window has focus. The GitHub menu's rows have
no keys out of the box, and you can give them some in the Keymap Editor.

Throughout, `Shift+F10` or the Applications key opens the context menu of
whatever has focus, and Escape closes the smaller window you are in. The
Workbench itself is the exception: Escape never closes it, and `Alt+F4` does.

### The ten to learn first

| Key | What it does |
| --- | --- |
| `F6` | Move between the tree, the filter, the list, the details and the status bar |
| Enter | Do the obvious thing with the selected row |
| `Backspace` | Go back to where you were |
| `Alt+Enter` | Everything about the selected row, on one sheet |
| `Shift+F1` | What you can do here, with each key |
| `F1` | What this place and control are for |
| `Ctrl+E` | Filter the list |
| `Ctrl+1` | Inbox |
| `Ctrl+L` | Go to any repository, issue or link |
| `F9` | Say the last result again |

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
you to. Every one of them can be changed in the Keymap Editor, and the menus,
`Shift+F1`, `Alt+Shift+F1` and the Key Describer always say the key that is
really bound. This chapter shows the keys the Workbench starts with.

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
| `Ctrl+7` | Watches |
| `Ctrl+8` | Saved Searches |
| `Ctrl+9` | Start Here |
| `Ctrl+0` | Across Repositories |
| `Ctrl+Shift+1` to `Ctrl+Shift+0` | The current repository's Issues, Pull Requests, Discussions, Actions Runs, Files, Releases, Projects, Security, Settings and Insights |
| `Alt+Up` | The place above this one |
| `Alt+Left`, `Alt+Right` | Back and Forward (`Backspace` goes back too) |
| `Ctrl+L` | Open GitHub Address: `owner/name`, `#42`, `owner/name#42` or any GitHub link |
| `Ctrl+G` | Go to an issue or pull request by number |
| `Ctrl+Period`, `Ctrl+Shift+Period` | Next or previous unread row |
| `Ctrl+Shift+E` | Back to the editor that opened the Workbench |

`Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys in the editors. The Workbench has
no AI menu, so here they belong to the Go row.

### Doing things to the selected row

| Key | What it does |
| --- | --- |
| Enter | The obvious thing: read an issue, review a pull request, a run's jobs, a branch's commits, a release's files |
| `Alt+Enter` | Properties: everything about it, on one sheet |
| `Shift+F10` or the Applications key | The row's context menu |
| `Shift+Enter` | Open it on GitHub, in your browser |
| `Ctrl+Enter` | Open a file in the editor |
| `Ctrl+N` | New here: issue, pull request, gist, saved search, pin, or the repositories for Across Repositories |
| `Ctrl+Shift+N` | New, asking what to make |
| `Ctrl+Shift+M` | Comment |
| `Ctrl+Shift+I` | Read as Document: an issue, pull request or discussion as one document |
| `Ctrl+Shift+D` | A pull request's changed files |
| `Ctrl+Shift+Enter` | Merge a pull request |
| `Ctrl+Shift+B` | Compare a branch with another |
| `Ctrl+B` | Compare the selected branch, tag, release or commit with the default branch |
| `Alt+Shift+B` | Compare a tag or release with the one before it, or a commit with its parent |
| `Ctrl+Shift+A` | Assign an issue to Copilot |
| `Ctrl+Shift+T` | Start an issue or pull request in a local worktree (QUILL only) |
| `Ctrl+Shift+W` | What failed in a run |
| `Ctrl+Shift+F5` | Re-run a run's failed jobs only |
| `Ctrl+Cancel` (the Ctrl+Break key) | Cancel the selected run, after asking (in the list) |
| `Ctrl+Shift+R` | Run a workflow on a branch |
| `Ctrl+Shift+G` | Repository Actions |
| `Ctrl+Alt+B` | Export Software Bill of Materials |
| `Ctrl+Alt+T` | Transfer Repository |
| `Ctrl+Alt+W` | Clone Wiki |
| `Ctrl+Q`, `Ctrl+Shift+Q` | Mark a notification read; mark the whole list read |
| `Ctrl+Alt+N` | Inbox Rules |
| `Ctrl+D` | Add to Favorites, or take it out |
| `Ctrl+C`, `Ctrl+Shift+C` | Copy the row; copy its address |
| Delete | The safe removal for the row, asking first when it cannot be undone (in the list) |
| `Ctrl+Z`, `Ctrl+Y` | Undo or redo your last change on GitHub, in the tree and the list |

### Lists

| Key | What it does |
| --- | --- |
| `Ctrl+E`, `Ctrl+Shift+F` | Move to the filter box |
| `Ctrl+Alt+F` | Filter Builder |
| `Ctrl+Shift+U` | Choose columns |
| `Ctrl+A` | Select every row |
| `F5`, `Ctrl+R` | Refresh |
| `Ctrl+F5` | Refresh, reading everything from GitHub again |
| `Alt+Page Down` | Load more |
| `Ctrl+Shift+Page Down` | Load all |
| `Ctrl+Shift+X` | Export List: the list as shown, as Excel, CSV or a Markdown table |
| `Ctrl+Alt+I` | Import Issues from a Spreadsheet |
| `Ctrl+Alt+L` | New Issues from Lines |
| Escape | Clear the filter box, then go back |

Sort By, Group By, Quick Filters and Show are on the View menu (`Alt+V`).
Their rows have letters, not keys.

### Account and tools

| Key | What it does |
| --- | --- |
| `Ctrl+Shift+K` | Manage GitHub Accounts |
| `Ctrl+Shift+L` | GitHub's remaining hourly allowance |
| `Ctrl+Shift+P` | GitHub Permissions |
| `Ctrl+Shift+H` | Change History |
| `Ctrl+Alt+S` | Set Your Status |
| `Ctrl+Shift+O` | Workbench Options |
| `Ctrl+Alt+D` | Dry Run on or off |
| `Ctrl+Shift+S` | Plain-Language Batch |
| `Ctrl+Shift+J` | GitHub API Console |
| `Alt+F4` | Close the Workbench |

**Account > Roles and Access** (My Access Here, View As Role, Compare Roles,
Why Can't They?, Access Review, Bulk Access Changes, Access Templates, Apply
Access Template, Compare Accounts, Act As Another Account, Workbench Level for
This Account, and Least Privilege Advice) has no keys out of the box; its rows
have letters. Chapter 13 covers them.

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
| `Alt+Shift+F1` | Every key in the window |
| `Ctrl+F2` | Tutorials: the GitHub lessons |
| `Ctrl+Alt+P` | Practice on GitHub |
| `Ctrl+Alt+F1` | GitHub Service Status |
| `F11` | Say or Type a Command, in this window |
| `Ctrl+Alt+Shift+F1` | What Can I Say Here: what `F11` can do in this window |
| `Ctrl+Alt+K` | Key Describer: keys say what they do instead of doing it, until `Escape` |
| `Alt+Shift+T` | Take the Tour: a spoken tour of the window, a pane at a time |
| `Alt+Shift+A` | Ask How: a question in your own words, answered from this help by the AI you chose |

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
| `Alt+D` | Convert to Draft, on a pull request that is not a draft |
| `Alt+B` | Update Branch... |
| `Alt+A` | Auto-Merge and Queue... |

Check Merge Policy has no access key. Request Copilot Review is on the pull
request's context menu (`Shift+F10` on the outline) and has none either.

### Compose Review

| Key | Control |
| --- | --- |
| `Alt+M` | Review message |
| `Alt+W` | Comment Window..., to write the message in a larger window |
| Escape | Save Draft and Close |

Review action and Submit Review have no access key; reach them with Tab.

## The diff

| Key | What it does |
| --- | --- |
| `Alt+M` | Line marks: words, short words, diff symbols, or diff symbols with changed lines |
| `Alt+N` / `Alt+P`, in the patch lines | Next / previous change, "Change 2 of 5" (`F8` / `Shift+F8` too) |
| `Alt+H` | Changed Lines Only |
| `Alt+W` | Hide Whitespace Changes |
| `Alt+T` | Choose Commit |
| `Alt+P`, from anywhere else | Move to the patch lines |
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
| `Alt+W` | Comment Window..., to write the comment in a larger window |

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
| `Alt+P` | Open Pull Request |
| `Alt+G` | Open on GitHub |
| `Ctrl+Tab` | Switch between the Commits and Changed Files tabs |

# Chapter 12: The GitHub Workbench, place by place

## What this chapter covers

The GitHub Workbench is one window for everything GitHub: what needs you,
your repositories, searches, people, gists, projects and watches. The other
chapters are about jobs, such as reviewing a pull request. This one is about
the window itself, so you can find any place in it and know what is there.

It walks through the tree the way it is laid out, one place at a time,
starting with Start Here. Then it covers what you can do to a selected row,
the help keys, Dry Run, the practice repository and Workbench Options.

By the end you will know where each thing lives, how to get there in one key,
and how to ask the window what you can do wherever you are.

Every later section assumes three things, so here they are first.

- **Three panes.** The tree on the left says where you are. The list says
  what is there. The details say what the selected row is. `F6` moves from
  pane to pane, through the filter box, and then to the status bar;
  `Shift+F6` goes the other way. Once you have opened a place in the tree,
  its name says how many rows it had, such as "Issues (12)", or "Issues (30
  or more)" when GitHub had more than one page. The count is added after you
  move away, so it is never read out while you are on the place; you hear it
  the next time you arrive. Searches have no count, because their rows depend
  on what you typed.
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
brings it forward instead of opening a second one. Chapter 1 has the other
ways in.

The Workbench is a window of its own, not a dialog. The editor stays usable
while it is open, and `Alt+Tab` moves between them. A smaller window the
Workbench opens, such as a run's logs, blocks only the Workbench, never the
editor. Inside the Workbench, `Ctrl+Shift+E` brings back the editor that
opened it. `Alt+F4` closes the Workbench; `Escape` never does. Escape clears
the filter box first, and then goes back to where you were. In Details, it
returns you to the list instead.

The window remembers where you were for each account: its size and how wide
the tree is, the place you had selected, the branches of the tree you had
open, and the repositories you visited. Next time it opens there, unless you
have chosen Inbox or Start Here in Workbench Options. When you come back to a
list, the row you were on is selected again.

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
- **Invitations** lists repositories you have been invited to, who invited
  you and with what access. Accept or Decline is on a row's context menu.
- **Review Requests**, **Assigned to Me**, **Mentions**, **My Open Pull
  Requests** and **My Open Issues** are the same work split by why it is
  yours.
- **Review Requests** holds two kinds: pull requests that ask you by name,
  and those that ask a team you belong to. A team's row ends in "team review
  request", so you know someone else on the team may take it; the pull
  request's own sheet names the team under Team reviewers. GitHub's search
  cannot say which team from the list itself. The Inbox marks them the same
  way.
- **My Activity Feed** is what you did lately.

When one of these is empty, the details pane says so and says what would fill
it, so an empty list never leaves you wondering whether it loaded. Chapter 3
covers working through them.

## Repositories

The repository you are working in comes first, then Pinned, Favorites, your
own repositories, Starred, Star Lists, Watched, My Packages, My Codespaces and
your organizations. Three of GitHub's own lists, read only, are here too:
**Licences**, **.gitignore Templates** and **Codes of Conduct**, the choices
a new repository offers.

`Ctrl+2` goes to the repository you are working in. `Ctrl+L` opens any other
one: type `owner/name`, or paste a link, and it gets a place of its own here.

Every repository has the same places under it, in the same order, so once you
know one you know them all: Overview, Issues, Pull Requests, Issues and Pull
Requests, Discussions, Merge Queue, Actions, Code, Releases, Labels,
Milestones, Templates, Projects, Activity, People, Insights, Deployments and
Environments, Wiki, GitHub Pages, Security and Settings. `Ctrl+Shift+1` to
`Ctrl+Shift+0` jump to ten of them:

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

- **Overview** reads the repository's README, description and community
  profile.
- **Issues and Pull Requests** has both in one list, newest first, if you
  prefer reading them the way an inbox reads.
- **Merge Queue** lists the default branch's merge queue in order, when the
  repository has one: "2. #57 Fix the parser, running its checks", with who
  queued it and the commit it was queued at in the details. A repository
  without a merge queue lists nothing; the place's note says why. Chapter 5
  has the merge queue.
- **Actions** holds Runs, Workflows, Runners, Caches and Artifacts (Chapter
  6). **Code** holds Files, Branches, Commits, Tags, Commit Comments,
  Codespaces, and Upstream on a fork (Chapter 7).
- **Files** lists the default branch a folder at a time. Enter on a folder
  opens it, and the first row, Up one folder, comes back out. Enter on a file
  opens it in the editor.
- **People** holds Contributors and People, Forks, Collaborators and Team
  Access, Watchers and Invitations. **Activity** holds All Issue Comments,
  Push Activity and My Notifications Here.
- **Security** holds Policy, Alerts, Dismissed and Resolved Alerts,
  Advisories, Code Scanning Analyses and CodeQL Databases (Chapter 8).
- **Settings** holds General (the name, visibility and default branch),
  Branch Protection, Rulesets, Rule Insights, Secret and Variable Names, each
  kind of secret and variable, Environments, Webhooks, Deploy Keys, Autolinks,
  Issue Types, Custom Property Values and CODEOWNERS Problems. Enter on
  General or Branch Protection opens that setting, which asks before anything
  changes. Chapter 13 covers rulesets and branch protection.
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
pin under Pinned, a watch under Watches, and a repository set under
Repository Sets. `Ctrl+Shift+N` asks what to make.

### A new issue, and issue forms

`Ctrl+N` in Issues reads the repository's issue templates first, then asks
which to start from: Blank issue, or one of the templates, each with its own
description. That list includes GitHub's issue forms, the ones written in
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
**Compare With Default** (`Ctrl+B`) compares the selected branch, tag, release
or commit with the default branch, and **Compare With Previous**
(`Alt+Shift+B`) compares a tag or release with the one before it, or a commit
with its parent.

### Templates and community files

A repository's **Templates** place lists everything GitHub reads to shape new
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
- **New Template...** (`Ctrl+N` on Templates) makes an issue form, a
  discussion form, a pull request template or the chooser. An issue form can
  start from a starter (bug report, feature request, accessibility bug
  report, or a blank form) or **From a SurveyJS or XLSForm file...**: choose
  a SurveyJS form (`.json`) or an XLSForm (`.xlsx`), name the form, and it
  opens in the builder converted, with a sentence for every question type
  GitHub forms cannot hold, such as a signature.
- **Write it as plain text.** In a form document, **Tools > Forms > Save As
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
as `is:open author:@me label:bug`, ask GitHub. `Ctrl+3` goes to Search, and
`Ctrl+8` to Saved Searches; `Ctrl+N` in a search keeps it there.

A search you use all the time can have a place of its own in the tree. In
Saved Searches, choose **Pin as Node** on its context menu: it appears under
Saved Searches, named by the search, and opening it asks GitHub for the
results afresh. **Unpin Node** takes the place away and keeps the saved
search; **Remove Saved Search** takes both.

Besides issues and pull requests, code, commits, security advisories and
repositories, Search has:

- **People and Organizations:** accounts whose name or login matches, such
  as `jeff`, or with GitHub's words, `type:org location:Tucson`. Each row
  says whether it is a person or an organization; Enter opens one.
- **Topics:** GitHub topics, with what each is about and whether GitHub
  features it, such as "Accessibility: For everyone (featured)".

## People, Gists and Projects

`Ctrl+4` goes to People: your profile, your keys, sponsorships, who you
follow, who follows you, your teams, your billing, and **Find a Person...**.
Enter on a person gives them a place in the tree, with their repositories and
activity. Follow or Unfollow is on a person's context menu.

A person's place also lists what GitHub shows of them publicly, read only:
**SSH Keys**, **GPG Keys** and **SSH Signing Keys** (check one before giving
them access to a server: "SSH key 4, ending abcdefgh."), **Social Accounts**,
**Gists**, **Starred**, **Watching**, **Projects**, **Packages**, and
**People They Follow: Activity**.

`Ctrl+6` goes to Projects; each repository's own Projects are under it,
`Ctrl+Shift+7`. Chapter 4 covers Projects.

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

**Set Your Status...** (`Ctrl+Alt+S`) sets your own GitHub status: a message,
an emoji, busy or not, and when it clears.

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
for, or a fine-grained token with Plan read permission. Without that, the
list does not pretend you used nothing. Its one row says which permission is
missing and that the same figures are on GitHub's billing page.

### Gists

`Ctrl+5` goes to My Gists.

- **New Gist** (`Ctrl+N` on My Gists) starts from the editor that opened the
  Workbench: the text you have selected there, or the whole document when
  nothing is selected, named after the document's file, or notes.md for one
  you have not saved. You can add more files, write a description, and choose
  public or secret before it is sent.
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
repositories a setting covers, are places in the tree that all work the same
way. Each row reads as a sentence. `Ctrl+N` adds one, where GitHub allows it;
**Change...** on the context menu changes the selected one; `Delete` deletes
it, after asking. Where a list can only be read, it says so when it is empty,
and the context menu has no Add or Delete.

**Under People, for your own account:**

- **My Issue Fields:** values your own repositories' issues can carry, such as
  Priority or Due date. `Ctrl+N` asks for its name, its kind (text, number,
  date, or single select), its choices for a single select, separated by
  commas, and a description.
- **My Installed Apps:** the GitHub Apps installed where you can manage them,
  and whether each reaches all repositories or chosen ones. **Repositories...**
  on a row checks which repositories it may reach; QUILL adds and removes them
  one at a time, so a change someone else made meanwhile is kept.
- **My Email Addresses**, **My Social Accounts**, **Blocked People**, **My
  Issue Types**, **My Organizations' Memberships** and **My Codespaces
  Secrets**.
- **My Public Email Addresses** and **Repositories I Watch:** read only.

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
- **Dependabot Alerts**, **Secret Scanning Alerts**, **Code Scanning
  Alerts** and **Security Advisories:** every repository's, in one list. A
  secret's value is never asked for, so it is never shown. Open a
  repository's Alerts to dismiss or resolve one.
- **Actions, Dependabot, Codespaces and Copilot Agent Secrets:** Change... on
  one sends a new value, sealed, or keeps it, and chooses all, private or
  selected repositories; Repositories Allowed... picks the selected ones.
- **Recent Events:** the organization's public activity, newest first.
- **Custom Property Values:** every repository's custom properties in one list.
- **Members**, **Invitations**, **Outside Collaborators**, **Security
  Managers**, **Teams**, **Organization Roles**, **Rulesets**, **Rule
  Insights**, **Access Review: People** and **Access Review: Teams:** who is
  in the organization and what they may do. Chapter 13 covers them.

**Under a repository:**

- **Activity > All Issue Comments**, **Push Activity** (pushes, force pushes,
  merges and branch changes) and **My Notifications Here:** read only.
- **Code > Commit Comments:** comments on commits. Change... rewrites one of
  yours; `Delete` deletes it.
- **People > Watchers:** who gets notifications for it.
- **Settings > CODEOWNERS Problems:** lines in the CODEOWNERS file GitHub could
  not use, with its suggestion.
- **Settings > Rule Insights:** recent pushes its rulesets passed, blocked or
  let through on a bypass.
- **Settings > Custom Property Values:** the organization's properties as this
  repository has them.

## Watches

`Ctrl+7` goes to Watches: rules, kept on this computer, that tell you when
something happens on GitHub. Each row is one rule: a run finishes on a
repository or branch, a review arrives on a pull request, a new release, or a
new comment.

- `Ctrl+N` adds one, Enter edits it, and `Delete` removes it.
- **Pause or Resume Watch** stops a watch for a while without losing it.
- **Check Watches Now** checks every watch at once, rather than waiting.
- **Why?** says what the watch looks for, how often it is checked, when it
  was last checked, and what it found.

Watches are checked on the same interval as notifications, set in Workbench
Options, while the Workbench is open, and each row says when it was last
checked. A watch never marks a notification read, and it changes nothing on
GitHub. It is not the same as watching a repository on GitHub, which is
**Watch or Unwatch** on a repository's context menu and sends notifications.

## Why Ctrl+3, Ctrl+4 and Ctrl+8 go places here

Elsewhere in the family, `Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys: a
document task, Choose Your AI, and Which AI Am I Using. The Workbench has no
AI menu, so here they keep their place in the Go row with the other digits:
`Ctrl+3` is Search, `Ctrl+4` is People and `Ctrl+8` is Saved Searches. Switch
back to the editor (`Ctrl+Shift+E`) and they are AI keys again.

## Across Repositories

`Ctrl+0` goes to Across Repositories: one kind of thing from several
repositories, in one list. It is for questions such as "what has been
released across all my projects this month?" or "which runs failed
anywhere?".

The repositories you read come from a **repository set**. **Repository Sets**,
under Across Repositories, lists your named sets. `Ctrl+N` there makes one:
choose repositories from a checklist, make the set from a filter such as
`org:name topic:x`, or take every repository you can reach. Enter on a set
uses it; **Rename Set...**, **Edit Repositories...** and **Set Filter...**
change it, and `Delete` forgets it after asking. Sets stay on this computer,
for the account you are signed in with. `Ctrl+N` on Across Repositories
itself edits the repositories of the set in use.

Under it are eight lists, each drawn from every repository in the set at
once:

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
crowd out the rest. **Next Repository** and **Previous Repository**, on a
row's context menu, jump to the next repository's rows, and **View More from
This Repository** reads more of one.

The status bar says how many rows came from how many repositories, and names
every repository that could not be read and why, such as "not found, or no
access" or "Discussions are off". A repository never just goes missing from
the list. A fork whose upstream is also in the set adds no issues of its own,
because on GitHub a fork's issues are its upstream's; the status bar says so,
and you read them once, under the upstream.

**Fleet** has one line per repository in the set: the exact revision of its
default branch, its checks, open pull requests, latest release and alerts,
and when it was read. A repository that could not be read keeps its line,
with the reason.

### Each name across the set

GitHub keeps a label, a tag or a secret inside one repository, but you think
of them by name across many: "the bug label", "the v3.2.0 tag", "the
NUGET_KEY secret". Across Repositories has a place for each such kind, in five
groups:

- **Planning by Name:** Labels, Milestones, Topics.
- **Code by Name:** Tags, Branches, Rules and Branch Protection, Packages.
- **Actions by Name:** Environments, Secrets, Variables, Workflows.
- **Files by Name:** Templates, Dependabot, CODEOWNERS.
- **Settings by Name:** Webhooks, Deploy Keys, Autolinks, Repository
  Settings, People.

A row is one name, such as "v3.2.0: in 4 of 4 repositories, 4 different
commits", "main: in 30 of 30 repositories, default in 30, protected in 26",
"ci.yml: in 12 of 12 repositories, 3 versions of the file" or "Allow
auto-merge: on in 20, off in 8".
Enter shows its variants, each with the repositories that have it, and the
repositories that lack it. A repository that could not be read, often because
reading secrets, webhooks and keys needs admin access, is named apart and
never counted as missing.

The places for files, people, settings and packages each read what one
repository already shows:

- **Workflows by Name** lists each workflow file. **Templates by Name** lists
  issue and pull request templates, discussion forms, and community files
  such as CONTRIBUTING and SECURITY, wherever each repository keeps them.
  **Dependabot by Name** lists dependabot.yml with its update entries, and
  **CODEOWNERS by Name** the CODEOWNERS file GitHub uses, with its rules and
  owners. A variant is a version of the file.
- **People by Name** is the access matrix from each person's side: their role
  in each repository and where it comes from, directly or from the
  organization or a team, and where they have no access. A repository whose
  collaborators GitHub does not show you is named apart.
- **Repository Settings by Name** lists each switch on the Repository sheet's
  Features and Merging pages, with how many repositories have it on and off.
- **Packages by Name** lists each package published from the set, with its
  type and visibility.

The context menu then changes it everywhere, as far as GitHub allows. Every
change shows a preview first, repository by repository, with what is blocked
and why, and then one result per repository. Each target is read again just
before it is written, so one somebody changed on GitHub meanwhile is left
alone and named.

- **Make Them the Same** (labels, milestones, rules, environments, variables,
  webhooks, repository settings, and the four kinds of file): choose the
  winning variant. An environment's custom branch list, and a team reviewer
  from another owner, are not copied. A webhook keeps its secret. A setting
  needs admin access in each repository, and Change History can put each one
  back.
- **Add to Missing** (labels, milestones, topics, rulesets, environments,
  variables, webhooks, autolinks, and the four kinds of file). An
  environment's custom list of branches, and a team reviewer from another
  owner, are not copied. A deploy key cannot be added to more: GitHub accepts
  one key in one repository only.
- **A file is never pushed.** For a workflow, template, Dependabot or
  CODEOWNERS file, Make Them the Same and Add to Missing open one pull
  request in each repository with the winning version. Nothing changes until
  each pull request is merged, and the results say how many wait for review.
  A file somebody changed since the list was read is not proposed.
- **Compare Configuration** (the four kinds of file): choose the version to
  compare from and the repository to compare with. The differences open in
  the same Compare Configuration window as Repository Actions, where Propose
  Update opens one pull request in that repository.
- **Release Train** (tags): make the tag, the tag's draft release, or the tag
  and a published release, on the default branch of each repository you
  choose. A repository that already has the tag is skipped, and its tag is
  never moved.
- **Draft Releases Together** (tags): one draft release of the tag in each
  repository you choose, those that have the tag checked first. Write the
  notes once; `{repository}` and `{tag}` in them become each repository's
  own, and GitHub's generated notes for each repository can follow yours. A
  repository that already has a release or a draft for the tag is left
  alone. A draft is seen only by people who may push, until somebody
  publishes it.
- **Set Secret Everywhere** (secrets): type the new value once. It is sealed
  for each repository before it leaves your computer, and it is never shown,
  kept in Change History or written to the details. No secret's old value can
  be read, by anyone.
- **Rename Everywhere** (labels, milestones, branches). For a branch the
  preview says where it is the default branch, where its protection moves
  with it, and how many open pull requests GitHub retargets. A repository
  that already has a milestone of the new name is skipped, with the reason.
  Undo GitHub Change (`Ctrl+Z`) puts a label's or a milestone's old name back,
  one repository at a time.
- **Merge Into** (labels): move every item to another label, then delete
  this one.
- **Close Everywhere** and **Move Open Work To** (milestones): close every
  open copy of a milestone, or move each repository's open items to another
  milestone of its own.
- **Find Uses** searches every issue and pull request that has it, across the
  set.
- **Turn On or Off Everywhere** (webhooks).
- **Delete Everywhere** (labels, milestones, topics, tags, environments,
  secrets, variables, webhooks, deploy keys, autolinks). A tag with a release
  built on it is kept, with the reason. A milestone's issues and pull
  requests stay, with no milestone, and the preview says how many.
- **Delete Where Merged** (branches): the branch is deleted only in the
  repositories where everything on it is already in the default branch, or
  where a merged pull request took its last commit, as a squash merge does.
  A copy that is the default branch, is protected, has open pull requests
  based on it or from it, or has commits found nowhere else is kept, with the
  reason, and so is one that gains a commit after the preview. Each result
  names the branch's last commit, so it can be made again by hand if it is
  ever wanted.
- **Promote to Organization** (rulesets, secrets, variables, webhooks): one
  organization ruleset, secret or variable for the set's repositories in that
  organization, or one organization webhook. GitHub sends an organization
  webhook for every repository in the organization, and the preview says so.
  Each repository's own copy is deleted only after the organization's one
  exists, because a repository's own secret or variable wins over the
  organization's. Labels, environments, deploy keys and autolinks have no
  organization form in GitHub, so they are not promoted.

A preview that deletes, or that dismisses alerts, starts on Cancel, so Enter
sends nothing: press the button that names the change. Its summary says how
many repositories will change and names each one.

People and packages are read only here. Bulk Access Changes gives or takes a
role in many repositories, and GitHub's API cannot change a package's
visibility or access.

Secrets, environments, webhooks, deploy keys, rules and repository settings
decide who may deploy, what is kept secret, where data is sent or how the
repository works, so changing them across repositories needs Full in the
Workbench.

### Dismissing one alert everywhere

On a Dependabot or code scanning alert in **Security Alerts**, **Dismiss
Everywhere...** dismisses every open copy of it in the set at once: the same
advisory for Dependabot, whatever manifest it is in, or the same rule of the
same tool for code scanning, wherever in the code it is. Choose one of
GitHub's reasons and, if you like, one comment of up to 280 characters. The
preview names every repository, with the alert numbers it will dismiss there,
or says that it has none open or could not be read. Each repository's alerts
are read again just before the change, so one closed meanwhile is left out
and named. Each dismissed alert is its own row in Change History, so Undo
GitHub Change reopens it, as **Dismiss or Reopen Alert...** does in one
repository. A secret scanning alert is never dismissed this way: each leaked
secret is its own, so each is resolved in its own repository.

## Doing things to what is selected

Enter does the obvious thing; the Applications key, or `Shift+F10`, opens the
context menu, with the obvious thing first and Properties last; and
`Alt+Enter` shows everything about the selected row on one sheet (Chapter
13). The **Item** menu (`Alt+I`) has the same commands as the context menu.

The keys you will use most:

| Key | Does |
| --- | --- |
| `Ctrl+Shift+M` | Comment on the selected issue or pull request |
| `Ctrl+Shift+I` | Read the selected issue, pull request or discussion as one document |
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

`Delete` always does the safe thing for the kind of row, and asks first
whenever it cannot be undone: on a branch, a label, a release's file, a gist,
an Actions cache or a workflow run it deletes that one thing, after asking. It
never deletes the repository's default branch. Enter never deletes anything.

### Taking a list with you

**Export List...** (`Ctrl+Shift+X`), on the Workbench's File menu, saves the
list you are looking at, as it is shown: its columns, its filter and its
rows. Choose an Excel workbook, a CSV file or a Markdown table in the Save
window. A Markdown table is the kind the editor reads as a table, so the
Workbench offers to open it there, where the table keys move cell by cell. It
then says how many rows it wrote, and names any columns you have hidden,
because those are left out. It works on any list: issues, pull requests,
runs, alerts, people, Change History. The WordPress Workbench's Export List
is the same command.

An alert list exports without anything secret in it. The Workbench never asks
GitHub for a secret scanning alert's value, so it is in neither the list nor
the file. Text GitHub wrote into an alert, such as a code scanning message
quoting a hard-coded password, passes the same redaction Change History uses
before it is written: a value shaped like a token or key becomes `[TOKEN]`,
and a link's user name and password are dropped. When that happens, the
Workbench says how many values it held back.

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

### Each kind of row's own commands

Everything happens in the Workbench, on the selected row; where a job needs a
window, such as a run's logs, that window opens in front of the Workbench and
blocks only the Workbench, never the editor. Each row's context menu has its
own list, the commands you use most first and the rest under **More**, and
`Shift+F1` reads it with the keys:

- **An issue:** Comment, Close or Reopen, Labels, Assignees, Milestone,
  Projects, Edit Title, React, View Timeline, Read as Document, Summarize
  Discussion, Assign to Copilot, Lock or Unlock Conversation, Pin or Unpin,
  Transfer Issue to another repository with the same owner, Check or Uncheck
  a Task, Convert Tasks to Sub-issues, Create Branch for This Issue, Unlink
  Branch, Set Issue Type, Reorder Sub-issues, Relationships, Issue Fields,
  Delete Issue, and Start in Local Worktree.
- **A pull request:** Review (Enter), File Differences, Comment, Merge, Why
  Can't I Merge?, Merge Selected, Auto-Merge, Reviews, the merge queue, Open
  Patch in Editor, Revert Pull Request, Resolve Conflicts in a Worktree, and
  the rest. Merge asks how (Squash and merge, Merge commit or Rebase), then
  asks you to type the pull request's number before anything happens,
  because a merge changes the branch for everyone.
- **A workflow run:** Jobs and Logs (Enter), What Failed, Re-run Failed Jobs
  Only, Re-run Workflow, Re-run One Job, Cancel Run (`Ctrl+Cancel`, the
  Ctrl+Break key), Force Cancel, Download Logs, Delete Logs, Earlier
  Attempts, View Artifacts, Combined Check Status, Review Pending
  Deployments, Approve Run from a Fork, and Delete Run.
- **A workflow:** its Runs (Enter), Run Workflow on Branch, Turn Workflow On
  or Off, and Edit Workflow.
- **A release:** its Assets (Enter), each with Download, Copy Link,
  Attestations, Properties (to rename a file or change its label) and Delete
  Asset; Edit Release; Draft Release Notes; Upload Asset; Release Evidence;
  and Delete Release. A draft opens on its sheet too, and deleting one says
  that a draft has no tag to delete.
- **A branch:** its Commits (Enter), Compare With Default, Compare Branches,
  Merge Into, Download Source, Copy Name, and Delete Branch, which asks you to
  type the branch name.
- **A commit or a tag:** Open, Commit Comments, to read and write comments
  on the commit and its lines, and Compare With Previous. A commit also has
  Set Status.
- **A tag**, besides: Read Tag Message, Download Source, and Delete Tag.
- **A label:** Find Issues with Label (Enter), Edit Label and Delete Label.
- **A milestone:** Find Issues in Milestone (Enter), and Delete Milestone.
- **A security alert:** Open, Dismiss or Reopen Alert, with a reason, Copilot
  Autofix, and Show Every Place.
- **A discussion:** Open Discussion Thread, to read and reply, and Read as
  Document.
- **A file or folder:** Open in Editor or Open Folder, and Who Owns This?,
  which names the CODEOWNERS rule.
- **An Actions cache:** Show Details and Delete Cache.
- **A runner:** Show Details, Runner Labels, Remove Runner, Open on GitHub
  (its settings page) and Copy Link.
- **A package:** Show Details, Show Versions, Restore Package Version, Delete
  Package Version and Delete Package.
- **A security advisory:** Show Details, Publish or Close Advisory, Request
  CVE, Open on GitHub and Copy Link.
- **A key:** Show Details, Delete Key and Open on GitHub.
- **A webhook:** Show Details, Ping, Send Test Push, Turn On or Off, Recent
  Deliveries, Change Address or Secret, and Delete Webhook.
- **A deploy key or an autolink:** Show Details, Delete, and Open on GitHub.
- **An environment:** Show Details, Deployments, Secrets, Variables, Branch
  Policies, Protection Rules, and Delete.
- **A codespace:** Show Details, Start, Stop, Change Machine, Export to a
  Branch, Publish to a New Repository, and Delete.
- **A GitHub Pages site:** Show Details, Check Site, Rebuild and Turn Off
  Pages.
- **The wiki:** Open on GitHub and Clone Wiki.
- **A sponsorship:** Show Details and Cancel Sponsorship. **A sponsor tier:**
  Show Details and Sponsor at This Tier.
- **A notification:** Open, Mark Read, Mark Done, Unsubscribe from Thread, and
  Snooze for One Day. Snoozing hides it in the Workbench on this computer
  until tomorrow and changes nothing on GitHub; Unsnooze Locally brings it
  back.
- **An invitation:** Accept Invitation and Decline Invitation.
- **A repository:** Open, Star or Unstar, Watch or Unwatch, Clone, Send
  Repository Dispatch, Pin, and Star Lists; in Star Lists, Rename or Delete
  Star List too.
- **A person:** Open, and Follow or Unfollow.
- **A team:** Members and Access, Pending Invitations and Delete Team.
- **An organization:** Open, Roles, and Rulesets (Chapter 13).
- **A watch:** Edit Watch, Pause or Resume Watch, Check Watches Now, Remove
  Watch and Why?.

Summarize Discussion uses the AI connection of the editor that opened the
Workbench, and Start in Local Worktree uses its local Git. When the editor
has not given the Workbench either one, the row is greyed and says why.

### What you hear afterwards

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

`F9` says the last result even when you only heard its sound. Chapter 10 lists
the refusals and what to do about each.

## More commands on rows

Many rows also have commands that make one call to GitHub and say what came
back, or show a longer answer in a window to read and copy. They are on the
row's context menu (`Shift+F10`, under More when the menu is long) and on
the Item menu. Each asks before it changes anything, and anything that
holds a token (a runner's setup or removal commands) goes to the clipboard
and is never said or shown. Here they are by what you are doing.

### Learning about a repository

- **A repository:** Languages, License, Star History, Sponsor Links (its
  FUNDING.yml), Dependency Manifests, SBOM Report, and Compare Dependencies...
  (between two branches, tags or commits, with licences and known
  vulnerabilities).
- **A commit:** Branches at This Commit, and Check Run Details... (a check's
  summary and every annotation).
- **A release:** GitHub's Release Notes..., the notes GitHub writes from the
  changes since another tag.

### Looking after a repository

- **A repository:** Mark Its Notifications Read, Set a Custom Property...,
  Ruleset History..., Require Sign-off on Web Commits..., Fork Workflow
  Settings and Fork Workflows from Private Repositories....
- **An environment:** Pin Environment, Unpin Environment and Move
  Environment....

### Builds and runners

- **A workflow run:** Read a Step's Log..., one step at a time.
- **A commit:** Re-run a Check Suite....
- **Runners:** in a repository's Runners or an organization's, Just-in-Time
  Runner... (a runner that takes one job) and Is a Runner Version
  Retiring?...; in an organization's, New Organization Runner...; on a
  runner, Removal Commands..., and on an organization's runner Add Runner
  Label... and Remove Runner Label.... **A runner group:** Runners in This
  Group, Hosted Runners in This Group, Add a Runner to This Group...,
  Remove a Runner from This Group....

### Reviews, issues and discussions

- **A pull request:** Re-request Review..., Dependency Review (what it
  changes in the dependencies, with licences and known vulnerabilities), and
  Dependabot Commands....
- **An issue:** Link a Pull Request That Closes It... and Unlink a Pull
  Request....
- **A discussion:** Close Discussion... (resolved, outdated or a duplicate),
  Reopen Discussion, Delete Discussion..., Upvote, Remove Upvote, Vote... (in
  its poll), Edit a Comment... and Delete a Comment....
- **A commit:** the reactions on its comments: Reactions on a Commit
  Comment..., React to a Commit Comment..., Remove My Reaction from a Commit
  Comment....

### Security

- **A repository:** Secret Scanning History, and Allow a Blocked Secret...
  (the placeholder id `git push` printed, and why).
- **A secret scanning alert:** Where It Was Found.
- **A security advisory:** Advisory Comments, Comment on Advisory..., Edit an
  Advisory Comment..., Make a Private Fork for the Fix.
- **An organization:** Security Overview (open alerts in every repository,
  worst first; a kind GitHub will not show you is said, never counted as
  none), and Members Without Two-Factor.

### Organizations and teams

- **An organization:** Dependabot Repository Access, Give Dependabot a
  Repository..., Take a Repository from Dependabot..., Dependabot's Default
  Access..., Make Someone an Outside Collaborator..., Define a Custom
  Property..., Set Repositories' Custom Property..., New Team..., Accept
  Membership, My Activity Here, Require Sign-off on Web Commits..., and
  Follow Organization and Unfollow Organization.
- **A team:** Pending Invitations and Delete Team.... **An invitation to an
  organization:** Teams It Adds To.

### Projects

- **A Project:** Add Draft Issue..., New Field..., Delete Field..., Post
  Status Update..., Link to Repository..., Unlink from Repository...,
  Template..., Copy Project..., Delete Project..., New View... and Items in a
  View....
- **A Project, inside:** Rename a View..., Delete a View..., Rename a
  Field..., Add an Issue Field..., Edit a Draft..., Make a Draft an
  Issue..., Move an Item..., Archive an Item..., Restore an Archived
  Item..., Remove an Item... (asks first), Edit a Status Update..., Delete a
  Status Update..., Delete a Workflow..., Share the Project..., Link a
  Team... and Unlink a Team....

### Your own account

- **Your sponsorships:** Set Up a Sponsors Profile..., New Sponsor Tier...
  and Patreon Sponsorships...; on a sponsorship, Sponsorship Preferences...;
  on one of your tiers, Publish Tier and Retire Tier....
- **Your emails:** Email Visibility.... **Your profile:** Interaction
  Limits, Limit Interactions... and Lift Interaction Limits.

### Copilot

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
- **Copilot in an organization:** Copilot Plan, Copilot Seats, A Member's
  Copilot Seat..., Give Copilot Seats..., Take Copilot Seats Away..., Give
  Teams Copilot..., Take Copilot from Teams..., Copilot Usage Report, Copilot
  Agent Access and Copilot Content Exclusions. **On a repository:** Copilot
  Agent Configuration and Copilot Review Settings. These are Copilot
  Business's, which an organization buys on any GitHub plan. Giving or taking
  a seat changes what the organization pays, so you need to own the
  organization, and each asks first, naming the people and the organization.
  Copilot's policies are read here and changed on GitHub's site.

A few of these use parts of GitHub newer than the description QUILL was
built against (closing references, a Project's views and issue fields).
Those first read from GitHub what the change needs, and if GitHub has
changed it, they send nothing and say to use Open on GitHub instead.

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
  **Help > Tutorials** (`Ctrl+F2`) goes straight there.
- **What Changed** says what is new.
- **Tips** holds QUILLBert's tips, one short thing worth trying in each.
  They wait in this list and are never pushed at you.
- **Ask a Person** says how to write to support@community-access.org, and
  has **Report a Help Problem**: for help that was wrong, missing or hard to
  follow. Enter opens a message in your own email, already saying where you
  were and the last thing the Workbench said, for you to change and send.
  The Workbench sends nothing, and no token or password is ever in it.

Once in a while a tip also comes to you at the right moment: the third time
you do something the long way (arrow through a long list without the filter,
open Properties on one row after another, press Load More again and again),
the tip for the short way is added to the end of the details pane, once, and
is not spoken, so it interrupts nothing. **Offer a tip when it would help**,
in Workbench Options, General, turns those off; they all stay in Tips. Words
are explained by QUILLBee, QUILLBert's friend, in one line each. **Plain
help, without QUILLBert and QUILLBee**, in Workbench Options, General, says
the same words without the two names.

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
| `Ctrl+F2` | Help > Tutorials: the GitHub lessons, under Help and Learning |
| `F11` | Say or Type a Command, in this window |
| `Ctrl+Alt+Shift+F1` | What Can I Say Here: what F11 can do in this window |
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

## Say or Type a Command

`F11` works here as it does in the editor, with this window's own commands.
Type what you want, such as "show the pull requests", "what failed" or "how
much rate limit is left", and press `Enter`. Only the Workbench's commands are
offered, and each runs exactly as its menu row would: a change still asks and
previews first, and a Read Only account is still refused. Commands that send
a change by themselves, such as Merge or Close, are not offered from a
sentence; their menu rows and keys still work.

**Help > What Can I Say Here?** (`Ctrl+Alt+Shift+F1`) lists what you can ask
for in this window, with an example for each. In this window, requests are
matched on this computer only and are never sent anywhere.

For a change to many items at once, described in words, use **Tools >
Plain-Language Batch...** (`Ctrl+Shift+S`) instead. Chapter 13 covers it.

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

## The GitHub API Console

**Tools > GitHub API Console...** (`Ctrl+Shift+J`) sends any GitHub REST
request or GraphQL query you type, for the times no command does what you
need. It completes paths from GitHub's own description of its API, says what
a request does and what it needs before you send it, and shows the answer as
a tree you can arrow through. A `GET` only reads. Any other method changes
something, so it needs Full in the Workbench and asks you to type the method
before it sends. Dry Run stops it like any other change.

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

## Is it GitHub, or is it me?

When GitHub is slow or failing, the Workbench's errors can look like your own
mistake. **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) reads GitHub's
public status page, www.githubstatus.com, and says whether GitHub says
everything is working, which parts are slow or down, and any incident GitHub
is working on, with its latest update. It asks the first time, reads the page
only when you choose the command, and is greyed in Safe Mode. Chapter 10 has
more.

## Workbench Options

GitHub's preferences live in the Workbench, not in the editor's Options:
**Tools > Workbench Options...**, `Ctrl+Shift+O`. It has five pages:

- **General:** where the window opens (Inbox, Start Here, or wherever you
  were last time), whether lists show a few columns or every column, and the
  order and state issues and pull requests open in.
- **Notifications and Inbox:** how often GitHub is checked, from 5 minutes to
  a day, whether each check plays a short sound, whether a new notification
  may interrupt speech, and whether read notifications are listed too.
- **Lists:** whether each column's name is said before its value.
- **Repositories:** your pinned repositories and favorites.
- **Privacy:** whether Insights loads the repository Health Snapshot, and
  whether the first few visits to a place start with a short "First time
  here?" paragraph.

Lists also has **Short rows for braille**: each list row becomes one short
line for a braille display, the number and title first, no column names, and
short words (`cl` for closed, `PR` for pull request, `3c` for three comments,
`9 Nov` for a date). Nothing is cut off, and Details still says everything.
Columns... still chooses what the line holds. General has **Offer a tip when
it would help** and **Plain help, without QUILLBert and QUILLBee**.

Each account's Workbench level, Read Only, Organize or Full, is not here: it
is **Account > Roles and Access > Workbench Level for This Account...**
(Chapter 13).

You never have to open Workbench Options: the Workbench works as it comes.

## A walk-through: finding your way on the practice repository

This takes about five minutes and changes nothing on GitHub. If you have not
made the practice repository yet, press `Ctrl+Alt+P` first and say yes.

1. Open the Workbench from **GitHub > Open GitHub Workbench**. You hear
   "GitHub Workbench" and the place it opened on.
2. Press `Ctrl+9`. You are on Start Here; `F6` and then the arrow keys read
   its details. Press `Shift+F6` to come back to the tree.
3. Press `Ctrl+L`, type `quill-practice`, with your login in front, such as
   `jeff/quill-practice`, and press Enter. The repository gets a place of its
   own and you are on it.
4. Press `Ctrl+Shift+1`. You are on its Issues, and the list loads three
   issues. Press `F6` to reach the list.
5. Arrow to the typo issue and press `Shift+F1`. You hear what you can do
   with an issue, with each key.
6. Press `Alt+Enter`. Its Properties sheet opens; `Escape` closes it without
   changing anything.
7. Press `Ctrl+Shift+4`. You are on Actions, Runs, with the practice run that
   failed on purpose. Press `Ctrl+Shift+W` to hear what failed.
8. Press `Alt+1`. You hear where you are. Press `Backspace` to go back to
   the issues, with the typo issue selected again.
9. Press `Ctrl+F1`. This guide opens at the chapter for where you are.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has the GitHub lessons. For this chapter:

- **Make a repository to practise on:** makes `quill-practice` and looks
  round it.
- **Try a command without sending it:** turns Dry Run on, tries closing an
  issue, and turns it off again.
- **Protect a branch:** protects main on the practice repository from
  Settings > Branch Protection, reads the rule on the branch's Protection
  page and in Settings > Rulesets, and takes it off again.
- **Use the API Console:** a read with the GitHub API Console.

# Chapter 13: Properties, filters and permissions

## What this chapter covers

On GitHub's website, the facts about an issue or a repository are spread over
a page, with the controls to change them tucked into menus and side panels.
In the Workbench, everything about one thing is on one sheet, and the sheet is
where you change it. This chapter is about that sheet, and about the two
questions that come with changing things: which ones, and am I allowed?

You open a Properties sheet and change a field, change many things at once,
say a change in words, undo a change, and filter and shape a list. Then you
look at permissions: what you are allowed to do, how to get what you are
missing, what the Workbench itself allows each account, and who else has
access and why.

By the end you will be able to change anything the Workbench shows, safely,
and answer "why can't I?" and "who can?" without leaving the window.

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
- An issue's **Issue Fields** page edits its organization's issue fields,
  each with its own kind of control: a date, a number, a single choice or
  text. Saving sets only the fields you changed and reads the issue again to
  check GitHub kept them; emptying a field clears it. A field with several
  choices, or of a kind QUILL does not know, stays read only. Without triage
  access the page says why each field is locked.
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

The rest of the relationships, and every one as a row on the context menu
too, each saying its outcome in one sentence:

- **A repository's You page** also has **Star lists** (your lists, the ones
  holding it checked, as Star Lists... sets them), **Forked by you** (check
  it to fork the repository to your account; a fork is a repository of its
  own, so clearing the box is refused and says where to delete it), and the
  read-only **Sponsoring the owner**. The rows **Fork...** and **Sponsor the
  Owner...** are on the repository's context menu: Sponsor the Owner opens the
  owner's Sponsor tiers, and nothing is charged until you choose a tier with
  Sponsor at This Tier... and type their name.
- **In Favorites** and **Pinned in the Workbench** close a repository's You
  page, and In Favorites an issue's and a pull request's. These live on this
  computer, not on GitHub, so they change at once, as the Favorites and Pin
  rows do.
- **Subscribe or Unsubscribe...** on an issue, a pull request, a discussion
  or a commit: all activity, or only when you take part or are mentioned.
- **Block or Unblock...** on a person.
- **Block from Organization...** on an organization (it asks whose account)
  and on a member in its Members list; its Blocked People list unblocks.
  **Leave Organization...** asks first. **Your Invitation** says whether the
  organization has invited you: Accept Membership joins, and since GitHub's
  API cannot decline an organization's invitation, it gives the page where
  GitHub does. A repository's invitations have Accept and Decline rows.
- **React to a Comment...** on an issue or a pull request (its conversation
  and its line comments) and on a discussion (comments and replies): choose a
  comment, then a reaction; one you gave already is taken back. On a commit,
  **React to a Commit Comment...** reacts to its comments, and **Commit
  Comments...** reads and adds them. GitHub's API reacts to a commit's
  comments, never to a commit itself.

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
- **A field GitHub needs is never sent empty.** Emptying a title, a name, a
  tag or a retention period leaves it as it is, and QUILL says so: "Title
  cannot be empty on GitHub, so it was left as it is." A number box must hold
  a whole number; anything else is said before anything is sent.
- **Rulesets, branch protection and environments are sent whole,** so each
  save rebuilds them from what GitHub has at that moment. A rule somebody
  else changed while your sheet was open is kept, including one you chose
  Keep Theirs for.
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
  (`F8`) runs the failed ones again. Each is read from GitHub afresh first,
  so a field that took the first time counts as already done.
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

Undo reads the object from GitHub first, so a milestone goes back as the
milestone it was and a ruleset keeps its other rules. If somebody changed the
field since, Undo stops and says so rather than overwrite them. A redone
change can be undone again. A change GitHub cannot reverse says why in its
preview, before you save it, and again if you ask to undo it: a secret's old
value is never given back, and taking an item out of a Project deletes its
field values there.

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

### Filtering every other list

Branches, tags, commits, releases, workflows, runs and the other lists are
read whole, so the words before a colon are checked here, over the rows
already loaded. Each list answers its own:

- **Branches:** `name:`, `protected:`, `ahead:`, `behind:`, `author:` (the
  last commit's) and `committed:` (its date).
- **Tags:** `name:` and `sha:`. **Commits:** `author:`, `committed:`,
  `message:` (words in it) and `sha:`.
- **Releases:** `tag:`, `name:`, `draft:`, `prerelease:` and `created:`.
  **Release assets:** `name:`, `size:`, `downloads:`, `type:` and `updated:`.
- **Workflows:** `name:`, `path:` and `state:`. **Runs:** `workflow:`,
  `branch:`, `event:`, `status:`, `conclusion:`, `created:` and `sha:`.
- **Every other list** (repositories, labels, milestones, notifications,
  packages and the rest): `name:`, `repo:`, `owner:` and `updated:`.

A name takes `*` as a pattern (`name:release-*`). A minus in front leaves
those out (`-conclusion:success`). Numbers and dates take `>`, `<`, `>=`, `<=`
and a range with two dots (`ahead:>=3`, `created:2026-01..2026-06`); a date
can be just a year or a month. `no:repo` keeps the rows with none. The Items
cell of the status bar says how many the filter kept of how many loaded, such
as "Filtered here: 2 of 3 loaded. Load All to be sure.", and names any word
this list cannot filter on, so nothing is quietly ignored.

The Search place's lists send the whole box to GitHub instead, so there
GitHub's own search terms work: `language:` and `stars:` for repositories,
`committer:` for commits, `location:` for people.

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
someone else's organization. Organize allows organizing and comments, such as
labels, assignees, reactions and closing issues, but not access, settings or
deleting. Full allows everything your access allows. Safe Mode makes every
account Read Only.

Every change is checked against the level once, before anything is sent,
whether it comes from a menu row, a sheet, a batch, `F11` or the API
Console. A change the level does not allow is refused in one sentence naming
the level it needs: "Cannot delete the label: it needs Full in the
Workbench, and this account is Organize; Account, Roles and Access,
Workbench Level for This Account changes it." On a sheet, the reason is
beside each locked field. `Alt+5` says what you can do where you are.

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

- **My Access Here...**, your role on this repository and where each part
  comes from;
- **View As Role...** and **Compare Roles...**, what a role may do, read-only;
- **Why Can't They?...**, what stops a person doing something, and who can
  change it;
- **Access Review...**, every person, team and repository in an organization
  with their role and where it comes from, copied as CSV too;
- **Bulk Access Changes...**, one team or person on many repositories at
  once, previewed person by person, with a result per change;
- **Access Templates...**, named sets of access, such as Contributor: write
  on these repositories and member of a team. Choose New Template..., give it
  a name, and write one line for each place: `write on owner/name` (read,
  triage, write, maintain or admin), `member of org/team` or `maintainer of
  org/team`, and `member of org` or `owner of org`. A line it cannot read is
  said and left out. Templates are kept on this computer, for this account,
  and making one sends nothing;
- **Apply Access Template...**, everything a template holds, given to one
  person by login in one batch: organization first, then teams, then
  repositories. The preview says every change in words and asks once; each
  change then has its own result and its own line in Change History. It
  needs Full for this account in the Workbench, as any access change does;
- **Compare Accounts...**, two of your signed-in accounts on this repository,
  side by side;
- **Act As Another Account...**, one action done as another of your
  signed-in accounts.

Every one of these answers from what GitHub itself says, and each line names
the reply it came from, such as "(GitHub: /repos/acme/web permissions)". My
Access Here reads the repository's permissions, GitHub's own
`viewerPermission`, your role name (a custom role is named too), your place in
the organization and its base permission, the teams that give you access, the
rules on the default branch, and this sign-in's scopes. Why Can't They? reads
the person's real role from GitHub rather than asking you for it, then the
rules GitHub says apply to the branch, and names the one that stops them.

Two things GitHub does not say, and the Workbench says so rather than
guessing. GitHub's API does not list what a role may do, so View As Role and
Compare Roles show GitHub's documented defaults for its built-in roles, say
that is what they are, and then list who on this repository GitHub says has
each role; a custom role is named, but what it adds is on the organization's
Repository roles page. And GitHub does not list a fine-grained token's
permissions: My Access Here says so, and when GitHub refuses something, the
Workbench says the permission GitHub named in its refusal. When GitHub will
not tell your account something at all (only people with write access may
read others' roles, for example), the answer says it cannot be known.

Bulk Access Changes reads each repository's current role first, and the
preview says it per person: "kelly on acme/web: write now, maintain after."
A repository where they already have that role is listed as "nothing is sent",
and nothing is.

#### Compare Accounts and Act As

With more than one account in Manage GitHub Accounts, **Compare Accounts...**
asks GitHub, with each account's own sign-in, about the open repository: its
role, `viewerPermission`, its role name and its sign-in's scopes, then what
one may do that the other may not. Before showing anything under an
account's name, it asks GitHub whose the saved token is; if GitHub names
somebody else, nothing is shown for that account, and you are told to sign in
again.

**Act As Another Account...** does one thing as another of your accounts and
then forgets it: approve the selected pull request (approving your own needs
a second account), comment on the selected issue or pull request, close or
reopen it, or star the repository. You choose the account, then the action.
The question names the account and its server ("As kelly-test on github.com,
not as you: approve pull request #7"), and so does the result ("Approved pull
request #7 in acme/web as kelly-test."). Act As is held to that account's own
Workbench level, not yours, and Safe Mode stops it like any write. It checks
whose the token is first, and sends nothing if it is not that account's. Your
own account, its lists and its remembered reads are never touched: everything
QUILL remembers is kept per account.

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

`Ctrl+N` in a repository's **Settings > Rulesets** makes a new ruleset. It
asks, one question at a time, for its name; whether it guards branches or
tags; which ones (the default branch, every one, or names matching a pattern
such as `release/*`); its rules, as a check list (a pull request before
merging, no force pushes, no deletion, linear history, signed commits, no
creating, no updating); how many approvals a pull request needs, when that
rule is checked; and whether it is on now or made off and turned on later.
Then it reads the whole ruleset back to you in one sentence and asks before
anything is sent, with No as the default. Its other rules and settings are on
its sheet afterwards. GitHub's Evaluate mode is not offered, because GitHub
keeps it for Enterprise organizations. To copy a ruleset to other
repositories, use Add to Missing under Across Repositories (Chapter 12).

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

## A walk-through: labelling two issues, then taking it back

This uses the practice repository (**Help > Practice on GitHub...**,
`Ctrl+Alt+P`). It changes two practice issues and puts them back.

1. In the Workbench, go to the practice repository and press `Ctrl+Shift+1`
   for its Issues. Press `F6` until you reach the list.
2. Press `Ctrl+E`, type `no:label`, and press Enter. The list narrows to the
   issues with no label. `Alt+7` says the filter in words.
3. Press `F6` to come back to the list, select the first issue, then hold
   Shift and press Down Arrow to select the second as well. `Alt+2` says how
   many are selected.
4. Press `Alt+Enter`. One sheet opens, "Properties of 2 issues". `Ctrl+Tab`
   moves through its pages to the one with the labels.
5. Tab to the labels list and check "practice: question" with Space. You hear
   "practice: question, on".
6. Press `Ctrl+Enter`. You hear the preview, "Change 2 issues: add practice:
   question.", and Enter goes ahead. The results list says Done for each.
   Escape closes it.
7. Press `Ctrl+Shift+H` for Change History. Each issue's change is a row of
   its own, newest first. Escape closes it.
8. Back in the list, press `Ctrl+Z`. The label comes off the issue changed
   last, and you hear what was undone. Press `Ctrl+Z` again for the other.
9. Press `Escape` in the filter box to clear the filter.

To try the same without changing anything, turn on Dry Run (`Ctrl+Alt+D`)
before step 6: you hear what would have been sent, and nothing is.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has the GitHub lessons. For this chapter:

- **Label, comment on and close an issue:** one issue's changes, on the
  practice repository.
- **Give someone access:** an access template, applied to a person, stopping
  at the preview so nothing is sent.

# Chapter 14: GitHub in QUILL Lite

## What this chapter covers

You use QUILL Lite, or both editors, and want to know what is different about
GitHub. Very little is. The GitHub Workbench is one piece of shared code that
both editors open, so every place, menu, key and sheet in this book works the
same in QUILL Lite.

This short chapter lists the few places where the two differ: how you open
the Workbench, the GitHub menu, the handful of rows that need something only
QUILL has, and the guide and lessons. Read it once and you can move between
the two editors without thinking about it.

## One Workbench, two editors

- The Workbench is the same window in both, with the same tree, menus, keys,
  Properties sheets and help.
- Your accounts are shared: one you add in either editor is there in both.
- GitHub is in every QUILL Lite profile, WordPad and Notepad included. Tools >
  Customize Features has no switch for it.

## Opening it

| | QUILL | QUILL Lite |
| --- | --- | --- |
| The Workbench | File > Open from Remote > GitHub Workbench... | File > GitHub Workbench... (`Alt+F`, then `G`) |
| Clone a repository | File > Open from Remote > Clone Repository... | File > Clone Repository... (`Alt+F`, then `Y`) |
| Sign in | File > Open from Remote > Manage GitHub Accounts... | File > Manage GitHub Accounts... (`Alt+F`, then `H`) |
| This guide | Help > Open GitHub Guide | Help > Open GitHub Guide |
| A pasted link | File > Open from Remote > Open GitHub Reference... | `Ctrl+L` in the Workbench |

Inside the Workbench, **Account > Manage GitHub Accounts...**
(`Ctrl+Shift+K`) works in both.

If you open the Workbench in QUILL Lite before you have signed in, it says
"You are not signed in to GitHub" and offers **Manage GitHub Accounts...**,
**Continue as Guest** and **Cancel**. QUILL opens straight on Start Here
instead, and Start Here says how to sign in.

## The GitHub menu

**View > GitHub Workbench Mode** works in both, and adds a GitHub menu after
Tools. QUILL Lite's GitHub menu is QUILL's with QUILL's own rows left out, so
the letters are the same:

- **In both:** Leave Workbench Mode, Open GitHub Workbench, Inbox, This
  Repository's Issues, This Repository's Pull Requests, Actions Runs, the From
  This Line rows, Clone Repository..., Manage GitHub Accounts... and Open
  GitHub Guide.
- **QUILL only:** Open GitHub Address..., Commit to GitHub..., Sync Folder
  with GitHub... and the Local Git submenu, because they are about a copy of
  the repository on your computer that QUILL looks after.

From This Line is a submenu in QUILL and rows in the menu itself in QUILL
Lite, with the same letters either way.

In QUILL Lite, the mode works in the empty window too, the one left when you
close every document. With the mode on there, that window is a GitHub
launcher with nothing to write in.

## Rows that need something only QUILL has

A few Workbench rows lean on the editor that opened the Workbench. QUILL Lite
does not give the Workbench those things, so these rows are greyed there, and
`Shift+F1` says why:

- **Summarize Discussion**, and the diff window's AI explanation, use QUILL's
  AI connection.
- **Start in Local Worktree...** and **Resolve Conflicts in a Worktree...**
  use QUILL's local Git.
- **Run Workflow on Branch...** (`Ctrl+Shift+R`) hands over to QUILL's Dispatch
  Workflow command.
- Some rows of **Repository > Repository Actions...** (`Ctrl+Shift+G`) run one
  of QUILL's own repository commands, such as Create Release or the GitHub
  CLI's Codespaces commands. QUILL Lite has no such command, so the row is
  greyed. The Workbench's own places do the same jobs where they can: a
  repository's Releases place makes a release, and Code > Codespaces starts
  one.

Everything else, every write included, works the same in QUILL Lite once you
are signed in.

## Files from GitHub

**Open in Editor** (`Ctrl+Enter`) on a file, and a pasted link to a file, open
the file's text in a new untitled document in QUILL Lite, because QUILL Lite
does not commit back to GitHub. **Save As** keeps a copy on your computer. In
QUILL, the file opens as itself, and **Commit to GitHub...** saves it back.

**Read as Document...** (`Ctrl+Shift+I`) works in both: it opens an issue,
pull request or discussion in the editor as one document, a heading per post.

## The guide and the lessons

**Help > Open GitHub Guide** in QUILL Lite opens this book, as QUILL Lite's
own copy. `Ctrl+F1` in the Workbench opens it at the chapter for where you
are, in whichever editor opened the window.

**Help > Tutorials** (`Ctrl+F2` in the Workbench) goes to Tutorials, under
Help and Learning. QUILL has the GitHub lessons in its own Tutorials window
too, and a lesson there notices when you have done each step. QUILL Lite has
no GitHub lessons of its own, so Enter on a lesson walks it in the Workbench
instead, one step at a time, and you move on yourself.

## A walk-through: the same job in both editors

1. In QUILL Lite, press `Alt+F`, then `G`. The Workbench opens on Inbox.
2. Press `Ctrl+L`, type `community-access/quill`, and press Enter.
3. Press `Ctrl+Shift+1` for its Issues, `F6` to the list, and arrow to an
   issue.
4. Press `Ctrl+Shift+I`. The issue opens in QUILL Lite as a document, a
   heading per post. Close it without saving.
5. Back in the Workbench, press `Shift+F1` on the issue. Summarize Discussion
   is listed as greyed, with the reason. Press Escape.
6. Open QUILL, and its Workbench. You are signed in with the same account.
