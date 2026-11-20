# The GitHub Guide for QUILL and QUILL Lite

This is the book on doing GitHub work with a screen reader in QUILL and QUILL
Lite: answering what needs you, reading and triaging issues, reviewing pull
requests line by line, finding out why a build failed, browsing code, and
looking after repositories, teams and access. It is a book of its own, beside
each editor's user guide, because there is a lot to say and you may only need
part of it.

You write in the editor, and you do GitHub work in the GitHub Workbench, one
window for everything GitHub. The same Workbench ships in both editors, and so
does this book. Where the two differ, a short paragraph starting **In QUILL
Lite** says how, and Chapter 14 lists every difference.

## How to read this book

- **New to it?** Read Chapters 1 and 2, in that order. They get you signed in
  and show you round the Workbench. Then go to the chapter for the job in
  front of you.
- **Clearing your inbox?** Chapter 3.
- **Issues?** Chapter 4. **Reviewing pull requests?** Chapter 5.
- **A build failed?** Chapter 6, and its section on What Failed.
- **Looking after a repository, an organization or who has access?**
  Chapters 7, 8 and 13.
- **Looking something up?** Chapter 11 has every key, Chapter 12 every place
  in the Workbench, and Appendix A what GitHub needs for each part.
- **Something went wrong?** Chapter 10 has the sentences QUILL says when
  something fails, and what to do about each.

Every chapter starts with why you are there, what you will do and what you
will have at the end, and most end with a walk-through on a practice
repository of your own and the guided lesson that goes with it. Headings are
real headings: each chapter is a level 3 heading on this page, so pressing 3
in JAWS or NVDA moves from chapter to chapter, and inside a chapter its topics
are level 2 headings. At the bottom of every chapter are links to the chapters
either side and back to these contents.

## Keys at a glance

- **Opening the Workbench.** In QUILL, **File > Open from Remote > GitHub
  Items...**. In QUILL Lite, **File > GitHub Workbench...**: `Alt+F`, then
  `G`. In either, **View > GitHub Workbench Mode** adds a GitHub menu
  (`Alt+G`) with the doors in.
- **`F6`** moves between the tree, the filter, the list, the details and the
  status bar.
- **Enter** does the obvious thing, **Backspace** comes back out, and
  **`Shift+Enter`** opens the row on GitHub.
- **`Ctrl+1` to `Ctrl+0`** go to a place: Inbox, the current repository,
  Search, People, Gists, Projects, Watches, Saved Searches, Start Here and
  Across Repositories. **`Ctrl+Shift+1` to `Ctrl+Shift+0`** go to a part of
  the repository: Issues, Pull Requests, Discussions, Actions and the rest.
- **`Alt+1` to `Alt+9`** say something without moving you: where you are,
  what is selected, the item's state, and more.
- **`Alt+Enter`** shows everything about the selected row on one sheet, where
  you can change it.
- **`Shift+F1`** says everything you can do with the selected row, with each
  key, and why anything is greyed. **`F1`** says what the place and the
  control are for.
- **`Ctrl+Z`** takes back your last change on GitHub, where GitHub allows it.
- **`Ctrl+E`** moves to the filter box.

[Chapter 11](lite-github-guide-11-keyboard-reference.html) has every key.

## The chapters

### [Chapter 1: Getting started](lite-github-guide-01-getting-started.html)

What the Workbench is, opening it in each editor, the one question QUILL asks
before it connects, signing in with GitHub, keeping more than one account, an
Enterprise Server, how much the Workbench may change, and Safe Mode. It ends
with a two-minute tour.

- [What the GitHub Workbench is](lite-github-guide-01-getting-started.html#what-the-github-workbench-is)
- [Three promises](lite-github-guide-01-getting-started.html#three-promises)
- [Opening the Workbench](lite-github-guide-01-getting-started.html#opening-the-workbench)
- [The first time: permission to connect](lite-github-guide-01-getting-started.html#the-first-time-permission-to-connect)
- [Signing in](lite-github-guide-01-getting-started.html#signing-in)
- [More than one account](lite-github-guide-01-getting-started.html#more-than-one-account)
- [How much the Workbench may change](lite-github-guide-01-getting-started.html#how-much-the-workbench-may-change)
- [The GitHub CLI and your account](lite-github-guide-01-getting-started.html#the-github-cli-and-your-account)
- [Safe Mode](lite-github-guide-01-getting-started.html#safe-mode)
- [A two-minute tour](lite-github-guide-01-getting-started.html#a-two-minute-tour)
- [Learn it with a guided lesson](lite-github-guide-01-getting-started.html#learn-it-with-a-guided-lesson)

### [Chapter 2: A tour of the GitHub Workbench](lite-github-guide-02-getting-around.html)

The GitHub menu, then the Workbench window: its tree and Go keys, lists, the
filter, Properties, the context menu, how QUILL asks before it changes
anything, Ctrl+Z and Change History, the status bar, pasting a link, GitHub's
hourly allowance, and the help keys.

- [GitHub Workbench Mode and the GitHub menu](lite-github-guide-02-getting-around.html#github-workbench-mode-and-the-github-menu)
- [Opening the Workbench](lite-github-guide-02-getting-around.html#opening-the-workbench)
- [The panes](lite-github-guide-02-getting-around.html#the-panes)
- [Finding your way round the tree](lite-github-guide-02-getting-around.html#finding-your-way-round-the-tree)
- [Reading a list](lite-github-guide-02-getting-around.html#reading-a-list)
- [Enter, Shift+Enter and Backspace](lite-github-guide-02-getting-around.html#enter-shiftenter-and-backspace)
- [The filter](lite-github-guide-02-getting-around.html#the-filter)
- [Properties](lite-github-guide-02-getting-around.html#properties)
- [The context menu and the Item menu](lite-github-guide-02-getting-around.html#the-context-menu-and-the-item-menu)
- [How QUILL asks before it changes GitHub](lite-github-guide-02-getting-around.html#how-quill-asks-before-it-changes-github)
- [Taking a change back](lite-github-guide-02-getting-around.html#taking-a-change-back)
- [The status bar](lite-github-guide-02-getting-around.html#the-status-bar)
- [What QUILL says, and what it leaves to your screen reader](lite-github-guide-02-getting-around.html#what-quill-says-and-what-it-leaves-to-your-screen-reader)
- [Open GitHub Reference: paste any link](lite-github-guide-02-getting-around.html#open-github-reference-paste-any-link)
- [Rate limits and the readout](lite-github-guide-02-getting-around.html#rate-limits-and-the-readout)
- [F1, and help for every place](lite-github-guide-02-getting-around.html#f1-and-help-for-every-place)
- [A walk-through: your first five minutes](lite-github-guide-02-getting-around.html#a-walk-through-your-first-five-minutes)
- [Practising on a repository of your own](lite-github-guide-02-getting-around.html#practising-on-a-repository-of-your-own)

### [Chapter 3: Your inbox and your work](lite-github-guide-03-inbox-and-your-work.html)

Needs My Attention: reading and clearing your notifications from the
keyboard, invitations, inbox rules, the Inbox that gathers everything waiting
on you, and your own open work.

- [Needs My Attention](lite-github-guide-03-inbox-and-your-work.html#needs-my-attention)
- [Reading your notifications](lite-github-guide-03-inbox-and-your-work.html#reading-your-notifications)
- [Opening a notification](lite-github-guide-03-inbox-and-your-work.html#opening-a-notification)
- [Invitations](lite-github-guide-03-inbox-and-your-work.html#invitations)
- [Inbox rules](lite-github-guide-03-inbox-and-your-work.html#inbox-rules)
- [How often QUILL checks](lite-github-guide-03-inbox-and-your-work.html#how-often-quill-checks)
- [The Inbox: what needs you to act](lite-github-guide-03-inbox-and-your-work.html#the-inbox-what-needs-you-to-act)
- [Your open work, split by why it is yours](lite-github-guide-03-inbox-and-your-work.html#your-open-work-split-by-why-it-is-yours)
- [Activity](lite-github-guide-03-inbox-and-your-work.html#activity)
- [A walk-through: clearing your inbox in the morning](lite-github-guide-03-inbox-and-your-work.html#a-walk-through-clearing-your-inbox-in-the-morning)
- [Learn it with a guided lesson](lite-github-guide-03-inbox-and-your-work.html#learn-it-with-a-guided-lesson)

### [Chapter 4: Issues](lite-github-guide-04-issues.html)

Finding, reading and commenting on issues, writing one from a template or an
issue form, labels, milestones, types and fields, closing, many at once,
relationships, Projects, and starting work in a folder of its own.

- [Finding an issue](lite-github-guide-04-issues.html#finding-an-issue)
- [Reading an issue](lite-github-guide-04-issues.html#reading-an-issue)
- [Commenting](lite-github-guide-04-issues.html#commenting)
- [Reactions](lite-github-guide-04-issues.html#reactions)
- [The timeline](lite-github-guide-04-issues.html#the-timeline)
- [Writing a new issue](lite-github-guide-04-issues.html#writing-a-new-issue)
- [Labels, milestones and assignees](lite-github-guide-04-issues.html#labels-milestones-and-assignees)
- [Closing and reopening](lite-github-guide-04-issues.html#closing-and-reopening)
- [Changing many issues at once](lite-github-guide-04-issues.html#changing-many-issues-at-once)
- [Housekeeping](lite-github-guide-04-issues.html#housekeeping)
- [Issue fields](lite-github-guide-04-issues.html#issue-fields)
- [Deleting an issue](lite-github-guide-04-issues.html#deleting-an-issue)
- [Branches and task lists](lite-github-guide-04-issues.html#branches-and-task-lists)
- [Projects](lite-github-guide-04-issues.html#projects)
- [Starting an issue in its own folder](lite-github-guide-04-issues.html#starting-an-issue-in-its-own-folder)
- [A walk-through: one issue, from open to closed](lite-github-guide-04-issues.html#a-walk-through-one-issue-from-open-to-closed)
- [Learn it with a guided lesson](lite-github-guide-04-issues.html#learn-it-with-a-guided-lesson)

### [Chapter 5: Pull requests and review](lite-github-guide-05-pull-requests-and-review.html)

The pull requests that need you, the review outline and its one-sentence
summary, the diff, comments on a line or a range, sending a review, and
everything that gets a pull request merged.

- [Finding the pull requests that need you](lite-github-guide-05-pull-requests-and-review.html#finding-the-pull-requests-that-need-you)
- [Opening a pull request](lite-github-guide-05-pull-requests-and-review.html#opening-a-pull-request)
- [The one-sentence summary](lite-github-guide-05-pull-requests-and-review.html#the-one-sentence-summary)
- [The review window](lite-github-guide-05-pull-requests-and-review.html#the-review-window)
- [Files you have viewed](lite-github-guide-05-pull-requests-and-review.html#files-you-have-viewed)
- [Changed since my last review](lite-github-guide-05-pull-requests-and-review.html#changed-since-my-last-review)
- [The diff](lite-github-guide-05-pull-requests-and-review.html#the-diff)
- [Commenting on a line or a range](lite-github-guide-05-pull-requests-and-review.html#commenting-on-a-line-or-a-range)
- [Pending comments and sending your review](lite-github-guide-05-pull-requests-and-review.html#pending-comments-and-sending-your-review)
- [Replying and resolving](lite-github-guide-05-pull-requests-and-review.html#replying-and-resolving)
- [Reviews already sent](lite-github-guide-05-pull-requests-and-review.html#reviews-already-sent)
- [Getting a pull request merged](lite-github-guide-05-pull-requests-and-review.html#getting-a-pull-request-merged)
- [The whole patch, a revert, and conflicts](lite-github-guide-05-pull-requests-and-review.html#the-whole-patch-a-revert-and-conflicts)
- [Dependabot's pull requests](lite-github-guide-05-pull-requests-and-review.html#dependabots-pull-requests)
- [Writing a new pull request](lite-github-guide-05-pull-requests-and-review.html#writing-a-new-pull-request)
- [Learn it with a guided lesson](lite-github-guide-05-pull-requests-and-review.html#learn-it-with-a-guided-lesson)

### [Chapter 6: Actions and checks](lite-github-guide-06-actions-and-checks.html)

Workflow runs, What Failed, jobs and logs, re-running and cancelling, checks,
starting and editing workflows, deployments and environments, artifacts,
caches and runners.

- [Finding a repository's runs](lite-github-guide-06-actions-and-checks.html#finding-a-repositorys-runs)
- [What Failed](lite-github-guide-06-actions-and-checks.html#what-failed)
- [Jobs and logs](lite-github-guide-06-actions-and-checks.html#jobs-and-logs)
- [Doing something about a run](lite-github-guide-06-actions-and-checks.html#doing-something-about-a-run)
- [Combined check status](lite-github-guide-06-actions-and-checks.html#combined-check-status)
- [Re-requesting a check](lite-github-guide-06-actions-and-checks.html#re-requesting-a-check)
- [Starting a workflow](lite-github-guide-06-actions-and-checks.html#starting-a-workflow)
- [Looking after workflows](lite-github-guide-06-actions-and-checks.html#looking-after-workflows)
- [Deployments and environments](lite-github-guide-06-actions-and-checks.html#deployments-and-environments)
- [Artifacts](lite-github-guide-06-actions-and-checks.html#artifacts)
- [Caches](lite-github-guide-06-actions-and-checks.html#caches)
- [Self-hosted runners](lite-github-guide-06-actions-and-checks.html#self-hosted-runners)
- [Secret and variable names](lite-github-guide-06-actions-and-checks.html#secret-and-variable-names)
- [A walk-through: reading the practice repository's failed run](lite-github-guide-06-actions-and-checks.html#a-walk-through-reading-the-practice-repositorys-failed-run)
- [Learn it with a guided lesson](lite-github-guide-06-actions-and-checks.html#learn-it-with-a-guided-lesson)

### [Chapter 7: Code and repositories](lite-github-guide-07-code-and-repositories.html)

Files at any branch, tag or commit, blame and history, GitHub from the line
you are on, branches, tags and releases, search, configuration, insights,
looking after a repository, the wiki, webhooks, packages and gists.

- [Browsing a repository's files](lite-github-guide-07-code-and-repositories.html#browsing-a-repositorys-files)
- [Blame and file history](lite-github-guide-07-code-and-repositories.html#blame-and-file-history)
- [From the line you are on](lite-github-guide-07-code-and-repositories.html#from-the-line-you-are-on)
- [Opening and saving files in QUILL](lite-github-guide-07-code-and-repositories.html#opening-and-saving-files-in-quill)
- [Cloning a repository](lite-github-guide-07-code-and-repositories.html#cloning-a-repository)
- [Branches](lite-github-guide-07-code-and-repositories.html#branches)
- [Setting a commit's status](lite-github-guide-07-code-and-repositories.html#setting-a-commits-status)
- [Commit comments](lite-github-guide-07-code-and-repositories.html#commit-comments)
- [Tags and releases](lite-github-guide-07-code-and-repositories.html#tags-and-releases)
- [Searching](lite-github-guide-07-code-and-repositories.html#searching)
- [Forks, templates and topics](lite-github-guide-07-code-and-repositories.html#forks-templates-and-topics)
- [The community profile](lite-github-guide-07-code-and-repositories.html#the-community-profile)
- [Dependabot, code owners and configuration](lite-github-guide-07-code-and-repositories.html#dependabot-code-owners-and-configuration)
- [Insights](lite-github-guide-07-code-and-repositories.html#insights)
- [Looking after a repository](lite-github-guide-07-code-and-repositories.html#looking-after-a-repository)
- [GitHub Pages](lite-github-guide-07-code-and-repositories.html#github-pages)
- [The wiki](lite-github-guide-07-code-and-repositories.html#the-wiki)
- [Webhooks, deploy keys and autolinks](lite-github-guide-07-code-and-repositories.html#webhooks-deploy-keys-and-autolinks)
- [Watching, starring and following](lite-github-guide-07-code-and-repositories.html#watching-starring-and-following)
- [Packages](lite-github-guide-07-code-and-repositories.html#packages)
- [Gists](lite-github-guide-07-code-and-repositories.html#gists)
- [Other places under a repository](lite-github-guide-07-code-and-repositories.html#other-places-under-a-repository)
- [A walk-through: from a branch to a tagged release](lite-github-guide-07-code-and-repositories.html#a-walk-through-from-a-branch-to-a-tagged-release)
- [Learn it with a guided lesson](lite-github-guide-07-code-and-repositories.html#learn-it-with-a-guided-lesson)

### [Chapter 8: Discussions and security](lite-github-guide-08-discussions-and-security.html)

Discussion threads, answers and polls; then security alerts, dependency
review, an organization's security overview, advisories and secrets.

- [Discussions](lite-github-guide-08-discussions-and-security.html#discussions)
- [Security alerts](lite-github-guide-08-discussions-and-security.html#security-alerts)
- [Dependency review on a pull request](lite-github-guide-08-discussions-and-security.html#dependency-review-on-a-pull-request)
- [An organization's security overview](lite-github-guide-08-discussions-and-security.html#an-organizations-security-overview)
- [Security policy and reporting](lite-github-guide-08-discussions-and-security.html#security-policy-and-reporting)
- [Security advisories](lite-github-guide-08-discussions-and-security.html#security-advisories)
- [Secrets](lite-github-guide-08-discussions-and-security.html#secrets)
- [Searching the Advisory Database](lite-github-guide-08-discussions-and-security.html#searching-the-advisory-database)
- [A software bill of materials](lite-github-guide-08-discussions-and-security.html#a-software-bill-of-materials)
- [A walk-through: your first discussion](lite-github-guide-08-discussions-and-security.html#a-walk-through-your-first-discussion)

### [Chapter 9: Codespaces and the GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html)

Your codespaces in the Workbench, making one, and the GitHub CLI, including
how QUILL keeps the two sign-ins on the same account.

- [Your codespaces in the Workbench](lite-github-guide-09-codespaces-and-the-cli.html#your-codespaces-in-the-workbench)
- [Making a codespace](lite-github-guide-09-codespaces-and-the-cli.html#making-a-codespace)
- [The GitHub CLI](lite-github-guide-09-codespaces-and-the-cli.html#the-github-cli)
- [QUILL's Codespaces commands](lite-github-guide-09-codespaces-and-the-cli.html#quills-codespaces-commands)
- [Other things that use Git or the CLI](lite-github-guide-09-codespaces-and-the-cli.html#other-things-that-use-git-or-the-cli)

### [Chapter 10: Troubleshooting, privacy and help](lite-github-guide-10-troubleshooting.html)

The sentences QUILL says when something fails, what each means and what to do
about it, using a token instead of signing in, exactly what goes over the
network, and how to reach a person.

- [Before you start: four quick checks](lite-github-guide-10-troubleshooting.html#before-you-start-four-quick-checks)
- [How a refusal sounds](lite-github-guide-10-troubleshooting.html#how-a-refusal-sounds)
- [The refusals, one by one](lite-github-guide-10-troubleshooting.html#the-refusals-one-by-one)
- [Held back by the Workbench](lite-github-guide-10-troubleshooting.html#held-back-by-the-workbench)
- [Connecting and signing in](lite-github-guide-10-troubleshooting.html#connecting-and-signing-in)
- [When GitHub refuses](lite-github-guide-10-troubleshooting.html#when-github-refuses)
- [Is it GitHub, or is it me?](lite-github-guide-10-troubleshooting.html#is-it-github-or-is-it-me)
- [When the help itself is wrong](lite-github-guide-10-troubleshooting.html#when-the-help-itself-is-wrong)
- [Advanced: using a token](lite-github-guide-10-troubleshooting.html#advanced-using-a-token)
- [Privacy: what goes over the network](lite-github-guide-10-troubleshooting.html#privacy-what-goes-over-the-network)
- [Getting help](lite-github-guide-10-troubleshooting.html#getting-help)

### [Chapter 11: Keyboard reference](lite-github-guide-11-keyboard-reference.html)

Every key the Workbench and its windows answer to.

- [The GitHub menu, in workbench mode](lite-github-guide-11-keyboard-reference.html#the-github-menu-in-workbench-mode)
- [The GitHub Workbench window](lite-github-guide-11-keyboard-reference.html#the-github-workbench-window)
- [Review pull request](lite-github-guide-11-keyboard-reference.html#review-pull-request)
- [The diff](lite-github-guide-11-keyboard-reference.html#the-diff)
- [Repository Files](lite-github-guide-11-keyboard-reference.html#repository-files)
- [Actions windows](lite-github-guide-11-keyboard-reference.html#actions-windows)
- [Issue windows](lite-github-guide-11-keyboard-reference.html#issue-windows)
- [Discussion windows](lite-github-guide-11-keyboard-reference.html#discussion-windows)
- [Compare branches](lite-github-guide-11-keyboard-reference.html#compare-branches)

### [Chapter 12: The GitHub Workbench, place by place](lite-github-guide-12-the-workbench.html)

The Workbench a place at a time: Start Here, Needs My Attention, each
repository's parts, Search, People, Watches, Across Repositories, the help
places, Dry Run, the API Console, the practice repository and Workbench
Options.

- [Opening it](lite-github-guide-12-the-workbench.html#opening-it)
- [Start Here](lite-github-guide-12-the-workbench.html#start-here)
- [Needs My Attention](lite-github-guide-12-the-workbench.html#needs-my-attention)
- [Repositories](lite-github-guide-12-the-workbench.html#repositories)
- [Search](lite-github-guide-12-the-workbench.html#search)
- [People, Gists and Projects](lite-github-guide-12-the-workbench.html#people-gists-and-projects)
- [Lists of settings](lite-github-guide-12-the-workbench.html#lists-of-settings)
- [Watches](lite-github-guide-12-the-workbench.html#watches)
- [Why Ctrl+3, Ctrl+4 and Ctrl+8 go places here](lite-github-guide-12-the-workbench.html#why-ctrl3-ctrl4-and-ctrl8-go-places-here)
- [Across Repositories](lite-github-guide-12-the-workbench.html#across-repositories)
- [Doing things to what is selected](lite-github-guide-12-the-workbench.html#doing-things-to-what-is-selected)
- [More commands on rows](lite-github-guide-12-the-workbench.html#more-commands-on-rows)
- [Hearing where you are](lite-github-guide-12-the-workbench.html#hearing-where-you-are)
- [Help and Learning](lite-github-guide-12-the-workbench.html#help-and-learning)
- [Say or Type a Command](lite-github-guide-12-the-workbench.html#say-or-type-a-command)
- [Dry Run](lite-github-guide-12-the-workbench.html#dry-run)
- [The GitHub API Console](lite-github-guide-12-the-workbench.html#the-github-api-console)
- [Practice on GitHub](lite-github-guide-12-the-workbench.html#practice-on-github)
- [Is it GitHub, or is it me?](lite-github-guide-12-the-workbench.html#is-it-github-or-is-it-me)
- [Workbench Options](lite-github-guide-12-the-workbench.html#workbench-options)
- [A walk-through: finding your way on the practice repository](lite-github-guide-12-the-workbench.html#a-walk-through-finding-your-way-on-the-practice-repository)
- [Learn it with a guided lesson](lite-github-guide-12-the-workbench.html#learn-it-with-a-guided-lesson)

### [Chapter 13: Properties, filters and permissions](lite-github-guide-13-properties-filters-permissions.html)

Alt+Enter on anything: the Properties sheet, changing many things at once,
undoing a change, filtering a list on anything, and permissions: yours, the
Workbench levels, and who else has access.

- [Properties: Alt+Enter on anything](lite-github-guide-13-properties-filters-permissions.html#properties-altenter-on-anything)
- [Many at once](lite-github-guide-13-properties-filters-permissions.html#many-at-once)
- [Undoing a change](lite-github-guide-13-properties-filters-permissions.html#undoing-a-change)
- [Filtering](lite-github-guide-13-properties-filters-permissions.html#filtering)
- [Permissions](lite-github-guide-13-properties-filters-permissions.html#permissions)
- [A walk-through: labelling two issues, then taking it back](lite-github-guide-13-properties-filters-permissions.html#a-walk-through-labelling-two-issues-then-taking-it-back)
- [Learn it with a guided lesson](lite-github-guide-13-properties-filters-permissions.html#learn-it-with-a-guided-lesson)

### [Chapter 14: GitHub in QUILL Lite](lite-github-guide-14-quill-lite.html)

What is the same in QUILL Lite, and the few things that differ.

- [One Workbench, two editors](lite-github-guide-14-quill-lite.html#one-workbench-two-editors)
- [Opening it](lite-github-guide-14-quill-lite.html#opening-it)
- [The GitHub menu](lite-github-guide-14-quill-lite.html#the-github-menu)
- [Rows that need something only QUILL has](lite-github-guide-14-quill-lite.html#rows-that-need-something-only-quill-has)
- [Files from GitHub](lite-github-guide-14-quill-lite.html#files-from-github)
- [The guide and the lessons](lite-github-guide-14-quill-lite.html#the-guide-and-the-lessons)
- [A walk-through: the same job in both editors](lite-github-guide-14-quill-lite.html#a-walk-through-the-same-job-in-both-editors)

### [Appendix A: What GitHub needs for each part of the Workbench](lite-github-guide-appendix-a-features.html)

What GitHub needs for each part of the Workbench: your role, your sign-in's
permissions, and the features a repository or organization must have.

- [How to read it](lite-github-guide-appendix-a-features.html#how-to-read-it)
- [Reading](lite-github-guide-appendix-a-features.html#reading)
- [Issues, pull requests and discussions](lite-github-guide-appendix-a-features.html#issues-pull-requests-and-discussions)
- [Code, releases and Actions](lite-github-guide-appendix-a-features.html#code-releases-and-actions)
- [Repository settings and security](lite-github-guide-appendix-a-features.html#repository-settings-and-security)
- [Organizations, teams and access](lite-github-guide-appendix-a-features.html#organizations-teams-and-access)
- [Enterprise Server](lite-github-guide-appendix-a-features.html#enterprise-server)
- [Outside GitHub](lite-github-guide-appendix-a-features.html#outside-github)

---

- [QUILL Lite User Guide](../userguide.html)
