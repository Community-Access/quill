# QUILL Cast User Guide

Version 1.0

QUILL Cast is podcasts the way a screen reader user would design them: a small window whose library tree has focus the instant it opens, a Podcast Manager built entirely for the keyboard, spoken feedback for every action, and a tray icon so playback continues while you work.

## Getting started

Launch QUILL Cast from the Start Menu (or `quill-cast` from a terminal if you installed from source). The window opens with keyboard focus on your **Library** tree.

- No shows yet? Press Alt+S for the Subscriptions menu, then **Add Podcast...** to subscribe by search or feed URL -- or **Import OPML...** to bring a library from another podcast app, or **Subscribe to ACB Media Podcasts** for ACB's whole live directory in one step.
- With shows: arrow to one and press **Enter** to play its next unplayed episode -- no detour through the Manager required. If every episode is already played, Enter plays the most recent one and says so.
- Want QUILL Cast on the moment it opens? Check **Subscriptions > Resume Last Episode on Launch** once, and launching the app picks up exactly where you left off.

Everything QUILL Cast announces goes through the same announcement engine QUILL uses, so it speaks through your screen reader (JAWS, NVDA, Narrator) without stealing focus -- and writes to your braille display at the same time (see "Spoken and braille announcements" below).

## The main window

Tab order: the now-playing line, the library tree, then five buttons.

- **Now playing** (read-only text): what is playing; mirrored in the status bar and the Episode menu.
- **Library** (tree): the same pinned views the Podcast Manager shows -- **Favorites**, **New Episodes**, **Continue Listening**, **Inbox** -- above your nested library folders and the shows filed in them, each with a live unplayed-episode count. Enter on a show plays its next episode; Enter on a pinned view opens the Podcast Manager to that view. Delete unsubscribes a show (with confirmation) or dissolves a folder (your shows step safely to the top level -- nothing is ever unsubscribed by deleting a folder). Shift+F10 opens the full context menu: Play/Stop, Add/Remove Favorites, Move to Folder, **Download All Episodes**, **Remove All Episodes**, **Feed Credentials...** (for private feeds -- see below), Unsubscribe, New Folder, and Open Manager. On a folder the context menu offers **Rename Folder...**, **Delete Folder...**, New Folder..., and Open Manager.
- **Episodes without leaving the main page.** Every show in the tree can be expanded (Right Arrow) to reveal its episodes, newest first, right where the show sits -- no detour through the Manager to reach one particular episode. Shows start collapsed so the tree reads as a list of shows rather than a wall of episodes. **Enter on an episode plays that episode**; Enter on the show itself still plays the show's next unplayed episode.
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
- **Chapters, from wherever they exist.** QUILL Cast looks for chapters in three places, cheapest first: the feed's own chapters document, chapter markers inside the downloaded file, and the timestamps published in the episode's show notes (the familiar `00:12:34 Topic` lines). The Chapters list says which of those it came from, so marks worked out from show notes are never presented as the publisher's own. The Chapters button is offered whenever any of them could exist, not only when the feed publishes a chapters file.
- **Filter episodes by "In progress"** -- the ones you have started but not finished -- alongside All, Unplayed, Played, Downloaded, and Not downloaded.
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

Open Podcast Manager... (Ctrl+M), Add Podcast..., Import OPML..., Export OPML..., New Folder... (creates a library folder without opening the Manager), Add Local Podcast..., Scan Watched Folders, Subscribe to ACB Media Podcasts, Podcast Settings..., **Quick Actions...**, **Export My Data...**, **Delete All Podcast Data...**, **Resume Last Episode on Launch** (check item -- the appliance switch), **Preferences...** (Ctrl+,), Send to Tray (Ctrl+W), Exit.

**Preferences...** (Ctrl+,) holds five checkboxes:

- **Resume Last Episode on Launch** -- pick up where you left off the moment the app opens.
- **Check for updates automatically on launch** -- the quiet once-a-day check.
- **Announce dialog transitions** -- off by default; turn it on for more spoken detail around every dialog.
- **Alt+F4 minimizes to the system tray** -- off by default. When on, Alt+F4 tucks the window away with playback still running instead of closing it, so the reflexive keyboard close stops ending your listening. The titlebar X and Exit are unaffected: a deliberate exit still exits.
- **Winamp playback keys** -- on by default. See "Winamp playback keys" below.

**Export My Data...** writes everything QUILL Cast knows about your listening -- subscriptions, folders, the Play Queue, playlists, episode notes, listening statistics, and your recently-played list -- to one readable JSON file. Export OPML covers your subscriptions and nothing else; this covers the rest.

**Delete All Podcast Data...** unsubscribes from everything and clears your queue, playlists, Inbox filing, statistics, and history. It asks twice, and asks about downloaded files separately, because "start over" and "reclaim the disk" are not the same wish.

### Podcast Settings and per-podcast settings

**Podcast Settings...** holds the shared defaults every show follows unless it sets its own. Alongside playback mode, retention, download location, and the reconnect rules, 1.1 adds:

- **Default playback speed** -- now anything from 0.5x to 5.0x in tenths, not six fixed choices.
- **Automatically download** -- none, the newest 1, 3, 5, 10, or every episode. This is the setting that makes new episodes arrive ready to play. "Every episode" and the older **Always sync the full catalog** checkbox are the same instruction, and setting either sets both.
- **Also download anything you add to the Play Queue** (on) and **Also download everything routed to the Inbox** (off).
- **Inbox: keep at most** -- 0 means no limit. See "Inbox limits" below.
- **Delete downloads after (days)** and **Total download storage cap (MB)** -- both 0 (off) by default. See "Managing your downloads".
- **When an episode finishes** -- "Play the next episode in the Play Queue" (on) and "When the queue is empty, keep going with the same podcast" (off). **With both off, playback stops at the end of the episode you started.**
- **Read the podcast name before the episode title in mixed lists** -- an accessibility preference. In a cross-show list of two hundred rows from forty shows, whichever name comes first is what you can skim by first letter.
- **Start on this view** -- which part of the library QUILL Cast opens on: New Episodes, Continue Listening, the Inbox, Favorites, Recently Expired, or the top of the tree.

**Settings for This Podcast...**, on any show's context menu in the Podcast Manager, holds the same choices for one show plus the ones that only make sense per podcast: **Auto-Queue New Episodes**, **Announce new episodes by name**, **Expire from the queue**, the Inbox age limit, Route to Inbox, and Favorite. Anything left on **Use the shared default** stores no override at all, so changing the global later still reaches that show. **Follow the Shared Defaults** drops every override for the show at once.

### Quick Actions

**Quick Actions...** lets you decide the order of the actions on episodes, podcasts, and Play Queue items. Three lists, each reordered with Move Up, Move Down, and **Make Default**. The order does three jobs at once:

- **The first action in each list is what Enter does.** If you always download before listening, make Download the default.
- **The first nine answer to Ctrl+1 through Ctrl+9** in the Podcast Manager's episode list.
- **The whole list is the order of the right-click menu**, so the items you use most are always in the same place.

Nothing changes until you change it: out of the box, Enter plays an episode and plays a podcast's next unplayed episode, exactly as before. **Reset This List** puts a list back to the shipped order.

### Episode (Alt+E)

A live now-playing line, **Player Information...**, then Play/Pause (Ctrl+P), **Stop** (Ctrl+.), **Mute/Unmute**, **Volume Up** (Ctrl+Up) and **Volume Down** (Ctrl+Down), Next Chapter, Previous Chapter, **Skip Forward** (Ctrl+Right), **Skip Back** (Ctrl+Left), **Speed Up** (Ctrl+Shift+Up), **Speed Down** (Ctrl+Shift+Down), **Reset Speed to Normal** (Ctrl+Shift+0), **Stop After This Episode**, Add Episode Note..., **Play Queue...** (the same reorderable queue the Manager offers, now one keystroke away), **Mark All as Played...**, **Listening Statistics...**, a **Recently Played** submenu (your last fifteen episodes, newest first, playable inline), Sleep Timer..., **Sleep at End of This Episode**, **Extend Sleep Timer 5 Minutes**, **Sound Enhancements...**, and **Skip Settings...**. The volume keys match Quill Radio's, so the two apps behave the same way.

**Speed Up / Speed Down / Reset Speed** move playback speed in tenths anywhere from 0.5x to 5.0x, and say both the new speed and whose it is -- the playing podcast's own if something is playing, or the shared default when nothing is. The same range is in Podcast Settings and in Settings for This Podcast...

**Stop After This Episode** is a one-off: it stops instead of auto-advancing, clears itself when it fires, and never survives a restart. What normally follows an episode is set by the two "When an episode finishes" switches in Podcast Settings -- with both off, playback simply stops at the end of the episode you started.

**Mark All as Played...** clears a podcast you have given up on. It always confirms, naming the show and the count; the episodes stay in your library, downloaded files are untouched, and they leave the Inbox because the Inbox is unplayed episodes.

**Sleep Timer...** gained two things. **End of this episode** is now one of the choices, and it follows the episode rather than a clock -- seek forward and the timer moves with you instead of stopping you early. It is offered only when a podcast episode is loaded, because a live radio stream has no end to stop at. **Extend 5 Minutes** sits on the timer dialog while it counts down, and on this menu; extending also undoes any fade already in progress, since the point of extending is that you are still listening.

**Sound Enhancements...** applies live, on top of whatever is playing: a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each) plus a "Quick preset" shortcut (Flat, Bass Boost, Voice Clarity, Podcast) that sets all three at once, a compressor ("Even Out Volume"), and **Smart Speed** (trims silence between words and sentences, distinct from the one-time leading/trailing silence trim Downloads can already do to the saved file -- Smart Speed is reversible and live, on any episode, any time). All of it needs FFmpeg (Help > Get FFmpeg...); if it's missing, playback continues unfiltered and QUILL Cast tells you why. Turning anything on or off, or scrubbing the seek bar while enhanced, briefly reconnects on Apply -- QUILL Cast restarts the filter at your exact position, so you never lose your place, and pausing/resuming works normally throughout. Every setting here is **per-podcast**: open it while an episode is playing to set that show's own sound, or with nothing playing to set the shared default every other show follows.

**Player Information...** puts everything about what is playing into one read-only text field you can review with the arrow keys, character by character or line by line, and copy: title, show, position, duration, time remaining, progress as a percentage, playback speed, whether it is streaming or a file on this computer, whether that file is kept or a temporary copy, how many notes it has, where it will resume, and which chapter you are in. A spoken status goes past once; this stays put until you close it.

**Skip Forward** and **Skip Back** jump the current episode by a fixed number of seconds -- 30 forward, 15 back by default -- unlike Next/Previous Chapter, which jump to the nearest chapter marker instead. **Skip Settings...** sets how far each jumps (per-podcast, the same way Sound Enhancements is), and, only when a show is loaded, **auto-skip intro** and **auto-skip outro** (0 = off): intro-skip jumps forward automatically on a fresh start (never when resuming your saved position); outro-skip ends the episode early, exactly as if it had finished naturally -- auto-advance and delete-after-play still fire.

### Downloads (Alt+D)

Pause All Downloads, Resume All Downloads, **Downloads...**, **Free Up Space**, **Run Housekeeping Now**.

## Managing your downloads

**Downloads...** answers "how much disk are my podcasts using". It shows the total, a breakdown by podcast with the largest first, and an **Unheard only** filter that tells you how many already-played downloads it hid. **Remove This Podcast's Downloads...** clears one show; the episodes stay in your library and can be downloaded again.

Two automatic rules live in Podcast Settings, both off by default:

- **Delete downloads after N days** -- per podcast overridable, so one archival show can keep everything while the rest expire.
- **Total download storage cap** in megabytes. When you go over, already-played downloads are removed oldest first.

**A queued or part-played episode is never removed by either rule.** That is what makes an automatic cap safe: disk pressure is not a reason to throw away the thing you are halfway through. It also means a cap can be unreachable -- if your queue is bigger than the cap, the queue stays and QUILL Cast tells you what it could not free.

**Free Up Space** applies both rules now and says how many bytes came back. **Run Housekeeping Now** does the full pass -- expire stale queue items, sweep Recently Expired, trim the Inbox, apply the storage rules -- and reports everything it did in one sentence. It also runs automatically after every feed refresh.

## Automatic downloads

Through 1.0.x, an episode arrived on your disk because you asked for it, or -- with Always Sync -- because every episode did. There was no "keep the newest three ready". **Automatically download** in Podcast Settings fixes that: choose none, the newest 1, 3, 5, 10, or every episode, and any podcast can set its own. New episodes are fetched on subscribe and on every refresh.

Two more switches sit with it. Anything you add to the **Play Queue** downloads too, whatever its age -- an episode you queued is one you meant to play. Anything routed to the **Inbox** does not, because the Inbox is a triage surface, not a commitment. QUILL Cast says how many episodes it started downloading; nothing happens silently.

Downloads never run in Safe Mode, and never for a podcast you have paused.

## Auto-Queue and per-show announcements

For a show you never skip, **Auto-Queue New Episodes** (Settings for This Podcast..., or the show's context menu) sends its new episodes straight into the Play Queue on refresh, skipping the Inbox.

**Announce New Episodes**, also per show, names the new episodes out loud and in braille when the background check finds them, plus a tray notification. It is per podcast deliberately: being told about every feed is being told about nothing.

## Queue expiration and Recently Expired

A queued episode you never got to is worse than clutter -- the queue decides what plays next, so a stale item takes a turn rather than just taking up space.

**Expire from the queue** (Settings for This Podcast...) removes a queued episode that has waited longer than 1 day, 2, 3, a week, a fortnight, or a month. **Never** is the default and there is deliberately no global setting: a daily news show wants two days, a weekly long-form show wants two weeks, and one number for everything is a number nobody wants.

Expiring is not deleting. The episode moves to **Recently Expired**, a pinned view in the Podcast Manager beside New Episodes and the Inbox, and waits there for seven days keeping its downloaded file, its saved position, and its place in its show. Its context menu offers:

- **Restore to the Play Queue** -- back at the end of the queue with a fresh clock, so it will not immediately expire again.
- **Restore All**.
- **Forget This One** -- stop offering it back. Its downloaded file is left alone.

Only the seven-day sweep removes a downloaded copy, and only for something you chose not to restore. Every expiry is announced.

**Upgrading from 1.0.x:** a queue saved before 1.1 has no timestamps to age against. QUILL Cast reads an unstamped episode as "added just now", so the first launch after updating cannot empty your queue.

## Inbox limits

An Inbox holding every unplayed episode of every routed show forever is a second library, not a triage surface. Any podcast can now cap it: **keep at most N episodes**, and **drop episodes older than** 6 hours up to 2 weeks. A global default for the count lives in Podcast Settings.

Two rules make the caps safe:

- **Trimming never deletes anything.** A trimmed episode leaves the Inbox and stays unplayed in its show's own episode list, downloaded file and all.
- **Three kinds of episode are never trimmed**: anything you have started, anything in your Play Queue, and anything you filed into an Inbox folder by hand. They do not even count toward the cap.

## Listening statistics

**Listening Statistics...** (Episode menu) reports time listened for this week, month, year, or all time; how much extra content faster playback bought you; how many episodes you finished; and a breakdown by podcast, most-listened first.

It is a read-only text field you arrow through line by line and can copy -- the same shape as Player Information. Durations are read as language ("3 hours, 47 minutes"), never as a clock face, because a screen reader reads `3:47:00` as a time of day.

**Export CSV...** saves every session for a spreadsheet. **Clear Statistics...** deletes the log and nothing else. Ninety days are kept.

One number is deliberately absent: time saved by Smart Speed. The silence-trimming path cannot honestly report how much silence it dropped, and an invented figure would be worse than no figure at all.

## Chapters you can skip

QUILL Cast finds chapters from three places -- the feed's own chapter document, markers inside the audio file, and timestamps in the show notes. From 1.1 you can also skip them.

Open **Chapters...** for the episode you are playing and use **Skip This Chapter** to mark the ad break, the sponsor read, or the outro. Playback jumps past it and says "Skipping chapter:" and its name. Consecutive marked chapters are stepped over together, and marking everything to the end simply finishes the episode normally, so auto-advance and delete-after-play still fire. **Skip Nothing** clears every mark.

Marks last for the listening session only -- a chapter you skipped in yesterday's episode says nothing about today's -- and the button only appears for the episode actually playing.

## Winamp playback keys

If you came through Winamp, the classic transport letters work in the Podcast Manager's lists and on the main window. They are the same keys Quill Radio's recordings player uses, from the same shared map.

| Key | Action |
| --- | --- |
| X | Play |
| C | Pause |
| V | Stop |
| B | Next episode |
| Z | Previous episode |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| T | Switch between elapsed and remaining |
| J | Jump to an episode by name |
| Ctrl+J | Jump to a time (90, 1:30, or 1:02:03) |
| L | Play what is selected |
| Ctrl+Up / Ctrl+Down | Volume up / down |

They are on by default and never fire while a text box has focus, so typing is never swallowed. Turn the letters off in Preferences (Ctrl+,) if you would rather use them for list typeahead; Ctrl+Up and Ctrl+Down for volume always work either way.

## Getting an episode back out

Three commands, all of them **Quick Actions** entries -- so they can be reordered, made the Enter default, or reached on Ctrl+1 to Ctrl+9 like everything else on those menus.

**Save Episode Audio As...** saves a copy of the episode's audio wherever you choose. It copies rather than moves: QUILL Cast goes on managing its own downloaded copy, so retention, the storage cap, resume and Remove Downloaded Copy all still apply to it, and your saved copy sits outside all of that. If the episode is not downloaded yet there is no audio file to copy, so QUILL Cast offers to fetch it and says to run the command again when it finishes -- rather than holding you behind a progress bar you cannot escape. The filename is suggested as "Show - Episode"; characters Windows will not accept are replaced, and very long titles are shortened, so the Save dialog never opens with a name the system would reject.

**Copy Podcast Link** copies the show's feed address, next to the existing **Copy Episode Link**. The feed address rather than the show's website, because a feed address is what another podcast app can be given. A local podcast has no feed and says so.

**Show in File Explorer** opens the folder holding a downloaded episode with the file selected. An episode you are streaming has no file to show, and says that instead of opening some other folder.

## Your notes on an episode

Episode notes mark a moment and jump back to it. Two ways in:

- from the **player**, with **My Notes in This Episode...**, which acts on whatever is playing;
- from an episode's context menu in the **Podcast Manager**, for any episode you select.

Selecting a note jumps to it. From the Manager the episode need not be the one playing -- it starts it first, then jumps.

**Copy Note** puts one note on the clipboard as text somebody else can use: the episode, the podcast, the timestamp, your note, and the audio link together. The note's own words on their own are a fragment with no way back to the moment they mark. A note whose podcast you have unsubscribed from still copies; the missing parts are simply left out.

## Importing a large subscription list

Import OPML is built for the real thing: a list of a thousand or more feeds exported from another app after years of listening.

The import runs in the background, so the window never freezes. Duplicates are matched on a normalized address, so the `http://` and `https://` forms of one feed are correctly one feed, and a file listing the same show twice imports it once. Two shows that merely share a *title* are both imported and flagged for you to review, because two different shows genuinely can be called "The Daily".

Tick **Check that each feed is still reachable** and QUILL Cast checks them all after importing, several at a time, with progress announced every ten per cent and a **Stop Checking** button that keeps everything already imported. A feed asking for a sign-in counts as reachable, so a private feed is never reported dead.

The report that follows lists corrections, unreachable feeds, skipped duplicates, and anything that could not be imported, with two exports:

- **Export Report...** -- the whole report as text.
- **Save Pruned OPML...** -- your original file written back without the feeds that no longer answer, folders and all, so the list you keep elsewhere can be cleaned up too.

**Add every show as streaming** is ticked by default for a bulk import, so a thousand shows do not immediately queue a download each.

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

## Spoken and braille announcements

Every action in QUILL Cast announces its outcome, and that announcement goes out on two channels at once.

**Speech** goes through your screen reader -- JAWS, NVDA, or Narrator -- without stealing focus, so a download finishing never interrupts what you were reading.

**Braille** goes to your display at the same time. This is new: the standalone apps used to speak but never write, so a braille reader saw nothing of QUILL Cast's own confirmations, progress, and errors. Three details make it usable rather than noisy:

- **A burst settles instead of flickering.** When several different messages arrive in quick succession -- a refresh cascade, a download reporting in -- the first is written instantly and the rest settle to whichever is newest, rather than each one shoving the last aside faster than cell one can be read.
- **Errors are exempt.** An error is written through immediately, never merged into a burst, and can be held on the display instead of flashing past.
- **Two braille styles.** Braille can carry exactly the wording that is spoken, or a compact position-first form. There is also a setting for how long an identical repeated message is suppressed.

These are shared accessibility settings, so you set them once in QUILL (Preferences > Accessibility) and they apply to QUILL Cast, Quill Radio, and the rest of the family. Turning braille off there turns it off here.

## Questions that could destroy something always start on No

Every confirmation that would delete or discard something opens with **No** selected -- **Delete Folder**, **Delete Playlist**, **Remove All Episodes**, and **Delete Downloaded Files** among them. Pressing Enter reflexively while a question is still being read can never lose your data; choosing Yes takes one arrow key and a deliberate decision. An automated check in the build refuses any new destructive question that opens on Yes.

## Hardware media keys

If your keyboard has media keys, Play/Pause, Stop, and Next/Previous Track (mapped to chapters) control QUILL Cast system-wide while it runs -- even from the tray. Keys another app already owns are left alone. Starting an episode also silences a playing radio stream and vice versa: nothing ever double-plays.

## Global hotkeys and keyboard shortcuts

**Keyboard Shortcuts (Help > Keyboard Shortcuts...)** opens the Keyboard Manager: a searchable, conflict-aware list of every QUILL Cast command and its assigned key, where you can reassign a key (with a warning for conflicts or risky keys), clear it, or restore the defaults. The keymap is **shared with QUILL and Quill Radio**, so a change here changes it everywhere in the family. A few commands whose default is a two-key chord or uses a comma (Preferences on Ctrl+,) keep their built-in shortcut until the next launch; plain single-key commands take effect immediately.

**Global Hotkeys (Help > Global Hotkeys...)** lets you give a **system-wide** key to QUILL Cast's Play/Pause and Stop, so you can control an episode from any program, and to **Show/Hide QUILL Cast to the Tray**, which tucks the window away or brings it back from wherever you are. Only those safe commands can be bound this way; the first assignment warns that a system-wide key may override the same key elsewhere, and a key another app already owns is left alone. (Windows only.)

Show/Hide QUILL Cast to the Tray starts on **Ctrl+Alt+Shift+Q**. That is the same chord QUILL itself uses for its own show/hide, and Windows gives a system-wide key to whichever app registers it first -- so if you run both, change one of them here.

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
| Stop | Ctrl+. |
| Volume up / down | Ctrl+Up / Ctrl+Down |
| Skip forward / back | Ctrl+Right / Ctrl+Left |
| Speed up / down | Ctrl+Shift+Up / Ctrl+Shift+Down |
| Reset speed to normal | Ctrl+Shift+0 |
| Sound Enhancements | Ctrl+E |
| Audio output mode | Ctrl+Shift+M |
| Run a Quick Action on the selected episode | Ctrl+1 ... Ctrl+9 |
| My Notes in This Episode | (unbound; assignable in Keyboard Shortcuts) |
| Winamp transport (play/pause/stop/next/previous) | X / C / V / B / Z |
| Winamp seek 5 / 30 seconds | Left, Right / Shift+Left, Shift+Right |
| Winamp jump to episode / to time | J / Ctrl+J |
| Winamp elapsed or remaining | T |
| Command Palette | Ctrl+Shift+P |
| Send to tray | Ctrl+W |
| Preferences | Ctrl+, |
| Play selected show's next episode | Enter (in the tree) |
| Expand a show to see its episodes | Right Arrow (in the tree) |
| Play the selected episode | Enter (on an episode in the tree) |
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
- **Episodes vanished from my queue.** Check **Recently Expired** in the Podcast Manager: a podcast with a queue age limit moves what has waited too long there, and Restore or Restore All puts it back. If you did not mean to set a limit, it is **Expire from the queue** in Settings for This Podcast...
- **The Inbox is missing episodes I expected.** Inbox limits (count or age) can trim a show's older episodes out of the Inbox. They are never deleted -- they are unplayed in the show's own episode list -- and anything started, queued, or filed by hand is never trimmed. Adjust or clear the limits in Settings for This Podcast...
- **A download disappeared.** The download age limit or the total storage cap (Podcast Settings) removed it; the episode is still there and can be downloaded again. Neither rule ever removes a queued or part-played episode. **Downloads...** shows what is currently on disk.
- **New Episodes only shows a thousand episodes.** Cross-show views fill the newest thousand rows so a very large library stays navigable; the status line says the true total. Narrow it with the Episodes filter, or open one podcast to see all of its own.
- **The library seems to save a moment after I pause.** On a very large library (tens of thousands of episodes), writing everything out takes seconds, so QUILL Cast settles those writes onto a short timer instead of running them mid-keystroke. Closing the app always writes everything first.
- **A letter key does something unexpected in a list.** The Winamp playback keys are on by default -- see "Winamp playback keys" above. Turn them off in Preferences (Ctrl+,) to use those letters for list typeahead instead.
