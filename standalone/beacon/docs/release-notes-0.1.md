# Quill Beacon 0.1 Release Notes

Version 0.1.0 (build 2).

Quill Beacon is new. It keeps your bookmarks, and it keeps your place.

A normal bookmark remembers an address. Quill Beacon also remembers where you
were inside it: a heading on a web page, a passage you selected, a moment in a
podcast, a radio station, a file or a folder. It keeps the reason you saved it,
in your own words, and gets you back there in seconds.

It is for anyone who saves more than they can find again, and it was built for
screen readers and the keyboard from the start. Nothing needs a mouse or drag
and drop.

This is the first public release, and the number says so. Quill Beacon 0.1 is
early. The parts that are here work, and the parts that are not are listed
plainly under "Known limitations" below.

## Sharp at any display scaling

QuillBeacon handles each monitor's scaling itself, so text stays sharp at 125, 150
and 200 percent and on monitors with different scaling, and windows and list
columns keep their proportions.

## Downloads

Two downloads. Choose one. Both run on Windows 10 and Windows 11.

- **Quill-Beacon-Setup-Shared-0.1.0.exe** -- the installer, recommended. It
  installs the shared QuillVille runtime if the computer does not already have
  it, then the app, with a Start Menu entry and an uninstaller. The
  Documentation component adds the user guide and these notes.
- **Quill-Beacon-Portable-0.1.0.zip** -- unpack it anywhere. It keeps your
  library, captures and settings in its own `data` folder next to the app.

## Try this first

1. Open Quill Beacon. The window has three panes: Destinations, the bookmarks
   list, and Details. **F6** moves between them.
2. Press **Ctrl+N** for **New Bookmark**, and save a page or a file.
3. Press **Ctrl+F** to search. Type a word, then press Down to reach the
   results. **Enter** opens the one you are on.
4. Press **Ctrl+F1** for **Where Am I?** at any time.
5. Press **F1** on anything you are unsure of. It tells you what the window
   is for and what that control does.

## What you can do with it

### Save the exact place

Save a web page, a file, a folder, a podcast episode or a radio station. Add a
note, tags and collections. When a saved place moves or breaks, Quill Beacon
never quietly swaps it for a guess. **Tools > Review Location Repair...** shows
the old place beside a proposed fix, and you choose.

### Capture from your browser

Quill Beacon has browser extensions for Chrome, Edge and Firefox. They can
save the whole page, the text you selected, a link, the nearest heading, or
the moment in a video or audio you are playing. To connect one, choose
**Tools > Capture Bridge...** (Ctrl+Shift+B) and copy the token into the
extension's Options. If Quill Beacon is not running, the extension says so
and saves nothing.

### Find it again

Search covers titles, notes, tags and the text you saved. You can narrow it
by typing filters such as `tag:research`, `type:episode`, `collection:`,
`domain:`, `has:note` or `not:archived`. **View > Build Search...**
(Ctrl+Shift+F) builds the same kind of search from fields instead.

**View > Save Search as Smart Collection...** (Ctrl+Shift+G) keeps a search
as a live collection in the sidebar. It always shows your library as it is
now. **Tools > Smart Collections Manager...** renames or deletes them.
Deleting one never deletes the bookmarks it found.

**Edit > Find Duplicates** (Ctrl+Alt+D) lists saved items that point at the
same place.

### Organize

- Collections, edited with **Tools > Collection Editor...** (Ctrl+Shift+C).
- Trails: ordered paths through saved items, each step with its own note.
  Create one with **Tools > Trail Editor...** (Ctrl+Alt+T). In the sidebar,
  a trail shows its progress, and you can step through it and mark steps
  done.
- Favorites, Archive and Trash, in the sidebar with Inbox, Recent,
  Listen Later, Podcasts, Radio and Needs Attention.
- **Edit > Attachments...** (Ctrl+Shift+E) pins a file, a link or a note to a
  saved item.
- Bulk commands on the Edit menu act on everything you selected: trash,
  archive, restore, favorite, add or remove a tag, add to a collection, or
  delete.
- **Edit > Undo** (Ctrl+Z) reverses the last change. A bulk command comes
  back as one step, even a permanent delete.

### Podcasts and radio

- **Media > Subscribe to Podcast...** (Ctrl+Shift+S) and
  **Media > Refresh Feeds** (Ctrl+Shift+R).
- **Media > Play in Player** (Ctrl+Shift+L) plays an episode in the built-in
  player, where you can save the exact second you want to come back to.
- **Media > Play in External Player** (Ctrl+Alt+P) hands the item to VLC, mpv
  or your system player, with the time to resume from. Choose the player with
  **Tools > External Player...**.
- **Media > Add Radio Station...** saves a station with backup stream
  addresses. **Media > Add Radio Program...** saves one show, with its host and
  air time.

### Keep links healthy

**Tools > Revalidate Health...** (Ctrl+Alt+H) checks whether saved places are
still there. Files are checked on your own disk. Web links are checked over
the internet only after you confirm. Broken ones go to Needs Attention.

### Bring your bookmarks in, take them out

**File > Import...** (Ctrl+I) reads browser bookmark files (HTML), OPML,
M3U and PLS playlists, CSV, JSON and plain text. **File > Export...**
(Ctrl+E) writes JSON, HTML, Markdown, CSV, OPML, M3U or plain text. Your
library is never locked in.

### Publish a collection

Select a collection, then **Tools > Publish Collection...** (Ctrl+Shift+W).
Quill Beacon makes a read-only, accessible web page from it: an HTML file you
can copy or host anywhere, plus a preview on this computer. Nothing on the
page can change your library.

### Help when you ask for it

The Assist menu can **Suggest Tags**, **Suggest Relationships** with other
saved items, and **Summarize Note**. These work on your computer, with no AI
service and no internet. They only run when you ask, and never change your
library on their own.

**Help > What's New** (Ctrl+Shift+F1) opens the changelog in your browser, on
the same key as every other QuillVille app.

### Sync between your own computers

Sync is off until you turn it on. Open **Sync > Sync Settings...** to choose
a folder you already trust, such as OneDrive, Dropbox or a shared drive.
Your library is encrypted with a passphrase only you know before it is
written there.

- **Sync > Sync Now** (F9) sends and fetches changes.
- **Sync > Sync History...** shows what synced and lets you roll back. If the
  same note changed on two computers, you choose which version to keep.
- **Sync > Auto Sync...** syncs on a timer. It is off by default.
- To add a second computer, use **Pair Device** in Sync Settings, then unlock
  there with the same passphrase.
- Something you trash on one computer goes to the Trash on the others, where
  you can restore it.

### Settings and sounds

- **View > Preferences...** (Ctrl+Comma) brings accessibility, sync, the
  capture bridge and published pages together in one window.
- **View > Accessibility Settings...** sets how much Quill Beacon says, high
  contrast, text size and reduced motion.
- Quill Beacon speaks through your screen reader and writes to a braille
  display.
- **Tools > App Sounds Play On...** (Ctrl+Alt+S) chooses where its sounds
  play. **Alt+Shift+M** turns them off and on.
- Minimizing the window sends Quill Beacon to the system tray. The tray icon
  can show the window, capture, sync, open the Status Center, and exit.
- **Tools > Status Center...** (Ctrl+Alt+I) shows the capture bridge, sync
  and library health at a glance.

## Essential keys

Every command is on a menu, and every menu command shows its key. These keys
work in the main window.

| Key | Command |
|---|---|
| Ctrl+N | File > New Bookmark |
| Enter | Edit > Open |
| Delete | Edit > Trash |
| Shift+Delete | Edit > Restore |
| F2 | Rename the selected bookmark (in the list) |
| Ctrl+D | Edit > Toggle Favorite |
| Ctrl+L | Edit > Add to Collection... |
| Ctrl+Shift+A | Edit > Archive |
| Ctrl+Z | Edit > Undo |
| Ctrl+Space or Shift+arrows | Select several bookmarks (in the list) |
| Ctrl+F | View > Search |
| Ctrl+Shift+F | View > Build Search... |
| Ctrl+Shift+P | View > Command Palette |
| Ctrl+F1 | View > Where Am I? |
| F6 | View > Next Pane |
| F1 | Help for this window and the control you are on |
| F9 | Sync > Sync Now |
| Ctrl+F9 | Sync > Sync Settings... |
| Ctrl+Alt+F2 | Help > Get Help from Support... |
| Ctrl+Q | File > Exit |

The Command Palette lists commands by name with their keys. Type part of a
name, such as "export", and press Enter.

## Privacy

Your library lives on your computer. Quill Beacon has no account and sends
nothing anywhere by default.

- **Sync** is off until you turn it on. When it is on, your library is
  encrypted with your passphrase before it leaves your computer.
- **The capture bridge** starts with the app so your browser extension can
  reach it. It listens only on this computer and needs a token.
- **Published pages** are previewed on this computer only. The HTML file goes
  wherever you choose to put it.
- **The internet is used only when you ask**: subscribing to or refreshing a
  podcast, playing something online, checking web links in Revalidate Health
  after you confirm, or syncing to a server.
- **Attachments** stay on your computer. They are not synced.
- **Assist** runs on your computer and calls no AI service.

## Known limitations

This is a 0.1 release. Please be patient with the edges.

- **The browser extensions are not in these downloads** and are not in any
  browser's store yet. They are loaded by hand in the browser's developer
  mode.
- **There is no hosted sync service yet.** Sync through a folder works today.
  Sync Settings can also sign in to a QuillSync server by email link, but no
  public server is offered in this release.
- **Quill Beacon does not yet connect to QUILL, Quill Radio or Quill Cast.**
  Saving a place from inside those apps, and opening a saved place back in
  them, are planned.
- **There is no phone app.**
- **Keys cannot be changed yet.** They work in the main window, not inside
  dialogs.
- **Ctrl+Alt keys and the right Alt key.** On keyboard layouts where the right
  Alt key types accented letters, a Ctrl+Alt key may run its command instead
  of typing the letter while the search box has focus. The menus always work.
- **The built-in player needs a media engine.** If none is available, it says
  "media backend unavailable"; Play in External Player still works.
- **Search matches words, not meaning.** Smarter search is not included.

## Getting help

Press F1 on any window or control. For anything else, choose
**Help > Get Help from Support...** (Ctrl+Alt+F2), or write to
support@community-access.org.
