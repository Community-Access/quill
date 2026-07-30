# QUILL Cast User Guide

Version 1.0

QUILL Cast is podcasts the way a screen reader user would design them: a small window whose library tree has focus the instant it opens, a Podcast Manager built entirely for the keyboard, spoken feedback for every action, and a tray icon so playback continues while you work.

## Getting started

Launch QUILL Cast from the Start Menu (or `quill-cast` from a terminal if you installed from source). The window opens with keyboard focus on your **Library** tree.

- No shows yet? Press Alt+S for the Subscriptions menu, then **Add Podcast...** to subscribe by search or feed URL -- or **Import OPML...** to bring a library from another podcast app, or **Subscribe to ACB Media Podcasts** for ACB's whole live directory in one step.
- With shows: arrow to one and press **Enter** to play its next unplayed episode -- no detour through the Manager required. If every episode is already played, Enter plays the most recent one and says so.
- Want QUILL Cast on the moment it opens? Check **Subscriptions > Resume Last Episode on Launch** once, and launching the app picks up exactly where you left off.

Everything QUILL Cast announces goes through the same announcement engine QUILL uses, so it speaks through your screen reader (JAWS, NVDA, Narrator) without stealing focus.

## The main window

Tab order: the now-playing line, the library tree, then five buttons.

- **Now playing** (read-only text): what is playing; mirrored in the status bar and the Episode menu.
- **Library** (tree): the same pinned views the Podcast Manager shows -- **Favorites**, **New Episodes**, **Continue Listening**, **Inbox** -- above your nested library folders and the shows filed in them, each with a live unplayed-episode count. Enter on a show plays its next episode; Enter on a pinned view opens the Podcast Manager to that view. Delete unsubscribes a show (with confirmation) or dissolves a folder (your shows step safely to the top level -- nothing is ever unsubscribed by deleting a folder). Shift+F10 opens the full context menu: Play/Stop, Add/Remove Favorites, Move to Folder, **Download All Episodes**, **Remove All Episodes**, **Feed Credentials...** (for private feeds -- see below), Unsubscribe, New Folder, and Open Manager.
- Buttons: **Play** (becomes **Pause** while playing, **Resume** while paused -- one transport control that is never dead), **Stop**, **Add to Favorites** (becomes **Remove from Favorites** when the playing show is already a favorite), **Open Manager...**, **Add Podcast...**.

## The Podcast Manager

The Manager (Ctrl+M) is where episode-level life happens, and it is the same Manager QUILL ships:

- **Pinned views** lead the folder tree: **Favorites**, **New Episodes**, **Continue Listening**, and the **Inbox**.
- **The Inbox** triages episodes rather than shows: route a show to the Inbox and its new episodes land there; file episodes into your own nested folders. Your first manual filing per show is remembered and applied automatically (Forget reverts it).
- **"View cross-show lists as"**, a combo box next to "Sort episodes", offers three ways to see the Inbox and every other cross-show list (New Episodes, Continue Listening, Favorites): **Grouped in list** (the default -- each show's episodes cluster together, read one podcast's backlog at a time), **Flat list** (everything as one stream, sorted purely by date across every show at once), or **Folders per podcast** (real expandable tree nodes, one per show, right under the pinned view). The Sort Episodes control now applies to these cross-show lists too, not just a single show's own episode list -- and it's per-podcast: select a show (or its Folders node) and change the sort to override just that podcast, leaving everyone else on the shared default.
- **Play Queue**: Play Next or Add to Queue on any episode; the queue auto-advances, survives restarts, and reorders from the keyboard (Move Up/Down, or Mark then Move for long hops).
- **Playlists**, below the Play Queue in the tree: saved, named episode lists, distinct from the (transient) Play Queue and the (fixed) pinned views. Right-click Playlists for **New Playlist...** (manual -- add episodes one at a time via **Add to Playlist...** on any episode's context menu) or **New Smart Playlist...** (rule-based -- which shows, episode status, how recent, how long, and how to sort, re-resolved live every time you open it). Edit Rules..., Rename (F2), and Delete round out each playlist's own context menu.
- **Search Everywhere** searches shows, episodes, your notes, and fetched transcripts at once and jumps to the result.
- **Transcripts**: when a feed provides one (Podcasting 2.0; VTT/SRT/JSON), save it to a file or open it -- cached for instant reopening. QUILL Cast never generates transcripts from audio; that stays in full QUILL.
- **Episode notes** timestamp the playing moment; Enter on a note jumps playback there.
- **Local podcasts**: turn folders of your own audio into shows, with optional watched folders that pick up dropped files.
- **Always Sync**, **auto-trim silence**, **normalize loudness**, and a live **volume boost** that respects the Sleep Timer's restore volume.
- **Download All Episodes / Remove All Episodes** on a show's context menu: Download All queues everything not already downloaded or in progress, no extra confirmation needed. Remove All Episodes confirms first, then -- only if the show has downloaded files -- asks separately whether to delete those too; the show itself stays subscribed either way.

## Private feeds (username and password)

Some feeds -- Patreon supporter feeds, premium and members-only shows, private company or organization feeds -- protect their RSS address with a username and password (HTTP Basic authentication). QUILL Cast handles them end to end.

**Subscribing.** Add the feed exactly as you would any other: Subscriptions > Add Podcast..., paste the address into **Add by Feed URL**, press **Add**. If the feed asks for a sign-in, a small **Feed Credentials** dialog opens with focus on the username field: enter the username and password your podcast provider gave you (Patreon and similar services show these on the same page as the feed address) and press OK. QUILL Cast retries with your credentials and the subscription continues normally. Wrong password? The dialog reopens with your username kept, and says so.

**Changing or clearing credentials later.** Open the show's context menu (Shift+F10 in the main window's library tree or the Podcast Manager's tree) and choose **Feed Credentials...** -- the same dialog, username prefilled. Enter a new password to replace the stored one, or press **Clear Credentials** to remove both and make the show public-only again. Every save and clear is announced.

**What signing in covers.** Once a show has credentials, QUILL Cast signs in automatically everywhere that show touches the network: feed refresh, episode downloads, streaming playback, and feed-provided transcripts and chapters. One deliberate security rule: credentials are only ever sent to the same host as the feed itself. If a show serves its audio from a different host (a public content network, say), those requests carry no credentials -- your password is never broadcast to third parties.

**Where the password lives.** Never in a plain file. On an installed copy it goes into Windows Credential Manager, protected by your Windows account. On a portable copy it is encrypted (Windows DPAPI) inside the `data` folder on your stick. It never appears in `podcasts.json`, never in logs, and **Export OPML** never includes it -- an exported subscription list is always safe to share.

**Portable caveat.** DPAPI encryption is tied to your Windows account and machine. Move the portable stick to a different PC or user account and your subscriptions all come along, but stored feed passwords cannot be decrypted there -- the first refresh of a private feed will say sign-in failed, and you re-enter the password once via Feed Credentials....

## Menus

### Subscriptions (Alt+S)

Open Podcast Manager... (Ctrl+M), Add Podcast..., Import OPML..., Export OPML..., New Folder... (creates a library folder without opening the Manager), Add Local Podcast..., Scan Watched Folders, Subscribe to ACB Media Podcasts, Podcast Settings..., **Resume Last Episode on Launch** (check item -- the appliance switch), **Preferences...** (Ctrl+,) -- Resume Last Episode on Launch, automatic Check for Updates, and Announce dialog transitions (off by default -- turn on for more spoken detail around every dialog), Send to Tray (Ctrl+W), Exit.

### Episode (Alt+E)

A live now-playing line, then Play/Pause (Ctrl+P), Stop, **Mute/Unmute**, Next Chapter, Previous Chapter, **Skip Forward**, **Skip Back**, Add Episode Note..., **Play Queue...** (the same reorderable queue the Manager offers, now one keystroke away), a **Recently Played** submenu (your last fifteen episodes, newest first, playable inline), Sleep Timer... (fade out and stop after a set time, restoring your volume), **Sound Enhancements...**, and **Skip Settings...**.

**Sound Enhancements...** applies live, on top of whatever is playing: a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each) plus a "Quick preset" shortcut (Flat, Bass Boost, Voice Clarity, Podcast) that sets all three at once, a compressor ("Even Out Volume"), and **Smart Speed** (trims silence between words and sentences, distinct from the one-time leading/trailing silence trim Downloads can already do to the saved file -- Smart Speed is reversible and live, on any episode, any time). All of it needs FFmpeg (Help > Get FFmpeg...); if it's missing, playback continues unfiltered and QUILL Cast tells you why. Turning anything on or off, or scrubbing the seek bar while enhanced, briefly reconnects on Apply -- QUILL Cast restarts the filter at your exact position, so you never lose your place, and pausing/resuming works normally throughout. Every setting here is **per-podcast**: open it while an episode is playing to set that show's own sound, or with nothing playing to set the shared default every other show follows.

**Skip Forward** and **Skip Back** jump the current episode by a fixed number of seconds -- 30 forward, 15 back by default -- unlike Next/Previous Chapter, which jump to the nearest chapter marker instead. **Skip Settings...** sets how far each jumps (per-podcast, the same way Sound Enhancements is), and, only when a show is loaded, **auto-skip intro** and **auto-skip outro** (0 = off): intro-skip jumps forward automatically on a fresh start (never when resuming your saved position); outro-skip ends the episode early, exactly as if it had finished naturally -- auto-advance and delete-after-play still fire.

### Downloads (Alt+D)

Pause All Downloads, Resume All Downloads.

### Help (Alt+H)

One standalone difference from QUILL: "Send Show Notes to Editor" copies notes to the clipboard instead, since there is no editor here.

- **Command Palette...** (Ctrl+Shift+P) -- every QUILL Cast command in one searchable list.
- **Keyboard Shortcuts...** -- open the Keyboard Manager to view, search, and change QUILL Cast's keyboard shortcuts (see "Global hotkeys and keyboard shortcuts" below).
- **Global Hotkeys...** -- assign a system-wide key to QUILL Cast's Play/Pause and Stop so they work while another program has focus (see below).
- **Get FFmpeg...** -- a safety net: ffmpeg ships inside QUILL Cast for trim/normalize passes and Sound Enhancements, but if it ever goes missing this downloads the official build so those settings work again.
- **User Guide** / **Release Notes** / **Product Requirements...** -- this guide, the version history, and the product requirements document, each opened right in your browser.
- **Redeem Unlock Code...** -- enter a signed unlock code for a pre-release capability. Verified entirely on your machine; nothing is transmitted. A code redeemed here counts for QUILL and Quill Radio too -- all three share one unlock store.
- **Check for Updates...** -- compares your version with the newest release of QUILL Cast, downloads the installer in-app with spoken progress, then offers Install now (closes the app and runs the installer) or Open folder. Already up to date shows a dialog too, not just a spoken announcement. QUILL Cast also runs this check quietly once a day on launch -- silent unless it actually finds something; Subscriptions > Preferences (Ctrl+,) turns it off.
- **About QUILL Cast** -- version, sync statement, and the project address.

## Spotify podcasts (experimental)

QUILL Cast can play podcasts hosted on Spotify -- but this is an **experimental capability that is off by default and hidden until you deliberately turn it on**. It ships "dark" behind a feature flag, so on a normal install there are no Spotify menu items and nothing reaches Spotify's servers. Turning it on takes four separate things, and one of them is a paid **Spotify Premium** account, because Spotify only lets an app stream its audio for Premium subscribers.

### What you need to enable it

All four of these must be in place; missing any one means the Spotify items never appear or never play.

| Requirement | Why it is needed |
| --- | --- |
| The Spotify feature, unlocked | Spotify is a locked, pre-release feature. Unlock it with a signed code via **Help > Redeem Unlock Code...** -- the same one-time, verified-on-your-machine unlock QUILL uses for other early features. A code redeemed here counts for QUILL and Quill Radio too; all three share one unlock store. |
| A Spotify Premium account | Spotify's Web Playback engine only streams audio to Premium subscribers. A free account can sign in and browse, but will not play. |
| Your own Spotify Client ID | QUILL Cast does not ship a Spotify app identity; you supply your own. Register an app in the Spotify Developer Dashboard, then set its redirect address to exactly `http://127.0.0.1:43217/callback`. There is no client secret to copy -- QUILL Cast signs in with the modern Authorization Code with PKCE flow, which needs only the Client ID. |
| Windows with the Edge WebView2 runtime | Spotify audio is copy-protected and can only be played by Spotify's own Web Playback engine, which runs inside a hidden Microsoft Edge WebView2 component. The WebView2 runtime is part of current Windows (it ships with Microsoft Edge), so it is normally already present. |

Once the feature is unlocked and you are not in Safe Mode, two new items appear in the **Help** menu: **Connect to Spotify...** and **Browse Spotify Podcasts...**

### Connecting to Spotify

Choose **Help > Connect to Spotify...** to open an accessible sign-in dialog. Enter your Client ID and start the sign-in: your web browser opens to Spotify's own approval page, you approve access, and Spotify sends you back to a tiny local address on your own machine (`127.0.0.1`) that QUILL Cast is listening on for exactly that one moment. QUILL Cast captures the result and stores your sign-in tokens in the **Windows credential vault** -- never in a plain file, never in `podcasts.json` or a log. Your Client ID is stored alongside them so the whole connection lives in one place and clears together.

### Browsing and playing

Choose **Help > Browse Spotify Podcasts...** to open an accessible search box with a results list. Type a show or episode name, arrow to a result, and press **Enter** to play it. A Spotify episode plays through the hidden Web Playback engine, which coexists with QUILL Cast's normal streaming engine -- a Spotify episode is routed to it automatically, and the transport controls (Play/Pause, Stop), the status bar, the tray, and any system-wide Global Hotkeys you have assigned all drive it exactly as they drive an ordinary episode.

### Spotify episodes are play-only

- **No download.** Spotify audio is copy-protected (DRM), and the Web Playback engine is the only sanctioned way to play it, so a Spotify episode plays but has no Download -- it cannot be saved to disk the way a normal podcast episode can.
- **Many Spotify shows are exclusive.** A large share of Spotify's shows exist only on Spotify, with no public RSS feed to fall back to.
- **A best-effort public-RSS match (idea, not yet a button).** Some shows publish the *same* episode both on Spotify and as an ordinary MP3 in their own public podcast feed. QUILL Cast has a core helper that can try to find that public enclosure -- downloading the **publisher's own public file**, never Spotify's audio -- for a Spotify episode that also exists on a normal feed. This is deliberately best-effort and, for now, is available in the underlying code but is not yet wired to a menu item or button.
- **Premium only, and off in Safe Mode.** Without Spotify Premium, playback will not start even after you sign in; and like every network feature, Spotify is disabled when QUILL Cast runs in Safe Mode. The first sign-in asks for a one-time network-access confirmation, because connecting reaches Spotify's servers.

## Hardware media keys

If your keyboard has media keys, Play/Pause, Stop, and Next/Previous Track (mapped to chapters) control QUILL Cast system-wide while it runs -- even from the tray. Keys another app already owns are left alone. Starting an episode also silences a playing radio stream and vice versa: nothing ever double-plays.

## Global hotkeys and keyboard shortcuts

**Keyboard Shortcuts (Help > Keyboard Shortcuts...)** opens the Keyboard Manager: a searchable, conflict-aware list of every QUILL Cast command and its assigned key, where you can reassign a key (with a warning for conflicts or risky keys), clear it, or restore the defaults. The keymap is **shared with QUILL and Quill Radio**, so a change here changes it everywhere in the family. A few commands whose default is a two-key chord or uses a comma (Preferences on Ctrl+,) keep their built-in shortcut until the next launch; plain single-key commands take effect immediately.

**Global Hotkeys (Help > Global Hotkeys...)** lets you give a **system-wide** key to QUILL Cast's Play/Pause and Stop, so you can control an episode from any program. Only those safe playback commands can be bound this way; none are set by default; and the first assignment warns that a system-wide key may override the same key elsewhere. A key another app already owns is left alone. (Windows only.)

## Quillins in QUILL Cast

QUILL Cast can now run **Quillins** -- QUILL's small, sandboxed, permission-gated add-ons -- from its own **Quillins** menu. A Quillin declares which apps it targets, so only add-ons written for QUILL Cast appear here. The bundled `cast-premium-auth` sample demonstrates a Quillin that supplies the sign-in header for a private, subscriber-only podcast feed (a companion to the built-in username/password support described above). Quillins are off in Safe Mode, and third-party Quillins remain disabled in this release -- the bundled ones are the foundation.

## Downloads that survive a dropped connection

If your internet hiccups mid-download, QUILL Cast first tries to quietly resume from where it left off; if the drop is real, it waits and reconnects automatically instead of leaving the episode stuck in Failed status -- you'll hear "Download connection dropped; reconnecting" when it happens. **Subscriptions > Podcast Settings...** has an **"If a download's connection drops"** section: turn automatic reconnecting on or off, and set how many attempts and how many seconds between them.

## The system tray

Closing the window keeps QUILL Cast in the notification area. Right-click (or Shift+F10 on) the tray icon for Show, podcast controls, and Exit. Double-click to bring the window back.

## Sharing data with QUILL

QUILL Cast reads and writes the same data store as QUILL and Quill Radio (`%APPDATA%\Quill`). Subscribe here, and the show is subscribed in QUILL's Podcasts; your queue, positions, notes, and downloads are one set of data. Local podcasts are stored outside the synced data folder by construction. Uninstalling QUILL Cast never deletes the shared store.

## Keyboard reference

| Action | Key |
| --- | --- |
| Open Podcast Manager | Ctrl+M |
| Play/Pause | Ctrl+P |
| Send to tray | Ctrl+W |
| Preferences | Ctrl+, |
| Play selected show's next episode | Enter (in the tree) |
| Unsubscribe / delete folder | Delete (in the tree) |
| Tree context menu | Shift+F10 (in the tree) |
| Subscriptions menu | Alt+S |
| Episode menu | Alt+E |
| Downloads menu | Alt+D |
| Help menu | Alt+H |

## Troubleshooting

- **A feed will not add.** Check the URL is the RSS/Atom feed itself, not the show's web page; the Add dialog's search can usually find the show by name instead.
- **Adding a feed asks for a username and password.** The feed is private (see "Private feeds" above). Enter the credentials your podcast provider gave you -- for Patreon-style feeds they're shown alongside the feed address on the provider's site. If the prompt keeps reopening, the username or password is wrong; re-copy both from the provider.
- **A private feed says "feed sign-in failed" during refresh.** The publisher rotated or revoked your credentials, or -- on a portable copy -- you've moved the stick to a different PC or Windows account, where stored passwords can't be decrypted. Either way: show's context menu > **Feed Credentials...**, re-enter the password, refresh again.
- **An episode will not download and reconnect isn't fixing it.** Downloads menu > Resume All Downloads; check Subscriptions > Podcast Settings... to confirm reconnecting is on and the attempt/wait numbers give it enough tries. Some hosts rate-limit regardless.
- **Positions seem stale across apps.** Positions are written on pause/stop/switch; if two apps play simultaneously against the same store, the last writer wins.
- **Resume Last Episode on Launch didn't pick up my episode.** It only fires at app startup, and only if the episode is still in your library (an unsubscribed show or a removed download won't resume).
