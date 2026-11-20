# Chapter 10: Troubleshooting, privacy and help

## What this chapter covers

Something did not work, and you want to know why and what to do. QUILL never
answers with a bare error code. When GitHub says no, or QUILL holds a change
back, you hear one sentence that says what it was trying to do, why it could
not, and usually what to do next.

This chapter collects those sentences, grouped by when you meet them, with
the reason behind each and the fix. Then it covers using a token instead of
signing in, says exactly what the Workbench sends over the network, and how
to reach a person.

By the end you should be back at work, and know whether the problem was
GitHub, your account or the Workbench.

## Before you start: four quick checks

Most problems are one of these:

1. **Are you signed in, and as whom?** `Alt+9` in the Workbench says the
   account, and whether you are signed in at all. A guest only reads.
2. **What is this account's Workbench level?** `Alt+5` says what you can do
   here. An account set to Read Only or Organize is held back on purpose; see
   "Held back by the Workbench", below.
3. **Is Dry Run on?** The Account cell of the status bar says "Dry Run:
   nothing is sent" while it is. `Ctrl+Alt+D` turns it off.
4. **Is it GitHub?** **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) says
   whether GitHub itself is having trouble. See "Is it GitHub, or is it me?",
   below.

## How a refusal sounds

Most refusals have two parts: what QUILL was trying to do, and why it could
not. "Could not re-run the failed jobs. Access denied. GitHub refused this
request: check the token permissions and its organization SSO authorization."
When GitHub gave a reason of its own, QUILL adds it after "GitHub said:".

Nothing is half-done. When a command is refused, nothing was changed on
GitHub, and anything you had typed, such as a comment, a review or a new
issue, is still on your computer.

`F9` says the last result again, and `Shift+F9` explains it: what it means,
and what you might do next.

## The refusals, one by one

The sentences come in three groups, by who said no:

- [Held back by the Workbench](#held-back-by-the-workbench): QUILL stopped
  the change itself, because of the account's level, Safe Mode, Dry Run or a
  check on another account. Nothing was sent.
- [Connecting and signing in](#connecting-and-signing-in): adding an
  account, a token or a server.
- [When GitHub refuses](#when-github-refuses): GitHub received the request
  and said no.

## Held back by the Workbench

These sentences come from QUILL, not GitHub. Nothing was sent.

### "Cannot ...: it needs Full in the Workbench, and this account is Organize"

Each account has a Workbench level: **Read Only**, **Organize** or **Full**.
It limits what the Workbench may change with that account, whatever GitHub
would allow. Organize allows organizing and comments, such as labels,
reactions and closing issues, but not access, settings or deleting. The full
sentence ends "Account, Roles and Access, Workbench Level for This Account
changes it." Do that if you meant to make the change; Chapter 13 explains the
levels.

On a Properties sheet the same rule shows as a sentence beside the field,
such as "This account is set to Organize in the Workbench, which allows
organizing and comments, not access, settings or deleting."

### "This account is read only in the Workbench."

The account is set to Read Only, so no command changes anything on GitHub
with it. **Account > Roles and Access > Workbench Level for This Account...**
changes it.

### "QUILL is in Safe Mode, so the Workbench changes nothing on GitHub."

In Safe Mode every account is Read Only until QUILL is started normally. A
command refused this way says "and QUILL is in Safe Mode, which keeps every
account Read Only until QUILL is started normally." Workbench Options cannot
change that; restarting QUILL normally does.

### "GitHub item browsing is disabled in Safe Mode."

The full sentence ends "Restart QUILL normally to browse a repository." QUILL
started in Safe Mode, which keeps GitHub's network services off, so the
Workbench does not open. Restart it normally.

### "Dry run: QUILL would send ... Nothing was changed."

Dry Run is on (`Ctrl+Alt+D`, on the Tools menu). Every command still asks and
previews, then stops at the moment it would change GitHub and says what it
would have sent. Press `Ctrl+Alt+D` again to send for real. Chapter 12 has
more.

### "Cannot act as ...", from Act As Another Account

**Act As Another Account...** sends one action as another of your signed-in
accounts. Before it sends, QUILL asks GitHub whose that account's saved token
is, and holds the action to that account's own Workbench level.

- "Cannot act as kelly-test on github.com: its saved token now belongs to
  someone-else, so nothing was sent. Sign in again as kelly-test from Manage
  GitHub Accounts." The token was replaced, or now belongs to a different
  login. Sign that account in again.
- "Cannot act as kelly-test on github.com: GitHub did not say whose its saved
  token is, so nothing was sent." GitHub did not answer. Try again, or sign
  the account in again.
- A sentence starting "Cannot approve this pull request as kelly-test: it
  needs ..." means the other account's level does not allow it. Change that
  account's level, not yours.
- "Act As needs a second signed-in account: Account, Manage GitHub Accounts
  adds one."

### Compare Accounts

**Compare Accounts...** shows two of your accounts side by side, each as
GitHub answered that account's own token.

- "Compare Accounts needs two signed-in accounts: Account, Manage GitHub
  Accounts adds another."
- "Cannot compare these: they are on different servers, and a repository
  lives on one." One account is on github.com and the other on a GitHub
  Enterprise Server.
- "The token saved for jeff now belongs to someone-else, so nothing is shown
  for jeff." QUILL checks whose each token is before it shows anything, so
  one account's access never appears under another's name. Sign that account
  in again.

### "Open a repository first. Ctrl+L opens one by name or link."

The command works on one repository and you are not in one. Go to a
repository in the tree, or press `Ctrl+L` and type `owner/name`.

## Connecting and signing in

### "The GitHub token is invalid or expired."

The full sentence ends "Add a valid token or switch accounts." Your token has
reached its expiry date, or was cancelled on GitHub, perhaps because QUILL was
revoked under Authorized OAuth Apps. Open **Manage GitHub Accounts...**
(`Ctrl+Shift+K` in the Workbench), remove the old account, and choose **Sign
In with GitHub...** again. If you added the account with a token, you can make
a new one instead: see "Advanced: using a token", below.

### Sign In with GitHub: "That code expired before it was used."

The full sentence ends "Nothing was saved." A code from Sign In with GitHub
lasts about fifteen minutes. Choose **Sign In with GitHub...** again, and type
the new code on GitHub's page. You never retype an old one: each try gets a
fresh code, already on the clipboard.

### Sign In with GitHub: the sign-in was declined

Somebody chose Cancel on GitHub's approval page instead of Authorize. Nothing
was saved. Choose **Sign In with GitHub...** again if that was a slip.

### Sign In with GitHub: "GitHub did not give a sign-in code."

The full sentence ends "Check the connection and try again." QUILL could not
reach github.com. Check your connection, and any proxy or firewall that might
block it. If your network will not let QUILL reach GitHub's sign-in page,
**Add Token (Advanced)...** still works wherever the Workbench itself does.

Sign In with GitHub is for github.com only. For a GitHub Enterprise Server,
make a token on that server and add it with **Add Token (Advanced)...**, or
use the GitHub CLI's sign-in.

### Use GitHub CLI Sign-In: what it can say

**Use GitHub CLI Sign-In...**, in Manage GitHub Accounts, adds the account the
GitHub CLI (`gh`) is already signed in to. It can say:

- "QUILL did not find the GitHub CLI (gh). Sign In with GitHub works without
  it." Install the CLI, or use Sign In with GitHub.
- "The GitHub CLI is not signed in to github.com. Run gh auth login there
  first, or use Sign In with GitHub."
- "The GitHub CLI answered with something that is not a GitHub token."

When it works, QUILL names the account and server and asks before it keeps
its own copy. Signing out of the CLI later does not sign QUILL out.

### "GitHub did not confirm an account for that token. Nothing was saved."

From **Add Token (Advanced)...**: QUILL asks GitHub who a token belongs to
before it keeps it, and GitHub did not say. The token is mistyped, expired,
or made on a different server from the one under **GitHub server**.

### A GitHub Enterprise Server name is refused

When you type a server under **GitHub server**, QUILL can say:

- "A GitHub server is reached over HTTPS only."
- "Type the server's name only, such as github.example.com, without a path."
- A sentence ending "is not a server name QUILL can reach."

Type the server's name alone, as your administrator gives it.

### An organization's repositories are missing after Sign In with GitHub

Some organizations stop apps from seeing their repositories until an owner
approves each app. Your own repositories show up, and the organization's are
missing or refused, even though you are a member.

The fix is a one-time approval of QUILL for that organization. On GitHub,
open your settings, then **Applications**, then **Authorized OAuth Apps**,
then QUILL (or QUILL Lite). Beside the organization, choose **Request**.
GitHub emails the organization's owners, and once one of them approves, the
repositories appear the next time you refresh. If you are an owner yourself,
the button says **Grant** and works at once. You only ask once per app and
organization.

If the organization would rather not approve apps, a token still works: see
"Advanced: using a token", below.

### "Write actions need a signed-in GitHub account"

The full sentence ends "this session is read-only." Some commands say "To
comment you need a signed-in GitHub account" instead. You are working as a
guest, so the Workbench only reads. Sign in with **Manage GitHub
Accounts...** (Chapter 1): in the Workbench it is **Account > Manage GitHub
Accounts...** (`Ctrl+Shift+K`); in QUILL it is also on **File > Open from
Remote**, and in QUILL Lite on **File** (`Alt+F`, then `H`).

### The GitHub menus are missing in QUILL

GitHub Remote Access is part of the Developer profile and is off in the
others. Press `Alt+Shift+P` and choose Developer, or turn on GitHub Remote
Access alone in **Profiles and Features...**. **Help > Why Don't I See a
Feature?** explains any missing command.

## When GitHub refuses

### "Access denied. GitHub refused this request"

The full sentence goes on "check the token permissions and its organization
SSO authorization." GitHub knows who you are, but will not let this token do
this. One of three things is usually true:

- **The token lacks a permission or scope.** When GitHub names what it
  needed, QUILL says it: "GitHub says it needs the token permission
  contents=write." for a fine-grained token, or "GitHub accepts the scope repo
  for it." for a classic one. You cannot add a permission to a token from
  QUILL: edit the token on GitHub, or sign in with GitHub instead. An account
  added with Sign In with GitHub has every scope the Workbench uses, so this
  usually means a token you added yourself. **Account > GitHub Permissions...**
  (`Ctrl+Shift+P`) lists every permission and whether you have it.
- **Your account lacks permission on GitHub.** Only people with write access
  can merge, rerun or label, and only administrators can rename, archive or
  change visibility. **Account > Roles and Access > My Access Here...** says
  your role here and where it comes from. Ask a maintainer.
- **The organization needs single sign-on.** See the next section.

Traffic in Insights is a special case. It needs push access, and QUILL says so
in plain words while still showing the contributors.

### "GitHub requires organization SSO authorization for this token."

The full sentence ends "In your GitHub token settings, authorize it for the
organization, then try again." The organization signs its members in through
its own system, and your token has not been authorized for it yet. On GitHub,
open your personal access tokens, choose **Configure SSO** beside the token,
and authorize it for the organization. The token keeps working everywhere else
in the meantime.

### "GitHub could not find it, or this account cannot see it."

The full sentence ends "Refresh the list; it may already be gone." Either the
thing really is gone, perhaps deleted or transferred, or it is private and
this account cannot see it. GitHub answers both the same way, on purpose, so
that private repositories cannot be discovered by guessing. Check the account
with `Alt+9`, and that the token can read private repositories if this one is
private.

### "This server's GitHub does not have ..."

Only on a GitHub Enterprise Server. The sentence names the server and, when
QUILL knows it, its version: "This server's GitHub does not have this, or this
account cannot see it: GitHub Enterprise Server at github.example.com, version
3.12, answered 'not found'. An older server lacks some of what GitHub.com has;
its administrator can say which version it runs." The feature is newer than
your server. Ask the administrator whether an upgrade is planned, or do it on
the server's own pages.

### "GitHub rate-limited this request."

The full sentence ends "Wait before retrying." You have used up an allowance,
or sent many requests close together. Press `Ctrl+Shift+L` to hear how much is
left and when it resets, or `Alt+6` to hear it in one line. Signed out you get
far fewer requests, so signing in is often the fix.

Two related sentences:

- "GitHub asked QUILL to wait 60 seconds." is a short pause GitHub asks for
  after a burst of requests. QUILL waits by itself and stops sending until the
  time is up. You hear it once.
- "GitHub API rate limit reached. Retry after" a number of seconds means the
  hourly allowance is gone. It comes back at the reset time the readout gives.

### "GitHub reported a conflict" and "GitHub refused the request"

A conflict means the thing changed while you were looking at it: someone else
merged, closed or edited it. Refresh (`F5`) and try again.

"GitHub refused the request" with a reason means GitHub will not do this in
the current state, such as rerunning the failed jobs of a run where nothing
failed. The reason that follows is GitHub's own.

### "GitHub had a server error"

The sentence gives the code, such as "(HTTP 502)", and ends "Wait a moment and
retry." The problem is at GitHub's end. Check GitHub's status, below.

### "GitHub redirected the request; QUILL did not follow it"

The sentence ends "so your token stayed on api.github.com" (or on your
Enterprise Server). QUILL never carries your token to another address. Use
**Open on GitHub** (`Shift+Enter`) for that item instead.

### A file shows no text

The Workbench shows text only for text files up to 1 MB, the most GitHub sends
this way, and says which rule a file broke. Open it on GitHub, or download it
there.

## Is it GitHub, or is it me?

When GitHub is slow or failing, the Workbench's errors can look like your own
mistake. **Help > GitHub Service Status...** (`Ctrl+Alt+F1`) reads GitHub's
public status page, www.githubstatus.com, and says what it says: "GitHub
says: All Systems Operational.", or which parts are slow or down, and any
incident GitHub is working on, with its latest update.

The first time, it asks before reading the page. If the page cannot be read,
you hear "QUILL could not read GitHub's status page" and why. The command is
greyed in Safe Mode.

## When the help itself is wrong

If a help sentence, a step in this book or a tutorial was wrong, missing or
hard to follow, tell us. In the Workbench's tree, open **Help and Learning >
Ask a Person**, and press Enter on **Report a Help Problem**. It opens a
message in your own email, already saying where you were and the last thing
the Workbench said, for you to change and send. The Workbench sends nothing,
and no token or password is ever in it.

## Advanced: using a token

Sign In with GitHub is the way to connect, and most people never need anything
else. A token is a long code you make yourself on GitHub's website and paste
into QUILL. It's worth the trouble in a few cases:

- **You want QUILL to reach only a few repositories.** A fine-grained token
  can be limited to the repositories you pick, and to only the things you
  allow in them.
- **Your organization blocks sign-in apps** and won't approve QUILL, but
  still lets its members use tokens.
- **Your organization issues you a token** and asks you to use that one.
- **Your account is on a GitHub Enterprise Server.** Sign In with GitHub is
  for github.com only.
- **Your network blocks GitHub's sign-in page**, github.com/login/device, but
  lets the Workbench itself through.

### Making a token

1. Open github.com, or your Enterprise Server, in your browser and sign in.
2. Go to your profile settings, then **Developer settings**, then
   **Personal access tokens**.
3. For a token limited to a few repositories, choose **Fine-grained tokens**,
   then **Generate new token**, and pick the repositories and permissions.
   Otherwise choose **Tokens (classic)**, then **Generate new token
   (classic)**, and check the scopes you need. Chapter 1 lists the scopes and
   what each one does.
4. Give it a name you'll recognise, such as "QUILL on my laptop", and an
   expiry date.
5. Generate the token and copy it. GitHub shows it only once.

Some parts of GitHub, the notifications inbox among them, don't accept
fine-grained tokens. If you need those, use a classic token, or sign in with
GitHub.

If your organization uses single sign-on, there is one more step. On GitHub's
token page, choose **Configure SSO** beside the token and authorize it for the
organization. Until you do, GitHub refuses the organization's repositories
even though the token is fine everywhere else.

Not sure which scopes to give it? **Account > Roles and Access > Least
Privilege Advice...** lists the smallest scopes, fine-grained permissions and
Workbench level that cover what QUILL saw this account do. Chapter 13 has
more.

### Adding it to QUILL

Open **Manage GitHub Accounts...** and choose **Add Token (Advanced)...**. The
**Add GitHub Token** window has two fields:

- **Personal access token:** paste the token.
- **GitHub server:** `github.com`, or your GitHub Enterprise Server's name,
  such as `github.example.com`. The token is only ever sent to this server.

Press **Connect**. QUILL asks GitHub who the token belongs to before it keeps
it. When GitHub confirms it, you hear "Added and switched to GitHub account"
and your GitHub username.

The same window has **Continue Anonymously** for working as a guest, and
**Cancel**. None of its buttons has an access key, so Tab to the one you want.

To stop using a token, remove the account in Manage GitHub Accounts, then
delete the token on GitHub's token page. Removing it in QUILL doesn't cancel
it on GitHub.

### When QUILL suggests signing in instead

If you added an account with a classic token that can do a lot, such as one
with the `repo` scope, QUILL mentions it once, the next time you open Manage
GitHub Accounts: "This account uses a token. Sign In with GitHub is easier to
keep up to date." Then it asks whether to sign in with GitHub now. Choose
**Yes** to go straight to Sign In with GitHub. Choose **No** and nothing
changes: the token keeps working, and QUILL doesn't ask again for that
account. It never asks about an account you signed in with, or about a
fine-grained token, since that's the kind people choose on purpose.

### When a token is about to expire

Tokens you make yourself usually have an expiry date, and GitHub tells QUILL
when it is. If the active account's token expires within seven days, QUILL
says so the first time the Workbench talks to GitHub that day, for example
"Your GitHub token for your-name expires in 3 days." If it has already
expired, you hear "Your GitHub token for your-name has expired." Either way
it's said at most once a day, and it also goes into **Notifications**, where
opening it takes you to Manage GitHub Accounts. From there, sign in with
GitHub, or add a new token.

QUILL Lite does all of this the same way.

## Privacy: what goes over the network

The Workbench talks to GitHub, and only when you ask it to. Two other
addresses are read, each only when you choose the command that reads it.

- **Before the first connection** QUILL asks your permission, once (Chapter
  1).
- **Requests go to GitHub's own servers**: `api.github.com` for nearly
  everything, and `uploads.github.com` when you upload a release file. An
  account on a GitHub Enterprise Server talks to that server only, and its
  token is never sent anywhere else. Connections are encrypted, and QUILL
  refuses to follow a redirect to any other address while carrying your
  token.
- **Signing in** uses github.com's own sign-in page and code, with QUILL's
  public app id. Your password never passes through QUILL.
- **Downloads** of logs and artifacts are handed by GitHub to a short-lived
  address elsewhere. QUILL fetches those without your token.
- **Compare Accounts and Act As** send each account's own token to that
  account's own server, and nowhere else.
- **GitHub Service Status** reads www.githubstatus.com, after asking the first
  time. It sends nothing about you, your accounts or your repositories.
- **Links opened in your browser** never carry your token.
- **The GitHub CLI** uses its own sign-in, never QUILL's token (Chapter 9).
  Use GitHub CLI Sign-In reads the CLI's sign-in once, after asking, and
  keeps QUILL's own copy.
- **AI** is used only where you ask for it, such as Summarize Discussion. It
  sends the text to the AI you chose, after the same questions as every AI
  feature.
<!-- PR#1975 -->
- **Help > Ask How...** (`Alt+Shift+A`) sends your question and the
  Workbench's own help text to the AI you chose, and nothing about your
  repositories. It is greyed without an AI and in Safe Mode.

What stays on your computer and never goes to GitHub: your token (in the
operating system's secure store), each account's Workbench level, your pins
and favorites, where you left off, your local drafts and pending review
comments, your saved searches, access templates, Change History, the
attention queue's settings and filters, and the copies of earlier answers
QUILL keeps so that unchanged reloads cost nothing.

Safe Mode switches all of it off.

## Getting help

If something here does not work the way this book says, or you are stuck,
write to a person. Support is run by Community Access, at
**support@community-access.org**. A real person reads every message and
replies by email. Nothing you send is posted on GitHub or anywhere else in
public.

The quickest way to write is **Help > Get Help from Support...**
(`Ctrl+Alt+F2`), in both editors. It fills in your app's version and your
screen reader for you, and opens your own mail program with the message
written. Nothing is sent until you send it from there.

It helps to say:

- which app and version you are using, and which screen reader;
- where in the Workbench you were (`Alt+1` says it), and what you pressed;
- what QUILL said, word for word if you can (`F9` says it again); and
- what you expected instead.

---

- Previous: [Chapter 9: Codespaces and the GitHub CLI](github-guide-09-codespaces-and-the-cli.html)
- Next: [Chapter 11: Keyboard reference](github-guide-11-keyboard-reference.html)
- [Contents](github-guide.html)
