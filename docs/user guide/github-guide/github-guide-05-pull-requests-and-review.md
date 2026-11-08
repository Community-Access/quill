# Chapter 5: Pull requests and review

## What this chapter covers

Reviewing a pull request on the website means a long page of code with
comments wedged between the lines. QUILL turns it into an outline you can
walk: the pull request, its changed files, the conversations on each file, and
its checks. This chapter covers reading a pull request, the diff, commenting
on a line or a range, suggesting a change, sending a review, replying and
resolving, asking Copilot for a review, and then everything that gets a pull
request merged.

Reading works signed out. Everything that writes needs a signed-in account.

**In QUILL Lite**, which works as a guest, you can read every part of a
review. The commands that write say they need a signed-in account.

## Opening a pull request

In GitHub Items, select a pull request and press **Review...** (`Alt+R`), or
choose **Open Review...** from its context menu. A pull request link pasted
into **Open Link...** opens straight into its review, and so does a pull
request in your notifications.

**Diff...** (`Alt+D`) skips the outline and opens the changed files on their
own. More on that below.

## The one-sentence summary

The first thing you hear when the review opens is the whole pull request in
one sentence:

"Review loaded for pull request #42. Approved, 2 checks failing, 1 open
thread, 3 commits behind main."

The sentence is built from these, in this order, leaving out what does not
apply:

- whether it is a **draft**;
- the review decision: **Approved**, **Changes requested**,
  **Review required**, or **No review decision**;
- the checks: how many are failing or still running, or "all 4 checks
  passing";
- the open review threads, or "no open threads";
- how far behind its base branch it is, or "up to date with main";
- **merge conflicts**, if there are any;
- **auto-merge on**, if it is set;
- and whether GitHub says it can merge, it is blocked by branch rules, or
  QUILL cannot tell. QUILL never guesses "ready": when it is not sure, it says
  "merge readiness unknown".

A merged or closed pull request just says "Merged." or "Closed without
merging." The same sentence is the first line of the window, **Pull request in
one sentence**, so you can read it again. **Copy Review Summary** (`Alt+S`)
copies the fuller summary.

## The review window

In Tab order:

- The one-sentence summary, then a status line: the merge readiness, the
  review decision, the checks, and how many threads are unresolved or
  outdated.
- **Pull request outline**, the tree. This is where you spend your time.
- **Changed since my last review** (`Alt+L`), a check box. See below.
- The selected node's details, a read-only text field.
- **Review summary**, with **Check Merge Policy** beside it, and the summary
  and merge readiness in full.
- **Checks**, a list of the check runs.
- The status line.
- The buttons: **Next Unresolved** (`Alt+U`), **Next Unvisited** (`Alt+V`),
  **Open on GitHub** (`Alt+G`), **Copy Review Summary** (`Alt+S`),
  **Timeline...** (`Alt+T`), **Compose Review...** (`Alt+C`),
  **Reply to Thread...** (`Alt+R`), **Request Reviewers...** (`Alt+W`),
  **Mark Ready** (`Alt+M`) on a draft or **Convert to Draft** (`Alt+D`)
  otherwise, **Update Branch...** (`Alt+B`), **Auto-Merge and Queue...**
  (`Alt+A`), and **Close**.

The buttons that write are unavailable when you are signed out or the pull
request is closed, and Reply is available only with a thread selected.

### The outline

The tree is a real tree: Up and Down move between the rows you can see, Right
opens a branch and Left closes it. Tab reads the selected row's details, and
Shift+Tab comes back.

- The top row is the pull request: "PR #42:" and its title.
- **Changed files** holds one row per file. Each file opens to the review
  threads on it: "Line 12, alice, 2 replies, unresolved". A thread on a line
  that has since changed adds "outdated".
- **General conversations** holds threads that are not on a file, when there
  are any.
- **Pending line comments, not sent yet** holds comments you have written but
  not sent. See below.
- **Checks** holds one row per check, its result first: "success: build",
  "failure: test", or "in progress: lint" while it runs.

Enter on a row does the natural thing: on a file it opens the file's diff; on
a thread it moves you into its details to read every comment and reply; on a
check it opens the check on GitHub; on anything else it opens or closes the
branch.

Reading or expanding never changes anything. Selecting a thread does not
resolve it or mark it read.

### Moving between threads

- **Next Unresolved** (`Alt+U`) moves to the next thread that is still open,
  and says "Moved to unresolved thread by" the author, and the line. It goes
  round from the end to the start.
- **Next Unvisited** (`Alt+V`) moves to the next thread you have not selected
  in this review. It is how you make sure you have read everything. When you
  have, it says "You have visited every loaded review thread in this
  session."

Neither of these tells GitHub anything. "Visited" lives only in this window.

## Changed since my last review

When someone pushes more commits after you have reviewed, you do not want to
read every file again. Check **Changed since my last review** (`Alt+L`).
QUILL finds the commit you last reviewed and keeps only the files that have
changed since then. The tree's first branch is renamed **Files changed since
your review on** and the date, and you hear how many:

- "3 files changed since your review on 4 November."
- "No files changed since your review on 4 November."
- "You have not reviewed this pull request yet, so every file is new to you."

If the branch has been force-pushed and the commit you reviewed is gone from
GitHub, QUILL says so plainly and shows every file. Uncheck the box to see
every file again.

## The diff

Enter on a file, **Open File Differences** on a file's or thread's context
menu, or **Diff...** in GitHub Items, opens the diff window, **PR #42 diff:**
and the title.

- **Changed files**: one row per file, "modified: src/status.py +12 -3".
  Select one to hear its changes.
- **Differences** reads the changes through the same engine as QUILL's Compare
  Documents: "Difference 2 of 5. Text changed at line 41", with both sides
  named and the changed words described.
- **Selected review hunk** shows the part of the file a thread is about, when
  you came here from a thread.
- **Line marks:** (`Alt+M`) chooses how changed lines are marked in the patch
  list: **Words** ("Added line 12", "Removed line 9", "Unchanged line 13") or
  **Symbols** (plus and minus). Symbols are shorter, but your screen reader
  says them only when it reads punctuation, and QUILL reminds you of that when
  you choose them. Your choice is kept.
- **Patch lines:** (`Alt+P`), the patch one line to a row. This is where you
  comment.
- **Comment on This Line...** (`Alt+L`), **Comment on Lines...** (`Alt+S`),
  **Copy Diff** (`Alt+C`) and **Open Diff in Default App** (`Alt+O`).
- Under them, how many of your line comments are waiting to be sent.

Opened from a thread, the diff goes straight to that thread's lines and says
"Review comment at" the file and line. If the line is no longer in the patch,
it says so and suggests the thread may be outdated.

**Open Diff in Default App** saves the diff as a `.diff` file and opens it in
whatever program your computer uses for those, and tells you where the file
is.

## Commenting on a line or a range

In **Patch lines:**, arrow to a line and press Enter, or press
**Comment on This Line...** (`Alt+L`). To comment on several lines, hold Shift
and arrow to select them, then press Enter or **Comment on Lines...**
(`Alt+S`). With one line or none selected, Comment on Lines asks you to type
the range instead, such as `12-15`, `12 to 15` or just `12`.

GitHub takes a comment only on lines the patch shows, and a range only inside
one block of changes. QUILL checks before it sends and tells you which rule
the lines broke, such as "Line 30 is not in this file's changes, so GitHub
will not take a comment on it."

The comment window is titled with where the comment goes, such as
"Comment on line 12 of src/status.py". It has:

- **Lines you are commenting on:**, read-only, so you can check.
- **Suggest a change** (`Alt+S`), a check box. See below.
- **Comment:** (`Alt+C`), where focus starts.
- **Add to Review** (`Alt+A`), the default: keep the comment and send it with
  your review.
- **Post Now** (`Alt+P`): send it on its own, straight away.
- **Cancel**.

Most of the time you want **Add to Review**. GitHub then sends your comments
together, with your verdict, as one review, and people are notified once
instead of once per comment.

### Suggesting a change

Check **Suggest a change** and QUILL puts the lines you chose into the comment
as a suggestion block, ready for you to edit into what they should say. On
GitHub, the author can accept a suggestion with one button. Uncheck it to take
the block out again. A suggestion replaces lines of the new file, so it works
on added and unchanged lines, not removed ones.

## Pending comments and sending your review

Comments added to your review are kept on this computer, for your account,
until you send them. You hear "Added to your review:" and where, and how many
are waiting. They show in the outline under
**Pending line comments, not sent yet**, each with its place and the start of
its text.

On a pending comment, Enter or **Edit Pending Comment...** changes it, and
**Delete Pending Comment...** removes it after asking. It was never sent, so
it cannot be got back.

### Compose Review

When you are ready, press **Compose Review...** (`Alt+C`). The window
**Review Pull Request #42** says how many line comments go with this review,
and has:

- **Review action:**, a list: **Comment**, **Approve** or
  **Request changes**.
- **Review message:** (`Alt+M`), your overall comment. Request changes needs
  one; so does Comment, unless you have line comments.
- **Discard Saved Draft**, to throw away a saved review message.
- **Submit Review**, which sends it, and **Save Draft and Close**, which keeps
  it. Escape is Save Draft and Close.

The review message saves as you type, so closing the window loses nothing.
Submit Review is the only thing that sends. Request changes asks once more
before it goes. You hear "Review submitted on pull request #42." and how many
line comments GitHub took with it.

### When the pull request moves under you

Comments are written against one version of the code. If new commits arrive
before you send, the lines you commented on may have moved. QUILL will not
send a review whose comments were written on an older version: it says how
many were, and asks you to delete or rewrite them under Pending line comments
first. If the version changes while the Compose window is open, nothing is
sent, and QUILL tells you to reopen the draft against the current diff.

## Replying and resolving

On a thread in the outline:

- `Ctrl+R`, or **Reply to Thread...** (`Alt+R`), replies. Type it in
  **Reply to this review thread:** and press **OK**. You hear "Reply posted to
  the review thread."
- `Ctrl+Shift+R` resolves the thread, or reopens a resolved one. It asks
  first. You hear "Review conversation resolved." If GitHub does not let you
  change it, QUILL says so.

The thread's context menu has these, plus **React to a Comment...**,
**Copy Conversation**, **Copy Thread Link**, **Open File Differences** and
**Open Thread on GitHub**.

`Ctrl+R` replies here, in the review window. In GitHub Items it refreshes.

## Getting a pull request merged

### Reviewers, draft and ready

- **Request Reviewers...** (`Alt+W`) asks for GitHub usernames, separated by
  commas. You hear "Review requested from" and their names.
- On a draft, **Mark Ready** (`Alt+M`) marks it ready for review. On one that
  is ready, **Convert to Draft** (`Alt+D`) turns it back into a draft. Both
  ask first.
- **Update Branch...** (`Alt+B`) merges the base branch into the pull
  request's branch, so it is up to date. It asks first, and is unavailable on
  a draft.

### Asking Copilot for a review

**Request Copilot Review**, on the pull request's context menu (`Shift+F10` on
the outline), asks Copilot code review to review the pull request. It has no
button or access key. You hear "Copilot review requested on pull request #4."
only when GitHub lists Copilot among the reviewers. GitHub sometimes accepts the
request and leaves Copilot off the list, which is how it answers an account or a
repository without Copilot code review; QUILL says that plainly rather than
telling you a request went in when it did not. Copilot's review arrives as
review comments, like anyone else's, and the outline shows them after a refresh.

### Merging

Merging is in GitHub Items, not the review window, because it is the one thing
here that changes the main branch for everyone. Select the pull request and
choose **Merge Pull Request #42...** from **Actions...** or its context menu.
QUILL asks you to type the pull request's number to confirm, not just press
Yes, and says what will happen: that it merges into the base branch and that
this changes the branch for everyone. You hear "Merged #42" and the new commit.
QUILL merges by squashing the pull request's commits into one.

### Auto-merge and the merge queue

**Auto-Merge and Queue...** (`Alt+A`) opens a menu:

- **Enable Auto-Merge...** tells GitHub to merge the pull request by itself as
  soon as its required reviews and checks pass. QUILL asks how: Create a merge
  commit, Squash and merge, or Rebase and merge.
- **Disable Auto-Merge...** turns it off.
- **Add to Merge Queue...** puts the pull request in the branch's merge queue,
  if it has one. You hear its place in the queue.
- **Remove from Merge Queue...** takes it out.
- **Combined Check Status** says all the checks in one sentence, such as
  "3 of 4 checks pass; failing: test."

Each asks first, and reports what GitHub confirmed. When GitHub refuses for a
reason QUILL knows, it says what to do about it, for example that auto-merge
is turned off for the repository and an administrator can turn it on in the
repository's settings, or that GitHub can merge the pull request now, so there
is nothing for auto-merge to wait for.

### Merge policy

**Check Merge Policy** reads the rules on the base branch: required reviews,
required checks, code owners and the merge queue. It adds them to the review
summary, and from then on the readiness and the combined check status count
only the checks that are required ("3 of 4 required checks pass"). The rules
are read for the current version of the pull request; refresh the review after
new commits to check again. GitHub always has the last word, and QUILL says
so.

### A check that needs another run

On a check in the outline, the context menu has **Re-request Check...**,
which asks GitHub to run that check again. Some checks are older-style commit
statuses rather than check runs, and those cannot be re-run from outside;
QUILL says so. Chapter 6 covers checks and workflow runs in full.

## Writing a new pull request

Signed in, **Actions...** in the Issues & PRs view has **New Pull Request...**.
QUILL asks four questions in turn: the title, the description (you can leave
it empty), the branch with your changes, and the branch to merge into, which
starts as `main`.

---

- Previous: [Chapter 4: Issues](github-guide-04-issues.html)
- Next: [Chapter 6: Actions and checks](github-guide-06-actions-and-checks.html)
- [Contents](github-guide.html)
