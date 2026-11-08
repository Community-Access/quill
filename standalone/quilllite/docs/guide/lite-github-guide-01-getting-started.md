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
  submenu has **Open GitHub Reference...** for pasting any GitHub link, and
  **Manage GitHub Accounts...** for signing in.
- **Tools > Git and GitHub > GitHub** has the commands that work on a whole
  repository, such as creating, forking and renaming one, plus
  **Notifications...**, **Security Alerts...** and Codespaces.

None of these has a key out of the box, so that they do not take keys a
writer needs. Press `Ctrl+Shift+P` for the Command Palette and type "GitHub" to
find any of them by name, or give one a key of your own in the Keymap Editor.

The GitHub commands belong to the feature called GitHub Remote Access, which
is part of QUILL's Developer profile. If the GitHub rows are missing from the
File and Tools menus, that feature is off. Press `Alt+Shift+P` to switch
profile and choose Developer, or turn on GitHub Remote Access on its own in
**Profiles and Features...**, in the **Customize and Support** submenu of the
Tools menu.

### In QUILL Lite

In QUILL Lite, choose **File > GitHub Workbench...**: press `Alt+F`, then `G`.
It opens GitHub Items. Everything else in this book is reached from there.
QUILL Lite has no Tools > Git and GitHub menu, so the commands this book
describes as being on QUILL's menus are QUILL's alone.

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
and every command that changes GitHub. You sign in with a personal access
token: a long password-like string that GitHub makes for you and that you can
cancel at any time.

### Making a token

1. Open github.com in your browser and sign in.
2. Go to your profile settings, then **Developer settings**, then
   **Personal access tokens**, then **Tokens (classic)**.
3. Choose **Generate new token (classic)**.
4. Give it a name you will recognise, such as "QUILL on my laptop", and an
   expiry date.
5. Check the scopes you need. The list below says which do what.
6. Generate the token and copy it. GitHub shows it only once.

A classic token is the simpler choice for the workbench. Some parts of GitHub,
the notifications inbox among them, do not accept the newer fine-grained
tokens.

The scopes, and what each one lets the workbench do:

- `repo`: private repositories, and everything that writes: issues, comments,
  reviews, merges, releases and workflow runs. Most people want this one.
- `notifications`: your notifications inbox, if you did not choose `repo`.
- `project`: Projects boards. `read:project` is enough to read them.
- `read:org`: the organizations you belong to, for browsing their
  repositories.
- `workflow`: only if you will save changes to workflow files themselves.
- `delete_repo`: only if you will delete repositories from QUILL.

If your organization uses single sign-on, there is one more step. On GitHub's
token page, choose **Configure SSO** beside the token and authorize it for the
organization. Until you do, GitHub refuses the organization's repositories
even though the token is fine everywhere else.

### Adding the token

In QUILL, choose **File > Open from Remote > Manage GitHub Accounts...**, then
**Add Account...**. The **Sign in to GitHub** window has one field,
**Personal access token**. Paste the token and press **Connect**. QUILL asks
GitHub who the token belongs to before it keeps it, so a mistyped or expired
token is turned away with "GitHub did not confirm an account for that token.
Nothing was saved." When GitHub confirms it, you hear "Added and switched to
GitHub account" and your GitHub username.

The same window has **Continue Anonymously** for working as a guest, and
**Cancel**. None of its buttons has an access key, so Tab to the one you want.

Some QUILL commands on the Tools menu need an account before they can do
anything. If you choose one while signed out, QUILL asks "This action needs a
signed-in GitHub account. Sign in now?" and opens the same window.

### Where the token is kept

The token is kept in your operating system's own secure store: Windows
Credential Manager on Windows, or the Keychain on a Mac. A portable copy keeps
it in its own encrypted file instead. It is never written
into a settings file or a log. QUILL sends it to GitHub's own servers and
nowhere else. When GitHub hands a download to another address, such as a log
or an artifact, QUILL fetches that without the token.

### In QUILL Lite

QUILL Lite has no window for signing in. It works as a guest: it reads public
repositories, and the commands that change GitHub say they need a signed-in
account. To review, reply, merge or triage your notifications, use QUILL.

## More than one account

If you have a personal account and a work account, keep both.
**Manage GitHub Accounts...** shows the active account at the top, such as
"Active account: your-name on github.com", and a list of every account you
have added. From there:

- **Use Selected Account** makes the chosen account the active one. You hear
  "Switched to GitHub account" and its name.
- **Remove Selected Account** deletes that account's token from this computer.
  It does not ask first, and it does not cancel the token on GitHub; do that
  on GitHub's token page if you want it gone for good.
- **Add Account...** adds another.
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
QUILL's Tools menu and the GitHub CLI commands are switched off the same way.
Start normally to use them again.

## A two-minute tour

This tour reads a public repository, so you can do it before you sign in.

1. Open GitHub Items: in QUILL, **File > Open from Remote > GitHub Items...**;
   in QUILL Lite, `Alt+F`, then `G`.
2. If this is the first time, press **Continue** in the GitHub Access window.
3. Type a repository you know, such as `community-access/quill`, and press
   Enter. You hear the repository's name, how many items loaded, and a short
   list of the keys that work here. Focus moves to the list, on the first row.
4. Arrow down the list. Each row is an issue or a pull request: its number,
   whether it is an issue or a PR, its state and its title.
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
