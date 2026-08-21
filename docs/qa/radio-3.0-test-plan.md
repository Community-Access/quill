# Quill Radio 3.0 -- test plan

> **Signing off, not investigating?** Use
> [radio-signoff.md](radio-signoff.md) instead: the same coverage as numbered
> steps with tick boxes, about 90 minutes, or 20 for the short run. This
> document is the reference behind it -- read it when a step fails and you want
> to know why the test exists.

A run-through of everything 3.0 changed, with **real links that were checked
against the live services** while this was written. Nothing here is a guessed
address: every one came back through Quill Radio's own adapters, so if a link
fails, that is a finding rather than a typo.

Where a service could not supply a case, this says so and tells you how to find
one yourself, rather than offering a link that might not be what it claims. And
where finding one took real work -- described audio on YouTube is the story of
this plan -- the section says what was tried, what failed, and what finally
worked, so the next run does not have to rediscover it.

## How to use this

Work top to bottom or dip in by section -- each is self-contained. Every
scenario is a numbered walkthrough with a test id (**T-1.1**, **T-9.3**, ...)
so a run can be recorded as a list of ids marked PASS or FAIL. Each one tells
you exactly what to press, what should happen, and -- where it matters -- the
**exact words** you should hear, because for this audience the spoken result
*is* the result: a thing that happens silently has not happened. Quoted
announcements are the literal strings in the shipping code; if what you hear
differs, write down both versions -- the difference is the finding.

Three settings worth knowing before you start:

- **Downloads land** in `Downloads\Quill Radio` unless you change it in
  preferences. Books go in `Books\`, podcasts in `Podcasts\`, music in `Music\`.
- **Safe Mode** (`--safe-mode`) turns off every network source. Several scenarios
  below check that it refuses *out loud, per branch*, rather than showing empty
  folders.
- **Nothing here needs an account, a key or a sign-in** except the Spotify
  section, which is explicitly marked and entirely optional.

---

## 1. Live radio: the ordinary path

**Stations verified live** (for reference and for pasting directly):

| Station | Address |
| --- | --- |
| BBC World Service | `http://stream.live.vc.bbcmedia.co.uk/bbc_world_service` |
| BBC Radio 4 | `http://as-hls-ww-live.akamaized.net/pool_55057080/live/ww/bbc_radio_fourfm/...` |
| SomaFM Groove Salad (`.pls`) | `https://somafm.com/groovesalad.pls` |

### T-1.1 Search, play, stop, resume

1. Press **Ctrl+F** (Station > Search Stations...). Focus lands in the
   search box.
2. Type `BBC World Service` and press **Enter**.
   - **Expect:** result rows arrive; each row says which source it came
     from.
3. Press **Enter** on the BBC World Service row.
   - **Expect:** it plays within a few seconds; the announcement names the
     station. PASS only if you both hear audio and hear the name.
4. Open **Playback > Stop**, wait two seconds, then **Playback > Play**.
   - **Expect:** the **same** station resumes -- no re-search, no prompt.

### T-1.2 Sound Enhancements are live, not queued

1. With a station playing, press **Ctrl+E** (Playback > Sound
   Enhancements...).
2. Move any slider a large step.
   - **Expect:** the change is audible **immediately** -- no gap, no
     silence, no reconnect. A stream that stutters or restarts here is a
     FAIL: enhancements apply to the running audio.
3. Escape closes the dialog; playback is untouched.

### T-1.3 A dropped stream says so

Hard to stage on demand; if a drop happens during any test, this is the
contract to check:

- **Listen for:** the app saying it is **reconnecting, with an attempt
  number**, then either *"Reconnected"* or an honest failure.
- Three attempts come at roughly 2, 5 and 15 seconds.
- The one FAIL that matters most: the stream going **silent with no
  announcement at all**.

---

## 2. Browse Stations: loading, and the two kinds of empty

The behaviour under test: the tree never blocks, every fetch runs off the UI
thread, and a branch that failed can be retried by closing and reopening it.

### T-2.1 Loading rows, and the cache

1. Open **Browse Stations** (Station > Browse Stations..., or the Browse
   Stations... button on the main window).
2. Arrow to **Internet Archive** and press **Right arrow** to expand.
   - **Listen for:** a *"Loading..."* row first, then real rows and a
     count, e.g. *"24 items."*
3. Collapse the branch (Left arrow), then expand it again.
   - **Expect:** instant -- the branch is **not** re-fetched.
   - **Listen for:** the count again, and **no second** "Loading...".

### T-2.2 The two kinds of empty

1. Disable your network (airplane mode, or pull the cable), then expand a
   branch you have **not** opened yet.
   - **Expect:** the placeholder clears -- the branch must never sit on
     "Loading..." forever.
   - **Listen for**, one of the two honest messages:
     - the hedge, when the tree cannot tell: *"Nothing in X. It may be
       empty, or the source could not be reached."*
     - the decisive one, when it can: *"X could not be reached. Close and
       reopen it to try again."*
2. Restore the network. Collapse and re-expand the same branch.
   - **Expect:** it **retries** and real rows arrive -- a failed branch is
     never stuck.
3. Quit, restart with `--safe-mode`, open Browse Stations, expand
   **TuneIn**.
   - **Listen for:** the refusal **by name**: *"TuneIn is disabled in Safe
     Mode."*

### T-2.3 Choosing which branches exist at all

Open **Station > Choose Browse Sources... (Ctrl+Shift+Alt+O)**. The rule
under test: a branch that is off is **not in the tree and is never
contacted** -- not hidden-but-fetched.

1. Arrow down the list without toggling anything.
   - **Listen for:** every row speaks its own state **first**: *"On.
     LibriVox Audiobooks. Public-domain audiobooks, by chapter."* -- and
     the group is named on the first row of each run.
2. Turn **LibriVox** off (Space), press OK, open Browse Stations.
   - **Expect:** no LibriVox branch anywhere; every other branch untouched.
3. Reopen the dialog, turn **everything** off, OK, open Browse Stations.
   - **Expect:** exactly one row: *"All sources are hidden. Choose Browse
     Sources from the menu to show some."*
4. Reopen the dialog and press **Reset to Default**.
   - **Expect:** the summary line states the count; **Explore (Wikidata)
     stays off** by default; everything else comes back on.
5. Quit Quill Radio entirely and restart it, then reopen the dialog.
   - **Expect:** your choices survived the restart.
6. In Browse Stations, put the cursor on a **ccMixter** branch and use
   **Find in this folder** for any word.
   - **Expect:** each result row keeps its note -- the licence rides along
     into search results.
7. Backspace the Find field to empty.
   - **Listen for:** *"Search cleared. Back on ..."* with the folder name
     -- erasing the text is the same as clearing, the folder gets its
     normal children back, and your cursor returns to it. (New in this
     build; before it, erased text left stale results in the tree.)

---

## 3. Search Stations reaches the libraries

### T-3.1 Five searches, five sources

For each row below: press **Ctrl+F**, type the query, press **Enter**, and
wait for the late arrivals.

1. `Middlemarch` -- radio stations answer first, then **LibriVox** audiobook
   rows arrive.
2. `Sherlock` -- **Project Gutenberg** audiobook rows appear.
3. `Johnny Dollar` -- **Internet Archive** recordings appear.
4. `The Rest Is History` -- a **Podcasts** group appears.
5. `jazz` -- **Audius**, **ccMixter** and **Mixcloud** rows appear.

- **Listen for:** the libraries answer *after* the stations, and you are
  told **once** when they have all reported -- never five separate times.
- **Expect:** if you are already arrowing the results when a late group
  lands, **your place is kept** -- the cursor must not jump.

### T-3.2 The music three (the regression case)

These sources shipped declared "cannot be searched"; all three publish a
keyword search, and the rows must carry their own truths:

1. On the `jazz` results, arrow to a **ccMixter** row.
   - **Expect:** the licence is spoken **in the row** itself.
2. Arrow to a **Mixcloud** row -- *before* pressing anything.
   - **Expect:** the row already says *"opens on Mixcloud in your
     browser"*. Being told after Enter is too late; the row is the consent.

---

## 4. Podcasts, with and without transcripts

Every step below was written against the shipping code: menu labels, key
presses, and quoted announcements are the literal strings Quill Radio speaks.
If what you hear differs from what is quoted, that difference **is the
finding** -- write down both versions.

### The test material

Three feeds that **do** publish Podcasting 2.0 tags (verified live):

| Show | Feed | Carries |
| --- | --- | --- |
| Podcasting 2.0 | `https://feeds.podcastindex.org/pc20.xml` | transcript (SRT), chapters, people, funding |
| Buzzcast | `https://feeds.buzzsprout.com/1538779.rss` | transcript (HTML), chapters, people, funding |
| No Agenda | `https://feed.nashownotes.com/rss.xml` | transcript (SRT), chapters, funding |

Three that **do not** -- the "without" cases, equally important, because the
honest absence message is as much a feature as the transcript:

| Show | Feed |
| --- | --- |
| The Rest Is History | `https://feeds.megaphone.fm/GLT4787413333` |
| 99% Invisible | `https://feeds.simplecast.com/BqbsxVfO` |
| Radiolab | `https://feeds.simplecast.com/EmVW7VGp` |

The feed addresses are for reference (paste one into a browser to see exactly
what the publisher declares); inside Quill Radio you reach these shows by
name, as walked below.

### T-4.1 Reaching a show and playing an episode

1. Start Quill Radio normally (not Safe Mode).
2. Press **Ctrl+F** (Station > Search Stations... -- the menu's own label;
   older revisions of this plan call it "Find Stations"), type
   `Podcasting 2.0`, press **Enter**.
3. Wait for the results. Radio stations answer first; a **Podcasts** group
   arrives after them, announced once when the libraries have all reported.
4. Arrow to the *Podcasting 2.0* show row and press **Enter** or expand it.
   - **Expect:** an episodes list, newest first. Each row reads as the
     episode title.
5. Press **Enter** on an episode.
   - **Expect:** it plays. PASS if audio starts and the row/now-playing
     announcement names the episode. FAIL if silence with no announcement.

Repeat once with `The Rest Is History` (a no-tags feed) -- playing must be
identical; the difference only appears in the transcript steps below.

### T-4.2 The Apple browse path and the leaf-genre check

1. Open **Browse Stations** from the Station menu.
2. Expand **Podcasts (Apple)**, then a country (United States is fine).
3. Expand the **Arts** genre in that country's top chart.
   - **Expect:** rows for its sub-areas -- Books, Design, Food -- appear.
   - **FAIL (this was a shipped bug):** the branch reads as empty. Arts is a
     "leaf genre" upstream, and the old code showed nothing for it.
4. Expand any show and press **Enter** on an episode: plays, as in T-4.1.

### T-4.3 Where episode extras actually live (a correction)

An earlier revision of this plan told you to open **About This Episode...**
here. That window belongs to **QUILL Cast** (its Episode menu); Quill Radio
deliberately stays the lightweight listener and does not carry it. What Radio
offers on a podcast episode row is **View Transcript...** (next section) and
the ordinary station actions. If you need People/Funding/Chapters tabs
verified, run that check in Cast against the same three feeds.

### T-4.4 Subscriptions shows Cast's folders, with unheard badges

Setup: in **QUILL Cast**, create a folder (Manager > New Folder), move one
subscribed show into it, and leave at least one of its episodes unplayed.

1. In Radio, open **Browse Stations**, expand **Podcasts**, then
   **Subscriptions**.
   - **Expect:** the folder appears **first**, before the loose shows, and
     its label carries the subtree count: *"News (2 unheard)"*.
2. Expand the folder.
   - **Expect:** its shows (and any subfolders) inside, each show badged
     with its own count -- or unbadged when everything is played.
3. Play one of those episodes to the end, then Refresh the branch.
   - **Expect:** the counts went down by one, in Radio **and** in Cast's
     manager tree -- one shared library, one truth.

### T-4.5 The unheard badge appears without ever opening Cast

1. Subscribe to a show **from Radio** (browse an Apple storefront, context
   menu, Subscribe to This Podcast) -- pick one you have never opened in
   Cast.
2. Open the show under Subscriptions once (this is the sync: browsing its
   episodes folds them into the shared library).
3. Collapse Subscriptions and expand it again.
   - **Expect:** the show now carries its *"(N unheard)"* badge. Before
     this build, a Radio-followed show stayed unbadged forever until Cast
     refreshed its feed -- that was the bug.

### T-4.6 Folders are made, renamed, filled, and deleted from Radio

All on the Browse tree's context menu (Applications key / Shift+F10):

1. On **Subscriptions**: choose **New Folder...**, type `Tech`, OK.
   - **Listen for:** *"Created folder Tech. It is shared with Quill
     Cast."* -- and the branch refreshes to show it.
2. On a **show row**: choose **Move to Folder...**.
   - **Expect:** the same folder picker Cast's manager opens (search box,
     tree, inline New Folder). Arrow to `Tech` **and press Enter** -- Enter
     in the folder tree confirms the move, exactly like the Move Here
     button. (Enter doing nothing here was a reported bug; it is a FAIL.)
   - **Listen for:** *"Moved <show> to Tech."* -- with **no** "Refresh
     Podcasts" instruction, because the tree does it: the branch reloads
     itself and **the cursor lands on the show inside its new folder**,
     already visible. Having to refresh by hand, or finding the cursor
     dumped somewhere else, is a FAIL.
3. On the **Tech folder row**: **Rename Folder...** to `Technology`.
   - **Listen for:** *"Renamed Tech to Technology."* -- and the tree shows
     the new name at once, cursor on the renamed folder.
4. On the folder row: **Delete Folder...**.
   - **Expect** a confirmation that says what deletion means: contents
     move up a level, **nothing is unsubscribed**.
   - **Listen for:** *"Deleted folder Technology. Its podcasts moved up a
     level; nothing was unsubscribed."* -- and the folder is gone from the
     tree without a refresh.
5. Open Cast's manager.
   - **Expect:** every one of those changes is simply there.

### T-4.7 Import Podcasts from OPML

Test file: any OPML export (`D:\downcast.opml`, a real 1,307-entry Downcast
export, was the acceptance file for this feature).

1. In Browse Stations, put the cursor on the **Podcasts** branch itself
   (the top-level row, not Subscriptions) and open its context menu.
   - **Expect** the item: **Import Podcasts from OPML...** -- on this row
     and only this row.
2. Choose it, pick the file.
   - **Listen for:** *"Importing podcasts..."* -- and the tree stays
     usable; a two-thousand-line file must not freeze it.
   - **Listen for**, when it finishes: *"Imported N podcasts, M already
     followed... Find them under Podcasts, Subscriptions, and in Quill
     Cast. Refresh Podcasts to see them."*
3. Import the **same file again**.
   - **Expect:** *"Imported 0 podcasts"* with everything counted as
     already followed -- never duplicates. (http/https twins of one feed
     count as one feed.)
4. If the file contains folder outlines, expand Subscriptions.
   - **Expect:** the folders arrived as real folders with their shows
     filed inside.
5. Quit Radio entirely, reopen, expand Subscriptions.
   - **Expect:** everything is still there -- the import is written to the
     shared store, not a session.
6. In **Safe Mode**: the same menu item answers *"Importing is disabled in
   Safe Mode. Restart Quill Radio normally."*

### T-4.8 Mark All as Played, dimmed when it is done

1. On a subscribed show row **with** unheard episodes, open the context
   menu.
   - **Expect:** **Mark All as Played...** is enabled. Choose it.
   - **Expect** a confirmation naming the show and the count, with a
     **"Don't ask me again" checkbox** (leave it unchecked for now) and
     **Mark Played** as the default button. Accept it.
   - **Listen for:** *"Marked N episodes of <show> as played."* -- and the
     branch reloads by itself: **the show's unheard badge is gone on
     screen immediately**, its folder's badge shrank to match, and the
     cursor is back on the show. A "Refresh Podcasts" chore here is a
     FAIL.
2. Reopen the same row's menu.
   - **Expect:** the item is still **there** but **dimmed** -- the verb
     belongs to the row; its state is "done". A vanished item is a FAIL.
3. Mark another show, and this time **check "Don't ask me again"** before
   accepting.
   - **Expect:** from now on Mark All as Played runs with no question --
     in Radio **and in QUILL Cast**: one answer, both apps, because it is
     the same verb over the same library. (Cancelling with the box checked
     must change nothing -- the question returns next time.)
4. In **QUILL Cast**: the Episode menu's Mark All as Played and the
   manager tree's context item dim the same way when the show has nothing
   unheard, and honor the same don't-ask answer.
5. Back in Radio, check the show's badge: gone, in both apps.

### T-4.9 A Cast position continues in Radio (and the furthest point wins)

Setup: in **QUILL Cast**, play a subscribed episode for at least two
minutes, then stop. Note the position (Cast's player shows it).

1. In Radio, open the same show under **Subscriptions** and press **Enter**
   on the same episode.
   - **Listen for:** the resume announcement with **Cast's** position:
     *"Resuming at 2 minutes 10 seconds."* -- the same wording recordings
     already use; only the number is new. (Its verbosity follows the same
     Preferences setting: spoken, brief, or silent.)
2. Listen a few minutes further in Radio, stop, and go back to Cast.
   - **Expect:** Cast learns Radio's position at its next launch (the
     handoff), and the **furthest** point wins -- neither app ever drags
     you backwards.
3. Play an ordinary LibriVox chapter.
   - **Expect:** exactly the old behaviour -- its resume comes from Radio's
     own store; the podcast library is never consulted for it.

### T-4.10 A private feed works in Radio too

Needs a podcast with feed credentials saved in Cast (Add Podcast >
authenticated feed). If you have none, note this as Not Run rather than
skipping silently.

1. In Radio, open that show under Subscriptions.
   - **Expect:** its episodes list, exactly like a public feed. Before this
     build the fetch went out with no credentials, so a private feed that
     worked in Cast read as broken here -- an empty or failed branch on
     this step is the old bug come back.
2. The same-host rule applies: credentials are only ever sent to the
   feed's own host, never to a redirect elsewhere.

### T-4.11 The show's speed follows the show -- and Radio remembers yours

Setup: in Cast, set a show's speed to 1.5x (Settings for This Podcast).

1. In Radio, play one of that show's episodes from Subscriptions.
   - **Expect:** it plays at **1.5x** -- audibly faster. The setting
     followed the show; Radio grew no settings UI for it.
2. Press **Ctrl+Alt+Up** (Play Faster).
   - **Listen for:** *"1.75 times speed. Remembered for this show."* --
     the session control always wins over the saved speed, and from this
     press on, the speed you chose is **Radio's own memory for this
     show**, kept separately from Cast's setting.
3. Play a different, ordinary station, then return to the show's episode.
   - **Expect:** **1.75x** -- the speed *you* chose in Radio, not Cast's
     1.5x. Your choice in Radio outranks the Cast setting for this show,
     and Cast's own setting is untouched (check it: still 1.5x there).
4. While a session speed is active (say you pressed Play Faster on the
   previous item), play the show's episode.
   - **Expect:** your **session speed is kept** -- a saved speed only
     applies when you have not chosen one this session.
5. Press **Ctrl+Alt+0** (Normal Speed) while the episode plays.
   - **Listen for:** *"Normal speed. This show will play at normal
     speed."* -- normal is the default, so the memory is forgotten rather
     than storing 1.0. The show now falls back to Cast's setting (1.5x)
     on its next fresh play.
6. Adjust speed while an ordinary station or video plays.
   - **Listen for:** exactly the old announcement, with **no** "Remembered"
     suffix -- only podcast episodes carry a show to remember for.

**The engine rule (why a saved speed sometimes waits):** a *downloaded*
episode always auto-applies its saved speed -- a local file has no network
to fall behind. A *streamed* episode auto-applies it only on the mpv
engine; on the Windows Media Player fallback engine (used when mpv is not
available), rates on network streams are unreliable, so the saved speed
**stays saved** and the episode starts at normal speed -- Play Faster is
still one keypress away, and your memory is intact for the next mpv or
downloaded play. A speed starting silently wrong-and-stuttering would be
worse than starting normal; this rule is that judgment written down.

### T-4.12 Podcasting 2.0 chapters on the player

Use a chaptered feed from the section-4 table (Podcasting 2.0 and No
Agenda both publish chapters).

1. Play an episode from Subscriptions and give it a few seconds (the
   chapters file is fetched in the background; playback never waits on
   it).
2. Use Radio's chapter commands -- the same ones that work on chaptered
   videos and audiobooks (next/previous chapter, and the chapter readout).
   - **Expect:** the publisher's own chapter titles, announced exactly as
     video chapters are. Same commands, no new UI -- that is the feature.
3. Play an episode from a feed with no chapters.
   - **Expect:** the chapter commands answer exactly as they do on an
     unchaptered video -- the honest "no chapters" path, never an invented
     marker.

### T-4.13 Downloading episodes: one, all, and taking them back

1. On any **podcast episode row** (Search Stations or the Browse tree),
   open the context menu.
   - **Expect:** **Download...** is on the menu. (Its absence on browse
     and subscription episodes was a reported bug -- the menu offered it
     only on search results. A missing Download here is that bug back.)
2. Choose it, then when the queue reports the save, find the file.
   - **Expect** it filed as `Downloads\Quill Radio\Podcasts\<Show>\<Episode>`
     -- under its **show's own folder**, exactly where Download All puts
     things. A bare file under `Recordings\` is the old filing bug.
3. On a **subscribed show row**: open the context menu.
   - **Expect:** **Download All N Episodes...** with the library's own
     count -- offered even if you have never expanded the show, because
     the library already knows the list. Dimmed only when the library has
     no episodes yet.
4. Choose it.
   - **Listen for:** the queue summary ("Queued ... You can carry on
     listening.") -- downloads run one at a time in the background, and
     everything lands under the show's folder.
5. Same row: **Remove All Downloads...**.
   - **Expect:** present always, **dimmed** when nothing is downloaded.
     With files present it confirms with the real file count and says the
     part that matters: *"Your subscription and played state are
     untouched."*
   - **Listen for**, after accepting: *"Removed N downloaded files."* --
     and the files are gone from the show's folder, while the show, its
     episodes, and every badge stay exactly as they were.
6. In **QUILL Cast**, right-click the same show in the library tree.
   - **Expect:** **Download All Episodes** (already there) now has its
     counterpart **Remove All Downloads...** beside it, honoring Keep
     This Episode: protected episodes are skipped and the announcement
     says how many were kept.

### T-4.14 Marking one episode, and badges that believe your ears

1. On a **subscribed** show's episode row, open the context menu.
   - **Expect:** **Mark Episode as Played** on an unplayed episode, or
     **Mark Episode as Unplayed** on a played one -- one direction at a
     time, never both.
2. Choose Mark Episode as Played.
   - **Listen for:** *"Marked <episode> as played."* -- the branch reloads
     and the show's unheard badge is one lower, immediately.
3. Now play a different episode of the show **to the end** (or use the
   seek commands to reach the last seconds and let it finish).
   - **Expect:** back in the tree, the show's badge is **already one
     lower** -- without opening Quill Cast, without refreshing by hand.
     Radio counts its own finished listening the moment it happens; the
     shared library still learns it at Cast's next launch, exactly as
     before. (A badge that keeps counting an episode you just finished
     was the reported bug.)
4. Episode rows of a show you are **not** subscribed to carry no mark
   item at all -- there is no library state to edit.

### T-4.15 Search: everything at once, or one source intelligently

1. Open Browse Stations (Ctrl+B).
   - **Expect:** the **first row of the tree** is **Search All
     Sources...** -- above Favorites, always present (hiding sources
     never hides it).
2. Press **Enter** on it.
   - **Expect:** the Search Stations window opens with focus in the
     search box and the Source filter on **All sources** -- one query,
     every provider's own search engine (Radio Browser, iHeart, TuneIn,
     Podcasts, YouTube, Spotify...), results interleaved with their
     source named on each row. This is the same window as Station >
     Search Stations; the tree row is simply the door from inside.
3. Now open the context menu on a **top-level source** that has a search
   engine -- **Podcasts (Apple)**, **iHeart**, **TuneIn**, **YouTube**.
   - **Expect:** **Search This Source...** on the menu.
4. Choose it on **Podcasts (Apple)** and search something.
   - **Expect:** the same search window, but the Source filter is already
     on **Podcasts** -- standing on podcasts searches podcasts. The facet
     is preset for this opening only; your own remembered filter comes
     back next time you open search normally.
5. Sources with no search engine of their own (Weather / NOAA, NFB
   Radio...) have no Search This Source item -- a search that could not
   actually be scoped would be a lying menu row.

### T-4.16 The row's own verbs: record it, schedule it, rename it

1. On any **live station row** in the browse tree, open the context menu.
   - **Expect:** **Record This Station...** and **Schedule Recording...**
     -- the same two commands the Record menu carries, pre-filled with
     *this row's* station instead of whatever is playing.
2. Choose Record This Station...
   - **Expect:** the Record Station dialog opens with the row's station
     already chosen; a machine without ffmpeg gets the usual honest
     refusal instead.
3. On a station you have **added to Favorites**, reopen the menu.
   - **Expect:** **Rename Favorite...** -- the same custom-name prompt the
     Favorites manager offers, in place. Blank restores the directory's
     own name.
4. Episode and chapter rows (recordings) offer **no** Record items --
   a recording is downloaded, not recorded; both verbs stay honest.

### T-4.17 Add a Podcast by URL, and the empty branch that helps

1. Open the context menu on the **Podcasts branch itself**, and then on
   **Subscriptions**.
   - **Expect:** **Add a Podcast by URL...** on both -- and on **neither**
     a show row nor an episode row (those already are subscriptions).
2. Choose it and paste a real feed address (any show's RSS link).
   - **Listen for:** *"Checking that feed..."* then *"Subscribed to
     <show>. N episodes are listed, and the show is shared with Quill
     Cast."* -- and, from the Subscriptions row, the tree reloads with
     the cursor on the new show, episodes already listed (no
     empty-until-refresh).
3. Now feed it mistakes, one at a time, and listen for the *specific*
   sentence -- a bare "invalid" anywhere here is a FAIL:
   - Nothing: *"Paste or type the feed's web address first."*
   - `the daily`: *"That does not look like a web address..."* pointing
     at the RSS/Subscribe link on the show's site.
   - A show's normal **web page** address: *"...answers with a web page,
     not a podcast feed"* with the same pointer.
   - A blog/news feed with no audio: named, and *"...lists no playable
     episodes -- it may be a news feed rather than a podcast."*
   - A made-up address: *"...could not be read as a feed"* plus check
     typos / check you are online.
   - A feed that needs a password: pointed at Quill Cast's Add Podcast
     dialog, which saves credentials for both apps.
   - An `http://` address is quietly tried as `https://` first rather
     than being bounced.
4. **The empty branch helps.** On a profile with no subscriptions at all,
   expand **Subscriptions**.
   - **Expect** exactly three rows, each of which *acts* on Enter:
     **Add a Podcast by URL...**, **Import Podcasts from OPML...**, and
     **Search for a Podcast...** (which opens search pre-narrowed to
     Podcasts). Subscribe to anything and they are gone -- they are the
     empty state, not furniture.
5. **In QUILL Cast**: the library tree offers **Add Podcast...** on
   folder rows and the tree's background (never on shows or episodes),
   and an empty library shows the same three filler rows -- Enter on
   Add/Search opens the Add Podcast dialog, Enter on Import opens the
   OPML chooser.
6. In **Safe Mode**, adding by URL refuses out loud: the network is off.

---

## 5. Transcripts

Radio reads two kinds of transcript through **one shared reader window** (the
same one Cast uses, on purpose, so they can never drift apart):

- a **podcast episode's** transcript, declared in its feed -- readable
  **without playing the episode**, from the episode row's context menu:
  **View Transcript...**;
- the **playing item's** transcript (a YouTube video's captions, or the
  playing episode) -- from **Playback > Transcript... (Ctrl+Shift+T)**.

### T-5.1 Opening a feed transcript without playing anything

1. Reach a *Podcasting 2.0* episode row as in T-4.1 (Search Stations or the
   Browse tree -- both carry the same context menu).
2. Press the **Applications key** (or Shift+F10) on the episode row.
3. Arrow to **View Transcript...** and press Enter.
   - **Listen for**, immediately: *"Fetching transcript..."*
   - **Expect:** the reader window opens with focus in a read-only text box,
     one caption line per row. Nothing is playing -- fetching a transcript
     must not start playback.
4. Read around with arrow keys, word movement, and your screen reader's
   review cursor.
   - **Expect:** a completely ordinary text box. Any dead navigation key is
     a FAIL.

### T-5.2 The reader's controls, one by one

Open a transcript via T-5.1 (or Ctrl+Shift+T while an episode plays), then:

1. Arrow around the transcript while the episode keeps playing.
   - **Expect:** your caret never moves on its own. Reading always wins.
     (There was a "Follow the audio as it plays" checkbox here until
     2026-08; it was removed, because a caret that moves while you are
     reading is a caret you are fighting. If you can still find it, FAIL.)
2. Put the caret on any line and press **Enter**.
   - **Listen for:** *"Playing from 4 minutes 12 seconds."* -- the position
     of *that* line, **always words, never** `4:12`.
   - **Expect:** the audio audibly jumps there.
3. Use the reader's **Find** for a word you saw later in the text.
   - **Listen for:** *"Found at 12 minutes 8 seconds. Enter plays from
     here."* (again: words, never `12:08`), and the caret lands **on the
     match** so Enter acts on the line you just found.
   - **Expect:** with nothing playing, the same sentence **without** the
     "Enter plays from here" half -- the reader must not offer a jump it
     cannot make.
4. Press the **Links...** button (or Ctrl+Shift+L).
   - **Expect:** a list of every web address in the transcript, each read as
     its name then its address. Enter (or **Open in Browser**) opens the
     highlighted one in your real browser; **Copy Address** puts one on the
     clipboard, **Copy All** puts all of them there one per line.
   - On a transcript with no addresses in it: *"There are no web addresses
     in this transcript."* -- spoken, never an empty window.
5. Press the **Save As...** button. The format list offers, in this order:
   **Plain text (.txt), WebVTT (.vtt), SubRip (.srt)**.
   - Save as **WebVTT**, then open the saved file (Quill, or any editor).
   - **Expect:** cue timings match what the reader spoke -- the round trip
     loses nothing.

### T-5.3 The honest absences

Each of these must be a spoken sentence, never a silent nothing and never an
empty window:

1. **A feed with no transcript.** On a *Radiolab* or *99% Invisible* episode
   row, the context menu simply **has no View Transcript... item** -- the
   feed declares none, so the menu does not offer one. If the item appears
   and opens an empty reader, FAIL.
2. **A fetch that comes back empty.** If a feed declares a transcript that
   cannot be read, the announcement is: *"No transcript could be read for
   this one. The publisher may not have provided captions or a transcript
   file."*
3. **A live stream**, with Ctrl+Shift+T while a live station plays:
   *"This is a live stream, so there is no transcript to read."*
4. **A video with no captions**, Ctrl+Shift+T: *"This video has no captions
   published, so there is no transcript."*
5. **Safe Mode** (start with `--safe-mode`), View Transcript... on any row:
   *"Transcripts are disabled in Safe Mode. Restart Quill Radio normally to
   read them."* No request leaves the machine.
6. **An unparsable transcript**: *"That transcript could not be read. It may
   be in a form Quill cannot parse."*

### T-5.4 Automatic captions are labelled automatic

1. Play a YouTube video that has only automatic captions (most ordinary
   uploads; the verified table in section 6 lists *human*-captioned ones, so
   pick any casual video outside it).
2. Press **Ctrl+Shift+T**.
   - **Expect:** the reader opens, and its **heading says the transcript is
     automatically generated**. A machine transcript presented as a human
     one is a confident wrong answer -- the label is the feature.

---

## 6. Video, captions, and described audio

**Verified videos** (all have human captions, not automatic):

| Video | URL | Chapters | Audio tracks |
| --- | --- | --- | --- |
| TED talk | `https://www.youtube.com/watch?v=iG9CE55wbtY` | 10 | 1 (English) |
| Big Buck Bunny | `https://www.youtube.com/watch?v=YE7VzlLtp-4` | 0 | 1 (English) |
| MrBeast | `https://www.youtube.com/watch?v=0e3GPea1Tyg` | 7 | 24 (dubbed: English (US), Hindi, Tamil, Japanese...) |

A single-track video still returns four to six audio *formats* -- one per codec
and per bitrate -- and the difference between those two numbers is the first
bug described below. The MrBeast video is the multi-language check: every one
of its twenty-four rows must read as a language name ("Tamil", "Bangla"), never
a code ("ta"), a mangled fragment ("ta (mil)"), or a duplicate.

All of these commands live in the **Playback** menu; the keys quoted are the
menu's own accelerators.

### T-6.1 Showing the picture without losing the sound

1. Play the TED talk from the table (paste its URL into Search Stations
   (Ctrl+F), or Station > Add from YouTube). Let the audio establish for a
   few seconds.
2. Press **Ctrl+Shift+V** (Playback > Show Video).
   - **Listen for:** *"Video shown, 1280 by 720."* (the numbers are the
     video's real size).
   - **Expect:** the picture appears and the audio **does not restart or
     hiccup**. Any gap or position jump is a FAIL.
   - The video window's own status line offers: *"Press Ctrl+Shift+T for
     the transcript."*
3. Press **Ctrl+Shift+V** again.
   - **Listen for:** *"Video hidden. Audio is still playing."*
   - **Expect:** exactly that -- audio continues.
4. With the video shown, press **F11**.
   - **Expect:** full screen, and the entry announcement states **both**
     ways out -- do not accept an entry that only mentions one.

### T-6.2 Captions

1. With the TED talk playing and video shown, press **Ctrl+Shift+K**
   (Playback > Captions).
   - **Expect:** captions appear; the announcement says plainly when a
     track is automatic (the TED talk's are human, so no such warning
     here).
2. Open **Playback > Caption Settings... (Ctrl+Shift+Alt+T)** and set the
   size to 300%.
   - **Expect:** the caption text visibly scales, and its background stays
     **opaque** by default -- readable over any scene.
3. Press **Ctrl+Shift+K** again: captions go, said out loud.

### T-6.3 The track picker speaks the truth (Ctrl+Shift+A)

1. Still on the TED talk, press **Ctrl+Shift+A** (Playback > Audio and
   Described Audio...).
   - **Expect:** the window **opens** -- it is never greyed out. Its list is
     named *"Audio tracks for this video; a described track narrates what
     is on screen"*, and above the list stands the heading: *"No described
     audio was published for this video."*
   - **Expect exactly one row**, "English". Four-to-six would mean the
     codec/bitrate *formats* are leaking through as tracks again (the first
     fixed bug below); zero or a duplicate row is the collapse bug.
2. Escape out. Play the **MrBeast** video and press **Ctrl+Shift+A**.
   - **Expect:** **twenty-four rows**, every one a language *name* --
     "Tamil", "Bangla", "Japanese" -- never a code ("ta"), a fragment, or a
     duplicate -- under the same honest heading: none of them is described.

### Described audio -- read this part

#### What a search of YouTube actually turns up

Around a hundred and forty videos were probed for this plan through Quill
Radio's own resolver: every result for *audio description*, *audio described*,
*described video*, *descriptive video service* and similar; the recent uploads of
**Apple**, **Apple Support**, **Microsoft**, **Microsoft Design** and Microsoft's
accessibility channel, **@MSFTEnable**; and finally a named list of videos
reported to carry a genuine selectable descriptive track.

Two different things came back, and keeping them apart is the whole of this
section.

**Most described content on YouTube is a second *video*, not a second track.**
Apple and Microsoft both work this way: *"Be My Eyes + Microsoft Disability
Answer Desk (audio described version)"* is its own upload with the narration
mixed into its only audio track. There is nothing to select, because the
description *is* the audio. One track is the correct answer for these, and the
picker must not invent a second.

**A few videos really do publish a selectable descriptive track -- and Quill
Radio finds it.** YouTube supports alternate audio renditions on one video, and
the videos in the table below use it (the *ART LAB* series says so in its own
description; several *Tested* videos carry a descriptive track supplied by the
Described and Captioned Media Program; two Apple films tell viewers to pick it
from the settings gear).

Reaching those tracks took a fight worth recording. YouTube's web player
response *names* the renditions -- "English original", "English descriptive" --
but serves them without addresses (SABR streaming), so yt-dlp discards them
before any caller sees one; asked the ordinary way, every one of these videos
claims a single track, labelled *"English original (default)"*, the platform
quietly admitting it kept the rest. The resolver now also asks as YouTube's
**iOS player client**, which is handed the same renditions with direct, playable
URLs -- verified live, the descriptive stream plays. Both clients are queried
concurrently, so resolving costs no extra time.

#### The described uploads worth playing anyway

These are real described content from the teams who make it, and they should
sound right end to end. Each one has human captions as well.

| Described upload | URL |
| --- | --- |
| Apple -- *Designed for Shane R. (with Audio Descriptions)* | `https://www.youtube.com/watch?v=r0XRoogmJuk` |
| MSFTEnable -- *Be My Eyes + Microsoft Disability Answer Desk (audio described version)* | `https://www.youtube.com/watch?v=LYKUnym0EqU` |
| MSFTEnable -- *Accessibility drives... (audio described version)* | `https://www.youtube.com/watch?v=l3qRka9mECI` |
| MSFTEnable -- *Introduction to Disability and Accessibility (audio described version)* | `https://www.youtube.com/watch?v=Kl4CT4DaypM` |
| MSFTEnable -- *Integrated Audio Description: At a Glance* | `https://www.youtube.com/watch?v=SgfICec18Gw` |
| Microsoft APAC -- *A Commitment to Accessibility, full length (Audio Description)* | `https://www.youtube.com/watch?v=pqiS7evCXsY` |

#### The A/B pairs -- the same film, described and not

This is the most useful comparison in the section, because it is the shape the
platform actually offers. Play the plain one, then the described one, and listen
for the narration appearing in the gaps. Quill Radio should report **one track**
for both, and should never claim description on the plain one.

| Plain | Described |
| --- | --- |
| *Be My Eyes + Microsoft Disability Answer Desk* -- `https://www.youtube.com/watch?v=VM9yLxnzQAM` | `https://www.youtube.com/watch?v=LYKUnym0EqU` |
| *Accessibility drives...* -- `https://www.youtube.com/watch?v=koAhcSTn-uU` | `https://www.youtube.com/watch?v=l3qRka9mECI` |
| *Introduction to Disability and Accessibility* -- `https://www.youtube.com/watch?v=GGB_xreE3OU` | `https://www.youtube.com/watch?v=Kl4CT4DaypM` |

#### T-6.4 Testing the absence path, which is the common case

1. Play the TED talk or Big Buck Bunny, press **Ctrl+Shift+A**.
   - **Expect:** the window opens (never greyed out), heading *"No
     described audio was published for this video."*, one row: English.
2. Press **Ctrl+Alt+D** (Playback > Play Described Audio) on the same
   video.
   - **Expect:** the same honest answer spoken -- **never silence**.
3. Press **Ctrl+Alt+D** while a **live station** plays.
   - **Listen for:** *"This is a live stream, so it has no described audio
     track to choose."*
4. Press **Ctrl+Shift+A** on any **described upload** from the table above.
   - **Expect:** the *absence* heading, and it is **correct**: for these
     uploads the description is mixed into the only track. The picker must
     not invent a second row.
5. Play a described upload end to end.
   - **Expect:** plays normally; the description simply *is* the audio.

#### The presence path: videos with a real descriptive track, all verified

Every video below resolves through Quill Radio to **two named tracks** -- the
original and *"English (described)"* -- and the described stream was fetched and
played during verification. These are the links to walk for the whole presence
experience: the announcement on start, the picker with the described track
first, Ctrl+Alt+D, and the position surviving the switch.

| Video | URL |
| --- | --- |
| Emily Graslie -- *ART LAB* introduction (says so in its own description) | `https://www.youtube.com/watch?v=UusppshIAio` |
| Tested -- *Adam Savage's Ingenious Fractal Vise* (DCMP track) | `https://www.youtube.com/watch?v=mZBwhJxrcW4` |
| Tested -- *Adam Savage Loves This Old Box* | `https://www.youtube.com/watch?v=1JgYMJDfPvc` |
| Tested -- *Setting Up the New Milling Machine* | `https://www.youtube.com/watch?v=OHfSZlfPTNc` |
| Tested -- *Workbench Cubby Door* | `https://www.youtube.com/watch?v=WhQU-nc4xkg` |
| Tested -- *Smartphone Camera Rig* | `https://www.youtube.com/watch?v=2igc_BelOXk` |
| Apple -- *I'm Not Remarkable* | `https://www.youtube.com/watch?v=KmFPWxjmnqE` |
| Apple -- *Designing the Hikawa Grip & Stand* | `https://www.youtube.com/watch?v=TTb_cjCo7Nc` |

There is an automated version of exactly this check, which walks every link in
this section and fails if the reading is dishonest:

```
QUILL_YT_LIVE=1 pytest tests/integration/test_youtube_audio_tracks_live.py -v
```

#### Three bugs this probing found, all fixed

**Rows multiplied.** Every ordinary video listed two or three audio tracks --
"English", "English" -- because a track was identified by its *quality tier*
(`low`, `medium`, `high`). yt-dlp returns one audio format per codec **and** per
bitrate: a TED talk returns four, all of them one track. The picker showed
duplicate rows nobody could choose between, which is precisely the "Track 1 /
Track 2" puzzle the feature exists to remove, sitting inside the feature.

**Then rows collapsed -- the worse one.** The first fix keyed a track on the
identifier yt-dlp supplies for multi-track videos, falling back to the language
code. yt-dlp does not supply that identifier for YouTube at all: it writes the
track's own name into the same field as the quality tier. So the fallback did all
the work, and because YouTube gives a video's original and descriptive renditions
the *same* language code, two tracks would have been read as one -- **silently
discarding the described track, in the feature whose only job is to find it.**

**Then a phantom row returned.** The iOS client's formats arrive stamped
"MISSING POT" (served without a proof-of-origin token), and with that left in
the name, the one original track read as two -- "English", "English (MISSING
POT)" -- on every ordinary video. It is a delivery detail, not a track, and is
now stripped. All three are covered by tests over the real shapes YouTube
returns.

**Worth re-checking on several videos** that the count is right in both
directions: never a duplicate row, never a missing one.

#### T-6.5 Walking the presence path, step by step

Use the *ART LAB* introduction (`https://www.youtube.com/watch?v=UusppshIAio`)
for the first full pass, then spot-check two or three others from the
presence table.

1. Play the video and just listen for a moment.
   - **Listen for, exactly once:** *"Described audio is available for this
     video. Press Ctrl+Alt+D to hear the narration of what is on screen."*
   - FAIL if it repeats, and FAIL if it never comes.
2. Press **Ctrl+Shift+A**.
   - **Expect:** the heading above the list is *"Described audio is
     available for this video."*, the **described track is listed first**,
     and the **cursor is already on it** -- the user who came for
     description does not hunt for it.
   - **Expect:** the ordinary track is still listed and still labelled, so
     nobody who did not ask for description gets surprised by it.
3. Choose the described track (Enter), or Escape and press **Ctrl+Alt+D**.
   - **Listen for:** *"Playing the described audio track."*
   - **Expect:** the narration is audibly there -- on *ART LAB* it begins
     over the opening titles. If the audio is indistinguishable from the
     ordinary track, the wrong stream is playing: FAIL.
4. Before switching, note your position (Ctrl+Shift+I reads it). Switch
   tracks and check the position again.
   - **Expect:** the position **survives the switch**. Losing an hour of a
     film to turn description on would defeat the feature exactly where it
     matters most.
5. If the stream cannot be fetched, the honest failure is: *"The described
   audio track could not be played."* -- never silence.

## 7. YouTube channels and playlists

### T-7.1 Following a channel

1. Open **Browse Stations**, expand **YouTube Channels**, choose its Add
   action.
2. Paste `https://www.youtube.com/@TED` and confirm.
   - **Expect:** the channel's recent videos appear as rows under the
     branch, each playable with Enter.

### T-7.2 A playlist becomes stations

1. Open **Station > Add from YouTube Playlist...**
2. Paste
   `https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Blw3RGYpWkSByi_T7Rygb`
   and confirm.
   - **Expect:** **19 entries** added as stations (that is the verified
     count for this playlist). More or fewer is a finding.

### T-7.3 What Am I Hearing (stream facts)

1. Play any of the added videos, then press **Ctrl+Shift+I**.
   - **Expect:** size, frame rate, codec -- and whether captions and
     described audio exist. This is also the quickest way to note your
     position before a track switch (T-6.5).

---

## 8. Playlists the internet actually uses

### T-8.1 Import a .pls

1. Download `https://somafm.com/groovesalad.pls` (a browser will save it as
   a small text file).
2. Open **Station > Import Stations from Playlist... (Ctrl+I)** and pick
   the file.
   - **Expect:** **3 entries** (verified), each playable with Enter.

### T-8.2 The M3U round trip

1. With a few favorites saved, open **Station > Export Favorites to
   Playlist... (Ctrl+Shift+X)** and save an `.m3u`.
2. Import that same file back with **Ctrl+I**.
   - **Expect:** the same stations, in the same order. Anything lost or
     reordered is a FAIL.

### T-8.3 Live365 pages become streams

1. Paste any `live365.com/station/...` **page** address where a stream URL
   is accepted (Search Stations, or Add Station).
   - **Expect:** the page address is rewritten to the real stream, **and
     the app says it did so** -- the correction is announced, not silent.

---

## 9. Downloads -- the new one, test it hardest

### T-9.0 Download Preferences

Open **Station > Download Preferences... (Ctrl+Alt+Shift+D)** -- also
reachable via the **Preferences...** button inside View > Downloads.

1. Open it and just listen, touching nothing.
   - **Expect:** focus lands in the **folder field**, and its accessible
     name explains what blank means and where the default is.
2. Toggle any checkbox.
   - **Expect:** the summary sentence at the bottom updates -- it always
     answers "what will happen to the next thing I save?"
3. Turn on **"Ask where to save each download instead of filing it
   automatically"**, press OK, then queue a whole book (T-9.2).
   - **Expect:** **one** folder prompt for the whole book -- never one per
     chapter.
4. Cancel that folder prompt.
   - **Listen for:** *"Download cancelled. Nothing was queued."* --
     declining the ask never files things anyway.
5. Change the downloads folder, OK, download one file.
   - **Expect:** it lands under the new folder **immediately** -- no
     restart needed.
6. Reopen the dialog, change things, then press **Cancel**.
   - **Expect:** nothing changed; the old rules still apply.

**Books verified live:**

| Book | Chapters | First chapter |
| --- | --- | --- |
| Middlemarch (George Eliot) | **86** | `https://www.archive.org/download/middlemarch_0810_librivox/middlemarch_01_eliot_...` |
| Middlemarch, version 2 | 84 | `https://www.archive.org/download/middlemarch_version2_1310_librivox/...` |

**Music with a licence:** ccMixter `Xtended Chords -- Javolenus`, licence
*Attribution Noncommercial (4.0)* -- search `jazz` in Search Stations
(Ctrl+F).

### T-9.1 What may and may not be saved

For each row kind, open its context menu (Applications key or Shift+F10)
and look for **Download...**:

1. **A LibriVox chapter** (search `Middlemarch`, expand the book): Download
   is offered. Choose it.
   - **Expect:** queued, and the file lands under `Books\`.
2. **A live station** (the BBC row): the menu has **no Download item at
   all**. Ask through the command palette instead and the refusal explains:
   *"A live station... has no end... Use Record Station"*.
3. **A Mixcloud row**: no Download; the refusal names Mixcloud and the
   browser.
4. **A YouTube video**: no Download; the refusal says Quill Radio
   *"deliberately does not download from YouTube"*.
5. **An Audius track**: no Download; the refusal cites *"the artist's
   choice"* and says the app *"does not guess"*.
6. **A ccMixter track** (search `jazz`): Download is offered.
   - **Expect:** the audio file saved **plus a `.licence.txt` beside it** --
     the licence travels with the music.

### T-9.2 A whole book, and the queue

1. In Browse Stations, open Middlemarch's folder (LibriVox), put the cursor
   **on the folder**, and open its context menu.
   - **Expect** the item: **Download All 86 Files...**
2. Choose it.
   - **Expect:** at most **one** folder prompt (per T-9.0), never 86.
   - **Listen for:** *"Queued Middlemarch... You can carry on listening."*
3. Start a live station playing while the book downloads.
   - **Expect:** playback is completely unaffected.
4. Open **View > Downloads... (Ctrl+Shift+J)** and arrow the rows.
   - **Listen for:** rows that read as sentences with the state **last**:
     *"Chapter 4, Middlemarch, downloading now"*.
5. Let several chapters finish.
   - **Expect:** finished rows **stay** in the list.
   - **Listen for:** a heartbeat every few chapters: *"12 of 86."*
6. Select a **finished** row and choose **Open Containing Folder**.
   - **Expect:** Explorer opens **with that file selected** -- not just the
     folder.
7. Select a **waiting** row and choose **Cancel This One**.
   - **Expect:** cancelled; anything already saved is kept.
8. Try **Remove From List** on the **running** row.
   - **Listen for** the refusal: *"That one is downloading now. Cancel it
     first."*
9. **Clear Finished**, then **Clear All**.
   - **Expect:** the list empties; **nothing on disk is touched**.
10. Press **Alt+F4** while downloads are still outstanding.
    - **Expect:** per your preference, downloads keep going **or** stop --
      and either way the app **says which**. The saying is the point.

### T-9.3 Where things land

Check the folder after each of these (default root: `Downloads\Quill
Radio`):

1. Download one book by George Eliot.
   - **Expect:** `Books\Middlemarch\` -- **no** author folder yet.
2. Download a second book by the same author.
   - **Expect:** the second goes under `Books\George Eliot\...` -- the
     author folder appears only when it disambiguates.
3. Download a podcast episode: lands in `Podcasts\<show name>\`.
4. Download a ccMixter track: lands in `Music\`.
5. Turn **off** "folder per book" in Download Preferences, download a
   chapter: it lands **directly** in `Books\`.

### T-9.4 Interruption

1. Start a whole-book download, then kill the network mid-chapter.
   - **Expect:** that chapter fails -- and the **next one still runs**.
2. Restore the network and download the same book again.
   - **Expect:** part-finished files **resume** rather than restart from
     zero.
3. Cancel a download mid-chapter.
   - **Expect:** it stops within seconds -- not at the end of a 90 MB file.

---

## 10. A downloaded book plays as a book

Use the Middlemarch download from T-9.2.

### T-10.1 Chapters chain, in the right order

1. Play chapter 1 of the downloaded book. It plays.
2. Let it run to its end, hands off.
   - **Expect:** **chapter 2 starts on its own.**
   - **Listen for:** *"2 of 86, ..."* -- the position comes **first**.
3. On a book with ten or more chapters, confirm chapter 2 plays before
   chapter 10 -- numeric order, not text order.
4. Play the **last** chapter to its end.
   - **Expect:** playback stops, and says so.
   - **Listen for:** *"That was the last chapter of Middlemarch."*

### T-10.2 The book is just the folder

1. Rename one chapter file by hand in Explorer, then reopen the book.
   - **Expect:** the book simply reflects the change -- no error, no ghost
     of the old name.
2. Let a **live station** play and (if it happens) drop.
   - **Expect:** it reconnects (T-1.3) -- a live stream is **never**
     treated as a book with a next chapter.

---

## 11. Continue Listening

### T-11.1 Three kinds of unfinished thing

1. Play a podcast episode for a couple of minutes, then **Stop**.
2. Play a LibriVox chapter (streaming, not downloaded) for a minute, then
   Stop.
3. Play a **downloaded** file for a minute, then Stop.
4. Open **Playback > Continue Listening... (Ctrl+Alt+Shift+L)**. The key moved
   off `Ctrl+Shift+Alt+C` on 2026-08-21: wx ignores modifier order, so that was
   the same chord as View > Choose Columns... and one of the pair never fired.
   - **Expect:** all three appear, **newest first**, and every row names
     its **kind** and **how far in** you were -- the streamed chapter
     labelled as a recording source, the downloaded one as a *file on this
     computer*.
   - **Listen for**, on opening: a summary like *"2 things you did not
     finish, across recordings, podcasts."*

### T-11.2 Resume, forget, and the missing file

1. **Resume** a row.
   - **Expect:** playback starts **where you left off** -- not from zero.
2. On another row choose **Forget This One**.
   - **Expect:** the row goes; the episode itself stays **unplayed** --
     forgetting is not marking-as-done.
3. Move a downloaded file somewhere else in Explorer, reopen the list.
   - **Expect:** that row is quietly **absent** -- never offered and then
     failing.
4. Play the moved file from its new location for a minute, stop, reopen.
   - **Expect:** it comes back, pointing at the new place.
5. If the list offers something only another app can play (a radio
   recording that lives in Cast):
   - **Expect:** Resume is disabled on that row, and the row **says which
     app** has it.

---

## 12. Recording

The Record button on the main window doubles as the stop control: while
recording it reads **"Stop Recording"**, and returns to **"Record"** when
recordings stop -- so the button's own label always tells you the state.

### T-12.1 A thirty-second capture

1. Play a live station. Press the **Record** button (or Recording > Record
   Now / Stop Recording).
   - **Expect:** the button now reads **Stop Recording**.
2. Wait about thirty seconds and press it again.
   - **Expect:** the file exists (Recording > Recordings... lists it),
     **and the stop is announced** -- a silent stop is a FAIL.

### T-12.2 Honesty about empty captures

1. Record a station that is producing no audio (a dead stream).
   - **Expect:** reported as capturing nothing, and the **empty file is
     deleted** -- no zero-byte souvenirs.

### T-12.3 Scheduling in hours and minutes

1. Open **Recording > Schedule Recording...**
   - **Expect:** separate **Hours** and **Minutes** boxes -- entering "3"
     and "0" means three hours, never three minutes.

---

## 13. Safe Mode

Quit and restart with `--safe-mode`.

### T-13.1 Refusals are per-branch and by name

1. Open Browse Stations and expand any network branch.
   - **Expect:** it refuses **by name**, per branch (T-2.2 step 3).
2. Try Favorites, **ACB Media**, **NFB Radio**, and **Networks**.
   - **Expect:** all still work -- they need no network, and Safe Mode must
     not take them hostage.
3. Try to download anything.
   - **Expect:** refused **before** any request is made.
4. Press Ctrl+F and search.
   - **Expect:** refuses; no request leaves the machine.

---

## 14. Spotify (optional, experimental)

Skip unless you have Premium and a Client ID. Nothing else in this plan
depends on it.

### T-14.1 Rows, and the two refusals

1. With Spotify enabled, search for an artist.
   - **Expect:** Spotify rows appear alongside stations.
2. Try to **download** a Spotify row.
   - **Listen for:** *"copy-protected and cannot be saved by any app,
     including this one."*
3. Try to **record** one: the same refusal.

---

## 15. The QuillVille menu

### T-15.1 Who is on the menu

1. Open the **QuillVille** menu.
   - **Expect:** **QUILL** and **Quill Weather**.
2. Look for Inkwell.
   - **Expect:** **not there** -- deliberately off Radio's menu for 3.0.

---

## What to report

For anything that fails, the useful report is three things: the **test id**
(T-9.2 step 8, say), what was **said** word for word, and what you expected
to hear. A silent failure is the most serious kind here -- if something
simply did nothing, that is worth reporting even when nothing looks broken.
A green run is the list of every T-number with PASS beside it.
