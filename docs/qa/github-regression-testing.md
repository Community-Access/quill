# GitHub Workbench regression testing

This is how the GitHub Workbench is tested against a real repository, so a
change that breaks a list, a sheet or a command is found by a run, not by
someone using it. It has two halves:

- **The live run** (`docs/qa/github-live-run.py`) does everything a machine can
  check, through the code the Workbench itself runs, and writes its results
  into the "Live run" section at the end of this document.
- **The checks only a person can make**: what is spoken and brailled, and how
  each dialog feels from the keyboard. Those are listed in "Needs Jeff" below
  and in `docs/qa/screen-reader-checks-2026-10.md`.

## What the live run covers

The run does not keep a hand-written list of features. It reads the code's own
tables, so whatever is added to the Workbench is in the next run:

- **Every list.** Each node in the Workbench's tree that loads rows (87 of them
  in November 2026, under the top level, a repository, a person and an
  organization) is opened through the window's own provider
  (`GitHubWorkbenchProvider.load`), with the same filters and limits as a fresh
  window. A node that cannot load for a stated reason, such as one that needs a
  repository open, says that reason, as the window would.
- **Every properties sheet.** Each of the 39 sheet kinds (`SHEETS`) is loaded
  on a real object. On the objects the run made itself, every editable field is
  then changed, read back from GitHub, and put back, through the sheet engine's
  `save` and `inverse`, which are the code behind the sheet's Save and the
  Workbench's Undo. A field the run leaves alone, such as your own profile's
  name, is listed with the reason.
- **Every write command.** Each of the Workbench's write commands
  (`COMMAND_REQUIREMENTS`, 95 of them) has a scenario that does what its
  handler does, through the same provider call, checks that GitHub took it, and
  undoes it. A command the run cannot do has a reason instead: "not here" when
  the test account has nothing to try it on (a second account, a fork, an
  organization the run must not change), and "needs Jeff" when it would change
  something of yours (your real notifications, a billed codespace) or only a
  person can judge it.
- **The features that are not single commands**: the line commands (Copy
  GitHub Link to This Line, Who Changed This Line?, the pull request for a
  line, references), Import Issues from a Spreadsheet, New Issues from Lines,
  and Export List.

`tests/unit/docs/test_github_live_run_coverage.py` fails the build when a write
command or a sheet is added without a scenario or a reason in the run. It does
not reach GitHub.

## The test repositories

The run works in two repositories of the signed-in account:
`<you>/quill-workbench-test` and `<you>/quill-workbench-test-2` (the second is
for Across Repositories and Transfer Issue). `--create` makes them, public by
default, because rulesets and branch protection need a paid plan on a private
repository; `--private` makes them private anyway. Before the checks, the run
makes one of everything the sheets and commands need, each called "QUILL live
test":

- files, including a workflow, an issue form and a pull request template;
- two labels, a milestone, two issues, a comment, a branch with a pull request,
  a protected branch, and a release;
- an environment, an Actions variable and secret, a webhook to `example.com`
  (turned off), a ruleset (not enforced), a read-only deploy key, a deployment,
  a discussion, a secret gist and a Project;
- one run of the test workflow, which leaves a job, an artifact and a cache.

Everything the run adds for a single check is deleted after that check, and
every field it changes is put back. The test repositories themselves are kept,
so the next run is quicker; delete them on GitHub when you no longer want them.
The run keeps its local lists (sets, favorites, snoozes, watches) in a scratch
folder that it deletes, never in your QUILL data.

## Running it

From the repository root, on the computer where you are signed in to GitHub in
QUILL:

```powershell
python docs/qa/github-live-run.py --create   # the first time: makes the two repositories
python docs/qa/github-live-run.py            # every run after that
python docs/qa/github-live-run.py --dry-run  # reads only: lists and sheets, writes nothing
python docs/qa/github-live-run.py --only lists,sheets
python docs/qa/github-live-run.py --keep     # leave what the run made, to look at it
```

The token comes, in this order, from `QUILL_LIVE_GITHUB_TOKEN`, QUILL's active
GitHub account, QUILL's older single token, then `gh auth token`. It is never
printed, logged or written; any error that contains it shows "(token)" instead.
A full run takes about fifteen minutes, most of it waiting for the test
workflow. It prints one line per result as it goes, writes the results below,
and exits with 1 when anything failed.

Some results depend on what the token may do:

- Projects need the `project` scope (`gh auth refresh -s project`).
- Following someone needs `user:follow`; the run follows and unfollows
  `octocat`, and leaves alone whether you followed them before.
- Reading an organization uses `--org` (Community-Access by default) and never
  changes it.

## Needs Jeff

These are not machine checks, and the run marks them "needs Jeff":

- What each list, sheet, preview and result window says with NVDA and JAWS, and
  what is brailled: the GitHub sections of
  `docs/qa/screen-reader-checks-2026-10.md`.
- Mark as Read, Mark as Done and Mark All as Read, which would change your real
  notifications.
- Open in Codespaces, which makes a billed codespace.
- Clone and Start Worktree, which ask for a folder and open it in the editor.

## Live run

Not run yet. The results of the next run replace this section.
