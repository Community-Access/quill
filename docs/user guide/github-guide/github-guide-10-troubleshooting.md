# Chapter 10: Troubleshooting, privacy and help

## What this chapter covers

When GitHub says no, QUILL tells you why in a sentence and what to do next.
This chapter lists the sentences you are most likely to hear, what each one
means and how to fix it. Then it covers using a token instead of signing
in, says exactly what the workbench sends over the network, and how to get
help from a person.

## How a refusal sounds

Most refusals have two parts: what QUILL was trying to do, and why it could
not. "Could not re-run the failed jobs. Access denied. GitHub refused this
request: check the token permissions and its organization SSO authorization."
When GitHub gave a reason of its own, QUILL adds it after "GitHub said:".

Nothing is half-done. When a command is refused, nothing was changed on
GitHub, and anything you had typed, such as a comment, a review or a new
issue, is still on your computer.

## The refusals, one by one

### "The GitHub token is invalid or expired."

The full sentence ends "Add a valid token or switch accounts." Your token has
reached its expiry date, or was cancelled on GitHub, perhaps because QUILL was
revoked under Authorized OAuth Apps. Open **Manage GitHub Accounts...**,
remove the old account, and choose **Sign In with GitHub...** again. If you
added the account with a token, you can make a new one instead: see
"Advanced: using a token", below.

### "Access denied. GitHub refused this request"

GitHub knows who you are, but will not let this token do this. One of three
things is usually true:

- **The token lacks a scope.** For example, a token without `repo` cannot
  write to a private repository, and one without `delete_repo` cannot delete
  one. Chapter 1 lists the scopes. An account added with Sign In with GitHub
  has every scope the workbench uses, so this usually means a token you added
  yourself. You cannot add a scope to a token from QUILL: edit
  the token on GitHub, or sign in with GitHub instead.
- **Your account lacks permission.** Only people with write access can merge,
  rerun or label, and only administrators can rename, archive or change
  visibility. Ask a maintainer.
- **The organization needs single sign-on.** See the next section.

Traffic in Insights is a special case. It needs push access, and QUILL says so
in plain words while still showing the contributors.

### "GitHub requires organization SSO authorization for this token."

The organization signs its members in through its own system, and your token
has not been authorized for it yet. On GitHub, open your personal access
tokens, choose **Configure SSO** beside the token, and authorize it for the
organization. Then try again. The token keeps working everywhere else in the
meantime.

### Sign In with GitHub: "The code expired before it was used."

A code from Sign In with GitHub lasts about fifteen minutes. Close the window,
choose **Sign In with GitHub...** again, and type the new code on GitHub's
page. You never have to retype an old one: each try gets a fresh code, already
on the clipboard.

### Sign In with GitHub: "The sign-in was declined on GitHub's page."

Somebody chose Cancel on GitHub's approval page instead of Authorize. Nothing
was saved. Choose **Sign In with GitHub...** again if that was a slip.

### Sign In with GitHub: "GitHub did not give a sign-in code."

QUILL could not reach github.com. Check your connection, and any proxy or
firewall that might block it, then try again. If your network will not let
QUILL through at all, **Add Token (Advanced)...** still works wherever the
workbench itself does.

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
organization, however many times you sign in.

If the organization would rather not approve apps, a token still works: see
"Advanced: using a token", below.

### "GitHub could not find it, or this account cannot see it."

The full sentence ends "Refresh the list; it may already be gone." Either the
thing really is gone, perhaps deleted or transferred, or it is private and
this account cannot see it. GitHub answers both the same way, on purpose, so
that private repositories cannot be discovered by guessing. Check that you are
using the right account (`Manage GitHub Accounts...` in QUILL), and that the
token has the `repo` scope if the repository is private.

### "GitHub rate-limited this request."

You have used up an allowance, or sent many requests close together. Press
`Ctrl+Shift+L` to hear how much is left and when it resets. Signed out you get
far fewer requests, so signing in is often the fix.

Two related sentences:

- "GitHub asked QUILL to wait 60 seconds." is a short pause GitHub asks for
  after a burst of requests. QUILL waits by itself and stops sending until the
  time is up. You hear it once.
- "GitHub API rate limit reached. Retry after" a number of seconds means the
  hourly allowance is gone. It comes back at the reset time the readout gives.

### "GitHub reported a conflict" and "GitHub refused the request"

A conflict means the thing changed while you were looking at it: someone else
merged, closed or edited it. Refresh and try again.

"GitHub refused the request" with a reason means GitHub will not do this in
the current state, such as rerunning the failed jobs of a run where nothing
failed. The reason that follows is GitHub's own.

### "GitHub had a server error"

The problem is at GitHub's end. Wait a moment and try again. GitHub keeps a
status page at `githubstatus.com`.

### "Write actions need a signed-in GitHub account"

You are working as a guest, so the workbench only reads. Sign in with
**Manage GitHub Accounts...** (Chapter 1): in QUILL it's on File > Open from
Remote, and in QUILL Lite it's on File (`Alt+F`, then `H`).

### The GitHub menus are missing in QUILL

GitHub Remote Access is part of the Developer profile and is off in the
others. Press `Alt+Shift+P` and choose Developer, or turn on GitHub Remote
Access alone in **Profiles and Features...**. **Help > Why Don't I See a
Feature?** explains any missing command.

### "GitHub item browsing is disabled in Safe Mode."

QUILL started in Safe Mode, which keeps every GitHub window closed. Restart it
normally.

### A file shows no text

Repository Files shows text only for UTF-8 text files up to 1 MB, and says
which rule a file broke. Open it on GitHub, or download it there.

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
- **Your network blocks GitHub's sign-in page**, github.com/login/device, but
  lets the workbench itself through.

### Making a token

1. Open github.com in your browser and sign in.
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

### Adding it to QUILL

Open **Manage GitHub Accounts...** and choose **Add Token (Advanced)...**. The
**Add GitHub Token** window has one field, **Personal access token**. Paste
the token and press **Connect**. QUILL asks GitHub who the token belongs to
before it keeps it, so a mistyped or expired token is turned away with
"GitHub did not confirm an account for that token. Nothing was saved." When
GitHub confirms it, you hear "Added and switched to GitHub account" and your
GitHub username.

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
changes: the token keeps working, the window opens as usual, and QUILL doesn't
ask again for that account. It never asks about an account you signed in with,
or about a fine-grained token, since that's the kind people choose on purpose.

### When a token is about to expire

Tokens you make yourself usually have an expiry date, and GitHub tells QUILL
when it is. If the active account's token expires within seven days, QUILL
says so the first time the workbench talks to GitHub that day, for example
"Your GitHub token for your-name expires in 3 days." If it has already
expired, you hear "Your GitHub token for your-name has expired." Either way
it's said at most once a day, and it also goes into **Notifications**, where
opening it takes you to Manage GitHub Accounts. From there, sign in with
GitHub, or add a new token.

QUILL Lite does all of this the same way.

## Privacy: what goes over the network

The workbench talks to GitHub and to nobody else, and only when you ask it to.

- **Before the first connection** QUILL asks your permission, once (Chapter
  1).
- **Requests go to GitHub's own servers**: `api.github.com` for nearly
  everything, and `uploads.github.com` when you upload a release file. They
  use encrypted connections, and QUILL refuses to follow a redirect to any
  other address while carrying your token.
- **Downloads** of logs and artifacts are handed by GitHub to a short-lived
  address elsewhere. QUILL fetches those without your token.
- **Links opened in your browser** never carry your token either.
- **The GitHub CLI** uses its own sign-in, never QUILL's token (Chapter 9).
- **AI summaries** in QUILL send the issue's text to the AI you chose, after
  the same questions as every AI feature. Nothing else in the workbench uses
  AI.

What stays on your computer and never goes to GitHub: your token (in the
operating system's secure store), your pins and favorites, where you left off,
your local drafts and pending review comments, your saved searches, the
attention queue's settings and filters, and the copies of earlier answers
QUILL keeps so that unchanged reloads cost nothing.

Safe Mode switches all of it off.

## Getting help

If something here does not work the way this book says, or you are stuck,
write to a person. Support is run by Community Access, at
**support@community-access.org**. A real person reads every message and
replies by email. Nothing you send is posted on GitHub or anywhere else in
public.

The quickest way to write is **Help > Get Help from Support...**, in both
apps. It fills in your app's version and your screen reader for you, and opens
your own mail program with the message written. Nothing is sent until you send
it from there.

It helps to say:

- which app and version you are using, and which screen reader;
- which window you were in, and what you pressed;
- what QUILL said, word for word if you can; and
- what you expected instead.

---

- Previous: [Chapter 9: Codespaces and the GitHub CLI](github-guide-09-codespaces-and-the-cli.html)
- Next: [Chapter 11: Keyboard reference](github-guide-11-keyboard-reference.html)
- [Contents](github-guide.html)
