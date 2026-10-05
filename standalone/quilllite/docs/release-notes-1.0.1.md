# QUILL Lite 1.0.1

*Released September 25, 2026.*

Welcome to QUILL Lite 1.0.1. This small update gets free AI help connecting on
the Windows 10 computers where it would not, and tells you clearly what went
wrong if a connection ever fails. Nothing else changes, and everything you have
is kept.

## AI help connects on every computer

On some Windows 10 computers, AI help would not connect. You pressed Connect,
it got as far as fetching your code, and then it said QUILL Lite "could not
reach the internet", even though your internet was fine.

Before QUILL Lite talks to its free AI service, it checks that the service is
really who it says it is. Your web browser makes the same check before it
shows you a padlock. On some computers, Windows had not yet fetched what it
needed for that check, so QUILL Lite stopped before sending anything, which
was the safe thing to do, and then blamed the internet.

Now QUILL Lite carries what it needs for the check itself, so connecting works
on those computers. The check is just as strict as before, and a connection
that cannot be checked is still refused.

## When a connection fails, it tells you why

Instead of one message for everything, there are now four, so you know which
of these happened:

- the service could not be confirmed as genuine,
- the service's address could not be found,
- the connection was refused,
- the service did not answer in time.

Each message names the service and ends with the reason Windows gave. If you
send one of these messages to support, we can tell straight away what
happened. In every case, nothing was sent and none of your allowance was used.

If someone helping you asks for an error code, these are the new ones:

- **QUILL-AI-GATEWAY-CERTIFICATE**: the service was reached but could not be
  confirmed as genuine. The usual cause is security software, or a work
  network that looks inside secure connections.
- **QUILL-AI-GATEWAY-UNREACHABLE**: the service was not reached. The
  connection was refused, cut off, or got no answer in time.
- **QUILL-AI-GATEWAY-OFFLINE**: the service's address could not be found. This
  computer is offline, or cannot look up addresses right now.

## Getting it

1. Choose **Help > Check for Updates** (**Ctrl+Alt+U**), then Update.
2. Or download QuillLite-Setup-Shared-1.0.1.exe to install or update.
3. Or, for a portable copy, download QuillLite-Portable-1.0.1.zip and unzip it
   over the copy you have.

Your settings, your recovered work and your AI connection are all kept.

## Where to learn more

The QUILL Lite User Guide, in the Start menu beside QUILL Lite, has a chapter
on AI help that walks you through connecting. In the app, **Help > Tutorials**
(**Ctrl+Alt+F1**) has a lesson called Asking a question about a document.

If you get stuck, choose **Help > Get Help from Support** (**Ctrl+Alt+F2**),
or write to support@community-access.org. A person at Community Access reads
every message.
