# Chapter 5: Pull requests and review

## What this chapter covers

Reviewing a pull request on the website means a long page of code with
comments wedged between the lines. QUILL turns it into an outline you can
walk: the pull request, its changed files, the conversations on each file, and
its checks. This chapter covers reading a pull request, the diff, commenting
on a line or a range, suggesting a change, sending a review, replying and
resolving, asking Copilot for a review, everything that gets a pull request
merged, and the whole patch, a revert and conflicts.

Reading works signed out. Everything that writes needs a signed-in account.

**In QUILL Lite**, a guest can read every part of a review, and the commands
that write say they need a signed-in account. Sign in with **File > Manage
GitHub Accounts...** (`Alt+F`, then `H`) and they work as they do in QUILL.

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

## Files you have viewed

GitHub remembers, for you alone, which of a pull request's files you have
viewed, so a long review can be done in sittings. Signed in, the review
window reads that after the review loads, and each row under **Changed files**
ends with its state: "src/status.py, viewed", "src/status.py, not viewed", or
"src/status.py, changed since you viewed it" when someone pushed to it after
you looked. The status line says how many you have viewed, such as "3 of 12
files viewed."

Shift+F10 on a file has:

- **Mark as Viewed**, or **Mark as Not Viewed** on one you have viewed. It is
  the same mark GitHub's Files tab shows, and you hear the new count.
- **Show Only Files Not Viewed** hides the files you have viewed, so the
  outline holds only what is left; **Show All Files** brings them back. You
  hear how many are left.
- **Comment on This File...** opens the comment window for a comment on the
  whole file rather than a line: for a file that should not be there, or one
  to rename. It posts at once, outside any review you have pending.

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
- **Changed Lines Only** (`Alt+H`), beside it, leaves the unchanged lines
  around each change out of the patch list, so the arrows go from change to
  change. The hunk headings stay, so each change still says where it is. You
  hear how many changed lines there are and how many unchanged ones were left
  out; uncheck it to see them again.
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

As you arrow through the patch lines, an added line and a removed line each
have a short sound of their own, so you can hear the shape of a change before
the words arrive. They are the sounds **Arrived on an added line of a diff**
and **Arrived on a removed line of a diff** in the Sound Scheme window, where
either can be previewed, changed or switched off, and they follow your sound
setting like every other QUILL Lite sound. Unchanged lines and headings are silent.

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

Merging is in the Workbench, not the review window, because it is the one
thing here that changes the base branch for everyone. Select the pull request
and press `Ctrl+Shift+Enter`, or choose **Merge...** from its context menu.

QUILL Lite first asks GitHub whether the pull request can merge. If it cannot, you
hear why, the same answer as **Why Can't I Merge?** below, and nothing else
happens. If it can, QUILL Lite asks how to merge: Squash and merge, Merge commit,
or Rebase. Then it asks you to type the pull request's number to confirm, not
just press Yes, and says what will happen: that it merges into the base
branch, as of the commit QUILL Lite checked, for example "as of commit 3f9a2c1",
and that this changes the branch for everyone. You hear "Merged #42" and the
start of the new commit.

That commit is the one that merges. If somebody pushes to the pull request
between the check and your typing the number, GitHub refuses, nothing is
merged, and QUILL Lite says so: "Somebody pushed to #42 after commit 3f9a2c1 was
checked, so nothing was merged." Check again and you are merging what you
have actually read.

### Why Can't I Merge?

**Why Can't I Merge?** on a pull request's context menu in the Workbench
answers the question GitHub's merge box answers with colours and icons. You
hear either that it can merge, "#42 can merge into main, as of commit
3f9a2c1.", or each reason it cannot, each with what to do:

- It is a draft: mark it ready for review first.
- It conflicts with its base: in QUILL, **Resolve Conflicts in a
  Worktree...** takes the conflicts to your computer.
- It is behind its base, and the branch's rules want it up to date: update
  the branch.
- A reviewer requested changes, or it needs an approving review.
- A required check failed, or has not finished, named: "Required checks test
  and lint failed. Re-run or fix it." A check that failed but is not
  required is mentioned as not required, and does not stop the merge.
- A rule on the base branch blocks it for another reason: **Check Merge
  Policy** in the review window names the rules.

It also says when auto-merge is on, and its place when the pull request is
in the merge queue. The answer is always for one commit, which it names, so
you know a push after you asked may change it.

### Auto-merge and the merge queue

On a pull request's row in the Workbench, **Auto-Merge...** turns auto-merge
on, after telling you what it would be waiting for and asking how to merge,
or offers to turn it off when it is on. A pull request that can merge now has
nothing to wait for, and QUILL Lite says so rather than switching it on. **Add to
or Remove from Merge Queue...** adds the pull request to its branch's queue,
naming the commit, or offers to take it out when it is in, saying its place.
The repository's **Merge Queue** node lists the whole queue in order.

In the review window, **Auto-Merge and Queue...** (`Alt+A`) opens a menu:

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

## The whole patch, a revert, and conflicts

Three commands on a pull request's row in the GitHub Workbench do what the
web's Files tab, its Revert button and its conflict editor do.

### Open Patch in Editor

**Open Patch in Editor** opens the pull request's whole change as one
document: every changed file, one after another, as a unified diff, the same
text the website's `.diff` link gives and the text `git apply` reads. Each
file starts with a line beginning `diff --git`, so the editor's Find moves
from file to file, and each change starts with a line beginning `@@`, which
names the lines it touches. A removed line starts with a minus sign and an
added line with a plus sign.

A file GitHub sends no text change for, such as an image or a very large file,
is not left out silently: it has a line of its own starting with `#`, which
names the file and says so. When the patch opens you hear how many files it
has and how many of them have no text, for example "Opened the patch of #42.
The patch has 12 files. 1 of them has no text change GitHub can send, binary
or too large, and each is named on a line starting with #."

The patch is saved as `<repository>-pr-<number>.diff` in the folder where the
Workbench keeps the documents it opens, so Save As keeps a copy anywhere you
like.

### Revert Pull Request

On a merged pull request, **Revert Pull Request...** opens a new pull request
that undoes it, as the Revert button on the website does. QUILL asks for the
new pull request's title, which starts as `Revert "` and the old title, and
then asks whether to open it as a draft. Yes opens a draft, which nobody can
merge until it is marked ready; No opens it ready for review. Nothing is
undone until the revert is itself merged, so this is a proposal, not a
change to the branch.

You hear "Opened pull request #57, which reverts #42." A pull request that
is not merged has nothing to revert; the command is greyed, and its help says
why. You need write access to the repository.

### Conflicts

QUILL Lite has no local Git, so it does not resolve conflicts on your
computer. **Resolve Conflicts in a Worktree...** is in QUILL, where it fetches
the pull request into a folder of its own, merges its base there and walks
each conflicted file; in QUILL Lite the row is greyed and says so.

## Writing a new pull request

In a repository's **Pull Requests**, press `Ctrl+N`. To start from a branch,
select it in Branches, press `Ctrl+Shift+N` and choose Pull Request. The New
Pull Request window has Merge into, Merge from, Title, Description and a
Create as a draft check box. The title and description start from the
commits you are proposing, a branch that already has an open pull request is
taken to that one instead of making a second, and Cancel keeps your text for
the session. [Chapter 12](lite-github-guide-12-the-workbench.html) walks through it.

---

- Previous: [Chapter 4: Issues](lite-github-guide-04-issues.html)
- Next: [Chapter 6: Actions and checks](lite-github-guide-06-actions-and-checks.html)
- [Contents](lite-github-guide.html)
