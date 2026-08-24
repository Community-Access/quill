# Changelog

All notable changes to QUILL Cast are documented here. See `docs/release-notes-2.0.md` for the fuller narrative version of the latest release (Help > Release Notes opens it in the app), and `docs/release-notes-1.1.md` for 1.1.

## 2.0.0

### QUILL Cast welcomes a first-time listener (2026-08-24)

Three screens on a genuinely first launch -- welcome, add your first podcast,
you're set -- with **Skip** as a first-class button rather than a small link,
because somebody who already knows what a podcast player is should be able to
leave in one keystroke.

They were written a long time ago and never once shown: nothing in the app
called them. Cast now does, at launch, and remembers that it has. It stays
away entirely from anybody who already has podcasts, however they got there --
an imported OPML, a restored setup, an upgrade -- because explaining how to
add a first podcast to somebody with two hundred is a way of saying nobody
checked. Skipping counts as done: somebody who skipped chose to, and asking
again next launch would be overriding that with a guess.

### Undo, Recent Problems, quiet hours, and a setup that travels (2026-08-24)

Nine things QUILL Cast owed a listener and was quietly not paying. Most are
shared with Quill Radio -- one store, one window, one wording -- so setting
them here sets them there.

- **Ctrl+Z takes back the last destructive thing you did.** Unsubscribe,
  Remove All Episodes, Mark All as Played, Remove All Downloads -- one step,
  and it says what came back ("Undid Unsubscribe. Brought back The Daily, with
  412 episodes and 3 downloaded files"). The alternative we deliberately did
  not take was a confirmation prompt on every verb: it costs a keystroke and a
  sentence on all nine hundred occasions you meant it, and it still cannot
  help the one time your cursor was on the wrong show. **Deleted files
  genuinely come back** -- an episode Cast removes on your behalf is moved
  aside rather than unlinked, and that includes the ones removed *for* you: if
  marking a show played fired your delete-after-play rule, the undo brings
  those files back too. It is one step, not a stack, and where something
  cannot come back (a private feed's stored password is deleted deliberately)
  the offer says so in the same breath.

- **Recent Problems (Help, Ctrl+Alt+Shift+P).** Feeds that failed and
  downloads that died, each with its reason, its time, and a Retry.
  Announcements are transient by design, which is right until the sentence you
  needed went past while you were in another window or asleep; that was the
  single place this app was not screen-reader-first. A feed failing on each of
  six checks reads as one row with a fresh time, but a *different* reason gets
  its own row. Copy All is for a bug report: addresses and error messages,
  never passwords. Nothing leaves this computer.

- **Quiet hours (Help, Ctrl+Alt+Shift+Z).** A window -- 22:00 to 07:00 by
  default, crossing midnight -- in which Cast stops speaking *on its own*:
  check ticks, "three new episodes of The Daily", a download landing. Feeds
  are still checked and new episodes still arrive, queue and download; only
  the sentences wait. **Anything you press a key for still answers**, which is
  the line the whole feature is built around and why each announcement had to
  opt in by name rather than everything being switched off at one point.
  Failures always speak. Shared with the rest of the family.

- **Move your setup to another machine (Help, Ctrl+Alt+Shift+X / +N).** One
  file carrying your subscriptions, folders and playlists, your settings, your
  Quick Action order, the confirmations you asked not to see again, your
  bookmarks and any keys you rebound. OPML moved subscriptions and nothing
  else -- the part that was easy to standardise. An ordinary ZIP with a
  readable manifest over a **declared list** of files rather than a sweep of
  the data folder; **passwords are not in it** (said before it acts); and
  importing **replaces** rather than merges, which it also says first.

- **Your place follows you into Quill Radio, and back.** Until now half an
  episode heard in Radio reached Cast at Cast's next launch -- the moment you
  are least likely to be mid-episode -- and nothing went the other way at all.
  One shared place per episode now, written on **pause** as well as on stop,
  switch and shutdown. The **later** decision wins, not the furthest through
  the episode: somebody who skipped to the outro and went back to the middle
  has decided the middle is where they are. The cross-app jump is explained
  out loud.

- **Find an episode inside one show.** The episode list has a **Find** box
  beside its filter. There was a filter by state and there was Search
  Everywhere across the whole library, and nothing in between -- so *which
  episode of this show was the one about the harbour* had no answer except
  arrowing two hundred rows. It matches **titles and show notes**, because a
  podcast that numbers its episodes and describes them in the notes is exactly
  the one a title-only search cannot help with, and it **narrows what the
  filter and sort already chose** rather than replacing them. Typing narrows
  quietly; **Enter** says how many matched out of how many were searched, and
  a search with no matches says the filter above may be the reason rather than
  announcing a zero.

- **Skip Silence while you are listening (Ctrl+Shift+9).** Cast has had this
  as **Smart Speed**, a per-show setting in Podcast Settings, and no way to
  reach it while an episode was playing -- which is the only moment anybody
  forms an opinion about it. It applies to the playing show (or, with nothing
  playing, to every podcast), takes effect on the episode in progress, and
  keeps your place. Quill Radio gained the same key for the same thing.

- **Go to Position (Ctrl+Alt+J, Episode menu).** Cast could already jump to a
  typed time from a Winamp letter key -- which means it existed for whoever
  had those keys on and knew about them, and for nobody else. It is a menu
  item and a palette command now, over the same labelled Hours / Minutes /
  Seconds window Quill Radio opens, and `1:02:03`, `62:03` and `3723` finally
  mean the same moment in both apps.

- **F1 answers with Cast's own words, and a dimmed item says why.** Every Cast
  window had been opening its help with a generic sentence -- true, and
  useless -- while Quill Radio's said what the window was for; a build gate now
  means a new Cast window cannot ship without one. And a dimmed menu item
  carries its reason ("Analyse Chapters: this episode is not downloaded yet,
  so there is nothing to analyse"), on the item, on the Quick Action number
  keys, and in the command palette. Adding a podcast you already follow now
  names it, *announces* it -- the refusal used to be a line of text a screen
  reader does not read when it changes -- and moves the Manager's cursor to
  the row you already have. Pause All Downloads says how many are waiting.

### Getting episodes without asking

- **QUILL Cast can now fetch episodes for you.** Until now it knew what to throw away and nothing about what to fetch: an episode landed on your disk because you asked for it, or -- with Always Sync -- because *everything* did. There was no "keep the newest three ready". Podcast Settings now has **Automatically download**, with None, the newest 1, 3, 5, 10, or every episode, and any podcast can set its own from **Settings for This Podcast...**. New episodes arrive downloaded, on subscribe and on every refresh. Two more switches: anything you add to the Play Queue downloads too (on -- something you queued is something you meant to play), and anything routed to the Inbox does not (off -- the Inbox is where episodes wait to be sorted, not a commitment).
- **Auto-Queue a podcast.** Turn on **Auto-Queue New Episodes** for a show and its new episodes go straight into the Play Queue on refresh, skipping the Inbox entirely. For the two or three shows you always listen to, that is the whole workflow.
- **Have one podcast announce itself.** **Announce New Episodes**, per show, names the new episodes out loud and in braille when the background check finds them, and shows a tray notification. Deliberately per podcast, and off until asked: being told about every feed is being told about nothing.

### Your queue looks after itself

- **Queue Expiration.** A queued episode you never got to is worse than clutter -- the queue decides what plays next, so a stale item does not merely sit there, it takes a turn. Any podcast can now set **Expire from the queue** (1 day up to a month; never, by default). Daily news show? Two days. Weekly long-form? Two weeks. Or leave it off entirely. There is deliberately no global setting: the right number differs per show, and one number for everything is a number nobody wants.
- **Recently Expired**, a new pinned view in the Podcast Manager beside New Episodes and the Inbox, holds what expired for seven days. **Restore** puts an episode back at the end of the queue with a fresh clock; **Restore All** takes the lot. Nothing is deleted when an episode expires -- it keeps its downloaded file, its position, and its place in its show. Only the seven-day sweep removes a downloaded copy, and only for something you chose not to restore. Every expiry is announced; a queue that quietly shortened itself is exactly the kind of silent change QUILL Cast does not do.
- **Upgrading is safe.** A queue saved before this release has no timestamps to age against. QUILL Cast reads an unstamped episode as "added just now", not "added long ago", so the first launch after updating cannot empty your queue.

### Knowing what you listened to

- **Listening Statistics** (Episode menu). Time listened this week, month, year, or all time; how much extra content faster playback bought you; how many episodes you finished; and a breakdown by podcast, most-listened first. It is a read-only text field you arrow through line by line and can copy, the same shape as Player Information -- not a chart with a caption. Durations are read as language ("3 hours, 47 minutes"), never as a clock face, because a screen reader reads `3:47:00` as a time of day. **Export CSV...** saves every session; **Clear Statistics...** deletes the log and nothing else. Ninety days are kept by default.
- **One number is missing on purpose.** Time saved by Smart Speed is not reported, because the silence-trimming path cannot say how much silence it actually dropped. An invented figure would flatter the feature and mislead you, so the line is simply absent rather than showing a confident zero.

### The menus are yours now

- **Quick Actions...** (Subscriptions menu) puts the actions you actually use where you expect them. Three lists -- episode, podcast, and Play Queue -- each reorderable with Move Up, Move Down, and Make Default. **The first action in each list is what Enter does.** The first nine also answer to **Ctrl+1** through **Ctrl+9** in the episode list, so the ones you use constantly need no menu at all. And the whole list is the order of the right-click menu, so muscle memory holds. Nothing changes until you change it: the shipped order puts Play first for an episode and Play Next Episode first for a show, exactly as before.

### Getting an episode back out

- **Save Episode Audio As...** keeps your own copy of the audio wherever you choose. This is the useful half of "sharing" on a desktop: what you actually want is a file you can put somewhere. It **copies** rather than moves -- QUILL Cast keeps managing its own downloaded copy, so retention, the storage cap, resume and Remove Downloaded Copy all still apply to it, and your saved copy sits outside all of that. An episode you have not downloaded offers to fetch it first rather than freezing behind a progress bar you cannot escape. The suggested filename is "Show - Episode", with anything Windows rejects replaced and the length bounded, so the Save dialog never opens pre-filled with a name the system will refuse.
- **Copy Podcast Link**, beside the existing Copy Episode Link. The feed address rather than the homepage, because a feed address is the thing another podcast app can actually be given. A local podcast says it has no link instead of silently copying nothing.
- **Show in File Explorer** opens the folder holding a downloaded episode with the file selected. (It genuinely selects it now -- see Fixed below.)
- All three are **Quick Actions** entries, not hard-coded menu items, so they can be reordered, made the Enter default, or reached on Ctrl+1 through Ctrl+9 like everything else.

### Deciding what happens next

- **Stop After This Episode** (Episode menu): a one-off that stops instead of auto-advancing, clears itself when it fires, and never survives a restart. QUILL Cast says "Will stop after this episode" when you turn it on.
- **Two switches for what follows an episode.** Podcast Settings now has "Play the next episode in the Play Queue" (on -- what QUILL Cast has always done) and "When the queue is empty, keep going with the same podcast" (off, new). With both off, playback stops at the end of the episode you started, which is the entire point of having the pair.
- **Finishing a mid-queue episode no longer throws you back to the top.** Play the ninth thing in your queue, and when it ends the tenth follows -- not the first. It always jumped to the queue head before.
- **Playback speed is a real range.** 0.5x to 5.0x in tenths, replacing six fixed choices that stopped at 2.0x. **Speed Up** (Ctrl+Shift+Up), **Speed Down** (Ctrl+Shift+Down), and **Reset Speed to Normal** (Ctrl+Shift+0) change it from the keyboard while you listen, and say which speed and whose -- the playing podcast's own, or the shared default when nothing is playing.
- **Mark All as Played...**, per podcast, always confirmed by name and count. The episodes stay in your library and downloaded files are not deleted; they simply leave the Inbox, because the Inbox is unplayed episodes and these are no longer that.
- **Sleep timer: "End of this episode"** is now a choice in the timer, and it follows the episode rather than a clock -- seek forward and it moves with you instead of cutting you off early. **Extend 5 Minutes** appears on the timer while it counts down and on the Episode menu, and it also undoes any fade already in progress, because the point of extending is that you are still listening.

### The Inbox and your disk

- **Inbox caps, per podcast.** Keep at most N episodes, and drop episodes older than 6 hours up to 2 weeks. **Trimming never deletes anything**: a trimmed episode leaves the Inbox and stays unplayed in its show's own list. And three kinds of episode are never trimmed at all -- anything you have started, anything in the Play Queue, and anything you filed into an Inbox folder by hand. That distinction is the difference between a helpful cap and losing your place.
- **Downloads...** (Downloads menu) finally answers "how much disk are my podcasts using". Total size, a per-podcast breakdown largest first, an Unheard/All filter that says how many rows it hid, and **Remove This Podcast's Downloads...** for one show at a time.
- **Two automatic storage rules**, both off by default: delete downloads older than N days, and a total storage cap in MB. When the cap is exceeded, already-played downloads go oldest first. **A queued or part-played episode is never removed** -- disk pressure is not a reason to throw away the thing you are halfway through. **Free Up Space** applies both on demand and reports the bytes reclaimed.
- **Run Housekeeping Now** does the whole pass -- expire, sweep, trim, enforce -- and tells you everything it did in one sentence. It also runs automatically after each refresh.

### Importing a real subscription list

- **Import OPML rebuilt for lists in the thousands.** Tested against a 1,307-feed export. Reading, parsing, and adding now happen off the UI thread instead of inside a button handler, so the window never freezes. Duplicate detection matches on a normalized address, so the `http://` and `https://` forms of one feed are correctly one feed -- and a file listing the same show twice imports it once. Two shows that merely share a *title* are both imported and flagged for review, because two shows genuinely can be called "The Daily".
- **QUILL Cast can now tell you which of your feeds are dead.** Tick "Check that each feed is still reachable" and it checks them concurrently after importing, with live progress you can hear (announced every ten per cent) and a **Stop Checking** button that keeps everything already imported. A feed asking for a sign-in counts as alive, so a private feed is never reported dead.
- **And then prune the file.** The import report has **Save Pruned OPML...**, which writes your original file back without the feeds that no longer answer -- folders, attributes, and all. Knowing that three hundred feeds are dead is only useful if you can do something about it.

### Winamp keys, the same ones as Quill Radio

- **The classic transport letters work in QUILL Cast.** `X` play, `C` pause, `V` stop, `B` next, `Z` previous; Left/Right seek 5 seconds and Shift+Left/Right seek 30; `T` switches between elapsed and remaining; `J` jumps to an episode by name and `Ctrl+J` to a time; `L` opens what is selected. Exactly the keys Quill Radio's recordings player uses, from the same shared map -- the whole value of muscle memory is that it does not have to be relearned per app. On by default, with one Preferences checkbox to turn the letters off if you would rather use them for list typeahead.

### Chapters you can skip

- **Mark chapters to skip.** In the Chapters dialog for the episode you are playing, **Skip This Chapter** marks the ad break, the sponsor read, or the outro; playback jumps past it and says "Skipping chapter:" and its name. Marks last for the listening session only -- a chapter you skipped in yesterday's episode says nothing about today's. Consecutive marked chapters are stepped over together, and marking everything to the end simply finishes the episode normally, so auto-advance and delete-after-play still fire.

### Speed, size, and not falling over

- **A big library no longer stalls the app.** With a thousand-plus shows fully refreshed, saving the library takes about seven seconds and writes a 164 MB file -- and that save used to run on every pause, every stop, and every episode change. Above a size threshold, saves and the library-tree rebuild now settle onto a short timer instead of running in the middle of your keystroke; below it nothing changes and saves stay immediate. Closing the app always writes everything out first.
- **Expanding a podcast is no longer the whole library.** A show's episodes are built when you expand it, not for every show up front. That was around 196,000 tree items on a large library, rebuilt on every save.
- **Long lists say what they are not showing.** A cross-show view (New Episodes, the Inbox) fills the newest thousand rows and the status line says so and what to do about it, instead of trying to list two hundred thousand episodes.

### Also

- **Settings for This Podcast...** collects everything that only makes sense one show at a time -- auto-download, auto-queue, announcements, queue expiry, speed, Inbox caps, download age limit -- with **Follow the Shared Defaults** to drop every override at once. Leaving a field on the shared default stores no override, so changing the global later still reaches that show.
- **Read the podcast name first**, an accessibility preference for cross-show lists. In a list of two hundred rows from forty shows, whichever name comes first is what you can skim by first letter -- and which one that should be depends entirely on how you look for things.
- **Start on this view**: choose which part of the library QUILL Cast opens on -- New Episodes, Continue Listening, the Inbox, Favorites, Recently Expired, or the top of the tree.
- **Group the Play Queue by podcast**, with move-group-to-top/up/down/bottom. Forty items from four shows is a list nobody can hold in their head; four groups is.
- **Export My Data...** writes your subscriptions, folders, queue, playlists, episode notes, listening statistics, and recently-played list to one readable JSON file. OPML covers subscriptions and nothing else.
- **Delete All Podcast Data...** starts you over, confirmed twice, with downloaded files as a separate question -- "start over" and "reclaim the disk" are not the same wish.

### Fixes and additions that landed alongside

- **A re-published episode comes back to your Inbox.** Publishers do re-issue episodes -- a corrected file, a re-cut, one pulled and put back -- and QUILL Cast used to refresh the details in place and leave it where it was. If the Inbox had already trimmed it, the corrected version sat in the show's own list where you were never going to look. It now returns, announced in words that do not call it new: "Episode 42 was re-published by The Daily, so it is back in your Inbox." Three kinds of episode are left alone, and they are the same three the Inbox caps already exempt -- one you **played**, one you **started**, and one you **queued** -- plus anything you filed into an Inbox folder yourself. A refresh should not argue with decisions you have already made.

- **Your place is kept even if QUILL Cast never gets to shut down properly.** The resume position was only written when *you* did something -- pause, stop, change episode, or quit cleanly. Every other ending took it with you: a crash, a power cut, Task Manager, a forced restart. You came back to your last pause, which after an uninterrupted hour is an hour ago. It now saves every fifteen seconds while an episode plays, so the worst an unclean exit can cost is a sentence.

- **Your episode notes are reachable from the player.** A note is something you make *while listening*, so needing to leave the player, find the episode in the library tree and open its context menu to read your notes back was the wrong shape. **My Notes in This Episode...** now acts on whatever is playing, and selecting a note jumps to it.
- **Copy Note** shares one bookmark as text somebody else can act on: the episode, the podcast, the timestamp, your note, and the audio link together. The note's own words pasted alone are a fragment with no way back to the moment they mark. A note whose podcast you have since unsubscribed from still copies -- the parts that are gone are simply left out.
- **Fixed: Player Information said "0 notes" for every episode.** The count was gathered by a call with the wrong number of arguments, and the error it raised every single time was swallowed -- so an episode with fifty notes read as having none. A confident wrong number is worse than an absent one.
- **Fixed: Show in File Explorer opened the wrong folder.** Windows Explorer wants `/select,` and the path as one argument; passed as two it quietly ignores the switch and opens Documents. A window appeared, so it looked like it had worked -- with nothing to tell a screen-reader user otherwise. There is one tested implementation now, shared with QUILL and Quill Radio.
- **A podcast host having a bad minute no longer looks like a dead feed.** Refreshing a feed, searching the directory, and the OPML reachability sweep retry twice on a transient failure -- a 5xx, a dropped connection, a timeout -- a second and then two seconds later. A 404, an address that does not resolve, and a sign-in failure still fail immediately, because asking again cannot change those answers. It matters most in the reachability sweep, whose verdict is what the import report offers to prune from your OPML file: one busy moment must never be the reason a live subscription gets deleted.

- **Fixed: QUILL Cast would not start at all.** On some builds the app closed before its window ever appeared, so there was nothing to report and nothing to work around. The library tree asks Windows to expand its top level; because the tree deliberately hides its invisible root node (so the first thing you arrow to is a real folder or show, not a meaningless "root"), Windows refused the request and took the app down with it. The request was never needed -- a hidden root's children already *are* the visible top level -- so it is now skipped. A regression test keeps the guard in place.
- **Announcements now reach a braille display.** Everything QUILL Cast says through your screen reader is also written to your braille display, which the standalone apps never did before -- previously braille users only saw whatever the display happened to be tracking. A burst of different messages no longer flickers past faster than cell one can be read: the first message of a quiet moment is written instantly, and anything arriving in the next fraction of a second settles to the newest instead of each shoving the last aside. Errors are exempt and always write through at once, and can be held on the display instead of flashing by. Braille can send either the same wording as speech or a compact position-first form, and the "identical message repeated" window is adjustable. These are shared accessibility settings, so they are set once in QUILL and apply here.
- **Every destructive confirmation now defaults to No.** **Delete Folder**, **Delete Playlist**, **Remove All Episodes**, and **Delete Downloaded Files** all used to open with Yes as the default button, so pressing Enter reflexively destroyed the thing. Enter is now always the safe answer, and Yes is a deliberate choice. An automated build check fails if a destructive Yes-default is ever added again.
- **Quillins in QUILL Cast.** A **Quillins** menu runs QUILL's small, sandboxed, permission-gated add-ons inside QUILL Cast. A Quillin declares which apps it targets, so only add-ons written for QUILL Cast appear. The bundled `cast-premium-auth` sample supplies a sign-in header for a private subscriber-only feed. Off in Safe Mode; third-party Quillins stay disabled in this release.
- **Keyboard Shortcuts... and Global Hotkeys... in the Help menu.** The same Keyboard Manager and Global Hotkeys manager QUILL uses, scoped to QUILL Cast's own commands. A new **Show/Hide QUILL Cast to the Tray** command can be given a system-wide key (Ctrl+Alt+Shift+Q by default) so the window tucks away or comes back even when another program has focus.
- **Spotify podcasts (experimental, off by default).** Groundwork for playing Spotify-hosted podcasts, shipped hidden behind a feature flag. Turning it on needs a signed unlock code, a Spotify Premium account, and your own Spotify Client ID. Spotify audio is copy-protected, so an episode plays but cannot be downloaded. See the User Guide.

## 1.0.7

- **Update in one click -- QUILL Cast installs it and restarts itself.** When an update is available, choose Download, then **Install and restart now**: QUILL Cast applies the update (extracting the new portable files over your folder, or running the installer silently) and relaunches automatically, keeping all your shows, downloads, and settings. No more closing the app, unzipping, and swapping folders by hand. Shared across every Quill app.

## 1.0.6

- **Private feeds (username and password)**: subscribe to Patreon supporter feeds, premium shows, and other HTTP Basic-auth-protected feeds. Add by Feed URL detects a protected feed and opens a **Feed Credentials** prompt; a new **Feed Credentials...** item on every show's context menu (main library tree and Podcast Manager alike) changes or clears them later. Credentials cover everything for that show -- refresh, downloads, streaming, transcripts, chapters -- but are only ever sent to the feed's own host, never to third-party content hosts. Passwords are stored in Windows Credential Manager (installed) or DPAPI-encrypted inside the portable `data` folder (portable), never in `podcasts.json` or logs; Export OPML never includes them. A failed sign-in during background refresh announces a clear "update credentials" message instead of a generic network error.
- **Podcast search returns you to the results list after subscribing (#1181 follow-up).** In **Add Podcast...**, subscribing to a search result left focus stranded on the Subscribe button, so adding a second show meant hunting back to the list. Focus now returns to the results list and re-selects the row you just subscribed from, ready to arrow on. Applies whether the subscribe succeeded, was already in your library, or failed. The Add-by-Feed-URL path is unchanged -- focus stays by the URL box.
- **Expand a show in the library tree to see its episodes in place (#1192).** Episodes now hang under each show on the main page. Shows start collapsed so the tree is not a wall of episodes; expand one to reveal them, and Enter on an episode plays that episode. Enter on a show still plays its next unplayed episode.
- **Playback keyboard shortcuts (#1189).** Episode menu: **Stop** (Ctrl+.), **Skip Back** / **Skip Forward** (Ctrl+Left / Ctrl+Right), and new **Volume Up** / **Volume Down** (Ctrl+Up / Ctrl+Down, matching Quill Radio). Play/Pause keeps Ctrl+P.
- **Alt+F4 minimizes to the system tray** -- a new Preferences checkbox, off by default. When on, the reflexive keyboard close tucks the window away with playback still running; the titlebar X and Exit keep the behavior you chose for closing the window, so a deliberate exit still exits.
- Fixed: the Podcast Manager could show no episodes at all for a selected show (#1189).
- Fixed: an in-app update could hang behind a stray console window that stole focus (#1191).
- Dialog buttons standardized: Apply/Save affirmative buttons are now labeled OK, so the confirming button is in the same place with the same name everywhere.

## 1.0.5

- Skip Forward and Skip Back (Episode menu), a fixed number of seconds each -- 30 forward, 15 back by default -- different from Next/Previous Chapter, which jumps to the nearest chapter marker instead. New **Skip Settings...** dialog (Episode menu) sets how far each jumps: open it while an episode is playing to set that show's own distance, or with nothing playing to set the shared default.
- Auto-skip intro and auto-skip outro, per podcast (in the same Skip Settings... dialog, only when a show is loaded): intro-skip jumps forward automatically on a fresh start (never when resuming your saved position); outro-skip ends the episode early, exactly as if it had finished naturally -- auto-advance and delete-after-play still fire.
- **Playlists**, below the Play Queue in the Podcast Manager's tree: saved, named episode lists. **New Playlist...** builds a manually curated list (add episodes from any episode's right-click menu with **Add to Playlist...**). **New Smart Playlist...** builds a rule-based list that re-resolves live every time you open it -- which shows, episode status, how recent, how long, and how to sort. Edit Rules..., Rename, and Delete round out each playlist's context menu.

## 1.0.4

- Sound Enhancements is now a real three-band equalizer: Bass, Mid, and Treble sliders (-12 to +12 dB each), freely adjustable. The old presets (Flat/Bass Boost/Voice Clarity/Podcast) still work as a "Quick preset" shortcut. Every enhancement setting -- the three bands, Even Out Volume, and Smart Speed -- is now **per-podcast**: a shared default plus a per-show override, the same way playback speed already worked. Open Sound Enhancements while an episode is playing to adjust that show specifically; open it with nothing playing to adjust the shared default.
- Check for Updates (Help menu) now shows a real dialog when you're already up to date, instead of only a spoken announcement that was easy to miss.
- Preferences (Ctrl+,) gained "Announce dialog transitions" (off by default) to reduce alert noise -- previously every dialog always spoke "Entered/Exited" cues with no way to turn it off.
- Help menu gained User Guide, Release Notes, and Product Requirements items, opening the bundled documentation right in your browser.

## 1.0.3

- Inbox (and every cross-show list -- New Episodes, Continue Listening, Favorites) can now be shown three ways, via a new **"View cross-show lists as"** combo box: **Flat list** (one chronological stream across every show), **Grouped in list** (the pre-existing look -- each show's episodes clustered together in the flat list), or **Folders per podcast** (real expandable tree nodes, one per show, under each pinned view). Grouped is the default, so nothing changes until you touch the combo box.
- The pre-existing "Sort episodes" control now actually applies to these cross-show views too (it previously only affected a single show's own episode list) -- and each podcast can have its **own** sort order: select a show (directly, or its Folders node) and change Sort Episodes to override just that podcast, leaving the shared default for everything else. Fixed a related bug where setting a podcast's own playback speed silently reset any other override that podcast already had.

## 1.0.2

- Sound Enhancements (Episode > Sound Enhancements...): an equalizer preset (Flat/Bass Boost/Voice Clarity/Podcast), a compressor ("Even Out Volume"), and Smart Speed (trims silence between words/sentences during playback) -- applied live via ffmpeg, no new audio engine, no new install step. Off by default; needs FFmpeg (Help > Get FFmpeg...). Full seek/scrub-bar support while enhanced, not a degraded mode. Distinct from the existing download-time silence trim (which permanently shortens the saved file's leading/trailing silence once); Smart Speed is a live, reversible, mid-episode filter you can toggle on any episode at any time.
- Download All Episodes and Remove All Episodes, on every show's context menu (Podcast Manager and the main library tree alike): Download All queues everything not already downloaded or in progress; Remove All Episodes asks to confirm, then -- only if any episode has a downloaded file -- asks separately whether to delete those files too. The show stays subscribed either way.

## 1.0.1

- Onedir packaging (was onefile): starts instantly instead of re-extracting to a temp folder on every launch. New consolidated `build_release.ps1` producing a staged app folder, a portable zip (with its own `data\` folder), and the installer from one build.
- Main page: the flat subscribed-shows list is now a real library tree -- pinned views (Favorites, New Episodes, Continue Listening, Inbox) above nested folders, with a full context menu.
- One state-aware Play/Pause/Stop transport button, a favorite-toggle button, Mute/Unmute.
- Resume Last Episode on Launch and a Recently Played submenu (distinct from Continue Listening).
- Play Queue promoted to a top-level menu item and Command Palette entry.
- Downloads now auto-reconnect on a dropped connection, configurable in Podcast Settings.
- Help > Get FFmpeg... safety net.
- Automatic Check for Updates: a throttled, silent check once a day on launch -- quiet unless a real update is found.
- Preferences... (Ctrl+,): a small dialog for Resume Last Episode on Launch and the new automatic update check.

## 1.0.0

- Initial release: podcasts as their own standalone app, sharing QUILL's own podcast feature code.
- Full Podcast Manager: pinned views, Inbox with per-show filing memory, Play Queue with keyboard reordering, Search Everywhere, filters.
- Feed-provided transcripts (Podcasting 2.0), episode notes with timestamp jump, chapters, sleep-timer-safe volume boost.
- Local podcasts with optional watched folders.
- Subscribe to ACB Media Podcasts in one command.
- Downloads with pause/resume all, Always Sync, auto-trim silence, normalize loudness.
- System tray presence with podcast controls.
- One data store shared with QUILL and Quill Radio.
- Check for Updates, Report a Bug, Redeem Unlock Code, Command Palette.
