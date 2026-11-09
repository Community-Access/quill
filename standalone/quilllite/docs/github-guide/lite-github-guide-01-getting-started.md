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
with all of those commands in it and a few more that open the views you use
most in one step, such as **Inbox...** and **Issues and Pull Requests...**.
`Alt+G` opens it. Chapter 2 walks through it.

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
- `user:follow`: following and unfollowing people.
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
QUILL's Tools menu and the GitHub CLI (command-line interface) commands are switched off the same way.
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
   whether it is an issue or a PR (pull request), its state and its title.
5. Press Tab to reach **Details**. Read it like any text field. It holds the
   whole issue, then its comments as they load.
6. Press `Alt+N`. You move to the first comment and hear "Comment 1 of" and
   the count. Press it again for the next one, and `Alt+P` to go back.
7. Press Shift+Tab to return to the list.
8. Press Shift+F10 on a row to hear what you can do with it.
9. Press Escape to close the menu, and Escape again to close GitHub Items.

Next time you open it, you are back on the same row.

---

- Next: [Chapter 2: Getting around](lite-github-guide-02-getting-around.html)
- [Contents](lite-github-guide.html)
