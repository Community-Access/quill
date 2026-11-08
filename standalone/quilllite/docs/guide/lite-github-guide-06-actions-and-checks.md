# Chapter 6: Actions and checks

## What this chapter covers

GitHub Actions runs a repository's builds and tests. When a run fails, the
website gives you a page of collapsed boxes and a log thousands of lines long.
This chapter shows you how to get from "the build failed" to the line that
broke it in a few keys: the run list, What Failed, jobs and logs, and the
commands that rerun, cancel, delete and approve runs. It also covers combined
check status, deployments waiting for approval, artifacts, caches, and the
names of a repository's secrets.

Reading runs and logs works signed out for a public repository. Anything that
changes a run needs a signed-in account.

## Workflows and workflow runs

GitHub Items has two views for Actions, both in **View:** (`Alt+I`):

- **Workflows** lists the repository's workflow definitions: name, whether it
  is active, and its file.
- **Workflow Runs** lists recent runs, newest first. Each row reads the
  workflow's name, its status ("completed", "in_progress", "queued"), its
  result ("success", "failure", "cancelled"), the branch, what started it
  ("push", "pull_request", "schedule") and the run number. These are GitHub's
  own words, as GitHub sends them.

Details on a run gives the same in full, one line each, with when it started
and its link.

### Running a workflow by hand

Some workflows are set up to be started by hand. Select one in **Workflows**
and press Enter, or choose **Run Workflow on Branch...** from its context
menu. QUILL asks which branch or tag to run it on, starting with `main`, then
confirms: "Run workflow" and its name, "on" the branch, "in" the repository.
You hear "Dispatched" and the workflow and branch.

QUILL asks only for the branch. A workflow that needs other inputs before it
can start has to be run from GitHub's own page.

In QUILL, **Tools > Git and GitHub > GitHub > Dispatch Workflow...** does the
same without opening GitHub Items.

## What Failed

This is the command to learn first. Select a failed run in **Workflow Runs**
and press `Ctrl+Shift+W`, or choose **What Failed...** from **Actions...** or
the context menu. `Ctrl+Shift+W` works only in that view; elsewhere in QUILL
it is another command.

A window titled **What Failed:** and the run opens. While it loads you hear
"Loading what failed...". When it is ready, focus lands at the top of a
read-only text field, **What failed** (`Alt+W`), and QUILL says "What failed
is ready." and the first line of the summary.

The text is one digest of everything you would otherwise dig for:

- How many jobs failed, such as "2 of 7 jobs failed."
- For each failed job, "Job 1 of 2:" with its name and result, then its failed
  steps by number and name.
- The job's annotations: the errors and warnings the tools reported, each with
  its file and line, such as "src/status.py:41: error: name is not defined".
- The last 40 meaningful lines of each failed step's log.

The log lines are cleaned up for listening. Timestamps and colour codes are
taken out, and GitHub's markers become words: "ERROR:", "WARNING:", "NOTE:",
"Command:". QUILL finds each failed step's lines by the times GitHub recorded
for that step. If GitHub gave no times, the digest says so and uses the end of
the job's log instead.

Up to ten failed jobs are shown; a run with more says how many are left and
suggests opening the run on GitHub.

**Copy All** (`Alt+C`) copies the whole digest, ready to paste into a comment
or a message. **Refresh** (`Alt+R`) reads it again, for a run that is still
going. Escape closes the window.

## Jobs and logs

For the whole picture, choose **View Jobs and Logs...** on a run. The window
**Jobs for** and the run has, in Tab order:

- **Attempt:** (`Alt+A`). A rerun makes a new attempt, and the earlier ones are
  kept. The current one is marked "(current)"; up to the latest 20 are
  offered.
- **Workflow jobs**, one row per job: its result, then its name, such as
  "failure: test (windows)".
- **Job details and log**, a read-only text field: the job's status and
  result, when it started and finished, the attempt, the commit, and every
  step with its result. After you load the log, the log is here too.
- The status line, then the buttons:
  - **Load Log** (`Alt+L`) loads the selected job's log as plain text. Enter
    on a job does the same. Focus moves to the details when it arrives.
  - **Load Annotations** (`Alt+N`) loads the errors and warnings the job's
    tools reported. If GitHub refuses, QUILL says so, rather than suggesting
    there were none.
  - **Open Job on GitHub** (`Alt+J`) and **Open Run on GitHub** (`Alt+R`).
  - **What Failed...** (`Alt+F`), the digest above, for the attempt you
    chose.
  - **Re-request Check** (`Alt+C`), see below.
  - **Close**. Escape closes too.

A log over 4 MB is cut off there, with a line saying so and suggesting the job
page on GitHub. Annotations stop at 100, also with a line saying so.

## Doing something about a run

On a run in **Workflow Runs**, **Actions...** and the context menu hold the
commands that act on it. Each one asks first, and the default answer is No.
Answering No to most of them says "Cancelled; nothing was sent to GitHub."

- **Re-run Workflow** reruns every job in the run.
- **Re-run Failed Jobs Only** reruns just the jobs that failed, which is
  usually what you want after fixing a flaky test. You hear "GitHub started a
  re-run of the failed jobs of" and the run. On a run where nothing failed,
  GitHub refuses, and QUILL passes on its reason.
- **Cancel Run...** stops a run that is still going. GitHub only promises to
  stop it, so QUILL says "GitHub accepted the cancel request and is stopping"
  the run, "Refresh to check."
- **Delete Run...** deletes the run for good. The confirmation names the run,
  its branch and its result, and says its logs and artifacts go with it and
  that this cannot be undone.
- **Approve Run from a Fork...** lets a run from someone else's fork go ahead.
  GitHub holds these until a maintainer approves them, because the code in
  them has not been reviewed. The confirmation says so: approve only code you
  have read, since it runs with this repository's permissions.
- **Review Pending Deployments...**, below.
- **Combined Check Status**, below.

## Combined check status

**Combined Check Status** reads every check on the run's commit and says them
in one sentence: "Commit 1a2b3c4: 3 of 4 checks pass; failing: test." If some
are still going it adds how many, and it names any that have not reported
yet. It reads only, so it works signed out.

The review window has the same command (Chapter 5). There, after
**Check Merge Policy**, it counts only the checks the branch requires.

## Re-requesting a check

A check that failed for reasons outside the code, a network blip, say, can be
asked to run again on its own. In **Jobs and Logs**, select the job and press
**Re-request Check** (`Alt+C`). QUILL asks first, then says "GitHub queued the
check for" and the job "to run again." The review window's Checks branch has
**Re-request Check...** on each check's context menu too.

## Deployments waiting for approval

A workflow can stop before deploying to an environment, such as production,
until someone approves. **Review Pending Deployments...** on the run opens the
window **Pending Deployments:** and the run.

- **Environments waiting for review** (`Alt+E`): one check box per
  environment, saying whether you can approve it, who the reviewers are, and
  any wait timer. The ones you are allowed to approve start checked.
- **Comment (GitHub requires one)** (`Alt+C`).
- **Approve** (`Alt+A`) and **Reject** (`Alt+R`), then **Close**.

Write a comment, check the environments, and press Approve or Reject. QUILL
asks once more, naming the environments, and then says which ones GitHub
approved or rejected. If nothing is waiting, the window says "This run is not
waiting on any deployment review."

## Artifacts

A run can leave files behind: a built installer, a test report. On a run,
choose **View Artifacts...**. The window lists them with their size and
whether they are still available; GitHub deletes them after a while, and an
expired one cannot be downloaded.

- **Download Selected...** (`Alt+S`) and **Download All...** (`Alt+A`) ask for
  a folder, then save each artifact as a `.zip` file. If a file of that name is
  already there, QUILL asks before replacing it. A progress window with a
  **Cancel** button follows the download.
- **Refresh** (`Alt+R`), for a run still making artifacts.
- **Open Run in Browser** (`Alt+B`) and **Close**.

GitHub hands each download to a short-lived address on another server. QUILL
fetches that without your token, so the token is only ever sent to GitHub.

## Caches

Workflows keep caches to run faster: downloaded packages, build outputs. They
are listed in Explore. Choose **Actions caches** in **View:**, with the
repository in **Repository:**. The first row sums them up, such as "12 Actions
caches in community-access/quill" and their total size. Each row after it
reads the cache's key, size, branch and when it was last used, newest first.

A stale or broken cache can make a build fail in strange ways. On a cache's
row, **Delete Cache...** removes it after asking. Workflows build it again the
next time they need it.

## Secret and variable names

**Secret and variable names**, also in Explore, lists the names of the
repository's secrets and variables, and those of each environment, with when
each was last updated: "Repository secret: DEPLOY_KEY, updated 2026-10-02". It
answers "is that secret set?" without anyone needing to see it.

The names are all you get. QUILL never reads a secret's or variable's value,
and it drops any value GitHub sends before it reaches the screen.

Both of these views need a signed-in account with access to the repository's
settings.

---

- Previous: [Chapter 5: Pull requests and review](lite-github-guide-05-pull-requests-and-review.html)
- Next: [Chapter 7: Code and repositories](lite-github-guide-07-code-and-repositories.html)
- [Contents](lite-github-guide.html)
