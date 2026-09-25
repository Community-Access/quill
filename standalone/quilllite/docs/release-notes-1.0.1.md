# QUILL Lite 1.0.1 — What's New

*Released September 25, 2026.*

**A fix for AI help on some Windows 10 computers.** If Connect stopped at the
step that gets your code and said QUILL Lite "could not reach the internet" --
on a computer whose internet was working perfectly well -- this release fixes
it. Nothing else changes, and everything you have is kept.

---

## What was wrong

When QUILL Lite connects to its free AI service, it first checks the service's
security certificate, the same check your browser makes before it shows a
padlock. To make that check, a program needs a list of the organisations it
trusts to issue certificates.

QUILL Lite 1.0 used only the list Windows keeps. Windows does not keep a
complete list up front: it downloads most of those organisations the first time
Windows' own networking needs one. A computer that has never had a reason to
download the one this service uses -- often because the browser on it keeps its
own list and never asks Windows -- did not have it. QUILL Lite could not
finish the check, stopped before sending anything, and then reported the wrong
problem: that the internet could not be reached.

## What 1.0.1 does

- **Connecting works on those computers.** QUILL Lite now also trusts the list
  it ships with, so the check succeeds whether or not Windows has downloaded
  that organisation yet. The check itself is exactly as strict as before: every
  certificate is still verified, and a connection that cannot be verified is
  still refused.
- **When a connection fails, it says how.** A certificate that cannot be
  verified, an address that cannot be looked up, a connection that was refused,
  and a service that did not answer in time are now four different messages.
  Each names the service and ends with the reason Windows gave, so a message
  you pass on to us tells us straight away what happened.

New error codes, in case you are asked for one:

- **QUILL-AI-GATEWAY-CERTIFICATE**: the service was reached, but its
  certificate could not be verified. Security software or a work network that
  inspects secure connections is the usual cause now.
- **QUILL-AI-GATEWAY-UNREACHABLE**: the service was not reached -- refused, cut
  off, or no answer in time.
- **QUILL-AI-GATEWAY-OFFLINE**: the service's address could not be looked up,
  so this computer is offline or its DNS is not answering.

In every one of these cases nothing was sent and none of your allowance was
used.

---

## Getting it

Choose **Help ▸ Check for Updates** (**Ctrl+Alt+U**) and then Update, or download
**QuillLite-Setup-Shared-1.0.1.exe** to install or update, or
**QuillLite-Portable-1.0.1.zip** to unzip over a portable copy. Your settings,
your recovered work and your AI connection are all kept.
