# QuillBeacon changelog

## Unreleased

- **Read both versions of a sync conflict before choosing** (FUX-12,
  2026-11-24). Sync History shows the selected conflict below the list
  (Alt+V): this device's version, the other device's, each line that differs
  marked as removed or added, and what Use Merged keeps.

- **An empty library says how to fill it** (FUX-09, 2026-11-24). A new
  library opened on the search box over an empty list and said only "0
  results". While there is no bookmark, a **Getting started** line above the
  search box says "No bookmarks yet. New Bookmark (Ctrl+N) saves one, or
  Import (Ctrl+I) brings bookmarks or subscriptions in.", and the window
  opens with focus on it.
- **Export says where the file went** (2026-11-23). File > Export now ends
  with the format, the file and its folder, for example "Exported your library
  as HTML bookmarks to quillbeacon-export.html in Downloads.", instead of
  reading the whole path aloud. An export that could not be written says so,
  where it used to say nothing.
- **The results list stays still** (FUX-06, 2026-11-23). The list is virtual,
  so after a capture from the browser or a sync the selection used to stay on
  the old row number, which was now another beacon, while the details showed
  the first row; Delete or Rename could act on a beacon you never chose. Now
  you stay on your own beacon, with the rest of your selection, on the same
  line, and the details follow it. The result count is said when you change
  the search, the sort or the destination, not on every refill or auto-sync.
  An auto-sync that pushed and pulled nothing says nothing. A beacon a sync
  removed is said once ("... is no longer in the list."), and you land on its
  neighbour.
- **Auto-sync stays out of your way** (2026-11-24). Automatic sync used to say
  "Auto-synced. Pushed 0, pulled 0." at every interval, refresh the list you
  were reading even when nothing had changed, and run while a dialog was open.
  Now a sync that brought nothing new is written on the status bar and not
  spoken, the list is refreshed only when something arrived, and a sync
  waits for the next interval while one of Beacon's dialogs is open. A
  failure, new arrivals and conflicts are still said.
- **Places in Scribe for Documents results** (2026-11-21). A Scribe
  Documents destination lists places in what Scribe for Documents made.
  Tools > Scribe for Documents > Add Documents in My Scribe Account as Places
  (Alt+Shift+F6) makes a place for each document in your Scribe account, and
  QUILL's Next Steps can save one at a heading. A place whose file is gone
  checks your Scribe account and offers to download it again, with no pages
  used. The submenu also holds Conversions on This Computer, Documents in My Scribe Account, Scribe
  Status, Repeat Last Scribe Message and Scribe for Documents Options, on
  Alt+Shift+F7 to F11.
- **Settings survive a full disk or a crash while saving** (2026-11-20).
  Accessibility, external player, routing and sync settings, and the sync
  conflicts waiting for review, are now written to a temporary file first
  and then put in place, so a save that fails part-way leaves your previous
  settings instead of an empty file.
- **A second sound scheme: VS Code Signals** (2026-11-02). QuillBeacon plays
  the QUILL family's sound scheme, and there are now two: Ink, still the
  default, and VS Code Signals, the accessibility signal sounds from Visual
  Studio Code, used under the MIT licence. Choose in the Sound Scheme window
  of QUILL or QUILL Lite, or in QUILL's setup wizard, and QuillBeacon plays it
  from the next time it starts. Anything it has no sound for stays quiet, or
  is spoken instead.
- **AI in the Assist menu, when you want it.** The three local helpers stay
  first and still call no AI service. After them: Ask (Ctrl+6) about the
  selected beacon or your search results, Which AI Am I Using (Ctrl+8),
  Choose Your AI (Ctrl+4), and Describe a Saved Picture (Ctrl+F5), which reads
  the words in a beacon's picture on your computer first, sends the picture
  once, and offers the description as a note. QuillBeacon signs in on its own,
  as QUILL Beacon. A line at the bottom of the results pane says which AI is in
  use. Nothing runs on a timer, and Safe Mode turns it all off.
- **Organize What I Saved** (Ctrl+3, Assist menu): an AI task that searches
  your library, reads beacons, uses the local Suggest Tags, and tags beacons or
  moves them into collections. Every change is shown as text and waits for
  Apply, and Ctrl+Z undoes it. Needs GitHub Copilot or Codex.

## 0.1.0

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which includes PyMuPDF 1.28.2 under AGPL-3.0 through the shared GLOW
  dependency; Beacon does not itself expose GLOW. Its exact source, and that
  of every other GPL, LGPL or AGPL part, is published with each release.
  Portable editions leave GLOW, and with it PyMuPDF, out. See Licences and
  Notices.
