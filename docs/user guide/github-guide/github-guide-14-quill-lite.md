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

---

- Previous: [Chapter 13: Properties, filters and permissions](github-guide-13-properties-filters-permissions.html)
- Next: [Appendix A: What GitHub needs for each part of the Workbench](github-guide-appendix-a-features.html)
- [Contents](github-guide.html)
