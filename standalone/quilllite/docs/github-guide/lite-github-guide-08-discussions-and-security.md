# Chapter 8: Discussions and security

## What this chapter covers

Two kinds of conversation that are not issues. Discussions are a repository's
forum: questions, ideas and announcements, with threaded replies, answers and
polls. Security alerts are GitHub telling a repository about a vulnerable
package, a weakness in the code, or a secret committed by mistake. This
chapter covers reading and taking part in both, a repository's security
policy and advisories, reporting a vulnerability privately, letting a blocked
secret through, reviewing a pull request's dependencies, an organization's
security overview, setting secrets safely, searching GitHub's Advisory
Database, and saving a software bill of materials for a security review.

## Discussions

### Finding them

In Explore, choose **Repository Discussions** in **View:** (`Alt+V`), with the
repository in **Repository:** (`Alt+R`). You need to be signed in. Each row
reads the number, the title and the category, and whether it is answered:
"#12 How do I turn off the sounds? (Q&A; Answered by alice)".

A discussion link pasted into **Open Link...** in GitHub Items opens here too.

### Reading a thread

Press Enter on a discussion, or choose **Open Discussion Thread...** from its
context menu. The window **Discussion #12:** and the repository has:

- **Thread** (`Alt+T`), a list. The first row is the discussion itself, then
  each comment followed by its replies: "Comment by bob, the answer, 2
  replies:" and its first line, then "Reply by alice:" and so on. The answer,
  if there is one, says so.
- **Text** (`Alt+X`), the selected row in full. Enter in the list takes you
  there.
- **Reply...** (`Alt+R`), **Mark as Answer...** (`Alt+M`),
  **Open on GitHub** (`Alt+O`), **Refresh** (`Alt+F`) and **Close**.

When it loads, the status line says who answered it, or "Not answered yet.",
and how many comments and replies there are. A category that does not take
answers says "This category does not take answers."

A discussion with a poll reads it one option to a line, after the question
and the total: "Poll: Which sound pack?, 25 votes in all", then "Classic: 15
votes, 60 percent".

### Replying

**Reply...** (`Alt+R`) replies to the selected comment, or to the discussion
itself when the first row is selected. It opens the comment window, titled
with which: "Reply to bob's comment", with Insert Mention (bob first),
Insert Reference, Insert Emoji, Insert Saved Reply, Preview and the check
before posting. You hear "Posted your reply". A closed discussion takes no
replies, so the button is unavailable.

### Marking the answer

In a question-and-answer category, the person who asked, or a maintainer, can
mark one comment as the answer. Select the comment and press
**Mark as Answer...** (`Alt+M`). QUILL asks first: "Mark bob's comment as the
answer to this discussion?" On the comment that is already the answer, the
button reads **Unmark Answer...**, still on `Alt+M`. A reply cannot be the
answer, only a top-level comment.

### Starting a discussion

In the **Repository Discussions** view, signed in, choose **New Discussion...**
from the context menu.

- **Category:** (`Alt+C`). Categories that take answers say ", takes answers".
- **Title:** (`Alt+T`) and **Body:** (`Alt+B`).
- **Start Discussion**, or **Cancel**.

You hear "Started the discussion" with its title and category.

### Polls as a table, and Vote...

In the GitHub Workbench, **Repository > Discussions** lists the discussions.
When one has a poll, its details end with the poll as a table: a line with
the question, the total and whether you may vote, "Poll: Which sound pack?,
25 votes in all. You may vote: Vote...", then "Option, votes, percent, your
vote:" and a row for each option, "Classic, 15 votes, 60 percent, your vote:
no". The discussion's **Properties...** has the same table on its **Poll**
page, under the question.

**Vote...** on the discussion's context menu, or **Add...** or **Change...**
under the Poll page's table, lists the options with their votes. Choose one
and you hear the outcome once, with the new count: "Voted for Classic. It has
16 votes now, of 26 in all." GitHub keeps a poll vote once it is cast: if
you have voted, Vote... says which option you chose, and **Remove** under
the table says a vote cannot be taken back. An account set to Read Only in
the Workbench (**Workbench Options**, Accounts) cannot vote: Vote... says so
and sends nothing.

### Pinned discussions: the spotlight

**Repository > Discussions > Pinned (spotlight)** lists the discussions
pinned at the top of the repository's Discussions page, first to last in
GitHub's order: "1. #12 How do I turn off the sounds? (Q&A; Answered by
alice)". The details begin "Pinned 1 of 3, by alice." Enter opens the
thread, and Vote... and Properties work as in the main list. If nothing is
pinned, the list is empty and the status bar says so.

GitHub's API reads pinned discussions but cannot pin, unpin or reorder one,
so this place is read only, and each pinned discussion's details say so. To
pin one, use **Open on GitHub** and pin it on GitHub's own page.

### Categories and their sections

**Repository > Discussions > Categories** lists the repository's discussion
categories. Where GitHub gives sections, each section is a row, "Section:
Q&A (3 categories)", and Enter opens it: its categories follow a first row,
**All sections**, which comes back. GitHub's API does not yet say which
section a category is in, so today the place lists every category in
GitHub's order, and the status bar says why once. Each category reads its
name, and ", question and answer" when a reply can be marked the answer;
Enter on one goes to Discussions with the list narrowed to that category's
name.

## Security alerts

### Finding them

In Explore, choose **Repository security alerts** in **View:**, with the
repository in **Repository:**. The view brings three kinds of alert together:

- **Dependabot**: a package the repository uses has a known vulnerability.
- **Code scanning**: a tool found a likely weakness in the code.
- **Secret scanning**: something that looks like a password or key was
  committed.

Each row reads the kind, the severity, the package or file, and a summary:
"Dependabot: high: lodash — Prototype pollution".

Reading alerts needs a signed-in account that can see the repository's
security alerts. If yours cannot read one kind, or the repository has that
kind turned off, QUILL says that kind is unavailable rather than showing it as
having no alerts. A secret's value is never loaded into the view.

In QUILL, **Tools > Git and GitHub > GitHub > Security Alerts...** lists a
repository's open Dependabot alerts on their own.

### Dismissing an alert

Not every alert needs a fix. The package might be used only in tests, or the
finding might be wrong. On an alert's row, **Dismiss Alert...** on the context
menu asks three things:

1. **Why**, from GitHub's own reasons for that kind of alert:
   - Dependabot: "A fix has already been started", "This alert is
     inaccurate or incorrect", "No bandwidth to fix this", "Vulnerable code
     is not actually used", or "Risk is tolerable to this project".
   - Code scanning: "False positive", "Won't fix" or "Used in tests".
   - Secret scanning: "False positive", "Won't fix", "Revoked" or "Used in
     tests".
2. **A comment**, which you can leave empty. GitHub takes up to 280
   characters.
3. **Are you sure**: the confirmation names the alert and the reason, and says
   everyone with access will see it as dismissed.

Cancel at any step and nothing is sent. QUILL reports the dismissal only when
GitHub sends the alert back in its new state.

An alert's Properties sheet (Alt+Enter) closes it the same way. Each kind
closes in its own words: a Dependabot or code scanning alert is dismissed,
a secret is resolved, and the sheet offers only that kind's reasons. A
choice that does not fit the kind is refused before anything is sent.
GitHub marks an alert fixed itself, so the sheet does not offer that.

### Reopening an alert

Dismissed and fixed alerts have their own view, **Dismissed and resolved
security alerts**. There, **Reopen Alert...** on the context menu asks first,
then reopens the alert.

### Copilot Autofix

On a code scanning alert, **Copilot Autofix...** says whether Copilot has a
suggested fix. When it has none, QUILL Lite offers to ask for one; when the fix is
ready, it offers to commit it to a branch you name, with a commit message you
may leave empty, so it can go through a pull request like any other change.
**Show Every Place** lists each file and line the alert was found in.

### Letting a blocked secret through

When push protection is on, GitHub refuses a push that contains something
that looks like a password or key, and `git push` prints a placeholder id for
each one. If the secret is not real, is only used in tests, or you will fix
it later, select the repository and choose **Allow a Blocked Secret...** on
its context menu. QUILL Lite asks for the placeholder id, then why, from GitHub's
three reasons: "It is not really a secret (a false positive)", "It is only
used in tests", or "It is real, and I will fix it later". It asks once more,
naming the repository, because the secret will stay in the repository's
history. Then you hear how long the allowance lasts, such as "GitHub will let
the GitHub personal access token through until 2026-11-19 at 18:00 UTC. Push
again now; GitHub keeps an alert for it."

### Requests to dismiss or bypass

Some organizations want a security manager to approve each dismissal or
push protection bypass. GitHub offers those requests, and reviewing them,
only on GitHub Enterprise Cloud, which QUILL Lite does not support; review them on
GitHub's own security page with **Open on GitHub**.

## Dependency review on a pull request

Before you merge a pull request, it helps to know what it does to your
dependencies. On a pull request's context menu, **Dependency Review** compares
the dependency graph at the pull request's base commit with its head commit
and shows the answer in a window to read. The first line is the summary:
"Added 3, removed 1. 1 added dependency has known vulnerabilities." Each
change follows, the vulnerable ones first: "Added: lodash 4.17.20 (npm,
package.json), licence MIT. Vulnerable: high, GHSA-p6mc-m468-83gw, Prototype
Pollution in lodash." A repository whose dependency graph is off says so in
words. **Compare Dependencies...** on a repository does the same between any
two branches, tags or commits you type.

## An organization's security overview

On an organization's context menu, **Security Overview** counts the open
alerts in every repository you can see there, worst first: "acme/web: 3
Dependabot (1 critical, 2 high); 1 code scanning (high); 2 secret scanning."
A totals line follows. If GitHub will not show you one kind, that kind is
named and the reason given, never counted as none: missing permission is not
the same as no risk. GitHub sends 100 alerts of a kind at a time; when a kind
reaches that, QUILL Lite says so and points you to the organization's own alert
lists, under the organization in the tree, for the rest.

## Security policy and reporting

Found a security hole in someone's project? Do not open a public issue: tell
the maintainers privately first. **Repository > Security > Policy** in the
GitHub Workbench says how. Its first row is the repository's security policy,
"Security policy: SECURITY.md. Enter opens it.", found in the root, `.github`
or `docs`, or says the repository has none. The second says whether private
vulnerability reporting is on. When it is, anyone signed in can report there,
below.

## Security advisories

A security advisory is a project's notice of a vulnerability: which package
and versions, how serious, and where it is fixed. Each has a GHSA (GitHub
Security Advisory) id, and often a CVE (Common Vulnerabilities and Exposures)
number too.

**Repository > Security > Advisories** lists a repository's advisories, one
sentence each: "GHSA-q4hm-2345-wxyz: high severity, draft: Path traversal in
the importer." Published advisories are listed for everyone; drafts and
private reports only for the repository's administrators and security
managers, and anyone else hears that rather than an empty list. The details
pane says which packages and versions are affected, which version fixes it,
who is credited, and the full description.

**New Here** in Advisories (`Ctrl+N`) asks which you want:

- **Report a vulnerability privately to the maintainers**, for anyone, when
  private reporting is on. QUILL Lite asks for a one-line summary, then what it is,
  how to reproduce it and what it lets an attacker do, then how severe it is,
  with "Not sure" as a choice. Only the maintainers see the report.
- **Draft an advisory**, for maintainers. The same three questions, then the
  affected package and its ecosystem, such as npm or pip, which you can leave
  for later. A draft is private until it is published.

On an advisory's context menu:

- **Publish or Close Advisory...** publishes it, closes it, or makes it a
  draft again. A report someone sent privately reads "private report to
  review"; on it, the same command offers **Accept it**, which makes it a draft
  advisory that you and the reporter work on, or **Close it**. Publishing makes it public for good, puts it in GitHub's
  Advisory Database and alerts the projects that depend on the package, so
  QUILL Lite asks you to type its GHSA id first.
- **Request CVE...** asks GitHub for a CVE number for a draft. GitHub reviews
  each request, so the number comes later.

On a draft, **Advisory Comments**, **Comment on Advisory...** and **Edit an
Advisory Comment...** are its private discussion, and **Make a Private Fork for
the Fix** makes the temporary private fork GitHub offers for working on it.

## Secrets

A secret is a value a workflow, Dependabot, a codespace or the Copilot agent
uses but nobody reads again, such as a deploy token. They are lists in the
tree: a repository's **Settings**, an organization's own node, and an
environment's **Secrets...** on its row. Each row says the secret's name and
when it changed: "Secret DEPLOY_TOKEN, changed 2026-11-02. Its value is never
shown."

A secret's value only ever goes one way, to GitHub:

- **New Here** (`Ctrl+N`) asks for its name, then its value in a password box.
  QUILL Lite seals the value on this computer with that repository's,
  environment's or organization's own public key (a libsodium sealed box, as
  GitHub requires) and sends only the sealed form. The value is never read
  back, said, shown, logged or kept: once the call ends, it is gone.
- **Change...** on a secret's row sends a new value the same way. For an
  organization's secret you may leave the value empty to keep it, and choose
  which of the organization's repositories may use it: **all**, **private**,
  or **selected**.
- **Repositories Allowed...** on a selected secret checks the repositories
  that may use it now; check or uncheck them, and QUILL Lite adds and removes them
  one at a time, so a change somebody else made meanwhile is kept.
- A repository's Actions secret also has a **Properties** sheet. Its **New
  value** box is a password box that always opens empty; Copy as Text says
  "hidden", the preview before it is sent says "(hidden)", the box is emptied
  once GitHub has it, and Change History records only that it was set.

## Searching the Advisory Database

**Search > Security Advisories** searches GitHub's Advisory Database, every
published advisory for every package. Type a package name, such as `lodash`,
a CVE number, or a GHSA id, then Enter. Each row reads like the ones above.

## A software bill of materials

A software bill of materials, or SBOM, is the list of every package a
repository depends on, with versions and licences. Security reviews,
procurement and some contracts ask for one. GitHub builds it from the
repository's dependency graph, in SPDX (Software Package Data Exchange), the
standard format those tools read.

In the GitHub Workbench, select a repository and choose **Repository > Export
Software Bill of Materials...** (`Ctrl+Alt+B`), or the same row on
**Repository Actions** (`Ctrl+Shift+G`). A Save dialog offers a name such as
`owner-name.spdx.json`. When it is saved you hear "Saved owner-name.spdx.json:
212 packages, in SPDX format." The file is JSON (JavaScript Object
Notation), so QUILL Lite opens it like any other text file.

A repository whose dependency graph is turned off has nothing to export, and
QUILL Lite says where to turn it on: the repository's settings, under Code
security. Nothing is saved in that case.

---

- Previous: [Chapter 7: Code and repositories](lite-github-guide-07-code-and-repositories.html)
- Next: [Chapter 9: Codespaces and the GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html)
- [Contents](lite-github-guide.html)
