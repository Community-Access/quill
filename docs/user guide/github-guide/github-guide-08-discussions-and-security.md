# Chapter 8: Discussions and security

## What this chapter covers

Two kinds of conversation that are not issues. Discussions are a repository's
forum: questions, ideas and announcements, with threaded replies, answers and
polls. Security alerts are GitHub telling a repository about a vulnerable
package, a weakness in the code, or a secret committed by mistake. This
chapter covers reading and taking part in both.

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
itself when the first row is selected. The prompt says which: "Your reply to
bob's comment:". You hear "Posted your reply". A closed discussion takes no
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

### Reopening an alert

Dismissed and fixed alerts have their own view, **Dismissed and resolved
security alerts**. There, **Reopen Alert...** on the context menu asks first,
then reopens the alert.

---

- Previous: [Chapter 7: Code and repositories](github-guide-07-code-and-repositories.html)
- Next: [Chapter 9: Codespaces and the GitHub CLI](github-guide-09-codespaces-and-the-cli.html)
- [Contents](github-guide.html)
