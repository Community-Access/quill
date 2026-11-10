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
- **Files** lists the default branch a folder at a time. Enter on a folder
  opens it, and the first row, Up one folder, comes back out. Enter on a file
  opens it in the editor.
- **Settings** lists the settings you can change, General and Branch
  Protection. Enter on one opens the same dialog the editor has always used,
  and that dialog asks before anything changes.
- **Repository Actions**, `Ctrl+Shift+G`, lists everything else you can do
  with the repository: star it, fork it, clone it, Codespaces, and its
  administration.

`Ctrl+N` makes something new where you are: an issue in Issues, a saved search
under Saved Searches, a pin under Pinned. `Ctrl+Shift+N` asks what to make.

## Search

Choose a search, press `Ctrl+E` to move to the filter box, type, and press
Enter. Plain words narrow the list you are looking at; GitHub's own words, such
as `is:open author:@me label:bug`, ask GitHub. `Ctrl+8` goes to Saved
Searches, and `Ctrl+N` in a search keeps it there.

## People, Gists and Projects

`Ctrl+4` goes to People: who you follow and who follows you. Enter on a person
gives them a place in the tree, with their repositories and activity. `Ctrl+5`
goes to your gists and `Ctrl+6` to Projects; each repository's own Projects
are under it.

Two places are shown but not built yet, so their keys already land somewhere
that says what they will hold: Watches (`Ctrl+7`) and Across Repositories
(`Ctrl+0`).

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
| `Ctrl+D` | Keep the selected row under Favorites, or take it out |
| `Ctrl+Shift+C` | Copy the selected row's address |
| `Shift+Enter` | Open it on GitHub, in your browser |
| `Delete` | Remove it safely: mark a notification done, close an issue after asking |

Anything the Workbench does not do itself yet opens GitHub Items on that one
item, in front of the Workbench, so nothing you could do before is out of
reach.

## Hearing where you are

`Alt+1` to `Alt+9` say something and move nothing: where you are, what is
selected, the selected item's state, the counts, your access, GitHub's hourly
allowance, the filter, what is loading, and your account. `F9` says the last
result again, and `Shift+F9` explains it: what it means, and what you might do
next.

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

## Workbench Options

GitHub's preferences live in the Workbench, not in the editor's Options:
**Tools > Workbench Options...**, `Ctrl+Shift+O`. It has five pages. General
says where the window opens and how lists start. Notifications and Inbox says
how often GitHub is checked, whether each check plays a sound, and whether a
new notification may interrupt speech. Lists, Repositories (your pinned
repositories and favorites) and Privacy follow. Privacy is also where you can
go back to the classic GitHub Items and Explore GitHub windows for this
release, by checking Use the classic GitHub windows.

You never have to open it: the Workbench works as it comes.

---

- Previous: [Chapter 11: Keyboard reference](lite-github-guide-11-keyboard-reference.html)
- [Contents](lite-github-guide.html)
