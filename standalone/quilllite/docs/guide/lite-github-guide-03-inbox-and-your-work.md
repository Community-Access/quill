# Chapter 3: Your inbox and your work

## What this chapter covers

GitHub sends you a notification whenever something you are part of moves. On
a busy project that is dozens a day, and the website's inbox is a long page of
links and icons. This chapter shows you how to go through it from the
keyboard: what each notification says, how to clear it, and how to keep your
place. Then it covers My Work, the attention queue that gathers everything
waiting for you, and the activity views.

All of this needs a signed-in account, because it is your inbox and your work.

**In QUILL Lite**, these views work once you sign in with **File > Manage
GitHub Accounts...** (`Alt+F`, then `H`). As a guest they say "Sign in to
GitHub for this account view."

## Opening your notifications

In QUILL, choose **Tools > Git and GitHub > GitHub > Notifications...**. Explore
GitHub opens straight at your inbox. From GitHub Items, press **Explore...**
(`Alt+E`) and choose **GitHub notifications** in **View:** (`Alt+V`).

When the inbox loads, QUILL says how many are unread, once:

- "12 unread."
- "3 unread of 40.", when you are showing read ones too.
- "No unread notifications; 40 read."
- "No notifications."

## What a notification says

Each row says, in this order, whether it is unread, why it reached you, the
repository and the title: "Unread, review requested: community-access/quill
— Fix the status bar".

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

**Selected result** holds the rest, one line each: what the subject is (an
issue, a pull request, a release, a discussion, a commit, a workflow run, a
security alert), the repository, why you got it, its state and when it last
changed, and the link.

## Opening one

Press Enter on a notification. Two things happen.

First, QUILL marks it read, the way opening it on GitHub would. It does this
quietly. The row's first word changes from Unread to Read, which you hear when
you next arrive on it.

Then it opens the notification in the best place for it:

- **A pull request** opens in the review window, on top of Explore. Close the
  review and you are back in your inbox, on the same row.
- **An issue** opens in GitHub Items, at that issue, and Explore closes.
- **Anything else**, such as a release or a workflow run, opens in your
  browser.

## Triage: Done, Unsubscribe and Mark All Read

In the notifications view, and only there, four controls appear under the
Results list:

- **Include read notifications** (`Alt+I`), a check box. Check it to see
  notifications you have already read as well. The list reloads.
- **Mark Done** (`Alt+D`) takes the selected notification out of your inbox.
  It is the same as Done on GitHub. The Delete key in the list does the same.
- **Unsubscribe** (`Alt+U`) stops notifications from that thread for good, and
  takes it out of the inbox.
- **Mark All Read** (`Alt+A`) marks everything read.

### Keeping your place

Mark Done and Unsubscribe take the row out of the list and put you on the next
one, with focus still in the list, so you can keep going: read, Delete, read,
Delete. You hear "Marked done." or "Unsubscribed from the thread." When the
last one goes, QUILL adds "No notifications left in this list."

If you reload, QUILL puts you back on the same notification, if it is still
there.

### Mark All Read

Mark All Read asks first: "Mark every notification in your GitHub inbox read,
up to when this list was loaded? Newer notifications stay unread." That second
sentence is the safety: anything that arrived after you loaded the list stays
unread, so you never clear something you have not seen.

You hear "Marked all notifications read." On a large inbox GitHub may do the
work in the background instead. Then you hear "GitHub accepted the request and
is marking them read in the background. Refresh in a minute to check."

### The context menu

Shift+F10 on a notification has the same commands, plus one more:
**Mark Notification Read**, **Mark Done**, **Unsubscribe from Thread**, and,
for the whole view, **Mark All Read...**. Mark Notification Read marks it read
without opening it.

## How often QUILL checks

GitHub tells apps how often they may check the inbox, usually once a minute,
and asks them to keep to it. QUILL does. If you reload sooner, it keeps the
list it already has, and adds to the unread count: "GitHub asks apps to check
notifications no more often than it says; this is the list from the last
check. Try again in" and the number of seconds.

When you do reload, QUILL asks GitHub only for what has changed since last
time. An unchanged inbox comes back in a moment and costs nothing from your
hourly allowance. When the allowance is running low, QUILL waits longer
between checks on its own: twice as long under a quarter left, four times as
long under a tenth.

## My Work

**My Work**, in Explore's **View:** list, is everything open that involves
you, across every repository you can see. It runs four searches and puts the
results in one list:

- **Assigned**: open issues and pull requests assigned to you.
- **Review requested**: open pull requests waiting for your review.
- **Mentioned**: where someone mentioned you.
- **Authored**: what you opened.

An item that turns up in more than one search appears once. Its details start
with the searches that found it, so you know whether it is here because you
were assigned or because you were mentioned. Each row reads the repository,
the number, the title, and whether it is an issue or a pull request.

## The attention queue

The attention queue is a shorter, sharper list: only what is waiting for you
to act. It is the view Explore opens on when you are signed in. It gathers four
kinds of work:

- **Assigned to me**
- **Review requested**
- **Mentioned**
- **Failed checks**: open pull requests whose checks failed, in the
  repositories the queue covers.

Each row names where it came from and when it last changed. QUILL remembers
when you last finished loading the queue, so the next time it can tell you
what moved: changed items say "Changed since your last visit." in their
details, and the status line adds how many changed. The first time, it says
"This is your first recorded visit."

If part of the queue could not load, perhaps because GitHub refused one of the
searches, QUILL does not pretend the list is complete. You hear the count "with
incomplete data. Check the status for details.", and the status line says
which part is missing.

### Queue Options

**Queue Options...** (`Alt+O`) opens a menu for shaping the queue. It is
available once the queue has loaded.

- **Choose Repositories...** limits the queue to up to ten repositories. Type
  them as `owner/repo`, separated by commas, or leave the box empty to search
  everything you can see.
- **Choose Categories...** picks which of the four kinds to include. Check the
  ones you want; at least one has to stay.
- **Save Current Filter...** names the current repositories and categories, so
  you can switch to them again. Each saved filter then has its own
  **Use Filter** and **Remove Filter** rows in this menu.

Filters are kept on this computer, for each account separately. None of this
changes anything on GitHub.

## Activity

Three views show what has been happening rather than what is waiting:

- **My activity feed**: events from the people you follow and the repositories
  you watch.
- **Repository activity**: recent events in the repository named in
  **Repository:**.
- **Person's public activity**: one person's public events. Type their
  username in **Person:** (`Alt+P`).

Each row reads the kind of event, the repository and who did it, such as
"Push: community-access/quill — jeff".

## A morning routine

1. Open your notifications: in QUILL, **Tools > Git and GitHub > GitHub >
   Notifications...**.
2. Listen to the unread count.
3. Arrow down. For each row, decide: read it now (Enter), clear it (Delete), or
   stop hearing about it (`Alt+U`).
4. After opening a pull request, close the review window to come back to the
   same place in the list.
5. When the inbox is clear, choose **Attention queue** in **View:** and work
   from the top.

---

- Previous: [Chapter 2: Getting around](lite-github-guide-02-getting-around.html)
- Next: [Chapter 4: Issues](lite-github-guide-04-issues.html)
- [Contents](lite-github-guide.html)
