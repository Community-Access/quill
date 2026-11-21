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
and [Chapter 14](github-guide-14-quill-lite.html) puts every difference in
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

- **File > Open from Remote > GitHub Items...** opens the Workbench. The row
  keeps its old name; the window it opens is the GitHub Workbench. The same
  submenu has **Clone Repository...**, **Open GitHub Reference...** for a
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

---

- Next: [Chapter 2: A tour of the GitHub Workbench](github-guide-02-getting-around.html)
- [Contents](github-guide.html)
