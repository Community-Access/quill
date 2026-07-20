# QuillSync and QuillBeacon -- What You Can Do

A plain-language guide for the people who will use this, not the engineers
who build it. If you use a screen reader, jump by heading: each section
below is a heading.

## The short version

QuillBeacon is the hub of the QUILL family's sync: a way to save your place in
*anything* -- a web page, a
heading inside a document, a moment in a podcast, a radio station, a file,
a folder -- and find your way back to it later, with the reason you saved it
still attached.

QuillSync is how your saved places, your settings, and your notes follow you
from one computer (or device) to another -- without you babysitting it, and
without handing your data to a company you have to trust.

You do not need a password. You do not need to visit a website to sign in.
And nothing leaves your machine until you decide it should.

## What QuillBeacon lets you do

- **Save the exact place, not just the address.** A normal bookmark remembers
  a URL. QuillBeacon remembers the heading, the selected passage, the time
  point in a podcast, or the line in a document -- so "where was I?" has a
  real answer.
- **Capture from anywhere.** Save a page from your browser with one click
  (the QuillBeacon browser extension), or from inside QuillBeacon itself.
  Capture the whole page, just the text you selected, a link, the nearest
  heading, or the exact moment in a video or audio you were listening to.
- **Find it again in seconds.** Search the full text of everything you saved
  -- titles, notes, tags, the words inside a page -- with filters like
  "only podcasts," "only this collection," or "only things I haven't read."
- **Keep the reason.** Every saved item can carry a note in your own words:
  why it mattered, what you were going to do with it, who you meant to send
  it to.
- **Listen and watch.** Subscribe to podcasts, refresh for new episodes, and
  play an episode in the built-in player -- with chapters, a transcript view,
  and the ability to drop a time-point bookmark at the exact second you want
  to come back to.
- **Let the app help, never decide for you.** It can suggest tags, suggest
  related items, and summarize a long note -- but only when you ask. It never
  changes your library in the background without your action.

## What QuillSync lets you do

QuillSync is the part that makes your stuff portable across your own devices.

- **Sit down at any of your machines and it is yours.** Your saved places,
  your tags, your collections, and your notes appear on every computer you
  turn on -- not a copy, the same library.
- **Your settings travel too.** If you use more than one QUILL app (the
  editor, the radio, the podcast manager), the things you set up once --
  voices, keyboard shortcuts, your subscriptions -- can follow you between
  machines.
- **Nothing is lost to a bad change.** Every change is saved as a step in a
  history you can look at and speak aloud. If an experiment goes wrong, you
  can go back to how things were.
- **When two devices disagree, you decide.** If you edited the same note on
  two machines, QuillSync does not silently pick one. It shows you both
  versions and asks you to choose. You never have to read ugly merge markers
  -- it presents the choice in plain language.
- **Deleting is never instant and never final everywhere.** If you trash
  something on one machine, it goes to recoverable Trash on the others -- not
  a permanent destroy. You can bring it back.

## How you sign in (no password, no website)

You sign in with a magic link sent to your email. There is no password to
remember, lose, or have stolen, and no captcha to fight with a screen reader.

1. In the app, you open Sync Settings and type your email address. That is
   the only field.
2. You press "Send sign-in link." The app emails you a single, one-time link.
3. You open the email and activate the link. It opens the app directly -- not
   a web page -- and finishes signing you in on that device.
4. You name the device ("Jeff's laptop") so you can tell your devices apart
   later and remove one if you lose it.

The link works once and expires in 15 minutes. The email is plain text with
the link on its own line, so a screen reader hears it clearly.

## Across the QUILL family of apps

QuillSync is shared across the QUILL apps, so you sign in once per machine and
your world follows you. **QuillBeacon is the hub**: it is the first app to ship
sync, the home the other apps plug into, and the place where the browser
capture bridge runs. If you are wondering where to start, start in QuillBeacon.

- **QuillBeacon** -- your saved places, notes, tags, and collections. This is
  where sync lives first, and where captures from the browser extension land.
  When Beacon is set up to sync, your whole library -- every saved place, note,
  tag, and collection -- is the same on every machine you sign in on.
- **Quill** (the editor) -- your settings, keyboard shortcuts, abbreviations,
  and your Vault of notes and ideas.
- **Quill Radio** -- your favorite stations and your recording schedules, so
  the same radio is ready on every machine. Radio is the first companion app
  to follow Beacon into sync.
- **Quill Cast** (podcast publishing) -- your episode notes and what has
  already been published where, so two machines never double-publish the same
  episode.
- **Quill Pocket** (the phone app, planned) -- capture an idea by voice or
  camera on your phone and have it land in your library on the desktop, ready
  and tagged.

Each app sees only its own part of your synced data. Signing in to Quill
Radio does not let it read your Quill editor notes, and vice versa. One
account, separate spaces -- but QuillBeacon is the common front door.

## You own your data, and it stays private

- **End-to-end encrypted.** Before anything leaves your machine, it is
  encrypted with a key that comes from a passphrase only you know. A server
  breach would reveal nothing readable.
- **You choose where it lives.** You can sync through a folder you already
  trust (iCloud, OneDrive, Dropbox, a shared drive) with no account at all,
  or use the hosted QuillSync service later if you do not want to think about
  it. The folder option costs nothing and owns everything.
- **You can leave with everything.** You can export your whole library in
  open, standard formats at any time. No feature depends on a cloud copy you
  cannot take with you.
- **Sync is off until you turn it on.** Nothing is sent anywhere by default.

## What happens when a piece is not ready yet

Most of QuillBeacon and QuillSync is built and working today. The few pieces
that are still ahead are designed to fail safely -- they never break the parts
that work, and they never harm your data:

- **If the optional smarter search is not turned on**, search simply works
  the normal way. Nothing is missing; the optional piece just is not there
  until you choose to add it.
- **If the browser extension cannot reach the app** (the app is closed, or
  the bridge is off), the extension tells you plainly and saves nothing. It
  does not silently drop your captures.
- **If sync is not set up**, QuillBeacon is a fully useful single-machine app.
  Sync is an addition, never a requirement.
- **If a sync transfer is interrupted**, your library is not left half-written.
  Each change is saved as a complete step or not at all, so a crash or a lost
  connection rolls back cleanly. Before every sync the app also snapshots your
  library, so you can roll back to exactly how it was before a sync.
- **If email sending is not configured**, sign-in still works for testing --
  the link is shown to you directly -- and it never sends mail by accident.
- **If an external media player is not installed**, handing off playback falls
  back to your system's default player. You are never left with nothing.

In short: the things that are finished work; the things that are not finished
stay out of the way until they are.

## What you can do in QuillBeacon today

These are all working in the app right now:

- **Smart Collections.** Save any search as a live collection -- "all my
  podcast episodes tagged research" -- and it always reflects your current
  library, never a frozen snapshot. Find it in the sidebar under Smart
  Collections, or save one with View, then Save Search as Smart Collection.
- **Undo and bulk actions.** Select many items at once (Ctrl with arrows) and
  trash, archive, restore, favorite, tag, or delete them together. Every
  bulk action is one Undo step (Ctrl+Z), so a whole batch comes back at once,
  even a permanent delete.
- **Attachments.** Pin a file, a link, or a note to any saved item so the
  supporting material travels with the place you saved.
- **Collections and Trails.** Create and edit collections (with a parent,
  description, and sharing hint) and learning Trails -- ordered paths through
  your saved items, each step with its own note.
- **Broken-location repair.** When a saved place has shifted or gone dark,
  open Review Location Repair to see the old location and a proposed fix side
  by side, and choose: accept the fix, keep the old location, or mark it for
  later. It never silently rewrites an exact bookmark.
- **Radio.** Save a station with fallback stream addresses, or capture a
  specific program (show, host, and air time) as its own saved item.
- **Sync, fully.** Open Sync Settings to choose a folder or the hosted
  service, sign in with a magic link, and unlock your vault. Sync Now pushes
  and pulls. Sync History shows what synced and lets you roll back.
- **Accessibility settings.** Set announcement verbosity, high contrast, text
  scale, and reduced motion -- all from one dialog, saved between sessions.
- **One Preferences window.** Press Ctrl+Comma (or View, then Preferences) to
  open one hub for Accessibility, Sync, the Capture Bridge, and your Published
  Pages. Change announcement verbosity or the auto-sync interval and Apply, or
  use the buttons to open Sync Settings, run Sync Now, copy the bridge token, or
  unpublish a page.
- **Status center and tray.** A status center shows capture, sync, and
  library health at a glance. The system-tray icon lets you capture, sync, and
  show or hide the window without the full window open.
- **External player.** Hand off a podcast or radio item to VLC or mpv (with
  resume time) or your system player when the built-in player is unavailable.
- **Attachments, in the UI.** Select a saved item and press Edit, then
  Attachments (Ctrl+Shift+E) to add a file, a URL, or a note, view it, or
  remove it. Attachments stay on your machine; they are not synced as blobs.
- **Trails you can step through.** Trails now appear in the sidebar with their
  progress (3 of 5, for example). Pick one to open a step-through view: read
  the note for the current step, open the item, mark it complete, and move
  Previous or Next. Your place is saved, so you can leave and come back.
- **Smart Collections you can edit.** Tools, then Smart Collections Manager
  lets you rename or re-query a saved search, or delete one. Deleting a Smart
  Collection never deletes the bookmarks it matched.
- **More bulk actions.** Select many items and use Edit, then Bulk Add to
  Collection (Ctrl+Shift+O) or Bulk Remove Tag (Ctrl+Shift+V). Each is one
  Undo step.
- **Health rechecks.** Tools, then Revalidate Health re-checks whether your
  saved links are still reachable. Local files are checked against your disk;
  web links are checked over the network only if you allow it, and only after
  you confirm. Broken links are marked so you can review or repair them.
- **Sync, smarter.** Sync only sends what changed (and any deletions), not the
  whole library every time. If two devices edit the same note, the conflict
  shows up in Sync History with Use Local / Use Remote / Use Merged buttons.
  To share your encrypted library with a second device, use Sync Settings,
  then Pair Device: it exports a short code you enter on the other device,
  then unlock there with the same passphrase. Sync, then Auto Sync lets you
  set an automatic interval (off by default), and the Status Center shows how
  many new changes are waiting on the server.
- **Publish a collection to a web page.** Select a collection in the sidebar,
  then Tools, then Publish Collection (Ctrl+Shift+W) to render it as a
  self-contained, read-only, accessible web page. You get a portable HTML file
  you can open, copy, or host anywhere, plus a localhost preview link behind a
  publish token. Nothing on the page can modify your library, and Unpublish
  removes the files. It is read-only by design -- there is no sign-in, no
  capture, and no write path back into QuillBeacon.

## Getting started

1. Open QuillBeacon. Your library lives on this machine by default.
2. To capture from your browser, install the QuillBeacon extension, then in
   the app choose Tools, then Capture Bridge, and copy the token into the
   extension's Options.
3. To sync across machines, open Sync Settings, enter your email, and follow
   the magic-link sign-in. Point sync at a shared folder, or use the hosted
   service when it is available.

For the technical design and the order in which apps will gain sync, see
`Docs/PLAN-quillsync-integration.md`. This document is the user's view; that
one is the builder's view.