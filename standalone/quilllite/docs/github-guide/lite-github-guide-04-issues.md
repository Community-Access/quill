# Chapter 4: Issues

## What this chapter covers

Issues are how a project keeps its list of work: bugs, ideas, questions and
tasks. Most days on GitHub start with one. On the website an issue is a long
page of comments, labels in coloured boxes and a sidebar of settings. In the
Workbench it is a row in a list, its details in a pane beside it, and a
Properties sheet with everything you can change.

In this chapter you read an issue and its comments, comment and react, read
its history, write a new issue from a template or a form, label it, put it in
a milestone, assign it, close it with a reason, and break it into sub-issues.
You also change many issues at once, keep issue fields and Projects up to
date, and start work on an issue in a branch and folder of its own.

By the end you will be able to take an issue from filed to closed without
leaving the keyboard. Pull requests are issues too, so most of this works on
them as well; Chapter 5 covers what is theirs alone.

Reading works signed out, on public repositories. Everything that changes an
issue needs a signed-in account, and the access GitHub gives you on that
repository: commenting needs only a sign-in, labels, assignees and milestones
need triage, and locking needs write.

**In QUILL Lite**, everything here works the same, except two commands that
need the editor's own connections: **Summarize Discussion** needs QUILL's AI
connection, and **Start in Local Worktree...** needs QUILL's local Git. In
QUILL Lite both are greyed, and `Shift+F1` says why.

## Finding an issue

A repository's issues are in its **Issues** place in the tree. `Ctrl+Shift+1`
goes there from anywhere in the repository. **Issues and Pull Requests**,
two places further down, lists both together, newest first.

- `Ctrl+G` (**File > Go to Number...**) goes to an issue or pull request in
  this repository by its number.
- `Ctrl+L` (**File > Open GitHub Address...**) takes `owner/name#42`, or a
  link pasted from anywhere, and goes there.
- `Ctrl+E` moves to the filter box. Plain words narrow the list you are
  looking at; GitHub's own words, such as `is:open label:bug`, ask GitHub.
- **View > Open or Closed** chooses open, closed or all, and **View > Quick
  Filters** has the common ones, such as Assigned to Me, No Label and Updated
  This Week. Chapter 13 has filtering, sorting and grouping in full.

## Reading an issue

Arrow to the issue and press **Enter**. Focus moves to the details pane,
which reads like a document:

- the number, whether it is an issue or a pull request, and the title;
- its state, author, when it was opened and last updated, and its link;
- its labels and assignees, when it has any, and how many comments;
- its type and issue fields, when the repository uses them;
- then a line of dashes, and the description.

`Shift+Tab` goes back to the list.

Shortcodes such as `:tada:` are read by their names, "party popper", so you
do not hear colons spelled out.

### Reading the comments

The details pane holds the description, and says how many comments there
are. To read the whole conversation, choose **Read as Document...**
(`Ctrl+Shift+I`). It asks how you want it:

- **Open in Editor** opens the thread as one document, a heading per post
  with its author and date, so your screen reader's heading keys move from
  post to post. You hear "Opened #12 in the editor, 5 posts."
- **Save as Markdown...** or **Save as HTML...** saves it to keep.

### A summary of the discussion

**Summarize Discussion**, on the issue's context menu, asks QUILL's AI to boil
the issue and its comments down to a few sentences: what it is about, where
it stands, the open questions and the next step. The summary goes at the top
of the details pane, with the issue's link under it, and focus moves there.
You hear "Summary ready for #12." It uses the AI connection you chose in
QUILL, and asks the same questions about sending text that every AI feature
asks. With no AI set up, you hear "AI is not set up, so there is no
summary."

## Commenting

Select the issue and choose **Comment...** (`Ctrl+Shift+M`). It is on the
context menu and the **Item** menu too. The comment window opens with the
cursor in **Comment:**. Write in Markdown; Enter starts a new line, and
`Ctrl+Enter` posts.

The buttons under the comment put things at the cursor:

- **Insert Mention...** (`Alt+M`) lists the people in the conversation first,
  then everyone who may be assigned, and inserts `@` and the name. GitHub will
  notify them.
- **Insert Reference...** (`Alt+R`) asks for words in a title, or a number,
  and lists the issues and pull requests that match; it inserts `#` and the
  number.
- **Insert Emoji...** (`Alt+E`) finds an emoji by its name, such as "thumbs up"
  or "party".
- **Insert Saved Reply...** (`Alt+S`) lists the saved replies you keep on
  GitHub, under Settings, Saved replies.
- **Attach Files...** (`Alt+F`) explains why it cannot: GitHub lets no other
  program attach a file. Put the file in a release or a gist and paste its
  link, or attach it on github.com.
- **Preview** (`Alt+P`) reads the comment into the **Preview:** box as GitHub
  will show it, one line each, saying what every line is: "Heading 2: Plan",
  "Not done: Run it", "Quote: ...", a code block and how long it is, and what
  each image and link stands for. Its last lines name who the comment will
  notify and which issues it refers to.

**Check before posting** (`Alt+H`) is checked to begin with. When you post, it
looks for things that trip a reader: an image with no description, a link
that says "click here", a heading that skips a level, a long run of capital
letters, and a comment that is only an emoji. If it finds any, it lists them
and asks whether to post anyway; No takes you back to the comment. Clear the
check box for a comment you know is fine.

**Post** sends the comment, and you hear "Comment posted on #12." Escape sends
nothing. If your account cannot comment, GitHub's refusal is said in words.

To change or delete a comment you already posted on an issue, use the issue's
page on GitHub (`Shift+Enter`). Chapter 5 covers a pull request's review
comments, and Chapter 8 a discussion's.

## Reactions

**React...** on the issue opens its Properties sheet at the **You** page, on
**Your reactions**: a check box for each of GitHub's eight reactions, thumbs
up, thumbs down, laugh, hooray, confused, heart, rocket and eyes, checked when
you have given it. Check or clear one and save.

## The timeline

Comments are only part of an issue's story. Labels are added, people are
assigned, the issue is closed and reopened, and pull requests mention it.
**View Timeline...** on the context menu opens the whole history in one text
box, **History, oldest first:** (`Alt+H`), one event to a line. **Copy All**
(`Alt+A`) copies it. A very long history is read up to five hundred events,
and QUILL says when it stopped early: "Only part of the history was read."

Two more buttons act on the comment whose line the cursor is on, the line
that says "commented":

- **Hide or Show Comment...** (`Alt+C`) folds a comment away for everyone
  without deleting it, as GitHub's own Hide does, for spam, abuse, off topic,
  outdated, a duplicate or resolved. Choose the reason, or **Show it again**
  for one that was hidden. You hear "Hid the comment as off topic." You need
  triage access.
- **Pin or Unpin Comment...** (`Alt+P`) keeps one comment at the top of the
  conversation, such as the answer or the current plan. Choose **Pin it to the
  top** or **Unpin it**. GitHub shows a pinned comment first, for everyone.

## Writing a new issue

Go to a repository's **Issues** or **Issues and Pull Requests**, and press
`Ctrl+N` (**File > New Here...**). The Workbench reads the repository's issue
templates first.

### Templates and issue forms

If the repository has templates, QUILL asks which to start from: **Blank
issue**, then each template with its description.

- **A Markdown template** fills the New Issue window with its title, body,
  labels and assignees, ready for you to change.
- **An issue form**, the kind written in YAML that shows on the website as a
  form with boxes, opens as a real form: one labelled control per field, with
  "(required)" in the name of every field that must be answered. Create Issue
  says what is still missing rather than sending an incomplete issue, and the
  issue GitHub receives reads the same as one filed from the website.

A form or template QUILL cannot fill, such as one too large to load, is left
off the list, and QUILL says so once; it is still there on GitHub. Chapter 12
has more on templates and forms, including building your own.

### The New Issue window

The window has **Title:**, **Body:**, **Labels (comma-separated):** and
**Assignees (GitHub usernames):**. Labels and assignees are optional, and
must already exist in the repository.

What you type is saved on this computer as you go, so closing the window by
mistake loses nothing: the next New Issue in that repository says "Recovered
a local draft", and **Discard Saved Draft** throws it away. A draft is never
sent by itself.

**Create Issue** is the only button that sends anything, and it shows a
preview first: the repository, title, template, labels, assignees and body.
For a long body the preview is shortened and says so; the full body is sent.
Yes sends it, and you hear "Created issue #43." The list loads again with the
new issue in it.

### Many issues at once

When the issues already exist somewhere else, you do not have to type them
one by one:

- **New Issue from Selection...**, in the editor's GitHub menu under From This
  Line, starts one issue quoting the lines you selected, under a link to them.
  See [From the line you are on](lite-github-guide-07-code-and-repositories.html#from-the-line-you-are-on).
- **New Issues from Lines...** (`Ctrl+Alt+L`), on the Workbench's File menu,
  makes one issue from each line you selected, a task list included, and can
  make them sub-issues of an issue you name.
- **Import Issues from a Spreadsheet...** (`Ctrl+Alt+I`), on the same menu,
  makes one issue from each row of a CSV or Excel file, with its labels,
  assignees, milestone and type.

Both of the last two show a preview first, and say which rows GitHub would
refuse and why. See [Bringing issues in](lite-github-guide-12-the-workbench.html#bringing-issues-in).

## Labels, milestones and assignees

**Labels...**, **Assignees...** and **Milestone...**, on the issue's context
menu, open its Properties sheet (`Alt+Enter`) at the **Organize** page, with
focus on that field:

- **Labels** is a list of every label in the repository, each a check box,
  checked when the issue has it. **New Label...** beside it makes one.
- **Assignees** is the same for the people who may be assigned, up to ten.
- **Milestone** is a choice of the repository's milestones, or none. **New
  Milestone...** beside it makes one, and chooses it.

Change what you like and press OK, or `Ctrl+S` to save and keep the sheet
open. QUILL sends only what you changed, reads the issue back, and says what
GitHub kept. `Ctrl+Z` in the list undoes it. Chapter 13 has the sheet in
full.

### Labels

A repository's **Labels** place lists its labels, each with its description.

- **Enter**, or **Find Issues with Label**, lists the issues and pull requests
  with that label.
- **Edit Label...** changes its name, colour or description.
- **Delete Label...**, or the Delete key, deletes it after asking. It comes
  off every issue that had it.

To make a label, use **New Label...** beside Labels on any issue's sheet.

### Milestones

A repository's **Milestones** place lists its milestones. Each reads in
words: "Release 2.0: 62 percent done, 5 open, 8 closed, due 12 December".

- **Enter**, or **Find Issues in Milestone**, lists its issues and pull
  requests.
- `Alt+Enter` opens its sheet, where the title, description and due date
  (typed as year-month-day, such as 2026-12-12) can be changed.
- **Delete Milestone...** deletes it after asking. Its issues and pull
  requests stay, with no milestone. Closing it keeps the milestone and its
  history, and is usually what you want.

**Repository > Repository Actions...** (`Ctrl+Shift+G`) also has
**Milestones...**, a window of its own:

- **Show:** (`Alt+S`) chooses Open, Closed or All.
- **Milestones** (`Alt+M`) is the list, and **Details** (`Alt+D`) the selected
  one in full.
- **New...** (`Alt+N`) and **Edit...** (`Alt+E`) ask for a **Title:**, a
  **Description:**, and a **Due date (year-month-day):**, which you can leave
  empty.
- **Close Milestone...** (`Alt+L`) closes the selected milestone after asking.
  On a closed one it reads **Reopen Milestone...**.
- **Open on GitHub** (`Alt+O`) and **Refresh** (`Alt+R`).

Every change is reported from what GitHub sends back.

### Handing an issue to Copilot

**Assign to Copilot...** (`Ctrl+Shift+A`) hands the issue to Copilot's coding
agent, which works on it in the background and opens a pull request for you
to review.

QUILL first asks GitHub whether Copilot can be assigned in this repository. If
it cannot, you hear why: the coding agent needs a Copilot plan that includes
it, and it has to be turned on for the repository, which an organization owner
may have to allow. Nothing is changed. If it can, QUILL asks before handing
the issue over and names anyone already assigned, who stay assigned. You hear
that it is assigned only when GitHub's answer lists Copilot as an assignee. A
closed issue, or one Copilot already has, gets a sentence saying so instead.

The command is only on issues. To have Copilot look at a pull request, choose
**Ask Copilot to Review** on the pull request (Chapter 5).

## Closing and reopening

**Close or Reopen...** on an open issue asks why, as GitHub does:
**Completed**, **Not planned**, or **Duplicate of another issue...**, which
then asks for the other issue's number. You hear "Closed #7 as completed.",
"Closed #7 as not planned." or "Closed #7 as a duplicate of #3, Original
title." A duplicate is recorded on GitHub against the issue you named.

The Delete key on an issue does the same: it closes, after asking, and never
deletes. On a closed issue the same command reopens it. A pull request keeps
the plain question, because GitHub gives it no reason.

**Not a Duplicate...** takes back "duplicate of" when an issue was closed
against the wrong one. QUILL asks which issue it was marked a duplicate of,
then says "#7 is no longer marked a duplicate of #3, Original title." The
issue stays closed; Close or Reopen... reopens it.

## Changing many issues at once

Select several issues: hold Shift with the arrows to select a run, hold Ctrl
and press Space to add or take away one row, or press `Ctrl+A` for them all.
Then press `Alt+Enter`. One Properties sheet opens for all of them, titled
"Properties of 5 issues". A field that differs says Mixed and is left alone
unless you change it, and a label on some of them reads "bug, on 3 of 5".

You hear a preview first, such as "Change 14 issues: add bug, remove triage.",
then a result for each issue: Done, Skipped because it was already so, or
Failed and why. **Retry Failed** (`F8`) runs the failed ones again.

To say the change in words instead, choose **Tools > Plain-Language Batch...**
(`Ctrl+Shift+S`) and type it, such as "close every issue labelled duplicate
older than 90 days" or "add label triage to every issue with no label". QUILL
finds the issues without any AI, shows them as a checked list for you to
check, and then runs the same preview and results.

Chapter 13 has both in full.

## Housekeeping

These are on the issue's context menu, under **More** when the menu is long:

- **Edit Title...** opens the sheet at the title.
- **Lock or Unlock Conversation...** opens the sheet at the **Conversation**
  page, where **Locked** is a check box. Only people with write access can
  comment on a locked issue. Locking needs write access.
- **Pin or Unpin Issue** pins the issue to the top of the repository's issue
  list, or takes it off. A repository can pin up to three.
- **Transfer Issue...** moves the issue to another repository with the same
  owner. QUILL asks for the repository as `owner/name`, then warns that labels
  and milestones that do not exist there are dropped, and that assignees who
  cannot be assigned there are removed. You hear "Moved #7 to" the repository
  and its new address.
- **Set Issue Type...** chooses the issue's type, such as Bug or Feature, from
  the types the organization has set up. A repository with none says so.
- **Reorder Sub-issues...** opens a list of the issue's sub-issues in order,
  **Sub-issues, in order:**. Select one and press **Move Up** (`Alt+U`) or
  **Move Down** (`Alt+D`). You hear its new place, such as "#12 is now 2 of
  5.", read back from GitHub. Enter opens the selected sub-issue in your
  browser.

## Issue fields

An organization can give every issue extra values of its own, such as
Priority, Points or Due date. On your own account you can make them for your
own repositories, under **People > My Issue Fields**; an organization's are
under its **Issue Fields**. Chapter 12 has both lists.

**Issue Fields...**, on an issue's context menu, lists each field with this
issue's value: "Priority (single choice, field 1): High", or "Due (date,
field 2): not set". A field you may not see, or one of a kind QUILL does not
know yet, says so rather than looking empty.

Choose a field to change it. A single choice offers its choices and **Clear
it**. Any other field with a value asks **Change it...** or **Clear it**
first, so pressing Cancel never clears anything; then QUILL asks for the value
the way its kind needs: a number, a date as year-month-day (2026-12-31), or
text. Only that field is sent, so a value someone else set on another field is
kept. You hear "Points is now 5 on #4."

### Issue types and fields in the lists

Each value keeps its type: a date reads as a date (2026-12-31), a number as a
number (3, or 2.5), a single choice as the choice's name, several choices as
their names, and text as text.

- **Columns.** In an Issues list, **View > Columns...** (`Ctrl+Shift+U`)
  offers **Issue type** and **Issue fields**. Neither shows until you choose
  it, because the fields cost GitHub one request an issue; with Issue fields
  chosen, QUILL reads the first 30 issues of the list. A cell reads
  "Priority: High; Due: 2026-12-31; Notes: empty; Owner: not set". A pull
  request leaves both cells blank, and an issue with no type says "no type".
- **Details.** An issue's details name its type, and once its fields are read,
  each field in full, such as "Field Due (date, field 2): 2026-12-31".
- **Filters.** GitHub's own search answers `type:Bug` and
  `field.priority:high`, so type either in the filter box. **Show Only** and
  **Hide** on an issue offer its type and each field value, which write those
  qualifiers for you. A field whose name has a space is not offered there.
  **View > Group By > Type** groups the list by issue type.

The states never sound alike, so a missing permission never sounds like an
empty field:

| State | In a cell | In details and Properties |
| --- | --- | --- |
| A value | Priority: High | High |
| Set to nothing | Priority: empty | set to nothing |
| Not set | Priority: not set | not set |
| Hidden from you | hidden from you | hidden from you |
| A kind QUILL does not change yet | Odd: shimmer (read only) | shimmer (read only) |
| The read failed | unreadable, and why | could not be read, and why |

## Deleting an issue

Closing an issue keeps it, its comments and its history, and that is almost
always what you want. A repository's admins can also delete an issue for
good, such as one made by mistake or full of spam: choose **Delete
Issue...**. QUILL explains that GitHub cannot bring it back, and asks you to
type the issue's number; anything else deletes nothing. A pull request cannot
be deleted this way.

## Branches and task lists

**Create Branch for This Issue...** makes a branch for the work, from the
default branch, and links it to the issue, so GitHub lists it under the
issue's Development. QUILL suggests a name the way GitHub does, such as
`7-fix-the-parser`; change it if you like. A name git would refuse, or a
branch that already exists, is refused before anything is sent. Afterwards
you hear how to start: `git fetch`, then `git switch` and the name. The
issue's Properties sheet lists its **Linked branches** on the Relationships
page, beside the pull requests that will close it.

**Unlink Branch...** lists the branches linked to the issue and takes the one
you choose off its Development, after asking. The branch itself stays, with
its commits; only the link goes. The **Linked branches** list on the
Relationships page does the same from the sheet: select a branch and press
Remove (or Delete) to unlink it, or Add (or Insert) to make a new one, and
the list changes as soon as GitHub has answered. A Read Only account, or QUILL
in Safe Mode, is told so and nothing is sent.

An issue's task list is the lines of its description that start with a check
box, `- [ ]` or `- [x]`.

- **Check or Uncheck a Task...** lists the tasks, each read as "Done" or "Not
  done" and its words. Enter on one turns it over and saves the description.
- **Convert Tasks to Sub-issues...** makes each task that is not an issue yet
  into an issue of its own, a sub-issue of this one, and changes its line to a
  link to the new issue, checked or not as it was. It names the tasks and asks
  first. GitHub then shows each line as the issue and its state.

Both read the description again just before saving. If somebody changed it on
GitHub while you were choosing, nothing is saved and you are told to try
again, so nobody's edit is lost.

2. Add one empty commit, "Start work on #42", when the branch has no commit of
   its own, because GitHub will not open a pull request with nothing to
   compare.
3. Open a draft pull request whose text begins `Closes #42`, so merging it
   closes the issue. A repository without draft pull requests gets an
   ordinary one, and the sentence afterwards says so.

## Relationships: parents, sub-issues and what blocks what

An issue can be part of a bigger one (its **parent**), have smaller ones
under it (its **sub-issues**), and wait on other issues (it is **blocked
by** them). Choose **Relationships...** on an issue's context menu (or the
Item menu) to see all of it in one list. You first hear a summary, such as
"#41 has a parent, #12, 3 sub-issues, 1 issue blocking it". Each row then
starts with what it is, so the kind comes first:

- "Parent: #12 Spring release (open)"
- "Sub-issue: #44 Write the help (open)"
- "Blocked by: #38 Fix the parser (closed)"
- "Related: #47 The old design (closed)", linked without either waiting on
  the other.
- "Blocking: #50 Publish (open)", an issue that waits on this one.

An issue in another repository is named with it, such as "acme/tools#7".
Enter opens the selected issue in your browser.

- **Add Sub-issue...** (`Alt+S`) asks for the issue to add. Type it as
  `#44`, as `owner/repo#44` for another repository, or paste its address
  from GitHub. If that issue is already a sub-issue of something else,
  QUILL asks before moving it here.
- **Add Blocked By...** (`Alt+B`) records that another issue must be
  finished first.
- **Add Related...** (`Alt+T`) links an issue that belongs with this one,
  such as an earlier attempt, without saying either must wait.
- **Remove** (`Alt+R`) takes away the selected sub-issue, blocked-by or
  related link, after asking. Both issues stay; only the link goes, and you
  can add it again. A parent row and a "Blocking" row are the other end of
  another issue's link, so you change them from that issue.

After each change QUILL reads the relationships back from GitHub and says
what happened, such as "#41 is now blocked by #38." **Reorder Sub-issues...**
changes their order.

## Projects

GitHub Projects are boards that track issues and pull requests across one or
more repositories, with fields of their own such as Status, Priority or
Iteration. `Ctrl+6` goes to **Projects**, the ones your account can see, and
a repository's own are under its **Projects** place (`Ctrl+Shift+7`).

**Projects...** on an issue opens its sheet at the **Projects** page: each
open Project it could be in, a check box, checked when it is. Clearing one
takes the issue out of that Project, with its field values. **New
Project...** beside the list makes one.

A Project's own row has these commands on its context menu:

- **Add Draft Issue...**: a quick note on the board, with a title and an
  optional body, before it is a real issue.
- **New Field...**: a field of your own. Choose Text, Number, Date, or
  Single select; a single select asks for its choices, separated by commas
  ("Small, Medium, Large").
- **Delete Field...**: choose one of the fields you or your team made, and
  confirm. Every item's value in it goes too. Fields GitHub provides, such
  as Title, Assignees and Labels, are not offered.
- **Post Status Update...**: how the project is going (On track, At risk,
  Off track, Complete or Inactive), with a note and an optional target
  date, the way GitHub shows it at the top of the board.
- **Link to Repository...** and **Unlink from Repository...**: a linked
  project shows in that repository's Projects. Type the repository as
  owner/name.
- **Template...**: make the project a template, or stop. GitHub allows
  templates only in an organization, and offers them when someone there
  makes a new project.
- **Copy Project...**: a copy for another user or organization, with a new
  title. Its fields, views and workflows come with it, and its draft
  issues if you say so; its issues and pull requests do not.
- **Delete Project...**: deletes the board for good. Its issues and pull
  requests stay. QUILL asks you to type the project's title, exactly, so a
  slip of the Enter key cannot delete it.

Under **More** are the board's views, fields, drafts, items, status updates,
workflows and sharing, each with a command of its own; Chapter 12 lists them.

**Repository > Repository Actions...** (`Ctrl+Shift+G`) has **Projects...**,
a window for reading and changing a board's items and their fields, with
**Next Unblocked** for the next item nothing is waiting on.

All of these need your GitHub sign-in to include the **project** scope.

## Starting an issue in its own folder

When you start work on an issue, you usually want a new branch, kept apart
from whatever else you have going. **Start in Local Worktree...**
(`Ctrl+Shift+T`) on an issue or pull request does that with Git's worktrees: a
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

**In QUILL Lite**, this command is greyed, because it needs QUILL's local Git.

## A walk-through: one issue, from open to closed

This uses the practice repository. If you do not have it yet, choose **Help >
Practice on GitHub...** (`Ctrl+Alt+P`) in the Workbench; it makes a private
repository called `quill-practice` with three issues to work on.

1. In the Workbench, go to `quill-practice`, then press `Ctrl+Shift+1`. You
   hear "Issues", and the list holds the three practice issues.
2. Arrow to the issue about the greeting's typo and press `Enter`. You are in
   the details pane, reading its description. Press `Shift+Tab` to go back to
   the list.
3. Press `Shift+F10` and choose **Labels...**. The Properties sheet opens on
   the Organize page, at Labels. Check **practice: bug** with Space, and press
   Enter. You hear what GitHub kept.
4. Press `Ctrl+Shift+M`. The comment window opens. Type "I will fix this
   today." and press `Ctrl+Enter`. You hear "Comment posted on" and the
   issue's number.
5. Press `Delete`. QUILL asks why you are closing it. Choose **Completed**.
   You hear "Closed", the number, "as completed."
6. Changed your mind? Arrow to the issue again, which **View > Open or
   Closed > All** shows, and choose **Close or Reopen...**. It asks, then
   reopens it.

That is the whole life of most issues: a label, a word, and closing it.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has these lessons on the
practice repository, each saying what to press and what you should hear:

- **Label, comment on and close an issue**: the walk-through above.
- **Build an issue form**: a form in the repository's Templates.
- **File an issue with a form**: filling the form you built.
- **Plan a milestone**: make one, put an issue in it, and give it a due date.
- **Organize a project board**: a Project with the practice issues on it.

---

- Previous: [Chapter 3: Your inbox and your work](lite-github-guide-03-inbox-and-your-work.html)
- Next: [Chapter 5: Pull requests and review](lite-github-guide-05-pull-requests-and-review.html)
- [Contents](lite-github-guide.html)
