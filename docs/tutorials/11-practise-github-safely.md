# Tutorial 11: Practise GitHub safely

**Goal:** get comfortable with GitHub in QUILL or QUILL Lite by working on a
practice project where nothing you do can go wrong. You'll read a real-looking
project, make a copy of your own, and then review, comment, merge and fix a
failing check in it.

This lesson works the same in **QUILL** and **QUILL Lite**. Where the two
differ, both are given. It takes about twenty minutes, plus as long as you
like afterwards.

## What you're practising on

Community Access keeps a practice repository on GitHub,
[Community-Access/quill-github-practice](https://github.com/Community-Access/quill-github-practice).
It holds a tiny Python project called Tally, which counts the words in some
text. The code hardly matters. What matters is everything around it, already
set up for you:

- six issues, with labels, an assignee, a milestone and a closed one;
- a pull request, "Add a line count", with a review that has a line comment
  and a suggested change;
- a draft pull request, "Speed up word counting", whose check fails on
  purpose;
- a release, `v0.1.0`, with a file attached;
- a discussion with replies;
- a security policy, a code of conduct, and issue and pull request templates.

The practice repository is the example everyone reads, so it's locked: you can
read everything in it, but only Community Access can change it. Everything
you do that writes something happens in **your own copy**, which you make in
part 2. Nobody else sees your copy unless you want them to, and you can delete
it when you're done.

## What you need

- A GitHub account. A free one is fine.
- QUILL or QUILL Lite, signed in to that account. If you haven't signed in
  yet: in QUILL, choose **File > Open from Remote > Manage GitHub
  Accounts...**. In QUILL Lite, choose **File > Manage GitHub Accounts...**
  (`Alt+F`, then `H`). The GitHub Guide's chapter 1 explains signing in.
- In QUILL, GitHub Remote Access, which is on in most profiles. If the GitHub
  rows aren't on the File menu, turn it on in **Profiles and Features...**, or
  press `Alt+Shift+P` and choose Developer.
- If you like, **View > GitHub Workbench Mode** (`Alt+V`, then `K`). It puts
  everything this tutorial uses in one **GitHub** menu (`Alt+G`), in both
  apps. The steps below give both routes.

## 1. Read the practice repository

1. Open GitHub Items. In QUILL, choose **File > Open from Remote > GitHub
   Items...**. In QUILL Lite, choose **File > GitHub Workbench...** (`Alt+F`,
   then `G`). In workbench mode, in either app, choose
   **GitHub > Repository Items...** (`Alt+G`, then `T`).
2. In **Repository:**, type `Community-Access/quill-github-practice` and
   press Enter. The issues load.
3. Arrow to "Word count is off by one when text ends with a space" and press
   Enter. Read it from the top. It has one comment, suggesting the fix.
4. Go back to the list and open "Question: what counts as a word?". Press
   `Alt+N` to move from comment to comment, and `Alt+P` to go back.
5. Switch **View:** (`Alt+I`) to the pull requests and open "Add a line
   count". You hear its one-sentence summary first.
6. Open it in the review window. Move through the outline, then from thread
   to thread. One thread has a suggested change: it shows what the reviewer
   thinks `line_count` should say instead.

That's the read-only part. Everything you just did works in any public
repository, signed in or not.

## 2. Make your own copy

The practice repository is a template, which means GitHub can make a fresh
copy of it for you, with its own history.

1. In GitHub Items, press `Alt+E` for **Explore...**.
2. In **Repository:** (`Alt+R`), type `Community-Access/quill-github-practice`
   and load it.
3. Open the context menu (the Applications key, or `Shift+F10`), then the
   **Repository Actions for Community-Access/quill-github-practice** submenu,
   and choose **Create Repository from This Template...**.
4. Name it, say `my-github-practice`. Leave the organization empty so the copy
   goes in your own account. It can be private if you'd rather nobody saw it.
5. Confirm. When it's made, QUILL says so.

If you'd rather use the web: on the practice repository's page, choose **Use
this template**, then **Create a new repository**.

## 3. Fill your copy with practice items

GitHub copies the files, but not the issues or pull requests. Your copy comes
with a workflow called **Set up practice** that makes them.

First, two settings, once. These are on GitHub's website, in your copy's
Settings:

- **Settings > Actions > General > Workflow permissions:** check **Allow
  GitHub Actions to create and approve pull requests**, then choose Save.
- **Settings > General > Features:** check **Discussions**.

Then run the workflow from QUILL:

1. In GitHub Items, load your copy, such as `your-name/my-github-practice`.
2. Set **View:** to **Workflows**.
3. Select **Set up practice** and press Enter, or choose **Run Workflow on
   Branch...** from its context menu. Keep `main` as the branch and confirm.
   You hear "Dispatched".
4. Set **View:** to **Workflow Runs**. After a minute, the Set up practice run
   says "completed" and "success".

Your copy now has the same issues, pull requests, release and discussion as
the practice repository. If you forgot a setting, the run fails instead, and
its summary says which setting to turn on. Turn it on and run it again. It
never makes anything twice, so you can run it whenever you want a fresh start.

## 4. Review and merge a pull request

Everything from here is in your copy.

1. Open the pull request "Add a line count" in the review window.
2. Go to the thread with the suggested change. Reply to it, saying you agree
   with the suggestion, then resolve the thread.
3. Comment on a line of the diff of your own choosing. Your comment waits as
   pending until you send your review.
4. Send your review as a comment.
5. Merge the pull request. The issue "Add a line count to the summary" closes
   by itself, because the pull request said it would.

QUILL doesn't commit a suggested change for you. On GitHub's website, the
suggestion has a **Commit suggestion** button, if you want to try that too.

## 5. Find out why a check failed

1. Set **View:** to **Workflow Runs** and select the failed **Tests** run for
   the branch `practice/speed-up-word-counting`. Set up practice started it
   for you.
2. In your copy, the draft pull request's own check may say it's waiting for
   approval, because a workflow opened the pull request rather than a person.
   You don't need it for this part: the run you just selected tested the same
   code.
3. Press `Ctrl+Shift+W` for **What Failed...**. You hear how many jobs
   failed, then the failed step, and then the lines that matter: the test
   `test_counts_hyphenated_words` expected 3 words and got 4.
4. That's the whole story. The change splits on hyphens, so "screen-reader"
   counts as two words, and the issue "Question: what counts as a word?"
   settled that it should be one.
5. From the run's **Actions...** menu, rerun the failed jobs. They'll fail again, of course, because the code
   hasn't changed. Rerunning is for failures that come from GitHub, not from
   the code.

## 6. Work with issues

1. Add the label `accessibility` to "CONTRIBUTING should explain how to write
   a test".
2. Write a new issue using the **Bug report** template. It doesn't have to be
   a real bug.
3. Put your new issue in the milestone "Practice milestone 1".
4. Close "Typo in the module docstring", then reopen it.
5. React to the first comment on "Question: what counts as a word?".

## 7. Clone your copy

To have your copy's files on your computer, clone it.

1. In QUILL, choose **File > Open from Remote > Clone Repository...**. In
   QUILL Lite, choose **File > Clone Repository...** (`Alt+F`, then `Y`). In
   workbench mode, choose **GitHub > Clone Repository...** (`Alt+G`, then `C`).
2. In **Repository**, type your copy's name, such as
   `your-name/my-github-practice`.
3. In **Into this folder**, keep the folder QUILL suggests, or choose
   **Browse...**.
4. Press **Clone**. You hear "Cloning", then "Cloned" when it's done.
5. When you're offered a file from the new folder, take it, and open
   `PRACTICE.md`.

Your copy can be private: cloning uses the account you signed in with, and
nothing in the new folder keeps your token.

## Where to go next

- The practice repository's `PRACTICE.md` has a set of exercises for every
  chapter of the GitHub Guide, including releases, discussions, codespaces
  and the command line.
- [The GitHub Guide](../user%20guide/github-guide/github-guide.md) explains
  every command used here, and many more. It comes with both QUILL and QUILL
  Lite.
- [Tutorial 8: GitHub inside QUILL and QUILL Lite](08-github-inside-quill.md)
  covers opening and saving files on GitHub, managing repositories and
  resolving merge conflicts.

When you've finished with your copy, you can delete it: in Explore, its
**Repository Actions** submenu has **Delete Repository...**. Or keep it, and
run Set up practice again whenever you want to start over.
