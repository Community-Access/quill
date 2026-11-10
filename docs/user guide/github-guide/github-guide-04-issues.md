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

## Commenting

You need to be signed in to comment. Select an issue and choose **Comment...**
from its context menu or the **Item** menu. Type the comment and press OK to
post it. Nothing is sent until you accept the comment window. GitHub's
permission response is shown in words if your account cannot comment.

The current Workbench posts new issue comments. Editing or deleting an
existing comment is not in its current issue actions; use GitHub.com for those
changes. For pull-request review comments, see Chapter 5.

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

Open a repository's **Issues** or **Issues and Pull Requests** node. Choose
**Item > New Here...** (Ctrl+N). The Workbench reads the repository's issue
templates before it opens the entry fields.

### Templates

If the repository has readable Markdown issue templates, QUILL asks which to
start from: **Blank issue**, then each fillable template with its description.
The template's title and body fill the entry fields, and its labels and
assignees are carried into the issue.

GitHub's structured YAML issue forms and Markdown templates too large for
QUILL to load are not fillable in the Workbench yet. QUILL identifies those
templates and lets you start with a blank issue or a readable Markdown
template.

### Title, body and preview

QUILL asks for the title and body in turn. A template can supply either as a
starting value, which you can edit. A blank issue starts with neither.

Before it sends anything, QUILL shows a preview with the repository, title,
template, labels, assignees and body. For a long body the preview shortens
what it displays and says so; the full body is sent if you confirm.

Choose **Create Issue** to send it or cancel to leave the repository
unchanged. When GitHub confirms it, the Workbench says the new issue number
and refreshes the list.

## Labels, milestones and assignees

### Labels

Labels from a Markdown template are included when the issue is created. A
blank issue starts without labels. After creation, select the issue and use
**Labels...** or **Assignees...** from its context menu to change them.

To manage labels, open the repository's **Labels** node. Select a label to
edit or delete it. To create a label while editing an issue, open the issue's
**Properties**, go to **Labels**, and choose **New Label...**.

### Milestones

Open the repository's **Milestones** node. Each one reads in words: "Release
2.0: 62 percent done, 5 open, 8 closed, due 12 December".

To create a milestone while editing an issue, open its **Properties**, go to
**Milestone**, and choose **New Milestone...**.

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

Markdown templates may provide assignees for a new issue. To change them,
select an issue and choose **Assignees...** from its context menu.

### Handing an issue to Copilot

Signed in, an issue's context menu in the Workbench (`Shift+F10` or the
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
Iteration. Open the Workbench's **Projects** place or **Repository >
Projects** node to see the projects available to your account. Select a
project and choose **Open on GitHub** to visit its board. Editing project
fields, blockers and sub-issues from the Workbench remains on the
implementation backlog.

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
