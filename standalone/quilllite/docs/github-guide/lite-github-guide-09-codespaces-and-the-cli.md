# Chapter 9: Codespaces and the GitHub CLI

## What this chapter covers

A codespace is a computer GitHub runs for you in the cloud, already set up
with a repository and its tools. This chapter covers opening the Codespaces
page from GitHub Items, QUILL's Codespaces commands, and the GitHub CLI those
commands rely on, including how QUILL makes sure it is using the same account
as you.

Codespaces can cost money. GitHub gives each account some free hours a month
and charges for more. Everything here that could start one says so before it
does.

## Opening Codespaces from GitHub Items

In both apps, the context menu of any row in GitHub Items has
**Open in GitHub Codespaces...**. On a branch, it opens Codespaces for that
branch. QUILL asks first, reminds you that starting a codespace can incur
charges, and then opens GitHub's own Codespaces page in your browser. It does
not create anything itself, and it does not send your token. You make your
choices on GitHub's page.

## The GitHub CLI

QUILL's own Codespaces commands use GitHub's command-line tool, called `gh`,
because it is the only way GitHub offers to manage codespaces from outside the
website. QUILL needs it installed. If it is not, you hear that QUILL did not
find it, with the address to get it from, `cli.github.com`.

On Windows and macOS, QUILL can fetch it for you instead:
**Help > Download Optional Components...** has the GitHub CLI, a portable copy
of about 14 MB that QUILL checks before using.

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

## QUILL's Codespaces commands

In QUILL, these are on **Tools > Git and GitHub > GitHub**. They are QUILL's
alone, and need the GitHub CLI and a signed-in account.

### Codespaces...

**Codespaces...** lists your codespaces. Each reads its name, its repository,
whether it is running, and how far its branch is ahead of or behind GitHub.
With none, you hear "No codespaces for" your account, and a pointer to
Create Codespace.

Choose one and a second list offers what to do with it:

- **Open in Browser (may start the codespace)**, after a confirmation, because
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

These two commands are newer than the rest of the workbench, and have not yet
been tried against every kind of codespace. If one says something that does
not match what you see on GitHub, please tell us (Chapter 10).

## Other things that use Git or the CLI

**Sync Folder with GitHub...**, on the same QUILL menu, keeps a folder on your
computer in step with a repository, using Git. The QUILL user guide covers it
under
[Sync a folder with GitHub](https://www.quillforall.org/docs/quill-guide-14-projects-notes-and-the-quillville-family.html#sync-a-folder-with-github).

Safe Mode switches off every command in this chapter: you hear "GitHub CLI
commands are disabled in Safe Mode".

---

- Previous: [Chapter 8: Discussions and security](lite-github-guide-08-discussions-and-security.html)
- Next: [Chapter 10: Troubleshooting, privacy and help](lite-github-guide-10-troubleshooting.html)
- [Contents](lite-github-guide.html)
