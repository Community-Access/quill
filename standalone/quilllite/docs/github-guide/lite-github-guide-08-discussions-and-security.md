# Chapter 8: Discussions and security

## What this chapter covers

You are here for one of two kinds of conversation that are not issues.
Discussions are a repository's forum: questions, ideas and announcements,
with threaded replies, answers and polls. Security alerts are GitHub telling a
repository about a vulnerable package, a weakness in the code, or a secret
committed by mistake.

You will read and take part in discussions, vote in a poll, mark an answer
and start a discussion of your own. Then you will find and triage security
alerts, let a blocked secret through, review what a pull request does to your
dependencies, read an organization's security overview, report a
vulnerability privately, work on an advisory, set secrets safely, search
GitHub's Advisory Database, and save a software bill of materials.

By the end you will know where each lives in the Workbench, what each asks
before it sends anything, and why QUILL says "could not read" rather than
"none" when GitHub will not show you something.

Discussions and security alerts need a signed-in account. Published
advisories and the Advisory Database can be read signed out.

## Discussions

### Finding them

**Discussions** under a repository (`Ctrl+Shift+3`) lists them. Each row reads
the number, the title and the category, and whether it is answered: "#12 How
do I turn off the sounds? (Q&A; Answered by alice)". A discussion link pasted
into **Open GitHub Address...** (`Ctrl+L`) opens here too.

Under Discussions are two more places:

- **Pinned (spotlight)** lists the discussions pinned at the top of the
  repository's Discussions page, first to last in GitHub's order: "1. #12 How
  do I turn off the sounds? (Q&A; Answered by alice)". The details begin
  "Pinned 1 of 3, by alice." Enter opens the thread, and Vote... and
  Properties work as in the main list. If nothing is pinned, the list is empty
  and the status bar says so. GitHub's API reads pinned discussions but cannot
  pin, unpin or reorder one, so this place is read only, and each pinned
  discussion's details say so. To pin one, use **Open on GitHub**
  (`Shift+Enter`) and pin it on GitHub's own page.
- **Categories** lists the repository's discussion categories. Where GitHub
  gives sections, each section is a row, "Section: Q&A (3 categories)", and
  Enter opens it: its categories follow a first row, **All sections**, which
  comes back. GitHub's API does not yet say which section a category is in,
  so today the place lists every category in GitHub's order, and the status
  bar says why once. Each category reads its name, and ", question and
  answer" when a reply can be marked the answer. Enter on one goes to
  Discussions with the list narrowed to that category's name.

### Reading a thread

Press Enter on a discussion, or choose **Open Discussion Thread** from its
context menu. The window **Discussion #12:** and the repository has:

- **Thread** (`Alt+T`), a list. The first row is the discussion itself, then
  each comment followed by its replies: "Comment by bob, the answer, 2
  replies:" and its first line, then "Reply by alice:" and so on.
- **Text** (`Alt+X`), the selected row in full. Enter in the list takes you
  there.
- **Reply...** (`Alt+R`), **Mark as Answer...** (`Alt+M`), **Open on
  GitHub** (`Alt+O`), **Refresh** (`Alt+F`) and **Close**.

When it loads, the status line says who answered it, or "Not answered yet.",
and how many comments and replies there are. A category that does not take
answers says "This category does not take answers."

To keep the whole thread, **Read as Document...** (`Ctrl+Shift+I`) on the
discussion's row opens it as one document, a heading per post, in the editor,
or saves it as Markdown or HTML.

### Replying

**Reply...** (`Alt+R`) replies to the selected comment, or to the discussion
itself when the first row is selected. It opens the comment window, titled
with which: "Reply to bob's comment", with Insert Mention (bob first), Insert
Reference, Insert Emoji, Insert Saved Reply, Preview and the check before
posting. You hear "Posted your reply". A closed discussion takes no replies,
so the button is unavailable.

To change or remove a comment you may edit, use **Edit a Comment...** or
**Delete a Comment...** on the discussion's row. Each asks which comment;
Delete asks again before it deletes.

### Marking the answer

In a question-and-answer category, the person who asked, or a maintainer, can
mark one comment as the answer. Select the comment in the thread and press
**Mark as Answer...** (`Alt+M`). QUILL asks first: "Mark bob's comment as the
answer to this discussion?" On the comment that is already the answer, the
button reads **Unmark Answer...**, still on `Alt+M`. Only a top-level comment
can be the answer, never a reply.

### Starting a discussion

In Discussions, press `Ctrl+N`. QUILL reads the repository's categories and
asks which; a category that takes answers says ", takes answers".

- When the category has its own discussion form, the form opens as a real
  form, a labelled control for each question, the same way an issue form
  does (Chapter 4).
- Otherwise the **New Discussion** window asks for **Title:** (`Alt+T`) and
  **Body:** (`Alt+B`).

**Start Discussion** shows what will be sent and asks once more. You hear
"Started discussion #14 in Q&A." If the category's form asks for labels,
the question says that starting a discussion this way does not add them.

### Polls as a table, and Vote...

When a discussion has a poll, its details end with the poll as a table: a
line with the question, the total and whether you may vote, "Poll: Which
sound pack?, 25 votes in all. You may vote: Vote...", then "Option, votes,
percent, your vote:" and a row for each option, "Classic, 15 votes, 60
percent, your vote: no". In the thread window the poll reads one option to a
line instead: "Classic: 15 votes, 60 percent". The discussion's
**Properties...** (`Alt+Enter`) has the same table on its **Poll** page,
under the question.

**Vote...** on the discussion's context menu, or **Add...** or **Change...**
under the Poll page's table, lists the options with their votes. Choose one
and you hear the outcome once, with the new count: "Voted for Classic. It has
16 votes now, of 26 in all." GitHub keeps a poll vote once it is cast: if you
have voted, Vote... says which option you chose, and **Remove** under the
table says a vote cannot be taken back. An account whose Workbench level is
Read Only (**Account > Roles and Access > Workbench Level for This
Account...**) cannot vote: Vote... says so and sends nothing.

### Upvoting, closing and deleting

A discussion's context menu also has:

- **Upvote** and **Remove Upvote**. An upvote helps a discussion rise in the
  list.
- **Close Discussion...**, which asks whether it is resolved, outdated or a
  duplicate, and **Reopen Discussion**. You hear "Closed the discussion." or
  "Reopened the discussion."
- **Delete Discussion...**, which deletes it with every comment in it after
  asking, because it cannot be undone. It needs admin access to the
  repository.

<!-- PR#1973 -->
### From a discussion to an issue

When a discussion turns into work, **Create Issue from Discussion...** on its
row opens an issue for it. It reads the discussion first, then asks for the
issue's title, the discussion's to start with, and its text, which begins
with a link back to the discussion and quotes it; change either as you like.
Last it asks how, naming the repository and your account: open the issue and
comment on the discussion with the issue's link, or open the issue only.
Nothing is sent until you answer.

GitHub has no way, in its API, to turn an issue into a discussion or a
discussion into an issue; its web page does that, through **Open on GitHub**.

<!-- PR#1973 -->
### What links to what: Related...

**Related...** on a discussion, an issue or a pull request lists the items
linked to it, each with its repository, its state and how it is linked: the
pull requests that close an issue, the issues a pull request closes, what
mentioned it, and the issues, pull requests and discussions its own text and
comments link to. Enter opens the selected one on GitHub, and Copy Link
copies its address. GitHub keeps no record of what links to a discussion, so
a discussion's list is only what the discussion and its replies link to, and
the list says so. When GitHub would not say what something is, the list says
that part is unread, never that there is none.

## Security alerts

### Finding them

**Security** under a repository (`Ctrl+Shift+8`) has the repository's
security places. **Alerts** brings three kinds of alert together:

- **Dependabot**: a package the repository uses has a known vulnerability.
- **Code scanning**: a tool found a likely weakness in the code.
- **Secret scanning**: something that looks like a password or key was
  committed.

Each row reads the kind, the severity, the package or file, and a summary:
"Dependabot: high: lodash, Prototype pollution".

Reading alerts needs a signed-in account that can see the repository's
security alerts. If yours cannot read one kind, or the repository has that
kind turned off, QUILL says that kind is unavailable rather than showing it
as having no alerts. A secret's value is never asked for, so it is never in
the list, the details, or a file you export with **Export List...**
(`Ctrl+Shift+X`).

In QUILL, **Tools > Git and GitHub > GitHub > Security Alerts...** opens the
Workbench at this place.

An alert's context menu has **Open**, **Dismiss or Reopen Alert...**,
**Copilot Autofix...**, **Show Every Place**, **Open on GitHub** and, on a
secret scanning alert, **Where It Was Found**.

### Dismissing an alert

Not every alert needs a fix. The package might be used only in tests, or the
finding might be wrong. **Dismiss or Reopen Alert...** on an open alert asks
three things:

1. **Why**, from GitHub's own reasons for that kind of alert:
   - Dependabot: "A fix has already been started", "This alert is
     inaccurate or incorrect", "No bandwidth to fix this", "Vulnerable code
     is not actually used", or "Risk is tolerable to this project".
   - Code scanning: "False positive", "Won't fix" or "Used in tests".
   - Secret scanning: "False positive", "Won't fix", "Revoked" or "Used in
     tests".
2. **A comment**, which you can leave empty. GitHub takes up to 280
   characters.
3. **Are you sure**: the question names the alert and the reason, and says
   everyone with access will see it as dismissed.

Cancel at any step and nothing is sent. QUILL reports the dismissal only when
GitHub sends the alert back in its new state.

<!-- PR#1967 -->
An alert's Properties sheet (`Alt+Enter`) closes it the same way. Each kind
closes in its own words: a Dependabot or code scanning alert is dismissed, a
secret is resolved, and the sheet offers only that kind's reasons. A choice
that does not fit the kind is refused before anything is sent. GitHub marks
an alert fixed itself, so the sheet does not offer that.

### Reopening an alert

Dismissed and fixed alerts have their own place, **Security > Dismissed and
Resolved Alerts**. There, **Dismiss or Reopen Alert...** asks first, then
reopens the alert.

### Copilot Autofix

On a code scanning alert, **Copilot Autofix...** says whether Copilot has a
suggested fix. When it has none, QUILL offers to ask for one; when the fix is
ready, it offers to commit it to a branch you name, with a commit message you
may leave empty, so it can go through a pull request like any other change.
**Show Every Place** lists each file and line the alert was found in.

### Code scanning analyses

**Security > Code Scanning Analyses** lists the analyses GitHub has for the
repository, and **CodeQL Databases** the databases CodeQL built. `Ctrl+N` in
Code Scanning Analyses is **Upload SARIF File...**: results from a scanning
tool you ran yourself, for the branch you name.

### Letting a blocked secret through

When push protection is on, GitHub refuses a push that contains something
that looks like a password or key, and `git push` prints a placeholder id for
each one. If the secret is not real, is only used in tests, or you will fix it
later, select the repository and choose **Allow a Blocked Secret...** on its
context menu. QUILL asks for the placeholder id, then why, from GitHub's
three reasons: "It is not really a secret (a false positive)", "It is only
used in tests", or "It is real, and I will fix it later". It asks once more,
naming the repository, because the secret will stay in the repository's
history. Then you hear how long the allowance lasts, such as "GitHub will let
the GitHub personal access token through until 2026-11-19 at 18:00 UTC. Push
again now; GitHub keeps an alert for it."

**Secret Scanning History**, on a repository's context menu, says when
GitHub last scanned the repository for secrets, and how.

### Requests to dismiss or bypass

Some organizations want a security manager to approve each dismissal or push
protection bypass. GitHub offers those requests, and reviewing them, only on
GitHub Enterprise Cloud, which QUILL does not support; review them on
GitHub's own security page with **Open on GitHub**.

## Dependency review on a pull request

Before you merge a pull request, it helps to know what it does to your
dependencies. On a pull request's context menu, **Dependency Review**
compares the dependency graph at the pull request's base commit with its head
commit and shows the answer in a window to read. The first line is the
summary: "Added 3, removed 1. 1 added dependency has known vulnerabilities."
Each change follows, the vulnerable ones first: "Added: lodash 4.17.20 (npm,
package.json), licence MIT. Vulnerable: high, GHSA-p6mc-m468-83gw, Prototype
Pollution in lodash." A repository whose dependency graph is off says so in
words.

**Compare Dependencies...** on a repository does the same between any two
branches, tags or commits you type, and **Dependency Manifests** lists the
files GitHub reads the dependencies from.

## An organization's security overview

On an organization's context menu, **Security Overview** counts the open
alerts in every repository you can see there, worst first: "acme/web: 3
Dependabot (1 critical, 2 high); 1 code scanning (high); 2 secret scanning."
A totals line follows. If GitHub will not show you one kind, that kind is
named and the reason given, never counted as none: a missing permission is
not the same as no risk.

GitHub sends 100 alerts of a kind at a time, so the overview reads every page
of each list, however many there are. A small window shows that it is
reading, with Cancel (or `Escape`) to stop before the next page. Nothing is
said while it reads; at the end the report's last line says how much it read:
"Read every page: 351 alerts in 6 pages." If you stop it, the Workbench says
how many it had read and shows nothing, because part of a count would read as
the whole of it.

The organization's place also has the alerts themselves, every repository's
in one list: **Dependabot Alerts**, **Code Scanning Alerts**, **Secret
Scanning Alerts** and **Security Advisories**. Open a repository's own Alerts
to dismiss or resolve one. **Security Managers** lists the teams that may
manage security for every repository there.

## Security policy and reporting

Found a security hole in someone's project? Do not open a public issue: tell
the maintainers privately first. **Security > Policy** under the repository
says how. Its first row is the repository's security policy, "Security
policy: SECURITY.md. Enter opens it.", found in the root, `.github` or
`docs`, or says the repository has none. The second says whether private
vulnerability reporting is on. When it is, anyone signed in can report, as
below.

## Security advisories

A security advisory is a project's notice of a vulnerability: which package
and versions, how serious, and where it is fixed. Each has a GHSA (GitHub
Security Advisory) id, and often a CVE (Common Vulnerabilities and Exposures)
number too.

**Security > Advisories** lists a repository's advisories, one sentence each:
"GHSA-q4hm-2345-wxyz: high severity, draft: Path traversal in the importer."
Published advisories are listed for everyone; drafts and private reports only
for the repository's administrators and security managers, and anyone else
hears that rather than an empty list. The details say which packages and
versions are affected, which version fixes it, who is credited, and the full
description.

`Ctrl+N` in Advisories asks which you want:

- **Report a vulnerability privately to the maintainers**, for anyone, when
  private reporting is on. QUILL asks for a one-line summary, then what it is,
  how to reproduce it and what it lets an attacker do, then how severe it is,
  with "Not sure" as a choice. Only the maintainers see the report.
- **Draft an advisory**, for maintainers. The same three questions, then the
  affected package and its ecosystem, such as npm or pip, which you can leave
  for later. A draft is private until it is published.

On an advisory's context menu:

- **Publish or Close Advisory...** publishes it, closes it, or makes it a
  draft again. A report someone sent privately reads "private report to
  review"; on it, the same command offers **Accept it**, which makes it a
  draft advisory you and the reporter work on, or **Close it**. Publishing
  makes it public for good, puts it in GitHub's Advisory Database and alerts
  the projects that depend on the package, so QUILL asks you to type its GHSA
  id first.
- **Request CVE...** asks GitHub for a CVE number for a draft. GitHub reviews
  each request, so the number comes later.
- **Advisory Comments**, **Comment on Advisory...** and **Edit an Advisory
  Comment...** are a draft's private discussion, and **Make a Private Fork for
  the Fix** makes the temporary private fork GitHub offers for working on it.

## Secrets

A secret is a value a workflow, Dependabot, a codespace or the Copilot agent
uses but nobody reads again, such as a deploy token. They are lists in the
tree: under a repository's **Settings**, **Actions Secrets**, **Dependabot
Secrets**, **Codespaces Secrets** and **Copilot Agent Secrets**; the same four
under an organization's place; and an environment's **Secrets...** on its
row. **Settings > Organization Secrets Here** lists the organization's secrets
this repository may use. Each row says the secret's name and when it changed:
"Secret DEPLOY_TOKEN, changed 2026-11-02. Its value is never shown."

A secret's value only ever goes one way, to GitHub:

- `Ctrl+N` asks for its name, then its value in a password box. QUILL seals
  the value on this computer with that repository's, environment's or
  organization's own public key (a libsodium sealed box, as GitHub requires)
  and sends only the sealed form. The value is never read back, said, shown,
  logged or kept: once the call ends, it is gone.
- **Change...** on a secret's row sends a new value the same way. For an
  organization's secret you may leave the value empty to keep it, and choose
  which of the organization's repositories may use it: **all**, **private**,
  or **selected**.
- **Repositories Allowed...** on a selected secret checks the repositories
  that may use it now; check or uncheck them, and QUILL adds and removes them
  one at a time, so a change somebody else made meanwhile is kept.
- A repository's Actions secret also has a **Properties** sheet. Its **New
  value** box is a password box that always opens empty; Copy as Text says
  "hidden", the preview before it is sent says "(hidden)", the box is emptied
  once GitHub has it, and Change History records only that it was set.

To set one secret in many repositories at once, use **Secrets by Name** under
Across Repositories (Chapter 12).

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

Select a repository and choose **Repository > Export Software Bill of
Materials...** (`Ctrl+Alt+B`), or the same row in **Repository Actions...**
(`Ctrl+Shift+G`). A Save window offers a name such as `owner-name.spdx.json`.
When it is saved you hear "Saved owner-name.spdx.json: 212 packages, in SPDX
format." The file is JSON (JavaScript Object Notation), so QUILL opens it like
any other text file. **SBOM Report**, on a repository's context menu, reads
the same list in a window instead of saving it.

A repository whose dependency graph is turned off has nothing to export, and
QUILL says where to turn it on: the repository's settings, under Code
security. Nothing is saved in that case.

## A walk-through: your first discussion

This uses the practice repository, which you make with **Help > Practice on
GitHub...** (`Ctrl+Alt+P`). Discussions are off in a new repository, so the
first step turns them on.

1. Select the practice repository in the tree and press `Alt+Enter`. Its
   Properties open. Move to the **Features** page, check **Discussions**, and
   save. You hear that the change was saved.
2. Press `Ctrl+Shift+3`. You arrive in Discussions, and the details say it is
   empty and what would fill it.
3. Press `Ctrl+N`. Choose **General** from the categories. In the New
   Discussion window, type a title in **Title:**, a line in **Body:**, and
   press **Start Discussion**. Answer Yes to the question. You hear "Started
   discussion" with its number and category, and it is in the list.
4. Press Enter on it. The thread window opens on the discussion itself.
   Press `Alt+R`, type a reply, and post it. You hear "Posted your reply".
   Press Escape to close the thread.
5. Press `Shift+F10` and choose **Close Discussion...**, then **Resolved**.
   You hear "Closed the discussion."
6. Press `Ctrl+Shift+8`, then arrow to **Alerts**. A new repository has
   none, or has a kind turned off; either way the list says which, rather
   than claiming there are no alerts.

---

- Previous: [Chapter 7: Code and repositories](lite-github-guide-07-code-and-repositories.html)
- Next: [Chapter 9: Codespaces and the GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html)
- [Contents](lite-github-guide.html)
