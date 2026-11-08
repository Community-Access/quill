# The GitHub Guide for QUILL and QUILL Lite

This is the book on doing GitHub work with a screen reader in QUILL and QUILL
Lite: reading and triaging issues, reviewing pull requests line by line,
finding out why a build failed, browsing code, and keeping on top of your
notifications. It is a book of its own, beside each editor's user guide,
because there is a lot to say and you may only need part of it.

The same GitHub windows ship in both editors, and so does this book. Where the
two differ, a short paragraph starting **In QUILL Lite** says how.

## How to read this book

- **New to it?** Read Chapters 1 and 2 in order. They get you signed in and
  moving. Then go to the chapter for the job in front of you.
- **Reviewing pull requests?** Chapter 5.
- **A build failed?** Chapter 6, and its section on What Failed.
- **Something went wrong?** Chapter 10 has the sentences QUILL says when
  GitHub refuses, and what to do about each.
- **Looking up a key?** Chapter 11 has every one, window by window.

Each chapter is a level 3 heading on this page, so pressing 3 in JAWS or NVDA
moves from chapter to chapter. Every chapter page starts with its title as a
level 1 heading, its main topics are level 2 headings, and at the bottom are
links to the chapters either side and back to these contents.

## Keys at a glance

- **Opening the workbench.** In QUILL, **File > Open from Remote > GitHub
  Items...**. In QUILL Lite, **File > GitHub Workbench...**: `Alt+F`, then
  `G`.
- **Enter goes in, `Ctrl+O` opens on GitHub, Backspace comes back out.**
- **Tab** reads the selected row's details; Shift+Tab returns to the list.
- **Shift+F10** opens the context menu, which holds everything you can do
  with the selected row.
- `Alt+N` and `Alt+P` move between comments, and between rows in History and
  Blame.
- `Ctrl+Shift+W` says what failed in a workflow run.
- `Ctrl+Shift+L` says how much of GitHub's hourly allowance is left.
- In a pull request review, `Ctrl+R` replies to a thread and `Ctrl+Shift+R`
  resolves it.

## The chapters

### [Chapter 1: Getting started](lite-github-guide-01-getting-started.html)

What the workbench is, opening it in each editor, the one question QUILL asks
before it connects, signing in with a token, keeping more than one account,
and Safe Mode. It ends with a two-minute tour.

- [Opening the workbench](lite-github-guide-01-getting-started.html#opening-the-workbench)
- [Signing in](lite-github-guide-01-getting-started.html#signing-in)
- [More than one account](lite-github-guide-01-getting-started.html#more-than-one-account)
- [A two-minute tour](lite-github-guide-01-getting-started.html#a-two-minute-tour)

### [Chapter 2: Getting around](lite-github-guide-02-getting-around.html)

GitHub Items and Explore GitHub, control by control, the three keys that do
most of the moving, context menus, searching, and coming back where you left
off. Also pasting a GitHub link, and GitHub's hourly allowance.

- [The GitHub Items window, top to bottom](lite-github-guide-02-getting-around.html#the-github-items-window-top-to-bottom)
- [Enter, Ctrl+O and Backspace](lite-github-guide-02-getting-around.html#enter-ctrlo-and-backspace)
- [What QUILL says, and what it leaves to your screen reader](lite-github-guide-02-getting-around.html#what-quill-says-and-what-it-leaves-to-your-screen-reader)
- [Open GitHub Reference: paste any link](lite-github-guide-02-getting-around.html#open-github-reference-paste-any-link)
- [Rate limits and the readout](lite-github-guide-02-getting-around.html#rate-limits-and-the-readout)

### [Chapter 3: Your inbox and your work](lite-github-guide-03-inbox-and-your-work.html)

Going through your notifications from the keyboard: what each says, clearing
them and keeping your place. Then My Work, the attention queue and activity.

- [Triage: Done, Unsubscribe and Mark All Read](lite-github-guide-03-inbox-and-your-work.html#triage-done-unsubscribe-and-mark-all-read)
- [My Work](lite-github-guide-03-inbox-and-your-work.html#my-work)
- [The attention queue](lite-github-guide-03-inbox-and-your-work.html#the-attention-queue)

### [Chapter 4: Issues](lite-github-guide-04-issues.html)

Reading an issue and its comments, replying, reactions, the timeline, writing
a new issue from a template, labels, milestones, assignees and batch changes,
housekeeping, Projects, and starting work in a folder of its own.

- [Reading an issue](lite-github-guide-04-issues.html#reading-an-issue)
- [Writing a new issue](lite-github-guide-04-issues.html#writing-a-new-issue)
- [Changing many issues at once](lite-github-guide-04-issues.html#changing-many-issues-at-once)
- [Housekeeping](lite-github-guide-04-issues.html#housekeeping)
- [Projects and dependencies](lite-github-guide-04-issues.html#projects-and-dependencies)

### [Chapter 5: Pull requests and review](lite-github-guide-05-pull-requests-and-review.html)

The review outline and its one-sentence summary, what changed since your last
review, the diff, comments on a line or a range, suggested changes, sending a
review, and everything that gets a pull request merged.

- [The one-sentence summary](lite-github-guide-05-pull-requests-and-review.html#the-one-sentence-summary)
- [The review window](lite-github-guide-05-pull-requests-and-review.html#the-review-window)
- [Commenting on a line or a range](lite-github-guide-05-pull-requests-and-review.html#commenting-on-a-line-or-a-range)
- [Pending comments and sending your review](lite-github-guide-05-pull-requests-and-review.html#pending-comments-and-sending-your-review)
- [Getting a pull request merged](lite-github-guide-05-pull-requests-and-review.html#getting-a-pull-request-merged)

### [Chapter 6: Actions and checks](lite-github-guide-06-actions-and-checks.html)

Workflow runs, What Failed, jobs and logs, rerunning, cancelling and deleting
runs, checks, deployments waiting for approval, artifacts, caches, and secret
names.

- [What Failed](lite-github-guide-06-actions-and-checks.html#what-failed)
- [Jobs and logs](lite-github-guide-06-actions-and-checks.html#jobs-and-logs)
- [Doing something about a run](lite-github-guide-06-actions-and-checks.html#doing-something-about-a-run)
- [Artifacts](lite-github-guide-06-actions-and-checks.html#artifacts)

### [Chapter 7: Code and repositories](lite-github-guide-07-code-and-repositories.html)

Files at any branch, tag or commit, blame and history, branches and
comparisons, tags and releases, search, forks, insights, looking after a
repository, and watching, starring and following.

- [Browsing a repository's files](lite-github-guide-07-code-and-repositories.html#browsing-a-repositorys-files)
- [Blame and file history](lite-github-guide-07-code-and-repositories.html#blame-and-file-history)
- [Tags and releases](lite-github-guide-07-code-and-repositories.html#tags-and-releases)
- [Searching](lite-github-guide-07-code-and-repositories.html#searching)
- [Looking after a repository](lite-github-guide-07-code-and-repositories.html#looking-after-a-repository)

### [Chapter 8: Discussions and security](lite-github-guide-08-discussions-and-security.html)

Discussion threads, replies, answers, polls and new discussions; then
security alerts, dismissing them with a reason, and reopening them.

- [Discussions](lite-github-guide-08-discussions-and-security.html#discussions)
- [Security alerts](lite-github-guide-08-discussions-and-security.html#security-alerts)

### [Chapter 9: Codespaces and the GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html)

Opening Codespaces, QUILL's Codespaces commands, and the GitHub CLI they rely
on, including how QUILL keeps the two sign-ins on the same account.

- [The GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html#the-github-cli)
- [QUILL's Codespaces commands](lite-github-guide-09-codespaces-and-the-cli.html#quills-codespaces-commands)

### [Chapter 10: Troubleshooting, privacy and help](lite-github-guide-10-troubleshooting.html)

Every common refusal and what to do about it, exactly what goes over the
network, and how to reach a person.

- [The refusals, one by one](lite-github-guide-10-troubleshooting.html#the-refusals-one-by-one)
- [Privacy: what goes over the network](lite-github-guide-10-troubleshooting.html#privacy-what-goes-over-the-network)
- [Getting help](lite-github-guide-10-troubleshooting.html#getting-help)

### [Chapter 11: Keyboard reference](lite-github-guide-11-keyboard-reference.html)

Every key the workbench answers to, one window at a time.

---

- [QUILL Lite User Guide](../userguide.html)
