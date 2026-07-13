# Tutorial 9: Internet Radio

**Goal:** find a station, play it in the background while you keep writing,
save your favorites, and control it without ever opening a dialog.

Internet Radio needs a network connection and is disabled entirely in Safe
Mode. Everything below lives under **Tools > Media > Internet Radio**.

## 1. Play something right away

1. **Tools > Media > Internet Radio > Browse Stations...**
2. The **Category** list opens on two options that need no network call to
   show: **Favorites** (empty your first time) and **ACB Media** — the
   American Council of the Blind's ten Live365 stations, bundled directly
   into QUILL. Arrow to one and press **Play**.
3. Close the dialog. The station keeps playing — closing Browse Stations
   never stops playback, the same way closing a document doesn't stop
   Read Aloud.

## 2. Search a real directory

Back in Browse Stations, use the **Search RadioBrowser** row above the
category list: type a station name (try `jazz` or a city you know has a
station), optionally narrow by tag/genre or country, and press **Search**.
Results land under a new **Search Results** category. Arrow through them —
a read-only **Station details** pane below reports everything QUILL knows
about the selected station: country, language, tags, codec and bitrate,
community vote count, homepage, and the stream URL itself, so you know what
you're about to hear before you press Play.

Found one you'll want again? **Add to Favorites** saves it; the button
relabels to **Remove from Favorites** once it's there.

## 3. Add a station RadioBrowser doesn't have

Two more buttons in Browse Stations cover the rest:

- **Add Custom Station...** — a name and any http/https stream URL, plus
  an optional homepage and tags. Press **Test** to play it right there
  before **Save**.
- **Find Streams from a Website...** — type a station's own website
  address. QUILL fetches that one page and lists every stream-shaped link
  it finds (an audio tag, a `.pls`/`.m3u` playlist, a Shoutcast/Icecast
  mount point), each with a plain-language reason. Select one, **Test** it,
  then **Use This Link...** to carry the guessed name and URL straight into
  Add Custom Station. This reads the one page you typed — it does not open
  a browser inside QUILL.

## 4. Control it without opening a dialog

Once something is playing, three ways to reach it without Browse Stations:

- **The status bar.** A **Radio** cell appears the first time you play
  something. Press Enter on it, or click it, to play/pause. Open its
  context menu (right-click, or Menu/Shift+F10) for Stop, Mute/Unmute, a
  **Favorite Stations** quick-switch, and a shortcut straight back to
  Browse Stations.
- **The system tray.** Send QUILL to the tray and its right-click menu
  carries the same Play/Pause, Stop, Mute, and Favorite Stations controls,
  plus a Now Playing line.
- **The keyboard, from anywhere in the editor.** Press your QUILL Key
  (**Ctrl+Shift+Grave**), then **N** to toggle play/pause; then **0** to
  stop; then **9** to mute. Remap any of these in **Preferences > Keyboard
  Shortcuts** like any other QUILL Key chord.

Try it now: start a station, switch back to your document, and press
Ctrl+Shift+Grave, then 9 — the music mutes without you ever leaving the
paragraph you were editing.

## 5. Set the volume once and forget it

Browse Stations has its own **Radio volume** slider and **Mute** button.
This is entirely separate from your Windows system volume and from your
screen reader's own speech volume — turn the music down (or mute it)
without ever touching how loud your screen reader talks.

## What's not here

TuneIn and iHeartRadio aren't supported — both are undocumented,
reverse-engineered commercial APIs with no public terms, and RadioBrowser
covers the same need without that risk. YouTube audio isn't supported
either. Stream recording and scheduled recording are real, planned
follow-ups — see `docs/planning/radio.md` if you're curious. Podcasts are a
separate, already-shipped feature — see [Tutorial 10](10-podcasts.md).

## The shape of it

One player, several doors into it: Browse Stations to find something new,
the status bar or tray for everyday control, and QUILL Key chords when
you'd rather not leave the keyboard at all. Closing any dialog never stops
the music.
