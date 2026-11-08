# Chapter 4: Issues

## What this chapter covers

This chapter is about issues: reading one and its comments, replying,
reacting, reading its history, writing a new one from a template, and keeping
issues in order with labels, milestones, assignees and batch changes, and
handing an issue to Copilot's coding agent. It also
covers the housekeeping commands, Projects boards and dependencies, and
starting work on an issue in a folder of its own. Pull requests are issues
too, so most of this applies to them as well.

## Reading an issue

Load a repository, keep **View:** on **Issues & PRs**, and arrow to the issue.
Press Tab to reach **Details**. It reads like a document:

- the number, whether it is an issue or a PR, and the title;
- its state, author, when it was opened and last updated, and its link;
- its labels and assignees, when it has any, and how many comments;
- then a line of dashes, and the description.

For a pull request, Details also says whether it is a draft, whether it is
merged, its review state, which branch merges into which, and how many lines
and files it changes.

The comments load on their own a moment after you select the issue. You hear
how many, such as "4 comments loaded. Alt+N to jump to the first." They follow
the description in Details, each starting "Comment 1 of 4", then the author
and the date.

### Moving between comments

`Alt+N` moves to the next comment and `Alt+P` to the previous one, from
anywhere in the window. QUILL moves focus into Details, selects the comment
and says "Comment 2 of 4". At either end you hear "Already at first comment."
or "Already at last comment." This is the quickest way through a long
thread: press `Alt+N`, read, press `Alt+N` again.

Reactions on a comment are in words at the end of it, such as "Reactions: 3
thumbs up, 1 heart".

### A summary of the discussion

**Summarize** (`Alt+Z`) asks QUILL's AI to boil the issue and its comments
down to a few sentences: what it is about, where it stands, the open
questions and the next step. The summary goes at the top of Details and is
read out. It uses the AI connection you chose in QUILL and asks the same
questions about sending text that every AI feature asks. If no AI is set up,
it offers to set one up.

**In QUILL Lite**, Summarize says "AI summaries are unavailable here."

## Replying, editing and deleting

You need to be signed in for these.

- **Reply.** Choose **Actions...** (`Alt+A`), then **Reply to Thread...**.
  Type your comment in **Reply:** and press **OK**. You hear "Reply posted".
  GitHub's issue comments are not threaded, so a reply is the next comment in
  the conversation.
- **Edit.** Move to your comment with `Alt+N` first. Then **Actions...** has
  **Edit This Comment...**. Change the text and press **OK**; you hear
  "Comment updated".
- **Delete.** On your comment, **Actions...** has **Delete This Comment...**.
  To confirm, you type the word "delete". You hear "Comment deleted".

GitHub lets you edit and delete only your own comments, unless you look after
the repository. Trying it on someone else's brings back GitHub's refusal. If
you have not moved to a comment yet, QUILL says "Navigate to a comment first
(Alt+N)."

## Reactions

Shift+F10 on the issue has **React...**, which reacts to the issue itself.
After `Alt+N`, it also has **React to This Comment...**. A list of GitHub's
eight reactions opens: thumbs up, thumbs down, laugh, hooray, confused, heart,
rocket and eyes. One you have already given reads, for example, "heart, yours:
choose to remove it", so the same list adds and takes away. You hear "Added
heart." or "Removed heart."

## The timeline

Comments are only part of an issue's story. Labels are added, people are
assigned, the issue is closed and reopened, and pull requests mention it.
Shift+F10 on the issue has **View Timeline...**, which opens the whole
history in one text field, **History, oldest first:** (`Alt+H`), one event to
a line. **Copy All** (`Alt+A`) copies it. When it loads, you hear "Timeline
loaded," and the number of events. A very long history is read up to five
hundred events, and QUILL says when it stopped early: "Only part of the
history was read."

## Writing a new issue

Signed in, choose **Actions...**, then **New Issue...**. With no row selected,
Shift+F10 in the list has it too.

### Templates

If the repository has issue templates, QUILL asks which to start from:
**Blank issue**, then each template with its description. The template's text
fills the form, ready to edit.

Some repositories use GitHub's structured issue forms instead of plain
templates. Those are filled in on GitHub, so QUILL offers to open the form in
your browser: "This structured issue form is completed on GitHub." It does the
same for a template too large to load.

### The form

The **New Issue** window has four fields:

- **Title:** (`Alt+T`), required, up to 256 characters.
- **Body:** (`Alt+B`), the description, in Markdown.
- **Labels (comma-separated):** (`Alt+L`).
- **Assignees (GitHub usernames):** (`Alt+A`).

**Create Issue** sends it, and **Cancel** closes the window.

### Drafts that keep themselves

Everything you type is saved on this computer as you go, a moment after you
stop typing. Nothing is sent. If QUILL closes, or you press Cancel, the next
**New Issue...** in that repository brings it back and says "Recovered a
local draft for" the repository, "It has not been submitted." If you do not
want it, **Discard Saved Draft** throws it away. A draft is deleted when the
issue is created.

Drafts are kept for each account and repository, in your own QUILL data
folder.

### Checking for duplicates

When you press **Create Issue**, QUILL first searches the repository's open
issues for similar titles. If it finds some, a window titled
**Possible Duplicate Issues** lists them and asks whether to create yours
anyway. It is worth reading: the issue you were about to write is often
already there, and a comment on it helps more than a second copy. When the
issue is created, you hear "Created issue" with its number and title.

## Labels, milestones and assignees

### Labels

You can add labels as you write an issue, in the form's **Labels** field. To
add one to issues that already exist, use the Batch menu, below.

To make a new label, open Explore, choose **Repository labels** in **View:**,
and choose **Create Label...** from the context menu. QUILL asks for its name,
a six-digit colour without the `#` sign, and an optional description.

### Milestones

**Milestones...** in GitHub Items (it has no access key; Tab to it, or use any
row's context menu) opens the repository's milestones. Each one reads in
words: "Release 2.0: 62 percent done, 5 open, 8 closed, due 12 December".

- **Show:** (`Alt+S`) chooses Open, Closed or All.
- **Milestones** (`Alt+M`) is the list, and **Details** (`Alt+D`) the selected
  one in full.
- **New...** (`Alt+N`) and **Edit...** (`Alt+E`) ask for a **Title:**, a
  **Description:**, and a **Due date (year-month-day):** such as 2026-12-12,
  which you can leave empty.
- **Close Milestone...** (`Alt+L`) closes the selected milestone after asking.
  On a closed one it reads **Reopen Milestone...**.
- **Open on GitHub** (`Alt+O`) and **Refresh** (`Alt+R`).

Every change is reported from what GitHub sends back.

### Assignees

Add assignees when you write an issue, in the form's **Assignees** field, or to
several at once with the Batch menu.

### Handing an issue to Copilot

Signed in, an issue's context menu in GitHub Items (`Shift+F10` or the
Applications key) has **Assign #3 to Copilot...**, with the issue's number. It
hands the issue to Copilot's coding agent, which works on it in the background
and opens a pull request for you to review.

QUILL first asks GitHub whether Copilot can be assigned in this repository. If
it cannot, you hear why: the coding agent needs a Copilot plan that includes it,
and it has to be turned on for the repository, which an organization owner may
have to allow. Nothing is changed. If it can, QUILL asks before handing the
issue over and names anyone already assigned, who stay assigned. You hear
"Issue #3 assigned to Copilot." only when GitHub's answer lists Copilot as an
assignee. A closed issue, or one Copilot already has, gets a sentence saying so
instead.

The item is only on issues. To have Copilot look at a pull request, use
**Request Copilot Review** in the review window (Chapter 5).

## Changing many issues at once

The list lets you select more than one row. Use the usual Windows keys for a
list: hold Shift with the arrows to select a run, or hold Ctrl and press Space
to add or remove one row at a time. Then press **Batch...** (`Alt+B`):

- **Close** the selected items.
- **Reopen** them.
- **Add label to** them. QUILL asks for the label.
- **Set milestone on** them, from a list of open milestones, or
  "No milestone (clear it)".
- **Add assignees to** them, as GitHub usernames separated by commas.

Each menu row says how many items it will change, such as "Close 3 selected".
The confirmation names every item and says "This changes the items on GitHub
for everyone watching them." When it is done you hear how many GitHub
confirmed, such as "Batch change applied to 3 of 3 item(s).", and the name of
anyone GitHub would not assign.

Batch works in the Issues & PRs view, and needs you to be signed in.

## Housekeeping

Shift+F10 on an issue has a submenu called **Housekeeping for** and its
number. Signed in, it holds:

- **Lock Conversation...**, with a reason: No reason given, Off-topic, Too
  heated, Resolved or Spam. Only collaborators can comment on a locked issue.
  **Unlock Conversation** opens it again.
- **Transfer Issue...** moves the issue to another repository you can write to.
  QUILL asks for the repository as `owner/name`, then warns that labels and
  milestones are not carried across.
- **Pin Issue** and **Unpin Issue**: a repository can pin a few issues to the
  top of its issue list.
- **Set Issue Type...** chooses the issue's type, such as Bug or Feature, from
  the types the organization has set up. A repository with none says so.
- **Reorder Sub-issues...** opens a list of the issue's sub-issues in order,
  **Sub-issues, in order:**. Select one and press **Move Up** (`Alt+U`) or
  **Move Down** (`Alt+D`). You hear its new place, such as "#12 is now 2 of
  5.", read back from GitHub. Enter opens the selected sub-issue in your
  browser.

On a pull request, the submenu holds only Lock and Unlock, because the others
are for issues.

## Projects and dependencies

GitHub Projects are boards that track issues and pull requests across one or
more repositories, with fields of their own such as Status, Priority or
Iteration. **Projects...** (`Alt+J`) in GitHub Items opens the window
**GitHub Projects and Dependencies** for the loaded repository. You need to be
signed in.

- **Load Projects** (`Alt+L`), then choose a board in **Project:** (`Alt+P`).
- **Project items** lists everything on the board. Each row reads the kind,
  the repository and number, the title, its state, and whether it is
  **Ready** or **Blocked**.
- **Selected item and dependencies** shows the selected item's fields, what
  blocks it, and its sub-issues and parent, with the parent's progress.
- **Next Unblocked** (`Alt+N`) moves to the next open item with nothing open
  blocking it. It is the answer to "what can I start now?" You hear
  "Selected unblocked work:" and its title, or "No open issue or pull request
  is currently unblocked."
- **Actions...** (`Alt+A`), and the list's context menu, hold
  **Edit Project Field...**, **Add Blocker...**, **Remove Blocker...**,
  **Add Sub-issue...**, **Remove Sub-issue...**, **Open on GitHub** and
  **Refresh Board**.

Edit Project Field changes text, number, date, single-select, multi-select and
iteration fields. Add Blocker and Add Sub-issue ask for the other issue, as a
GitHub link or as `owner/repo#number`. Every change names its target and what
it will do, and asks first.

## Starting an issue in its own folder

This one is QUILL's alone. When you start work on an issue, you usually want a
new branch, kept apart from whatever else you have going. Shift+F10 on an
issue or pull request has **Start issue #N in Local Worktree...** (or
**Start pull request #N in Local Worktree...**). It uses Git's worktrees: a
second folder for the same repository, on a branch of its own.

1. QUILL uses the Git folder of the document you have open, or asks you to
   choose the local checkout of the repository.
2. It checks that the checkout's remote really is this GitHub repository, and
   stops with **Repository Does Not Match** if it is not.
3. It suggests a branch name, such as `issue-208-fix-the-status-bar`, and tells
   you which local branch it starts from and whether you have uncommitted
   changes. Those stay where they are, in the folder you already have.
4. It asks you to confirm. Nothing is fetched and nothing is sent to GitHub.
5. You choose where the new folder goes. QUILL suggests one beside the
   existing checkout.

**In QUILL Lite**, this command is not on the menu.

---

- Previous: [Chapter 3: Your inbox and your work](github-guide-03-inbox-and-your-work.html)
- Next: [Chapter 5: Pull requests and review](github-guide-05-pull-requests-and-review.html)
- [Contents](github-guide.html)
