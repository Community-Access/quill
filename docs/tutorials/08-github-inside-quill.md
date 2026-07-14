# Tutorial 8: GitHub inside QUILL

**Goal:** everything QUILL can do with GitHub and local git, in one sitting —
browsing and saving files, working issues and pull requests, administering a
repository, and resolving a merge conflict without ever opening a browser or
a terminal.

Three layers, and you can use any of them independently:

- **GitHub browsing and the Items viewer** — read/write issues, PRs,
  branches, commits, releases, workflow runs. Needs a GitHub account for
  anything beyond public browsing.
- **Repository administration** — create, fork, rename, and configure
  repositories from QUILL. Needs a signed-in account for everything.
- **Local Git** — accessible merge-conflict resolution and interactive
  rebase. Needs no GitHub account at all; works on any local repository.

## 0. Sign in (once)

The first time you touch any GitHub feature, QUILL shows a one-time consent
dialog explaining it will connect to api.github.com. Accept it, then:

1. **File > Open from Remote > Manage GitHub Accounts...**
2. **Add Token.** On github.com: **Settings > Developer settings > Personal
   access tokens > Tokens (classic) > Generate new token**, select the
   `repo` scope, and copy it — you only see it once.
3. Paste it into QUILL. It's stored in your OS's secure credential store
   (Windows Credential Manager or macOS Keychain), never in a plain file.

Public repositories are browsable without a token, at a lower rate limit.
Everything that *writes* to GitHub needs a token; if you try a write command
without one, QUILL offers to sign you in right there instead of just
refusing.

## 1. Browse, open, and save a file

1. **File > Open from Remote > GitHub Repository...**
2. Type an `owner/repo` (try `octocat/Hello-World` if you don't have one
   handy) and press Enter.
3. Arrow through the file list — folders first, then files. Enter opens a
   folder or a file.
4. Edit the file, then **File > Open from Remote > Save to GitHub...** and
   type a commit message. QUILL commits straight to the same repository,
   branch, and path.

If you already have the URL, **File > Open from Remote > GitHub File URL...**
skips the browser entirely — paste a `github.com/owner/repo/blob/branch/path`
link and QUILL fetches it directly.

## 2. The Items viewer: issues, PRs, branches, and everything else

**File > Open from Remote > GitHub Items...** opens a list-over-detail
browser for one repository's issues, pull requests, branches, commits, tags,
releases, workflows, and workflow runs. This viewer is built on, and owes
real credit to, [GHManage](https://github.com/kellylford/GHManage) — Kelly
Ford's open-source, screen-reader-first GitHub browser, which QUILL has
used as its reference since this integration began. Every feature below
with a GHManage ancestor keeps its idea and extends it with something
specific to QUILL.

1. Type `owner/repo`, an `https://github.com/owner/repo` URL, or a
   `git@github.com:owner/repo.git` remote, then press **Load** — QUILL
   normalizes any of those to `owner/repo`. (If your current document lives
   inside a git checkout whose origin points at GitHub, the field is
   already filled in.)
2. Pick a **View** — start with Issues & PRs. **Show**, **State**, and
   **Sort** filter that view further. **Columns...** picks which fields
   show as list columns for the current view — uncheck ones you don't need,
   and the choice is remembered next time you open the viewer.
3. Select a row; the details pane loads its full text, then its comment
   thread. **Alt+N** / **Alt+P** jump between comments — the navigator
   announces "Comment 2 of 5."
4. Press **M** to toggle **List mode** between Quick (compact) and Full
   (every cell spoken as `field: value`).

**Search** (Ctrl+F) takes full GitHub search syntax scoped to the loaded
repo: try `label:bug is:open`. **Quick filter** (Ctrl+Shift+F) is different —
it narrows the list you already loaded as you type, instantly and with no
network request; Escape clears it. **Pinned...** keeps a short list of repos
you jump back to often; **Ctrl+D** favorites the selected row from any repo,
and **Favorites...** lists everything you've bookmarked across all of them.

### Running a workflow

Switch to the **Workflows** view to see the repository's workflow
definitions (the `.yml` files themselves, not their run history). Select one
and press **Enter** (or **Actions... > Run ... on Branch...**) to dispatch
it — QUILL asks for the branch, confirms, and reports whether GitHub
accepted the run. This needs a signed-in account, and GitHub tells you
plainly if a workflow doesn't accept manual (`workflow_dispatch`) runs
rather than QUILL guessing. The separate **Workflow Runs** view still shows
run history and lets you re-run or inspect artifacts from a past run.

### Reading a pull request's actual changes

Select a PR row and press **Diff...**. QUILL fetches both sides of every
changed file and runs them through the same compare engine as **Compare
Documents**, so you hear a real difference walk — "Difference 2 of 5, text
changed at line 41" — instead of a raw patch.

### Comparing two branches

Switch to the **Branches** view, select one, and press **Compare...** (or
**Ctrl+Shift+B**) — this works without signing in, since it never writes to
GitHub. Type the base branch, then the branch to compare against it (the
selected row prefills the second prompt). QUILL reports how far the two have
diverged, lists every commit between them, and — on the **Changed Files**
tab — walks each file's differences the same accessible way **Diff...**
does. Enter on a branch drills into its **Commits**; **Backspace** in the
Commits view steps back out to the branch list.

### Getting a TL;DR

Select a long issue or PR and press **Summarize**. QUILL's AI condenses the
whole discussion into what it's about, where it stands, and what's still
open. Uses your existing AI setup; if you haven't configured one, pressing
Summarize offers to walk you through it.

## 3. Writing back: the Actions and Batch menus

Everything so far works read-only. Signed in, two more buttons appear.

**Batch...** applies close, reopen, or add-label to every checked row at
once (hold Shift or Ctrl to check several). A confirmation names the exact
action and the exact item numbers before anything changes.

**Actions...** is context-sensitive to what you're looking at:

- In **Issues & PRs**: **New Issue...** / **New Pull Request...** prompt
  for a title, body, and (for a PR) head/base branches. With a single
  unmerged PR selected, **Merge Pull Request #N...** also appears —
  retype the PR number to confirm, since merging is one of the four
  highest-stakes actions in this whole integration.
- With a comment thread loaded: **Reply to Thread...** posts a new
  comment. Navigate to a specific comment with Alt+N/Alt+P first, and
  **Edit This Comment...** / **Delete This Comment...** also appear
  (GitHub only lets you edit or delete your own comments).
- In **Branches**: select one and **Delete Branch...** appears — retype
  the branch name to confirm.
- In **Workflow Runs**: select one and **Re-run Workflow** appears.

Try it: load a repo you maintain, select **New Issue...**, give it a title,
and watch it appear in the list after you confirm.

## 4. Repository administration (Tools > GitHub)

Everything above works on repositories that already exist. **Tools >
GitHub** creates and configures them.

1. **Create Repository...** — name, description, private or public, and an
   optional organization. The moment it's created, QUILL asks whether to
   set up a local folder synced to it right now. Say yes, pick a folder, and
   you've gone from nothing to a pushed local repository in one motion.
2. **Fork Repository...** — same local-sync offer afterward.
3. **Rename Repository...**, **Change Repository Visibility...**, **Change
   Default Branch...**, **Delete Branch...** — retype the name to confirm
   the first two and the branch-delete; visibility changes warn extra
   loudly when you're about to make something public.
4. **Configure Branch Protection...** — pick a branch, then either set
   required approving reviews and required status checks, or tick "remove
   all protection instead" to clear existing rules.
5. **Commit Multiple Files...** — pick several local files with a file
   browser, choose a branch and a commit message, and QUILL commits all of
   them in one atomic commit. This is different from **Save to GitHub**
   (section 1), which only ever handles the one document you have open.

All eight commands are in the Command Palette and ship default keyboard
shortcuts through the QUILL Key (press your QUILL Key, then the listed
letter): Create = Shift+K, Fork = Shift+F, Rename = Shift+E, Visibility =
Shift+V, Default Branch = Shift+B, Branch Protection = Shift+L, Delete
Branch = Shift+X, Commit Multiple Files = Shift+U.

### Organizations, releases, workflows, notifications, security

Five more commands round out **Tools > GitHub**:

- **Browse Organization Repositories...** — pick an organization you
  belong to, then one of its repositories, and QUILL opens it straight
  into the Items viewer.
- **Create Release...** — a tag, optional title, and either your own notes
  or GitHub's auto-generated notes from merged PRs since the last release.
- **Dispatch Workflow...** — run a workflow on a branch or tag, the same
  as clicking "Run workflow" on github.com.
- **Notifications...** — a real inbox across every repository you have
  access to, not just the one you have loaded. Selecting one opens it and
  marks it read.
- **Security Alerts...** — a repository's open Dependabot alerts:
  severity, affected package, and a summary, so you know what needs
  attention without a browser.

## 5. Local Git: resolving conflicts and rebasing, out loud

Switch gears entirely — **Tools > Local Git** needs no GitHub account and
touches no network. It works on the working copy of any git repository on
your machine, and it exists because two of git's most common tasks —
resolving a merge conflict and reordering commits with an interactive
rebase — are notoriously hard with a screen reader everywhere else.

Try this with a real (or throwaway test) repository:

1. **Uncommitted Changes...** — lists everything you've changed since your
   last commit, staged and unstaged. Select a file to hear an accessible
   diff of it (same reading style as Compare Documents); **Stage** /
   **Unstage** it, or **Stage All**.
2. **Switch Branch...** — pick a local branch from a list. If you have
   uncommitted changes, QUILL asks whether to switch anyway and bring them
   along, rather than silently dropping or blocking you.
3. **Stash Changes...** / **Manage Stashes...** — save work aside with a
   name, then list, apply, or drop it later.
4. **Who Wrote This Line...** — with your cursor on a line in an open file
   that's part of a git repo, this speaks who last touched that line, when,
   and the commit's summary.
5. **Start Bisect...** — give it a known-bad and a known-good commit, and
   QUILL checks out the midpoint and asks "Is this version good or bad?"
   Answer, and it narrows down to the exact commit that introduced the
   problem. **End Bisect** when you're done.

### Resolving a merge conflict without decoding markers

Create a real conflict (or find one) and run **Resolve Conflicts...**.
Instead of `<<<<<<<`/`=======`/`>>>>>>>` markers, you get: "Conflict 1 of 3
in `file.py`: your version says X, their version says Y," with **your
version** / **their version** / **both** / **edit manually** as your
choice. Work through every conflict in every affected file; QUILL writes
the resolved content back and stages it. The same walker opens
automatically if a rebase (next) or a **Sync Folder with GitHub** stops on
a conflict — you never have to go find a different tool mid-task.

### Interactive rebase, as a real dialog

**Interactive Rebase...** asks which commit to rebase onto, then shows every
commit since then as a real list — not a text buffer you're expected to
hand-edit. Pick an action per row (pick, squash, reword, drop) from a
dropdown, and reorder with **Move Up** / **Move Down**. Press **Start
Rebase**. If a step conflicts, the conflict walker above opens
automatically; resolve it and the rebase continues on its own. **Abort
Rebase** restores your branch exactly as it was if you change your mind.

None of the ten Local Git commands have a default keyboard shortcut — every
letter on the QUILL Key leader is already claimed elsewhere — but all ten
are in the Command Palette and the **Tools > Local Git** menu, and you can
assign your own shortcuts in **Preferences > Keyboard Shortcuts**.

## 6. Syncing a whole folder

One more command, adjacent to everything above: **Tools > Sync Folder with
GitHub...** commits, pulls, and pushes an entire folder over its own git
remote — a writing project, a notes folder, anything, not just files opened
through the commands above. See [Start an Accessible
Vault](05-start-a-vault.md) for the same engine in its original home
(**Sync Vault**); this is the general-purpose version, generalized to work
on any folder you point it at.

## The shape of it

Browse and save individual files without an account; sign in once for
everything else. The Items viewer's **Batch...** and **Actions...** menus
cover day-to-day issue/PR work; **Tools > GitHub** covers repository
lifecycle and the rest of the API; **Tools > Local Git** covers the parts
that were never about GitHub at all — and are, as far as we can tell, the
first genuinely accessible interactive rebase and merge-conflict experience
anywhere.
