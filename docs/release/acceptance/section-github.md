# Section — GitHub, Local Git, and Publishing (`github.*` `localgit.*` `publishing.*`, 40 commands)

Three related but separate surfaces, all about moving your writing between QUILL
and the wider world:

- **GitHub** (`github.*`, 17) — operate a GitHub account's repositories, releases,
  branches, notifications, security alerts, Codespaces, and Copilot CLI, without
  leaving QUILL. These live under **Tools menu ▸ Git and GitHub ▸ GitHub**. (The
  File-menu GitHub commands — save-back, open a file/repo/items, manage accounts —
  are `file.*` and are covered in `section-file.md` as **FILE-25…FILE-29**; do not
  re-test them here, but you must have connected an account there first.)
- **Local Git** (`localgit.*`, 12) — screen-reader-first front ends for everyday
  local `git` work (status, branches, stash, blame, bisect, conflicts, rebase,
  worktrees) on a repository on your own disk. Under **Tools menu ▸ Git and
  GitHub ▸ Local Git**. No network; no GitHub account.
- **Publishing** (`publishing.*`, 11) — connect a WordPress-style site, browse its
  posts/pages, and (when unlocked) create/update/publish/schedule content. Under
  **File menu ▸ Publish**.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → the `github.*`, `localgit.*`, and
`publishing.*` sections. Read §2–§3 of `README.md` for the scenario layout and the
Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible boxes.

**Read these preconditions before you start — many scenarios are Blocked or N/A
without them:**

- **GitHub account + network.** Every `github.*` command needs a **connected,
  signed-in GitHub account** (a personal access token) and a live network. Connect
  one first via **FILE-29 — Manage GitHub Accounts…** (`file.github_manage_accounts`,
  chord then Shift+Z). If no account is connected, a command offers to sign you in
  on the spot; if you cannot sign in or have no network, mark the scenario
  **Blocked**. **Tokens are stored in the platform secret store** (Windows
  Credential Manager / DPAPI, portable `keys.enc`, or macOS Keychain) — never in
  plain text. In **Safe Mode** every GitHub command refuses aloud; that is correct,
  not a failure.
- **GitHub CLI (`gh`) for Codespaces and Copilot.** GH-06, GH-07, GH-08, GH-14
  additionally need the **GitHub CLI** installed and on your PATH (or QUILL's
  self-hosted copy via **Help ▸ Download Optional Components**). These four are
  wired but flagged **needs live-device verification** — record exactly what you saw.
- **A local git repo for `localgit.*`.** You need a folder that is a git
  repository, plus a `git` executable (QUILL offers **Help ▸ Download Optional
  Components** if none is found; if you decline and have no system git, mark
  **Blocked**). To make a throwaway repo, open a terminal and run:
  `mkdir qa-git && cd qa-git && git init && echo one > a.txt && git add a.txt &&
  git commit -m "first" && echo two >> a.txt && git commit -am "second"`. Open
  `qa-git/a.txt` in QUILL so the repo is auto-detected, or let each command's folder
  picker point at `qa-git`.
- **Publishing is feature-gated.** The **read-only half** (PUB-01…PUB-03:
  connections, verify, browse) is behind `future.publishing_read` — off by default
  except in the **Full Quill** profile, but any user may switch it on via **Tools ▸
  Customize and Support ▸ Manage Individual Features…**. The **send half**
  (PUB-04…PUB-11: create/publish/update/compare/schedule) is behind
  `future.publishing`, which is **locked off** for public 1.0. On a public build the
  **File ▸ Publish** submenu shows only the read items (or is absent entirely); the
  send items are **[GATED]** — mark them **N/A**. Publishing site secrets are stored
  in the platform secret store (Credential Manager / DPAPI), never in plain text.

---

**GitHub (`github.*`) — 17 commands. GH-01…GH-17.** Every one is gated on Safe
Mode, consent + the PyGithub library, and a signed-in token, and runs its network
call on a background thread so the window never freezes. Errors are spoken via the
status bar, not raised as silent crashes. Unless noted, the repository field
prefills from the current document's GitHub origin and takes the form
**`owner/repo`**.

## GH-01 — Browse Organization Repositories… (`github.browse_organization`)

*What & why.* List the organizations your account belongs to, pick one, then pick
one of its repositories to open in the GitHub Items viewer.

**Before you start**
- Connected GitHub account (FILE-29); ideally a member of at least one org.

**Do this**
1. **Tools menu ▸ Git and GitHub ▸ GitHub ▸ Browse Organization Repositories…**
   (or Command Palette → "Browse Organization Repositories").
2. In the first list, arrow to an organization; press **Enter**.
3. In the repository list, arrow to a repo; press **Enter**.

**You should see and hear**
- "Loading organizations" is announced. A keyboard-navigable single-choice list of
  org names appears; choosing one loads and announces its repositories in a second
  list; choosing a repo opens the **GitHub Items viewer** for it. If the account is
  in no orgs, you hear "This account belongs to no organizations"; an org with no
  visible repos says so — never a silent dead end.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-02 — Change Default Branch… (`github.change_default_branch`, Ctrl+Shift+Grave then Shift+B)

*What & why.* Set which branch GitHub treats as the repository's default.

**Before you start**
- Connected account with **write access** to a repo that has two or more branches.
- Chord: press **Ctrl+Shift+Grave**, release, then **Shift+B**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Change Default
   Branch…**.
2. Type the repository as **`owner/repo`**; confirm.
3. In the branch list, arrow to the new default branch; press **Enter**.

**You should see and hear**
- The repo prompt is a labelled text field. "Loading branches for owner/repo" is
  announced, then a single-choice list of branch names. On confirm you hear
  "owner/repo's default branch is now `<branch>`". No branches found is reported.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-03 — Change Repository Visibility… (`github.change_repository_visibility`, Ctrl+Shift+Grave then Shift+V)

*What & why.* Flip a repository between public and private. High-consequence, so it
is guarded by a **typed confirmation** (you retype the repo name), and making a repo
public carries an explicit warning that its whole history becomes visible.

**Before you start**
- Connected account with admin rights to a repo. Chord: **Ctrl+Shift+Grave** then
  **Shift+V**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Change Repository
   Visibility…**.
2. Enter **`owner/repo`**; confirm.
3. Read the confirmation; in the typed-confirm dialog, **type the repository name
   exactly** to enable the action, then confirm.

**You should see and hear**
- "Checking owner/repo" then a confirmation stating the current visibility and the
  target ("… is currently public. Make it private?"). Making a repo **public** adds
  the warning about exposing full history. The typed-confirm field is labelled and
  must match before the button enables — cancelling or a mismatch leaves it
  unchanged and says "Visibility change cancelled". On success: "owner/repo is now
  private" (or public).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-04 — Commit Multiple Files… (`github.commit_multiple_files`, Ctrl+Shift+Grave then Shift+U)

*What & why.* Push several local files to a repo branch in one atomic commit,
without cloning it first.

**Before you start**
- Connected account with write access. A couple of local files to upload. Chord:
  **Ctrl+Shift+Grave** then **Shift+U**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Commit Multiple
   Files…**.
2. Enter **`owner/repo`**.
3. In the file picker (multi-select), choose the files; confirm.
4. Enter the branch (defaults to **`main`**) and a commit message.
5. Read the file listing in the confirmation; choose **Yes**.

**You should see and hear**
- Labelled prompts for repo, branch, and message; a keyboard-operable multi-select
  file dialog. The confirmation lists the files (first ten, then "and N more") and
  the target branch — nothing is pushed until you confirm. On success:
  "Committed N file(s) to owner/repo (`<short-sha>`)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-05 — Configure Branch Protection… (`github.configure_branch_protection`, Ctrl+Shift+Grave then Shift+L)

*What & why.* Add or remove branch-protection rules (required reviews, required
status checks, enforce-on-admins) for a branch.

**Before you start**
- Connected account with admin rights. Chord: **Ctrl+Shift+Grave** then **Shift+L**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Configure Branch
   Protection…**.
2. Enter **`owner/repo`**.
3. In the Branch Protection dialog, pick the branch and set the options (or choose
   Remove); confirm.
4. Answer the "Protect …?" / "Remove all protection …?" confirmation.

**You should see and hear**
- "Loading owner/repo", then a dialog whose branch chooser and option fields
  (required approving reviews, status checks, enforce admins) are labelled and
  keyboard-complete, defaulting to the repo's default branch. A plain confirmation
  precedes the change. On success: "Protected `<branch>` in owner/repo" or "Removed
  protection from `<branch>` in owner/repo".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-06 — Explain a Command… (`github.copilot_explain`)

*What & why.* Paste a `git` or `gh` command and have GitHub Copilot CLI explain it
in plain language.

**Before you start**
- **Precondition:** the **GitHub CLI (`gh`)** installed with Copilot access
  (`gh copilot`). If not present, QUILL points you to cli.github.com / Download
  Optional Components — mark **Blocked** if you cannot install it. Needs live-device
  verification.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Explain a Command…**.
2. Paste a command such as **`git reset --soft HEAD~1`**; confirm.

**You should see and hear**
- "Asking Copilot" is announced; the explanation appears in a readable, dismissible
  message box. If `gh` is missing you hear the "GitHub CLI Not Found" guidance
  instead of an error; an empty answer reports "Copilot did not explain that
  command."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-07 — Ask Copilot for a Command… (`github.copilot_suggest`)

*What & why.* Describe what you want to do in words and get a suggested `git`/`gh`
command from Copilot CLI.

**Before you start**
- Same `gh` + Copilot precondition as GH-06 (else **Blocked**). Needs live-device
  verification.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Ask Copilot for a Command…**.
2. Type e.g. **`undo my last commit but keep the changes`**; confirm.

**You should see and hear**
- "Asking Copilot"; the suggested command appears in a readable message box; a blank
  result says "Copilot did not suggest anything." Missing `gh` gives the guidance
  message, not a crash.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-08 — Create Codespace… (`github.create_codespace`)

*What & why.* Start a new GitHub Codespace for a repository. **Codespaces cost real
compute/storage minutes** on GitHub's side — the confirmation says so explicitly.

**Before you start**
- **Precondition:** `gh` CLI installed and a Codespaces-enabled account. Needs
  live-device verification; mark **Blocked** if unavailable. Be aware this may
  **cost money** on your plan.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Create Codespace…**.
2. Enter **`owner/repo`**; optionally a branch (blank = default).
3. Read the paid-compute warning; choose **Yes** to proceed.

**You should see and hear**
- The confirmation is titled "Confirm Create Codespace (uses paid GitHub compute)"
  and warns it is not a free action — nothing is created until you accept. On
  success: "Created codespace `<name>` (`<state>`)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-09 — Create Release… (`github.create_release`)

*What & why.* Cut a GitHub release from a tag, optionally auto-generating notes from
merged pull requests, and optionally as a draft.

**Before you start**
- Connected account with write access to a repo.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Create Release…**.
2. Enter **`owner/repo`**, then a tag (e.g. **`v1.0.0`**) and an optional title.
3. Answer "Auto-generate release notes …?"; if No, enter notes.
4. Answer "Save as a draft …?".

**You should see and hear**
- Labelled prompts throughout. On success: "Created draft release `<tag>`
  (`<url>`)" or "Created published release `<tag>` (`<url>`)" matching your draft
  choice. Errors (bad tag, no access) are spoken.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-10 — Create Repository… (`github.create_repository`, Ctrl+Shift+Grave then Shift+K)

*What & why.* Create a brand-new GitHub repository (optionally in an org, public or
private) and, in one continuous flow, offer to wire it up to a local sync folder.

**Before you start**
- Connected account. Chord: **Ctrl+Shift+Grave** then **Shift+K**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Create Repository…**.
2. In the Create Repository dialog set name, private/public, description, and
   optional org; confirm.
3. When asked "Set up a local folder to sync …?", either choose a folder or decline.

**You should see and hear**
- The dialog's fields are labelled and keyboard-complete. On success: "Created
  `<owner/name>` at `<url>`", then the sync offer. Declining says "Local sync
  skipped"; accepting and choosing a folder runs the local init/sync and announces
  progress.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-11 — Delete Branch… (`github.delete_branch`, Ctrl+Shift+Grave then Shift+X)

*What & why.* Delete a branch from a repository. The default branch is excluded from
the list, and deletion is guarded by a **typed confirmation** (retype the branch
name).

**Before you start**
- Connected account with write access to a repo that has a deletable (non-default)
  branch. Chord: **Ctrl+Shift+Grave** then **Shift+X**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Delete Branch…**.
2. Enter **`owner/repo`**.
3. Pick the branch from the list; in the typed-confirm dialog, **type the branch
   name exactly**; confirm.

**You should see and hear**
- The branch list excludes the default branch ("No deletable branches … (default
  branch excluded)" if none remain). The confirmation warns "This cannot be undone
  from QUILL" and requires the exact branch name. On success: "Deleted branch
  `<name>` from owner/repo".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-12 — Dispatch Workflow… (`github.dispatch_workflow`)

*What & why.* Manually trigger a GitHub Actions workflow (`workflow_dispatch`) on a
chosen branch or tag.

**Before you start**
- Connected account with write access to a repo that has a dispatchable workflow
  (e.g. `ci.yml`).

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Dispatch Workflow…**.
2. Enter **`owner/repo`**, the workflow file name (e.g. **`ci.yml`**), and a ref
   (defaults to **`main`**).
3. Confirm "Dispatch … ?".

**You should see and hear**
- Labelled prompts; a confirmation before firing. On success: "Dispatched `<file>`
  on `<ref>`". A missing workflow or no access is reported clearly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-13 — Fork Repository… (`github.fork_repository`, Ctrl+Shift+Grave then Shift+F)

*What & why.* Fork a repository into your account or an organization, then offer the
same local-sync wiring as Create Repository.

**Before you start**
- Connected account. A public repo to fork (e.g. a well-known one). Chord:
  **Ctrl+Shift+Grave** then **Shift+F**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Fork Repository…**.
2. Enter the source **`owner/repo`**; optionally an org to fork into (blank = your
   account); confirm.
3. Decline or accept the "Set up a local folder to sync …?" offer.

**You should see and hear**
- Labelled prompts. On success: "Created `<your-owner>/<repo>` at `<url>`" followed
  by the local-sync offer, same as GH-10.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-14 — Codespaces… (`github.list_codespaces`)

*What & why.* List your existing Codespaces and act on one (Stop or Delete).

**Before you start**
- **Precondition:** `gh` CLI installed. Needs live-device verification; **Blocked**
  without `gh`.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Codespaces…**.
2. If any exist, arrow to one; press **Enter**; from the pop-up menu choose **Stop**
   or **Delete**.

**You should see and hear**
- "Loading codespaces". With none: "No codespaces. Use GitHub: Create Codespace…
  to start one." With some: a single-choice list of "name (repo) — state"; a
  pop-up offers Stop / Delete; **Delete** requires a confirmation ("cannot be
  undone"). Results are spoken ("Stopped …", "Deleted …").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-15 — Rename Repository… (`github.rename_repository`, Ctrl+Shift+Grave then Shift+E)

*What & why.* Rename a repository. GitHub auto-redirects the old URL, but this is
still guarded by a **typed confirmation** (retype the full `owner/repo`).

**Before you start**
- Connected account with admin rights. Chord: **Ctrl+Shift+Grave** then **Shift+E**.

**Do this**
1. Open via the chord, or **Tools ▸ Git and GitHub ▸ GitHub ▸ Rename Repository…**.
2. Enter **`owner/repo`**, then the new name.
3. In the typed-confirm dialog, **type `owner/repo` exactly**; confirm.

**You should see and hear**
- The confirmation notes GitHub will redirect the old URL but hardcoded references
  need updating, and requires the exact `owner/repo` to enable. On success:
  "Renamed to `<owner/newname>`". Cancel/mismatch says "Rename cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-16 — Notifications… (`github.view_notifications`)

*What & why.* Read your GitHub notifications as a keyboard list and open one; the
one you open is marked read.

**Before you start**
- Connected account with at least one notification (star/watch a repo and generate
  activity if needed).

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Notifications…**.
2. Arrow to a notification; press **Enter**.

**You should see and hear**
- "Loading notifications". With none: "No notifications". With some: a single-choice
  list reading "Unread/Read: repo — subject (reason)". Opening one launches the
  GitHub notifications page in your browser; an unread one is then marked read
  ("Marked as read").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GH-17 — Security Alerts… (`github.view_security_alerts`)

*What & why.* List a repository's open Dependabot/security alerts and open one in the
browser.

**Before you start**
- Connected account with access to a repo that has open alerts.

**Do this**
1. **Tools ▸ Git and GitHub ▸ GitHub ▸ Security Alerts…**.
2. Enter **`owner/repo`**.
3. Arrow to an alert; press **Enter**.

**You should see and hear**
- "Loading security alerts for owner/repo". With none: "No open security alerts".
  With some: a list reading "#N severity: package — summary"; opening one launches
  its GitHub page in the browser.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

**Local Git (`localgit.*`) — 12 commands. GIT-01…GIT-12.** All operate on a local
git repository (never GitHub's API, never a remote). Each resolves the repo from the
current document's folder, or prompts you to pick a folder; each needs a `git`
executable and refuses in Safe Mode. Make the throwaway `qa-git` repo from the
preconditions above and open `qa-git/a.txt` before you begin. If `git` cannot be
found and you decline the download, mark the affected scenarios **Blocked**.

## GIT-01 — Uncommitted Changes… (`localgit.uncommitted_changes`)

*What & why.* See what has changed in the working tree, read a diff, and stage or
unstage files — by keyboard and by ear.

**Before you start**
- `qa-git` repo with at least one uncommitted change (edit `a.txt` and save it).

**Do this**
1. **Tools menu ▸ Git and GitHub ▸ Local Git ▸ Uncommitted Changes…**.
2. Arrow the change list; read a file's diff; use the dialog's Stage / Unstage /
   Stage All controls.

**You should see and hear**
- "Checking for changes"; with none, "No uncommitted changes". Otherwise a
  keyboard-navigable list of changed files with a diff view (HEAD vs working copy);
  staging announces "Staged `<path>`", unstaging "Unstaged `<path>`", stage-all
  "Staged all changes".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-02 — Switch Branch… (`localgit.switch_branch`)

*What & why.* Check out a different local branch, with a spoken guard when
uncommitted changes are in the way.

**Before you start**
- `qa-git` repo with a second branch (`git branch feature` in the terminal).

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Switch Branch…**.
2. Pick a branch (the current one is excluded); press **Enter**.

**You should see and hear**
- "Loading branches", then a single-choice list of other branches ("No other local
  branches" if none). On success the result is announced. If uncommitted changes
  block the switch, you are asked "…Switch anyway and carry them over?" and can
  cancel — never a silent overwrite.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-03 — Stash Changes… (`localgit.stash_changes`)

*What & why.* Set aside your uncommitted work on a named stash.

**Before you start**
- `qa-git` repo with an uncommitted change.

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Stash Changes…**.
2. Type an optional stash message; confirm.

**You should see and hear**
- A labelled message field. "Stashing changes", then "Changes stashed". The working
  tree returns to a clean state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-04 — Manage Stashes… (`localgit.manage_stashes`)

*What & why.* Review existing stashes and apply or drop one.

**Before you start**
- `qa-git` repo with at least one stash (do GIT-03 first).

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Manage Stashes…**.
2. Pick a stash; from the pop-up menu choose **Apply** or **Drop**.

**You should see and hear**
- "Loading stashes"; with none, "No stashes". Otherwise a single-choice list reading
  "`<ref>`: `<message>`"; a pop-up offers Apply / Drop, announcing "Applied `<ref>`"
  or "Dropped `<ref>`".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-05 — Who Wrote This Line… (`localgit.blame_at_cursor`)

*What & why.* Announce the author, summary, and commit of the line at the cursor
(git blame), spoken rather than shown in a gutter.

**Before you start**
- Open a **committed** file inside `qa-git` (e.g. `a.txt`) and put the cursor on a
  line.

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Who Wrote This Line…**.

**You should see and hear**
- "Line N: `<author>`, `<summary>` (`<short-sha>`)". With no open file, "No file to
  blame"; a file outside a repo, "This file is not inside a git repository".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-06 — Start Bisect… (`localgit.bisect_start`)

*What & why.* Begin a `git bisect` to hunt down the commit that introduced a bug,
answering good/bad by keyboard as QUILL checks out each candidate.

**Before you start**
- `qa-git` repo with several commits (the precondition script gives you two; add a
  few more for a meaningful run).

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Start Bisect…**.
2. Enter the bad commit (default **`HEAD`**) and a known-good commit or tag.
3. Answer each "Is this version good or bad? (Yes = bad, No = good)".

**You should see and hear**
- "Starting bisect", then for each step a confirmation telling you QUILL checked out
  the next commit to test and asking good/bad. When done: "Bisect complete: …".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-07 — End Bisect (`localgit.bisect_reset`)

*What & why.* Stop a bisect in progress and return to your original checkout.

**Before you start**
- A bisect started (GIT-06). (Running it with no bisect active still ends cleanly.)

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ End Bisect**.

**You should see and hear**
- "Ending bisect", then "Bisect ended"; the repo returns to its pre-bisect state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-08 — Resolve Conflicts… (`localgit.resolve_conflicts`)

*What & why.* Walk each conflicted file's hunks and choose a resolution, then mark it
resolved — accessible merge-conflict handling.

**Before you start**
- A repo with an in-progress merge conflict. To make one in `qa-git`:
  `git checkout -b other && echo other-change > a.txt && git commit -am other &&
  git checkout main && echo main-change > a.txt && git commit -am main &&
  git merge other` (this leaves `a.txt` conflicted). If you cannot produce one, mark
  **Blocked**.

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Resolve Conflicts…**.
2. For each conflicted file, choose a resolution per hunk in the dialog; confirm.

**You should see and hear**
- "Checking for conflicts"; with none, "No conflicts to resolve". Otherwise each
  conflicted file opens a hunk-by-hunk dialog with keyboard choices; on finishing,
  the file is written and marked resolved. Skipping a file says how many remain.
  When all are done: "Resolved N file(s)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-09 — Interactive Rebase… (`localgit.interactive_rebase`)

*What & why.* Reorder, squash, edit, or drop commits since a base ref, through a
keyboard dialog instead of an editor of cryptic todo lines — with conflict handling
if the rebase stops.

**Before you start**
- `qa-git` repo with a few commits on the current branch and a base to rebase onto
  (e.g. an earlier commit or another branch).

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Interactive Rebase…**.
2. Enter the base (branch, tag, or commit).
3. In the rebase dialog set each commit's action; confirm.
4. If it pauses on conflicts, answer "Resolve them now?" and work through them.

**You should see and hear**
- "Loading commits"; "No commits between …" if the range is empty. Otherwise a
  keyboard-navigable list of commits with per-commit actions. "Rebasing", then a
  spoken result. A conflict pause offers to resolve conflicts (as in GIT-08) and
  continue.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-10 — Abort Rebase (`localgit.rebase_abort`)

*What & why.* Cancel an in-progress rebase and restore the original branch state.

**Before you start**
- A rebase paused/in progress (e.g. from GIT-09).

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Abort Rebase**.
2. Confirm "Abort the in-progress rebase …?".

**You should see and hear**
- A spoken confirmation you can cancel; on confirm, "Aborting rebase" then "Rebase
  aborted", with the branch back to its original state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-11 — Worktrees… (`localgit.worktrees`)

*What & why.* List and manage git worktrees. QUILL prefers worktrees precisely
because switching a branch in place silently rewrites the open file under a
screen-reader user; a worktree makes "change branch" into "open a different file"
you can hear.

**Before you start**
- `qa-git` repo.

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ Worktrees…**.
2. In the dialog, explore the list and its controls: New, Open, Remove, Lock/Unlock,
   Prune.

**You should see and hear**
- "Loading worktrees", then a keyboard-navigable list of worktrees with the actions
  above. **Open** opens the current document's counterpart from the chosen worktree
  (or offers a file picker pointed there if there is none). **Remove** warns the
  folder will be deleted (branch kept) and confirms before force-removing
  uncommitted changes. Every action is announced before and after.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GIT-12 — New Worktree… (`localgit.new_worktree`)

*What & why.* Create a new worktree (for an existing or new branch) directly, without
opening the list first.

**Before you start**
- `qa-git` repo with a branch not already checked out anywhere.

**Do this**
1. **Tools ▸ Git and GitHub ▸ Local Git ▸ New Worktree…**.
2. In the New Worktree dialog choose the branch (or a new branch + start ref) and the
   parent folder; confirm.

**You should see and hear**
- A labelled dialog defaulting the parent folder to the repo's parent; the branch
  chooser lists only branches not already checked out. "Creating the worktree. This
  can take a moment …" is announced, then the result. Cancel says "New worktree
  cancelled."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

**Publishing (`publishing.*`) — 11 commands. PUB-01…PUB-11.** These live under
**File menu ▸ Publish**. **PUB-01…PUB-03 (read-only)** require `future.publishing_read`
— on by default only in the **Full Quill** profile, otherwise switch it on via
**Tools ▸ Customize and Support ▸ Manage Individual Features…**; if you cannot enable
it, mark them **Blocked**. **PUB-04…PUB-11 (send)** require `future.publishing`,
which is **locked off** for public 1.0 — on a public build those menu items are
**absent**; mark each **[GATED] → N/A** (do not fail them for being missing). All
publishing require a connected WordPress-style site; **site secrets are stored in
the platform secret store (Credential Manager / DPAPI), never in plain text.**

## PUB-01 — Publishing Connections… (`publishing.connections`) [GATED future.publishing_read]

*What & why.* Add, edit, and remove the site accounts publishing uses; the read-only
front door.

**Before you start**
- `future.publishing_read` enabled. Details of a WordPress-style site (URL + an
  application password / API token). If you cannot enable the flag, **Blocked**; if
  not present at all on this build, **N/A**.

**Do this**
1. **File menu ▸ Publish ▸ Publishing Connections…**.
2. Add a connection: enter the site URL and credentials by keyboard; save; then
   remove it to confirm removal.

**You should see and hear**
- A keyboard-operable connections dialog with labelled fields; saving announces
  "Updated publishing connections", cancelling "Publishing connections cancelled".
  The **secret is written to the OS secret store**, not to any settings file in
  plain text — confirm you are never shown or asked to paste it back from a plain
  file.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-02 — Verify Current Publishing Connection (`publishing.verify_connection`) [GATED future.publishing_read]

*What & why.* Check that the selected connection actually reaches the site with the
stored credentials.

**Before you start**
- `future.publishing_read` enabled and a connection added (PUB-01), and selected as
  current.

**Do this**
1. **File menu ▸ Publish ▸ Verify Current Publishing Connection**.

**You should see and hear**
- A spoken result in a message box and the status bar: success or a clear failure
  reason. With no current connection selected: "No current publishing connection is
  selected." — never a silent no-op.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-03 — Browse Publishing Content… (`publishing.browse_content`) [GATED future.publishing_read]

*What & why.* Browse the site's posts/pages and open one into the editor as an
editable document.

**Before you start**
- `future.publishing_read` enabled, a verified connection with some content.

**Do this**
1. **File menu ▸ Publish ▸ Browse Publishing Content…**.
2. Browse the list by keyboard; open a post or page.

**You should see and hear**
- A keyboard-navigable browse dialog; opening an item creates a new document tab
  from its content and announces "Opened post from publishing." (or "page"). Cancel
  says "Browse publishing content cancelled". The opened document is tagged as remote
  so the send commands (below) can target it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-04 — Create Post Draft… (`publishing.create_draft`) [GATED future.publishing]

*What & why.* Send the current document to the site as a **draft** post.

**Before you start**
- `future.publishing` **locked off** in public 1.0 → this menu item is absent. Mark
  **N/A**. (If a dev/admin build has it on: a connection selected and a document
  open.)

**Do this**
1. **File menu ▸ Publish ▸ Create Post Draft…**.
2. Read the review confirmation (title, authoring surface, site); choose **Yes**.

**You should see and hear** *(dev/admin build only)*
- A review dialog stating what will be sent and where; nothing leaves until you
  accept. On success a "created" result with the remote title/URL; with no
  connection, "No current publishing connection is selected."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-05 — Create Page Draft… (`publishing.create_page_draft`) [GATED future.publishing]

*What & why.* Send the current document to the site as a **draft page** (rather than
a post).

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Create Page Draft…**.
2. Review and confirm.

**You should see and hear** *(dev/admin build only)*
- Same review-then-send flow as PUB-04, labelled as a page draft; success reports the
  created page.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-06 — Publish Post Now… (`publishing.publish_current`) [GATED future.publishing]

*What & why.* Send the current document and **publish** it immediately as a post.

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Publish Post Now…**.
2. Review the "Publish … as published on `<site>`?" confirmation; choose **Yes**.

**You should see and hear** *(dev/admin build only)*
- An explicit publish confirmation; on success the document is linked to the remote
  item and the title bar updates. Cancel says "Publish current document cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-07 — Publish Page Now… (`publishing.publish_current_page`) [GATED future.publishing]

*What & why.* Send the current document and **publish** it immediately as a page.

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Publish Page Now…**.
2. Review and confirm.

**You should see and hear** *(dev/admin build only)*
- Same as PUB-06, labelled as a page; success reports the published page.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-08 — Compare With Remote… (`publishing.compare_remote_item`) [GATED future.publishing]

*What & why.* Compare the open remote-sourced document against the current state of
its remote item before you overwrite it.

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0. (Dev/admin:
  a document opened via PUB-03 whose connection matches the current one.)

**Do this**
1. **File menu ▸ Publish ▸ Compare With Remote…**.

**You should see and hear** *(dev/admin build only)*
- A spoken comparison report. Guard messages if the document is not remote-sourced or
  the connection/site does not match — never a wrong-target overwrite.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-09 — Update Remote Content… (`publishing.update_remote_item`) [GATED future.publishing]

*What & why.* Send the current document text back to the remote item it came from
(without changing its published/draft status).

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Update Remote Content…**.
2. Review "Update this remote …?" (title, authoring surface, remote URL); choose
   **Yes**.

**You should see and hear** *(dev/admin build only)*
- A review confirmation naming the exact remote item; on success an "updated" result
  and the document re-linked/marked saved. Connection/site mismatch and
  not-remote-sourced are guarded aloud.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-10 — Publish Open Remote Content… (`publishing.publish_remote_item`) [GATED future.publishing]

*What & why.* Send the current document to its remote item **and publish** it.

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Publish Open Remote Content…**.
2. Review the publish confirmation; choose **Yes**.

**You should see and hear** *(dev/admin build only)*
- Same guarded review-then-send as PUB-09 but with publish status; success reports
  the published remote item.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## PUB-11 — Schedule Publish… (`publishing.schedule_publish`) [GATED future.publishing]

*What & why.* Schedule the current document to publish (as a new item or an update to
the open remote item) at a chosen future date/time.

**Before you start**
- `future.publishing` locked off → item absent → **N/A** on public 1.0.

**Do this**
1. **File menu ▸ Publish ▸ Schedule Publish…**.
2. In the Schedule Publish dialog set the date/time (and content kind if not fixed);
   review the confirmation; choose **Yes**.

**You should see and hear** *(dev/admin build only)*
- A labelled scheduling dialog; a review stating "Scheduled for: `<local time>`";
  on success a "scheduled" result with the remote item's scheduled time recorded.
  No connection or a mismatch is reported, not silently ignored.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 40
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
