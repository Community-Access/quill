# Tutorial 11: Practise GitHub safely

**Goal:** get comfortable with GitHub in QUILL or QUILL Lite by working on a
practice repository of your own, where nothing you do can go wrong. You'll
make it, look round it, try a change without sending it, then label and close
an issue, review and merge a pull request, and find out why a check failed.

This lesson works the same in **QUILL** and **QUILL Lite**, because both open
the same GitHub Workbench. Where the two differ, both are given. It takes
about twenty minutes, plus as long as you like afterwards.

## What you need

- A GitHub account. A free one is fine.
- QUILL or QUILL Lite, signed in to that account. If you haven't signed in
  yet: in QUILL, choose **File > Open from Remote > Manage GitHub
  Accounts...**. In QUILL Lite, choose **File > Manage GitHub Accounts...**
  (`Alt+F`, then `H`). [Chapter 1 of the GitHub
  Guide](../user%20guide/github-guide/github-guide-01-getting-started.md)
  explains signing in.
- In QUILL, GitHub Remote Access, which is on in most profiles. If the GitHub
  rows aren't on the File menu, press `Alt+Shift+P` and choose a profile that
  has it, such as Developer.

## What you're practising on

**Help > Practice on GitHub...** (`Ctrl+Alt+P`), in the Workbench, makes a
private repository in your own account called `quill-practice`. Nobody else
sees it, and you can delete it when you're done. QUILL fills it with:

- three issues: "Practice: the greeting has a typo", to label, assign and
  close; "Practice: a task list to work through", to check off and turn into
  sub-issues; and "Practice: should we add a changelog?", to answer and close
  as not planned;
- two labels, "practice: bug" and "practice: question";
- a branch, `fix-greeting`, with a pull request to review and merge;
- a workflow, "Practice checks", whose last step fails on purpose, so there
  is a failure to read.

Every lesson in **Help > Tutorials** (`Ctrl+F2` in the Workbench) that changes
something uses this repository. The steps below are the same ground, at your
own pace.

## 1. Make the practice repository

1. Open the GitHub Workbench. In QUILL, choose **File > Open from Remote >
   GitHub Items...**. In QUILL Lite, choose **File > GitHub Workbench...**
   (`Alt+F`, then `G`). You land on Inbox.
2. Press `Ctrl+Alt+P` for **Help > Practice on GitHub...**. QUILL says what it
   will make and asks first. Choose **Yes**.
3. You hear each part as it is made, then the Workbench opens the new
   repository, with you on its place in the tree.

If you have made it before, the same command offers **Open It**, **Delete It
and Start Over...** and **Delete It...**.

## 2. Look round

1. Press `Ctrl+Shift+1` for its Issues, then `F6` to the list. Arrow through
   the three issues.
2. Press `F6` again to read the selected issue in the details, and
   `Shift+F6` to come back.
3. Press `Ctrl+Shift+2` for its Pull Requests. There is one, from the
   `fix-greeting` branch.
4. Press `Ctrl+Shift+4` for its Actions runs. The "Practice checks" run
   failed, on purpose.
5. Press `Alt+1` at any time to hear where you are, and `Shift+F1` on any row
   to hear what you can do with it.

## 3. Try a change without sending it

1. Press `Ctrl+Alt+D` for **Tools > Dry Run**. The status bar's Account cell
   now says "Dry Run: nothing is sent".
2. Go back to Issues (`Ctrl+Shift+1`), select "Practice: the greeting has a
   typo", and press `Delete` to close it. QUILL asks as usual, then stops and
   says what it would have sent. Nothing changed on GitHub.
3. Press `Ctrl+Alt+D` again to turn Dry Run off.

Use Dry Run whenever you want to see what a command would do before you let
it.

## 4. Label, comment on and close an issue

1. In Issues, select "Practice: the greeting has a typo".
2. Press `Alt+Enter` for its Properties sheet. On its Organize page, check
   the label "practice: bug" if it is not already, and assign it to yourself.
   Choose **OK**. You hear what was saved.
3. Press `Ctrl+Shift+M`, write a short comment, and press `Ctrl+Enter` to post
   it.
4. Press `Delete` to close it. Choose "completed" as the reason.
5. Press `Ctrl+Shift+H` for **Account > Change History...**. It lists what you
   just changed, newest first, with before and after, and Undo on each change
   GitHub lets QUILL take back. A comment, once sent, is not one of them.

## 5. Review and merge the pull request

1. Press `Ctrl+Shift+2` for Pull Requests, select the one from `fix-greeting`,
   and press Enter. The review window opens with the pull request in one
   sentence.
2. Arrow to **Changed files**, press Right Arrow, and press Enter on the file.
   The diff opens. Press `Alt+P` for the patch lines and arrow through them;
   added and removed lines each have their own sound.
3. Press Escape to close the diff, and Escape again to close the review.
4. Back in the Workbench, press `Shift+F10` on the pull request and choose
   **Why Can't I Merge?**. You hear whether it can merge, as of the commit it
   names.
5. Press `Ctrl+Shift+Enter`, choose **Squash and merge**, type the pull
   request's number, and press Enter. You hear "Merged" and the new commit.

You made this pull request yourself, so GitHub will not let the same account
approve it. On someone else's, **Compose Review...** (`Alt+C`) in the review
window is where you send Approve. [Chapter 5 of the GitHub
Guide](../user%20guide/github-guide/github-guide-05-pull-requests-and-review.md)
has the rest of reviewing.

## 6. Find out why a check failed

1. Press `Ctrl+Shift+4` for Actions runs and select the failed "Practice
   checks" run.
2. Press `Ctrl+Shift+W` for **What Failed...**. You hear which job failed,
   the step "Fail on purpose", and the last lines of its log, which say it
   fails on purpose.
3. Press Escape, then `Ctrl+Shift+F5` to run only the failed jobs again. It
   will fail again, because nothing in the workflow changed. Running again is
   for failures that come from GitHub, not from the code.

[Chapter 6 of the GitHub
Guide](../user%20guide/github-guide/github-guide-06-actions-and-checks.md)
covers jobs, logs and the rest of a run.

## 7. Clone your practice repository

To have its files on your computer, clone it.

1. In QUILL, choose **File > Open from Remote > Clone Repository...**. In
   QUILL Lite, choose **File > Clone Repository...** (`Alt+F`, then `Y`). In
   workbench mode, choose **GitHub > Clone Repository...** (`Alt+G`, then
   `C`).
2. In **Repository**, type `your-name/quill-practice`.
3. In **Into this folder**, keep the folder QUILL suggests, or choose
   **Browse...**.
4. Press **Clone**. You hear "Cloning", then "Cloned" when it is done.

The repository is private: cloning uses the account you signed in with, and
nothing in the new folder keeps your sign-in.

## Learn it with the guided lessons

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has the same ground as
lessons that tell you, at each step, what to press and what you should hear:

| Lesson | What it covers |
| --- | --- |
| Make a repository to practise on | Making `quill-practice` and looking round |
| Label, comment on and close an issue | Part 4 above |
| Try a command without sending it | Dry Run |
| Review and merge a pull request | Part 5 above |
| Read a failed run | Part 6 above |
| Triage your inbox | Notifications, review requests and marking read |
| Delete the practice repository | Cleaning up |

In QUILL, a lesson notices when you have done each step. In QUILL Lite, Enter
on a lesson walks it in the Workbench, and you move on yourself.

## Where to go next

- [The GitHub Guide](../user%20guide/github-guide/github-guide.md) explains
  every command used here, and many more. It comes with both QUILL and QUILL
  Lite.
- [Tutorial 8: GitHub inside QUILL and QUILL Lite](08-github-inside-quill.md)
  covers opening and saving files on GitHub, repository commands and
  resolving merge conflicts.

When you've finished, **Help > Practice on GitHub...** offers **Delete
It...**, which asks first. GitHub lets QUILL delete a repository only when you
signed in with permission to delete repositories, which Sign In with GitHub
asks for; if it cannot, QUILL says where on GitHub to delete it yourself. Or
keep it, and choose **Delete It and Start Over...** whenever you want a fresh
start.
