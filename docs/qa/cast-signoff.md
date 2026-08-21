# QUILL Cast -- sign-off checklist

One pass, top to bottom, ticking boxes. Every step says exactly what to press,
exactly what to type, and the one thing that decides pass or fail.

The narrative version of every feature below is
[the user guide](../../standalone/cast/docs/userguide.md); the reasoning is in
[the PRD](../../standalone/cast/docs/prd.md) and
[release notes 2.0](../../standalone/cast/docs/release-notes-2.0.md).

## Before you start (3 minutes)

- Install or launch the build under test. Note the version from
  **Help > About QUILL Cast**: `____________`
- Have a screen reader running and speaking (JAWS or NVDA).
- Cast shares its library with QUILL and Quill Radio in `%APPDATA%\Quill`. If
  you want a clean run, take a copy of that folder first.
- **Fail means:** it did not happen, or it happened silently, or what you heard
  differs from what this file quotes. Write down what you actually heard.
- Safe Mode is `quill-cast.exe --safe-mode`.
- Feeds used throughout (all verified live):

| Show | Feed | Carries |
| --- | --- | --- |
| Podcasting 2.0 | `https://feeds.podcastindex.org/pc20.xml` | transcript, chapters, people, funding |
| Buzzcast | `https://feeds.buzzsprout.com/1538779.rss` | transcript, chapters, people |
| No Agenda | `https://feed.nashownotes.com/rss.xml` | transcript, chapters, funding |
| The Rest Is History | `https://feeds.megaphone.fm/GLT4787413333` | none of it |
| 99% Invisible | `https://feeds.simplecast.com/BqbsxVfO` | none of it |

## The 20-minute pass

No time for the whole thing? Run exactly these ten and stop -- all are quick
and need no key, no second machine and no long download:
**C-02, C-03, C-06, C-11, C-37, C-40, C-52, C-59, C-88, C-102.**

---

## Block A -- First run and the main window (6 min)

**C-01. First run is three screens, not seven**
- Do: launch a copy with no podcasts (or a fresh profile).
- Pass: three screens -- welcome, add your first podcast, you're set -- each a
  text box you can arrow through and copy. **Skip** is a real button and
  counts as done. Someone who already has podcasts never sees it.
- [ ] pass  [ ] fail: ______

**C-02. Focus lands where the work is**
- Do: open Cast normally.
- Pass: keyboard focus is in the **Library** tree the instant the window opens.
- [ ] pass  [ ] fail: ______

**C-03. Add your first podcast**
- Do: **Alt+S > Add Podcast...**, type `Podcasting 2.0`, search, arrow to the
  result, press **Enter**.
- Pass: Enter opens a read-only **Preview** -- what it is, who makes it, how
  many episodes, its description as arrowable text, ten recent episode titles
  with dates -- and **Subscribe** is on that same window. Enter must not
  subscribe outright.
- [ ] pass  [ ] fail: ______

**C-04. Tab order on the main window**
- Do: Tab from the top.
- Pass: now-playing line, library tree, then **Play**, **Stop**, **Add to
  Favorites**, **Open Manager...**, **Add Podcast...**
- [ ] pass  [ ] fail: ______

**C-05. The transport button is never dead**
- Do: press **Play**, then press it again, then again.
- Pass: it reads **Play**, then **Pause** while playing, then **Resume** while
  paused. Add to Favorites likewise becomes **Remove from Favorites**.
- [ ] pass  [ ] fail: ______

**C-06. Enter on a show plays its next unplayed episode**
- Do: arrow to a show in the tree, press **Enter**.
- Pass: the next unplayed episode plays, with no detour through the Manager. If
  every episode is played, it plays the most recent one **and says so**.
- [ ] pass  [ ] fail: ______

**C-07. Episodes without leaving the main window**
- Do: press **Right Arrow** on a show, arrow to an episode, press **Enter**.
- Pass: shows start collapsed; expanding lists episodes newest first; Enter on
  an episode plays *that* episode.
- [ ] pass  [ ] fail: ______

**C-08. The counts are in words**
- Do: read a show row and a folder row.
- Pass: "(3 unheard)" on a show; a folder says how many podcasts live under it,
  counting its whole subtree.
- [ ] pass  [ ] fail: ______

**C-09. Rename the pinned views, not the shows**
- Do: **F2** on **Favorites**; then **F2** on a show.
- Pass: the view takes your name and keeps it in the Manager too, and its menu
  gains **Reset Name**; the show refuses -- its name comes from the feed.
- [ ] pass  [ ] fail: ______

**C-10. One-sentence tips, once each**
- Do: use Cast normally for a few minutes on a fresh profile.
- Pass: occasional single sentences (Play Queue vs Inbox, settings can differ
  per podcast), never modal, never taking the keyboard, spoken **and** brailled.
  One switch turns them off; **Show Tips Again** brings them back.
- [ ] pass  [ ] fail: ______

## Block B -- The Podcast Manager (8 min)

**C-11. The Manager opens on its pinned views**
- Do: **Ctrl+M**.
- Pass: **Favorites**, **New Episodes**, **Continue Listening**, **Inbox** lead
  the tree, above your folders and shows.
- [ ] pass  [ ] fail: ______

**C-12. Cross-show lists read three ways**
- Do: in **New Episodes**, change **"View cross-show lists as"** to each of
  **Grouped in list**, **Flat list**, **Folders per podcast**.
- Pass: grouped clusters each show together; flat is one date-sorted stream;
  folders per podcast are real expandable nodes under the view.
- [ ] pass  [ ] fail: ______

**C-13. Sort episodes, per podcast**
- Do: change **Sort episodes** with a show (or its Folders node) selected.
- Pass: it applies to cross-show lists too, and selecting one show overrides
  just that podcast, leaving the shared default alone.
- [ ] pass  [ ] fail: ______

**C-14. Sort shows, including your own order**
- Do: **Sort shows** > each option; then **Alt+Up** / **Alt+Down** on a show.
- Pass: the dropdown opens on whatever the library really is sorted by; the
  first Alt+Up switches to **Custom Order** starting from the order already on
  screen, so nothing jumps, and the new position is spoken.
- [ ] pass  [ ] fail: ______

**C-15. Filter episodes**
- Do: work through the Episodes filter: All, Unplayed, Played, **In progress**,
  Downloaded, Not downloaded.
- Pass: each narrows correctly, and the status line reports the true total.
- [ ] pass  [ ] fail: ______

**C-16. Search Everywhere**
- Do: search a word you know appears in an episode title, a note, and a fetched
  transcript. Then **empty the box**.
- Pass: shows, episodes, notes and transcripts all match, and Enter jumps to the
  result; emptying the box empties the results **at once**.
- [ ] pass  [ ] fail: ______

**C-17. A very large library stays navigable**
- Do: on a library with thousands of episodes, open **New Episodes**.
- Pass: the newest thousand rows fill the list and the status line says the
  **true** total.
- [ ] pass  [ ] fail: ______

## Block C -- Subscribing (7 min)

**C-18. Two directories, and where results came from**
- Do: **Add Podcast...**, set **Directory** to **iTunes**, search `history`.
  Then add a free key at **Alt+S > Podcast Index Credentials...** and set
  Directory to **Both**.
- Pass: iTunes needs nothing and is the default; **Podcast Index does not
  appear at all until a key exists**; Both merges by feed address and says
  "12 results: 9 from iTunes, 3 from Podcast Index." A directory that fails
  contributes a sentence, not a failed search.
- [ ] pass  [ ] fail  [ ] no key -- not run

**C-19. Read It Back**
- Do: in Podcast Index Credentials..., press **Read It Back**.
- Pass: the secret is spoken once, four characters at a time; the box is masked
  otherwise; clearing both boxes and saving removes them.
- [ ] pass  [ ] fail: ______

**C-20. Add by feed URL**
- Do: **Add Podcast...** > **Add by Feed URL**, paste
  `https://feed.nashownotes.com/rss.xml`, press **Add**.
- Pass: it subscribes and the episodes are listed.
- [ ] pass  [ ] fail: ______

**C-21. A private feed, end to end**
- Do: add a feed that requires a sign-in.
- Pass: a **Feed Credentials** dialog opens **with focus on the username
  field**; a wrong password reopens it with the username kept and says so;
  afterwards refresh, download, playback, transcripts and chapters are all
  signed in.
- [ ] pass  [ ] fail  [ ] no private feed -- not run

**C-22. Credentials go to the credential store, and only to the feed's host**
- Do: **Shift+F10** on that show > **Feed Credentials...**, change the password,
  then **Clear Credentials**. Then open **Export OPML...** output in a text
  editor and search it for the password.
- Pass: every save and clear is announced; the password is nowhere in the OPML,
  nowhere in `podcasts.json`, nowhere in a log.
- [ ] pass  [ ] fail: ______

**C-23. ACB Media and local podcasts**
- Do: **Alt+S > Subscribe to ACB Media Podcasts**. Then **Add Local
  Podcast...** on a folder of your own audio, then **Scan Watched Folders**.
- Pass: ACB's directory arrives in one step; the local folder becomes a show
  and dropped files are picked up on a scan.
- [ ] pass  [ ] fail: ______

## Block D -- Folders (5 min)

**C-24. A folder is somewhere you listen from**
- Do: **Shift+F10** on a folder > **Play All Unplayed**.
- Pass: the newest unplayed episode of **each** show in it -- one per show --
  queued and started. A folder always means its whole subtree.
- [ ] pass  [ ] fail: ______

**C-25. Add All to Queue, and moving folders**
- Do: **Add All to Queue** on that folder, then **Move Up** / **Move Down**.
- Pass: every unplayed episode in it is queued; the new position is spoken
  ("News, 2 of 5").
- [ ] pass  [ ] fail: ______

**C-26. Folder Settings apply to everything under it**
- Do: **Folder Settings...**, change queue expiry only, OK.
- Pass: each control starts at **"change nothing"**; it says how many podcasts
  it changed; a show moved into the folder afterwards keeps its own settings.
- [ ] pass  [ ] fail: ______

**C-27. Export one folder**
- Do: **Export This Folder as OPML...**
- Pass: that folder and its sub-folders only -- not the whole library.
- [ ] pass  [ ] fail: ______

**C-28. Move several podcasts in one step**
- Do: on any podcast's menu, **Move Several Podcasts to Folder...**; extend with
  Shift+arrow, toggle with Ctrl+Space, then **Select All**.
- Pass: the count is spoken as you go, and the folder is asked **once** for the
  lot.
- [ ] pass  [ ] fail: ______

**C-29. Deleting a folder never unsubscribes**
- Do: **Delete** (or Delete Folder...) on a folder with shows in it.
- Pass: the confirmation opens on **No**; accepting dissolves the folder and the
  shows step safely to the top level.
- [ ] pass  [ ] fail: ______

## Block E -- Queue, playlists and the Inbox (10 min)

**C-30. The Play Queue**
- Do: **Play Next** and **Add to Queue** on a few episodes, then reorder with
  Move Up/Down (and Mark then Move for a long hop). Restart Cast.
- Pass: it auto-advances, reorders from the keyboard, and survives the restart.
- [ ] pass  [ ] fail: ______

**C-31. Grouping the queue never changes the order**
- Do: set **Group by** to **Podcast**, then **Library folder**.
- Pass: only the reading changes; a group header announces itself as one
  ("News, group, 4 episodes"), and Play, Move and Remove all ignore headers.
- [ ] pass  [ ] fail: ______

**C-32. A manual playlist**
- Do: **Shift+F10** on **Playlists** > **New Playlist...**, then **Add to
  Playlist...** on a few episodes. Rename with **F2**.
- Pass: it holds what you put in it, renames, and deletes with a confirmation
  that opens on **No**.
- [ ] pass  [ ] fail: ______

**C-33. A smart playlist says what you mean**
- Do: **New Smart Playlist...**, set **match any**, add two rules (a library
  folder, and "has a note of mine"), and watch the live count.
- Pass: **"Matches 23 episodes right now"** recomputes as you type; "at most N"
  is applied **after** sorting, so "the ten newest" really is.
- [ ] pass  [ ] fail: ______

**C-34. Starter playlists**
- Do: **Add Starter Playlists**.
- Pass: five ordinary, editable playlists appear (Continue Listening, New This
  Week, Quick Listens, Downloaded and Unplayed, Long Reads) -- not built-ins.
- [ ] pass  [ ] fail: ______

**C-35. The Inbox fills the way you told it to**
- Do: **Podcast Settings... > Which shows go to the Inbox**, switch between
  *Only the shows I choose* and *Every show except the ones I exclude*.
- Pass: nothing moves until you change the setting; the per-show menu item
  flips to **Keep This Show Out of the Inbox** and says so when used.
- [ ] pass  [ ] fail: ______

**C-36. Filing is remembered per show**
- Do: file an episode into one of your Inbox folders by hand, then let a new
  episode of the same show arrive.
- Pass: the second is filed there automatically; **Forget** reverts it.
- [ ] pass  [ ] fail: ______

**C-37. Bulk actions, asked once**
- Do: select several episodes (Shift/Ctrl+arrow, or **Ctrl+A**) and open the
  context menu.
- Pass: **Add N Episodes to Queue**, **Download N Episodes**, **Mark N Episodes
  as Played**, **Add N Episodes to Playlist...**, **Remove N Downloaded
  Copies**, and **File N Episodes to Inbox Folder...** -- which asks **once**
  which folder, and says a show gained a remembered folder once, not once per
  episode.
- [ ] pass  [ ] fail: ______

**C-38. Removing downloads is not unsubscribing**
- Do: **Remove N Downloaded Copies** on that selection.
- Pass: the episodes stay in the library with their played marks and positions.
- [ ] pass  [ ] fail: ______

**C-39. Inbox limits trim without deleting**
- Do: set an Inbox count limit in **Settings for This Podcast...**
- Pass: older episodes leave the Inbox but stay unplayed in the show's own
  list; anything started, queued or filed by hand is never trimmed.
- [ ] pass  [ ] fail: ______

## Block F -- Playing an episode (10 min)

**C-40. The transport keys**
- Do: **Ctrl+P**, **Ctrl+.**, **Ctrl+Up** / **Ctrl+Down**, **Ctrl+Right** /
  **Ctrl+Left**.
- Pass: play/pause, stop, volume, and skip forward 30 / back 15 -- each spoken.
- [ ] pass  [ ] fail: ______

**C-41. Speed, in tenths, and whose it is**
- Do: **Ctrl+Shift+Up**, **Ctrl+Shift+Down**, **Ctrl+Shift+0**.
- Pass: anywhere from 0.5x to 5.0x in tenths, and the announcement says both
  the new speed and whose it is -- the playing show's own, or the shared
  default when nothing is playing.
- [ ] pass  [ ] fail: ______

**C-42. Scan forward by holding a key**
- Do: **hold Shift+Right**, then let go -- while listening at 1.5x.
- Pass: *"Scanning forward, 4 times speed"*, then *"Back to 1.5 times speed"*
  -- exactly the speed you were at, not 1.0. Losing the window ends a scan too.
- [ ] pass  [ ] fail: ______

**C-43. Skip Settings, per podcast**
- Do: **Skip Settings...**, change the jumps, and set an **auto-skip intro**.
- Pass: the jumps change for that show; the intro skip fires on a **fresh**
  start and never when resuming a saved position; an outro skip ends the
  episode as if it had finished, so auto-advance still runs.
- [ ] pass  [ ] fail: ______

**C-44. Sound Enhancements, live and per podcast**
- Do: **Ctrl+E** while an episode plays. Set a Quick preset, turn on **Even Out
  Volume** and **Smart Speed**, Apply.
- Pass: applied live; the brief reconnect on Apply resumes at **your exact
  position**; pause/resume works throughout. Opened with nothing playing, it
  sets the shared default instead.
- [ ] pass  [ ] fail: ______

**C-45. FFmpeg missing is explained, not silent**
- Do: if FFmpeg is unavailable, use enhancements anyway.
- Pass: playback continues unfiltered and Cast says why, pointing at **Help >
  Get FFmpeg...**
- [ ] pass  [ ] fail  [ ] not applicable

**C-46. Audio output**
- Do: **Ctrl+Shift+M** (Audio Output Mode), then **Ctrl+Shift+K** (Audio Output
  Device...).
- Pass: the mode changes; the device item **says in a sentence** that Cast plays
  through Windows' default device and offers to open Windows' own per-app sound
  settings -- rather than opening a picker that would do nothing.
- [ ] pass  [ ] fail: ______

**C-47. Sleep timer**
- Do: **Sleep Timer...**, choose **End of this episode**, then seek forward.
  Use **Extend Sleep Timer 5 Minutes** while it counts down.
- Pass: the end-of-episode choice is offered only when an episode is loaded and
  **follows the episode** when you seek; extending also undoes a fade in
  progress.
- [ ] pass  [ ] fail: ______

**C-48. Stop After This Episode**
- Do: turn it on, let the episode end. Then restart Cast.
- Pass: it stops instead of auto-advancing, clears itself when it fires, and
  never survives a restart.
- [ ] pass  [ ] fail: ______

**C-49. Player Information stays put**
- Do: **Player Information...** while something plays.
- Pass: one read-only field you can arrow through and copy -- title, show,
  position, duration, remaining, percent, speed, streaming or local, kept or
  temporary, note count, resume point, current chapter.
- [ ] pass  [ ] fail: ______

**C-50. The position survives a hard close**
- Do: play two minutes, then end the process from Task Manager. Relaunch and
  play the same episode.
- Pass: at most a sentence is lost -- the position is written every fifteen
  seconds.
- [ ] pass  [ ] fail: ______

**C-51. Resume Last Episode on Launch**
- Do: tick **Alt+S > Resume Last Episode on Launch**, quit mid-episode,
  relaunch.
- Pass: it picks the episode back up at launch (and only at launch).
- [ ] pass  [ ] fail: ______

## Block G -- Chapters (8 min)

**C-52. Chapters a publisher wrote**
- Do: play a **Podcasting 2.0** or **No Agenda** episode, open **Chapters...**
- Pass: the publisher's own titles, and the list says they came from the feed.
- [ ] pass  [ ] fail: ______

**C-53. Chapters from show-note timestamps**
- Do: open Chapters on an episode whose notes carry `00:12:34 Topic` lines.
- Pass: they are read as chapters -- including `1:02:03`, `12.34`, `1h05m`,
  bracketed and bulleted forms, and the time at the **end** of the line -- and
  the list says where they came from.
- [ ] pass  [ ] fail: ______

**C-54. Marked moments are labelled as such**
- Do: open Chapters on an episode with publisher highlights and no chapter file.
- Pass: they appear as **Moments this podcast marked**, each keeping its own
  real end -- never presented as a full chapter list.
- [ ] pass  [ ] fail: ______

**C-55. Worked-out chapters say how hard they looked**
- Do: **Podcast Settings > Chapters**, set effort to **Thorough**, then open
  Chapters on an episode with none published.
- Pass: nothing interrupts you -- the menu item reads "Chapters (working them
  out...)", opening it says it will tell you when they are ready, and the
  finished summary names the method, how much was examined, and a confidence
  ("12 sections, worked out by listening for pauses. Examined: 48 minutes of
  audio. Confidence 41%").
- [ ] pass  [ ] fail: ______

**C-56. Off means off**
- Do: switch one individual method off, and set **when** to *never*.
- Pass: that method never runs at any effort level; with the whole feature off,
  Cast never mentions worked-out chapters again.
- [ ] pass  [ ] fail: ______

**C-57. Deep transcribes on this machine**
- Do: set effort to **Deep** on an episode with no transcript, then stop it
  part-way.
- Pass: it transcribes locally with no download and no network, and stopping
  works at any point.
- [ ] pass  [ ] fail: ______

**C-58. Skip a chapter**
- Do: with an episode playing, **Chapters...** > **Skip This Chapter** on an ad
  break. Then **Skip Nothing**.
- Pass: playback jumps past it saying *"Skipping chapter:"* and its name;
  consecutive marks are stepped over together; marking to the end simply
  finishes the episode so auto-advance still fires. Marks last the session
  only, and the button appears only for the episode actually playing.
- [ ] pass  [ ] fail: ______

## Block H -- What else the podcast published (5 min)

**C-59. About This Episode**
- Do: **About This Episode...** on a **Podcasting 2.0** episode.
- Pass: a one-line spoken summary **before** the window opens ("2 people, 1
  marked moment, 1 recommended podcast"), then tabs -- and a tab exists only
  when it has something in it.
- [ ] pass  [ ] fail: ______

**C-60. Each tab reads as sentences**
- Do: walk **People**, **Highlights**, **Live**, **Other Audio**,
  **Recommended**, **Support**, **Place**.
- Pass: "Bob Brown, guest (this episode)"; "The good bit -- 1 hour 2 minutes in,
  1 minute long"; a live stream plays through the **ordinary transport**;
  Subscribe under Recommended is a **real** subscribe with artwork and
  episodes; Support opens in your browser.
- [ ] pass  [ ] fail: ______

**C-61. The button says what it will do**
- Do: arrow down a tab's list.
- Pass: the button changes -- *Open in Browser*, *Play*, *Subscribe to This
  Podcast* -- and reads *Nothing to Open*, disabled, on a row with nothing.
- [ ] pass  [ ] fail: ______

**C-62. A podcast that publishes none of it**
- Do: **About This Episode...** on a **99% Invisible** episode.
- Pass: the window still opens and says this podcast publishes no extra
  details. A greyed-out menu item here would be a fail.
- [ ] pass  [ ] fail: ______

**C-63. Transcripts**
- Do: on a **Buzzcast** episode, open the transcript; save it to a file; reopen
  it.
- Pass: it opens, saves, and reopens instantly from cache. Cast never generates
  one from audio -- that stays in QUILL.
- [ ] pass  [ ] fail: ______

**C-64. Episode notes**
- Do: **Add Episode Note...** while playing, then **My Notes in This
  Episode...**, then **Copy Note** and paste it somewhere.
- Pass: the note is stamped with the playing moment; Enter jumps playback there;
  from the Manager it starts the episode first, then jumps; the copied text
  carries episode, podcast, timestamp, your words and the audio link.
- [ ] pass  [ ] fail: ______

## Block I -- Downloads and housekeeping (10 min)

**C-65. Download one, and download all**
- Do: **Download Episode** from an episode's context menu; then **Download All
  Episodes** on the show.
- Pass: the file lands as `show-title\episode-title.mp3` under your download
  location; Download All queues everything not already there, with no extra
  confirmation.
- [ ] pass  [ ] fail: ______

**C-66. Remove All Downloads keeps Keep This Episode**
- Do: mark one episode **Keep This Episode**, then **Remove All Downloads...**
  on the show.
- Pass: only the files go; episodes, played state and positions stay; the kept
  one is skipped and the announcement says how many were kept.
- [ ] pass  [ ] fail: ______

**C-67. Automatic downloads**
- Do: **Podcast Settings > Automatically download**, set *newest 3*. Refresh.
- Pass: three arrive, and Cast says how many it started. Anything you add to the
  **Play Queue** downloads too; anything routed to the **Inbox** does not.
- [ ] pass  [ ] fail: ______

**C-68. A metered connection holds automatic downloads only**
- Do: mark your connection metered in Windows, wait for a refresh, then press
  **Download Episode** by hand.
- Pass: automatic downloads wait; the one you pressed happens anyway. An
  unknown connection counts as unmetered.
- [ ] pass  [ ] fail  [ ] cannot stage -- not run

**C-69. A dropped connection reconnects**
- Do: pull the network mid-download, restore it.
- Pass: *"Download connection dropped; reconnecting"* and it resumes -- it does
  not sit in Failed. The attempts and wait are configurable in Podcast Settings.
- [ ] pass  [ ] fail: ______

**C-70. Downloads... answers "how much disk"**
- Do: **Alt+D > Downloads...**, then tick **Unheard only**.
- Pass: a total, a breakdown by podcast largest first, and it says how many
  already-played downloads the filter hid. **Remove This Podcast's
  Downloads...** clears one show without touching the library.
- [ ] pass  [ ] fail: ______

**C-71. The two automatic rules, and what they will not touch**
- Do: set **Delete downloads after N days** and a **Total download storage
  cap**, then **Alt+D > Free Up Space**.
- Pass: it says how many bytes came back; a **queued or part-played** episode is
  never removed; if the cap cannot be reached it says what it could not free.
- [ ] pass  [ ] fail: ______

**C-72. Run Housekeeping Now**
- Do: **Alt+D > Run Housekeeping Now**.
- Pass: one sentence reporting everything it did -- expired queue items, the
  Recently Expired sweep, the Inbox trim, the storage rules.
- [ ] pass  [ ] fail: ______

**C-73. Pause and resume all downloads**
- Do: **Alt+D > Pause All Downloads**, then **Resume All Downloads**.
- Pass: both take effect and are announced.
- [ ] pass  [ ] fail: ______

## Block J -- Expiry, and getting things back (5 min)

**C-74. A queued episode expires into Recently Expired**
- Do: **Settings for This Podcast... > Expire from the queue**, set 1 day, and
  age a queued item (or run housekeeping after changing the clock).
- Pass: it moves to **Recently Expired** -- keeping its file, its position and
  its place in the show -- and the expiry is announced. Never is the default,
  and there is deliberately no global setting.
- [ ] pass  [ ] fail: ______

**C-75. Restore, Restore All, Forget This One**
- Do: use all three on Recently Expired rows.
- Pass: Restore puts it at the end of the queue with a fresh clock; Forget stops
  offering it and leaves its file alone. Only the seven-day sweep removes a
  downloaded copy.
- [ ] pass  [ ] fail: ______

**C-76. Re-published episodes**
- Do: on a show that re-publishes an episode, refresh.
- Pass: it is recognised rather than arriving as a duplicate.
- [ ] pass  [ ] fail  [ ] cannot stage -- not run

**C-77. Getting an episode back out**
- Do: **Save Episode Audio As...**, **Copy Podcast Link**, **Show in File
  Explorer**.
- Pass: Save copies rather than moves and suggests "Show - Episode" with illegal
  characters replaced; an undownloaded episode is offered a fetch instead of a
  progress bar you cannot escape; Copy Podcast Link gives the **feed** address
  (a local podcast says it has none); Show in File Explorer selects the file,
  and a streamed episode says it has none.
- [ ] pass  [ ] fail: ______

## Block K -- Statistics (4 min)

**C-78. Listening Statistics**
- Do: **Listening Statistics...**
- Pass: week / month / year / all time, what faster playback bought you,
  episodes finished, and a breakdown by podcast -- as arrowable, copyable text,
  with durations as language ("3 hours, 47 minutes"), never `3:47:00`.
- [ ] pass  [ ] fail: ______

**C-79. Export and clear**
- Do: **Export CSV...**, then **Clear Statistics...**
- Pass: every session exports; clearing deletes the log and nothing else.
- [ ] pass  [ ] fail: ______

**C-80. Retention is your choice**
- Do: **Podcast Settings**, set history retention to **don't keep one**.
- Pass: it stops the writing rather than deleting what exists. The log never
  leaves the machine either way.
- [ ] pass  [ ] fail: ______

**C-81. Year in Review, and streaks that are off by default**
- Do: **Year in Review...**; then turn streaks on in Podcast Settings.
- Pass: a few sentences you can arrow, copy or save -- not a dashboard -- and
  anything the log cannot support is **left out**, not printed as zero. Streaks
  are off until asked for, and a run that ended yesterday still counts as
  current.
- [ ] pass  [ ] fail: ______

## Block L -- Sharing and syncing (6 min)

**C-82. Share This Moment copies two things**
- Do: **Share This Moment** on a playing episode, then paste.
- Pass: a sentence -- "Blind Abilities, Episode 214, at 41 minutes 12 seconds"
  -- **and** a `quill-cast://` link that reopens it at that second.
- [ ] pass  [ ] fail: ______

**C-83. A link for a show you do not follow does nothing**
- Do: open a share link for a podcast you are not subscribed to.
- Pass: it says so and does nothing. Cast never fetches a web address, and never
  adds a subscription, because a link asked it to.
- [ ] pass  [ ] fail: ______

**C-84. Carry My Place -- the encrypted half**
- Do: **Help > Command Palette... (Ctrl+Shift+P)** > **Carry My Place Between
  Machines...**, choose a folder inside a service you already sync, set a
  recovery phrase.
- Pass: it sets up with no account and no server; only a machine with the phrase
  can read it.
- [ ] pass  [ ] fail: ______

**C-85. Listening Places -- the plain half**
- Do: in the same window turn on **A plain file other apps can read**.
- Pass: it needs **no recovery phrase**; every device writes exactly one file
  and reads the others (so no "conflicted copy" is ever produced); ids are
  hashed, and **Include episode and file names** is a separate switch.
- [ ] pass  [ ] fail: ______

**C-86. The two sync rules that matter**
- Do: jump back twenty minutes in an episode, then open it on the other
  machine. Then, with Cast open, change a position elsewhere and wait.
- Pass: the **most recent** position wins, not the furthest; and nothing is read
  mid-session -- only at launch and when you press **Sync Now**.
- [ ] pass  [ ] fail  [ ] one machine only -- not run

**C-87. Continue Listening spans the family**
- Do: **Continue Listening...** with an unfinished Quill Radio recording around.
- Pass: one list, newest first, each row naming its kind ("Rome, The Rest Is
  History, podcast, 20 minutes in, 33% through"); **Resume** and **Forget This
  One** behave as named -- forgetting leaves the episode unplayed; a radio
  recording Cast cannot play is still listed with Resume unavailable **and says
  so**.
- [ ] pass  [ ] fail: ______

## Block M -- Columns, Quick Actions, keys (7 min)

**C-88. Choose Columns**
- Do: **Ctrl+Alt+Shift+C** (Subscriptions > Choose Columns...). Move a column
  up, **Hide** another, read the **A row will read:** line, press OK.
- Pass: the preview matches what rows then say; a hidden column is **absent
  from the row**, not last; showing it again returns it to its place, not the
  end; the pinned column refuses to be hidden **and says why**.
- [ ] pass  [ ] fail: ______

**C-89. Three lists, and the off-by-default columns**
- Do: switch between the **episode list**, **Downloads** and **Add Podcast's
  results**.
- Pass: the episode list offers **Podcast**, **Time Left** and **Downloaded**
  (all off by default); Add Podcast offers **Feed Address**. **Reset This
  List** restores one list. Changing the layout while the Manager is open takes
  effect there and then.
- [ ] pass  [ ] fail: ______

**C-90. Quick Actions decide what Enter does**
- Do: **Alt+S > Quick Actions...**, move **Download** to the top of the episode
  list with **Make Default**. Then press **Enter** on an episode, and
  **Ctrl+3**.
- Pass: Enter now downloads; Ctrl+1..Ctrl+9 run the first nine in order; the
  right-click menu is in the same order. **Reset This List** restores the
  shipped order.
- [ ] pass  [ ] fail: ______

**C-91. Winamp keys, and typeahead**
- Do: in a list, press **X**, **C**, **V**, **B**, **Z**, **T**, **J**,
  **Ctrl+J**. Then focus a text box and type those letters.
- Pass: play / pause / stop / next / previous / elapsed-or-remaining / jump to
  episode / jump to a time -- and **never** while a text box has focus. Turning
  them off in **Ctrl+,** returns the letters to typeahead; Ctrl+Up and
  Ctrl+Down keep working either way.
- [ ] pass  [ ] fail: ______

**C-92. Hardware media keys**
- Do: press the keyboard's Play/Pause, Stop and Next/Previous Track -- including
  from the tray.
- Pass: they control Cast system-wide; Next/Previous map to chapters; a key
  another app already owns is left alone. Starting an episode silences a playing
  radio stream and vice versa -- nothing double-plays.
- [ ] pass  [ ] fail  [ ] no media keys -- not run

**C-93. Global hotkeys**
- Do: **Help > Global Hotkeys...**, assign Play/Pause, then use it from another
  program. Note that **Show/Hide to the Tray** starts on **Ctrl+Alt+Shift+Q**.
- Pass: only the safe commands can be bound; the first assignment warns that a
  system-wide key may override the same key elsewhere; a key another app owns is
  left alone. If you also run QUILL, that chord collides by design -- change one
  of them here and confirm the change sticks.
- [ ] pass  [ ] fail: ______

**C-94. The Keyboard Manager is shared with the family**
- Do: **Help > Keyboard Shortcuts...**, search for a command, reassign it,
  then check the same command in Quill Radio.
- Pass: conflicts and risky keys are warned about; the change reaches the whole
  family; a two-key chord or a comma key keeps its built-in shortcut until the
  next launch.
- [ ] pass  [ ] fail: ______

**C-95. The Command Palette**
- Do: **Ctrl+Shift+P**, type part of a command name.
- Pass: every Cast command is reachable and searchable here.
- [ ] pass  [ ] fail: ______

## Block N -- The window, the tray, your data (6 min)

**C-96. Send to tray, and Alt+F4**
- Do: **Ctrl+W**. Then bring it back and, with the preference on, press
  **Alt+F4** while playing.
- Pass: the window tucks away with playback running and says so; the titlebar X
  and **Exit** still exit. Right-click (or **Shift+F10**) the tray icon for
  Show, podcast controls and Exit; double-click restores.
- [ ] pass  [ ] fail: ______

**C-97. Import a large OPML**
- Do: **Import OPML...** on an export of a thousand or more feeds, with **Check
  that each feed is still reachable** ticked. Use **Stop Checking** part way.
- Pass: it runs in the background without freezing; `http://` and `https://`
  twins count as one feed; two shows sharing only a *title* are both imported
  and flagged; progress every ten per cent; stopping keeps everything already
  imported; **Add every show as streaming** is ticked by default.
- [ ] pass  [ ] fail: ______

**C-98. The import report**
- Do: from that report, **Export Report...** and **Save Pruned OPML...**
- Pass: corrections, unreachable feeds, skipped duplicates and failures are all
  listed; a feed asking for a sign-in counts as **reachable**; the pruned file
  keeps your folders and drops only the dead feeds.
- [ ] pass  [ ] fail: ______

**C-99. Opening an OPML from Explorer**
- Do: if you ticked the installer's file-association box, double-click a
  `.opml` file.
- Pass: Cast opens **straight into the import** and names the file. The box is
  **off** unless asked for, and uninstalling gives the file type back.
- [ ] pass  [ ] fail  [ ] association not enabled

**C-100. Export My Data**
- Do: **Alt+S > Export My Data...**, open the result.
- Pass: one readable JSON file with subscriptions, folders, the Play Queue,
  playlists, notes, statistics and recently played -- and **no passwords**.
- [ ] pass  [ ] fail: ______

**C-101. Delete All Podcast Data asks twice**
- Do: **Alt+S > Delete All Podcast Data...** -- then **cancel**.
- Pass: it asks twice, and asks about downloaded **files** separately. Both
  questions open on **No**.
- [ ] pass  [ ] fail: ______

**C-102. Destructive questions all open on No**
- Do: open **Delete Folder**, **Delete Playlist**, **Remove All Episodes** and
  **Delete Downloaded Files**.
- Pass: every one opens with **No** selected. Reflexive Enter can never lose
  data.
- [ ] pass  [ ] fail: ______

## Block O -- Announcements, Safe Mode, updates (5 min)

**C-103. Speech and braille together**
- Do: with a braille display connected, trigger a burst (a refresh cascade or a
  download reporting in), then trigger an error.
- Pass: speech never steals focus; braille gets the same messages; a burst
  settles to the newest rather than flickering; an **error** is written straight
  through and can be held.
- [ ] pass  [ ] fail  [ ] no display -- not run

**C-104. Braille settings live in QUILL**
- Do: change braille style in **QUILL > Preferences > Accessibility**.
- Pass: the change applies to Cast and Radio too; turning braille off there
  turns it off here.
- [ ] pass  [ ] fail: ______

**C-105. Safe Mode**
- Do: relaunch with `--safe-mode`. Try a refresh, a download, Add Podcast, and
  the Quillins menu.
- Pass: network features refuse out loud and nothing reaches the network;
  downloads never run; Quillins are off.
- [ ] pass  [ ] fail: ______

**C-106. Quillins**
- Do: open the **Quillins** menu normally.
- Pass: only add-ons that declare QUILL Cast appear (the bundled
  `cast-premium-auth` sample among them); third-party Quillins stay disabled in
  this release.
- [ ] pass  [ ] fail: ______

**C-107. Check for Updates**
- Do: **Help > Check for Updates...**
- Pass: it compares versions, downloads in-app with spoken progress, then offers
  **Install now** or **Open folder** -- and shows a **dialog** when already up
  to date, not just an announcement. The quiet daily check is switchable off in
  **Ctrl+,**.
- [ ] pass  [ ] fail: ______

**C-108. Redeem Unlock Code**
- Do: **Help > Redeem Unlock Code...** with a signed code.
- Pass: verified entirely on the machine, nothing transmitted, and the unlock
  counts for QUILL and Quill Radio too.
- [ ] pass  [ ] fail  [ ] no code -- not run

## Block P -- One library, three apps (4 min)

**C-109. Subscribe here, subscribed everywhere**
- Do: subscribe in Cast, then look in QUILL's Podcasts and in Quill Radio's
  Browse Stations > Podcasts > Subscriptions.
- Pass: one library. Queue, positions, notes and downloads are one set of data.
- [ ] pass  [ ] fail: ______

**C-110. Radio's folder and badge changes land here**
- Do: create a folder and move a show **from Quill Radio** (see radio-signoff
  R-22), then open Cast's manager.
- Pass: the changes are simply there, with matching unheard counts.
- [ ] pass  [ ] fail: ______

**C-111. Radio's hand-off instructions arrive**
- Do: use **Play Next in QUILL Cast**, **Add to QUILL Cast Queue** and **Send to
  the QUILL Cast Inbox** from Radio, then open Cast.
- Pass: each lands. An instruction waits for Cast rather than being silently
  discarded -- an older Cast simply never opens the file.
- [ ] pass  [ ] fail: ______

**C-112. Mark All as Played dims and shares its answer**
- Do: in Cast, **Mark All as Play&ed...** on a show with nothing unheard; then
  tick **Don't ask me again** on another and try the same in Radio.
- Pass: the menu item is present but **dimmed** when there is nothing to do, and
  neither app asks again.
- [ ] pass  [ ] fail: ______

**C-113. Local podcasts stay out of the shared folder**
- Do: check where a local podcast's data lives.
- Pass: outside the synced data folder, by construction. Uninstalling Cast never
  deletes the shared store.
- [ ] pass  [ ] fail: ______

## Block Q -- Spotify (optional, skip freely)

**C-114. Off and invisible until deliberately enabled**
- Do: on an ordinary install, look for Spotify items in the **Help** menu.
- Pass: there are none, and nothing has reached Spotify's servers.
- [ ] pass  [ ] fail: ______

**C-115. Connect and play**
- Do: with the feature unlocked, Premium, your own Client ID (redirect exactly
  `http://127.0.0.1:43217/callback`) and WebView2: **Help > Connect to
  Spotify...**, then **Browse Spotify Podcasts...**
- Pass: sign-in returns to the local address, tokens go to the Windows
  credential vault, and an episode plays with the ordinary transport, status
  bar, tray and global hotkeys driving it.
- [ ] pass  [ ] fail  [ ] skipped

**C-116. Spotify episodes are play-only**
- Do: look for **Download** on a Spotify episode.
- Pass: there is none, and the reason is copy protection. Spotify is off in Safe
  Mode, and the first sign-in asks a one-time network-access confirmation.
- [ ] pass  [ ] fail  [ ] skipped

---

## Sign-off

- Build / version: ______________
- Date: ______________
- Screen reader and version: ______________
- Windows version: ______________
- Blocks run: ______________
- Result: [ ] ship  [ ] ship with the findings below  [ ] do not ship

**For every fail, report three things:** the test id (C-71, say), what was said
**word for word**, and what you expected to hear. A step that did nothing at
all is the most serious kind of failure here -- report it even when nothing
looks broken.
