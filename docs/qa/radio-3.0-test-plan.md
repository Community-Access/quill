# Quill Radio 3.0 -- test plan

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

Work top to bottom or dip in by section -- each is self-contained. Every scenario
has a **Do**, an **Expect**, and where it matters a **Listen for**, because for
this audience the spoken result *is* the result: a thing that happens silently
has not happened.

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

| Do | Expect |
| --- | --- |
| Find Stations -> type `BBC World Service` -> Enter | Plays. Row says where it came from. |
| Playback > Stop, then Play again | Resumes the same station. |
| Ctrl+E (Sound Enhancements), move a slider | Audible **immediately** -- no gap, no reconnect. |

**Stations verified live:**

| Station | Address |
| --- | --- |
| BBC World Service | `http://stream.live.vc.bbcmedia.co.uk/bbc_world_service` |
| BBC Radio 4 | `http://as-hls-ww-live.akamaized.net/pool_55057080/live/ww/bbc_radio_fourfm/...` |
| SomaFM Groove Salad (`.pls`) | `https://somafm.com/groovesalad.pls` |

**Listen for:** a station that drops should say it is reconnecting, with an
attempt number, and either "Reconnected" or an honest failure. It must **not**
go silent. (Three attempts, at roughly 2, 5 and 15 seconds.)

---

## 2. Browse Stations: loading, and the two kinds of empty

| Do | Expect | Listen for |
| --- | --- | --- |
| Open Browse Stations, expand **Internet Archive** | A "Loading..." row appears, then real rows | "Loading...", then a count: "24 items." |
| Expand a branch, then collapse and expand again | Instant -- it is not re-fetched | The count again, no second "Loading..." |
| Expand any network branch with the network **off** | The placeholder clears; the branch does not sit on "Loading..." forever | "Nothing in X. It may be empty, or the source could not be reached." |
| Same branch again after reconnecting | It **retries** -- a branch that failed is not stuck | Real rows this time |
| Run in Safe Mode, expand **TuneIn** | Refuses by name | "TuneIn is disabled in Safe Mode." |
| Pull the network, expand a fresh branch | The decisive message, not the hedge | "X could not be reached. Close and reopen it to try again." |

This is the async-loading behaviour: the tree never blocks, every fetch is off
the UI thread, and a failed branch can be retried by closing and reopening it.

### Choosing which branches exist at all

Station > Ch&oose Browse Sources... The rule under test: a branch that is off
is **not in the tree and is never contacted** -- not hidden-but-fetched.

| Do | Expect |
| --- | --- |
| Arrow the list | Every row speaks its own state first: "On. LibriVox Audiobooks. Public-domain audiobooks, by chapter." -- with the group named on the first row of each run |
| Turn LibriVox off, close, open Browse Stations | No LibriVox branch anywhere; everything else untouched |
| Turn Off everything, open Browse Stations | One row only: "All sources are hidden. Choose Browse Sources from the menu to show some." |
| Reset to Default | The summary line says the count; Explore (Wikidata) stays off by default, everything else on |
| Restart the app | The choice survived |
| Find in this folder, on a ccMixter branch | Each result row keeps its note -- the licence rides along into search results |

---

## 3. Find Stations reaches the libraries

| Do | Expect |
| --- | --- |
| Find Stations -> `Middlemarch` | Radio stations first, then **LibriVox** rows as they arrive |
| Find Stations -> `Sherlock` | **Project Gutenberg** audiobook rows appear |
| Find Stations -> `Johnny Dollar` | **Internet Archive** recordings appear |
| Find Stations -> `The Rest Is History` | A **Podcasts** group appears |
| Find Stations -> `jazz` | **Audius**, **ccMixter** and **Mixcloud** rows appear |

**Listen for:** libraries answer *after* the stations and you are told **once**
when they have all reported -- not five times. If you are already arrowing the
results when one lands, your place must be kept.

**The music three are the regression case.** They shipped declared "cannot be
searched"; all three publish a keyword search. A ccMixter row carries its licence
in the row. A Mixcloud row says *"opens on Mixcloud in your browser"* **before**
you press Enter.

---

## 4. Podcasts, with and without transcripts

Three feeds that **do** publish Podcasting 2.0 tags (verified):

| Show | Feed | Carries |
| --- | --- | --- |
| Podcasting 2.0 | `https://feeds.podcastindex.org/pc20.xml` | transcript (SRT), chapters, people, funding |
| Buzzcast | `https://feeds.buzzsprout.com/1538779.rss` | transcript (HTML), chapters, people, funding |
| No Agenda | `https://feed.nashownotes.com/rss.xml` | transcript (SRT), chapters, funding |

Three that **do not** -- the "without" cases, equally important:

| Show | Feed |
| --- | --- |
| The Rest Is History | `https://feeds.megaphone.fm/GLT4787413333` |
| 99% Invisible | `https://feeds.simplecast.com/BqbsxVfO` |
| Radiolab | `https://feeds.simplecast.com/EmVW7VGp` |

| Do | Expect |
| --- | --- |
| Browse Stations -> Podcasts (Apple) -> pick a country -> a genre -> a show | Episodes list; Enter plays |
| Choose the **Arts** genre in a country's top chart | Results include Books, Design, Food -- **not** empty (this was the leaf-genre bug) |
| Open an episode from a feed in the first table -> **About This Episode...** | Tabs for People, and Support; no empty tabs |
| Same on a feed from the second table | Says plainly that the podcast published no extra details |

---

## 5. Transcripts

| Do | Expect | Listen for |
| --- | --- | --- |
| An episode from **Podcasting 2.0** -> Read Transcript... | Opens as a read-only text box | Arrow keys, word/line movement and your review cursor all behave normally |
| Turn **Follow the audio** on | Caret tracks the spoken line | Nothing spoken per line -- silence here is correct |
| Turn it off, arrow around | Playback never moves your caret | -- |
| Enter on any line | Plays from there | "Playing from 4 minutes 12 seconds" -- words, never `4:12` |
| Find a word | Jumps and says where | "Found at 12 minutes 8 seconds" |
| Save As -> WebVTT, reopen it | Timings survive the round trip | -- |
| An episode with no transcript | Says so; does not open an empty window | -- |

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

| Do | Expect | Listen for |
| --- | --- | --- |
| Play one, then Ctrl+Shift+V | Picture appears **without restarting** the audio | "Video shown, 1280 by 720." |
| Ctrl+Shift+V again | Picture goes; audio continues | "Video hidden. Audio is still playing." |
| Ctrl+Shift+K | Captions on/off | Says plainly if they are automatic |
| Caption Settings -> 300% | Text scales; background is **opaque** by default | -- |
| F11 | Full screen | **Both** ways out stated on entry |
| Ctrl+Shift+A (Audio and Described Audio) | Lists every track by name | -- |

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

#### Testing the absence path, which is the common case

| Do | Expect |
| --- | --- |
| Ctrl+Shift+A on the TED talk or Big Buck Bunny | Window **opens** (never greyed out): *"This video has one audio track, English. No described audio was published."* |
| Ctrl+Alt+D on the same video | The same honest answer -- not silence |
| Ctrl+Shift+A on the MrBeast video | All twenty-four dubbed tracks, each named as a language, and the same closing honesty: none of them is described |
| Ctrl+Shift+A on a **described upload** from the table above | The same honest answer, and it is **correct**: the description is baked in, so there is genuinely one track. The picker must not invent a second |
| Play a described upload through | Plays normally; description is simply the audio |

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

#### Walking the presence path

On each video in the presence table above, expect:

- On starting the video, **once**: *"Described audio is available for this
  video. Press Ctrl+Alt+D to hear the narration of what is on screen."*
- In Ctrl+Shift+A, the described track listed **first**, cursor already on it,
  and a line **above** the list: *"Described audio is available for this
  video."*
- Ctrl+Alt+D switches straight to it, and the narration is audibly there -- on
  the *ART LAB* introduction it begins over the opening titles.
- Switching **keeps your position** -- it is a separate stream, and losing an
  hour of a film to turn description on would defeat the feature exactly where
  it matters most.
- The ordinary track still listed and still labelled, so nobody who did not ask
  for description is surprised by it.

## 7. YouTube channels and playlists

| Do | Link | Expect |
| --- | --- | --- |
| Browse Stations -> YouTube Channels -> Add a channel | `https://www.youtube.com/@TED` | Channel's recent videos appear as rows |
| Station > Add from YouTube Playlist | `https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Blw3RGYpWkSByi_T7Rygb` | **19 entries** added as stations (verified count) |
| Play one, then Ctrl+Shift+I | -- | Size, frame rate, codec, and whether captions and described audio exist |

---

## 8. Playlists the internet actually uses

| Do | Link | Expect |
| --- | --- | --- |
| Import a `.pls` | `https://somafm.com/groovesalad.pls` | 3 entries (verified); each playable |
| Export favorites as M3U, re-import | -- | Same stations, same order |
| Paste a Live365 station page | any `live365.com/station/...` | Rewritten to the real stream, and it says it did |

---

## 9. Downloads -- the new one, test it hardest

### 9-pre. Download Preferences

Station > &Download Preferences... (also the &Preferences... button inside
View > Downloads).

| Do | Expect |
| --- | --- |
| Open it and just listen | Focus lands in the folder field; its name says what blank means and where the default is |
| Toggle any checkbox | The sentence at the bottom updates -- it always answers "what will happen to the next thing I save?" |
| Turn on "Ask where to save", OK, then Download a whole book | **One** folder prompt for the whole book -- never one per chapter |
| Cancel that prompt | "Download cancelled. Nothing was queued." -- declining the ask never files things anyway |
| Change the downloads folder, OK, download one file | It lands under the new folder immediately -- no restart |
| Cancel the dialog after editing | Nothing changed; the old rules still apply |

**Books verified live:**

| Book | Chapters | First chapter |
| --- | --- | --- |
| Middlemarch (George Eliot) | **86** | `https://www.archive.org/download/middlemarch_0810_librivox/middlemarch_01_eliot_...` |
| Middlemarch, version 2 | 84 | `https://www.archive.org/download/middlemarch_version2_1310_librivox/...` |

**Music with a licence:** ccMixter `Xtended Chords -- Javolenus`, licence
*Attribution Noncommercial (4.0)* -- search `jazz` in Find Stations.

### 9a. What may and may not be saved

| Row | Do | Expect |
| --- | --- | --- |
| A LibriVox chapter | Right-click -> Download... | Queued; saved under `Books\` |
| A live station (BBC) | Right-click | **No** Download item. Via the palette: *"A live station... has no end... Use Record Station"* |
| A Mixcloud row | Right-click | No Download. Refusal names Mixcloud and the browser |
| A YouTube video | Right-click | No Download. *"deliberately does not download from YouTube"* |
| An Audius track | Right-click | No Download. *"the artist's choice... does not guess"* |
| A ccMixter track | Download | Saved **plus** a `.licence.txt` beside it |

### 9b. A whole book, and the queue

| Do | Expect | Listen for |
| --- | --- | --- |
| Open Middlemarch's folder in Browse, right-click the folder | **Download All 86 Files...** | -- |
| Choose it | One folder prompt, not 86 | "Queued Middlemarch... You can carry on listening." |
| Start a station playing while it runs | Playback is unaffected | -- |
| **View > Downloads...** (Ctrl+Shift+J) | Queue window; rows read as sentences with state last | "Chapter 4, Middlemarch, downloading now" |
| Let several finish | Finished rows **stay** | A heartbeat every few chapters: "12 of 86." |
| Select a finished row -> Open Containing Folder | Explorer opens **on that file** | -- |
| Select a waiting row -> Cancel This One | Cancelled; anything saved is kept | -- |
| Remove From List on the **running** row | Refused | "That one is downloading now. Cancel it first." |
| Clear Finished, then Clear All | List empties; disk untouched | -- |
| Alt+F4 with downloads outstanding | Per preference: keeps going **or** stops | Either way it **says which** -- this is the point |

### 9c. Where things land

| Do | Expect |
| --- | --- |
| Download one book by George Eliot | `Books\Middlemarch\` -- **no** author folder |
| Download a second by the same author | The second goes in `Books\George Eliot\...` |
| Download a podcast episode | `Podcasts\<show name>\` |
| Download a ccMixter track | `Music\` |
| Turn off "folder per book" | Chapters land directly in `Books\` |

### 9d. Interruption

| Do | Expect |
| --- | --- |
| Start a book, kill the network mid-chapter | That chapter fails; the **next one still runs** |
| Restore the network, download the same book again | Part-finished files **resume** rather than restart |
| Cancel mid-chapter | Stops within seconds, not at the end of a 90 MB file |

---

## 10. A downloaded book plays as a book

| Do | Expect | Listen for |
| --- | --- | --- |
| Play chapter 1 of a downloaded book | Plays | -- |
| Let it run to the end | **Chapter 2 starts on its own** | "2 of 86, ..." -- position first |
| Check ordering on a book with 10+ chapters | Chapter 2 comes before chapter 10 | -- |
| Play the **last** chapter to its end | Stops, and says so | "That was the last chapter of Middlemarch." |
| Rename a chapter file by hand, reopen | The book simply reflects the change | -- |
| Let a **live station** run and drop | Reconnects -- never treated as a book | -- |

---

## 11. Continue Listening

| Do | Expect |
| --- | --- |
| Get 20 minutes into a podcast episode, stop | Appears in the list |
| Get 10 minutes into a LibriVox chapter, stop | Appears, labelled **recording** |
| Get 10 minutes into a downloaded file, stop | Appears, labelled **file on this computer** |
| Open **Continue Listening...** | Newest first; every row names its kind and how far in |
| Resume a row | Starts where you left off |
| Forget This One | Row goes; the episode stays **unplayed** |
| Move a downloaded file, reopen the list | That row is quietly **absent** -- not offered and then failing |
| Play the moved file again from its new place, stop | It comes back |

**Listen for:** "2 things you did not finish, across recordings, podcasts." A row
this app cannot play (a radio recording inside Cast) must have Resume disabled
and say which app has it.

---

## 12. Recording

| Do | Expect |
| --- | --- |
| Record a live station for 30 seconds, stop | File exists **and** the stop is announced |
| Record a station that produces no audio | Reported as capturing nothing, and the empty file is deleted |
| Schedule a recording in hours and minutes | Separate Hours/Minutes boxes; "3" and "0" means three hours |

---

## 13. Safe Mode

Run with `--safe-mode`.

| Do | Expect |
| --- | --- |
| Expand any network branch | Refuses **by name**, per branch |
| Favorites, ACB Media, NFB Radio, Networks | Still work -- they need no network |
| Try a download | Refused before any request |
| Find Stations | Refuses; no request leaves the machine |

---

## 14. Spotify (optional, experimental)

Skip unless you have Premium and a Client ID. Nothing else in this plan depends
on it.

| Do | Expect |
| --- | --- |
| Search with Spotify enabled | Rows appear alongside stations |
| Try to download a Spotify row | *"copy-protected and cannot be saved by any app, including this one."* |
| Try to record one | Same refusal |

---

## 15. The QuillVille menu

| Do | Expect |
| --- | --- |
| Open the QuillVille menu | **QUILL** and **Quill Weather** |
| Look for Inkwell | **Not there** -- deliberately off Radio's menu for 3.0 |

---

## What to report

For anything that fails, the useful report is: what you did, what was **said**,
and what you expected to hear. A silent failure is the most serious kind here --
if something simply did nothing, that is worth reporting even when nothing looks
broken.
