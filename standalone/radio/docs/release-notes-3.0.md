# Quill Radio 3.0 Release Notes

Quill Radio has always been able to play a station you can name. This is the
release where it becomes somewhere you can **wander** -- and where it starts
doing several things no other radio app on your desktop does at all.

Here is the shape of it, in the order you are most likely to care:

- **It finds described audio for you, and tells you it is there.** The narration
  that says what is happening on screen -- and no other desktop player will point
  you at it.
- **YouTube and Live365 become stations.** Paste a link and it plays, records,
  favorites and schedules like anything else -- chapters, playlists and all.
- **It plays podcasts with no key, no account and no sign-in**, walking Apple's
  entire directory from any country in the world.
- **You can keep things.** A public-domain book, a chapter, an episode: saved to
  your own disk, a whole book at a time, while you carry on listening.
- **Browse Stations grew from thirteen branches to twenty-eight**, and you can
  now *type a title* and have every one of those libraries answer.
- **The whole station directory ships inside the app** -- 62,000+ stations
  browsable from your own disk, instantly, with or without the internet, and
  it quietly keeps itself fresh.
- **It shows video, reads transcripts back, and remembers your place** in
  anything that has an end.
- **The app grows up around you.** Real backups, favorites that keep the order
  you built, one volume when you want one, Winamp's keys in the Recordings
  player, windows that stay put, braille for everything it says.
- **And the broadcast processor is the real one now**, not an impression of it.

Everything below is in that order: what changes most about what you can do,
first.

> **This is the whole release in one document.** It is long because 3.0 is
> large: alongside the new work, a body of features that was finished and
> documented -- and then never put in anybody's hands -- ships for the first
> time here. If you are coming from 2.1.2, and everyone is, all of it is new
> to you.

---

## Described audio, and a way to actually find it

**This is the one to read.**

A *described* audio track is a second narration mixed into a programme that says
what a sighted viewer can see: who came into the room, what the caption on screen
says, where the scene moved to. Broadcasters publish them as a matter of course.
YouTube carries them on a growing number of videos.

And essentially no desktop media player lets a blind listener find one. The
better ones expose an audio-track menu; what it contains is "Track 1, Track 2,
Track 3". Which of those narrates the picture? The only way to find out is to
play each in turn and listen. That is not a feature, it is a puzzle, and it is
the exact shape of the problem this app was built to stop.

Quill Radio names them.

**Playback > Audio and Described Audio... (Ctrl+Shift+A)** lists every audio
track a video publishes -- "English", "Spanish", "English (described) -- narrates
what is on screen" -- with the described one **first**, the cursor already on it,
and a line above the list that says, before anything else you hear, *"Described
audio is available for this video."*

**Playback > Play Described Audio (Ctrl+Alt+D)** skips the list entirely and
switches straight to it. One keystroke, for anybody who always wants description
and should not have to go looking each time.

**And it tells you, without being asked.** When you play a video that carries a
described track, Quill Radio says so once: *"Described audio is available for
this video. Press Ctrl+Alt+D to hear the narration of what is on screen."* Once
per video, never repeated, never interrupting.

That sentence is the feature. A command you have to know about only helps people
who already know it exists -- and those are exactly the people who least need
telling. Almost nobody expects a desktop radio player to have described audio at
all, so the app has to be the one to mention it.

Three things about it are deliberate.

**Switching keeps your place.** A described track is a separate stream rather
than a channel inside one, so changing to it means reconnecting -- and Quill
Radio puts you back where you were. Losing your position an hour into a film to
turn description on would make the feature useless in precisely the case it
matters most.

**Nothing is promoted behind your back.** The described track is listed first and
named; the ordinary track is still right there, still labelled. Somebody who did
not ask for description never gets it by surprise.

**When there is none, it says so, and says what there is instead.** The command
is never greyed out. You get *"This video has one audio track, English. No
described audio was published."* -- because "no described audio" on its own
leaves you wondering whether the video is missing it or the app cannot find it,
and those are completely different things to know.

The detection is deliberately generous, because publishers label these tracks
half a dozen ways -- "English (Audio Description)", "descriptive", "eng-desc",
"English AD" -- and all of them mean the same thing to somebody who needs one.

**And on YouTube, finding these tracks took a fight that is worth telling.**
Most described content there is a separate upload with the narration mixed in --
Apple's and Microsoft's accessibility films both work that way, and they play
perfectly, because the description simply *is* the audio. But some videos
publish a real selectable descriptive track: Emily Graslie's *ART LAB* series,
several of Adam Savage's *Tested* builds, two Apple films. Ask YouTube for those
the ordinary way and it names the renditions -- *"English original"*, *"English
descriptive"* -- then hands over only the original, keeping the described
track's address for its own player. Quill Radio now asks a second way at the
same time, as YouTube's own iOS player, which is given every rendition with a
playable address. So the described track is *there*, named, first in the list,
one keystroke away -- on a platform where the player in your browser makes you
find a settings gear inside a submenu to learn it exists at all.

**The same door opened every dubbed track.** A multi-language video now lists
all of its renditions by name -- one popular video offers twenty-four, from
Hindi and Tamil to Japanese and Polish -- each spoken as a language, never as a
code or a track number, with the original marked and nothing switched behind
your back.

## Two new kinds of station: YouTube and Live365

### YouTube plays and records like any other station

Paste a YouTube link into **Add Custom Station** -- an ordinary video link, a
`youtu.be` short link, or a channel's live page -- and it becomes a station: it
plays through the same player, sits in Favorites, records with Record Now, and
can be captured by a scheduled recording. Quill Radio saves the *page* address,
never a stream address, and re-finds the audio each time you play or record, so
a recording you schedule today still works next week. Off in Safe Mode. A
private, removed, region-blocked, or not-yet-live video says so in plain words.

### It works out of the box

The `yt-dlp` helper that finds the audio behind a link is built into Quill
Radio, so your first YouTube link simply plays -- no download, no consent
prompt, nothing to agree to before you have heard anything. It costs about 3 MB
in the installer, which is a better trade than a dialog standing between you and
the thing you asked for. The helper is bundled only in the apps that can
actually use it -- Quill Radio, Audio Studio, and Audio Converter -- so Weather,
Cast, Social, Beacon, and Inkwell do not carry it.

### Update YouTube Support, for when YouTube changes

**Station > Update YouTube Support...** fetches a newer `yt-dlp` than the one
your copy of Quill Radio was built with. YouTube changes how it serves audio
every so often, and when it does the helper needs updating -- so this exists to
keep you from waiting for the next Quill Radio release to get YouTube working
again. An update installed this way takes precedence over the built-in copy from
then on. It tells you which version you ended up with, asks before it reaches the
network, and is off in Safe Mode. You should not need it otherwise.

### A YouTube station knows what it is playing

Finding the audio behind a link takes one request, and that request answers with
far more than an audio address. Quill Radio keeps all of it: the video's
**length**, its **uploader**, its **description**, the **chapters the uploader
published**, and whether a **caption track** exists. None of it costs an extra
moment or an extra connection -- it rides the request the app was making anyway.

A live broadcast reports no length at all, which is the honest answer -- it has
no timeline to sit on.

### A finished video has a timeline, so you can move around it

This is the part a live broadcast can never offer, and it is where a YouTube
station stops being "radio that happens to come from YouTube" and starts being a
player. Everything below is on the **Playback** menu and works on any finished
video:

| Key | What it does |
| --- | --- |
| Ctrl+Shift+C | **Chapters...** -- the uploader's own chapter list; Enter jumps to one |
| Ctrl+Alt+Right | Next chapter |
| Ctrl+Alt+Left | Previous chapter, or back to the start of this one |
| Ctrl+Shift+Right | Forward 30 seconds |
| Ctrl+Shift+Left | Back 30 seconds |
| Ctrl+Alt+Up | Play faster |
| Ctrl+Alt+Down | Play slower |
| Ctrl+Alt+0 | Normal speed |
| Ctrl+Shift+P | **Where am I?** -- position, length, and the chapter you are in |

The chapter list reads each entry as a whole sentence -- "3. Introducing layers,
starts at 5 minutes 31 seconds" -- and marks the one playing now. Speed steps
through round, speakable values (0.25x to 4x) rather than drifting by a
multiplier, and the speed you choose is remembered for the next video.

**Every one of these says why when it declines.** Point any of them at a live
stream and you hear "This is a live stream, so there is no timeline to move
along", not silence. A slider that cannot move and a "next chapter" that quietly
does nothing are worse than not offering them at all, because you cannot tell a
broken control from a stream that has no timeline. Ask for chapters on a video
whose uploader published none and it says that too.

**Go to Position... (Ctrl+Shift+J)** is the other half of having a timeline.
Skipping thirty seconds at a time gets you near; this gets you exactly where you
meant. It opens the same accessible dialog the Quill Media Player uses -- three
labelled Hours / Minutes / Seconds spin controls as the primary input, plus a
timecode field if you would rather type `1:23:45` -- rather than growing a
second, lesser prompt of its own. Ask for a point past the end and it says so
and takes you to the end instead of failing.

**And a fix that belongs here.** Rewind / Forward 30 Seconds always ran the
*live-stream* seek, which moves inside mpv's rolling buffer and reports how far
behind the live edge you now are. On a finished video there is no live edge, so
that number was invented -- exactly the kind of confident wrong measurement this
app refuses to make anywhere else. The keys now pick the operation the source
actually deserves: a video moves along its own timeline and says "3 minutes 10
seconds of 18 minutes 40 seconds"; a live stream behaves precisely as before.

### Add from YouTube Playlist

On the Station menu. Paste a `playlist?list=...` link -- already filled in for
you if it is on your clipboard -- and Quill Radio lists the videos in the
uploader's own running order, never re-sorted, because a series is meant to be
worked through in order.

Each row reads as a whole sentence: "3. Introducing layers, 5 minutes 31
seconds, 3Blue1Brown". Everything about a video is in the line your screen
reader speaks, so there are no columns to arrow across. Times are spelled out in
words on purpose -- "5:31" read aloud is ambiguous unless you already know it is
a time.

Arrow the list, select what you want with Shift or Ctrl, and choose **Add
Selected** -- or take the lot with **Add All**. Each becomes an ordinary station
you can play, favorite, and record. Quill Radio says how many it added and how
many were already in your favorites, so adding fifty videos never leaves you
wondering whether the button worked.

The listing itself is deliberately shallow: one request for the whole playlist
rather than one per video, and no video's audio is fetched until you play it.

The window is headed with the playlist's own name, read from the same request
that fetched the list, so you always know which playlist you are looking at.

A *watch* link that happens to carry a `list=` in it is still just that one
video. You asked for the video; quietly turning it into fifty stations would be
a nasty surprise.

**What this is, and what it is not.** Adding a playlist is an **import**, not a
subscription and not a play queue. The videos you pick become ordinary favorites
-- each plays, records, and schedules exactly like a station -- and they sit in
your favorites list alongside everything else rather than in a folder of their
own. Nothing plays through them in order: playing one video plays that video, and
Quill Radio does not move on when it ends. Nothing re-checks the playlist later,
so videos added upstream after your import are not picked up -- run the command
again on the same link to collect them, and anything already in your favorites is
skipped rather than duplicated. Playing a playlist as a queue, and keeping one in
step with its source, are separate pieces of work; saying so is better than
letting "playlist support" imply either.

### Search YouTube from Find Stations

Type a search and YouTube videos appear alongside the radio directories, each
one an ordinary station you can play, favorite and record. No key, no account,
no setup -- it uses the same yt-dlp that already plays your YouTube links, so
there is nothing to configure.

Rows read "title, uploader", and the search is deliberately shallow: one
request for the whole result set, and no video's audio is fetched until you
actually play it.

A note on how this works, because it matters for what to expect. Quill Radio
does not use YouTube's official Data API, which would require every listener to
create a Google Cloud project and paste an API key in before searching. It uses
yt-dlp's keyless extraction -- the same approach FreeTube, NewPipe and
Invidious all take. The trade-off is that YouTube occasionally changes how its
site works and extraction breaks until upstream fixes it. That is exactly what
**Station > Update YouTube Support...** is for: it fetches a newer yt-dlp
without waiting for the next Quill Radio release.

### Paste a Live365 link and it just plays

The Live365 link you actually have is almost never the stream -- it is the
station page or the web player, and both of those are web pages, which no player
can play. Add Custom Station recognizes any Live365 station page, player link, or
bare station id and rewrites it to that station's real stream address, telling
you it did. It is a pure text rewrite: no network
lookup, nothing sent anywhere, and a link that is not Live365 is passed through
exactly as you typed it.

## Podcasts, and not a single key anywhere

Open **Podcasts (Apple)**.

Choose a country. You get that storefront's top shows, and Apple's entire
podcast genre tree -- Arts, and inside it Books, Design, Fashion & Beauty, Food,
Performing Arts; Comedy; Education; Fiction; and the rest, with their subgenres
beneath them. Open a show and you get its episodes. Press Enter on an episode and
it plays.

There is no key, no account, no registration and no sign-in at any point in that
chain. There is no "connect your account" step and nothing to configure in
Preferences before it works.

Two things about it are worth knowing.

**The top podcasts in Ireland, or Japan, or Brazil are one folder away.** Apple
publishes its charts per storefront, so the country you pick at the top is a real
axis rather than a label. Almost no desktop podcast client offers this, and for
anyone who follows broadcasting outside their own country it is the whole point.

**Apple stops being involved as soon as you open a show.** A show resolves to its
own RSS feed, published by whoever makes the show, and everything after that --
the episode list, the audio, the transcripts -- comes from them. Apple is a way to
*find* the feed and nothing more. If this branch were switched off tomorrow you
would lose a way to discover shows and you would not lose a single thing you
already subscribe to or play.

**And you can just type the name.** Podcasts are searched from Find Stations
alongside everything else, so a show you can name does not need a walk through
the genre tree at all. Shows arrive in their own **Podcasts** group in the
results.

**A note on a bug worth knowing about, because you may have hit it.** Apple tags
a charting show with its *leaf* genre and never with the genres above it -- a
show filed under Books carries Books and not Arts. Filtering a storefront's top
hundred by Arts therefore returned nothing at all, which looks exactly like an
empty chart. Choosing a genre now includes everything beneath it, so Arts means
Arts *and* Books, Design, Food and the rest.

**It is gentle with Apple, deliberately.** One chart request serves every genre
in a storefront rather than one per genre, the genre tree is kept for a week,
charts for six hours, and a resolved feed address for a month. Wandering the tree
costs almost nothing after the first visit, and nobody's directory is hammered
for the privilege.

---

## Keep it: the things you are allowed to keep

Quill Radio plays a great deal that is genuinely yours -- public-domain
audiobooks, old-time radio, Creative Commons music, podcast episodes published
for exactly this purpose. Until now it could play all of that and save none of
it.

**Download...** on a row's menu saves it to a folder you choose. **Download All
Files...** on a book's folder saves the whole thing, chapter by chapter, in
order, while you carry on listening to something else.

**A whole book is the case this was built for.** A LibriVox novel is forty
chapters and forty separate addresses -- an hour of transferring over a
connection that will hiccup at least once. So chapters are fetched **in order**,
which means a part-finished book is the first twelve chapters, something you can
start listening to, rather than a scattering you cannot. A part-finished *file*
picks up where it stopped instead of starting again. One bad address costs **one
chapter**, never the book, and the summary names which one. And progress is
counted the way a person counts: *"12 of 40"*, spoken every few chapters, rather
than a percentage of a number nobody actually has.

**Stopping keeps what arrived.** Stop takes effect inside a chapter rather than
at the end of a 90 MB one, and everything already saved stays saved.

**And it will not save what is not yours to save.** This is worth being plain
about, because getting it wrong means an app writing you a file it had no right
to write. A source has to be **affirmatively allowed**; anything unrecognised is
refused rather than guessed at. Where Download is not offered, asking for it
anyway tells you which of four quite different things is true:

| Why it is not offered | What Quill Radio tells you |
| --- | --- |
| It is a live station | There is no file to save -- a broadcast has no end. **Record Station** is the command you actually want, and it says so. |
| Spotify | Copy-protected. No app can save it, including this one. |
| YouTube | A decision, not a limitation. Quill Radio plays and records; downloading from YouTube is not something it does. |
| Audius | Whether a track may be downloaded is the artist's choice, and the listing does not say. Quill Radio will not guess on their behalf. |

**And it queues.** Say yes to four books while you carry on listening to a
fifth. **View > Downloads...** (Ctrl+Shift+J) is the queue: what is waiting,
what is going, what arrived, and what failed -- each row a sentence with its
state last, because when you are arrowing a list you already know what the items
are and what you are looking for is where each has got to.

Finished rows **stay** until you clear them, because *"did that actually
download?"* is the question people ask most and a list that tidies itself away
cannot answer it. **Open Containing Folder** takes you to a saved file; a
download you cannot find is a download that did not really happen. Cancel one,
remove one from the list, clear the finished, or clear the lot -- and every one
of those keeps whatever is already on disk.

**Close the window and it keeps going**, if that is what you asked for. Either
way Quill Radio says which: a queue that silently keeps running is exactly as
surprising as one that silently stops, and which happens is a preference you set
once and will not remember at the moment it matters.

**Where things land is arranged for you -- and every rule is yours.** A podcast
goes under its show; a book gets a folder of its own, because a book *is* a
folder. And when you have more than one book by somebody, the author gets a
folder too -- but not before then, since an author folder holding exactly one
book is a folder you open and immediately leave.

**Station > Download Preferences...** is where those rules live: the downloads
folder itself (blank means a Quill Radio folder inside your own Downloads), a
switch for each filing rule, whether closing to the tray keeps the queue going,
and an *ask me where* mode that asks **once per book, never once per chapter**
-- and if you cancel the ask, nothing is queued, said out loud, rather than
quietly filed somewhere you just declined. A live sentence at the bottom of the
window always answers the only question that matters there: *what will happen
to the next thing I save?* The same window is one button away inside View >
Downloads, because that is where the question occurs to people.

**A downloaded book plays like a book.** Chapters are in order -- 2 before 10,
which is obvious to a person and wrong in every naive sort -- and when one ends
the next begins, announcing itself briefly: *"4 of 40, The Dead Hand."* The end
of a book says so rather than falling silent, because silence after fourteen
hours is indistinguishable from something breaking.

**A Creative Commons licence travels with the file.** Save a ccMixter track and
its terms are written into a small text file beside the audio -- because saving
somebody's work under a licence and dropping the licence strips exactly the
information it exists to carry.

## The catalog: the radio that works before the internet does

3.0 changes not just where you can wander but **when**: now. Before the
network is up. On the train. During the outage. The whole station directory
ships inside the app and lives on your computer, and the internet's new job
is keeping it fresh rather than answering every question.

### Sixty-two thousand stations, zero waiting

Open Browse Stations and expand By Country. It answers instantly -- not
"fast", instantly, under a millisecond -- because the answer comes from a
catalog on your own disk: the full working-station directory, more than
62,000 stations across 240 countries, every genre, every language, every
codec, plus SomaFM and the complete Project Gutenberg audio shelf. All of it
arrives with the app. First launch on a machine with no internet at all is a
complete radio.

And every folder now tells you its size before you open it -- "France, 812
stations" -- something the live directory could never afford to say, because
counting used to cost a network round trip and now costs nothing.

Find Stations gains the same superpower: local matches appear the moment you
search, with the live directories layering in behind them. Pull the network
cable mid-search and you still get results.

### What is offline, and -- just as plainly -- what is not

The catalog covers the station directory itself: Radio Browser's 62,000+
stations and every axis through them, SomaFM, and the Project Gutenberg
audiobook shelf. These branches answer with no internet at all.

The rest stays live, each for a stated reason:

- **Apple Podcasts (iTunes)** -- charts are rankings, and Apple's terms bar
  storing them. Browsing and playing podcasts needs the internet.
- **TuneIn** -- its directory is a remote tree that may not be stored.
- **iHeart** -- its terms do not allow storing its listings.
- **Internet Archive** -- its collections run to half a million items;
  a copy would dwarf the app.
- **LibriVox** -- live *for now*: its full chapter listing alone is bigger
  than everything else in the catalog combined, and it deserves a compact
  format of its own rather than a squeezed-in copy.
- **The music charts (Audius, Mixcloud, ccMixter)** -- charts are stale the
  moment they are stored.

None of this is buried in a manual. View > Station Catalog Status lays it
out in plain sentences: what is stored on this computer and how fresh it is,
source by source -- and what is not stored and why. The same honesty runs
through the browse window itself: highlight any branch and the details panel
says either "Answers from your catalog, updated 2 hours ago" or "Asks the
internet each time; nothing is stored."

And if you are offline, the app says so exactly once: "You are offline.
Browsing from your catalog, updated this morning." Then it gets out of the
way and keeps working, because quietly working is the feature.

### It keeps itself fresh, and tells you what changed

A catalog that ages into a lie would be worse than no catalog. So it updates
three ways, each yours to switch off:

- **Shortly after launch**, a quick background check -- skipped when the
  catalog is already fresh, so a restart never hammers anyone's directory.
- **On a schedule**, every 24 hours by default (choose 6 hours to 2 days, or
  "Manually only"), one source at a time, a trickle rather than a burst.
- **On demand**: Station > Update Station Catalog, which always answers out
  loud -- "Station catalog updated: 174 new stations, 431 updated. Xiph could
  not be reached; keeping what you have."

That last sentence is the whole philosophy. A directory that is down costs
you its freshness, never your stations. A source that answers with nothing
when it had thousands yesterday is treated as an outage, not as the truth. A
station that disappears is hidden at once but only truly forgotten after two
weeks, so one bad afternoon at a directory cannot hollow out your catalog.

### Popular and Trending stay honest too

Rankings are statements about *now*, so they stay live-first. When the
directory cannot answer, the catalog steps in with its vote snapshot -- and
every one of those rows says "as of 2 hours ago" out loud, because an
unlabeled stale ranking is a small lie and a labeled one is a rescue.

### Your stations were never part of the deal

Everything above concerns the catalog, and the catalog is a copy of public
directories. Your favorites, your custom stations, your servers, your
YouTube channels -- those live in their own files, and no catalog operation
reads or writes them. Not carefully avoided: structurally elsewhere. Rebuild
the catalog from scratch and your stations are byte-for-byte untouched, and
there is a test that proves exactly that.

### The fine print that is actually good news

- The whole catalog adds about seven and a half megabytes to the download.
- Turning the catalog off (Preferences) restores live-only browsing exactly:
  nothing stored, no background requests of any kind.
- Safe Mode never refreshes; reading the local catalog is allowed, because it
  is local data, exactly like your favorites.
- A branch you hide in Choose Browse Sources is not refreshed either. Off
  means off -- not in the tree, never contacted.

## Somewhere to wander: Browse Stations

Open **Browse Stations** and there are far more ways in than there used to be.
Four are axes the station directory always had and nobody had ever exposed;
seven are whole libraries that simply were not there.

### Four new ways through the station directory

Open **Browse Stations** and there are four branches that were not there before.
None of them required a new service, a new account, or anyone's permission. Every
one of them is data the station directory has always published and Quill Radio
was already downloading.

#### Browse by country, then by state or region

The most-asked-for way to find a station anywhere, and the one Quill Radio was
closest to having without knowing it. Radio Browser records the country and the
region of every station it lists. Quill Radio used that to fill one dropdown in
the Search dialog and nothing else.

Now: open **By Country**, choose a country, and you get its states or regions.
Open one of those and you get its stations, most-listened first. A country with
no regional breakdown -- and there are many -- gives you its stations directly
rather than making you open an empty folder to find out that it has none.

#### Browse by language

The same data on a different axis, and the one that is genuinely hard to find
anywhere else. Most radio apps organise the world by where a station is. If the
radio you want is not in the language of the country you happen to be sitting in
-- which is an ordinary situation for a great many people -- that organisation is
the wrong one. **By Language** is the right one.

#### Browse what is trending now

Not the same thing as **Popular Stations**, which has been there for a while.
Popular ranks by votes: what people once thought was good, accumulated over
years. **Trending Now** ranks by what is being listened to *today*. The two lists
disagree far more than you would expect, and offering only the first was missing
the livelier half of the directory.

#### Browse stations recently added or changed

New stations, and stations whose address was just repaired. Cheap to offer, and
it is the branch that makes a directory feel alive rather than archival.

---

### Seven more places to wander

Everything above is a station directory rearranged. These are new libraries.

#### Internet Archive: old-time radio and live music

Open it and you get Old Time Radio, Audiobooks & Poetry, the Live Music Archive,
Radio Programs, News & Public Affairs, and more. Open one of those and you get
its series; open a series and you get its episodes; open an episode and you get
its files. The depth is not something we built -- the Archive genuinely is a
tree, every item declares its parents, and one query shape walks the whole
thing. Old Time Radio alone holds 8,710 recordings across 114 series.

A folder that holds more than a page says **More...** and tells you how much it
is hiding, because a tree that quietly shows the first hundred of eight thousand
is lying. And an item with no published rights information says exactly that,
rather than letting you assume.

#### LibriVox: public-domain audiobooks

Recently Added, By Genre across 43 genres, and By Author grouped A-Z through
some seven thousand of them. A book with chapters is a folder of chapters; a
book that is a single reading is simply playable.

There is deliberately no **By Title**. LibriVox's own catalogue can be browsed by
author, by genre and by date, and not by title -- there is simply no such list to
ask it for. Offering the branch anyway would give you a folder that always came
back empty, and a branch that quietly finds nothing is worse than one that is not
there.

#### Project Gutenberg: human-read audiobooks

The 1,124 Gutenberg records that carry human-read audio, by topic and by
language. Complementary to LibriVox rather than a duplicate of it.

#### Audius, Mixcloud and ccMixter: three music libraries

**Audius** -- independent music, trending overall and trending within 27 genres.
No key; the app identifies itself by name. Gated tracks are dropped rather than
listed and then refused when you press Enter.

**Mixcloud** -- 28 music categories and 10 talk categories of DJ sets and radio
shows. Browsing is metadata only: Quill Radio never extracts a Mixcloud stream,
and activating a show opens it on Mixcloud in your own browser. **The row says
so before you press Enter**, not after.

**ccMixter** -- Creative Commons music by tag, and every row carries its licence
in the row itself. For material offered under terms, showing the terms is the
whole courtesy.

#### Explore: every station Wikidata knows about

The branch with axes no station directory publishes: **By City**, **By Owner**,
**By Network**, **By Format**, and **On the Dial**, which groups stations by the
part of the FM band they sit in.

None of that is Radio Browser's data. Wikidata knows who owns a station, which
network it belongs to and what city it licenses from; Radio Browser knows how to
play it. Putting the two together is what makes "every station this company owns"
a folder you can open.

It is labelled **from Wikidata** on every row, and it should be, because the join
between the two is Quill Radio's own rather than something either source
publishes. Nothing here changes how a station plays, records or is favorited --
the stream is still Radio Browser's, exactly as it is everywhere else in the
tree.

#### My Servers: your own Icecast or Shoutcast

The branch no directory can give you.

TuneIn never listed the community station three towns over. Radio Browser never
indexed the church, the school, or the reading service that runs its own box.
But almost all of them run Icecast or SHOUTcast, and both publish -- with no key
and no registration -- a complete list of what they are serving right now.

So you supply the address once and browse it forever after. Open **My Servers**,
choose **Add a Server...**, paste the address (already filled in for you if it is
on your clipboard), and Quill Radio checks it before saving it: "Added
http://stream.example.org:8000. It has 4 stations." An address that answers with
nothing is deliberately **not** saved -- a branch that is empty the day you add it
is nearly always a wrong address, most often a missing port number, and keeping
it would just leave a row that never does anything.

Every stream on the server then appears with **what is playing on it right now**,
so you can tell what is on before you tune in. Refresh brings it up to date.

One honest note: a great many small Icecast boxes are plain `http` on a high port
and always have been. Quill Radio accepts those here rather than refusing the
entire audience this branch exists for. It is an address you typed yourself,
nothing is sent but a request for the station list, and no password is ever
attached to it.

#### YouTube Channels: follow a channel like a station

Follow a channel without a Google account, without signing in to anything, and
without a subscription that anybody else can see.

**Add a Channel...** takes a channel address; Quill Radio reads it once to check
that it can before saving it. After that the channel is a folder: **Uploads**,
plus any playlists the channel publishes. A channel with four thousand videos
does not try to be one enormous list -- it pages, and the **More...** row tells
you there is more. Videos play, record and can be favorited exactly like a
station.

#### Browse by network: the BBC, NPR, and broadcasters worldwide

Browse Stations gains a **Networks** branch that gathers well-known broadcasters
into one-click lists, grouped by type: public broadcasters (BBC, CBC, ABC
Australia, RTE, RNZ, NHK, Deutsche Welle, Deutschlandfunk, Radio France, and
more), US news and talk (NPR, Fox News Radio, CNN, Bloomberg), US public radio,
sports, and music. Each list is drawn live from the Radio Browser directory, so
there is nothing new to keep up to date and no new place your searches go.
Syndication services that have no single stream of their own -- Westwood One, NBC
News Radio, ABC News Radio -- open a search across their local affiliate stations
instead, and the label says so.

**Browse Stations also remembers where you were.** Play a station and reopen the
browse tree, and it lands on the source you were last in -- Networks, TuneIn,
iHeart, wherever -- instead of collapsed at the top with everything closed.

### And the tree is yours to prune

Twenty-eight branches is a good problem and still a problem: if you only ever
open your local stations and ACB Media, every branch you never use is not
clutter, it is *distance* -- something to arrow past, every time, forever.

**Station > Choose Browse Sources...** fixes that the same way Search Sources
does. Every branch can be hidden, each row in the chooser says its own state
out loud -- *"On. LibriVox Audiobooks. Public-domain audiobooks, by chapter."*
-- and one button flips the branch you are on, with Turn On All and Reset to
Default beside it. The rule is the one that matters: **a branch that is off is
not in the tree at all, and is never contacted.** Not hidden-but-fetched;
gone. So this is a speed and a privacy control as much as a tidiness one.

Two details are deliberate. Hide everything and Browse Stations does not open
onto a blank window -- one row tells you exactly how to get your sources back.
And the choice is stored as *your* choice, so a source added in a future
version appears on its own for anyone who never touched the setting, instead
of being frozen out by a list written before it existed.

### Finding your next favorite

Browsing got kinder. Expanding a country or a genre in Browse Stations no longer
flings your cursor down into the station list; it stays on the folder you opened
-- you still hear its count -- so you step into the stations when *you* decide to.
The search source picker now reads **Radio Browser** as two clear words (run
together, a screen reader could make the option sound as though it had gone
missing), and there is a **Radio Browser (by Genre)** branch so you can wander
that enormous directory by genre instead of only searching it. And after you
update in place, new categories -- iHeart, Radio Reading Services -- show up right
away: Browse used to keep serving the previous version's cached directory until it
expired, and it now recognizes when the app itself ships a newer one, while still
respecting a directory you refreshed by hand.

## Type a title, and everything answers

Browsing is how you find something you could not have named. Search is how you
get to something you can -- and in 3.0 it reaches everything, not just the radio
directories.

### Choose what Find Stations searches

Quill Radio now searches eight places, which is wonderful when you are hunting
for something and noise when you already know what you want. **Station > Search
Sources...** lets you switch any of them off:

| Source | What it is |
| --- | --- |
| Radio Browser | The community directory behind most results |
| TuneIn | TuneIn's station directory |
| iHeart | iHeartRadio's stations |
| SomaFM | SomaFM's listener-supported channels |
| NOAA Weather Radio | US weather radio by SAME code, callsign, county or state |
| Radio Reading Service | Services broadcasting newspapers and magazines aloud |
| Spotify | Songs, shows and episodes; needs a connected account |
| YouTube | Videos, added as stations |

**A source that is off is never contacted.** This is not a filter applied to
results that were fetched anyway -- turning off iHeart means those network
requests do not happen. So switching sources off makes searching genuinely
faster and quieter, not just tidier.

Each row says its own state and what the source is: "On. YouTube. Videos, added
as stations you can play and record." There are no checkboxes, because checkbox
state inside a list is announced inconsistently across NVDA, JAWS and Narrator
-- and on/off is the one thing this dialog exists to tell you. **Turn On or
Off** flips the row you are on and says what happened.

**Your choices are remembered** -- both which sources are on and the Source
filter in the results list. A preference you have to set again on every search
is not really a preference. **Reset to Default** turns everything back on.

### Find Stations reaches the libraries too

Type a title and the results list gets **LibriVox books, Internet Archive
recordings, Project Gutenberg audiobooks and podcasts** alongside the radio
stations -- each row labelled with where it came from, so a book and a station
are never confused, and the existing **Source** dropdown narrows to one of them
if you want.

The libraries answer **separately from the stations and appear as they arrive**,
so one slow library never holds up the rest, and you are told once when they have
all reported rather than five times as they land. If you are already arrowing the
station results when a library answers, your place is kept.

**And the music libraries answer too.** Audius, Mixcloud and ccMixter were nearly
shipped as "browse only" -- the tree offers them as trending, categories and tags,
and that had quietly become a belief that the services could not be asked a
question at all. They can, all three, and they always could. Type a title and
their results arrive with everything else.

The three behave slightly differently once found, and each row says which it is.
An **Audius** track and a **ccMixter** upload play here, and a ccMixter row
carries its Creative Commons licence in the row itself, because for material
somebody released on those terms, showing the terms is the whole courtesy. A
**Mixcloud** row is the show's page and opens in your browser -- Quill Radio
never takes a stream from Mixcloud -- and it tells you that before you press
Enter rather than after.

## See the picture, when you want it

Quill Radio could play a YouTube link and could not show it. It can now --
**Playback > Show Video (Ctrl+Shift+V)** -- and the design is one sentence:

**Video is a view onto what is playing, never a mode of playing.**

Closing the video window, or never opening it, leaves Quill Radio behaving
exactly as it always has. Opening it costs nothing and interrupts nothing: the
picture attaches to a stream that is already playing, so showing it does not
restart anything and **cannot cost you your place**. Hiding it again is the same
keystroke, and the audio does not so much as stutter.

Why this matters even in an app built for blind listeners: somebody with usable
residual vision, who uses Quill Radio precisely because YouTube's own site is
hostile with a screen reader, was getting audio only. So was anybody wanting to
share what they are listening to with a sighted person in the room. Neither is a
group to exclude from a feature that is nominally for them.

**The picture reports itself properly.** This is where video players usually
fail: the image is an unnamed window that a screen reader lands on and calls
"graphic", if it says anything at all. Here it has a real name -- *"Video: The
Adventures of Sherlock Holmes, part 4"* -- and a description that says what it is
and where the controls are. It is in the tab order exactly once, Tab always
leaves it, and it never grabs focus by itself.

**There are no on-screen buttons, on purpose.** Every command is on the Playback
menu, on the Command Palette, and on a key you can change. An unlabelled strip of
picture buttons is how video players become unusable, and this window does not
have one. The status line beneath the picture is text you read when you want it,
not something that announces itself -- a position display that speaks constantly
is the single most common way a media player becomes intolerable.

What you get:

| Command | Key | What it does |
| --- | --- | --- |
| Show Video | Ctrl+Shift+V | Shows or hides the picture. "Video shown, 1280 by 720." / "Video hidden. Audio is still playing." |
| Captions | Ctrl+Shift+K | On and off. Says plainly when the captions are automatic. |
| Caption Settings... | -- | Size to 300%, text and background colour, opacity, top or bottom. |
| Video Information | Ctrl+Shift+I | Size, frame rate, codec, and whether captions and described audio exist. |
| Take a Snapshot | -- | The current frame as a picture file -- for a slide you want to read with OCR or send to somebody. |
| Full Screen | F11 | And it tells you both ways out on the way in. |
| Video Size | -- | Fit, 50%, 100%, 200% -- from the keyboard, because everything here is. |

**Captions default to solid white on solid black.** Not the semi-transparent grey
most players use, and the reason is simple: caption text sits over arbitrary
moving pictures, so no colour can be guaranteed to contrast with whatever is
behind it. An opaque box is the only honest default. They scale to 300%, because
the standard asks for 200% and a floor is not a target.

**And the picture can be dimmed.** Nothing can tell whether a video contains
flashing before it plays, so promising it does not would be a lie. What can be
offered is control: the picture can be dimmed for light sensitivity, and the
keystroke that removes it entirely works from anywhere in the app -- so getting
away from an unpleasant image never means finding the right window first.

Two things deliberately not built: **no YouTube web player** (it would bring a
browser engine, its accessibility, its adverts and its tracking into an app that
exists to avoid all four), and **no video downloading**. Recording still captures
audio.

**The YouTube notice changed.** It used to say Quill Radio contacts YouTube "to
find the audio stream behind the page". That stopped being the whole truth, so
it now says audio *or video*, and says the rights reminder more firmly, because
video raises more of those questions. Anybody who already agreed is not asked
again -- consenting to YouTube is consenting to YouTube, and asking twice for a
superset of the same thing is friction rather than ethics -- which is exactly why
it is written down here.

## Transcripts learned to keep time

A finished video's captions, and a podcast episode's published transcript, could
already be fetched and opened as a QUILL document to annotate or braille. What
they could not do was connect to the audio, because reading them threw the
timings away -- exactly right for "open this as a document" and useless for
anything that follows along.

Transcripts and captions are now read into **timed lines**, and there is a window
that uses them. **Playback > Transcript...** (Ctrl+Shift+T) on a finished video
opens it.

It is an ordinary read-only text box, deliberately: arrow keys, word and line
movement, selection and your screen reader's own review cursor all work exactly
the way they work everywhere else, which a custom list would have taken away and
replaced with nothing you asked for. What the timings add is everything around
the edges:

- **Follow the audio.** Turn it on and the cursor moves to the line being spoken.
  It is **off** by default, and that is the important half: while you are
  reading, playback never moves your cursor. You are reading; the audio can wait.
- **Play from here.** Press Enter on any line and playback jumps to the moment
  that line was spoken -- "Playing from 4 minutes 12 seconds."
- **Find, with the position spoken.** Ctrl+F searches, and each hit is announced
  as *"Found at 12 minutes 8 seconds"* rather than just moving the cursor. That is
  the thing a transcript in a text file can never do for you.
- **Copy** the selection, or the whole transcript when nothing is selected.
- **Save As** in plain text, **WebVTT** or **SubRip** -- the timed forms, because
  somebody keeping a transcript usually wants one another player can follow.
- **Open in QUILL** as a document, exactly as before.

**An automatic caption track says so, in the heading**, every time. Machine
transcripts are useful and they are not accurate; presenting one as if a person
wrote it would be the sort of confident wrong answer this app refuses to give.

Two details:

**YouTube captions stopped being thrown away.** Every time Quill Radio resolved a
YouTube link it also received that video's caption track, and discarded it. That
format is now understood alongside WebVTT, SubRip and Podcasting 2.0's own
format, so a YouTube video's transcript costs nothing extra to obtain -- it had
already been downloaded and dropped on the floor.

**Nothing you already relied on changed.** The plain-text form of a transcript is
now *defined* as the timed form with the timings removed, so there is one reader
rather than two that drift apart, and every transcript Cast could read before
reads identically today.

---

## Pick up where you left off

A live station has no place to come back to: you tune in and you are where
everybody else is. Anything with an **end** is the opposite, and losing your
place in a fourteen-hour book is the difference between a library and a shelf you
cannot reach.

### Everything you started, in one list

**Playback > Continue Listening...** shows every recording you began and did not
finish, newest first, with how far in you are: "The Moonstone, chapter 4,
recording, 10 minutes in, 8% through". A live station never appears -- you tune
in and you are where everyone else is, so there is nothing to come back to -- and
neither does anything you finished.

**Resume** starts the highlighted one where you left off, through exactly the
path Browse uses, so nothing about how it resumes is special-cased. **Forget This
One** drops the saved place and takes the row out, because a resume list you
cannot clear fills up with things you abandoned on purpose and stops being worth
opening.

**Files on this computer are in the list too** -- a downloaded book, an
imported recording, anything played from disk. Your place in a file is
remembered by the file's *contents* rather than its name, so it survives moving
and renaming; where the file actually sits is kept separately and never leaves
this machine. A file that has moved is quietly left out of the list rather than
offered and then failing, and your place in it is not lost: it is found again the
next time you play it.

Recordings you left before this release are still resumed when you open them
again; they simply cannot be *listed* here, because the older saved places kept
only a position and no name to show. Anything you play from now on appears.

### Your place is kept, where a place makes sense

A live station has no position worth remembering. You tune in and you are where
everybody else is, and a radio that offered to "resume" a live stream would be
offering nonsense.

A recording is the opposite. A LibriVox chapter, an Old Time Radio episode, a
podcast episode -- losing your place in a four-hour recording is the difference
between a library and a shelf you cannot reach. Quill Radio now keeps your place
in anything that has an end, and offers it back the next time you play it.

Two deliberate refusals inside that. **Four seconds in is not a position**, so
saving one clears the entry rather than leaving a prompt to dismiss for no gain.
And **finishing clears it too**, so replaying something starts at the start
rather than at the closing credits.

---

## Know what is playing, and hold onto it

**Ctrl+T** does more than speak now. "What's Playing?" opens a small window with
the current title and artist in a field you can arrow through character by
character and copy -- to catch a spelling, or paste a song into a search -- and it
still speaks the title, still falls back to speaking when a stream has not sent
its track yet. Any favorite gives you the same reviewable readout through
**Station Details...** on its context menu: source, stream, format, country. More
stations actually have a title to show, as well: a batch of streams -- some HLS,
and a handful others could read but Quill Radio could not -- tuck the current song
into the player's metadata rather than the main title field, and Quill Radio now
reads that too, so names and artists appear where they used to be blank. And there
is a new way to reach the volume: a **Volume** slider right in the Tab order, so
you can tab to it mid-song and arrow it up or down -- however you change the
volume, the slider, the status bar, and Ctrl+Up/Down all stay in perfect
agreement.

**Report Bad Station.** A station that plays for the directory but not for you is
something only you can flag. **Report Bad Station...** on any station's context
menu (in Browse Stations and Search Stations) opens the normal Report a Bug flow
pre-filled with that station's details -- name, stream, source, country -- so the
report is complete on the first try. It carries station information only; never
your name, email, or file paths.

## Song History: what that station played earlier

**What's Playing** tells you the song on right now, and then it is gone. **Song
History** (Playback menu, **Ctrl+Shift+H**) is the memory behind it: a
per-station list of every track change Quill Radio noticed, newest first, with
the time you heard it. Pick a station at the top, arrow the list, and each entry
reads as a whole sentence -- "Your Song by Elton John, heard 10:04, played
twice".

From any song you can **Copy** it, **Send to Clip Library** to keep it with your
other saved snippets, or ask for **Background**: a short, friendly note about the
song and artist from whichever AI provider you have set up. That answer is always
introduced as written by an AI model rather than by the station, because it sits
inches from the station's own information and the two must never be confused. It
needs no setup beyond the AI you may already have configured, it is never
available in Safe Mode, and if you have no provider set up the window simply says
so.

The log is yours and stays on your machine. It keeps up to 200 songs per station,
one station's listening never pushes out another's, and **Clear...** empties one
station or all of them. If you would rather Quill Radio not keep the list at all,
turn off **Keep a song history for each station** in Preferences; existing
entries stay until you clear them.

Quiet touches that make the list worth reading: a song still playing when the
poll comes round again folds into the entry already there (with a play count)
rather than filling the list with the same title six times, and stations that
broadcast their own name, "Live", or an advert marker instead of a track are left
out.

### Song History can tell you more than the title

**Song Details**, on any song in the Song History window. Quill Radio has always
recorded the artist and title a station broadcast, which makes a list of titles.
This answers the two questions people actually ask about something they just
heard: **which release it came from, what year it is, and how long it runs.**

It uses MusicBrainz, which needs no key and no account, and it is deliberately a
button rather than something that happens by itself. A history window that
quietly made a network request for every row would be spending your connection on
curiosity you never expressed. It never holds up playback, and when nothing is
known it says exactly that -- "MusicBrainz has nothing more about that song" --
rather than showing you an error about a server.

## One volume for every station

Quill Radio remembers a volume for each favorite. That is lovely when stations
are mastered at wildly different levels, and maddening when you simply want
everything quieter -- because the per-station level won outright, twenty
favorites meant twenty places to turn the volume down.

**Playback > Use One Volume for All Stations** fixes that. Tick it and a single
level answers for every station, so **Ctrl+Up** and **Ctrl+Down** turn
*everything* up or down instead of only the station you happen to be on. Ticking
it adopts whatever you are hearing at that moment, so nothing lurches.

Your per-station levels are not thrown away. Untick it and every station goes
straight back to its own remembered volume, exactly as it was -- so trying this
out costs you nothing. If you would rather be rid of them properly, **Forget
Every Station's Own Volume...** does that deliberately: it tells you how many
stations have one, asks first, and leaves your stations, folders, and every other
setting untouched.

It is off unless you turn it on, and the menu's checkmark follows the setting
however you change it -- from the menu, the Command Palette, or a shortcut you
rebound yourself.

## Broadcast polish, and the real engine behind it

Broadcast polish is the processing that stops a quiet programme and a loud one
from being two different listening experiences. Quill Radio has had it for a
while. Two things changed here, and the second is the one worth reading.

Everything in this section is built on **OptiLab Core**, the free accessible
broadcast and mastering engine by **Lanes Audio / dgl1984**
(<https://github.com/dgl1984/optilab>), used here with thanks and under its
Apache-2.0 with Commons Clause licence.

### The built-in chain got better

**Broadcast polish follows OptiLab Core.** If you use **Stream Polish**
for music, its Auto-Adapt slider behaves better now, particularly at the top.

Previously, raising Auto-Adapt pushed every stage harder at once -- the leveler,
the compressor and the limiter all leaned in together -- and that is what
produced the occasional volume lurch when the material changed. Following
upstream, each stage now fades in over its own part of the slider using
OptiLab's own smoothing curve, so there is no point where something switches on.
The leveler actually *eases off* as you raise Auto-Adapt, and a separate slow
loudness lift takes over instead.

That lift only responds to real program material: silence, low-level hiss and
rumble no longer cause it to build gain, which is the other half of what made
the old behaviour unpredictable. Bright, high-frequency moments get firmer
control as the slider rises rather than the flat presence boost the chain used
to apply at every setting, the limiter looks further ahead toward the top of the
range, and the whole chain now delivers to OptiLab's -0.1 dBFS target -- so high
settings give you more sustained loudness rather than more processing.

**Podcast Leveler** and **Smooth Limiter** are untouched: this release's
Auto-Adapt work is specific to Stream Polish.

This built-in version reproduces the *shape* of OptiLab's three modes --
**Podcast Leveler**, **Stream Polish** and **Smooth Limiter** -- as audio filters
rather than running the engine itself. That is why it works on any machine, needs
nothing compiled, and previews live as you move a control: every slider is
audible instantly, with no gap and no reconnect.

The next section is about running the real engine instead.

### And now the real thing

Reproducing the shape of those modes has one honest limit, and it is worth
stating plainly. OptiLab eases its lift and pulls back bass assistance *while*
its final limiter is working hard. A filter chain cannot do that: nothing in it
can see how hard a later stage is working, so there is no way to react to it.
Faking the effect would have meant guessing, and a guess dressed as a feature is
worse than an absence. There are smaller differences too -- the chain has none of
OptiLab's gated automatic gain control, its six-band density processing, its
adaptive bass, or its hybrid final stage, and Quill Radio's Podcast and Limiter
modes deliver to their own ceilings rather than OptiLab's.

So Quill Radio can now run the **actual** OptiLab engine. Lanes Audio's
processing code is included in the build and does the work itself, rather than
being imitated -- which means the feedback loop above simply happens, and what
you get is what OptiLab would have produced.

One new choice in Sound Enhancements, **Exact OptiLab processing**, says where:

- **Off** -- the built-in chain everywhere, exactly as before. This is the
  default, and nothing changes unless you change it.
- **When saving** -- recordings and converted files go through the real engine.
  Recommended.
- **When saving and while listening** -- everything does, including the stream
  you are listening to right now.

**Why listening is the option with a cost.** The engine is a separate program,
and Quill Radio's live playback never hands audio to anything else: it tells the
player what to apply and the player does it, which is exactly why every slider
you move is audible instantly, with no gap and no reconnect. Running the real
engine while you listen means routing the stream *through* that program --
decode, process, re-encode -- so the station takes a moment longer to start, uses
more of your processor, and, most noticeably, **needs a moment to reconnect every
time you change a setting**. The engine is set up with its mode when it starts
and cannot be re-tuned in mid-flight. It is a genuine trade, so it is a choice
you make, not one made for you.

Saving has none of those costs: a recording is processed once, *after* it
finishes, where taking a little longer costs nothing. And because it happens
afterwards, nothing that goes wrong in the engine can ever affect the recording
itself -- the original is only replaced once a good processed copy exists.

Everything else -- the equalizer, Even Out Volume, channel mode, night mode --
still applies exactly as it does today, whichever setting you choose. What
changes is only which piece of software does the broadcast polish.

It is entirely optional. If your build does not include the OptiLab component
the option is disabled and tells you so, and everything else works exactly as
before.

| | Built-in chain | Exact OptiLab |
| --- | --- | --- |
| Where it can run | Everywhere -- live, relayed, recorded | Everywhere, but live costs a reconnect on each change |
| Hear changes as you make them | Yes, instantly | Only on saved files; live needs a moment |
| Limiter feedback loop | Absent -- the chain cannot react to its own limiter | Present |

**Sound Enhancements answers Ctrl+E.** The three-band equalizer -- Bass, Mid and
Treble, each freely adjustable from -12 to +12 dB, with Flat, Bass Boost, Voice
Clarity, Podcast, Small Speakers and Late Night as starting points -- along with
the compressor, channel mode, night mode and broadcast polish, has been in Quill
Radio since 1.0.2. What it never had was a key of its own; you went through the
Playback menu every time. **Ctrl+E** now opens it. Everything inside still
previews live as you move a slider, and is still remembered per station as well
as shared.

## The playlist formats the internet actually uses

Quill Radio understood M3U. That covers a lot of the web, and not the part you
usually have in your hand.

A "Listen Live" link is at least as likely to be a **`.pls`** -- the standard
SHOUTcast and Icecast listen link -- or an **`.xspf`**, which is what the Xiph
directory itself serves, or an **`.asx`**, which is still what several radio
reading services publish. All three now open.

ASX deserves a note: in the wild it is frequently not valid XML at all -- unclosed
tags, mixed case, no declaration. It is read twice, once properly and once
forgivingly for when the file will not parse, because for that format the second
case is the common one rather than the exception.

**A live stream can no longer be imported as a list of stations.** An `.m3u8`
file is either a playlist of stations or a live stream's manifest, and the two
share an extension *and* a first line. Handing the second to the playlist
importer produced a list of two-second fragments presented to you as stations,
which is a genuinely baffling thing to be shown. They are now told apart before
anything else happens -- and what is inside the file wins over what the file is
called, because a server naming a live stream `.m3u` is common.

**Favorites export in four formats now** -- M3U, PLS, XSPF and ASX -- and every
one of them reads back in. A station name containing an ampersand survives the
round trip, which is not true of most playlist writers.

**A playlist file can no longer attack you.** XSPF and ASX are XML from
strangers, so they are read with entity expansion switched off. A small crafted
file that would expand to gigabytes of memory is refused out loud instead of
opened.

---

## Your stations, yours to keep

Here is the piece many of you asked for: a real backup you can carry to a new
machine. **Station > Back Up Stations and Settings...** gathers your favorites,
settings, wake timer, and recording schedule -- and, if you want them, your
recorded shows -- into a single `.qrbackup` file, and **Restore from Backup...**
brings it all home on a new PC, a new BrailleNote, or a fresh Windows. Made for
exactly the day you switch devices.

Underneath that, your favorites now protect themselves. Every change quietly
snapshots the previous version aside -- the **last 20 are kept** -- so a bad edit
or an accidental delete is never final; you can step back. That safety net is what
makes the Favorites Manager's **Remove All...** button safe to offer: clear every
station at once (your folders stay) behind a plain confirmation, and if you change
your mind, your list is still there to bring back. This is the "delete all my
favorites so I can import a fresh list in a different order" request, answered.

**Export Favorites to Playlist** (Station menu) saves your stations to an M3U
playlist you can hand to any media player, share, or keep as a plain-text backup
outside Quill Radio. It is the twin of Import Stations from Playlist, and the two
round-trip -- so exporting, re-ordering the file elsewhere, clearing your list,
and importing it back is now a complete, supported journey.

## Favorites, exactly the way you arranged them

If you have ever hand-sorted thirty stations into the order that makes sense to
*you*, this part is a love letter. Moving a favorite up or down from a sorted
A-to-Z view no longer quietly overwrites that hand-built order first: Quill Radio
switches to manual order (and says so -- "Switched to manual order"), then moves
the station, leaving your saved arrangement intact. When a long haul of arrow
presses feels absurd, **Mark and Move** does it in one gesture -- right-click (or
the Applications key) a station, choose **Mark for Move**, travel to the
destination, and pick **Move Marked Above** or **Move Marked Below**, and it jumps
straight there, adopting that spot's folder, on the main list and in the Manager
alike. The Manager's own **Move Up / Down / Above / Below** buttons work from the
alphabetical view now, too (they used to sit dead unless you were already in
manual order). **Ctrl+Shift+E** makes a **New Folder** from anywhere, including
with your cursor in the favorites tree. Adding a **custom station** shows it in
your list right away instead of looking as though nothing happened. And **TuneIn**
stations -- which only work out their stream when you play them -- can finally be
added to Favorites straight from Browse, stream and all.

### Quick-play your favorites

Ten commands -- *Play Favorite 1* through *Play Favorite 10* -- play the first
ten stations in your favorites list directly, without opening anything. They
default to **Ctrl+Alt+Shift+1** through **Ctrl+Alt+Shift+0** (the plain number
keys are already used by window switching, headings, and the copy tray), and like
every command they are rebindable in **Keyboard Shortcuts** -- set them to Alt+1
through Alt+0 if you prefer -- and appear on the Command Palette.

## The windows finally stay where you put them

For a while, opening Browse Stations, Search Stations, Manage Favorites, Schedule
Recording, or the Weather Center could make the menu bar seem to vanish into thin
air -- because those screens were dialogs, and a dialog cannot carry a menu bar --
and the modal ones locked you out of the main window entirely. They are proper
**windows** now. Each one carries the full menu bar, so the menus are always a
single **Alt** away no matter where you are, and none of them holds the main
window hostage; you can keep several open at once. A new **Window** menu lists
everything you have open, numbered in the order you opened it, and you move
between them the way you already do everywhere else: **Ctrl+Tab** for the next,
**Ctrl+Shift+Tab** for the previous, **Ctrl+1** through **Ctrl+9** to leap
straight to one. Each window opens only when you ask, and closing it sets you
gently back where you came from, announced as you land. The menus are there from
the very first keystroke, too: pressing **Alt** right after launch used to summon
the window's own Minimize/Maximize menu, because focus had not settled inside yet
-- focus lands in the window immediately now, so Alt opens Radio's own menu bar
the instant the app appears.

## The View menu: a dashboard you can read

A new **View** menu gathers several comforts in one place. **Show Station
Details** turns the read-only details box in Browse and Search on or off, and
every station screen honors your choice. **Show Status Bar** lays a strip along
the bottom of the main window that always tells you what is going on -- what is
playing, the volume (and whether Volume Boost is on), whether a recording is
running, the sleep timer, how many favorites you have, and the time. Press **F6**
to land in it, arrow left and right across the cells (**Home** and **End** jump to
the ends), and press **Enter** on a cell to *act*: Enter on Now Playing opens the
What's Playing window, on Volume mutes, on Recording starts or stops a capture, on
the Sleep timer opens it. Right-click any cell for more -- play and pause, mute,
volume up and down, Volume Boost, stop all recordings -- and **Escape** (or a
second F6) hands focus straight back to your favorites. The menu also lifts **Sort
Favorites** (Ascending, Descending, Unsorted) up out of Preferences, adds **Expand
All** and **Collapse All Folders** to open or shut your whole tree at once, and
offers **Text Size** (Normal, Large, Larger) to enlarge everything on the main
window together. Every choice here is remembered between sessions.

**Customize Features** (View menu) turns whole areas of Quill Radio on or off --
the **Recording** and **Weather** menus, each with a description. Uncheck one and
its whole menu (and every command under it) is left out the next time the app
opens, so you can trim Quill Radio to just what you use. Everything is on until
you turn it off.

## Everything Quill Radio says now reaches braille

Everything Quill Radio speaks -- What's Playing, a finished refresh, a recording
starting -- is now also written to a connected braille display, not only spoken.
Nothing is truncated, an identical message inside two seconds does not steal the
display twice, and braille never costs speech: an unplugged display or a reader
that refuses the call degrades to "spoke but did not braille", never to silence.
Turn it off with **Show announcements in braille** in Preferences >
Accessibility. A *burst* of different messages no longer flickers across the
display either -- the first message of a quiet period writes instantly and
anything landing within the next 150 ms settles to the newest, with errors always
writing through at once.

Speech is gone the moment it finishes, so **Repeat Last Announcement** (Command
Palette) brings the last thing Quill Radio said back. **Announcement
Self-Test...** announces a phrase and then tells you which channels actually
delivered it and through which backend, so "braille is broken" and "no display is
connected" stop looking the same. Quill Radio also gains its own sound cues, all
of which can be turned off or replaced from a sound pack.

## Reach Quill Radio from anywhere with one global hotkey

A new system-wide hotkey shows or hides Quill Radio without your having to find
its window first. Press **Ctrl+Alt+Shift+R** from inside any program -- your
browser, your editor, wherever you happen to be working -- and Quill Radio tucks
itself into the system tray, saying "hidden to the tray"; the music (or a
recording in progress) never stops, and the tray icon keeps it a keystroke away.
Press the same keys again and the window comes right back and takes focus,
announced with "shown". It is the fastest way to glance at what is playing, or to
step away and back, without leaving what you are doing. Windows only, and
courteous about it: if another app has already claimed Ctrl+Alt+Shift+R, Quill
Radio leaves that chord alone and never grabs it -- no error, nothing broken, and
the tray icon and the Alt+F4-to-tray preference still show and hide the window
exactly as before. Every app in the family gets its own chord so they never
collide: QUILL is Ctrl+Alt+Shift+Q, and Quill Weather is Ctrl+Alt+Shift+W.

## The QuillVille menu, and Weather as its own app

Quill Radio, QUILL, and Quill Weather each carry the same top-level **QuillVille**
menu (**Alt+Q**) listing every family member, so you can jump to any of them from
the same place everywhere. Opening an app that is already running just brings it
forward.

The weather work that grew up in this release has moved into a home of its own:
**Quill Weather**, a small, standalone, tray-resident app that watches your
location for official alerts, speaks each new warning the moment it is issued, can
start with Windows, and will even keep watch with no window open at all. Its full
story -- background alert monitoring, the customizable alert sounder, Test Alert,
the hour-by-hour forecast, the moon almanac, worldwide forecasts, and the rest --
now lives in the **Quill Weather release notes and user guide**, not here.

And the hand-off is real: the alert watch itself belongs to Quill Weather.
Quill Radio no longer resumes background alert monitoring at launch -- one
watcher, not two, and the radio opens talking about radio. Its Weather menu
still answers on demand whenever you ask.

It is still right where you expect it inside Quill Radio, too. The **Weather** menu
is present whenever the **Weather** feature is enabled (**View > Customize
Features...**), and it now leads with an **Open the Quill Weather App** item so you
can hand the watch off to the standalone app in one step. Turn Weather off in
Customize Features and the menu disappears entirely -- perfect if you only want the
radio.

And on the radio side, **Station > Start Quill Radio with Windows** launches Quill
Radio automatically when you sign in.

## A scheduled recording, and a computer that is actually awake for it

This one came from a listener, not a bug report -- which is the only way it
could have come. He scheduled a football pregame show for 11:00 and Quill Radio
announced the recording at 11:03. Nothing had failed. Nothing said anything was
wrong. He simply lost the first three minutes and had no way to find out why.

Here is why. A schedule is a thread inside a running application, and a
sleeping computer does not run threads. If Windows dozes off at 10:58 nobody
asks the schedule anything until the machine wakes, and the recording starts
then -- which from the outside is indistinguishable from the app losing track
of the time. Quill Radio has always kept the machine awake *while* something is
playing or recording. It did nothing at all about the quiet stretch beforehand,
which is exactly when a machine with nothing to do decides to sleep.

Three answers now, and they are meant to work together.

**It says so.** The scheduling window states the requirement in a line, before
you set anything: Quill Radio has to be running for a scheduled recording to
start, and the system tray counts. A requirement you only discover by losing
the first three minutes of a game is not a requirement, it is a trap.

**It holds sleep off as the time approaches.** For the few minutes before a
recording is due, Quill Radio asks Windows not to go to standby -- the same
request it already makes while a recording is running, simply started earlier.
This costs nothing when nothing is scheduled, and it covers the ordinary case
of a machine that is awake now and would have dozed at the worst possible
moment. (Your screen may still turn off. Only the computer has to stay up.)

**And it can wake the machine.** If the computer is *already* asleep when the
time comes, no amount of asking from inside a sleeping process will help --
only the operating system can wake it. So Quill Radio registers a Windows task
that does exactly that, a couple of minutes before the recording, then starts
Quill Radio if it is not already running. It is one task, replaced each time
your schedule changes and removed when nothing is scheduled, so Task Scheduler
never fills up with dead entries.

Both automatic parts are separate checkboxes in Preferences and both are on by
default. They are separate deliberately: holding sleep off is a small local
thing that needs no permissions, while waking the machine changes how your
computer behaves. Somebody may reasonably want the first and not the second,
and one switch would make that impossible to say.

**One thing that was already right, and is worth knowing.** A recording that
starts late does not run late at the other end. Quill Radio records the time
that is *left* in the window, so an 11:00 to 2:00 recording that starts at
11:03 still stops at 2:00 rather than overrunning into whatever you scheduled
next. That is also why a late start costs you the beginning rather than the
end -- and why, if you want a cushion before a show, the thing to do is start
the schedule earlier **and** lengthen it by the same amount.

## Recording, made sturdier in three ways

**An interrupted recording ends up as one file.** When a stream drops
mid-recording, Quill Radio reconnects and continues into a "(part 2)" file -- and
now, when the recording finishes, it stitches the pieces back into a single
recording under the name you expected. A show that dropped twice no longer leaves
you three files to find and play in order. The join is a straight copy, so nothing
is re-encoded and even a long capture takes seconds, and it is done in an order
that cannot lose your audio: the joined file is written, verified, and only then
put in place, and the parts are removed only once that has demonstrably worked.
Anything that goes wrong -- a missing part, parts in different formats, an FFmpeg
error -- leaves every part exactly where it is. You are told either way: "Joined 3
parts into one recording", or "Kept 3 separate parts" and the reason.

**A recording that stops recording is now noticed**, even when nothing reports a
problem. A stalled stream can leave FFmpeg alive and apparently healthy while the
file stops growing, so the recording looked fine and captured nothing. Quill Radio
now watches the recording file's size as a second, independent check: if it has
not gained a byte across four checks in a row -- about a minute -- the recording is
treated exactly like a dropped connection, so it reconnects and continues or stops
and saves what it captured. It is patient enough that a slow network or a
station's own rebuffering is never mistaken for a dead one, and it is never
applied to a recording you have just asked to stop.

**The scheduled-recordings list is ordered by when each recording next occurs**,
soonest first, rather than the order you entered them, and each row shows the
stream's host in brackets so two similar entries -- or a duplicate still pointing
at the original station -- are easy to tell apart.

## Winamp's keys, in the Recordings player

If you came to Windows audio through Winamp, its classic-skin keys never really
left your fingers. Until now the Recordings window answered to exactly two of
them -- Ctrl+Up and Ctrl+Down for volume -- and nothing else. There was no play,
no pause, no stop, no seek, nothing to move between recordings. The whole
transport set is now there, on the letter keys you already know, with no
modifier to reach for:

| Key | What it does |
| --- | --- |
| X | Play the selected recording, or resume a paused one |
| C | Pause / unpause |
| V | Stop |
| Shift+V | Stop (Winamp's fade-out; this player has no fade, so it stops cleanly) |
| B | Next recording -- moves down the list and plays it |
| Z | Previous recording |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| R | Shuffle on / off |
| S | Repeat: off, then all recordings, then this recording |
| Ctrl+V | Stop after the current recording |
| T | Elapsed time, or time remaining -- press again to swap |
| J | Jump to a recording: type any part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30`, or `1:02:03` |
| L | Open (the same as Play) |
| Ctrl+Up / Ctrl+Down | Volume up / down |

Every one of them says what it did. A transport key whose result you cannot hear
is not a working transport key, so "Playing", "Paused", "Back 5 seconds" and the
rest are spoken -- and brailled as well.

There are two places this deliberately parts company with Winamp, and both are
the better answer here rather than an oversight:

- **Ctrl+T stays What's Playing.** Winamp puts the elapsed/remaining toggle
  there; in a radio app, knowing what is on the air is worth more. The time
  toggle is on plain **T**, which nothing else was using.
- **Up and Down still move through the list.** In Winamp those are volume in the
  main window but list navigation in the Playlist Editor -- and the recordings
  list *is* a playlist editor by any other name. Volume stays on Ctrl+Up and
  Ctrl+Down, exactly where it already was.

### And the last three keys, which needed a queue first

**R**, **S** and **Ctrl+V** were held back on purpose. All three -- shuffle,
repeat, stop-after-current -- describe a play queue, and the recordings list did
not have one. Binding them to something that only looked like it worked would
have been worse than leaving them unbound, because you cannot tell a key that
does nothing from an app that is broken.

The list has a queue now, so they are bound.

**Shuffle (R) is a fixed order, not a fresh roll each time.** That distinction
is the whole feature. "Pick one at random on every Next" eventually plays the
same recording twice before it plays some others at all -- and, far worse here,
**Z** cannot take you back to what you just heard, because nothing recorded
where you had been. Shuffle instead reorders the whole list once: every
recording plays exactly once before any repeats, and previous is the exact
inverse of next.

**Repeat (S)** cycles off, then all recordings, then this recording, saying
which each time. Repeat-one applies when a recording *finishes on its own* --
pressing **B** still moves you on, because a Next that refused to move would
look broken rather than deliberate.

**Stop after current (Ctrl+V)** is a one-shot. It outranks repeat, because it is
the thing you asked for a moment ago rather than a standing preference; it
clears itself the instant it fires; and it is deliberately *not* remembered
between sessions. A stop that survived a restart would halt playback for a
reason nobody could remember asking for.

A recording that reaches its end is now followed by whatever the queue says is
next, rather than simply stopping. Shuffle and repeat are remembered; the
one-shot is not.

Seeking needs something with a timeline, which means a finished recording on the
mpv engine; on a live stream, or with the classic Windows Media engine, the seek
keys say why they cannot move rather than silently doing nothing. A letter typed
into a text field is never swallowed. And if you would rather have the letters
for list typeahead, **Winamp-style playback keys in the Recordings player** in
Preferences turns them off -- volume is unaffected either way.

The map itself lives in one small shared module with no wx in it, so anything
else in the family that grows a transport can adopt exactly these keys instead of
a second, subtly different set.

## Quillins in Quill Radio

Quill Radio can run Quillins -- QUILL's small, sandboxed, permission-gated add-ons
-- from its own Quillins menu. A Quillin declares which apps it is for, so only
add-ons written for the radio appear. One thing a radio Quillin can do is
contribute an extra station directory, which then shows up alongside RadioBrowser
and the others when you search. Off in Safe Mode; third-party Quillins stay
disabled in this release.

## Spotify (experimental)

Quill Radio can search Spotify, browse your library and playlists, and play
through Spotify's own playback engine. It is **experimental**, and it needs
setting up -- so here is the whole thing, plainly.

### Does a free Spotify account work?

**Yes for finding things, no for playing them inside Quill Radio.** The
distinction is worth being precise about, because it is easy to hear "Premium
required" and conclude a free account is useless here. It is not.

**What works on a free account:**

- Searching Spotify from inside Quill Radio.
- Browsing your saved shows, episodes, tracks, and playlists.
- Everything else in Quill Radio, which is untouched by any of this.

**What does not:**

- Audio starting *inside Quill Radio*. A track you choose here will not sound.

**Why -- and what this is not.** This is **not** "free accounts cannot play
Spotify music". Of course they can, and millions of people do every day, in
Spotify's own app, where the advertising that funds the free tier lives. The
restriction is about **where** the audio plays, not whether you are allowed to
listen. Spotify does not license other people's apps to stream free-tier audio,
and it says so plainly in its own developer documentation. There are exactly two
ways another app could play a Spotify track, and both are closed to free
accounts:

- The Web Playback SDK, which "requires a Spotify Premium subscription (mobile
  only types of premium subscriptions are excluded)".
- The Start/Resume Playback web endpoint, of which Spotify says: "This API only
  works for users who have Spotify Premium."

So with a free account, use Quill Radio to *find* things -- which is the part
that is genuinely hard with a screen reader -- and play them in the Spotify app.
Quill Radio now tells you which kind of account you signed in with, immediately,
rather than letting you discover it when a track silently refuses to start.

### Spotify in Find Stations

Because searching Spotify works on **every** account tier, Spotify results now
appear in **Find Stations** alongside the radio directories, once you have
connected your account. Search once and you see stations, shows, and tracks
together, instead of remembering which of two search boxes holds which kind of
thing.

- Songs read as "title, artist", so a list of results is still usable when
  several share a name.
- Shows read as "show, publisher".
- Every Spotify row is labelled **Spotify** in the Source column, and there is a
  **Spotify** entry in the Source filter if you want only those -- or want them
  out of the way.

On a Spotify row, Shift+F10 offers **Open in Spotify**, which opens it in the
Spotify app. That is deliberately not called "Open Website": on a free account
it is not a footnote about a station's home page, it is *how you play the thing*.
Premium subscribers can simply press Enter and hear it here.

If you have never connected Spotify, nothing changes -- no Spotify rows appear,
and Find Stations behaves exactly as before. Off in Safe Mode. If Spotify is
slow or unreachable, the rest of your results still arrive.

For the same reason, a Spotify selection can never be **recorded** or
**downloaded** on any account, unlike every other station in the app: the audio
is copy-protected.

### What you need

1. **A Spotify account** -- free or Premium, per above.
2. **Your own Spotify Client ID.** Quill Radio ships no shared identity, so
   nothing of yours passes through anyone else's account.
3. **Windows with the Edge WebView2 runtime**, which current Windows already has
   -- it arrives with Microsoft Edge.

### Getting your Client ID, step by step

1. Go to the **Spotify Developer Dashboard** at
   `https://developer.spotify.com/dashboard` and sign in with your ordinary
   Spotify account. There is no charge, and this works with a free account.
2. Choose **Create app**.
3. Give it any **App name** and **App description** you like -- they are just for
   you. "Quill Radio" is fine.
4. In **Redirect URI**, enter exactly this, then press **Add**:

   `http://127.0.0.1:43217/callback`

   It must match character for character, including the port number. This is how
   Spotify hands the finished sign-in back to your own computer; it never leaves
   your machine.
5. Under **Which API/SDKs are you planning to use?**, tick **Web API** and
   **Web Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your new app's **Settings**. Your **Client ID** is shown there -- copy it.

   You will also see a **Client secret**. **You do not need it**, and you should
   not paste it anywhere. Quill Radio signs in with the modern PKCE flow, which
   is designed precisely for apps that cannot keep a secret.

### Where to put it in Quill Radio

1. **Station > Connect to Spotify...**
2. Paste your Client ID into the **Client ID** field.
3. Choose **Connect**. Your browser opens Spotify's own approval page: you are
   signing in to Spotify, and your password is never typed into this app.
4. Approve access. Spotify returns you to a small address on your own machine
   (`127.0.0.1`) that Quill Radio listens on for that one moment.
5. Your sign-in is stored in the **Windows Credential Manager** -- never in a
   plain file, never in a log -- alongside your Client ID, so the whole
   connection lives in one place and clears together.

You do this once. Afterwards, **Station > Browse Spotify...** opens a search box and
a results list you can arrow through and play with Enter.

Nothing reaches Spotify until you deliberately connect an account, and the whole
feature is refused in Safe Mode. If you would rather not see it at all, turn
**Spotify** off in Manage Individual Features and its menu items disappear.

## The QuillVille Runtime: downloads that finally travel light

This is the big change in how Quill Radio is delivered. Quill Radio, QUILL, Quill
Weather, and QUILL Audio Studio now share **one** Python engine -- the
**QuillVille Runtime** -- installed just once per user and reused by every app in
the family. Install any one of them, and every app you add afterward starts
instantly, because the engine it needs is already there. No second copy, no
second long download. The runtime is reference-counted, so it is removed only
when the last app that relies on it is uninstalled; uninstalling Quill Radio
while Quill Weather is still around leaves the shared engine in place for
Weather.

That shared engine unlocks two brand-new, much smaller ways to get Quill Radio,
alongside the two full downloads you already knew:

- **Companion edition (new)** -- `Quill-Radio-Companion-<version>.zip`, about
  **3 MB**. Just the app and its docs, running on the shared runtime. The first
  time you launch it, if the runtime is not already installed, Quill Radio offers
  to download and install it once (about 230 MB) with a fully accessible progress
  bar. After that first time, this app and every other QuillVille app start
  instantly. Three megabytes instead of three hundred.
- **Thin installer (new)** -- the small "Lite" setup. It installs the app and
  downloads the shared runtime only if it is not already present. If you already
  run another QuillVille app, there is nothing large to fetch.
- **Full portable zip** -- `Quill-Radio-Portable-<version>.zip`, about **200 MB**.
  Still the one for a USB stick: fully self-contained, runs with no installation
  and no internet, carrying its own genuine, unmodified copy of Python plus the
  bundled ffmpeg and mpv engines.
- **Full installer** -- `Quill-Radio-Setup-Shared-<version>.exe`. The recommended
  path for most people: it installs the shared runtime (unless another QuillVille
  app already put it there) plus the app.

**Accessible progress, every time.** Whenever the runtime is downloaded -- by an
installer or by the Companion edition's own first launch -- Quill Radio shows a
progress bar that works with NVDA, JAWS, and Narrator, announcing progress as a
percentage the whole way.

**Friendlier to antivirus.** Quill Radio's launcher is now a genuine, tiny native
program, and the Python it runs is the official, unmodified build. Earlier
versions used a renamed and modified copy of Python's own `pythonw.exe` as the
launcher -- a pattern some antivirus tools flagged as a false positive. That
pattern is completely gone, so the app is far less likely to be mistaken for
something it is not. And as of 3.0, releases are **code-signed**: the
installers, the uninstallers, and the app itself carry a genuine Authenticode
signature, so SmartScreen and antivirus tools can verify exactly who built
what you are running.

The full picture, edition by edition, is in the **Installing** chapter of the
Quill Radio User Guide.

## An icon of its own -- and one for every app in the family

Quill Radio's icon was never the problem. The problem was that it was also **Quill Inkwell's icon, Quill Weather's icon, and QUILL Audio Studio's icon** -- byte-identical copies of the same file, not similar drawings. On a desktop with more than one Quill app installed, four different products wore one face in the taskbar, in Alt+Tab, in the Start menu and in the notification area. Nobody chose that; each new app was built from the last one's template, and an icon is easy not to notice.

Every app in the family now has its own, and they are still recognisably a set: one rounded tile shape, one gold accent, one bold picture. What separates them is deliberate on two axes at once -- a distinct silhouette *and* a distinct colour that differs in lightness as well as hue, because a set separated only by hue is a set that some colour-blind users cannot tell apart, and colour is the first thing to go at small sizes.

Radio keeps the design it always had -- a source with waves leaving it, on a deep indigo tile -- redrawn for the size that actually matters. At 16 by 16 pixels, which is the notification area and the small icons in a file list, the old three thin arcs merged into a single smear. There are now two, thicker and further apart.

## Things that were quietly wrong, and are not now

These are the ones worth reading even if none of the above interests you, because
every one of them was broken, and not one announced itself.

### The Xiph genre list was losing 412 genres, every single time

The Xiph directory's genre index had grown past a size limit Quill Radio applies
when reading any web page. So the page was being cut off part way through.

The reader is deliberately forgiving of a mangled page -- which is the right
behaviour when a website tweaks its markup, and precisely the wrong behaviour for
a size limit. It degraded in perfect silence: no error, no warning, just fewer
genres, and a *different* number of them on every refresh depending on where the
cut landed.

The limit now fits the page, and a page that ever outgrows it again says so
rather than dropping entries.

### The Xiph genre list was also sorted into uselessness

Xiph publishes its genres in order of how many stations use them: various, Pop,
Rock, Dance, 80s, House, Oldies, Electronic, Hits, Jazz.

Quill Radio sorted that alphabetically. So the list opened on `00`, then `00s`,
then `00s Dance`, then `100.1`, then `104.5` -- and Jazz was some three thousand
rows further down.

The directory's own order is now kept. Entries that are plainly not genres are
dropped, and the branch offers the 120 most-used rather than every free-text
string that three thousand broadcasters have ever typed into a field.

### A station that hiccuped once was dead

This one came in as a report while 3.0 was being finished, and it is the most
consequential fix in the release.

> *"Some stations such as KFI in Los Angeles play for about 20 seconds and then
> stop. JAWS says stop, which is how I know the station is not playing any more.
> Something similar is happening with another station where they talk for about
> 30 seconds and then the last five seconds repeat over again."*

The twenty seconds turned out to be exactly the shape of the problem. iHeart
serves its stations as HLS: a playlist of three ten-second segments -- a
**thirty-second window** -- behind a redirect to a per-listener address carrying
a token that expires in **five seconds**, topped up every ten. So the player is
permanently living on half a minute of buffered audio that has to be refilled
constantly.

Miss **one** refill and nothing appears to be wrong. The audio already in hand
keeps playing for twenty to thirty seconds, and then it simply runs out. Quill
Radio saw the stream reach its end, concluded the stream had ended, and said
"Stopped". The repeated five seconds is the same fault caught a moment earlier:
a connection silently re-established replays what it already sent.

That is now fixed in three places, and it is worth saying what each one does,
because they are three different answers to the same failure.

**The connection heals itself.** The player was given no instruction to
reconnect a dropped read at all, so a single transient failure was final. It now
reconnects at that level, which is where the great majority of these belong --
nothing is announced, because nothing was lost.

**A dropped station is reconnected, out loud.** When the connection is genuinely
gone rather than briefly interrupted, Quill Radio now tries to get it back
instead of stopping: three attempts, two seconds apart, then five, then fifteen,
each one announced with its number -- "Reconnecting to KFI AM 640. Attempt 1 of
3." When it works you hear "Reconnected to KFI AM 640." When it does not, you
are told that plainly, with the honest guess that the station may be off the
air. Nothing here retries silently, because a player that retries in silence is
indistinguishable from one that has hung.

A recording is deliberately excluded. A LibriVox chapter or an Archive episode
reaching its end has *ended*, and reconnecting would replay it. And pressing
Stop, or playing something else, cancels a retry that was waiting rather than
letting it seize playback a few seconds later.

**iHeart stations use their steadier stream.** Given the choice, Quill Radio now
asks iHeart for the progressive form of a station rather than the HLS form: one
long connection with no segment window, no five-second token and no per-listener
session to lose. It removes the failure mode rather than recovering from it, and
it streamed cleanly for a solid minute in testing where the HLS form is the one
that fails intermittently in the field. HLS remains the fallback for stations
that publish nothing else.

A note on the third part, because the obvious version of it is wrong. It would
be tempting to always prefer the steadier stream format wherever a station offers
both. But some directories list two addresses for one station that turn out to be
served by two entirely different companies -- and on at least one station, the
second one carries a different station id and a music genre where the station is
sports. Quietly playing you a different broadcaster would be far worse than a
dropout. So the steadier form is preferred only when both addresses come from the
same place, which is a good sign they are two deliveries of one stream. Where
they are not, the reconnection above does the work instead.

There is also a fourth, smaller change: the network timeout moved from fifteen
seconds to thirty. Fifteen was tight for a playlist that only advances every ten
seconds, and ordinary jitter could brush against it.

### A recording that captured nothing said nothing

Reported alongside the dropout above: pressing Record on a station that would not
stay connected gave no confirmation that a recording had started, none that it
had stopped, and left the recordings folder empty. Nothing told you anything had
gone wrong.

Two things were true at once. A recording file is created the moment recording
begins -- before a single second of audio arrives -- so "the file is there" never
meant "something was recorded". And when a capture ended having recorded nothing,
Quill Radio treated it exactly like a finished one.

Now a capture that saved nothing is reported as what it is, in words, with the
reason: *"Recording of 96.5 The Fan saved nothing: the connection failed. No file
was kept."* The empty file is removed rather than left for you to find and
wonder about, and the message uses the error sound rather than the saved sound,
so the two outcomes can never be mistaken for each other. Where the station said
why -- it refused the connection, the address is gone, the disk is full, the
folder could not be written to -- you are told that instead of a generic failure.

If the reason genuinely is not knowable, it says that too, rather than inventing
one.

### TuneIn could hand you an unencrypted stream

When a TuneIn station returned several addresses, Quill Radio took the first one
that was not TuneIn's own un-followable redirect. That is not the same as taking
the best one, and on at least one station in a sample of forty it meant choosing
a plain `http://` address while an `https://` one was sitting right there.

Stream choice is now ranked rather than filtered: not-a-redirect first, then
encrypted over unencrypted. It still prefers a working plain address over an
encrypted one that nothing can play, because an address that plays beats an
address that is merely tidy.

---

### It looks after itself now

A cluster of quiet reliability wins. Quill Radio **keeps your computer awake**
while a station plays or a recording runs, so Windows dozing off can no longer cut
a long listen -- or a scheduled capture -- short. (Your screen may still sleep to
save power; only the machine's sleep is held, and only while something is actually
going, and a Preferences checkbox turns it off if you would rather Quill Radio
never touch your power settings.) The **Stop button answers Alt+S** again: it used
to advertise Alt+S and Alt+P, which are really the Station and Playback menu keys,
so pressing them opened a menu instead of stopping the radio -- it no longer claims
those, and **Ctrl+P** stops or plays from anywhere, welcome when a loud station is
drowning out your screen reader. **Exit means exit**: if you close to the tray,
choosing Exit -- even from the tray menu -- genuinely quits now instead of ducking
back into hiding. On the pausing-and-rewinding engine, audio **stops firmly on
exit** rather than lingering for a beat (closing to the tray with Ctrl+W or the X
still keeps playing on purpose -- that is what the tray is for). **Install and
restart** no longer hangs behind a stray, focus-stealing terminal window; it runs
fully hidden and finishes. And you can **schedule a recording in hours and
minutes** now -- separate Hours and Minutes boxes, so three hours is simply "3" and
"0", no arithmetic (your existing schedules are unchanged).

**Output Device on the Playback menu (Ctrl+Shift+D).** Switch the radio to another
sound card or USB headset in one keystroke instead of opening Preferences. It
changes the device immediately and remembers the choice, exactly like the
Preferences setting it shortcuts.

### Smaller fixes

- **Quill Radio remembers your volume, and Ctrl+Up/Down works from anywhere.**
  The player started every session at 100% unless the station was a favorite with
  its own remembered level, so a non-favorite station came back at full blast on
  the next launch. The last level you set is now saved and restored (a favorite's
  own level still wins), and saving it no longer reloads the favorites list or
  re-announces the station. Separately, **Ctrl+Up** and **Ctrl+Down** only worked
  while the favorites tree had focus; they now work from any focus in the window
  -- except inside a text field, where Ctrl+arrow still edits text.
- **"Copy What's Playing" and "What's Playing - Review and Copy" always answer
  you.** With a station playing, both commands could come back having done nothing
  at all -- no window, no copy, no message -- while with nothing playing they spoke
  a sensible message, which made the bug look inverted. Now, if a station is on,
  both fetch the title first ("Checking what's playing..."), then copy it or open
  the review window; a stream that sends no titles says so and still opens a window
  naming the station; a failed lookup is reported instead of silently swallowed;
  and the copy confirmation names what it copied.
- **The Command Palette now says which way every toggle is currently set.**
  Two people asked for this about **Announce Track Titles**: the palette has no
  checkmark, so the entry read the same whichever way the switch actually was --
  you had to throw it to find out. It now reads **"Announce Track Titles
  (currently On)"** or **"(currently Off)"** and updates the moment you toggle
  it. That was never one entry's problem, though, so the fix was generalised:
  *every* on/off command in the palette now carries its own state, refreshed each
  time the palette opens.
- **Recording filenames follow the computer's current time zone.** Change the
  computer's time zone (or ride a daylight-saving shift) while Quill Radio is
  running and new recordings are named with the new local time straight away -- no
  restart. Filenames used to keep stamping the zone that was in force when the app
  launched.
- **Launching Quill Radio no longer crashes on a stray keystroke.** A key pressed
  at the wrong moment during launch could take the app down before its window
  appeared.
- **Every destructive question now defaults to No.** Remove Favorite, Delete
  Folder, Remove Recording, Remove All Favorites, and Reset Sound Enhancements all
  used to open with Yes as the default button, so pressing Enter reflexively
  destroyed the thing. Enter is now always the safe answer and you choose Yes
  deliberately. A build check keeps it that way.

## Underneath the browse tree: why the next source will be easy

This part is invisible and it is the reason the rest of this release exists.

The Browse window used to have to know how every single source worked. Adding one
meant teaching it a new special case in half a dozen places, and the
search-within-a-folder box needed a second copy of the same knowledge kept in
step by hand -- which is how a source could end up visible in the tree and
silently unsearchable, with nothing to tell you.

Every source now answers exactly one question: *what is inside this folder*. The
Browse window knows only that a row is something you can open or something you
can play, and nothing else. Fifteen new branches arrived that way in a single
release, and the window ended up **smaller** than it was.

That is why this section exists in release notes you would otherwise have no
reason to read: it is the difference between "we added a few sources" and "the
next one costs an afternoon".

Three smaller things came with it:

- **An empty branch tells you which kind of empty it is.** "There are no stations
  in this genre" and "that directory could not be reached" used to look
  identical. That is how a listener concludes a working source is broken -- or,
  worse, decides a broken one is simply empty and stops checking.
- **A folder says how big it is before you open it.** Where a source can tell us
  cheaply, the size is announced with the name, so you can decide whether to
  spend the wait before you have spent it.
- **Browse levels are remembered between sessions.** Opening a source used to
  fetch its whole index again every single time, and some of those are very
  large. They are kept now, so a branch opens straight away; a refresh that fails
  leaves you with what you had rather than an empty branch, and anything shown
  from memory can tell you how old it is instead of quietly implying it is
  current.

---

## Knowing when someone else's service moves

Quill Radio depends on eighteen services it does not control. Historically the
way we learned that one of them had changed was that something stopped working
for somebody.

Each of them is now checked automatically, thirty-seven checks in all, and each
one asks a real question rather than "did the server answer". Not *is it there*
but *did asking for that station give back an address that actually plays*.

Building those checks found three faults before any of this reached you: a
podcast category that came back completely empty when it should have held
dozens of shows, a country list that quietly reported having no regions at all,
and a directory that gave a different answer half an hour later.

All three would have shipped. Two would have looked like "that part just doesn't
find anything", which is the hardest kind of problem to report and the easiest to
put up with.

---
## What is not in 3.0, and why saying so matters

"Not mentioned" and "not built" look identical from the outside, so here is the
rest.

**Live streams still have no transcript.** The reader described above works on a
finished video's captions and on a published transcript, both of which exist as a
document before you open them. A live broadcast has no such document, and
producing one would mean transcribing audio as it arrives -- a different feature
with different costs, not a missing corner of this one.

**Quill Radio itself has no sync setup.** Where you got to in a recording is
remembered on the computer you were using. The full QUILL application can carry
those places to another machine through a shared folder; the standalone app does
not offer that window, so on its own, a place stays where it was made.

None of this is blocked; it is listed because you should not have to guess.

## Compatibility

Nothing in this release changes where your favorites, history, recordings or
settings are stored, and nothing needs migrating. Every new branch can be ignored
entirely; if you never open Browse Stations, Quill Radio 3.0 behaves exactly as
the version you are coming from did, minus the three faults above.

Safe Mode continues to disable every network source and to say so per branch,
while Favorites, ACB Media, NFB Radio and the Networks catalogue keep working
offline as before.

---
## Where the notes for 2.0 and 2.1 live

The 2.0 and 2.1 releases -- recordings you can trust, iHeart and TuneIn in the
search, weather radio and radio reading services -- have their own document,
`release-notes-2.0`, which ships in the `docs` folder beside this one.
