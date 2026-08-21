# Quill Radio -- sign-off checklist

One pass, top to bottom, ticking boxes. Every step says exactly what to press,
exactly what to type, and the one thing that decides pass or fail. Nothing here
needs an account or a key except Block M (Spotify), which is optional.

The reasoning, the background, and the "why this test exists" prose live in
[radio-3.0-test-plan.md](radio-3.0-test-plan.md). This file is the fast run.

## Before you start (3 minutes)

- Install or launch the build under test. Note the version from
  **Help > About Quill Radio (Alt+F1)**: `____________`
- Have a screen reader running and speaking (JAWS or NVDA).
- Downloads land in `Downloads\Quill Radio` -- `Books\`, `Podcasts\`, `Music\`
  underneath -- unless you change it.
- **Fail means:** it did not happen, or it happened silently, or what you heard
  differs from what this file quotes. Write down what you actually heard. A
  silent success is a fail.
- Safe Mode is `quill-radio.exe --safe-mode`, or the `--safe-mode` shortcut.

## The 20-minute pass

No time for the whole thing? Run exactly these ten and stop -- all are quick
and need no long download or multi-app setup:
**R-02, R-04, R-08, R-14, R-18, R-37, R-45, R-55, R-69, R-73.**
All ten green is a credible smoke test.

---

## Block A -- Starting up (5 min)

**R-01. First run**
- Do: launch a copy with no settings yet (or a fresh profile).
- Pass: the first-run screens appear, each a text box you can arrow through,
  and **Skip** leaves in one keystroke and never asks again.
- [ ] pass  [ ] fail: ______

**R-02. Play a station**
- Do: **Ctrl+F**, type `BBC World Service`, **Enter**, then **Enter** on the
  BBC World Service row.
- Pass: audio inside a few seconds **and** the station name is spoken.
- [ ] pass  [ ] fail: ______

**R-03. Stop and resume**
- Do: **Playback > Stop**, wait two seconds, **Playback > Play (Ctrl+P)**.
- Pass: the same station resumes. No re-search, no prompt.
- [ ] pass  [ ] fail: ______

**R-04. Sound Enhancements apply live**
- Do: with that station playing, **Ctrl+E**, move any slider a large step.
- Pass: audible immediately. A gap, stutter or reconnect is a fail.
- [ ] pass  [ ] fail: ______

**R-05. The catalog says where its answers come from**
- Do: **Ctrl+Alt+Shift+S** (View > Station Catalog Status...).
- Pass: every source is named, with whether it is stored, how fresh it is, and
  why the live-only ones are live-only.
- [ ] pass  [ ] fail: ______

**R-06. Audio Health**
- Do: **Ctrl+Alt+Shift+M** (Audio Health...).
- Pass: it opens and reports the current engine and device state in sentences.
- [ ] pass  [ ] fail: ______

## Block B -- Browse Stations (8 min)

**R-07. Loading rows, then a count**
- Do: **Ctrl+B** (Station > Browse Stations...), arrow to **Internet Archive**,
  press **Right arrow**.
- Pass: a *"Loading..."* row first, then real rows **and a count** ("24 items").
- [ ] pass  [ ] fail: ______

**R-08. The cache**
- Do: **Left arrow** to collapse, **Right arrow** to expand again.
- Pass: instant, the count again, and **no second** "Loading...".
- [ ] pass  [ ] fail: ______

**R-09. Offline browsing answers from your own disk**
- Do: turn off the network (airplane mode). Expand **By Country**, then a
  country.
- Pass: rows arrive instantly with counts, and offline browsing announces
  itself once per session.
- [ ] pass  [ ] fail: ______

**R-10. The two kinds of empty**
- Do: still offline, expand a branch you have **not** opened before.
- Pass: the placeholder clears -- never stuck on "Loading..." -- and you hear
  one of: *"Nothing in X. It may be empty, or the source could not be
  reached."* or *"X could not be reached. Close and reopen it to try again."*
- [ ] pass  [ ] fail: ______

**R-11. A failed branch retries**
- Do: restore the network. Collapse and re-expand the same branch.
- Pass: real rows arrive. A branch is never permanently stuck.
- [ ] pass  [ ] fail: ______

**R-12. Choosing which branches exist**
- Do: **Ctrl+Shift+Alt+O** (Station > Choose Browse Sources...), hide one
  source, OK, reopen Browse Stations.
- Pass: that branch is gone; everything else is where it was.
- [ ] pass  [ ] fail: ______

**R-13. Update the catalog by hand**
- Do: **Ctrl+Alt+Shift+G** (Update Station Catalog).
- Pass: a spoken summary of what changed. The window stays usable throughout.
- [ ] pass  [ ] fail: ______

## Block C -- Search (5 min)

**R-14. Five searches, five sources**
- Do: **Ctrl+F** and run each, waiting for the late arrivals:
  `Middlemarch` (LibriVox), `Sherlock` (Project Gutenberg),
  `Johnny Dollar` (Internet Archive), `The Rest Is History` (Podcasts),
  `jazz` (Audius, ccMixter, Mixcloud).
- Pass: stations answer first, libraries after, and you are told **once** when
  they have all reported.
- [ ] pass  [ ] fail: ______

**R-15. Your place is kept**
- Do: start arrowing the results while a late group is still landing.
- Pass: the cursor does not jump.
- [ ] pass  [ ] fail: ______

**R-16. The row carries its own truth**
- Do: on the `jazz` results, arrow to a **ccMixter** row, then a **Mixcloud**
  row -- before pressing anything.
- Pass: ccMixter speaks its licence in the row; Mixcloud says *"opens on
  Mixcloud in your browser"* in the row, not after Enter.
- [ ] pass  [ ] fail: ______

**R-17. Search All Sources, and search one source**
- Do: open Browse Stations. The **first row** is **Search All Sources...** --
  press Enter on it. Then Escape, and open the context menu (**Shift+F10**) on
  **Podcasts (Apple)** and choose **Search This Source...**.
- Pass: the first opens search with the filter on **All sources**; the second
  opens it pre-filtered to **Podcasts**. Sources with no search of their own
  (Weather / NOAA, NFB Radio) offer no such item.
- [ ] pass  [ ] fail: ______

## Block D -- Podcasts (15 min)

Test feeds that publish Podcasting 2.0 tags:

| Show | Feed |
| --- | --- |
| Podcasting 2.0 | `https://feeds.podcastindex.org/pc20.xml` |
| Buzzcast | `https://feeds.buzzsprout.com/1538779.rss` |
| No Agenda | `https://feed.nashownotes.com/rss.xml` |

Test feeds that publish none (the honest-absence cases):

| Show | Feed |
| --- | --- |
| The Rest Is History | `https://feeds.megaphone.fm/GLT4787413333` |
| 99% Invisible | `https://feeds.simplecast.com/BqbsxVfO` |
| Radiolab | `https://feeds.simplecast.com/EmVW7VGp` |

**R-18. Reach a show and play an episode**
- Do: **Ctrl+F**, type `Podcasting 2.0`, **Enter**. Enter on the show row, then
  Enter on an episode.
- Pass: episodes list newest first; audio starts and the episode is named.
- [ ] pass  [ ] fail: ______

**R-19. The Apple browse path, including a leaf genre**
- Do: Browse Stations > **Podcasts (Apple)** > **United States** > expand
  **Arts**.
- Pass: sub-areas (Books, Design, Food) appear. An empty Arts branch is the old
  leaf-genre bug.
- [ ] pass  [ ] fail: ______

**R-20. Subscriptions shows Cast's folders with unheard badges**
- Setup: in QUILL Cast, put a subscribed show in a folder, leave an episode
  unplayed.
- Do: Browse Stations > **Podcasts** > **Subscriptions**.
- Pass: the folder is **first**, labelled with its subtree count ("News (2
  unheard)"); shows inside carry their own counts.
- [ ] pass  [ ] fail: ______

**R-21. A badge appears without ever opening Cast**
- Do: subscribe to a show from Radio, open it once under Subscriptions,
  collapse and re-expand.
- Pass: the show now carries its "(N unheard)" badge.
- [ ] pass  [ ] fail: ______

**R-22. Folders made, filled, renamed and deleted from Radio**
- Do: on **Subscriptions**, **Shift+F10 > New Folder...**, type `Tech`, OK. On
  a show row, **Move to Folder...**, arrow to `Tech`, **Enter**. On the folder,
  **Rename Folder...** to `Technology`, then **Delete Folder...**.
- Pass, in order: *"Created folder Tech. It is shared with Quill Cast."*;
  *"Moved <show> to Tech."* with the cursor landing on the show inside the
  folder and no refresh chore; *"Renamed Tech to Technology."*; *"Deleted
  folder Technology. Its podcasts moved up a level; nothing was
  unsubscribed."*
- [ ] pass  [ ] fail: ______

**R-23. Add a Podcast by URL**
- Do: **Shift+F10** on the **Podcasts** branch (and on **Subscriptions**) >
  **Add a Podcast by URL...**, paste `https://feeds.buzzsprout.com/1538779.rss`.
- Pass: *"Checking that feed..."* then *"Subscribed to <show>. N episodes are
  listed, and the show is shared with Quill Cast."*, with the cursor on the new
  show and episodes already listed.
- [ ] pass  [ ] fail: ______

**R-24. The refusals are specific, one at a time**
- Do: feed the same dialog, one per attempt: nothing at all; `the daily`;
  `https://www.bbc.co.uk/` (a web page); a made-up address such as
  `https://example.invalid/feed.xml`.
- Pass: four **different** sentences -- paste an address first / that does not
  look like a web address / answers with a web page, not a podcast feed / could
  not be read as a feed. A bare "invalid" anywhere is a fail.
- [ ] pass  [ ] fail: ______

**R-25. The empty branch helps**
- Do: on a profile with no subscriptions, expand **Subscriptions**.
- Pass: exactly three rows, each of which acts on Enter -- **Add a Podcast by
  URL...**, **Import Podcasts from OPML...**, **Search for a Podcast...**
- [ ] pass  [ ] fail: ______

**R-26. Import OPML**
- Do: **Shift+F10** on the **Podcasts** branch > **Import Podcasts from
  OPML...**, pick any OPML export. Then import the **same file again**.
- Pass: *"Importing podcasts..."* with the tree still usable; a count on
  finishing; the second run reports *"Imported 0 podcasts"* and no duplicates.
  Quit and reopen -- everything is still there.
- [ ] pass  [ ] fail: ______

**R-27. Mark All as Played, and the dimmed verb**
- Do: **Shift+F10** on a show with unheard episodes > **Mark All as
  Played...**, accept. Reopen the menu.
- Pass: *"Marked N episodes of <show> as played."*, badge gone on screen
  immediately, cursor back on the show; the menu item is still **there** but
  **dimmed**. A vanished item is a fail.
- [ ] pass  [ ] fail: ______

**R-28. Don't ask me again crosses to Cast**
- Do: on another show, tick **"Don't ask me again"** and accept. Try the same
  command in **QUILL Cast**.
- Pass: neither app asks again. (Cancelling with the box ticked must change
  nothing.)
- [ ] pass  [ ] fail: ______

**R-29. A Cast position continues in Radio**
- Setup: in Cast, play an episode two minutes, stop.
- Do: play the same episode in Radio.
- Pass: *"Resuming at 2 minutes 10 seconds."* -- Cast's position, in words.
- [ ] pass  [ ] fail: ______

**R-30. The show's speed follows the show**
- Setup: in Cast, set a show's speed to 1.5x.
- Do: play one of its episodes in Radio, then press **Ctrl+Shift+Up**.
- Pass: it starts at 1.5x, and the press says *"1.75 times speed. Remembered
  for this show."* Return later: 1.75x, and Cast still says 1.5x.
- [ ] pass  [ ] fail: ______

**R-31. Marking one episode, and a badge that believes your ears**
- Do: **Shift+F10** on an episode > **Mark Episode as Played**. Then play a
  different episode of that show **to the end**.
- Pass: the badge drops by one each time, immediately, without opening Cast.
- [ ] pass  [ ] fail: ______

**R-32. Handing an episode to Cast**
- Do: **Shift+F10** on a subscribed show's episode row.
- Pass: **Play Next in QUILL Cast**, **Add to QUILL Cast Queue** and **Send to
  the QUILL Cast Inbox** are on the menu, and each lands in Cast (next launch
  is acceptable; being silently discarded is not).
- [ ] pass  [ ] fail: ______

**R-33. Download one, download all, take them back**
- Do: **Shift+F10** on an episode row > **Download...**. Then on the show row >
  **Download All N Episodes...**, then **Remove All Downloads...**.
- Pass: the file lands under `Downloads\Quill Radio\Podcasts\<Show>\`; the
  queue says *"Queued ... You can carry on listening."*; Remove All confirms
  with the real file count, says *"Your subscription and played state are
  untouched."*, and leaves every badge as it was.
- [ ] pass  [ ] fail: ______

**R-34. A private feed works here too**
- Do: with a credentialed feed saved in Cast, open that show in Radio.
- Pass: its episodes list, exactly like a public feed. (No such feed? Mark
  **not run** rather than skipping silently.)
- [ ] pass  [ ] fail  [ ] not run

**R-35. Chapters on a podcast episode**
- Do: play an episode of **Podcasting 2.0** or **No Agenda**, give it a few
  seconds, then **Ctrl+Shift+C** and **Ctrl+Shift+.** / **Ctrl+Shift+,**.
- Pass: the publisher's own chapter titles. On an unchaptered feed, the same
  commands give the honest "no chapters" answer, never an invented marker.
- [ ] pass  [ ] fail: ______

**R-36. Record and rename from the row**
- Do: **Shift+F10** on a **live station** row.
- Pass: **Record This Station...** and **Schedule Recording...** are there,
  pre-filled with *that* station; on a favorite, **Rename Favorite...** too.
  Episode and chapter rows offer no Record items.
- [ ] pass  [ ] fail: ______

## Block E -- Transcripts (6 min)

**R-37. Read a transcript without playing anything**
- Do: reach a **Podcasting 2.0** episode row, **Shift+F10 > View
  Transcript...**
- Pass: *"Fetching transcript..."*, then a read-only text box, one caption line
  per row -- and **nothing starts playing**.
- [ ] pass  [ ] fail: ______

**R-38. The caret is yours**
- Do: with the episode playing, arrow around the transcript.
- Pass: the caret never moves on its own. (There is no "follow the audio"
  checkbox any more. If you find one, fail.)
- [ ] pass  [ ] fail: ______

**R-39. Enter plays from a line; Find lands on the match**
- Do: put the caret on a line, press **Enter**. Then use **Find** for a word
  further down.
- Pass: *"Playing from 4 minutes 12 seconds."* and the audio jumps there;
  *"Found at 12 minutes 8 seconds. Enter plays from here."* -- always words,
  never `4:12`. With nothing playing, the same sentence without the second half.
- [ ] pass  [ ] fail: ______

**R-40. Links, and Save As**
- Do: press **Links... (Ctrl+Shift+L)**, then **Save As...** and save as
  **WebVTT**, then open the saved file.
- Pass: each link read as name then address, with Open / Copy Address / Copy
  All working; a transcript with none says *"There are no web addresses in this
  transcript."* out loud; the saved cue timings match what the reader spoke.
- [ ] pass  [ ] fail: ______

**R-41. The honest absences, one each**
- Do: **Ctrl+Shift+T** while a **live station** plays; then on a **video with
  no captions**; then **View Transcript...** in Safe Mode. And check a
  *Radiolab* episode row.
- Pass: three distinct spoken sentences (live stream / no captions published /
  disabled in Safe Mode), and the Radiolab row simply **has no View
  Transcript... item** rather than opening an empty reader.
- [ ] pass  [ ] fail: ______

**R-42. Automatic captions are labelled automatic**
- Do: play any casual YouTube upload (not one from the table below) and press
  **Ctrl+Shift+T**.
- Pass: the reader's heading says the transcript is automatically generated.
- [ ] pass  [ ] fail: ______

## Block F -- Video, captions, described audio (10 min)

| Video | URL | Tracks |
| --- | --- | --- |
| TED talk | `https://www.youtube.com/watch?v=iG9CE55wbtY` | 1 |
| Big Buck Bunny | `https://www.youtube.com/watch?v=YE7VzlLtp-4` | 1 |
| MrBeast (dubbed) | `https://www.youtube.com/watch?v=0e3GPea1Tyg` | 24 |
| ART LAB (really described) | `https://www.youtube.com/watch?v=UusppshIAio` | 2 |

**R-43. Show the picture without losing the sound**
- Do: play the TED talk (paste the URL into **Ctrl+F**), let it settle, press
  **Ctrl+Shift+V**. Press it again. Then **F11**.
- Pass: *"Video shown, 1280 by 720."*, no audio gap; *"Video hidden. Audio is
  still playing."*; full screen announces **both** ways out.
- [ ] pass  [ ] fail: ______

**R-44. Captions**
- Do: **Ctrl+Shift+K**, then **Ctrl+Shift+Alt+T** and set size to 300%, then
  **Ctrl+Shift+K** again.
- Pass: captions appear and go, each said out loud; text scales; the background
  stays opaque.
- [ ] pass  [ ] fail: ______

**R-45. The track picker counts correctly**
- Do: **Ctrl+Shift+A** on the TED talk, then on MrBeast.
- Pass: TED = **exactly one** row, "English"; MrBeast = **24** rows, every one a
  language *name* ("Tamil", "Bangla"), never a code, fragment or duplicate.
  Both under the heading *"No described audio was published for this video."*
- [ ] pass  [ ] fail: ______

**R-46. The absence path is spoken, not silent**
- Do: **Ctrl+Alt+D** on the TED talk. Then **Ctrl+Alt+D** while a **live
  station** plays.
- Pass: an honest answer both times -- the second is *"This is a live stream,
  so it has no described audio track to choose."* Silence is a fail.
- [ ] pass  [ ] fail: ______

**R-47. The presence path**
- Do: play the **ART LAB** video and listen. Then **Ctrl+Shift+A**. Note your
  position with **Ctrl+Shift+I**, switch to the described track, check again.
- Pass: *"Described audio is available for this video. Press Ctrl+Alt+D to hear
  the narration of what is on screen."* -- **once**; the picker heading says it
  is available, the described track is **first** with the cursor already on it;
  the narration is audibly there; the position **survives the switch**.
- [ ] pass  [ ] fail: ______

**R-48. A described upload that is one track**
- Do: **Ctrl+Shift+A** on `https://www.youtube.com/watch?v=LYKUnym0EqU`
  (Microsoft, audio-described version).
- Pass: the *absence* heading and one row -- correct, because the description is
  mixed into the only track. An invented second row is a fail.
- [ ] pass  [ ] fail: ______

## Block G -- YouTube and playlists (5 min)

**R-49. Follow a channel**
- Do: Browse Stations > **YouTube Channels** > its Add action, paste
  `https://www.youtube.com/@TED`.
- Pass: recent videos appear as rows, each playable with Enter.
- [ ] pass  [ ] fail: ______

**R-50. A playlist becomes stations**
- Do: **Station > Add from YouTube Playlist...**, paste
  `https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Blw3RGYpWkSByi_T7Rygb`.
- Pass: **19 entries** added. A different count is a finding.
- [ ] pass  [ ] fail: ______

**R-51. Import a .pls**
- Do: save `https://somafm.com/groovesalad.pls`, then **Ctrl+I** (Station >
  Import Stations from Playlist...) and pick it.
- Pass: **3 entries**, each playable.
- [ ] pass  [ ] fail: ______

**R-52. The M3U round trip**
- Do: **Ctrl+Shift+X** to export favorites as `.m3u`, then **Ctrl+I** to import
  that same file.
- Pass: the same stations, in the same order.
- [ ] pass  [ ] fail: ______

**R-53. A Live365 page becomes a stream**
- Do: paste any `https://live365.com/station/...` **page** address where a
  stream URL is accepted.
- Pass: it is rewritten to the real stream **and the app says it did so**.
- [ ] pass  [ ] fail: ______

## Block H -- Downloads (12 min)

**R-54. Download Preferences**
- Do: **Ctrl+Alt+Shift+D**. Listen without touching anything, then toggle a
  checkbox, then Cancel.
- Pass: focus lands in the folder field and its name explains what blank means;
  the summary sentence updates on every toggle; Cancel changes nothing.
- [ ] pass  [ ] fail: ______

**R-55. What may and may not be saved**
- Do: open **Shift+F10** on each row kind and look for **Download...**:
  a LibriVox chapter (search `Middlemarch`), the BBC live station, a Mixcloud
  row, a YouTube video, an Audius track, a ccMixter track (search `jazz`).
- Pass: offered on the LibriVox chapter and the ccMixter track only; the other
  four have **no Download item**, and asking through the command palette gives a
  refusal that names the reason (no end / Mixcloud opens in the browser /
  deliberately not from YouTube / the artist's choice). The ccMixter download
  saves a `.licence.txt` beside the audio.
- [ ] pass  [ ] fail: ______

**R-56. A whole book, and one folder prompt**
- Do: turn on "Ask where to save each download" in R-54, then in Browse
  Stations put the cursor on Middlemarch's **folder** (LibriVox) >
  **Download All 86 Files...**
- Pass: **one** folder prompt for the whole book, never 86; *"Queued
  Middlemarch... You can carry on listening."*; cancelling the prompt says
  *"Download cancelled. Nothing was queued."*
- [ ] pass  [ ] fail: ______

**R-57. The downloads list reads as sentences**
- Do: play a live station while it downloads, then **Ctrl+Shift+J** (View >
  Downloads...) and arrow the rows.
- Pass: playback unaffected; rows read *"Chapter 4, Middlemarch, downloading
  now"* -- state **last**; a heartbeat every few chapters (*"12 of 86."*);
  finished rows stay in the list.
- [ ] pass  [ ] fail: ______

**R-58. The list's own verbs**
- Do: on a finished row, **Open Containing Folder**. On a waiting row, **Cancel
  This One**. On the running row, **Remove From List**. Then **Clear Finished**
  and **Clear All**.
- Pass: Explorer opens **with the file selected**; the waiting one cancels and
  keeps what was saved; the running one is refused -- *"That one is downloading
  now. Cancel it first."*; clearing empties the list and touches nothing on
  disk.
- [ ] pass  [ ] fail: ______

**R-59. Where things land**
- Do: download a second book by the same author, a podcast episode, and a
  ccMixter track.
- Pass: `Books\Middlemarch\` for the first book with **no** author folder; an
  author folder appears only once a second book needs to disambiguate;
  `Podcasts\<show>\`; `Music\`.
- [ ] pass  [ ] fail: ______

**R-60. Interruption and resume**
- Do: kill the network mid-chapter, restore it, download the same book again.
  Then cancel a download mid-chapter.
- Pass: that chapter fails and the **next one still runs**; part-finished files
  **resume** rather than restart; the cancel stops within seconds.
- [ ] pass  [ ] fail: ______

**R-61. Quitting with downloads outstanding**
- Do: press **Alt+F4** while downloads are running.
- Pass: they keep going or they stop, per your preference -- and the app
  **says which**.
- [ ] pass  [ ] fail: ______

## Block I -- Books and Continue Listening (6 min)

**R-62. Chapters chain in numeric order**
- Do: play chapter 1 of the downloaded Middlemarch, hands off to its end.
- Pass: chapter 2 starts on its own, announced *"2 of 86, ..."* -- position
  **first**. Chapter 2 plays before chapter 10.
- [ ] pass  [ ] fail: ______

**R-63. The last chapter says so**
- Do: play the last chapter to its end.
- Pass: playback stops and says *"That was the last chapter of Middlemarch."*
- [ ] pass  [ ] fail: ______

**R-64. Three kinds of unfinished thing**
- Do: leave a podcast episode, a streamed LibriVox chapter and a downloaded
  file each part-played, then **Ctrl+Alt+Shift+L** (Playback > Continue
  Listening...). This key changed: it was `Ctrl+Shift+Alt+C`, which is the same
  chord as Choose Columns, so one of the two never fired.
- Pass: all three, newest first, each naming its kind and how far in; an opening
  summary such as *"2 things you did not finish, across recordings, podcasts."*
- [ ] pass  [ ] fail: ______

**R-65. Resume, forget, and the missing file**
- Do: Resume one row. **Forget This One** on another. Move a downloaded file in
  Explorer and reopen the list; then play it from its new place and reopen.
- Pass: resume starts where you left off; forgetting removes the row and leaves
  the episode **unplayed**; the moved file's row is quietly absent, and comes
  back pointing at the new place.
- [ ] pass  [ ] fail: ______

## Block J -- Recording (4 min)

**R-66. A thirty-second capture**
- Do: with a station playing, press the **Record** button, wait 30 seconds,
  press it again. Check **Recording > Recordings...**
- Pass: the button reads **Stop Recording** while recording and **Record**
  after; the file is listed; the stop is announced. A silent stop is a fail.
- [ ] pass  [ ] fail: ______

**R-67. Honesty about an empty capture**
- Do: record a station producing no audio.
- Pass: reported as capturing nothing, and the empty file is deleted.
- [ ] pass  [ ] fail: ______

**R-68. Scheduling in hours and minutes**
- Do: **Recording > Schedule Recording...**
- Pass: separate **Hours** and **Minutes** boxes -- "3" and "0" is three hours.
- [ ] pass  [ ] fail: ______

## Block K -- Lists, columns and the window (5 min)

**R-69. Choose Columns**
- Do: **View > Choose Columns...**, move a column up, **Hide** another, read
  the **A row will read:** line, press OK.
- Pass: the preview line matches what rows then actually say; a hidden column
  is **absent from the row**, not moved to the end; the pinned column refuses
  to be hidden and says why; **Reset This List** restores the shipped order.
- [ ] pass  [ ] fail: ______

**R-70. It survives a restart**
- Do: quit and relaunch, return to the same list.
- Pass: your column order and hiding are still in force.
- [ ] pass  [ ] fail: ______

**R-71. Alt+F4 to tray**
- Do: with the preference on, press **Alt+F4** while playing.
- Pass: the window tucks away, playback continues, and it says so. The titlebar
  X and Exit still exit.
- [ ] pass  [ ] fail: ______

**R-72. The QuillVille menu**
- Do: open the **QuillVille** menu.
- Pass: **QUILL** and **Quill Weather** only. Inkwell is deliberately not there.
- [ ] pass  [ ] fail: ______

## Block L -- Safe Mode and updates (5 min)

**R-73. Refusals are per-branch and by name**
- Do: relaunch with `--safe-mode`. Expand **TuneIn**; then try Favorites,
  **ACB Media**, **NFB Radio** and **Networks**.
- Pass: *"TuneIn is disabled in Safe Mode."* by name; the four offline branches
  still work.
- [ ] pass  [ ] fail: ______

**R-74. Safe Mode refuses before it asks**
- Do: in Safe Mode, press **Ctrl+F** and search; try a download; try **Add a
  Podcast by URL...**; try **Import Podcasts from OPML...**
- Pass: each refuses out loud, and **no request leaves the machine**. The OPML
  one says *"Importing is disabled in Safe Mode. Restart Quill Radio
  normally."*
- [ ] pass  [ ] fail: ______

**R-75. Check for Updates knows which edition you installed**
- Do: **Ctrl+Alt+U** (Help > Check for Updates...).
- Pass: it offers the edition you actually have (installer vs portable), with
  spoken progress, and says so plainly when you are already up to date.
- [ ] pass  [ ] fail: ______

## Block M -- Spotify (optional, skip freely)

**R-76. Rows and the two refusals**
- Do: with Spotify enabled and Premium, search for an artist; then try to
  **download** and to **record** a Spotify row.
- Pass: rows appear alongside stations; both attempts refuse with *"copy-
  protected and cannot be saved by any app, including this one."*
- [ ] pass  [ ] fail  [ ] skipped

---

## The two C-and-L chords, together

Fixed on 2026-08-21; confirm the fix held rather than assuming it.

**R-77. One chord, one command**
- Do: press **Ctrl+Alt+Shift+C**, close what opens, then press
  **Ctrl+Alt+Shift+L**.
- Pass: **Choose Columns** for the first, **Continue Listening** for the
  second. Both opening the same window means the old collision is back.
- [ ] pass  [ ] fail: ______

## Sign-off

- Build / version: ______________
- Date: ______________
- Screen reader and version: ______________
- Windows version: ______________
- Blocks run: ______________
- Result: [ ] ship  [ ] ship with the findings below  [ ] do not ship

**For every fail, report three things:** the test id (R-57, say), what was said
**word for word**, and what you expected to hear. A step that did nothing at
all is the most serious kind of failure here -- report it even when nothing
looks broken.
