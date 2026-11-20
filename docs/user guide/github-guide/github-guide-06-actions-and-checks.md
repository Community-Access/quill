# Chapter 6: Actions and checks

## What this chapter covers

GitHub Actions runs a repository's builds and tests. When a run fails, the
website gives you a page of collapsed boxes and a log thousands of lines long.
You want the line that broke, and you want it quickly.

In this chapter you find a repository's runs, get from "the build failed" to
the failing step in one key, read jobs and logs, and rerun, cancel, delete and
approve runs. Then you start, turn on and off, and edit workflows, approve
deployments that are waiting, and look after artifacts, caches, runners and
the names of a repository's secrets.

By the end you will know how to find out why any run failed, and how to do
something about it, without opening a browser.

Reading runs and logs works signed out for a public repository. Anything that
changes a run needs a signed-in account, and a Workbench level that allows
it: Organize for rerunning, cancelling and starting runs, and Full for
approving deployments and fork runs and for deleting. Chapter 13 explains the
levels.

## Finding a repository's runs

Every repository in the GitHub Workbench's tree has an **Actions** place.
`Ctrl+Shift+4` goes straight to its **Runs**. Under Actions are:

- **Runs**: each time a workflow ran, newest first. A row reads the
  workflow's name, its status ("completed", "in_progress", "queued"), its
  result ("success", "failure", "cancelled"), the branch, what started it
  ("push", "pull_request", "schedule") and the run number. These are GitHub's
  own words, as GitHub sends them. The details pane gives the same in full,
  one line each, with when it started and its link.
- **Workflows**: the repository's workflow definitions, with whether each is
  active, and its file. Enter on a workflow lists its runs.
- **Artifacts**: files the runs kept, such as builds and test reports.
- **Caches**: files Actions kept between runs.
- **Runners**: the repository's own machines, for its administrators.

**Across Repositories > Workflow Runs** (`Ctrl+0`) lists the runs of every
repository in your set in one list, newest first, for "which runs failed
anywhere?". Chapter 12 has Across Repositories.

## What Failed

This is the command to learn first. Select a failed run in **Runs** and press
`Ctrl+Shift+W`, or choose **What Failed...** from its context menu or the
Item menu.

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

For the whole picture, press Enter on a run, or choose **Jobs and Logs** from
its context menu. The window **Jobs for** and the run has, in Tab order:

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
  - **Follow This Job** (`Alt+W`), see below.
  - **Close**. Escape closes too.

A log over 4 MB is cut off there, with a line saying so and suggesting the job
page on GitHub. Annotations stop at 100, also with a line saying so.

On a run's context menu, under More, three more read the logs another way:
**Read a Step's Log...** reads one step at a time, **Download Logs...** saves
every log of the run as a zip file, and **Earlier Attempts...** says how an
earlier attempt went, or reads its logs.

### Following a job while it runs

GitHub shows a running job's log only on its own web page; the log QUILL can
load arrives when the job has finished. What QUILL can follow while it runs is
its steps. Select a running job and check **Follow This Job** (`Alt+W`): you
hear where it is, for example "build: On step 3 of 9, Run tests; 2 done", and
from then on, every few seconds, each step as it starts and as it finishes,
"Step 3, Run tests, failed.", without your having to look. When the job ends
you hear how, "build failed. Load Log reads its whole log.", and following
stops by itself. Uncheck the box to stop sooner.

At any moment in this window, `Alt+8` says how far along the selected job is:
the step it is on, how many are done, and any that have failed so far.

To hear when a whole run finishes without keeping a window open, add a watch
under **Watches** (`Ctrl+7`). Chapter 12 has Watches.

## Doing something about a run

On a run in **Runs**, the context menu and the Item menu hold the commands
that act on it. Each one asks first, and the default answer is No.

- **Re-run Failed Jobs Only** (`Ctrl+Shift+F5`) reruns just the jobs that
  failed, which is usually what you want after fixing a flaky test. You hear
  "GitHub started a re-run of the failed jobs of" and the run. Pressing it
  twice never starts two reruns. On a run where nothing failed, GitHub
  refuses, and QUILL passes on its reason.
- **Re-run Workflow** reruns every job in the run. You hear "Re-running" and
  the workflow.
- **Re-run One Job...** reruns a single job, with debug logs if you ask for
  them.
- **Cancel Run...** stops a run that is still going. GitHub only promises to
  stop it, so QUILL says "GitHub accepted the cancel request and is stopping"
  the run. Refresh (`F5`) to check. **Force Cancel...**, under More, is for a
  run that Cancel has not stopped.
- **Delete Run...** deletes the run for good. The question names the run,
  its branch and its result, and says its logs and artifacts go with it and
  that this cannot be undone. **Delete Logs...** deletes only its logs; the
  run stays.
- **Approve Run from a Fork...** lets a run from someone else's fork go ahead.
  GitHub holds these until a maintainer approves them, because the code in
  them has not been reviewed. The question says so: approve only code you
  have read, since it runs with this repository's permissions. You hear
  "GitHub approved" the run, and that it will start shortly.
- **Review Pending Deployments...** and **Approvals**, below.
- **Combined Check Status**, below.

## Combined check status

**Combined Check Status** reads every check on the run's commit and says them
in one sentence: "Commit 1a2b3c4: 3 of 4 checks pass; failing: test." If some
are still going it adds how many, and it names any that have not reported
yet. It reads only, so it works signed out.

The review window has the same command (Chapter 5). There, after
**Check Merge Policy**, it counts only the checks the branch requires.

A commit's own row, under Code, has two more: **Check Run Details...**, a
check's summary and every annotation, and **Re-run a Check Suite...**.

## Re-requesting a check

A check that failed for reasons outside the code, a network blip, say, can be
asked to run again on its own. In **Jobs and Logs**, select the job and press
**Re-request Check** (`Alt+C`). QUILL asks first, then says "GitHub queued the
check for" and the job "to run again." The review window's Checks branch has
**Re-request Check...** on each check's context menu too.

## Starting a workflow

### Running a workflow by hand

Some workflows are set up to be started by hand. Choose **Run Workflow on
Branch...** (`Ctrl+Shift+R`) from the Repository menu, or from a workflow's
context menu in **Workflows**. QUILL asks three things: the repository, as
`owner/name`, filled in with the repository of the document you are editing;
the workflow's file name, such as `ci.yml`; and the branch or tag, starting
with `main`. Then it asks "Dispatch" the workflow "on" the branch "in" the
repository, and the editor's status bar says "Dispatched" and the workflow
and branch.

It does not yet take the workflow or the repository from the row you
selected, so type them as the workflow's file name says. QUILL asks only for
the branch, not for a workflow's other inputs; a workflow that needs those
before it can start has to be run from GitHub's own page.

**Run Workflow on Branch...** is the editor's **Dispatch Workflow...**, which
is also in the Workbench's **Repository Actions...** (`Ctrl+Shift+G`), and in
QUILL's **Tools > Git and GitHub > GitHub** submenu. **In QUILL Lite**, which has no
such command, the row is greyed and says the editor that opened the window
does not have it.

### Starting workflows from outside

A workflow can start on `repository_dispatch`, an event sent on purpose rather
than by a push. **Send Repository Dispatch...**, on a repository's context
menu, sends one: give the event's name, as the workflow's `types` list says,
such as `deploy`, and optionally extra values as JSON, such as
`{"env": "test"}`, which the workflow reads as `github.event.client_payload`.
You hear "Sent deploy." and the run appears under Actions.

## Looking after workflows

### Turning a workflow on or off

A workflow that is turned off runs on nothing: not on a push, not on a
schedule, not even Run Workflow. GitHub turns off a scheduled workflow by
itself after sixty days without activity in the repository, which is a common
reason a nightly job quietly stopped. **Turn Workflow On or Off...** on a
workflow's context menu says its state in words first, "on", "turned off" or
"turned off by GitHub after 60 days without activity", and asks before
changing it. You hear "Turned on" and its name, or "Turned off". The
workflow's Properties sheet (`Alt+Enter`) has the same switch as its Enabled
field.

### Editing a workflow

**Edit Workflow...** on a workflow's context menu opens the workflow file as a
form you read from top to bottom instead of YAML. **New Workflow...**, in
**Repository Actions...** (`Ctrl+Shift+G`), starts one from a starter that
runs on a push to main and by hand.

- **Triggers** is a list, one row per event: "On a push, branches main, paths
  ignore docs/\*\*", "Run by hand, 2 inputs", "On a schedule: 30 5 \* \* 1".
  **Add Trigger...** asks for the event, then its settings: branches, tags and
  paths for a push or pull request, one cron line per time for a schedule,
  and for Run by hand a list of inputs, each with its type, whether it is
  required, its default and, for a choice, its options.
- **Workflow Permissions...** sets what the workflow's token may do: not set,
  read everything, write everything, none, or one level per scope.
- **Jobs** is a list, one row per job: "Build (build), runs on ubuntu-latest,
  runs after Test and Lint, 4 steps". **Edit Job...** has its id, name,
  runner and a check box for each job it runs after; renaming a job carries
  every other job's needs with it. **Job Steps...** lists the steps, each a
  form with the action it uses or the commands it runs, its inputs (one
  `name: value` per line), variables and condition. **Job Permissions...**
  is the same form as the workflow's, for one job.
- **When jobs run** reads the whole dependency graph in words: "First Test
  and Lint, together. Then Build."
- **What GitHub would say** lists everything GitHub would reject the file
  for, kept current as you change it: a key GitHub does not know, a job that
  needs a job that does not exist, jobs that wait for each other in a loop, a
  step that both uses an action and runs commands, an action with no
  version, a permission GitHub does not have. Save refuses while any is
  listed.

Save asks first, naming the file, the repository and your account, then
commits to the default branch, or to a new branch with a pull request when
the default branch is protected or **Save through a pull request** is
checked. If someone changed the file on GitHub since you opened it, nothing
is overwritten and the editor opens again with your draft. Comments at the
top of the file are kept; comments inside it are not, because QUILL's YAML
reader cannot keep them, and the window says so. A file you did not change is
never rewritten.

Chapter 7 has Dependabot's configuration, code owners, and comparing a
repository's configuration with another's.

## Deployments and environments

### Deployments waiting for approval

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

**Approvals**, on the run's context menu, says who approved or rejected its
deployments afterwards.

### An environment's rules

A repository's environments are listed under **Settings > Environments**.
An environment's row has these on its context menu, beside **Secrets...** and
**Variables...**, which are that environment's own:

- **Branch Policies...:** which branches and tags may deploy to it, when it
  allows chosen ones only. Add one by name or with a wildcard, such as
  `release/*`, and say whether it names branches or tags. Change rewrites the
  pattern; Delete removes it.
- **Protection Rules...:** GitHub Apps that must approve each deployment to it.
  Add one by choosing from the apps GitHub says are installed and can do this;
  if there are none, QUILL says so. Delete removes one.
- **Deployments...:** its newest deployments, each with its latest state:
  "production: success, 2026-11-01 11:05 by jeff (v1.0, commit 3f9a2c1)." You
  hear how many there are and the newest one's state; the list has a line
  each. To approve or reject a deployment that is waiting, use **Review
  Pending Deployments...** on the run that is waiting, above.
- **Pin Environment**, **Unpin Environment** and **Move Environment...**,
  under More, choose the order GitHub shows environments in.

An environment's **Properties...** (`Alt+Enter`) puts its protection on one
sheet: the required reviewers, prevent self-review, the wait timer and whether
administrators may bypass, with the custom protection rules (the apps) listed
under them; which branches and tags may deploy, with the chosen ones listed;
how many secrets and variables it has, with their names; and its newest
deployments. The protection, the wait timer and the branch choice can be
changed there; the lists are read only, and the commands above change them.

To compare an environment's rules across many repositories, or make them the
same, use **Across Repositories > Actions by Name > Environments by Name**
(Chapter 12).

### Deleting a deployment

The repository's **Deployments and Environments** place lists where the code
was deployed. A deployment's context menu has **Delete Deployment...**, which
removes it from the history after asking. GitHub deletes only an inactive
deployment; a newer deployment to the same environment makes the older one
inactive, and QUILL says so if you try too early.

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

The repository's **Actions > Artifacts** place lists every run's artifacts
together.

## Caches

Workflows keep caches to run faster: downloaded packages, build outputs. They
are listed in the repository's **Actions > Caches**. The first row sums them
up, such as "12 Actions caches in community-access/quill" and how much space
the listed ones use. Each row after it reads the cache's key, size, branch
and when it was last used, newest first.

A stale or broken cache can make a build fail in strange ways. On a cache's
row, **Delete Cache...**, or the Delete key, removes it after asking.
Workflows build it again the next time they need it.

## Self-hosted runners

A runner is the machine a workflow's jobs run on. GitHub lends its own, and a
repository can bring its own as well, called self-hosted: a lab machine with a
graphics card, a Mac for signing, a build server inside a company network.
When those jobs sit waiting forever, the first question is whether the
machine is even there.

The repository's **Actions > Runners** lists them. Each row reads the
runner's name, its state and its system, such as "lab-1: online, busy, Linux"
or "old-mac: offline, macOS". "Online, idle" means it is there and waiting for
work; "online, busy" means it is running a job now; "offline" means GitHub has
not heard from it, which is why jobs that ask for it never start. The details
pane adds the runner's labels, the words a workflow's `runs-on:` line asks
for, so you can check that the job and the machine agree. **Open on GitHub**
opens the repository's runner settings page.

GitHub shows runners only to the repository's administrators. Anyone else
hears "GitHub shows owner/name's runners only to its administrators." in the
place's note, rather than an empty list that looks like there are none. A
repository that uses only GitHub's own runners lists nothing.

Adding and removing runners needs you to administer the repository:

- **New Runner...**: press `Ctrl+N` in Runners. QUILL asks which system the
  machine runs, such as Linux x64 or Windows x64, then puts the commands that
  set it up on the clipboard and says so. Paste them into a terminal on that
  machine. They download the runner, check its SHA-256 checksum, and register
  it with a token that works for an hour. The token is never said or shown in
  a list.
- **Runner Labels...** on a runner adds a label, such as `gpu`, or takes away
  one that someone added. The labels GitHub gives every runner, such as
  `self-hosted` and `linux`, cannot be taken away.
- **Remove Runner...**, or the Delete key, asks first, then GitHub forgets the
  runner and the program on that machine gets no more jobs.
- **Removal Commands...** puts the commands that unregister a runner on its
  own machine on the clipboard, again without saying or showing the token.

An organization's runners, runner groups and larger runners are under the
organization in the tree. Chapter 12 lists the commands on them, such as
**Just-in-Time Runner...** and **Is a Runner Version Retiring?...**.

## Secret and variable names

A repository's **Settings > Secret and Variable Names** lists the names of the
repository's secrets and variables, and those of each environment, with when
each was last updated: "Repository secret: DEPLOY_KEY, updated 2026-10-02". It
answers "is that secret set?" without anyone needing to see it.

The names are all you get. QUILL never reads a secret's or variable's value,
and it drops any value GitHub sends before it reaches the screen. Reading the
names needs a signed-in account with access to the repository's settings.

To set a secret's value, or add, change and delete variables, use
**Settings > Actions Secrets** and **Actions Variables**. Chapter 8 covers
secrets, and how a value is sealed on your computer before it is sent.

## A walk-through: reading the practice repository's failed run

The practice repository has a workflow that fails on purpose. Make it first
with **Help > Practice on GitHub...** (`Ctrl+Alt+P`) if you have not.

1. In the Workbench, press `Ctrl+L`, type `quill-practice` and press Enter.
2. Press `Ctrl+Shift+4` for its Runs, then F6 to the list. You hear a row
   starting "failure, Practice checks".
3. Press `Ctrl+Shift+W`. The What Failed window opens, and you hear "What
   failed is ready." and the first line. Arrow down: the failing step is
   called Fail on purpose, and its last log lines follow.
4. Press Escape to close it.
5. Press Enter on the same run. The jobs window opens. Arrow to the failed
   job and press `Alt+L` to load its whole log. Press Escape when you are
   done.
6. Press `Ctrl+Shift+F5` and answer Yes. You hear that GitHub started a re-run
   of the failed jobs. It fails again, which is the point here; in a real
   repository you would fix it first.
7. Press `F5` after a minute to refresh the list and hear the new attempt.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2`) has **Read a failed run**, on the practice
repository: list the runs, read what failed, and run only the failure again.
**Try a command without sending it** shows Dry Run, so you can try Delete
Run... and hear what it would send without sending it.

---

- Previous: [Chapter 5: Pull requests and review](github-guide-05-pull-requests-and-review.html)
- Next: [Chapter 7: Code and repositories](github-guide-07-code-and-repositories.html)
- [Contents](github-guide.html)
