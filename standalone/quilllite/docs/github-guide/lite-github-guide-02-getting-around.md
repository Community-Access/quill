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
tree, with you on it. A compare link opens the comparison. `Ctrl+G` (**File >
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

---

- Previous: [Chapter 1: Getting started](lite-github-guide-01-getting-started.html)
- Next: [Chapter 3: Your inbox and your work](lite-github-guide-03-inbox-and-your-work.html)
- [Contents](lite-github-guide.html)
