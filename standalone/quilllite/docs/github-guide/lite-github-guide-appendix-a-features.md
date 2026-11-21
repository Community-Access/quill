# Appendix A: What GitHub needs for each part of the Workbench

## What this appendix covers

You are looking after an organization and deciding what to let people do, or
a command said it could not do something and you want to know why. This
appendix is for you.

The Workbench can do anything GitHub lets your account do, and nothing more.
Three things decide what that is, and this appendix lists, part by part, what
each one needs:

- **Your role** on the repository or organization: read, triage, write,
  maintain or admin on a repository; member or owner in an organization. A
  custom role counts as whatever it grants.
- **Your sign-in's permissions**, called scopes. Sign In with GitHub asks for
  every scope the Workbench uses (Chapter 1). A token you made yourself has
  only what you gave it. **Account > GitHub Permissions...** (`Ctrl+Shift+P`)
  lists them all, and which you have.
- **Your Workbench level**, Read Only, Organize or Full, which QUILL checks
  before GitHub is asked (Chapters 1 and 13).

Some parts also need a feature GitHub turns on only for certain repositories,
organizations or plans. Those are named in the last column.

## How to read it

- **Role** is the role the Workbench checks for before it offers a command,
  which is the smallest role GitHub asks for. An organization can make
  GitHub stricter; GitHub's answer always wins.
- **Workbench level.** Read Only reads everything. Organize adds organizing
  changes, such as labels, reactions and stars, and changes other people
  will see, such as comments, merges and re-runs. Full adds access and
  settings changes, and anything destructive or hard to reverse, such as
  deleting. `Shift+F1` on a command says the level it needs.
- **When it is missing.** QUILL does not guess. A place you cannot read says
  why on its one row, and a command you cannot use is greyed, and `Shift+F1`
  says why. When GitHub itself refuses, QUILL says so and names the
  permission or scope GitHub asked for (Chapter 10).

## Reading

| Part | Role | Scope | Also needs |
| --- | --- | --- | --- |
| A public repository's issues, pull requests, files, runs and logs | none: works signed out | none | nothing |
| Private repositories | read | `repo` | nothing |
| Inbox, notifications, review requests, mentions | signed in | `repo` | nothing |
| Your organizations and their repositories | member | `read:org` | an organization that has not blocked QUILL (Chapter 10) |
| Projects | read on the project | `project` | nothing |
| Your gists | signed in | `gist` | nothing |
| Your keys | signed in | `admin:public_key`, `admin:gpg_key`, `admin:ssh_signing_key` | nothing |
| Your billing and usage | signed in | `user` | nothing |
| Your packages | signed in | `read:packages` | nothing |
| Insights: Health Snapshot | read | `repo` | your opt-in, in Workbench Options, Privacy |

## Issues, pull requests and discussions

| Part | Role | Also needs |
| --- | --- | --- |
| Comment, react, open an issue | signed in | nothing |
| Labels, assignees, milestones, issue type, issue fields, sub-issues | triage | issue types and issue fields need an organization that has them |
| Close or reopen | whatever GitHub says this account may do; the author of an issue may close it | nothing |
| Pin an issue | triage | nothing |
| Lock a conversation, transfer an issue | write | nothing |
| Delete an issue | admin | nothing |
| Review a pull request, re-request a review | write to request; anyone signed in may review | approving your own needs a second account (Act As) |
| Merge, auto-merge, merge queue | write, and whatever the branch's rules ask | a merge queue needs a repository with a merge queue rule |
| Discussions: reply, upvote, vote | signed in | Discussions turned on for the repository |
| Discussions: close or reopen | triage | nothing |
| Assign to Copilot, Ask Copilot to Review, agent tasks | write | a Copilot plan with the cloud agent |

## Code, releases and Actions

| Part | Role | Also needs |
| --- | --- | --- |
| Make a branch or a tag | write | a protected branch refuses what its rules forbid |
| Delete a branch, a tag or a label | write | the default branch is never deleted |
| Make and edit releases, upload files | write | an immutable release cannot be changed after it is published |
| Delete a release | push | nothing |
| Re-run, cancel and delete runs, run a workflow by hand | write | a workflow with a manual trigger, to run one by hand |
| New and edit a workflow | write | the `workflow` scope |
| Approve a deployment, approve a run from a fork | write | nothing |
| Environments: secrets, variables, protection rules, branch policies | admin | nothing |
| Self-hosted runners | admin; owner for an organization's | nothing |
| Codespaces | signed in, with access to the repository | Codespaces on your account or organization; costs may apply |
| Delete a package or a version | signed in, admin on the package | `delete:packages` |

## Repository settings and security

| Part | Role | Also needs |
| --- | --- | --- |
| Repository settings, branch protection | admin | nothing |
| Webhooks, deploy keys, autolinks | admin | nothing |
| Collaborators, access templates, bulk access changes | admin | nothing |
| Dismiss or reopen an alert | write | the `security_events` scope, and the scanning turned on for the repository |
| Allow a blocked secret | write | a real blocked push, and its placeholder id |
| Security advisories | admin | nothing |
| Transfer a repository | admin | you type its name |
| Delete a repository | admin | `delete_repo`, and you type its full name |

## Organizations, teams and access

| Part | Role | Also needs |
| --- | --- | --- |
| Accept an invitation or a membership | signed in | nothing |
| New team | member, where the organization allows it | nothing |
| Delete a team | owner | nothing |
| Members, outside collaborators | owner | QUILL refuses a change that would leave nobody to manage it |
| Organization roles and rulesets | owner | custom roles depend on the organization's plan |
| Dependabot's repository access, custom properties, fork settings | owner | nothing |
| Organization runners | owner | nothing |
| Organization webhooks | owner | `admin:org_hook` |
| Access Review, Security Overview | member, to read what GitHub shows you | parts GitHub will not show you are said, never counted as none |

## Enterprise Server

An account on a GitHub Enterprise Server reaches the same parts, if that
server's GitHub has them. When it does not, QUILL says "This server's GitHub
does not have" that part, with the server's name and version, and sends
nothing more for it. Enterprise accounts, and administering the server
itself, are not part of the Workbench.

## Outside GitHub

Two commands read something other than GitHub, and both say so first:

- **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) reads
  www.githubstatus.com, only when you ask.
- **Use GitHub CLI Sign-In...** asks the `gh` program on your computer for
  its sign-in. Nothing leaves your computer for it.

Chapter 10 has the full list of what goes over the network.

---

- Previous: [Chapter 14: GitHub in QUILL Lite](lite-github-guide-14-quill-lite.html)
- [Contents](lite-github-guide.html)
