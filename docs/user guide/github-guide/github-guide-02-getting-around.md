# Chapter 2: Getting around

## What this chapter covers

This chapter is about moving, not doing. It walks through the GitHub Items
window and the Explore GitHub window control by control, explains the three
keys that do most of the moving, and covers context menus, searching,
favorites, coming back where you left off, pasting a link, and GitHub's hourly
allowance. Every later chapter builds on it.

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

**Explore...** (`Alt+E`) in GitHub Items opens Explore GitHub. In QUILL,
**Tools > Git and GitHub > GitHub > Notifications...** opens it too, straight at
your notifications.

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

---

- Previous: [Chapter 1: Getting started](github-guide-01-getting-started.html)
- Next: [Chapter 3: Your inbox and your work](github-guide-03-inbox-and-your-work.html)
- [Contents](github-guide.html)
