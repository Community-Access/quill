# Chapter 9: Codespaces and the GitHub CLI

## What this chapter covers

A codespace is a computer GitHub runs for you in the cloud, already set up
with a repository and its tools. You might want one to try a pull request
without setting anything up on your own computer, or to work on a machine
bigger than yours.

In this chapter you list, make, start, stop and delete codespaces in the
GitHub Workbench, and meet the GitHub CLI, the command-line tool a few of
QUILL's own Codespaces commands use, and how QUILL keeps the two sign-ins on
the same account.

By the end you will know where your codespaces are, what each command does
before you run it, and how to keep one from running, and charging, when you
are not using it.

Codespaces can cost money. GitHub gives each account some free hours a month
and charges for more, for as long as a codespace runs. Everything here needs a
signed-in account.

## Your codespaces in the Workbench

Two places in the tree list codespaces:

- **Repositories > My Codespaces** lists every codespace of yours, in any
  repository.
- A repository's **Code > Codespaces** lists your codespaces for that one
  repository.

Each row is one sentence: the codespace's name, its repository and branch,
its state as GitHub words it (such as Available or Shutdown), its machine, and
when it was last used. Its context menu has:

- **Show Details**: the same, with its address on GitHub.
- **Start** and **Stop**. You hear "Starting" and its name, or "Stopping" and
  its name, and that its files are kept. A stopped codespace does not charge
  for computing time.
- **Change Machine...** lists the machines GitHub offers for it and uses the
  one you choose from its next start. When there is no other, QUILL says so.
- **Export to a Branch** puts the codespace's changes on a branch of their
  own, and says when that is done.
- **Publish to a New Repository...**, for a codespace made from a template:
  give the new repository a name, or leave it empty for GitHub's, and choose
  private or public.
- **Delete...**, under More, asks first: changes you have not pushed or
  exported are lost.
- **Open on GitHub** and **Copy Link**.

## Making a codespace

There are three ways:

- **In a repository's Code > Codespaces**, press `Ctrl+N`. QUILL asks which
  branch, starting with `main`, then reads what a codespace for that
  repository can use and asks which machine, and which dev container when
  the repository has more than one. You hear "Making the codespace" and its
  name, and that it takes a minute or two to start.
- **On an open pull request**, **Open in a Codespace** makes one on the pull
  request's branch at once. Use it to try a change for real before you
  review it.
- **Open in Codespaces...**, on the context menu of a repository, branch or
  pull request, asks first, reminds you that starting a codespace can cost
  money, and then opens GitHub's own Codespaces page in your browser. It
  makes nothing itself and does not send your token. You make your choices
  on GitHub's page.

**Ctrl+N** and **Open in a Codespace** make and start a codespace straight
away, with no further question: choosing them is the decision. **Stop** it
when you are done.

If a repository's dev container asks for permissions you have not accepted,
QUILL says so and makes nothing. Open the repository's Codespaces on GitHub
once to accept them, then try again.

Values your codespaces read, such as a key for a private package registry,
are kept as secrets: **People > My Codespaces Secrets** for yours,
**Settings > Codespaces Secrets** for one repository's, and an organization's
own. Chapter 8 covers secrets.

## The GitHub CLI

Two of QUILL's Codespaces commands, below, use GitHub's command-line tool,
called `gh`. Everything in the Workbench above talks to GitHub directly and
does not need it. If `gh` is not installed when a command needs it, you hear
that QUILL did not find it, with the address to get it from, `cli.github.com`.

On Windows and macOS, QUILL can fetch it for you instead:
**Help > Download Optional Components...** has the GitHub CLI, a portable copy
of about 14 MB that QUILL checks before using. A copy of `gh` already
installed on your computer is always used first.

### Two sign-ins, one account

`gh` signs in to GitHub on its own, separately from QUILL. Sign in once in a
terminal with `gh auth login`. QUILL never hands `gh` its token.

Because there are two sign-ins, they can disagree: you might be signed in to
QUILL with your work account and to `gh` with your personal one. Before each
Codespaces command, QUILL asks `gh` which account it is using. If that is not
the account QUILL is using, it stops and tells you, naming both: "GitHub CLI
is signed in as" one, "but QUILL is using" the other, and asks you to switch
one of them first. This is what keeps a codespace, and its bill, off the wrong
account.

### Using gh's sign-in in QUILL

It works the other way too. If `gh` is already signed in, you do not have to
sign in to QUILL again. In **Manage GitHub Accounts...** (`Ctrl+Shift+K` in
the Workbench), choose **Use GitHub CLI Sign-In...**. QUILL asks which
server's sign-in to use, `github.com` or your GitHub Enterprise Server's
name, asks `gh` for it, checks with GitHub which account it is, and asks you
before it keeps it. Chapter 1 covers accounts in full.

## QUILL's Codespaces commands

These two are QUILL's alone, and need the GitHub CLI and a signed-in
account. In QUILL they are on **Tools > Git and GitHub > GitHub**, and in the
Workbench's **Repository Actions...** (`Ctrl+Shift+G`).

### Codespaces...

**Codespaces...** lists your codespaces. Each reads its name, its repository,
whether it is running, and how far its branch is ahead of or behind GitHub.
With none, you hear "No codespaces for" your account, and a pointer to
Create Codespace.

Choose one and a second list offers what to do with it:

- **Open in Browser (may start the codespace)**, after a question, because
  opening a stopped codespace starts it.
- **View Codespace Health**: its repository, state, machine, location, when it
  was last used and created, and its Git status.
- **Stop**, which stops it running, and charging.
- **Delete**, which asks first: "Delete codespace" and its name, "This cannot
  be undone." Anything in it you have not pushed to GitHub goes with it.

### Create Codespace...

**Create Codespace...** asks for the repository as `owner/repo`, then the
branch, which you can leave empty for the default branch. It checks the CLI's
account, then asks you to confirm in a window whose title says it uses paid
GitHub compute. You hear "Created codespace" with its name and state.

**In QUILL Lite**, which has neither command, use the Workbench's own
Codespaces places above. They do not need the GitHub CLI.

## Other things that use Git or the CLI

**Sync Folder with GitHub...**, on the same QUILL menu, keeps a folder on your
computer in step with a repository, using Git. The QUILL user guide covers it
under
Sync a folder with GitHub.

Safe Mode switches off every command in this chapter. The Workbench does not
open in Safe Mode, and the CLI commands say "GitHub CLI commands are disabled
in Safe Mode".

## A walk-through: a codespace for the practice pull request, and back

This one costs a few minutes of GitHub's free codespace hours. Make the
practice repository first with **Help > Practice on GitHub...**
(`Ctrl+Alt+P`) if you have not.

1. In the Workbench, press `Ctrl+L`, type `quill-practice` and press Enter.
2. Press `Ctrl+Shift+2` for its Pull Requests, and F6 to the list.
3. On the pull request that fixes the greeting, press `Shift+F10`, open More,
   and choose **Open in a Codespace**. You hear "Making the codespace" and its
   name.
4. Go to **Repositories > My Codespaces** and press `F5` after a minute or
   two. Its row says Available when it is running.
5. Press `Shift+F10` on it and choose **Stop**. You hear "Stopping" and its
   name, and that its files are kept.
6. When you no longer need it, choose **Delete...** from the same menu and
   answer Yes.

---

- Previous: [Chapter 8: Discussions and security](lite-github-guide-08-discussions-and-security.html)
- Next: [Chapter 10: Troubleshooting, privacy and help](lite-github-guide-10-troubleshooting.html)
- [Contents](lite-github-guide.html)
