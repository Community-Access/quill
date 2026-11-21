# Tutorial 8: GitHub inside QUILL and QUILL Lite

**Goal:** learn what QUILL can do with GitHub and with Git on your own
computer: open and save files, work with issues and pull requests in the
GitHub Workbench, look after a repository, and sort out a merge conflict,
without opening a browser or a terminal.

The GitHub Workbench is one window for everything GitHub, and it is the same
window in QUILL and QUILL Lite. In QUILL Lite you open it with **File > GitHub
Workbench...** (`Alt+F`, then `G`). QUILL's file opening, repository commands
on the Tools menu and Local Git commands, in parts 1, 4, 5 and 6, are QUILL's
own.

There are three kinds of work here, and you can use any of them on its own:

- **The GitHub Workbench**: your inbox, issues, pull requests, runs, releases
  and repositories. Reading public repositories needs no account; anything
  that changes GitHub needs you to sign in.
- **Repository commands in QUILL**: create, fork and configure repositories,
  and commit several files at once.
- **Local Git**: accessible merge-conflict resolution and interactive rebase.
  It needs no GitHub account at all, and works on any repository on your
  computer.

**A shorter way to all of it.** Turn on **View > GitHub Workbench Mode**
(`Alt+V`, then `K`), in either app. A **GitHub** menu joins the menu bar after
Tools (`Alt+G`), with the doors into the Workbench: **Open GitHub Workbench**,
**Inbox**, **This Repository's Issues**, **This Repository's Pull Requests**
and **Actions Runs**. The menu paths in this tutorial are the ones you see with
the mode off; with it on, look in the GitHub menu instead. Turn the mode off
from the same place, with **GitHub > Leave Workbench Mode**.

The [GitHub Guide](../user%20guide/github-guide/github-guide.md) has the
whole story; each part below names the chapter to read next.

## 0. Sign in (once)

The first time you touch any GitHub feature, QUILL asks once whether it may
connect to GitHub. Choose **Continue**, then:

1. **File > Open from Remote > Manage GitHub Accounts...** In QUILL Lite it is
   **File > Manage GitHub Accounts...** (`Alt+F`, then `H`).
2. **Sign In with GitHub...**, the first button. QUILL puts a short code on
   the clipboard, opens github.com/login/device in your browser, and moves you
   to the code, which it spells out a character at a time.
3. In the browser, paste the code, choose **Continue**, then **Authorize**.
4. Come back to QUILL. The window closes by itself and you hear "Added and
   switched to GitHub account" and your username. Your sign-in is kept in
   Windows Credential Manager or the macOS Keychain, never in a plain file.

The code lasts about fifteen minutes; if it runs out, choose **Sign In with
GitHub...** again for a new one. If you already use GitHub's command-line
tool, **Use GitHub CLI Sign-In...** adds the account `gh` is signed in to
instead. [Chapter 1 of the GitHub
Guide](../user%20guide/github-guide/github-guide-01-getting-started.md) covers
more than one account, Enterprise Server and how much the Workbench may
change.

## 1. Open, edit and save a file (QUILL)

1. **File > Open from Remote > GitHub Repository...**
2. Type an `owner/name` (try `octocat/Hello-World` if you don't have one
   handy) and press Enter.
3. Arrow through the file list: folders first, then files. Enter opens a
   folder or a file.
4. Edit the file, then choose **File > Open from Remote > Commit to
   GitHub...** and type a commit message. QUILL commits to the same
   repository, branch and path. Pressing `Ctrl+S` never does this for you.

If you already have the address, **File > Open from Remote > GitHub File
URL...** skips the browsing: paste a `github.com/owner/name/blob/branch/path`
link.

To work on a whole repository in a folder of your own, **File > Open from
Remote > Clone Repository...** copies it to your computer: type `owner/name`,
choose a folder, and press **Clone**. QUILL Lite has it as **File > Clone
Repository...** (`Alt+F`, then `Y`).

## 2. The GitHub Workbench

**File > Open from Remote > GitHub Items...** opens the GitHub Workbench. The
row keeps its old name; the window is the Workbench. Many of its ideas come
from [GHManage](https://github.com/kellylford/GHManage), Kelly Ford's free
GitHub browser for screen reader users, and we are grateful for it.

The window has a tree on the left that says where you are, a list of what is
there, and the details of the row you are on. `F6` moves between them.

1. Open the Workbench. Signed in, you land on **Inbox**; signed out, on
   **Start Here**.
2. Press `Ctrl+L`, type `owner/name` or paste a GitHub link, and press Enter.
   The repository gets a place of its own in the tree, and you are on it.
3. Press `Ctrl+Shift+1` for its **Issues**, then `F6` to the list. Arrow
   through the rows, and press `F6` again to read the selected issue in the
   details.
4. Press `Ctrl+Shift+2` for its **Pull Requests**, `Ctrl+Shift+4` for its
   Actions runs, and `Ctrl+Shift+6` for its releases. Every repository has the
   same places, in the same order.
5. Press `Shift+F1` on any row. You hear everything you can do with it, with
   each key, and why anything greyed is greyed.

`Ctrl+E` moves to the filter box. Plain words narrow the rows already loaded;
GitHub's own words, such as `is:open label:bug`, ask GitHub. `Alt+Enter`
shows everything about the selected row on one sheet, where you can change
it. Backspace goes back to where you were, and `Shift+Enter` opens the row
on GitHub. `Ctrl+Shift+I` opens an issue or pull request in the editor as one
document, a heading per post.

[Chapter 2 of the GitHub
Guide](../user%20guide/github-guide/github-guide-02-getting-around.md) is a
full tour of the window.

### Reading and reviewing a pull request

Select a pull request and press Enter. The review window opens with the whole
pull request in one sentence: its review decision, its checks, its open
threads and how far behind it is. Below that is the **Pull request outline**,
a tree of the changed files, the conversations on each file, and the checks.

1. Right Arrow opens a branch of the outline and Left Arrow closes it.
2. Select a thread and press Tab to read the whole conversation. Shift+Tab
   comes back.
3. `Ctrl+R` replies to the selected thread, and `Ctrl+Shift+R` resolves it or
   reopens it.
4. Enter on a file opens its diff. Press `Alt+P` for the patch lines and
   arrow through them; `F8` jumps to the next change, and Enter on a line
   comments on it.
5. **Compose Review...** (`Alt+C`) sends your review: Approve, Request
   changes or Comment, with your pending line comments.

From the Workbench's list, **File Differences...** (`Ctrl+Shift+D`) opens the
diff straight away. [Chapter 5 of the GitHub
Guide](../user%20guide/github-guide/github-guide-05-pull-requests-and-review.md)
covers reviews in full.

### Finding out why a run failed

In a repository's Actions runs (`Ctrl+Shift+4`), select a failed run and
press `Ctrl+Shift+W` for **What Failed...**. You hear the failed jobs and
steps, the errors with their file and line, and the last lines of each failed
step's log. Enter on a run opens its jobs and logs. `Ctrl+Shift+F5` runs only
the failed jobs again. [Chapter 6 of the GitHub
Guide](../user%20guide/github-guide/github-guide-06-actions-and-checks.md)
has the rest.

### Comparing two branches

In a repository's **Branches**, select one and press `Ctrl+B` to compare it
with the default branch, or **Compare Branches...** (`Ctrl+Shift+B`) to choose
the other branch. The window has two tabs: Commits, and Changed Files, where
you read each file's changes the same way as a pull request's diff.

### Across GitHub

`Ctrl+1` goes to your **Inbox**: notifications, review requests, assignments
and mentions in one list. `Ctrl+3` goes to **Search**, for issues, code,
commits, repositories, people and topics across GitHub. `Ctrl+4` goes to
**People**, and `Ctrl+0` to **Across Repositories**, one kind of thing, such
as releases or failed runs, from several repositories in one list.

## 3. Changing things on GitHub

Everything so far only reads. Signed in, the same rows change things, and
QUILL asks more the bigger the change:

- **Organizing changes**, such as a label or an assignee, are saved at once,
  and `Ctrl+Z` takes them back.
- **Changes other people will see**, such as a comment, are saved at once.
- **Access and settings** show a preview in words first.
- **Anything hard to reverse**, such as a merge or deleting a branch, has you
  type its name or number to confirm.

Try these on a repository of your own, or on the practice repository in
[Tutorial 11](11-practise-github-safely.md):

- **A new issue.** In Issues, press `Ctrl+N`. Choose a template or a blank
  issue, write the title and body, and choose **Create Issue**. Nothing is
  sent until you do.
- **A comment.** On an issue or pull request, press `Ctrl+Shift+M`, write,
  and press `Ctrl+Enter` to post it.
- **Labels on many issues at once.** Select several issues with Shift or Ctrl
  and the arrows, press `Alt+Enter`, and change the labels on the one sheet.
  **Account > Change History...** (`Ctrl+Shift+H`) lists what you changed,
  with Undo.
- **Merge.** On a pull request, press `Ctrl+Shift+Enter`, choose how to
  merge, and type the pull request's number. **Why Can't I Merge?**, on its
  context menu, says first whether it can.
- **Close.** `Delete` on an issue closes it, after asking.

**Tools > Dry Run** (`Ctrl+Alt+D`) lets you try any of these without sending
anything: every command asks and previews as usual, then says what it would
have sent. Press it again to turn it off.

## 4. Repository commands in QUILL (Tools > Git and GitHub > GitHub)

**Tools > Git and GitHub > GitHub** has the commands that work on a whole
repository.

1. **Create Repository...**: a name, a description, private or public, and an
   organization if you want one. As soon as it is made, QUILL asks whether to
   set up a folder on your computer that stays in step with it.
2. **Fork Repository...**: the same offer of a folder afterwards.
3. **Rename Repository...**, **Change Repository Visibility...**, **Change
   Default Branch...** and **Configure Branch Protection...** open the
   Workbench on that repository's Properties sheet, at the right page. Change
   what you need and choose **OK**; anything about access or settings shows a
   preview first.
4. **Delete Branch...** opens the repository's Branches in the Workbench.
   Select the branch and press `Delete`; you type its name to confirm. The
   default branch is never deleted.
5. **Commit Multiple Files...**: pick several files on your computer, choose
   a branch and a commit message, and QUILL commits them together. This is
   different from **Commit to GitHub...** in part 1, which saves only the
   document you have open.

The same submenu has **Browse Organization Repositories...**, **Create
Release...**, **Dispatch Workflow...**, **Notifications...** and **Security
Alerts...**. Each opens the Workbench at the matching place. None of these
commands has a key out of the box; find them in the Command Palette
(`Ctrl+Shift+P`), or give one a key in the Keymap Editor. [Chapter 7 of the
GitHub
Guide](../user%20guide/github-guide/github-guide-07-code-and-repositories.md)
covers looking after a repository.

## 5. Local Git: resolving conflicts and rebasing, out loud (QUILL)

This part is different. **Tools > Git and GitHub > Local Git** needs no GitHub
account and does not go online. It works on any Git repository on your
computer. It is here because two everyday Git jobs, sorting out a merge
conflict and reordering commits with an interactive rebase, are very hard
with a screen reader in most other tools.

Try this with a real or a throwaway repository:

1. **Uncommitted Changes...** lists everything you have changed since your
   last commit, staged and unstaged. Select a file to hear what changed in it;
   **Stage** or **Unstage** it, or **Stage All**.
2. **Switch Branch...** picks a local branch from a list. If you have
   uncommitted changes, QUILL asks whether to switch anyway and bring them
   with you. It never throws them away.
3. **Stash Changes...** and **Manage Stashes...** put work aside with a name,
   then list, apply or drop it later.
4. **Who Changed This Line?**, on **GitHub > From This Line** in workbench
   mode or **Tools > Git and GitHub > GitHub > From This Line** with it off,
   says who last touched the line your cursor is on, when, and the commit's
   summary. **Open the Pull Request for This Line** opens the pull request
   that brought it.
5. **Start Bisect...** takes a known bad and a known good commit, checks out
   the midpoint and asks "Is this version good or bad?" Answer, and it narrows
   down to the commit that brought the problem in. **End Bisect** when you are
   done.

### Resolving a merge conflict without decoding markers

Create a conflict, or find one, and run **Resolve Conflicts...**. Instead of
`<<<<<<<`, `=======` and `>>>>>>>` markers, you hear "Conflict 1 of 3 in
`file.py`": your version, their version, and a choice of **your version**,
**their version**, **both** or **edit manually**. Work through every
conflict in every file; QUILL writes the result back and stages it. The same
walker opens by itself when a rebase or **Sync Folder with GitHub...** stops
on a conflict, and when you choose **Resolve Conflicts in a Worktree...** on
a pull request in the Workbench.

### Interactive rebase, as a real dialog

**Interactive Rebase...** asks which commit to rebase onto, then shows every
commit since then as a list, instead of a text file you edit by hand. Choose
an action for each row (pick, squash, reword or drop) and reorder with **Move
Up** and **Move Down**. Press **Start Rebase**. If a step conflicts, the
conflict walker opens; resolve it and the rebase carries on. **Abort Rebase**
puts your branch back exactly as it was.

The Local Git commands have no keys out of the box. All of them are in the
Command Palette and the **Tools > Git and GitHub > Local Git** menu, and you
can give them keys in the Keymap Editor.

## 6. Syncing a whole folder (QUILL)

**Tools > Git and GitHub > GitHub > Sync Folder with GitHub...** keeps a whole
folder in step with GitHub, such as a writing project or a notes folder. It
works the same way as **Sync Vault** in [Start an Accessible
Vault](05-start-a-vault.md), but on any folder you choose.

## In short

Open and save single files without an account; sign in once for everything
else. The GitHub Workbench is where you read and change issues, pull
requests, runs and repositories, and `Shift+F1` always says what you can do.
**Tools > Git and GitHub > GitHub** creates and configures repositories, and
**Tools > Git and GitHub > Local Git** covers the Git work on your own
computer, such as merge conflicts and interactive rebase.

To try all of this somewhere nothing can go wrong, [Practise GitHub
safely](11-practise-github-safely.md) makes you a practice repository and
walks you through reviewing, merging and reading a failed run in it.
