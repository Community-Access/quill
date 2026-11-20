# Chapter 3: Your inbox and your work

## What this chapter covers

GitHub tells you whenever something you are part of moves. On a busy project
that is dozens of notifications a day, and the website shows them as a long
page of links and icons. In QUILL they are a list you work through from the
keyboard.

In this chapter you open Needs My Attention, read what each notification
says, mark it read or done, put it off for a day, and stop hearing about a
thread. You set up inbox rules for the notifications that always get the same
answer, answer an invitation, and use the lists that split your open work by
why it is yours.

By the end you will be able to clear your inbox every morning, and know where
to look for the reviews, assignments and mentions waiting on you.

All of this needs a signed-in account, because it is your own inbox and your
own work. Until you sign in, each of these places says so and names the way
in: **Manage GitHub Accounts...** (`Ctrl+Shift+K` in the Workbench). Chapter 1
shows how.

## Needs My Attention

Everything waiting on you is under **Needs My Attention**, near the top of the
Workbench's tree. `Ctrl+1` goes straight to its first place, Inbox, from
anywhere in the window, and so does `Alt+Home`. From the editor, the GitHub
menu's **Inbox** row opens the Workbench there (Chapter 2 has the GitHub
menu).

The places under it, in order:

| Place | What it holds |
| --- | --- |
| Inbox | What needs you to act: work assigned to you, review requests, mentions, and pull requests whose checks failed |
| Notifications | GitHub's own notifications, unread ones |
| Invitations | Repositories you have been invited to |
| Review Requests | Pull requests waiting for your review, or your team's |
| Assigned to Me | Issues and pull requests assigned to you |
| Mentions | Issues and pull requests where someone wrote your name |
| My Open Pull Requests | Pull requests you opened that are still open |
| My Open Issues | Issues you opened that are still open |
| My Activity Feed | What you did on GitHub lately, newest first |

When one of them is empty, its details say so and say what would fill it, so
an empty list never leaves you wondering whether it loaded.

## Reading your notifications

Arrow down the tree to **Notifications**. The list loads by itself. Press
`Tab` to move into it, or `F6` to move from pane to pane.

Each row says, in this order, whether it is unread, why it reached you, the
repository and the title: "Unread, review requested: community-access/quill",
then the title.

The reason is in words, not GitHub's code names:

- "review requested"
- "you were mentioned", or "your team was mentioned"
- "you were assigned"
- "you opened it", or "you commented"
- "you changed its state"
- "you are watching the repository", or "you subscribed"
- "a workflow run you started finished"
- "your approval was requested for a deployment"
- "security alert"
- "you were invited to the repository"
- "you were credited on a security advisory"

The details pane holds the rest, one line each: what the subject is (an
issue, a pull request, a release, a discussion, a commit, a workflow run or a
security alert), the repository, why you got it, whether it is read and when
it last changed, and its link.

**Why?**, on a notification's context menu, says the reason in a sentence and
what decides it, such as watching the repository or being on a team.

Notifications lists the unread ones. A notification you mark read leaves the
list the next time it loads.

## Opening a notification

**Enter** moves you to the details pane, so you can read the notification in
full. To act on what it is about:

- `Shift+Enter` opens it on GitHub, in your browser.
- `Ctrl+Shift+C` copies its address.
- `Ctrl+L` (**File > Open GitHub Address...**) takes an address or a number,
  such as `owner/name#42`, and goes to its place in the tree. Chapter 2 has
  more on it.

Opening a notification does not mark it read. Mark it read yourself when you
have dealt with it, as the next section shows.

## Clearing your inbox: Mark Read, Mark Done, Snooze and Unsubscribe

Each of these is on a notification's context menu (`Shift+F10` or the
Applications key), and the commonest have keys of their own:

| Command | Key | What it does |
| --- | --- | --- |
| Mark Read | `Ctrl+Q` | Marks it read, here and on GitHub. You hear "Marked read." |
| Mark Done | `Delete` | Takes it out of your inbox, the same as Done on GitHub. You hear "Marked done." |
| Unsubscribe from Thread | none | Stops notifications from that thread for good, and takes it out of the inbox. You hear "Unsubscribed." |
| Snooze for One Day | none | Notes on this computer that you have put it off until tomorrow. GitHub is not told. You hear "Snoozed here for one day. GitHub was not changed." |
| Unsnooze Locally | none | Takes the snooze off again. |
| Mark All Read in View | `Ctrl+Shift+Q` | Marks every notification in the list read. |

After Mark Read, Mark Done or Unsubscribe the list loads again.

The Workbench does not hide a snoozed notification yet: it stays in the list,
so Snooze is a note to yourself for now.

`Ctrl+.` moves to the next unread row in the list, and `Ctrl+Shift+.` to the
one before, so you can skip what you have already read.

### Mark All Read

**Item > Mark All Read in View** (`Ctrl+Shift+Q`) marks every notification in
the list read. When there are more than twenty, it asks first: "Mark all 41
notifications in this view read?" You then hear how many it marked, such as
"Marked 41 read."

### Keeping your place

When you come back to Notifications with Back (`Alt+Left`), or the list loads
again after a change, QUILL returns you to the row you left rather than the
top of the list.

## Invitations

When someone invites you to a repository, GitHub sends a notification, and
the invitation itself waits in **Needs My Attention > Invitations**. Each row
says the repository, who invited you and with what access: "octo/app: ann
invited you, write access". The details say when.

- **Enter**, or **Accept Invitation...** on the context menu, asks first, then
  joins you to the repository.
- **Decline Invitation...** asks first, then says no.

An invitation expires after a week. An expired one ends in "expired", cannot
be accepted, and can still be declined to clear it away.

An organization's invitation is different. On an organization's row,
**Your Invitation** says whether it has invited you. GitHub lets apps accept
an organization's invitation but not decline one, so it also says where on
GitHub to decline it. **Accept Membership**, on the same menu, joins you.

## Inbox rules

Some notifications always get the same answer: a Dependabot update you will
never read before it merges, a busy repository you only watch, a mention you
always want first. An inbox rule gives that answer for you as the list
arrives.

Choose **Item > Inbox Rules...** (`Ctrl+Alt+N`). The window lists your rules,
each read as a sentence, and **New Rule...** at the end. A new rule asks five
questions, one at a time:

1. **What should the rule do?** Mark it done, Mark it read, or Move it to the
   top.
2. **From which repository?** An `owner/name`, or a `*` for any part, so
   `octo/*` is every repository of `octo`. Leave it blank for any. If a
   notification was selected, its repository is already filled in.
3. **Why it came to you:** any reason, or one of GitHub's, such as "you were
   mentioned" or "review requested".
4. **What it is about:** anything, or a pull request, an issue, a discussion, a
   release, a workflow run, a commit or a security alert.
5. **Words its title must contain**, or blank for any. Dependabot's titles
   start with "Bump".

A rule needs at least one of these. One with none would act on every
notification, so QUILL will not save it.

Before saving, QUILL reads the rule back and tries it on the notifications
already loaded today: "When a notification is from octo/*, about a pull
request, with 'Bump' in its title: mark it done. It matches 3 of the 41
notifications loaded today, and would mark them done:" and their titles. Yes
saves it; No saves nothing.

From then on the rules run every time Notifications loads, before you see the
list. The first rule that fits a notification decides what happens to it.
Marking done and marking read are sent to GitHub, as if you had pressed the
keys yourself. Moving to the top only changes the order here. The status bar
then says what the rules did, such as "Inbox rules: 3 marked done, 1 moved to
the top."

To delete a rule, choose it in the Inbox Rules window and say Yes.

Rules are kept on this computer.

## How often QUILL checks

The Workbench reads Notifications when you arrive on it, and again when you
press `F5` (**View > Refresh**). Each time, QUILL asks GitHub only for what
has changed since the last read. An unchanged inbox comes back in a moment
and costs nothing from your hourly allowance.

While QUILL is open, it can also check for new notifications in the
background. **Tools > Workbench Options...** (`Ctrl+Shift+O`), on the
**Notifications and Inbox** page, sets how often, from 5 minutes to a day,
whether each check plays a short sound, and whether a new notification may
interrupt what is being said. GitHub may ask for longer between checks, and
then it gets longer. When your hourly allowance runs low, QUILL waits longer
on its own: twice as long with under a quarter left, four times as long with
under a tenth.

## The Inbox: what needs you to act

**Inbox** is the short, sharp list: only what is waiting for you to do
something. It gathers four kinds of open work, the most recently updated
first:

- **Assigned to me**
- **Review requested**, from you or from a team you are on
- **Mentioned**
- **Failed checks**: open pull requests whose checks failed

Each row's details start with where it came from, so you know whether it is
there because you were assigned or because you were mentioned. An item found
for more than one reason appears once, its details starting "Also:" and every
reason. A review asked
of a team you are on, rather than of you by name, ends in "team review
request", because someone else on the team may take it.

### Where each pull request stands

A pull request in the Inbox also says where it stands, in the same sentence
the review window opens with: "Approved, 2 checks failing, 1 open thread". It
comes after the row's name in the list, and in the details it follows the
reason the row is there.

QUILL reads every pull request's sentence in one request when the Inbox
loads. It covers the twenty newest. When there are more, the status bar says
so, such as "Summaries cover the newest 20 of 26 pull requests".

The sentence never calls a pull request ready on data it does not have. When
GitHub sent only part of the picture, it says "merge readiness unknown". When
GitHub did not answer for a pull request at all, its row says "Summary
unavailable".

If part of the Inbox could not load, perhaps because GitHub refused one of
the searches, QUILL does not pretend the list is complete. The status bar
says which part is missing.

## Your open work, split by why it is yours

The next five places under Needs My Attention are the same work split by
reason:

- **Review Requests** holds two kinds: pull requests that ask you by name,
  and those that ask a team you belong to. A team's row ends in "team review
  request". The pull request's own Properties sheet (`Alt+Enter`) names the
  team under Team reviewers. GitHub's search cannot say which team from the
  list itself. Enter on a pull request here opens its review (Chapter 5).
- **Assigned to Me**, **Mentions**, **My Open Pull Requests** and **My Open
  Issues** are what their names say, across every repository you can see.

An item that turns up for more than one reason appears once in each list it
fits. Its details start with every reason that found it.

Every list here works like any other in the Workbench: the filter box
(`Ctrl+E`) narrows it, **View > Sort By** and **View > Group By** shape it,
and **File > Export List...** (`Ctrl+Shift+X`) saves it. Chapter 13 has
filtering and grouping.

## Activity

Three places show what has been happening rather than what is waiting:

- **Needs My Attention > My Activity Feed**: what you did lately.
- **Activity**, under a repository: its recent events.
- **Activity**, under a person: their public events. Enter on a person, in
  People or anywhere else, gives them a place in the tree.

Each row reads the kind of event, the repository and who did it.

## A walk-through: clearing your inbox in the morning

You start the day with a handful of notifications. Here is the routine.

1. Open the Workbench and press `Ctrl+1`. You hear "Inbox", and how many rows
   it has. These are the things waiting on you to act.
2. Arrow down the tree to **Notifications**, and press `Tab` to move into the
   list. You hear the first row, such as "Unread, review requested:", the
   repository and the title.
3. Press `Enter` to read it in full in the details pane. Press `Shift+Tab` to
   go back to the list.
4. Decide. If you have dealt with it, press `Ctrl+Q`: you hear "Marked read."
   If it needs nothing from you, press `Delete`: you hear "Marked done." If
   you never want to hear about that thread again, choose **Unsubscribe from
   Thread** from the context menu.
5. When the list is clear, arrow down the tree to **Review Requests** and
   work from the top. Enter on a pull request opens its review.

If the same kind of notification turns up every morning, make an inbox rule
for it with `Ctrl+Alt+N`, and tomorrow it is dealt with before you arrive.

## Learn it with a guided lesson

**Help > Tutorials** (`Ctrl+F2` in the Workbench) has **Triage your inbox**,
a six-minute lesson that goes to the Inbox, looks at Review Requests, marks a
notification read, snoozes one and brings it back. Each step says what to
press and what you should hear.

---

- Previous: [Chapter 2: Getting around](github-guide-02-getting-around.html)
- Next: [Chapter 4: Issues](github-guide-04-issues.html)
- [Contents](github-guide.html)
