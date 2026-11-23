# GitHub Workbench help sessions (GH-R-119, D20)

This is the kit for the timed "find the answer in help" sessions that close GH-R-119. The help itself is built and checked by GATE-GITHUB-HELP: one catalogue behind F1, Shift+F1, Alt+F1, Search Help and the generated reference. What is left is measuring it with people, as the PRD's D20 and section 12 ask.

GH-R-119 changes from Partly to Met in `github-workbench-requirement-audit-2026-11.md` once the five sessions below are recorded and every task that failed has an issue filed against the help.

## Who

About five people, as section 12 asks. Between them, cover:

- someone new to GitHub and someone experienced;
- screen-reader users (NVDA and JAWS, and one using a braille display if possible) and at least one sighted person.

Write each person down by a short code (P1 to P5) and what they use, never by name.

## Setting up

1. An installed QUILL build from main, signed in to the test repository with a Read Only account, so nothing a participant does can change GitHub.
2. The GitHub Workbench open on Inbox. Clear the help history and Search Help's last search.
3. A timer. Time starts when you finish reading the task aloud, and stops when the person says the answer or gives up.
4. Do not show anyone where help lives. If someone asks "how do I get help?", say "however you'd normally look", and note that they asked.

## The tasks

Read each task aloud exactly as written. Tasks 1 to 5 are section 12's; tasks 6 to 10 are "find the answer in help" tasks, which D20 asks to time. Stop a task at 5 minutes and mark it Gave up.

1. Find the pull requests waiting for your review.
2. Re-run only the failed jobs of the latest workflow run.
3. Draft release notes for the latest release.
4. Find who has access to the repository.
5. Read the issue a notification is about, then open the file it names in the editor and come back.
6. Using help, find out what Type to Confirm is for, and when QUILL asks for it.
7. Using help, find out how to compare a Dependabot configuration across repositories.
8. Using help, find out what the GitHub Permissions shown for this repository mean you can do.
9. Using help, find out how to see what failed in a workflow run without opening every job.
10. Using help, find out every key the GitHub Workbench has.

## What to record

For each task:

- **Time,** in seconds.
- **Wrong turns:** each time the person went somewhere that did not lead to the answer (a wrong node, a wrong menu, a help topic that did not answer it).
- **Help used:** none, F1, Shift+F1, Alt+F1, Search Help or the generated reference. List them in the order used.
- **Result:** Found, Found with a hint, or Gave up.
- **What they said:** their words about anything confusing, especially a help topic's first sentence (D20 puts the answer there, within a 40-cell braille line where it can).

## Results

Copy this table once per person.

**P_ (new or experienced; screen reader, braille display or sighted):**

| Task | Time (s) | Wrong turns | Help used | Result | Notes |
|---|---|---|---|---|---|
| 1. Pull requests waiting for review | | | | | |
| 2. Re-run failed jobs | | | | | |
| 3. Draft release notes | | | | | |
| 4. Who has access | | | | | |
| 5. Notification, file and back | | | | | |
| 6. Type to Confirm | | | | | |
| 7. Compare Dependabot configuration | | | | | |
| 8. GitHub Permissions | | | | | |
| 9. What Failed | | | | | |
| 10. Every Workbench key | | | | | |

## After the sessions

1. Add a short summary here: the median time and the wrong turns per task, and which tasks anyone gave up on.
2. For each Gave up or Found with a hint, file an issue naming the task, the help surface they tried, and their words. A help fix changes the catalogue, so GATE-GITHUB-HELP checks it.
3. Record any screen-reader problems in `screen-reader-checks-2026-10.md`.
4. Change GH-R-119 to Met in the requirement audit and recount its summary table.
