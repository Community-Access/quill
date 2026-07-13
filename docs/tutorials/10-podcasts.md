# Tutorial 10: Podcasts

**Goal:** subscribe to a show, organize your library into folders, download
an episode for offline listening, and control playback without ever leaving
the keyboard — QUILL's own podcast client, built on the same "one player
that outlives any dialog" idea as [Internet Radio](09-internet-radio.md).

Podcasts need a network connection to subscribe and download, and are
disabled entirely in Safe Mode. Everything below lives under **Tools >
Media > Podcasts...**.

## 1. Subscribe to a show

1. **Tools > Media > Podcasts...** opens the Podcast Manager: an empty
   folder tree on the left, an empty episode list on the right, the first
   time you use it.
2. Press **Add Podcast...**. Three ways in, all on the same dialog:
   - Type a show name in the search box and press **Search** — this
     queries Apple's free iTunes Search directory. Arrow to a result and
     press **Subscribe to Selected**.
   - Already know the feed address? Paste it into **Add by Feed URL** and
     press **Add** — skips the search entirely.
   - Coming from another podcast app? **Import OPML...** reads its whole
     exported subscription list — folders included — in one step.
3. Close the Add Podcast dialog. Your new show appears in the Podcast
   Manager's tree, and its episodes fill the list on the right when you
   select it.

## 2. Organize into folders

Press **New Folder...** to create one, nested under whatever's selected in
the tree — select a folder first, then New Folder again, to nest one inside
it. There's no drag-and-drop yet; moving a show between folders is a
planned follow-up (see the end of this tutorial).

Not ready to unsubscribe from a show but don't want new episodes right now?
Right-click it in the tree (or open its context menu with Menu/Shift+F10)
and choose **Pause Downloads for This Podcast** — it stays in your library,
episodes and all, but QUILL stops fetching or downloading anything new for
it until you choose **Resume Downloads for This Podcast** later.

## 3. Download an episode for offline listening

Select an episode in the list and press **Download**, or reach the same
action from its right-click context menu. Downloads run on their own
dedicated background thread, so a big backlog never slows down anything
else QUILL is doing — an AI request, a transcription job — while it works
through the queue.

Two separate pause controls, worth knowing apart:

- **Pause All Downloads** / **Resume All Downloads** — reachable from the
  tray menu, the status bar's Podcasts cell, or the Podcast Manager —
  stops the queue from *starting* anything new. Whatever's already
  mid-transfer keeps running to completion.
- **Pause Download** on one specific episode (its button, or its context
  menu) halts that one transfer immediately, right where it is. Choosing
  **Resume Download** later picks the file back up from the exact byte it
  stopped at — nothing already downloaded is thrown away.

Try it: start downloading a longer episode, then immediately pause just
that one episode. Its status column shows "Paused." Resume it and watch the
status move back through "Downloading" to "Downloaded."

## 4. Play an episode, and control speed

Select an episode and press **Play/Pause**, double-click it, or use its
context menu. Starting a different episode always replaces whatever was
playing — QUILL never plays two things at once, whether that's two
episodes or an episode and a radio station. Closing the Podcast Manager
never stops playback, exactly like Browse Stations in Internet Radio.

Your place in an episode is saved automatically. Come back to it later —
even much later, even after closing QUILL — and it resumes exactly where
you stopped.

The **Speed** control on the player row sets playback rate for whichever
podcast you currently have selected, from 0.75x up to 2.0x. It's
remembered per show, so a fast-talking interview show and a slow, dense
lecture series can each have their own comfortable speed.

## 5. Control it without opening the dialog

- **The status bar.** A **Podcasts** cell appears the first time you play
  an episode. Press Enter, or click it, to play/pause. Its context menu
  adds Stop and Pause/Resume All Downloads.
- **The system tray.** Send QUILL to the tray and its right-click menu
  carries the same controls for when the window is hidden.
- **The keyboard, from anywhere in the editor.** Your QUILL Key
  (**Ctrl+Shift+Grave**), then **8**, toggles play/pause; then **7** stops.
  Deliberately parked right next to Radio's N/0/9 chords, not on top of
  them. Remap either in **Preferences > Keyboard Shortcuts**.

## 6. Take your library with you

**Export OPML...** on the Podcast Manager writes your whole subscription
list — folder structure included — to a standard `.opml` file that any
other podcast app can read. Bring it back into QUILL (or take it
somewhere else) with **Import OPML...**, the same button you used in step 1.

## What's not here yet

No video podcasts — audio only, matching every other playback surface in
QUILL. Chapter navigation and transcript viewing/export are parsed from the
feed already but have no UI of their own yet; a separate Inbox view, a
cross-show reorderable Play Queue, local (imported-file) podcasts, and
richer sorting/filtering are the next planned phases — see
`docs/planning/podcasts.md` if you want the full roadmap.

## The shape of it

Subscribe with a search, a URL, or an OPML import; organize into folders;
download with two pause controls that mean genuinely different things;
play through one shared player that never stops just because you closed a
dialog. Right-click nearly anything for the full set of actions, and reach
the essentials — play, pause, stop — from the status bar, the tray, or the
keyboard without ever opening the Podcast Manager at all.
