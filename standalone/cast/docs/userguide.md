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
- **Library** (tree): the same pinned views the Podcast Manager shows -- **Favorites**, **New Episodes**, **Continue Listening**, **Inbox** -- above your nested library folders and the shows filed in them. A show wears its unplayed count in words -- "(3 unheard)" -- and a folder wears how many podcasts live under it, counting everything expanding it would reveal. Enter on a show plays its next episode; Enter on a pinned view opens the Podcast Manager to that view. Delete unsubscribes a show (with confirmation) or dissolves a folder (your shows step safely to the top level -- nothing is ever unsubscribed by deleting a folder). Shift+F10 opens the full context menu: Play/Stop, Add/Remove Favorites, Move to Folder, **Move Up / Move Down in Custom Order** (Alt+Up / Alt+Down -- see Sort Podcasts below), **Download All Episodes**, **Remove All Episodes**, **Feed Credentials...** (for private feeds -- see below), Unsubscribe, New Folder, and Open Manager. On a folder the context menu offers **Rename Folder... (F2)**, **Delete Folder...**, New Folder..., and Open Manager.
- **The pinned views rename too.** Press **F2** on Favorites, New Episodes, Continue Listening or the Inbox (or choose **Rename...** from its context menu) and give it your own name -- it follows you into the Podcast Manager as well. A renamed view's menu gains **Reset Name**; entering a blank, or the shipped name itself, also resets it. Shows and episodes deliberately refuse F2: their names come from the podcast's own feed.
- **Episodes without leaving the main page.** Every show in the tree can be expanded (Right Arrow) to reveal its episodes, newest first, right where the show sits -- no detour through the Manager to reach one particular episode. Shows start collapsed so the tree reads as a list of shows rather than a wall of episodes. **Enter on an episode plays that episode**; Enter on the show itself still plays the show's next unplayed episode. An episode row's context menu offers **Play Episode** (Stop, while it is the one playing) and **Download Episode** -- the file lands under your Download location as `show-title\episode-title.mp3`, so it has a name that means something outside the app.
- Buttons: **Play** (becomes **Pause** while playing, **Resume** while paused -- one transport control that is never dead), **Stop**, **Add to Favorites** (becomes **Remove from Favorites** when the playing show is already a favorite), **Open Manager...**, **Add Podcast...**.

## The Podcast Manager

The Manager (Ctrl+M) is where episode-level life happens, and it is the same Manager QUILL ships:

- **Pinned views** lead the folder tree: **Favorites**, **New Episodes**, **Continue Listening**, and the **Inbox**.
- **The Inbox** triages episodes rather than shows: route a show to the Inbox and its new episodes land there; file episodes into your own nested folders. Your first manual filing per show is remembered and applied automatically (Forget reverts it). **Which shows go to the Inbox** (Podcast Settings) decides how the Inbox is filled: *Only the shows I choose* -- the default, and what QUILL Cast has always done -- or *Every show except the ones I exclude*, which suits a large subscription list you triage rather than a few shows you follow closely. Choosing the second reuses the same per-show mark and reads it the other way round, so the menu item on a show changes to **Keep This Show Out of the Inbox** and says so when you use it. Nothing moves unless you change the setting.
- **"View cross-show lists as"**, a combo box next to "Sort episodes", offers three ways to see the Inbox and every other cross-show list (New Episodes, Continue Listening, Favorites): **Grouped in list** (the default -- each show's episodes cluster together, read one podcast's backlog at a time), **Flat list** (everything as one stream, sorted purely by date across every show at once), or **Folders per podcast** (real expandable tree nodes, one per show, right under the pinned view). The Sort Episodes control now applies to these cross-show lists too, not just a single show's own episode list -- and it's per-podcast: select a show (or its Folders node) and change the sort to override just that podcast, leaving everyone else on the shared default.
- **Play Queue**: Play Next or Add to Queue on any episode; the queue auto-advances, survives restarts, and reorders from the keyboard (Move Up/Down, or Mark then Move for long hops).
- **Playlists**, below the Play Queue in the tree: saved, named episode lists, distinct from the (transient) Play Queue and the (fixed) pinned views. Right-click Playlists for **New Playlist...** (manual -- add episodes one at a time via **Add to Playlist...** on any episode's context menu) or **New Smart Playlist...** (rule-based -- which shows, episode status, how recent, how long, and how to sort, re-resolved live every time you open it). Edit Rules..., Rename (F2), and Delete round out each playlist's own context menu.
- **Search Everywhere** searches shows, episodes, your notes, and fetched transcripts at once and jumps to the result. Emptying the search box empties the results at once -- stale matches for a query that is no longer there never sit around looking current. (Add Podcast's search behaves the same way.)
- **"Sort shows"** orders the podcasts within each folder: Title A-Z, Title Z-A, Most unheard first, Recently updated first, or **Your custom order** -- the hand-arranged order from Sort Podcasts and Alt+Up/Alt+Down. The dropdown opens on whatever the library is actually sorted by, so the Manager and the main window never disagree.
- **Transcripts**: when a feed provides one (Podcasting 2.0; VTT/SRT/JSON), save it to a file or open it -- cached for instant reopening. QUILL Cast never generates transcripts from audio; that stays in full QUILL.
- **Episode notes** timestamp the playing moment; Enter on a note jumps playback there.
- **Chapters, from wherever they exist.** QUILL Cast looks for chapters in three places, cheapest first: the feed's own chapters document, chapter markers inside the downloaded file, and the timestamps published in the episode's show notes (the familiar `00:12:34 Topic` lines). The Chapters list says which of those it came from, so marks worked out from show notes are never presented as the publisher's own. The Chapters button is offered whenever any of them could exist, not only when the feed publishes a chapters file.
- **Filter episodes by "In progress"** -- the ones you have started but not finished -- alongside All, Unplayed, Played, Downloaded, and Not downloaded.
- **Local podcasts**: turn folders of your own audio into shows, with optional watched folders that pick up dropped files.
- **Always Sync**, **auto-trim silence**, **normalize loudness**, and a live **volume boost** that respects the Sleep Timer's restore volume.
- **Download All Episodes / Remove All Downloads / Remove All Episodes** on a show's context menu: Download All queues everything not already downloaded or in progress, no extra confirmation needed. **Remove All Downloads** is its symmetric counterpart -- it deletes the show's downloaded files and only the files (episodes, played state, and positions stay; anything marked Keep This Episode is skipped and the announcement says how many were kept). Remove All Episodes confirms first, then -- only if the show has downloaded files -- asks separately whether to delete those too; the show itself stays subscribed either way.

## What each row says

An episode list is read out one column at a time, so the columns *are* the
sentence you hear on every row. **Subscriptions > Choose Columns...**
(Ctrl+Alt+Shift+C) is where you decide it -- for the episode list, for
Downloads, and for Add Podcast's search results.

The window holds two lists: **Shown, in the order they are read** and
**Hidden**. Move Up and Move Down (or Alt+Up and Alt+Down) rearrange the shown
ones. **Hide** takes a column out of the row altogether -- not to the end of it,
out of it, because a column that is still there is still spoken. **Show** puts
one back where its place in the order says it belongs.

Underneath the lists, **A row will read:** spells out the sentence one row will
say with the settings exactly as they stand, so you can hear a change before
pressing OK.

**One column in each list is pinned** -- the episode's title, the podcast's
name -- because a row with nothing to identify it is a row you cannot choose
between.

**Some columns are offered but start switched off.** The episode list can also
show **Podcast** (worth having in a list that spans several shows, and noise in
a list of one), **Time Left** on an episode you have started, and
**Downloaded**. Add Podcast's results can also show the **Feed Address**, which
is what tells two shows with the same name apart.

**Reset This List** puts one list back the way it shipped. Your choice is saved
per list and kept between sessions. Changing it while the Manager is open takes
effect there and then, rather than next time.

## Private feeds (username and password)

Some feeds -- Patreon supporter feeds, premium and members-only shows, private company or organization feeds -- protect their RSS address with a username and password (HTTP Basic authentication). QUILL Cast handles them end to end.

**Subscribing.** Add the feed exactly as you would any other: Subscriptions > Add Podcast..., paste the address into **Add by Feed URL**, press **Add**. If the feed asks for a sign-in, a small **Feed Credentials** dialog opens with focus on the username field: enter the username and password your podcast provider gave you (Patreon and similar services show these on the same page as the feed address) and press OK. QUILL Cast retries with your credentials and the subscription continues normally. Wrong password? The dialog reopens with your username kept, and says so.

**Changing or clearing credentials later.** Open the show's context menu (Shift+F10 in the main window's library tree or the Podcast Manager's tree) and choose **Feed Credentials...** -- the same dialog, username prefilled. Enter a new password to replace the stored one, or press **Clear Credentials** to remove both and make the show public-only again. Every save and clear is announced.

**What signing in covers.** Once a show has credentials, QUILL Cast signs in automatically everywhere that show touches the network: feed refresh, episode downloads, streaming playback, and feed-provided transcripts and chapters. One deliberate security rule: credentials are only ever sent to the same host as the feed itself. If a show serves its audio from a different host (a public content network, say), those requests carry no credentials -- your password is never broadcast to third parties.

**Where the password lives.** Never in a plain file. On an installed copy it goes into Windows Credential Manager, protected by your Windows account. On a portable copy it is encrypted (Windows DPAPI) inside the `data` folder on your stick. It never appears in `podcasts.json`, never in logs, and **Export OPML** never includes it -- an exported subscription list is always safe to share.

**Portable caveat.** DPAPI encryption is tied to your Windows account and machine. Move the portable stick to a different PC or user account and your subscriptions all come along, but stored feed passwords cannot be decrypted there -- the first refresh of a private feed will say sign-in failed, and you re-enter the password once via Feed Credentials....

## Menus

### Subscriptions (Alt+S)

Open Podcast Manager... (Ctrl+M), Add Podcast..., Import OPML..., Export OPML..., New Folder... (creates a library folder without opening the Manager), **Sort Podcasts** (a submenu -- see below), Add Local Podcast..., Scan Watched Folders, Subscribe to ACB Media Podcasts, Podcast Settings..., **Podcast Index Credentials...**, **Quick Actions...**, **Export My Data...**, **Delete All Podcast Data...**, **Resume Last Episode on Launch** (check item -- the appliance switch), **Preferences...** (Ctrl+,), Send to Tray (Ctrl+W), Exit.

**Sort Podcasts** decides how your shows are ordered everywhere they are listed: **Ascending (A to Z)**, **Descending (Z to A)**, or **Custom Order**. Custom order is the one you build by hand: **Alt+Up / Alt+Down** on a show in the library tree (or Move Up/Down in Custom Order on its context menu) nudges it among its folder's neighbours. The first move switches to custom automatically -- starting from the order already on screen, so nothing jumps -- and the radio items here always show which mode is live.

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
- **Start loading the next episode before this one ends** (off). When one queued episode ends and the next begins there is normally a pause while the next one is opened -- on a slow connection, several seconds of silence. Turning this on fetches the next episode's first moments while you are still listening to the current one, so it simply carries on. It is off by default because it uses data you have not asked for, which matters if you pay for it by the megabyte; it does nothing for episodes already downloaded, and nothing until you are near the end.
- **Which shows go to the Inbox**: *Only the shows I choose* (the default) or *Every show except the ones I exclude*. The second is the one to pick if you follow a great many shows and use the Inbox to sort through them; the first if you follow a few closely. Whichever you choose, the per-show Inbox caps keep it from becoming a wall of episodes.
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

A live now-playing line, **Player Information...**, **Continue Listening...**, **About This Episode...**, then Play/Pause (Ctrl+P), **Stop** (Ctrl+.), **Mute/Unmute**, **Volume Up** (Ctrl+Up) and **Volume Down** (Ctrl+Down), Next Chapter, Previous Chapter, **Skip Forward** (Ctrl+Right), **Skip Back** (Ctrl+Left), **Speed Up** (Ctrl+Shift+Up), **Speed Down** (Ctrl+Shift+Down), **Reset Speed to Normal** (Ctrl+Shift+0), **Stop After This Episode**, Add Episode Note..., **Play Queue...** (the same reorderable queue the Manager offers, now one keystroke away), **Mark All as Played...**, **Listening Statistics...**, a **Recently Played** submenu (your last fifteen episodes, newest first, playable inline), Sleep Timer..., **Sleep at End of This Episode**, **Extend Sleep Timer 5 Minutes**, **Sound Enhancements...**, and **Skip Settings...**. The volume keys match Quill Radio's, so the two apps behave the same way.

**Speed Up / Speed Down / Reset Speed** move playback speed in tenths anywhere from 0.5x to 5.0x, and say both the new speed and whose it is -- the playing podcast's own if something is playing, or the shared default when nothing is. The same range is in Podcast Settings and in Settings for This Podcast...

**Stop After This Episode** is a one-off: it stops instead of auto-advancing, clears itself when it fires, and never survives a restart. What normally follows an episode is set by the two "When an episode finishes" switches in Podcast Settings -- with both off, playback simply stops at the end of the episode you started.

**Mark All as Played...** clears a podcast you have given up on. It confirms, naming the show and the count; the episodes stay in your library, downloaded files are untouched, and they leave the Inbox because the Inbox is unplayed episodes. The confirmation carries a **"Don't ask me again"** checkbox, and the answer is shared with Quill Radio -- check it in either app and both stop asking (cancelling with the box ticked changes nothing).

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

## When a podcast re-publishes an episode

Publishers sometimes re-issue an episode: a corrected file, a re-cut, one pulled
and put back. QUILL Cast notices, and if the episode had already been trimmed
out of your Inbox it comes back, announced as what it is -- "Episode 42 was
re-published by The Daily, so it is back in your Inbox" -- rather than as a new
episode, which it is not.

Three kinds of episode are deliberately left alone, and they are the same three
the Inbox limits already exempt:

- one you have **played** -- you are finished with it, and a re-cut does not
  un-finish it;
- one you have **started** -- having it reappear as though it were new would
  misrepresent your own history with it;
- one you have **queued** -- you already decided when to hear it, and the Inbox
  is for episodes still waiting on that decision.

An episode you filed into an Inbox folder by hand stays where you put it too. A
refresh should not argue with decisions you have already made.

## Inbox limits

An Inbox holding every unplayed episode of every routed show forever is a second library, not a triage surface. Any podcast can now cap it: **keep at most N episodes**, and **drop episodes older than** 6 hours up to 2 weeks. A global default for the count lives in Podcast Settings.

Two rules make the caps safe:

- **Trimming never deletes anything.** A trimmed episode leaves the Inbox and stays unplayed in its show's own episode list, downloaded file and all.
- **Three kinds of episode are never trimmed**: anything you have started, anything in your Play Queue, and anything you filed into an Inbox folder by hand. They do not even count toward the cap.

## Listening statistics

**Listening Statistics...** (Episode menu) reports time listened for this week, month, year, or all time; how much extra content faster playback bought you; how many episodes you finished; and a breakdown by podcast, most-listened first.

It is a read-only text field you arrow through line by line and can copy -- the same shape as Player Information. Durations are read as language ("3 hours, 47 minutes"), never as a clock face, because a screen reader reads `3:47:00` as a time of day.

**Export CSV...** saves every session for a spreadsheet. **Clear Statistics...** deletes the log and nothing else.

**How long the log is kept is yours to choose** (Podcast Settings): don't keep one, 30 days, 90 days (the default), a year, or forever. Choosing not to keep one stops the writing rather than deleting afterwards, which is what somebody choosing it asked for. The log never leaves this computer either way.

**Year in Review...** is a few sentences about a year of listening -- how long, what you listened to most and what share of the year each show was, your busiest month, what faster playback bought you, and how many days you listened on. It is text you can arrow through, copy, or save, rather than a dashboard: a table read aloud is a list of numbers with their meanings three columns away. Anything the log cannot honestly support is left out rather than printed as a zero.

**Listening streaks** -- how many days in a row you have listened -- are **off unless you ask for them** (Podcast Settings). A streak is a nudge, and a nudge nobody asked for is pressure. When they are on, they appear in the statistics readout and in Year in Review. A run that ended yesterday is still current: your streak is never reported as broken before you have had a chance to listen today.

One number is deliberately absent: time saved by Smart Speed. The silence-trimming path cannot honestly report how much silence it dropped, and an invented figure would be worse than no figure at all.

## The first time you open it

QUILL Cast starts with three short screens: what it is, how to add your first
podcast, and two things worth knowing before you begin. Three, not seven -- there
is no account to make and nothing to consent to, so there is nothing to page
through.

Each screen is a text box you can arrow through and copy, so a sentence you
missed is there to read again rather than something to ask the app to repeat.
**Skip** leaves at any point and counts as done -- you will not be asked again.
And if you already have podcasts, from an import or a backup you restored, you
never see it at all.

### Tips

After that, the first time you reach somewhere one non-obvious fact would change
what you can do, QUILL Cast says a single sentence about it -- the difference
between the Play Queue and the Inbox, that most settings can differ per podcast,
that a worked-out chapter list can tell you how it was found.

Each tip appears **once, ever**. They are never a dialog, never take the
keyboard, and go to your braille display as well as to speech. One checkbox turns
them all off for good, and **Show Tips Again** brings them back if you want the
refresher later.

## Chapters you can skip

QUILL Cast finds chapters from three places -- the feed's own chapter document, markers inside the audio file, and timestamps in the show notes. From 1.1 you can also skip them.

Open **Chapters...** for the episode you are playing and use **Skip This Chapter** to mark the ad break, the sponsor read, or the outro. Playback jumps past it and says "Skipping chapter:" and its name. Consecutive marked chapters are stepped over together, and marking everything to the end simply finishes the episode normally, so auto-advance and delete-after-play still fire. **Skip Nothing** clears every mark.

Marks last for the listening session only -- a chapter you skipped in yesterday's episode says nothing about today's -- and the button only appears for the episode actually playing.

### Chapters from a running order written in prose

Most podcasts publish no chapter list, and a good many of them do something
almost as useful that QUILL Cast used to throw away: they describe their running
order in the show notes.

> "high school student Tyler Juranek begins a series of short reviews he calls
> Techie Tidbits ... Next, we visit with Gerry Chevalier about the newest release
> of the Victor Reader Stream ... Finally, Matt Roberts brings us part one of a
> demonstration on accessing DVR from Dish Network"

That is a running order: four segments, named, in sequence, **written by a
person**. Cast now takes each described topic and finds where in the episode its
distinctive words actually arrive. The result is a chapter list whose *titles* a
human wrote and whose *times* were worked out -- the only route to authored
titles that involves no AI at all. On the episodes this was measured against,
the marks landed within 9 and 15 seconds of the real section starts.

Where the notes describe two or more segments, Cast uses them and stops. Four
chapters that are mostly right beats fourteen that are mostly wrong.

### How hard to look, and what each level really does

The **Chapters** group in Podcast Settings leads with the only question most
people will ever want to answer, and everything else follows from it:

- **Quick** -- only what is already here: a published list, or a transcript you
  already have.
- **Thorough** (the default) -- fetches a published transcript if the episode has
  one, and works the sections out of the words. **If there is no transcript it
  says so rather than guessing.** Listening for pauses used to be Thorough's
  fallback and no longer is: measured against hand-built reference chapter
  lists, it scored 0.06 where cutting the episode into equal slices with no
  knowledge of it at all scored 0.15. An answer worse than dividing by *n* is
  not an answer.
- **Deep** -- transcribes the episode on this computer and works the sections out
  from that, then keeps the pause scan as a last resort, because somebody who
  chose Deep has said they would rather have a weak answer than none. The engine
  ships with the app: 40 MB, CPU-only, no download and no network. It was chosen
  over models thirty-five times its size because it *scored better* and ran 4.7
  times faster -- and not on transcription quality. Its lines break at natural
  pauses, so its edges are already plausible section starts.

Beneath the effort control, a sentence says exactly what that level will do, and
it changes as you change the choice. The rest of the group switches individual
sources on and off -- show notes, transcript, pause scan -- and **off means off**
at any effort level. There is also **Chapter preview length**, which is how much
Review Chapters plays either side of a mark, and whether Cast says how many
chapters it found.

**Work chapters out** decides when any of this happens at all: never, only for
episodes you have downloaded (the default), or for every episode. A chapter list
the podcast published is always shown whatever this says.

### When an episode has no chapters at all

Most episodes do not publish any. QUILL Cast can work them out, and -- new in this
version -- the sections it works out are now **named after what they are about**
rather than after their own first few words or as "Section 4", which told you
nothing.

It looks in the cheap places first and stops at the first real answer: the feed's
own chapter document, chapter marks inside the downloaded file, the timestamps in
the show notes, the moments the podcast marked as worth hearing, and anything
worked out on a previous run. **A chapter list published by the podcast always
wins** over anything worked out -- a person wrote those titles.

Marked moments are new here, and they are the last of the authored sources for a
reason: a podcast that marks two highlights in an hour has answered "what is the
good bit" completely and "how is this episode laid out" barely at all. So they
are used only when nothing better was published, each keeps its own real end
rather than running on to the next one, and the list says what they are --
**Moments this podcast marked** -- so a set of highlights is never mistaken for a
chapter list covering the whole episode. One marked moment is enough to offer:
it is still a place worth jumping to.

Show notes are worth a word of their own, because a publisher who wrote chapter
timestamps has already done the work for you. QUILL Cast now reads the shapes
people actually write -- `00:00`, `1:02:03`, `12.34`, `1h05m`, numbered and
bulleted and bracketed lists, the time at the *end* of the line ("Introduction —
00:00"), and show notes that arrive as web markup rather than plain text.

When none of those exist, **Podcast Settings > Chapters** decides what happens,
and there is one thing to choose: **how long are you willing to wait?**

- **Quick** -- only what is already here. Instant.
- **Thorough** (the default) -- fetch a published transcript if there is one, or
  listen to the audio for pauses. Seconds.
- **Deep** -- transcribe the episode on this machine, then work the sections out
  from what was said. Minutes, and you can stop it at any point.

You can also say **when** to bother at all -- never, only for episodes you have
downloaded (the default), or always -- and switch each individual method off. Off
means off: if you say never scan the audio, it never scans the audio, whatever
the effort is set to. And if you would rather not have worked-out chapters at
all, one setting turns the whole thing off and you will not hear about it again.

**Nothing interrupts you.** The work happens in the background while you listen.
While it runs, the menu item says so in its own words -- "Chapters (working them
out...)" -- and opening it says "Chapters are being worked out. I will say when
they are ready" rather than showing you something to wait in front of. When it
finishes you hear one short sentence, and the list is there when you want it.

**And you can ask how they were found.** Chapters that were worked out rather
than published say so, and the summary tells you which method found them, how
much was examined, and how confident it was -- "12 sections, worked out by
listening for pauses in the audio. Examined: 48 minutes of audio. Confidence
41%." A worked-out chapter list is a guess, and you are entitled to know how good
a guess it is.

## What else the podcast published

Podcast feeds can carry a good deal more than a title and an audio file, and
until now QUILL Cast read two of it -- chapters and transcripts -- and threw the
rest away while it was sitting right there in bytes it had already downloaded.

**About This Episode...** (the Episode menu, and any episode's context menu in
the Podcast Manager) is where the rest of it now lives. It opens as tabs, and a
tab is only there when it has something in it -- no empty People tab on a podcast
that publishes no credits.

- **People.** Who is on this episode, and who makes the podcast. Each row reads
  as a sentence -- "Bob Brown, guest (this episode)", "Alice Adams, host (this
  podcast)" -- and where the publisher gave a link, Enter opens it.
- **Highlights.** The moments the podcast marked as worth hearing, each with what
  it is called, when it starts and how long it runs, in words: "The good bit --
  1 hour 2 minutes in, 1 minute long". These are chapter marks written by a
  person, so they also appear in the chapter list, where Enter plays from one.
- **Live.** Some podcasts carry a live stream inside their feed. If one is on the
  air, Enter plays it through the ordinary player -- the same transport, the same
  volume and pause keys as everything else. One that has finished says so instead
  of pretending to be playable.
- **Other Audio.** A second version of the same episode where the publisher
  offered one, usually a smaller file for a slow or metered connection.
- **Recommended.** The podcasts this show recommends. Subscribing here is a real
  subscribe -- QUILL Cast fetches the feed and the show arrives with its proper
  name, its artwork and its episodes.
- **Support.** Where the podcast asked to be supported. QUILL Cast opens the page
  in your browser and has nothing whatever to do with what happens there. Nothing
  in QUILL Cast costs money and nothing here changes that.
- **Place.** Where the episode is about, as text. No map, and none is wanted.

The command speaks a one-line summary before the window opens -- "Extra details
for this episode: 2 people, 1 marked moment, 1 recommended podcast" -- so if all
you wanted was to know whether there was anything, you have your answer without
opening anything. On an episode whose podcast published none of it, the window
still opens and says so: "this podcast publishes no extra details" and "QUILL
Cast cannot read them" are very different things to know, and a greyed-out menu
item would leave you guessing which one it was.

**The button says what it will do.** It changes as you move down a list -- *Open
in Browser*, *Play*, *Subscribe to This Podcast* -- and on a row with nothing to
do it reads *Nothing to Open* and is disabled, rather than being pressed and
quietly declining.

## Finding a podcast to subscribe to

**Add Podcast...** searches a **Directory**, and there are two.

- **iTunes** is the default and needs nothing. It indexes very nearly every
  podcast there is.
- **Podcast Index** answers out of the box. QUILL Cast carries its own
  credential for it, so there is nothing to register for and nothing to set up,
  and **Both** is what a new library searches. It is the index the Podcasting
  2.0 tags were defined for -- chapters, transcripts, funding, credits -- and it
  is where independent, self-hosted and de-listed shows live, which is why
  asking both finds shows a store alone does not.
- Searching both merges results by feed address and says where they came from:
  "12 results: 9 from iTunes, 3 from Podcast Index." A directory that fails does
  not fail the search -- you keep what arrived, and the status line names the
  one that was quiet.

You can still use a key of your own. Register free at podcastindex.org and put
the key and secret into **Subscriptions > Podcast Index Credentials...**; yours
takes precedence over the built-in one, and goes into Windows' credential store
rather than a settings file, scrubbed from crash reports. That is now a way to
use your own quota rather than something you must do before the feature works.

## Looking at a podcast before subscribing

A search result is a title, and subscribing to a title is how you end up
unsubscribing from a title a minute later.

**Preview** (or just Enter on a result -- Enter previews now rather than
subscribing) opens the show read-only: what it is, who makes it, how many
episodes it has, its own description as a text field you arrow through, and its
ten most recent episode titles with their dates. Between them those answer *is
this the show I meant*, *is it still running*, and *is it in my language*.
**Subscribe** is on the same window when the answer is yes.

## Doing something to a whole folder

A folder in your library is somewhere you listen from, not only somewhere shows
are filed. Right-click one (or press the applications key) for:

- **Play All Unplayed** -- the newest unplayed episode of *each* show in the
  folder, queued and started. One per show on purpose: a folder of forty shows
  holds hundreds of unplayed episodes, and a queue of hundreds is not a queue.
- **Add All to Queue** -- every unplayed episode in it, for when you meant it.
- **Move Up** / **Move Down** -- reorder folders among their neighbours, with
  the new position spoken ("News, 2 of 5").
- **Folder Settings...** -- set the queue-expiry window, Inbox routing and
  playback speed for every podcast in the folder at once. Each control starts at
  "change nothing", so nothing is applied by accident, and it says how many
  podcasts it changed. The values are written into each podcast, so a show you
  move into the folder afterwards keeps its own settings -- there is one place a
  setting comes from, not two.
- **Export This Folder as OPML...** -- hand one folder and its sub-folders to
  another machine or another person, without exporting your whole library.
- **Check All Feeds Now** -- ask every subscribed podcast whether it has
  published anything new. See "Checking for new episodes" below.

A folder always means everything beneath it. Playing "News" plays what is in
"News/Local" too.

**Move Several Podcasts to Folder...** (on any podcast's menu) files a batch in
one step: arrows move through the list, Shift and arrow extend the selection,
Ctrl and Space adds or removes one, and Select All takes the lot. It says how
many are selected as you go, then asks once which folder they go to.

## Checking for new episodes

There are two questions, and QUILL Cast answers them separately.

**"Anything new in this one?"** -- **Refresh Feed** on a podcast's own context
menu. It works on any show that has a feed address, including one you have
paused.

**"Anything new anywhere?"** -- **Check All Feeds Now**, on a folder or on the
tree below your podcasts. It says how many feeds it is checking before it
starts, because the answers arrive show by show over the next few seconds.

Both of these are things you asked for, so both check paused shows as well. A
pause means *leave this show alone* -- no automatic check, no automatic
download, for a finished show or a seasonal one between seasons -- and it never
means the show is out of reach. That it costs nothing you cannot undo with one
keystroke on the row in front of you is what makes a pause safe to use freely.

**Checking without being asked** is a separate switch, in Podcast Settings, and
it is off by default. Turn it on and pick a cadence -- from every 15 minutes to
once a day -- and Cast will look on its own. A check reads episode lists: it
starts no downloads by itself unless you have also asked for automatic
downloads, and it never changes what you are playing. Check All Feeds Now works
whether or not that switch is on; it is not the same question.

**If you also run Quill Radio**, the two apps will not ask the same publisher
twice. Each keeps its own cadence on purpose -- otherwise turning the check on
here would turn it on there, with no way to say "let Radio do it" -- but they
share the record of when a check last happened, so whichever one goes first, the
other finds the work already done and stays quiet. There is nothing to
configure.

## Lineups: saving the order you listen in

A lineup is "the order I listen in on a Tuesday" -- four shows, in a sequence
that took a minute to arrange and disappears the moment the queue is used for
something else.

In the Play Queue window, **Save Lineup...** keeps the current order under a
name you choose. **Apply Lineup...** puts it back later.

Applying **moves; it never replaces**. The queue you have is a decision you
made, so:

- every episode in the lineup that is still available and unplayed moves to the
  **front**, in the lineup's order, whether it was already queued or not;
- everything else in the queue **stays**, in the order it already had, behind
  them;
- anything you have since played, or that has left your library, is **skipped**
  -- and counted, so you hear "applied 3, skipped 2" rather than a silence that
  looks the same whether it worked or half-worked.

Episodes keep the age they had, so queue expiry still measures how long
something has really been waiting rather than how recently it was reordered.
Re-saving a lineup under a name you already used replaces it: saving "Tuesday"
again means *this* is Tuesday now.

Lineups are saved playlists, so everything the Playlists branch does works on
them -- rename, delete, and they travel in an export.

## Selecting more than one episode

Every episode list takes a multiple selection, the Play Queue included. Shift
and an arrow extend the selection, Ctrl and Space adds or removes one, and
Select All takes the lot. The count is spoken as you go, and any verb that acts
on the selection says how many rows it touched -- "Removed: 6 episodes eligible,
6 done" rather than "Removed".

## Being told when downloads finish

Off by default, in **Podcast Settings**: *Notify me when downloads finish*.

One desktop notification when the download queue goes **quiet**, not one per
episode -- a forty-episode batch is one event to you, however many rows it had.
Nothing leaves this computer; this is the Windows notification centre, not a
service and not an account.

It goes through **quiet hours** like any other background news. The downloads
themselves still run; what is held back is the interruption about them. That is
the whole point: an overnight batch was otherwise the one thing here that could
wake you at three in the morning.

## Grouping the Play Queue

The Play Queue has a **Group by** control: Nothing, Podcast, or Library folder.

Grouping never changes the play order -- only how the list reads. A group header
announces itself as one ("News, group, 4 episodes"), and no action can act on a
header by mistake: Play, Move and Remove all ignore them.

## Sharing where you are in an episode

**Share This Moment** (any episode's menu) copies two things at once:

- a sentence -- "Blind Abilities, Episode 214, at 41 minutes 12 seconds";
- a link that reopens the episode at exactly that second.

The sentence is not an afterthought. A link nobody can open is worse than a
sentence anybody can paste, and the person you are sending it to very often does
not have QUILL Cast. The sentence works in an email, in a message, and read down
the phone.

Opening a link somebody sent you plays that episode from that second -- provided
it is a podcast **you already subscribe to**. A link for a podcast you do not
follow says so and does nothing at all: a link cannot add a subscription, and
QUILL Cast never fetches a web address because a link asked it to.

## Carrying your place to another device

**Carry My Place Between Machines...** now offers two ways to share, and they
are separate switches because they carry different exposure.

- **Encrypted, for my other QUILL machines** -- what this feature has always
  been. Locked with your recovery phrase; only a machine that has the phrase can
  read it.
- **A plain file other apps can read** -- a small published format called
  *Listening Places* that other podcast apps can read and write, in the same
  folder. It needs **no recovery phrase at all**: a feature nobody can set up
  syncs nothing.

Both work through a folder you already sync -- inside Dropbox, OneDrive, Google
Drive, iCloud Drive, Nextcloud, Syncthing, or a network share. There is no
account and no server, and QUILL holds nothing.

What the plain file gives away: every episode in it is identified by a hash, so
somebody with access to the folder learns how many things you listen to and
roughly when, and nothing about what. **Include episode and file names** is a
third switch, on by default -- with it on, a disagreement can say "you and your
phone disagree about Episode 214" instead of reading out a hash; with it off,
the folder learns less.

Two things worth knowing about how it behaves:

- **The most recent position wins, not the furthest.** If you jump back twenty
  minutes to hear something again and then open the episode on the laptop, the
  furthest position is exactly the wrong answer.
- **It reads at launch and when you press Sync Now, and at no other time.** A
  position arriving mid-session would move your playhead with no warning, which
  is unacceptable and worse when you cannot see it happen. The cost is that a
  change made elsewhere while Cast is open waits until next launch. The promise
  being kept is that your place is right when you sit down.

## Picking up whatever you were in the middle of

**Continue Listening...** (the Episode menu) is one list of everything you
started and did not finish, newest first, with the kind named on every row --
"Rome, The Rest Is History, podcast, 20 minutes in, 33% through". If you also
use Quill Radio, an unfinished LibriVox chapter or recorded programme appears in
the same list, because the question people actually have is *what was I in the
middle of*, not *which app was it in*.

**Resume** starts it where you left off. **Forget This One** drops the saved
place and takes the row out -- the episode stays unplayed, because "I am not
going back to this" and "I finished it" are different things to say, and a
resume list you cannot clear is one that fills with things you abandoned on
purpose and stops being useful.

Anything the app you are in cannot play -- a radio recording, in Cast -- is
still listed, but Resume is unavailable for it and says so rather than doing
nothing.

## Doing something to a lot of episodes at once

Select several episodes in the Manager's list (Shift or Ctrl with the arrow
keys, or Ctrl+A) and the context menu gains actions for the whole selection:
**Add N Episodes to Queue**, **Download N Episodes**, **Mark N Episodes as
Played**, **Add N Episodes to Playlist...**, and **Remove N Downloaded Copies**.

**File N Episodes to Inbox Folder...** is the one the Inbox needed most, since
triage is what the Inbox is for and triage happens a handful of episodes at a
time. It asks **once** which folder and files the lot; if that sets a show's
remembered folder, it says so once rather than once per episode.

Removing downloaded copies never removes the episodes: freeing space and
unsubscribing are very different things to want, and the episodes stay in your
library with their played marks and positions, ready to download again.

## Opening a subscription list from Explorer

An OPML file is how one podcast app hands its whole subscription list to
another. If you let the installer associate `.opml` files with QUILL Cast (a
tick box during setup, **off** unless you ask for it), double-clicking one opens
Cast straight into the import, and Cast says which file it is opening. You can
still use **Import OPML...** at any time, and a list exported with an `.xml`
extension imports perfectly well that way.

Uninstalling QUILL Cast gives the file type back rather than leaving a dead
handler behind.

## Scanning forward through an episode

Skipping forward in fixed jumps answers *"get me past this"*. It does not answer
*"where does this bit end?"* -- for that you need to hear the audio going past.

**Hold Shift+Right** and playback runs at four times speed. Let go and it drops
back to **exactly** the speed you were listening at: if you listen at 1.5, you
get 1.5 back, not 1.0. Both edges are announced -- "Scanning forward, 4 times
speed", then "Back to 1.5 times speed" -- because a player left at four times
speed without saying so is indistinguishable from a broken one. Moving to
another window, or closing the app, ends a scan too.

Four times is deliberate: fast enough to cover a minute in fifteen seconds, slow
enough that speech is still recognisable as speech.

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

## Bookmarks: keeping a moment

**Bookmark This Moment** (Episode menu, or Ctrl+Alt+A) marks where you are in
one keystroke. **Bookmarks...** (Help menu, or Ctrl+Alt+Shift+J) opens the
list, where Enter goes to the highlighted one.

**No note is required.** Episode notes used to insist on text, so "I was here"
-- the commonest kind of bookmark there is -- was not something you could
record. It is now. Add a note later with **Edit Note** if it turns out there
was something to say.

The other verbs in the list: **Share** copies the place, the note and what it
is in, together; **Delete** takes everything selected and says how many;
**Export...** writes the lot as Markdown, grouped by what each bookmark is in.

**The list is shared with Quill Radio.** A bookmark you make here is in Radio's
Bookmarks window and the other way round -- no sync and no account, exactly the
way your place in an episode already travels between the two. Rows this app
cannot open, such as a bookmark Radio made on a live station, still appear with
**Go There** dimmed and a reason. Hiding them would leave you wondering where
your bookmark went.

## Getting an episode back out

Four commands, all of them **Quick Actions** entries -- so they can be reordered, made the Enter default, or reached on Ctrl+1 to Ctrl+9 like everything else on those menus.

**Save Episode Audio As...** saves a copy of the episode's audio wherever you choose. It copies rather than moves: QUILL Cast goes on managing its own downloaded copy, so retention, the storage cap, resume and Remove Downloaded Copy all still apply to it, and your saved copy sits outside all of that. The filename is suggested as "Show - Episode"; characters Windows will not accept are replaced, and very long titles are shortened, so the Save dialog never opens with a name the system would reject.

If the episode is not downloaded yet, it says **"Preparing audio file for export"**, fetches it, and opens the save dialog when the file arrives -- you press the key once rather than twice. It used to ask you to run the command again afterwards, which made you the scheduler. The wait can end four ways and it says which: the file arrives, the download fails and names the reason, you cancel it from the Downloads window, or it takes long enough that going on waiting silently would be indistinguishable from a hang -- in which case it says the download is carrying on without it and to use the command again once it has finished.

**Copy Podcast Link** copies the show's feed address, next to the existing **Copy Episode Link**. The feed address rather than the show's website, because a feed address is what another podcast app can be given. A local podcast has no feed and says so.

**Show in File Explorer** opens the folder holding a downloaded episode with the file selected. An episode you are streaming has no file to show, and says that instead of opening some other folder.

**Copy File Path** puts a downloaded episode's location on the clipboard, for an upload box, a terminal, or a message to somebody -- the half of handing a file off that needs no file manager at all. It reads back the file name and the folder rather than the whole path, because a path spoken aloud is mostly separators. An episode with no file says so: a path to nothing is worse than no path.

## Picking up where you left off

Every episode remembers where you stopped, and playing it again resumes there.

The position is written every fifteen seconds while you listen, not only when
you pause or quit — so if QUILL Cast is closed the hard way, or the machine
loses power, the most you lose is a sentence. **Resume Last Episode on Launch**
(Subscriptions > Preferences) goes one step further and picks the last episode
back up the moment the app opens.

An episode you finish is marked played and its position cleared, so it starts
from the beginning if you ever play it again.

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

## Skip Silence

**Ctrl+Shift+9** shortens the long pauses in what is playing. QUILL Cast has
had this as **Smart Speed** in Podcast Settings for a while; what it did not
have was a way to reach it while listening, which is the only moment anybody
forms an opinion about it.

It applies to the playing podcast, or -- with nothing playing -- to every
podcast, which is the same scope the speed keys use. It takes effect on the
episode in progress and keeps your place: somebody forty minutes in who turns
it on is not sent back to the beginning to get it.

Quill Radio has the same key for the same thing.

## Finding an episode inside one show

The episode list has a **Find** box beside its filter. Type into it and the
list narrows to the episodes whose **title or show notes** contain what you
typed -- descriptions included, because a podcast that numbers its episodes
and describes them in the notes is exactly the one where searching titles
alone finds nothing.

It narrows what the filter and the sort already chose rather than replacing
them, so "unplayed episodes about the harbour, newest first" is three controls
you set independently.

Typing narrows the list quietly, so nothing talks over you. **Enter** says how
many matched out of how many were searched. A search that found nothing says
so and tells you the filter above may be the reason, rather than announcing a
zero and leaving you to work out why.

This searches the podcast you are on. **Search Everywhere** is the one that
crosses your whole library.

## Taking back the last thing you did

Press **Ctrl+Z** (Edit > Undo Last Action) and the last destructive thing you
did comes back: an unsubscribe, a Remove All Episodes, a Remove All Downloads,
a Mark All as Played, a deleted recording. It says what it brought back --
"Undid Unsubscribe. Brought back The Daily, with 412 episodes and 3 downloaded
files."

Three things worth knowing.

**It is one step, not a stack.** Undoing twice in a row does nothing the
second time; you get one, and the app says "Nothing to undo" rather than
quietly rewinding something older that you had forgotten about. If you have to
count how many times to press Ctrl+Z, you have been given a puzzle rather than
an undo.

**Deleted files come back, not just the intent to fetch them.** A file this
app deletes on your behalf is moved aside first, so an undo restores the bytes
themselves. Once you do the next destructive thing, the one before it is gone
for good -- which is what makes a single step safe to offer without asking you
first.

**Anything it cannot bring back, it says so in the same breath.** A private
feed's saved password, for instance, is deleted deliberately when you
unsubscribe; the undo brings the subscription back and tells you the password
has to be entered again.

Every action that can be undone ends its own announcement with "Ctrl+Z undoes
this", so you never have to remember whether this particular verb was one of
them.

## Why a menu item is dimmed

A greyed menu item used to be a dead end: a screen reader says "dimmed" and
stops, and the item itself says nothing about what would un-dim it. Every
dimmed item now carries its reason, which the status bar shows and which
readers that voice menu help speak:

- "Analyse Chapters: this episode is not downloaded yet, so there is nothing
  to analyse."
- "Download All Episodes: nothing to download, all 40 are already here."
- "Mark All as Played: nothing to mark, all 63 episodes are already played."

Pressing a Quick Action number on a dimmed row says the same thing, rather
than the old "that Quick Action is not available". So does the command palette
(Ctrl+Shift+P), where an unavailable command reads its reason instead of a
bare "(unavailable)".

Items dim rather than disappear on purpose: a verb the row genuinely owns is
better as a state you can hear than as something that comes and goes.

## Recent Problems

**Help > Recent Problems...** (Ctrl+Alt+Shift+P) is a list of what has failed
recently -- feeds that could not be read, downloads that died, streams that
dropped -- each with its reason and the time it happened.

It exists because announcements are transient. That is right almost always,
and wrong the one time the sentence you needed went past while you were in
another window: before this list, a spoken failure that was missed was gone
for good.

**Retry** tries the highlighted row again. **Copy All** takes the list as
text, which is what to paste into a bug report -- it contains addresses and
error messages, never passwords. **Clear List** empties it, and does not fix
anything or stop the same problem being recorded again next time it happens.

Nothing in the list leaves this computer.

## Quiet hours

**Help > Quiet Hours...** (Ctrl+Alt+Shift+Z) sets a window -- 22:00 to 07:00
by default, and a window may cross midnight -- in which the app stops speaking
*on its own*.

What that means precisely, because the name invites two wrong readings:

- Feeds are still checked, downloads still run, recordings still record.
  Nothing stops happening. Only the announcements about them wait.
- **Anything you press a key for still answers.** Press Play at three in the
  morning and you hear what is playing. Quiet hours never silence the reply to
  something you asked for; they hold back the speech nobody asked for.
- Failures always speak, whatever the window says. A recording that stopped at
  3 a.m. is exactly the thing somebody set an alarm-clock radio for.

There is one override: reminders can be let through anyway, since an alarm
clock is a reason to set one.

The window is shared with the other Quill listening apps, so you set it once.

## Moving your setup to another machine

**Help > Export My Setup...** (Ctrl+Alt+Shift+X) writes one file -- a
`.quillsetup` -- carrying what you have built up: your subscriptions, folders
and playlists, your favorite stations and saved places, your settings, your Go
To order, your Quick Action order, your scheduled recordings, your bookmarks
and any keys you rebound. **Help > Import My Setup...** (Ctrl+Alt+Shift+N)
puts them on the other machine.

An OPML export moves subscriptions and nothing else. This moves the rest.

Three things about the file:

- It is an ordinary ZIP with a readable manifest inside, so you can see what
  you are carrying between machines.
- **Passwords are not in it.** Private-feed sign-ins, server credentials and
  unlock codes stay on the machine that holds them and have to be entered
  again on the new one. The confirmation says so before it does anything.
- Importing **replaces** what is on this machine rather than merging with it.
  The confirmation names what the file holds and says this plainly; merging
  two libraries is a different job with different questions.

Close and reopen the app after an import, so everything is read back in.

## Your place follows you between Quill Radio and QUILL Cast

Both apps can play the same subscribed episode, and they now share one place
per episode on this computer. Pause an episode in one, open it in the other,
and it picks up where you left off -- and says so: "Picking up where you left
off in Quill Radio, at 1 hour 2 minutes 3 seconds."

The **later** decision wins, not the furthest through the episode. If you
skipped to the outro to check something and then went back to the middle, the
middle is where you are; an app that dragged you forward again on the grounds
that it was further in would be overruling you with arithmetic.

An episode either app has finished stays finished.

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
