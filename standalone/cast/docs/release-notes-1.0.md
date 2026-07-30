# QUILL Cast 1.0 -- Release Notes

Your shows, on their own. QUILL Cast takes the podcast environment QUILL users already know and gives it a window, a menu bar, and a tray icon of its own -- for the days you want your queue without the manuscript.

## Coming: Spotify podcasts (experimental)

Groundwork has landed for playing podcasts hosted on Spotify inside QUILL Cast. It is **experimental and off by default** -- it ships hidden behind a feature flag, so you will not see it on a normal install, and turning it on takes a signed unlock code, a Spotify **Premium** account, and your own Spotify Client ID. Spotify audio is copy-protected, so a Spotify episode plays but cannot be downloaded, and many Spotify shows are exclusive with no public feed. The full story -- what you need, how to connect, and how to browse and play -- is in the new **"Spotify podcasts (experimental)"** section of the QUILL Cast User Guide.

## What's new in 1.0.7

- **Update in one click -- QUILL Cast installs it and restarts itself.** When an update is available, choose Download, then **Install and restart now**: QUILL Cast applies the update -- extracting the new portable files over your folder, or running the installer silently -- and relaunches on its own, keeping all your shows, downloads, and settings. No more closing the app, unzipping, and swapping folders by hand. This is the same one-click self-update shared across every Quill app.

## What's new in 1.0.6

- **Private feeds -- your supporter subscriptions, finally first-class.** Patreon feeds, premium shows, members-only company feeds: any podcast protected by a username and password (HTTP Basic authentication) now subscribes like any other. Paste the feed address into Add by Feed URL as usual; if the feed asks for a sign-in, a small **Feed Credentials** dialog opens -- enter what your provider gave you and QUILL Cast retries and subscribes. Change or clear credentials any time from the show's context menu (**Feed Credentials...**), in the main library tree or the Podcast Manager alike.
- **Signed in everywhere that show goes -- and nowhere else.** Once a show has credentials, refresh, episode downloads, streaming playback, transcripts, and chapters all authenticate automatically. One deliberate security rule: credentials only ever travel to the feed's own host. Audio served from a third-party content network gets no password attached -- yours is never broadcast beyond the publisher who issued it.
- **Stored like a secret, because it is one.** Passwords live in Windows Credential Manager on an installed copy, or DPAPI-encrypted inside the portable `data` folder on a stick -- never in `podcasts.json`, never in logs, and never in an exported OPML file, so sharing your subscription list stays safe. One portable caveat, documented in the User Guide: DPAPI is tied to your Windows account and machine, so a stick moved to a new PC keeps every subscription but asks for private-feed passwords once more.
- **Honest errors.** A wrong or rotated password no longer hides behind "could not reach that feed" -- subscribing reopens the credentials prompt and says so, and a background refresh that fails to sign in announces exactly which show needs its credentials updated and where to do it.

## What's new in 1.0.5

- **Skip Forward and Skip Back.** Two new Episode-menu commands jump the current episode by a fixed number of seconds -- 30 forward, 15 back by default -- for the times a chapter marker isn't where you want to land. A new **Skip Settings...** dialog sets how far each jumps, per podcast: open it while an episode is playing to set that show's own distance, or with nothing playing to set the shared default every other show follows.
- **Auto-skip intro and outro, per podcast.** The same Skip Settings... dialog offers, only when a show is loaded, auto-skip intro (jump forward automatically the moment an episode starts fresh -- never when resuming your saved position, so you never lose your place) and auto-skip outro (end the episode early, exactly as if it had reached its own true end -- auto-advance to the next queued episode and delete-after-play still fire). Both off by default.
- **Playlists.** A new "Playlists" node sits below the Play Queue in the Podcast Manager's tree -- saved, named episode lists, distinct from the transient Play Queue and the four fixed pinned views. Build a manual Playlist by adding episodes one at a time (any episode's right-click menu gets **Add to Playlist...**), or create a Smart Playlist that re-resolves live every time you open it, from rules you set: which shows, episode status (unplayed/in progress/played), how recently published, a minimum and maximum length, and how to sort the result.

## What's new in 1.0.4

- **A real three-band equalizer, per podcast.** Sound Enhancements' single preset choice became Bass, Mid, and Treble sliders (-12 to +12 dB each), freely adjustable. The old presets are still there as a "Quick preset" shortcut. And every enhancement setting -- the three bands, Even Out Volume, Smart Speed -- is now per-podcast: a shared default plus a per-show override, exactly like playback speed already worked. Open Sound Enhancements while an episode is playing to adjust that show specifically; with nothing playing, you're adjusting the shared default.
- **A real dialog when you're already up to date.** Help > Check for Updates used to only announce "up to date" -- easy to miss. It now shows a proper dialog, the same as a genuine update does.
- **Quieter by default.** Preferences (Ctrl+,) gained "Announce dialog transitions" (off by default) -- previously every dialog spoke "Entered/Exited" cues with no way to turn it off.
- **Documentation, right in the Help menu.** User Guide, Release Notes, and Product Requirements now open directly from Help, rendered in your browser.

## What's new in 1.0.3

- **Three ways to view the Inbox and every cross-show list.** A new "View cross-show lists as" combo box next to the Podcast Manager's "Sort episodes" control offers **Flat list** (one stream sorted purely by date across every show -- a true "what's new, period" feed), **Grouped in list** (the default and pre-existing look -- each show's episodes cluster together, read one podcast's backlog at a time), or **Folders per podcast** (real expandable tree nodes, one per show, under the Inbox and every other pinned view).
- **Per-podcast sort order.** The sort control now actually applies to these cross-show views too (it previously only affected a single show's own list) -- and any podcast can have its own sort order that overrides the shared default: select that show (or its Folders node) and change Sort Episodes. Also fixed: setting a podcast's own playback speed no longer silently resets any other setting override that podcast already had.

## What's new in 1.0.2

- **Sound Enhancements.** Episode > Sound Enhancements... adds an equalizer preset (Flat, Bass Boost, Voice Clarity, Podcast), a compressor ("Even Out Volume"), and **Smart Speed** (trims silence between words and sentences, live and reversible on any episode, distinct from the one-time leading/trailing trim Downloads already offers) -- all applied through the ffmpeg QUILL Cast already uses for download processing. Off by default. Full seek and scrub-bar support while enhanced: scrubbing or toggling anything on/off never loses your place or forces a paused episode to resume.
- **Download All Episodes / Remove All Episodes.** New on every show's context menu, in the Podcast Manager and the main library tree alike. Download All queues everything not already downloaded or in progress -- no extra confirmation, just like downloading one episode. Remove All Episodes confirms first, then -- only if the show actually has downloaded files -- asks separately whether to delete those too; either way the show stays subscribed, so a future feed refresh can bring episodes back.

## What's new in 1.0.1

- **Automatic Check for Updates.** QUILL Cast quietly checks for a newer version once a day when it launches -- silent unless a real update is found, at which point you get the same "download it now?" prompt Help > Check for Updates always gave you. Throttled so it never hits the network on every single launch.
- **Preferences...** (Ctrl+,) is a new, small dialog gathering the app's startup behavior in one place: Resume Last Episode on Launch and the new automatic update check, each its own checkbox. Turning either off takes effect immediately.

## Highlights

- **Your library, on the front page.** The main window is your library tree -- the same pinned views the Manager shows (Favorites, New Episodes, Continue Listening, Inbox) above your nested folders and the shows filed in them, each with a live unplayed count and a full context menu (Play/Stop, Favorite toggle, Move to Folder, Unsubscribe, New Folder) one Shift+F10 away. Enter on a show plays its next unplayed episode directly -- no detour through the Manager required.
- **One transport button, not two dead ones.** Play becomes Pause while playing and Resume while paused, exactly like the panel it sits on. A Favorites button tracks whatever is playing and flips to Remove when it's already saved.
- **Podcasts as an appliance.** Check Subscriptions > Resume Last Episode on Launch once, and opening QUILL Cast is all you ever do -- it picks up exactly where you left off. A Recently Played submenu (Episode menu) keeps your last fifteen episodes one keystroke deep, distinct from the Continue Listening view's in-progress list.
- **Play Queue, promoted.** The same reorderable cross-show queue the Manager offers now has its own top-level menu item and Command Palette entry -- no longer a button buried in a dialog.
- **Mute, everywhere you'd expect it.** A dedicated Mute/Unmute command silences playback without losing your level.
- **Downloads that survive a dropped connection.** If your internet hiccups mid-download, QUILL Cast retries automatically instead of leaving the episode stuck in Failed status, resuming from the partial file already on disk. How many attempts and how long to wait between them are yours to tune in Podcast Settings.
- **The whole Manager.** Pinned Favorites, New Episodes, and Continue Listening views; an Inbox that triages episodes into your own folders and remembers how you file each show; episode and show filters that narrow the list live.
- **A Play Queue that behaves.** Play Next or Add to Queue from any episode, auto-advance when one ends, survives restarts, and reorders entirely from the keyboard -- Move Up/Down, or Mark and Move for long hops.
- **Search Everywhere.** Shows, episodes, your notes, and fetched transcripts, one search, straight to the result.
- **Transcripts and notes.** Feed-provided transcripts (Podcasting 2.0) save or open instantly from cache; episode notes timestamp the playing moment, and Enter on a note jumps playback there.
- **Local podcasts.** Your own audio files become shows, with watched folders that turn dropped files into new episodes. Stored outside the synced data folder by construction.
- **ACB Media, one command.** Subscribe to ACB's whole live directory idempotently.
- **Downloads that respect you.** Pause/resume all; Always Sync for shows you want complete; auto-trim silence and normalize loudness on finished downloads; a volume boost that never disturbs the Sleep Timer's restore volume.
- **A tray citizen.** Close to the notification area and keep listening; control playback from the tray menu.
- **Two flavors, everything bundled.** A system installer and a truly portable zip whose `data` folder keeps your whole library on the stick. ffmpeg included, its own app icon, no downloads ever -- and if ffmpeg somehow goes missing, **Help > Get FFmpeg...** restores it from the official source.
- **Spoken feedback everywhere.** Every action announces its outcome through your screen reader -- JAWS, NVDA, or Narrator -- without stealing focus.
- **One data store.** Subscriptions, queue, positions, notes, and downloads are shared with QUILL and Quill Radio. Subscribe here, see it there.
- **Check for Updates, built in.** The update check compares your version against this repository's releases, downloads the installer in-app with spoken progress, and offers Install now.
- **Folders from the menu.** Subscriptions > New Folder... creates a library folder without opening the Manager; Send to Tray (Ctrl+W) and Exit live there too. (Send Show Notes to Editor copies to the clipboard here -- there is no editor buffer to send to.)

## What QUILL Cast deliberately is not

It is not QUILL minus some menus -- it is the podcast app, period. The editor, AI, speech transcription engines, braille, and speech-synthesis stacks are not installed at all, which keeps the install small and the app simple. Feed transcripts still work fully; generating transcripts from audio is full QUILL's job, one Help menu item away.

## Not a fork -- a guarantee

QUILL Cast runs the exact same podcast feature code as QUILL, from the same upstream package. Fixes and features land upstream once and reach QUILL, QUILL Cast, and Quill Radio together. This repository only carries the wrapper, the installer, and these docs.

## Requirements

Windows 10 or 11, x64 (or ARM64 under emulation). No Python installation required.

## Known limitations

- Global hotkeys for transport are configured from full QUILL (Tools > Global Hotkeys...), not from this app, in 1.0.
